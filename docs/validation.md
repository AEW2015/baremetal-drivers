# Validation and practical limits

## Original SOM campaign

All 15 registered board suite entries passed against their recorded original
ELFs. The selected runs, UART logs and SHA-256 values are preserved in the
[hardware validation report](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/VALIDATION.md).
The packaged repository's full build, OCRAM build and pinned ATF/Quartus image
packaging were checked separately. A newly compiled ELF does not inherit an
older binary's hardware result.

## Tutorial follow-up checks

| Check | Observed result |
|---|---|
| Arm GNU 13.2.Rel1 builds QEMU exercise | PASS |
| QEMU 8.2.2, EL3 + NEON + 4096-byte copy | PASS, semihosted exit status zero |
| QEMU GDB break at `main`, step, stop at `qemu_done` | PASS |
| QEMU variables | `failures=0`, vector `{11,22,33,44}`, matching last copied word |
| Physical A55 GDB break at `example_main`, instruction step, `finish` | PASS |
| Physical core-example UART markers after continuing | PASS |
| Final DDR restore, patterns, payload and PC proof | PASS, DDR Hello left running |
| Desktop VS Code F5 session | Not exercised; supplied configuration mirrors tested GDB operations |

The debugger checks used GDB 15.1. Hardware used Quartus OpenOCD
`0.12.0+quartus-gc58ca4ebc`, the existing matching Modular design and the
repository's packaged DDR initializer. Published text evidence normalizes
workspace paths, line endings and trailing whitespace.

[Read the tutorial check manifest and logs](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/tutorial).
Future GitHub Actions runs check the QEMU exercise with Ubuntu's freestanding
cross-compiler invocation, plus the strict website build. Those CI results do not
represent physical-board tests or a test of the desktop GUI.

## What these results do not establish

The 64 MiB scratch check does not qualify the entire 8 GiB bank. The configured
2 GiB/detected 8 GiB diagnostic warning remains applicable. Cache discovery,
secondary core execution and CCU register reads do not prove cache coherency.
Polled GIC acknowledgement does not prove exception-vector delivery.

SMMU identification does not test address translation. ECC register checks do not
inject errors or prove recovery. SPI loopback is internal. Watchdog testing stops
before a system reset. I3C1 is tested in legacy-I2C mode, without native I3C
DAA/CCC/IBI targets.

Ethernet PHY IDs, USB controller IDs and SD card detect do not establish packet
traffic, enumeration or media read/write. No populated NAND/eMMC was established
on this SOM. EEPROM contents were read, not programmed. External-peer and
U-Boot/Linux recipes are separate setup references.
