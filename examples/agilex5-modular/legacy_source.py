#!/usr/bin/env python3
"""Fetch the immutable 25.1 API used by the recorded Modular/legacy Simics labs."""
import os
from pathlib import Path
import subprocess
import sys
COMMIT='1419101568f1a9034630b632634fe9fe71773266'
URL='https://github.com/altera-fpga/baremetal-drivers.git'
ROOT=Path(__file__).resolve().parent

def git(path,*args):
    return subprocess.check_output(['git','-C',str(path),*args],text=True,stderr=subprocess.PIPE,timeout=180).strip()

def ensure():
    supplied=os.environ.get('AGILEX_LEGACY_SOURCE')
    path=Path(supplied).expanduser().resolve() if supplied else ROOT/'.deps/baremetal-25.1'
    if not (path/'.git').exists():
        if supplied:raise RuntimeError('AGILEX_LEGACY_SOURCE must be a Git checkout of '+COMMIT)
        if path.exists() and any(path.iterdir()):raise RuntimeError('Legacy dependency directory is not an empty Git checkout: '+str(path))
        path.mkdir(parents=True,exist_ok=True)
        git(path,'init','-q');git(path,'remote','add','origin',URL)
        git(path,'fetch','--depth','1','origin',COMMIT);git(path,'checkout','--detach','FETCH_HEAD')
    if git(path,'rev-parse','HEAD')!=COMMIT:raise RuntimeError('Legacy source revision mismatch; require '+COMMIT)
    if git(path,'status','--porcelain','--untracked-files=no'):raise RuntimeError('Legacy dependency has modified tracked files: '+str(path))
    return path

if __name__=='__main__':
    try:print(ensure())
    except (RuntimeError,subprocess.SubprocessError) as exc:
        print('Legacy source unavailable: '+str(exc),file=sys.stderr);raise SystemExit(1)
