/* Run after the verified ATF DDR initializer, at AArch64 EL3, MMU/D-cache off. */
#include <stdint.h>
#define REG32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define READ_SYS(name) ({uint64_t x; __asm__ volatile("mrs %0, " #name : "=r"(x)); x;})
static void put(char c) { while(!(REG32(0x10c02014)&0x20)){} REG32(0x10c02000)=(uint8_t)c; }
static void text(const char *s) { while(*s) {if(*s=='\n')put('\r'); put(*s++);} }
static void hex(uint64_t x) { text("0x"); for(int i=60;i>=0;i-=4)put("0123456789abcdef"[(x>>i)&15]); }
static void value(const char *name,uint64_t x) {text(name);hex(x);text("\n");}
extern void neon_add(const uint32_t *,const uint32_t *,uint32_t *);
static void cpu_neon(void) {
    value("MIDR_EL1 = ",READ_SYS(midr_el1));
    value("MPIDR_EL1 = ",READ_SYS(mpidr_el1));
    value("CurrentEL = ",READ_SYS(CurrentEL));
    const uint32_t a[4]={1,2,3,4},b[4]={10,20,30,40};uint32_t c[4];
    neon_add(a,b,c);
    for(unsigned i=0;i<4;i++)if(c[i]!=(i+1)*11){text("FAIL CPU_NEON\n");return;}
    text("PASS CPU_NEON: four vector additions\n");
}
static void cache_info(void) {
    value("CTR_EL0 = ",READ_SYS(ctr_el0));
    value("CLIDR_EL1 = ",READ_SYS(clidr_el1));
    value("SCTLR_EL3 = ",READ_SYS(sctlr_el3));
    text("PASS CACHE_INFO: configuration read; cache coherency is a separate test\n");
}
static void ddr_buffers(void) {
    volatile uint64_t *s=(volatile uint64_t *)0x85000000UL;
    volatile uint64_t *d=(volatile uint64_t *)0x85010000UL;
    for(unsigned i=0;i<8192;i++){s[i]=0x5a5a000000000000ULL^i;d[i]=0;}
    for(unsigned i=0;i<8192;i++)d[i]=s[i];
    __asm__ volatile("dsb sy" ::: "memory");
    for(unsigned i=0;i<8192;i++)if(d[i]!=(0x5a5a000000000000ULL^i)){text("FAIL DDR_BUFFERS\n");return;}
    text("PASS DDR_BUFFERS: CPU copied and verified 64 KiB\n");
}
static void gpio_input(void) {
    value("GPIO0 direction = ",REG32(0x10c03204));
    value("GPIO0 external inputs = ",REG32(0x10c03250));
    text("PASS GPIO_READ: no output pin direction changed\n");
}
static void timer_counter(void) {
    uint64_t before=READ_SYS(cntpct_el0);
    for(volatile unsigned i=0;i<100000;i++){}
    uint64_t after=READ_SYS(cntpct_el0);
    value("CNTFRQ_EL0 = ",READ_SYS(cntfrq_el0));value("Counter delta = ",after-before);
    text(after>before?"PASS COUNTER: generic timer increments\n":"FAIL COUNTER: counter did not increment\n");
}
static void gic_info(void) {
    value("GICD_TYPER = ",REG32(0x1d000004));
    value("GICD_IIDR = ",REG32(0x1d000008));
    text("PASS GIC_INFO: identification only; interrupt delivery is a separate example\n");
}
void example_main(void) {
    text("HPS CORE EXAMPLES BEGIN (DDR 0x82100000)\n");
    cpu_neon();cache_info();ddr_buffers();gpio_input();timer_counter();gic_info();
    text("HPS CORE EXAMPLES COMPLETE\n");
}
