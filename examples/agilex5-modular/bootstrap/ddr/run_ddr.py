#!/usr/bin/env python3
"""Host runner: locked volatile DDR bring-up, fresh UART checks and DDR-PC proof."""
import argparse
import datetime
import os
import pathlib
import re
import select
import signal
import subprocess
import sys
import termios
import time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from bench import (BenchError, HELP, checked_container, container_command, container_path,
                   validate_uart, verify_container_tools, verify_mapped_files, verify_mount)
from hardware_lock import HardwareLock
from owned_process import OwnedContainerProcess, OwnedProcessError, run_owned
ROOT = pathlib.Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default=os.environ.get('AGILEX_UART', ''))
    parser.add_argument('--full-recovery', action='store_true', help='Program merged matching SOF, replacing volatile fabric and HPS configuration')
    args = parser.parse_args()
    image = ROOT / ('ddr_recovery.sof' if args.full_recovery else 'ddr_probe.hps.rbf')
    cfg = ROOT.parent / 'ocram/agilex5.cfg'
    # The suite explicitly passes its locked file descriptor. Direct callers
    # acquire their own lock and cannot bypass an active F5/debugger session.
    with HardwareLock():
        print('DDR stage: checking UART, container mount, tools and image hashes...', flush=True)
        validate_uart(args.port)
        verify_mount()
        verify_container_tools(['jtagconfig', 'quartus_pgm', 'openocd'])
        hashes = verify_mapped_files([image, cfg])
        chain = checked_container(['jtagconfig'])
        first = chain.split('2)')[0]
        cable_match = re.search(r'^1\) (Agilex_5E MDK Carrier .*)$', first, re.M)
        if not cable_match:
            raise BenchError('Expected Modular carrier as cable 1. Inspect jtagconfig; do not select another connected board to bypass this check.')
        ids = re.findall(r'^\s+([0-9A-Fa-f]{8})\s', first, re.M)
        ids = [value.upper() for value in ids]
        if '0364F0DD' not in ids:
            raise BenchError('Expected Modular ES FPGA ID 0364F0DD not present. Verify the physical kit and cable order.')
        index = ids.index('0364F0DD') + 1
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        programmer_log = ROOT / f'program-{stamp}.log'
        uart_log = ROOT / f'uart-{stamp}.bin'
        proof_log = ROOT / f'pc-{stamp}.log'
        proc = None
        fd = os.open(args.port, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            settings = termios.tcgetattr(fd)
            settings[0] = settings[1] = settings[3] = 0
            settings[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            settings[4] = settings[5] = termios.B115200
            settings[6][termios.VMIN] = settings[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, settings)
            termios.tcflush(fd, termios.TCIFLUSH)
            checked_container(['jtagconfig', '--setparam', '1', 'JtagClock', '6M'])
            print(f'DDR stage: programming {image.name} at verified FPGA position {index}.\nImage SHA256: {hashes[str(image.resolve())]}\nProgrammer log: {programmer_log}', flush=True)
            with programmer_log.open('w') as log:
                proc = OwnedContainerProcess(['quartus_pgm', '-c', cable_match[1], '-m', 'jtag', '-o',
                    f'p;{container_path(image)}@{index}'], stdout=log, stderr=subprocess.STDOUT)
                data = b''
                deadline = time.monotonic() + 180
                expected = b'Hello, World! executing from HPS DDR bank 3A @ 0x82000000\r\n'
                print(f'DDR stage: waiting for four patterns, payload and three fresh Hello messages.\nUART capture: {uart_log}', flush=True)
                while time.monotonic() < deadline:
                    if select.select([fd], [], [], .5)[0]:
                        try:
                            chunk = os.read(fd, 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            raise BenchError(f'UART disconnected; re-identify SOM J2. Capture: {uart_log}')
                        data += chunk
                        uart_log.write_bytes(data)
                    if proc.poll() is not None and proc.returncode:
                        raise BenchError(f'Programming failed. Inspect {programmer_log}; fresh power-up/different fabric may need the matching --full-recovery image.')
                    if (b'###DDR:init success###' in data and all(f'pattern {i} PASS'.encode() in data for i in range(4))
                            and b'payload readback PASS' in data
                            and data.split(b'payload readback PASS')[-1].count(expected) >= 3 and proc.poll() == 0):
                        break
                else:
                    raise BenchError(f'Timeout waiting for complete fresh DDR proof. Inspect {programmer_log} and {uart_log}; stop further examples until restoration is verified.')
            print('DDR stage: confirming CPU PC through OpenOCD...', flush=True)
            commands = 'hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; halt; echo [get_reg {pc}]; resume; shutdown'
            try:
                proof = run_owned(['openocd', '-f', container_path(cfg), '-c', commands], timeout=30)
            except OwnedProcessError:
                raise
            except BenchError as exc:
                proof_log.write_text(str(exc) + '\n')
                raise BenchError(f'DDR PC proof failed. Inspect {proof_log}.') from exc
            proof_log.write_text(proof)
            pcs = [int(value, 16) for value in re.findall(r'^pc (0x[0-9a-fA-F]+)', proof, re.M)]
            if not pcs or not 0x82000000 <= pcs[-1] < 0x82000100:
                raise BenchError(f'PC is not in the DDR payload. Inspect {proof_log}; restoration is not verified.')
            print('PASS: HPS DDR bank 3A initialized; four 64 MiB patterns and payload readback passed.')
            print(expected.decode().strip())
            print(f'CPU PC confirmed in DDR: 0x{pcs[-1]:x}. Application left running.')
        finally:
            try:
                if proc is not None:
                    proc.close()
            finally:
                os.close(fd)
    return 0

if __name__ == '__main__':
    def interrupted(*_):
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('DDR initialization interrupted. Restoration is not verified; inspect the programmer/logs before another operation.', file=sys.stderr)
        raise SystemExit(130)
    except OwnedProcessError as exc:
        print(f'ERROR: {exc}\nSTOP: owned process state is uncertain; automatic reprogramming must wait. Help: {HELP}', file=sys.stderr)
        raise SystemExit(3)
    except (BenchError, OSError, termios.error) as exc:
        print(f'ERROR: {exc}\nHelp: {HELP}', file=sys.stderr)
        raise SystemExit(1)
