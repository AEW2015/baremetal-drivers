#!/usr/bin/env python3
"""Write PR base/implementation revisions after reviewing the generated hierarchy."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--project',type=Path,required=True)
p.add_argument('--slot',required=True,help='Exact generated hierarchy, including component wrapper')
p.add_argument('--place-region',required=True,help='Reviewed candidate: Xn Yn Xn Yn; fitter must validate legality')
p.add_argument('--route-region',required=True)
a=p.parse_args();root=a.project.resolve()
for region in (a.place_region,a.route_region):
 if not re.fullmatch(r'X\d+ Y\d+ X\d+ Y\d+',region):p.error('Expected Xn Yn Xn Yn coordinates')
if not re.fullmatch(r'[A-Za-z0-9_|]+',a.slot):p.error('Invalid hierarchy')
base=root/'baseline_a55.qsf'
if not base.is_file() or not (root/'fabric_subsys/synth/fabric_subsys.v').is_file():p.error('Generate the staged platform first')
if (root/'pr-config.json').exists():p.error('PR configuration already exists; preserve that attempt')
s=base.read_text()
if 'A5ED065BB32AE6SR0' not in s:p.error('Wrong device')
common=f'''
set_instance_assignment -name PARTITION lab_pr_partition -to {a.slot}
set_instance_assignment -name PARTIAL_RECONFIGURATION_PARTITION ON -to {a.slot}
set_instance_assignment -name PLACE_REGION "{a.place_region}" -to {a.slot}
set_instance_assignment -name RESERVE_PLACE_REGION ON -to {a.slot}
set_instance_assignment -name CORE_ONLY_PLACE_REGION ON -to {a.slot}
set_instance_assignment -name ROUTE_REGION "{a.route_region}" -to {a.slot}
set_instance_assignment -name RESERVE_ROUTE_REGION OFF -to {a.slot}
'''
base.write_text(s+common+'''set_global_assignment -name REVISION_TYPE PR_BASE
set_instance_assignment -name EXPORT_PARTITION_SNAPSHOT_FINAL pr_static.qdb -to | -entity baseline_a55
''')
for name,entity in (('pr_add','pr_slot'),('pr_xor','pr_slot_xor')):
 (root/(name+'.qsf')).write_text(s+common+f'''set_global_assignment -name REVISION_TYPE PR_IMPL
set_instance_assignment -name QDB_FILE_PARTITION pr_static.qdb -to | -entity baseline_a55
set_instance_assignment -name ENTITY_REBINDING {entity} -to {a.slot}
''')
(root/'baseline_a55.qpf').write_text(''.join('PROJECT_REVISION = "'+n+'"\n' for n in ('baseline_a55','pr_add','pr_xor')))
(root/'pr-config.json').write_text(json.dumps({'status':'configured-not-compiled','slot':a.slot,'place_region':a.place_region,'route_region':a.route_region,'device':'A5ED065BB32AE6SR0','note':'Coordinates/hierarchy require compiler validation. No fitted image or physical PR result exists from this command.'},indent=2)+'\n')
print('PR revisions configured; NOT compiled or deployed')
