/* Shared execution/readback checks; release is platform-specific, not PSCI. */
#include "lab.h"
struct record { uint64_t ready,mpidr,midr,el; };
static volatile struct record records[4];
volatile uint64_t multicore_ready;
extern void secondary_start(void);
void secondary_main(unsigned cpu) {
 if (cpu>=4) for (;;) __asm__ volatile("wfi");
 while (multicore_ready!=0xcafe1234ULL) __asm__ volatile("yield" ::: "memory");
 records[cpu].mpidr=SYS(mpidr_el1);
 records[cpu].midr=SYS(midr_el1);
 records[cpu].el=SYS(CurrentEL);
 barrier();records[cpu].ready=0xcafe;barrier();
#ifdef LAB_AGILEX5
 /* Stable parking code survives subsequent diagnostic reloads. */
 ((void (*)(void))0x82010000UL)();
#endif
 for (;;) __asm__ volatile("wfi");
}
int main(void) {
 lab_begin("multicore");
#ifdef LAB_AGILEX5
 check(!(MMIO32(0x10d14058)&0xc00),"A55_BOOT_CONFIGURATION");
 MMIO32(0x82010000)=0xd503205f;MMIO32(0x82010004)=0x17ffffff;
#endif
 multicore_ready=0xcafe1234ULL;barrier();
#ifdef LAB_AGILEX5
 /* Same matching TF-A reset/power sequence as our qualified board example. */
 MMIO32(0x10d1220c)=(MMIO32(0x10d1220c)&~0x3cU)|8;
 *(volatile uint64_t *)0x10d110a0=(uintptr_t)secondary_start>>2;
 *(volatile uint64_t *)0x10d110a8=(uintptr_t)secondary_start>>2;
 *(volatile uint64_t *)0x10d110b0=(uintptr_t)secondary_start>>2;
 barrier();MMIO32(0x10d14050)|=0xe<<1;barrier();MMIO32(0x10d11094)=0xe;
#endif
 uint64_t deadline=SYS(cntpct_el0)+5*SYS(cntfrq_el0);
 for (unsigned cpu=1;cpu<4;cpu++) {
  while (records[cpu].ready!=0xcafe)
   if (SYS(cntpct_el0)>deadline) fail("SECONDARY_EXECUTION_TIMEOUT");
  barrier();
  value("SECONDARY_CPU=",cpu);value("MPIDR=",records[cpu].mpidr);
  value("MIDR=",records[cpu].midr);value("EL=",records[cpu].el>>2);
#ifdef LAB_AGILEX5
  unsigned affinity=(records[cpu].mpidr>>8)&255;
  unsigned expected_part=cpu==1?0xd05:0xd0b;
#else
  unsigned affinity=records[cpu].mpidr&255;
  unsigned expected_part=0xd03; /* QEMU practice profile: Cortex-A53. */
#endif
  check(affinity==cpu && records[cpu].el==12 &&
        ((records[cpu].midr>>24)&255)==0x41 &&
        ((records[cpu].midr>>4)&4095)==expected_part,"SECONDARY_IDENTITY");
 }
 check(1,"THREE_SECONDARIES_EXECUTED");lab_done(0);
}
