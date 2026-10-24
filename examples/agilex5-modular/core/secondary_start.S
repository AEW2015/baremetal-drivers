/* Standalone EL3 secondary entry: no C runtime, dedicated record per affinity. */
.section .text,"ax"
.global secondary_entry
.balign 4
secondary_entry:
 msr daifset,#15
 mrs x0,sctlr_el3
 bic x0,x0,#1
 bic x0,x0,#4
 msr sctlr_el3,x0
 isb
 mrs x1,mpidr_el1
 ubfx x2,x1,#8,#8
 ldr x3,=0x85300000
 add x3,x3,x2,lsl #5
 mrs x4,midr_el1
 str x1,[x3,#8]
 str x4,[x3,#16]
 mov x4,#0xcafe
 dsb sy
 str x4,[x3]
 dsb sy
 ldr x5,=0x82010000
 br x5
