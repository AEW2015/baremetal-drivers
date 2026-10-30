// Transaction-stepped RTL backend. Protocol stdout is reserved for responses.
#include "Vlab_ip.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
struct Bus {
    Vlab_ip rtl;
    uint64_t cycles=0;
    void tick(){rtl.clk=0;rtl.eval();rtl.clk=1;rtl.eval();rtl.clk=0;rtl.eval();++cycles;}
    void reset(){rtl.avs_read=0;rtl.avs_write=0;rtl.avs_byteenable=15;rtl.reset_n=0;tick();rtl.reset_n=1;tick();}
    uint32_t read(unsigned off){rtl.avs_address=off/4;rtl.avs_read=1;tick();uint32_t v=rtl.avs_readdata;rtl.avs_read=0;tick();return v;}
    void write(unsigned off,uint32_t v){rtl.avs_address=off/4;rtl.avs_writedata=v;rtl.avs_byteenable=15;rtl.avs_write=1;tick();rtl.avs_write=0;tick();}
};
int main(int argc,char **argv){
    Verilated::commandArgs(argc,argv);Bus bus;bus.reset();
    std::cout<<"READY 1\n"<<std::flush;
    std::string line;
    while(std::getline(std::cin,line)){
        if(line.size()>96){std::cout<<"ERR request-too-long\n"<<std::flush;return 2;}
        std::istringstream request(line);std::string op,extra;unsigned off=0;uint64_t value=0;
        request>>op;
        if(op=="Q" && !(request>>extra)){std::cout<<"BYE\n"<<std::flush;return 0;}
        if((op!="R" && op!="W") || !(request>>std::hex>>off) || off>=64 || off%4 || (op=="W" && (!(request>>value) || value>0xffffffffULL)) || (request>>extra)){
            std::cout<<"ERR invalid-request\n"<<std::flush;return 2;
        }
        uint32_t result=0;
        if(op=="R")result=bus.read(off);else bus.write(off,uint32_t(value));
        std::cout<<"OK "<<std::hex<<result<<" "<<bus.cycles<<"\n"<<std::flush;
    }
    return 0;
}
