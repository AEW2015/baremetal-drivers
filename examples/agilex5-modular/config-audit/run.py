#!/usr/bin/env python3
"""Execute read-only HPS configuration snapshots on the Agilex Simics model."""
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,new_run,execute,save
NAMES=['sysmgr','pinmux','unstable']
REGISTERS={'sysmgr':['SILICONID1','SILICONID2','MPU_STATUS'],
           'pinmux':['PIN2SEL','PIN3SEL','UART0_USEFPGA']}

def snapshot(name,body):
    registers={}
    for key in REGISTERS['pinmux' if name=='unstable' else name]:
        matches=re.findall(r'^'+key+r'(0x[0-9a-f]{16})\s*$',body,re.M)
        if len(matches)!=1:raise ValueError('Missing or duplicate register: '+key)
        registers[key]=int(matches[0],16)
        if registers[key]>0xffffffff:raise ValueError('Not a 32-bit register: '+key)
    return {'registers':registers}

def assess(name,body,code):
    if code!=0 or 'FAIL EXCEPTION' in body:return 'fail'
    if name not in NAMES:return 'fail'
    base='pinmux' if name=='unstable' else name
    if 'CONFIG_AUDIT_BEGIN '+base not in body:return 'fail'
    expected_status='1' if name=='unstable' else '0'
    if re.findall(r'CONFIG_AUDIT_COMPLETE status=([01])',body)!=[expected_status]:return 'fail'
    try:values=snapshot(name,body)['registers']
    except ValueError:return 'fail'
    if any(v==0xffffffff for v in values.values()):return 'fail'
    if name=='unstable':
        return 'pass' if 'FAIL UNSTABLE_OR_UNAVAILABLE PIN2SEL' in body and 'CONFIG_AUDIT_COMPLETE status=1' in body and 'status=0' not in body else 'fail'
    return 'pass' if 'PASS READ_ONLY_SNAPSHOT registers=3' in body and 'CONFIG_AUDIT_COMPLETE status=0' in body and 'FAIL ' not in body else 'fail'

def script(image,boot):
    q=json.dumps
    return f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$done = (bp.console_string.break $con -regexp "CONFIG_AUDIT_COMPLETE status=[01]")
$con.record-start
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "CONFIG_AUDIT_DDR_READY"
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
    p.add_argument('--only',default=','.join(NAMES))
    p.add_argument('--project',type=Path,default=PROJECT)
    p.add_argument('--boot',type=Path,default=ROOT/'build/upstream26-ocram/baremetal.bin')
    p.add_argument('--timeout',type=int,default=60)
    a=p.parse_args();names=a.only.split(',')
    if not names or any(n not in NAMES for n in names):p.error('Choose '+','.join(NAMES))
    if not 1<=a.timeout<=300:p.error('timeout must be 1..300 seconds')
    build=ROOT/'build/config-audit';metadata=json.loads((build/'build.json').read_text())
    out=new_run('config-audit');record={'environment':'simics','scope':'Read-only snapshots and negative control; no physical-board qualification','build':metadata,'bootstrap_sha256':digest(a.boot),'runner_sha256':digest(Path(__file__)),'tests':[]}
    for name in names:
        image=build/(name+'.bin');elf=build/(name+'.elf')
        if any(digest(path)!=metadata['artifacts'][path.name] for path in (image,elf)):raise RuntimeError('Build artifact hash mismatch')
        folder=out/name;folder.mkdir();path=folder/'test.simics';path.write_text(script(image.resolve(),a.boot.resolve()))
        code,seconds,body=execute(a.project,path,folder/'terminal.log',a.timeout)
        match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
        uart=match[1].replace('\r','') if match else ''
        # The stock console prompt does not end in a newline.
        begin=uart.find('CONFIG_AUDIT_BEGIN ')
        if begin>=0:uart=uart[begin:]
        (folder/'uart.txt').write_text(uart)
        status=assess(name,uart,code)
        if 'CONFIG_AUDIT_DDR_READY' not in body or 'DDR stage skipped' in body:status='fail'
        if status=='pass':(folder/'snapshot.json').write_text(json.dumps(snapshot(name,uart),indent=2)+'\n')
        record['tests'].append({'name':name,'status':status,'process_exit':code,'seconds':seconds,'elf_sha256':digest(elf),'negative_control':name=='unstable'})
        save(out,record);print(name+': '+status,flush=True)
        if status!='pass':print(body[-2000:],flush=True)
    return int(any(t['status']!='pass' for t in record['tests']))

if __name__=='__main__':raise SystemExit(main())
