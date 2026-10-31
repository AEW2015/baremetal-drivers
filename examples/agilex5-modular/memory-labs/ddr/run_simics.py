#!/usr/bin/env python3
"""Exercise DDR-path code on the Agilex Simics model, never qualify physical timing."""
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
spec=importlib.util.spec_from_file_location('ddr_oracle',Path(__file__).with_name('run.py'))
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
CASES={'ddr-path':None,'ddr-copy-fault':'DDR_COPY_READBACK',
       'ddr-clock-fault':'DDR_DECLARED_TIMER_FREQUENCY_RANGE'}


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
    p.add_argument('--artifacts',type=Path,default=ROOT/'build/memory-ddr-agilex5')
    p.add_argument('--boot',type=Path,default=ROOT/'build/upstream26-ocram/baremetal.bin')
    p.add_argument('--timeout',type=int,default=180)
    p.add_argument('--only',default=','.join(CASES))
    p.add_argument('--output',type=Path)
    args=p.parse_args();names=args.only.split(',')
    if not 1<=args.timeout<=180:p.error('timeout must be 1..180 seconds per guest')
    if len(names)!=len(set(names)) or any(n not in CASES for n in names):p.error('Choose distinct names from '+','.join(CASES))
    metadata=json.loads((args.artifacts/'build.json').read_text())
    if metadata['target']!='agilex5':p.error('Simics requires the Agilex5-target build')
    out=args.output or Path(__file__).parent/'validation'/('simics-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(parents=True,exist_ok=True)
    record={'environment':'Agilex5 Simics model','scope':'Model functional execution only; counter-derived results do not qualify physical DDR/MPFE timing',
            'runner_sha256':digest(__file__),'oracle_sha256':digest(Path(__file__).with_name('run.py')),
            'bootstrap_sha256':digest(args.boot),'simics_launcher_sha256':digest(args.project/'simics'),
            'build':metadata,'tests':[]}
    for name in names:
        folder=out/name;folder.mkdir(exist_ok=True)
        image=args.artifacts/(name+'.bin');elf=args.artifacts/(name+'.elf')
        for path in (image,elf):
            if digest(path)!=metadata['artifacts'].get(path.name):raise RuntimeError('Artifact differs from build.json: '+str(path))
        path=folder/'test.simics';path.write_text(script(image.resolve(),args.boot.resolve()))
        code,seconds,body=execute(args.project,path,folder/'terminal.log',args.timeout)
        match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
        uart=match[1].replace('\r','') if match else ''
        begin=uart.find('LAB BEGIN ddr-path')
        if begin>=0:uart=uart[begin:]
        (folder/'uart.txt').write_text(uart)
        accepted,samples=oracle.assess(uart,code)
        marker=CASES[name]
        if marker is None:passed=accepted
        else:
            lines=uart.splitlines()
            passed=(code==0 and not accepted and 'LAB BEGIN ddr-path' in lines
                    and 'FAIL '+marker in lines and 'LAB FAILED' in lines
                    and 'LAB COMPLETE' not in lines)
        passed=(passed and 'SIMICS_DDR_BOOTSTRAP_COMPLETE' in body and 'DDR stage skipped' not in body)
        # Oracle's derived fields are named "emulated_*" and remain model-only.
        record['tests'].append({'name':name,'status':'pass' if passed else 'fail',
                                'negative_control':marker is not None,'expected_failure':marker,
                                'process_exit':code,'seconds':seconds,'elf_sha256':digest(elf),
                                'script_sha256':digest(path),'samples':samples})
        record['passed']=all(t['status']=='pass' for t in record['tests'])
        (out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
        print(name+': '+('pass' if passed else 'fail'),flush=True)
        if not passed:print(body[-2500:],flush=True)
    print(out)
    return int(not record['passed'])


if __name__=='__main__':raise SystemExit(main())
