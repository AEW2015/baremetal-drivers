#!/usr/bin/env python3
"""Bench-only bounded reference checks, using the shared Modular hardware mutex."""
import argparse,datetime,fcntl,hashlib,json,os,re,select,subprocess,sys,termios,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--bench',type=Path,required=True);p.add_argument('--mcp-client',type=Path,required=True)
 p.add_argument('--port',default='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
 a=p.parse_args();sys.path.insert(0,str(a.mcp_client.parent));from mcp_client import MCP
 out=ROOT/'runs'/('reference-hardware-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));out.mkdir(parents=True)
 record={'scope':'Semihost source executing in physical OCRAM; read-only exception-register probe in DDR','tests':[],'restoration':'pending','runner_sha256':digest(Path(__file__)),'bootstrap_sha256':digest(a.bench/'ddr-bringup/ddr_probe.hps.rbf')}
 def save():(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
 lock=(a.bench/'examples/hardware.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 m=MCP('programmer');bootstrap_failed=False;fd=None;print('Evidence: '+str(out),flush=True);save()
 def bootstrap(label):
  nonlocal bootstrap_failed
  chain=m.call('read_jtag_config',{});(out/(label+'-chain.json')).write_text(json.dumps(chain,indent=2)+'\n')
  text=json.dumps(chain).lower()
  if '364f0dd' not in text:raise RuntimeError('Modular ES identity missing')
  r=subprocess.run([sys.executable,str(a.bench/'ddr-bringup/run_ddr.py'),'--port',a.port]+(['--full-recovery'] if '4ba06477' not in text else []),capture_output=True,timeout=230)
  (out/(label+'-bootstrap.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:bootstrap_failed=True;raise RuntimeError('Bootstrap failed; stopping board operations')
 def debug(script,label,timeout=30):
  source=a.bench/'examples/build'/(out.name+'-'+label+'.tcl');source.write_text(script)
  (out/(label+'.tcl')).write_text(script)
  cmd=['docker','exec','agilex-xrdp','timeout','--kill-after=5s',str(timeout)+'s','openocd','-f','/home/dev/baremetal-guide-validation/ocram/agilex5.cfg','-f','/home/dev/baremetal-guide-validation/examples/build/'+source.name]
  r=subprocess.run(cmd,capture_output=True,timeout=timeout+10)
  body=(r.stdout+r.stderr).decode(errors='replace');(out/(label+'.log')).write_text(body)
  return r.returncode,body
 prefix='''hps.a55.0 configure -event halted {}
hps.a55.0 configure -event resumed {}
gdb port disabled
tcl port disabled
telnet port disabled
init
halt
hps.dap apsel 0x4000
set csw_report [hps.dap apcsw]
if {![regexp {csw (0x[0-9a-fA-F]+)} $csw_report -> old_csw]} {error "CSW decode failed"}
hps.dap apcsw 0x10000000 0x30000000
'''
 try:
  image=ROOT/'build/reference-hardware/semihost.bin';elf=image.with_suffix('.elf')
  if not image.is_file() or not elf.is_file():raise RuntimeError('Build the reference ELF first')
  bootstrap('semihost')
  payload=a.bench/'examples/build'/(out.name+'-semihost.bin');payload.write_bytes(image.read_bytes())
  remote='/home/dev/baremetal-guide-validation/examples/build/'+payload.name
  readback=Path(str(payload)+'.readback');readback.unlink(missing_ok=True)
  script=prefix+f'''targets hps.sys_bus
load_image {remote} 0x20000 bin
dump_image {remote}.readback 0x20000 {image.stat().st_size}
hps.dap apcsw $old_csw
targets hps.a55.0
arm semihosting enable
bp 0x20010 4 hw
resume 0x20004
wait_halt 5000
puts [get_reg {{pc}}]
rbp 0x20010
puts "REFERENCE_SEMIHOST_STOP_COMPLETE"
shutdown
'''
  code,body=debug(script,'semihost-debug',15)
  passed=code==0 and 'Error:' not in body and 'Hello, World! Agilex 5 HPS executing from OCRAM.' in body and 'REFERENCE_SEMIHOST_STOP_COMPLETE' in body and re.search(r'pc 0x0*20010\b',body) is not None and readback.is_file() and readback.read_bytes()==image.read_bytes()
  record['tests'].append({'name':'semihost','status':'pass' if passed else 'fail','elf_sha256':digest(elf),'binary_sha256':digest(image),'source_sha256':digest(ROOT/'bootstrap/ocram/hello_semihost.S'),'entry':'0x20004','completion_pc':'0x20010','debug_exit':code});save();print('semihost: '+record['tests'][-1]['status'],flush=True)
  bootstrap('fault-probe')
  elf=ROOT/'build/fault_probe.elf';payload=a.bench/'examples/build'/(out.name+'-fault-probe.elf');payload.write_bytes(elf.read_bytes())
  fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK);v=termios.tcgetattr(fd);v[0]=v[1]=v[3]=0;v[2]=termios.CS8|termios.CREAD|termios.CLOCAL;v[4]=v[5]=termios.B115200;v[6][termios.VMIN]=v[6][termios.VTIME]=0;termios.tcsetattr(fd,termios.TCSANOW,v);termios.tcflush(fd,termios.TCIFLUSH)
  script=prefix+f'''targets hps.sys_bus
load_image /home/dev/baremetal-guide-validation/examples/build/{payload.name}
hps.dap apcsw $old_csw
targets hps.a55.0
resume 0x82500000
shutdown
'''
  code,body=debug(script,'fault-probe-debug');uart=b'';deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   if select.select([fd],[],[],.1)[0]:
    try:data=os.read(fd,65536)
    except BlockingIOError:continue
    if not data:raise RuntimeError('UART disconnected')
    uart+=data
   if b'HPS FAULT PROBE COMPLETE' in uart:break
  os.close(fd);fd=None
  (out/'fault-probe-uart.txt').write_bytes(uart)
  required=[b'HPS FAULT PROBE BEGIN',b'ESR_EL3 = ',b'ELR_EL3 = ',b'FAR_EL3 = ',b'SCTLR_EL3 = ',b'CPTR_EL3 = ',b'HPS FAULT PROBE COMPLETE']
  passed=code==0 and 'Error:' not in body and all(x in uart for x in required) and b'FAIL ' not in uart
  record['tests'].append({'name':'fault-probe','status':'pass' if passed else 'fail','elf_sha256':digest(elf),'source_sha256':digest(ROOT/'core/fault_probe.c'),'debug_exit':code,'scope':'Reads exception state; does not inject or recover a fault'});save();print('fault-probe: '+record['tests'][-1]['status'],flush=True)
 except BaseException as exc:record['error']=repr(exc);save();raise
 finally:
  if fd is not None:os.close(fd)
  try:
   if bootstrap_failed:record['restoration']='not attempted after bootstrap failure'
   else:bootstrap('restore');record['restoration']='pass'
  except BaseException as exc:record['restoration']='fail';record['restore_error']=repr(exc)
  save();m.close();lock.close();print('DDR Hello restoration: '+record['restoration'],flush=True)
 return int(record['restoration']!='pass' or any(t['status']!='pass' for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
