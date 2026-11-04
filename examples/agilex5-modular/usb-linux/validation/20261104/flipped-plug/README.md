# WD25: opposite Type-C orientation

2026-11-04 UTC. The user confirmed unplugging the dock from the SOM, rotating
its host plug 180 degrees and reconnecting it with dock power retained.
Linux stayed running throughout.

| Observation | First orientation | Flipped orientation |
|---|---|---|
| External USB devices / hubs | 0 / 0 | 0 / 0 |
| USB2 / USB3 PORTSC | `0x2a0` / `0x2a0` | `0x2a0` / `0x2a0` |
| USB3320 OTG control | `0x27` | `0x27` |
| Rising / falling enable masks | `0x1f` / `0x1f` | `0x1f` / `0x1f` |
| Live PHY status | `0x14` | `0x14` |

The first-orientation evidence is in
[`../../20261103/dock-reattached/`](../../20261103/dock-reattached/README.md).
The local ID sample remains floating with pull-up enabled; the enabled
internal VBUS comparator remains not valid. Neither orientation produced a
device connection or descriptor. This does not establish the separate
HD3SS3220 CC state or a specific electrical fault.

`console-report/` and `kernel-log/` contain the actual Linux UART captures.
`registers.log` and `phy-status.json` contain the bounded memory-AP/ULPI reads
and version-2 decode. `final-report/` confirms Linux remained responsive with
zero external devices after the diagnostic work below. No mouse reports,
flash transactions or USB Ethernet traffic through this dock were qualified.

## Targeted management-route experiment

The matched SOM sheet 7 separates HPS management I2C from the clock/USB-mux
I2C bus on FPGA BR28/BR31. The carrier also connects BMC level translators to
these buses; their existence alone does not establish a working HPS route.

`gpio-route/probe.c` is the exact HPS-side diagnostic prototype. It uses
Linux GPIO v2 open-drain requests for GPIO0 lines 8/9 and two fixed
register-pointer/read transactions. A fresh chip identity check requires
`10c03200.gpio` with 24 lines. Under the shared hardware mutex, JTAG temporarily
selects the previously validated GPIO mux value 8 for IOA9/10, then restores
the original 4/4 selectors. The original selectors and released GPIO
directions are checked before selection. No target data register is written.

Actual output:

```text
GPIO_CHIP name=gpiochip0 label=10c03200.gpio lines=24
I2C_READ address=0x48 pointer=0xfe bytes=54 49
I2C_NACK address=0x47 stage=address
CC_CONTROLLER_NOT_REACHED_ON_THIS_ROUTE

USB_CONSOLE_STATUS=2
```

The valid TMP464 manufacturer ID is a positive control for the transaction
timing. The HD3SS3220 address did not acknowledge on this route. Its registers
were **not read**; an address NACK does not prove the chip is absent, broken,
disabled, or in a particular Type-C role.

`gpio-route/metadata.json` records the source/ELF hashes, pinned Linux nolibc
header source and compiler command. The executable was uploaded into `/tmp`
in the RAM filesystem; no executable binary is published here. The paired Tcl
files/logs show selection and restoration. Treat this as experiment evidence,
not a standalone operator command: it depends on the matching board, GPIO
ownership, pinmux guards, UART session and hardware mutex.

Two earlier timing attempts were rejected as invalid controls: JTAG-driven
GPIO reads returned `7f ff` for the TMP464 ID; a Linux prototype using
`usleep(10)` received a pointer NACK. The minimal kernel has
`CONFIG_HZ=250` and no `CONFIG_HIGH_RES_TIMERS`, so a short requested sleep is
unsuitable for these I2C edges. The recorded working control uses a monotonic
clock busy wait. Neither rejected attempt supports a CC-controller verdict.

## Carrier service discovery

`services/services.log` records service enumeration only. The carrier exposes
a VTAP10 JTAG master, but its address map and transfer protocol have not been
qualified for this read. No BMC register was read or written. The FPGA BTS
I2C core addresses must not be assumed to be the BMC's register map.

The dock works on the PC, but its SOM attach failure remains unresolved.
A plain hub without laptop charging would provide a useful comparison;
otherwise the next diagnostic needs direct, verified CC-controller access.
