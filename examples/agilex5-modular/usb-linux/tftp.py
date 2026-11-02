"""Read-only, bounded TFTP server for three explicit RAM-boot artifacts."""
import hashlib
import socket
import struct
import threading
import time

class Server:
    def __init__(self, bind, peer, files, port=1069, timeout=600):
        if set(files)!={'Image','initramfs.cpio.gz','board.dtb'}:
            raise ValueError('Only the three RAM-boot artifacts may be served')
        if any(not 0<len(value)<=48*1024*1024 for value in files.values()):
            raise ValueError('Artifact size outside the RAM-boot bound')
        self.files=files;self.peer=peer;self.events=[];self.errors=[]
        self.deadline=time.monotonic()+timeout;self.stop=threading.Event()
        self.listener=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.listener.bind((bind,port));self.port=self.listener.getsockname()[1]
        self.listener.settimeout(.2)
        self.thread=threading.Thread(target=self.run,daemon=True)

    def __enter__(self):self.thread.start();return self
    def __exit__(self,*args):
        self.stop.set();self.thread.join(2);self.listener.close()

    def acknowledged(self,stream,peer,packet,block):
        for attempt in range(5):
            if self.stop.is_set() or time.monotonic()>self.deadline:
                raise TimeoutError('TFTP session ended')
            stream.sendto(packet,peer)
            deadline=time.monotonic()+.8
            while time.monotonic()<deadline:
                stream.settimeout(max(.01,deadline-time.monotonic()))
                try:reply,address=stream.recvfrom(2048)
                except socket.timeout:break
                if address==peer and reply==struct.pack('!HH',4,block):return
        raise TimeoutError('No valid TFTP ACK for block '+str(block))

    def transfer(self,request,peer):
        fields=request[2:].split(b'\0')
        if request[:2]!=b'\0\1' or len(fields)<3 or fields[1].lower()!=b'octet':
            raise ValueError('Only octet RRQ is supported')
        name=fields[0].decode('ascii')
        if name not in self.files:raise ValueError('Artifact is not allowed')
        data=self.files[name];options={}
        for i in range(2,len(fields)-1,2):
            if fields[i]:options[fields[i].lower()]=fields[i+1]
        blocksize=512;accepted=[]
        if b'blksize' in options:
            blocksize=min(1468,max(8,int(options[b'blksize'])))
            accepted += [b'blksize',str(blocksize).encode()]
        if b'tsize' in options:accepted += [b'tsize',str(len(data)).encode()]
        start=time.monotonic();blocks=0
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as stream:
            stream.bind((self.listener.getsockname()[0],0))
            if accepted:self.acknowledged(stream,peer,b'\0\6'+b'\0'.join(accepted)+b'\0',0)
            for offset in range(0,len(data)+1,blocksize):
                chunk=data[offset:offset+blocksize];blocks+=1
                packet=struct.pack('!HH',3,blocks&0xffff)+chunk
                self.acknowledged(stream,peer,packet,blocks&0xffff)
                if len(chunk)<blocksize:break
        self.events.append({'name':name,'bytes':len(data),'blocks':blocks,
                            'sha256':hashlib.sha256(data).hexdigest(),'seconds':time.monotonic()-start})

    def run(self):
        while not self.stop.is_set() and time.monotonic()<self.deadline:
            try:request,peer=self.listener.recvfrom(2048)
            except socket.timeout:continue
            except OSError:break
            if peer[0]!=self.peer:continue
            try:self.transfer(request,peer)
            except (ValueError,UnicodeError) as error:
                self.listener.sendto(b'\0\5\0\2Only reviewed RAM-boot artifacts are available\0',peer)
                self.errors.append(str(error))
            except (OSError,TimeoutError) as error:
                if not self.stop.is_set():self.errors.append(str(error))
