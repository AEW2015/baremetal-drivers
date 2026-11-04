# DFP mode configured after clearing host-powered attachment

The user confirmed that the WD25 upstream cable was unplugged from the SOM,
with dock power retained. The first guarded configuration attempt correctly
refused to write: the controller still reported UFP/sink (`0x09=0x90`), even
though current-mode detection had dropped from `0x30` to `0x00`. The SOM VBUS
detector remained high. See `unplugged-power-still-on/`; its operation list is
empty.

The Linux kernel's root-port `disable` attribute invokes its normal hub port
power API. Disabling both USB3 and USB2 root ports returned `1/1` readback.
A new CC capture then reported **unattached**, with the SOM VBUS detector low:

```text
CC_INPUTS before=0x82fc80cc fault_n=1 vbus_det=0 id=1 scl=1 sda=1
CC_REGISTER reg=0x08 value=0x00
CC_REGISTER reg=0x09 value=0x30
CC_REGISTER reg=0x0a value=0x00
```

This supports host port power preventing recognition of detachment in the
observed sink state. The detector is a logic indication, not a measured voltage.
TI section 6.3.11 describes VBUS detection as part of UFP attach/detach.

## Positive mode-write hardware result

With the cable unplugged and fresh unattached status verified, the guarded
tool completed TI's sequence and independently read back each value:

| Operation | General Control readback | Result |
|---|---|---|
| Disable termination, retain default mode | `0x01` | Verified |
| Select DFP while termination disabled | `0x21` | Verified |
| Re-enable termination in DFP mode | `0x20` | Verified |

`dfp-mode-sequence/` contains every submitted Tcl operation, fresh chain check,
write completion, separate identity/status readback and result JSON. The final
state was `configured_mode=DFP/source`, `attached_state=unattached`. A later
fresh read in `waiting-dfp-read/` confirmed it persisted. No I2C soft reset,
shared board reset, clock configuration, storage or NVM write was used.

The original-default restore value `0x00` is RTL-simulated but was not hardware
exercised in this record. The initial guard failure and all partial-stage
readbacks are retained.

## Pending dock reconnect

Linux and the diagnostic image remain running. Both root ports are deliberately
disabled (`ports-status/`, `guarded-ports-off/`) while waiting for the powered
dock to reconnect. The maintained console harness now provides `ports`,
`ports-off` and `ports-on`: power-off refuses external devices, and power-on
first requires a fresh verified **DFP/source attachment** under the same bench
mutex. An unattached or UFP/sink result cannot enable port power through that
entry point.

No reconnected-dock enumeration, flash read, mouse report or USB Ethernet
transaction is qualified by this mode-configuration record. Those are the next
tests after actual CC attachment and guarded host-port power-on.

References: [TI HD3SS3220 sections 6.3.1, 6.3.11 and 6.6.4](https://www.ti.com/lit/ds/symlink/hd3ss3220.pdf),
[pinned Linux port-power implementation](https://github.com/altera-fpga/linux-socfpga/blob/0c0e456cdde08783d0a56ef593af45899f5d11af/drivers/usb/core/port.c#L102).
