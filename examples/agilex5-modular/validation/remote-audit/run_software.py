from pathlib import Path
import subprocess,time,json,datetime
out=Path(__file__).parent
root=Path('/home/lada/altera-agilex/home/baremetal-remote-audit-0daff10')
container_root='/home/dev/baremetal-remote-audit-0daff10'
results={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'remote':'https://github.com/AEW2015/baremetal-drivers.git','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':[]}
stages=[
 ('versions','aarch64-none-elf-gcc --version && qemu-system-aarch64 --version && gdb-multiarch --version && verilator --version'),
 ('qemu-doctor','python3 doctor.py --target qemu'),
 ('qemu-build','./qemu/build.sh'),
 ('qemu-hello','python3 qemu/run.py --check'),
 ('qemu-experiment','python3 qemu/experiment.py'),
 ('qemu-labs-build','bash qemu/labs/build.sh'),
 ('qemu-labs-run','python3 qemu/labs/run.py --negative --gdb'),
 ('regressions','AGILEX_TEST_REAL_QEMU=1 python3 -m unittest discover -s tests -v'),
 ('fabric-simulation','./fabric/test.sh'),
 ('fabric-driver-build','LAB_CPU_BASE=0x20020000 ./fabric/build.sh'),
 ('all-examples-build','./build_all.sh'),
 ('ocram-build','./bootstrap/ocram/build_uart.sh'),
]
for name,command in stages:
 print(f'START {name}',flush=True);start=time.monotonic()
 with (out/(name+'.log')).open('w') as log:
  args=['docker','exec','-u','dev','agilex-xrdp','bash','-lc',f'source /etc/profile.d/baremetal-tools.sh && cd {container_root}/examples/agilex5-modular && {command}']
  try:rc=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=1200).returncode
  except subprocess.TimeoutExpired:rc=124
 result={'name':name,'command':command,'exit':rc,'seconds':round(time.monotonic()-start,2),'log':name+'.log'}
 results['tests'].append(result);(out/'software-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print(f'{"PASS" if rc==0 else "FAIL"} {name} exit={rc} ({result["seconds"]}s)',flush=True)
raise SystemExit(any(t['exit'] for t in results['tests']))
