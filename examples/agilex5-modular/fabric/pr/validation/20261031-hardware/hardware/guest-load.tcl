hps.a55.0 configure -event halted {}
hps.a55.0 configure -event resumed {}
gdb port disabled
tcl port disabled
telnet port disabled
init
halt
hps.dap apsel 0x4000
targets hps.sys_bus
load_image /home/dev/baremetal-guide-validation/examples/build/pr-hardware-20261031T223750.584108Z-guest.bin 0x82100000 bin
dump_image /home/dev/baremetal-guide-validation/examples/build/pr-hardware-20261031T223750.584108Z-guest.bin.readback 0x82100000 9424
puts "PR_GUEST_LOAD_COMPLETE"
shutdown
