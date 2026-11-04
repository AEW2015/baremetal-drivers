"""Check CC identity decoding and the actual host Tcl capture guards."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import unittest

HERE = Path(__file__).resolve().parents[1] / 'cc-probe'
spec = importlib.util.spec_from_file_location('cc_probe_reader', HERE/'read.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

class Decode(unittest.TestCase):
    def test_role_requires_complete_verified_identity(self):
        values = [0x32,0x32,0x33,0x42,0x53,0x55,0x54,0,0,0x60,0x20]
        log = '\n'.join(f'CC_REGISTER reg=0x{i:02x} value=0x{v:02x}' for i,v in enumerate(values))
        with self.assertRaises(ValueError):reader.decode(log)
        log += '\nCC_PROBE_CAPTURE_COMPLETE'
        self.assertEqual(reader.decode(log)['attached_state'], 'DFP/source')
        self.assertEqual(reader.decode(log)['configured_mode'], 'DFP/source')
        self.assertEqual(reader.decode(log.replace('reg=0x09 value=0x60','reg=0x09 value=0x80'))['attached_state'], 'UFP/sink')
        with self.assertRaises(ValueError):reader.decode(log.replace('reg=0x00 value=0x32','reg=0x00 value=0xff'))

@unittest.skipUnless(shutil.which('tclsh'), 'Tcl interpreter required')
class Capture(unittest.TestCase):
    def invoke(self, mode):
        script = r'''
set mode MODE
set control 0
set started 0
set polls 0
set toggles 0
set bytes {50 50 51 66 83 85 84 0 0 96 32}
proc after {args} {}
proc echo {message} {puts $message}
proc hps.sys_bus {method address width argument} {
    global mode control started polls toggles bytes
    if {$method eq {write_memory}} {
        if {$address != 0x20010080 || $width != 32} {error {Unexpected mutation}}
        set next [lindex $argument 0]
        if {($control ^ $next) & (1 << 31)} {incr toggles;set started 1}
        set control $next
        return
    }
    if {$address == 0x10d1102c} {return [list [expr {$mode eq {bridge-reset} ? 2 : 0}]]}
    if {$address == 0x20010080} {return [list $control]}
    if {$address != 0x20010070} {error {Unexpected read}}
    if {$mode eq {wrong-image}} {return [list 0]}
    set index [expr {($control >> 4) & 15}]
    set byte [expr {$index == 15 ? 204 : [lindex $bytes $index]}]
    set status [expr {0xc0000 | $byte}]
    if {$started} {
        incr polls
        if {$polls == 1 && $mode ne {stale-done}} {return [list [expr {$status | (1<<30)}]]}
        set status [expr {$status | (1<<31)}]
        if {$mode eq {nack}} {set status [expr {$status | (1<<26)}]}
    }
    return [list $status]
}
if {[catch {source SCRIPT} reason]} {puts "ERROR $reason"}
puts "TOGGLES $toggles"
'''.replace('MODE',mode).replace('SCRIPT','{'+(HERE/'read.tcl').as_posix()+'}')
        return subprocess.check_output(['tclsh'],input=script,text=True)

    def test_one_read_trigger_and_no_target_configuration_writes(self):
        output=self.invoke('normal')
        self.assertIn('TOGGLES 1',output)
        self.assertEqual(reader.decode(output)['attached_state'],'DFP/source')

    def test_wrong_image_or_reset_bridge_gets_no_trigger(self):
        for mode in ('wrong-image','bridge-reset'):
            output=self.invoke(mode)
            self.assertIn('TOGGLES 0',output)
            self.assertNotIn('CC_PROBE_CAPTURE_COMPLETE',output)

    def test_nack_or_stale_completion_never_qualifies_registers(self):
        for mode in ('nack','stale-done'):
            output=self.invoke(mode)
            self.assertNotIn('CC_REGISTER',output)
            with self.assertRaises(ValueError):reader.decode(output)

if __name__ == '__main__':unittest.main()
