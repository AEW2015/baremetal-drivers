"""Reject completion-only and weak upstream example diagnostics."""
import importlib.util
from pathlib import Path
import unittest
path=Path(__file__).resolve().parents[1]/'upstream-lab/run.py'
spec=importlib.util.spec_from_file_location('upstream_examples',path)
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

class UpstreamExamples(unittest.TestCase):
    prefix='UPSTREAM_LAB_BEGIN case=0\n'
    suffix='\nUPSTREAM_LAB_COMPLETE status=0\n'

    def test_crc_requires_four_successful_cases(self):
        good=self.prefix+'passed   : 4 case(s)\n  failed   : 0 case(s)'+self.suffix
        self.assertEqual(lab.assess('crc',good,0),'pass')
        self.assertEqual(lab.assess('crc',good.replace('4 case','3 case'),0),'fail')
        self.assertEqual(lab.assess('crc',self.prefix+self.suffix,0),'fail')

    def test_memory_requires_independent_full_readback(self):
        body=self.prefix+'[PERF] mem-copy: bytes=131072 time=42 us'+self.suffix
        self.assertEqual(lab.assess('perf',body,0),'fail')
        body=body.replace(self.suffix,'\nPASS PERF_MEMORY_READBACK words=16384 mismatches=0'+self.suffix)
        self.assertEqual(lab.assess('perf',body,0),'pass')
        self.assertEqual(lab.assess('perf',body.replace('mismatches=0','mismatches=1'),0),'fail')

    def test_reboot_return_is_not_reset_evidence(self):
        self.assertEqual(lab.assess('reboot',self.prefix+'Reboot Manager Example Done'+self.suffix,0),'fail')

    def test_iossm_zero_events_do_not_qualify_error_injection(self):
        body=self.prefix+'All 8 words match.\nECC error count after SBE injection: 0'+self.suffix
        self.assertEqual(lab.assess('iossm',body,0),'partial')

    def test_model_exit_zero_without_completion_is_failure(self):
        self.assertEqual(lab.assess('crc',self.prefix+'Device in Reset',0),'fail')
        self.assertEqual(lab.assess('perf',self.prefix+self.suffix,124),'timeout')

    def test_fault_and_unsupported_paths_are_distinct(self):
        body=self.prefix+'Combo PHY base is not defined for this platform build.'+self.suffix
        self.assertEqual(lab.assess('combophy',body,0),'unsupported')
        body=self.prefix+'Combo PHY version=0x1234 features=0x0001\nFAIL EXCEPTION'+self.suffix
        self.assertEqual(lab.assess('combophy',body,0),'fail')
