.section .text,"ax"
.global _start
_start:
    ldr x2, =0x10c02000
again:
    adr x1, message
next:
    ldrb w0, [x1], #1
    cbz w0, delay
wait:
    ldr w3, [x2, #0x14]
    tbz w3, #5, wait
    str w0, [x2]
    b next
delay:
    mov x4, #0x100000
spin:
    subs x4, x4, #1
    b.ne spin
    b again
message:
    .asciz "Hello, World! executing from HPS DDR bank 3A @ 0x82000000\r\n"
