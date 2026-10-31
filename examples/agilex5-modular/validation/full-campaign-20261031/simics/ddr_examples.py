#!/usr/bin/env python3
"""Native current DDR console exploration; never accesses physical media."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'simics'))
from support import execute,PROJECT
q=json.dumps
parser=argparse.ArgumentParser();parser.add_argument('--only');parser.add_argument('--bl31',type=Path);args=parser.parse_args()
out=Path(__file__).resolve().parent/('current-ddr-el2' if args.bl31 else 'current-ddr');out.mkdir(exist_ok=True)
boot=ROOT/'build/upstream26-ocram/baremetal.bin';image=ROOT/'build/campaign-simics-ddr/baremetal.bin';elf=image.with_suffix('.elf')
commands={'ccu':'ccu_selftest','clk_mngr':'clk_mngr_selftest','dma':'dma_selftest','ecc':'ecc_selftest','fcs':'fcs_selftest','gpio':'gpio_selftest','i2c':'i2c_selftest','i3c':'i3c_selftest','mmu':'mmu_selftest 3','sdmmc':'sdmmc_selftest','seu':'seu_selftest','smmu':'smmu_selftest','spi':'spi_selftest'}
if args.only:commands={k:v for k,v in commands.items() if k in args.only.split(',')}
# Thirteen current previously untested examples include ccu/clk_mngr; thirteen
# command cases here, with i3c containing three bundled subtests.
record={'scope':'Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only','source_revision':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'artifacts':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [boot,image,elf]},'tests':[]}
checks={'ccu':['CCU ID:','CCU uncorrected error status:','CCU L3 cache flush PASS'], 'clk_mngr':['Clock Manager Example Done','init: OK','L4_SP div=4 (valid)   : OK','L4_SP div=99 (invalid): OK'], 'dma':['[PASS] Sync data verification','[PASS] Async data verification','Callback fired : yes','[PASS] No transfer errors'], 'mmu':['MMU EL3: disabled'], 'smmu':['SMMU: disabled'], 'sdmmc':['[SDMMC][PASS] verify  1024 bytes match','[SDMMC] ---- done ----'], 'spi':['SPI0 loopback PASS (32 bytes, CS1)']}
if args.bl31:record['bl31_sha256']=hashlib.sha256(args.bl31.read_bytes()).hexdigest()
for name,command in commands.items():
 transfer=' set-pc 0x80200000'
 if args.bl31:transfer=f' hps.phys_mem.load-file {q(str(args.bl31.resolve()))} 0x80000000\n write-reg x0 0\n write-reg x1 0\n write-reg x2 0\n write-reg x3 0\n set-pc 0x80000000'
 folder=out/name;folder.mkdir(exist_ok=True)
 script=f'''$fsbl_image_filename = {q(str(boot))}
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
{transfer}
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "DDR_CONSOLE_READY"
 $con.input {q(command+chr(10))}
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "DDR_COMMAND_RETURNED"
 $transcript = ($con.record-stop)
 echo "UART_RECORD_BEGIN"
 echo $transcript
 echo "UART_RECORD_END"
 exit 0
}}
'''
 p=folder/'test.simics';p.write_text(script);code,sec,body=execute(PROJECT,p,folder/'terminal.log',45)
 match=re.search('UART_RECORD_BEGIN\\n(.*?)UART_RECORD_END',body,re.S)
 uart=(match[1] if match else body).replace('\r','');(folder/'uart.txt').write_text(uart)
 # Discard bootstrap PASS lines before the selected command.
 selected=uart.split(command+'\n',1)[-1]
 status='fail';limit=None
 ready=code==0 and 'DDR_COMMAND_RETURNED' in body and 'DDR stage skipped' not in uart
 inspected=selected.replace('GIC interrupt_enable failed (id=112, rc=1) - falling back to polling mode','GIC polling fallback')
 bad=bool(re.search(r'\[FAIL\]|\[MISMATCH\]|SELF-TEST FAILED|failed:|failed \(|timed out|^FAIL ',inspected,re.M|re.I))
 if ready and not bad:
  if name in checks:status='pass' if all(s in selected for s in checks[name]) else 'partial'
  elif name=='gpio':status='partial';limit='Source never opens the GPIO handle; printed value cannot prove a GPIO operation'
  elif name=='fcs':status='partial';limit='FCS identity/session/model capabilities must be separated; inspect per-step results'
  elif name=='i2c':status='partial' if '[SKIP]' in selected or 'skipped' in selected.lower() else 'pass'
  elif name=='i3c':status='pass' if all(s in selected for s in ['[I3C_I2C_XFER][PASS]','[I3C_PRIV_XFER][PASS]']) else 'partial'
  elif name in ['ecc','seu']:status='partial';limit='Injection completion and actual counter/event changes require manual model evidence review'
 if code==124:status='timeout';limit='Guest did not return to DDR console before the wall-clock bound'
 if status=='partial' and limit is None:limit='Command returned but required meaningful success markers were incomplete'
 record['tests'].append({'name':name,'catalog_id':'upstream/'+name,'command':command,'status':status,'process_exit':code,'seconds':sec,'limitation':limit,'script_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 (out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
 print(name+': '+status,flush=True)
