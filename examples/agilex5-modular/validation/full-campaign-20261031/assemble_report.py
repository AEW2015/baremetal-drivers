#!/usr/bin/env python3
"""Reconcile captured campaign outcomes into the registered example catalog."""
import collections,copy,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
REPO=ROOT.parents[1]
PREFIX='validation/full-campaign-20261031'
H=BASE/'hardware'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows={r['id']:r for r in read(ROOT/'catalog.json')['examples']}
record={'scope':'Fresh physical Modular ES runs. Named rows bundle related controls; partial is not a full upstream exercise pass. Original verdicts and all restoration logs retained.','tests':[]}
def add(ident,folder,names,status=None,scope=None,filename='results.json'):
 path=H/folder/filename;raw=read(path)
 assert raw['restoration']=='pass',(ident,raw.get('restoration'))
 assert names and len(names)==len(set(names)),ident
 index={t['name']:t for t in raw['tests']};cases=[index[n] for n in names]
 statuses=[t['status'] for t in cases]
 assert all(s in ('pass','partial','fail','blocked') for s in statuses),ident
 observed=next((s for s in ('fail','blocked','partial') if s in statuses),'pass')
 if status is None or observed in ('fail','blocked') or (observed=='partial' and status=='pass'):status=observed
 item={'name':ident,'status':status,'source_evidence':str(path.relative_to(ROOT)),'source_sha256':sha(path),'cases':copy.deepcopy(cases),'restoration':'pass','scope':scope or rows[ident]['scope']}
 record['tests'].append(item)
for name in ('core','dma','gic','interfaces','mailbox','mmu','multicore','som','som-i2c','som-i3c','vendor-ccu','vendor-clkmgr','vendor-ecc','vendor-smmu','vendor-uart'):
 add('board/'+name,'board-suite',[name])
add('board/vendor-timer','vendor-timer',['vendor-timer'],scope='Unchanged pinned25.1 timer body through the board adapter: count set, started, observed zero and returned success; no interrupt or calibrated period claim.')
practice={'startup':['startup','startup-no-bss','startup-no-data'],'corruption':['corruption','corruption-no-injection'],'exception':['exception','exception-wrong-brk'],'timer':['timer','timer-wrong-ppi'],'mmu':['mmu','mmu-writable-ro'],'uart':['uart'],'multicore':['multicore']}
for name,cases in practice.items():add('practice/'+name,'practice',cases)
for name in ('crc','perf','combophy','noc','reset'):
 add('upstream/'+('reset_mngr' if name=='reset' else name),'upstream',[name])
add('upstream/mailbox','upstream-runtime',['mailbox'])
add('custom/bridge-control','upstream-runtime',['bridge-control'])
add('config/sysmgr','config',['sysmgr','unstable'])
add('config/pinmux','config',['pinmux'])
for name in ('hello','ccu-readonly','clkmgr-readonly','dma','gic','mmu','smmu','spi','timer'):
 ident='upstream/'+{'ccu-readonly':'ccu','clkmgr-readonly':'clk_mngr'}.get(name,name)
 partial=name in ('ccu-readonly','clkmgr-readonly','spi')
 add(ident,'candidates',[name],status='partial' if partial else 'pass',filename='reviewed-results.json',scope=read(H/'candidates/reviewed-results.json')['tests'][['hello','ccu-readonly','clkmgr-readonly','dma','gic','mmu','smmu','spi','timer'].index(name)]['scope'])
