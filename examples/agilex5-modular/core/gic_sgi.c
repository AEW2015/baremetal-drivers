/* GICv3 secure Group-0 SGI, acknowledged by polling (no exception vector).
 * Requires exclusive bare-metal ownership of the GIC; reboot the bootstrap after.
 */
#include <stdint.h>
#define R(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define SYS(name) ({uint64_t x;__asm__ volatile("mrs %0,"#name:"=r"(x));x;})
#define MSR(name,v) __asm__ volatile("msr "#name",%0"::"r"((uint64_t)(v)):"memory")
static void put(char c){while(!(R(0x10c02014)&0x20)){}R(0x10c02000)=(uint8_t)c;}
static void text(const char*s){while(*s){if(*s=='\n')put('\r');put(*s++);}}
void example_main(void){
 text("HPS GIC SGI EXAMPLE BEGIN\n");
 uint64_t mpidr=SYS(mpidr_el1);
 if((mpidr&0xffffff)!=0){text("FAIL GIC: example expects boot core affinity 0\n");return;}
 R(0x1d000000)=0;__asm__ volatile("dsb sy;isb");
 R(0x1d000000)=0x10; /* ARE_S, groups disabled during configuration */
 /* GIC-600 redistributor power is separate from architectural sleep. */
 unsigned power_timeout=1000000;
 while((((R(0x1d060024)>>2)^(R(0x1d060024)>>3))&1)&&--power_timeout){}
 if(!power_timeout){text("FAIL GIC: power group transition timeout\n");return;}
 R(0x1d060024)=0;
 power_timeout=1000000;while((R(0x1d060024)&1)&&--power_timeout){}
 if(!power_timeout){text("FAIL GIC: redistributor power timeout\n");return;}
 R(0x1d060014)&=~2U; /* wake A55.0 redistributor */
 unsigned n=1000000;while((R(0x1d060014)&4)&&--n){}
 if(!n){text("FAIL GIC: redistributor wake timeout\n");return;}
 R(0x1d070180)=1;R(0x1d070080)&=~1U;R(0x1d070d00)&=~1U;
 R(0x1d070400)=(R(0x1d070400)&~255U)|0x80;
 R(0x1d070100)=1;R(0x1d000000)=0x11;
 MSR(icc_sre_el3,SYS(icc_sre_el3)|15);__asm__ volatile("isb");
 MSR(icc_pmr_el1,0xff);MSR(icc_igrpen0_el1,1);__asm__ volatile("dsb sy;isb");
 uint64_t sgi=((mpidr>>32)&255ULL)<<48|((mpidr>>16)&255ULL)<<32|((mpidr>>8)&255ULL)<<16|1;
 MSR(icc_sgi0r_el1,sgi);__asm__ volatile("isb");
 uint64_t irq=1023;n=1000000;
 do{irq=SYS(icc_iar0_el1)&0xffffff;}while(irq>=1020&&--n);
 if(irq==0){MSR(icc_eoir0_el1,irq);text("PASS GIC_SGI: core 0 received and acknowledged SGI 0\n");}
 else{text("FAIL GIC: SGI not acknowledged\n");}
 MSR(icc_igrpen0_el1,0);R(0x1d070180)=1;__asm__ volatile("dsb sy;isb");
}
