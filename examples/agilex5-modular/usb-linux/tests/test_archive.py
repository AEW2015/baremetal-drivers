import gzip
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('usb_linux_prepare',Path(__file__).resolve().parents[1]/'prepare.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RamArchive(unittest.TestCase):
 def test_console_node_symlink_and_binary_survive_newc_alignment(self):
  expected=[('dev/console',0o020600,b'',5,1),('bin/sh',0o120777,b'busybox',0,0),('bin/data',0o100600,b'a\0b\xff',0,0)]
  packed=m.archive(expected);self.assertEqual(packed,m.archive(expected))
  data=gzip.decompress(packed);offset=0;actual=[]
  while True:
   self.assertEqual(data[offset:offset+6],b'070701')
   fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
   name=data[offset+110:offset+110+fields[11]-1].decode()
   offset=(offset+110+fields[11]+3)&~3
   payload=data[offset:offset+fields[6]];offset=(offset+fields[6]+3)&~3
   if name=='TRAILER!!!':break
   actual.append((name,fields[1],payload,fields[9],fields[10]))
  self.assertEqual(actual,expected)
if __name__=='__main__':unittest.main()
