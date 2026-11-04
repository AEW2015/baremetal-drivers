"""Run the actual root-port shell command against an isolated sysfs fixture."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('usb_console_power',HERE/'console.py')
console=importlib.util.module_from_spec(spec);spec.loader.exec_module(console)

class RoleGuard(unittest.TestCase):
    def test_only_a_successful_dfp_source_capture_permits_power_on(self):
        for role in ('unattached','UFP/sink','accessory'):
            with self.assertRaises(RuntimeError):console.require_dfp_source({'status':'pass','attached_state':role})
        with self.assertRaises(RuntimeError):console.require_dfp_source({'status':'fail','attached_state':'DFP/source'})
        console.require_dfp_source({'status':'pass','attached_state':'DFP/source'})

@unittest.skipUnless(shutil.which('sh'),'POSIX shell required')
class SysfsCommands(unittest.TestCase):
    def fixture(self,root,controller='11000000.usb'):
        base=root/controller/'devices';base.mkdir(parents=True)
        for bus,pid in ((1,'0002'),(2,'0003')):
            device=base/f'usb{bus}';device.mkdir()
            (device/'idVendor').write_text('1d6b\n');(device/'idProduct').write_text(pid+'\n')
            port=base/f'{bus}-0:1.0'/f'usb{bus}-port1';port.mkdir(parents=True)
            (port/'disable').write_text('0\n')
        return base

    def invoke(self,base,action):
        command=console.port_power_command(action).replace('/sys/bus/usb/devices',str(base))
        return subprocess.run(['sh','-c',command],capture_output=True,text=True)

    def states(self,base):
        return [(base/f'{b}-0:1.0'/f'usb{b}-port1'/'disable').read_text().strip() for b in (1,2)]

    def test_off_then_on_writes_both_ports_and_checks_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=self.fixture(Path(tmp))
            off=self.invoke(base,'off');self.assertEqual(off.returncode,0,off.stderr)
            self.assertEqual(self.states(base),['1','1'])
            self.assertIn('USB_PORT_POWER_COMPLETE',off.stdout)
            on=self.invoke(base,'on');self.assertEqual(on.returncode,0,on.stderr)
            self.assertEqual(self.states(base),['0','0'])

    def test_external_device_refuses_power_off_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=self.fixture(Path(tmp));external=base/'1-1';external.mkdir()
            (external/'idVendor').write_text('21c4\n')
            result=self.invoke(base,'off');self.assertNotEqual(result.returncode,0)
            self.assertIn('REFUSED_EXTERNAL_DEVICE',result.stdout)
            self.assertEqual(self.states(base),['0','0'])

    def test_wrong_controller_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=self.fixture(Path(tmp),'different-controller')
            result=self.invoke(base,'off');self.assertNotEqual(result.returncode,0)
            self.assertEqual(self.states(base),['0','0'])

if __name__=='__main__':unittest.main()
