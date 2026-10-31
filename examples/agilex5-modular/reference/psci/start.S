/* NS-EL2 primary and PSCI CPU_ON secondary entry, dedicated stacks/vectors. */
.section .text.start,"ax"
.global _start
_start:
 msr daifset,#15
 msr spsel,#1
 ldr x0,=0x83fff000
 mov sp,x0
 mrs x0,CurrentEL
 cmp x0,#8
 b.ne .Lguard
 mrs x0,sctlr_el2
 bic x0,x0,#2
 msr sctlr_el2,x0
 mov x0,#0
 msr cptr_el2,x0
 ldr x0,=primary_vectors
 msr vbar_el2,x0
 isb
 b .Lbss
.Lguard:
 cmp x0,#12
 b.ne .Lbss
 ldr x0,=primary_vectors
 msr vbar_el3,x0
 isb
.Lbss:
 ldr x0,=__bss_start
 ldr x1,=__bss_end
1: cmp x0,x1
 b.hs 2f
 strb wzr,[x0],#1
 b 1b
2: bl main
3: wfi
 b 3b
.balign 64
.global psci_secondary_entry
psci_secondary_entry:
 /* x0 is the PSCI context_id; preserve it until C receives it. */
 mov x20,x0
 msr daifset,#15
 msr spsel,#1
 ldr x1,=0x83ffb000
 mov sp,x1
 mrs x1,CurrentEL
 cmp x1,#8
 b.ne .Lsecondary_bad_el
 ldr x1,=secondary_vectors
 msr vbar_el2,x1
 mrs x1,sctlr_el2
 bic x1,x1,#2
 msr sctlr_el2,x1
 isb
 mov x0,x20
 bl secondary_main
4: wfi
 b 4b
.Lsecondary_bad_el:
 /* No privileged EL2 operation at an unexpected level. */
 mov x0,x20
 bl secondary_wrong_el
 b 4b
.balign 2048
primary_vectors:
.rept 16
 b primary_fault
 .balign 128
.endr
.balign 2048
secondary_vectors:
.rept 16
 b secondary_fault
 .balign 128
.endr
