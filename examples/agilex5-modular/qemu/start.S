.section .text.start,"ax"
.global _start
_start:
 msr daifset,#15
 msr spsel,#1
 ldr x0,=__stack_top
 mov sp,x0
 mrs x0,cptr_el3
 bic x0,x0,#0x400
 msr cptr_el3,x0
 mov x0,#(3 << 20)
 msr cpacr_el1,x0
 isb
 ldr x0,=__bss_start
 ldr x1,=__bss_end
1: cmp x0,x1
 b.hs 2f
 strb wzr,[x0],#1
 b 1b
2: bl main
3: wfi
 b 3b
.global qemu_neon_add
qemu_neon_add:
 ld1 {v0.4s},[x0]
 ld1 {v1.4s},[x1]
 add v0.4s,v0.4s,v1.4s
 st1 {v0.4s},[x2]
 ret
