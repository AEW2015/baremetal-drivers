#!/usr/bin/env python3
"""Deploy a fabric lesson with matching generated full images, not a PR image."""
import argparse,json,os,signal,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bench import ROOT,BenchError,HELP,digest,verify_mapped_files,verify_mount
import run_suite

def verify():
    try:
        image=json.loads((ROOT/'bootstrap/ddr/build-manifest.json').read_text())
        build=json.loads((ROOT/'build/fabric-build.json').read_text())
        if image['lwh2f_enabled'] is not True:
            raise BenchError('Repackage with AGILEX_ENABLE_LWH2F=1; the ordinary DDR hook skips bridge enable.')
        for name in ('ddr_probe.hps.rbf','ddr_recovery.sof'):
            if digest(ROOT/'bootstrap/ddr'/name)!=image['images'][name]:
                raise BenchError('DDR image hash differs from its build manifest; repackage matching images.')
        if digest(ROOT/'build/fabric_example.elf')!=build['elf_sha256']:
            raise BenchError('Fabric ELF hash differs from its build metadata; rebuild.')
        base=build['cpu_base']
        if not isinstance(base,int) or base<0x20000000 or base+64>0x40000000 or base%64:
            raise BenchError('CPU base must be a 64-byte aligned register window within LWH2F.')
        return base
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise BenchError('Missing/invalid fabric build metadata. Build fabric ELF and repackage the matching SOF with AGILEX_ENABLE_LWH2F=1.') from exc

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--persona',required=True,choices=['add','xor'])
    p.add_argument('--port',default=os.environ.get('AGILEX_UART',''))
    p.add_argument('--run',action='store_true',help='Program the matched full volatile image, test, restore DDR Hello')
    a=p.parse_args()
    if not a.run:
        base=verify();print(f'Build metadata verified; CPU CSR base 0x{base:08x}. No programming performed.')
        print('This verifies file pairing, not that this SOF contains the IP at that address. Check the Platform Designer map and bridge timing, then repeat with --run.')
        return 0
    persona={'add':'41444431','xor':'584f5231'}[a.persona]
    run_suite.TESTS['fabric']={'elf':'fabric_example','entry':0x82100000,
        'markers':['HPS FABRIC IP BEGIN','PERSONA = 0x00000000'+persona,
                   'PASS FABRIC_MATH','PASS FABRIC_QUIESCE','HPS FABRIC IP COMPLETE']}
    def preflight():
        verify()
        verify_mapped_files([ROOT/'bootstrap/ddr/build-manifest.json',ROOT/'build/fabric-build.json'])
    sys.argv=[sys.argv[0],'--only','fabric','--port',a.port,'--full-recovery']
    return run_suite.main(preflight=preflight)

if __name__=='__main__':
    def stop(*_):raise KeyboardInterrupt
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,stop)
    try:raise SystemExit(main())
    except KeyboardInterrupt:print('Interrupted; inspect hardware run/restoration logs.',file=sys.stderr);raise SystemExit(130)
    except (BenchError,OSError) as exc:print(f'ERROR: {exc}\nHelp: {HELP}',file=sys.stderr);raise SystemExit(1)
