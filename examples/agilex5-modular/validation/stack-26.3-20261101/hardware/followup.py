"""After the recorded campaign, repeat GPIO I2C then qualify real PR images."""
import contextlib,json,os,subprocess,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(ROOT))
from hardware_lock import HardwareLock
from bench import BenchError
record={'scope':'Current 26.3 stack follow-up; no simulated or old-image hardware passes','groups':[]}
def save():(OUT/'followup-groups.json').write_text(json.dumps(record,indent=2)+'\n')
print('WAITING_FOR_CAMPAIGN_USB_RESTORATION',flush=True)
while True:
 p=OUT/'groups.json';groups=json.loads(p.read_text())['groups'] if p.exists() else []
 if any(g['name']=='usb' for g in groups):
  latest={g['name']:g for g in groups}
  assert all(g['restorations'] and all(r=='pass' for r in g['restorations']) for g in latest.values()),'Campaign restoration failed; do not acquire hardware'
  break
 time.sleep(10)
def run(name,command,options=None):
 before=set((ROOT/'runs').glob('*'));start=time.monotonic();print('START',name,flush=True)
 with (OUT/(name+'.log')).open('w') as log:
  r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=700,**(options or {}))
 created=sorted(set((ROOT/'runs').glob('*'))-before)
 raw=[json.loads((d/'results.json').read_text()) for d in created if (d/'results.json').exists()]
 restorations=[d['restoration'] for d in raw if 'restoration' in d]
 g={'name':name,'command':command,'exit':r.returncode,'seconds':time.monotonic()-start,'runs':[str(d.relative_to(ROOT)) for d in created],'restorations':restorations}
 record['groups'].append(g);save();print('END',name,r.returncode,restorations,flush=True)
 assert restorations and all(v=='pass' for v in restorations),'STOP: restoration not established'
while True:
 try:
  lock=HardwareLock();lock.__enter__();break
 except BenchError as exc:
  if 'Hardware is busy' not in str(exc):raise
  time.sleep(10)
try:
 for attempt in [1,2]:run('som-i2c-retry-'+str(attempt),[sys.executable,'run_suite.py','--only','som-i2c'],lock.child_options())
finally:lock.close()
run('pr-hardware',[sys.executable,'fabric/pr/hardware/run.py','--manifest','/home/lada/quartus26-mcp-demos/agilex5-stack-20261101/hardware-manifest.json','--bench','/home/lada/altera-agilex/home/baremetal-guide-validation','--mcp-client','/home/lada/quartus26-mcp-demos/mcp_client.py','--run','--wait-for-hardware'])
print('FOLLOWUP_COMPLETE',flush=True)
