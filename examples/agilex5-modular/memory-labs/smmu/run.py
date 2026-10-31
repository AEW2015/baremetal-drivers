#!/usr/bin/env python3
"""Run real QEMU SMMUv3/EDU models and verify positive and deliberate failures."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent
PACK=ROOT.parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu',default='qemu-system-aarch64')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    out=args.out or ROOT/'validation'/('qemu-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    out.mkdir(parents=True,exist_ok=False)
    build=PACK/'build/memory-smmu'
    manifest=json.loads((build/'build.json').read_text())
    results={'scope':manifest['scope'],'qemu_version':subprocess.check_output([args.qemu,'--version'],text=True).splitlines()[0],
             'build':manifest,'runner_sha256':digest(Path(__file__)),'tests':[]}
    reasons={'bypass':'translated EDU DMA round trip verifies all 4096 bytes',
             'keep-mapping':'unmapped DMA did not produce an SMMU event'}
    for name in ['normal','bypass','keep-mapping']:
        image=build/(name+'.elf')
        if digest(image)!=manifest['artifacts_sha256'][image.name]:
            raise RuntimeError('ELF changed since recorded build: '+str(image))
        command=[args.qemu,'-machine','virt,iommu=smmuv3,secure=on,virtualization=on,highmem=off',
                 '-cpu','cortex-a57','-m','256M','-net','none','-device','edu,addr=1.0,dma_mask=4294967295',
                 '-global','arm-smmuv3.stage=2','-display','none','-serial','stdio','-monitor','none',
                 '-semihosting-config','enable=on,target=native','-device','loader,file='+str(image)+',cpu-num=0']
        try:
            run=subprocess.run(command,capture_output=True,timeout=15)
            raw=run.stdout+run.stderr
            text=raw.decode(errors='replace').replace('\r','')
            if name=='normal':
                event={k:int(v,16) for k,v in re.findall(r'^(event word0|event address)=0x([0-9a-f]+)$',text,re.M)}
                passed=(run.returncode==0 and 'LAB COMPLETE\n' in text and 'FAIL ' not in text
                        and 'PASS translated EDU DMA round trip verifies all 4096 bytes\n' in text
                        and 'PASS faulting DMA left all 4096 guard bytes unchanged\n' in text
                        and event.get('event word0')==(8<<32)|0x10
                        and event.get('event address')==0x60200000)
            else:
                passed=(run.returncode==1 and 'FAIL '+reasons[name]+'\n' in text
                        and 'LAB FAILED\n' in text and 'LAB COMPLETE' not in text)
            item={'name':name,'status':'pass' if passed else 'fail','expected_negative':name!='normal',
                  'guest_exit_status':run.returncode,'command':command,'elf_sha256':digest(image)}
        except subprocess.TimeoutExpired as exc:
            raw=(exc.stdout or b'')+(exc.stderr or b'')
            item={'name':name,'status':'fail','error':'QEMU timeout; not an accepted negative result','command':command}
        (out/(name+'.log')).write_bytes(raw)
        results['tests'].append(item)
        print(('PASS ' if item['status']=='pass' else 'FAIL ')+name)
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Evidence:',out)
    return int(any(t['status']!='pass' for t in results['tests']))

if __name__=='__main__':
    raise SystemExit(main())
