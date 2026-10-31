# Agilex 5 Modular kit HPS examples

SOM-first bare-metal examples for the Agilex 5 E-Series Modular ES kit (FPGA ID
`0x0364f0dd`, A5ED065 ES R0), using the kit's JTAG and J2 HPS UART. These supplement
the repository's Simics reference tests with physical-board startup and checks.
They are independent of the Premium kit pinout.

The original bench campaign passed all 15 suite entries. See
[validation scope and evidence](VALIDATION.md) and [SOM/carrier mapping](HARDWARE.md).
Rebuilt binaries do not inherit those historical results. No FPGA programming
images, schematic PDFs, compiler binaries or proprietary tools are included.

The [memory and fabric labs](memory-labs/README.md) add cached multicore handoff,
DDR sweeps, SMMU translation/fault tests and an AXI traffic generator with
Simics/Verilator integration. Model and physical-board outcomes are separate.

## Examples

| Suite entry | Behavior checked |
|---|---|
| `core` | A55 identification, NEON addition, cache discovery, CPU DDR copy, GPIO snapshot, counter and GIC IDs |
| `dma` | DMAC0 linked-list 4096-byte copy, actual completion and full data readback |
| `gic` | GIC-600 redistributor power-up and secure Group-0 SGI0 polled acknowledgement |
| `mmu` | EL3 identity translation using AT/PAR and a DDR store/read |
| `som` | Peripheral timer expiry, watchdog interrupt-first mode, SPI internal loopback, LED pad toggle/readback, I2C controller IDs |
| `som-i2c` | GPIO open-drain I2C reads of SOM TMP464 manufacturer ID and 16 EEPROM bytes |
| `som-i3c` | Native I3C1 controller in legacy-I2C mode, same SOM sensor and EEPROM reads |
| `interfaces` | EMAC2 MDIO PHY identity, SD controller/card detect, USB1 DWC_usb31 identity |
| `mailbox` | Read-only SDM GET_IDCODE request and matching FPGA ID |
| `multicore` | Release three secondary A55/A76 cores and verify their MIDR/MPIDR records |
| `vendor-uart` | Vendor UART example with physical-kit startup/divisor preservation |
| `vendor-ccu` | Vendor CCU register-access checks; version warnings retained |
| `vendor-clkmgr` | Vendor clock-register reads; initialized/default-value warnings retained |
| `vendor-smmu` | Vendor ID example plus exact revision-2 SOM IIDR check |
| `vendor-ecc` | Vendor ECC register/default checks |

Sources are in [core/](core/). The separate PSCI example is compile-only: this
EL3 bootstrap does not provide resident BL31 for a nonsecure PSCI caller.
OCRAM UART and semihosting sources are in [bootstrap/ocram/](bootstrap/ocram/).

<!-- example-platform-checklist:start -->
## Example platform checklist

**✅ = recorded execution passed.** ⬜ = not tested, not a promise of support. ⚠️ = partial, ❌ = failed, ➖ = unsupported, 🔨 = build only, 📖 = reference, 🚧 = blocked.

Checkmarks apply to the linked evidence and the stated scope, including historical versions. Controller IDs, simulator models and physical transfers have different coverage.

| QEMU | SIMICS | Agilex 5 Modular hardware |
|:---:|:---:|:---:|
| **15 / 94 ✅** | **42 / 94 ✅** | **34 / 94 ✅** |

Expand a group for every example. [Detailed scope and results](../../docs/example-catalog.md).

