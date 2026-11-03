# USB3320 register reads through DWC3's ULPI viewport, with Linux still running.
# The viewport is written to request reads; PHY configuration is never written.
# Register 0x13 is live status. Do not substitute the read-to-clear latch 0x14.
# Caller owns the hardware mutex, verifies the board and initializes OpenOCD.
namespace eval usb_lab_phy {
    proc read32 {address} {
        return [lindex [hps.sys_bus read_memory $address 32 1] 0]
    }
    proc snapshot {} {
        set identity [read32 0x1100c120]
        set config [read32 0x1100c200]
        set parameters [read32 0x1100c14c]
        if {($identity >> 16) != 0x3331} {
            error "USB PHY diagnostic: unexpected DWC3 controller"
        }
        if {!($config & 0x10) || (($parameters >> 2) & 3) < 2} {
            error "USB PHY diagnostic: controller is not configured for ULPI"
        }
        echo [format {USB_PHY_CONFIG GSNPSID=0x%08x GUSB2PHYCFG=0x%08x} $identity $config]
        foreach address {0 1 2 3 10 19} {
            # Let an already-enabled ID pull-up settle before the live sample.
            if {$address == 19} {after 50}
            set before [read32 0x1100c280]
            if {($before & (1 << 23)) || (($before & (1 << 25)) && !($before & (1 << 24)))} {
                error "USB PHY diagnostic: outstanding viewport request; not replaced"
            }
            # NEWREQ and address only. WRITE (bit 22) stays zero.
            set request [expr {(1 << 25) | ($address << 16)}]
            hps.sys_bus write_memory 0x1100c280 32 [list $request]
            set complete 0
            for {set poll 0} {$poll < 100} {incr poll} {
                after 1
                set status [read32 0x1100c280]
                if {($status & (1 << 24)) && !($status & (1 << 23))} {
                    set complete 1
                    break
                }
            }
            if {!$complete} {error "USB PHY diagnostic: bounded read timeout"}
            echo [format {USB_PHY_REGISTER reg=0x%02x value=0x%02x viewport=0x%08x} $address [expr {$status & 255}] $status]
        }
        echo USB_PHY_STATUS_COMPLETE
    }
    snapshot
}
