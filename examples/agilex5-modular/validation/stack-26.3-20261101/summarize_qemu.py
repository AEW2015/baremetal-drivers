import json,hashlib,collections
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
OUT=next((BASE/'qemu').glob('20*'))
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=read(OUT/'results.json');assert all(s['status']=='pass' for s in record['steps'])
tests=[]
def add(ident,path,cases):
 data=read(path);index={t['name']:t for t in data['tests']};selected=[index[n] for n in cases]
 assert all(t.get('passed',t.get('status')=='pass') for t in selected),(ident,selected)
 tests.append({'name':ident,'status':'pass','source_evidence':str(path.relative_to(ROOT)),'source_sha256':sha(path),'cases':cases})
tests.append({'name':'custom/qemu-hello','status':'pass','source_evidence':str((OUT/'hello-run.log').relative_to(ROOT)),'source_sha256':sha(OUT/'hello-run.log'),'scope':'Real QEMU hello plus isolated corruption/recovery experiment; GDB practice separately recorded'})
practice=read(OUT/'practice/results.json')
for name in ['startup','corruption','exception','timer','mmu','uart','multicore']:
 cases=[t['name'] for t in practice['tests'] if t['name']==name or t['name'].startswith(name+'-')]
 add('practice/'+name,OUT/'practice/results.json',cases)
for ident,name in [('upstream/crc','crc'),('upstream/perf','perf'),('diagnostic/smc-guard','smc-guard'),('diagnostic/perf-zero-clock','perf-zero-clock')]:add(ident,OUT/'upstream/results.json',[name])
for ident,folder in [('memory/dsu','dsu'),('memory/ddr-sweep','ddr'),('memory/smmu-qemu','smmu')]:
 path=OUT/folder/'results.json';add(ident,path,[t['name'] for t in read(path)['tests']])
add('reference/semihost',OUT/'semihost/results.json',['semihost'])
assert len(tests)==16
record['tests']=tests;record['counts']=dict(collections.Counter(t['status'] for t in tests))
(OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print(record['counts'])
