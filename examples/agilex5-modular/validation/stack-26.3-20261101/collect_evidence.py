#!/usr/bin/env python3
"""Copy completed physical runs without mixing concurrent simulator outputs."""
import hashlib,json,shutil,re
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
H=BASE/'hardware'
manifest=[]
groups=json.loads((H/'groups.json').read_text())['groups']
if (H/'followup-groups.json').exists():groups+=json.loads((H/'followup-groups.json').read_text())['groups']
for group in groups:
 for name in group['runs']:
  source=ROOT/name
  p=source/'results.json'
  if not p.is_file():continue
  result=json.loads(p.read_text())
  if 'restoration' not in result:continue
  dest=H/group['name']
  dest.mkdir(exist_ok=True)
  for f in source.rglob('*'):
   if not f.is_file():continue
   rel=f.relative_to(source)
   if f.suffix in ('.json','.log','.txt','.gdb','.tcl'):
    target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
    if b'\0' in target.read_bytes():target.write_text(target.read_bytes().decode(errors='replace').replace('\x00',r'\x00'))
   elif 'uart' in f.name and f.suffix=='.bin':
    target=(dest/rel).with_suffix('.txt');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(f.read_bytes().decode(errors='replace').replace('\r','').replace('\x00',r'\x00'))
   else:continue
   manifest.append({'source':str(f.relative_to(ROOT)),'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'saved_as':str(target.relative_to(BASE)),'saved_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
# Include each DDR runner's fresh chain, programmer, FPGA state and PC proof.
stamps=set()
for p in H.glob('**/*bootstrap.log'):
 stamps.update(re.findall(r'program-(\d{8}-\d{6}-\d{6})\.log',p.read_text(errors='replace')))
for p in H.glob('**/restore.log'):
 stamps.update(re.findall(r'program-(\d{8}-\d{6}-\d{6})\.log',p.read_text(errors='replace')))
for stamp in sorted(stamps):
 for prefix,suffix in [('mcp-chain','.json'),('program','.log'),('pc','.log'),('config','.log'),('uart','.bin')]:
  f=ROOT/'bootstrap/ddr'/(prefix+'-'+stamp+suffix)
  if not f.is_file():continue
  target=H/'bootstrap'/stamp/(prefix+('.txt' if suffix=='.bin' else suffix));target.parent.mkdir(parents=True,exist_ok=True)
  if suffix=='.bin':target.write_text(f.read_bytes().decode(errors='replace').replace('\r','').replace('\x00',r'\x00'))
  else:shutil.copy2(f,target)
  manifest.append({'source':str(f.relative_to(ROOT)),'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'saved_as':str(target.relative_to(BASE)),'saved_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(BASE/'copied-evidence.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Collected',len(manifest),'text evidence files')
