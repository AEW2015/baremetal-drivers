# Validation and practical limits

## Upstream 26.3 sync and Simics

The repository root merges upstream `66bdcc3`. A clean checkout of merge
`cd74c90` compiled both new profiles and passed five current OCRAM console
checks in Simics 26.3. The pinned legacy suite recorded 13 passes and three
failures separately. QEMU/fabric checks and all 39 regressions passed.
See [the Simics workflow and evidence](simics.md) and
[the API/migration guide](upstream-26.3.md). No new upstream image was deployed
onto the physical kit during this sync.

## SOM Ethernet traffic campaign

The separate Ethernet lab passed real UDP/TCP packet checks, 40 bandwidth
measurements and a ten-minute simultaneous TCP soak on the direct SOM-to-PC
link. Mean one-way TCP payload goodput was about 230 Mb/s into the SOM and
949 Mb/s out. See [Ethernet measurements and evidence](ethernet-validation.md)
for rates, loss, exact artifacts, failures and recovery. This extends the earlier
PHY identification result; it does not add Ethernet to the 15-test register suite.

## Fresh-clone remote campaign

A new clone of remote `main` at `0daff10` built and passed all 15 registered
hardware tests in one campaign, with fresh DDR initialization and successful
restoration. QEMU labs, negative controls, GDB, fabric simulation and the skill
package were also checked. Two additional compiler/launcher defects were
reproduced and fixed, with expanded CI coverage. Read the
[fresh-clone report and evidence](remote-validation.md) for revisions, results
and the follow-up with the corrected launcher.

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
| Desktop VS Code F5 session | Not exercised in this original campaign; subsequently checked in the [desktop follow-up](feedback-followup.md) |

The debugger checks used GDB 15.1. Hardware used Quartus OpenOCD
`0.12.0+quartus-gc58ca4ebc`, the existing matching Modular design and the
repository's packaged DDR initializer. Published text evidence normalizes
workspace paths, line endings and trailing whitespace.

[Read the tutorial check manifest and logs](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/tutorial).
Future GitHub Actions runs check the QEMU exercise with Ubuntu's freestanding
cross-compiler invocation, plus the strict website build. Those CI results do not
represent physical-board tests or a test of the desktop GUI.

## Robustness follow-up

Three simulated student reviews drove setup, runner and recovery improvements.
The follow-up includes 18 automated checks, positive/negative real QEMU runs,
command-line GDB and a physical core run with successful DDR restoration.
Read the [review methods, feedback and evidence](student-review.md). These are
agent simulations and executed technical checks, not independent human usability
results. The historical 15-example hardware results remain separate.

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

## Fabric IP extension

The new [fabric lesson](fabric-ip.md) includes ADD/XOR RTL, its register ABI,
actual C-driver/RTL co-simulation, an AArch64 build and a bridge-enabled ATF
packaging path. Evidence distinguishes these software/component checks from
a fitted whole-board project. The new fabric design has not been board-qualified;
[partial reconfiguration](partial-reconfiguration.md) remains an advanced
integration lab requiring a compiled static base, isolation and tested transport.

## Onboarding feedback follow-up

The [follow-up report](feedback-followup.md) records a clean-container QEMU
trial, public-source container builds, desktop QEMU/hardware debugger checks
and remaining fresh-kit limitations. These are later checks; the original
logs and historical hardware results remain unchanged.
