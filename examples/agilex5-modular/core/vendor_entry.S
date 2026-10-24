/* Board C runtime startup. DDR is already initialized by the matching ATF hook.
 * Start with MMU/D-cache off; C installs the tested noncacheable identity map.
 * The simulation hook's page tables are not reused here.
 */
.section .text,"ax"
.global board_vendor_entry
board_vendor_entry:
 msr daifset,#15
 msr spsel,#1
 ldr x0,=0x83fff000
 mov sp,x0
 mrs x0,cptr_el3
 bic x0,x0,#0x400
 msr cptr_el3,x0
 adr x0,board_vectors
 msr vbar_el3,x0
 isb
 ldr x0,=__bss_start__
 ldr x1,=__bss_end__
1: cmp x0,x1
 b.hs 2f
 strb wzr,[x0],#1
 b 1b
2: bl board_vendor_run
3: wfi
 b 3b
.balign 2048
board_vectors:
.rept 16
 b board_vendor_fault
 .balign 128
.endr
