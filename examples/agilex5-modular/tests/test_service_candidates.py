"""Security denial cannot masquerade as full FCS pass; ECC stays read-only scope."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('service_oracle_test',ROOT/'service-candidates/oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
PREFIX='''SERVICE_BEGIN name=fcs EL=2
SERVICE_FCS_API init rc=0
PASS FCS_REAL_INIT
SERVICE_FCS_API chip rc=0 hi=0x12345678 lo=0x23456789
PASS FCS_REAL_CHIP_ID_DATA
SERVICE_FCS_API jtag rc=0 value=0x0364f0dd
PASS FCS_REAL_MODULAR_JTAG_ID
SERVICE_FCS_API deinit rc=0
PASS FCS_REAL_DEINIT
PASS FCS_REAL_CALL_SEQUENCE
'''
FULL=PREFIX+'''SERVICE_FCS_API open rc=0
PASS FCS_REAL_SESSION_UUID
SERVICE_FCS_BYTES uuid count=16 hex=00112233445546778899aabbccddeeff
SERVICE_FCS_API rng rc=0 context=0xc0ffee01 uuid_matches=1 size=16
SERVICE_FCS_BYTES rng count=16 hex=12345678123456781234567812345678
PASS FCS_REAL_RNG_DATA
SERVICE_FCS_API close rc=0 uuid_matches=1
PASS FCS_REAL_SESSION_CLOSED
SERVICE_FCS_SUMMARY init=1 chip=1 jtag=1 open=1 rng=1 close=1 deinit=1 provision=0 denied=0
=== FCS demo: 7/7 step(s) PASS ===
SERVICE_COMPLETE status=0
'''
DENIED=PREFIX+'''SERVICE_FCS_API open rc=-5
SERVICE_PARTIAL FCS_SDM_SECURITY_DENIED_0x85
SERVICE_FCS_API get_provision rc=-5 bytes=1024 (read-only)
PASS FCS_READONLY_PROVISION_RESULT
SERVICE_FCS_SUMMARY init=1 chip=1 jtag=1 open=1 rng=0 close=0 deinit=1 provision=1 denied=1
=== FCS demo: 4/4 step(s) PASS (1 expected security skip(s)) ===
SERVICE_COMPLETE status=0
'''
class ServiceSafety(unittest.TestCase):
 def test_full_pass_requires_real_data_and_lifecycle(self):
  self.assertEqual(oracle.assess('fcs',FULL,0),'pass')
  self.assertEqual(oracle.assess('fcs',FULL.replace('0x0364f0dd','0x0364F0DD').replace('0xc0ffee01','0xC0FFEE01').replace('00112233445546778899aabbccddeeff','00112233445546778899AABBCCDDEEFF'),0),'pass')
  self.assertEqual(oracle.assess('fcs',FULL.replace('00112233445546778899aabbccddeeff','00000000000040008000000000000000'),0),'fail')
  for before,after in [('hex=12345678123456781234567812345678','hex='+'0'*32),('value=0x0364f0dd','value=0x00000000'),('close rc=0 uuid_matches=1','close rc=0 uuid_matches=0'),('deinit=1 provision=0','deinit=0 provision=0')]:
   with self.subTest(before=before):self.assertEqual(oracle.assess('fcs',FULL.replace(before,after),0),'fail')
 def test_security_denial_is_only_partial_with_valid_identity_cleanup(self):
  self.assertEqual(oracle.assess('fcs',DENIED,0),'partial')
  self.assertEqual(oracle.assess('fcs',DENIED.replace('get_provision rc=-5','get_provision rc=-1'),0),'fail')
  self.assertEqual(oracle.assess('fcs',DENIED.replace('hi=0x12345678 lo=0x23456789','hi=0x00000000 lo=0x00000000'),0),'fail')
 def test_summary_alone_and_debugger_error_rejected(self):
  self.assertEqual(oracle.assess('fcs','SERVICE_BEGIN name=fcs EL=2\n=== FCS demo: 7/7 step(s) PASS ===\nSERVICE_COMPLETE status=0\n',0),'fail')
  self.assertEqual(oracle.assess('fcs',FULL,1),'fail')
 def test_ecc_snapshot_is_partial_and_requires_matching_raw_values(self):
  text='SERVICE_BEGIN name=ecc-readonly EL=3\nSERVICE_ECC_READONLY SERR=0x00000000 DERR=0x00000000 RAW_SERR=0x00000000 RAW_DERR=0x00000000\nPASS ECC_READONLY_API_RAW_AGREE\nSERVICE_PARTIAL ECC_STATUS_ONLY_NO_INIT_CLEAR_OR_INJECTION\nSERVICE_COMPLETE status=0\n'
  self.assertEqual(oracle.assess('ecc-readonly',text,0),'partial')
  self.assertEqual(oracle.assess('ecc-readonly',text.replace('RAW_DERR=0x00000000','RAW_DERR=0x00000001'),0),'fail')
 def test_service_boot_profiles_rejected_before_hardware_access(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)
   base=[sys.executable,str(ROOT/'upstream-lab/hardware.py'),'--suite','services','--bench',str(p/'missing-bench'),'--artifacts',str(p/'missing-artifacts'),'--mcp-client',str(p/'missing-mcp.py')]
   for extra,expected in [(['--only','fcs'],'FCS services require resident BL31'),(['--only','ecc-readonly','--bl31',str(p/'missing-bl31')],'ECC read-only snapshot requires standalone EL3')]:
    result=subprocess.run(base+extra,capture_output=True,text=True)
    self.assertEqual(result.returncode,2,result.stderr);self.assertIn(expected,result.stderr)
   self.assertFalse((p/'missing-bench').exists())
if __name__=='__main__':unittest.main()
