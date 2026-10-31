from pathlib import Path
import subprocess,tempfile,time,json,hashlib
root=Path.cwd();out=Path(__file__).resolve().parent/'hello-gdb';out.mkdir()
elf=root/'build/qemu/hello.elf'
with tempfile.TemporaryDirectory(prefix='agx5-hello-') as td:
 sock=Path(td)/'gdb'
 cmd=['qemu-system-aarch64','-machine','virt,secure=on,virtualization=on,gic-version=3','-cpu','cortex-a53','-m','128M','-nic','none','-display','none','-monitor','none','-serial','stdio','-semihosting-config','enable=on,target=native','-device',f'loader,file={elf},cpu-num=0','-S','-chardev',f'socket,id=gdb,path={sock},server=on,wait=off','-gdb','chardev:gdb']
 with (out/'qemu.log').open('wb') as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
  try:
   deadline=time.monotonic()+5
   while not sock.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.05)
   assert sock.exists()
   commands=[f'target remote {sock}','break main','break qemu_done','continue','step','continue','print status','print failures','print vector_result','print source[511] == destination[511]','if status != 0 || failures != 0 || vector_result[0] != 11 || vector_result[1] != 22 || vector_result[2] != 33 || vector_result[3] != 44 || source[511] != destination[511]','quit 2','end',r'printf "PASS HELLO_GDB_CHECKED_RESULTS\n"','continue']
   gdb=['gdb-multiarch','-q','-batch',str(elf)]
   for c in commands:gdb+=['-ex',c]
   # Multiline control flow must be parsed from a command file.
   script=out/'walkthrough.gdb';script.write_text('\n'.join(commands)+'\n')
   result=subprocess.run(['gdb-multiarch','-q','-batch',str(elf),'-x',str(script)],capture_output=True,timeout=20)
   (out/'gdb.log').write_bytes(result.stdout+result.stderr)
   rc=proc.wait(timeout=5)
   passed=result.returncode==0 and rc==0 and b'PASS HELLO_GDB_CHECKED_RESULTS' in result.stdout and b'Breakpoint 1, main' in result.stdout and b'Breakpoint 2, qemu_done' in result.stdout
  finally:
   if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
 record={'tests':[{'name':'hello-gdb','status':'pass' if passed else 'fail','qemu_returncode':rc,'gdb_returncode':result.returncode,'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'qemu_command':cmd}],'scope':'Actual GDB breakpoints at main and qemu_done, source step, inspected status/failures/vector and final memory word; QEMU virt only'}
 (out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
 assert passed,result.stdout.decode()+result.stderr.decode()
 print('PASS hello-gdb: main, source step, qemu_done and independently checked results')