<details>
<summary><strong>Current upstream</strong> · 26 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`upstream/bridge`](../bridge) | ➖ Unsupported | [✅ Passed](validation/runtime-fixes/simics-services/results.json) | ⬜ Not tested |
| [`upstream/ccu`](../ccu) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/clk_mngr`](../clk_mngr) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/combophy`](../combophy) | ➖ Unsupported | [✅ Passed](validation/runtime-fixes/simics-other/results.json) | [✅ Passed](validation/upstream26-examples) |
| [`upstream/crc`](../crc) | [✅ Passed](validation/runtime-fixes/qemu/results.json) | [✅ Passed](validation/runtime-fixes/simics-other/results.json) | [✅ Passed](validation/upstream26-examples) |
| [`upstream/ddr`](../ddr) | ➖ Unsupported | [✅ Passed](validation/simics26/upstream26-clean-checkout/results.json) | ⬜ Not tested |
| [`upstream/dma`](../dma) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/ecc`](../ecc) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/fcs`](../fcs) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/gic`](../gic) | ➖ Unsupported | [✅ Passed](validation/simics26/upstream26-clean-checkout/results.json) | ⬜ Not tested |
| [`upstream/gpio`](../gpio) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/hello`](../hello) | ➖ Unsupported | [✅ Passed](validation/simics26/upstream26-clean-checkout/results.json) | ⬜ Not tested |
| [`upstream/i2c`](../i2c) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/i3c`](../i3c) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/iossm`](../iossm) | ➖ Unsupported | [⚠️ Partial](validation/runtime-fixes/simics-services/results.json) | ⬜ Not tested |
| [`upstream/mailbox`](../mailbox) | ➖ Unsupported | [⚠️ Partial](validation/runtime-fixes/simics-services/results.json) | [✅ Passed](validation/cross-platform/hardware-runtime/results.json) |
| [`upstream/mmu`](../mmu) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/noc`](../noc) | ➖ Unsupported | [✅ Passed](validation/runtime-fixes/simics-other/results.json) | [✅ Passed](validation/upstream26-examples) |
| [`upstream/perf`](../perf) | [✅ Passed](validation/runtime-fixes/qemu/results.json) | [✅ Passed](validation/runtime-fixes/simics-services/results.json) | [✅ Passed](validation/cross-platform/hardware-runtime/results.json) |
| [`upstream/reboot_mngr`](../reboot_mngr) | ➖ Unsupported | [✅ Passed](validation/runtime-fixes/simics-services/results.json) | ⬜ Not tested |
| [`upstream/reset_mngr`](../reset_mngr) | ➖ Unsupported | [✅ Passed](validation/runtime-fixes/simics-other/results.json) | [✅ Passed](validation/upstream26-examples) |
| [`upstream/sdmmc`](../sdmmc) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/seu`](../seu) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/smmu`](../smmu) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/spi`](../spi) | ➖ Unsupported | ⬜ Not tested | ⬜ Not tested |
| [`upstream/timer`](../timer) | ➖ Unsupported | [✅ Passed](validation/simics26/upstream26-clean-checkout/results.json) | ⬜ Not tested |

</details>

