"""Simics-only device adapter; arithmetic/register behavior lives in Verilator RTL.

Uses public confclass/io_memory and memory-space.map APIs. This independent
implementation is not a redistribution of the installed vendor sample code.
"""
import atexit
import simics
from transport import Backend

BASE=0x20020000
SPAN=0x40
_active=None

class RTLDevice:
    cls=simics.confclass('baremetal_verilator_mmio',short_doc='Transaction-stepped external Verilator RTL')

    @cls.iface.io_memory.operation
    def operation(self,mop,info):
        if simics.SIM_get_mem_op_inquiry(mop):return simics.Sim_PE_Inquiry_Unhandled
        offset=simics.SIM_get_mem_op_physical_address(mop)+info.start-info.base
        if simics.SIM_get_mem_op_size(mop)!=4 or offset<0 or offset>=SPAN or offset%4:
            _active.abort()
            print('SIMICS_RTL_ADAPTER_ERROR unsupported MMIO size/alignment/offset')
            return simics.Sim_PE_IO_Error
        try:
            write=simics.SIM_mem_op_is_write(mop)
            value=simics.SIM_get_mem_op_value_le(mop) if write else 0
            initiator=simics.SIM_get_mem_op_initiator(mop)
            result=_active.access(offset,write,value,initiator.name if initiator else None)
            if not write:simics.SIM_set_mem_op_value_le(mop,result)
            return simics.Sim_PE_No_Exception
        except (OSError,ValueError,RuntimeError) as exc:
            print('SIMICS_RTL_ADAPTER_ERROR '+str(exc))
            return simics.Sim_PE_IO_Error

def install(executable,trace,missing_done=False):
    global _active
    if _active is not None:raise RuntimeError('Only one RTL backend per fresh Simics session')
    _active=Backend(executable,trace,missing_done)
    atexit.register(_active.abort)
    space=simics.SIM_get_object('system.board.fpga.soc_inst.hps_subsys.agilex_hps.phys_mem')
    device=simics.SIM_create_object('baremetal_verilator_mmio','lab_verilator',[])
    # Overlay exactly 64 bytes; priority -100 wins over default platform bridge
    # mappings. This is a simulated MMIO attachment, not HPS bridge RTL validation.
    space.map=list(space.map)+[[BASE,device,0,0,SPAN,None,-100,4]]
    print('SIMICS_RTL_ATTACHED base=0x20020000 span=0x40 backend='+str(executable))
    return _active
