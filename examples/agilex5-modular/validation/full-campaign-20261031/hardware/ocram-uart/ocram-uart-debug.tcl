hps.a55.0 configure -event halted {}
hps.a55.0 configure -event resumed {}
gdb port disabled
tcl port disabled
telnet port disabled
init
halt
hps.dap apsel 0x4000
set csw_report [hps.dap apcsw]
if {![regexp {csw (0x[0-9a-fA-F]+)} $csw_report -> old_csw]} {error "CSW decode failed"}
hps.dap apcsw 0x10000000 0x30000000
targets hps.sys_bus
load_image /home/dev/baremetal-guide-validation/examples/build/reference-hardware-20261031T191037.126106Z-uart.bin 0 bin
dump_image /home/dev/baremetal-guide-validation/examples/build/reference-hardware-20261031T191037.126106Z-uart.bin.readback 0 464
hps.dap apcsw $old_csw
targets hps.a55.0
resume 0
shutdown
