/* SPDX-License-Identifier: MIT-0
 * QEMU virt SMMUv3 stage-2 + PCI EDU DMA exercise, not an Agilex DMA adapter.
 * Register layouts are from QEMU v8.2.2 smmuv3-internal.h and EDU spec.
 */
#include "lab.h"
#define SMMU 0x09050000UL
#define ECAM 0x3f008000UL /* highmem=off, bus0 device1 function0: SID 8 */
#define EDU  0x10000000UL
#define SRC_IOVA 0x60000000UL
#define DST_IOVA 0x60200000UL
#define SRC_PA   0x48000000UL
#define DST_PA   0x48200000UL
#define BYTES 4096
#define SID 8
#define REG32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define REG64(a) (*(volatile uint64_t *)(uintptr_t)(a))
static uint64_t streams[32][8] __attribute__((aligned(4096)));
static uint64_t l1[512] __attribute__((aligned(4096)));
static uint64_t l2[512] __attribute__((aligned(4096)));
static uint64_t commands[8][2] __attribute__((aligned(4096)));
static volatile uint64_t events[8][4] __attribute__((aligned(4096)));
static unsigned producer;
static uint64_t deadline(void) { return SYS(cntpct_el0)+2*SYS(cntfrq_el0); }
static void wait32(uintptr_t address, uint32_t mask, uint32_t expected, const char *reason) {
 uint64_t end=deadline();
 while ((REG32(address)&mask)!=expected) {
  if (SYS(cntpct_el0)>end) { value("poll address=",address);value("poll value=",REG32(address)); fail(reason); }
 }
}
static void cmd(uint64_t a, uint64_t b) {
 unsigned slot=producer&7;
 commands[slot][0]=a;commands[slot][1]=b;barrier();
 producer=(producer+1)&15;REG32(SMMU+0x98)=producer;
 wait32(SMMU+0x9c,0x00ffffff,producer,"SMMU command completion timeout");
 check((REG32(SMMU+0x9c)&0x7f000000)==0,"command queue has no error");
}
static void invalidate(void) {
 cmd(0x28ULL | (1ULL<<32),0); /* TLBI_S12_VMALL VMID=1 */
 cmd(0x46,0);               /* CMD_SYNC, no completion interrupt */
 barrier();
}
static void dma(uint64_t source,uint64_t destination,unsigned direction,unsigned count) {
 REG64(EDU+0x80)=source;REG64(EDU+0x88)=destination;
 REG64(EDU+0x90)=count;barrier();REG64(EDU+0x98)=1|direction;
 wait32(EDU+0x98,1,0,"EDU DMA timeout");barrier();
}
int main(void) {
 lab_begin("smmu-translated-dma");
 check(SYS(cntfrq_el0)!=0,"counter frequency available");
 check((SYS(sctlr_el3)&5)==0,"CPU MMU and data cache off for DMA buffers and tables");
 value("SMMU_IDR0=",REG32(SMMU));value("SMMU_IDR1=",REG32(SMMU+4));
 check((REG32(SMMU)&1)!=0,"model advertises stage-2 translation");
 check(REG32(ECAM)==0x11e81234,"PCI EDU identity at BDF 00:01.0");
 REG32(ECAM+0x10)=EDU;REG32(ECAM+4)=6;
 check((REG32(EDU)&0xffff)==0xed,"EDU BAR mapped");
 REG32(EDU+4)=0x12345678;
 check(REG32(EDU+4)==~0x12345678U,"EDU register liveness");
 for(unsigned i=0;i<32;i++) streams[i][0]=1; /* Abort all unrelated streams. */
 streams[SID][0]=1|(6<<1); /* Valid, stage-2 only */
#ifdef NEGATIVE_BYPASS
 streams[SID][0]=1|(4<<1);
#endif
 /* 32-bit IPA, 4KiB granule, start L1, inner/outer WB, inner-shareable,
  * 40-bit output, AArch64 tables, VMID1, record faults, abort rather than stall.
  */
 uint64_t s2=32|(1<<6)|(3<<8)|(3<<10)|(3<<12)|(2<<16)|(1<<19)|(1<<26);
 streams[SID][2]=1|(s2<<32);streams[SID][3]=(uintptr_t)l1;
 l1[SRC_IOVA>>30]=(uintptr_t)l2|3;
 const unsigned src_index=(SRC_IOVA>>21)&511,dst_index=(DST_IOVA>>21)&511;
 l2[src_index]=SRC_PA|0x7fd; /* 2MiB block, normal WB, RW, SH, AF */
 l2[dst_index]=DST_PA|0x7fd;
 volatile uint8_t *source=(void *)SRC_PA,*destination=(void *)DST_PA;
 for(unsigned i=0;i<BYTES;i++) {source[i]=(i*37U+19U)^(i>>5);destination[i]=0;}
 barrier();
 REG32(SMMU+0x20)=0;wait32(SMMU+0x24,0xffffffff,0,"SMMU disable ACK");
 REG64(SMMU+0x80)=(uintptr_t)streams|(1ULL<<62);
 REG32(SMMU+0x88)=5; /* Linear 32-entry stream table */
 REG64(SMMU+0x90)=(uintptr_t)commands|(1ULL<<62)|3;
 REG64(SMMU+0xa0)=(uintptr_t)events|(1ULL<<62)|3;
 REG32(SMMU+0x98)=0;REG32(SMMU+0x9c)=0;
 REG32(SMMU+0xa8)=0;REG32(SMMU+0xac)=0;
 REG32(SMMU+0x20)=12;wait32(SMMU+0x24,0xffffffff,12,"queue enable ACK");
 cmd(4,31); /* CFGI_STE_RANGE range=31: invalidate all config caches */
 invalidate();
 REG32(SMMU+0x20)=13;wait32(SMMU+0x24,0xffffffff,13,"SMMU enable ACK");
 value("source IOVA=",SRC_IOVA);value("source PA=",SRC_PA);
 value("destination IOVA=",DST_IOVA);value("destination PA=",DST_PA);
 check(SRC_IOVA!=SRC_PA && DST_IOVA!=DST_PA,"IOVA differs from CPU physical address");
 dma(SRC_IOVA,0x40000,0,BYTES);dma(0x40000,DST_IOVA,2,BYTES);
 unsigned mismatch=0;for(unsigned i=0;i<BYTES;i++) mismatch+=source[i]!=destination[i];
 check(mismatch==0,"translated EDU DMA round trip verifies all 4096 bytes");
 check(REG32(SMMU+0xa8)==0,"valid transfers produced no SMMU fault");
 for(unsigned i=0;i<BYTES;i++)destination[i]=0xa5;
#ifndef NEGATIVE_KEEP_MAPPING
 l2[dst_index]=0;
#endif
 barrier();invalidate();
 dma(0x40000,DST_IOVA,2,1); /* One-byte fault: avoid flooding a small event queue. */
 uint64_t end=deadline();
 while(REG32(SMMU+0xa8)==REG32(SMMU+0xac)) {
  if(SYS(cntpct_el0)>end)fail("unmapped DMA did not produce an SMMU event");
 }
 barrier();
 value("event word0=",events[0][0]);value("event word1=",events[0][1]);
 value("event address=",events[0][2]);value("event auxiliary=",events[0][3]);
 check((events[0][0]&255)==0x10,"event is F_TRANSLATION");
 check((events[0][0]>>32)==SID,"event identifies EDU stream 8");
 check((events[0][1]&(1ULL<<39))!=0,"event identifies stage-2 fault");
 check(events[0][2]==DST_IOVA,"event identifies unmapped destination IOVA");
 check(REG32(SMMU+0xa8)==1,"one-byte invalid DMA produced exactly one event");
 mismatch=0;for(unsigned i=0;i<BYTES;i++)mismatch+=destination[i]!=0xa5;
 check(mismatch==0,"faulting DMA left all 4096 guard bytes unchanged");
 REG32(SMMU+0xac)=REG32(SMMU+0xa8);REG32(ECAM+4)=0;
 REG32(SMMU+0x20)=0;wait32(SMMU+0x24,0xffffffff,0,"SMMU final disable ACK");
 value("SMMU GERROR=",REG32(SMMU+0x60));value("SMMU GERRORN=",REG32(SMMU+0x64));
 check(REG32(SMMU+0x60)==REG32(SMMU+0x64),"no unacknowledged SMMU global error");
 text("PASS SMMU_TRANSLATED_DMA_AND_FAULT QEMU SMMUv3/EDU models only\n");
 lab_done(0);
}
