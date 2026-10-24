/* EL3 identity map: device below 2 GiB, normal noncacheable DDR above it.
 * Demonstrates actual AT translation and a DDR load/store with MMU enabled.
 */
#include "common.h"
static uint64_t table[512] __attribute__((aligned(4096)));
void example_main(void){
 text("HPS MMU EXAMPLE BEGIN\n");
 uint64_t saved=SYS(sctlr_el3);
 if(saved&5){text("FAIL MMU: expected MMU and data cache off\n");return;}
 for(unsigned i=0;i<4;i++)table[i]=((uint64_t)i<<30)|1|(1<<10)|(i>=2?4:0);
 barrier();MSR(mair_el3,0x4404);MSR(ttbr0_el3,(uintptr_t)table);
 MSR(tcr_el3,(1ULL<<31)|(1<<23)|(2<<16)|(3<<12)|(1<<10)|(1<<8)|32);
 __asm__ volatile("tlbi alle3;dsb sy;isb":::"memory");MSR(sctlr_el3,saved|1);barrier();
 uint64_t address=0x85200000;
 __asm__ volatile("at s1e3r,%0;isb"::"r"(address):"memory");
 uint64_t par=SYS(par_el1);value("PAR_EL1 = ",par);
 R64(address)=0x12345678abcdef01ULL;barrier();uint64_t readback=R64(address);
 int ok=!(par&1)&&((par&0x0000fffffffff000ULL)==address)&&readback==0x12345678abcdef01ULL;
 MSR(sctlr_el3,saved);barrier();__asm__ volatile("tlbi alle3;dsb sy;isb":::"memory");
 text(ok?"PASS MMU_TRANSLATION: EL3 translation and DDR readback\n":"FAIL MMU_TRANSLATION\n");
}
