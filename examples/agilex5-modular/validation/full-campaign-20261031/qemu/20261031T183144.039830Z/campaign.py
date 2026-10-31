from pathlib import Path
import subprocess,json,datetime,hashlib,shutil,time,os
root=Path('/home/lada/quartus26-mcp-demos/baremetal-fixes-20261029/examples/agilex5-modular')
out=root/'validation/full-campaign-20261031/qemu'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out.mkdir(parents=True)
remote='/workspace/baremetal-fixes-20261029/examples/agilex5-modular'
record={'scope':'QEMU functional and independent RTL campaign; no hardware or cycle-accurate timing claim','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'steps':[],'tests':[]}
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print(out,flush=True)
def run(name,command,timeout=240):
 start=time.monotonic()
 cmd=['docker','exec','-e','CROSS_COMPILE=aarch64-none-elf-','-e','FABRIC_DDR_BUILD=../../build/fabric-ddr-qemu-campaign','agilex26-mcp-demos','bash','-lc','cd '+remote+' && '+command]
 try:
  p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
  raw=p.stdout;rc=p.returncode
 except subprocess.TimeoutExpired as e:raw=e.stdout or b'';rc=124
 (out/(name+'.log')).write_bytes(raw)
 item={'name':name,'command':cmd,'status':'pass' if rc==0 else 'fail','returncode':rc,'elapsed_seconds':time.monotonic()-start}
 record['steps'].append(item);(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
 print(name,item['status'],flush=True)
 return rc
run('versions',"qemu-system-aarch64 --version; aarch64-none-elf-gcc --version; aarch64-linux-gnu-gcc --version; gdb-multiarch --version; verilator --version")
run('hello-build','bash qemu/build.sh')
run('hello-run','python3 qemu/run.py --check')
run('hello-experiment','python3 qemu/experiment.py')
run('practice-build','bash qemu/labs/build.sh qemu')
remote_out=remote+'/'+str(out.relative_to(root))
run('practice-run','python3 qemu/labs/run.py --negative --gdb --output '+remote_out+'/practice',timeout=360)
run('dsu-build','bash memory-labs/dsu/build.sh qemu')
run('dsu-run','python3 memory-labs/dsu/run.py --output '+remote_out+'/dsu',timeout=240)
run('ddr-build','bash memory-labs/ddr/build.sh qemu')
run('ddr-run','python3 memory-labs/ddr/run.py --output '+remote_out+'/ddr',timeout=360)
run('smmu-build','bash memory-labs/smmu/build.sh')
run('smmu-run','python3 memory-labs/smmu/run.py --out '+remote_out+'/smmu',timeout=120)
run('upstream-build','bash upstream-lab/build.sh qemu')
before=set((root/'runs').glob('new-examples-qemu-*'))
run('upstream-run','python3 upstream-lab/run.py qemu --only crc,perf,smc-guard,perf-zero-clock',timeout=240)
for p in set((root/'runs').glob('new-examples-qemu-*'))-before:shutil.copytree(p,out/'upstream')
run('fabric-rtl','bash fabric/test.sh',timeout=240)
run('fabric-ddr-rtl','bash memory-labs/fabric-ddr/test.sh',timeout=240)
artifacts={}
for folder in ['build/qemu','build/qemu-labs','build/dsu-qemu','build/memory-ddr-qemu','build/memory-smmu','build/upstream-lab-qemu']:
 for p in sorted((root/folder).glob('*')):
  if p.suffix in ('.elf','.bin','.json'):artifacts[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
record['artifacts_sha256']=artifacts
record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('DONE',out,flush=True)
