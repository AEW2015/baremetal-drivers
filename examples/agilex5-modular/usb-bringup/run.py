#!/usr/bin/env python3
"""Host: bounded volatile U-Boot USB session, followed by DDR Hello restoration."""
import argparse,datetime,fcntl,hashlib,json,os,re,select,subprocess,sys,termios,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def allowed_command(command):
    fixed={'version','bdinfo','usb start','usb tree','usb info','usb storage','usb dev 0',
           'printenv bootdelay bootcmd preboot','dm tree','net list',
           'usb_lab_mouse 1','usb_lab_mouse 4','usb_lab_mouse 8','usb_lab_phy',
           'md.l 0x10c03200 2','md.l 0x10c03250 1','md.l 0x10d13008 1','md.l 0x10d13028 1',
           'setenv ethrotate no','setenv autostart no','setenv ipaddr 192.168.50.3',
           'setenv serverip 192.168.50.1','setenv netmask 255.255.255.0',
           'ping 192.168.50.1','tftpboot 0x82000000 usb-demo.bin',
           'usb read 0x82200000 0 8','usb read 0x82300000 0 8',
           'hash sha256 0x82200000 0x1000','hash sha256 0x82300000 0x1000',
           'hash sha256 0x82000000 0x100000'}
    return command in fixed or re.fullmatch(r'setenv ethact (?:usb_ether|r8152|asix|ax88179|lan75|lan78|smsc95)[A-Za-z0-9_#@.:+-]*',command) is not None

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bench',type=Path,required=True)
    p.add_argument('--mcp-client',type=Path,required=True)
    p.add_argument('--uboot',type=Path,default=ROOT/'build/usb-bringup/u-boot-usb-volatile.bin')
    p.add_argument('--monitor',type=Path,default=ROOT/'build/usb-bringup-atf/agilex5/debug/bl31.bin')
    p.add_argument('--port',default='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
    p.add_argument('--command',action='append',help='One allowed console command; repeat to select commands')
    p.add_argument('--timeout',type=int,default=60)
    p.add_argument('--queue',type=Path,help='Optional append-only JSON command list; __DONE__ restores DDR Hello')
    p.add_argument('--queue-seconds',type=int,default=300)
    a=p.parse_args()
    commands=a.command or ['version','bdinfo','usb start','usb tree','usb info','usb storage','net list']
    if any(not allowed_command(c) for c in commands):p.error('Command outside the USB/read-only-media/isolated-network allowlist')
    if not 5<=a.timeout<=120:p.error('timeout must be 5..120 seconds')
    if not 30<=a.queue_seconds<=600:p.error('queue-seconds must be 30..600')
    for path in [a.uboot,a.monitor]:
        if not path.is_file():p.error('Prepare artifact first: '+str(path))
    out=ROOT/'runs'/('usb-uboot-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));out.mkdir(parents=True)
    record={'scope':'Volatile U-Boot USB session; no persistent environment or media writes','uboot_sha256':digest(a.uboot),'monitor_sha256':digest(a.monitor),'runner_sha256':digest(Path(__file__)),'commands':[],'restoration':'pending'}
    def save():(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    lock=(a.bench/'examples/hardware.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('Shared hardware mutex busy; no board access')
    print('Evidence: '+str(out),flush=True);save()
    sys.path.insert(0,str(a.mcp_client.parent));from mcp_client import MCP
    m=MCP('programmer');fd=None;old=None;bootstrap_failed=False
    cfg='/home/dev/baremetal-guide-validation/ocram/agilex5.cfg'
    prefix='hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; '
    def debug(command,label):
        result=subprocess.run(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','300s','openocd','-f',cfg,'-c',command],capture_output=True,timeout=310)
        (out/(label+'.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('OpenOCD failed: '+label)
    def bootstrap(label):
        nonlocal bootstrap_failed
        chain=m.call('read_jtag_config',{});(out/(label+'-chain.json')).write_text(json.dumps(chain,indent=2)+'\n')
        if '364f0dd' not in json.dumps(chain).lower():raise RuntimeError('Modular ES FPGA identity missing')
        result=subprocess.run(['python3',str(a.bench/'ddr-bringup/run_ddr.py'),'--port',a.port]+(['--full-recovery'] if '4ba06477' not in json.dumps(chain).lower() else []),capture_output=True,timeout=230)
        (out/(label+'-bootstrap.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:bootstrap_failed=True;raise RuntimeError('DDR bootstrap failed; stop board operations')
    def receive(timeout,guard=False):
        body=b'';deadline=time.monotonic()+timeout;last_guard=0;last_data=time.monotonic()
        prompt=re.compile(rb'(?:SOCFPGA[^\r\n]*#|=>) *[\r\n]*$')
        while time.monotonic()<deadline:
            if select.select([fd],[],[],.1)[0]:
                try:data=os.read(fd,65536)
                except BlockingIOError:continue
                if not data:raise RuntimeError('UART disconnected')
                body+=data;last_data=time.monotonic()
                if len(body)>2*1024*1024:raise RuntimeError('UART output exceeds 2 MiB bound')
            if prompt.search(body.replace(b'\r',b'')) and time.monotonic()-last_data>.25:return body,True
            if guard and time.monotonic()-last_guard>.4:
                os.write(fd,b' ');last_guard=time.monotonic()
        return body,False
    try:
        bootstrap('initial')
        for path,address,secure,label in [(a.uboot,0x80200000,False,'uboot'),(a.monitor,0x80000000,True,'monitor')]:
            name=out.name+'-'+label+'.bin';destination=a.bench/'examples/build'/name;destination.write_bytes(path.read_bytes())
            remote='/home/dev/baremetal-guide-validation/examples/build/'+name;readback=Path(str(destination)+'.readback');readback.unlink(missing_ok=True)
            secure_set='hps.dap apsel 0x4000; set old_csw [hps.dap apcsw]; hps.dap apcsw 0x10000000 0x30000000; ' if secure else ''
            secure_restore='hps.dap apcsw $old_csw; ' if secure else ''
            debug(prefix+secure_set+f'targets hps.sys_bus; load_image {remote} {address:#x} bin; dump_image {remote}.readback {address:#x} {path.stat().st_size}; '+secure_restore+'shutdown',label+'-load')
            if not readback.is_file() or readback.read_bytes()!=path.read_bytes():raise RuntimeError('Load/readback mismatch: '+label)
            record[label+'_readback']='pass';save()
        fd=os.open(a.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK);old=termios.tcgetattr(fd)
        attrs=termios.tcgetattr(fd);attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[4]=attrs[5]=termios.B115200;attrs[6][termios.VMIN]=attrs[6][termios.VTIME]=0;termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIFLUSH)
        debug(prefix+'reg x0 0; reg x1 0; reg x2 0; reg x3 0; resume 0x80000000; shutdown','resume')
        body,ready=receive(a.timeout,guard=True);(out/'boot-uart.txt').write_bytes(body)
        record['uboot_prompt']=ready;save();print(body[-6000:].decode(errors='replace'),flush=True)
        if not ready:
            try:debug(prefix+'reg pc; reg cpsr; reg sp; reg x0; reg x1; reg x2; reg x3; shutdown','boot-stop-diagnostics')
            except Exception as exc:record['diagnostic_error']=repr(exc);save()
            raise RuntimeError('U-Boot prompt was not observed; no commands sent')
        # Discard guard spaces before the first command; this never starts boot.
        os.write(fd,b'\x03');receive(2)
        def console(command,index,budget=None):
            os.write(fd,command.encode()+b'\r')
            body,ready=receive(a.timeout if budget is None else min(a.timeout,budget))
            (out/f'{index:02d}-console.txt').write_bytes(body)
            item={'command':command,'prompt_returned':ready}
            if command=='usb start':
                text=body.decode(errors='replace').replace('\r','')
                item['xhci_started']=bool(re.search(r'^USB XHCI [0-9a-fA-F]+\.[0-9a-fA-F]+',text,re.M)) and 'No USB controllers found' not in text
                item['device_counts']=[int(n) for n in re.findall(r'(\d+) USB Device\(s\) found',text)]
                item['external_devices_observed']=item['xhci_started'] and any(n>1 for n in item['device_counts'])
            if command=='usb_lab_phy':
                item['phy_id_pass']=bool(re.search(rb'^PASS USB_PHY_ID USB3320 ',body,re.M)) and b'FAIL USB_' not in body
            record['commands'].append(item);save();print(command+'\n'+body[-7000:].decode(errors='replace'),flush=True)
            if not ready:raise RuntimeError('Console command did not return: '+command)
        # Network downloads must remain data in RAM, even if an imported vendor
        # environment had enabled automatic execution after TFTP completion.
        console('setenv autostart no',len(record['commands']))
        for command in commands:console(command,len(record['commands']))
        if a.queue:
            print('USB_COMMAND_QUEUE_READY '+str(a.queue),flush=True)
            record['queue_ready']=True;save();seen=[];deadline=time.monotonic()+a.queue_seconds
            while time.monotonic()<deadline:
                if (out/'CANCEL').exists():raise RuntimeError('Session cancelled; restoring DDR Hello')
                if a.queue.exists():
                    if a.queue.stat().st_size>16384:raise RuntimeError('Command queue exceeds 16 KiB bound')
                    pending=json.loads(a.queue.read_text())
                    if not isinstance(pending,list) or len(pending)>64 or pending[:len(seen)]!=seen:raise RuntimeError('Command queue must be an append-only JSON list, at most 64 entries')
                    done=False
                    for command in pending[len(seen):]:
                        if command=='__DONE__':done=True;break
                        if not isinstance(command,str) or not allowed_command(command):raise RuntimeError('Queued command outside the safe allowlist')
                        remaining=deadline-time.monotonic()
                        if remaining<=0:raise RuntimeError('Command queue deadline exceeded; restoring DDR Hello')
                        console(command,len(record['commands']),remaining);seen.append(command)
                    if done:break
                time.sleep(.2)
        record['session_complete']=True;save()
    except BaseException as exc:record['error']=repr(exc);save();raise
    finally:
        if fd is not None:
            try:
                if old is not None:termios.tcsetattr(fd,termios.TCSANOW,old)
            except Exception as exc:record['uart_restore_error']=repr(exc)
            finally:
                try:os.close(fd)
                except Exception as exc:record['uart_close_error']=repr(exc)
        try:
            if bootstrap_failed:record['restoration']='not attempted after bootstrap failure'
            else:bootstrap('restore');record['restoration']='pass'
        except Exception as exc:record['restoration']='fail';record['restore_error']=repr(exc)
        save();m.close();lock.close();print('DDR Hello restoration: '+record['restoration'],flush=True)
    starts=[c for c in record['commands'] if c['command']=='usb start']
    phys=[c for c in record['commands'] if c['command']=='usb_lab_phy']
    return int(record['restoration']!='pass' or bool(starts) and not starts[-1]['external_devices_observed'] or any(not c['phy_id_pass'] for c in phys))

if __name__=='__main__':raise SystemExit(main())
