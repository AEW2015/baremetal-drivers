#!/usr/bin/env python3
"""Run a QEMU virt exercise, optionally serving a loopback-only GDB connection."""
import argparse,os,pathlib,signal,socket,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--debug',action='store_true')
p.add_argument('--check',action='store_true')
p.add_argument('--port',type=int,default=3338)
a=p.parse_args()
if a.debug and a.check:p.error('--debug and --check are mutually exclusive')
if not 1<=a.port<=65535:p.error('port must be 1..65535')
elf=root/'build/qemu/hello.elf'
if not elf.is_file():p.error('Build first with ./qemu/build.sh')
cmd=[os.environ.get('QEMU','qemu-system-aarch64'),'-machine','virt,secure=on,virtualization=on,gic-version=3','-cpu','cortex-a53','-accel','tcg','-nic','none','-m','128M','-display','none','-monitor','none','-serial','stdio','-semihosting-config','enable=on,target=native','-device',f'loader,file={elf},cpu-num=0']
if a.debug:cmd+=['-S','-gdb',f'tcp:127.0.0.1:{a.port}']
if a.check:
 result=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
 print(result.stdout,end='');print(result.stderr,end='')
 markers=['PASS EL3','PASS NEON: 11 22 33 44','PASS MEMORY: 4096-byte CPU copy','QEMU EXAMPLE COMPLETE']
 if result.returncode or 'FAIL' in result.stdout or not all(s in result.stdout for s in markers):raise SystemExit(1)
 raise SystemExit(0)
proc=subprocess.Popen(cmd)
def stop(*_):
 if proc.poll() is None:proc.terminate()
for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,stop)
try:
 if a.debug:
  deadline=time.monotonic()+10
  while time.monotonic()<deadline and proc.poll() is None:
   try:
    with socket.create_connection(('127.0.0.1',a.port),timeout=.1):pass
    print(f'QEMU GDB ready on 127.0.0.1:{a.port}',flush=True);break
   except OSError:time.sleep(.05)
  else:raise RuntimeError('QEMU GDB listener did not start')
 raise SystemExit(proc.wait())
finally:
 if proc.poll() is None:proc.terminate()
 try:proc.wait(timeout=5)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
