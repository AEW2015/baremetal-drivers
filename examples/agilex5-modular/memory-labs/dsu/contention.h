// SPDX-License-Identifier: MIT-0
/* Optional probe/hammer workload. These are software-loop counter ticks,
 * never an isolated measurement of physical L3 access latency.
 */
#ifndef DSU_CONTENTION_H
#define DSU_CONTENTION_H
#ifdef DSU_CONTENTION
#define PROBE_BASE (RAM_BASE+0x05000000UL)
#define PROBE_LINES 6144U /* 384 KiB, one pointer per 64-byte line. */
#define PROBE_STRIDE 1537U /* Coprime to 6144: one cycle covers every node. */
#define PROBE_BATCHES 1024U
#define PROBE_BATCH_STEPS 64U
#define HAMMER_LINES (DSU_HAMMER_BYTES/64) /* Separate 2 MiB per A76. */
static struct flag workload_start, measure_go, workload_stop, probe_done;
static uintptr_t hammer_base(unsigned cpu) { return RAM_BASE+0x04000000UL+(cpu-2)*0x00800000UL; }
static void workload_init(void) {
    /* Initialize before cache enable, then use the static WB mapping. */
    for (unsigned i=0;i<PROBE_LINES;i++)
        *(volatile uint64_t *)(PROBE_BASE+i*64)=PROBE_BASE+((i+PROBE_STRIDE)%PROBE_LINES)*64;
    for (unsigned cpu=2;cpu<4;cpu++)
        for (unsigned i=0;i<HAMMER_LINES;i++)
            *(volatile uint64_t *)(hammer_base(cpu)+i*64)=i;
    barrier();
}
static void wait_gate(unsigned cpu,const uint64_t *gate) {
    uint64_t limit=deadline()+TIMEOUT_SECONDS*SYS(cntfrq_el0);
    while (!acquire(gate)) {
        if (acquire(&abort_requested.value)) quiesce(cpu);
        if (expired(limit)) { consumer_failure(cpu,0,WORDS,0,1,2);quiesce(cpu); }
        relax();
    }
}
static void secondary_workload(unsigned cpu) {
    struct channel *c=&channels[cpu];
    release(&c->workload_ready.value,READY);
    wait_gate(cpu,&workload_start.value);
    if (cpu==1) {
        wait_gate(cpu,&measure_go.value);
        uintptr_t pointer=PROBE_BASE;
        uint64_t minimum=~0ULL,maximum=0,total=0;
        for (unsigned batch=0;batch<PROBE_BATCHES;batch++) {
            if (acquire(&abort_requested.value)) quiesce(cpu);
            __asm__ volatile("isb" ::: "memory");
            uint64_t before=SYS(cntpct_el0);
            for (unsigned step=0;step<PROBE_BATCH_STEPS;step++) {
                uint64_t next=*(volatile uint64_t *)pointer;
                if (next<PROBE_BASE || next>=PROBE_BASE+PROBE_LINES*64 || ((next-PROBE_BASE)&63)) {
                    consumer_failure(cpu,batch,step,next,PROBE_BASE,3);quiesce(cpu);
                }
                pointer=(uintptr_t)next;
            }
            __asm__ volatile("dsb ld; isb" ::: "memory");
            uint64_t ticks=SYS(cntpct_el0)-before;
            if (ticks<minimum) minimum=ticks;
            if (ticks>maximum) maximum=ticks;
            total+=ticks;
        }
        uintptr_t expected=PROBE_BASE+(((uint64_t)PROBE_BATCHES*PROBE_BATCH_STEPS*PROBE_STRIDE)%PROBE_LINES)*64;
        if (pointer!=expected) { consumer_failure(cpu,0,0,pointer,expected,3);quiesce(cpu); }
        c->probe_min=minimum;c->probe_max=maximum;c->probe_total=total;
        c->probe_steps=(uint64_t)PROBE_BATCHES*PROBE_BATCH_STEPS;
        release(&probe_done.value,READY);
        wait_gate(cpu,&workload_stop.value);
    } else {
        uint64_t state=0x123456789abcdefULL^cpu,operations=0;
        while (!acquire(&workload_stop.value)) {
            if (acquire(&abort_requested.value)) quiesce(cpu);
            for (unsigned i=0;i<64;i++) {
                state^=state<<13;state^=state>>7;state^=state<<17;
                volatile uint64_t *word=(uint64_t *)(hammer_base(cpu)+(state&(HAMMER_LINES-1))*64);
                *word=state;
                uint64_t actual=*word;
                if (actual!=state) { consumer_failure(cpu,0,i,actual,state,4);quiesce(cpu); }
                operations++;
            }
            if (operations==64) release(&c->hammer_live.value,READY);
        }
        c->hammer_operations=operations;
    }
}
static void primary_workload(void) {
    uint64_t limit=deadline();
    for (unsigned cpu=1;cpu<4;cpu++)
        while (acquire(&channels[cpu].workload_ready.value)!=READY) {
            check_consumer_errors();
            if (expired(limit)) dsu_fail("DSU_WORKLOAD_READY_TIMEOUT");
            relax();
        }
    release(&workload_start.value,READY);
    for (unsigned cpu=2;cpu<4;cpu++)
        while (acquire(&channels[cpu].hammer_live.value)!=READY) {
            check_consumer_errors();
            if (expired(limit)) dsu_fail("DSU_HAMMER_START_TIMEOUT");
            relax();
        }
    release(&measure_go.value,READY);
    limit=deadline();
    while (acquire(&probe_done.value)!=READY) {
        check_consumer_errors();
        if (expired(limit)) dsu_fail("DSU_PROBE_TIMEOUT");
        relax();
    }
    release(&workload_stop.value,READY);
    limit=deadline();
    for (unsigned cpu=1;cpu<4;cpu++)
        while (acquire(quiescent(cpu))!=READY) {
            check_consumer_errors();
            if (expired(limit)) dsu_fail("DSU_WORKLOAD_STOP_TIMEOUT");
            relax();
        }
    value("PROBE_BYTES=",PROBE_LINES*64);value("PROBE_STEPS=",channels[1].probe_steps);
    value("TICKS_PER_64_STEPS_MIN=",channels[1].probe_min);
    value("TICKS_PER_64_STEPS_MAX=",channels[1].probe_max);
    value("PROBE_TOTAL_TICKS=",channels[1].probe_total);
    for (unsigned cpu=2;cpu<4;cpu++) {
        dsu_check(channels[cpu].hammer_operations>=64,"HAMMER_EXECUTED_DURING_PROBE");
        value("HAMMER_CPU=",cpu);value("HAMMER_OPERATIONS=",channels[cpu].hammer_operations);
    }
    dsu_check(channels[1].probe_steps==PROBE_BATCHES*PROBE_BATCH_STEPS,"DEPENDENT_PROBE_COMPLETED");
    text("PASS CONTENTION_WORKLOAD_COMPLETE\n");
    text("INFO COUNTER_TICKS_INCLUDE_LOOP_CHECKS_AND_BARRIERS_NOT_RAW_L3_LATENCY\n");
}
#else
static void workload_init(void) {}
static void secondary_workload(unsigned cpu) { (void)cpu; }
static void primary_workload(void) {}
#endif
#endif
