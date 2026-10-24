/* DMAC0 channel 0: polling, one linked-list block, 64-bit widths, DDR-to-DDR. */
#include <stdint.h>
#include "dma_regs.h"
#include "dma.h"
#define REG32(a) (*(volatile uint32_t *)(uintptr_t)(a))
static void put(char c){while(!(REG32(0x10c02014)&0x20)){}REG32(0x10c02000)=(uint8_t)c;}
static void text(const char*s){while(*s){if(*s=='\n')put('\r');put(*s++);}}
static void value(const char*s,uint64_t v){text(s);text("0x");for(int i=60;i>=0;i-=4)put("0123456789abcdef"[(v>>i)&15]);text("\n");}
void example_main(void){
 text("HPS DMA EXAMPLE BEGIN\n");
 dma_regs_t *d=(dma_regs_t *)(uintptr_t)DMA0_BASE;
 volatile uint64_t *src=(volatile uint64_t *)0x85100000UL;
 volatile uint64_t *dst=(volatile uint64_t *)0x85110000UL;
 uint64_t sctlr;__asm__ volatile("mrs %0,sctlr_el3":"=r"(sctlr));
 if(sctlr&4){text("FAIL DMA: run with D-cache off or add cache maintenance\n");return;}
 value("DMAC0 ID = ",d->IDREG);value("DMAC0 version = ",d->COMPVERREG);
 if(d->CHENREG&15){text("FAIL DMA: controller already busy\n");return;}
 for(unsigned i=0;i<512;i++){src[i]=0x1234567800000000ULL^i;dst[i]=0;}
 __asm__ volatile("dsb sy":::"memory");
 d->CFGREG=0;
 d->dma_ch[0].SAR=(uintptr_t)src;
 d->dma_ch[0].DAR=(uintptr_t)dst;
 d->dma_ch[0].BLOCK_TS=511;
 volatile dma_lli_t *lli=(volatile dma_lli_t *)0x85120000UL;
 for(unsigned i=0;i<sizeof(*lli)/8;i++)((volatile uint64_t *)lli)[i]=0;
 lli->sar=(uintptr_t)src;lli->dar=(uintptr_t)dst;lli->block_ts=511;
 lli->ctl=(3ULL<<8)|(3ULL<<11)|(1ULL<<63)|(1ULL<<62);
 __asm__ volatile("dsb sy":::"memory");
 d->dma_ch[0].CFG2=(d->dma_ch[0].CFG2&~(7ULL<<32))|15ULL;
 d->dma_ch[0].LLP=(uintptr_t)lli;
 d->dma_ch[0].CTL=lli->ctl;
 d->dma_ch[0].INTCLEARREG=~0ULL;
 d->dma_ch[0].INTSTATUS_ENABLEREG=~0ULL;
 d->dma_ch[0].INTSIGNAL_ENABLEREG=0; /* polling; no interrupt delivery */
 d->CFGREG=3;
 d->CHENREG=0x101;
 unsigned remaining=1000000;
 while((d->CHENREG&1)&&--remaining){}
 __asm__ volatile("dsb sy":::"memory");
 uint64_t status=d->dma_ch[0].INTSTATUS;
 value("DMA channel status = ",status);
 if(!remaining){d->CHENREG=(1ULL<<40)|(1ULL<<32);text("FAIL DMA: bounded timeout\n");return;}
 if(!(status&DMA_CHx_INTSTS_DMA_TFR_DONE)){text("FAIL DMA: transfer-complete bit absent\n");return;}
 for(unsigned i=0;i<512;i++)if(dst[i]!=(0x1234567800000000ULL^i)){text("FAIL DMA: destination mismatch\n");return;}
 d->dma_ch[0].INTCLEARREG=status;d->CFGREG=0;
 text("PASS DMA_COPY: 4096 bytes transferred by DMAC0 and verified\n");
}
