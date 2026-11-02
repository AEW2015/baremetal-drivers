#!/usr/bin/env python3
"""Reconcile fresh model evidence to all distinct catalog rows."""
from pathlib import Path
import collections,datetime,hashlib,json
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
rows=json.loads((ROOT/'catalog.json').read_text())['examples']
observed={}
def load(label):return json.loads((OUT/label/'results.json').read_text())
def add(id,label,name=None,scope=None):
 data=load(label)
 case=data if name is None else next(t for t in data['tests'] if t['name']==name)
 status=case.get('status')
 if status is None:status='pass' if case.get('passed') else 'fail'
 if status=='timeout':status='fail'
 observed[id]={'name':id,'status':status,'evidence':str((OUT/label/'results.json').relative_to(ROOT)),'source_case':name,'scope':scope or data.get('scope'),'limitation':case.get('limitation')}
for name in ['hello','timer','gic','ddr']:add('upstream/'+name,'upstream-console',name)
for name in ['crc','perf','combophy','noc','reset']:
 add('upstream/'+({'reset':'reset_mngr'}.get(name,name)),'upstream-adapters',name)
add('upstream/reboot_mngr','reboot-bl31','reboot')
for name in ['iossm','bridge','mailbox']:add('upstream/'+name,'upstream-services',name)
for name in ['smc-guard','perf-zero-clock']:add('diagnostic/'+name,'upstream-adapters',name)
add('custom/bridge-control','upstream-services','bridge-control')
# Clock getters with error (-EINVAL) do not establish the entire example.
p=OUT/'current-ddr/results.json';d=json.loads(p.read_text())
for t in d['tests']:
 if t['name'] in ('clk_mngr','spi'):
  t.setdefault('initial_status',t['status'])
  if t['status']=='pass':t.update(status='partial',limitation=('Clock init/getters worked; SOFT_PHY and CS_CLK divisor getters return -EINVAL, no physical frequency claim.' if t['name']=='clk_mngr' else 'Internal SPI loopback passed; full command status queries fail after the API auto-closes.'))
p.write_text(json.dumps(d,indent=2)+'\n')
for t in d['tests']:
 label='current-ddr-el2' if t['name'] in ['fcs','seu'] else 'current-ddr'
 add('upstream/'+t['name'],label,t['name'])
for t in load('legacy-all')['tests']:add('legacy/'+t['name'],'legacy-all',t['name'])
for name in ['startup','corruption','exception','timer','mmu','uart','multicore']:add('practice/'+name,'practice',name)
for name in ['sysmgr','pinmux']:add('config/'+name,'config-audit',name)
add('model/pio','model-audit','pio')
for name in ['add','xor']:add('integration/simics-rtl-'+name,'rtl',name)
for id,label in [('memory/dsu','dsu'),('memory/ddr-sweep','ddr'),('memory/native-tbu','native-tbu'),('memory/dma-tbu','dmac-tbu')]:
 data=load(label);tests=data['tests']
 status='pass' if all(t.get('status','pass' if t.get('passed') else 'fail')=='pass' for t in tests) else 'fail'
 observed[id]={'name':id,'status':status,'evidence':str((OUT/label/'results.json').relative_to(ROOT)),'source_cases':[t['name'] for t in tests],'scope':data.get('scope'),'limitation':None}
fabric=[]
for name in ['physical','axi-error','read-error','timeout-drain','f2h-valid','f2h-fault','f2sdram-valid','f2sdram-fault']:
 d=load('fabric-'+name);fabric.append({'name':name,'status':d['status'],'evidence':str((OUT/('fabric-'+name)/'results.json').relative_to(ROOT)),'scope':d['scope']})
