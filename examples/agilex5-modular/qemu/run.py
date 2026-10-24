#!/usr/bin/env python3
"""Run the generic virt exercise with actionable failures and an owned GDB socket."""
import argparse
import os
import pathlib
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKERS = ['PASS EL3', 'PASS NEON: 11 22 33 44',
           'PASS MEMORY: 4096-byte CPU copy', 'QEMU EXAMPLE COMPLETE']
HELP = 'https://aew2015.github.io/baremetal-drivers/troubleshooting/#qemu'

class RunError(RuntimeError):
    pass

def output(data):
    if data:
        print(data.decode(errors='replace') if isinstance(data, bytes) else data, end='', flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--debug', action='store_true')
    mode.add_argument('--check', action='store_true')
    parser.add_argument('--port', type=int, default=3338)
    parser.add_argument('--timeout', type=float, default=20, help='Bounded --check timeout in seconds (default: 20)')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    if not .05 <= args.timeout <= 300:
        parser.error('timeout must be 0.05..300 seconds')
    elf = ROOT / 'build/qemu/hello.elf'
    if not elf.is_file():
        raise RunError('ELF is missing. From examples/agilex5-modular run ./qemu/build.sh, then retry.')
    executable = os.environ.get('QEMU', 'qemu-system-aarch64')
    if shutil.which(executable) is None:
        raise RunError(f'QEMU executable not found: {executable}. Install qemu-system-arm in THIS environment (host or attached container), or correct/unset QEMU.')
    cmd = [executable, '-machine', 'virt,secure=on,virtualization=on,gic-version=3',
           '-cpu', 'cortex-a53', '-accel', 'tcg', '-nic', 'none', '-m', '128M',
           '-display', 'none', '-monitor', 'none', '-serial', 'stdio',
           '-semihosting-config', 'enable=on,target=native',
           '-device', f'loader,file={elf},cpu-num=0']
    if args.check:
        print('QEMU: running bounded checks...', flush=True)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        except subprocess.TimeoutExpired as exc:
            output(exc.stdout); output(exc.stderr)
            raise RunError(f'QEMU check timed out after {args.timeout:g}s; partial output is shown above. Rebuild the supplied ELF and keep the runner platform/semihosting settings. Command: {shlex.join(cmd)}') from exc
        output(result.stdout); output(result.stderr)
        missing = [marker for marker in MARKERS if marker not in result.stdout]
        if result.returncode or 'FAIL' in result.stdout or missing:
            raise RunError(f'QEMU check failed (exit {result.returncode}); missing markers: {", ".join(missing) or "none"}. Inspect FAIL lines and restore any deliberate source changes, then rebuild.')
        print('PASS QEMU_CHECK: all required markers and exit status zero', flush=True)
        return 0
    listener = None
    proc = None
    try:
        if args.debug:
            # Reserve the actual listening socket and pass that descriptor to
            # QEMU. There is no bind/probe race with an unrelated listener.
            listener = socket.socket()
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(('127.0.0.1', args.port))
                listener.listen(1)
            except OSError as exc:
                raise RunError(f'Cannot reserve GDB port 127.0.0.1:{args.port}: {exc}. Inspect ss -ltnp, stop your own previous session, or choose --port and update GDB accordingly.') from exc
            cmd += ['-S', '-chardev', f'socket,id=tutorial_gdb,fd={listener.fileno()},server=on,wait=off',
                    '-gdb', 'chardev:tutorial_gdb']
        proc = subprocess.Popen(cmd, pass_fds=(() if listener is None else (listener.fileno(),)))
        if listener is not None:
            listener.close(); listener = None
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    with socket.create_connection(('127.0.0.1', args.port), timeout=.1):
                        pass
                    time.sleep(.1)
                    if proc.poll() is not None:
                        break
                    print(f'QEMU GDB ready on 127.0.0.1:{args.port}', flush=True)
                    break
                except OSError:
                    time.sleep(.05)
            else:
                raise RunError('The owned QEMU GDB listener did not become ready. Inspect emulator output above.')
            if proc.poll() is not None:
                raise RunError(f'QEMU exited during debugger startup (exit {proc.returncode}); inspect its diagnostic output.')
        rc = proc.wait()
        if rc:
            raise RunError(f'QEMU exited with status {rc}; inspect the emulator output above.')
        return 0
    finally:
        if listener is not None:
            listener.close()
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()

if __name__ == '__main__':
    def interrupted(*_):
        raise KeyboardInterrupt
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('QEMU session stopped.', file=sys.stderr)
        raise SystemExit(130)
    except (RunError, OSError) as exc:
        print(f'ERROR: {exc}\nHelp: {HELP}', file=sys.stderr)
        raise SystemExit(1)
