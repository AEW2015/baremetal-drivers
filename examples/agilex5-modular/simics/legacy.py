#!/usr/bin/env python3
"""Container: run the explicitly pinned 25.1 sample suite on Simics 26.3."""
import argparse,json,re,subprocess,sys
from pathlib import Path
from support import ROOT,PROJECT,digest,new_run,execute,save
sys.path.insert(0,str(ROOT))
from legacy_source import ensure,COMMIT
NAMES=['hello-world','uart','dma','timer','watchdog','i2c','i3c','spi','sdmmc','xgmac','mmu_el3','smmu','ccu','clkmgr','ecc','hps_mailbox']

def adapt(text,source,image_root):
    text=text.replace('sim->workspace','sim->project').replace('/targets/sm-hps/agilex5e-universal.simics','/targets/agilex5e-universal/agilex5e-universal.simics').replace('run-command-file','run-script')
    for key in ('fsbl_elf_filename','fsbl_image_filename'):
        text=re.sub(r'(\$'+key+r' = )"([^"]+)"',lambda m:m[1]+json.dumps(str((image_root/m[2]).resolve())),text)
    # Capture the actual exit argument, before puts clobbers X0 on Hello's marker.
    text=text.replace('$bp_ID = (bp.console_string.break $con -regexp "__(PASS|FAIL)__")','$bp_ID = (bp.memory.break -x (dbg0.sym-address "exit"))')
    text=text.replace('exit $test_result_value','echo "SIMICS_TEST_RETURN"\n        echo $test_result_value\n        exit $test_result_value')
    return 'add-directory '+json.dumps(str(source.parent))+'\n'+text

def assess_legacy(body,code):
    marker=re.search(r'^SIMICS_TEST_RETURN\n(0x[0-9a-fA-F]+|[0-9]+)\n',body,re.M)
    guest=int(marker[1],0) if marker else None
    passed=code==0 and guest==0 and 'Reached exit' in body and '__FAIL__' not in body
    return passed,guest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--only',default='hello-world',help='Comma-separated names; --all runs all 16')
    p.add_argument('--all',action='store_true');p.add_argument('--build',action='store_true')
    p.add_argument('--project',type=Path,default=PROJECT);p.add_argument('--timeout',type=int,default=40)
    a=p.parse_args();names=NAMES if a.all else a.only.split(',')
    if any(n not in NAMES for n in names):p.error('Choose '+','.join(NAMES))
    if not 1<=a.timeout<=300:p.error('timeout must be 1..300 seconds')
    source=ensure();scripts={n:source/'test/simics'/n/'test.simics' for n in names}
    if a.build:
        subprocess.run(['bash',str(ROOT/'configure_vendor.sh')],cwd=ROOT,check=True)
        targets=[Path(re.search(r'\$fsbl_elf_filename = "([^"]+)"',s.read_text())[1]).name for s in scripts.values()]
        subprocess.run(['cmake','--build',str(ROOT/'build/legacy-vendor'),'--target',*targets,'-j4'],check=True)
    out=new_run('legacy25');record={'scope':'legacy 25.1 reference tests, not the rewritten 26.3 APIs','legacy_commit':COMMIT,'tests':[]}
    for name,s in scripts.items():
        original=s.read_text();elf=source/re.search(r'\$fsbl_elf_filename = "([^"]+)"',original)[1]
        if not elf.is_file():p.error('Build the selected OCRAM image first with --build')
        target=out/name;target.mkdir();path=target/'test.simics';path.write_text(adapt(original,s,source))
        code,seconds,body=execute(a.project,path,target/'terminal.log',a.timeout)
        passed,guest=assess_legacy(body,code)
        item={'name':name,'status':'pass' if passed else 'timeout' if code==124 else 'fail','guest_return':guest,'simulator_exit':code,'seconds':seconds,'elf_sha256':digest(elf),'script_sha256':digest(path)}
        record['tests'].append(item);save(out,record)
        print(('PASS ' if passed else 'FAIL ')+name,flush=True)
    return 0 if all(x['status']=='pass' for x in record['tests']) else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(1)
