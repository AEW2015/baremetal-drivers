#!/usr/bin/env python3
"""Build the first QEMU lesson without a shell; works with a native host compiler."""
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    compiler = os.environ.get('CROSS_COMPILE','aarch64-none-elf-')+'gcc'
    if not shutil.which(compiler):
        raise SystemExit('Compiler missing: '+compiler+'. Install the host Arm toolchain or use python lab.py qemu from the repository root.')
    (ROOT/'build/qemu').mkdir(parents=True,exist_ok=True)
    command = [compiler,'-Og','-g3','-Wall','-Wextra','-Werror','-mcpu=cortex-a53',
        '-mgeneral-regs-only','-ffreestanding','-fno-builtin','-nostdlib','-static',
        '-Wl,--build-id=none,-T,qemu/link.ld','-o','build/qemu/hello.elf',
        'qemu/start.S','qemu/hello.c']
    subprocess.run(command,cwd=ROOT,check=True)


if __name__=='__main__':main()
