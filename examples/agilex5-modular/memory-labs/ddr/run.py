#!/usr/bin/env python3
"""QEMU functional checks for the DDR-path guest; never qualifies physical timing."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SIZES=(65536,262144,1048576,4194304,16777216)
OPS=('read','write','copy','dependent-load')
SAMPLE=re.compile(r'^DDR_SAMPLE op=([\w-]+) working_set_bytes=(\d+) ticks=(\d+) payload_bytes=(\d+) accesses=(\d+) checksum=(\d+)$',re.M)

def assess(output,returncode):
    lines=output.splitlines()
    matches=list(SAMPLE.finditer(output))
    required=['DDR_MMU_AND_DCACHE_INITIALLY_OFF','DDR_DECLARED_TIMER_FREQUENCY_RANGE',
              'DDR_TIMER_ADVANCES','DDR_TRANSLATION_STATE_RESTORED','DDR_SWEEP_COMPLETE']
    valid=(returncode==0 and 'LAB BEGIN ddr-path' in lines and 'LAB COMPLETE' in lines
           and 'LAB FAILED' not in lines and not any(l.startswith('FAIL ') for l in lines)
           and all('PASS '+name in lines for name in required)
           and lines.count('PASS DDR_READ_CHECKSUM')==5
           and lines.count('PASS DDR_DEPENDENT_RING_INTEGRITY')==5
           and lines.count('PASS DDR_NONZERO_SAMPLE_TICKS')==20
           and len(matches)==20 and {(m[1],int(m[2])) for m in matches}=={(op,size) for op in OPS for size in SIZES}
           and all(int(m[3])>0 for m in matches))
    freq=re.search(r'^DDR_TIMER frequency_hz=(\d+)$',output,re.M)
    valid=valid and freq is not None and 1000000<=int(freq[1])<=2000000000
    samples=[]
    for m in matches:
        op,size,ticks,payload,accesses,checksum=m.groups()
        expected_accesses=int(size)//(64 if op=='dependent-load' else 8)*2
        expected_bytes=expected_accesses*8
        valid=valid and int(accesses)==expected_accesses and int(payload)==expected_bytes
        item=dict(op=op,working_set_bytes=int(size),ticks=int(ticks),payload_bytes=int(payload),accesses=int(accesses),checksum=int(checksum))
        if freq and int(ticks):
            item['emulated_declared_seconds']=int(ticks)/int(freq[1])
            item['emulated_payload_bytes_per_second']=int(payload)*int(freq[1])/int(ticks)
            if op=='dependent-load':item['emulated_ns_per_load']=int(ticks)*1e9/(int(freq[1])*int(accesses))
        samples.append(item)
    return bool(valid),samples

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifacts',type=Path,default=ROOT/'build/memory-ddr-qemu')
    p.add_argument('--qemu',default=os.environ.get('QEMU','qemu-system-aarch64'))
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    out=args.output or Path(__file__).parent/'validation'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True,exist_ok=True)
    results={'scope':'QEMU TCG functional execution only; no hardware DDR latency/bandwidth claim',
             'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'qemu_version':subprocess.check_output([args.qemu,'--version'],text=True).splitlines()[0],
             'build':json.loads((args.artifacts/'build.json').read_text()),'tests':[]}
    if results['build']['target']!='qemu':p.error('Use a QEMU-target build, not an Agilex memory map')
    for name,expected in [('ddr-path',None),('ddr-copy-fault','DDR_COPY_READBACK'),('ddr-clock-fault','DDR_DECLARED_TIMER_FREQUENCY_RANGE')]:
        elf=args.artifacts/(name+'.elf')
        actual_hash=hashlib.sha256(elf.read_bytes()).hexdigest()
        if results['build']['artifacts'].get(elf.name)!=actual_hash:raise RuntimeError('ELF differs from build.json: '+str(elf))
        command=[args.qemu,'-machine','virt,secure=on,virtualization=on,gic-version=3','-cpu','cortex-a53','-accel','tcg','-smp','1','-nic','none','-m','128M','-display','none','-monitor','none','-serial','stdio','-semihosting-config','enable=on,target=native','-device',f'loader,file={elf},cpu-num=0']
        try:
            proc=subprocess.run(command,capture_output=True,timeout=90)
            raw=proc.stdout+proc.stderr;code=proc.returncode
        except subprocess.TimeoutExpired as exc:
            raw=(exc.stdout or b'')+(exc.stderr or b'');code=-1
        (out/(name+'.log')).write_bytes(raw)
        output=raw.decode(errors='replace').replace('\r','')
        accepted,samples=assess(output,code)
        passed=accepted if expected is None else (not accepted and code>0 and 'LAB BEGIN ddr-path' in output.splitlines() and 'FAIL '+expected in output.splitlines() and 'LAB FAILED' in output.splitlines() and 'LAB COMPLETE' not in output.splitlines())
        item={'name':name,'status':'pass' if passed else 'fail','negative_control':expected is not None,'expected_failure':expected,'returncode':code,'command':command,'elf_sha256':actual_hash,'samples':samples}
        results['tests'].append(item)
        print(('PASS ' if passed else 'FAIL ')+name)
    results['passed']=all(t['status']=='pass' for t in results['tests'])
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(out)
    return int(not results['passed'])

if __name__=='__main__':raise SystemExit(main())
