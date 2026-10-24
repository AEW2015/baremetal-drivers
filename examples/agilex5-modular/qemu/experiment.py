#!/usr/bin/env python3
"""Predict, break, and recover independent checks in temporary copies; no board access."""
from pathlib import Path
import subprocess,sys,tempfile,shutil

def run(root):
    subprocess.run(['bash',str(root/'qemu/build.sh')],check=True,capture_output=True)
    return subprocess.run([sys.executable,str(root/'qemu/run.py'),'--check'],capture_output=True,text=True,timeout=30)

def verify(label, result, expected_status, *markers):
    output = result.stdout + result.stderr
    if result.returncode != expected_status or any(marker not in output for marker in markers):
        raise RuntimeError(f'{label}: unexpected result (runner exit {result.returncode}).\n'+output)
    for check in ('NEON', 'MEMORY'):
        lines = result.stdout.splitlines()
        if any(line.startswith(f'PASS {check}:') for line in lines) and f'FAIL {check}' in lines:
            raise RuntimeError(f'{label}: contradictory {check} diagnostics.\n'+output)
    if expected_status == 1 and 'PASS QEMU_CHECK' in output:
        raise RuntimeError(f'{label}: failed run claimed success.\n'+output)
    if expected_status == 1 and 'QEMU check failed (exit 1)' not in output:
        raise RuntimeError(f'{label}: expected guest/QEMU exit 1.\n'+output)
    print(f'{label}: runner exit {result.returncode}', flush=True)
    print(output, end='', flush=True)

def main():
    original=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='agilex-student-') as folder:
        root=Path(folder);shutil.copytree(original,root/'qemu',ignore=shutil.ignore_patterns('__pycache__'))
        source=root/'qemu/hello.c';runner=root/'qemu/run.py'
        pristine=source.read_text()
        baseline=run(root)
        verify('BASELINE',baseline,0,'PASS NEON','PASS MEMORY','PASS QEMU_CHECK')
        print('BASELINE: vector {11,22,33,44}; all checks pass.')
        source.write_text(source.read_text().replace('vector_b[4]={10,20,30,40}','vector_b[4]={11,20,30,40}'))
        broken=run(root)
        verify('MISMATCH',broken,1,'FAIL NEON','PASS MEMORY','QEMU EXAMPLE FAILED')
        print('MISMATCH: predicted vector {12,22,33,44}; old expectation fails; memory still passes.')
        source.write_text(source.read_text().replace('vector_result[i]!=(i+1)*11','vector_result[i]!=(i==0?12:(i+1)*11)').replace('PASS NEON: 11 22 33 44','PASS NEON: 12 22 33 44'))
        runner.write_text(runner.read_text().replace('PASS NEON: 11 22 33 44','PASS NEON: 12 22 33 44'))
        fixed=run(root)
        verify('CORRECTED',fixed,0,'PASS NEON: 12 22 33 44','PASS QEMU_CHECK')
        print('CORRECTED: expected values and marker agree; all checks pass.')
        runner.write_text((original/'run.py').read_text())
        # Inject after computation, before validation; keep checks unchanged.
        neon_anchor='for(unsigned i=0;i<4;i++)if(vector_result[i]'
        memory_anchor='for(unsigned i=0;i<512;i++)if(destination[i]'
        for label,anchor,injection,markers in [
            ('NEON_RESULT',neon_anchor,'vector_result[0]^=1;\n ',('FAIL NEON','PASS MEMORY')),
            ('LAST_WORD',memory_anchor,'destination[511]^=1;\n ',('PASS NEON','FAIL MEMORY')),
        ]:
            if pristine.count(anchor)!=1:raise RuntimeError(f'{label}: injection location changed; update exercise.')
            source.write_text(pristine.replace(anchor,injection+anchor,1))
            verify(label,run(root),1,*markers,'QEMU EXAMPLE FAILED')
        source.write_text(pristine)
        verify('RECOVERED',run(root),0,'PASS NEON: 11 22 33 44','PASS MEMORY','PASS QEMU_CHECK')
        print('RECOVERED: original values restored; original checkout unchanged.')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:print(f'ERROR: {exc}',file=sys.stderr);raise SystemExit(1)
