#!/usr/bin/env python3
"""Host hardware runner; fresh DDR boot per ELF, bounded capture, durable results."""
import argparse,datetime,fcntl,hashlib,json,os,pathlib,re,select,signal,subprocess,termios,time
from bench import container_command, container_path
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
# SPI's original test transmits to an EEPROM; mailbox test asserts Simics offsets.
# Their board-specific replacements are registered separately when built.
def container(args,timeout=45):
 return subprocess.run(container_command(args),capture_output=True,timeout=timeout)
def save(out,result):
 temp=out/'results.json.tmp';temp.write_text(json.dumps(result,indent=2)+'\n');temp.replace(out/'results.json')
def run_one(name,out,port):
 t=TESTS[name];elf=ROOT/'build'/(t['elf']+'.elf')
 result={'name':name,'elf':str(elf),'sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'status':'running'}
 start=time.monotonic()
 bootstrap=subprocess.run(['python3',str(ROOT/'bootstrap/ddr/run_ddr.py'),'--port',port],capture_output=True,timeout=230)
 (out/(name+'-bootstrap.log')).write_bytes(bootstrap.stdout+bootstrap.stderr)
 if bootstrap.returncode:raise RuntimeError('DDR bootstrap failed: '+str(out/(name+'-bootstrap.log')))
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
   proc=subprocess.Popen(container_command(['openocd','-f',cfg,'-c',cmd]),stdout=log,stderr=subprocess.STDOUT)
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
   if proc.poll() is None:
    proc.terminate();proc.wait(timeout=5)
  current=data[data.find(begin):] if begin in data else b''
  passed=proc.returncode==0 and bool(current) and all(x.encode() in current for x in t['markers']) and b'HPS_SUITE_FAIL' not in current and b'FAIL ' not in current
  if not passed:
   diagnostic=container(['openocd','-f',cfg,'-c','hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; echo [reg pc]; echo [reg cpsr]; echo [reg x0]; echo [reg x1]; shutdown'],timeout=45)
   (out/(name+'-halt.log')).write_bytes(diagnostic.stdout+diagnostic.stderr)
  result.update(status='pass' if passed else 'fail',entry=f'0x{entry:x}',elapsed_seconds=round(time.monotonic()-start,1),missing=[x for x in t['markers'] if x.encode() not in current],debug_returncode=proc.returncode,observed_pass_markers=re.findall(r'^PASS[^\r\n]*',current.decode(errors='replace'),re.M),failure_lines=re.findall(r'^(?:FAIL|HPS_SUITE_FAIL)[^\r\n]*',current.decode(errors='replace'),re.M))
  print(name+': '+result['status'],flush=True)
  print(current.decode(errors='replace')[-2200:],flush=True)
  return result
 finally:
  os.close(fd)
  if proc is not None and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--only',default=','.join(TESTS));p.add_argument('--port',default=PORT);p.add_argument('--list',action='store_true')
 a=p.parse_args()
 signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
 signal.signal(signal.SIGINT,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
 if a.list:
  print('\n'.join(TESTS));return
 if not a.port:p.error('Set AGILEX_UART or pass --port with the SOM J2 UART device')
 names=a.only.split(',')
 for n in names:
  if n not in TESTS:p.error('Unknown test '+n)
 # Reject configuration errors before touching hardware or attempting restoration.
 container_path(ROOT)
 if not pathlib.Path(a.port).exists():p.error('UART device does not exist: '+a.port)
 for n in names:
  if not (ROOT/'build'/(TESTS[n]['elf']+'.elf')).is_file():p.error('Missing ELF for '+n+'; run build_all.sh')
 if not (ROOT/'bootstrap/ddr/ddr_probe.hps.rbf').is_file():p.error('Missing DDR HPS RBF; run bootstrap/ddr/build_ddr.sh')
 lock=(ROOT/'hardware.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 out=ROOT/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');out.mkdir(parents=True)
 results={'requested_tests':names,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':[],'restoration':'pending'}
 print('Evidence: '+str(out),flush=True);save(out,results)
 try:
  for n in names:
   try:r=run_one(n,out,a.port)
   except BaseException as exc:
    results['tests'].append({'name':n,'status':'error','error':repr(exc)});save(out,results);raise
   results['tests'].append(r);save(out,results)
 finally:
  restore=subprocess.run(['python3',str(ROOT/'bootstrap/ddr/run_ddr.py'),'--port',a.port],capture_output=True,timeout=230)
  (out/'restore.log').write_bytes(restore.stdout+restore.stderr)
  results['restoration']='pass' if restore.returncode==0 else 'fail';save(out,results)
  print('DDR Hello restoration: '+results['restoration'],flush=True)
 if results['restoration']!='pass' or any(r['status']!='pass' for r in results['tests']):raise SystemExit(1)
if __name__=='__main__':main()
