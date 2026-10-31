// SPDX-License-Identifier: MIT-0
// Actual RTL AXI initiator; memory requests pause the clock for Simics service.
#include "Vddr_probe.h"
#include "verilated.h"
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

struct Bus {
    Vddr_probe rtl;
    uint64_t cycles=0, awaddr=0;
    unsigned awprot=0,awuser=0;
    bool aw_pending=false,b_pending=false,r_pending=false;
    bool stall_aw=false;
    unsigned bresp=0,rresp=0;
    uint64_t rdata=0;
    std::string response() {
        std::string line;
        if(!std::getline(std::cin,line) || line.size()>128)throw std::runtime_error("memory response missing/too long");
        return line;
    }
    unsigned write_memory(uint64_t addr,uint64_t data,unsigned prot,unsigned user) {
        std::cout<<"MEM_W "<<std::hex<<addr<<" "<<data<<" "<<prot<<" "<<user<<"\n"<<std::flush;
        std::istringstream in(response());std::string op,extra;unsigned resp=0;
        if(!(in>>op>>std::hex>>resp) || op!="MW" || resp>3 || (in>>extra))throw std::runtime_error("bad memory write response");
        return resp;
    }
    void read_memory(uint64_t addr,unsigned prot,unsigned user,unsigned &resp,uint64_t &data) {
        std::cout<<"MEM_R "<<std::hex<<addr<<" "<<prot<<" "<<user<<"\n"<<std::flush;
        std::istringstream in(response());std::string op,extra;
        if(!(in>>op>>std::hex>>resp>>data) || op!="MR" || resp>3 || (in>>extra))throw std::runtime_error("bad memory read response");
    }
    void tick() {
        rtl.m_awready=!aw_pending && !b_pending && (!stall_aw || cycles>=1600);
        rtl.m_wready=aw_pending && !b_pending;
        rtl.m_arready=!r_pending;
        rtl.m_bvalid=b_pending;rtl.m_bresp=bresp;rtl.m_bid=0;
        rtl.m_rvalid=r_pending;rtl.m_rresp=rresp;rtl.m_rid=0;rtl.m_rlast=1;rtl.m_rdata=rdata;
        rtl.clk=0;rtl.eval();
        bool aw=rtl.m_awvalid && rtl.m_awready;
        bool wd=rtl.m_wvalid && rtl.m_wready;
        bool ar=rtl.m_arvalid && rtl.m_arready;
        bool br=rtl.m_bvalid && rtl.m_bready;
        bool rd=rtl.m_rvalid && rtl.m_rready;
        uint64_t wa=rtl.m_awaddr,ra=rtl.m_araddr,data=rtl.m_wdata;
        unsigned wp=rtl.m_awprot,wu=rtl.m_awuser,rp=rtl.m_arprot,ru=rtl.m_aruser;
        if((aw && (rtl.m_awlen || rtl.m_awsize!=3 || rtl.m_awburst!=1 || rtl.m_awid || rtl.m_awcache || (wp!=0 && wp!=2) || wu)) ||
           (ar && (rtl.m_arlen || rtl.m_arsize!=3 || rtl.m_arburst!=1 || rtl.m_arid || rtl.m_arcache || (rp!=0 && rp!=2) || ru)) ||
           (wd && (rtl.m_wstrb!=255 || !rtl.m_wlast)))throw std::runtime_error("unexpected AXI shape");
        rtl.clk=1;rtl.eval();rtl.clk=0;rtl.eval();++cycles;
        if(br)b_pending=false;
        if(rd)r_pending=false;
        if(aw){aw_pending=true;awaddr=wa;awprot=wp;awuser=wu;}
        if(wd){bresp=write_memory(awaddr,data,awprot,awuser);aw_pending=false;b_pending=true;}
        if(ar){read_memory(ra,rp,ru,rresp,rdata);r_pending=true;}
    }
    void reset() {
        rtl.csr_read=0;rtl.csr_write=0;rtl.csr_byteenable=15;
        rtl.reset=1;tick();tick();rtl.reset=0;tick();
    }
    uint32_t read(unsigned off) {
        rtl.csr_address=off/4;rtl.csr_read=1;tick();
        uint32_t v=rtl.csr_readdata;rtl.csr_read=0;tick();return v;
    }
    void write(unsigned off,uint32_t v) {
        rtl.csr_address=off/4;rtl.csr_writedata=v;rtl.csr_write=1;tick();rtl.csr_write=0;tick();
    }
};

int main(int argc,char **argv) {
    try {
        Verilated::commandArgs(argc,argv);Bus bus;
        if(argc==2 && std::string(argv[1])=="--aw-stall")bus.stall_aw=true;
        else if(argc!=1)throw std::runtime_error("unknown backend option");
        bus.reset();
        std::cout<<"READY DDR2\n"<<std::flush;
        std::string line;
        while(std::getline(std::cin,line)) {
            if(line.size()>128)throw std::runtime_error("oversize CSR command");
            std::istringstream in(line);std::string op,extra;unsigned off;uint64_t value=0;
            in>>op;
            if(op=="Q" && !(in>>extra)) {std::cout<<"BYE\n"<<std::flush;return 0;}
            if((op!="R" && op!="W") || !(in>>std::hex>>off) || off>=256 || off%4 ||
               (op=="W" && (!(in>>value) || value>0xffffffffULL)) || (in>>extra))throw std::runtime_error("invalid CSR command");
            uint32_t result=0;
            if(op=="R")result=bus.read(off);else bus.write(off,uint32_t(value));
            std::cout<<"OK "<<std::hex<<result<<" "<<bus.cycles<<"\n"<<std::flush;
        }
    } catch(const std::exception &e) {
        std::cerr<<"FABRIC_DDR_BACKEND_ERROR "<<e.what()<<"\n";
        std::cout<<"ERR\n"<<std::flush;return 2;
    }
    return 0;
}
