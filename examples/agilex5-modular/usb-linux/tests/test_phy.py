"""Exercise the actual Tcl transaction script with a memory-AP test double."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('usb_phy_runner',ROOT/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

@unittest.skipUnless(shutil.which('tclsh'),'Tcl interpreter required')
class ViewportTransactions(unittest.TestCase):
    def run_script(self,mode):
        script=r'''
set mode MODE
set selected -1
set writes {}
set polls 0
proc after {args} {}
proc echo {text} {puts $text}
proc hps.sys_bus {method address width argument} {
    global mode selected writes polls
    if {$method eq "write_memory"} {
        if {$address != 0x1100c280 || $width != 32} {error "Unexpected write target"}
        set request [lindex $argument 0]
        if {$request & (1 << 22)} {error "PHY configuration write requested"}
        set selected [expr {($request >> 16) & 63}]
        lappend writes $selected
        return
    }
    switch [format %x $address] {
        1100c120 {return [list 0x33313100]}
        1100c200 {return [list 0x10]}
        1100c14c {return [list 8]}
        1100c280 {
            if {$mode eq "busy"} {return [list 0x00800000]}
            if {$selected < 0} {return [list 0]}
            if {$mode eq "timeout"} {incr polls; return [list 0x02000000]}
            set values {0 36 1 4 2 7 3 0 10 6 19 22}
            return [list [expr {0x01000000 | [dict get $values $selected]}]]
        }
    }
    error "Unexpected read target"
}
if {[catch {source SCRIPT} reason]} {puts "ERROR $reason"}
puts "WRITES $writes"
puts "POLLS $polls"
'''.replace('MODE',mode).replace('SCRIPT','{'+str(ROOT/'phy-status.tcl')+'}')
        return subprocess.check_output(['tclsh'],input=script,text=True)

    def test_completed_reads_exclude_latches_and_never_write_phy_configuration(self):
        output=self.run_script('normal')
        self.assertIn('WRITES 0 1 2 3 10 19',output)
        decoded=runner.phy_status(output)
        self.assertTrue(decoded['vbus_valid_sample'])
        self.assertTrue(decoded['id_grounded_sample'])
        self.assertEqual(decoded['typec_role'],'not measured')
        self.assertNotIn('id_role_sample_qualified',decoded)

    def test_outstanding_request_is_not_overwritten(self):
        output=self.run_script('busy')
        self.assertIn('ERROR USB PHY diagnostic: outstanding viewport request',output)
        self.assertIn('WRITES \n',output)
        self.assertNotIn('USB_PHY_STATUS_COMPLETE',output)

    def test_timeout_stops_after_one_request_and_100_polls(self):
        output=self.run_script('timeout')
        self.assertIn('ERROR USB PHY diagnostic: bounded read timeout',output)
        self.assertIn('WRITES 0\n',output)
        self.assertIn('POLLS 100\n',output)
        with self.assertRaisesRegex(ValueError,'Incomplete'):runner.phy_status(output)

if __name__=='__main__':unittest.main()
