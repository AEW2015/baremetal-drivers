#!/usr/bin/env python3
"""Read the SOM USB reset GPIO/pinmux through the memory AP under the bench lock."""
import argparse
import datetime
import fcntl
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stack_bench import StackBench
from hardware_lock import HardwareLock
from owned_process import run_owned
from bench import BenchError

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bench', type=Path)
    parser.add_argument('--mcp-client', type=Path, default=ROOT/'mcp_client.py')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stack=StackBench(args.bench)
    with HardwareLock():
        sys.path.insert(0, str(args.mcp_client.parent))
        from mcp_client import MCP
        client = MCP('programmer')
        try:
            chain = client.call('read_jtag_config', {})
            identity = json.dumps(chain).lower()
            if '364f0dd' not in identity or '4ba06477' not in identity:
                raise RuntimeError('Expected Modular ES FPGA and HPS DAP not found')
            out = root/'runs'/('usb-reset-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
            out.mkdir(parents=True)
            (out/'chain.json').write_text(json.dumps(chain, indent=2)+'\n')
            command = ('init; foreach a {0x10d13028 0x10c03200 0x10c03204 0x10c03250} '
                       '{echo [format {USB_RESET_REG %08x %08x} $a '
                       '[lindex [read_memory $a 32 1] 0]]}; shutdown')
            # The vendor launcher reparses -c arguments. Use a Tcl file so
            # braces and variables reach OpenOCD without shell expansion.
            (out/'read-registers.cfg').write_text(command+'\n')
            arguments=['timeout','--kill-after=5s','30s','openocd','-f',
                       stack.remote(ROOT/'bootstrap/ocram/sysbus.cfg'),
                       '-f',stack.remote(out/'read-registers.cfg')]
            invocation=stack.command(arguments)
            try:
                raw=run_owned(arguments,timeout=40).encode()
                code=0
            except BenchError as error:
                raw=str(error).encode();code=1
            (out/'memory-ap.log').write_bytes(raw)
            values = {}
            for address, word in re.findall(rb'USB_RESET_REG ([0-9a-fA-F]{8}) ([0-9a-fA-F]{8})', raw):
                values[int(address,16)] = int(word,16)
            expected = [0x10d13028, 0x10c03200, 0x10c03204, 0x10c03250]
            result = {'scope': 'Memory AP register reads only; no CPU halt/resume, peripheral writes or PHY transactions',
                      'invocation': invocation, 'returncode': code,
                      'complete': code == 0 and all(a in values for a in expected),
                      'registers': {hex(a): hex(v) for a,v in values.items()}}
            if result['complete']:
                result.update(pin10sel_gpio=values[0x10d13028] & 15 == 8,
                              gpio0_bit10_output=bool(values[0x10c03204] & (1 << 10)),
                              gpio0_bit10_input_high=bool(values[0x10c03250] & (1 << 10)))
            (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
            print(out)
            print(json.dumps(result, indent=2))
            return int(not result['complete'])
        finally:
            client.close()


if __name__ == '__main__':
    raise SystemExit(main())
