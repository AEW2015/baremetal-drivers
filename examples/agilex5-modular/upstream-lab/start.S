.section .text.start,"ax"
.global _start
_start:
    msr daifset,#15
    msr spsel,#1
    ldr x0,=LAB_STACK
    mov sp,x0
    mrs x0,cptr_el3
    bic x0,x0,#0x400
    msr cptr_el3,x0
    /* Bootstrap supplies physical RAM with translation/cache disabled. */
    mrs x0,sctlr_el3
    bic x0,x0,#2
    msr sctlr_el3,x0
    ldr x0,=vectors
    msr vbar_el3,x0
    isb
    ldr x0,=__bss_start
    ldr x1,=__bss_end
1:  cmp x0,x1
    b.hs 2f
    strb wzr,[x0],#1
    b 1b
2:  bl main
3:  wfi
    b 3b
.balign 2048
vectors:
.rept 16
    b fault
    .balign 128
.endr
