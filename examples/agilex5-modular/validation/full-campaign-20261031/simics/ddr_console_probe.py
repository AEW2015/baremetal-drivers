#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'simics'))
from support import execute,PROJECT
q=json.dumps
boot=ROOT/'build/upstream26-ocram/baremetal.bin';image=ROOT/'build/upstream26-ddr/baremetal.bin';out=Path(__file__).resolve().parent/'ddr-console-probe';out.mkdir(exist_ok=True)
s=f'''$fsbl_image_filename = {q(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$con.record-start
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "PREPARED_DDR"
 hps.phys_mem.load-file {q(str(image))} 0x80200000
 pselect "system.board.fpga.soc_inst.hps_subsys.agilex_hps.core[0]"
 set-pc 0x80200000
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "DDR_CONSOLE_READY"
 $con.input "help\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "DDR_CONSOLE_HELP_DONE"
 $transcript = ($con.record-stop)
 echo "UART_RECORD_BEGIN"
 echo $transcript
 echo "UART_RECORD_END"
 exit 0
}}
'''
p=out/'test.simics';p.write_text(s);code,sec,body=execute(PROJECT,p,out/'terminal.log',45)
(out/'results.json').write_text(json.dumps({'status':'pass' if code==0 and 'DDR_CONSOLE_HELP_DONE' in body else 'fail','process_exit':code,'seconds':sec},indent=2)+'\n')
print(body[-3500:]);print('exit',code)
