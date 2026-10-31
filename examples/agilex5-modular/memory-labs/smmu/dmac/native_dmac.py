# SPDX-License-Identifier: MIT-0
"""Simics host fixture for a real guest-programmed DMAC0 transfer.

No Python-issued ingress transactions: Python writes configuration/PTEs,
observes physical data/events, and releases the guest's uncached phase flag.
"""
import json
from pathlib import Path
from cli import run_command
from simics import SIM_quit
from native_fixture import NativeTBUFixture

SRC_IOVA=0x85000000
DST_IOVA=0x85200000
LLI_IOVA=0x85600000
SRC_PA=0x86000000
DST_PA=0x86200000
LLI_PA=0x86400000
CONTROL=0x86600000
DMAC=0x10db0000
fixture=None
output=None
record={}

def pattern(phase,i):return 0x1234567800000000^(phase<<48)^i
def guard(i):return 0xa5a5a5a5a5a5a5a5^i
def save():
    if output:Path(output).write_text(json.dumps(record,indent=2)+'\n')
def capture_failure():
    try:
        run_command('$failed_uart = ($con.record-stop)')
        run_command('echo "UART_RECORD_BEGIN"')
        run_command('echo $failed_uart')
        run_command('echo "UART_RECORD_END"')
    except Exception as exc:print('DMAC_FAILURE_CAPTURE_ERROR',repr(exc))
def safe(fn,*args):
    try:return fn(*args)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        record['passed']=False;record['error']=repr(exc)
        if fixture is not None:
            record['failure_snapshot']={'control':[fixture.read(CONTROL+i*8,8) for i in range(3)],
                'chen':hex(fixture.read(DMAC+0x18,8)),
                'channel_status':hex(fixture.read(DMAC+0x188,8)),
                'fault':fixture.fault()}
            fixture.close()
        save();capture_failure();SIM_quit(1)

def configure(path):
    global fixture,output,record
    output=path
    fixture=NativeTBUFixture('dma0',SRC_IOVA,SRC_PA)
    record={'scope':'AArch64 guest programs real native DMAC0; host only configures native SMMU stage2 and removes destination mapping',
            'python_issued_dma_transactions':False,'tlbi_scope':'Native TLB cache disabled; fresh walks only, no command queue/TLBI qualification',
            'hardware_scope':'Not ported or run on physical hardware','passed':False}
    record['dma_cfg_before']=fixture.read(DMAC+0x10,8)
    record['configuration']=fixture.configure()
    fixture.map_block(DST_IOVA,DST_PA)
    fixture.map_block(LLI_IOVA,LLI_PA)
    record['configuration']=fixture.observations
    save()
    print('PASS NATIVE_DMAC_THREE_NONIDENTITY_MAPS_CONFIGURED')

def verify_aliases():
    for address in (SRC_IOVA,DST_IOVA,LLI_IOVA):
        for i in range(512):
            assert fixture.read(address+i*8,8)==guard(i),'Raw IOVA alias changed: '+hex(address+i*8)

def after_phase1():
    assert fixture.read(CONTROL,8)==1,'Guest did not complete native DMAC translated copy'
    for i in range(512):
        assert fixture.read(SRC_PA+i*8,8)==pattern(1,i),'Physical source mismatch'
        assert fixture.read(DST_PA+i*8,8)==pattern(1,i),'Native DMA did not reach mapped physical destination'
    verify_aliases()
    assert fixture.fault()['producer']==0,'Valid engine transfer generated SMMU fault'
    record['phase1']={'passed':True,'bytes_checked':4096,'raw_alias_guard_bytes':3*4096,
                      'channel_status':hex(fixture.read(DMAC+0x188,8))}
    fixture.unmap(DST_IOVA)
    assert fixture.smmu.tlb_cache_enable is False,'Fresh-walk fixture no longer applicable'
    fixture.write(CONTROL+8,0xface2,8)
    record['configuration']=fixture.observations
    save()
    print('PASS NATIVE_DMAC_PHASE1_PA_AND_ALIAS_READBACK bytes=4096')
    print('NATIVE_DMAC_DEST_UNMAPPED '+json.dumps(fixture.observations,sort_keys=True))

def finish():
    assert fixture.read(CONTROL,8)==2 and fixture.read(CONTROL+16,8)==0x600d,'Guest did not complete checked fault phase'
    for i in range(512):
        assert fixture.read(SRC_PA+i*8,8)==pattern(2,i),'Second source pattern missing'
        assert fixture.read(DST_PA+i*8,8)==pattern(1,i),'Unmapped destination guard changed'
    verify_aliases()
    event=fixture.fault();words=event['words']
    assert event['producer']>0 and words[0]&255==0x10,'Expected native translation event missing'
    assert words[0]>>32==8 and words[1]&(1<<39),'Fault does not report DMA SID8/stage2'
    assert words[2]==DST_IOVA,'Native fault IOVA differs from destination'
    assert event['global_error']==0,'Unexpected SMMU global error'
    assert fixture.read(DMAC+0x18,8)&15==0,'DMA channels not quiescent'
    assert fixture.read(DMAC+0x10,8)==record['dma_cfg_before'],'DMA global configuration not restored'
    record['fault']=event
    record['phase2']={'passed':True,'unchanged_destination_bytes':4096,'raw_alias_guard_bytes':3*4096,
                      'channel_enable':hex(fixture.read(DMAC+0x18,8))}
    fixture.close()
    record['fixture_restored']={'cr0':hex(fixture.read(fixture.REG+0x20)),
                              'dma_sid':hex(fixture.read(0x10d121a8)),
                              'dma_stream_control':hex(fixture.read(0x10d1217c))}
    record['passed']=True
    save()
    print('PASS NATIVE_DMAC_ENGINE_TRANSLATION_AND_FAULT')