add('reference/semihost','references',['semihost'])
add('custom/fault-probe','references',['fault-probe'])
add('custom/ocram-hello','ocram-uart',['ocram-uart'],scope='Fresh physical OCRAM UART output, full payload readback and PC in its image. Entered by JTAG after bootstrap; this run does not separately qualify cold boot with DDR absent. Replays matching handoff and fixed100MHz UART divisor54.')
add('reference/psci','psci',['psci'],scope='Exact CPU_ON helper under resident BL31/NS EL2: physical A55.1 context, identity, stack and CPU_OFF affinity verified; no forced takeover.')
add('memory/dsu','memory-dsu',['normal','corrupt','stalled','contention'])
add('memory/l3-partition','l3-partition',['partitioned'])
add('memory/ddr-sweep','memory-ddr',['ddr-calibrated','ddr-path','ddr-copy-fault','ddr-clock-fault'])
add('diagnostic/smc-guard','diagnostics',['smc-guard'])
add('diagnostic/perf-zero-clock','diagnostics',['perf-zero-clock'])
add('upstream/fcs','fcs-fixed',['fcs'],scope='Fixed HAL identity and36-byte read-only provision query complete; actual SDM0x85 denies session opening. Crypto session/RNG untested; no provisioning or key writes. Original stack-corruption failure preserved.')
add('upstream/ecc','ecc-readonly',['ecc-readonly'],scope='Current getter APIs match raw SERR0x00010000/DERR0 without initialization, clearing, injection or recovery. Nonzero status remains unchanged; this is not an ECC-health qualification.')
eth=read(H/'ethernet/results.json')
add('custom/ethernet','ethernet',[t['name'] for t in eth['tests']],scope='Physical HPS EMAC2 at1Gb/s: ARP/ping, counter check, five UDP echo sizes, sequence/corruption controls and TCP65536-byte receive/transmit. Smoke campaign, no new bandwidth/soak claim; not USB Ethernet.')
usb=read(H/'usb/results.json');assert usb['restoration']=='pass' and usb['uboot_prompt']
start=next(c for c in usb['commands'] if c['command']=='usb start')
record['tests'].append({'name':'custom/usb-host','status':'pass' if start['external_devices_observed'] else 'fail','source_evidence':PREFIX+'/hardware/usb/results.json','source_sha256':sha(H/'usb/results.json'),'cases':[start],'restoration':'pass','scope':'Physical guarded U-Boot boots; xHCI CNR timeout prevents enumeration. No hub/mouse/flash/USB-NIC class traffic qualified.'})
boot=H/'fcs-fixed/restore-bootstrap.log';text=boot.read_text();assert 'four 64 MiB patterns and payload readback passed' in text and 'CPU PC confirmed in DDR' in text
record['tests'].append({'name':'custom/ddr-hello','status':'pass','source_evidence':str(boot.relative_to(ROOT)),'source_sha256':sha(boot),'cases':[],'restoration':'pass','scope':'Fresh matching DDR bootstrap repeatedly validates four64MiB patterns, payload readback and executing PC in HPS bank3A; not full8GiB qualification.'})
assert len(record['tests'])==len({r['name'] for r in record['tests']})
record['counts']=dict(collections.Counter(t['status'] for t in record['tests']))
(H/'results.json').write_text(json.dumps(record,indent=2)+'\n')
catalog=read(ROOT/'catalog.json');sources={
 'qemu':BASE/'qemu/20261031T183144.039830Z/results.json',
 'simics':BASE/'simics/results.json',
 'hardware':H/'results.json'}
indices={p:{t['name']:t for t in read(path)['tests']} for p,path in sources.items()}
# The fixed model run supersedes the baseline FCS verdict's control-flow cause;
# it does not turn unavailable native SDM services into a feature PASS.
fixed_model=BASE/'simics/fcs-fixed-results.json'
for row in catalog['examples']:
 for platform,path in sources.items():
  item=indices[platform].get(row['id'])
  if item and item['status'] in ('pass','partial','fail','blocked'):
   row['platforms'][platform]={'status':item['status'],'evidence':str(path.relative_to(ROOT)),'case':row['id']}
 if row['id'] in indices['hardware']:row['scope']=indices['hardware'][row['id']]['scope']
 if row['id']=='upstream/fcs':row['platforms']['simics']={'status':'fail','evidence':str(fixed_model.relative_to(ROOT)),'case':'fcs-fixed'}
 if row['id']=='upstream/clk_mngr':row['scope']='Physical read-only current getters verified; full initialization/divisor writes excluded. Model also has two unsupported divisor getters; partial on both targets.'
