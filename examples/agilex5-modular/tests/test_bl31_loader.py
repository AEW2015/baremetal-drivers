"""Run the generated Tcl with a stub AP and reject misleading OpenOCD exits."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bl31_loader',ROOT/'upstream-lab/hardware.py')
hardware=importlib.util.module_from_spec(spec);spec.loader.exec_module(hardware)

class Bl31Loader(unittest.TestCase):
 def tcl(self,failing=False,malformed=False):
  # All commands are local Tcl stubs, with a vendor-shaped descriptive CSW.
  report='no readable AP CSW' if malformed else 'AP#0x4000 selected, csw 0xa2000000'
  stub='''proc init {} {}
proc halt {} {}
proc targets {args} {}
proc shutdown {} {}
proc hps.dap {args} {
 if {[lindex $args 0] eq "apsel"} {return}
 if {[llength $args] == 1} {return "REPORT"}
 puts "CSW_SET=[lindex $args 1]"
}
proc load_image {args} {BODY}
proc dump_image {args} {puts "DUMP_COMPLETED"}
'''.replace('REPORT',report).replace('BODY','error "injected load failure"' if failing else 'puts "LOAD_COMPLETED"')
  code=stub+hardware.bl31_load_script('init; halt; ','/tmp/owned-monitor.bin',4)
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'load.tcl';p.write_text(code)
   return subprocess.run(['tclsh',str(p)],capture_output=True,text=True)
 @unittest.skipUnless(shutil.which('tclsh'),'Tcl interpreter unavailable')
 def test_descriptive_csw_is_decoded_and_exact_value_restored(self):
  r=self.tcl();self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('CSW_SET=0x10000000',r.stdout)
  self.assertIn('CSW_SET=0xa2000000',r.stdout)
  self.assertIn('DUMP_COMPLETED',r.stdout)
  self.assertIn('BL31_LOAD_READBACK_COMPLETE',r.stdout)
 @unittest.skipUnless(shutil.which('tclsh'),'Tcl interpreter unavailable')
 def test_failed_transfer_restores_csw_and_never_prints_completion(self):
  r=self.tcl(failing=True);self.assertNotEqual(r.returncode,0)
  self.assertIn('CSW_SET=0xa2000000',r.stdout)
  self.assertNotIn('DUMP_COMPLETED',r.stdout)
  self.assertNotIn('BL31_LOAD_READBACK_COMPLETE',r.stdout)
 @unittest.skipUnless(shutil.which('tclsh'),'Tcl interpreter unavailable')
 def test_malformed_csw_stops_before_secure_writes(self):
  r=self.tcl(malformed=True);self.assertNotEqual(r.returncode,0)
  self.assertNotIn('CSW_SET=',r.stdout)
  self.assertNotIn('LOAD_COMPLETED',r.stdout)
 def test_exit_zero_error_or_missing_marker_or_bad_readback_cannot_pass(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'readback';p.write_bytes(b'good')
   def result(body,code=0):return subprocess.CompletedProcess([],code,body,b'')
   marker=b'BL31_LOAD_READBACK_COMPLETE\n'
   self.assertTrue(hardware.bl31_readback_valid(result(marker),p,b'good'))
   for body,code in [(marker+b'Error: invalid CSW\n',0),(b'',0),(marker,1)]:
    self.assertFalse(hardware.bl31_readback_valid(result(body,code),p,b'good'))
   self.assertFalse(hardware.bl31_readback_valid(result(marker),p,b'other'))
   p.unlink();self.assertFalse(hardware.bl31_readback_valid(result(marker),p,b'good'))

if __name__=='__main__':unittest.main()
