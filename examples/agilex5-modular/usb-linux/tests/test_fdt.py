import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('usb_linux_prepare_fdt',Path(__file__).resolve().parents[1]/'prepare.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@unittest.skipUnless(all(shutil.which(x) for x in ('dtc','fdtget','fdtput')),'device-tree compiler tools required')
class DeviceTreeProperties(unittest.TestCase):
 def test_driver_match_and_status_are_nul_terminated_strings(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);source=root/'board.dts';blob=root/'board.dtb'
   source.write_text('/dts-v1/; / { usb { }; };\n')
   subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(blob),str(source)],check=True)
   for name,value in (('compatible','snps,dwc3'),('status','okay'),('dr_mode','host')):
    m.fdt(blob,'/usb',name,value)
    actual=subprocess.check_output(['fdtget','-t','s',str(blob),'/usb',name],text=True).strip()
    self.assertEqual(actual,value)
   m.fdt(blob,'/usb','snps,dis_u3_susphy_quirk')
   self.assertEqual(subprocess.check_output(['fdtget','-t','bx',str(blob),'/usb','snps,dis_u3_susphy_quirk'],text=True).strip(),'')
if __name__=='__main__':unittest.main()
