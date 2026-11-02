"""Select current release images/debugger while retaining legacy bench compatibility."""
import os,subprocess,sys
from pathlib import Path
from bench import ROOT,bootstrap_image_path,container_command,container_path
class StackBench:
 def __init__(self,bench):
  self.bench=Path(bench);self.current=bool(os.environ.get('AGILEX_BOOTSTRAP_DIR'))
 @property
 def image(self):
  return bootstrap_image_path('ddr_probe.hps.rbf') if self.current else self.bench/'ddr-bringup/ddr_probe.hps.rbf'
 @property
 def cfg(self):return container_path(ROOT/'bootstrap/ocram/agilex5.cfg') if self.current else '/home/dev/baremetal-guide-validation/ocram/agilex5.cfg'
 def payload(self,name):
  folder=ROOT/'build/bench-transfers' if self.current else self.bench/'examples/build'
  folder.mkdir(parents=True,exist_ok=True);return folder/name
 def remote(self,path):return container_path(path) if self.current else '/home/dev/baremetal-guide-validation/examples/build/'+Path(path).name
 def command(self,args):return container_command(args) if self.current else ['docker','exec','agilex-xrdp',*args]
 def bootstrap(self,port,lock_fd,full=False):
  script=ROOT/'bootstrap/ddr/run_ddr.py' if self.current else self.bench/'ddr-bringup/run_ddr.py'
  args=[sys.executable,str(script),'--port',port]+(['--full-recovery'] if full else [])
  options={}
  if self.current:options={'env':dict(os.environ,AGILEX_LOCK_FD=str(lock_fd)),'pass_fds':(lock_fd,)}
  return subprocess.run(args,capture_output=True,timeout=400,**options)
