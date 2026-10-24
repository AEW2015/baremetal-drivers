.section .text.start,"ax"
.global _start
_start:
 msr daifset,#15
 mrs x0,cptr_el3
 bic x0,x0,#0x400
 msr cptr_el3,x0
 msr spsel,#1
 ldr x0,=0x83fff000
 mov sp,x0
 adr x0,net_vectors
 msr vbar_el3,x0
 isb
 ldr x0,=__bss_start
 ldr x1,=__bss_end
1: cmp x0,x1
 b.hs 2f
 strb wzr,[x0],#1
 b 1b
2: bl example_main
3: wfi
 b 3b
.balign 2048
net_vectors:
.rept 16
 b board_exception
 .balign 128
.endr
