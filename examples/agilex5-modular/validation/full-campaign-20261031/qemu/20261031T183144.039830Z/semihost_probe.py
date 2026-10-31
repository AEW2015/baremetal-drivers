"""QEMU-only relocation/semihosting check; message text does not prove OCRAM."""
from pathlib import Path
import subprocess,tempfile,time,json,hashlib,os
root=Path.cwd()
out=Path(__file__).resolve().parent/'semihost';out.mkdir()
build=root/'build/qemu-semihost-campaign';build.mkdir(exist_ok=True)
elf=build/'hello_semihost.elf'
cmd=['aarch64-none-elf-gcc','-nostdlib','-g3','-Wl,--build-id=none,-Ttext=0x40200000,-e,hello_entry','bootstrap/ocram/hello_semihost.S','-o',str(elf)]
build_result=subprocess.run(cmd,capture_output=True);(out/'build.log').write_bytes(build_result.stdout+build_result.stderr)
assert build_result.returncode==0
proc=None
with tempfile.TemporaryDirectory(prefix='agx5-semihost-') as td:
 sock=Path(td)/'gdb'
 qemu=['qemu-system-aarch64','-machine','virt,secure=on,virtualization=on','-cpu','cortex-a53','-m','128M','-nic','none','-display','none','-serial','none','-monitor','none','-semihosting-config','enable=on,target=native','-device',f'loader,file={elf},cpu-num=0','-S','-chardev',f'socket,id=gdb,path={sock},server=on,wait=off','-gdb','chardev:gdb']
 with (out/'qemu.log').open('wb') as log:
  try:
   proc=subprocess.Popen(qemu,stdout=log,stderr=subprocess.STDOUT)
   deadline=time.monotonic()+5
   while not sock.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.05)
   assert sock.exists()
   gdb=['gdb-multiarch','-q','-batch',str(elf),'-ex',f'target remote {sock}','-ex','break hello_done','-ex','continue','-ex','printf "SEMIHOST_DONE_PC=%#lx\n", $pc','-ex','detach']
   result=subprocess.run(gdb,capture_output=True,timeout=15)
   (out/'gdb.log').write_bytes(result.stdout+result.stderr)
   assert result.returncode==0
   assert b'Breakpoint 1, hello_done' in result.stdout
   assert b'SEMIHOST_DONE_PC=0x40200010' in result.stdout
  finally:
   if proc is not None and proc.poll() is None:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
 body=(out/'qemu.log').read_text()
 passed='Hello, World! Agilex 5 HPS executing from OCRAM.' in body
 record={'scope':'Unchanged reference assembly relinked into QEMU virt RAM; semihost SYS_WRITE0 plus GDB stop at hello_done. Printed OCRAM text is literal source wording, not a physical OCRAM qualification. Guest deliberately loops at hello_done and host terminates after GDB proof.', 'tests':[{'name':'semihost','status':'pass' if passed else 'fail','catalog_id':'reference/semihost','compiler_exit':build_result.returncode,'gdb_exit':result.returncode,'qemu_exit_after_deliberate_host_termination':proc.returncode,'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((root/'bootstrap/ocram/hello_semihost.S').read_bytes()).hexdigest(),'build_command':cmd,'qemu_command':qemu,'gdb_command':gdb}]}
 (out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
 assert passed
 print('PASS reference/semihost: SYS_WRITE0 output and GDB hello_done stop; QEMU RAM only')
