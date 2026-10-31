#!/usr/bin/env python3
"""Execute the DSU lab's portable cached-memory controls on native Agilex Simics.

Never execute the partitioned policy-register variant or qualify L3 timing.
"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,execute
spec=importlib.util.spec_from_file_location('dsu_oracle',Path(__file__).with_name('run.py'))
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
CASES=('normal','corrupt','stalled','contention')

def script(image,boot):
    q=json.dumps
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$done = (bp.console_string.break $con -regexp "LAB (COMPLETE|FAILED)")
$con.record-start
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "SIMICS_DDR_BOOTSTRAP_COMPLETE"
 hps.phys_mem.load-file {q(str(image))} 0x82400000
 pselect "system.board.fpga.soc_inst.hps_subsys.agilex_hps.core[0]"
 set-pc 0x82400000
 run
 bp.wait-for-breakpoint $done
 stop
 $transcript = ($con.record-stop)
 echo "UART_RECORD_BEGIN"
 echo $transcript
 echo "UART_RECORD_END"
 exit 0
}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=PROJECT)
    p.add_argument('--artifacts',type=Path,default=ROOT/'build/dsu-agilex5')
    p.add_argument('--boot',type=Path,default=ROOT/'build/upstream26-ocram/baremetal.bin')
    p.add_argument('--timeout',type=int,default=180)
    p.add_argument('--only',default=','.join(CASES))
    p.add_argument('--output',type=Path)
    a=p.parse_args();names=a.only.split(',')
    if not 1<=a.timeout<=180:p.error('timeout must be 1..180 seconds per guest')
    if len(names)!=len(set(names)) or any(n not in CASES for n in names):
        p.error('Choose distinct portable names from '+','.join(CASES)+'; partitioned is forbidden')
    metadata=json.loads((a.artifacts/'build.json').read_text())
    if metadata['target']!='agilex5':p.error('The native model requires the Agilex5-target build')
    out=a.output or Path(__file__).parent/'validation'/('simics-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(parents=True,exist_ok=False)
    result={'environment':'Native Agilex5 Simics model','scope':'Cached guest/control-flow execution only; no physical coherency, L3 partition, cache timing or bandwidth qualification',
            'runner_sha256':digest(__file__),'oracle_sha256':digest(Path(__file__).with_name('run.py')),
            'bootstrap_sha256':digest(a.boot),'simics_launcher_sha256':digest(a.project/'simics'),
            'build':metadata,'tests':[]}
    for name in names:
        folder=out/name;folder.mkdir()
        binary=a.artifacts/(name+'.bin');elf=a.artifacts/(name+'.elf')
        for path in (binary,elf):
            if digest(path)!=metadata['artifacts'].get(path.name):raise RuntimeError('Artifact differs from build.json: '+str(path))
        cfg=folder/'test.simics';cfg.write_text(script(binary.resolve(),a.boot.resolve()))
        code,seconds,body=execute(a.project,cfg,folder/'terminal.log',a.timeout)
        match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
        uart=match[1].replace('\r','') if match else ''
        begin=uart.find('LAB BEGIN dsu')
        if begin>=0:uart=uart[begin:]
        (folder/'uart.txt').write_text(uart)
        passed=(oracle.assess_target(name,uart,code)=='pass' and
                'SIMICS_DDR_BOOTSTRAP_COMPLETE' in body and 'DDR stage skipped' not in body)
        result['tests'].append({'name':name,'status':'pass' if passed else 'fail',
                               'negative_control':name in ('corrupt','stalled'),
                               'process_exit':code,'seconds':seconds,'elf_sha256':digest(elf),'script_sha256':digest(cfg)})
        result['passed']=all(t['status']=='pass' for t in result['tests'])
        (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(name+': '+('pass' if passed else 'fail'),flush=True)
        if not passed:print(body[-2500:],flush=True)
    print(out)
    return int(not result['passed'])

if __name__=='__main__':raise SystemExit(main())
