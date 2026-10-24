.section .text.start,"ax"
.global _start
_start:
    ldr x0, =0x70000
    mov sp, x0
    bl uart_main
1:  b 1b
