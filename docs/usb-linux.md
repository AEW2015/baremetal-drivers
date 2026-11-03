# USB hub bring-up with U-Boot and Linux

The USB lab can now boot a source-built Linux kernel and BusyBox entirely in
HPS DDR. On the physical Modular ES kit, Linux enumerated a Lexar USB flash
drive at **480 Mb/s** and passed matching, read-only sector reads. This is a
Linux result, separate from the bare-metal and U-Boot-only examples.

The user subsequently confirmed that the flash drive was connected **directly
to the SOM** during these runs. Their missing-hub entries describe that topology;
they are not failed tests of a connected hub. The connected-hub retry below
is a separate result.

A subsequent retry **with the hub connection confirmed** reached Linux but
enumerated no external devices. Live xHCI reads returned `PORTSC=0x000002a0`
for both root ports: port power enabled in the controller, connection bit clear,
link state RxDetect, no overcurrent bit. This does not measure VBUS voltage or
identify the Type-C role. The hub model, power indication and connector-flip
check remain pending. See the
[connected-hub evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/usb-linux/validation/20261102/hub-connected).

| Check | Observed result |
|---|---|
| U-Boot and Linux boot | Passed on hardware; payload SHA-256 checked on the board |
| USB host controller | Both USB2 and SuperSpeed root buses created |
| Lexar flash | Enumerated; two matching 4096-byte reads, disk set read-only |
| External USB hub | Connected-hub retry enumerated no external devices; both root ports reported connection clear |
| Mouse reports | No mouse enumerated |
| USB Ethernet | No USB NIC enumerated |
| External SuperSpeed transfer | Not established; the flash negotiated 480 Mb/s |

The HPS Ethernet jack carries the boot files. That traffic does not establish
USB Ethernet connectivity. A root hub's advertised speed does not establish
the speed of an external device.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](assets/architecture/design.html?example=custom%2Fusb-host){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=custom%2Fusb-host" data-example-id="custom/usb-host">custom/usb-host</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=custom%2Fusb-host" title="HPS and fabric diagram for usb-linux.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Build and run

Use the normal [hardware configuration](hardware.md) and the
[Linux compiler container](container.md). From the repository root:

```sh
python3 lab.py hardware usb-linux --build --usb-peer 192.168.0.66
```

Replace the peer address with this PC's address reachable through the hub's
Ethernet switch. The PC's HPS-facing interface must already be configured;
the default boot link uses PC `192.168.50.1/24` and board `192.168.50.3`.
Override these using `--bind` and `--board-ip`. Omitting `--usb-peer` skips the
USB Ethernet ping rather than selecting a bench-specific PC address.

The runner owns the board mutex, captures UART, checks received payload hashes,
and restores DDR Hello afterward. No SD image, persistent U-Boot environment,
flash installation or filesystem write to the USB drive is involved. Linux
uses one CPU, 128 MiB of DDR and a RAM root filesystem for this exercise.

For the individual build/run commands, bounded live diagnostic queue, address
map and troubleshooting, see the
[source lab guide](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/usb-linux).

## Real terminal output

```text
[    0.673345] xhci-hcd xhci-hcd.0.auto: xHCI Host Controller
[    6.369499] scsi 0:0:0:0: Direct-Access     Lexar    USB Flash Drive       PQ: 0 ANSI: 4
[    6.379901] sd 0:0:0:0: [sda] 243404800 512-byte logical blocks: (125 GB/116 GiB)
USB_DEVICE name=1-1 vid=21c4 pid=0809 class=00 speed_mbps=480
5441cc368b9f34aad17b926eee05b0beba91501182cd5e7bc91f4eb2e0a3826c  /run/flash-a.bin
5441cc368b9f34aad17b926eee05b0beba91501182cd5e7bc91f4eb2e0a3826c  /run/flash-b.bin
USB_FLASH_READ_PASS device=sda bytes=4096 kernel_readonly=1
USB_LINUX#
```

The drive-specific checksum will differ for other media. This small read test
is a functional check; its `dd` timing is not a storage bandwidth benchmark.
The [hardware evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/usb-linux/validation/20261102)
includes both successful runs and the preserved console-harness failure.

## Lessons from bring-up

The pinned 26.3 kernel's Altera USB binding requires an Altera wrapper plus a
`snps,dwc3` child. The derived lab tree supplies that structure and validates
its string properties. The vendor U-Boot configuration also starts a
30-second watchdog by default; this RAM-only profile disables autostart because
its minimal Linux configuration does not service that watchdog.

The harness accepts a completed shell prompt even when an asynchronous SCSI
hotplug message follows it. An automated timeout without checking the full
UART capture can otherwise misclassify a working console.

Continue hub qualification by recording an external hub's VID/PID and speed,
then fresh mouse reports, flash reads through the hub, and a USB-backed NIC's
DHCP address and ping. The current flash result does not replace those checks.

## Powered laptop docks and USB-C roles

The attached unit was subsequently reported as a powered **Dell Pro Dock
“DW26”**, with its top button unlit. The exact bottom-label model and USB IDs
still need confirmation; do not silently substitute a WD25 or Thunderbolt model.

There is a plausible role-negotiation compatibility issue. The SOM schematic
identifies an HD3SS3220 Type-C controller. TI states that this device cannot
exchange USB Power Delivery messages and needs additional USB-PD functionality
for split power/data roles, such as a USB host that consumes power. A laptop dock
that supplies power while acting as a USB peripheral can require that split.
See [TI's datasheet, sections 6.1.1 and 7.1](https://www.ti.com/lit/ds/symlink/hd3ss3220.pdf)
and [TI's CC-versus-PD application note](https://www.ti.com/lit/an/slaae24/slaae24.pdf).

This is a **hypothesis**, not a measured role or a confirmed incompatibility of
this dock. Neither xHCI `PORTSC` nor the top-button light establishes its CC
role. Next, enumerate the dock on the PC, identify its actual hub/NIC, and check
the exact model's upstream requirements. A negative PC test also needs its host
capabilities checked; an ordinary desktop USB-C port is not automatically a
PD/Thunderbolt/DisplayPort-capable laptop port. Keep video support separate
from the USB storage, HID and Ethernet checks.
