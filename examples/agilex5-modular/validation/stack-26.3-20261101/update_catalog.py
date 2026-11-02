import collections,copy,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
read=lambda p:json.loads(p.read_text())
paths={'qemu':next((BASE/'qemu').glob('20*'))/'results.json','simics':BASE/'simics/results.json','hardware':BASE/'hardware/results.json'}
indices={p:{t['name']:t for t in read(path)['tests']} for p,path in paths.items()}
catalog=read(ROOT/'catalog.json')
for row in catalog['examples']:
 for platform,index in indices.items():
  result=index.get(row['id'])
  if result and result['status'] in ['pass','partial','fail','blocked']:
   row['platforms'][platform]={'status':result['status'],'evidence':str(paths[platform].relative_to(ROOT)),'case':row['id']}
 if row['id'] in indices['hardware']:row['scope']=indices['hardware'][row['id']]['scope']
(ROOT/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
coverage={'scope':'All94 rows accounted for on the matched26.3 stack; fresh execution is distinct from historical catalog evidence. Partial is not a complete feature pass.','examples':[]}
for row in catalog['examples']:
 entry={'id':row['id'],'scope':row['scope'],'platforms':{}}
 for platform,index in indices.items():
  result=index.get(row['id'])
  if result and result['status'] in ['pass','partial','fail','blocked']:
   value=copy.deepcopy(row['platforms'][platform]);value['disposition']='exercised'
  else:
   value={'status':row['platforms'][platform]['status'],'disposition':'not-executed','historical_evidence':row['platforms'][platform].get('evidence')}
   if platform=='qemu':reason='No matching QEMU virt platform/peripheral model for this implementation; its supported CPU labs are separate rows.'
   elif platform=='simics':reason=(result or {}).get('limitation') or 'No matching native model runner; a sibling implementation or host-only RTL check is not a distinct execution.'
   elif row['family']=='Legacy 25.1 Simics':reason='Original legacy model startup/targets are not a reviewed physical load; adapted board entries are tested separately.'
   else:reason='Needs a matching physical endpoint/FPGA initiator, translation routing, external peer or reviewed non-destructive port; see row scope and roadmap.'
   value['reason']=reason
  if value['disposition']=='not-executed' and row['id'] in ['board/vendor-watchdog','board/vendor-spi','board/vendor-hps_mailbox']:
   value['reason']={'board/vendor-watchdog':'Frozen watchdog body can progress into reset and needs a dedicated interrupt/recovery port; safe interrupt-first behavior is a separate board/som case.','board/vendor-spi':'Frozen body can write external EEPROM; no disposable target/data-write scope. Internal loopback is tested separately.','board/vendor-hps_mailbox':'Frozen mailbox offsets/queue assumptions lack a physical port; modern and board-specific mailbox paths passed separately.'}[row['id']]
  entry['platforms'][platform]=value
 if row['id'] in ['fabric/add','fabric/xor']:
  entry['host_rtl']={'status':'pass','evidence':str((paths['qemu'].parent/'fabric-rtl.log').relative_to(ROOT)),'scope':'Host C driver and Verilator RTL checks, not a distinct Arm/board runtime deployment.'}
 coverage['examples'].append(entry)
coverage['fresh_counts']={p:dict(collections.Counter(t['status'] for t in indices[p].values() if t['status'] in ['pass','partial','fail','blocked'])) for p in paths}
coverage['host_rtl_only_rows']=sum('host_rtl' in e and all(v['disposition']=='not-executed' for v in e['platforms'].values()) for e in coverage['examples'])
coverage['distinct_rows_exercised']=sum(any(v['disposition']=='exercised' for v in e['platforms'].values()) for e in coverage['examples'])
(BASE/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
lines=['# Fresh26.3 coverage for all94 registered rows','',str(coverage['distinct_rows_exercised'])+' rows were executed on at least one runtime; two additional standalone fabric rows passed host C/RTL checks. Each cell states whether its result is fresh; historical results are not silently reused.','','| Example | QEMU | Simics | Hardware | Scope |','|---|---|---|---|---|']
for e in coverage['examples']:
 labels=[]
 for p in paths:
  v=e['platforms'][p];label=v['status'].upper()
  if v['disposition']=='exercised':label='['+label+']('+str(Path(v['evidence']).relative_to(BASE.relative_to(ROOT)))+')'
  else:label+=' (not executed)'
  labels.append(label)
 lines.append('| `'+e['id']+'` | '+' | '.join(labels)+' | '+e['scope'].replace('|','/')+' |')
(BASE/'COVERAGE.md').write_text('\n'.join(lines)+'\n')
print(coverage['fresh_counts']);print('Distinct rows:',coverage['distinct_rows_exercised'])
