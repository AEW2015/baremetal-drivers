# SPDX-License-Identifier: MIT-0
"""Simics-only native Agilex SMMU fixture. No software address translation.

Requires the native model's TLB cache to be disabled, as in the tested platform.
This exercises fresh table walks; CR0ACK/command-queue invalidation are not
qualified. All requests go to the installed memory-space/TBU implementation.
"""
from simics import (SIM_get_object, SIM_read_phys_memory, SIM_write_phys_memory,
                    transaction_t, Sim_PE_No_Exception)

HPS='system.board.fpga.soc_inst.hps_subsys.agilex_hps'

class NativeTBUFixture:
    REG=0x16000000
    TABLE=0x85400000
    L1=0x85401000
    L2=0x85402000
    EVENT=0x85404000
    ROUTES={'dma0':('dmac_smmu_mem_space_0',0),
            'f2h':('f2soc_smmu_mem_space',4),
            'f2sdram':('f2sdram_smmu_mem_space',5)}

    def __init__(self,route='dma0',iova=0x85000000,physical=0x86000000,hps=HPS):
        if route not in self.ROUTES: raise ValueError('Unknown native ingress')
        if iova&0x1fffff or physical&0x1fffff: raise ValueError('Fixture needs 2MiB-aligned bases')
        if not (0<=iova<1<<32 and 0x85000000<=physical<0x87000000):
            raise ValueError('Address outside fixture input/physical scratch profile')
        if iova==physical: raise ValueError('Nonidentity mapping required')
        self.route=route;self.iova=iova;self.physical=physical
        self.sid=8 if route=='dma0' else 0
        self.cpu=SIM_get_object(hps+'.core[0]')
        self.smmu=SIM_get_object(hps+'.smmu')
        self.space=SIM_get_object(hps+'.'+self.ROUTES[route][0])
        self.saved_dma=None
        self.observations={}

    def read(self,address,size=4):
        return SIM_read_phys_memory(self.cpu,address,size)

    def write(self,address,value,size=4):
        SIM_write_phys_memory(self.cpu,address,value,size)

    def configure(self,reset_model=True):
        if reset_model:
            self.smmu.port.HRESET.iface.signal.signal_raise()
            self.smmu.port.HRESET.iface.signal.signal_lower()
        if self.smmu.tlb_cache_enable:
            raise RuntimeError('Native fixture needs cache-off fresh walks; real TLBI support not qualified')
        if not self.read(self.REG)&1:
            raise RuntimeError('Native SMMU does not advertise stage-2 support')
        for address in range(self.TABLE,self.EVENT+4096,8): self.write(address,0,8)
        for sid in range(32): self.write(self.TABLE+sid*64,1,8)
        self.write(self.TABLE+self.sid*64,1|(6<<1),8)
        s2=32|(1<<6)|(3<<8)|(3<<10)|(3<<12)|(2<<16)|(1<<19)|(1<<26)
        self.write(self.TABLE+self.sid*64+16,1|(s2<<32),8)
        self.write(self.TABLE+self.sid*64+24,self.L1,8)
        self.write(self.L1+(self.iova>>30)*8,self.L2|3,8)
        self.pte=self.L2+((self.iova>>21)&511)*8
        self.write(self.pte,self.physical|0x7fd,8)
        self.write(self.REG+0x20,0)
        self.write(self.REG+0x80,self.TABLE|(1<<62),8)
        self.write(self.REG+0x88,5)
        self.write(self.REG+0xa0,self.EVENT|(1<<62)|3,8)
        self.write(self.REG+0xac,0)
        # Enable translation and event collection; no unmodeled command-queue
        # completion is asserted or bypassed by writing ACK/consumer values.
        self.write(self.REG+0x20,5)
        if self.route=='dma0':
            self.saved_dma=(self.read(0x10d121a8),self.read(0x10d1217c))
            self.write(0x10d121a8,0x00080008)
            self.write(0x10d1217c,3)
        self.observations={'route':self.route,'memory_space':self.space.name,
            'tbu_index':self.ROUTES[self.route][1],'sid':self.sid,
            'sid_origin':('DMA0 System Manager read/write stream-ID registers programmed to 8'
                if self.route=='dma0' else
                'Native ingress default SID 0; no arm_smmu_attributes atom supplied; physical AXUSER-to-SID mapping not qualified'),
            'iova':hex(self.iova),'physical':hex(self.physical),'table_base':hex(self.TABLE),
            'model_reset_pulse':reset_model,'tlb_cache_enable':False,
            'invalidation_scope':'fresh table walk only; no command queue/TLBI claim',
            'cr0':hex(self.read(self.REG+0x20)),'cr0ack':hex(self.read(self.REG+0x24))}
        return self.observations

    def transaction(self,address,size=8,value=None,initiator=None):
        if not self.iova<=address<address+size<=self.iova+0x10000:
            raise ValueError('Transaction outside 64KiB owned IOVA window')
        # AXI PROT=0b010: nonsecure, unprivileged data. No SID atom is inserted.
        # DMA0 marker supplies SID8 from System Manager; fabric ingress default
        # SID0 is checked against the native fault record, not inferred from RTL.
        attrs=dict(size=size,arm_nonsecure=True,arm_privileged=False,
                   initiator=initiator or self.smmu)
        if value is None: req=transaction_t(read=True,**attrs)
        else: req=transaction_t(write=True,value_le=value,**attrs)
        status=self.space.iface.transaction.issue(req,address)
        return status,(req.value_le if value is None and status==Sim_PE_No_Exception else None)

    def map_block(self,iova,physical):
        if iova&0x1fffff or physical&0x1fffff or iova>>30 != self.iova>>30:
            raise ValueError('Additional 2MiB mapping must use the fixture L1 region')
        if not 0x85000000<=physical<0x87000000:
            raise ValueError('Physical target outside owned DDR scratch')
        self.write(self.L2+((iova>>21)&511)*8,physical|0x7fd,8)
        self.observations.setdefault('additional_mappings',[]).append({'iova':hex(iova),'physical':hex(physical)})

    def unmap(self,iova=None):
        if self.smmu.tlb_cache_enable:
            raise RuntimeError('Cannot substitute PTE edit for required cache invalidation')
        address=self.iova if iova is None else iova
        if address&0x1fffff or address>>30 != self.iova>>30:
            raise ValueError('Unmap must name an aligned block in the fixture L1 region')
        pte=self.L2+((address>>21)&511)*8
        self.write(pte,0,8)
        self.observations['unmapped_pte']=hex(pte)

    def fault(self):
        return {'producer':self.read(self.REG+0xa8),
                'consumer':self.read(self.REG+0xac),
                'words':[self.read(self.EVENT+i*8,8) for i in range(4)],
                'global_error':self.read(self.REG+0x60)}

    def close(self):
        self.write(self.REG+0x20,0)
        if self.saved_dma is not None:
            self.write(0x10d121a8,self.saved_dma[0])
            self.write(0x10d1217c,self.saved_dma[1])
