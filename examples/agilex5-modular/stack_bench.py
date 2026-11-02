"""Repository-owned tool/image mapping; historical bench arguments are no longer required."""
import os
from pathlib import Path
import subprocess
import sys
from bench import ROOT, bootstrap_directory, bootstrap_image_path, container_command, container_path


class StackBench:
    def __init__(self, bench=None):
        # Keep the old CLI argument parseable, but never require or execute an
        # external checkout's scripts. All active assets belong to this clone.
        self.bench = ROOT/'build/bench'
        (self.bench/'examples').mkdir(parents=True,exist_ok=True)
        self.current = True

    @property
    def lock_path(self):
        path = Path(os.environ.get('AGILEX_HARDWARE_LOCK',ROOT/'hardware.lock'))
        path.parent.mkdir(parents=True,exist_ok=True)
        return path

    @property
    def image(self):
        return bootstrap_image_path('ddr_probe.hps.rbf')

    @property
    def cfg(self):
        return container_path(ROOT/'bootstrap/ocram/agilex5.cfg')

    def payload(self,name):
        folder = ROOT/'build/bench-transfers'
        folder.mkdir(parents=True,exist_ok=True)
        return folder/name

    def remote(self,path):
        return container_path(path)

    def command(self,args):
        return container_command(args)

    def bootstrap(self,port,lock_fd,full=False):
        args = [sys.executable,str(ROOT/'bootstrap/ddr/run_ddr.py'),'--port',port]
        if full:args.append('--full-recovery')
        return subprocess.run(args,capture_output=True,timeout=400,
            env=dict(os.environ,AGILEX_LOCK_FD=str(lock_fd),
                AGILEX_BOOTSTRAP_DIR=str(bootstrap_directory()),
                AGILEX_MCP_CLIENT=os.environ.get('AGILEX_MCP_CLIENT',str(ROOT/'mcp_client.py'))),
            pass_fds=(lock_fd,))
