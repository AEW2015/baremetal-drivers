import importlib.util
from pathlib import Path
import socket
import struct
import unittest
spec=importlib.util.spec_from_file_location('usb_linux_tftp',Path(__file__).resolve().parents[1]/'tftp.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Transfers(unittest.TestCase):
 def test_binary_transfer_with_negotiation_and_exact_final_block(self):
  files={'Image':bytes(range(256))*8,'initramfs.cpio.gz':b'ram','board.dtb':b'dtb'}
  with m.Server('127.0.0.1','127.0.0.1',files,port=0,timeout=5) as server:
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
    client.settimeout(2)
    client.sendto(b'\0\1'+b'\0'.join([b'Image',b'octet',b'blksize',b'1024',b'tsize',b'0'])+b'\0',('127.0.0.1',server.port))
    data=bytearray()
    while True:
     packet,peer=client.recvfrom(2048);op,block=struct.unpack('!HH',packet[:4])
     if op==5:continue
     if op==6:client.sendto(b'\0\4\0\0',peer);continue
     self.assertEqual(op,3);data.extend(packet[4:]);client.sendto(struct.pack('!HH',4,block),peer)
     if len(packet[4:])<1024:break
    self.assertEqual(bytes(data),files['Image'])
 def test_writes_and_path_traversal_are_rejected(self):
  files={'Image':b'i','initramfs.cpio.gz':b'r','board.dtb':b'd'}
  with m.Server('127.0.0.1','127.0.0.1',files,port=0,timeout=5) as server:
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
    client.settimeout(2)
    for packet in (b'\0\2Image\0octet\0',b'\0\1../Image\0octet\0'):
     client.sendto(packet,('127.0.0.1',server.port));response,_=client.recvfrom(2048)
     self.assertEqual(response[:4],b'\0\5\0\2')
if __name__=='__main__':unittest.main()
