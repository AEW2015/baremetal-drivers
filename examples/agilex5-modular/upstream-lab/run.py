#!/usr/bin/env python3
"""Execute selected unchanged 26.3 examples through the isolated bench adapter."""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,new_run,execute,save
NAMES=['crc','perf','combophy','noc','iossm','bridge','reset','reboot','mailbox','smc-guard','bridge-control','perf-zero-clock']

def assess(name,body,code):
    if code!=0:return 'timeout' if code==124 else 'fail'
    if 'UPSTREAM_LAB_BEGIN' not in body:return 'fail'
    if name=='reboot':
        after=body.split('Inititating Warm Reboot',1)
        return 'pass' if len(after)==2 and 'Welcome to SoCFPGA Baremetal World' in after[1] and 'FAIL EXCEPTION' not in after[1] else 'fail'
    if 'UPSTREAM_LAB_COMPLETE status=0' not in body:return 'fail'
    if name=='perf-zero-clock':
        return 'pass' if 'TIMING_UNAVAILABLE' in body and 'PASS PERF_MEMORY_READBACK words=16384 mismatches=0' in body and 'rate=' not in body else 'fail'
    if name=='combophy' and 'base is not defined' in body:return 'unsupported'
    if name=='noc' and 'base is not defined' in body:return 'unsupported'
    if name=='bridge' and 'SiP bridge control not supported' in body:return 'unsupported'
    if re.search(r'\[FAIL\]|\[MISMATCH\]|SELF-TEST FAILED|^FAIL |failed \(rc=',body,re.M):return 'fail'
    checks={
      'crc':r'passed\s+: 4 case\(s\)\s+failed\s+: 0 case\(s\)',
      'perf':r'PASS PERF_MEMORY_READBACK words=16384 mismatches=0',
      'combophy':r'Combo PHY version=0x[0-9A-Fa-f]+ features=0x',
      'noc':r'RESULT : 6 of 6 tests passed  -  SELF-TEST PASSED',
      'iossm':r'All \d+ words match\.',
      'bridge':r'\[PASS\].*[Ll]oopback',
      'reset':r'SDMMC: RELEASED',
      'bridge-control':r'PASS BRIDGE_CONTROL enable=0 disable=0',
      'mailbox':r'\[MBOX\] done',
      'smc-guard':r'PASS SMC_EL3_REJECTED_AND_IOSSM_STATUS_VALIDATED',
    }
    if name=='reboot':return 'fail' # A reset request returning to main is not reset proof.
    if name=='iossm' and ('ECC error count after SBE injection: 0' in body or 'ECC error count after DBE injection: 0' in body):return 'partial'
    return 'pass' if re.search(checks[name],body) else 'fail'

def simics_script(image,boot,bl31=None,name=None):
    q=json.dumps
    transfer=' set-pc 0x82400000'
    if bl31:
        transfer=f' hps.phys_mem.load-file {q(str(bl31))} 0x80000000\n write-reg x0 0\n write-reg x1 0\n write-reg x2 0\n write-reg x3 0\n set-pc 0x80000000'
    wait='$ready' if name=='reboot' else '$done'
    witness=' echo "SIMICS_WARM_RESET_OBSERVED"' if name=='reboot' else ''
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$done = (bp.console_string.break $con -regexp "UPSTREAM_LAB_COMPLETE status=[01]")
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
{transfer}
 run
 bp.wait-for-breakpoint {wait}
 stop
{witness}
 $transcript = ($con.record-stop)
 echo "UART_RECORD_BEGIN"
 echo $transcript
 echo "UART_RECORD_END"
 exit 0
}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('environment',choices=['qemu','simics'])
    p.add_argument('--only',default='crc,perf')
    p.add_argument('--bl31',type=Path,help='Pinned RESET_TO_BL31 image; enters preloaded adapter as BL33 at EL2')
    p.add_argument('--timeout',type=int,default=45)
    p.add_argument('--project',type=Path,default=PROJECT)
    a=p.parse_args();names=a.only.split(',')
    if any(n not in NAMES for n in names):p.error('Choose '+','.join(NAMES))
    if a.environment=='qemu' and any(n not in ['crc','perf','smc-guard','perf-zero-clock'] for n in names):p.error('QEMU virt supports only the software CRC/memory-performance examples')
    target='qemu' if a.environment=='qemu' else 'agilex5'
    build=ROOT/'build'/('upstream-lab-'+target)
    metadata=json.loads((build/'build.json').read_text())
    out=new_run('new-examples-'+a.environment)
    record={'environment':a.environment,'runner_sha256':digest(Path(__file__)),'build':metadata,'tests':[]}
    for name in names:
        folder=out/name;folder.mkdir();image=build/(name+'.bin');elf=build/(name+'.elf')
        for path in (elf,image):
            if digest(path)!=metadata['artifacts'][path.name]:raise RuntimeError('Artifact differs from build manifest')
        if a.environment=='qemu':
            cmd=['qemu-system-aarch64','-M','virt,secure=on,virtualization=on,gic-version=3','-cpu','cortex-a53','-m','128M','-nographic','-nic','none','-semihosting-config','enable=on,target=native','-device',f'loader,file={elf},cpu-num=0']
            try:
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=a.timeout)
                code=r.returncode;body=r.stdout+r.stderr
            except subprocess.TimeoutExpired as exc:
                code=124;body=((exc.stdout or b'')+(exc.stderr or b'')).decode(errors='replace')
            (folder/'terminal.log').write_text(body)
        else:
            script=folder/'test.simics'
            script.write_text(simics_script(image.resolve(),(ROOT/'build/upstream26-ocram/baremetal.bin').resolve(),a.bl31.resolve() if a.bl31 else None,name))
            code,_,body=execute(a.project,script,folder/'terminal.log',a.timeout)
        match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
        uart=match[1].replace('\r','') if match else body.replace('\r','')
        (folder/'uart.txt').write_text(uart)
        status=assess(name,uart,code)
        if name=='reboot' and 'SIMICS_WARM_RESET_OBSERVED' not in body:status='fail'
        limitation=None
        if a.environment=='simics' and name=='iossm' and 'offset 0x300 where nothing is mapped' in body and 'All 8 words match.' in uart:
            status='partial';limitation='Model ECC counter register is unmapped; memory readback passes, injection command failure remains unqualified'
        if a.environment=='simics' and name=='mailbox' and '[MBOX][PASS] NOOP:' in uart and '[MBOX][PASS] CONFIG_STATUS:' in uart and 'SDM mbox cmd 0x10 rejected (err=0x3)' in uart:
            status='partial';limitation='Model rejects GET_IDCODE; NOOP and CONFIG_STATUS passed through BL31'

        if a.environment=='simics' and ('SIMICS_DDR_BOOTSTRAP_COMPLETE' not in body or 'DDR stage skipped' in uart):status='fail'
        record['tests'].append({'name':name,'status':status,'process_exit':code,'limitation':limitation,'bl31_sha256':digest(a.bl31) if a.bl31 else None,'elf_sha256':digest(elf),'timing_valid':name=='perf' and status=='pass' and 'TIMING_UNAVAILABLE' not in uart})
        save(out,record);print(name+': '+status,flush=True)
    return int(any(t['status'] not in ['pass','unsupported'] for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
