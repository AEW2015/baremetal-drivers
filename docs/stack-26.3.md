# Quartus 26.3 stack migration

The active Modular ES platform uses **Quartus 26.3 Build 114**, HPS IP **14.1.0**
and HPS EMIF **5.1.0**. The board remains `A5ED065BB32AE6SR0`, with its original
Modular pins, clock sources and bank-3A DDR4-1600 configuration.

The machine-readable [release manifest](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/stack-versions.json)
pins the current drivers, ATF and U-Boot. Firmware builders read this file.
ATF and U-Boot use `QPDS26.3_REL_BASELINE_PR`; drivers remain upstream commit
`66bdcc347564c5698a8997169bce83a31647d618`, which was still upstream HEAD at
verification. Fork-local FCS, mailbox and performance fixes are retained; the
upstream hash is a base revision, while build manifests record the actual
source hashes. The 25.1 driver checkout remains a clearly labeled historical
API fixture. Arm GNU 13.2.Rel1 remains the supported example compiler.

## Upgrade the matching hardware project

Use the [physical PR build workflow](partial-reconfiguration.md) and its
`fabric/pr/hardware/prepare.py`, `generate.sh` and `configure.py` scripts.
Prepare an isolated copy of the qualified **Modular ES** baseline. Generation
upgrades all root systems and leaf IP, records before/after hashes, and checks
that parent-system snapshots have not restored older HPS/EMIF versions.
A vendor GUI reference targeting a different device is not a board image.

Compile the base, analyze timing and assemble it. Export the static partition
with `export_static.sh`, including its IP-owned SDC, before building ADD/XOR.
Check each persona against the exact bootloader-embedded full SOF.
No generated IP HDL, QDB or programming binary is required in Git.

## Boot and test the matched stack

Build boot firmware from the pinned ATF source. FPGA-first configuration uses
a complete SOF with BL2 embedded; PFG rejects the HPS-only conversion for that
boot order. Keep the previous known-good recovery image separately.

On the host, from `examples/agilex5-modular`, with the same checkout mounted
inside the tool container:

```sh
export AGILEX_CONTAINER=agilex-hardware
export AGILEX_CONTAINER_USER=dev
export AGILEX_CONTAINER_ROOT=/home/dev/baremetal-drivers/examples/agilex5-modular
export AGILEX_BOOTSTRAP_DIR="$PWD/build/boot"
export AGILEX_HARDWARE_LOCK="$PWD/hardware.lock"
export AGILEX_UART=/dev/serial/by-path/YOUR-VERIFIED-SOM-UART
export AGILEX_FORCE_FULL_BOOT=1
python3 bootstrap/ddr/run_ddr.py --full-recovery
python3 run_suite.py
```

The example above selects the output of `bootstrap/ddr/build_ddr.sh`. The
recorded bench used an isolated `build/platform26.3/boot` directory instead.
Choose the directory containing your newly built pair.

The bootstrap directory must be inside this shared example tree and contain
the matching `ddr_recovery.sof`, so both host and container see the same bytes.
`AGILEX_BOOTSTRAP_DIR` selects the current runner/container profile; it also
stages payloads under the repository rather than the older bench directory.
The repository-owned programmer client is selected automatically. Optional
`AGILEX_PROGRAMMER_MCP_COMMAND` selects an installed vendor MCP server; CLI
discovery is labelled separately. Every operation
holds the shared hardware mutex and freshly identifies the Modular FPGA.

The runner halts the preceding boot before starting UART capture, then
requires four address-dependent 64 MiB patterns, payload readback, three fresh
DDR Hello lines, FPGA user mode with CONF_DONE/INIT_DONE, and a PC in DDR.
It reloads the same full image before every guest and after the suite. A
`boot_order: fpga-first` build manifest also selects the full image, preventing
a leftover HPS-only RBF from an older build from being selected.
These scratch checks do not qualify the entire 8 GiB bank. The retained
firmware configuration still reports its 2 GiB versus detected 8 GiB warning.

## GPIO EEPROM retry diagnostics

The first migrated run passed the temperature ID but failed the GPIO EEPROM
transaction at its address stage. The native I3C legacy-I²C path read the same
EEPROM. A stage number alone does not distinguish NACK from a GPIO line that
failed to rise, so the GPIO example now records both conditions and retries
only the same bounded pointer/read transaction, with STOP and idle in between.
It still requires a complete 16-byte read. No EEPROM data writes, broad address
scan or shared reset pulse is used. This is not a claim that the EEPROM was
busy: [Microchip documents address NACK during write cycles](https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA64-24FC64-24LC64-64-Kbit-I2C-Serial-EEPROM-DS20001189.pdf),
but the initial failure's electrical cause has not been established.

## Validation record

Read the [fresh results and terminal output](validation-26.3.md): 50 hardware
passes and 6 partial capabilities, 16 QEMU passes, and 49 Simics passes.

New campaign evidence is collected under
[`validation/stack-26.3-20261101`](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/stack-26.3-20261101).
Historical passes describe their recorded binaries and tool stacks; they are
not automatically promoted to passes on newly generated images. Physical
results require execution and successful restoration, independently of builds
or simulator outcomes.
