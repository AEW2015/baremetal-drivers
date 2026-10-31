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
set load_status [catch {
targets hps.sys_bus
load_image /home/dev/baremetal-guide-validation/examples/build/upstream26-bl31.bin 0x80000000 bin
dump_image /home/dev/baremetal-guide-validation/examples/build/upstream26-bl31.bin.readback 0x80000000 73816
} load_message]
hps.dap apcsw $old_csw
if {$load_status} {error $load_message}
puts "BL31_LOAD_READBACK_COMPLETE"
shutdown
