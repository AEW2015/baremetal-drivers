#!/usr/bin/env python3
"""Run the shared EL3 practice labs on the Agilex 5 Simics platform.

Hardware uses upstream-lab/hardware.py --suite practice, with the same oracle.
"""
import argparse,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,new_run,execute,save
spec=importlib.util.spec_from_file_location('practice_oracle',ROOT/'qemu/labs/run.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
NAMES=list(oracle.LABS)
UART_CASES=oracle.UART_CASES

def assess(name,body,code):
    # The upstream console prompt has no trailing newline before transfer.
    begin=re.search(r'LAB BEGIN [a-z]+',body)
    if begin:body=body[begin.start():]
    if name in oracle.NEGATIVES:
        base,marker=oracle.NEGATIVES[name]
        lines=body.splitlines()
        return 'pass' if code==0 and f'LAB BEGIN {base}' in lines and 'FAIL '+marker in lines and 'LAB FAILED' in lines and 'LAB COMPLETE' not in lines else 'fail'
    if not oracle.accepts(name,body,code):return 'fail'
    if name=='uart':
        # Validate each response independently, including overflow recovery.
        chunks=body.split('lab> ')
        if len(chunks)!=len(UART_CASES)+1:return 'fail'
        for chunk,(_,_,expected) in zip(chunks[1:],UART_CASES):
            if expected!=b'lab> ' and expected.decode() not in chunk:return 'fail'
    return 'pass'

def script(image,boot,name):
    q=json.dumps
    interaction=''
    if name=='uart':
        interaction=' run\n bp.wait-for-breakpoint $prompt\n stop\n'
        for label,payload,_ in UART_CASES:
            # Simics console.input maps LF to CR; avoid sending CR twice.
            interaction+=f' $con.input {q(payload.decode().replace(chr(13)+chr(10),chr(13)))}\n run\n bp.wait-for-breakpoint '+('$done' if label=='exit' else '$prompt')+'\n stop\n'
    else:interaction=' run\n bp.wait-for-breakpoint $done\n stop\n'
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$done = (bp.console_string.break $con -regexp "LAB (COMPLETE|FAILED)")
$prompt = (bp.console_string.break $con "lab> ")
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
{interaction}
 $transcript = ($con.record-stop)
 echo "UART_RECORD_BEGIN"
 echo $transcript
 echo "UART_RECORD_END"
 exit 0
}}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only',default=','.join(NAMES))
    p.add_argument('--negative',action='store_true')
    p.add_argument('--project',type=Path,default=PROJECT)
    p.add_argument('--timeout',type=int,default=60)
    a=p.parse_args();names=a.only.split(',')
    if any(n not in NAMES for n in names):p.error('Choose '+','.join(NAMES))
    if a.negative:names+=list(oracle.NEGATIVES)
    build=ROOT/'build/practice-agilex5';metadata=json.loads((build/'build.json').read_text())
    boot=ROOT/'build/upstream26-ocram/baremetal.bin'
    out=new_run('practice');record={'environment':'simics','runner_sha256':digest(Path(__file__)),'bootstrap_sha256':digest(boot),'build':metadata,'tests':[]}
    for name in names:
        image=build/(name+'.bin');elf=build/(name+'.elf')
        for path in (image,elf):
            if digest(path)!=metadata['artifacts'][path.name]:raise RuntimeError('Artifact hash mismatch')
        folder=out/name;folder.mkdir();path=folder/'test.simics'
        path.write_text(script(image.resolve(),boot.resolve(),name))
        code,seconds,body=execute(a.project,path,folder/'terminal.log',a.timeout)
        match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
        uart=match[1].replace('\r','') if match else body.replace('\r','')
        (folder/'uart.txt').write_text(uart)
        status=assess(name,uart,code)
        if 'SIMICS_DDR_BOOTSTRAP_COMPLETE' not in body or 'DDR stage skipped' in uart:status='fail'
        record['tests'].append({'name':name,'status':status,'process_exit':code,'seconds':seconds,'elf_sha256':digest(elf)})
        save(out,record);print(name+': '+status,flush=True)
        if status!='pass':print(body[-1800:],flush=True)
    return int(any(t['status']!='pass' for t in record['tests']))
if __name__=='__main__':raise SystemExit(main())
