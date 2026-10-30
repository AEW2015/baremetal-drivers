#!/usr/bin/env python3
"""Run the board-free labs, UART interaction and GDB exercises under QEMU TCG."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build/qemu-labs'
LABS = {
    'startup': ['DATA_RELOCATED', 'DISTINCT_LOAD_AND_RUNTIME_ADDRESSES',
                'BSS_ZERO', 'STACK_ALIGNED_IN_RANGE'],
    'corruption': ['EXPECTED_CORRUPTION_INDEX_37', 'REPAIRED_COPY_512_WORDS'],
    'exception': ['BRK_SYNDROME_AND_RETURN', 'FAULT_PC_CAPTURED'],
    'timer': ['TIMER_FREQUENCY', 'TIMER_10_INTERRUPTS', 'WFI_IDLE_LOOP'],
    'mmu': ['MMU_AND_DCACHE_INITIALLY_OFF', 'MMU_RW_READBACK', 'MMU_RO_READBACK',
            'MMU_WRITE_PERMISSION_FAULT', 'MMU_RO_UNCHANGED', 'MMU_DISABLED_AFTER_TEST'],
    'uart': ['UART_MEMCHECK', 'UART_SESSION'],
    'multicore': ['SECONDARY_IDENTITY', 'THREE_SECONDARIES_EXECUTED'],
}
NEGATIVES = {
    'startup-no-bss': ('startup', 'BSS_ZERO'),
    'startup-no-data': ('startup', 'DATA_RELOCATED'),
    'corruption-no-injection': ('corruption', 'EXPECTED_CORRUPTION_INDEX_37'),
    'exception-wrong-brk': ('exception', 'unexpected BRK syndrome'),
    'timer-wrong-ppi': ('timer', 'timer interrupt identity'),
    'mmu-writable-ro': ('mmu', 'MMU_WRITE_PERMISSION_FAULT'),
}
UART_CASES = [
    ('help', b'help\r\n', b'COMMANDS help status memcheck exit\n'),
    ('backspace', b'statuX\x08s\r', b'STATUS EL3 READY\n'),
    ('delete', b'statuX\x7fs\n', b'STATUS EL3 READY\n'),
    ('memory', b'memcheck\r', b'PASS UART_MEMCHECK\n'),
    ('unknown', b'no-such-command\r', b'ERROR unknown command\n'),
    ('empty', b'\r', b'lab> '),
    ('length-31', b'x'*31+b'\r', b'ERROR unknown command\n'),
    ('length-32', b'x'*32+b'\r', b'ERROR line too long\n'),
    ('length-80', b'x'*80+b'\r', b'ERROR line too long\n'),
    ('overflow-recovery', b'status\r', b'STATUS EL3 READY\n'),
    ('exit', b'exit\r', b'LAB COMPLETE\n'),
]


def qemu_command(name, port=None):
    elf = BUILD / (name + '.elf')
    if not elf.is_file():
        raise FileNotFoundError(f'{elf}: run bash qemu/labs/build.sh first')
    cmd = [os.environ.get('QEMU', 'qemu-system-aarch64'), '-machine',
           'virt,secure=on,virtualization=on,gic-version=3', '-cpu', 'cortex-a53',
           '-accel', 'tcg', '-smp', '1', '-nic', 'none', '-m', '128M',
           '-display', 'none', '-monitor', 'none', '-serial', 'stdio',
           '-semihosting-config', 'enable=on,target=native',
           '-device', f'loader,file={elf},cpu-num=0']
    if port is not None:
        cmd += ['-S', '-gdb', f'tcp:127.0.0.1:{port}']
    if name=='multicore':
        cmd[cmd.index('-smp')+1]='4'
        # Loader starts each vCPU at the same ELF entry; startup selects its
        # dedicated secondary path. This tests execution, not PSCI CPU_ON.
        for cpu in range(1,4):cmd+=['-device',f'loader,addr=0x40200000,cpu-num={cpu}']
    return cmd


def accepts(name, output, returncode):
    """Acceptance requires fresh begin, all exact PASS lines and successful exit."""
    lines = output.splitlines()
    return (returncode == 0 and f'LAB BEGIN {name}' in lines and
            'LAB COMPLETE' in lines and 'LAB FAILED' not in lines and
            not any(line.startswith('FAIL ') for line in lines) and
            all('PASS ' + marker in lines for marker in LABS[name]) and
            (name!='multicore' or lines.count('PASS SECONDARY_IDENTITY')==3))


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def run_uart():
    """Send each input only after a prompt; inspect its individual response."""
    proc = subprocess.Popen(qemu_command('uart'), stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    transcript = bytearray()
    observations = []
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)

    def read_until(marker, start):
        deadline = time.monotonic() + 5
        while marker not in transcript[start:]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('UART response timeout')
            events = selector.select(min(remaining, .2))
            if events:
                chunk = os.read(proc.stdout.fileno(), 4096)
                if not chunk:
                    raise RuntimeError('QEMU ended before expected UART response')
                transcript.extend(chunk)
        return bytes(transcript[start:])

    # Both accepted length 31 and rejected length 32 are tested, plus recovery.
    cases = UART_CASES
    try:
        read_until(b'lab> ', 0)
        for label, payload, expected in cases:
            start = len(transcript)
            proc.stdin.write(payload)
            proc.stdin.flush()
            response = read_until(b'LAB COMPLETE\n' if label == 'exit' else b'lab> ', start)
            ok = expected in response
            observations.append(dict(case=label, passed=ok))
            if not ok:
                raise AssertionError(f'UART case {label}: {response!r}')
        proc.wait(timeout=3)
        return transcript.decode(errors='replace'), proc.returncode, observations
    except Exception as exc:
        transcript.extend(f'\nHOST ERROR: {exc}\n'.encode())
        return transcript.decode(errors='replace'), -1, observations
    finally:
        selector.close()
        stop(proc)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def run_gdb(name, out):
    port = free_port()
    if name == 'startup':
        exercise = '''python
import gdb
assert int(gdb.parse_and_eval('initialized')) == 0
load = int(gdb.parse_and_eval('(unsigned long)__data_load'))
assert int.from_bytes(bytes(gdb.selected_inferior().read_memory(load, 8)), 'little') == 0x123456789abcdef0
print('GDB PASS DATA_BEFORE_RELOCATION')
end
hbreak main
continue
python
assert int(gdb.parse_and_eval('initialized')) == 0x123456789abcdef0
begin = int(gdb.parse_and_eval('(unsigned long)__bss_start'))
end = int(gdb.parse_and_eval('(unsigned long)__bss_end'))
assert not any(bytes(gdb.selected_inferior().read_memory(begin, end-begin)))
assert int(gdb.parse_and_eval('$sp')) & 15 == 0
print('GDB PASS STARTUP_MEMORY_AND_STACK')
end
'''
        markers = ['GDB PASS DATA_BEFORE_RELOCATION', 'GDB PASS STARTUP_MEMORY_AND_STACK']
    else:
        exercise = '''hbreak copy_complete
continue
watch destination[37]
continue
bt
python
import gdb
assert gdb.newest_frame().name() == 'inject_corruption'
assert int(gdb.parse_and_eval('destination[37]')) == 0x1234567800000024
assert int(gdb.parse_and_eval('source[37]')) == 0x1234567800000025
print('GDB PASS WATCHPOINT_CAUGHT_BAD_WRITE')
end
delete breakpoints
hbreak lab_done
continue
python
assert int(gdb.parse_and_eval('status')) == 0
assert int(gdb.parse_and_eval('mismatch_count')) == 1
assert int(gdb.parse_and_eval('first_bad_index')) == 37
src = gdb.parse_and_eval('source')
dst = gdb.parse_and_eval('destination')
assert all(int(src[i]) == int(dst[i]) for i in range(512))
print('GDB PASS ALL_512_WORDS_REPAIRED')
end
'''
        markers = ['GDB PASS WATCHPOINT_CAUGHT_BAD_WRITE', 'GDB PASS ALL_512_WORDS_REPAIRED']
    script = ('set pagination off\nset confirm off\nset architecture aarch64\n'
              f'target remote 127.0.0.1:{port}\n' + exercise + 'detach\nquit\n')
    script_path = out / (name + '.gdb')
    script_path.write_text(script)
    with (out / (name + '-gdb-qemu.log')).open('w') as log:
        proc = subprocess.Popen(qemu_command(name, port), stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1):
                        break
                except OSError:
                    if proc.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('QEMU GDB listener unavailable')
                    time.sleep(.05)
            gdb = subprocess.run([os.environ.get('GDB', 'gdb-multiarch'), '-q', '-batch',
                                  '-x', str(script_path), str(BUILD / (name + '.elf'))],
                                 capture_output=True, text=True, timeout=15)
            output = gdb.stdout + gdb.stderr
            (out / (name + '-gdb.log')).write_text(output)
            proc.wait(timeout=5)
            return dict(name=name + '-gdb', passed=gdb.returncode == 0 and
                        proc.returncode == 0 and all(m in output for m in markers),
                        gdb_returncode=gdb.returncode, qemu_returncode=proc.returncode)
        finally:
            stop(proc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=LABS, help='run one lab instead of all six')
    parser.add_argument('--negative', action='store_true', help='also verify all six broken variants are rejected')
    parser.add_argument('--gdb', action='store_true', help='also check startup and corruption in batch GDB')
    parser.add_argument('--interactive', action='store_true', help='attach the UART lab directly to this terminal')
    parser.add_argument('--debug', action='store_true', help='start the selected lab paused for manual GDB')
    parser.add_argument('--port', type=int, default=3339)
    parser.add_argument('--output', type=Path, help='evidence directory (default: timestamped runs/qemu-labs-...)')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be in 1..65535')
    if args.debug or args.interactive:
        if args.negative or args.gdb or args.output:
            parser.error('interactive/debug mode cannot be combined with batch checks or --output')
        if args.interactive and (args.debug or args.only not in (None, 'uart')):
            parser.error('--interactive is for the UART lab; use --debug --only uart for UART debugging')
        name = args.only or ('uart' if args.interactive else 'startup')
        cmd = qemu_command(name, args.port if args.debug else None)
        if args.debug:
            print(f'GDB: target remote 127.0.0.1:{args.port}', flush=True)
            print(f'ELF: {BUILD / (name + ".elf")}', flush=True)
        proc = subprocess.Popen(cmd)
        try:
            return proc.wait()
        except KeyboardInterrupt:
            return 130
        finally:
            stop(proc)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = (args.output or ROOT / 'runs' / ('qemu-labs-' + stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = []
    print('Evidence:', out, flush=True)
    versions = {}
    for key, cmd in [('qemu', os.environ.get('QEMU', 'qemu-system-aarch64')),
                     ('compiler', os.environ.get('CROSS_COMPILE', 'aarch64-none-elf-') + 'gcc')]:
        versions[key] = subprocess.check_output([cmd, '--version'], text=True).splitlines()[0]
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(Path(__file__).parent.iterdir()) if p.is_file()}
    manifest = dict(started_utc=stamp, tools=versions, source_sha256=sources, tests=results)

    def record(result):
        results.append(result)
        (out / 'results.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(result['name'] + ': ' + ('PASS' if result['passed'] else 'FAIL'), flush=True)
        if not result['passed']:
            if result.get('error'):
                print(result['error'], flush=True)
            for suffix in ('.log', '-qemu.log'):
                log = out / (result['name'] + suffix)
                if log.is_file():
                    print(f'--- {log.name} ---\n{log.read_text(errors="replace")[-8000:]}', flush=True)

    names = [args.only] if args.only else list(LABS)
    for name in names + (list(NEGATIVES) if args.negative else []):
        result = dict(name=name, passed=False)
        try:
            cmd = qemu_command(name)
            result['command'] = cmd
            result['elf_sha256'] = hashlib.sha256((BUILD / (name + '.elf')).read_bytes()).hexdigest()
            if name == 'uart':
                output, rc, cases = run_uart()
                result['input_cases'] = cases
                result['passed'] = accepts(name, output, rc) and len(cases) == 11 and all(c['passed'] for c in cases)
            else:
                run = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                output, rc = run.stdout + run.stderr, run.returncode
                if name in NEGATIVES:
                    base, marker = NEGATIVES[name]
                    result['passed'] = (rc == 1 and 'FAIL ' + marker in output.splitlines()
                                        and 'LAB FAILED' in output.splitlines()
                                        and not accepts(base, output, rc))
                    result['expected_failure'] = marker
                else:
                    result['passed'] = accepts(name, output, rc)
            result['qemu_returncode'] = rc
            (out / (name + '.log')).write_text(output)
        except subprocess.TimeoutExpired as exc:
            result['error'] = 'QEMU timeout (10 seconds)'
            (out / (name + '.log')).write_bytes((exc.stdout or b'') + (exc.stderr or b''))
        except Exception as exc:
            result['error'] = repr(exc)
        record(result)
    if args.gdb:
        manifest['tools']['gdb'] = subprocess.check_output(
            [os.environ.get('GDB', 'gdb-multiarch'), '--version'], text=True).splitlines()[0]
        for name in ['startup', 'corruption']:
            try:
                record(run_gdb(name, out))
            except Exception as exc:
                record(dict(name=name + '-gdb', passed=False, error=repr(exc)))
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
