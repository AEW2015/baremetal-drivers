# Obtain and qualify the FPGA design

Hardware students need both a tool environment and a board-specific design.
The bare-metal repository provides neither a universal Modular SOF nor a
reconstruction of the complete custom FPGA project used for the earlier tests.
This page identifies that project's origin and separates it from the public
reference starting point.

## The exact design behind the recorded results

| Item | Recorded bench |
|---|---|
| FPGA | `A5ED065BB32AE6SR0`, JTAG ID `0364F0DD` |
| Integration | Custom HPS + dual-DDR1600, local revision `dual_ddr1600_hps_lw_r3` |
| HPS upstream | `altera-fpga/agilex5e-ed-gsrd`, commit `d970f25424bb413081fa7d4329535b0071d79627` |
| Upstream design | `mk-a5e065bb32aes1/baseline-a55` |
| Tools | Quartus Pro 26.1.1 |
| HPS DDR | Bank 3A, 8 GiB DDR4-1600, 150 MHz EMIF reference |
| Qualified pair identity | `profiles/modular-es-ddr1600.json` |

The custom integration also contains unrelated fabric DDR/diagnostic logic.
Its generated SOF is not identical to the unmodified upstream baseline. The
complete custom project's inputs are not currently packaged in this public
repository. An instructor using the recorded bench must supply that exact
qualified pair and its build reports. Do not tell a new-kit student that merely
cloning the C examples reproduces the original hardware result.

## Check the instructor-supplied pair before packaging

On any Linux machine with Python 3, from the example directory:

```sh
python3 check_artifacts.py \
  --sof /absolute/path/to/memory_test.sof \
  --handoff /absolute/path/to/hps_bootloader_handoff.bin
```

This reads files without programming or querying a board. It compares both
SHA-256 values with the trusted recorded profile; exact identity returns
`"status": "match"` and exit zero. Missing, changed or unqualified pairs fail.
The hashes are also published in the profile for independent checking.

**Identity is not a general compatibility test.** A match establishes the
previously tested bytes, not the physical PCB revision, cables, clocks or device
on a new bench. Read the SOM revision and FPGA marking, compare the expected
DDR/pinmux profile, then run the hardware doctor/JTAG identity check before
programming. An arbitrary new SOF cannot be qualified by copying its hash into
the profile. Keep custom/fabric/PR variants in separately reviewed profiles.

## Public reference starting point for a new Modular ES project

The immutable [upstream design directory](https://github.com/altera-fpga/agilex5e-ed-gsrd/tree/d970f25424bb413081fa7d4329535b0071d79627/mk-a5e065bb32aes1/baseline-a55)
is the relevant **ES Modular** reference, not the similarly named production
065B or Premium project. Its README specifies the part, Quartus version and
HPS-first boot configuration. Use the matching
[Modular ES GSRD guide](https://altera-fpga.github.io/rel-26.1.1/embedded-designs/agilex-5/e-series/modular/gsrd/ug-gsrd-agx5e-modular/)
for the board-specific flow; skip its media/flash-writing steps when following
this volatile bare-metal lab.

In the Quartus **development environment**, in a separate source directory:

```sh
git clone https://github.com/altera-fpga/agilex5e-ed-gsrd.git
cd agilex5e-ed-gsrd
git checkout --detach d970f25424bb413081fa7d4329535b0071d79627
```

Run the pinned Makefile's hardware stages in order (not `make all`, which also
builds unrelated platforms/software):

```sh
make mk-a5e065bb32aes1-baseline-a55-pre-prep
make mk-a5e065bb32aes1-baseline-a55-generate-design
make mk-a5e065bb32aes1-baseline-a55-package-design
make mk-a5e065bb32aes1-baseline-a55-prep
make mk-a5e065bb32aes1-baseline-a55-build
```

These commands are a source-reviewed build recipe, not a claim that a fresh
reference build was executed in this tutorial campaign. Retain the generated
HPS handoff and SOF from the same successful compile. Locate them with:

```sh
find . -type f \( -name '*.sof' -o -name 'hps_bootloader_handoff.bin' \)
```

A rebuild of that reference has not been qualified with this tutorial's
custom diagnostic bootstrap. Its DDR/ECC, clocks, memory map and pinmux may differ
from the recorded integration. Before using it here, an FPGA instructor must
review the reports, check the ATF/handoff compatibility and establish fresh
UART, DDR-pattern and PC evidence on that board. The current exact-hash checker
will correctly reject it as a different pair. This remains a **new-kit onboarding
gap**, not a completed fresh-kit validation.

## Instructor handoff package

Provide one directory containing the full SOF, matching handoff, FPGA project
revision/source commit, Quartus version, exported pin/clock/DDR configuration,
timing result and a reviewed hash manifest. State what the image actually
contains and whether it was tested on this PCB revision. Include boot-mode
settings and exact cables/UART identification; do not distribute license files.

Then use [hardware setup](hardware.md) to build the pinned diagnostic initializer,
produce the matched HPS RBF/full recovery SOF, and verify one core example plus
DDR restoration. Preserve the failed attempts and exact binary hashes. The
existing 64 MiB scratch result does not qualify the whole DDR bank.
