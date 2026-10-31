#!/usr/bin/env python3
"""Run a guest-controlled real native DMAC0/SMMU transfer and unmapped fault."""
import argparse
import datetime
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,execute

def script(image,boot,native_result):
    q=json.dumps
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$phase1 = (bp.console_string.break $con -regexp "(DMAC_SMMU_PHASE1_COMPLETE|LAB FAILED)")
$done = (bp.console_string.break $con -regexp "LAB (COMPLETE|FAILED)")
$con.record-start
@import sys; sys.path.insert(0,{q(str(HERE))}); sys.path.insert(0,{q(str(HERE.parent))}); import native_dmac
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "SIMICS_DDR_BOOTSTRAP_COMPLETE"
 @native_dmac.safe(native_dmac.configure,{q(str(native_result))})
 hps.phys_mem.load-file {q(str(image))} 0x82400000
 pselect "system.board.fpga.soc_inst.hps_subsys.agilex_hps.core[0]"
 set-pc 0x82400000
 run
 bp.wait-for-breakpoint $phase1
 stop
 @native_dmac.safe(native_dmac.after_phase1)
 run
 bp.wait-for-breakpoint $done
 stop
 @native_dmac.safe(native_dmac.finish)
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
    p.add_argument('--artifacts',type=Path,default=ROOT/'build/memory-smmu-dmac')
    p.add_argument('--boot',type=Path,default=ROOT/'build/upstream26-ocram/baremetal.bin')
    p.add_argument('--timeout',type=int,default=180)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not 1<=a.timeout<=180:p.error('timeout must be 1..180 seconds')
    metadata=json.loads((a.artifacts/'build.json').read_text())
    if metadata['target']!='agilex5-simics-native-dmac':p.error('Build the native-DMAC guest first')
    out=a.output or HERE/'validation'/('simics-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    out.mkdir(parents=True,exist_ok=False)
    binary=a.artifacts/'dmac-smmu.bin';elf=a.artifacts/'dmac-smmu.elf'
    for path in (binary,elf):
        if digest(path)!=metadata['artifacts'].get(path.name):raise RuntimeError('Artifact differs from build metadata')
    native=out/'native.json';cfg=out/'test.simics';cfg.write_text(script(binary.resolve(),a.boot.resolve(),native.resolve()))
    record={'scope':'Guest DMAC0 native-model transfer/fault, host-configured native S2 tables, TLB cache disabled; no physical hardware/TLBI qualification',
            'runner_sha256':digest(__file__),'fixture_sha256':digest(HERE/'native_dmac.py'),
            'native_fixture_sha256':digest(HERE.parent/'native_fixture.py'),
            'bootstrap_sha256':digest(a.boot),'build':metadata,'passed':False,'tests':[]}
    code,seconds,body=execute(a.project,cfg,out/'terminal.log',a.timeout)
    match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
    uart=match[1].replace('\r','') if match else ''
    begin=uart.find('LAB BEGIN dmac-smmu')
    if begin>=0:uart=uart[begin:]
    (out/'uart.txt').write_text(uart)
    observation=json.loads(native.read_text()) if native.is_file() else {}
    lines=uart.splitlines()
    markers=['PASS DMAC_SMMU_COPY_4096_NATIVE_ENGINE','PASS DMAC_SMMU_FAULT_GUARD_4096_NATIVE_ENGINE',
             'PASS DMAC_NATIVE_S2_TRANSLATION_FAULT_SID8','PASS DMAC_UNMAPPED_NO_FALSE_DONE',
             'PASS DMAC_FAULT_CHANNEL_QUIESCENT','PASS DMAC_REGISTERS_CLEANED_UP','LAB COMPLETE']
    passed=(code==0 and observation.get('passed') is True and all(m in lines for m in markers) and
            not any(line.startswith('FAIL ') for line in lines) and
            'SIMICS_DDR_BOOTSTRAP_COMPLETE' in body and 'DDR stage skipped' not in body)
    record.update(passed=passed,process_exit=code,seconds=seconds,native=observation)
    record['tests'].append({'name':'native-dmac-smmu','status':'pass' if passed else 'fail'})
    (out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
    print(('PASS' if passed else 'FAIL')+' NATIVE_DMAC_SMMU',out,flush=True)
    if not passed:print(body[-5000:],flush=True)
    return int(not passed)

if __name__=='__main__':raise SystemExit(main())
