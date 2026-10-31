// Simulation-only loader: advances only on MMIO transactions; accepts no RBFs.
#include "Vpr_model.h"
#include "verilated.h"
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#ifndef PR_FAULT
#define PR_FAULT 0
#endif
struct Bus {
 Vpr_model rtl; uint64_t cycles=0;unsigned remaining=0,target=1;
 void tick(){
  rtl.pr_busy=remaining>1;rtl.pr_done=remaining==1 && PR_FAULT!=1;rtl.pr_error=remaining==1 && PR_FAULT==1;
  if(remaining==1 && PR_FAULT!=1)rtl.select_persona=PR_FAULT==2?1:target;
  rtl.clk=0;rtl.eval();rtl.clk=1;rtl.eval();rtl.clk=0;rtl.eval();++cycles;
  if(remaining)--remaining;
 }
 void reset(){rtl.read=0;rtl.write=0;rtl.byteenable=15;rtl.select_persona=1;rtl.suppress_reset=0;rtl.reset_n=0;tick();rtl.reset_n=1;tick();}
 uint32_t access(unsigned off,bool write,uint32_t value){
  rtl.address=off/4;rtl.writedata=value;
  if(off==0x80 && write){if(!rtl.frozen || remaining || (value!=1 && value!=2))throw std::runtime_error("unsafe-simulated-load");target=value;remaining=8;}
  rtl.read=!write && off<0x80;rtl.write=write && off<0x80;tick();
  uint32_t result=off<0x80?rtl.readdata:remaining;
  rtl.read=0;rtl.write=0;tick();return write?0:result;
 }
};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Bus bus;bus.reset();std::cout<<"READY 1\n"<<std::flush;
 std::string line;
 while(std::getline(std::cin,line)){
  std::istringstream in(line);std::string op,extra;unsigned off;uint64_t value=0;in>>op;
  if(op=="Q" && !(in>>extra)){std::cout<<"BYE\n"<<std::flush;return 0;}
  if(line.size()>96 || (op!="R" && op!="W") || !(in>>std::hex>>off) || off>0x80 || off%4 || (op=="W" && (!(in>>value)||value>0xffffffffULL)) || (in>>extra)){std::cout<<"ERR invalid-request\n"<<std::flush;return 2;}
  try {uint32_t result=bus.access(off,op=="W",uint32_t(value));std::cout<<"OK "<<std::hex<<result<<" "<<bus.cycles<<"\n"<<std::flush;}
  catch(const std::exception& e){std::cout<<"ERR "<<e.what()<<"\n"<<std::flush;return 2;}
 }
 return 0;
}
