#!/usr/bin/env python3
"""Host hardware runner; fresh DDR boot per ELF, bounded capture, durable results."""
import argparse,datetime,hashlib,json,os,pathlib,re,select,signal,subprocess,sys,termios,time
from bench import (BenchError, HELP, container_command, container_path, validate_uart,
                   verify_mount, verify_container_tools, verify_mapped_files)
from hardware_lock import HardwareLock
from owned_process import OwnedContainerProcess, OwnedProcessError, run_owned
ROOT=pathlib.Path(__file__).resolve().parent
PORT=os.environ.get('AGILEX_UART','')
TESTS={
 'core':{'elf':'core_examples','entry':0x82100000,'markers':['PASS CPU_NEON','PASS CACHE_INFO','PASS DDR_BUFFERS','PASS GPIO_READ','PASS COUNTER','PASS GIC_INFO','HPS CORE EXAMPLES COMPLETE']},
 'dma':{'elf':'dma_copy','entry':0x82200000,'markers':['PASS DMA_COPY']},
 'gic':{'elf':'gic_sgi','entry':0x82300000,'markers':['PASS GIC_SGI']},
}
TESTS['mmu']={'elf':'mmu_translation','entry':0x82400000,'markers':['PASS MMU_TRANSLATION']}
for name,elf,markers in [('som','som_peripherals',['PASS HPS_TIMER','PASS WATCHDOG_IRQ','PASS SPI_LOOPBACK','PASS GPIO_LED_PAD','PASS I2C_IDENT','HPS SOM PERIPHERALS COMPLETE']),('som-i2c','som_i2c',['PASS SOM_TEMP_ID','PASS SOM_EEPROM_READ','HPS SOM I2C EXAMPLE COMPLETE']),('multicore','multicore',['PASS MULTICORE'])]:
 TESTS[name]={'elf':elf,'entry':0x82400000,'markers':markers}
TESTS['som-i3c']={'elf':'som_i3c','entry':0x82400000,'markers':['PASS NATIVE_I3C_TEMP','PASS NATIVE_I3C_EEPROM','HPS NATIVE I3C EXAMPLE COMPLETE']}
TESTS['mailbox']={'elf':'mailbox_status','entry':0x82400000,'markers':['PASS MAILBOX_IDCODE']}
TESTS['interfaces']={'elf':'som_interfaces','entry':0x82400000,'markers':['PASS SOM_PHY_ID','PASS SDMMC_IDENT','PASS USB_IDENT','HPS SOM INTERFACES COMPLETE']}
for name in ['uart','ccu','clkmgr','smmu','ecc']:
 TESTS['vendor-'+name]={'elf':'vendor_'+name,'entry':None,'markers':['HPS_SUITE_PASS '+name+' rc=0x00000000']}
DEFAULT_NAMES=','.join(TESTS)
# Optional unchanged legacy timer body, bounded by the same host runner.
TESTS['vendor-timer']={'elf':'vendor_timer','entry':None,'markers':['Timer count set','Timer mode set','Timer started','Timer expired -- test pass','HPS_SUITE_PASS timer rc=0x00000000']}
# SPI's original test transmits to an EEPROM; mailbox test asserts Simics offsets.
# Their board-specific replacements are registered separately when built.
def container(args,timeout=45):
 return subprocess.run(container_command(args),capture_output=True,timeout=timeout)
def save(out,result):
 temp=out/'results.json.tmp';temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(out/'results.json')
