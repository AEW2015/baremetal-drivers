#!/usr/bin/env python3
"""Native Agilex Simics attempt of the unchanged physical-addressed PSCI harness."""
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent/'psci';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'simics'))
from support import PROJECT,digest,execute
spec=importlib.util.spec_from_file_location('upstream_runner',ROOT/'upstream-lab/run.py');up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
spec=importlib.util.spec_from_file_location('psci_oracle',ROOT/'reference/psci/oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
build=ROOT/'build/reference-psci';metadata=json.loads((build/'build.json').read_text())
for suffix in ['.bin','.elf']:
 image=build/('psci'+suffix)
 assert metadata['artifacts'][image.name]==digest(image)
image=build/'psci.bin';boot=ROOT/'build/upstream26-ocram/baremetal.bin';bl31=ROOT/'build/runtime-atf/agilex5/debug/bl31.bin'
s=up.simics_script(image.resolve(),boot.resolve(),bl31.resolve(),'psci')
s=s.replace('UPSTREAM_LAB_COMPLETE status=[01]','PSCI_COMPLETE status=[012]')
s=s.replace(' echo "UART_RECORD_BEGIN"',' echo "PSCI_NATIVE_MODEL_DONE"\n echo "UART_RECORD_BEGIN"')
p=OUT/'test.simics';p.write_text(s)
code,seconds,body=execute(PROJECT,p,OUT/'terminal.log',120)
match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
uart=(match[1] if match else body).replace('\r','');(OUT/'uart.txt').write_text(uart)
status=oracle.assess('psci',uart,code)
if 'SIMICS_DDR_BOOTSTRAP_COMPLETE' not in body or 'DDR stage skipped' in uart:status='fail'
record={'scope':'Native Agilex Simics cores and resident TF-A PSCI; same physical-addressed C/ASM harness and strict oracle, no QEMU substitution or physical-board claim','simulator_exit':code,'seconds':seconds,'build':metadata,'boot_sha256':digest(boot),'bl31_sha256':digest(bl31),'oracle_sha256':digest(ROOT/'reference/psci/oracle.py'),'script_sha256':digest(p),'tests':[{'name':'reference/psci','status':status}]}
(OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print(status);print(uart[-4000:])
