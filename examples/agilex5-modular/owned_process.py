"""Stop only a container process launched for this run, not unrelated tools."""
import json
import os
import pathlib
import signal
import subprocess
import tempfile
import time
from bench import BenchError, ROOT, checked_container, container_command, container_path

class OwnedProcessError(BenchError):
    """Remote process cancellation could not be confirmed; do not reprogram."""

class OwnedContainerProcess:
    def __init__(self, args, **kwargs):
        fd, name = tempfile.mkstemp(prefix='.agilex-process-', dir=ROOT)
        os.close(fd)
        self.record = pathlib.Path(name)
        self.token = os.urandom(24).hex()
        self.closed = False
        code = ('import json,os,pathlib,sys; '
                'os.environ["AGILEX_RUN_OWNER"]=sys.argv[2]; '
                'pathlib.Path(sys.argv[1]).write_text(json.dumps({"pid":os.getpid(),"token":sys.argv[2]})); '
                'os.execvp(sys.argv[3],sys.argv[3:])')
        try:
            self.proc = subprocess.Popen(container_command(['python3', '-c', code,
                container_path(self.record), self.token, *args]), **kwargs)
        except BaseException:
            self.record.unlink(missing_ok=True)
            raise

    @property
    def returncode(self):
        return self.proc.returncode

    def poll(self):
        return self.proc.poll()

    def wait(self, timeout=None):
        return self.proc.wait(timeout=timeout)

    def signal_owned(self, signum):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                record = json.loads(self.record.read_text())
                break
            except (OSError, ValueError):
                time.sleep(.05)
        else:
            raise OwnedProcessError(f'Cannot identify the owned container process. Keep {self.record}; do not start another hardware operation until its state is checked.')
        if record.get('token') != self.token:
            raise OwnedProcessError('Container process ownership record changed; automatic cancellation refused.')
        # The token is inherited through the Quartus/OpenOCD exec wrapper.
        # Check it in /proc before signaling the exact PID; never kill a group,
        # JTAG daemon, or every process with a matching executable name.
        code = '''import os,pathlib,signal,sys,time
pid=int(sys.argv[1]); token=('AGILEX_RUN_OWNER='+sys.argv[2]).encode()
permission_retries=0
def active():
 global permission_retries
 try:
  state=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
  if state == 'Z': return False
  current=pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\\0')
 except FileNotFoundError: return False
 except PermissionError:
  try: state=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
  except FileNotFoundError: return False
  if state in ('Z','X'): return False
  permission_retries += 1
  if permission_retries > 20: raise
  time.sleep(.05)
  return active()
 if state in ('Z','X'): return False
 if not any(current) and permission_retries < 20:
  permission_retries += 1
  time.sleep(.05)
  return active()
 if token not in current: raise SystemExit('PID ownership changed; no further signal sent')
 return True
for sig,seconds in ((int(sys.argv[3]),3),(signal.SIGKILL,3)):
 if not active(): raise SystemExit(0)
 try: os.kill(pid,sig)
 except ProcessLookupError: raise SystemExit(0)
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  if not active(): raise SystemExit(0)
  time.sleep(.05)
raise SystemExit('Owned PID still active after bounded termination; keep record')
'''
        try:
            checked_container(['python3', '-c', code, str(record['pid']), self.token, str(signum)], timeout=10)
        except BenchError as exc:
            raise OwnedProcessError(f'Could not confirm cancellation of the owned process; keep {self.record}. {exc}') from exc

    def close(self):
        if getattr(self, "closed", False):
            return
        try:
            # A disconnected Docker CLI does not prove its container child exited.
            self.signal_owned(signal.SIGTERM)
            if self.proc.poll() is None:
                try:
                    self.proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    self.signal_owned(signal.SIGKILL)
                    self.proc.wait(timeout=5)
        except (BenchError, subprocess.TimeoutExpired) as exc:
            raise OwnedProcessError(f'Hardware process shutdown is not verified: {exc}') from exc
        else:
            self.record.unlink(missing_ok=True)
            self.closed = True


def run_owned(args, timeout=30):
    """Capture a short hardware command and verify its remote cleanup on all exits."""
    with tempfile.TemporaryFile() as log:
        proc = OwnedContainerProcess(args, stdout=log, stderr=subprocess.STDOUT)
        try:
            rc = proc.wait(timeout=timeout)
            log.seek(0)
            output = log.read().decode(errors='replace')
            if rc:
                raise BenchError(f'Hardware command exited {rc}: {output}')
            return output
        finally:
            proc.close()
