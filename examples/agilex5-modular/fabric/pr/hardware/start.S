/* EL3 diagnostic boot can enter using SP_EL0. Exceptions select SP_EL3:
 * provide an independent stack before the C fault reporter touches memory.
 */
#define example_main pr_hps_entry
#define board_exception pr_exception_entry
#include "../../../core/start.S"
#undef board_exception
#undef example_main
.section .text,"ax"
pr_hps_entry:
    msr daifset, #15
    msr spsel, #1
    ldr x0, =0x83fff000
    mov sp, x0
    b example_main
.section .text,"ax"
pr_exception_entry:
    ldr x0, =0x83ffe000
    mov sp, x0
    b board_exception
