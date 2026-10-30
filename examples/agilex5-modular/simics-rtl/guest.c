#include "../core/common.h"
#include "../fabric/lab_driver.h"
#define BASE 0x20020000u
#ifndef EXPECT_TIMEOUT
#define EXPECT_TIMEOUT 0
#endif
static void finish(int ok){
    text(ok?"SIMICS_RTL_COMPLETE status=0\n":"SIMICS_RTL_COMPLETE status=1\n");
    for(;;)__asm__ volatile("wfi");
}
void example_main(void){
    text("SIMICS_RTL_BEGIN: Arm guest -> MMIO -> Verilator RTL\n");
    struct lab_device d=lab_mmio(BASE);uint32_t persona=0,result=0;
    if(lab_probe(&d,&persona)){text("FAIL RTL_PROBE\n");finish(0);}
    value("PERSONA = ",persona);
    if(EXPECT_TIMEOUT){
        int rc=lab_execute(&d,7,5,&result,8);
        if(rc!=-3){text("FAIL EXPECTED_TIMEOUT\n");finish(0);}
        text("PASS RTL_NEGATIVE: missing DONE rejected with driver rc=-3\n");finish(1);
    }
    const uint32_t vectors[][2]={{7,5},{0xffffffff,1},{0xaaaaaaaa,0x55555555},{0,0}};
    for(unsigned i=0;i<4;++i){
        uint32_t a=vectors[i][0],b=vectors[i][1];
        if(lab_execute(&d,a,b,&result,32) || result!=(persona==LAB_ADD?a+b:a^b)){
            text("FAIL RTL_VECTOR\n");finish(0);
        }
        value("RESULT = ",result);
    }
    if(d.read(d.context,LAB_SEQUENCE)!=4){text("FAIL RTL_SEQUENCE\n");finish(0);}
    text("PASS RTL_MATH: four vectors and fresh sequence checks\n");
    if(lab_quiesce(&d,32) || d.read(d.context,LAB_PERSONA)!=0){text("FAIL RTL_QUIESCE\n");finish(0);}
    d.write(d.context,LAB_CONTROL,LAB_START|LAB_QUIESCE);
    if(!(d.read(d.context,LAB_STATUS)&LAB_REJECTED) || d.read(d.context,LAB_SEQUENCE)!=4 || lab_resume(&d,32) || lab_probe(&d,&persona)){
        text("FAIL RTL_RESUME\n");finish(0);
    }
    text("PASS RTL_QUIESCE: blocked start rejected; resumed identity valid\n");finish(1);
}
