// SPDX-License-Identifier: MIT-0
#include "lab.h"
#include "../driver.h"
#ifndef TARGET_PHYSICAL
#define TARGET_PHYSICAL 0x85000000UL
#endif
#ifndef EXPECT_AXI_FAULT
#define EXPECT_AXI_FAULT 0
#endif
#ifndef EXPECT_DATA_FAULT
#define EXPECT_DATA_FAULT 0
#endif
#ifndef EXPECT_TIMEOUT
#define EXPECT_TIMEOUT 0
#endif
int main(void) {
    lab_begin("fabric-ddr-rtl");
    check(!(SYS(sctlr_el3)&5),"FABRIC_DDR_CACHE_AND_MMU_OFF");
    struct ddr_probe device=ddr_probe_mmio(0x20030000);
    struct ddr_result result;
    const uint32_t seed=0x12345678,words=64;
    int rc=ddr_probe_run(&device,0x85000000+(EXPECT_AXI_FAULT?0x2000:0),words,seed,4096,&result);
    value("FABRIC_DDR_DRIVER_RC=",(uint64_t)(int64_t)rc);
    value("FABRIC_DDR_STATUS=",result.status);
    value("FABRIC_DDR_ERROR=",result.error);
    value("FABRIC_DDR_VERIFIED=",result.verified);
    value("FABRIC_DDR_FAIL_ADDRESS=",result.address);
    if(EXPECT_TIMEOUT) {
        check(rc==-4 && (result.status&(DDR_TIMEOUT|DDR_BUSY))==(DDR_TIMEOUT|DDR_BUSY),"FABRIC_DDR_EXPECTED_TIMEOUT_BUSY");
        check(ddr_probe_drain(&device,4096)==0,"FABRIC_DDR_TIMEOUT_DRAINED");
        uint32_t status=device.read(device.context,DDR_STATUS);
        check((status&(DDR_DONE|DDR_FAULT|DDR_TIMEOUT|DDR_BUSY))==(DDR_DONE|DDR_FAULT|DDR_TIMEOUT)
              && device.read(device.context,DDR_ERROR)==4 && device.read(device.context,DDR_VERIFIED)==0,
              "FABRIC_DDR_TIMEOUT_STOPPED_AFTER_DRAIN");
        check(((volatile uint64_t *)TARGET_PHYSICAL)[0]==ddr_probe_pattern(seed,0),"FABRIC_DDR_DRAINED_WRITE_COMPLETED");
        lab_done(0);
    }
    if(EXPECT_DATA_FAULT) {
        uint64_t expected=ddr_probe_pattern(seed,63);
        check(rc==-5 && result.error==2 && result.verified==63 && result.address==0x850001f8
              && result.expected==expected && result.observed==(expected^1),"FABRIC_DDR_EXPECTED_READ_CORRUPTION");
        check(((volatile uint64_t *)TARGET_PHYSICAL)[63]==expected,"FABRIC_DDR_NATIVE_MEMORY_UNCHANGED");
        lab_done(0);
    }
    if(EXPECT_AXI_FAULT) {
        check(rc==-5 && result.error==3 && result.verified==0 &&
              (result.status&(DDR_DONE|DDR_FAULT))==(DDR_DONE|DDR_FAULT) &&
              result.address==0x85002000,"FABRIC_DDR_EXPECTED_AXI_FAULT");
        lab_done(0);
    }
    check(rc==0 && result.verified==words,"FABRIC_DDR_RTL_VERIFIED");
    for(uint32_t i=0;i<words;i++)
        if(((volatile uint64_t *)TARGET_PHYSICAL)[i]!=ddr_probe_pattern(seed,i))fail("FABRIC_DDR_CPU_READBACK");
    check(1,"FABRIC_DDR_CPU_READBACK");
    rc=ddr_probe_run(&device,0x85010000,words,seed,4096,&result);
    check(rc==-2,"FABRIC_DDR_UNSAFE_RANGE_REJECTED");
    text("FABRIC_DDR_SCOPE functional-RTL-to-model-memory; no physical bridge or timing qualification\n");
    lab_done(0);
}