<details>
<summary><strong>Original Modular suite</strong> · 15 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`board/core`](core/core_examples.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/dma`](core/dma_copy.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/gic`](core/gic_sgi.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/interfaces`](core/som_interfaces.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/mailbox`](core/mailbox_status.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/mmu`](core/mmu_translation.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/multicore`](core/multicore.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/som`](core/som_peripherals.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/som-i2c`](core/som_i2c.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/som-i3c`](core/som_i3c.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/vendor-ccu`](core/vendor_wrapper.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/vendor-clkmgr`](core/vendor_wrapper.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/vendor-ecc`](core/vendor_wrapper.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/vendor-smmu`](core/vendor_wrapper.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |
| [`board/vendor-uart`](core/vendor_wrapper.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/results.json) |

</details>

<details>
<summary><strong>Additional vendor board adapters</strong> · 4 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`board/vendor-timer`](build_board_vendor.py) | ➖ Unsupported | ⬜ Not tested | 🔨 Build only |
| [`board/vendor-watchdog`](build_board_vendor.py) | ➖ Unsupported | ⬜ Not tested | 🔨 Build only |
| [`board/vendor-spi`](build_board_vendor.py) | ➖ Unsupported | ⬜ Not tested | 🔨 Build only |
| [`board/vendor-hps_mailbox`](build_board_vendor.py) | ➖ Unsupported | ⬜ Not tested | 🔨 Build only |

</details>

<details>
<summary><strong>Legacy 25.1 Simics</strong> · 16 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`legacy/hello-world`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/uart`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/dma`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/timer`](simics/legacy.py) | ➖ Unsupported | [❌ Failed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/watchdog`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/i2c`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/i3c`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/spi`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/sdmmc`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/xgmac`](simics/legacy.py) | ➖ Unsupported | [❌ Failed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/mmu_el3`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/smmu`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/ccu`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/clkmgr`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/ecc`](simics/legacy.py) | ➖ Unsupported | [✅ Passed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |
| [`legacy/hps_mailbox`](simics/legacy.py) | ➖ Unsupported | [❌ Failed](validation/simics26/legacy25-compatibility/results.json) | ⬜ Not tested |

</details>

<details>
<summary><strong>Shared CPU and practice labs</strong> · 8 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`custom/qemu-hello`](qemu/hello.c) | [✅ Passed](validation/tutorial/results.json) | ⬜ Not tested | ⬜ Not tested |
| [`practice/startup`](qemu/labs/startup.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |
| [`practice/corruption`](qemu/labs/corruption.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |
| [`practice/exception`](qemu/labs/exception.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |
| [`practice/timer`](qemu/labs/timer.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |
| [`practice/mmu`](qemu/labs/mmu.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |
| [`practice/uart`](qemu/labs/uart.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |
| [`practice/multicore`](qemu/labs/multicore.c) | [✅ Passed](validation/cross-platform/qemu-practice/results.json) | [✅ Passed](validation/cross-platform/simics-practice/results.json) | [✅ Passed](validation/cross-platform/hardware-practice/results.json) |

</details>

<details>
<summary><strong>Additional diagnostics and integration</strong> · 12 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`diagnostic/smc-guard`](upstream-lab/lab.c) | [✅ Passed](validation/runtime-fixes/qemu/results.json) | ⬜ Not tested | ⬜ Not tested |
| [`diagnostic/perf-zero-clock`](upstream-lab/lab.c) | [✅ Passed](validation/runtime-fixes/qemu/results.json) | ⬜ Not tested | ⬜ Not tested |
| [`custom/bridge-control`](upstream-lab/lab.c) | ➖ Unsupported | [✅ Passed](validation/runtime-fixes/simics-services/results.json) | [✅ Passed](validation/cross-platform/hardware-runtime/results.json) |
| [`custom/ocram-hello`](bootstrap/ocram/uart_local.c) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](../../docs/examples/ocram.md) |
| [`custom/ddr-hello`](bootstrap/ddr) | ➖ Unsupported | ⬜ Not tested | [✅ Passed](validation/cross-platform/hardware-runtime/restore-bootstrap.log) |
| [`reference/semihost`](bootstrap/ocram/hello_semihost.S) | ⬜ Not tested | ⬜ Not tested | 📖 Reference |
| [`reference/psci`](core/secondary_core.c) | ⬜ Not tested | ⬜ Not tested | 🔨 Build only |
| [`custom/fault-probe`](core/fault_probe.c) | ➖ Unsupported | ⬜ Not tested | 🔨 Build only |
| [`custom/ethernet`](ethernet) | ⬜ Not tested | ⬜ Not tested | [✅ Passed](validation/ethernet/README.md) |
| [`fabric/add`](fabric) | ⬜ Not tested | ⬜ Not tested | ⬜ Not tested |
| [`fabric/xor`](fabric) | ⬜ Not tested | ⬜ Not tested | ⬜ Not tested |
| [`reference/pr`](fabric) | 📖 Reference | 📖 Reference | 📖 Reference |

</details>

<details>
<summary><strong>HPS configuration diagnostics</strong> · 2 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`config/sysmgr`](config-audit) | ➖ Unsupported | [✅ Passed](validation/config-audit/simics/results.json) | [✅ Passed](validation/config-audit/hardware/results.json) |
| [`config/pinmux`](config-audit) | ➖ Unsupported | [✅ Passed](validation/config-audit/simics/results.json) | [✅ Passed](validation/config-audit/hardware/results.json) |

</details>

<details>
<summary><strong>Simics / RTL integration</strong> · 2 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`integration/simics-rtl-add`](simics-rtl) | ➖ Unsupported | [✅ Passed](simics-rtl/validation/results.json) | ➖ Unsupported |
| [`integration/simics-rtl-xor`](simics-rtl) | ➖ Unsupported | [✅ Passed](simics-rtl/validation/results.json) | ➖ Unsupported |

</details>

<details>
<summary><strong>Simics native fabric models</strong> · 1 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`model/pio`](model-audit) | ➖ Unsupported | [✅ Passed](model-audit/validation/results.json) | ➖ Unsupported |

</details>

<details>
<summary><strong>Memory and fabric labs</strong> · 8 examples</summary>

| Example / source | QEMU | SIMICS | Hardware |
|---|:---:|:---:|:---:|
| [`memory/dsu`](memory-labs/dsu) | [✅ Passed](memory-labs/dsu/validation/results.json) | [✅ Passed](memory-labs/dsu/validation/simics-results.json) | [🔨 Build only](memory-labs/dsu/validation/build-agilex5.json) |
| [`memory/l3-partition`](memory-labs/dsu) | ➖ Unsupported | ➖ Unsupported | [🔨 Build only](memory-labs/dsu/validation/build-agilex5.json) |
| [`memory/ddr-sweep`](memory-labs/ddr) | [✅ Passed](memory-labs/ddr/validation/qemu-final/results.json) | [✅ Passed](memory-labs/ddr/validation/simics-results.json) | [🔨 Build only](memory-labs/ddr/validation/build-agilex5-calibrated.json) |
| [`memory/smmu-qemu`](memory-labs/smmu) | [✅ Passed](memory-labs/smmu/validation/qemu-20261031T022532.436895Z/results.json) | ➖ Unsupported | ➖ Unsupported |
| [`memory/native-tbu`](memory-labs/smmu/native_fixture.py) | ➖ Unsupported | [✅ Passed](memory-labs/smmu/validation/simics-native-20261031T024350.917717Z/results.json) | ➖ Unsupported |
| [`memory/dma-tbu`](memory-labs/smmu/dmac) | ➖ Unsupported | [✅ Passed](memory-labs/smmu/dmac/validation/simics-final/results.json) | ⬜ Not tested |
| [`memory/fabric-ddr`](memory-labs/fabric-ddr) | ➖ Unsupported | [✅ Passed](memory-labs/fabric-ddr/simics/validation/results.json) | 🚧 Blocked |
| [`custom/usb-host`](usb-bringup) | ➖ Unsupported | ⬜ Not tested | [❌ Failed](validation/usb-baremetal/20261031/results.json) |

</details>

**USB work in progress:** the [bare-metal USB lab](usb-bringup/README.md) boots U-Boot on hardware, but USB controller readiness still fails. Hub enumeration, mouse input, flash reads and USB-Ethernet traffic are pending.

Maintainers: regenerate these checklists with `python3 examples/agilex5-modular/catalog.py`; CI checks for drift.
<!-- example-platform-checklist:end -->

## Build

Use an AArch64 bare-metal GCC toolchain (validated: Arm GNU 13.2.Rel1), CMake,
Ninja, Python 3, make and git. Existing container users can run:

```sh
docker exec -u dev agilex-xrdp bash -lc \
  'cd /home/dev/baremetal-drivers/examples/agilex5-modular && ./build_all.sh'
```

Or run `./build_all.sh` directly in this directory with `aarch64-none-elf-*` on
PATH. If present, `/etc/profile.d/baremetal-tools.sh` supplies the existing bench
tools. `build/` contains local ELFs, while upstream reference ELFs use the
pinned dependency's `build/aarch64/out/` output convention.

`configure_vendor.sh` fetches the 25.1 source at commit `1419101568f1a9034630b632634fe9fe71773266` into ignored `.deps/baremetal-25.1` and configures it in `build/legacy-vendor/` and accepts
additional CMake arguments. Upstream FetchContent downloads Arm Trusted Firmware
and GoogleTest; to reuse existing sources, pass
`-DFETCHCONTENT_SOURCE_DIR_ATF=/path/to/atf` and
`-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=/path/to/googletest`.
The build compiles 15 upstream reference targets, 11 local DDR programs, the
PSCI object, and 9 board-adapted vendor ELFs. Compilation does not run any tests.

To build only the custom DDR examples:

```sh
./build_core.sh
./build_dma.sh
./build_gic.sh
SKIP_VENDOR=1 ./build_board.sh
```

`bootstrap/ocram/build_uart.sh` separately builds OCRAM UART ELF/bin/hex. If
`AGILEX_SOF` is supplied it also packages a volatile HPS programming image. The
OCRAM code uses this bench's handoff layout and 54 UART divisor; verify the handoff
and input clock on a different design. `hello_semihost.S` is provided as a source
reference; it is not part of the automated DDR suite.

## DDR initialization prerequisite

The examples expect DDR already initialized by a **matching hardware handoff**.
The tested bank is HPS bank 3A, 8 GiB DDR4-1600, 150 MHz EMIF reference. The
original diagnostic reported a configured 2 GiB versus detected 8 GiB warning;
only 64 MiB is tested. Other SOM DDR banks are FPGA fabric interfaces.

Inside the tool container:

```sh
export AGILEX_SOF=/absolute/path/to/matching-hps-enabled-memory_test.sof
./bootstrap/ddr/build_ddr.sh
```

This fetches the pinned ATF commit, applies the included diagnostic hook after DDR
initialization and before storage boot, builds the DDR Hello payload, and uses
Quartus PFG to create `bootstrap/ddr/ddr_probe.hps.rbf` and a merged recovery SOF.
An optional `AGILEX_ATF_DIR` selects a dedicated clone; the build patches that
clone. The expected commit is checked before modifying it. The matching SOF must
be supplied by your FPGA project; generated images are deliberately untracked.

## Run from the Linux host

The source tree must be mounted into the container, with Quartus Programmer,
OpenOCD with `aji_client`/ADIv6 support, and AArch64 binutils available there.
Set the **container path to this example directory**, and the host's actual SOM
J2 UART device:

```sh
export AGILEX_CONTAINER=agilex-xrdp
export AGILEX_CONTAINER_USER=dev
export AGILEX_CONTAINER_ROOT=/home/dev/baremetal-drivers/examples/agilex5-modular
export AGILEX_UART=/dev/serial/by-path/YOUR-SOM-J2-UART-CHANNEL
cd examples/agilex5-modular
python3 run_suite.py --list
python3 run_suite.py --only core,dma,gic,mmu,som,som-i2c,som-i3c,interfaces,mailbox,multicore
# After reviewing the vendor adapters:
python3 run_suite.py --only vendor-uart,vendor-ccu,vendor-clkmgr,vendor-smmu,vendor-ecc
```

The bootstrap requires the verified Modular carrier as cable 1; it checks its name
and FPGA ID before programming and derives the FPGA position from the current
chain. The selected cable's full enumerated name is used; USB topology suffixes
are not hardcoded. Another board on another cable must remain untouched.

Each test freshly initializes DDR to avoid stale I-cache reloads, captures a new
begin marker and required results, records the ELF SHA-256, and restores DDR Hello
in `finally`. `runs/<UTC timestamp>/results.json` and UART/debug/bootstrap logs
are the evidence. A restore PASS is separate from a test PASS. Set `--port` to
override `AGILEX_UART`. Use a persistent USB-by-path device after verifying it;
on the tested SOM, FT4232H channel C was HPS UART, at 115200 8N1.

The runner replaces the current volatile application and uses scratch RAM. It
holds a local advisory `hardware.lock`; every other debugger/runner must also
respect exclusive ownership. No flash/SD/EEPROM-array or clock-NVM writes occur
in these selected board tests. Do not blindly execute every original Simics test:
several model EEPROMs, write media, reset hardware or assume simulation timing.

## Memory and test limits

Local program entry addresses are 0x82100000, 0x82200000, 0x82300000 and
0x82400000; fault probe uses 0x82500000. Stack is below 0x84000000. Vendor board
adapters use text 0x80200000/data 0x80400000. Reserve 0x82000000 for DDR Hello,
0x82010000 for parked secondary cores, 0x84000000–0x87ffffff for bootstrap tests,
and scratch buffers 0x85000000–0x85300080 (reused after the bootstrap test).
These are isolated EL3 diagnostics, with data cache disabled, not concurrent OS
applications. The MMU example and vendor adapters enable translation separately.

Polled SGI acknowledgement does not test exception delivery. Cache discovery,
secondary execution and CCU reads do not establish cache coherency. The SMMU test
checks identity, not DMA translation. ECC register checks do not inject errors.
Watchdog testing stops before a system reset. Counter advancement does not prove
a calibrated frequency (CNTFRQ was zero). I3C legacy-I2C does not establish native
I3C DAA/CCC/IBI behavior. EEPROM reads use address-pointer writes only; no array
write-test is claimed. PHY/controller IDs and SD card detect do not establish
Ethernet traffic, USB enumeration or SD media access.

The U-Boot/Linux commands in [recipes/](recipes/) are for a separately configured
board environment and external peers, not for the host container. They were not
run in this campaign. NAND/eMMC population is not established on this SOM.

For manual debugging, initialize DDR first, then run `debug-server.sh` inside the
container and use [recipes/debug.gdb](recipes/debug.gdb) from this directory with
an AArch64-capable GDB in the same container. It binds local debugger ports only.
The interactive recipe has not been separately hardware-qualified; the batch
OpenOCD ELF load and PC checks have.

See [PORTING.md](PORTING.md) for demonstrated startup, libc and recovery lessons.

## VS Code, QEMU and hardware tutorial

Follow the [web tutorial](https://aew2015.github.io/baremetal-drivers/) and open
[agilex5-modular.code-workspace](agilex5-modular.code-workspace) in the compiler
environment. The separate [QEMU exercise](qemu/) targets generic QEMU `virt`;
the Agilex MMIO examples require the physical kit. New debugger and emulator
checks are recorded in [tutorial validation](validation/tutorial/results.json).

## Environment checks and troubleshooting

Run `python3 doctor.py --target qemu` in the compiler environment, or
`python3 doctor.py --target hardware` on the configured Linux host before board
work. See the [troubleshooting guide](https://aew2015.github.io/baremetal-drivers/troubleshooting/)
and [simulated student review](https://aew2015.github.io/baremetal-drivers/student-review/)
for failure checks, recovery steps and validation limits. Software regressions:
`AGILEX_TEST_REAL_QEMU=1 python3 -m unittest discover -s tests -v`
(omit the environment flag to skip the real compiler/emulator exercise).

## Fabric IP and persona swaps

The optional [fabric IP lesson](https://aew2015.github.io/baremetal-drivers/fabric-ip/)
provides ADD/XOR RTL, a 64-byte register ABI, an actual C driver/RTL co-simulation
and matched full-image deployment. The
[PR lesson](https://aew2015.github.io/baremetal-drivers/partial-reconfiguration/)
covers static partitions, freeze/reset and live-swap acceptance checks. The new
whole-board fabric design and live PR remain unqualified; these are separate
from the historical HPS suite results. Start with `./fabric/test.sh`.

## Six QEMU practice labs

The [shared platform extension](../../docs/cross-platform.md) ports these six
labs to Agilex Simics and the Modular kit and adds a seventh, multicore exercise.
See the [complete example catalog](../../docs/example-catalog.md) for recorded
results across legacy, current and custom implementations.

Build and test startup relocation, a corrupted copy, synchronous exceptions,
timer interrupts, MMU permissions and a UART command parser with
[the practice lab instructions](../../docs/examples/qemu-labs.md).
From this directory, with the AArch64 compiler, QEMU and GDB on `PATH`:

```sh
bash qemu/labs/build.sh
python3 qemu/labs/run.py --negative --gdb
```

The runner saves logs, source/ELF hashes and results under `runs/`.
[Recorded QEMU evidence](validation/qemu-labs/README.md) describes the tested versions.

## Recreate the environment and inspect FPGA provenance

Use the [public container recipe](https://aew2015.github.io/baremetal-drivers/container/)
and [FPGA onboarding](https://aew2015.github.io/baremetal-drivers/fpga-design/).
`check_artifacts.py --sof <file> --handoff <file>` checks exact identity against
the recorded bench profile; a hash match is not a qualification of a new PCB.
The [desktop follow-up](https://aew2015.github.io/baremetal-drivers/feedback-followup/)
records actual GUI checks and screenshots separately from historical evidence.

## Use with Codex

The repository includes a portable
[agilex5-baremetal skill](../../skills/agilex5-baremetal/SKILL.md) with board
identity checks, host/container guidance and demonstrated recovery lessons.
See [installation and example prompts](../../docs/agent-skill.md).

## Ethernet bandwidth example

The separate [Ethernet lab](../../docs/examples/ethernet.md) provides a real
XGMAC2 DMA adapter and a pinned lwIP TCP/IP stack for the SOM's direct PC link.
`build_all.sh` now also builds its default cached-CPU/noncacheable-DMA image.
Use `ethernet/build.sh` for an individual build and `ethernet/run.py --help`
for host-side execution. The network run requires an explicitly selected wired
interface and is separate from the 15-entry on-chip/SOM suite. It uses a custom
socket benchmark protocol; it is not an iperf server.

## Current upstream and Simics

The repository root now contains the upstream 26.3 driver/API rewrite. Existing
vendor board adaptations intentionally use the pinned 25.1 compatibility source;
the root no longer contains the old `inc/` and `test/simics/` API. Use
[the migration guide](../../docs/upstream-26.3.md) for the current API and
[Simics](../../docs/simics.md) alongside the existing QEMU labs.
