/* Shared secure EL3 startup. Primary initializes C state; secondaries bypass it. */
.section .text.start,"ax"
.global _start
_start:
 msr daifset,#15
 msr spsel,#1
 ldr x0,=__stack_top
 mov sp,x0
#ifdef LAB_MULTICORE
 mrs x0,mpidr_el1
#ifdef LAB_AGILEX5
 ubfx x0,x0,#8,#8
#else
 and x0,x0,#255
#endif
 cbnz x0,secondary_start
#endif
#ifdef LAB_AGILEX5
 /* The established diagnostic enters EL3 with translations/cache off. */
 mrs x0,sctlr_el3
 bic x0,x0,#2
 msr sctlr_el3,x0
 mrs x0,cntfrq_el0
 cbnz x0,9f
 ldr x0,=400000000 /* pinned TF-A platform frequency; not a rate claim */
 msr cntfrq_el0,x0
9: isb
#endif
 /* Relocate initial .data bytes from their ELF load address to runtime RAM. */
 ldr x0,=__data_load
 ldr x1,=__data_start
 ldr x2,=__data_end
#ifndef SKIP_DATA_COPY
1: cmp x1,x2
 b.hs 2f
 ldrb w3,[x0],#1
 strb w3,[x1],#1
 b 1b
#endif
 /* Poison BSS first so clearing is tested even when QEMU supplies zero RAM. */
2: ldr x0,=__bss_start
 ldr x1,=__bss_end
 mov w2,#0xa5
3: cmp x0,x1
 b.hs 4f
 strb w2,[x0],#1
 b 3b
4:
#ifndef SKIP_BSS_CLEAR
 ldr x0,=__bss_start
5: cmp x0,x1
 b.hs 6f
 strb wzr,[x0],#1
 b 5b
#endif
6: ldr x0,=vectors
 msr vbar_el3,x0
 isb
 bl main
 mov x0,#1
 bl lab_done

/* Each vector slot is 128 bytes, table base aligned to 2048 bytes. */
.macro slot target
 .balign 128
 b \target
.endm
.balign 2048
.global vectors
vectors:
 slot sync_entry
 slot irq_entry
 slot fiq_entry
 slot other_entry
 slot sync_entry
 slot irq_entry
 slot fiq_entry
 slot other_entry
 slot other_entry
 slot other_entry
 slot other_entry
 slot other_entry
 slot other_entry
 slot other_entry
 slot other_entry
 slot other_entry
.balign 128

.macro entry name, kind
\name:
 sub sp,sp,#256
 stp x0,x1,[sp,#0]
 stp x2,x3,[sp,#16]
 stp x4,x5,[sp,#32]
 stp x6,x7,[sp,#48]
 stp x8,x9,[sp,#64]
 stp x10,x11,[sp,#80]
 stp x12,x13,[sp,#96]
 stp x14,x15,[sp,#112]
 stp x16,x17,[sp,#128]
 stp x18,x19,[sp,#144]
 stp x20,x21,[sp,#160]
 stp x22,x23,[sp,#176]
 stp x24,x25,[sp,#192]
 stp x26,x27,[sp,#208]
 stp x28,x29,[sp,#224]
 str x30,[sp,#240]
 mov x0,#\kind
 bl exception_dispatch
 ldp x0,x1,[sp,#0]
 ldp x2,x3,[sp,#16]
 ldp x4,x5,[sp,#32]
 ldp x6,x7,[sp,#48]
 ldp x8,x9,[sp,#64]
 ldp x10,x11,[sp,#80]
 ldp x12,x13,[sp,#96]
 ldp x14,x15,[sp,#112]
 ldp x16,x17,[sp,#128]
 ldp x18,x19,[sp,#144]
 ldp x20,x21,[sp,#160]
 ldp x22,x23,[sp,#176]
 ldp x24,x25,[sp,#192]
 ldp x26,x27,[sp,#208]
 ldp x28,x29,[sp,#224]
 ldr x30,[sp,#240]
 add sp,sp,#256
 eret
.endm
entry sync_entry,0
entry irq_entry,1
entry fiq_entry,2
entry other_entry,3

#ifdef LAB_MULTICORE
.global secondary_start
secondary_start:
 /* Each secondary has its own stack and waits for primary C initialization. */
 msr daifset,#15
 msr spsel,#1
 mrs x0,mpidr_el1
#ifdef LAB_AGILEX5
 ubfx x0,x0,#8,#8
 mrs x1,sctlr_el3
 bic x1,x1,#1
 bic x1,x1,#4
 msr sctlr_el3,x1
 isb
#else
 and x0,x0,#255
#endif
 ldr x1,=__stack_top
 sub x1,x1,x0,lsl #14
 mov sp,x1
 bl secondary_main
1: wfi
 b 1b
#endif

/* Fault and recovery labels let handlers skip only a known lab instruction. */
.global trigger_break,break_instruction,break_resume
trigger_break:
break_instruction:
#ifdef WRONG_BRK
 brk #0x124
#else
 brk #0x123
#endif
break_resume:
 ret
.global trigger_store,store_instruction,store_resume
trigger_store:
store_instruction:
 str x1,[x0]
store_resume:
 ret
