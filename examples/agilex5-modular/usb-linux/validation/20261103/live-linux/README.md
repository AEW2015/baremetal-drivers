# Live Linux and PHY diagnostic, 2026-11-03

This run booted the pinned Linux lab on the Modular ES SOM and deliberately
left it running with `--leave-linux-running`. The dock was still enumerated
on the PC at the time of these captures. Zero external devices on the SOM is
therefore an **unattached baseline**, not a new connected-dock failure.

[`results.json`](results.json) records checked boot payloads, exact runner and
Tcl source hashes, the completed diagnostic batch and `final_state` of
`linux-running`. Its overall USB verdict is partial. The UART and hardware
mutex were released; DDR Hello restoration was intentionally skipped by the
explicit option after Linux remained responsive.

## PHY viewport reads

**Decoder erratum:** the original JSON's derived `id_grounded_sample` field
has reversed polarity. Raw register captures are unchanged. See the
[correction and qualified follow-up](../dock-reattached/README.md#decoder-erratum).

[`linux-phy-status.log`](linux-phy-status.log) records the actual host-side Tcl
probe under the hardware mutex. OpenOCD initialized the memory AP without
halting or resetting the Linux CPU. The source writes only ULPI **read request**
words to DWC3's viewport, with the PHY WRITE bit clear. It refuses an existing
busy request and bounds each read to 100 polls. It excludes clear-on-read
latches and changes no PHY configuration.

```text
USB_PHY_CONFIG GSNPSID=0x33313130 GUSB2PHYCFG=0x00102510
USB_PHY_REGISTER reg=0x00 value=0x24 viewport=0x01000024
USB_PHY_REGISTER reg=0x01 value=0x04 viewport=0x01010004
USB_PHY_REGISTER reg=0x02 value=0x07 viewport=0x01020007
USB_PHY_REGISTER reg=0x03 value=0x00 viewport=0x01030000
USB_PHY_REGISTER reg=0x0a value=0x27 viewport=0x010a0027
USB_PHY_REGISTER reg=0x13 value=0x14 viewport=0x01130014
USB_PHY_STATUS_COMPLETE
```

The ID is the expected USB3320 `0424:0007`. The remaining values are local
OTG control and live PHY input indications. They are neither a measurement of
connector voltage nor a capture of the separate HD3SS3220 CC role or USB-PD
messages. They do not by themselves establish the cause of the WD25 failure.

## Attach without another boot

[`console-report/`](console-report) records a separate invocation of
`usb-linux/console.py report` after the batch had exited. It reacquired the
shared mutex, verified an Agilex device-tree identity, captured the inventory
and released UART. It did not reboot or program the board. A successful
inventory command with zero devices is a console-command pass, not a hub pass.
The later [uptime query](console-uptime/diagnostic-uart.txt) returned 404.53
seconds, confirming that Linux stayed responsive across separate console
attachments for more than six minutes.

This workflow leaves the OS ready for the user's cable move, avoiding a reset
between a request to reconnect the dock and the next observation. A subsequent
board operator can still replace Linux under the shared hardware mutex.
