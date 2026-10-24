#!/usr/bin/env python3
"""Host runner: volatile HPS DDR bring-up, UART validation and DDR-PC proof."""
import argparse,os,pathlib,re,select,subprocess,termios,time,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from bench import container_command, container_path
root=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--port',default=os.environ.get('AGILEX_UART',''))
p.add_argument('--full-recovery',action='store_true',help='Program merged DDR recovery SOF, replacing volatile fabric and HPS configuration')
a=p.parse_args()
if not a.port:p.error("Set AGILEX_UART or pass --port")
program_image='ddr_recovery.sof' if a.full_recovery else 'ddr_probe.hps.rbf'
if not (root/program_image).is_file(): raise RuntimeError('Missing programming image '+program_image)
def container(args,timeout=90):
    r=subprocess.run(container_command(args),capture_output=True,text=True,timeout=timeout)
    if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    return r.stdout+r.stderr
chain=container(['jtagconfig']);first=chain.split('2)')[0]
if not re.search(r'^1\) Agilex_5E MDK Carrier ',first,re.M): raise RuntimeError('Expected Modular carrier as cable 1')
ids=re.findall(r'^\s+([0-9A-Fa-f]{8})\s',first,re.M)
if '0364F0DD' not in ids: raise RuntimeError('Expected Modular ES FPGA not present')
index=ids.index('0364F0DD')+1
container(['jtagconfig','--setparam','1','JtagClock','6M'])
stamp=time.strftime('%Y%m%d-%H%M%S',time.gmtime())
fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
try:
    v=termios.tcgetattr(fd);v[0]=v[1]=v[3]=0
    v[2]=termios.CS8|termios.CREAD|termios.CLOCAL
    v[4]=v[5]=termios.B115200;v[6][termios.VMIN]=v[6][termios.VTIME]=0
    termios.tcsetattr(fd,termios.TCSANOW,v);termios.tcflush(fd,termios.TCIFLUSH)
    with (root/f'program-{stamp}.log').open('w') as log:
        proc=subprocess.Popen(container_command(['quartus_pgm','-c',
            first.splitlines()[0].split(') ',1)[1],'-m','jtag','-o',
            f'p;{container_path(root/program_image)}@{index}']),stdout=log,stderr=subprocess.STDOUT)
        data=b'';deadline=time.monotonic()+180
        expected=b'Hello, World! executing from HPS DDR bank 3A @ 0x82000000\r\n'
        while time.monotonic()<deadline:
            if select.select([fd],[],[],.5)[0]:
                try: chunk=os.read(fd,65536)
                except BlockingIOError: continue
                if not chunk: raise RuntimeError("UART disconnected")
                data+=chunk
                (root/f'uart-{stamp}.bin').write_bytes(data)
            if proc.poll() is not None and proc.returncode: raise RuntimeError('Programming failed; see log')
            if (b'###DDR:init success###' in data and
                all(f'pattern {i} PASS'.encode() in data for i in range(4)) and
                b'payload readback PASS' in data and
                data.split(b'payload readback PASS')[-1].count(expected)>=3 and proc.poll()==0): break
        else:
            if proc.poll() is None: proc.terminate();proc.wait(timeout=10)
            raise RuntimeError('Timeout waiting for successful programming and three fresh DDR Hello messages')
        (root/f'uart-{stamp}.bin').write_bytes(data)
    for marker in [b'###DDR:init success###',*[f'pattern {i} PASS'.encode() for i in range(4)],b'payload readback PASS',expected]:
        if marker not in data: raise RuntimeError(f'Missing {marker!r}; see UART capture')
    cfg=container_path(root.parent/'ocram/agilex5.cfg')
    commands='hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; echo [get_reg {pc}]; resume; shutdown'
    proof=container(['openocd','-f',cfg,'-c',commands],30)
    (root/f'pc-{stamp}.log').write_text(proof)
    pcs=[int(x,16) for x in re.findall(r'^pc (0x[0-9a-fA-F]+)',proof,re.M)]
    if not pcs or not 0x82000000<=pcs[-1]<0x82000100: raise RuntimeError('PC not in DDR payload')
    print('PASS: HPS DDR bank 3A initialized; four 64 MiB patterns and payload readback passed.')
    print(expected.decode().strip());print(f'CPU PC confirmed in DDR: 0x{pcs[-1]:x}. Application left running.')
finally:
    if "proc" in globals() and proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=10)
    os.close(fd)
