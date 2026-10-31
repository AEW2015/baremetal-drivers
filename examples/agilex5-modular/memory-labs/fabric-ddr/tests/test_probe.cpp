// SPDX-License-Identifier: MIT-0
#include "Vddr_probe.h"
#include "verilated.h"
#include "driver.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <string>

struct Model {
    Vddr_probe rtl;
    std::array<uint64_t,4096> ram{};
    uint64_t cycles=0,aw_address=0,read_address=0;
    unsigned writes=0,reads=0,bd=0,rd=0;
    bool have_aw=false,b_pending=false,r_pending=false,corrupt=false,bad_b=false,bad_r=false;
    std::string stall;
    bool hold_aw=false,hold_w=false,hold_ar=false;
    uint64_t old_aw=0,old_w=0,old_ar=0;
    uint32_t rng=7;
    unsigned random(){rng=rng*1664525+1013904223;return rng;}
    static constexpr uint64_t base=0x10000000;
    void tick() {
        rtl.clk=0;
        rtl.m_awready=stall!="aw" && (random()>>24)%4!=0;
        rtl.m_wready=stall!="w" && (random()>>24)%4!=0;
        rtl.m_arready=stall!="ar" && (random()>>24)%4!=0;
        rtl.m_bid=0;rtl.m_rid=0;
        rtl.m_bvalid=b_pending && !bd && stall!="b";
        rtl.m_bresp=bad_b?2:0;
        rtl.m_rvalid=r_pending && !rd && stall!="r";
        rtl.m_rresp=bad_r?3:0;rtl.m_rlast=1;
        if(r_pending){
            assert(read_address>=base && read_address<base+ram.size()*8);
            rtl.m_rdata=ram[(read_address-base)/8];
            if(corrupt && read_address==base+37*8)rtl.m_rdata^=1;
        }
        rtl.eval();
        if(hold_aw)assert(rtl.m_awvalid && rtl.m_awaddr==old_aw);
        if(hold_w)assert(rtl.m_wvalid && rtl.m_wdata==old_w && rtl.m_wstrb==255 && rtl.m_wlast);
        if(hold_ar)assert(rtl.m_arvalid && rtl.m_araddr==old_ar);
        hold_aw=rtl.m_awvalid&&!rtl.m_awready;old_aw=rtl.m_awaddr;
        hold_w=rtl.m_wvalid&&!rtl.m_wready;old_w=rtl.m_wdata;
        hold_ar=rtl.m_arvalid&&!rtl.m_arready;old_ar=rtl.m_araddr;
        bool aw=rtl.m_awvalid&&rtl.m_awready,w=rtl.m_wvalid&&rtl.m_wready;
        bool b=rtl.m_bvalid&&rtl.m_bready,ar=rtl.m_arvalid&&rtl.m_arready;
        bool r=rtl.m_rvalid&&rtl.m_rready;
        if(aw){assert(!have_aw && !b_pending);have_aw=true;aw_address=rtl.m_awaddr;}
        if(w){
            assert(have_aw && aw_address>=base && aw_address<base+ram.size()*8);
            assert(rtl.m_awlen==0 && rtl.m_awsize==3 && rtl.m_wstrb==255 && rtl.m_wlast);
            ram[(aw_address-base)/8]=rtl.m_wdata;have_aw=false;b_pending=true;bd=2;++writes;
        }
        if(ar){assert(!r_pending);read_address=rtl.m_araddr;r_pending=true;rd=3;++reads;}
        rtl.clk=1;rtl.eval();rtl.clk=0;rtl.eval();++cycles;
        if(b)b_pending=false;
        if(r)r_pending=false;
        if(bd)--bd;if(rd)--rd;
    }
    Model(){rtl.reset=1;rtl.csr_read=rtl.csr_write=0;rtl.csr_byteenable=15;tick();rtl.reset=0;tick();}
    uint32_t read(unsigned off){rtl.csr_address=off/4;rtl.csr_read=1;tick();uint32_t v=rtl.csr_readdata;rtl.csr_read=0;tick();return v;}
    void write(unsigned off,uint32_t value){rtl.csr_address=off/4;rtl.csr_writedata=value;rtl.csr_write=1;tick();rtl.csr_write=0;tick();}
    ddr_probe device(){return {this,[](void*p,unsigned o){return ((Model*)p)->read(o);},[](void*p,unsigned o,uint32_t v){((Model*)p)->write(o,v);}};}
};
static void valid(unsigned words){
    Model m;auto dev=m.device();ddr_result result;
    assert(ddr_probe_run(&dev,Model::base,words,0x51a70123,100000,&result)==0);
    assert(result.verified==words && m.writes==words && m.reads==words && !(result.status&DDR_BUSY));
    for(unsigned i=0;i<words;++i)assert(m.ram[i]==ddr_probe_pattern(0x51a70123,i));
    std::printf("PASS FABRIC_DDR words=%u writes=%u reads=%u cycles=%llu randomized_backpressure=1\n",words,m.writes,m.reads,(unsigned long long)result.cycles);
}
static void range(){
    Model m;auto dev=m.device();ddr_result result;
    assert(ddr_probe_run(&dev,Model::base+1,8,1,100,&result)==-2);
    assert(ddr_probe_run(&dev,Model::base,0,1,100,&result)==-2);
    assert(ddr_probe_run(&dev,Model::base+32760,2,1,100,&result)==-2);
    // Bypass software: hardware itself must reject every unsafe descriptor.
    for(uint64_t a:{Model::base-8,Model::base+1,Model::base+32768,UINT64_MAX-7}){
        m.write(DDR_BASE,(uint32_t)a);m.write(DDR_BASE+4,(uint32_t)(a>>32));
        m.write(DDR_WORDS,2);m.write(DDR_CONTROL,1);
        assert((m.read(DDR_STATUS)&(DDR_DONE|DDR_FAULT|DDR_REJECTED))==(DDR_DONE|DDR_FAULT|DDR_REJECTED));
        assert(m.read(DDR_ERROR)==1 && m.writes==0 && m.reads==0);
    }
    std::puts("PASS FABRIC_RANGE software_and_RTL_guards no_AXI_transactions");
}
static void fault(bool corrupt,bool bad_b,bool bad_r){
    Model m;m.corrupt=corrupt;m.bad_b=bad_b;m.bad_r=bad_r;
    auto dev=m.device();ddr_result result;
    assert(ddr_probe_run(&dev,Model::base,128,7,10000,&result)==-5);
    assert(result.error==(corrupt?2U:3U));
    if(corrupt){assert(result.verified==37 && result.address==Model::base+37*8 && (result.expected^result.observed)==1);}
    std::printf("PASS FABRIC_FAULT kind=%s verified=%u error=%u\n",corrupt?"corruption":bad_b?"BRESP":"RRESP",result.verified,result.error);
}
static void timeout(const char* channel){
    Model m;m.stall=channel;auto dev=m.device();ddr_result result;
    assert(ddr_probe_run(&dev,Model::base,8,9,10000,&result)==-4);
    auto s=m.read(DDR_STATUS);assert((s&(DDR_BUSY|DDR_TIMEOUT|DDR_FAULT))==(DDR_BUSY|DDR_TIMEOUT|DDR_FAULT));
    // The core must not violate AXI by dropping its pending request on timeout.
    assert(ddr_probe_drain(&dev,30)==-4);
    unsigned w=m.writes,r=m.reads;m.stall.clear();
    assert(ddr_probe_drain(&dev,100)==0);
    assert(!(m.read(DDR_STATUS)&DDR_BUSY) && (m.read(DDR_STATUS)&DDR_DONE));
    assert(m.writes<=w+1 && m.reads<=r+1 && m.read(DDR_ERROR)==4);
    std::printf("PASS FABRIC_TIMEOUT channel=%s request_held_then_drained no_following_transactions\n",channel);
}
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);
    valid(1);valid(257);valid(4096);range();fault(true,false,false);fault(false,true,false);fault(false,false,true);
    for(auto channel:{"aw","w","b","ar","r"})timeout(channel);
    std::puts("FABRIC_DDR_COMPLETE: actual C driver + actual RTL; behavioral RAM/AXI peer, no physical HPS bridge or SMMU qualification");
}
