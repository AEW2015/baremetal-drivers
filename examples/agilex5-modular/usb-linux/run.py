#!/usr/bin/env python3
"""Boot a verified Linux USB lab through U-Boot, using RAM only."""
import argparse
import datetime
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import termios
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stack_bench import StackBench
from bench import validate_uart,verify_mount
from tftp import Server
ADDRESSES={'Image':0x82000000,'initramfs.cpio.gz':0x86000000,'board.dtb':0x81f00000,'u-boot.bin':0x80200000,'bl31.bin':0x80000000}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prompt_seen(data,linux=False):
    # Kernel hotplug messages may follow the shell prompt before UART settles.
    pattern=rb'(?:^|\n)USB_LINUX# ' if linux else rb'(?:SOCFPGA[^\r\n]*#|=>) *[\r\n]*$'
    return re.search(pattern,data.replace(b'\r',b'')) is not None

def validate_bundle(folder):
    record=json.loads((folder/'build.json').read_text())
    if record['addresses']!=ADDRESSES:raise ValueError('Unexpected RAM address plan')
    if record['linux_commit']!='0c0e456cdde08783d0a56ef593af45899f5d11af':raise ValueError('Linux pin mismatch')
    for name in ADDRESSES:
        path=folder/name;expected=record['artifacts'][name]
        if not path.is_file() or path.stat().st_size!=expected['bytes'] or sha(path)!=expected['sha256']:
            raise ValueError('Missing or changed artifact: '+name)
    if record['artifacts']['Image']['bytes']>0x3000000 or record['artifacts']['initramfs.cpio.gz']['bytes']>0x800000:
        raise ValueError('RAM payload exceeds reserved window')
    return record

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=ROOT/'build/usb-linux/bundle')
    parser.add_argument('--port',default=os.environ.get('AGILEX_UART',''))
    parser.add_argument('--bind',default='192.168.50.1')
    parser.add_argument('--board-ip',default='192.168.50.3')
    parser.add_argument('--usb-peer',default=os.environ.get('AGILEX_USB_PEER',''),help='PC IPv4 address reachable through the USB Ethernet switch; omit to skip ping')
    parser.add_argument('--transport',choices=('tftp','jtag'),default='tftp')
    parser.add_argument('--queue',type=Path,help='Append-only JSON list of reviewed Linux diagnostic names')
    parser.add_argument('--hold-seconds',type=int,default=0)
    a=parser.parse_args();bundle=a.bundle.resolve();manifest=validate_bundle(bundle)
    for address in (a.bind,a.board_ip,*([a.usb_peer] if a.usb_peer else [])):
        if not ipaddress.IPv4Address(address).is_private:parser.error('Use the isolated private test network')
    if not 0<=a.hold_seconds<=600:parser.error('Hold bound is 0..600 seconds')
    validate_uart(a.port);verify_mount();stack=StackBench()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=ROOT/'runs'/('usb-linux-'+stamp);out.mkdir(parents=True)
    record={'scope':'Volatile U-Boot to Linux USB lab; RAM root; no media/environment/NVM writes',
            'manifest':manifest,'commands':[],'restoration':'pending','status':'running','mouse_report':'not tested','usb_ethernet':'not tested'}
    record['runner_sha256']=sha(Path(__file__))
    record['tftp_source_sha256']=sha(Path(__file__).with_name('tftp.py'))
    record['source_revision']=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    record['network']={'boot_server':a.bind,'boot_board':a.board_ip,'usb_peer':a.usb_peer or None}
    def save():(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Evidence:',out,flush=True);save()
    lock=stack.lock_path.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    from mcp_client import MCP
    mcp=MCP('programmer');fd=None;old=None;uncertain=False;touched=False;bootstrap_failed=False
    prefix='hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; '
    def chain(label):
        chain=mcp.call('read_jtag_config',{});(out/(label+'-chain.json')).write_text(json.dumps(chain,indent=2)+'\n')
        body=chain.get('text','')
        blocks=re.split(r'(?m)^  (?=\d+:)',body)
        matches=[b for b in blocks if re.match(r'\d+: Agilex_5E MDK Carrier',b) and any(int(value,16)==0x0364f0dd for value in re.findall(r'JTAG ID 0x([0-9A-Fa-f]+)',b))]
        if len(matches)!=1 or not matches[0].startswith('1:'):raise RuntimeError('Cannot uniquely verify the Modular ES carrier as cable 1')
    def bootstrap(label):
        nonlocal touched,bootstrap_failed
        chain(label);touched=True
        result=stack.bootstrap(a.port,lock.fileno(),full=True)
        (out/(label+'-bootstrap.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:
            bootstrap_failed=True
            raise RuntimeError('DDR bootstrap failed: '+label)
    def debug(script,label,budget=120):
        nonlocal uncertain
        path=stack.payload(out.name+'-'+label+'.tcl');path.write_text(script+'\n')
        uncertain=True
        result=subprocess.run(stack.command(['timeout','--kill-after=5s',str(budget)+'s','openocd','-f',stack.cfg,'-f',stack.remote(path)]),capture_output=True,timeout=budget+15)
        uncertain=False;(out/(label+'.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('OpenOCD operation failed: '+label)
    def receive(budget,linux=False,guard=False):
        data=b'';deadline=time.monotonic()+budget;last=time.monotonic();last_guard=0
        while time.monotonic()<deadline:
            if select.select([fd],[],[],.1)[0]:
                try:chunk=os.read(fd,65536)
                except BlockingIOError:continue
                if not chunk:raise RuntimeError('SOM UART disconnected')
                data+=chunk;last=time.monotonic()
                if len(data)>4*1024*1024:raise RuntimeError('UART evidence exceeds bound')
            if prompt_seen(data,linux) and time.monotonic()-last>.2:return data,True
            if guard and time.monotonic()-last_guard>.4:os.write(fd,b' ');last_guard=time.monotonic()
        return data,False
    def command(text,label,budget=60,linux=False):
        os.write(fd,text.encode()+b'\r');data,ready=receive(budget,linux=linux)
        (out/(label+'-uart.txt')).write_bytes(data)
        record['commands'].append({'command':text,'label':label,'prompt_returned':ready});save()
        print(label+':\n'+data[-8000:].decode(errors='replace'),flush=True)
        if not ready:raise RuntimeError('Console did not return: '+label)
        return data.decode(errors='replace').replace('\r','')
    diagnostics={
        'report':'/bin/usb-lab',
        'dmesg':'dmesg',
        'flash':'/bin/usb-flash-read',
        'mouse':'/bin/usb-mouse-read',
        'network':'ip link show; ip addr show',
        'drivers':'for d in /sys/bus/platform/devices/*11000000*; do echo \"$d\"; ls -l \"$d/driver\"; cat \"$d/modalias\"; done',
        'uptime':'cat /proc/uptime',
        'usb-network':'/bin/usb-net-test '+a.usb_peer if a.usb_peer else 'echo USB_ETH_TEST_SKIPPED_NO_PEER',
    }
    try:
        bootstrap('initial')
        for name in ('u-boot.bin','bl31.bin'):
            chain(name)
            image=stack.payload(out.name+'-'+name);image.write_bytes((bundle/name).read_bytes())
            rb=Path(str(image)+'.readback');rb.unlink(missing_ok=True)
            secure='hps.dap apsel 0x4000; set old_csw_text [hps.dap apcsw]; if {![regexp {(0x[0-9a-fA-F]+)$} $old_csw_text -> old_csw]} {error {Cannot decode original AP CSW}}; hps.dap apcsw 0x10000000 0x30000000; ' if name=='bl31.bin' else 'hps.dap apsel 0x4000; '
            restore='hps.dap apcsw $old_csw; ' if name=='bl31.bin' else ''
            debug(prefix+secure+f'targets hps.sys_bus; load_image {stack.remote(image)} {ADDRESSES[name]:#x} bin; dump_image {stack.remote(image)}.readback {ADDRESSES[name]:#x} {image.stat().st_size}; '+restore+'shutdown',name+'-load')
            if not rb.is_file() or rb.read_bytes()!=image.read_bytes():raise RuntimeError('Firmware readback mismatch: '+name)
        record['firmware_readback']='pass';save()
        fd=os.open(a.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK);old=termios.tcgetattr(fd)
        attrs=termios.tcgetattr(fd);attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[4]=attrs[5]=termios.B115200;attrs[6][termios.VMIN]=attrs[6][termios.VTIME]=0
        termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIFLUSH)
        debug(prefix+'reg x0 0; reg x1 0; reg x2 0; reg x3 0; resume 0x80000000; shutdown','start-uboot')
        data,ready=receive(80,guard=True);(out/'uboot-boot-uart.txt').write_bytes(data)
        if not ready:raise RuntimeError('U-Boot did not reach its guarded prompt')
        os.write(fd,b'\x03');receive(2)
        command('setenv autostart no','disable-autostart')
        command('version','uboot-version')
        transport=a.transport
        if transport=='tftp':
            command('setenv ethrotate no','fixed-boot-interface')
            command('setenv ethact ethernet@10830000','select-hps-emac2')
            command('setenv ipaddr '+a.board_ip,'board-ip')
            command('setenv serverip '+a.bind,'server-ip')
            command('setenv netmask 255.255.255.0','netmask')
            command('setenv tftpdstp 1069','tftp-port')
            reply=command('ping '+a.bind,'boot-link',budget=25)
            if 'is alive' not in reply:
                record['tftp_link']='not established';transport='jtag'
                print('HPS Ethernet boot link unavailable; using checked JTAG RAM loads',flush=True)
        files={name:(bundle/name).read_bytes() for name in ('Image','initramfs.cpio.gz','board.dtb')}
        record['boot_transport']=transport;save()
        if transport=='tftp':
            with Server(a.bind,a.board_ip,files) as server:
                for name in files:
                    command(f'tftpboot {ADDRESSES[name]:#x} {name}','tftp-'+name,budget=100)
                    body=command(f'hash sha256 {ADDRESSES[name]:#x} {len(files[name]):#x}','hash-'+name)
                    if manifest['artifacts'][name]['sha256'] not in body:raise RuntimeError('Board SHA256 mismatch: '+name)
                record['tftp']=server.events;record['tftp_errors']=server.errors;save()
        else:
            command('dcache off','uncached-jtag-loads')
            for name,data in files.items():
                chain('payload-'+name);image=stack.payload(out.name+'-'+name);image.write_bytes(data)
                debug(prefix+f'hps.dap apsel 0x4000; targets hps.sys_bus; load_image {stack.remote(image)} {ADDRESSES[name]:#x} bin; targets hps.a55.0; resume; shutdown','payload-'+name,budget=600)
                body=command(f'hash sha256 {ADDRESSES[name]:#x} {len(data):#x}','hash-'+name)
                if manifest['artifacts'][name]['sha256'] not in body:raise RuntimeError('Board SHA256 mismatch: '+name)
        record['linux_payload_hashes']='pass';save()
        command('setenv bootargs '+manifest['bootargs'],'linux-bootargs')
        initrd=manifest['artifacts']['initramfs.cpio.gz']['bytes']
        body=command(f'booti 0x82000000 0x86000000:{initrd:#x} 0x81f00000','linux-boot',budget=120,linux=True)
        record['linux_ready']='USB_LINUX_READY' in body;save()
        if not record['linux_ready']:raise RuntimeError('Linux readiness marker absent')
        report=command('sleep 2; '+diagnostics['report'],'linux-usb-report',linux=True)
        counts=re.findall(r'USB_LAB_COUNTS external_devices=(\d+) external_hubs=(\d+)',report)
        record['external_devices'],record['external_hubs']=map(int,counts[-1]) if counts else (0,0)
        flash=command(diagnostics['flash'],'linux-flash-read',linux=True)
        record['flash_read']='USB_FLASH_READ_PASS' in flash
        command(diagnostics['dmesg'],'linux-dmesg',linux=True)
        command(diagnostics['network'],'linux-network',linux=True)
        mouse=command(diagnostics['mouse'],'linux-mouse',linux=True)
        record['mouse_report']='pass' if re.search(r'(?m)^[0-9a-f]{7,8}\s+[0-9a-f]{4}\s',mouse) else 'no fresh reports'
        network=command(diagnostics['usb-network'],'linux-usb-ethernet',budget=60,linux=True)
        record['usb_ethernet']='pass' if re.search(r'(?m)^USB_ETH_PING_PASS ',network) else 'not established'
        save()
        if a.queue and a.hold_seconds:
            print('USB_LINUX_COMMAND_QUEUE_READY '+str(a.queue),flush=True)
            seen=0;deadline=time.monotonic()+a.hold_seconds
            while time.monotonic()<deadline:
                if (out/'CANCEL').exists():break
                if a.queue.exists():
                    values=json.loads(a.queue.read_text())
                    if not isinstance(values,list) or len(values)>30:raise ValueError('Invalid diagnostic queue')
                    for item in values[seen:]:
                        if item=='done':deadline=0;break
                        if item not in diagnostics:raise ValueError('Unknown Linux diagnostic')
                        reply=command(diagnostics[item],'queued-'+str(seen)+'-'+item,linux=True)
                        if item=='report':
                            counts=re.findall(r'USB_LAB_COUNTS external_devices=(\d+) external_hubs=(\d+)',reply)
                            if counts:record['external_devices'],record['external_hubs']=map(int,counts[-1])
                        if item=='flash':record['flash_read']='USB_FLASH_READ_PASS' in reply
                        if item=='mouse' and re.search(r'(?m)^[0-9a-f]{7,8}\s+[0-9a-f]{4}\s',reply):record['mouse_report']='pass'
                        if item=='usb-network' and re.search(r'(?m)^USB_ETH_PING_PASS ',reply):record['usb_ethernet']='pass'
                        seen+=1;save()
                time.sleep(.2)
        record['status']='pass' if record['external_hubs']>0 and record['flash_read'] and record['mouse_report']=='pass' and record['usb_ethernet']=='pass' else 'partial'
        save()
    except BaseException as error:
        record['status']='fail';record['error']=repr(error);save();raise
    finally:
        if fd is not None:
            try:
                if old is not None:termios.tcsetattr(fd,termios.TCSANOW,old)
            except OSError as error:record['uart_restore_error']=repr(error)
            finally:os.close(fd);fd=None
        try:
            if touched and not uncertain and not bootstrap_failed:bootstrap('restore');record['restoration']='pass'
            elif touched:record['restoration']='not attempted after bootstrap failure' if bootstrap_failed else 'not attempted: programming completion uncertain'
            else:record['restoration']='not needed'
        except BaseException as error:record['restoration']='fail';record['restore_error']=repr(error)
        save();mcp.close();lock.close();print('DDR Hello restoration:',record['restoration'],flush=True)
    return int(record['status']!='pass' or record['restoration']!='pass')
if __name__=='__main__':raise SystemExit(main())
