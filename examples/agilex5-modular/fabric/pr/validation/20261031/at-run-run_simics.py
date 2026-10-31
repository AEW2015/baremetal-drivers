#!/usr/bin/env python3
"""Run Arm guest MMIO against actual external Verilator RTL through Simics."""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,new_run,execute,save
from oracle import assess

CASES={'swap':(0,False),'load-error':(1,True),'wrong-persona':(2,True)}

def script(boot,image,server,trace,missing_done):
    q=json.dumps
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
@import sys
@sys.path.insert(0, {q(str(ROOT/'fabric/pr'))})
@import pr_adapter
@rtl_bridge = pr_adapter.install({q(str(server))}, {q(str(trace))}, {missing_done!r})
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$done = (bp.console_string.break $con -regexp "PR_LAB_COMPLETE status=[01]")
$con.record-start
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "SIMICS_RTL_DDR_BOOTSTRAP_COMPLETE"
 hps.phys_mem.load-file {q(str(image))} 0x82100000
 pselect "system.board.fpga.soc_inst.hps_subsys.agilex_hps.core[0]"
 set-pc 0x82100000
 run
 bp.wait-for-breakpoint $done
 stop
 @rtl_bridge.close()
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
    p.add_argument('--boot',type=Path,default=ROOT/'build/upstream26-ocram/baremetal.bin')
    p.add_argument('--only',default=','.join(CASES))
    p.add_argument('--timeout',type=int,default=60)
    a=p.parse_args();names=a.only.split(',')
    if any(n not in CASES for n in names):p.error('Choose '+','.join(CASES))
    if not 1<=a.timeout<=300:p.error('timeout must be 1..300 seconds')
    if not a.boot.is_file():p.error('Build bootstrap first: ./simics/build.sh OCRAM, or supply --boot')
    build=ROOT/'build/pr';metadata=json.loads((build/'build.json').read_text())
    for path,expected in metadata['sha256'].items():
        if digest(ROOT/path)!=expected:raise RuntimeError('Build source/artifact changed: '+path+'; rerun ./simics-rtl/build.sh')
    simics_version=subprocess.check_output([str(a.project.resolve()/'simics'),'--version'],text=True,timeout=15)
    out=new_run('pr-runtime');record={'scope':'One Arm guest executes ADD-XOR-ADD through the actual static-shell RTL and simulated loader; no RBF parsing, physical PR or HPS bridge timing qualification','simics_version':simics_version,'boot_sha256':digest(a.boot),'build':metadata,'adapter_sha256':digest(ROOT/'fabric/pr/pr_adapter.py'),'transport_sha256':digest(ROOT/'fabric/pr/pr_transport.py'),'runner_sha256':digest(Path(__file__)),'oracle_sha256':digest(ROOT/'fabric/pr/oracle.py'),'base_transport_sha256':digest(ROOT/'simics-rtl/transport.py'),'tests':[]}
    for name in names:
        mode,negative=CASES[name];folder=out/name;folder.mkdir();target=folder/'test.simics'
        server=build/f'model{mode}/Vpr_model';image=build/f'guest{int(negative)}.bin';trace=folder/'transactions.jsonl'
        target.write_text(script(a.boot.resolve(),image.resolve(),server.resolve(),trace.resolve(),False))
        code,seconds,body=execute(a.project,target,folder/'terminal.log',a.timeout)
        match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S);uart=match[1].replace('\r','') if match else ''
        (folder/'uart.txt').write_text(uart)
        summary=re.search(r'SIMICS_RTL_BACKEND_SUMMARY (\{[^\n]+\})',body)
        backend=json.loads(summary[1]) if summary else None
        transactions=[json.loads(line) for line in trace.read_text().splitlines() if line.startswith('{')] if trace.exists() else []
        guest_transactions=bool(transactions) and all((t.get('initiator') or '').endswith('.core[0]') for t in transactions)
        loads=[t.get('write_value') for t in transactions if t.get('op')=='write' and t.get('offset')==0x80]
        good=assess(name,uart,transactions,code,backend,body)
        item={'name':name,'status':'pass' if good else 'timeout' if code==124 else 'fail','process_exit':code,'seconds':seconds,'backend':backend,'all_transactions_from_arm_core0':guest_transactions,'simulated_loads':loads,'script_sha256':digest(target),'transactions_sha256':digest(trace) if trace.exists() else None}
        record['tests'].append(item);save(out,record);print(('PASS ' if good else 'FAIL ')+name,flush=True)
        if not good:print(body[-4000:],flush=True)
    return int(any(t['status']!='pass' for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
