from pathlib import Path
import hashlib,json,re,shutil
repo=Path('/home/lada/altera-agilex/home/baremetal-drivers-aew2015')
source=Path('/home/lada/altera-agilex/home/baremetal-remote-audit-0daff10/examples/agilex5-modular')
audit=Path(__file__).parent
dest=repo/'examples/agilex5-modular/validation/remote-audit';dest.mkdir(exist_ok=True)
for p in audit.iterdir():
 if p.is_file() and p.suffix in ('.log','.json','.py'):shutil.copy2(p,dest/p.name)
for name in ['qemu-labs-gnu-before','qemu-labs-gnu-after','qemu-labs-arm-after']:
 shutil.copytree(audit/name,dest/name,dirs_exist_ok=True)
shutil.copytree(source/'runs/qemu-labs-20261024T022358.213610Z',dest/'qemu-labs-baseline',dirs_exist_ok=True)

def hardware(run_name,name):
 run=source/'runs'/run_name;target=dest/name;target.mkdir(exist_ok=True)
 results=json.loads((run/'results.json').read_text())
 assert results['restoration']=='pass',results['restoration']
 assert all(t['status']=='pass' for t in results['tests'])
 shutil.copytree(run,target,dirs_exist_ok=True)
 for p in target.glob('*-uart.bin'):p.rename(p.with_suffix('.txt'))
 raw=target/'bootstrap';raw.mkdir(exist_ok=True)
 for log in list(run.glob('*-bootstrap.log'))+[run/'restore.log']:
  body=log.read_text()
  for value in re.findall(r'(?:Programmer log|UART capture): (\S+)',body):
   p=Path(value);shutil.copy2(p,raw/(p.stem+'.txt' if p.suffix=='.bin' else p.name))
   if p.name.startswith('uart-'):
    proof=p.with_name(p.name.replace('uart-','pc-')).with_suffix('.log')
    shutil.copy2(proof,raw/proof.name)
 print(name,len(results['tests']),'passed; restore',results['restoration'])
hardware('20261024T022502.660358Z','hardware-baseline')
if (audit/'hardware-after-results.json').exists():
 after=json.loads((audit/'hardware-after-results.json').read_text())
 if any(x['name']=='hardware-suite-after' and x['exit']==0 for x in after['stages']):
  text=(audit/'hardware-suite-after.log').read_text();name=re.search(r'Evidence: (\S+)',text)[1].split('/')[-1]
  hardware(name,'hardware-fixed')
  for p in (source/'bootstrap/ocram/build').glob('program-uart-*.log'):shutil.copy2(p,dest/p.name)
  for p in (source/'bootstrap/ocram/build').glob('uart-pass-*.bin'):shutil.copy2(p,dest/(p.stem+'.txt'))
# Preserve raw bytes; .txt extensions keep serial evidence visible in GitHub.
index={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='sha256.json'}
(dest/'sha256.json').write_text(json.dumps(index,indent=2)+'\n')
print('Collected files:',len(index))
