#!/usr/bin/env python3
"""Linux host: exclusive board ownership, DDR boot, network tests and restoration."""
import argparse,contextlib,datetime,json,os,pathlib,re,select,subprocess,sys,termios,time,signal,ipaddress
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bench import BenchError,container_path,verify_mount,verify_mapped_files,validate_uart
from hardware_lock import HardwareLock
from owned_process import OwnedProcessError,run_owned
from run_suite import run_bootstrap,restore_ddr
from peer import Peer

def root_command(args):
 cmd=['docker','exec','-u','root',os.environ.get('AGILEX_CONTAINER','agilex-xrdp'),*args]
 result=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
 if result.returncode:raise BenchError('Host NIC command failed: '+result.stderr.strip()+'; use a host-network container with NET_ADMIN for temporary addressing.')
 return result.stdout

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--interface',required=True);p.add_argument('--port',default=os.environ.get('AGILEX_UART',''))
 p.add_argument('--coordination-lock',action='append',default=[])
 p.add_argument('--smoke',action='store_true');p.add_argument('--seconds',type=int,default=30)
 p.add_argument('--tcp-stress',action='store_true')
 p.add_argument('--repeats',type=int,default=3);p.add_argument('--soak-seconds',type=int,default=600);p.add_argument('--quick',action='store_true')
 a=p.parse_args();validate_uart(a.port)
 if not 1<=a.seconds<=60 or not 1<=a.repeats<=5 or not 0<=a.soak_seconds<=900:p.error('seconds 1..60; repeats 1..5; soak 0..900')
 if not re.fullmatch(r'[A-Za-z0-9_.:-]+',a.interface):p.error('Invalid interface')
 if root_command(['readlink','/proc/self/ns/net']).strip()!=os.readlink('/proc/self/ns/net'):raise BenchError('The hardware container needs --network host for this Ethernet runner.')
 ipdata=json.loads(root_command(['ip','-j','address','show','dev',a.interface]))[0]
 v4=[x['local'] for x in ipdata['addr_info'] if x['family']=='inet']
 if v4 and (v4!=['192.168.50.1'] or next(x['prefixlen'] for x in ipdata['addr_info'] if x['family']=='inet')!=24):raise BenchError('Use a dedicated wired interface with no IPv4 address, or 192.168.50.1 only.')
 for route in json.loads(root_command(['ip','-j','route','show','table','main'])):
  dst=route.get('dst','default')
  if dst!='default' and route.get('dev')!=a.interface and ipaddress.ip_address('192.168.50.2') in ipaddress.ip_network(dst):
   raise BenchError('The benchmark subnet overlaps an existing route on another interface.')
 out=ROOT/'runs'/('ethernet-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));out.mkdir(parents=True)
 result={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'interface_before':ipdata,'tests':[],'restoration':'pending'}
 print('Evidence: '+str(out),flush=True)
 added=False;fd=None;peer=None;uncertain=False;failure=None;uart=b''
 with contextlib.ExitStack() as stack:
  for path in a.coordination_lock:stack.enter_context(HardwareLock(path))
  lock=stack.enter_context(HardwareLock())
  verify_mount();result['hashes']=verify_mapped_files([ROOT/'build/network.elf',ROOT/'bootstrap/ddr/ddr_probe.hps.rbf',ROOT/'bootstrap/ocram/agilex5.cfg'])
  if (ROOT/'build/network.json').is_file():
   result['build']=json.loads((ROOT/'build/network.json').read_text())
   if result['build']['elf_sha256']!=result['hashes'][str((ROOT/'build/network.elf').resolve())]:raise BenchError('Firmware differs from its build manifest')

  try:
   if not v4:root_command(['ip','addr','add','192.168.50.1/24','dev',a.interface]);added=True
   print('Initializing DDR...',flush=True)
   bootstrap=run_bootstrap(out/'bootstrap.log',a.port,lock)
   if bootstrap.returncode==3:raise OwnedProcessError('Uncertain bootstrap cleanup')
   if bootstrap.returncode:raise BenchError('DDR bootstrap failed')
   fd=os.open(a.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
   v=termios.tcgetattr(fd);v[0]=v[1]=v[3]=0;v[2]=termios.CS8|termios.CREAD|termios.CLOCAL;v[4]=v[5]=termios.B115200;v[6][termios.VMIN]=v[6][termios.VTIME]=0
   termios.tcsetattr(fd,termios.TCSANOW,v);termios.tcflush(fd,termios.TCIFLUSH)
   cfg=container_path(ROOT/'bootstrap/ocram/agilex5.cfg');elf=container_path(ROOT/'build/network.elf')
   command=f'hps.a55.0 configure -event halted {{}}; hps.a55.0 configure -event resumed {{}}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; load_image {elf}; resume 0x82600000; shutdown'
   (out/'load.log').write_text(run_owned(['openocd','-f',cfg,'-c',command],timeout=45))
   deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    if select.select([fd],[],[],.2)[0]:
     try:chunk=os.read(fd,65536)
     except BlockingIOError:continue
     if not chunk:raise BenchError('UART disconnected')
     uart+=chunk;(out/'server-uart.txt').write_bytes(uart);print(chunk.decode(errors='replace'),end='',flush=True)
    if b'FAIL ' in uart:raise BenchError('Firmware reported failure')
    if b'READY NETWORK:' in uart:break
   else:raise BenchError('Network startup timeout')
   peer=Peer();result['initial_stats']=peer.stats()
   ping=subprocess.run(['ping','-I',a.interface,'-c','3','-W','1','192.168.50.2'],capture_output=True,text=True,timeout=8)
   (out/'ping.log').write_text(ping.stdout+ping.stderr)
   if ping.returncode:raise BenchError('Ping failed')
   print('PASS ARP_PING',flush=True)
   result['tests']=peer.smoke()
   if a.tcp_stress:
    result['bandwidth']=[]
    for direction in ('pc_to_som','som_to_pc'):
     result['bandwidth'].append(peer.tcp_trial(direction,a.seconds,4))
     (out/'bandwidth.json').write_text(json.dumps(result['bandwidth'],indent=2)+'\n')
    result['bandwidth'].append(peer.tcp_bidir(a.seconds))
    (out/'bandwidth.json').write_text(json.dumps(result['bandwidth'],indent=2)+'\n')
   elif not a.smoke:result['bandwidth']=peer.bandwidth(out,a.seconds,a.repeats,a.soak_seconds,a.quick)
   result['final_stats']=peer.stats()
  except BaseException as exc:
   failure=exc;uncertain=isinstance(exc,OwnedProcessError);result['error']=f'{type(exc).__name__}: {exc}';print('ERROR '+result['error'],flush=True)
   if fd is not None and not uncertain:
    try:
     os.write(fd,b'D');deadline=time.monotonic()+2
     while time.monotonic()<deadline:
      if select.select([fd],[],[],.1)[0]:
       try:uart+=os.read(fd,65536)
       except BlockingIOError:pass
     (out/'server-uart.txt').write_bytes(uart)
    except OSError:pass

  finally:
   if peer:
    try:peer.command(5)
    except Exception:pass
    peer.close()
   if fd is not None:
    try:os.write(fd,b'Q')
    except OSError:pass
    time.sleep(.3)
    if select.select([fd],[],[],.2)[0]:
     try:uart+=os.read(fd,65536)
     except BlockingIOError:pass
    (out/'server-uart.txt').write_bytes(uart);os.close(fd)
   restore_ddr(out,result,a.port,lock,skip=uncertain)
   if added:
    try:root_command(['ip','addr','del','192.168.50.1/24','dev',a.interface]);result['host_address_restored']=True
    except Exception as exc:result['host_address_restored']=False;result['host_restore_error']=str(exc)
   result['interface_after']=json.loads(root_command(['ip','-j','address','show','dev',a.interface]))[0]
   (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 return 1 if failure or result['restoration']!='pass' or result.get('host_address_restored') is False else 0
if __name__=='__main__':
 def interrupted(*_):raise KeyboardInterrupt
 for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
 try:raise SystemExit(main())
 except (BenchError,OSError,subprocess.SubprocessError) as exc:print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(1)
