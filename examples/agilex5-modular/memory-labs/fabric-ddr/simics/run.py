#!/usr/bin/env python3
"""Run the actual Arm driver -> Verilator AXI -> native Simics memory path."""
import argparse
import json
from pathlib import Path
import re
import sys
import datetime

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,execute

CASES={'physical':('physical','none'),'axi-error':('fault','axi-response'),
       'read-error':('read-fault','read-data'),'timeout-drain':('timeout','aw-stall'),
       'native-valid':('translated','none'),'native-fault':('fault','none')}

def script(boot,image,server,trace,route,injection):
    q=json.dumps
    configure=' @fabric_adapter.configure_native('+str(image.name=='fault.bin')+')\n' if route!='physical' else ''
    finish=' @fabric_adapter.finish_native()\n' if route!='physical' else ''
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
@import sys
@sys.path.insert(0, {q(str(HERE))})
@import fabric_adapter
@bridge = fabric_adapter.install({q(str(server))}, {q(str(trace))}, {q(route)}, {q(injection)})
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
 echo "FABRIC_DDR_BOOTSTRAP_COMPLETE"
{configure}\
 hps.phys_mem.load-file {q(str(image))} 0x82400000
 pselect "system.board.fpga.soc_inst.hps_subsys.agilex_hps.core[0]"
 set-pc 0x82400000
 run
 bp.wait-for-breakpoint $done
 stop
{finish}\
 @bridge.close()
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
    p.add_argument('--output',type=Path)
    p.add_argument('--timeout',type=int,default=90)
    p.add_argument('--route',choices=['physical','f2soc','f2sdram'],default='physical')
    p.add_argument('--case',choices=CASES,default='physical')
    args=p.parse_args()
    if not 1<=args.timeout<=180:p.error('timeout must be 1..180')
    native_case=args.case.startswith('native-')
    if native_case!=(args.route!='physical'):p.error('Native cases require f2soc/f2sdram; explicit injections require physical route')
    build=ROOT/'build/fabric-ddr-simics';metadata=json.loads((build/'build.json').read_text())
    for rel,sha in metadata['sources'].items():
        if digest(ROOT/rel)!=sha:raise RuntimeError('Build source changed; rebuild: '+rel)
    for rel,sha in metadata['artifacts'].items():
        if digest(build/rel)!=sha:raise RuntimeError('Build artifact changed: '+rel)
    out=args.output or HERE/'validation'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=True)
    path=out/'test.simics';trace=out/'transactions.jsonl'
    guest,injection=CASES[args.case]
    image=build/(guest+'.bin');server=build/'rtl/Vddr_probe'
    if native_case:server=build/'rtl-ns/Vddr_probe'
    fixture=ROOT/'memory-labs/smmu/native_fixture.py'
    fixture_hash=digest(fixture) if native_case else None
    path.write_text(script(args.boot.resolve(),image.resolve(),server.resolve(),trace.resolve(),args.route,injection))
    code,seconds,body=execute(args.project,path,out/'terminal.log',args.timeout)
    match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
    uart=match[1].replace('\r','') if match else ''
    begin=uart.find('LAB BEGIN fabric-ddr-rtl')
    if begin>=0:uart=uart[begin:]
    (out/'uart.txt').write_text(uart)
    summary=re.search(r'FABRIC_DDR_BACKEND_SUMMARY (\{[^\n]+\})',body)
    backend=json.loads(summary[1]) if summary else None
    native_match=re.search(r'FABRIC_DDR_NATIVE_RESULT (\{[^\n]+\})',body)
    native_result=json.loads(native_match[1]) if native_match else None
    transactions=[json.loads(line) for line in trace.read_text().splitlines() if line.startswith('{')] if trace.exists() else []
    axi=[t for t in transactions if t['kind']=='axi'];csr=[t for t in transactions if t['kind']=='csr']
    native=[t for t in transactions if t['kind']=='native-memory']
    writes=[t for t in axi if t['op']=='MEM_W'];reads=[t for t in axi if t['op']=='MEM_R']
    memory_ok=(len(writes)==len(reads)==64 and len(native)==128
               and all(t['response']==0 for t in axi)
               and all(t['space'].endswith('.phys_mem') and t['native_no_exception'] for t in native)
               and [t['address'] for t in writes]==[0x85000000+8*i for i in range(64)]
               and [t['address'] for t in reads]==[0x85000000+8*i for i in range(64)]
               and [t['data'] for t in writes]==[(((0x12345678^i)<<32)|((0x12345678+i)&0xffffffff)) for i in range(64)]
               and [t['data'] for t in reads]==[t['data'] for t in writes])
    markers=('FABRIC_DDR_CACHE_AND_MMU_OFF','FABRIC_DDR_RTL_VERIFIED','FABRIC_DDR_CPU_READBACK','FABRIC_DDR_UNSAFE_RANGE_REJECTED')
    injections=[t for t in transactions if t['kind']=='fault-injection']
    native_ok=all(t['space'].endswith('.phys_mem') and t['native_no_exception'] for t in native)
    backend_ok=bool(backend) and backend['axi_reads']==64 and backend['axi_writes']==64 and backend['axi_faults']==0
    if args.case=='axi-error':
        markers=('FABRIC_DDR_CACHE_AND_MMU_OFF','FABRIC_DDR_EXPECTED_AXI_FAULT')
        memory_ok=(len(writes)==len(native)==len(injections)==1 and not reads and native_ok
                   and writes[0]['address']==0x85002000 and writes[0]['response']==3
                   and injections[0]['type']=='axi-response')
        backend_ok=bool(backend) and backend['axi_writes']==1 and backend['axi_reads']==0 and backend['axi_faults']==1
    elif args.case=='read-error':
        markers=('FABRIC_DDR_CACHE_AND_MMU_OFF','FABRIC_DDR_EXPECTED_READ_CORRUPTION','FABRIC_DDR_NATIVE_MEMORY_UNCHANGED')
        memory_ok=(len(writes)==len(reads)==64 and len(native)==128 and native_ok
                   and len(injections)==1 and injections[0]['type']=='read-data'
                   and injections[0]['address']==0x850001f8
                   and all(t['response']==0 for t in axi)
                   and [t['data'] for t in reads[:-1]]==[t['data'] for t in writes[:-1]]
                   and reads[-1]['data']==writes[-1]['data']^1)
    elif args.case=='timeout-drain':
        markers=('FABRIC_DDR_CACHE_AND_MMU_OFF','FABRIC_DDR_EXPECTED_TIMEOUT_BUSY','FABRIC_DDR_TIMEOUT_DRAINED',
                 'FABRIC_DDR_TIMEOUT_STOPPED_AFTER_DRAIN','FABRIC_DDR_DRAINED_WRITE_COMPLETED')
        memory_ok=(len(writes)==len(native)==len(injections)==1 and not reads and native_ok
                   and writes[0]['address']==0x85000000 and writes[0]['response']==0
                   and injections[0]['type']=='aw-stall' and injections[0]['ready_after_rtl_cycle']==1600)
        backend_ok=bool(backend) and backend['axi_writes']==1 and backend['axi_reads']==0 and backend['axi_faults']==0 and backend['rtl_cycles']>=1600
    elif native_case:
        suffix='.f2soc_smmu_mem_space' if args.route=='f2soc' else '.f2sdram_smmu_mem_space'
        path_ok=bool(native) and all(t['space'].endswith(suffix) and t['axprot']==2 and t['axuser']==0 for t in native)
        fixture_ok=(native_result is not None and native_result['passed'] and native_result['configuration']['tlb_cache_enable'] is False
                    and native_result['configuration']['sid']==0 and native_result['physical_iova_guard_unchanged']
                    and native_result['target_words_checked']==64 and fixture_hash==digest(fixture))
        if args.case=='native-valid':
            memory_ok=(len(writes)==len(reads)==64 and len(native)==128 and path_ok and fixture_ok
                       and not native_result['unmapped'] and all(t['native_no_exception'] for t in native)
                       and [t['address'] for t in writes]==[0x85000000+8*i for i in range(64)]
                       and [t['address'] for t in reads]==[0x85000000+8*i for i in range(64)]
                       and [t['data'] for t in reads]==[t['data'] for t in writes]
                       and [t['data'] for t in writes]==[(((0x12345678^i)<<32)|((0x12345678+i)&0xffffffff)) for i in range(64)])
        else:
            markers=('FABRIC_DDR_CACHE_AND_MMU_OFF','FABRIC_DDR_EXPECTED_AXI_FAULT')
            memory_ok=(len(writes)==len(native)==1 and not reads and path_ok and fixture_ok
                       and native_result['unmapped'] and not native[0]['native_no_exception']
                       and writes[0]['address']==0x85002000 and writes[0]['response']==3
                       and not injections)
            backend_ok=bool(backend) and backend['axi_writes']==1 and backend['axi_reads']==0 and backend['axi_faults']==1
    good=(code==0 and 'FABRIC_DDR_BOOTSTRAP_COMPLETE' in body and 'DDR stage skipped' not in body
          and 'FABRIC_DDR_ADAPTER_ERROR' not in body and 'LAB BEGIN fabric-ddr-rtl' in uart
          and 'LAB COMPLETE' in uart.splitlines() and 'FAIL ' not in uart and backend is not None
          and all('PASS '+marker in uart.splitlines() for marker in markers)
          and bool(csr) and all((t['initiator'] or '').endswith('.core[0]') for t in csr)
          and memory_ok and backend_ok
          and all(t.get('axprot')==(2 if native_case else 0) and t.get('axuser')==0 for t in axi))
    scope=('Actual Arm driver CSR -> actual Verilator AXI initiator -> native Simics '+
           ('F2H/F2SDRAM TBU stage-2 table walks -> DDR; model TLB cache disabled, no command-queue/TLBI claim'
            if native_case else 'physical DDR; explicit injections are not native SMMU faults')+
           '; no physical bridge or cycle-accurate platform timing qualification')
    result={'scope':scope,
            'status':'pass' if good else 'fail','route':args.route,'case':args.case,'explicit_injection':injection,
            'process_exit':code,'seconds':seconds,'backend':backend,
            'native_smmu':native_result,'native_fixture_sha256':fixture_hash,
            'memory_transactions_checked':memory_ok,'build':metadata,'bootstrap_sha256':digest(args.boot),
            'runner_sha256':digest(__file__),'adapter_sha256':digest(HERE/'fabric_adapter.py'),
            'transport_sha256':digest(HERE/'transport.py'),'script_sha256':digest(path)}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(('PASS ' if good else 'FAIL ')+'fabric-ddr-rtl-'+args.case)
    print(out)
    if not good:print(body[-3500:])
    return int(not good)

if __name__=='__main__':raise SystemExit(main())
