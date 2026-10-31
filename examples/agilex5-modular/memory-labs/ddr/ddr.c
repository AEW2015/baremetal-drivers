// SPDX-License-Identifier: MIT-0
/* Scalar CPU memory-path measurements, not peak DDR/MPFE bandwidth. */
#include "lab.h"
#ifdef LAB_AGILEX5
#define RAM_BASE 0x80000000UL
#define SOURCE 0x85000000UL
#define DESTINATION 0x86000000UL
#else
#define RAM_BASE 0x40000000UL
#define SOURCE 0x45000000UL
#define DESTINATION 0x46000000UL
#endif
#define ROUNDS 2U
static uint64_t l1[512] __attribute__((aligned(4096)));
static uint64_t l2[512] __attribute__((aligned(4096)));
static uint64_t frequency;
static void decimal(uint64_t n) {
 char digits[24]; unsigned count=0;
 do { digits[count++]=(char)('0'+n%10); n/=10; } while(n);
 while(count) putchar_uart(digits[--count]);
}
static void field(const char *name,uint64_t n) { text(name); decimal(n); }
static uint64_t ticks(void) {
 uint64_t t;
 __asm__ volatile("dsb sy; isb; mrs %0,cntpct_el0; isb" : "=r"(t) :: "memory");
 return t;
}
static void deadline(uint64_t start) {
 if (ticks()-start>30*frequency) fail("DDR_OPERATION_TIMEOUT");
}
static uint64_t pattern(uint64_t i) { return (i*0x9e3779b185ebca87ULL)^0x123456789abcdef0ULL; }
static void report(const char *op,uint64_t size,uint64_t elapsed,uint64_t bytes,uint64_t accesses,uint64_t checksum) {
 check(elapsed>0,"DDR_NONZERO_SAMPLE_TICKS");
 text("DDR_SAMPLE op=");text(op);field(" working_set_bytes=",size);
 field(" ticks=",elapsed);field(" payload_bytes=",bytes);field(" accesses=",accesses);
 field(" checksum=",checksum);text("\n");
}
static void sweep(uint64_t bytes) {
 volatile uint64_t *source=(volatile uint64_t *)SOURCE;
 volatile uint64_t *destination=(volatile uint64_t *)DESTINATION;
 uint64_t words=bytes/8,start,elapsed,sum=0,expected=0;
 for(uint64_t i=0;i<words;i++) { source[i]=pattern(i); expected+=pattern(i); }
 start=ticks();
 for(unsigned round=0;round<ROUNDS;round++)
  for(uint64_t i=0;i<words;i++) { sum+=source[i]; if((i&4095)==0) deadline(start); }
 elapsed=ticks()-start;
 check(sum==expected*ROUNDS,"DDR_READ_CHECKSUM");
 report("read",bytes,elapsed,bytes*ROUNDS,words*ROUNDS,sum);
 start=ticks();
 for(unsigned round=0;round<ROUNDS;round++)
  for(uint64_t i=0;i<words;i++) { destination[i]=pattern(i); if((i&4095)==0) deadline(start); }
 elapsed=ticks()-start;
 for(uint64_t i=0;i<words;i++) if(destination[i]!=pattern(i)) fail("DDR_WRITE_READBACK");
 report("write",bytes,elapsed,bytes*ROUNDS,words*ROUNDS,expected);
 for(uint64_t i=0;i<words;i++) destination[i]=0;
 start=ticks();
 for(unsigned round=0;round<ROUNDS;round++)
  for(uint64_t i=0;i<words;i++) { destination[i]=source[i]; if((i&4095)==0) deadline(start); }
 elapsed=ticks()-start;
#ifdef INJECT_COPY_FAULT
 destination[words-1]^=1;
#endif
 for(uint64_t i=0;i<words;i++) if(destination[i]!=source[i]) fail("DDR_COPY_READBACK");
 report("copy",bytes,elapsed,bytes*ROUNDS,words*ROUNDS,expected);
 /* One dependent load per 64-byte line. Odd stride forms a complete ring
  * for every power-of-two node count; this is not a sequential bandwidth loop. */
 uint64_t nodes=bytes/64,mask=nodes-1,index=0;
 for(uint64_t i=0;i<nodes;i++) source[i*8]=(i+257)&mask;
 for(uint64_t i=0;i<nodes;i++) if(source[i*8]!=((i+257)&mask)) fail("DDR_RING_READBACK");
 sum=0;start=ticks();
 for(unsigned round=0;round<ROUNDS;round++)
  for(uint64_t i=0;i<nodes;i++) {
   index=source[index*8];sum+=index;
   if((i&4095)==0) deadline(start);
  }
 elapsed=ticks()-start;
 check(index==0 && sum==ROUNDS*(nodes*(nodes-1)/2),"DDR_DEPENDENT_RING_INTEGRITY");
 report("dependent-load",bytes,elapsed,8*nodes*ROUNDS,nodes*ROUNDS,sum);
}
int main(void) {
 lab_begin("ddr-path");
 uint64_t saved=SYS(sctlr_el3),old_mair=SYS(mair_el3),old_ttbr=SYS(ttbr0_el3),old_tcr=SYS(tcr_el3);
 check(!(saved&5),"DDR_MMU_AND_DCACHE_INITIALLY_OFF");
 frequency=SYS(cntfrq_el0);
#ifdef INJECT_CLOCK_FAULT
 frequency=0;
#endif
 check(frequency>=1000000 && frequency<=2000000000ULL,"DDR_DECLARED_TIMER_FREQUENCY_RANGE");
#ifdef LAB_AGILEX5
 check(frequency==400000000,"DDR_TIMER_MATCHES_PINNED_BOOTSTRAP");
 text("TIMER_SOURCE pinned-bootstrap-declared-400MHz; external-calibration-not-performed\n");
#else
 text("TIMER_SOURCE QEMU-architectural-declared-frequency; not-hardware-timing\n");
#endif
 field("DDR_TIMER frequency_hz=",frequency);text("\n");
 uint64_t before=ticks();
 for(volatile unsigned i=0;i<10000;i++) __asm__ volatile("nop");
 check(ticks()>before,"DDR_TIMER_ADVANCES");
 /* Same EL3 NC mapping recipe as the existing MMU lab, with explicit SH=Inner
  * Shareable. Device-nGnRE MMIO, normal noncacheable owned 128 MiB DDR window.
  * Enter only from the fresh cache-off diagnostic bootstrap: no flush is faked. */
 l1[0]=1|(1U<<10)|(1ULL<<54);
 l1[RAM_BASE>>30]=(uintptr_t)l2|3;
 for(unsigned i=0;i<64;i++) l2[i]=(RAM_BASE+((uint64_t)i<<21))|1|(1U<<10)|(3U<<8)|4;
 barrier();MSR(mair_el3,0x4404);MSR(ttbr0_el3,(uintptr_t)l1);
 MSR(tcr_el3,(1ULL<<31)|(1U<<23)|(2U<<16)|(3U<<12)|(1U<<10)|(1U<<8)|32);
 __asm__ volatile("tlbi alle3; dsb sy; isb" ::: "memory");
 MSR(sctlr_el3,saved|1);barrier();
 text("DDR_STATE mmu=on memory=normal-noncacheable shareability=inner data_cache=off\n");
 text("DDR_SCOPE scalar-CPU-effective-path; copy-bytes-are-payload; no-peak-MPFE-claim\n");
 value("DDR_SOURCE=",SOURCE);value("DDR_DESTINATION=",DESTINATION);
 const uint64_t sizes[]={65536,262144,1048576,4194304,16777216};
 for(unsigned i=0;i<sizeof(sizes)/sizeof(sizes[0]);i++) sweep(sizes[i]);
 MSR(sctlr_el3,saved);barrier();
 __asm__ volatile("tlbi alle3; dsb sy; isb" ::: "memory");
 MSR(ttbr0_el3,old_ttbr);MSR(tcr_el3,old_tcr);MSR(mair_el3,old_mair);barrier();
 check(SYS(sctlr_el3)==saved && SYS(mair_el3)==old_mair && SYS(ttbr0_el3)==old_ttbr && SYS(tcr_el3)==old_tcr,"DDR_TRANSLATION_STATE_RESTORED");
 check(1,"DDR_SWEEP_COMPLETE");lab_done(0);
}
