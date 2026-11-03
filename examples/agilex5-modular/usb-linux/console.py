#!/usr/bin/env python3
"""Run a bounded diagnostic on Linux left running by the USB lab; no reboot."""
import argparse
import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import sys
import termios
import time

from run import ROOT,prompt_seen,sha
from bench import validate_uart
from hardware_lock import HardwareLock

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diagnostic',choices=('report','dmesg','uptime','flash','mouse','network','usb-network'))
    parser.add_argument('--port',default=os.environ.get('AGILEX_UART',''))
    parser.add_argument('--usb-peer',default=os.environ.get('AGILEX_USB_PEER',''))
    args=parser.parse_args()
    validate_uart(args.port)
    if args.diagnostic=='usb-network':
        if not args.usb_peer or not ipaddress.IPv4Address(args.usb_peer).is_private:
            parser.error('USB network test requires --usb-peer on the private test LAN')
    commands={'report':'/bin/usb-lab','dmesg':'dmesg','uptime':'cat /proc/uptime',
              'flash':'/bin/usb-flash-read','mouse':'/bin/usb-mouse-read',
              'network':'ip link show; ip addr show',
              'usb-network':'/bin/usb-net-test '+args.usb_peer}
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=ROOT/'runs'/('usb-linux-console-'+stamp);out.mkdir(parents=True)
    result={'scope':'Live Agilex Linux UART diagnostic; no programming or reboot',
            'diagnostic':args.diagnostic,'status':'running','linux_left_running':None,
            'limits':'A successful inventory/status command does not qualify absent USB devices',
            'console_source_sha256':sha(Path(__file__)),
            'shared_runner_sha256':sha(Path(__file__).with_name('run.py'))}
    def save():(out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    def receive(fd,budget,label):
        data=b'';last=time.monotonic();deadline=last+budget
        try:
            while time.monotonic()<deadline:
                if select.select([fd],[],[],.1)[0]:
                    try:chunk=os.read(fd,65536)
                    except BlockingIOError:continue
                    if not chunk:raise RuntimeError('SOM UART disconnected')
                    data+=chunk;last=time.monotonic()
                    if len(data)>4*1024*1024:raise RuntimeError('UART capture exceeded bound')
                if prompt_seen(data,True) and time.monotonic()-last>.2:return data
            raise RuntimeError('USB Linux prompt did not return; capture bytes='+str(len(data)))
        finally:(out/(label+'-uart.txt')).write_bytes(data)
    print('Evidence:',out,flush=True);save()
    with HardwareLock():
        fd=os.open(args.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        old=termios.tcgetattr(fd)
        try:
            settings=termios.tcgetattr(fd)
            settings[0]=settings[1]=settings[3]=0
            settings[2]=termios.CS8|termios.CREAD|termios.CLOCAL
            settings[4]=settings[5]=termios.B115200
            settings[6][termios.VMIN]=settings[6][termios.VTIME]=0
            termios.tcsetattr(fd,termios.TCSANOW,settings)
            termios.tcflush(fd,termios.TCIFLUSH)
            os.write(fd,b'\r');receive(fd,10,'prompt')
            identity="tr '\\000' '\\n' < /proc/device-tree/compatible; uname -r"
            os.write(fd,identity.encode()+b'\r')
            data=receive(fd,10,'identity')
            if not re.search(rb'(?m)^(?:intel|altr),[^\r\n]*agilex5',data.replace(b'\r',b'')):
                raise RuntimeError('Console does not identify Agilex 5 Linux; diagnostic not sent')
            command=commands[args.diagnostic]+"; printf '\\nUSB_CONSOLE_STATUS=%s\\n' \"$?\""
            os.write(fd,command.encode()+b'\r')
            data=receive(fd,60,'diagnostic')
            body=data.decode(errors='replace').replace('\r','')
            print(body,flush=True)
            status=re.findall(r'(?m)^USB_CONSOLE_STATUS=(\d+)$',body)
            result['guest_returncode']=int(status[-1]) if status else None
            result['status']='pass' if result['guest_returncode']==0 else 'partial'
            result['linux_left_running']=True
            marker={'report':'USB_LAB_TOPOLOGY_END','flash':'USB_FLASH_READ_PASS',
                    'usb-network':'USB_ETH_PING_PASS'}.get(args.diagnostic)
            if marker and not re.search(r'(?m)^'+marker+r'(?: |$)',body):result['status']='partial'
            if args.diagnostic=='mouse' and not re.search(r'(?m)^[0-9a-f]{7,8}\s+[0-9a-f]{4}\s',body):
                result['status']='partial';result['mouse_report']='no fresh reports'
        except BaseException as error:
            result['status']='fail';result['error']=repr(error);raise
        finally:
            try:termios.tcsetattr(fd,termios.TCSANOW,old)
            finally:os.close(fd);save()
    return int(result['status']!='pass')

if __name__=='__main__':raise SystemExit(main())
