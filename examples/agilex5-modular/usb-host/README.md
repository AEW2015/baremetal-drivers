# USB host inventory (Linux on the SoM)

This small Python 3 collector checks whether the SoM's Linux system sees the
USB devices in a connected topology: a USB 3 hub, a USB Ethernet interface, a
USB 2 mouse, and USB-backed storage. It reads device-tree identity and selected
sysfs attributes, emits one JSON capture, then a host-side assessor checks the
requested inventory criteria.

The capture is read-only. The collector does not mount or write the flash disk,
read file contents, configure network interfaces, or send network traffic. It
records the USB Ethernet interface's MAC address and current carrier/operstate
only. The separate Ethernet packet test is needed to establish traffic.

## Run on Agilex 5 Linux

Copy this directory to the board or run it from a checked-out repository. Python
3 is required on the board; the collector uses only the Python standard library.
It refuses to collect unless `/proc/device-tree/compatible` contains
`agilex5`, so a run from a host PC is rejected.

With the hub, NIC, mouse, and flash drive plugged in:

```sh
cd examples/agilex5-modular/usb-host
python3 collect.py > usb-inventory.json
python3 assess.py --input usb-inventory.json
```

Keep the JSON capture with the test record. It includes the USB topology chain
for each matched interface, event device, and whole-disk block device. It omits
USB serial numbers and disk contents. The Ethernet MAC is useful for identifying
the interface, so review/redact it before sharing a capture publicly.

The assessor reports `inventory_pass` only when all of these conditions hold:

- A USB hub device reports device class `09` and negotiated speed of at least
  5000 Mbps.
- A USB-backed network interface appears below that hub. Its MAC address,
  carrier, and operstate are recorded; link state alone is not packet evidence.
- An input device whose name contains “mouse” appears at a USB speed of at most
  480 Mbps and greater than zero. On a USB 3 hub the USB 2 device may appear on
  a different logical hub and bus, so ancestry alone does not prove it is
  behind the same physical hub. The collector reads Linux USB hub-port `peer`
  symlinks and only confirms the mouse when the kernel explicitly pairs its
  USB 2 hub with the enumerated USB 3 hub. The mouse link is identified; its
  movement is not tested. See the Linux kernel's [USB power management
  documentation](https://docs.kernel.org/driver-api/usb/power-management.html)
  for the `peer` port relationship.
- A non-partition USB-backed block device with nonzero capacity appears below
  the hub. Capacity is read from sysfs; no disk data is read. Check its USB
  product/manufacturer fields in the capture to confirm it is the intended
  flash drive; the assessor does not infer flash technology from a block node.

Exit status `0` means the requested inventory was observed and the USB 2/USB 3
hub pairing was confirmed. Exit status `1` means one or more required devices
or speed conditions were missing. Exit status `3` means the USB 2 mouse was
seen but the kernel exposed no matching port-peer relationship; the assessment
reports `topology_unconfirmed` and does not pass or fail the mouse's physical
association. Do not infer a match from similar bus/port numbers or VID/PID.
Exit status `2` means the collector rejected a non-Agilex 5 target, or the
assessor received an invalid capture. Even `inventory_pass` means enumeration
and read-only attributes only. It does not qualify Ethernet traffic, mouse
events, USB storage reads, or physical USB performance.

If the assessor reports a missing device, inspect the emitted JSON before
changing anything: confirm the device's parent chain, speed, and kernel-exposed
interface. A USB 2 mouse is expected to negotiate at 12 or 480 Mbps, while the
USB 3 hub itself must report at least 5000 Mbps. Older kernels may not expose
the port `peer` links needed to confirm companion topology; in that case the
collector preserves the observed device details and reports an unconfirmed
topology. It never guesses from port numbering or matching product IDs. The
collector does not modify USB, storage, or network configuration to make a
device appear.

## Offline tests

Run the assessor unit tests on a development host:

```sh
python3 -m unittest discover -s tests -v
```

These eight tests use synthetic in-memory fixtures and one temporary fake
sysfs tree for peer-link parsing. They exercise hub speed, explicit USB2/USB3
companion pairing, unconfirmed unrelated USB2 mice, downstream ancestry, the
board guard, and side-effect rejection. Fixture captures are always reported
as `fixture_not_hardware`; the tests cannot produce a hardware PASS. They do
not inspect the machine running the tests.
