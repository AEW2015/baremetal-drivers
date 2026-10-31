from pathlib import Path
import json,subprocess,time,datetime
root=Path('/home/lada/quartus26-mcp-demos/baremetal-fixes-20261029/examples/agilex5-modular')
out=root/'validation/full-campaign-20261031/qemu/20261031T183144.039830Z'
p=out/'results.json';record=json.loads(p.read_text())
for name,command in [
 ('unit-main','AGILEX_TEST_REAL_QEMU=1 python3 -m unittest discover -s tests -v'),
 ('unit-model','python3 -m unittest discover -s model-audit -p "test_*.py" -v'),
 ('unit-config','python3 -m unittest discover -s config-audit -p "test_*.py" -v'),
 ('unit-usb-bringup','python3 -m unittest discover -s usb-bringup -p "test*.py" -v'),
 ('unit-usb-host','python3 -m unittest discover -s usb-host/tests -p "test*.py" -v'),
 ('simics-rtl-protocol','python3 simics-rtl/test_protocol.py'),
 ('simics-rtl-transport','python3 simics-rtl/test_transport.py')]:
 start=time.monotonic();cmd=['docker','exec','-e','CROSS_COMPILE=aarch64-none-elf-','agilex26-mcp-demos','bash','-lc','cd /workspace/baremetal-fixes-20261029/examples/agilex5-modular && '+command]
 try:
  result=subprocess.run(cmd,capture_output=True,timeout=360);raw=result.stdout+result.stderr;rc=result.returncode
 except subprocess.TimeoutExpired as e:raw=(e.stdout or b'')+(e.stderr or b'');rc=124
 (out/(name+'.log')).write_bytes(raw)
 record['steps'].append({'name':name,'command':cmd,'returncode':rc,'status':'pass' if rc==0 else 'fail','elapsed_seconds':time.monotonic()-start})
 record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();p.write_text(json.dumps(record,indent=2)+'\n')
 print(name,rc,flush=True)
