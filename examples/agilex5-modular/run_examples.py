#!/usr/bin/env python3
"""Compatibility entry point for the locked, evidence-recording suite runner."""
import argparse,pathlib,subprocess,sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('example',choices=['core','dma'])
p.add_argument('--port')
a=p.parse_args()
cmd=[sys.executable,str(pathlib.Path(__file__).with_name('run_suite.py')),'--only',a.example]
if a.port:cmd+=['--port',a.port]
raise SystemExit(subprocess.call(cmd))
