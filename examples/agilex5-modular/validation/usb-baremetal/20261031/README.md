# USB bare-metal follow-up evidence

Run-directory timestamps are UTC (these tests occurred on October 30 in the
bench's local Mountain time zone). These captures come from the physical
Agilex 5 Modular ES board; no OS was booted.

| Capture | Observed result |
|---|---|
| `usb-uboot-20261031T020301.134353Z` | Both PLL lock bits set; USB31 counter reset clear; divider matches handoff. CNR remains set. |
| `usb-uboot-20261031T020612.343236Z` | First USB3320 ULPI ID read times out, viewport `02800000`; no VID/PID obtained. |
| `usb-reset-20261031T021157.846665Z` | Memory-AP-only read: PIN10SEL=8, GPIO0 direction=0, input bit10 high. |
| `usb-uboot-20261031T021228.871394Z` | Opt-in U-Boot SPL-compatible reset-pulse bit12 experiment; bit set, same CNR and ULPI timeouts. |

All three U-Boot sessions restored DDR Hello successfully. The normal monitor
keeps the TF-A bit12 default; the failed experiment uses a separate image.
No hub, mouse, storage or USB-Ethernet traffic has passed. Neither the register
configuration nor PHY timeout establishes a physical clock frequency or a
specific faulty component.

Earlier `usb-reset-*` attempts are retained: one produced no captured register
values, and two failed due to vendor launcher argument expansion. Their
`complete=false` results are not hardware findings. The final snapshot passes
Tcl through a file, explicitly prints all four values and requires all of them.

The next requested experiment is a full board power cycle with the hub left
attached, followed by a fresh default-monitor run. This checks cold PHY state;
it is not a claimed fix. No board operations remain running while waiting.

See [USB bring-up instructions](../../../usb-bringup/README.md).
