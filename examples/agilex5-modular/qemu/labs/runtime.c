#include "lab.h"
#ifdef LAB_AGILEX5
#define UART 0x10c02000UL
#else
#define UART 0x09000000UL
#endif
volatile struct exception_record last_exception;
exception_handler_t exception_handler;

void uart_init(void) {
#ifndef LAB_AGILEX5
 MMIO32(UART+0x30)=0;
 MMIO32(UART+0x24)=1;
 MMIO32(UART+0x28)=0;
 MMIO32(UART+0x2c)=(3U<<5)|(1U<<4); /* 8-bit words, FIFO enabled */
 MMIO32(UART+0x44)=0x7ff;
 MMIO32(UART+0x30)=0x301; /* UARTEN, TXE, RXE */
#endif /* Preserve the physical handoff's DW16550 clock/divisor. */
}
void putchar_uart(char c) {
#ifdef LAB_AGILEX5
 if (c=='\n') putchar_uart('\r');
 while (!(MMIO32(UART+0x14)&0x20)) {}
#else
 while (MMIO32(UART+0x18)&(1U<<5)) {}
#endif
 MMIO32(UART)=(uint8_t)c;
}
int getchar_uart(void) {
 uint64_t deadline=SYS(cntpct_el0)+60*SYS(cntfrq_el0);
#ifdef LAB_AGILEX5
 while (!(MMIO32(UART+0x14)&1))
#else
 while (MMIO32(UART+0x18)&(1U<<4))
#endif
  if (SYS(cntpct_el0)>deadline) return -1;
 return (int)(MMIO32(UART)&255);
}
void text(const char *s) { while (*s) putchar_uart(*s++); }
void hex(uint64_t v) {
 text("0x");
 for (int i=60;i>=0;i-=4) putchar_uart("0123456789abcdef"[(v>>i)&15]);
}
void value(const char *name,uint64_t v) { text(name); hex(v); text("\n"); }
void check(int condition,const char *message) {
 if (!condition) fail(message);
 text("PASS "); text(message); text("\n");
}
void lab_begin(const char *name) {
 uart_init();
 text("LAB BEGIN "); text(name); text("\n");
 if (SYS(CurrentEL)!=12) fail("EL3 required");
}
__attribute__((noreturn,noinline)) void lab_done(unsigned status) {
 text(status ? "LAB FAILED\n" : "LAB COMPLETE\n");
#ifndef LAB_AGILEX5
 uint64_t reason[2]={0x20026,status};
 register uint64_t operation __asm__("x0")=0x20;
 register void *arguments __asm__("x1")=reason;
 __asm__ volatile("hlt #0xf000" :: "r"(operation),"r"(arguments) : "memory");
#endif
 for (;;) __asm__ volatile("wfi");
}
__attribute__((noreturn)) void fail(const char *message) {
 text("FAIL "); text(message); text("\n"); lab_done(1);
}
void exception_dispatch(unsigned kind) {
 last_exception.kind=kind;
 last_exception.esr=SYS(esr_el3);
 last_exception.elr=SYS(elr_el3);
 last_exception.far=SYS(far_el3);
 if (exception_handler) { exception_handler(kind); return; }
 value("ESR_EL3=",last_exception.esr);
 value("ELR_EL3=",last_exception.elr);
 value("FAR_EL3=",last_exception.far);
 fail("unexpected exception");
}
