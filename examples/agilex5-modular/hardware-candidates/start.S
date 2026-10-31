.section .text.start,"ax"
.global _start
_start:
    msr daifset,#15
    msr spsel,#1
    ldr x0,=LAB_STACK
    mov sp,x0
    mrs x2,CurrentEL
    cmp x2,#12
    b.ne 4f
    mrs x0,cptr_el3
    bic x0,x0,#0x400
    msr cptr_el3,x0
    mrs x0,sctlr_el3
    bic x0,x0,#2
    msr sctlr_el3,x0
#ifndef LAB_QEMU
    /* Pinned TF-A Agilex5 PLAT_SYS_COUNTER_FREQ_IN_TICKS. */
    mrs x0,cntfrq_el0
    cbnz x0,5f
    ldr x0,=400000000
    msr cntfrq_el0,x0
5:
#endif
    ldr x0,=vector_table
    msr vbar_el3,x0
    b 6f
4:  cmp x2,#8
    b.ne 7f
    mov x0,#0
    msr cptr_el2,x0
    mrs x0,sctlr_el2
    bic x0,x0,#2
    msr sctlr_el2,x0
    ldr x0,=vector_table
    msr vbar_el2,x0
    b 6f
7:  ldr x0,=vector_table
    msr vbar_el1,x0
6:  isb
    ldr x0,=__bss_start
    ldr x1,=__bss_end
1:  cmp x0,x1
    b.hs 2f
    strb wzr,[x0],#1
    b 1b
2:  bl main
3:  wfi
    b 3b