def run_one(name,out,port,lock,full_recovery=False):
 t=TESTS[name];elf=ROOT/'build'/(t['elf']+'.elf')
 result={'name':name,'elf':str(elf),'sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'status':'running'}
 start=time.monotonic()
 print(f'[{name}] Initializing DDR; follow {out/(name+"-bootstrap.log")} for live stages.',flush=True)
 bootstrap=run_bootstrap(out/(name+'-bootstrap.log'),port,lock,full_recovery)
 if bootstrap.returncode==3:raise OwnedProcessError('Bootstrap could not confirm process shutdown; inspect its log before another hardware operation.')
 if bootstrap.returncode:raise BenchError('DDR bootstrap failed: '+str(out/(name+'-bootstrap.log')))
 verify_mapped_files([elf],expected={str(elf):result['sha256']})
 print(f'[{name}] Loading {elf.name} and collecting fresh UART results...',flush=True)
 entry=t['entry']
 if entry is None:
  hdr=container(['aarch64-none-elf-readelf','-h',container_path(elf)])
  entry=int(re.search(rb'Entry point address:\s*(0x[0-9a-fA-F]+)',hdr.stdout)[1],16)
 fd=os.open(port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
 data=b'';proc=None
 try:
  v=termios.tcgetattr(fd);v[0]=v[1]=v[3]=0;v[2]=termios.CS8|termios.CREAD|termios.CLOCAL
  v[4]=v[5]=termios.B115200;v[6][termios.VMIN]=v[6][termios.VTIME]=0
  termios.tcsetattr(fd,termios.TCSANOW,v);termios.tcflush(fd,termios.TCIFLUSH)
  cfg=container_path(ROOT/'bootstrap/ocram/agilex5.cfg')
  cmd=f'hps.a55.0 configure -event halted {{}}; hps.a55.0 configure -event resumed {{}}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; load_image {container_path(elf)}; resume 0x{entry:x}; shutdown'
  with (out/(name+'-debug.log')).open('wb') as log:
   proc=OwnedContainerProcess(['openocd','-f',cfg,'-c',cmd],stdout=log,stderr=subprocess.STDOUT)
   deadline=time.monotonic()+35;terminal_at=None
   while time.monotonic()<deadline:
    if select.select([fd],[],[],.2)[0]:
     try: chunk=os.read(fd,65536)
     except BlockingIOError: continue
     if not chunk:raise RuntimeError('UART disconnected')
     data+=chunk;(out/(name+'-uart.bin')).write_bytes(data)
    # Require results following this program's begin message, ignoring old Hello.
    begin=b'HPS_SUITE_BEGIN ' if name.startswith('vendor-') else b'HPS '
    if name=='core':begin=b'HPS CORE EXAMPLES BEGIN'
    if name=='dma':begin=b'HPS DMA EXAMPLE BEGIN'
    if name=='gic':begin=b'HPS GIC SGI EXAMPLE BEGIN'
    if name=='mmu':begin=b'HPS MMU EXAMPLE BEGIN'
    if name=='som':begin=b'HPS SOM PERIPHERALS BEGIN'
    if name=='som-i2c':begin=b'HPS SOM I2C EXAMPLE BEGIN'
    if name=='multicore':begin=b'HPS MULTICORE EXAMPLE BEGIN'
    if name=='som-i3c':begin=b'HPS NATIVE I3C EXAMPLE BEGIN'
    if name=='mailbox':begin=b'HPS MAILBOX EXAMPLE BEGIN'
    if name=='interfaces':begin=b'HPS SOM INTERFACES BEGIN'
    current=data[data.find(begin):] if begin in data else b''
    if proc.poll() is not None and (all(x.encode() in current for x in t['markers']) or b'HPS_SUITE_FAIL' in current or b'FAIL ' in current):
     if terminal_at is None:terminal_at=time.monotonic()
     if time.monotonic()-terminal_at>.5:break
   proc.close()
  current=data[data.find(begin):] if begin in data else b''
  passed=proc.returncode==0 and bool(current) and all(x.encode() in current for x in t['markers']) and b'HPS_SUITE_FAIL' not in current and b'FAIL ' not in current
  if not passed:
   diagnostic=run_owned(['openocd','-f',cfg,'-c','hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; echo [reg pc]; echo [reg cpsr]; echo [reg x0]; echo [reg x1]; shutdown'],timeout=45)
   (out/(name+'-halt.log')).write_text(diagnostic)
  result.update(status='pass' if passed else 'fail',entry=f'0x{entry:x}',elapsed_seconds=round(time.monotonic()-start,1),missing=[x for x in t['markers'] if x.encode() not in current],debug_returncode=proc.returncode,observed_pass_markers=re.findall(r'^PASS[^\r\n]*',current.decode(errors='replace'),re.M),failure_lines=re.findall(r'^(?:FAIL|HPS_SUITE_FAIL)[^\r\n]*',current.decode(errors='replace'),re.M))
  print(name+': '+result['status'],flush=True)
  print(current.decode(errors='replace')[-2200:],flush=True)
  return result
 finally:
  os.close(fd)
  if proc is not None:proc.close()
def run_bootstrap(log_path,port,lock,full_recovery=False):
 cmd=[sys.executable,str(ROOT/'bootstrap/ddr/run_ddr.py'),'--port',port]
 if full_recovery:cmd.append('--full-recovery')
 with log_path.open('wb') as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,**lock.child_options())
  try:
   proc.wait(timeout=420)
  except (subprocess.TimeoutExpired,KeyboardInterrupt):
   # Let the child run its owned-container-process cleanup before restoring.
   proc.terminate()
   try:proc.wait(timeout=30)
   except subprocess.TimeoutExpired:
    proc.kill();proc.wait()
    raise OwnedProcessError(f'Bootstrap cleanup did not finish; keep {log_path}. Do not reprogram until owned process state is checked.')
   if proc.returncode==3:raise OwnedProcessError(f'Bootstrap cancellation is uncertain; inspect {log_path}.')
   raise
  return proc

def restore_ddr(out,results,port,lock,skip=False):
 print('[restore] Restoring DDR Hello; inspect restore.log for live stages.',flush=True)
 if skip:
  results['restoration']='error'
  results['restoration_error']='Not attempted: previous owned-process shutdown was not verified.'
  (out/'restore.log').write_text(results['restoration_error']+'\n')
 else:
  try:
   restore=run_bootstrap(out/'restore.log',port,lock)
   results['restoration']='pass' if restore.returncode==0 else 'fail'
   if restore.returncode:results['restoration_error']=f'DDR initializer exited {restore.returncode}; inspect restore.log.'
  except BaseException as exc:
   results['restoration']='error'
   results['restoration_error']=f'{type(exc).__name__}: {exc}'
   with (out/'restore.log').open('a') as log:log.write('\nRESTORATION ERROR: '+results['restoration_error']+'\n')
 save(out,results)
 print('DDR Hello restoration: '+results['restoration'],flush=True)
 if results['restoration']!='pass':
  print('STOP: restoration is not verified. Keep these logs; stop further examples until programmer state, matching image, fresh DDR markers and PC proof are checked. '+str(out/'restore.log'),file=sys.stderr,flush=True)

def main(preflight=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--only',default=DEFAULT_NAMES);p.add_argument('--port',default=PORT)
 p.add_argument('--list',action='store_true')
 p.add_argument('--full-recovery',action='store_true',help='Use the matching merged volatile SOF for the first bootstrap')
 a=p.parse_args()
 if a.list:print('\n'.join(TESTS));return 0
 names=a.only.split(',')
 for name in names:
  if name not in TESTS:p.error('Unknown test '+name+'; use --list')
 validate_uart(a.port)
 with HardwareLock() as lock:
  print('[preflight] Checking host/container mapping, tools and artifact hashes...',flush=True)
  verify_mount();verify_container_tools(['jtagconfig','quartus_pgm','openocd','aarch64-none-elf-readelf'])
  images=[ROOT/'bootstrap/ddr/ddr_probe.hps.rbf',ROOT/'bootstrap/ocram/agilex5.cfg']
  if a.full_recovery:images.append(ROOT/'bootstrap/ddr/ddr_recovery.sof')
  verify_mapped_files(images+[ROOT/'build'/(TESTS[name]['elf']+'.elf') for name in names])
  if preflight is not None:preflight()
  out=ROOT/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out.mkdir(parents=True)
  results={'requested_tests':names,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'initial_full_recovery':a.full_recovery,'tests':[],'restoration':'pending'}
  print('Evidence: '+str(out),flush=True);save(out,results)
  failed=None
  try:
   for index,name in enumerate(names):
    try:r=run_one(name,out,a.port,lock,a.full_recovery and index==0)
    except BaseException as exc:
     results['tests'].append({'name':name,'status':'error','error':f'{type(exc).__name__}: {exc}'});save(out,results);raise
    results['tests'].append(r);save(out,results)
  except BaseException as exc:
   failed=exc;results['error']=f'{type(exc).__name__}: {exc}';save(out,results)
  finally:
   restore_ddr(out,results,a.port,lock,skip=isinstance(failed,OwnedProcessError))
  if failed:
   print(f'ERROR: {type(failed).__name__}: {failed}. Evidence: {out}',file=sys.stderr)
   return 130 if isinstance(failed,KeyboardInterrupt) else 1
  return 1 if results['restoration']!='pass' or any(r['status']!='pass' for r in results['tests']) else 0

if __name__=='__main__':
 def interrupted(*_):raise KeyboardInterrupt
 for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
 try:raise SystemExit(main())
 except KeyboardInterrupt:
  print('Hardware command interrupted before a completed run; check the board state before retrying.',file=sys.stderr);raise SystemExit(130)
 except (BenchError,OSError,subprocess.TimeoutExpired) as exc:
  print(f'ERROR: {exc}\nHelp: {HELP}',file=sys.stderr);raise SystemExit(1)
