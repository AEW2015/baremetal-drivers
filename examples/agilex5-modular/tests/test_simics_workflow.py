"""Regressions for observed Simics false-success and cancellation failures."""
import importlib.util
from pathlib import Path
import subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simics'))
from run import assess
from legacy import assess_legacy
from support import execute

class SimicsWorkflow(unittest.TestCase):
    def test_model_stop_with_exit_zero_does_not_pass(self):
        body='Device in Reset: Access to Device in Reset is restricted!\n'
        self.assertFalse(assess_legacy(body,0)[0])
        self.assertFalse(assess(body,'Hello, Baremetal World!',0)[0])

    def test_console_breakpoint_uart_address_is_not_guest_success(self):
        body='Reached exit\nSIMICS_TEST_RETURN\n0x10c02000\n'
        self.assertFalse(assess_legacy(body,0)[0])
        self.assertEqual(assess_legacy(body,0)[1],0x10c02000)

    def test_actual_guest_result_and_completion_required(self):
        self.assertTrue(assess_legacy('Reached exit\nSIMICS_TEST_RETURN\n0x0\n',0)[0])
        self.assertFalse(assess_legacy('Reached exit\nSIMICS_TEST_RETURN\n0x1\n',1)[0])
        self.assertFalse(assess_legacy('SIMICS_TEST_RETURN\n0x0\n',0)[0])

    def test_generic_command_completion_is_not_selftest_success(self):
        body='SIMICS_UPSTREAM_READY\nSIMICS_UPSTREAM_COMPLETE\nUART_RECORD_BEGIN\nRESULT : command completed - CHECK DETAILED OUTPUT\nUART_RECORD_END\n'
        self.assertFalse(assess(body,'RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED',0)[0])
        good=body.replace('RESULT : command completed - CHECK DETAILED OUTPUT','RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED')
        self.assertTrue(assess(good,'RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED',0)[0])
        self.assertFalse(assess(good.replace('SIMICS_UPSTREAM_COMPLETE',''),'RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED',0)[0])

    def test_timeout_reaps_only_owned_process_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);pid=root/'pid';fake=root/'simics'
            fake.write_text('#!'+sys.executable+'\nimport os,time,pathlib\npathlib.Path('+repr(str(pid))+').write_text(str(os.getpid()))\nprint("partial model output",flush=True)\ntime.sleep(30)\n');fake.chmod(0o755)
            other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
            try:
                code,_,body=execute(root,root/'unused.simics',root/'terminal.log',1)
                self.assertEqual(code,124);self.assertIn('partial model output',body)
                self.assertIsNone(other.poll())
                with self.assertRaises(ProcessLookupError):__import__('os').kill(int(pid.read_text()),0)
            finally:other.terminate();other.wait(timeout=5)
