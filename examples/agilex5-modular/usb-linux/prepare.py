#!/usr/bin/env python3
"""Package a source-built kernel and static BusyBox for a volatile USB lab."""
import argparse
import gzip
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def archive(entries):
    """Deterministic newc archive, including console nodes without host root."""
    result=bytearray()
    for ino,(name,mode,data,major,minor) in enumerate(entries+[('TRAILER!!!',0,b'',0,0)],1):
        name=name.encode()+b'\0'
        fields=(ino,mode,0,0,1,0,len(data),0,0,major,minor,len(name),0)
        result+=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)+name
        result+=b'\0'*(-len(result)%4)
        result+=data
        result+=b'\0'*(-len(result)%4)
    return gzip.compress(bytes(result),mtime=0)

def fdt(path,*args):
    subprocess.run(['fdtput','-t','s',str(path),*args],check=True,capture_output=True)

def nodes(path,node='/'):
    yield node
    children=subprocess.check_output(['fdtget','-l',str(path),node],text=True).splitlines()
    for name in children:yield from nodes(path,node.rstrip('/')+'/'+name)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel',type=Path,default=ROOT/'build/usb-linux/kernel')
    p.add_argument('--busybox',type=Path,default=ROOT/'build/usb-linux/busybox/busybox')
    p.add_argument('--uboot',type=Path,default=ROOT/'build/usb-linux/uboot/u-boot-usb-standalone.bin')
    p.add_argument('--monitor',type=Path,default=ROOT/'build/usb-bringup-atf-26.3/agilex5/debug/bl31.bin')
    p.add_argument('--output',type=Path,default=ROOT/'build/usb-linux/bundle')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    binary=a.busybox.read_bytes()
    if binary[:4]!=b'\x7fELF' or struct.unpack_from('<H',binary,18)[0]!=183:
        raise ValueError('BusyBox must be an AArch64 ELF')
    segments=struct.unpack_from('<H',binary,56)[0]
    off=struct.unpack_from('<Q',binary,32)[0];size=struct.unpack_from('<H',binary,54)[0]
    if any(struct.unpack_from('<I',binary,off+i*size)[0]==3 for i in range(segments)):
        raise ValueError('BusyBox must be statically linked; PT_INTERP found')
    entries=[(name,0o040755,b'',0,0) for name in ('bin','sbin','usr','usr/bin','usr/sbin','dev','proc','sys','run','tmp','etc')]
    entries += [('dev/console',0o020600,b'',5,1),('dev/null',0o020666,b'',1,3),('bin/busybox',0o100755,binary,0,0),('bin/sh',0o120777,b'busybox',0,0)]
    for name in ('init','usb-lab','usb-flash-read','usb-net-test','udhcpc-hook','usb-mouse-read'):
        target=name if name=='init' else 'bin/'+name
        entries.append((target,0o100755,(ROOT/'usb-linux'/name).read_bytes(),0,0))
    (a.output/'initramfs.cpio.gz').write_bytes(archive(entries))
    shutil.copyfile(a.kernel/'arch/arm64/boot/Image',a.output/'Image')
    image=(a.output/'Image').read_bytes()
    if image[56:60]!=b'ARM\x64':raise ValueError('Missing AArch64 Image header')
    if struct.unpack_from('<Q',image,16)[0]>0x3000000:raise ValueError('Kernel exceeds reserved 48 MiB load window')
    dtb=a.output/'board.dtb'
    shutil.copyfile(a.kernel/'arch/arm64/boot/dts/intel/socfpga_agilex5_socdk_a0_modular.dtb',dtb)
    reservation=subprocess.check_output(['fdtget','-t','x',str(dtb),'/reserved-memory/svcbuffer@0','reg'],text=True).split()
    if [int(cell,16) for cell in reservation]!=[0,0x80000000,0,0x02000000]:
        raise ValueError('Expected vendor 32 MiB no-map firmware/service reservation')
    # A bounded RAM-only memory map. No storage or unrelated fabric probing.
    subprocess.run(['fdtput','-t','x',str(dtb),'/memory@80000000','reg','0','80000000','0','08000000'],check=True)
    disabled=[]
    for node in list(nodes(dtb)):
        name=node.rsplit('/',1)[-1]
        if name.startswith(('mmc','nand','spi@','ethernet@','fpga-region','fpga-mgr','eccmgr','watchdog')) or name=='usb@10b00000':
            fdt(dtb,node,'status','disabled');disabled.append(node)
    usb=[node for node in nodes(dtb) if node.endswith('@11000000')]
    if len(usb)!=1:raise ValueError('Cannot identify USB31 controller')
    parent=usb[0]
    # Follow this kernel's intel,socfpga-dwc3.yaml binding: wrapper + core.
    # The vendor board DTS is flat; of-simple otherwise creates no core child.
    properties=('reg','interrupts','iommus','phys','phy-names','maximum-speed',
                'snps,dis_u2_susphy_quirk','snps,dis_u3_susphy_quirk',
                'snps,dma_set_40_bit_mask_quirk')
    core=parent+'/usb@11000000'
    subprocess.run(['fdtput','-c',str(dtb),core],check=True)
    fdt(dtb,parent,'compatible','intel,agilex5-dwc3')
    fdt(dtb,core,'compatible','snps,dwc3')
    for prop in properties:
        value=subprocess.run(['fdtget','-t','bx',str(dtb),parent,prop],capture_output=True,text=True)
        if value.returncode:continue
        values=value.stdout.split()
        if values:subprocess.run(['fdtput','-t','bx',str(dtb),core,prop,*values],check=True)
        else:fdt(dtb,core,prop)
        if prop!='reg':subprocess.run(['fdtput','-d',str(dtb),parent,prop],check=True)
    fdt(dtb,parent,'status','okay');fdt(dtb,core,'status','okay')
    fdt(dtb,core,'dr_mode','host')
    bootargs='console=ttyS0,115200n8 earlycon=uart8250,mmio32,0x10c02000 rdinit=/init maxcpus=1 clk_ignore_unused loglevel=7 panic=0'
    fdt(dtb,'/chosen','bootargs',bootargs)
    # A malformed status/compatible string silently prevents Linux probing.
    for node,prop,value in ((parent,'compatible','intel,agilex5-dwc3'),
                            (core,'compatible','snps,dwc3'),(core,'status','okay'),
                            (core,'dr_mode','host'),('/chosen','bootargs',bootargs)):
        actual=subprocess.check_output(['fdtget','-t','s',str(dtb),node,prop],text=True).strip()
        if actual!=value:raise ValueError('Device-tree string validation failed: '+node+'/'+prop)

    shutil.copyfile(a.uboot,a.output/'u-boot.bin');shutil.copyfile(a.monitor,a.output/'bl31.bin')
    result={'scope':'Source-built RAM-only USB lab; execution verdict is recorded by run.py',
            'linux_commit':subprocess.check_output(['git','-C',str(ROOT/'.deps/usb-linux-source-26.3'),'rev-parse','HEAD'],text=True).strip(),
            'linux_config_sha256':sha(a.kernel/'.config'),'busybox_version':'1.37.0',
            'stack_pins':json.loads((ROOT/'stack-versions.json').read_text()),
            'source_sha256':{name:sha(ROOT/name) for name in
                ('usb-linux/build.sh','usb-linux/kernel.config','usb-linux/prepare.py',
                 'usb-linux/init','usb-linux/usb-lab','usb-linux/usb-flash-read',
                 'usb-linux/usb-mouse-read','usb-linux/usb-net-test','usb-linux/udhcpc-hook',
                 'usb-bringup/build_uboot.sh','usb-bringup/patch_monitor.py')},
            'bootargs':bootargs,'disabled_nodes':disabled,
            'reserved_memory':{'base':0x80000000,'bytes':0x02000000,'purpose':'Vendor no-map service buffer also protects resident BL31'},
            'addresses':{'Image':0x82000000,'initramfs.cpio.gz':0x86000000,'board.dtb':0x81f00000,'u-boot.bin':0x80200000,'bl31.bin':0x80000000},
            'artifacts':{name:{'bytes':(a.output/name).stat().st_size,'sha256':sha(a.output/name)} for name in ('Image','initramfs.cpio.gz','board.dtb','u-boot.bin','bl31.bin')}}
    (a.output/'build.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS USB_LINUX_PREPARE',a.output)
if __name__=='__main__':main()
