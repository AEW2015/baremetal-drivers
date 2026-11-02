# USB hub lab: U-Boot to Linux in HPS DDR

This lab builds a small Linux kernel and a static BusyBox initramfs, loads them
through U-Boot, and tests the SOM's USB3 host port. It uses the existing matched
Modular ES FPGA image and HPS DDR bootstrap. The root filesystem lives in RAM.
It does not install Linux on SD, flash or eMMC.

The HPS Ethernet jack supplies the boot transport. USB Ethernet is tested
separately, through the attached hub. Successful TFTP is not a USB network test.

On 2026-11-02 this lab booted Linux on the physical Modular ES kit, enumerated a
Lexar flash drive at 480 Mb/s, and passed the read-only sector comparison.
External hub enumeration, mouse reports, USB Ethernet and external SuperSpeed
operation are still separate checks; root-hub speed is not an attached-device
speed measurement.
See the [hardware evidence and preserved failure](validation/20261102/README.md).
The user confirmed that the flash drive was directly attached to the SOM for
those runs. They qualify direct USB storage, not storage through a hub.

## Build

Use the Linux compiler environment described in [container setup](../../../docs/container.md).
From `examples/agilex5-modular`:

```sh
bash usb-linux/build.sh
```

Requirements include `aarch64-linux-gnu-gcc`, its static C library, GNU make,
bc, bison, flex, OpenSSL development headers, Python 3, git, curl, bzip2 and
the device-tree compiler tools. Builds use four jobs by default; set
`USB_LINUX_JOBS` for the available RAM. First use downloads pinned sources.

The kernel is Altera's 26.3 baseline, commit
`0c0e456cdde08783d0a56ef593af45899f5d11af` (Linux 6.18.37). BusyBox 1.37.0's
archive is checked against its recorded SHA-256. U-Boot and TF-A use the repo's
26.3 pins. The USB, storage, HID and supported USB network drivers are built in.
There are no runtime module downloads.

Outputs are in `build/usb-linux/`. `bundle/build.json` records payload sizes,
addresses and hashes. `prepare.py` creates the initramfs, including device
nodes, without root privileges. It also derives a USB-only device tree from
the vendor Modular A0 board tree. Storage controllers and unrelated FPGA
devices are disabled for this lab.

## Run on the board

Configure the normal [hardware environment](../../../docs/hardware.md) first. Hardware
automation runs on the Linux host, using the shared hardware lock. Connect the
hub's upstream cable to the SOM HPS USB Type-C port, attach the mouse and flash
drive, and connect its Ethernet jack to a DHCP-enabled test switch.

The following example assumes the PC's HPS-facing NIC already has
`192.168.50.1/24`. Replace `192.168.0.66` with this PC's address reachable from
the hub's Ethernet network:

```sh
python3 usb-linux/run.py --port "$AGILEX_UART" \
  --bind 192.168.50.1 --board-ip 192.168.50.3 \
  --usb-peer 192.168.0.66
```

The runner bootstraps DDR, loads and reads back U-Boot and BL31, starts a
restricted TFTP server on UDP port 1069, and verifies each received payload's
SHA-256 on the board before `booti`. If the HPS Ethernet ping fails it falls
back to checked JTAG loads. `--transport jtag` selects that slower path directly.
It captures the Linux console and restores DDR Hello before releasing the lock.
Do not run a second serial terminal or debugger during this operation.

From the repository root, the configured portable launcher also supports:

```sh
python3 lab.py hardware usb-linux --build --usb-peer 192.168.0.66
```

## What constitutes a result

| Check | Required evidence |
|---|---|
| Linux boot | `USB_LINUX_READY` and a responsive `USB_LINUX#` prompt |
| External hub | A non-root USB device of class `09`; record its negotiated speed |
| Flash | `USB_FLASH_READ_PASS`: two matching 4096-byte reads from a USB-backed disk, with the kernel block device set read-only |
| Mouse | Fresh bytes between `USB_MOUSE_BYTES_BEGIN` and `USB_MOUSE_BYTES_END`; move the mouse during the 12-second capture |
| USB Ethernet | USB-backed NIC path, DHCP address, and `USB_ETH_PING_PASS` to the specified PC |

