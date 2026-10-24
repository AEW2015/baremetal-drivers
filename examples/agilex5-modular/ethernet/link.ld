ENTRY(_start)
SECTIONS {
 . = 0x82600000;
 .text : { *(.text.start) *(.text*) *(.rodata*) }
 . = ALIGN(16);
 .data : { *(.data*) }
 __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) }
 __bss_end = .;
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
 ASSERT(. < 0x83400000, "Network image exceeds reserved code/data region")
}
