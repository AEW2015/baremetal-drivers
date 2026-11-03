# WD25 reference test on the PC, 2026-11-03

This is a **PC reference test**, not an Agilex hardware pass. The user moved
the powered dock's upstream cable from the SOM to the PC for identification.
No board programming was involved in these PC checks.

The actual USB descriptor identifies **Dell Pro Dock WD25**, `413c:b0a2`.
The earlier user-reported name “DW26” was not used to guess a driver/model.
[`usb-devices.json`](usb-devices.json) records the newly enumerated subtree,
without USB serial-number fields. [`results.json`](results.json) summarizes
the separate observations below.

| Check | Result |
|---|---|
| Hub | Three Realtek USB3 hub devices at 5000 Mb/s, with USB2 companion hubs |
| Ethernet | Realtek `0bda:8156`, `r8152`, firmware `rtl8156b-2 v3 10/20/23` |
| Ethernet link | 1000 Mb/s full duplex; the adapter supports 2.5 Gb/s, but the connected switch advertised at most 1 Gb/s |
| Network | DHCP address observed; five pings bound to this USB NIC reached the private LAN gateway, zero loss |
| Flash | Lexar `21c4:0809`, 480 Mb/s; two matching 4096-byte direct reads through the dock |
| Mouse | Primax `0461:4d65`, `usbhid`, 1.5 Mb/s; no fresh reports received in a 45-second capture |

The Ethernet transcript is in [`ethernet-ping.log`](ethernet-ping.log). Its
MAC-derived host interface name is replaced by `USB_NIC`; other output is
unchanged. This was an interface-bound test (`ping -I`), not traffic that could
silently use Wi-Fi. Link rate and five small packets are not a bandwidth test.

The flash was verified as an unmounted, USB-backed Lexar whole-disk device.
The read process used `O_RDONLY | O_DIRECT` and a Docker device mapping with
read-only device permission. It neither changed the host block device's
read-only flag nor mounted or wrote the filesystem. The two SHA-256 values in
[`flash-read.json`](flash-read.json) match the earlier direct-SOM flash test.

The mouse node was matched to the dock's `USB Optical Mouse` path before its
read. [`mouse-reports.json`](mouse-reports.json) preserves the lack of fresh
reports; enumeration alone is not promoted to an input-transfer pass.

The PC test rules out a generally nonfunctional dock or missing PC class
drivers. It does not establish the SOM's Type-C role, prove USB-PD negotiation
mandatory, or identify the SOM failure's cause. Return the dock upstream cable
to the SOM for the next comparison. Do not relabel this PC capture as an
Agilex capture or bypass the board guard in `usb-host/collect.py`.
