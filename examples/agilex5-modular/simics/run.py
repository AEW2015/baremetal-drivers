#!/usr/bin/env python3
"""Container: exercise the current upstream 26.3 OCRAM command console in Simics."""
import argparse,json,re,struct,sys
from pathlib import Path
from support import ROOT,PROJECT,digest,new_run,execute,save
COMMANDS={
 'hello':('hello_selftest','Hello, Baremetal World!'),
 'help':('help','hello_selftest'),
 'timer':('timer_selftest','RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED'),
 'gic':('gic_selftest','RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED'),
 'ddr':('ddr_selftest','RESULT : 4 of 4 tests passed  -  SELF-TEST PASSED'),
}

def script(image,command):
    q=json.dumps
    return f'''$fsbl_image_filename = {q(str(image))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$con.record-start
script-branch {{
    run
    bp.wait-for-breakpoint $ready
    stop
    echo "SIMICS_UPSTREAM_READY"
    $con.input {q(command+chr(10))}
    run
    bp.wait-for-breakpoint $ready
    stop
    echo "SIMICS_UPSTREAM_COMPLETE"
    $transcript = ($con.record-stop)
    echo "UART_RECORD_BEGIN"
    echo $transcript
    echo "UART_RECORD_END"
    exit 0
}}
'''

def assess(body,expected,code):
    match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
    uart=match[1].replace('\r','') if match else ''
    passed=code==0 and 'SIMICS_UPSTREAM_READY' in body and 'SIMICS_UPSTREAM_COMPLETE' in body and expected in uart and 'SELF-TEST FAILED' not in uart and 'Unknown command.' not in uart
    return passed,uart

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only',default='hello',help='Comma-separated '+','.join(COMMANDS))
    p.add_argument('--project',type=Path,default=PROJECT)
    p.add_argument('--timeout',type=int,default=60)
    a=p.parse_args();names=a.only.split(',')
    if any(n not in COMMANDS for n in names):p.error('Choose '+','.join(COMMANDS))
    if not 1<=a.timeout<=300:p.error('timeout must be 1..300 seconds')
    build=ROOT/'build/upstream26-ocram';elf=build/'baremetal.elf';image=build/'baremetal.bin'
    if not elf.is_file() or not image.is_file():p.error('Build first: ./simics/build.sh OCRAM')
    header=elf.read_bytes()[:64]
    if len(header)<64 or header[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',header,18)[0]!=183 or struct.unpack_from('<Q',header,24)[0]!=0:p.error('Expected the standalone OCRAM ELF with entry 0')
    out=new_run('upstream26');record={'scope':'upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification','elf_sha256':digest(elf),'binary_sha256':digest(image),'tests':[]}
    metadata=build/'build.json'
    if metadata.exists():
        record['build']=json.loads(metadata.read_text())
        if record['build']['elf_sha256']!=record['elf_sha256'] or record['build']['binary_sha256']!=record['binary_sha256']:raise RuntimeError('Image differs from build metadata; rerun ./simics/build.sh OCRAM')
    for name in names:
        command,expected=COMMANDS[name];target=out/name;target.mkdir()
        path=target/'test.simics';path.write_text(script(image.resolve(),command))
        code,seconds,body=execute(a.project,path,target/'terminal.log',a.timeout)
        passed,uart=assess(body,expected,code);(target/'uart.txt').write_text(uart)
        fallback=name=='ddr' and 'DDR stage skipped' in uart
        item={'name':name,'command':command,'status':'pass' if passed else 'timeout' if code==124 else 'fail','simulator_exit':code,'seconds':seconds,'expected':expected,'ddr_stage_skipped':fallback,'script_sha256':digest(path)}
        record['tests'].append(item);save(out,record)
        print(('PASS ' if passed else 'FAIL ')+name+(' (OCRAM fallback only; DDR stage skipped)' if fallback else ''),flush=True)
        if not passed:print(body[-1800:],flush=True)
    return 0 if all(x['status']=='pass' for x in record['tests']) else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,RuntimeError) as exc:print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(1)
