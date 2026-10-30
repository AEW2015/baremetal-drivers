"""Reject misleading configuration snapshot completions and corrupted captures."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'config-audit/run.py'
spec=importlib.util.spec_from_file_location('config_audit',path)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class ConfigAudit(unittest.TestCase):
    good=('CONFIG_AUDIT_BEGIN pinmux\nPIN2SEL0x0000000000000005\n'
          'PIN3SEL0x0000000000000005\nUART0_USEFPGA0x0000000000000000\n'
          'PASS READ_ONLY_SNAPSHOT registers=3\nCONFIG_AUDIT_COMPLETE status=0\n')

    def test_complete_capture_and_rejections(self):
        self.assertEqual(audit.assess('pinmux',self.good,0),'pass')
        for body in (self.good.replace('PIN2SEL0x0000000000000005\n',''),
                     self.good+'PIN2SEL0x0000000000000005\n',
                     self.good.replace('0000000000000005','00000000ffffffff'),
                     self.good.replace('status=0','status=1'),
                     self.good+'CONFIG_AUDIT_COMPLETE status=1\n',
                     self.good.replace('0000000000000005','0000000100000005'),
                     self.good+'FAIL EXCEPTION\n',
                     'CONFIG_AUDIT_COMPLETE status=0\n'):
            self.assertEqual(audit.assess('pinmux',body,0),'fail')
        self.assertEqual(audit.assess('pinmux',self.good,124),'fail')

    def test_negative_control_requires_observed_failure(self):
        self.assertEqual(audit.assess('unstable',self.good,0),'fail')
        bad=self.good.replace('PASS READ_ONLY_SNAPSHOT registers=3',
                              'FAIL UNSTABLE_OR_UNAVAILABLE PIN2SEL').replace('status=0','status=1')
        self.assertEqual(audit.assess('unstable',bad,0),'pass')
        self.assertEqual(audit.assess('pinmux',bad,0),'fail')
