from pathlib import Path
import json,os,subprocess,sys,tempfile,time
from unittest import mock
root=Path('/home/lada/altera-agilex/home/baremetal-remote-audit-0daff10/examples/agilex5-modular');sys.path.insert(0,str(root))
import bench,owned_process
with tempfile.TemporaryDirectory() as folder:
 temp=Path(folder);binpath=temp/'bin';binpath.mkdir()
 docker=binpath/'docker'
 docker.write_text('#!'+sys.executable+'\nimport os,sys\ni=sys.argv.index("-c")+1\nsys.argv[i]=sys.argv[i].replace("os.execvp(sys.argv[3],sys.argv[3:])", "__import__(\'time\').sleep(30); os.execvp(sys.argv[3],sys.argv[3:])")\nos.execvp(sys.argv[5],sys.argv[5:])\n');docker.chmod(0o755)
 env=dict(os.environ,PATH=str(binpath)+os.pathsep+os.environ['PATH'],AGILEX_CONTAINER_ROOT=str(temp));env.pop('AGILEX_LOCK_FD',None)
 with mock.patch.object(bench,'ROOT',temp),mock.patch.object(owned_process,'ROOT',temp),mock.patch.dict(os.environ,env,clear=True):
  proc=owned_process.OwnedContainerProcess([sys.executable,'-c','import time;time.sleep(30)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   deadline=time.monotonic()+3
   while time.monotonic()<deadline:
    try:record=json.loads(proc.record.read_text());break
    except ValueError:time.sleep(.01)
   else:raise RuntimeError('No published ownership record')
   print('Owned wrapper has published its record; exec is deliberately delayed.',flush=True)
   try:proc.close()
   except owned_process.OwnedProcessError as exc:
    print('REPRODUCED: early cancellation incorrectly rejects its own pre-exec wrapper.\n'+str(exc),flush=True)
   else:raise RuntimeError('Expected original startup race was not reproduced')
  finally:
   if proc.proc.poll() is None:proc.proc.terminate();proc.proc.wait(timeout=5)
