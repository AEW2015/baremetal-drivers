from pathlib import Path
import subprocess,json,time,shutil,re
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
REMOTE='/workspace/baremetal-fixes-20261029/examples/agilex5-modular'
commands=[
 ('current-ddr','python3 validation/stack-26.3-20261101/simics/ddr_examples.py'),
 ('current-ddr-el2','python3 validation/stack-26.3-20261101/simics/ddr_examples.py --only fcs,seu --bl31 build/runtime-atf-26.3-ddr-console/agilex5/debug/bl31.bin'),
 ('psci','python3 validation/stack-26.3-20261101/simics/psci_model.py'),
 ('fcs-fixed','python3 validation/stack-26.3-20261101/simics/fcs_fixed.py'),
 ('reboot-bl31','python3 upstream-lab/run.py simics --only reboot --bl31 build/runtime-atf-26.3/agilex5/debug/bl31.bin --timeout 60'),
 ('qemu-semihost','python3 validation/stack-26.3-20261101/qemu/20261102T030401.999771Z/semihost_probe.py')]
results=[]
for name,command in commands:
 print('BEGIN',name,flush=True);start=time.monotonic()
 r=subprocess.run(['docker','exec','-u','dev','-w',REMOTE,'agilex26-mcp-demos','bash','-lc',command],capture_output=True,text=True,timeout=850)
 body=r.stdout+r.stderr;(OUT/(name+'-additional.log')).write_text(body)
 folders=[]
 for match in re.findall(r'Evidence:\s+(\S+)',body):
  p=Path(match.replace('/workspace/baremetal-fixes-20261029',str(ROOT.parents[1])))
  if p.is_dir():
   target=OUT/name
   if target.resolve()!=p.resolve():shutil.copytree(p,target,dirs_exist_ok=True)
   folders.append(str(target.relative_to(OUT)))
 results.append({'label':name,'command':command,'exit_code':r.returncode,'seconds':time.monotonic()-start,'evidence':folders})
 (OUT/'additional-campaign-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print('END',name,r.returncode,flush=True)
