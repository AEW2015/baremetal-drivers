/* HPS OCRAM-only smoke test: no DDR, C runtime, MMU, UART or stack required.
 * Enter at 0, attach OpenOCD with semihosting enabled, then resume at 4.
 */
.section .text
.global _start
_start:
    b _start
.global hello_entry
hello_entry:
    mov x0, #4                 /* SYS_WRITE0 */
    adr x1, message
    hlt #0xf000                /* AArch64 semihosting */
.global hello_done
hello_done:
    b hello_done
message:
    .asciz "Hello, World! Agilex 5 HPS executing from OCRAM.\n"
