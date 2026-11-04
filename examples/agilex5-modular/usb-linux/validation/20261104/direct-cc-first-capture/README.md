# Direct HD3SS3220 capture: SOM attached as UFP/sink

The first isolated read-only FPGA diagnostic was built with Quartus 26.3,
paired with source-built matching BL2 firmware with LWH2F enabled, and loaded
under the hardware mutex. The fresh DDR bootstrap passed four 64-MiB patterns,
payload readback, DDR execution and PC verification. Linux was then RAM-booted
and left running. The WD25 remained attached per the last user confirmation.

The FPGA directly accessed the **clock/USB-mux I2C bus** at BR28/BR31, rather
than the previously tested HPS management GPIO route. Actual capture:

```text
CC_INPUTS before=0x03ec00cc fault_n=1 vbus_det=1 id=1 scl=1 sda=1
CC_TRANSACTION status=0x83ec00cc busy_seen=1 completed=1 error=0
CC_REGISTER reg=0x00 value=0x32
CC_REGISTER reg=0x01 value=0x32
CC_REGISTER reg=0x02 value=0x33
CC_REGISTER reg=0x03 value=0x42
CC_REGISTER reg=0x04 value=0x53
CC_REGISTER reg=0x05 value=0x55
CC_REGISTER reg=0x06 value=0x54
CC_REGISTER reg=0x07 value=0x00
CC_REGISTER reg=0x08 value=0x30
CC_REGISTER reg=0x09 value=0x90
CC_REGISTER reg=0x0a value=0x00
CC_PROBE_CAPTURE_COMPLETE
```

The expected identity bytes matched. Register `0x09` bits 7:6 are `2`, meaning
**UFP/sink**, while the Linux HPS USB controller was configured as host.
Register `0x0a=0x00` selects the PORT-pin default. This is a measured role
mismatch; it does not establish that this is the only problem or that the
WD25 cannot attach when the SOM is configured as DFP. No USB hub/device
enumerated in this run. Neither CC indications nor VBUS-detector logic
constitute a connector-voltage measurement or a PD-message capture.

See [TI HD3SS3220 sections 6.6.3 and 6.6.4](https://www.ti.com/lit/ds/symlink/hd3ss3220.pdf).
The documented DFP-mode experiment requires an unattached connector and is
separate from this read-only capture.

## Preserve the prototype's repeat failure

This first prototype sent a direct address-read byte without explicitly
setting the register pointer. Its first capture was valid, but a later
capture returned zeros and was **rejected by the identity guard**. Those logs
and the failed result are preserved in `repeat-rejected/`. They establish
no subsequent attach state. `rtl-at-capture.sv` is the exact initial hardware
source, not the maintained replacement.

The replacement reader uses an explicit pointer-zero write followed by
repeated START and an 11-byte read. Its slave model retains an initially
nonzero pointer and tests successive captures. A mode-capable variant also
has a strict allowlist for volatile register `0x0a`; that is not a capability
of the read-only prototype recorded here. Hardware qualification of the
replacement belongs in separate evidence.

`evidence.json`, `fpga-inputs.json` and `boot-manifest.json` identify the
source/image inputs. The final timing run corrected the removed DIP-switch
constraint and the asynchronous USB-status input exceptions; fitted logic was
unchanged. Its reports show no unmatched constraints, zero unconstrained
paths and nonnegative slack. The original timing attempt remains on the bench.