(ROOT/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
ledger={'scope':'All94 registered rows accounted for; exercised includes failed/partial runtime attempts, not a claim of full capability. HostRTL evidence is separate from QEMU/Simics/hardware.','examples':[]}
reasons={
 'reference/pr':'Needs matching fitted PR static/persona images and recovery; no live PR design deployed.',
 'board/vendor-watchdog':'Original watchdog can progress into system reset; needs dedicated interrupt/reset recovery adaptation. Safe interrupt-first behavior is covered by board/som.',
 'board/vendor-spi':'Original pinned test can write external EEPROM; no disposable target authorized. Current internal-loopback path tested separately.',
 'board/vendor-hps_mailbox':'Original pinned mailbox offsets/queue assumptions not ported to this board; modern and board-specific mailbox paths tested separately.'}
for row in catalog['examples']:
 item={'id':row['id'],'scope':row['scope'],'platforms':{}}
 for p in ('qemu','simics','hardware'):
  result=copy.deepcopy(row['platforms'][p]);fresh=result.get('evidence','').startswith(PREFIX+'/')
  result['campaign_disposition']='exercised' if fresh and result['status'] in ('pass','partial','fail','blocked') else 'not-executed'
  if result['campaign_disposition']=='not-executed':
   if row['id'] in reasons:reason=reasons[row['id']]
   elif p=='qemu':reason='No matching QEMU virt platform/startup or peripheral model for this registered implementation; existing supported CPU exercises are separate rows.'
   elif p=='simics':reason='No matching distinct native model runner/profile for this registered implementation; physical adapters and model integrations are separate rows.'
   elif row['family']=='Legacy 25.1 Simics':reason='Native legacy ELF/startup assumes modeled targets/addresses. Reviewed board adapters execute separately; no direct unsafe legacy load.'
   else:reason='Needs a physical port, matched fabric image, specific peer, reset/recovery setup or reviewed non-destructive command; see hardware eligibility audit.'
   result['reason']=reason
  item['platforms'][p]=result
 if row['id'] in ('fabric/add','fabric/xor'):
  item['host_rtl']={'status':'pass','evidence':PREFIX+'/qemu/20261031T183144.039830Z/fabric-rtl.log','scope':'Native C driver against actual Verilator RTL; not a physical FPGA or a QEMU peripheral model.'}
 ledger['examples'].append(item)
ledger['counts']={p:dict(collections.Counter(e['platforms'][p]['status'] for e in ledger['examples'])) for p in ('qemu','simics','hardware')}
ledger['exercised']={p:sum(e['platforms'][p]['campaign_disposition']=='exercised' for e in ledger['examples']) for p in ('qemu','simics','hardware')}
ledger['distinct_runtime_rows']=sum(any(e['platforms'][p]['campaign_disposition']=='exercised' for p in ('qemu','simics','hardware')) for e in ledger['examples'])
ledger['host_rtl_only_rows']=sum('host_rtl' in e and not any(e['platforms'][p]['campaign_disposition']=='exercised' for p in ('qemu','simics','hardware')) for e in ledger['examples'])
(BASE/'coverage.json').write_text(json.dumps(ledger,indent=2)+'\n')
lines=['# Complete campaign disposition','',f"{ledger['distinct_runtime_rows']}/94 rows exercised on at least one runtime; {ledger['host_rtl_only_rows']} additional rows checked by host Verilator.",'','| Example | QEMU | Simics | Hardware | Scope / dependency |','|---|---|---|---|---|']
for e in ledger['examples']:
 labels=[]
 for p in ('qemu','simics','hardware'):
  r=e['platforms'][p];label=r['status'].upper()
  if r.get('evidence'):label=f"[{label}](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/{r['evidence']})"
  labels.append(label)
 reason=reasons.get(e['id'],e['scope'])
 if 'host_rtl' in e:reason+=' Host Verilator passed.'
 lines.append('| `'+e['id']+'` | '+' | '.join(labels)+' | '+reason.replace('|','/')+' |')
(BASE/'COVERAGE.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'fresh':ledger['exercised'],'distinct':ledger['distinct_runtime_rows'],'rtl_only':ledger['host_rtl_only_rows'],'counts':ledger['counts']},indent=2))
