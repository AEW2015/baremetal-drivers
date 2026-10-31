#!/usr/bin/env python3
"""Bounded, read-only TFTP peer serving one generated RAM-test payload only."""
import argparse,hashlib,ipaddress,json,socket,struct,time

FILENAME='usb-demo.bin'
def payload(size=1048576):return hashlib.shake_256(b'Agilex 5 USB Ethernet read-only RAM demo v1').digest(size)

def transfer(listener,data,peer_ip,timeout=60,retries=5):
    """Serve one RRQ from the explicit board IP; ignore requested RFC options.

    DATA block 1 without OACK selects the standard 512-byte fallback. No WRQ
    or filesystem paths are accepted; received network data is never saved.
    """
    start=time.monotonic();deadline=start+timeout
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('No valid board TFTP request before deadline')
        listener.settimeout(min(1,remaining))
        try:request,peer=listener.recvfrom(2048)
        except socket.timeout:continue
        if peer[0]!=peer_ip:continue
        parts=request[2:].split(b'\0')
        if len(request)<4 or request[:2]!=b'\0\1' or len(parts)<3 or parts[0]!=FILENAME.encode() or parts[1].lower()!=b'octet':
            listener.sendto(b'\0\5\0\2Only the generated read-only payload is available\0',peer)
            continue
        break
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as stream:
        stream.bind((listener.getsockname()[0],0))
        blocks=0
        for offset in range(0,len(data)+1,512):
            if offset==len(data) and len(data)%512:break
            block=(blocks+1)&0xffff;chunk=data[offset:offset+512]
            packet=struct.pack('!HH',3,block)+chunk;ack=struct.pack('!HH',4,block)
            for attempt in range(retries):
                if time.monotonic()>=deadline:raise TimeoutError('TFTP transfer deadline exceeded')
                stream.sendto(packet,peer);stream.settimeout(min(.8,max(.01,deadline-time.monotonic())))
                try:reply,source=stream.recvfrom(2048)
                except socket.timeout:continue
                if source==peer and reply==ack:break
            else:raise TimeoutError('Missing valid ACK for block '+str(block))
            blocks+=1
            if len(chunk)<512:break
    return {'scope':'PC-side acknowledged TFTP transfer; board RAM hash must be checked separately',
            'peer':peer[0],'filename':FILENAME,'bytes':len(data),'blocks':blocks,
            'sha256':hashlib.sha256(data).hexdigest(),'seconds':time.monotonic()-start}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind',required=True,help='Dedicated PC wired IPv4 address, not 0.0.0.0')
    p.add_argument('--peer',default='192.168.50.3')
    p.add_argument('--port',type=int,default=69)
    p.add_argument('--timeout',type=int,default=120)
    p.add_argument('--bytes',type=int,default=1048576)
    a=p.parse_args()
    if not ipaddress.ip_address(a.bind).is_private or a.bind=='0.0.0.0':p.error('Bind to the dedicated private PC interface')
    ipaddress.IPv4Address(a.peer)
    if not 1<=a.port<=65535 or not 5<=a.timeout<=300 or not 512<=a.bytes<=1048576:p.error('Invalid bounded port/timeout/payload size')
    data=payload(a.bytes)
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as listener:
        listener.bind((a.bind,a.port))
        print('TFTP_READY '+json.dumps({'bind':a.bind,'port':a.port,'peer':a.peer,'filename':FILENAME,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}),flush=True)
        result=transfer(listener,data,a.peer,a.timeout)
        print('TFTP_COMPLETE '+json.dumps(result,sort_keys=True),flush=True)

if __name__=='__main__':main()
