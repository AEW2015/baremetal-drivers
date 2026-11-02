#!/usr/bin/env python3
"""Upgrade a staged Modular ES Platform Designer platform before generation."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from release_pins import PINS
EXPECTED=[('agilex_hps',PINS['quartus']['hps_ip']),('emif_io96b_hps',PINS['quartus']['hps_emif_ip'])]

def versions(root):
 result={}
 for p in sorted((root/'ip').glob('*/*.ip')):
  vals=re.findall(r'<(?:ipxact:)?version>([^<]+)',p.read_text())
  result[str(p.relative_to(root))]={'version':vals[0] if vals else None,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',required=True,type=Path);parser.add_argument('--verify-only',action='store_true')
 a=parser.parse_args();root=a.project.resolve();qsf=root/'baseline_a55.qsf'
 if not qsf.is_file() or 'A5ED065BB32AE6SR0' not in qsf.read_text():parser.error('Expected the matching Modular ES source project')
 if a.verify_only:
  after=versions(root)
  for name,wanted in EXPECTED:
   if after['ip/hps_subsys/'+name+'.ip']['version']!=wanted:raise RuntimeError('A generated parent restored stale IP: '+name)
  print('PASS GENERATED_IP_VERSIONS: HPS14.1.0, EMIF5.1.0');return
 before=versions(root)
 systems=[root/(name+'.qsys') for name in ('baseline_top','shell_subsys','fabric_subsys','hps_subsys','niosv_subsys')]
 files=systems+sorted((root/'ip').glob('*/*.ip'))
 if any(not p.is_file() for p in files):parser.error('Missing source system')
 search=str(root/'custom_ip')+','+str(root/'custom_ip/baremetal/fabric/pr')+',$'
 cmd=['qsys-generate','--upgrade-ip-cores','--part=A5ED065BB32AE6SR0','--search-path='+search,*['--batch='+str(p) for p in files[1:]],str(files[0])]
 with (root/'upgrade-ip.log').open('w') as log:r=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 body=(root/'upgrade-ip.log').read_text(errors='replace')
 if r.returncode or re.search(r'^.*(?:Error:|Error \()',body,re.M):raise RuntimeError('IP upgrade failed; inspect '+str(root/'upgrade-ip.log'))
 after=versions(root)
 for name,wanted in EXPECTED:
  actual=after['ip/hps_subsys/'+name+'.ip']['version']
  if actual!=wanted:raise RuntimeError(f'{name}: expected qualified26.3 catalog {wanted}, got {actual}')
 version=subprocess.check_output(['quartus_sh','--version'],text=True).strip()
 (root/'ip-upgrade-manifest.json').write_text(json.dumps({'tool':version,'target':'A5ED065BB32AE6SR0','before':before,'after':after,'command':cmd,'status':'upgraded-not-generated-or-hardware-tested'},indent=2)+'\n')
 print('PASS IP_UPGRADE: HPS14.1.0, HPS EMIF5.1.0; hardware not tested')
if __name__=='__main__':main()
