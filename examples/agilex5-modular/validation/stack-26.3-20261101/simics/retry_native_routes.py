from pathlib import Path
import subprocess,json,time
OUT=Path(__file__).resolve().parent
REMOTE='/workspace/baremetal-fixes-20261029/examples/agilex5-modular'
results=[]
for name,route,case in [('f2h-valid','f2soc','native-valid'),('f2h-fault','f2soc','native-fault'),('f2sdram-valid','f2sdram','native-valid'),('f2sdram-fault','f2sdram','native-fault')]:
 label='fabric-'+name
 old=OUT/(label+'.log')
 if old.exists() and not (OUT/(label+'-cli-error.log')).exists():old.rename(OUT/(label+'-cli-error.log'))
 command=f'cd {REMOTE} && python3 memory-labs/fabric-ddr/simics/run.py --case {case} --route {route} --output {REMOTE}/validation/stack-26.3-20261101/simics/{label}'
 print('BEGIN',name,flush=True);start=time.monotonic()
 r=subprocess.run(['docker','exec','agilex26-mcp-demos','bash','-lc',command],capture_output=True,text=True,timeout=180)
 old.write_text(r.stdout+r.stderr)
 results.append({'label':label,'command':command,'exit_code':r.returncode,'seconds':time.monotonic()-start,'evidence':label+'/results.json'})
 (OUT/'native-route-retry-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print('END',name,r.returncode,flush=True)
