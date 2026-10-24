/* Physical-kit adapter: preserve initialized UART baud, expose main return value.
 * The vendor driver otherwise installs a fixed divisor for its simulation clock.
 */
#include <stdint.h>
#include <stdio.h>
#define R(a) (*(volatile uint32_t *)(uintptr_t)(a))
#ifndef TEST_NAME
#define TEST_NAME "unknown"
#endif
static void put(char c){while(!(R(0x10c02014)&32)){}R(0x10c02000)=(uint8_t)c;}
static void text(const char *s){while(*s){if(*s=='\n')put('\r');put(*s++);}}
/* newlib expects the number of input bytes consumed, excluding CR insertion.
 * The reference _write returns uart_write's expanded count, corrupting stdio
 * bookkeeping after newline output. Stream directly without a stack VLA. */
int __wrap__write(int fd, const char *buf, int len){
 (void)fd;
 for(int i=0;i<len;i++){
  if(buf[i]=='\n' && (i==0 || buf[i-1]!='\r'))put('\r');
  put(buf[i]);
 }
 return len;
}
extern int32_t __real_uart_init(uintptr_t);
int32_t __wrap_uart_init(uintptr_t base){
 uint32_t lcr=R(base+12);R(base+12)=lcr|128;
 uint32_t lo=R(base),hi=R(base+4);R(base+12)=lcr&~128U;
 int32_t rc=__real_uart_init(base);
 R(base+12)|=128;R(base)=lo;R(base+4)=hi;R(base+12)&=~128U;
 return rc;
}
extern int __real_main(void);
int __wrap_main(void){
 text("HPS_SUITE_BEGIN " TEST_NAME "\n");
 int rc=__real_main();
#ifdef BOARD_TEST_SMMU
 uint32_t id=R(0x16000018);
 printf("SMMU exact IIDR = 0x%08lx\n",(unsigned long)id);
 /* SOM reports product 0x483, variant 2, revision 2, Arm 0x43b.
  * Reference hardcodes revision 1 and its bitwise-AND check is too weak.
  * IIDR field definitions: Linux arm-smmu-v3.h, IIDR_* macros. */
 if(id!=0x4832243b)rc=-2;
#endif
 /* UART test closes its driver; direct polling still reports its result. */
 text(rc==0?"HPS_SUITE_PASS ":"HPS_SUITE_FAIL ");text(TEST_NAME);text(" rc=0x");
 for(int i=28;i>=0;i-=4)put("0123456789abcdef"[((uint32_t)rc>>i)&15]);
 text("\n");return rc;
}
void board_vendor_fault(void){
 uint64_t esr,elr,far;
 __asm__ volatile("mrs %0,esr_el3":"=r"(esr));
 __asm__ volatile("mrs %0,elr_el3":"=r"(elr));
 __asm__ volatile("mrs %0,far_el3":"=r"(far));
 text("HPS_SUITE_FAIL " TEST_NAME " exception ESR/ELR/FAR\n");
 uint64_t regs[3]={esr,elr,far};
 for(unsigned j=0;j<3;j++){text("0x");for(int i=60;i>=0;i-=4)put("0123456789abcdef"[(regs[j]>>i)&15]);text("\n");}
 for(;;)__asm__ volatile("wfi");
}
extern int32_t stdout_uart_fd;
extern void __libc_init_array(void);
static uint64_t board_l1[512] __attribute__((aligned(4096)));
void board_vendor_run(void){
 /* Normal noncacheable DDR permits libc's unaligned accesses; device MMIO
  * below 2 GiB retains device attributes. Same TCR as the tested MMU sample. */
 for(unsigned i=0;i<4;i++)board_l1[i]=((uint64_t)i<<30)|1|(1<<10)|(i>=2?4:0);
 uint64_t mair=0x4404,tcr=(1ULL<<31)|(1<<23)|(2<<16)|(3<<12)|(1<<10)|(1<<8)|32;
 uint64_t ttbr=(uintptr_t)board_l1,sctlr;
 __asm__ volatile("dsb sy;msr mair_el3,%0;msr tcr_el3,%1;msr ttbr0_el3,%2;tlbi alle3;dsb sy;isb"::"r"(mair),"r"(tcr),"r"(ttbr):"memory");
 __asm__ volatile("mrs %0,sctlr_el3":"=r"(sctlr));sctlr=(sctlr|1)&~6ULL; /* A=0 for newlib unaligned normal-memory loads; C=0. */
 __asm__ volatile("msr sctlr_el3,%0;isb"::"r"(sctlr):"memory");
 __libc_init_array();
 stdout_uart_fd=0x10c02000;
 setvbuf(stdout,0,_IONBF,0);
 (void)__wrap_main();
}
