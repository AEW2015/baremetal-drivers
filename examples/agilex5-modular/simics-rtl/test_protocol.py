#!/usr/bin/env python3
"""Host-only checks of the Verilator transactor protocol; not Simics coverage."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'runs/simics-rtl-protocol.json')
    args=p.parse_args();results=[]
    for mode,result in [(1,'c'),(2,'2')]:
        executable=ROOT/f'build/simics-rtl/mode{mode}/Vlab_ip'
        r=subprocess.run([str(executable)],input='R 0\nW 14 7\nW 18 5\nW c 1\nR 1c\nQ\n',text=True,capture_output=True,timeout=5)
        lines=r.stdout.splitlines()
        assert r.returncode==0 and lines==['READY 1','OK 4c414231 4','OK 0 6','OK 0 8','OK 0 a','OK '+result+' c','BYE'],(mode,r)
        results.append({'mode':mode,'check':'real RTL arithmetic and exact cycle sequence','status':'pass'})
        for label,request in [('unaligned','R 3\n'),('out-of-range','R 40\n'),('missing-value','W 14\n'),('overlong','R '+'0'*100+'\n')]:
            r=subprocess.run([str(executable)],input=request,text=True,capture_output=True,timeout=5)
            assert r.returncode==2 and r.stdout.startswith('READY 1\nERR '),(label,r)
            results.append({'mode':mode,'check':label+' rejected','status':'pass'})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'scope':'Host-only Verilator transactor protocol; independent of actual Simics guest execution','tests':results},indent=2)+'\n')
    print('PASS SIMICS_RTL_PROTOCOL: '+str(len(results))+' checks; actual ADD/XOR RTL and malformed requests')
if __name__=='__main__':main()
