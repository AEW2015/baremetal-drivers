// SPDX-License-Identifier: MIT-0
/* Coherent CPU-to-CPU transfer: no payload cache maintenance after enable. */
#include "lab.h"
#include "partition.h"

#ifdef LAB_AGILEX5
#define RAM_BASE 0x80000000UL
#else
#define RAM_BASE 0x40000000UL
#endif
#define ROUNDS 256U
#define WORDS 512U
#define READY 0x4453554341434845ULL
#define TIMEOUT_SECONDS 5U
#define QUIESCENT_BASE (RAM_BASE+0x06000000UL)
#define DSU_HAMMER_BYTES 0x00200000UL

struct flag { uint64_t value; unsigned char pad[56]; } __attribute__((aligned(64)));
struct channel {
    struct flag sequence, acknowledgement, online, finished, error;
    struct flag workload_ready, hammer_live;
    uint64_t failed_round, failed_word, actual, expected;
    uint64_t words_checked, checksum, sctlr, ctr, par;
    uint64_t probe_min, probe_max, probe_total, probe_steps, hammer_operations;
    struct policy_record policy;
    uint64_t payload[WORDS] __attribute__((aligned(64)));
} __attribute__((aligned(64)));
static struct channel channels[4];
static uint64_t l1[512] __attribute__((aligned(4096)));
static uint64_t l2[512] __attribute__((aligned(4096)));
volatile uint64_t dsu_tables_ready;
static struct flag abort_requested;
extern void secondary_start(void), vectors(void);

