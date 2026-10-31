#ifndef PR_LAB_DRIVER_H
#define PR_LAB_DRIVER_H
#include "../lab_driver.h"
#define PR_CONTROL 0x40
#define PR_HEARTBEAT 0x44
#define PR_SCRATCH 0x48
#define PR_EXPECTED 0x4c
#define PR_SWAPS 0x50
#define PR_OBSERVED 0x54
#define PR_SIGNATURE 0x58
#define PR_SIM_LOAD 0x80 /* SIMULATION ONLY; absent from physical static shell */
int pr_prepare(struct lab_device *d,uint32_t persona,unsigned polls);
int pr_finish(struct lab_device *d,uint32_t persona,unsigned polls);
#endif
