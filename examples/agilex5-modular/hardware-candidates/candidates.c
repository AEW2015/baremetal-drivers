/* Isolated hardware wrappers: no upstream main, FSBL, pinmux or clock init. */
#include <stdarg.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include "console_api.h"
#include "example_register.h"
#include "lib_printf.h"
#include "ccu_api.h"
#include "clk_mngr_api.h"
#include "dma_api.h"
#include "mmu_api.h"
#include "smmu_api.h"
#include "timer_api.h"
#include "spi_api.h"
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define REG64(a) (*(volatile uint64_t *)(uintptr_t)(a))
static cli_cmd_t commands[32];
static unsigned count,failures;
static void emit(char c,void *unused) {
 (void)unused;
 while(!(REG(0x10c02014)&32U)){}
 REG(0x10c02000)=(uint8_t)c;
}
int __wrap_printf(const char *fmt,...) {
 va_list ap;va_start(ap,fmt);int n=lib_vprintf(emit,0,fmt,ap);va_end(ap);return n;
}
int __wrap_putchar(int c){emit((char)c,0);return c;}
int __wrap_puts(const char *s){while(*s)emit(*s++,0);emit('\n',0);return 0;}
int __wrap_cli_register_command(const char *name,cmd_func_t fn) {
 if(count>=32)return -1;
 commands[count++]=(cli_cmd_t){name,fn};return 0;
}
static void check(bool ok,const char *name){printf("%s %s\n",ok?"PASS":"FAIL",name);if(!ok)failures++;}
__attribute__((noreturn,noinline)) void candidate_done(unsigned status);
void __real_gic_api_init(void);
void __wrap_gic_api_init(void) {
 /* The unchanged SGI command calls this before unmasking DAIF. Its SDK
  * initializer enables both interrupt groups, while our EL3 vector services
  * Group0 only. Disable both secure/nonsecure Group1 CPU-interface enables
  * before the command can unmask interrupts. No SDK source is changed. */
 __real_gic_api_init();
 uint64_t el,group1;
 __asm__ volatile("mrs %0,CurrentEL":"=r"(el));
 if(el!=12){check(false,"GIC_GROUP0_STANDALONE_EL3_REQUIRED");candidate_done(failures);}
 __asm__ volatile("msr icc_igrpen1_el3,xzr; isb; mrs %0,icc_igrpen1_el3":"=r"(group1)::"memory");
 printf("GIC_GROUP1_CPU_CONTROL=0x%llx\n",group1);
 check((group1&3U)==0,"GIC_GROUP1_CPU_DISABLED");
 if(failures)candidate_done(failures);
}
static void dispatch(const char *name,const char *args) {
 printf("CANDIDATE_COMMAND %s %s\n",name,args);
 for(unsigned i=0;i<count;i++) {
  const char *a=name,*b=commands[i].name;while(*a&&*a==*b){a++;b++;}
  if(!*a&&!*b){commands[i].func(args);return;}
 }
 check(false,"COMMAND_REGISTERED");
}
__attribute__((noreturn,noinline)) void candidate_done(unsigned status) {
 __asm__ volatile("msr daifset,#15; dsb sy; isb":::"memory");
 printf("CANDIDATE_COMPLETE status=%u\n",status);
 for(;;)__asm__ volatile("wfi");
}
void fault(void) {
 uint64_t esr,elr,far;__asm__ volatile("mrs %0,esr_el3":"=r"(esr));
 __asm__ volatile("mrs %0,elr_el3":"=r"(elr));__asm__ volatile("mrs %0,far_el3":"=r"(far));
 printf("FAIL EXCEPTION ESR=0x%llx ELR=0x%llx FAR=0x%llx\n",esr,elr,far);candidate_done(1);
}
static bool gic_power(void) {
 /* Demonstrated GIC-600 A55.0 redistributor power/wake preflight. */
 unsigned n=1000000;
 while((((REG(0x1d060024)>>2)^(REG(0x1d060024)>>3))&1U)&&--n){}
 if(!n)return false;
 REG(0x1d060024)=0;__asm__ volatile("dsb sy":::"memory");
 n=1000000;while((REG(0x1d060024)&1U)&&--n){}
 if(!n)return false;
 REG(0x1d060014)&=~2U;n=1000000;
 while((REG(0x1d060014)&4U)&&--n){}
 return n!=0;
}
static unsigned char dma_src[4096] __attribute__((aligned(64)));
static unsigned char dma_dst[4096] __attribute__((aligned(64)));
static void dma_strict(void) {
 for(unsigned i=0;i<4096;i++){dma_src[i]=(uint8_t)(0xa5U^(i*37U)^(i>>8));dma_dst[i]=0;}
 int rc=dma_init(0,0);printf("DMA_STRICT_INIT rc=%d\n",rc);check(rc==0,"DMA_STRICT_INIT");
 if(rc)return;
 rc=dma_memcpy(dma_dst,dma_src,4096);printf("DMA_STRICT_COPY rc=%d\n",rc);
 __asm__ volatile("dsb sy":::"memory");
 unsigned bad=0;for(unsigned i=0;i<4096;i++)if(dma_dst[i]!=dma_src[i])bad++;
 printf("DMA_STRICT_READBACK bytes=4096 mismatches=%u\n",bad);
 check(rc==0&&bad==0,"DMA_STRICT_4096_READBACK");
 /* DMA get_error() is a stub in this SDK, so do not use it as error proof. */
 printf("DMA_STRICT_HW CHEN=0x%llx INTSTATUS=0x%llx\n",REG64(0x10db0018),REG64(0x10db0188));
 dma_deinit();
 check((REG64(0x10db0018)&1U)==0,"DMA_STRICT_CHANNEL_IDLE");
}
void main(void) {
 uint64_t el,sctlr;__asm__ volatile("mrs %0,CurrentEL":"=r"(el));__asm__ volatile("mrs %0,sctlr_el3":"=r"(sctlr));
 printf("CANDIDATE_BEGIN name=%s\n",CANDIDATE_NAME);
 printf("CANDIDATE_EL=%u SCTLR=0x%llx\n",(unsigned)(el>>2),sctlr);
 check(el==12&&!(sctlr&5U),"STANDALONE_EL3_MMU_DCACHE_OFF");
 if(failures)candidate_done(failures);
 app_register();
 if(CANDIDATE_CASE==0)dispatch("hello_selftest","");
 if(CANDIDATE_CASE==1) {
  /* The original command unconditionally says PASS and flushes every DMI.
   * Qualify only its two read APIs here; do not execute the flush. */
  uint32_t id=0,error=0;int a=ccu_api_get_id(&id),b=ccu_api_get_error_status(&error);
  printf("CCU_READONLY ID=0x%08x ERROR=0x%08x rc_id=%d rc_error=%d\n",id,error,a,b);
  check(!a&&!b&&id!=0&&id!=0xffffffffU&&id==REG(0x1c000000)&&error==REG(0x1c000108),"CCU_READONLY_API_RAW_AGREE");
  puts("SCOPE CCU status only; original all-DMI flush not executed");
 }
 if(CANDIDATE_CASE==2) {
  /* Do not call cmd_clk_mngr: it initializes clocks and changes L4_SP. */
  uint32_t before=REG(0x10d10044);unsigned ok=0;
  const uint32_t ids[]={CLK_MNGR_BLOCK_UART,CLK_MNGR_BLOCK_WDT,CLK_MNGR_BLOCK_I2C,CLK_MNGR_BLOCK_SP_TIMER,CLK_MNGR_BLOCK_OSC1TIMER,CLK_MNGR_BLOCK_MPU,CLK_MNGR_BLOCK_SSPI,CLK_MNGR_BLOCK_L4MAIN};
  for(unsigned i=0;i<sizeof(ids)/sizeof(ids[0]);i++){uint32_t hz=0;int rc=clk_mngr_api_get_freq(ids[i],&hz);printf("CLK_READONLY block=%u rc=%d frequency_hz=%u\n",ids[i],rc,hz);if(!rc&&hz)ok++;}
  check(ok==sizeof(ids)/sizeof(ids[0]),"CLK_READONLY_ALL_RATES_NONZERO");
  check(before==REG(0x10d10044),"CLK_READONLY_REGISTER_UNCHANGED");
  puts("SCOPE Clock getter path only; no PLL/pinmux/divisor initialization or physical frequency measurement");
 }
 if(CANDIDATE_CASE==3){dispatch("dma_selftest","");dma_strict();}
 if(CANDIDATE_CASE==4){check(gic_power(),"GIC_REDISTRIBUTOR_POWER_READY");if(!failures)dispatch("gic_selftest","");}
 if(CANDIDATE_CASE==5) {
  bool enabled=true;int rc=mmu_api_is_enabled(3,&enabled);
  dispatch("mmu_selftest","3");check(!rc&&!enabled,"MMU_EL3_STATUS_DISABLED");
 }
 if(CANDIDATE_CASE==6) {
  bool enabled=false;int rc=smmu_api_is_enabled(&enabled);uint32_t cr0=REG(0x16000020);
  dispatch("smmu_selftest","");printf("SMMU_STATUS_RAW CR0=0x%08x\n",cr0);
  check(!rc&&enabled==((cr0&1U)!=0),"SMMU_STATUS_API_RAW_AGREE");
 }
 if(CANDIDATE_CASE==7){dispatch("spi_selftest","0 1 32");int rc=spi_api_loopback_test(0,1,256);printf("SPI_API_256 rc=%d\n",rc);check(rc==0,"SPI_API_256_LOOPBACK");}
 if(CANDIDATE_CASE==8)dispatch("timer_selftest","");
 candidate_done(failures);
}
