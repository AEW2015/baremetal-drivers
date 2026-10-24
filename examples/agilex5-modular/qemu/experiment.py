#!/usr/bin/env python3
"""Predict, break, and fix NEON in temporary source copies; no board access."""
from pathlib import Path
import subprocess,sys,tempfile,shutil

def run(root):
    subprocess.run(['bash',str(root/'qemu/build.sh')],check=True,capture_output=True)
    return subprocess.run([sys.executable,str(root/'qemu/run.py'),'--check'],capture_output=True,text=True,timeout=30)

def main():
    original=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='agilex-student-') as folder:
        root=Path(folder);shutil.copytree(original,root/'qemu',ignore=shutil.ignore_patterns('__pycache__'))
        source=root/'qemu/hello.c';runner=root/'qemu/run.py'
        baseline=run(root)
        if baseline.returncode:raise RuntimeError(baseline.stdout+baseline.stderr)
        print('BASELINE: vector {11,22,33,44}; all checks pass.')
        source.write_text(source.read_text().replace('vector_b[4]={10,20,30,40}','vector_b[4]={11,20,30,40}'))
        broken=run(root)
        if not broken.returncode or 'FAIL NEON' not in broken.stdout or 'PASS MEMORY' not in broken.stdout:
            raise RuntimeError('The deliberate mismatch did not fail independently as expected.\n'+broken.stdout+broken.stderr)
        print('MISMATCH: predicted vector {12,22,33,44}; old expectation fails; memory still passes.')
        source.write_text(source.read_text().replace('vector_result[i]!=(i+1)*11','vector_result[i]!=(i==0?12:(i+1)*11)').replace('PASS NEON: 11 22 33 44','PASS NEON: 12 22 33 44'))
        runner.write_text(runner.read_text().replace('PASS NEON: 11 22 33 44','PASS NEON: 12 22 33 44'))
        fixed=run(root)
        if fixed.returncode or 'PASS NEON: 12 22 33 44' not in fixed.stdout:raise RuntimeError(fixed.stdout+fixed.stderr)
        print('CORRECTED: expected values and marker agree; all checks pass; original checkout unchanged.')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:print(f'ERROR: {exc}',file=sys.stderr);raise SystemExit(1)
