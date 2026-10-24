from pathlib import Path
import json,os,sys,tempfile,time
from unittest import mock
root=Path('/home/lada/altera-agilex/home/baremetal-drivers-aew2015/examples/agilex5-modular');sys.path.insert(0,str(root))
import bench,owned_process
base=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='process-check-',dir=base) as folder:
 temp=Path(folder);container='/home/dev/baremetal-remote-audit-evidence/'+temp.name
 with mock.patch.object(bench,'ROOT',temp),mock.patch.object(owned_process,'ROOT',temp),mock.patch.dict(os.environ,{'AGILEX_CONTAINER':'agilex-xrdp','AGILEX_CONTAINER_USER':'dev','AGILEX_CONTAINER_ROOT':container}):
  for i in range(3):
   proc=owned_process.OwnedContainerProcess(['python3','-c','import time;time.sleep(30)'])
   try:
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
     try:record=json.loads(proc.record.read_text());break
     except ValueError:time.sleep(.01)
    else:raise RuntimeError('Record did not become ready')
    proc.close();assert not proc.record.exists();assert proc.poll() is not None
    print(f'PASS REAL_DOCKER_CANCEL {i+1}: exact PID {record["pid"]} stopped; ownership record removed',flush=True)
   finally:
    if proc.poll() is None:proc.close()
  output=owned_process.run_owned(['python3','-c','print("OWNED_REMOTE_OK")'])
  assert 'OWNED_REMOTE_OK' in output
  assert not list(temp.glob('.agilex-process-*'))
  print('PASS REAL_DOCKER_COMPLETION: captured output; verified remote exit; no ownership records')
