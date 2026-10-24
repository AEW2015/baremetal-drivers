"""Hermetic student-failure regressions. Default tests never contact hardware.

Optional AGILEX_TEST_REAL_QEMU=1 runs the real emulator/compiler in temp copies.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bench
from bench import BenchError
from hardware_lock import HardwareLock
import run_suite
import owned_process
from owned_process import OwnedContainerProcess, OwnedProcessError
import time

class StudentFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'qemu').mkdir()
        shutil.copy2(ROOT/'qemu/run.py', self.root/'qemu/run.py')
        (self.root/'build/qemu').mkdir(parents=True)
        (self.root/'build/qemu/hello.elf').write_bytes(b'fixture-not-executed')
        self.env = dict(os.environ)
        self.env.pop('AGILEX_LOCK_FD', None)

    def tool(self, body):
        tool = self.root/'fake-qemu'
        tool.write_text('#!'+sys.executable+'\n'+body+'\n')
        tool.chmod(0o755)
        return str(tool)

    def run_qemu(self, *args, tool=None):
        env = dict(self.env, QEMU=tool or '/missing/qemu-for-student-test')
        return subprocess.run([sys.executable, str(self.root/'qemu/run.py'), *args], env=env,
                              capture_output=True, text=True, timeout=8)

    def assert_friendly_failure(self, result, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stdout+result.stderr)
        self.assertNotIn('Traceback', result.stdout+result.stderr)

    def test_missing_emulator_is_actionable(self):
        self.assert_friendly_failure(self.run_qemu('--check'), 'Install qemu-system-arm in THIS environment')

    def test_missing_elf_points_to_build(self):
        (self.root/'build/qemu/hello.elf').unlink()
        self.assert_friendly_failure(self.run_qemu('--check'), './qemu/build.sh')

    def test_occupied_port_never_launches_or_claims_ready(self):
        marker = self.root/'launched'
        tool = self.tool(f'from pathlib import Path\nPath({str(marker)!r}).write_text("launched")')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            port = listener.getsockname()[1]
            result = self.run_qemu('--debug', '--port', str(port), tool=tool)
            self.assert_friendly_failure(result, 'Cannot reserve GDB port')
            self.assertFalse(marker.exists())
            self.assertNotIn('QEMU GDB ready', result.stdout)
            self.assertEqual(listener.getsockname()[1], port)

    def test_check_rejects_missing_markers_even_on_exit_zero(self):
        self.assert_friendly_failure(self.run_qemu('--check', tool=self.tool('print("hello only")')), 'missing markers')

    def test_nonzero_exit_preserves_diagnostic(self):
        result = self.run_qemu('--check', tool=self.tool('print("emulator diagnostic"); raise SystemExit(7)'))
        self.assert_friendly_failure(result, 'exit 7')
        self.assertIn('emulator diagnostic', result.stdout)

    def test_timeout_preserves_partial_output_and_reaps_child(self):
        pidfile = self.root/'child.pid'
        tool = self.tool(f'import os,time\nfrom pathlib import Path\nPath({str(pidfile)!r}).write_text(str(os.getpid()))\nprint("partial boot",flush=True)\ntime.sleep(30)')
        result = self.run_qemu('--check', '--timeout', '.2', tool=tool)
        self.assert_friendly_failure(result, 'timed out')
        self.assertIn('partial boot', result.stdout)
        with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()), 0)

    def test_inherited_lock_does_not_unlock_parent(self):
        path = self.root/'hardware.lock'
        code = 'import sys;sys.path.insert(0,sys.argv[1]);from hardware_lock import HardwareLock;\nwith HardwareLock(sys.argv[2]): print("owned")'
        cmd = [sys.executable, '-c', code, str(ROOT), str(path)]
        with HardwareLock(path) as lock:
            child = subprocess.run(cmd, capture_output=True, text=True, **lock.child_options())
            self.assertEqual(child.returncode, 0, child.stderr)
            outsider = subprocess.run(cmd, env=self.env, capture_output=True, text=True)
            self.assertNotEqual(outsider.returncode, 0)
            self.assertIn('Hardware is busy', outsider.stderr)
        released = subprocess.run(cmd, env=self.env, capture_output=True, text=True)
        self.assertEqual(released.returncode, 0, released.stderr)

    def test_direct_bootstrap_respects_debugger_lock_before_docker(self):
        for name in ['bench.py', 'hardware_lock.py', 'owned_process.py']:
            shutil.copy2(ROOT/name, self.root/name)
        target = self.root/'bootstrap/ddr';target.mkdir(parents=True)
        shutil.copy2(ROOT/'bootstrap/ddr/run_ddr.py', target/'run_ddr.py')
        with HardwareLock(self.root/'hardware.lock'):
            result = subprocess.run([sys.executable, str(target/'run_ddr.py'), '--port', '/dev/null'],
                                    env=self.env, capture_output=True, text=True, timeout=5)
        self.assert_friendly_failure(result, 'Hardware is busy')

    def test_mount_nonce_rejects_another_clone_and_is_cleaned(self):
        fakebin = self.root/'bin';fakebin.mkdir()
        docker = fakebin/'docker'
        docker.write_text('#!'+sys.executable+'\nimport os,sys\nos.execvp(sys.argv[5],sys.argv[5:])\n')
        docker.chmod(0o755)
        host = self.root/'host';host.mkdir()
        other = self.root/'another-clone';other.mkdir()
        env = dict(self.env, PATH=str(fakebin)+os.pathsep+self.env['PATH'], AGILEX_CONTAINER_ROOT=str(other))
        with mock.patch.object(bench, 'ROOT', host), mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(BenchError, 'mapping is not verified'):bench.verify_mount()
            self.assertFalse(list(host.glob('.agilex-mount-*')))
            os.environ['AGILEX_CONTAINER_ROOT'] = str(host)
            bench.verify_mount()
            self.assertFalse(list(host.glob('.agilex-mount-*')))

    def fake_docker(self):
        fakebin = self.root/'fake-docker-bin';fakebin.mkdir()
        docker = fakebin/'docker'
        docker.write_text('#!'+sys.executable+'\nimport os,sys\nos.execvp(sys.argv[5],sys.argv[5:])\n')
        docker.chmod(0o755)
        return dict(self.env, PATH=str(fakebin)+os.pathsep+self.env['PATH'], AGILEX_CONTAINER_ROOT=str(self.root))

    def wait_for_record(self, proc):
        deadline = time.monotonic()+3
        while time.monotonic()<deadline:
            try:return json.loads(proc.record.read_text())
            except ValueError:time.sleep(.02)
        self.fail('owned process record not created')

    def test_owned_container_cancellation_preserves_unrelated_process(self):
        env = self.fake_docker()
        outsider = subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        try:
            with mock.patch.object(bench,'ROOT',self.root), mock.patch.object(owned_process,'ROOT',self.root), mock.patch.dict(os.environ,env,clear=True):
                proc=OwnedContainerProcess([sys.executable,'-c','import time;time.sleep(30)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                record=self.wait_for_record(proc)
                proc.close()
                self.assertIsNotNone(proc.poll())
                self.assertFalse(proc.record.exists())
                self.assertIsNone(outsider.poll())
        finally:outsider.terminate();outsider.wait(timeout=5)

    def test_cancellation_before_exec_has_initial_ownership_token(self):
        env = self.fake_docker()
        docker = self.root/'fake-docker-bin/docker'
        docker.write_text('#!'+sys.executable+'\n'
                          'import os,sys\n'
                          'i=sys.argv.index("-c")+1\n'
                          'sys.argv[i]=sys.argv[i].replace("os.execvp(sys.argv[3],sys.argv[3:])", '
                          '"__import__(\'time\').sleep(30); os.execvp(sys.argv[3],sys.argv[3:])")\n'
                          'os.execvp(sys.argv[5],sys.argv[5:])\n')
        with mock.patch.object(bench,'ROOT',self.root), mock.patch.object(owned_process,'ROOT',self.root), mock.patch.dict(os.environ,env,clear=True):
            proc = OwnedContainerProcess([sys.executable,'-c','import time;time.sleep(30)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                self.wait_for_record(proc)
                proc.close()
                self.assertIsNotNone(proc.poll())
                self.assertFalse(proc.record.exists())
            finally:
                if proc.poll() is None:
                    proc.proc.terminate();proc.proc.wait(timeout=5)

    def test_owned_container_refuses_a_pid_with_wrong_ownership_token(self):
        env=self.fake_docker()
        outsider=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        try:
            with mock.patch.object(bench,'ROOT',self.root), mock.patch.object(owned_process,'ROOT',self.root), mock.patch.dict(os.environ,env,clear=True):
                proc=OwnedContainerProcess([sys.executable,'-c','import time;time.sleep(30)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                record=self.wait_for_record(proc)
                try:
                    proc.record.write_text(json.dumps({'pid':outsider.pid,'token':record['token']}))
                    with self.assertRaises(OwnedProcessError):proc.close()
                    self.assertIsNone(outsider.poll())
                finally:
                    proc.record.write_text(json.dumps(record));proc.close()
        finally:outsider.terminate();outsider.wait(timeout=5)

    def test_exited_transport_still_checks_remote_ownership(self):
        proc = object.__new__(OwnedContainerProcess)
        proc.proc = mock.Mock()
        proc.proc.poll.return_value = 1
        proc.record = self.root/"ownership-record"
        proc.record.write_text("record")
        proc.signal_owned = mock.Mock()
        proc.close()
        proc.signal_owned.assert_called_once_with(15)
        self.assertFalse(proc.record.exists())

    def test_disconnected_transport_kills_owned_process_ignoring_term(self):
        env = self.fake_docker()
        token = 'student-test-owner'
        ready = self.root/'ready'
        code = f'import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path({str(ready)!r}).touch();time.sleep(30)'
        remote = subprocess.Popen([sys.executable,'-c',code],env=dict(self.env,AGILEX_RUN_OWNER=token))
        try:
            deadline=time.monotonic()+3
            while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(ready.exists())
            proc=object.__new__(OwnedContainerProcess)
            proc.proc=mock.Mock();proc.proc.poll.return_value=1
            proc.record=self.root/'.agilex-process-disconnected'
            proc.record.write_text(json.dumps({'pid':remote.pid,'token':token}))
            proc.token=token
            with mock.patch.dict(os.environ,env,clear=True):proc.close()
            self.assertEqual(remote.wait(timeout=2),-9)
            self.assertFalse(proc.record.exists())
        finally:
            if remote.poll() is None:remote.kill();remote.wait()

    def test_unresolved_record_blocks_new_hardware_owner(self):
        (self.root/'.agilex-process-uncertain').write_text('preserved evidence')
        with self.assertRaisesRegex(BenchError, 'Unresolved hardware process record'):
            with HardwareLock(self.root/'hardware.lock'):pass

    def test_regular_file_is_not_a_uart(self):
        with self.assertRaisesRegex(BenchError, 'not a serial TTY'):bench.validate_uart(self.root/'build/qemu/hello.elf')

    def test_restore_timeout_is_durable_and_preserves_original_error(self):
        results = {'error': 'original example error', 'restoration': 'pending'}
        with mock.patch.object(run_suite, 'run_bootstrap', side_effect=subprocess.TimeoutExpired('fixture', .1)), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            run_suite.restore_ddr(self.root, results, '/not-opened', object())
        saved = json.loads((self.root/'results.json').read_text())
        self.assertEqual(saved['restoration'], 'error')
        self.assertEqual(saved['error'], 'original example error')
        self.assertIn('TimeoutExpired', saved['restoration_error'])
        self.assertIn('RESTORATION ERROR', (self.root/'restore.log').read_text())

    def test_uncertain_process_shutdown_prevents_reprogramming(self):
        results = {'restoration': 'pending'}
        with mock.patch.object(run_suite, 'run_bootstrap') as bootstrap, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            run_suite.restore_ddr(self.root, results, '/not-opened', object(), skip=True)
        bootstrap.assert_not_called()
        self.assertEqual(json.loads((self.root/'results.json').read_text())['restoration'], 'error')

@unittest.skipUnless(os.environ.get('AGILEX_TEST_REAL_QEMU') == '1', 'set AGILEX_TEST_REAL_QEMU=1 for compiler/emulator tests')
class RealQemuExercise(unittest.TestCase):
    def test_positive_and_deliberate_neon_failure_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT/'qemu', root/'qemu', ignore=shutil.ignore_patterns('__pycache__'))
            subprocess.run(['bash', str(root/'qemu/build.sh')], check=True, capture_output=True)
            cmd = [sys.executable, str(root/'qemu/run.py'), '--check']
            good = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.assertEqual(good.returncode, 0, good.stdout+good.stderr)
            source = root/'qemu/hello.c'
            source.write_text(source.read_text().replace('vector_b[4]={10,20,30,40}', 'vector_b[4]={11,20,30,40}'))
            subprocess.run(['bash', str(root/'qemu/build.sh')], check=True, capture_output=True)
            bad = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn('FAIL NEON', bad.stdout)
            self.assertIn('PASS MEMORY: 4096-byte CPU copy', bad.stdout)
            self.assertNotIn('FAIL MEMORY', bad.stdout)
            self.assertIn('QEMU EXAMPLE FAILED', bad.stdout)

if __name__ == '__main__':unittest.main(verbosity=2)