Root hubs do not count as external devices. Enumeration does not establish
storage transfers, mouse reports, Ethernet traffic or bandwidth. The flash
check reads raw sectors into tmpfs; it neither mounts nor modifies the drive.
The network test changes only the RAM-booted board's interface configuration.
These class checks also do not prove USB2/USB3 companion-hub association. The
separate [full Linux inventory collector](../usb-host/README.md) checks the
kernel's explicit port-peer links; it requires Python 3 on the board, which
this minimal BusyBox initramfs does not include.

For repeated diagnostics, create an empty JSON list and supply a bounded queue:

```sh
python3 -c "from pathlib import Path; Path('build/usb-linux/queue.json').write_text('[]')"
python3 usb-linux/run.py --port "$AGILEX_UART" --usb-peer 192.168.0.66 \
  --queue build/usb-linux/queue.json --hold-seconds 600
```

While the runner reports `USB_LINUX_COMMAND_QUEUE_READY`, append reviewed names
to that JSON list: `report`, `drivers`, `dmesg`, `uptime`, `flash`, `mouse`,
`network`, `usb-network`. Append `done` to restore DDR Hello immediately.
Preserve earlier entries; the queue is append-only. Evidence is written under
`runs/usb-linux-<UTC timestamp>/`, including failures and restoration status.

## Boot profile and troubleshooting

This intentionally small profile uses one CPU and 128 MiB of HPS DDR. Its
address plan is not a general-purpose Linux distribution's memory map:

| Payload | Physical load address |
|---|---|
| Secure BL31 | `0x80000000` |
| U-Boot BL33 | `0x80200000` |
| Linux device tree | `0x81f00000` |
| Linux Image | `0x82000000` |
| Initramfs | `0x86000000` |

The vendor device tree reserves the first 32 MiB as a no-map service buffer,
which also protects resident BL31. Preparation checks that reservation before
packaging the bundle. Linux's general allocator starts above it.

U-Boot autoboot and persistent environment backends are disabled. Watchdog
autostart is also disabled: the minimal Linux profile does not service the
watchdog that the vendor U-Boot defconfig otherwise starts with a 30-second
timeout. A successful prompt followed by an unresponsive console after about
30 seconds was observed with that older configuration.

If Linux boots without a USB host, check driver binding and the device tree
before changing board resets. `status`, `compatible` and `dr_mode` must be
NUL-terminated strings; `prepare.py` validates them with `fdtget`. This pinned
kernel's `intel,socfpga-dwc3.yaml` binding requires an Altera wrapper with a
`snps,dwc3` child. The derived tree supplies that topology.

If only root hubs appear, inspect power, cable roles and controller/PHY logs.
Do not infer external enumeration from the USB3320 ID or an xHCI banner.
The SOM's shared reset also affects UART and other devices; this lab does not
pulse that reset. Keep unsuccessful attempts as evidence.

Offline checks:

```sh
python3 -m unittest discover -s usb-linux/tests -v
```

Observed flash output (the checksum depends on your media):

```text
[    6.369499] scsi 0:0:0:0: Direct-Access     Lexar    USB Flash Drive       PQ: 0 ANSI: 4
[    6.379901] sd 0:0:0:0: [sda] 243404800 512-byte logical blocks: (125 GB/116 GiB)
USB_DEVICE name=1-1 vid=21c4 pid=0809 class=00 speed_mbps=480
5441cc368b9f34aad17b926eee05b0beba91501182cd5e7bc91f4eb2e0a3826c  /run/flash-a.bin
5441cc368b9f34aad17b926eee05b0beba91501182cd5e7bc91f4eb2e0a3826c  /run/flash-b.bin
USB_FLASH_READ_PASS device=sda bytes=4096 kernel_readonly=1
USB_LINUX#
```

Driver references: [Altera Linux source](https://github.com/altera-fpga/linux-socfpga/tree/0c0e456cdde08783d0a56ef593af45899f5d11af)
and [Altera USB3.1 driver guide](https://altera-fpga.github.io/rel-25.1.1/linux-embedded/drivers/usb3_1/usb3_1/).
