#!/usr/bin/env python3
"""Run on the host: program the HPS OCRAM image and verify physical UART output."""
import argparse,os,pathlib,re,select,subprocess,termios,time
root=pathlib.Path('/home/lada/altera-agilex/home/baremetal-remote-audit-0daff10/examples/agilex5-modular/bootstrap/ocram')
import sys
sys.path.insert(0,str(root.parents[1]))
from owned_process import run_owned
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--port',default='/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0')
a=p.parse_args()
def container(args):
    return run_owned(args,timeout=90)
chain=container(['jtagconfig'])
first=chain.split('2)')[0]
if not re.search(r'^1\) Agilex_5E MDK Carrier ',first,re.M):
    raise RuntimeError('Expected Agilex 5 carrier as cable 1')
ids=re.findall(r'^\s+([0-9A-Fa-f]{8})\s',first,re.M)
if '0364F0DD' not in ids: raise RuntimeError('Expected Modular ES FPGA absent')
index=ids.index('0364F0DD')+1
fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
try:
    v=termios.tcgetattr(fd);v[0]=v[1]=v[3]=0
    v[2]=termios.CS8|termios.CREAD|termios.CLOCAL
    v[4]=v[5]=termios.B115200
    v[6][termios.VMIN]=v[6][termios.VTIME]=0
    termios.tcsetattr(fd,termios.TCSANOW,v)
    termios.tcflush(fd,termios.TCIFLUSH)
    stamp=time.strftime('%Y%m%d-%H%M%S',time.gmtime())
    output=container(['quartus_pgm','-c','Agilex_5E MDK Carrier [1-4.2.1]','-m','jtag',
        '-o',f'p;/home/dev/baremetal-remote-audit-0daff10/examples/agilex5-modular/bootstrap/ocram/build/hello_uart.hps.rbf@{index}'])
    (root/'build'/f'program-uart-{stamp}.log').write_text(output)
    # Drain pre-programming bytes; require a fresh line from the running image.
    termios.tcflush(fd,termios.TCIFLUSH)
    data=b'';deadline=time.monotonic()+12
    expected=b'Hello, World! Agilex 5 HPS OCRAM UART\r\n'
    while time.monotonic()<deadline and data.count(expected)<3:
        if select.select([fd],[],[],0.5)[0]: data+=os.read(fd,65536)
    (root/'build'/f'uart-pass-{stamp}.bin').write_bytes(data)
    if data.count(expected)<3: raise RuntimeError(f'UART did not produce three expected lines: {data!r}')
    print(data.decode('ascii'),end='')
    print(f'PASS: physical HPS UART {a.port}, 115200 8N1; application runs in OCRAM.')
finally:
    os.close(fd)
