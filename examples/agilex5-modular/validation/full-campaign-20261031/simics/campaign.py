#!/usr/bin/env python3
"""Host orchestration for existing Simics runners; no physical hardware calls."""
from pathlib import Path
import datetime,hashlib,json,re,shutil,subprocess,time
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
REMOTE='/workspace/baremetal-fixes-20261029/examples/agilex5-modular'
commands=[
 ('upstream-console','python3 simics/run.py --only hello,help,timer,gic,ddr'),
 ('legacy-all','python3 simics/legacy.py --all --timeout 40'),
 ('upstream-adapters','python3 upstream-lab/run.py simics --only crc,perf,combophy,noc,reset,reboot,smc-guard,perf-zero-clock --timeout 60'),
 ('upstream-services','python3 upstream-lab/run.py simics --only iossm,bridge,mailbox,bridge-control --bl31 build/runtime-atf/agilex5/debug/bl31.bin --timeout 60'),
 ('practice','python3 practice/run.py --negative --timeout 90'),
 ('config-audit','python3 config-audit/run.py'),
 ('model-audit','python3 model-audit/run.py'),
 ('rtl','python3 simics-rtl/run.py --timeout 90'),
 ('dsu','python3 memory-labs/dsu/run_simics.py --output '+REMOTE+'/validation/full-campaign-20261031/simics/dsu'),
 ('ddr','python3 memory-labs/ddr/run_simics.py --output '+REMOTE+'/validation/full-campaign-20261031/simics/ddr'),
 ('native-tbu','python3 memory-labs/smmu/native_run.py'),
 ('dmac-tbu','python3 memory-labs/smmu/dmac/run_simics.py --output '+REMOTE+'/validation/full-campaign-20261031/simics/dmac-tbu'),
]
for name,route in [('physical','physical'),('axi-error','physical'),('read-error','physical'),('timeout-drain','physical'),('f2h-valid','f2soc'),('f2h-fault','f2soc'),('f2sdram-valid','f2sdram'),('f2sdram-fault','f2sdram')]:
 commands.append(('fabric-'+name,f'python3 memory-labs/fabric-ddr/simics/run.py --case {name} --route {route} --output {REMOTE}/validation/full-campaign-20261031/simics/fabric-{name}'))
report={'scope':'Fresh Simics campaign using existing hash-validated artifacts; no hardware qualification','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':[]}
report['simics_version']=subprocess.check_output(['docker','exec','agilex26-mcp-demos','bash','-lc',f'cd {REMOTE} && build/simics26/simics --version'],text=True)
for label,command in commands:
 start=time.monotonic();print('BEGIN '+label,flush=True)
 cmd=['docker','exec','agilex26-mcp-demos','bash','-lc',f'cd {REMOTE} && {command}']
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=1000);code=r.returncode;body=r.stdout+r.stderr
 except subprocess.TimeoutExpired as exc:
  code=124;body=((exc.stdout or b'')+(exc.stderr or b'')).decode(errors='replace')
 (OUT/(label+'.log')).write_text(body)
 evidence=[]
 for match in re.findall(r'Evidence:\s+(\S+)',body):
  p=Path(match.replace('/workspace/baremetal-fixes-20261029','/home/lada/quartus26-mcp-demos/baremetal-fixes-20261029'))
  if p.is_dir():
   dest=OUT/label
   if dest.exists() and dest.resolve()!=p.resolve():shutil.rmtree(dest)
   if dest.resolve()!=p.resolve():shutil.copytree(p,dest)
   evidence.append(str(dest.relative_to(OUT)))
 direct=OUT/label
 if (direct/'results.json').is_file() and label not in evidence:evidence.append(label)
 item={'label':label,'command':command,'exit_code':code,'seconds':time.monotonic()-start,'evidence':evidence,'log_sha256':hashlib.sha256(body.encode()).hexdigest()}
 report['commands'].append(item)
 (OUT/'campaign-results.json').write_text(json.dumps(report,indent=2)+'\n')
 print('END '+label+' exit='+str(code)+' evidence='+str(evidence),flush=True)
report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(OUT/'campaign-results.json').write_text(json.dumps(report,indent=2)+'\n')
