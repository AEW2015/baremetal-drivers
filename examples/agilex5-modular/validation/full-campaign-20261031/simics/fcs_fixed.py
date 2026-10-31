#!/usr/bin/env python3
"""Controlled fixed-FCS rerun; leave the baseline 63-row campaign untouched."""
import datetime,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/('fcs-fixed-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));OUT.mkdir()
sys.path.insert(0,str(ROOT/'simics'));from support import PROJECT,digest,execute
spec=importlib.util.spec_from_file_location('upstream_runner',ROOT/'upstream-lab/run.py');up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
spec=importlib.util.spec_from_file_location('service_oracle',ROOT/'service-candidates/oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
build=ROOT/'build/service-candidates-fcs-fixed';metadata=json.loads((build/'build.json').read_text())
for suffix in ['.bin','.elf']:
 p=build/('fcs'+suffix);assert digest(p)==metadata['artifacts'][p.name],p
image=build/'fcs.bin';boot=ROOT/'build/upstream26-ocram/baremetal.bin';bl31=ROOT/'build/runtime-atf/agilex5/debug/bl31.bin'
s=up.simics_script(image.resolve(),boot.resolve(),bl31.resolve(),'fcs')
s=s.replace('UPSTREAM_LAB_COMPLETE status=[01]','SERVICE_COMPLETE status=[0123456789]+')
p=OUT/'test.simics';p.write_text(s)
code,seconds,body=execute(PROJECT,p,OUT/'terminal.log',120)
match=re.search(r'UART_RECORD_BEGIN\n(.*?)UART_RECORD_END',body,re.S)
uart=(match[1] if match else body).replace('\r','');(OUT/'uart.txt').write_text(uart)
status=oracle.assess('fcs',uart,code)
if 'SIMICS_DDR_BOOTSTRAP_COMPLETE' not in body or 'DDR stage skipped' in uart:status='fail'
selected=uart.split('SERVICE_BEGIN name=fcs EL=2',1)[-1]
completed=bool(re.search(r'^SERVICE_COMPLETE status=\d+$',selected,re.M))
restart='Welcome to SoCFPGA Baremetal World' in selected
record={'scope':'Fixed FCS HAL response-lifetime test on native Agilex Simics + resident TF-A BL31; strict API capability result separate from preserved control flow; no physical claim','simulator_exit':code,'seconds':seconds,'build':metadata,'boot_sha256':digest(boot),'bl31_sha256':digest(bl31),'oracle_sha256':digest(ROOT/'service-candidates/oracle.py'),'script_sha256':digest(p),'tests':[{'name':'fcs-fixed','status':status,'service_completion_observed':completed,'unexpected_ocram_restart':restart,'control_flow_preserved':completed and not restart and 'FAIL SERVICE_EXCEPTION' not in selected,'model_sdm_rejection_observed':bool(re.search(r'mailbox_err 0?3|SDM.*(?:err|status).*0x3|\[FCS\]\[FAIL\]',selected,re.I))}]}
(OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('Evidence:',OUT);print('FCS strict capability result:',status);print('Preserved control flow:',record['tests'][0]['control_flow_preserved']);print(selected[-6500:])
