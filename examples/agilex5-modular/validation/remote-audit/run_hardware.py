from pathlib import Path
import contextlib,json,os,subprocess,sys,time
root=Path('/home/lada/altera-agilex/home/baremetal-remote-audit-0daff10/examples/agilex5-modular')
out=Path(__file__).parent
sys.path.insert(0,str(root))
from hardware_lock import HardwareLock
env=dict(os.environ,AGILEX_CONTAINER='agilex-xrdp',AGILEX_CONTAINER_USER='dev',AGILEX_CONTAINER_ROOT='/home/dev/baremetal-remote-audit-0daff10/examples/agilex5-modular',AGILEX_UART='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
env.pop('AGILEX_LOCK_FD',None)
result={'source_commit':'0daff10b3ea2d1075fa75c8f5c16526ed99b2e98','uart':env['AGILEX_UART'],'stages':[]}
with contextlib.ExitStack() as stack:
 for lockpath in ['/home/lada/altera-agilex/home/baremetal-guide-validation/examples/hardware.lock','/home/lada/altera-agilex/home/baremetal-drivers-aew2015/examples/agilex5-modular/hardware.lock']:
  stack.enter_context(HardwareLock(lockpath))
 commands=[('hardware-doctor',[sys.executable,'doctor.py','--target','hardware','--sof','/home/lada/altera-agilex/home/agilex5-litedram-phylite/build/dual_ddr1600_hps_lw_r3/memory_test.sof','--handoff','/home/lada/altera-agilex/home/agilex5-litedram-phylite/build/dual_ddr1600_hps_lw_r3/hps_bootloader_handoff.bin']),('hardware-suite',[sys.executable,'run_suite.py'])]
 for name,cmd in commands:
  print(f'START {name}',flush=True);start=time.monotonic()
  with (out/(name+'.log')).open('w') as log:
   rc=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
  result['stages'].append({'name':name,'command':cmd,'exit':rc,'seconds':round(time.monotonic()-start,2)})
  (out/'hardware-results.json').write_text(json.dumps(result,indent=2)+'\n')
  print(f'{"PASS" if rc==0 else "FAIL"} {name} exit={rc}',flush=True)
  if rc:raise SystemExit(rc)
