# Repeatable direct CC capture, mode experiment ready

The corrected FPGA reader explicitly sets the HD3SS3220 pointer to register
zero, then issues repeated START and an 11-byte read. Three successive
hardware captures passed identity validation and returned the same values:

```text
CC_INPUTS before=0x03ec80cc fault_n=1 vbus_det=1 id=1 scl=1 sda=1
CC_TRANSACTION status=0x83fc80cc busy_seen=1 completed=1 error=0
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

This excerpt is from `capture-1/capture.log`; captures 2/3 are separate fresh
transactions. Accepted-toggle/status fields differ between transactions as
expected. All three verified the identity and **UFP/sink** attach state.
They confirm repeatable reads, replacing the
[initial prototype's rejected repeat](../direct-cc-first-capture/README.md).

## Image and Linux qualification

The matching Modular ES image compiled with Quartus 26.3 and was paired with
the already source-built, hardware-verified BL2 firmware with LWH2F enabled.
The new full image passed all four 64-MiB DDR patterns, payload readback,
three fresh Hello messages and PC verification before Linux was RAM-booted.
`boot-manifest.json` records both image and reused BL2 provenance hashes.

Final timing has nonnegative reported slack, zero unconstrained paths, no
unmatched constraints and **0 of 88 Design Assistant rules failed**. The
timing-only correction added explicit external-delay/source-latency declarations
and retained first-stage asynchronous exceptions; fitted logic was unchanged.
The initial timing report remains on the bench. `fpga/` includes the final
reports and fitted BR28/BR31 pin rows. `evidence.json` records source/image
hashes and job IDs; the maintained RTL matches the compiled source exactly.

Linux stayed responsive. Its final inventory still reports
`external_devices=0 external_hubs=0`. No WD25 USB storage, HID or NIC traffic
was qualified. A CC-status pass is separate from a USB-device test.

## Attached-peer guard was tested; mode writes were not

The explicit variant supports only the documented volatile General Control
values. A hardware `configure.py --mode dfp --check-only` preflight obtained
a fresh valid identity/status capture, then refused the attached peer:

```text
RuntimeError: Unplug the dock first: CC reports UFP/sink
```

`attached-preflight/results.json` records `check_only=true`, an empty
`operations` list, and no mode write submitted. General Control remained
`0x00`. The positive mode-write sequence is RTL-simulated, **not hardware
executed** in this record.

The diagnostic image and Linux remain running with UART and mutex released.
The pending physical step is to unplug the dock's upstream cable from the SOM,
leave the dock powered, then verify fresh unattached status before selecting
DFP. Actual reconnection, enumeration and class traffic tests follow that
configuration; they must have their own evidence.
