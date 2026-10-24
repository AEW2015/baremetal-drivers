#include <stdint.h>
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define UART 0x10c02000u
volatile uint32_t uart_diag[8] = {0x48454c4f,0,0,0,0,0,0,0};
static uint32_t swap(uint32_t x) { return __builtin_bswap32(x); }
static void handoff(unsigned off, unsigned base, unsigned count) {
    volatile uint32_t *h=(volatile uint32_t *)(uintptr_t)(0x7f000+off);
    for(unsigned i=0;i<count;i++) REG(base+swap(h[2*i]))=swap(h[2*i+1]);
}
void uart_main(void) {
    handoff(0x20,0x10d13000,48);
    handoff(0x1b0,0x10d13130,48);
    handoff(0x340,0x10d13300,20);
    handoff(0x400,0x10d13400,48);
    REG(0x10d11028) &= ~0x30000u;
    REG(UART+0xc)=0x83;
    REG(UART)=54;
    REG(UART+4)=0;
    REG(UART+0xc)=3;
    REG(UART+4)=0;
    REG(UART+8)=7;
    REG(UART+0x10)=0;
    const char *msg="Hello, World! Agilex 5 HPS OCRAM UART\r\n";
    for(;;) {
        for(const char *p=msg;*p;p++) {
            while(!(REG(UART+0x14)&0x20)) {}
            uint64_t before, after, freq;
            __asm__ volatile("mrs %0, cntpct_el0" : "=r"(before));
            REG(UART)=(unsigned char)*p;
            while(!(REG(UART+0x14)&0x40)) {}
            __asm__ volatile("mrs %0, cntpct_el0" : "=r"(after));
            __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(freq));
            __asm__ volatile("mov x20, %0; mov x21, %1" :: "r"(after-before), "r"(freq) : "x20", "x21");
        }
        uart_diag[1]++;
        uart_diag[2]=REG(UART+0x14);
        uart_diag[3]=REG(UART+0x7c);
        uart_diag[4]=REG(0x10d10000);
        for(volatile unsigned i=0;i<1000000;i++) {}
    }
}
