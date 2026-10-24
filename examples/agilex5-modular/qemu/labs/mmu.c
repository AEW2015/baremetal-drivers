#include "lab.h"
#define RO 0x44000000UL
#define RW 0x44200000UL
static uint64_t l1[512] __attribute__((aligned(4096)));
static uint64_t l2[512] __attribute__((aligned(4096)));
volatile unsigned permission_faults;
extern void trigger_store(uintptr_t address,uint64_t v),store_instruction(void),store_resume(void);
static void handle_abort(unsigned kind) {
 if (kind!=0 || last_exception.esr>>26!=0x25 || (last_exception.esr&0x3f)!=0x0e ||
     !(last_exception.esr&(1U<<6)) || last_exception.far!=RO ||
     last_exception.elr!=(uintptr_t)store_instruction) fail("unexpected permission syndrome");
 permission_faults++;
 value("ESR_EL3=",last_exception.esr);
 value("ELR_EL3=",last_exception.elr);
 value("FAR_EL3=",last_exception.far);
 MSR(elr_el3,(uintptr_t)store_resume);
}
int main(void) {
 lab_begin("mmu");
 uint64_t saved=SYS(sctlr_el3);
 check(!(saved&5),"MMU_AND_DCACHE_INITIALLY_OFF");
 *(volatile uint64_t *)RO=0x1122334455667788ULL;
 /* L1 device block for low MMIO; L2 normal noncacheable RAM blocks. */
 l1[0]=1|(1U<<10)|(1ULL<<54);
 l1[1]=(uintptr_t)l2|3;
 /* QEMU has 128 MiB RAM: leave entries beyond its 64 blocks invalid. */
 for (unsigned i=0;i<64;i++) l2[i]=(0x40000000ULL+((uint64_t)i<<21))|1|(1U<<10)|4;
#ifndef WRITABLE_RO
 l2[(RO-0x40000000UL)>>21]|=1U<<7; /* EL3 AP[2]: read-only */
#endif
 exception_handler=handle_abort;
 barrier(); MSR(mair_el3,0x4404); MSR(ttbr0_el3,(uintptr_t)l1);
 MSR(tcr_el3,(1ULL<<31)|(1U<<23)|(2U<<16)|(3U<<12)|(1U<<10)|(1U<<8)|32);
 __asm__ volatile("tlbi alle3; dsb sy; isb" ::: "memory");
 MSR(sctlr_el3,saved|1); barrier();
 *(volatile uint64_t *)RW=0xaabbccddeeff0011ULL;
 check(*(volatile uint64_t *)RW==0xaabbccddeeff0011ULL,"MMU_RW_READBACK");
 check(*(volatile uint64_t *)RO==0x1122334455667788ULL,"MMU_RO_READBACK");
 trigger_store(RO,0xbad);
 check(permission_faults==1,"MMU_WRITE_PERMISSION_FAULT");
 check(*(volatile uint64_t *)RO==0x1122334455667788ULL,"MMU_RO_UNCHANGED");
 MSR(sctlr_el3,saved); barrier();
 __asm__ volatile("tlbi alle3; dsb sy; isb" ::: "memory");
 check(!(SYS(sctlr_el3)&1),"MMU_DISABLED_AFTER_TEST");
 lab_done(0);
}
