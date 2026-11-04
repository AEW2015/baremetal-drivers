#!/usr/bin/env python3
# SPDX-License-Identifier: MIT-0
"""Select the HD3SS3220's documented DFP/default mode while physically unattached.

Requires the explicit mode-write FPGA variant. No arbitrary register/value,
I2C software reset, VBUS override, shared reset pulse or NVM write is supported.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re

from read import ROOT, decode
from bench import verify_mount
from hardware_lock import HardwareLock
from mcp_client import MCP
from stack_bench import StackBench
from owned_process import run_owned

VALUES = {1: 0x01, 2: 0x21, 3: 0x20, 4: 0x00}

def require_unattached(data):
    if not data['mode_writes_supported']:
        raise RuntimeError('Read-only FPGA image; no mode write permitted')
    if data['attached_state'] != 'unattached':
        raise RuntimeError('Unplug the dock first: CC reports '+data['attached_state'])

def plan(mode, current):
    if current not in (0x00,0x01,0x20,0x21):
        raise ValueError('Unexpected General Control; refusing to overwrite other fields')
    target = 0x20 if mode == 'dfp' else 0
    if current == target:
        return []
    disable = 2 if current & 0x20 else 1
    return [disable, 2, 3] if mode == 'dfp' else [disable, 1, 4]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('dfp','default'))
    parser.add_argument('--check-only', action='store_true', help='Read and validate eligibility, then report the plan without sending mode writes')
    args = parser.parse_args()
    stack = StackBench()
    here = Path(__file__).resolve().parent
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT/'runs'/('usb-cc-configure-'+stamp)
    out.mkdir(parents=True)
    result = {'status': 'running', 'scope': __doc__, 'requested_mode': args.mode,
              'operations': [], 'check_only': args.check_only, 'restoration': 'not needed; no write yet',
              'source_sha256': {name: hashlib.sha256((here/name).read_bytes()).hexdigest()
                                for name in ('configure.py','read.tcl','write.tcl')}}
    def save(): (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Evidence:',out,flush=True)
    save()
    with HardwareLock():
        verify_mount()
        def transaction(label, body):
            client = MCP('programmer')
            try:
                chain = client.call('read_jtag_config',{})
                (out/(label+'-chain.json')).write_text(json.dumps(chain,indent=2)+'\n')
                blocks = re.split(r'(?m)^  (?=\d+:)',chain.get('text',''))
                if not any(re.match(r'1: Agilex_5E MDK Carrier',b) and
                           any(int(v,16)==0x0364f0dd for v in re.findall(r'JTAG ID 0x([0-9a-fA-F]+)',b)) for b in blocks):
                    raise RuntimeError('Wrong or ambiguous board')
            finally:
                client.close()
            prefix = ('hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; '
                      'gdb port disabled; tcl port disabled; telnet port disabled; init; targets hps.sys_bus;\n')
            script = prefix+body+'\nshutdown\n'
            path = stack.payload(out.name+'-'+label+'.tcl')
            path.write_text(script)
            (out/(label+'.tcl')).write_text(script)
            try:
                log = run_owned(['timeout','--kill-after=3s','30s','openocd',
                    '-f',stack.cfg,'-f',stack.remote(path)],timeout=40)
            except BaseException as error:
                (out/(label+'.log')).write_text(str(error))
                raise
            (out/(label+'.log')).write_text(log)
            return log
        def read_state(label):
            data = decode(transaction(label,(here/'read.tcl').read_text()))
            print(label+': '+json.dumps(data),flush=True)
            return data
        try:
            current = read_state('initial')
            result['initial'] = current
            require_unattached(current)
            actions = plan(args.mode,int(current['registers']['0xa'],16))
            result['planned_operations'] = actions
            save()
            if args.check_only:
                result['status'] = 'pass'
                result['final'] = current
                result['restoration'] = 'not needed; check-only sent no mode write'
                print('CC_MODE_CHECK_ONLY planned_operations='+json.dumps(actions),flush=True)
                return 0
            for index,operation in enumerate(actions):
                require_unattached(current)
                # Mark before submission: an uncertain timeout may have reached
                # the chip and requires a fresh read before any restoration.
                result['restoration'] = 'mode change submitted; verified readback pending'
                save()
                log = transaction('write-'+str(index), 'set cc_operation '+str(operation)+'\n'+(here/'write.tcl').read_text())
                if 'CC_MODE_WRITE_COMPLETE' not in log: raise RuntimeError('Missing write completion marker')
                current = read_state('readback-'+str(index))
                if int(current['registers']['0xa'],16) != VALUES[operation]:
                    raise RuntimeError('General Control readback mismatch')
                result['operations'].append({'operation':operation,'value':hex(VALUES[operation]),'readback':current})
                save()
            result['final'] = current
            result['status'] = 'pass'
            result['restoration'] = 'selected volatile mode retained intentionally; --mode default restores 0x00 while unattached'
        except BaseException as error:
            result['status'] = 'fail'
            result['error'] = str(error)
            # Never change modes behind an attached peer to hide a failure.
            # Record uncertainty; use fresh state and explicit default recovery.
            raise
        finally:
            save()
    print(json.dumps(result,indent=2),flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
