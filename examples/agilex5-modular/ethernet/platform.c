/* Modular ES profile: EL3 identity map; selectable CPU cache; noncacheable DMA pool. */
#include "platform.h"
#include <stdlib.h>
#include <string.h>
static uint64_t table[512] __attribute__((aligned(4096)));
static uint64_t ddr[512] __attribute__((aligned(4096)));
#ifndef NET_CACHED
#define NET_CACHED 0
#endif
uint64_t ticks(void){return SYS(cntpct_el0);}
u32_t sys_now(void){return (u32_t)(ticks()/(COUNTER_HZ/1000));}
uint32_t net_random(void){static uint32_t state=0xa5051234;state^=state<<13;state^=state>>17;state^=state<<5;return state;}
void net_panic(const char*s){text("FAIL NETWORK: ");text(s);text("\n");for(;;)__asm__ volatile("wfi");}
void platform_init(void){
 for(unsigned i=0;i<4;i++)table[i]=((uint64_t)i<<30)|1|(1<<10)|(i>=2?4:0);
 if(NET_CACHED){
  for(unsigned i=0;i<512;i++){
   uint64_t address=0x80000000ULL+((uint64_t)i<<21);
   unsigned attr=(address>=0x85000000 && address<0x85400000)?1:2;
   ddr[i]=address|1|(1<<10)|(3<<8)|(attr<<2);
  }
  table[2]=(uintptr_t)ddr|3;
 }
 barrier();MSR(mair_el3,0xff4404);MSR(ttbr0_el3,(uintptr_t)table);
 MSR(tcr_el3,(1ULL<<31)|(1<<23)|(2<<16)|(3<<12)|(1<<10)|(1<<8)|32);
 __asm__ volatile("tlbi alle3;dsb sy;isb":::"memory");
 MSR(sctlr_el3,(SYS(sctlr_el3)|1)&~6ULL);barrier();
 if(NET_CACHED){
  extern unsigned char __bss_end[];
  unsigned line=4u<<((SYS(ctr_el0)>>16)&15);
  /* Fresh DDR/HPS bootstrap is required. Invalidate application and stack
   * lines before enabling CPU cache; DMA has a distinct noncacheable pool. */
  for(uintptr_t p=0x82600000;p<(uintptr_t)__bss_end;p+=line)__asm__ volatile("dc ivac,%0"::"r"(p):"memory");
  for(uintptr_t p=0x83f00000;p<0x84000000;p+=line)__asm__ volatile("dc ivac,%0"::"r"(p):"memory");
  __asm__ volatile("dsb sy;ic iallu;dsb sy;isb":::"memory");
  MSR(sctlr_el3,SYS(sctlr_el3)|(1<<2)|(1<<12));barrier();
 }
 uint64_t address=0x85000000;
 __asm__ volatile("at s1e3r,%0;isb"::"r"(address):"memory");uint64_t par=SYS(par_el1);
 value("DMA PAR_EL1",par);if((par&1)||(par>>56)!=0x44)net_panic("DMA pool must be normal noncacheable");
 address=0x85200000;
 __asm__ volatile("at s1e3r,%0;isb"::"r"(address):"memory");par=SYS(par_el1);
 value("RX DMA PAR_EL1",par);if((par&1)||(par>>56)!=0x44)net_panic("RX pool must be normal noncacheable");
 address=0x82600000;
 __asm__ volatile("at s1e3r,%0;isb"::"r"(address):"memory");par=SYS(par_el1);
 value("CPU PAR_EL1",par);if((par&1)||(par>>56)!=(NET_CACHED?0xffu:0x44u))net_panic("CPU memory attributes");
 text(NET_CACHED?"MEMORY MODE: cached CPU, noncacheable DMA\n":"MEMORY MODE: noncacheable CPU and DMA\n");
 /* Pinned Agilex5 ATF platform defines the system counter as 400 MHz.
  * Host runner independently compares these ticks with monotonic wall time. */
 MSR(cntfrq_el0,COUNTER_HZ);
}
/* Newlib support: no filesystem, bounded private heap, UART output only. */
#include <errno.h>
#include <sys/stat.h>
#include <stddef.h>
static uint8_t libc_heap[65536] __attribute__((aligned(16)));
void *_sbrk(ptrdiff_t increment){
 static ptrdiff_t used;ptrdiff_t next=used+increment;
 if(next<0||next>(ptrdiff_t)sizeof(libc_heap)){errno=ENOMEM;return (void*)-1;}
 void*p=libc_heap+used;used=next;return p;
}
int _write(int fd,const char*p,int len){(void)fd;for(int i=0;i<len;i++){if(p[i]=='\n')put('\r');put(p[i]);}return len;}
int _read(int fd,char*p,int len){(void)fd;(void)p;(void)len;errno=ENOSYS;return -1;}
int _close(int fd){(void)fd;errno=EBADF;return -1;}
int _fstat(int fd,struct stat*s){(void)fd;memset(s,0,sizeof(*s));s->st_mode=S_IFCHR;return 0;}
int _isatty(int fd){(void)fd;return 1;}
int _lseek(int fd,int off,int whence){(void)fd;(void)off;(void)whence;errno=ESPIPE;return -1;}
int _getpid(void){return 1;}
int _kill(int pid,int sig){(void)pid;(void)sig;errno=ESRCH;return -1;}
__attribute__((noreturn)) void _exit(int status){(void)status;net_panic("unexpected libc exit");for(;;){}}
