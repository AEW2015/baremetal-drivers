#!/usr/bin/env python3
"""Check the tutorial environment without programming the board."""
import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
from pathlib import Path
from bench import (ROOT, BenchError, HELP, checked_container, container_path, validate_uart,
                   verify_container_tools, verify_mapped_files, verify_mount)
from hardware_lock import HardwareLock

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['qemu', 'hardware'], default='qemu')
    parser.add_argument('--port', default=os.environ.get('AGILEX_UART', ''))
    parser.add_argument('--json', action='store_true', help='Print machine-readable checks')
    args = parser.parse_args()
    checks = []
    def add(name, status, message):
        checks.append({'check': name, 'status': status, 'message': message})
    def attempt(name, call):
        try:
            value = call()
            add(name, 'pass', value or 'OK')
            return True
        except (BenchError, OSError, subprocess.SubprocessError) as exc:
            add(name, 'fail', str(exc))
            return False
    where = 'container' if Path('/.dockerenv').exists() else 'host/native environment'
    add('environment', 'pass', f'{where}; {platform.system()} {platform.machine()}; workspace {ROOT}')
    if args.target == 'qemu':
        if platform.machine() not in ('x86_64', 'amd64'):
            add('host architecture', 'warn', 'The tutorial download is x86-64. Use a toolchain archive built for your host architecture; QEMU can still work with compatible installed tools.')
        for label, executable in [('compiler', os.environ.get('CROSS_COMPILE', 'aarch64-none-elf-') + 'gcc'),
                                  ('QEMU', os.environ.get('QEMU', 'qemu-system-aarch64')),
                                  ('GDB', 'gdb-multiarch')]:
            def version(executable=executable):
                if not shutil.which(executable):
                    raise BenchError(f'{executable} is missing in THIS environment. Follow setup.md and check PATH; host and container installations are separate.')
                result = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=10)
                if result.returncode:
                    raise BenchError(f'{executable} did not run: {result.stderr.strip()}')
                return result.stdout.splitlines()[0]
            attempt(label, version)
        elf = ROOT/'build/qemu/hello.elf'
        add('QEMU ELF', 'pass' if elf.is_file() else 'warn', str(elf) if elf.is_file() else 'Not built yet. Run ./qemu/build.sh; this is expected on a fresh clone.')
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', 3338))
                add('GDB port 3338', 'pass', 'Available now; the debug runner reserves its own listener atomically.')
            except OSError:
                add('GDB port 3338', 'warn', 'In use. Inspect ss -ltnp and stop your own previous debugger before F5; normal --check does not need this port.')
    else:
        # This checks configuration/mounts and may query JTAG identity; it never
        # sets JTAG speed, programs an image, reads UART bytes, or loads an ELF.
        attempt('host UART access', lambda: validate_uart(args.port))
        if attempt('container path', lambda: container_path(ROOT)):
            mounted = attempt('same bind-mounted checkout', verify_mount)
        else:
            mounted = False
        if mounted:
            tools = attempt('container tools', lambda: verify_container_tools(['jtagconfig', 'quartus_pgm', 'openocd', 'aarch64-none-elf-readelf']))
            attempt('core/image hashes', lambda: (verify_mapped_files([ROOT/'build/core_examples.elf', ROOT/'bootstrap/ddr/ddr_probe.hps.rbf', ROOT/'bootstrap/ocram/agilex5.cfg']) and 'Host/container artifact hashes match.'))
            if tools:
                try:
                    with HardwareLock():
                        chain = checked_container(['jtagconfig'])
                        first = chain.split('2)')[0]
                        if not re.search(r'^1\) Agilex_5E MDK Carrier ', first, re.M) or '0364F0DD' not in first.upper():
                            raise BenchError('Expected Modular ES carrier/FPGA ID 0364F0DD as cable 1. Inspect jtagconfig; do not select another board.')
                        add('JTAG identity/ownership', 'pass', 'Verified Modular ES cable 1; no programming or clock changes performed.')
                        if '4BA06477' not in first.upper():
                            add('HPS DAP', 'warn', 'Not present. Establish the matching merged image with --full-recovery before the first suite run.')
                        code = '''import json,socket
busy=[]
for port in (3337,6677,4457):
 with socket.socket() as sock:
  sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
  try: sock.bind(('127.0.0.1',port))
  except OSError: busy.append(port)
print(json.dumps(busy))
'''
                        busy = json.loads(checked_container(['python3', '-c', code]))
                        add('OpenOCD ports', 'fail' if busy else 'pass', f'Busy ports: {busy}; identify and stop only your own session.' if busy else '3337, 6677 and 4457 available now.')
                except (BenchError, OSError) as exc:
                    add('JTAG identity/ownership', 'fail', str(exc))
    failed = any(item['status'] == 'fail' for item in checks)
    result = {'target': args.target, 'status': 'fail' if failed else 'pass', 'checks': checks,
              'next': HELP if failed else ('Run ./qemu/build.sh then python3 qemu/run.py --check.' if args.target == 'qemu' else 'Review fresh-board versus running-design initialization before run_suite.py --only core.')}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for item in checks:
            print(f"{item['status'].upper():4} {item['check']}: {item['message']}")
        print('NEXT: ' + result['next'])
    return int(failed)

if __name__ == '__main__':
    raise SystemExit(main())
