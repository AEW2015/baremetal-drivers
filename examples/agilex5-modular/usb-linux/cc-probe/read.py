#!/usr/bin/env python3
# SPDX-License-Identifier: MIT-0
"""Read the dedicated FPGA CC probe; no CPU halt, reset or CC configuration write."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bench import verify_mount
from hardware_lock import HardwareLock
from mcp_client import MCP
from stack_bench import StackBench
from owned_process import run_owned

def decode(log):
    values = {int(a, 16): int(v, 16) for a, v in re.findall(
        r'CC_REGISTER reg=0x([0-9a-f]+) value=0x([0-9a-f]+)', log)}
    if set(values) != set(range(11)) or 'CC_PROBE_CAPTURE_COMPLETE' not in log:
        raise ValueError('No complete CC register capture')
    if [values[i] for i in range(8)] != [0x32, 0x32, 0x33, 0x42, 0x53, 0x55, 0x54, 0]:
        raise ValueError('CC device identity does not match HD3SS3220')
    return {
        'registers': {hex(i): hex(v) for i, v in values.items()},
        'identity': 'HD3SS3220, verified register signature',
        'mode_writes_supported': bool(int(re.search(r'CC_INPUTS before=0x([0-9a-f]+)', log).group(1),16)&(1<<15)) if re.search(r'CC_INPUTS before=0x([0-9a-f]+)', log) else False,
        'attached_state': ('unattached', 'DFP/source', 'UFP/sink', 'accessory')[values[9] >> 6],
        'cable_direction_bit': bool(values[9] & 32),
        'configured_mode': ('PORT pin default', 'UFP/sink', 'DFP/source', 'DRP')[(values[10] >> 4) & 3],
        'limits': 'CC status only; no PD-message capture, connector-voltage measurement or USB data transfer qualification',
    }

def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'runs' / ('usb-cc-probe-' + stamp)
    out.mkdir(parents=True)
    print('Evidence:', out, flush=True)
    source = Path(__file__).with_name('read.tcl')
    result = {'status': 'running', 'scope': __doc__,
              'tcl_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    stack = StackBench()
    try:
        with HardwareLock():
            verify_mount()
            client = MCP('programmer')
            try:
                chain = client.call('read_jtag_config', {})
                (out/'chain.json').write_text(json.dumps(chain, indent=2)+'\n')
                blocks = re.split(r'(?m)^  (?=\d+:)', chain.get('text', ''))
                matches = [b for b in blocks if re.match(r'1: Agilex_5E MDK Carrier', b)
                           and any(int(v,16) == 0x0364f0dd for v in re.findall(r'JTAG ID 0x([0-9a-fA-F]+)', b))]
                if len(matches) != 1:
                    raise RuntimeError('Fresh chain does not uniquely identify the Modular ES carrier as cable 1')
            finally:
                client.close()
            script = ('hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; '
                      'gdb port disabled; tcl port disabled; telnet port disabled; init; targets hps.sys_bus;\n'
                      + source.read_text() + '\nshutdown\n')
            path = stack.payload(out.name+'.tcl')
            path.write_text(script)
            try:
                log = run_owned(['timeout', '--kill-after=3s', '30s', 'openocd',
                    '-f', stack.cfg, '-f', stack.remote(path)], timeout=40)
            except BaseException as error:
                (out/'capture.log').write_text(str(error))
                raise
            (out/'capture.log').write_text(log)
            print(log[-2400:], flush=True)
            result.update(decode(log))
            result['status'] = 'pass'
    except BaseException as error:
        result['status'] = 'fail'
        result['error'] = str(error)
        raise
    finally:
        (out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
