/* Bench adapter: invokes unchanged upstream examples; no platform clock init. */
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "console_api.h"
#include "example_register.h"
#include "lib_printf.h"
#include "uart_api.h"
#include "socfpga_sip_handler.h"
#include "bridge_api.h"
#include "socfpga_iossm_ll.h"
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
static cli_cmd_t commands[32];
static unsigned count;
static void emit(char c,void *unused) {
    (void)unused;
#ifdef LAB_QEMU
    while(REG(0x09000018)&32) {}
    REG(0x09000000)=(uint8_t)c;
#else
    while(!(REG(0x10c02014)&32)) {}
    REG(0x10c02000)=(uint8_t)c;
#endif
}
int __wrap_printf(const char *fmt,...) {
    va_list ap; va_start(ap,fmt);
    int n=lib_vprintf(emit,0,fmt,ap); va_end(ap); return n;
}
int __wrap_putchar(int c) {emit((char)c,0);return c;}
int __wrap_puts(const char *s) {while(*s)emit(*s++,0);emit('\n',0);return 0;}
int __wrap_cli_register_command(const char *name,cmd_func_t fn) {
    if(count>=32)return -1;
    commands[count++]=(cli_cmd_t){name,fn}; return 0;
}
static void dispatch(const char *name,const char *args) {
    printf("UPSTREAM_COMMAND %s %s\n",name,args);
    for(unsigned i=0;i<count;i++) {
        const char *a=name,*b=commands[i].name;
        while(*a && *a==*b){a++;b++;}
        if(*a || *b)continue;
        commands[i].func(args);return;
    }
    printf("FAIL command not registered\n");
}
__attribute__((noreturn,noinline)) void lab_done(unsigned status) {
    printf("UPSTREAM_LAB_COMPLETE status=%u\n",status);
#ifdef LAB_QEMU
    uint64_t block[2]={0x20026,status};
    register uint64_t op __asm__("x0")=0x20;
    register void *arg __asm__("x1")=block;
    __asm__ volatile("hlt #0xf000"::"r"(op),"r"(arg):"memory");
#endif
    for(;;)__asm__ volatile("wfi");
}
void fault(void) {
    uint64_t esr,elr,far;
    uint64_t el;__asm__ volatile("mrs %0,CurrentEL":"=r"(el));
    if(el==12) {
      __asm__ volatile("mrs %0,esr_el3":"=r"(esr));
      __asm__ volatile("mrs %0,elr_el3":"=r"(elr));
      __asm__ volatile("mrs %0,far_el3":"=r"(far));
    } else if(el==8) {
      __asm__ volatile("mrs %0,esr_el2":"=r"(esr));
      __asm__ volatile("mrs %0,elr_el2":"=r"(elr));
      __asm__ volatile("mrs %0,far_el2":"=r"(far));
    } else {
      __asm__ volatile("mrs %0,esr_el1":"=r"(esr));
      __asm__ volatile("mrs %0,elr_el1":"=r"(elr));
      __asm__ volatile("mrs %0,far_el1":"=r"(far));
    }
    printf("FAIL EXCEPTION ESR=0x%llx ELR=0x%llx FAR=0x%llx\n",esr,elr,far);
    lab_done(1);
}
void main(void) {
#ifndef LAB_QEMU
    /* DDR mode hook preserves the bootstrapped UART and pinmux. */
    uart_init(0,115200,100000000);
#endif
    printf("UPSTREAM_LAB_BEGIN case=%u\n",LAB_CASE);
    uint64_t el;__asm__ volatile("mrs %0,CurrentEL":"=r"(el));
    printf("GUEST_EXCEPTION_LEVEL=%u\n",(unsigned)(el>>2));
    app_register();
    unsigned status=0;
    if(LAB_CASE==0) dispatch("crc_selftest","");
    if(LAB_CASE==11) {__asm__ volatile("msr cntfrq_el0,xzr; isb":::"memory");}
    if(LAB_CASE==1 || LAB_CASE==11) {
        uint64_t hz;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(hz));
        printf("COUNTER_HZ=%llu\n",hz);
        if(!hz)printf("TIMING_UNAVAILABLE counter frequency is zero; memory correctness only\n");
        if(hz) {
            uint64_t start,now;
            printf("COUNTER_INTERVAL_START\n");
            __asm__ volatile("isb; mrs %0,cntpct_el0":"=r"(start));
            do {__asm__ volatile("isb; mrs %0,cntpct_el0":"=r"(now));} while(now-start<hz);
            printf("COUNTER_INTERVAL_END ticks=%llu\n",now-start);
        }
        dispatch("perf_selftest","timer");
        dispatch("perf_selftest","mem " LAB_SCRATCH_TEXT " 65536 2");
        volatile uint32_t *src=(void *)(uintptr_t)LAB_SCRATCH;
        volatile uint32_t *dst=src+16384;
        unsigned bad=0;
        for(unsigned i=0;i<16384;i++)if(src[i]!=(0xA5000000U^i^1U)||dst[i]!=src[i])bad++;
        printf("%s PERF_MEMORY_READBACK words=16384 mismatches=%u\n",bad?"FAIL":"PASS",bad);
        status=bad!=0;
        dispatch("perf_selftest","latency timer 100");
        dispatch("perf_selftest","log dump");
    }
    if(LAB_CASE==2)dispatch("combophy_selftest","");
    if(LAB_CASE==3)dispatch("noc_selftest","");
    if(LAB_CASE==4)dispatch("iossm_demo","");
    if(LAB_CASE==5)dispatch("bridge_selftest",LAB_BRIDGE_ARGS);
    if(LAB_CASE==6)dispatch("reset_mngr_selftest","");
    if(LAB_CASE==10) {
        bridge_handle_t bridge=bridge_api_open(BRIDGE_API_LWHPS2FPGA);
        int enabled=bridge?bridge_api_enable(bridge):-1;
        int disabled=bridge?bridge_api_disable(bridge):-1;
        if(bridge)bridge_api_close(BRIDGE_API_LWHPS2FPGA);
        status=enabled!=0 || disabled!=0;
        printf("%s BRIDGE_CONTROL enable=%d disable=%d (no fabric memory access)\n",status?"FAIL":"PASS",enabled,disabled);
    }
    if(LAB_CASE==9) {
        uint64_t regs[SMC_CALL_REG_COUNT]={0};
        int rc=smc_call(0x84000000,regs);
        int ok=el==12 && rc==-1 && IOSSM_LL_RESPONSE_OK(0x10001) && !IOSSM_LL_RESPONSE_OK(3) && !IOSSM_LL_RESPONSE_OK(0) && (0x101U&IOSSM_ECC_COUNT_MASK)==0x101U;
        printf("%s SMC_EL3_REJECTED_AND_IOSSM_STATUS_VALIDATED\n",ok?"PASS":"FAIL");
        status=!ok;
    }
    if(LAB_CASE==8)dispatch("mailbox_selftest","");
    if(LAB_CASE==7)dispatch("reboot_mngr_selftest","");
    /* Host checks detailed results; completion alone is never a PASS. */
    lab_done(status);
}
