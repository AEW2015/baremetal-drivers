ENTRY(_start)
SECTIONS {
 . = 0x40200000;
 .text : { *(.text.start) *(.text*) *(.rodata*) }
 . = ALIGN(16);
 .data : { *(.data*) }
 __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) }
 __bss_end = .;
 __stack_top = 0x41000000;
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
 ASSERT(. < 0x40300000, "QEMU demo exceeds reserved code/data region")
}
