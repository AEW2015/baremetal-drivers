"""Exercise mode plans and the actual Tcl write-interface rejection guards."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]/'cc-probe'
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('cc_mode_configure',HERE/'configure.py')
configure=importlib.util.module_from_spec(spec);spec.loader.exec_module(configure)

class ModePlans(unittest.TestCase):
    def test_attached_peer_and_readonly_image_are_rejected(self):
        for state in ('DFP/source','UFP/sink','accessory'):
            with self.assertRaises(RuntimeError):
                configure.require_unattached({'mode_writes_supported':True,'attached_state':state})
        with self.assertRaises(RuntimeError):
            configure.require_unattached({'mode_writes_supported':False,'attached_state':'unattached'})
        configure.require_unattached({'mode_writes_supported':True,'attached_state':'unattached'})

    def test_dfp_and_restore_keep_termination_disabled_during_mode_change(self):
        self.assertEqual(configure.plan('dfp',0),[1,2,3])
        self.assertEqual(configure.plan('default',0x20),[2,1,4])
        self.assertEqual(configure.plan('dfp',0x20),[])
        self.assertEqual(configure.plan('default',0),[])
        for value in (0x08,0x40,0x06,0x10):
            with self.assertRaises(ValueError):configure.plan('dfp',value)

@unittest.skipUnless(shutil.which('tclsh'),'Tcl interpreter required')
class WriteTransactions(unittest.TestCase):
    def run_script(self, capability, operation=2, bridge_reset=0):
        source=r'''
set cc_operation OPERATION
set capability CAPABILITY
set bridge_reset BRIDGE_RESET
set control 0
set toggles 0
proc echo {message} {puts $message}
proc after {args} {}
proc hps.sys_bus {method address width argument} {
    global control capability toggles bridge_reset
    if {$method eq {write_memory}} {
        if {$address != 0x20010080 || $width != 32} {error {Unexpected mutation}}
        set next [lindex $argument 0]
        if {($control ^ $next)&(1<<31)} {incr toggles}
        set control $next
        return
    }
    if {$address == 0x10d1102c} {return [list $bridge_reset]}
    if {$address == 0x20010080} {return [list $control]}
    if {$address != 0x20010070} {error {Unexpected read}}
    set status [expr {0xc00cc | ($capability<<15)}]
    if {$toggles} {
        set status [expr {$status | (1<<31) | ((($control>>31)&1)<<20) | ($control&1792)}]
    }
    return [list $status]
}
if {[catch {source SCRIPT} why]} {puts "ERROR $why"}
puts "TOGGLES $toggles"
puts "FINAL_COMMAND [expr {($control>>8)&7}]"
'''.replace('BRIDGE_RESET',str(bridge_reset)).replace('OPERATION',str(operation)).replace('CAPABILITY',str(capability)).replace('SCRIPT','{'+(HERE/'write.tcl').as_posix()+'}')
        return subprocess.check_output(['tclsh'],input=source,text=True)

    def test_readonly_image_or_invalid_command_gets_no_write_trigger(self):
        for capability,operation in ((0,2),(1,0),(1,5)):
            output=self.run_script(capability,operation)
            self.assertIn('TOGGLES 0',output)
            self.assertNotIn('CC_MODE_WRITE_COMPLETE',output)

    def test_reset_bridge_is_rejected_before_any_trigger(self):
        output=self.run_script(1,bridge_reset=2)
        self.assertIn('TOGGLES 0',output)
        self.assertNotIn('CC_MODE_WRITE_COMPLETE',output)

    def test_short_write_has_fresh_toggle_and_clears_command_without_retrigger(self):
        output=self.run_script(1)
        self.assertIn('TOGGLES 1',output)
        self.assertIn('FINAL_COMMAND 0',output)
        self.assertIn('CC_MODE_WRITE_COMPLETE',output)

if __name__=='__main__':unittest.main()
