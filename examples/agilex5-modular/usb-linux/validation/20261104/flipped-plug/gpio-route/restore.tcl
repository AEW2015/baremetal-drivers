hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; targets hps.sys_bus;

set directions [lindex [hps.sys_bus read_memory 0x10c03204 32 1] 0]
hps.sys_bus write_memory 0x10c03204 32 [list [expr {$directions & ~768}]]
hps.sys_bus write_memory 0x10d13020 32 {4}
hps.sys_bus write_memory 0x10d13024 32 {4}
if {[lindex [hps.sys_bus read_memory 0x10d13020 32 1] 0] != 4 || [lindex [hps.sys_bus read_memory 0x10d13024 32 1] 0] != 4} {error {Mux restoration mismatch}}
echo MGMT_RESTORE_OK

shutdown
