ENTRY(_start)
SECTIONS {
 . = 0;
 .text : { *(.text.start) *(.text*) *(.rodata*) }
 . = ALIGN(16);
 .data : { *(.data*) }
 .bss (NOLOAD) : { *(.bss*) *(COMMON) }
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
 ASSERT(. < 0x60000, "Application must fit in OCRAM")
}