(OUT/'fabric-results.json').write_text(json.dumps({'scope':'Eight actual Arm C driver/RTL/native memory profiles; transaction-stepped co-simulation, no physical bridge/timing qualification','tests':fabric},indent=2)+'\n')
observed['memory/fabric-ddr']={'name':'memory/fabric-ddr','status':'pass' if all(t['status']=='pass' for t in fabric) else 'fail','evidence':str((OUT/'fabric-results.json').relative_to(ROOT)),'source_cases':[t['name'] for t in fabric],'scope':'Actual C driver -> Verilator RTL -> native physical DDR/F2H/F2SDRAM TBU; includes native fault and explicit-injection controls; model only','limitation':None}
limits={'upstream/ecc':'OCRAM ECC initialization timed out before error injection.',
'upstream/i3c':'Native model critical access to held-reset I3C0; enum names incorrectly tested with #ifdef in API reset selection.',
'upstream/sdmmc':'SDMMC command/transfer timeout during initialization; no successful media transfer.',
'upstream/i2c':'Seven of nine phases passed; explicit target write/readback and P3T sensor phases skipped (no matching target supplied/found).'}
for id,limit in limits.items():observed[id]['limitation']=limit
add('reference/psci','psci','reference/psci')
observed['reference/pr']={'name':'reference/pr','status':'partial','evidence':str((OUT/'pr/assessment.json').relative_to(ROOT)),'source_case':'pr-transition','scope':'Real Arm C guest and Verilator persona-transition controls; simulated loader has no RBF/SDM implementation.'}
results=[]
for row in rows:
 if row['id'] in observed:r=observed[row['id']]
 else:
  old=row['platforms']['simics']['status']
  status=old if old in ['reference','not-supported'] else 'not-run'
  reason='No matching model runner for this distinct implementation; a passed sibling implementation does not qualify it.'
  if row['id']=='memory/l3-partition':reason='Native model does not implement the target hardware partition policy; build-only hardware variant.'
  if row['id']=='memory/smmu-qemu':reason='QEMU PCI EDU device/topology does not exist on the Agilex Simics target.'
  if row['id']=='reference/pr':reason='Requires matching static/PR bitstreams and physical PR deployment; Simics does not run fabric RTL through reconfiguration.'
  r={'name':row['id'],'status':status,'limitation':reason}
 results.append(r)
counts=collections.Counter(r['status'] for r in results)
record={'scope':'Fresh native Simics and Simics/Verilator campaign; per-row distinctions retained; no physical hardware claims','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'simics_version':json.loads((OUT/'campaign-results.json').read_text())['simics_version'],'inventory_rows':len(rows),'rows_executed':len(observed),'counts':dict(counts),'tests':results,'notes':['All evidence is from the 26.3 campaign; legacy API fixtures retain their intentional 25.1 pin.','The initial descriptive native-fabric case labels were rejected before execution; corrected native-valid/native-fault cases all passed.','EL3 reboot is rejected; the matched resident BL31/EL2 retry passed.','The DDR console BL31 is separately built for BL33 entry0x80200000; standalone adapters use0x82400000.','FCS service completion and control flow are preserved, but native SDM denies identity/session operations; capability remains failed.','Partial clock/SPI/GPIO/I2C results are not promoted from CLI DONE lines.']}
(OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n')
text=['# Fresh Simics campaign','',f"**{len(observed)} of {len(rows)} distinct catalog rows exercised:** "+', '.join(f'{counts[k]} {k}' for k in ['pass','partial','fail'])+'. Remaining: '+', '.join(f'{counts[k]} {k}' for k in ['not-run','reference','not-supported','blocked'])+'.','', 'The remaining rows have no matching distinct model runner, require unavailable model features, or are references. No historical pass was silently reused as a fresh execution. Build manifests and per-case artifact hashes accompany the raw terminal captures.','', '## Current upstream DDR console','', '| Example | Result | Limit |','|---|---|---|']
for r in results:
 if r['name'].startswith('upstream/'):
  text.append('| '+r['name']+' | '+r['status']+' | '+str(r.get('limitation') or r.get('scope') or '').replace('|','/')+' |')
text+=['','Native PSCI and all eight fabric routes have fresh execution evidence. See results.json and the command ledgers for partial capabilities and model limitations.']
(OUT/'SUMMARY.md').write_text('\n'.join(text)+'\n')
print(dict(counts))
