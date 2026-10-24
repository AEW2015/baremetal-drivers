.section .text.start,"ax"
.global _start
_start:
    ldr x0, =0x83fff000
    mov sp, x0
    ldr x0, =board_exception_vectors
    msr vbar_el3, x0
    isb
    mrs x0, cptr_el3
    bic x0, x0, #0x400
    msr cptr_el3, x0
    isb
    ldr x0, =__bss_start
    ldr x1, =__bss_end
1:  cmp x0, x1
    b.hs 2f
    strb wzr, [x0], #1
    b 1b
2:  bl example_main
3:  wfi
    b 3b
.section .text,"ax"
.global neon_add
neon_add:
    ld1 {v0.4s}, [x0]
    ld1 {v1.4s}, [x1]
    add v0.4s, v0.4s, v1.4s
    st1 {v0.4s}, [x2]
    ret

.balign 2048
board_exception_vectors:
.rept 16
    b board_exception
    .balign 128
.endr
