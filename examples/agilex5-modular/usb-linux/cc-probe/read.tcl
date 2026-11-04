# SPDX-License-Identifier: MIT-0
# Caller owns the bench mutex, checks fresh JTAG identity and initializes the
# HPS memory AP without halting the CPU. Requires the matching CC-probe SOF.
namespace eval cc_probe {
    proc rd {address} {return [lindex [hps.sys_bus read_memory $address 32 1] 0]}
    proc control {value} {hps.sys_bus write_memory 0x20010080 32 [list $value]}
    # Pinned Agilex 5 TF-A definitions: RSTMGR base 0x10d11000,
    # BRGMODRST offset 0x2c, LWHPS2FPGA reset bit 1. Fail before fabric access.
    if {[rd 0x10d1102c] & 2} {error "LWH2F is held in reset; no fabric access attempted"}
    set saved [rd 0x20010080]
    set selected [expr {($saved & ~2032) | 240}]
    control $selected
    set before [rd 0x20010070]
    if {(($before >> 16) & 15) != 12 || ($before & 255) != 204} {
        error "CC probe signature absent; no read trigger sent"
    }
    if {$before & (1 << 30)} {error "CC probe already busy; not replaced"}
    echo [format {CC_INPUTS before=0x%08x fault_n=%d vbus_det=%d id=%d scl=%d sda=%d} $before [expr {($before>>25)&1}] [expr {($before>>24)&1}] [expr {($before>>23)&1}] [expr {($before>>22)&1}] [expr {($before>>21)&1}]]
    set triggered [expr {$selected ^ (1 << 31)}]
    control $triggered
    if {[rd 0x20010080] != $triggered} {error "CC trigger PIO readback mismatch"}
    set busy_seen 0
    set completed 0
    for {set poll 0} {$poll < 200} {incr poll} {
        set status [rd 0x20010070]
        if {$status & (1 << 30)} {set busy_seen 1}
        if {$busy_seen && ($status & (1 << 31)) && !($status & (1 << 30))} {
            set completed 1
            break
        }
        after 1
    }
    echo [format {CC_TRANSACTION status=0x%08x busy_seen=%d completed=%d error=%d} $status $busy_seen $completed [expr {($status>>26)&15}]]
    if {!$completed} {error "Fresh CC transaction completion not observed"}
    if {($status >> 26) & 15} {error "CC read engine reported a failed transfer; no register bytes qualified"}
    for {set index 0} {$index < 11} {incr index} {
        # Retain the toggle: selecting a byte does not start another read.
        control [expr {($triggered & ~240) | ($index << 4)}]
        set value [expr {[rd 0x20010070] & 255}]
        echo [format {CC_REGISTER reg=0x%02x value=0x%02x} $index $value]
    }
    # Preserve trigger history; restore the other original PIO output bits.
    control [expr {($saved & ~((1 << 31) | 1792)) | ($triggered & (1 << 31))}]
    echo CC_PROBE_CAPTURE_COMPLETE
}
