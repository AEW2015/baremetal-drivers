hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; targets hps.sys_bus;

set sda [lindex [hps.sys_bus read_memory 0x10d13020 32 1] 0]
set scl [lindex [hps.sys_bus read_memory 0x10d13024 32 1] 0]
set directions [lindex [hps.sys_bus read_memory 0x10c03204 32 1] 0]
if {$sda != 4 || $scl != 4 || ($directions & 768)} {error {Unexpected initial mux/direction}}
hps.sys_bus write_memory 0x10d13020 32 {8}
hps.sys_bus write_memory 0x10d13024 32 {8}
echo MGMT_SELECT_OK

shutdown