static uint64_t acquire(const uint64_t *p) { return __atomic_load_n(p,__ATOMIC_ACQUIRE); }
static void release(uint64_t *p,uint64_t value) { __atomic_store_n(p,value,__ATOMIC_RELEASE); }
static uint64_t deadline(void) { return SYS(cntpct_el0)+TIMEOUT_SECONDS*SYS(cntfrq_el0); }
static int expired(uint64_t limit) { return (int64_t)(SYS(cntpct_el0)-limit)>=0; }
static void relax(void) { __asm__ volatile("yield" ::: "memory"); }
static uint64_t *quiescent(unsigned cpu) { return (uint64_t *)(QUIESCENT_BASE+cpu*64); }
static uint64_t pattern(unsigned cpu,unsigned round,unsigned word) {
    return 0x6a09e667f3bcc909ULL ^ ((uint64_t)cpu<<56) ^
           ((uint64_t)round<<32) ^ ((uint64_t)word*0x9e3779b97f4a7c15ULL);
}
static __attribute__((noreturn)) void park(void) {
#ifdef LAB_AGILEX5
    ((void (*)(void))0x82010000UL)();
#endif
    for (;;) __asm__ volatile("wfi");
}
static __attribute__((noreturn)) void quiesce(unsigned cpu) {
    struct channel *c=&channels[cpu];
    c->policy.restored=policy_exit(&c->policy);
    release(&c->finished.value,READY);
    uintptr_t stack_top=(uintptr_t)0;
    extern char __stack_top;
    stack_top=(uintptr_t)&__stack_top-(cpu<<14);
    uintptr_t hammer_start=0,hammer_end=0;
#ifdef DSU_CONTENTION
    if (cpu>=2) {
        hammer_start=RAM_BASE+0x04000000UL+(cpu-2)*0x00800000UL;
        hammer_end=hammer_start+DSU_HAMMER_BYTES;
    }
#endif
    /* No C or stack writes after cleaning. The final flag is statically NC,
     * so primary cannot observe it before this core has cleaned and stopped
     * touching cached payload/control/stack memory.
     */
    __asm__ volatile(
        "mov x9,%0\n1: dc cvac,x9\nadd x9,x9,#64\ncmp x9,%1\nb.lo 1b\n"
        "mov x9,%2\n2: dc cvac,x9\nadd x9,x9,#64\ncmp x9,%3\nb.lo 2b\n"
        "mov x9,%6\ncmp x9,%7\nb.hs 4f\n"
        "3: dc cvac,x9\nadd x9,x9,#64\ncmp x9,%7\nb.lo 3b\n4:\n"
        "dsb sy\nstlr %5,[%4]\ndsb sy\n"
#ifdef LAB_AGILEX5
        "mov x9,%8\nbr x9\n"
#else
        "5: wfi\nb 5b\n"
#endif
        :: "r"((uintptr_t)c),"r"((uintptr_t)(c+1)),
           "r"(stack_top-0x4000),"r"(stack_top),"r"(quiescent(cpu)),"r"(READY),
           "r"(hammer_start),"r"(hammer_end)
#ifdef LAB_AGILEX5
           ,"r"(0x82010000UL)
#endif
        : "x9","memory");
    __builtin_unreachable();
}
static int wait_quiescent(void) {
    uint64_t limit=deadline();
    for (unsigned cpu=1;cpu<4;cpu++) {
        if (acquire(&channels[cpu].online.value)!=READY) continue;
        while (acquire(quiescent(cpu))!=READY) {
            if (expired(limit)) return 0;
            relax();
        }
    }
    return 1;
}
static __attribute__((noreturn)) void dsu_fail(const char *message) {
    release(&abort_requested.value,1);
    if (wait_quiescent()) {
        text("PASS SECONDARIES_CLEANED_AND_QUIESCENT_ON_FAILURE\n");
        int cluster_ok=global_policy_exit(),primary_ok=policy_exit(&channels[0].policy);
        if (!cluster_ok || !primary_ok)
            text("FAIL DSU_POLICY_RESTORE\n");
#ifdef DSU_PARTITIONED
        else text("PASS PARTITION_POLICY_RESTORED_ON_FAILURE\n");
#endif
    } else text("FAIL DSU_QUIESCENCE_TIMEOUT reset_required\n");
    fail(message);
}
static void dsu_check(int condition,const char *message) {
    if (!condition) dsu_fail(message);
    check(1,message);
}
static void tables_init(void) {
    /* Low MMIO is Device-nGnRnE, PXN. Only the 128 MiB RAM window is mapped. */
    l1[0]=1ULL|(1ULL<<10)|(1ULL<<54);
    l1[RAM_BASE>>30]=(uintptr_t)l2|3ULL;
    for (unsigned i=0;i<64;i++)
        l2[i]=(RAM_BASE+((uint64_t)i<<21))|1ULL|(1ULL<<10)|(3ULL<<8)|4ULL;
    l2[48]=(QUIESCENT_BASE)|1ULL|(1ULL<<10)|(3ULL<<8)|8ULL;
    barrier();
}
static int enable_cached_map(void) {
    uint64_t control=SYS(sctlr_el3);
    if ((control&5) || SYS(CurrentEL)!=12) return 0;
    MSR(vbar_el3,(uintptr_t)vectors);
    MSR(mair_el3,0x44ff00); /* Attr0 Device; Attr1 WB/WA; Attr2 Normal NC. */
    MSR(ttbr0_el3,(uintptr_t)l1);
    MSR(tcr_el3,(1ULL<<31)|(1ULL<<23)|(2ULL<<16)|(3ULL<<12)|
                    (1ULL<<10)|(1ULL<<8)|32ULL);
    __asm__ volatile("dsb sy; tlbi alle3; ic iallu; dsb sy; isb" ::: "memory");
    MSR(sctlr_el3,control|1ULL|4ULL|(1ULL<<12));
    barrier();
    return (SYS(sctlr_el3)&0x1005)==0x1005;
}
static uint64_t payload_translation(struct channel *c) {
    __asm__ volatile("at s1e3r,%0; isb" :: "r"((uintptr_t)c->payload) : "memory");
    return SYS(par_el1);
}
static int cached_translation(struct channel *c) {
    const uint64_t physical_mask=0x0000fffffffff000ULL;
    return !(c->par&1) && (c->par>>56)==0xff && ((c->par>>7)&3)==3 &&
           (c->par&physical_mask)==((uintptr_t)c->payload&physical_mask);
}
static void consumer_failure(unsigned cpu,unsigned round,unsigned word,
                             uint64_t actual,uint64_t expected,unsigned kind) {
    struct channel *c=&channels[cpu];
    c->failed_round=round;c->failed_word=word;c->actual=actual;c->expected=expected;
    release(&c->error.value,kind);
}
static void check_consumer_errors(void);
#include "contention.h"
void secondary_main(unsigned cpu) {
    if (!cpu || cpu>=4) park();
#ifdef LAB_AGILEX5
    if (!SYS(cntfrq_el0)) MSR(cntfrq_el0,400000000);
#endif
    uint64_t limit=deadline();
    while (acquire((const uint64_t *)&dsu_tables_ready)!=READY) {
        if (expired(limit)) park();
        relax();
    }
    struct channel *c=&channels[cpu];
    if (!policy_enter(cpu,&c->policy)) { policy_exit(&c->policy);park(); }
    if (!enable_cached_map()) { policy_exit(&c->policy);park(); }
    c->sctlr=SYS(sctlr_el3);c->ctr=SYS(ctr_el0);c->par=payload_translation(c);
    if ((4ULL<<((c->ctr>>16)&15))!=64) { policy_exit(&c->policy);park(); }
    release(&c->online.value,READY);
#ifdef DSU_OMIT_CONSUMER
    if (cpu==3) {
        while (!acquire(&abort_requested.value)) relax();
        quiesce(cpu);
    }
#endif
    uint64_t checksum=0;
    for (unsigned round=1;round<=ROUNDS;round++) {
        /* Let the producer's 5-second watchdog report a missing consumer
         * before another healthy consumer times out waiting for the producer.
         */
        limit=deadline()+TIMEOUT_SECONDS*SYS(cntfrq_el0);
        while (acquire(&c->sequence.value)!=round) {
            if (acquire(&abort_requested.value)) quiesce(cpu);
            if (expired(limit)) { consumer_failure(cpu,round,WORDS,0,round,2);quiesce(cpu); }
            relax();
        }
        for (unsigned word=0;word<WORDS;word++) {
            uint64_t actual=c->payload[word],expected=pattern(cpu,round,word);
            if (actual!=expected) { consumer_failure(cpu,round,word,actual,expected,1);quiesce(cpu); }
            checksum+=actual;
        }
        c->words_checked+=WORDS;c->checksum=checksum;
        release(&c->acknowledgement.value,round);
    }
    secondary_workload(cpu);
    quiesce(cpu);
}
static void check_consumer_errors(void) {
    for (unsigned cpu=1;cpu<4;cpu++) {
        struct channel *c=&channels[cpu];
        uint64_t error=acquire(&c->error.value);
        if (error) {
            value("ERROR_CPU=",cpu);value("ERROR_ROUND=",c->failed_round);
            value("ERROR_WORD=",c->failed_word);value("ACTUAL=",c->actual);
            value("EXPECTED=",c->expected);
            dsu_fail(error==1?"DSU_PAYLOAD_MISMATCH":error==2?"DSU_CONSUMER_TIMEOUT":
                     error==3?"DSU_PROBE_POINTER":"DSU_HAMMER_READBACK");
        }
    }
}
int main(void) {
    lab_begin("dsu");
    check(!(SYS(sctlr_el3)&5),"ENTRY_MMU_DCACHE_OFF");
#ifdef LAB_AGILEX5
    check(!(MMIO32(0x10d14058)&0xc00),"A55_BOOT_CONFIGURATION");
    MMIO32(0x82010000)=0xd503205f;MMIO32(0x82010004)=0x17ffffff;
#endif
    for (unsigned cpu=0;cpu<4;cpu++) *quiescent(cpu)=0;
    workload_init();
    tables_init();
#ifdef DSU_PARTITIONED
    dsu_check(policy_enter(0,&channels[0].policy),"PRIMARY_POLICY_PROFILE_ACCEPTED");
    dsu_check(global_policy_enter(),"CLUSTER_POLICY_PROFILE_ACCEPTED");
#endif
    release((uint64_t *)&dsu_tables_ready,READY); /* Published while caches off. */
    barrier();
    dsu_check(enable_cached_map(),"PRIMARY_CACHE_MMU_ENABLED");
#ifdef LAB_AGILEX5
    /* Qualified standalone reset/power entry sequence; not PSCI CPU_ON. */
    MMIO32(0x10d1220c)=(MMIO32(0x10d1220c)&~0x3cU)|8;
    *(volatile uint64_t *)0x10d110a0=(uintptr_t)secondary_start>>2;
    *(volatile uint64_t *)0x10d110a8=(uintptr_t)secondary_start>>2;
    *(volatile uint64_t *)0x10d110b0=(uintptr_t)secondary_start>>2;
    barrier();MMIO32(0x10d14050)|=0xe<<1;barrier();MMIO32(0x10d11094)=0xe;
#endif
    uint64_t limit=deadline();
    for (unsigned cpu=1;cpu<4;cpu++) {
        while (acquire(&channels[cpu].online.value)!=READY) {
            if (expired(limit)) dsu_fail("DSU_SECONDARY_ONLINE_TIMEOUT");
            relax();
        }
        dsu_check((channels[cpu].sctlr&0x1005)==0x1005,"SECONDARY_CACHE_MMU_ENABLED");
        value("CPU=",cpu);value("CTR_EL0=",channels[cpu].ctr);
        value("PAYLOAD_PAR_EL1=",channels[cpu].par);
        dsu_check(cached_translation(&channels[cpu]),"SECONDARY_WB_INNER_SHAREABLE_TRANSLATION");
    }
    check(1,"WB_INNER_SHAREABLE_MAP_ALL_CORES");
    uint64_t begin=SYS(cntpct_el0);
    for (unsigned round=1;round<=ROUNDS;round++) {
        for (unsigned cpu=1;cpu<4;cpu++) {
            struct channel *c=&channels[cpu];
            for (unsigned word=0;word<WORDS;word++) c->payload[word]=pattern(cpu,round,word);
#ifdef DSU_CORRUPT_PAYLOAD
            if (cpu==1 && round==37) c->payload[127]^=1;
#endif
            release(&c->sequence.value,round);
        }
        limit=deadline();
        for (unsigned cpu=1;cpu<4;cpu++) {
            while (acquire(&channels[cpu].acknowledgement.value)!=round) {
                check_consumer_errors();
                if (expired(limit)) dsu_fail("DSU_PRODUCER_TIMEOUT");
                relax();
            }
        }
    }
    uint64_t elapsed=SYS(cntpct_el0)-begin;
    primary_workload();
    for (unsigned cpu=1;cpu<4;cpu++) {
        limit=deadline();
        while (acquire(&channels[cpu].finished.value)!=READY) {
            check_consumer_errors();
            if (expired(limit)) dsu_fail("DSU_FINISH_TIMEOUT");
            relax();
        }
        dsu_check(channels[cpu].words_checked==ROUNDS*WORDS,"CONSUMER_FULL_PAYLOAD_VERIFIED");
        value("CONSUMER=",cpu);value("WORDS_CHECKED=",channels[cpu].words_checked);
        value("CHECKSUM=",channels[cpu].checksum);
    }
    check(1,"THREE_CACHED_CONSUMERS_VERIFIED");
    dsu_check(wait_quiescent(),"SECONDARIES_CLEANED_AND_QUIESCENT");
#ifdef DSU_PARTITIONED
    for (unsigned cpu=1;cpu<4;cpu++)
        dsu_check(channels[cpu].policy.restored,"SECONDARY_POLICY_RESTORED");
    dsu_check(global_policy_exit(),"CLUSTER_POLICY_RESTORED");
    dsu_check(policy_exit(&channels[0].policy),"PRIMARY_POLICY_RESTORED");
#endif
    value("TRANSFER_ROUNDS=",ROUNDS);value("ELAPSED_COUNTER_TICKS=",elapsed);
#ifdef LAB_AGILEX5
    text("INFO HARDWARE_COHERENCY_RESULT_REQUIRES_CAPTURED_BOARD_RUN\n");
#else
    text("INFO QEMU_FUNCTIONAL_MODEL_NOT_PHYSICAL_CACHE_OR_L3_TIMING\n");
#endif
#ifdef DSU_PARTITIONED
    text("INFO DSU_L3_PARTITIONED_POLICY: compare ticks only with matching physical baseline\n");
#else
    text("NOT_RUN DSU_L3_PARTITION_COMPARISON: hardware register policy not enabled\n");
#endif
    lab_done(0);
}
