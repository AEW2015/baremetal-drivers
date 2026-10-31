// SPDX-License-Identifier: MIT-0
/* Native Agilex Simics only: real DMAC0 channel requests through DMA0 TBU.
 * SMMU stage-2 tables and destination unmap are an explicit host fixture.
 */
#include "lab.h"
#include "dma_regs.h"
#include "dma.h"
#define SRC_IOVA 0x85000000UL
#define DST_IOVA 0x85200000UL
#define LLI_IOVA 0x85600000UL
#define SRC_PA 0x86000000UL
#define DST_PA 0x86200000UL
#define LLI_PA 0x86400000UL
#define CONTROL_PA 0x86600000UL
#define EVENT_PA 0x85404000UL
#define SMMU_REG 0x16000000UL
#define WORDS 512U
#define HOST_UNMAPPED 0xface2ULL
#define ERROR_MASK 0x03ff7fe0ULL
#define AXPROT_NS2 ((2ULL<<32)|(2ULL<<35))
#define AXPROT_MASK ((7ULL<<32)|(7ULL<<35))
static dma_regs_t *const dma=(dma_regs_t *)(uintptr_t)DMA0_BASE;
static volatile uint64_t *const control=(volatile uint64_t *)CONTROL_PA;
static uint64_t saved_cfg,saved_sar,saved_dar,saved_block,saved_ctl,saved_cfg2,saved_llp,saved_intstat,saved_intsignal;
static uint64_t observed_status;

