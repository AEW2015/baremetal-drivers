/* Bare-metal PSCI helper exercise. Requires resident BL31 and NS EL2 caller. */
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include "lib_printf.h"
#define REG(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define REC ((volatile struct record *)(uintptr_t)0x85000000)
#define CONTEXT UINT64_C(0x5053434943545854)
#define READY UINT64_C(0x5053434952454144)
#define RELEASE UINT64_C(0x4f464643505531)
#define TARGET UINT64_C(0x100)
#define PSCI_VERSION UINT64_C(0x84000000)
#define PSCI_FEATURES UINT64_C(0x8400000a)
#define PSCI_CPU_ON UINT64_C(0xc4000003)
#define PSCI_CPU_OFF UINT64_C(0x84000002)
#define PSCI_AFFINITY UINT64_C(0xc4000004)
struct record {
 uint64_t context,midr,mpidr,el,sctlr,secondary_entry,stack,fault;
 uint64_t ready,release,off_attempt,off_returned,off_result;
};
extern int64_t example_psci_cpu_on(uint64_t,uintptr_t,uint64_t);
extern void psci_secondary_entry(void);
static unsigned failures;
static uint64_t timer_hz;
static void dsb(void){__asm__ volatile("dsb sy":::"memory");}
static uint64_t current_el(void){uint64_t v;__asm__ volatile("mrs %0,CurrentEL":"=r"(v));return v>>2;}
static uint64_t ticks(void){uint64_t v;__asm__ volatile("isb; mrs %0,cntpct_el0":"=r"(v));return v;}
static int64_t call(uint64_t id,uint64_t a,uint64_t b,uint64_t c) {
 register uint64_t x0 __asm__("x0")=id,x1 __asm__("x1")=a,x2 __asm__("x2")=b,x3 __asm__("x3")=c;
 __asm__ volatile("smc #0":"+r"(x0),"+r"(x1),"+r"(x2),"+r"(x3)::"memory","x4","x5","x6","x7");
 return (int64_t)x0;
}
static void emit(char c,void *unused){(void)unused;while(!(REG(0x10c02014)&32U)){}REG(0x10c02000)=(uint8_t)c;}
int __wrap_printf(const char *fmt,...){va_list ap;va_start(ap,fmt);int n=lib_vprintf(emit,0,fmt,ap);va_end(ap);return n;}
int __wrap_puts(const char *s){while(*s)emit(*s++,0);emit('\n',0);return 0;}
int __wrap_putchar(int c){emit((char)c,0);return c;}
static void check(bool ok,const char *name){printf("%s %s\n",ok?"PASS":"FAIL",name);if(!ok)failures++;}
__attribute__((noreturn)) static void finish(unsigned status){printf("PSCI_COMPLETE status=%u\n",status);for(;;)__asm__ volatile("wfi");}
__attribute__((noreturn)) static void blocked(const char *reason,int64_t code){printf("BLOCKED PSCI reason=%s code=%lld\n",reason,(long long)code);finish(2);}
void primary_fault(void) {
 uint64_t el=current_el(),esr=0,pc=0;
 if(el==2){__asm__ volatile("mrs %0,esr_el2":"=r"(esr));__asm__ volatile("mrs %0,elr_el2":"=r"(pc));}
 else if(el==3){__asm__ volatile("mrs %0,esr_el3":"=r"(esr));__asm__ volatile("mrs %0,elr_el3":"=r"(pc));}
 printf("FAIL PSCI_PRIMARY_EXCEPTION EL=%llu ESR=0x%llx PC=0x%llx\n",el,esr,pc);finish(1);
}
__attribute__((noreturn)) static void secondary_off(void) {
 REC->off_attempt=1;dsb();
 int64_t rc=call(PSCI_CPU_OFF,0,0,0);
 REC->off_result=(uint64_t)rc;REC->off_returned=1;dsb();
 for(;;)__asm__ volatile("wfi");
}
void secondary_fault(void) {
 REC->fault=2;dsb();REC->ready=READY;dsb();secondary_off();
}
void secondary_wrong_el(uint64_t context) {
 REC->context=context;REC->el=current_el();REC->fault=1;dsb();REC->ready=READY;dsb();
 /* A PSCI SMC from an unexpected level is not attempted. */
 for(;;)__asm__ volatile("wfi");
}
void secondary_main(uint64_t context) {
 uint64_t midr,mpidr,sctlr,stack;
 __asm__ volatile("mrs %0,midr_el1":"=r"(midr));__asm__ volatile("mrs %0,mpidr_el1":"=r"(mpidr));
 __asm__ volatile("mrs %0,sctlr_el2":"=r"(sctlr));__asm__ volatile("mov %0,sp":"=r"(stack));
 REC->context=context;REC->midr=midr;REC->mpidr=mpidr;REC->el=current_el();REC->sctlr=sctlr;
 REC->secondary_entry=(uintptr_t)psci_secondary_entry;REC->stack=stack;REC->fault=0;
 dsb();REC->ready=READY;dsb();
 /* Both elapsed counter and finite polls bound a missing primary release. */
 uint64_t frequency;__asm__ volatile("mrs %0,cntfrq_el0":"=r"(frequency));if(!frequency)frequency=400000000;
 uint64_t start=ticks();unsigned polls=100000000;
 while(REC->release!=RELEASE&&--polls&&ticks()-start<frequency*5U){}
 secondary_off();
}
static bool wait_ready(void){uint64_t start=ticks();unsigned n=100000000;while(REC->ready!=READY&&--n&&ticks()-start<timer_hz*3U){}dsb();return REC->ready==READY;}
void main(void) {
 printf("PSCI_BEGIN target_mpidr=0x%llx context=0x%llx\n",TARGET,CONTEXT);
 uint64_t el=current_el();printf("PSCI_PRIMARY_EL=%llu\n",el);
 if(el!=2)blocked("resident_BL31_NS_EL2_required",(int64_t)el);
 uint64_t sctlr,mpidr;__asm__ volatile("mrs %0,sctlr_el2":"=r"(sctlr));__asm__ volatile("mrs %0,mpidr_el1":"=r"(mpidr));
 check(!(sctlr&5U)&&(mpidr&UINT64_C(0xff00ffffff))==0,"PSCI_PRIMARY_EL2_CACHE_OFF_CORE0");
 if(failures)finish(1);
 __asm__ volatile("mrs %0,cntfrq_el0":"=r"(timer_hz));if(!timer_hz){timer_hz=400000000;puts("INFO PSCI_COUNTER_DECLARED_400MHZ_NO_CALIBRATION");}
 if(timer_hz<1000000||timer_hz>2000000000)blocked("invalid_counter_frequency",(int64_t)timer_hz);
 uint64_t before=ticks(),after=before;unsigned polls=100000;while(after==before&&--polls)after=ticks();if(after==before)blocked("counter_not_advancing",0);
 int64_t version=call(PSCI_VERSION,0,0,0);printf("PSCI_VERSION=0x%llx\n",(uint64_t)version);
 if((int32_t)version<0||version<2)blocked("version_unavailable",version);
 const uint64_t ids[]={PSCI_CPU_ON,PSCI_CPU_OFF,PSCI_AFFINITY};
 for(unsigned i=0;i<3;i++){int64_t rc=call(PSCI_FEATURES,ids[i],0,0);printf("PSCI_FEATURE id=0x%llx result=%lld\n",ids[i],rc);if((int32_t)rc<0)blocked("required_feature_unavailable",rc);}
 int64_t initial=call(PSCI_AFFINITY,TARGET,0,0);printf("PSCI_INITIAL_AFFINITY=%lld\n",initial);
 if(initial!=1)blocked(initial==0?"target_already_on":"target_not_off",initial);
 volatile uint64_t *words=(void*)REC;for(unsigned i=0;i<sizeof(*REC)/8;i++)words[i]=0;
 dsb();__asm__ volatile("ic iallu; dsb sy; isb":::"memory");
 int64_t on=example_psci_cpu_on(TARGET,(uintptr_t)psci_secondary_entry,CONTEXT);printf("PSCI_CPU_ON_RESULT=%lld\n",on);
 if((int32_t)on==-4)blocked("CPU_ON_ALREADY_ON",on);
 if(on!=0){check(false,"PSCI_CPU_ON_SUCCESS");finish(1);}
 check(true,"PSCI_CPU_ON_SUCCESS");
 bool ready=wait_ready();check(ready,"PSCI_SECONDARY_RECORD_PUBLISHED");
 if(ready){
  printf("PSCI_SECONDARY context=0x%llx MIDR=0x%llx MPIDR=0x%llx EL=%llu SCTLR=0x%llx ENTRY=0x%llx STACK=0x%llx FAULT=%llu\n",REC->context,REC->midr,REC->mpidr,REC->el,REC->sctlr,REC->secondary_entry,REC->stack,REC->fault);
  check(REC->context==CONTEXT&&(REC->mpidr&UINT64_C(0xff00ffffff))==TARGET&&((REC->midr>>4)&0xfffU)==0xd05U&&((REC->midr>>24)&255U)==0x41U&&REC->el==2&&!(REC->sctlr&5U)&&REC->secondary_entry==(uintptr_t)psci_secondary_entry&&REC->stack>0x83ff9000&&REC->stack<=0x83ffb000&&REC->fault==0,"PSCI_SECONDARY_IDENTITY_CONTEXT_AND_STACK");
 }
 REC->release=RELEASE;dsb();
 int64_t affinity=-1;uint64_t start=ticks();polls=1000000;
 do {affinity=call(PSCI_AFFINITY,TARGET,0,0);if(affinity==1)break;}while(--polls&&ticks()-start<timer_hz*5U);
 dsb();printf("PSCI_FINAL_AFFINITY=%lld OFF_ATTEMPT=%llu OFF_RETURNED=%llu OFF_RESULT=%lld\n",affinity,REC->off_attempt,REC->off_returned,(int64_t)REC->off_result);
 check(affinity==1&&REC->off_attempt==1&&REC->off_returned==0,"PSCI_CPU_OFF_AFFINITY_CONFIRMED");
 finish(failures?1:0);
}
