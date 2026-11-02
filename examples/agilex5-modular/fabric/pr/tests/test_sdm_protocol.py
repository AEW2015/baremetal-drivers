"""Compile the production transport against a fake SDM register bank."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

class SdmProtocol(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'host C compiler unavailable')
    def test_transport_and_preconditions(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'sdm-test'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(Path(__file__).with_name('sdm_protocol_test.c')),
                            '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True, timeout=5)

if __name__ == '__main__':
    unittest.main()
