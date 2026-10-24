from pathlib import Path
import contextlib,json,os,re,subprocess,sys,time
root=Path('/home/lada/altera-agilex/home/baremetal-remote-audit-0daff10/examples/agilex5-modular');out=Path(__file__).parent
sys.path.insert(0,str(root))
from hardware_lock import HardwareLock
from owned_process import run_owned
from unittest import mock
env=dict(AGILEX_CONTAINER='agilex-xrdp',AGILEX_CONTAINER_USER='dev',AGILEX_CONTAINER_ROOT='/home/dev/baremetal-remote-audit-0daff10/examples/agilex5-modular',AGILEX_UART='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
results={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'stages':[]}
def run(name,args,lock):
 print('START '+name,flush=True);start=time.monotonic()
 with (out/(name+'.log')).open('w') as log:rc=subprocess.run(args,cwd=root,stdout=log,stderr=subprocess.STDOUT,**lock.child_options()).returncode
 results['stages'].append({'name':name,'exit':rc,'seconds':round(time.monotonic()-start,2),'command':args});save();print(('PASS ' if rc==0 else 'FAIL ')+name,flush=True);return rc
def save():(out/'hardware-after-results.json').write_text(json.dumps(results,indent=2)+'\n')
with mock.patch.dict(os.environ,env),contextlib.ExitStack() as stack:
 for path in ['/home/lada/altera-agilex/home/baremetal-guide-validation/examples/hardware.lock','/home/lada/altera-agilex/home/baremetal-drivers-aew2015/examples/agilex5-modular/hardware.lock']:
  stack.enter_context(HardwareLock(path))
 lock=stack.enter_context(HardwareLock())
 ocram_rc=run('ocram-hardware',[sys.executable,str(out/'run_ocram_from_bench.py'),'--port',env['AGILEX_UART']],lock)
 if ocram_rc==0:
  cfg=env['AGILEX_CONTAINER_ROOT']+'/bootstrap/ocram/agilex5.cfg'
  try:
   proof=run_owned(['openocd','-f',cfg,'-c','hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; echo [get_reg {pc}]; resume; shutdown'],timeout=30)
   (out/'ocram-pc.log').write_text(proof)
   pcs=[int(x,16) for x in re.findall(r'^pc (0x[0-9a-fA-F]+)',proof,re.M)]
   results['ocram_pc']=hex(pcs[-1]) if pcs else None
   if not pcs or not 0<=pcs[-1]<0x60000:ocram_rc=1
  except Exception as exc:results['ocram_pc_error']=str(exc);ocram_rc=1
  save()
 if list(root.glob('.agilex-process-*')):
  results['restoration']='not attempted: unresolved ownership record';save();raise SystemExit(1)
 restore_rc=run('ocram-ddr-restore',[sys.executable,str(root/'bootstrap/ddr/run_ddr.py')],lock)
 if ocram_rc or restore_rc:raise SystemExit(1)
 rc=run('hardware-suite-after',[sys.executable,str(root/'run_suite.py'),'--only','core,dma'],lock)
 raise SystemExit(rc)