static uint64_t pattern(unsigned phase,unsigned i) { return 0x1234567800000000ULL^((uint64_t)phase<<48)^i; }
static uint64_t guard(unsigned i) { return 0xa5a5a5a5a5a5a5a5ULL^i; }
static int aliases_unchanged(void) {
    for (unsigned i=0;i<WORDS;i++)
        if (((volatile uint64_t *)SRC_IOVA)[i]!=guard(i) ||
            ((volatile uint64_t *)DST_IOVA)[i]!=guard(i) ||
            ((volatile uint64_t *)LLI_IOVA)[i]!=guard(i)) return 0;
    return 1;
}
static int disable_channel(void) {
    if (dma->CHENREG&1) {
        dma->CHENREG=(1ULL<<40)|(1ULL<<32); /* Abort channel 0 + write enable. */
        unsigned count=100000;
        while ((dma->CHENREG&1) && --count) __asm__ volatile("yield");
        if (dma->CHENREG&1) dma->CHENREG=1ULL<<8; /* Explicit disable + WE. */
    }
    barrier();
    return !(dma->CHENREG&1);
}
static int cleanup(void) {
    int idle=disable_channel();
    dma->CFGREG=0;
    dma->dma_ch[0].INTCLEARREG=~0ULL;
    if (idle) {
        dma->dma_ch[0].SAR=saved_sar;dma->dma_ch[0].DAR=saved_dar;
        dma->dma_ch[0].BLOCK_TS=saved_block;dma->dma_ch[0].CTL=saved_ctl;
        dma->dma_ch[0].CFG2=saved_cfg2;dma->dma_ch[0].LLP=saved_llp;
        dma->dma_ch[0].INTSTATUS_ENABLEREG=saved_intstat;
        dma->dma_ch[0].INTSIGNAL_ENABLEREG=saved_intsignal;
        dma->CFGREG=saved_cfg;
    }
    value("DMAC_FINAL_CHEN=",dma->CHENREG);
    return idle && dma->CFGREG==saved_cfg && dma->dma_ch[0].SAR==saved_sar &&
           dma->dma_ch[0].DAR==saved_dar && dma->dma_ch[0].BLOCK_TS==saved_block &&
           dma->dma_ch[0].CTL==saved_ctl && dma->dma_ch[0].CFG2==saved_cfg2 &&
           dma->dma_ch[0].LLP==saved_llp && dma->dma_ch[0].INTSTATUS_ENABLEREG==saved_intstat &&
           dma->dma_ch[0].INTSIGNAL_ENABLEREG==saved_intsignal;
}
static __attribute__((noreturn)) void stop(const char *reason) {
    control[2]=0xbad;
    if (!cleanup()) text("FAIL DMAC_CLEANUP\n");
    fail(reason);
}
static void must(int condition,const char *marker) {
    if (!condition) stop(marker);
    check(1,marker);
}
static void prepare_transfer(void) {
    volatile dma_lli_t *lli=(volatile dma_lli_t *)LLI_PA;
    dma->CFGREG=0;
    for (unsigned i=0;i<sizeof(*lli)/8;i++) ((volatile uint64_t *)lli)[i]=0;
    lli->sar=SRC_IOVA;lli->dar=DST_IOVA;lli->block_ts=WORDS-1;
    lli->ctl=(3ULL<<8)|(3ULL<<11)|(1ULL<<63)|(1ULL<<62)|(1ULL<<30)|AXPROT_NS2;
    dma->dma_ch[0].SAR=SRC_IOVA;dma->dma_ch[0].DAR=DST_IOVA;
    dma->dma_ch[0].BLOCK_TS=WORDS-1;
    /* CFG2[34:32] is TT_FC, NOT PROT. Zero selects memory-to-memory. */
    dma->dma_ch[0].CFG2=(saved_cfg2&~DMA_CHx_CFG2_TT_FC_MASK)|15ULL;
    dma->dma_ch[0].LLP=LLI_IOVA;dma->dma_ch[0].CTL=lli->ctl;
    dma->dma_ch[0].INTCLEARREG=~0ULL;
    dma->dma_ch[0].INTSTATUS_ENABLEREG=~0ULL;
    dma->dma_ch[0].INTSIGNAL_ENABLEREG=0;
    barrier();
    must((dma->dma_ch[0].CTL&AXPROT_MASK)==AXPROT_NS2,"DMAC_CTL_NONSECURE_AR_AW");
    value("DMAC_SAR_IOVA=",dma->dma_ch[0].SAR);
    value("DMAC_DAR_IOVA=",dma->dma_ch[0].DAR);
    value("DMAC_LLP_IOVA=",dma->dma_ch[0].LLP);
    value("DMAC_CTL=",dma->dma_ch[0].CTL);
}
static int execute_transfer(void) {
    dma->CFGREG=3;dma->CHENREG=0x101;
    unsigned count=1000000;
    while ((dma->CHENREG&1) && --count) {
        if (dma->dma_ch[0].INTSTATUS&ERROR_MASK) break;
        __asm__ volatile("yield");
    }
    barrier();
    observed_status=dma->dma_ch[0].INTSTATUS;
    value("DMAC_CHANNEL_STATUS=",observed_status);
    value("DMAC_CHANNEL_ENABLE=",dma->CHENREG);
    value("DMAC_POLL_REMAINING=",count);
    return count && !(dma->CHENREG&1) && !(observed_status&ERROR_MASK) &&
           (observed_status&DMA_CHx_INTSTS_DMA_TFR_DONE);
}
int main(void) {
    lab_begin("dmac-smmu");
    check(!(SYS(sctlr_el3)&5),"DMAC_CPU_MMU_DCACHE_OFF");
    saved_cfg=dma->CFGREG;saved_sar=dma->dma_ch[0].SAR;saved_dar=dma->dma_ch[0].DAR;
    saved_block=dma->dma_ch[0].BLOCK_TS;saved_ctl=dma->dma_ch[0].CTL;
    saved_cfg2=dma->dma_ch[0].CFG2;saved_llp=dma->dma_ch[0].LLP;
    saved_intstat=dma->dma_ch[0].INTSTATUS_ENABLEREG;
    saved_intsignal=dma->dma_ch[0].INTSIGNAL_ENABLEREG;
    if (dma->CHENREG&15) fail("DMAC_ALREADY_BUSY");
    control[0]=0;control[1]=0;control[2]=0;
    must(MMIO32(0x10d121a8)==0x00080008 && MMIO32(0x10d1217c)==3,"NATIVE_DMA0_SID8_ROUTE");
    must((MMIO32(SMMU_REG+0x20)&5)==5,"NATIVE_SMMU_TRANSLATION_EVENT_ENABLED");
    for (unsigned i=0;i<WORDS;i++) {
        ((volatile uint64_t *)SRC_PA)[i]=pattern(1,i);
        ((volatile uint64_t *)DST_PA)[i]=0;
        ((volatile uint64_t *)SRC_IOVA)[i]=guard(i);
        ((volatile uint64_t *)DST_IOVA)[i]=guard(i);
        ((volatile uint64_t *)LLI_IOVA)[i]=guard(i);
    }
    prepare_transfer();
    must(execute_transfer(),"DMAC_TRANSLATED_TRANSFER_DONE");
    for (unsigned i=0;i<WORDS;i++)
        if (((volatile uint64_t *)DST_PA)[i]!=pattern(1,i)) {
            value("DMAC_MISMATCH_WORD=",i);value("DMAC_ACTUAL=",((volatile uint64_t *)DST_PA)[i]);
            stop("DMAC_NONIDENTITY_PA_READBACK");
        }
    must(aliases_unchanged(),"DMAC_RAW_IOVA_ALIASES_UNCHANGED");
    must(MMIO32(SMMU_REG+0xa8)==0,"DMAC_VALID_TRANSFER_NO_SMMU_EVENT");
    text("PASS DMAC_SMMU_COPY_4096_NATIVE_ENGINE\n");
    barrier();control[0]=1;barrier();
    text("DMAC_SMMU_PHASE1_COMPLETE\n");
    unsigned waiting=10000000;
    while (control[1]!=HOST_UNMAPPED && --waiting) __asm__ volatile("yield" ::: "memory");
    must(waiting,"DMAC_HOST_UNMAP_HANDSHAKE");
    for (unsigned i=0;i<WORDS;i++) ((volatile uint64_t *)SRC_PA)[i]=pattern(2,i);
    prepare_transfer();
    int incorrectly_completed=execute_transfer();
    must(!incorrectly_completed && !(observed_status&DMA_CHx_INTSTS_DMA_TFR_DONE),"DMAC_UNMAPPED_NO_FALSE_DONE");
    must(disable_channel(),"DMAC_FAULT_CHANNEL_QUIESCENT");
    for (unsigned i=0;i<WORDS;i++)
        if (((volatile uint64_t *)DST_PA)[i]!=pattern(1,i)) stop("DMAC_FAULT_DESTINATION_GUARD");
    must(aliases_unchanged(),"DMAC_FAULT_IOVA_GUARDS_UNCHANGED");
    uint64_t event0=*(volatile uint64_t *)EVENT_PA;
    uint64_t event1=*(volatile uint64_t *)(EVENT_PA+8);
    uint64_t address=*(volatile uint64_t *)(EVENT_PA+16);
    value("DMAC_SMMU_EVENT0=",event0);value("DMAC_SMMU_EVENT1=",event1);value("DMAC_SMMU_FAULT_IOVA=",address);
    must(MMIO32(SMMU_REG+0xa8)>0 && (event0&255)==0x10 && (event0>>32)==8 &&
         (event1&(1ULL<<39)) && address==DST_IOVA,"DMAC_NATIVE_S2_TRANSLATION_FAULT_SID8");
    must(cleanup(),"DMAC_REGISTERS_CLEANED_UP");
    control[0]=2;control[2]=0x600d;barrier();
    text("PASS DMAC_SMMU_FAULT_GUARD_4096_NATIVE_ENGINE\n");
    text("INFO NATIVE_SIMICS_FIXTURE_CACHE_DISABLED_NO_HARDWARE_OR_TLBI_CLAIM\n");
    lab_done(0);
}
