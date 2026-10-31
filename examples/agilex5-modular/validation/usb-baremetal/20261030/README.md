# Physical USB bare-metal investigation, 2026-10-30

These are captured executions on the Agilex 5 Modular ES SOM with the hub
attached to its HPS USB Type-C connector. No operating system was booted.

| Run suffix | Experiment | Observed result |
|---|---|---|
| 233940.762675Z | Source-built U-Boot, FDT DDR fallback | U-Boot prompt, 128 MiB DDR; USB probe -110 |
| 234638.318952Z | Stage/register logging | Halt and HCRST return 0; CNR remains set, -110 |
| 235008.147778Z | Clear USB3 suspend bit | Bit clears; same CNR failure |
| 235620.021010Z | Restore normal vendor PIPE-power-present initialization | System-manager bit14 sets; same CNR failure |

All four sessions restored the established DDR Hello program successfully.
`results.json` records the actual loaded firmware hashes and restoration status;
console files preserve UART bytes. No hub enumeration, mouse events, flash
reads or USB-Ethernet traffic passed. An empty USB tree does not identify a
faulty external device. Hardware failure is at controller initialization.

The firmware recipes and interpretation are in
[usb-bringup/README.md](../../../usb-bringup/README.md).
