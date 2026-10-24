---
name: agilex5-baremetal
description: Build, run, debug, and validate the Agilex 5 Modular kit bare-metal HPS examples in AEW2015/baremetal-drivers, using QEMU or the matching board, container, JTAG and SOM UART. Use for OCRAM/DDR bring-up and schematic-based SOM peripheral work.
---

# Agilex 5 bare-metal workflow

Use the Modular kit's actual hardware profile and matching handoff. The Premium
kit guide supplies software context, not interchangeable pinout or FPGA images.

## Locate the checkout and choose the environment

Find the user's `baremetal-drivers` checkout and inspect applicable `AGENTS.md`.
Set the working directory to `examples/agilex5-modular`. All commands below are
relative to that directory, not to the installed skill. If the checkout is
absent, obtain it at the user's chosen location from
https://github.com/AEW2015/baremetal-drivers. Installing this skill alone does not
install tools, examples or hardware images.

Read `docs/setup.md` and `docs/container.md` in that checkout for tool setup.
Build and run QEMU in the development environment (native Linux or the attached
container). Run physical-board automation on the Linux host; set
`AGILEX_CONTAINER_ROOT` to this same example directory inside the bind mount.
Use `env-learning.sh.example` and `env-hardware.sh.example` rather than copying
another bench's paths. The hardware runner verifies the shared checkout with a
nonce; two identical clones are not the same mount.

## QEMU and debugger work

Run `python3 doctor.py --target qemu`, `./qemu/build.sh`, then
`python3 qemu/run.py --check`. Require all markers and exit zero.
`python3 qemu/experiment.py` runs isolated corruption/recovery cases in temporary
copies; expected failed guests exit 1 while the complete experiment exits 0.
Read [testing and recovery](references/testing.md) for the independent-check
lesson and warning interpretation. Six further labs are in `qemu/labs/`;
consult `docs/examples/qemu-labs.md` for their commands and scope.

Use the supplied `agilex5-modular.code-workspace` and `docs/vscode.md` for GUI
setup. QEMU first stops at `_start`; set managed source breakpoints at `main`
and `qemu_done`, then continue. Use `docs/qemu.md` for the CLI GDB walkthrough.
Do not reuse the QEMU PL011 address or ELF on physical hardware.

## Hardware work

Before hardware access read [the hardware profile](references/hardware.md),
[testing and recovery](references/testing.md), and the checkout's `HARDWARE.md`,
`docs/hardware.md` and `docs/fpga-design.md` (the latter two at repository root).
Confirm the actual PCB/device, fresh JTAG chain, host SOM J2 UART, and qualified
SOF/handoff pair. Never assume cable or FPGA device indices are stable. Leave
other connected boards and unrelated processes alone.

Use `python3 check_artifacts.py --sof PATH --handoff PATH` for recorded artifact
identity, then the hardware doctor with the documented arguments. Matching a
hash is not qualification for a different board. The complete custom FPGA
project/image is not bundled; do not substitute a Premium image or present a
public reference rebuild as independently qualified.

- Build with `./build_all.sh` in the configured compiler environment; individual
  builds are documented in `README.md`. Compilation is not execution evidence.
- OCRAM UART builds through `./bootstrap/ocram/build_uart.sh`; use the documented
  HPS-RBF flow in `docs/hardware.md` to load it. There is no separate OCRAM runner
  in this fork.
- DDR uses `bootstrap/ddr/build_ddr.sh` in the compiler environment and
  `bootstrap/ddr/run_ddr.py` on the host. Inspect `--help` and configured inputs;
  do not reconstruct the fragile Quartus/OpenOCD sequence from memory.
- List the physical suite with `python3 run_suite.py --list`, then use `--only`
  for the requested tests. It bootstraps DDR before each ELF and restores DDR
  Hello afterward. Inspect every requested result, fresh UART, ELF hashes,
  timeout/fault logs and restoration; restoration alone does not prove tests passed.
- `build_vendor.sh` compiles simulation references; `build_board_vendor.py`
  produces board adaptations. Their scope and observed results differ.
- For SOM Ethernet traffic and UDP/TCP bandwidth work, read
  [the Ethernet workflow](references/ethernet.md). PHY identification alone
  does not qualify packets or throughput; use the separate Ethernet runner.

Respect the hardware lock, debugger ownership records and any shared lock used
by other checkouts. An unresolved process record or uncertain cancellation is a
reason to diagnose ownership, not delete the lock or program again. Clean up
only owned processes. On unrecoverable debug/clock failure stop retrying and use
the documented power-cycle recovery, with new DDR/readback/PC evidence afterward.

A request to run these examples can include their necessary volatile programming
and scratch RAM use. It does not authorize storage erases, EEPROM array writes,
clock NVM changes or touching another board. Preserve SOM-only scope when asked.

## Evidence and advanced integration

Record source revision/changes, ELF and hardware-artifact hashes, UART path,
entry address, fresh completion/readback, failures and restoration. Keep failed
attempts. Read `VALIDATION.md` for historical scope; newly rebuilt binaries do
not inherit that evidence. Separate controller identification, loopback,
external-device transactions and end-to-end traffic. Do not turn a weak vendor
PASS expression into a hardware claim.

For fabric IP or partial reconfiguration, read `docs/fabric-ip.md` and
`docs/partial-reconfiguration.md`. RTL/driver simulation does not qualify a
fitted image or live PR. The published fabric/PR labs still require target-specific
integration; no live persona swap is established by the existing HPS campaign.
When improving this skill, preserve demonstrated failures and narrow remedies,
not universal rules inferred from one bench.
