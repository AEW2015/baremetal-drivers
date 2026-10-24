ENTRY(_start)
PHDRS {
 text PT_LOAD FLAGS(5);
 rodata PT_LOAD FLAGS(4);
 data PT_LOAD FLAGS(6);
}
SECTIONS {
 . = 0x40200000;
 .text : { *(.text.start) *(.text*) } :text
 . = ALIGN(4096);
 .rodata : { *(.rodata*) } :rodata
 ASSERT(. < 0x40300000, "Lab code exceeds its reserved region")
 /* QEMU loads p_paddr=0x40300000. Startup copies to VMA=0x40400000. */
 .data 0x40400000 : AT(0x40300000) {
  __data_start = .;
  *(.data*)
  __data_end = .;
 } :data
 __data_load = LOADADDR(.data);
 . = ALIGN(16);
 __bss_start = .;
 .bss (NOLOAD) : { *(.bss*) *(COMMON) } :data
 __bss_end = .;
 __stack_top = 0x41000000;
 ASSERT(. < 0x40500000, "Lab data exceeds its reserved region")
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
