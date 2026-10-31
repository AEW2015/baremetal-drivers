"""PSCI cannot pass without actual context/identity and CPU_OFF affinity proof."""
import importlib.util
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('psci_test_oracle',ROOT/'reference/psci/oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
VALID='''PSCI_BEGIN target_mpidr=0x100 context=0x5053434943545854
PSCI_PRIMARY_EL=2
PASS PSCI_PRIMARY_EL2_CACHE_OFF_CORE0
PSCI_VERSION=0x10001
PSCI_FEATURE id=0xc4000003 result=0
PSCI_FEATURE id=0x84000002 result=0
PSCI_FEATURE id=0xc4000004 result=0
PSCI_INITIAL_AFFINITY=1
PSCI_CPU_ON_RESULT=0
PASS PSCI_CPU_ON_SUCCESS
PASS PSCI_SECONDARY_RECORD_PUBLISHED
PSCI_SECONDARY context=0x5053434943545854 MIDR=0x41afd050 MPIDR=0x80000100 EL=2 SCTLR=0x30c50830 ENTRY=0x82400080 STACK=0x83ffaef0 FAULT=0
PASS PSCI_SECONDARY_IDENTITY_CONTEXT_AND_STACK
PSCI_FINAL_AFFINITY=1 OFF_ATTEMPT=1 OFF_RETURNED=0 OFF_RESULT=0
PASS PSCI_CPU_OFF_AFFINITY_CONFIRMED
PSCI_COMPLETE status=0
'''
class PSCISafety(unittest.TestCase):
 def test_requires_actual_records_and_off_affinity(self):
  self.assertEqual(oracle.assess('psci',VALID,0),'pass')
  for before,after in [('context=0x5053434943545854 MIDR','context=0x5053434943545855 MIDR'),('MPIDR=0x80000100','MPIDR=0x80000200'),('PSCI_FINAL_AFFINITY=1','PSCI_FINAL_AFFINITY=0'),('OFF_RETURNED=0','OFF_RETURNED=1'),('PSCI_CPU_ON_RESULT=0','PSCI_CPU_ON_RESULT=-4')]:
   with self.subTest(before=before):self.assertEqual(oracle.assess('psci',VALID.replace(before,after),0),'fail')
  self.assertEqual(oracle.assess('psci',VALID,124),'fail')
 def test_mixed_case_hex_keeps_all_identity_and_off_checks(self):
  mixed=re.sub(r'0x([0-9a-f]+)',lambda m:'0x'+m[1].upper(),VALID)
  self.assertEqual(oracle.assess('psci',mixed,0),'pass')
  self.assertEqual(oracle.assess('psci',mixed.replace('MIDR=0x41AFD050','MIDR=0x41AFD060'),0),'fail')
  self.assertEqual(oracle.assess('psci',mixed.replace('OFF_RETURNED=0','OFF_RETURNED=1'),0),'fail')
 def test_already_on_is_blocked_not_pass_and_cannot_mix_completion(self):
  text='PSCI_BEGIN target_mpidr=0x100 context=0x5053434943545854\nBLOCKED PSCI reason=CPU_ON_ALREADY_ON code=-4\nPSCI_COMPLETE status=2\n'
  self.assertEqual(oracle.assess('psci',text,0),'blocked')
  self.assertEqual(oracle.assess('psci',text+'PSCI_COMPLETE status=0\n',0),'fail')
 def test_missing_bl31_rejected_before_hardware(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)
   result=subprocess.run([sys.executable,str(ROOT/'upstream-lab/hardware.py'),'--suite','psci','--bench',str(p/'missing-bench'),'--artifacts',str(p/'missing-artifacts'),'--mcp-client',str(p/'missing-mcp.py')],capture_output=True,text=True)
   self.assertEqual(result.returncode,2,result.stderr)
   self.assertIn('PSCI requires resident BL31',result.stderr)
   self.assertFalse((p/'missing-bench').exists())
if __name__=='__main__':unittest.main()
