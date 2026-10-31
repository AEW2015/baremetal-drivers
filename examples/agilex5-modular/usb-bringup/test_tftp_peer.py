"""Loopback-only TFTP tests; no USB or board qualification."""
import importlib.util,socket,struct,threading,unittest
from pathlib import Path
p=Path(__file__).with_name('tftp_peer.py');spec=importlib.util.spec_from_file_location('usb_tftp',p)
tftp=importlib.util.module_from_spec(spec);spec.loader.exec_module(tftp)

class PeerTests(unittest.TestCase):
    def exercise(self,size):
        data=tftp.payload(size);result={}
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
            server.bind(('127.0.0.1',0));address=server.getsockname()
            def serve():result.update(tftp.transfer(server,data,'127.0.0.1',5))
            thread=threading.Thread(target=serve);thread.start()
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
                client.settimeout(2)
                # Write requests and arbitrary filenames must not be served.
                client.sendto(b'\0\2usb-demo.bin\0octet\0',address)
                self.assertEqual(client.recvfrom(2048)[0][:2],b'\0\5')
                client.sendto(b'\0\1../secret\0octet\0',address)
                self.assertEqual(client.recvfrom(2048)[0][:2],b'\0\5')
                client.sendto(b'\0\1'+b'\0'.join([b'usb-demo.bin',b'octet',b'blksize',b'1468',b'']),address)
                received=b'';number=1
                while True:
                    packet,peer=client.recvfrom(2048)
                    self.assertEqual(packet[:4],struct.pack('!HH',3,number))
                    received+=packet[4:];client.sendto(struct.pack('!HH',4,number),peer)
                    if len(packet)<516:break
                    number+=1
                self.assertEqual(received,data)
            thread.join(2);self.assertFalse(thread.is_alive())
        self.assertEqual(result['bytes'],size)
        self.assertEqual(result['blocks'],size//512+1)

    def test_exact_block_boundary_has_final_empty_packet(self):self.exercise(1024)
    def test_short_final_packet_and_read_only_rejections(self):self.exercise(777)
