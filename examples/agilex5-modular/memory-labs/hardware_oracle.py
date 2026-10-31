"""Outcome checks for standalone EL3 memory guests captured by the bench runner."""
import importlib.util
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def module(name):
    spec=importlib.util.spec_from_file_location('memory_'+name,ROOT/name/'run.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result
DDR_NAMES=['ddr-path','ddr-calibrated','ddr-copy-fault','ddr-clock-fault']
DSU_NAMES=['normal','corrupt','stalled','contention','partitioned']
def assess(kind,name,body,code):
    marker='LAB BEGIN '+('ddr-path' if kind=='ddr' else 'dsu')
    start=body.find(marker)
    if start<0 or code!=0:return 'fail'
    calibrated_markers=True
    if name=='ddr-calibrated':
        prefix=body[:start].replace('\r','')
        begin=body.find('COUNTER_INTERVAL_START')
        end=body.find('COUNTER_INTERVAL_END')
        checks=('DDR_CALIBRATION_EL3_CACHE_OFF','DDR_CALIBRATION_DECLARED_400MHZ',
                'DDR_COUNTER_ADVANCES_BEFORE_CALIBRATION','DDR_CALIBRATION_INTERVAL_COMPLETE')
        declared=re.findall(r'^DDR_CALIBRATION_DECLARED_HZ=0x([0-9a-fA-F]+)$',prefix,re.M)
        samples=re.findall(r'^DDR_CALIBRATION ticks=(\d+) polls=(\d+)$',prefix,re.M)
        calibrated_markers=(body.count('COUNTER_INTERVAL_START')==1 and
                            body.count('COUNTER_INTERVAL_END')==1 and 0<=begin<end<start and
                            all(prefix.splitlines().count('PASS '+x)==1 for x in checks) and
                            'FAIL ' not in prefix and 'LAB FAILED' not in prefix and
                            len(declared)==1 and int(declared[0],16)==400000000 and
                            len(samples)==1 and int(samples[0][0])>=400000000 and
                            int(samples[0][1])<268435456)
    body=body[start:].replace('\r','')
    if kind=='dsu':return module('dsu').assess_target(name,body,code)
    if name not in DDR_NAMES:return 'fail'
    accepted,_=module('ddr').assess(body,code)
    if name in ('ddr-path','ddr-calibrated'):
        return 'pass' if accepted and calibrated_markers else 'fail'
    lines=body.splitlines()
    expected='DDR_COPY_READBACK' if name=='ddr-copy-fault' else 'DDR_DECLARED_TIMER_FREQUENCY_RANGE'
    return 'pass' if not accepted and 'FAIL '+expected in lines and 'LAB FAILED' in lines and 'LAB COMPLETE' not in lines else 'fail'
