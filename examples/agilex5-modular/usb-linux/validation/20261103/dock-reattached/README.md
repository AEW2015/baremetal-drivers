# WD25 reattached to SOM, 2026-11-03

The user confirmed the dock was moved from the PC to the SOM and the optical
mouse was being moved. No reboot occurred. Linux remained responsive.

- `console-report/diagnostic-uart.txt`: actual Linux inventory, zero external
  devices and hubs. Its command status zero is not a successful dock test.
- `registers.log`: fresh JTAG memory-AP reads without CPU halt/reset, under
  the shared hardware mutex. Both xHCI PORTSC registers are `0x2a0`.
- `chain.json`: fresh Modular ES JTAG identity check.
- `phy-status.json`: corrected version-2 decode and exact Tcl source hash.

The USB3320 identity is `0424:0007`; OTG control is `0x27`, rising/falling
interrupt-enable masks are both `0x1f`, and live status is `0x14`. This means
the pulled-up local ID sample is floating and the enabled internal VBUS
comparator reports not valid. It does not establish the separate HD3SS3220
CC role, PD negotiation, connector voltage or the cause of failed attachment.
No hub, mouse, storage or NIC transaction through the dock is qualified on SOM.

## Decoder erratum

Earlier committed `live-linux/results.json` derived field
`phy_status.id_grounded_sample` has its polarity reversed. The raw register
capture is preserved and valid. USB3320 section 5.6.1.1 defines bit 4 of status
`0x13` as zero for grounded ID and one for floating ID. The earlier `0x14`
sample therefore indicates floating with the pull-up enabled, not grounded.
Earlier captures did not include the interrupt-enable masks, so a VBUS-valid
zero in those captures was not qualified against comparator-disable state.

The new decoder requires both masks, qualifies the internal VBUS comparator,
and returns null for ID when the pull-up is disabled. Regression tests cover
both ID polarities, comparator disable, external selection, busy requests and
bounded read timeout. Reference:
[USB3320 datasheet, sections 5.6.1.1 and 5.6.2.3](https://ww1.microchip.com/downloads/en/DeviceDoc/00001792E.pdf).
