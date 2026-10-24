#include "../core/common.h"
#include "lab_driver.h"
#ifndef LAB_CPU_BASE
#error Build with the CPU-visible base exported by your Platform Designer design
#endif
static void fail(void){text("FAIL FABRIC_IP\n");for(;;)__asm__ volatile("wfi");}
void example_main(void) {
    text("HPS FABRIC IP BEGIN\n");
    struct lab_device dev=lab_mmio(LAB_CPU_BASE);
    uint32_t id,result;
    if(lab_probe(&dev,&id))fail();
    value("PERSONA = ",id);
    const uint32_t vectors[][2]={{7,5},{0xffffffff,1},{0xaaaaaaaa,0x55555555},{0,0}};
    for(unsigned i=0;i<4;i++) {
        uint32_t a=vectors[i][0],b=vectors[i][1];
        if(lab_execute(&dev,a,b,&result,10000))fail();
        if(result!=(id==LAB_ADD ? a+b : a^b))fail();
        value("RESULT = ",result);
    }
    text("PASS FABRIC_MATH: four vectors and fresh sequence checks\n");
    if(lab_quiesce(&dev,10000))fail();
    if(dev.read(dev.context,LAB_PERSONA)!=0)fail();
    dev.write(dev.context,LAB_CONTROL,LAB_START|LAB_QUIESCE);
    if(!(dev.read(dev.context,LAB_STATUS)&LAB_REJECTED))fail();
    if(lab_resume(&dev,10000) || lab_probe(&dev,&id))fail();
    text("PASS FABRIC_QUIESCE: blocked start rejected; resumed identity valid\n");
    text("HPS FABRIC IP COMPLETE\n");
}
