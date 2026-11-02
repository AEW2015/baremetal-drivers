#!/usr/bin/env python3
"""Recorded bench campaign; run from the active example-pack directory on host."""
import fcntl,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'validation/stack-26.3-20261101/hardware'
BENCH=Path('/home/lada/altera-agilex/home/baremetal-guide-validation')
MCP=Path('/home/lada/quartus26-mcp-demos/mcp_client.py')
env=dict(os.environ)
assert env.get('AGILEX_FORCE_FULL_BOOT')=='1', 'Source current-stack-env.sh first'
assert env.get('AGILEX_CONTAINER')=='agilex26-mcp-demos'
env.pop('AGILEX_LOCK_FD',None)
base=[sys.executable,'upstream-lab/hardware.py','--bench',str(BENCH),'--mcp-client',str(MCP)]
commands=[
 ('references',[sys.executable,'reference/run_hardware.py','--bench',str(BENCH),'--mcp-client',str(MCP)],False),
 ('board-suite',[sys.executable,'run_suite.py'],False),
 ('practice',base+['--artifacts','build/practice-agilex5','--suite','practice','--only','startup,corruption,exception,timer,mmu,uart,multicore,startup-no-bss,startup-no-data,corruption-no-injection,exception-wrong-brk,mmu-writable-ro,timer-wrong-ppi'],False),
 ('upstream',base+['--artifacts','build/upstream-lab-agilex5','--only','crc,perf,combophy,noc,reset'],False),
 ('upstream-runtime',base+['--artifacts','build/upstream-lab-agilex5','--bl31','build/runtime-atf-26.3/agilex5/debug/bl31.bin','--only','mailbox,bridge-control'],False),
 ('config',base+['--artifacts','build/config-audit','--suite','config'],False),
 ('candidates',base+['--artifacts','build/hardware-candidates','--suite','candidates'],False),
 ('ocram-uart',[sys.executable,'reference/run_hardware.py','--bench',str(BENCH),'--mcp-client',str(MCP),'--ocram-uart'],False),
 ('psci',base+['--artifacts','build/reference-psci','--suite','psci','--bl31','build/runtime-atf-26.3/agilex5/debug/bl31.bin'],False),
 ('vendor-timer',[sys.executable,'run_suite.py','--only','vendor-timer'],False),
 ('diagnostics',base+['--artifacts','build/upstream-lab-agilex5','--only','smc-guard,perf-zero-clock'],False),
 ('fcs',base+['--artifacts','build/service-candidates','--suite','services','--only','fcs','--bl31','build/runtime-atf-26.3/agilex5/debug/bl31.bin'],False),
 ('ecc-readonly',base+['--artifacts','build/service-candidates','--suite','services','--only','ecc-readonly'],False),
 ('memory-ddr',base+['--artifacts','build/memory-ddr-agilex5','--suite','memory-ddr','--only','ddr-path,ddr-calibrated,ddr-copy-fault,ddr-clock-fault'],False),
 ('memory-dsu',base+['--artifacts','build/dsu-agilex5','--suite','memory-dsu','--only','normal,corrupt,stalled,contention,partitioned'],False),
 ('ethernet',[sys.executable,'ethernet/run.py','--interface','enp111s0','--smoke','--coordination-lock',str(BENCH/'examples/hardware.lock')],False),
 ('usb',[sys.executable,'usb-bringup/run.py','--bench',str(BENCH),'--mcp-client',str(MCP),'--uboot','build/usb-uboot-26.3/u-boot-usb-standalone.bin','--command','usb start','--command','usb tree','--command','usb storage'],False),
]
record=json.loads((OUT/'groups.json').read_text()) if (OUT/'groups.json').is_file() else {'scope':'Physical runs; unsupported/destructive/fixture-dependent references excluded after source audit','groups':[]}
completed={g['name'] for g in record['groups'] if g.get('restorations') and all(s=='pass' for s in g['restorations'])}
for name,cmd,external_lock in commands:
 if name in completed:continue
 before=set((ROOT/'runs').glob('*'));start=time.monotonic();lock=None
 print('START '+name,flush=True)
 try:
  if external_lock:
   lock=(BENCH/'examples/hardware.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  attempt=sum(g['name']==name for g in record['groups'])+1
  log_name=name+('' if attempt==1 else '-retry'+str(attempt))+'.log'
  with (OUT/log_name).open('w') as log:
   result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=2400)
 finally:
  if lock is not None:lock.close()
 created=sorted(set((ROOT/'runs').glob('*'))-before)
 item={'name':name,'log':log_name,'command':cmd,'exit':result.returncode,'seconds':round(time.monotonic()-start,2),'runs':[str(p.relative_to(ROOT)) for p in created]}
 records=[]
 for folder in created:
  evidence=folder/'results.json'
  if evidence.is_file():
   value=json.loads(evidence.read_text())
   if 'restoration' in value:records.append(value)
 item['restorations']=[r.get('restoration') for r in records]
 record['groups'].append(item);(OUT/'groups.json').write_text(json.dumps(record,indent=2)+'\n')
 print(('PASS ' if result.returncode==0 else 'FAIL ')+name+' restorations='+str(item['restorations']),flush=True)
 if not records or any(r.get('restoration')!='pass' for r in records):
  raise SystemExit('STOP: no confirmed restoration; no more board operations')
