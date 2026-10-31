"""Reject superficially successful upstream summaries and wrong-target loads."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('candidate_oracle',ROOT/'hardware-candidates/oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)

def transcript(name,content=''):
 return 'CANDIDATE_BEGIN name='+name+'\nPASS STANDALONE_EL3_MMU_DCACHE_OFF\n'+content+'\nCANDIDATE_COMPLETE status=0\n'

class CandidateSafety(unittest.TestCase):
 def test_completion_and_upstream_summary_are_not_sufficient(self):
  for name in oracle.NAMES:
   with self.subTest(name=name):
    self.assertEqual(oracle.assess(name,transcript(name,'RESULT : 3 of 3 tests passed  -  SELF-TEST PASSED'),0),'fail')
 def test_spi_unconditional_summary_cannot_hide_loopback_failure(self):
  body=transcript('spi','SPI0 version: 0x3430312a\nSPI loopback failed: -5\nPASS\nRESULT : 3 of 3 tests passed  -  SELF-TEST PASSED\nPASS SPI_API_256_LOOPBACK')
  self.assertEqual(oracle.assess('spi',body,0),'fail')
 def test_failed_debugger_or_duplicate_capture_rejected(self):
  body=transcript('hello','Hello, Baremetal World!')
  self.assertEqual(oracle.assess('hello',body,0),'pass')
  self.assertEqual(oracle.assess('hello',body,1),'fail')
  self.assertEqual(oracle.assess('hello',body+body,0),'fail')
 def test_qemu_candidate_metadata_rejected_before_bench_access(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);art=p/'artifacts';art.mkdir();(art/'build.json').write_text(json.dumps({'target':'qemu'}))
   r=subprocess.run([sys.executable,str(ROOT/'upstream-lab/hardware.py'),'--suite','candidates','--only','hello','--bench',str(p/'missing-bench'),'--artifacts',str(art),'--mcp-client',str(p/'missing-mcp.py')],capture_output=True,text=True)
   self.assertEqual(r.returncode,2,r.stderr)
   self.assertIn('never load QEMU-addressed artifacts',r.stderr)
   self.assertFalse((p/'missing-bench').exists())
 def test_group0_sgi_requires_group1_cpu_mask_readback(self):
  good='PASS GIC_REDISTRIBUTOR_POWER_READY\nGIC_GROUP1_CPU_CONTROL=0x0\nPASS GIC_GROUP1_CPU_DISABLED\nPASS (IRQ=1, count=1)\nRESULT : 2 of 2 tests passed  -  SELF-TEST PASSED'
  self.assertEqual(oracle.assess('gic',transcript('gic',good),0),'pass')
  for broken in [good.replace('GIC_GROUP1_CPU_CONTROL=0x0\n',''),
                 good.replace('PASS GIC_GROUP1_CPU_DISABLED\n',''),
                 good.replace('GIC_GROUP1_CPU_CONTROL=0x0','GIC_GROUP1_CPU_CONTROL=0x3'),
                 good+'\nGIC_GROUP1_CPU_CONTROL=0x0']:
   with self.subTest(broken=broken):
    self.assertEqual(oracle.assess('gic',transcript('gic',broken),0),'fail')


class CapturedCandidateParsing(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=json.loads((ROOT/'hardware-candidates/validation/oracle-fixtures.json').read_text())
  cls.captures=cls.fixture['captures']
 def body(self,name):return self.captures[name]['uart']
 def test_frozen_actual_captures_require_actual_markers_and_values(self):
  import hashlib
  for name,capture in self.captures.items():
   with self.subTest(name=name):
    self.assertEqual(hashlib.sha256(capture['uart'].encode()).hexdigest(),capture['uart_sha256'])
    self.assertEqual(oracle.assess(name,capture['uart'],capture['debug_exit']),'partial' if name=='spi' else 'pass')
 def test_truncation_duplicates_or_failed_debugger_never_pass(self):
  for name,capture in self.captures.items():
   body=capture['uart']
   with self.subTest(name=name):
    self.assertEqual(oracle.assess(name,body.split('CANDIDATE_COMPLETE')[0],0),'fail')
    self.assertEqual(oracle.assess(name,body+'\nCANDIDATE_BEGIN name='+name+'\n',0),'fail')
    self.assertEqual(oracle.assess(name,body,1),'fail')
 def test_dma_real_callback_fill_and_full_payload_checks_remain_mandatory(self):
  body=self.body('dma')
  for before,after in [('Callback fired : yes','Callback fired : no'),('mismatches=0','mismatches=1'),('All 256 bytes match 0xA5','All 256 bytes match 0xA4'),('PASS DMA_STRICT_CHANNEL_IDLE','MISSING DMA_STRICT_CHANNEL_IDLE')]:
   with self.subTest(before=before):self.assertEqual(oracle.assess('dma',body.replace(before,after),0),'fail')
 def test_gic_group1_disable_and_actual_irq_delivery_remain_mandatory(self):
  body=self.body('gic')
  for before,after in [('GIC_GROUP1_CPU_CONTROL=0x0','GIC_GROUP1_CPU_CONTROL=0x1'),('PASS GIC_GROUP1_CPU_DISABLED','MISSING GIC_GROUP1_CPU_DISABLED'),('IRQ=1, count=1','IRQ=1, count=0'),('Verify no ISR was invoked ................. PASS','Verify no ISR was invoked ................. FAIL (unexpected IRQ=2, count=1)')]:
   with self.subTest(before=before):self.assertEqual(oracle.assess('gic',body.replace(before,after),0),'fail')
 def test_timer_debug_lines_do_not_replace_five_actual_values(self):
  body=self.body('timer')
  import re
  final=re.search(r'Sample 5 of 5[^\n]*\n(\d+) us',body)[1]
  self.assertEqual(oracle.assess('timer',body.replace(final+' us','VALUE_MISSING'),0),'fail')
  stale=re.sub(r'(Sample \d of 5[^\n]*\n)\d+ us',r'\g<1>123 us',body)
  self.assertEqual(oracle.assess('timer',stale,0),'fail')
 def test_spi_successful_loopbacks_do_not_qualify_closed_status_phase(self):
  body=self.body('spi')
  self.assertEqual(oracle.assess('spi',body,0),'partial')
  for before,after in [('SPI0 loopback PASS (32 bytes, CS1)','SPI0 loopback MISSING'),('SPI_API_256 rc=0','SPI_API_256 rc=-5'),('SPI0 version: 0x3430302A','SPI0 version: 0xFFFFFFFF')]:
   with self.subTest(before=before):self.assertEqual(oracle.assess('spi',body.replace(before,after),0),'fail')

if __name__=='__main__':unittest.main()
