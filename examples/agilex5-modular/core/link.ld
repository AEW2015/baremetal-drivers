ENTRY(_start)
SECTIONS {
 . = 0x82100000;
 .text : { *(.text.start) *(.text*) *(.rodata*) }
 . = ALIGN(16);
 .data : { *(.data*) }
 __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) }
 __bss_end = .;
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
 ASSERT(. < 0x82200000, "Example exceeds reserved code region")
}
