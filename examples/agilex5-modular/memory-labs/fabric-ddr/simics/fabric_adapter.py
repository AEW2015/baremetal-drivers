"""Simics CSR overlay and native memory-space service for actual Verilator AXI."""
import atexit
import json
from pathlib import Path
import sys
import simics
from transport import Backend

BASE=0x20030000
SPAN=0x100
_active=None
_fixture=None
_guard=None
_native_fault=False

class FabricDDR:
    cls=simics.confclass('baremetal_fabric_ddr_rtl',short_doc='Verilator DDR probe with native Simics memory service')
    @cls.iface.io_memory.operation
    def operation(self,mop,info):
        if simics.SIM_get_mem_op_inquiry(mop):return simics.Sim_PE_Inquiry_Unhandled
        offset=simics.SIM_get_mem_op_physical_address(mop)+info.start-info.base
        if simics.SIM_get_mem_op_size(mop)!=4 or offset%4 or not 0<=offset<SPAN:return simics.Sim_PE_IO_Error
        try:
            write=simics.SIM_mem_op_is_write(mop)
            value=simics.SIM_get_mem_op_value_le(mop) if write else 0
            initiator=simics.SIM_get_mem_op_initiator(mop)
            result=_active.access(offset,write,value,initiator.name if initiator else None)
            if not write:simics.SIM_set_mem_op_value_le(mop,result)
            return simics.Sim_PE_No_Exception
        except (OSError,ValueError,RuntimeError) as exc:
            print('FABRIC_DDR_ADAPTER_ERROR '+str(exc))
            return simics.Sim_PE_IO_Error

def install(executable,trace,route='physical',injection='none'):
    global _active,_fixture
    if _active is not None:raise RuntimeError('Fresh Simics session required per backend')
    prefix='system.board.fpga.soc_inst.hps_subsys.agilex_hps'
    targets={'physical':'phys_mem','f2soc':'f2soc_smmu_mem_space','f2sdram':'f2sdram_smmu_mem_space'}
    if route not in targets:raise ValueError('Unknown memory ingress')
    if injection not in ('none','axi-response','read-data','aw-stall'):raise ValueError('Unknown explicit injection')
    if injection!='none' and route!='physical':raise ValueError('Injections are not native SMMU faults')
    space=simics.SIM_get_object(prefix+'.'+targets[route])
    if route!='physical':
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'smmu'))
        from native_fixture import NativeTBUFixture
        _fixture=NativeTBUFixture(route='f2h' if route=='f2soc' else 'f2sdram',iova=0x85000000,physical=0x86000000)
    device=simics.SIM_create_object('baremetal_fabric_ddr_rtl','fabric_ddr_rtl',[])
    def memory(write,address,data,prot,user):
        # The native memory-space interface executes the transfer. There is no
        # Python RAM array, address translation or page-table permission model.
        if _fixture is not None:
            # Exact AXPROT=010: nonsecure, unprivileged data. The fixture maps
            # those same native transaction atoms; no SID atom is supplied.
            if prot!=2 or user!=0:raise RuntimeError('Native fixture requires actual AXPROT=2 AXUSER=0')
            error,result=_fixture.transaction(address,size=8,value=data if write else None,initiator=device)
            if write or result is None:result=0
        elif write:
            error=space.iface.memory_space.write(device,address,tuple(data.to_bytes(8,'little')),0)
            result=0
        else:
            raw=space.iface.memory_space.read(device,address,8,0)
            if len(raw)!=8:raise RuntimeError('Native memory read returned wrong length')
            result=int.from_bytes(bytes(raw),'little');error=simics.Sim_PE_No_Exception
        response=0 if error==simics.Sim_PE_No_Exception else 3
        _active.log({'kind':'native-memory','space':space.name,'write':write,'address':address,
                     'native_exception':int(error),'native_no_exception':error==simics.Sim_PE_No_Exception,
                     'data':data if write else result,'axprot':prot,'axuser':user})
        if injection=='axi-response' and write:
            response=3
            _active.log({'kind':'fault-injection','type':injection,'address':address,'response':response})
        if injection=='read-data' and not write and address==0x850001f8:
            result^=1
            _active.log({'kind':'fault-injection','type':injection,'address':address,'delivered_data':result})
        return response,result
    _active=Backend(executable,trace,memory,injection=injection)
    if injection=='aw-stall':_active.log({'kind':'fault-injection','type':'aw-stall','ready_after_rtl_cycle':1600})
    atexit.register(_active.abort)
    phys=simics.SIM_get_object(prefix+'.phys_mem')
    phys.map=list(phys.map)+[[BASE,device,0,0,SPAN,None,-100,4]]
    print(f'FABRIC_DDR_ATTACHED csr=0x{BASE:x} route={route} memory_space={space.name}')
    return _active

def configure_native(fault=False):
    global _guard,_native_fault
    if _fixture is None:raise RuntimeError('No native fixture installed')
    _native_fault=fault
    observations=_fixture.configure()
    offset=0x2000 if fault else 0
    _guard={'offset':offset,'sentinel':0xa55a0123deadbeef}
    for i in range(64):
        _fixture.write(_fixture.iova+offset+i*8,_guard['sentinel'],8)
        _fixture.write(_fixture.physical+offset+i*8,_guard['sentinel'],8)
    if fault:_fixture.unmap()
    print('FABRIC_DDR_NATIVE_SETUP '+json.dumps(observations,sort_keys=True))
    return observations

def finish_native():
    if _fixture is None or _guard is None:raise RuntimeError('Native fixture was not configured')
    offset=_guard['offset'];sentinel=_guard['sentinel']
    iova_guard=all(_fixture.read(_fixture.iova+offset+i*8,8)==sentinel for i in range(64))
    event=_fixture.fault()
    if _native_fault:
        target_ok=all(_fixture.read(_fixture.physical+offset+i*8,8)==sentinel for i in range(64))
        words=event['words']
        event_ok=(event['producer']==1 and words[0]&255==0x10 and words[0]>>32==_fixture.sid
                  and bool(words[1]&(1<<39)) and words[2]==_fixture.iova+offset and event['global_error']==0)
    else:
        target_ok=all(_fixture.read(_fixture.physical+i*8,8)==(((0x12345678^i)<<32)|((0x12345678+i)&0xffffffff)) for i in range(64))
        event_ok=event['producer']==0 and event['global_error']==0
    result={'passed':iova_guard and target_ok and event_ok,'unmapped':_native_fault,
            'physical_iova_guard_unchanged':iova_guard,'target_words_checked':64,
            'target_ok':target_ok,'event_ok':event_ok,'event':event,'configuration':dict(_fixture.observations)}
    _fixture.close()
    result['cr0_after_cleanup']=_fixture.read(_fixture.REG+0x20)
    result['passed']=result['passed'] and result['cr0_after_cleanup']==0
    print('FABRIC_DDR_NATIVE_RESULT '+json.dumps(result,sort_keys=True))
    return result
