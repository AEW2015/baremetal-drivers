from pathlib import Path
import json,subprocess,time
out=Path(__file__).resolve().parent
remote='/workspace/baremetal-fixes-20261029/examples/agilex5-modular'
records=[]
for label,case,route in [('f2h-valid','native-valid','f2soc'),('f2h-fault','native-fault','f2soc'),('f2sdram-valid','native-valid','f2sdram'),('f2sdram-fault','native-fault','f2sdram')]:
 command=f'python3 memory-labs/fabric-ddr/simics/run.py --case {case} --route {route} --output {remote}/validation/full-campaign-20261031/simics/fabric-{label}'
 start=time.monotonic();r=subprocess.run(['docker','exec','agilex26-mcp-demos','bash','-lc',f'cd {remote} && {command}'],capture_output=True,text=True,timeout=200)
 (out/f'fabric-{label}-retry.log').write_text(r.stdout+r.stderr)
 records.append({'name':label,'command':command,'exit_code':r.returncode,'seconds':time.monotonic()-start,'evidence':f'fabric-{label}/results.json'})
 (out/'fabric-retry-results.json').write_text(json.dumps({'scope':'Retry with actual runner CLI names; initial human-label arguments were rejected before execution','commands':records},indent=2)+'\n')
 print(label+': '+str(r.returncode),flush=True)
