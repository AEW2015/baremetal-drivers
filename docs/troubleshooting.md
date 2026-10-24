# Troubleshooting

## Compiler or source lookup fails

Check `command -v aarch64-none-elf-gcc` in the actual VS Code environment.
A compiler installed on the host is not automatically installed in an attached
container. Start native VS Code from the configured shell. Open the supplied
workspace, whose root is `examples/agilex5-modular`, and build before debugging.
Use `gdb-multiarch` if the downloaded toolchain's GDB has missing host libraries.

Optimized hardware code can jump between C lines and optimize variables away.
Use the disassembly view and instruction stepping to distinguish this from a
failed breakpoint. The QEMU exercise uses `-Og -g3` for easier inspection.

## QEMU stays silent or fails to load

With `--debug`, silence before GDB continues is expected. Connect to port 3338,
set `hbreak main`, then `continue`. Without `--debug`, use `--check` for a bounded
run that requires all expected markers.

Use the supplied runner: it disables the default NIC, loads the ELF above the
DTB region at `0x40200000`, enables the secure/virtualization environment expected
by the EL3 startup, and enables semihosted exit. Changing those settings can
cause missing option-ROM errors, overlapping DTB/ELF regions, wrong exception
level or a program that does not exit. An HPS ELF uses incompatible MMIO and
cannot run unchanged on `virt`.

## Debugger port is already in use

QEMU uses 3338; OpenOCD uses 3337, 6677 and 4457, all on loopback. Stop your own
previous debug session or emulator. Identify the owning process before stopping
anything; another board or developer may have an unrelated debugger running.

## Hardware runner rejects the board or UART

Inspect fresh `jtagconfig`, the carrier name/FPGA ID, cable order and the actual
SOM J2 by-path serial device. The FTDI interfaces do not have reliable unique
by-id names on the tested kit. Device numbers can change after reconnecting.
The Linux host must have serial permissions, and the container needs working
Quartus USB/JTAG access. Never point the runner at the other board to bypass a
failed identity check.

## UART receives only DDR Hello

A begin marker from the newly loaded program is required. Old Hello lines during
JTAG attachment are not its result. Confirm the correct ELF, entry PC and fresh
DDR initialization. Stop other UART readers before automated capture; they can
consume the bytes you are waiting for. Debugger disconnect alone is not proof
that the new program completed: continue deliberately and check its markers.

## Programming or DDR initialization fails

Use the matching Modular SOF/handoff, not a Premium image. After a power cycle,
the merged `--full-recovery` image may be needed to establish the correct volatile
fabric/HPS state. A raw HPS-enabled SOF without its bootloader can be rejected as
incomplete. The test only qualifies its 64 MiB scratch region; inspect the DDR
configuration warning separately.

An earlier wrong selector routed HCLK onto management pins and stalled HPS
clocking. Repeated JTAG programming did not repair that state; a physical power
cycle and the corrected matching image did. IOA9/10 selectors are **0 I3C1,
4 I2C_EMAC1, 8 GPIO, 9 HCLK** in the authoritative Quartus table. Do not infer
pinmux values from dropdown order. See the
[recorded recovery lesson](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/PORTING.md).

## Example prints PASS but a peripheral still does not work

Check the [scope table](examples.md). An ID read does not establish USB
 enumeration, Ethernet traffic, SD reads, SMMU translation or ECC recovery.
Preserve warnings and failing runs instead of changing expected values solely
to produce PASS. For a new chip revision, decode the documented ID fields first.
