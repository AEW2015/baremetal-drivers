"""Exercise interruption/connection failures without any board or Docker access."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('discovery_hardware', ROOT/'upstream-lab/hardware.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class DiscoveryRecovery(unittest.TestCase):
    def exercise(self, stage):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'bench/examples').mkdir(parents=True)
            artifacts = root/'artifacts'
            artifacts.mkdir()
            hashes = {}
            for name in ('crc.elf', 'crc.bin'):
                (artifacts/name).write_bytes(b'fixture')
                hashes[name] = hashlib.sha256(b'fixture').hexdigest()
            (artifacts/'build.json').write_text(json.dumps({'artifacts':hashes}))
            image = root/'image'
            image.write_bytes(b'fixture')
            stack = MagicMock(image=image)
            client = MagicMock()
            client.call.return_value = {'text':'0364F0DD 4BA06477'}
            factory = MagicMock(return_value=client)
            if stage == 'connect':
                factory.side_effect = RuntimeError('connection failed')
            elif stage == 'discovery':
                client.call.side_effect = KeyboardInterrupt()
            else:
                stack.bootstrap.side_effect = [KeyboardInterrupt(), subprocess.CompletedProcess([],0,b'restored',b'')]
            args = ['hardware.py','--only','crc','--bench',str(root/'bench'),
                    '--artifacts',str(artifacts),'--mcp-client',str(root/'mcp_client.py')]
            expected = RuntimeError if stage == 'connect' else KeyboardInterrupt
            with patch.object(runner,'ROOT',root), patch.object(runner,'StackBench',return_value=stack), \
                 patch.dict(sys.modules,{'mcp_client':types.SimpleNamespace(MCP=factory)}), \
                 patch.object(sys,'argv',args), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(expected):
                    runner.main()
            record = json.loads(next((root/'runs').glob('*/results.json')).read_text())
            mutex = json.loads(next((root/'runs').glob('*/mutex.json')).read_text())
            self.assertEqual(mutex['state'],'released')
            # The lock is released even if MCP startup itself fails.
            import fcntl
            with (root/'bench/examples/hardware.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if stage in ('connect','discovery'):
                stack.bootstrap.assert_not_called()
                self.assertEqual(record['restoration'],'not required; no bootstrap or payload attempted')
            else:
                self.assertEqual(stack.bootstrap.call_count,2)
                self.assertEqual(record['restoration'],'pass')
                self.assertTrue(record['bootstrap_attempted'])
            if stage != 'connect':
                client.close.assert_called_once()

    def test_connection_failure_releases_mutex_without_programming(self):
        self.exercise('connect')

    def test_discovery_interrupt_does_not_attempt_board_restoration(self):
        self.exercise('discovery')

    def test_interrupt_after_bootstrap_attempt_still_restores(self):
        self.exercise('bootstrap')
