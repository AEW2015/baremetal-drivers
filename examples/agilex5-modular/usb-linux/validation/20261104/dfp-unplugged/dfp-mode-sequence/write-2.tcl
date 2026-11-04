hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; gdb port disabled; tcl port disabled; telnet port disabled; init; targets hps.sys_bus;
set cc_operation 3
# SPDX-License-Identifier: MIT-0
# A reviewed caller supplies cc_operation in 1..4. The FPGA additionally gates
# writes with a build parameter and fixes address 0x47, register 0x0a and value.
namespace eval cc_mode {
    if {![info exists ::cc_operation] || $::cc_operation < 1 || $::cc_operation > 4} {
        error "No allowed CC operation supplied"
    }
    proc rd {address} {return [lindex [hps.sys_bus read_memory $address 32 1] 0]}
    proc control {value} {hps.sys_bus write_memory 0x20010080 32 [list $value]}
    # Pinned Agilex 5 TF-A definitions: RSTMGR base 0x10d11000,
    # BRGMODRST offset 0x2c, LWHPS2FPGA reset bit 1. Fail before fabric access.
    if {[rd 0x10d1102c] & 2} {error "LWH2F is held in reset; no fabric access attempted"}
    set saved [rd 0x20010080]
    set selected [expr {($saved & ~2032) | 240}]
    control $selected
    set before [rd 0x20010070]
    if {(($before>>16)&15) != 12 || ($before&255) != 204 || !($before & (1<<15))} {
        error "No mode-write-capable CC probe; no write trigger sent"
    }
    if {$before & (1<<30)} {error "CC probe already busy"}
    set triggered [expr {($selected | ($::cc_operation<<8)) ^ (1<<31)}]
    control $triggered
    if {[rd 0x20010080] != $triggered} {error "CC operation PIO readback mismatch"}
    set completed 0
    for {set poll 0} {$poll < 200} {incr poll} {
        set status [rd 0x20010070]
        # The accepted toggle and command identify this transaction even if a
        # short transfer completes before the first JTAG status read.
        if {(($status>>20)&1) == (($triggered>>31)&1) && (($status>>8)&7) == $::cc_operation && ($status&(1<<31)) && !($status&(1<<30))} {
            set completed 1
            break
        }
        after 1
    }
    # Clearing command bits while retaining the toggle starts no transaction.
    control [expr {($saved & ~((1<<31)|1792)) | ($triggered&(1<<31))}]
    echo [format {CC_MODE_TRANSACTION operation=%d completed=%d error=%d status=0x%08x} $::cc_operation $completed [expr {($status>>26)&15}] $status]
    if {!$completed || (($status>>26)&15)} {error "CC mode write did not complete successfully"}
    echo CC_MODE_WRITE_COMPLETE
}

shutdown
