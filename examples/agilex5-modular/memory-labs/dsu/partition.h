// SPDX-License-Identifier: MIT-0
/* Opt-in Agilex-only policy, derived from the pinned Altera RT helper:
 * meta-altera-rt 7cf884ac5be93779f37b189c2720fa3f92955de5,
 * recipes-bsp/arm-trusted-firmware/files/core1_nl3a_cp_qos_plat_helpers.S.
 * Change partition/SID only: do not change no-L3-allocation or CHI QoS.
 */
#ifndef DSU_PARTITION_H
#define DSU_PARTITION_H
struct policy_record { uint64_t actlr, sid, active, restored; };
#if defined(DSU_PARTITIONED) && !defined(LAB_AGILEX5)
#error DSU partition writes are restricted to the explicit Agilex hardware variant
#endif
#ifdef DSU_PARTITIONED
#define DSU_PARTCR S3_0_C15_C4_3
#define DSU_THREADSID S3_0_C15_C4_0
#define DSU_SYS(name) SYS(name)
#define DSU_MSR(name,value) MSR(name,value)
static uint64_t saved_partcr, global_policy_active;
static int policy_enter(unsigned cpu,struct policy_record *record) {
    unsigned part=(SYS(midr_el1)>>4)&0xfff;
    if (SYS(CurrentEL)!=12 || ((SYS(midr_el1)>>24)&255)!=0x41 ||
        part!=(cpu<2?0xd05U:0xd0bU)) return 0;
    record->actlr=SYS(actlr_el3);
    MSR(actlr_el3,record->actlr|(3ULL<<10));
    __asm__ volatile("isb" ::: "memory");
    record->sid=DSU_SYS(DSU_THREADSID);
    if (record->sid!=0) {
        MSR(actlr_el3,record->actlr);
        __asm__ volatile("isb" ::: "memory");
        return 0; /* Comparison requires all cores to start in scheme 0. */
    }
    record->active=1;
    DSU_MSR(DSU_THREADSID,cpu==1?1:0);
    __asm__ volatile("isb" ::: "memory");
    return DSU_SYS(DSU_THREADSID)==(cpu==1?1ULL:0ULL);
}
static int policy_exit(struct policy_record *record) {
    if (!record->active) return 1;
    __asm__ volatile("dsb sy" ::: "memory");
    DSU_MSR(DSU_THREADSID,record->sid);
    __asm__ volatile("isb" ::: "memory");
    int ok=DSU_SYS(DSU_THREADSID)==record->sid;
    MSR(actlr_el3,record->actlr);
    __asm__ volatile("isb" ::: "memory");
    record->restored=ok && SYS(actlr_el3)==record->actlr;
    record->active=0;
    return record->restored;
}
static int global_policy_enter(void) {
    saved_partcr=DSU_SYS(DSU_PARTCR);
    value("PARTCR_SAVED=",saved_partcr);
    if ((saved_partcr&0xff)!=0) return 0; /* Require a shared baseline. */
    DSU_MSR(DSU_PARTCR,(saved_partcr&~0xffULL)|0x1eULL);
    __asm__ volatile("dsb sy; isb" ::: "memory");
    global_policy_active=1;
    value("PARTCR_ACTIVE=",DSU_SYS(DSU_PARTCR));
    return DSU_SYS(DSU_PARTCR)==((saved_partcr&~0xffULL)|0x1eULL);
}
static int global_policy_exit(void) {
    if (!global_policy_active) return 1;
    DSU_MSR(DSU_PARTCR,saved_partcr);
    __asm__ volatile("dsb sy; isb" ::: "memory");
    int ok=DSU_SYS(DSU_PARTCR)==saved_partcr;
    value("PARTCR_RESTORED=",DSU_SYS(DSU_PARTCR));
    global_policy_active=0;
    return ok;
}
#else
static int policy_enter(unsigned cpu,struct policy_record *record) { (void)cpu;(void)record;return 1; }
static int policy_exit(struct policy_record *record) { (void)record;return 1; }
static inline int global_policy_enter(void) { return 1; }
static int global_policy_exit(void) { return 1; }
#endif
#endif
