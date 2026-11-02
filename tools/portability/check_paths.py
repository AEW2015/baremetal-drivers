#!/usr/bin/env python3
"""Reject personal bench paths in maintained entry points; preserve historical evidence."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BANNED=('/home/lada/', '/workspace/baremetal-fixes-', 'current-stack-env.sh')
files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
failures=[]
for name in files:
    path=Path(name)
    if path == Path('tools/portability/check_paths.py'):continue
    if not name or any(part in {'validation','runs','build','tests','vendor'} for part in path.parts):continue
    if path.suffix not in {'.md','.py','.sh','.yml','.yaml','.code-workspace'}:continue
    for number,line in enumerate((ROOT/path).read_text(encoding='utf-8').splitlines(),1):
        if any(token in line for token in BANNED):failures.append(f'{name}:{number}')
if failures:raise SystemExit('Personal paths in maintained files: '+', '.join(failures))
print('PASS portable paths; historical captures are unchanged')
