// SPDX-License-Identifier: MIT-0
/* Hardware-only timing gate around the unchanged DDR sweep. */
#ifndef LAB_AGILEX5
#error The calibrated wrapper is only built for the Agilex hardware profile
#endif
#define main ddr_sweep_main
#include "ddr.c"
#undef main

int main(void) {
    const uint64_t expected_hz=400000000;
    const uint64_t poll_limit=268435456;
    uart_init();
    text("DDR_CALIBRATION_BEGIN nominal_seconds=1 host_interval_required\n");
    check(SYS(CurrentEL)==12 && !(SYS(sctlr_el3)&5),"DDR_CALIBRATION_EL3_CACHE_OFF");
    uint64_t declared=SYS(cntfrq_el0);
    check(declared==expected_hz,"DDR_CALIBRATION_DECLARED_400MHZ");
    uint64_t first=ticks();
    for(volatile unsigned i=0;i<10000;i++) __asm__ volatile("nop");
    check(ticks()>first,"DDR_COUNTER_ADVANCES_BEFORE_CALIBRATION");
    value("DDR_CALIBRATION_DECLARED_HZ=",declared);
    text("COUNTER_INTERVAL_START\n");
    uint64_t start=ticks(),now=start,polls;
    for(polls=0;polls<poll_limit;polls++) {
        now=ticks();
        if(now-start>=declared)break;
    }
    text("COUNTER_INTERVAL_END\n");
    field("DDR_CALIBRATION ticks=",now-start);
    field(" polls=",polls);text("\n");
    check(polls<poll_limit && now-start>=declared,"DDR_CALIBRATION_INTERVAL_COMPLETE");
    text("DDR_CALIBRATION_SCOPE host_coarse_0.9_to_1.1_seconds_required; not_fine_accuracy\n");
    return ddr_sweep_main();
}
