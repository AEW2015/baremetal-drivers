# SPDX-License-Identifier: MIT-0
"""Execute inside an isolated, bootstrapped Agilex Simics process only."""
import json
from pathlib import Path
from simics import Sim_PE_No_Exception, SIM_quit
from native_fixture import NativeTBUFixture

def run_cases(output):
    results={'scope':'Host-issued transactions through native Agilex SMMU/TBU models; not a physical DMA/fabric initiator qualification; model TLB cache disabled; no command-queue invalidation claim','tests':[]}
    try:
        for route in ('dma0','f2h','f2sdram'):
            fixture=NativeTBUFixture(route)
            try:
                observation=fixture.configure()
                expected=[0x1234567800000000^i for i in range(64)]
                for i in range(64):
                    fixture.write(fixture.physical+8*i,0,8)
                    fixture.write(fixture.iova+8*i,0xa5a5a5a5a5a5a5a5,8)
                for i,value in enumerate(expected):
                    status,_=fixture.transaction(fixture.iova+8*i,value=value)
                    assert status==Sim_PE_No_Exception,'valid native TBU write failed'
                for i,value in enumerate(expected):
                    status,data=fixture.transaction(fixture.iova+8*i)
                    assert status==Sim_PE_No_Exception and data==value,'valid native TBU read failed'
                    assert fixture.read(fixture.physical+8*i,8)==value,'nonidentity physical target mismatch'
                    assert fixture.read(fixture.iova+8*i,8)==0xa5a5a5a5a5a5a5a5,'untranslated alias guard changed'
                assert fixture.fault()['producer']==0,'valid traffic generated fault'
                print('PASS NATIVE_TBU_DATA route='+route+' words=64 SID='+str(fixture.sid))
                fixture.unmap()
                status,_=fixture.transaction(fixture.iova,value=0xdeadbeefcafef00d)
                assert status!=Sim_PE_No_Exception,'unmapped native TBU write succeeded'
                event=fixture.fault();words=event['words']
                assert event['producer']==1,'one invalid transfer must produce one event'
                assert words[0]&255==0x10,'event is not F_TRANSLATION'
                assert words[0]>>32==fixture.sid,'fault stream ID mismatch'
                assert words[1]&(1<<39),'fault is not stage2'
                assert words[2]==fixture.iova,'fault address mismatch'
                for i,value in enumerate(expected):
                    assert fixture.read(fixture.physical+8*i,8)==value,'invalid DMA changed target guard'
                    assert fixture.read(fixture.iova+8*i,8)==0xa5a5a5a5a5a5a5a5,'invalid DMA changed IOVA guard'
                assert event['global_error']==0,'unexpected native SMMU global error'
                print('NATIVE_TBU_EVENT '+route+' '+json.dumps(event,sort_keys=True))
                print('PASS NATIVE_TBU_UNMAP_FAULT route='+route+' SID='+str(fixture.sid)+' guard_words=64')
                results['tests'].append({'name':route,'status':'pass','configuration':observation,'fault':event})
            finally:
                fixture.close()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        results['error']=repr(exc)
        Path(output).write_text(json.dumps(results,indent=2)+'\n')
        print('FAIL NATIVE_TBU_CASES')
        SIM_quit(1)
    Path(output).write_text(json.dumps(results,indent=2)+'\n')
    print('PASS NATIVE_TBU_CASES count=3')
    SIM_quit(0)
