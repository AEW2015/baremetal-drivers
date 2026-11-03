"""Hotplug messages must not turn a completed command into a console timeout."""
import importlib.util
from pathlib import Path
import sys
import unittest

directory=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(directory))
spec=importlib.util.spec_from_file_location('usb_linux_runner',directory/'run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ConsoleCompletion(unittest.TestCase):
    def test_prompt_survives_asynchronous_scsi_message(self):
        self.assertTrue(m.prompt_seen(b'/bin/usb-lab\r\nUSB_LINUX# [6.38] sd [sda] Attached disk\r\n',True))
        self.assertTrue(m.prompt_seen(b'USB_LINUX# ',True))
        self.assertFalse(m.prompt_seen(b'echo USB_LINUX# \r\n',True))
        self.assertFalse(m.prompt_seen(b'USB_LINUX_READY\r\n',True))

    def test_only_a_completed_responsive_linux_run_may_skip_restoration(self):
        live={'status':'partial','linux_ready':True}
        self.assertTrue(m.can_leave_linux(live,True,False,False))
        self.assertFalse(m.can_leave_linux(live,False,False,False))
        self.assertFalse(m.can_leave_linux(live,True,True,False))
        self.assertFalse(m.can_leave_linux(live,True,False,True))
        self.assertFalse(m.can_leave_linux({'status':'fail','linux_ready':True},True,False,False))
        self.assertFalse(m.can_leave_linux({'status':'running','linux_ready':True},True,False,False))
        self.assertFalse(m.can_leave_linux({'status':'partial','linux_ready':False},True,False,False))

if __name__=='__main__':unittest.main()
