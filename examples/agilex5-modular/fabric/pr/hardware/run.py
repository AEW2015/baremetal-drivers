#!/usr/bin/env python3
"""Qualified-bench coordinator: one HPS invocation, two real JTAG PR loads."""
import argparse,datetime,fcntl,hashlib,json,os,re,select,subprocess,sys,termios,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_manifest(path):
 d=json.loads(path.read_text())
 if d.get('device_id')!='0364F0DD':raise ValueError('Wrong physical device profile')
 for key in ('full_sof','guest_bin','guest_elf','add','xor'):
  obj=d[key];p=Path(obj['path'])
  if not p.is_file() or sha(p)!=obj['sha256']:raise ValueError('Missing/changed artifact: '+key)
 for key in ('add','xor'):
  proof=d[key]['compatibility']
  if proof.get('status')!='pass' or proof['parent_sha256']!=d['full_sof']['sha256'] or proof['child_sha256']!=d[key]['sha256']:raise ValueError('No matching PR compatibility evidence: '+key)
  if sha(proof['path'])!=proof['sha256']:raise ValueError('Changed compatibility evidence')
 return d

def require_fabric_user_mode(config_text):
 # STATE=IDLE is the configuration engine state even after entry to user mode.
 # Qualify the decoded device state together with the actual completion bits.
 if ('Device has entered user mode' not in config_text or
     not re.search(r'CONF_DONE\s*=\s*1',config_text) or
     not re.search(r'INIT_DONE\s*=\s*1',config_text)):
  raise RuntimeError('Fabric has not entered user mode; no MMIO access permitted')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--manifest',required=True,type=Path);p.add_argument('--bench',required=True,type=Path)
 p.add_argument('--mcp-client',required=True,type=Path);p.add_argument('--port',default='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
 p.add_argument('--run',action='store_true');p.add_argument('--wait-for-hardware',action='store_true')
 a=p.parse_args();manifest=validate_manifest(a.manifest)
 workspace=a.mcp_client.resolve().parent
 def remote(path):return '/workspace/'+str(Path(path).resolve().relative_to(workspace))
 for key in ('full_sof','add','xor'):remote(manifest[key]['path'])
 if not a.run:print('PASS PR_ARTIFACT_PREFLIGHT; no hardware access');return 0
 sys.path.insert(0,str(workspace));from mcp_client import MCP
 out=ROOT/'runs'/('pr-hardware-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));out.mkdir(parents=True)
 record={'scope':'Physical Modular ES, one HPS guest with JTAG ADD-XOR-ADD PR; no flash/media/fuse writes','manifest':manifest,'runner_sha256':sha(Path(__file__)),'tests':[],'restoration':'pending'}
 def save():(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
 print('Evidence:',out,flush=True);save()
 lock=(a.bench/'examples/hardware.lock').open('a')
 while True:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
  except BlockingIOError:
   if not a.wait_for_hardware:raise RuntimeError('Shared hardware mutex busy')
   if (out/'CANCEL').exists():return 2
   print('WAITING_FOR_HARDWARE_MUTEX',flush=True);time.sleep(5)
 m=MCP('programmer');fd=None;uncertain=False;hardware_touched=False
 def chain(label):
  d=m.call('read_jtag_config',{});(out/(label+'-chain.json')).write_text(json.dumps(d,indent=2)+'\n')
  body=d.get('text','');blocks=re.split(r'(?m)^  (?=\d+:)',body)
  blocks=[b for b in blocks if re.match(r'\d+: Agilex_5E MDK Carrier',b)]
  if len(blocks)!=1:raise RuntimeError('Cannot uniquely identify Modular carrier: '+body)
  block=blocks[0];idx,cable=block.splitlines()[0].split(': ',1)
  pos=[int(n) for n,v in re.findall(r'Device (\d+): JTAG ID 0x([0-9a-fA-F]+)',block) if int(v,16)==0x0364f0dd]
  if len(pos)!=1:raise RuntimeError('Modular ES FPGA ID missing')
  subprocess.run(['docker','exec','agilex26-mcp-demos','jtagconfig','--setparam',idx,'JtagClock','6M'],check=True,capture_output=True)
  return idx,cable,pos[0]
 def drain(wait=.1):
  data=b''
  if select.select([fd],[],[],wait)[0]:
   try:data=os.read(fd,65536)
   except BlockingIOError:pass
   if not data:raise RuntimeError('SOM UART disconnected')
  return data
 def program(key,label,collector):
  nonlocal uncertain,hardware_touched
  if sha(manifest[key]['path'])!=manifest[key]['sha256']:raise RuntimeError('Artifact changed before programming: '+key)
  _,cable,index=chain(label);uncertain=True;hardware_touched=True
  job=m.call('program_sram_device',{'file_path':remote(manifest[key]['path']),'cable':cable,'device_index':index})
  (out/(label+'-kickoff.json')).write_text(json.dumps(job,indent=2)+'\n')
  if 'jobId' not in job:raise RuntimeError('Programming did not return a tracked job')
  deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   state=m.call('get_job_status',{'jobId':job['jobId'],'projectDir':job['projectDir']})
   (out/(label+'-program.json')).write_text(json.dumps(state,indent=2)+'\n')
   collector.extend(drain(0));(out/(label+'-uart.txt')).write_bytes(collector)
   if state.get('status') in ('completed','failed','cancelled'):
    uncertain=False
    if state['status']!='completed' or state.get('success') is False or state.get('exitCode',0):raise RuntimeError('Programming failed: '+label)
    config=m.call('read_config_status',{'cable':cable,'device_index':index})
    (out/(label+'-config-status.json')).write_text(json.dumps(config,indent=2)+'\n')
    config_text=config.get('text','')
    require_fabric_user_mode(config_text)
    return
   time.sleep(1)
  raise RuntimeError('Programming completion uncertain; automatic recovery disabled')
 def boot(key,label):
  termios.tcflush(fd,termios.TCIFLUSH);body=bytearray();program(key,label,body);deadline=time.monotonic()+180
  hello=b'Hello, World! executing from HPS DDR bank 3A @ 0x82000000'
  while time.monotonic()<deadline:
   body+=drain();(out/(label+'-uart.txt')).write_bytes(body)
   if b'###DDR:init success###' in body and all(('pattern %d PASS'%i).encode() in body for i in range(4)) and b'payload readback PASS' in body and body.split(b'payload readback PASS')[-1].count(hello)>=3:
    if b'LOCAL FABRIC: LWH2F enabled' not in body:raise RuntimeError('Bridge enable was not observed')
    return
   if b'ERROR:' in body or b'FAIL' in body:raise RuntimeError('DDR bootstrap failed')
  raise RuntimeError('DDR bootstrap timeout')
 def command(argv,label,timeout=50):
  nonlocal uncertain
  uncertain=True
  r=subprocess.run(argv,capture_output=True,timeout=timeout)
  uncertain=False;body=(r.stdout+r.stderr).decode(errors='replace');(out/(label+'.log')).write_text(body)
  if r.returncode or re.search(r'(?m)^Error(?: \(|:)',body):raise RuntimeError('Command failed: '+label+'\n'+body[-2000:])
  return body
 def control(stage,expected,label):
  _,cable,index=chain(label+'-control')
  script=out/(label+'.tcl');script.write_text(f'set pr_stage {stage}\nset pr_expected {expected:#x}\nset pr_sof {{{remote(manifest["full_sof"]["path"])}}}\nset pr_cable {{{cable}}}\nset pr_index {index}\n'+Path(__file__).with_name('host_control.tcl').read_text())
  body=command(['docker','exec','agilex26-mcp-demos','timeout','--kill-after=5s','35s','system-console','--script='+remote(script)],label)
  marker='PR_HOST_STAGE_RESULT stage='+stage+' PASS'
  if len(re.findall('^'+re.escape(marker)+'$',body,re.M))!=1 or 'PR_HOST_STAGE_ERROR' in body:raise RuntimeError('No trustworthy System Console completion: '+label)
 try:
  fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
  v=termios.tcgetattr(fd);v[0]=v[1]=v[3]=0;v[2]=termios.CS8|termios.CREAD|termios.CLOCAL;v[4]=v[5]=termios.B115200;v[6][termios.VMIN]=v[6][termios.VTIME]=0;termios.tcsetattr(fd,termios.TCSANOW,v)
  boot('full_sof','base')
  chain('guest-load');termios.tcflush(fd,termios.TCIFLUSH)
  image=Path(manifest['guest_bin']['path']);copy=a.bench/'examples/build'/(out.name+'-guest.bin');copy.write_bytes(image.read_bytes());readback=Path(str(copy)+'.readback');readback.unlink(missing_ok=True)
  rp='/home/dev/baremetal-guide-validation/examples/build/'+copy.name
  script=a.bench/'examples/build'/(out.name+'-guest.tcl')
  script.write_text(f'''hps.a55.0 configure -event halted {{}}
hps.a55.0 configure -event resumed {{}}
gdb port disabled
tcl port disabled
telnet port disabled
init
halt
hps.dap apsel 0x4000
targets hps.sys_bus
load_image {rp} 0x82100000 bin
dump_image {rp}.readback 0x82100000 {image.stat().st_size}
puts "PR_GUEST_LOAD_COMPLETE"
shutdown
''')
  (out/'guest-load.tcl').write_text(script.read_text())
  body=command(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f','/home/dev/baremetal-guide-validation/ocram/agilex5.cfg','-f','/home/dev/baremetal-guide-validation/examples/build/'+script.name],'guest-load',45)
  if 'PR_GUEST_LOAD_COMPLETE' not in body or not readback.is_file() or readback.read_bytes()!=image.read_bytes():raise RuntimeError('Guest readback mismatch; CPU remains halted')
  (out/'guest-readback.json').write_text(json.dumps({'status':'pass','sha256':sha(readback),'bytes':readback.stat().st_size},indent=2)+'\n')
  script.write_text('hps.a55.0 configure -event halted {}\nhps.a55.0 configure -event resumed {}\ngdb port disabled\ntcl port disabled\ntelnet port disabled\ninit\nhalt\nresume 0x82100000\nshutdown\n')
  (out/'guest-start.tcl').write_text(script.read_text())
  command(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f','/home/dev/baremetal-guide-validation/ocram/agilex5.cfg','-f','/home/dev/baremetal-guide-validation/examples/build/'+script.name],'guest-start',45)
  uart=b'';loads=[];deadline=time.monotonic()+300
  while time.monotonic()<deadline:
   uart+=drain();(out/'guest-uart.txt').write_bytes(uart)
   requests=re.findall(rb'PR_HOST_LOAD_REQUEST=0x([0-9a-fA-F]+)',uart)
   if len(requests)>len(loads):
    if len(loads)>=2:raise RuntimeError('Unexpected third load request')
    expected=(0x584f5231,0x41444431)[len(loads)]
    if int(requests[len(loads)],16)!=expected:raise RuntimeError('Wrong load sequence')
    key=('xor','add')[len(loads)]
    if sha(manifest[key]['path'])!=manifest[key]['sha256']:raise RuntimeError('Persona changed before programming')
    control('begin',expected,key+'-begin');_,cable,index=chain(key+'-pr')
    body=command(['docker','exec','agilex26-mcp-demos','timeout','--kill-after=5s','120s','quartus_pgm','-c',cable,'-m','jtag','--pr',remote(manifest[key]['path'])+'@'+str(index)],key+'-pr',135)
    if 'Successfully performed operation' not in body:raise RuntimeError('No positive PR programmer completion')
    control('done',expected,key+'-done');loads.append(key);record['completed_loads']=loads;save()
   if b'PR_LAB_COMPLETE' in uart:break
  text=uart.decode(errors='replace').replace('\r','')
  required=('INITIAL_ADD_ID','INITIAL_ADD_VECTORS','XOR_VECTORS','RETURN_ADD_VECTORS','TWO_RUNTIME_SWAPS')
  ok=loads==['xor','add'] and text.count('PR_LAB_BEGIN jtag_loader=1')==1 and text.count('PR_LAB_COMPLETE status=0')==1 and 'FAIL ' not in text and all(text.count('PASS '+s)==1 for s in required) and all(text.count('PASS '+s)==2 for s in ('SWAP_RESET_AND_ID','STATIC_SCRATCH_CONTINUITY','STATIC_HEARTBEAT_PROGRESS','DDR_GUARD_256_WORDS','ISOLATED_READ_RESPONSE'))
  record['tests'].append({'name':'pr-swap','status':'pass' if ok else 'fail','loads':loads,'uart_sha256':sha(out/'guest-uart.txt')});save()
  if not ok:raise RuntimeError('Physical PR guest evidence incomplete')
 except BaseException as exc:record['error']=repr(exc);save();raise
 finally:
  if fd is not None:os.close(fd);fd=None
  try:
   if hardware_touched and not uncertain:
    idx,_,_=chain('restore')
    if idx!='1':raise RuntimeError('Bench recovery requires verified carrier as cable 1')
    # Stop the previous boot's UART before the legacy recovery capture starts.
    # Otherwise a boot still printing its DDR patterns can satisfy that runner
    # before the replacement boot has reached DDR (observed PC 0x2760).
    halt='hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; shutdown'
    command(['docker','exec','agilex-xrdp','timeout','--kill-after=5s','30s','openocd','-f','/home/dev/baremetal-guide-validation/ocram/agilex5.cfg','-c',halt],'restore-prehalt',45)
    r=subprocess.run([sys.executable,str(a.bench/'ddr-bringup/run_ddr.py'),'--port',a.port,'--full-recovery'],capture_output=True,timeout=240)
    (out/'restore.log').write_bytes(r.stdout+r.stderr);record['restoration']='pass' if r.returncode==0 else 'fail'
   else:record['restoration']='not attempted: uncertain owned process' if uncertain else 'not needed'
  except BaseException as exc:record['restoration']='fail';record['restore_error']=repr(exc)
  save();m.close();lock.close();print('Restoration:',record['restoration'],flush=True)
 return int(record['restoration']!='pass' or any(t['status']!='pass' for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
