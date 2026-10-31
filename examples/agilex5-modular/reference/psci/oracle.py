"""Host-only PSCI evidence oracle; completion alone never qualifies CPU_ON/OFF."""
import re
NAMES=['psci']
CONTEXT=0x5053434943545854
TARGET=0x100
BLOCKED_REASONS={'resident_BL31_NS_EL2_required','invalid_counter_frequency','counter_not_advancing','version_unavailable','required_feature_unavailable','target_already_on','target_not_off','CPU_ON_ALREADY_ON'}
def assess(name,body,code):
 if name!='psci' or code!=0:return 'fail'
 text=body.replace('\r','');lines=text.splitlines()
 if lines.count('PSCI_BEGIN target_mpidr=0x100 context=0x5053434943545854')!=1:return 'fail'
 if any(line.startswith('FAIL ') for line in lines):return 'fail'
 blocked=re.findall(r'^BLOCKED PSCI reason=(\w+) code=(-?\d+)$',text,re.M)
 if blocked:
  if len(blocked)==1 and blocked[0][0] in BLOCKED_REASONS and lines.count('PSCI_COMPLETE status=2')==1 and 'PSCI_COMPLETE status=0' not in lines:return 'blocked'
  return 'fail'
 if lines.count('PSCI_COMPLETE status=0')!=1 or 'PSCI_COMPLETE status=1' in lines or 'PSCI_COMPLETE status=2' in lines:return 'fail'
 required=['PSCI_PRIMARY_EL=2','PASS PSCI_PRIMARY_EL2_CACHE_OFF_CORE0','PSCI_INITIAL_AFFINITY=1','PSCI_CPU_ON_RESULT=0',
  'PASS PSCI_CPU_ON_SUCCESS','PASS PSCI_SECONDARY_RECORD_PUBLISHED','PASS PSCI_SECONDARY_IDENTITY_CONTEXT_AND_STACK','PASS PSCI_CPU_OFF_AFFINITY_CONFIRMED']
 if not all(lines.count(line)==1 for line in required):return 'fail'
 version=re.findall(r'^PSCI_VERSION=0x([0-9a-fA-F]+)$',text,re.M)
 features=re.findall(r'^PSCI_FEATURE id=0x([0-9a-fA-F]+) result=(-?\d+)$',text,re.M)
 if len(version)!=1 or not 2<=int(version[0],16)<0x80000000:return 'fail'
 if len(features)!=3 or {int(fid,16) for fid,_ in features}!={0xc4000003,0x84000002,0xc4000004} or any(int(rc)<0 for _,rc in features):return 'fail'
 secondary=re.findall(r'^PSCI_SECONDARY context=0x([0-9a-fA-F]+) MIDR=0x([0-9a-fA-F]+) MPIDR=0x([0-9a-fA-F]+) EL=(\d+) SCTLR=0x([0-9a-fA-F]+) ENTRY=0x([0-9a-fA-F]+) STACK=0x([0-9a-fA-F]+) FAULT=(\d+)$',text,re.M)
 if len(secondary)!=1:return 'fail'
 ctx,midr,mpidr,el,sctlr,entry,stack,fault=secondary[0]
 ctx,midr,mpidr,sctlr,entry,stack=map(lambda value:int(value,16),(ctx,midr,mpidr,sctlr,entry,stack))
 if not(ctx==CONTEXT and mpidr&0xff00ffffff==TARGET and (midr>>4)&0xfff==0xd05 and (midr>>24)&255==0x41 and int(el)==2 and not sctlr&5 and 0x82400000<=entry<0x82700000 and entry%64==0 and 0x83ff9000<stack<=0x83ffb000 and int(fault)==0):return 'fail'
 final=re.findall(r'^PSCI_FINAL_AFFINITY=(-?\d+) OFF_ATTEMPT=(\d+) OFF_RETURNED=(\d+) OFF_RESULT=(-?\d+)$',text,re.M)
 if final!=[('1','1','0','0')]:return 'fail'
 return 'pass'
