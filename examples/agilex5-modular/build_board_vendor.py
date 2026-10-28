#!/usr/bin/env python3
"""Container: relink selected vendor tests with a physical-board UART adapter."""
import pathlib,subprocess,shlex,sys
from legacy_source import ensure
vendor=ensure()
root=pathlib.Path(__file__).resolve().parent
(root/'build').mkdir(exist_ok=True)
entry=root/'build/vendor_entry.o'
subprocess.run(['aarch64-none-elf-gcc','-c',str(root/'core/vendor_entry.S'),'-o',str(entry)],check=True)
ld=root/'build/vendor_board.ld'
ld.write_text((vendor/'build/aarch64/core0.ld').read_text().replace('STACKTOP = 0xA0000000','STACKTOP = 0x83fff000'))
names=sys.argv[1:] or ['uart','timer','watchdog','spi','ccu','clkmgr','smmu','ecc','hps_mailbox']
for name in names:
 if name not in ['uart','timer','watchdog','spi','ccu','clkmgr','smmu','ecc','hps_mailbox']:raise SystemExit('Unknown vendor test '+name)
 obj=root/'build'/f'{name}_wrapper.o'
 subprocess.run(['aarch64-none-elf-gcc','-Os','-g','-Wall','-Wextra','-Werror',f'-DTEST_NAME="{name}"',*(['-DBOARD_TEST_SMMU'] if name=='smmu' else []),'-c',str(root/'core/vendor_wrapper.c'),'-o',str(obj)],check=True)
 commands=subprocess.check_output(['ninja','-C',str(root/'build/legacy-vendor'),'-t','commands',name+'_test.elf'],text=True)
 link=next(x for x in commands.splitlines() if ' -o ' in x and 'aarch64-none-elf-g++' in x and not ' -c ' in x)
 link=link.split(' && ')[1]
 args=shlex.split(link)
 out=root/'build'/f'vendor_{name}.elf'
 args[args.index('-o')+1]=str(out)
 normalized=[]
 it=iter(args)
 for x in it:
  if x=='-T':
   next(it);normalized.append('-T'+str(ld))
  elif x.startswith('-T'):normalized.append('-T'+str(ld))
  else:normalized.append(x)
 args=normalized
 args += [str(entry),'-Wl,--entry=board_vendor_entry',str(obj),'-Wl,--wrap=main,--wrap=uart_init,--wrap=_write']
 subprocess.run(args,check=True,cwd=root/'build/legacy-vendor')
 print(out)
