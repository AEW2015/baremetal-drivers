#!/usr/bin/env python3
"""Run native Agilex SMMU/TBU transaction probes in an isolated Simics process."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
PACK=ROOT.parents[1]
sys.path.insert(0,str(PACK/'simics'))
from support import execute

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def script(project,boot,output):
    q=json.dumps
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "NATIVE_TBU_DDR_BOOTSTRAP_COMPLETE"
 @import sys
 @sys.path.insert(0,{q(str(ROOT))})
 @import native_cases
 @native_cases.run_cases({q(str(output))})
}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=PACK/'build/simics26')
    p.add_argument('--boot',type=Path,default=PACK/'build/upstream26-ocram/baremetal.bin')
    p.add_argument('--timeout',type=int,default=90)
    a=p.parse_args()
    project=a.project.resolve();boot=a.boot.resolve()
    if not (project/'simics').is_file() or not boot.is_file():p.error('Deploy Simics and build the OCRAM bootstrap first')
    out=ROOT/'validation'/('simics-native-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    out.mkdir(parents=True)
    target=out/'test.simics';target.write_text(script(project,boot,out/'native-results.json'))
    version=subprocess.check_output([str(project/'simics'),'--version'],text=True,timeout=15)
    code,seconds,body=execute(project,target,out/'terminal.log',a.timeout)
    result={'scope':'Host-issued transactions through native Agilex SMMU/TBU models; not physical DMA/fabric qualification; fresh walks with model TLB cache disabled; no command-queue invalidation claim',
            'simics_version':version,'returncode':code,'seconds':seconds,'boot_sha256':sha(boot),
            'source_sha256':{f.name:sha(f) for f in [ROOT/'native_fixture.py',ROOT/'native_cases.py',Path(__file__)]},
            'script_sha256':sha(target),'tests':[]}
    native_path=out/'native-results.json'
    if native_path.is_file():
        native=json.loads(native_path.read_text());result['tests']=native['tests']
        if native.get('error'):result['error']=native['error']
    passed=(code==0 and len(result['tests'])==3 and 'NATIVE_TBU_DDR_BOOTSTRAP_COMPLETE' in body
            and 'PASS NATIVE_TBU_CASES count=3' in body and 'FAIL NATIVE_TBU_CASES' not in body)
    for row in result['tests']:
        cfg=row['configuration'];ev=row['fault'];sid=8 if row['name']=='dma0' else 0
        passed=passed and row['status']=='pass' and cfg['sid']==sid and cfg['tlb_cache_enable'] is False
        passed=passed and ev['producer']==1 and ev['global_error']==0
        passed=passed and ev['words'][0]&255==0x10 and ev['words'][0]>>32==sid and ev['words'][2]==0x85000000
    result['passed']=bool(passed)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(('PASS' if passed else 'FAIL')+' NATIVE_TBU_CASES')
    print('Evidence:',out)
    return int(not passed)
if __name__=='__main__': raise SystemExit(main())
