# Physical Linux USB validation, 2026-11-02

Target: Agilex 5 Modular ES, FPGA JTAG ID `0x0364f0dd`, carrier cable selected
from a fresh Programmer MCP chain. Host SOM J2 UART was captured at 115200.
Each operation held the canonical shared hardware mutex; each completed run
restored full DDR Hello and its DDR guard checks.

## First successful flash test

[`first-flash/results.json`](first-flash/results.json) records the manifest,
payload hashes, boot transport, individual checks and restoration. The overall
verdict is **partial**, because the captured tree contains one Lexar storage
device and no external hub, mouse or USB NIC.

After these runs, the user confirmed the Lexar was plugged directly into the
SOM. The zero-hub inventory therefore matches the physical connection. These
captures establish direct flash access; they do not represent a failed attempt
to enumerate an attached hub. Hub testing remains pending reconnection.

- HPS EMAC2 ping and TFTP passed; U-Boot checked all three Linux payload SHA-256 values.
- Linux 6.18.37 started both USB host buses and reached its RAM shell.
- VID:PID `21c4:0809` enumerated at 480 Mb/s as a 125 GB Lexar drive.
- [`linux-flash-read-uart.txt`](first-flash/linux-flash-read-uart.txt) records matching 4096-byte reads and kernel read-only state.
- [`queued-3-uptime-uart.txt`](first-flash/queued-3-uptime-uart.txt) confirms a responsive console beyond 72 seconds; the earlier 30-second watchdog autostart was disabled.
- [`queued-4-drivers-uart.txt`](first-flash/queued-4-drivers-uart.txt) confirms the Altera wrapper and DWC3 core bound to their separate driver nodes.
- DDR Hello restoration passed. No storage, saved environment or board NVM was written.

The command paths and network addresses in the captures identify this bench;
use the relative commands and configurable addresses in the lab README for
another installation. Root-hub speed is not an external SuperSpeed result.
The short `dd` timing is not a sustained bandwidth measurement.

## Preserved harness failure

[`console-hotplug-timeout/results.json`](console-hotplug-timeout/results.json)
retains the previous failed verdict. Linux and the flash drive had actually
started, but SCSI hotplug messages followed `USB_LINUX#` before the UART became
quiet. The original completion regex required the prompt at the very end of
the capture and timed out. The raw report shows the prompt and later SCSI
messages. The runner now accepts a line-start prompt followed by asynchronous
logs, with a regression test. That fix does not rewrite the older verdict.

Initial firmware and kernel setup failures remain in the ignored `runs/`
directories on the bench. This selected export is not a claim that every
bring-up attempt passed.

## Public build-script rerun

[`source-build/results.json`](source-build/results.json) records a second
successful Linux boot and flash-read test using the final bundle produced by
`bash usb-linux/build.sh`. It contains the kernel/firmware pins, build-input
hashes and the exact runner/TFTP source hashes. Its responsive-console check
reached 54 seconds. Both flash comparisons passed and DDR Hello restoration
passed. Overall status remains **partial**: no external hub, mouse or USB NIC
was enumerated. This rerun does not turn absent devices into passing results.

## Retry after the user connected the hub

[`hub-connected/results.json`](hub-connected/results.json) is a separate
physical run after the user confirmed the hub, mouse, flash drive and Ethernet
were attached. Linux boot and payload hashes passed, but the inventory found
**zero external devices**. Overall status is partial; hub enumeration failed
and no downstream class transaction passed. DDR Hello restoration passed.

The extra [live xHCI read](hub-connected/live-port-registers.log) used the
memory AP without halting Linux. Our idle console orchestrator was briefly
stopped to serialize access while it retained the canonical hardware lock,
then resumed. The post-read console [uptime](hub-connected/queued-9-uptime-uart.txt)
was 495 seconds. No reset or USB register write was made by this diagnostic.

The [decoded register snapshot](hub-connected/port-status.json) records two
root ports, each with `PORTSC=0x000002a0`: connection clear, controller port
power enabled, RxDetect, no overcurrent flag. Definitions were checked against
the pinned kernel's
[xhci-port.h](https://github.com/altera-fpga/linux-socfpga/blob/0c0e456cdde08783d0a56ef593af45899f5d11af/drivers/usb/host/xhci-port.h).
These bits do not measure VBUS voltage or reveal the separate Type-C
controller's role. They locate the observed failure before class enumeration.

The SOM schematic, sheet 41 (150-0330723-B1 rev 2.1), identifies an HD3SS3220
Type-C controller/mux and a VBUS load switch. Its attachment/role status is
separate from xHCI; see [TI's controller datasheet](https://www.ti.com/lit/ds/symlink/hd3ss3220.pdf).
Hub make/model, power indication and the requested USB-C connector-flip result
remain pending. No specific component or cable has been identified as faulty.
