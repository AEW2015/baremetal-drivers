#!/usr/bin/env python3
"""Execute four-vCPU QEMU functional controls; never label TCG timing as L3 timing."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
NAMES=['normal','corrupt','stalled','contention','partitioned']

def _assess(name,body,code,target):
    name={'shared-contention':'contention'}.get(name,name)
    if name not in NAMES or (target=='qemu' and name=='partitioned'):return False
    body=body.replace('\r','')
    if 'LAB BEGIN dsu' in body:body=body[body.index('LAB BEGIN dsu'):]
    lines=body.splitlines()
    if 'LAB BEGIN dsu' not in lines:return False
    if name in ('corrupt','stalled'):
        marker='DSU_PAYLOAD_MISMATCH' if name=='corrupt' else 'DSU_PRODUCER_TIMEOUT'
        return (code==(1 if target=='qemu' else 0) and 'FAIL '+marker in lines and
                'PASS SECONDARIES_CLEANED_AND_QUIESCENT_ON_FAILURE' in lines and
                'FAIL DSU_POLICY_RESTORE' not in lines and 'FAIL DSU_QUIESCENCE_TIMEOUT reset_required' not in lines and
                'LAB FAILED' in lines and 'LAB COMPLETE' not in lines)
    partition_ok=True
    if name=='partitioned':
        def value(key):
            values=[line.split('=',1)[1] for line in lines if line.startswith(key+'=')]
            try:return int(values[0],16) if len(values)==1 else None
            except ValueError:return None
        saved,active,restored=(value(k) for k in ['PARTCR_SAVED','PARTCR_ACTIVE','PARTCR_RESTORED'])
        partition_ok=(None not in (saved,active,restored) and saved&255==0 and
                      active==((saved&~255)|0x1e) and restored==saved and
                      lines.count('PASS SECONDARY_POLICY_RESTORED')==3 and
                      'PASS CLUSTER_POLICY_RESTORED' in lines and 'PASS PRIMARY_POLICY_RESTORED' in lines)
    return (partition_ok and (name not in ('contention','partitioned') or ('PASS CONTENTION_WORKLOAD_COMPLETE' in lines and
             lines.count('PASS HAMMER_EXECUTED_DURING_PROBE')==2 and
             'PASS DEPENDENT_PROBE_COMPLETED' in lines)) and
            code==0 and 'LAB COMPLETE' in lines and 'LAB FAILED' not in lines and
            not any(x.startswith('FAIL ') for x in lines) and
            lines.count('PASS SECONDARY_CACHE_MMU_ENABLED')==3 and
            lines.count('PASS SECONDARY_WB_INNER_SHAREABLE_TRANSLATION')==3 and
            lines.count('PASS CONSUMER_FULL_PAYLOAD_VERIFIED')==3 and
            'PASS THREE_CACHED_CONSUMERS_VERIFIED' in lines and
            'PASS SECONDARIES_CLEANED_AND_QUIESCENT' in lines and
            lines.count('WORDS_CHECKED=0x0000000000020000')==3 and
            (target!='qemu' or 'INFO QEMU_FUNCTIONAL_MODEL_NOT_PHYSICAL_CACHE_OR_L3_TIMING' in lines))

def assess(name,code,body):
    return _assess(name,body,code,'qemu')

def assess_target(name,body,process_code):
    """Hardware/Simics runners return 0 when capture succeeds, including guest FAIL controls."""
    return 'pass' if _assess(name,body,process_code,'agilex5') else 'fail'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'build/dsu-qemu')
    p.add_argument('--output',type=Path)
    p.add_argument('--qemu',default='qemu-system-aarch64')
    a=p.parse_args()
    build=json.loads((a.build/'build.json').read_text())
    if build['target']!='qemu':p.error('Only QEMU build artifacts can use this runner')
    out=a.output or ROOT/'runs'/('dsu-qemu-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    out.mkdir(parents=True,exist_ok=False)
    results={'scope':'QEMU TCG functional execution; no physical DSU cache, L3 partition or bandwidth qualification',
             'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'qemu':subprocess.check_output([a.qemu,'--version'],text=True).splitlines()[0],
             'build':build,'tests':[]}
    for name in ['normal','corrupt','stalled','contention']:
        elf=a.build/(name+'.elf');digest=hashlib.sha256(elf.read_bytes()).hexdigest()
        if digest!=build['artifacts'][elf.name]:raise RuntimeError('Build artifact hash changed: '+str(elf))
        cmd=[a.qemu,'-machine','virt,secure=on,virtualization=on,gic-version=3','-cpu','cortex-a53',
             '-accel','tcg','-smp','4','-nic','none','-m','128M','-display','none','-monitor','none',
             '-serial','stdio','-semihosting-config','enable=on,target=native',
             '-device',f'loader,file={elf},cpu-num=0']
        for cpu in range(1,4):cmd+=['-device',f'loader,addr=0x40200000,cpu-num={cpu}']
        try:
            run=subprocess.run(cmd,capture_output=True,timeout=25)
            body=(run.stdout+run.stderr).decode(errors='replace');code=run.returncode
        except subprocess.TimeoutExpired as e:
            body=((e.stdout or b'')+(e.stderr or b'')).decode(errors='replace');code=124
        (out/(name+'.log')).write_text(body)
        passed=assess(name,code,body)
        results['tests'].append({'name':name,'passed':passed,'returncode':code,'elf_sha256':digest,'command':cmd})
        print(('PASS' if passed else 'FAIL')+' DSU_QEMU_'+name.upper(),flush=True)
    results['passed']=all(t['passed'] for t in results['tests'])
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(out)
    return int(not results['passed'])

if __name__=='__main__':raise SystemExit(main())
