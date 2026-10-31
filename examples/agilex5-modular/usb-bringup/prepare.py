#!/usr/bin/env python3
"""Extract a reviewed U-Boot FIT payload for volatile USB bring-up; never boots it."""
import argparse,hashlib,json,struct,subprocess,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIT_SHA='9015fb9f50559364cd0e888e445e10f64b9e38dc7b219efedad033b8bbd0a6ef'
PAYLOAD_SHA='854df5f16661f72fa41ca3c90ef566be00c4b070094760dbb539e1c6e20b45ed'
FDT_SHA='b3d3ec1525c84ebb66bcb3b917f932b087eed485da35ba4a8a72d78fd9985384'
TEXT_BASE=0x80200000

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def capture(*args):return subprocess.check_output(args,text=True).strip()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fit',type=Path,required=True,help='Reviewed 26.1.1 baseline-a55 u-boot.itb')
    p.add_argument('--output',type=Path,default=ROOT/'build/usb-bringup')
    a=p.parse_args();fit=a.fit.resolve();out=a.output.resolve()
    if sha(fit)!=FIT_SHA:p.error('FIT differs from the reviewed offline artifact; no generic FIT boot is permitted')
    out.mkdir(parents=True,exist_ok=True)
    expected={'uboot':(0,PAYLOAD_SHA),'fdt-0':(2,FDT_SHA)}
    files={}
    for name,(index,expected_sha) in expected.items():
        target=out/('u-boot-nodtb.bin' if name=='uboot' else 'u-boot-original.dtb')
        subprocess.run(['dumpimage','-T','flat_dt','-p',str(index),'-o',str(target),str(fit)],check=True,capture_output=True)
        if sha(target)!=expected_sha:raise RuntimeError('Extracted component identity mismatch: '+name)
        crc=int(capture('fdtget','-t','x',str(fit),'/images/'+name+'/hash','value'),16)
        if zlib.crc32(target.read_bytes())!=crc:raise RuntimeError('FIT CRC mismatch: '+name)
        files[name]=target
    payload=files['uboot'].read_bytes();dtb=files['fdt-0'].read_bytes()
    text_base,end,bss_start,bss_end=struct.unpack_from('<QQQQ',payload,8)
    fit_load=int(capture('fdtget','-t','x',str(fit),'/images/uboot','load'),16)
    if text_base!=TEXT_BASE or fit_load!=TEXT_BASE or end!=len(payload):raise RuntimeError('Unexpected U-Boot ARM64 header/load/appended-FDT boundary')
    if not 0<bss_start<bss_end<=end:raise RuntimeError('Unexpected BSS offsets')
    if bytes.fromhex('d00dfeed') in payload:raise RuntimeError('U-Boot unexpectedly already contains FDT magic')
    if b'bootdelay=5\0' not in payload or b'bootcmd=run distro_bootcmd\0' not in payload:raise RuntimeError('Unexpected default autoboot environment')
    if b'preboot' in payload:raise RuntimeError('Unexpected preboot support/literal; review before any hardware run')
    model=capture('fdtget',str(files['fdt-0']),'/','model')
    if model!='SoCFPGA Agilex5 SoCDK A0 Modular':raise RuntimeError('Unexpected U-Boot DTB model')
    if struct.unpack_from('>I',dtb,0)[0]!=0xd00dfeed or struct.unpack_from('>I',dtb,4)[0]!=len(dtb):raise RuntimeError('Invalid original DTB')
    patched=out/'u-boot-no-autoboot.dtb';patched.write_bytes(dtb)
    subprocess.run(['fdtput','-c',str(patched),'/config'],check=True)
    subprocess.run(['fdtput','-t','x',str(patched),'/config','bootdelay','ffffffff'],check=True)
    if capture('fdtget','-t','x',str(patched),'/config','bootdelay')!='ffffffff':raise RuntimeError('Failed to disable autoboot through OF_CONTROL config override')
    combined=out/'u-boot-usb-volatile.bin';combined.write_bytes(payload+patched.read_bytes())
    metadata={'scope':'Offline extraction/preparation only; no U-Boot execution, USB enumeration, FPGA load or persistent write claimed',
      'fit_sha256':sha(fit),'source_fit':str(fit),'model':model,'u_boot_text_base':hex(TEXT_BASE),'u_boot_bytes':len(payload),'appended_fdt_address':hex(TEXT_BASE+len(payload)),
      'bss_start':hex(TEXT_BASE+bss_start),'bss_end':hex(TEXT_BASE+bss_end),'combined_bytes':combined.stat().st_size,
      'autoboot_guard':{'method':'appended OF_CONTROL /config/bootdelay override','value_u32':'0xffffffff','value_signed':-1,'expected_effect':'autoboot_command does not execute bootcmd, even if environment bootcmd is imported from media','preboot_literal_absent':True,'persistent_environment_changes':False},
      'files':{x.name:sha(x) for x in [files['uboot'],files['fdt-0'],patched,combined]},
      'prohibited_actions':['Do not boot FIT default configuration','Do not load FIT FPGA components','Do not run bootcmd/distro_bootcmd/bootm/booti','Do not saveenv or write SD/flash/EEPROM'],
      'next_step':'Build isolated RESET_TO_BL31 monitor with PRELOADED_BL33_BASE=0x80200000; main hardware operator reviews and loads through the shared mutex'}
    (out/'prepare.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('PASS USB_UBOOT_PREPARE: text=0x80200000 appended_fdt='+hex(TEXT_BASE+len(payload))+' autoboot=-1; OFFLINE ONLY')
if __name__=='__main__':main()
