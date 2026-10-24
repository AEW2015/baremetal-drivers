#include "Vlab_ip.h"
#include "verilated.h"
#include "lab_driver.h"
#include <cassert>
#include <cstdio>
struct Bus {
    Vlab_ip top;
    bool missing_done=false, bad_id=false;
    void tick(){top.clk=0;top.eval();top.clk=1;top.eval();top.clk=0;top.eval();}
    void reset(){top.avs_read=0;top.avs_write=0;top.reset_n=0;tick();top.reset_n=1;tick();}
    uint32_t read(unsigned offset){top.avs_address=offset/4;top.avs_read=1;tick();auto v=top.avs_readdata;top.avs_read=0;tick();return v;}
    void write(unsigned offset,uint32_t v,unsigned be=15){top.avs_address=offset/4;top.avs_writedata=v;top.avs_byteenable=be;top.avs_write=1;tick();top.avs_write=0;tick();}
};
static uint32_t rd(void *ctx,unsigned offset){auto &b=*(Bus *)ctx;if(b.bad_id && offset==LAB_ID)return 0;if(b.missing_done && offset==LAB_STATUS)return 0;return b.read(offset);}
static void wr(void *ctx,unsigned offset,uint32_t v){((Bus *)ctx)->write(offset,v);}
int main(int argc,char **argv){
    Verilated::commandArgs(argc,argv);
    Bus b;b.reset();lab_device d{&b,rd,wr};uint32_t persona=0,r=0;
    assert(lab_probe(&d,&persona)==0);
    assert(persona==LAB_ADD || persona==LAB_XOR);
    const uint32_t vectors[][2]={{7,5},{0xffffffff,1},{0xaaaaaaaa,0x55555555},{0,0}};
    for(auto &v:vectors){assert(lab_execute(&d,v[0],v[1],&r,20)==0);assert(r==(persona==LAB_ADD ? v[0]+v[1] : v[0]^v[1]));}
    assert(b.read(LAB_SEQUENCE)==4);
    b.write(LAB_A,0x11223344);b.write(LAB_A,0xaabbccdd,5);assert(b.read(LAB_A)==0x11bb33dd);
    b.write(LAB_ID,0);assert(b.read(LAB_ID)==LAB_MAGIC);
    b.write(LAB_STATUS,LAB_DONE);assert((b.read(LAB_STATUS)&LAB_DONE)==0);
    assert(lab_quiesce(&d,20)==0);assert(b.read(LAB_PERSONA)==0);
    assert(lab_execute(&d,1,2,&r,20)!=0);
    b.write(LAB_CONTROL,LAB_START|LAB_QUIESCE);assert(b.read(LAB_STATUS)&LAB_REJECTED);assert(b.read(LAB_SEQUENCE)==4);
    assert(lab_resume(&d,20)==0);assert(lab_execute(&d,7,5,&r,20)==0);
    b.bad_id=true;assert(lab_probe(&d,&persona)!=0);b.bad_id=false;
    b.missing_done=true;assert(lab_execute(&d,7,5,&r,3)==-3);b.missing_done=false;
    b.reset();assert(b.read(LAB_SEQUENCE)==0);assert(b.read(LAB_STATUS)==0);
    std::printf("PASS FABRIC_RTL_DRIVER: persona %08x, vectors, byte enables, W1C, read-only, quiesce, timeout, reset\n",persona);
}
