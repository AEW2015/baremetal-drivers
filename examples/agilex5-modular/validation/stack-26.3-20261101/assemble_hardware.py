"""Map fresh physical cases to catalog rows; retain failed attempts and scope."""
import collections,copy,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];H=BASE/'hardware'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows={r['id']:r for r in read(ROOT/'catalog.json')['examples']}
record={'scope':'Physical Modular ES on the 26.3 HPS14.1/EMIF5.1 + ATF26.3 stack; original attempts retained. A partial result qualifies only its stated behavior.','tests':[]}
def add(ident,folder,names,status=None,scope=None,filename='results.json'):
 p=H/folder/filename;d=read(p);assert d['restoration']=='pass',(ident,d.get('restoration'))
 assert len(names)==len(set(names)),ident
 index={t['name']:t for t in d['tests']};cases=[index[n] for n in names]
 observed=next((v for v in ('fail','blocked','partial') if any(t['status']==v for t in cases)),'pass')
 if status is None or observed in ('fail','blocked') or (observed=='partial' and status=='pass'):status=observed
 record['tests'].append({'name':ident,'status':status,'source_evidence':str(p.relative_to(ROOT)),'source_sha256':sha(p),'cases':copy.deepcopy(cases),'restoration':'pass','scope':scope or rows[ident]['scope']})
for name in ['core','dma','gic','interfaces','mailbox','mmu','multicore','som','som-i3c','vendor-ccu','vendor-clkmgr','vendor-ecc','vendor-smmu','vendor-uart']:
 add('board/'+name,'board-suite',[name])
# Both repeated new-code runs must pass before superseding the original failure.
retry=[]
for attempt in [1,2]:
 p=H/('som-i2c-retry-'+str(attempt))/'results.json';d=read(p);assert d['restoration']=='pass'
 retry.append({'source_evidence':str(p.relative_to(ROOT)),'source_sha256':sha(p),'case':next(t for t in d['tests'] if t['name']=='som-i2c')})
record['tests'].append({'name':'board/som-i2c','status':'pass' if all(r['case']['status']=='pass' for r in retry) else 'fail','cases':retry,'restoration':'pass','initial_failure_evidence':str((H/'board-suite/results.json').relative_to(ROOT)),'scope':'GPIO open-drain TMP464 identity and 16-byte EEPROM read with bounded retries and separate NACK/line-timeout diagnostics. Requires two fresh successful runs; no EEPROM data writes or broad address scan.'})
add('board/vendor-timer','vendor-timer',['vendor-timer'],scope='Frozen25.1 timer body through physical adapter; set/start/read-zero completion, no interrupt or calibrated period claim.')
practice={'startup':['startup','startup-no-bss','startup-no-data'],'corruption':['corruption','corruption-no-injection'],'exception':['exception','exception-wrong-brk'],'timer':['timer','timer-wrong-ppi'],'mmu':['mmu','mmu-writable-ro'],'uart':['uart'],'multicore':['multicore']}
for name,cases in practice.items():add('practice/'+name,'practice',cases)
for name in ['crc','perf','combophy','noc','reset']:add('upstream/'+({'reset':'reset_mngr'}.get(name,name)),'upstream',[name])
add('upstream/mailbox','upstream-runtime',['mailbox']);add('custom/bridge-control','upstream-runtime',['bridge-control'])
add('config/sysmgr','config',['sysmgr','unstable']);add('config/pinmux','config',['pinmux'])
scopes={
 'hello':'Unchanged current hello CLI under board DDR startup.',
 'ccu-readonly':'Current CCU identity/error APIs only; full all-DMI cache flush excluded.',
 'clkmgr-readonly':'Current clock getter APIs only; no initialization/divisor writes or physical frequency measurement.',
 'dma':'Current sync256/async1024 demo and4096-byte API copy with full readback; polling fallback can invoke callback, no DMA IRQ qualification.',
 'gic':'Group0 SGI ISR demo with GIC-600 power preflight, Group1 interfaces disabled/read back and EL3 IRQ/FIQ vector shim.',
 'mmu':'Unchanged MMU EL3 status command; separate board/mmu exercises translation.',
 'smmu':'Unchanged SMMU enable-status command; no DMA translation qualification.',
 'spi':'32-byte and current API256-byte internal loopbacks; full command status remains partial when API auto-closes; no external SPI peer.',
 'timer':'Unchanged timer polling command, advancing samples and stopped state; no timing calibration.'}
