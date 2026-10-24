#include "lab.h"
#define GICD 0x08000000UL
#define GICR 0x080a0000UL
#define SGI (GICR+0x10000)
#define TIMER_PPI 29U /* Secure physical timer: Group 0 delivers FIQ at EL3. */
#ifndef EXPECT_TIMER_PPI
#define EXPECT_TIMER_PPI TIMER_PPI
#endif
volatile unsigned ticks,wfi_entries;
static uint64_t interval;
static void handle_timer(unsigned kind) {
 uint64_t irq=SYS(icc_iar0_el1)&0xffffff;
 if (kind!=2 || irq!=EXPECT_TIMER_PPI || !(SYS(cntps_ctl_el1)&4)) fail("timer interrupt identity");
 MSR(cntps_ctl_el1,0);
 ticks++;
 if (ticks<10) { MSR(cntps_tval_el1,interval); MSR(cntps_ctl_el1,1); }
 MSR(icc_eoir0_el1,irq);
 barrier();
}
static void wait_clear(uintptr_t reg,uint32_t mask) {
 unsigned timeout=1000000;
 while (MMIO32(reg)&mask) if (!--timeout) fail("GIC configuration timeout");
}
int main(void) {
 lab_begin("timer");
 exception_handler=handle_timer;
 interval=SYS(cntfrq_el0)/100; /* Ten 10-ms intervals; not a speed benchmark. */
 check(interval>0,"TIMER_FREQUENCY");
 MMIO32(GICD)=0; wait_clear(GICD,1U<<31);
 MMIO32(GICD)=1U<<4; wait_clear(GICD,1U<<31);
 MMIO32(GICR+0x14)&=~2U; wait_clear(GICR+0x14,4);
 MMIO32(SGI+0x180)=1U<<TIMER_PPI;
 MMIO32(SGI+0x80)&=~(1U<<TIMER_PPI);
 MMIO32(SGI+0xd00)&=~(1U<<TIMER_PPI);
 MMIO32(SGI+0x400+28)=0x80808080;
 MMIO32(SGI+0x100)=1U<<TIMER_PPI;
 MMIO32(GICD)=(1U<<4)|1;
 MSR(icc_sre_el3,SYS(icc_sre_el3)|15); barrier();
 MSR(icc_pmr_el1,0xff);
 MSR(icc_igrpen0_el1,1);
 MSR(scr_el3,SYS(scr_el3)|4); barrier();
 MSR(cntps_tval_el1,interval); MSR(cntps_ctl_el1,1); barrier();
 /* Mask around the condition check to avoid a final-interrupt/WFI race.
  * A pending interrupt wakes WFI even while masked, then unmask to service it. */
 while (ticks<10) {
  __asm__ volatile("msr daifset,#3" ::: "memory");
  if (ticks<10) { wfi_entries++; __asm__ volatile("dsb sy; wfi" ::: "memory"); }
  __asm__ volatile("msr daifclr,#3; isb" ::: "memory");
 }
 __asm__ volatile("msr daifset,#3" ::: "memory");
 MSR(cntps_ctl_el1,0); MSR(icc_igrpen0_el1,0);
 check(ticks==10,"TIMER_10_INTERRUPTS");
 check(wfi_entries>0,"WFI_IDLE_LOOP");
 value("TICKS=",ticks); value("WFI_ENTRIES=",wfi_entries);
 lab_done(0);
}
