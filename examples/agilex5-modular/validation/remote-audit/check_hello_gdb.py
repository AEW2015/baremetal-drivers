from pathlib import Path
import os,select,socket,subprocess,time,sys
root=Path('/home/dev/baremetal-remote-audit-0daff10/examples/agilex5-modular')
with socket.socket() as s:
 s.bind(('127.0.0.1',0));port=s.getsockname()[1]
p=subprocess.Popen(['python3',str(root/'qemu/run.py'),'--debug','--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  if select.select([p.stdout],[],[],.2)[0]:
   line=p.stdout.readline();print(line,end='',flush=True)
   if 'QEMU GDB ready' in line:break
  if p.poll() is not None:raise RuntimeError('QEMU exited before debugger ready')
 else:raise TimeoutError('Debugger readiness timeout')
 commands=[f'target remote 127.0.0.1:{port}','hbreak main','continue','info line','stepi','hbreak qemu_done','continue','print status','print failures','print vector_result','print source[511] == destination[511]',"python assert int(gdb.parse_and_eval('status')) == 0", "python assert int(gdb.parse_and_eval('failures')) == 0", "python assert [int(gdb.parse_and_eval('vector_result[%d]' % i)) for i in range(4)] == [11,22,33,44]", "python assert bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval('&source')),4096)) == bytes(gdb.selected_inferior().read_memory(int(gdb.parse_and_eval('&destination')),4096))",'continue']
 args=['gdb-multiarch','-nx','-q','--batch',str(root/'build/qemu/hello.elf')]
 for c in commands:args.extend(['-ex',c])
 result=subprocess.run(args,stdout=sys.stdout,stderr=subprocess.STDOUT,text=True,timeout=30)
 if result.returncode:raise RuntimeError(f'GDB exit {result.returncode}')
 if p.wait(timeout=5):raise RuntimeError(f'QEMU exit {p.returncode}')
 print(p.stdout.read(),end='');print('PASS HELLO_GDB: main, single step, qemu_done, status, NEON and all 512 words')
finally:
 if p.poll() is None:
  p.terminate()
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait()