for name in scopes:
 ident='upstream/'+{'ccu-readonly':'ccu','clkmgr-readonly':'clk_mngr'}.get(name,name)
 add(ident,'candidates',[name],status='partial' if name in ['ccu-readonly','clkmgr-readonly','spi'] else None,scope=scopes[name])
add('reference/semihost','references',['semihost']);add('custom/fault-probe','references',['fault-probe'])
add('custom/ocram-hello','ocram-uart',['ocram-uart'],scope='Physical OCRAM UART with full payload readback and PC in image, JTAG entry after DDR bootstrap. Not an independent cold boot with DDR absent.')
add('reference/psci','psci',['psci'])
add('memory/dsu','memory-dsu',['normal','corrupt','stalled','contention'])
add('memory/l3-partition','memory-dsu',['partitioned'])
add('memory/ddr-sweep','memory-ddr',['ddr-path','ddr-calibrated','ddr-copy-fault','ddr-clock-fault'])
for name in ['smc-guard','perf-zero-clock']:add('diagnostic/'+name,'diagnostics',[name])
add('upstream/fcs','fcs',['fcs'],scope='Read-only FCS identity/provision query with corrected response lifetime; inspect returned security/session denial separately from service completion. No provisioning or key writes.')
add('upstream/ecc','ecc-readonly',['ecc-readonly'],scope='Current ECC getters compared with raw registers; no clearing, injection or recovery. Nonzero status is retained, not an ECC-health qualification.')
eth=read(H/'ethernet/results.json');add('custom/ethernet','ethernet',[t['name'] for t in eth['tests']],scope='HPS EMAC2 physical ARP/ping, five UDP echo sizes and negative controls, TCP65536-byte receive/transmit; fresh smoke test, no new bandwidth/soak claim. Not USB Ethernet.')
usb=read(H/'usb/results.json');assert usb['restoration']=='pass' and usb['uboot_prompt'];start=next(c for c in usb['commands'] if c['command']=='usb start')
record['tests'].append({'name':'custom/usb-host','status':'partial' if start['xhci_started'] else 'fail','source_evidence':str((H/'usb/results.json').relative_to(ROOT)),'source_sha256':sha(H/'usb/results.json'),'cases':[start],'restoration':'pass','scope':'26.3 stack now initializes xHCI and enumerates its5Gb/s root hub, clearing the previous CNR stall. External hub, flash, mouse and USB Ethernet remain undetected/unqualified; raw runner exit1 is preserved. No media writes.'})
usb_case=record['tests'][-1]
usb_case['additional_evidence']=[]
for folder in ['usb-diagnostic','usb-rescan']:
 p=H/folder/'results.json';d=read(p);assert d['restoration']=='pass'
 usb_case['additional_evidence'].append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'commands':d['commands']})
usb_case['scope']='Current xHCI initialization,5Gb/s root hub and USB3320 identity0424:0007 passed. External hub/flash/mouse/USB Ethernet did not enumerate, including a bounded bus reset/rescan; raw exit1 retained. No media writes.'
add('reference/pr','pr-hardware',['pr-swap'],scope='One HPS guest, real JTAG ADD-XOR-ADD partial loads on26.3 HPS14.1/EMIF5.1 base; static scratch/heartbeat and256-word HPS DDR guard verified, full current DDR Hello restored.')
p=next(p for p in [H/'usb-rescan/restore-bootstrap.log',H/'usb-diagnostic/restore-bootstrap.log',H/'pr-hardware/restore.log'] if p.exists());body=p.read_text();assert 'four 64 MiB patterns and payload readback passed' in body and 'CPU PC confirmed in DDR' in body
record['tests'].append({'name':'custom/ddr-hello','status':'pass','source_evidence':str(p.relative_to(ROOT)),'source_sha256':sha(p),'cases':[],'restoration':'pass','scope':'New full FPGA-first image and ATF26.3 bootstrap: four64MiB patterns, payload/PC proof and FPGA user mode; not full8GiB qualification.'})
record['counts']=dict(collections.Counter(t['status'] for t in record['tests']));(H/'results.json').write_text(json.dumps(record,indent=2)+'\n');print(record['counts'])
