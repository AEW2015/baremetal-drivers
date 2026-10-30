# Example catalog and platform results

Generated from the [machine-readable catalog](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/catalog.json).

Each row is one named exercise or implementation. Legacy, board-adapted and current implementations count separately. A bundled exercise counts once; individual assertions, negative variants, help commands and debugger walkthroughs are excluded.

PASS records execution of the referenced artifacts, not a promise about every future rebuild. Partial results do not count as passes. “Not run” is not a claim that a platform supports the example. Software/RTL co-simulation is recorded separately from these three targets.

| Platform | Recorded PASS | Partial | Failed |
|---|---:|---:|---:|
| qemu | 12 | 0 | 0 |
| simics | 32 | 2 | 3 |
| hardware | 32 | 0 | 0 |

Inventory: **81 rows**. Results include historical versions; see each row’s scope and evidence.

## Current upstream

| Example | QEMU | Simics | Hardware | Scope |
|---|---|---|---|---|
| bridge | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/results.json) | NOT-RUN | Simics 16-word loopback; physical fabric endpoint still required. |
| ccu | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| clk_mngr | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| combophy | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-other/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/upstream26-examples) | Current 26.3 implementation; not qualified by legacy results. |
| crc | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/qemu/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-other/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/upstream26-examples) | Current 26.3 implementation; not qualified by legacy results. |
| ddr | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/upstream26-clean-checkout/results.json) | NOT-RUN | Current OCRAM console DDR validation; separate physical bootstrap listed below. |
| dma | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| ecc | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| fcs | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| gic | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/upstream26-clean-checkout/results.json) | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| gpio | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| hello | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/upstream26-clean-checkout/results.json) | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| i2c | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| i3c | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| iossm | NOT-SUPPORTED | [PARTIAL](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/results.json) | NOT-RUN | Simics image readback passes; ECC injection/clear rejected and recovery unqualified. |
| mailbox | NOT-SUPPORTED | [PARTIAL](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-runtime/results.json) | Simics NOOP/config pass, GET_IDCODE rejected; physical TF-A path passes all three. |
| mmu | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| noc | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-other/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/upstream26-examples) | Current 26.3 implementation; not qualified by legacy results. |
| perf | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/qemu/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-runtime/results.json) | CPU memory correctness; physical 400 MHz counter checked against host time. Diagnostic rates, not optimized DDR bandwidth. |
| reboot_mngr | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/results.json) | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| reset_mngr | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-other/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/upstream26-examples) | Current 26.3 implementation; not qualified by legacy results. |
| sdmmc | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| seu | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| smmu | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| spi | NOT-SUPPORTED | NOT-RUN | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |
| timer | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/upstream26-clean-checkout/results.json) | NOT-RUN | Current 26.3 implementation; not qualified by legacy results. |

## Original Modular suite

| Example | QEMU | Simics | Hardware | Scope |
|---|---|---|---|---|
| core | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | CPU/NEON, cache discovery, DDR copy, GPIO/counter/GIC reads; no coherency proof. |
| dma | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | 4096-byte linked-descriptor DMA copy; complete data readback. |
| gic | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Polled secure SGI acknowledgement; not exception delivery. |
| interfaces | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Ethernet PHY, SD/card-detect and USB controller identification only. |
| mailbox | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Direct SDM GET_IDCODE, separate from TF-A mailbox API. |
| mmu | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | EL3 identity translation and DDR access. |
| multicore | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Direct reset/power release; three secondary identity records; not PSCI. |
| som | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Peripheral timer, watchdog interrupt-first mode, SPI loopback, LED pad, I2C IDs. |
| som-i2c | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | GPIO I2C sensor ID and EEPROM reads; no EEPROM array writes. |
| som-i3c | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | I3C controller legacy-I2C sensor/EEPROM reads; no native I3C qualification. |
| vendor-ccu | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Pinned 25.1 vendor adaptation; register/identity checks, with recorded ES warnings. |
| vendor-clkmgr | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Pinned 25.1 vendor adaptation; register/identity checks, with recorded ES warnings. |
| vendor-ecc | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Pinned 25.1 vendor adaptation; register/identity checks, with recorded ES warnings. |
| vendor-smmu | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Pinned 25.1 vendor adaptation; register/identity checks, with recorded ES warnings. |
| vendor-uart | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/results.json) | Pinned 25.1 vendor adaptation; register/identity checks, with recorded ES warnings. |

## Additional vendor board adapters

| Example | QEMU | Simics | Hardware | Scope |
|---|---|---|---|---|
| vendor-timer | NOT-SUPPORTED | NOT-RUN | COMPILE-ONLY | Compiled adapter; not one of the 15 qualified board-suite entries. |
| vendor-watchdog | NOT-SUPPORTED | NOT-RUN | COMPILE-ONLY | Compiled adapter; not one of the 15 qualified board-suite entries. |
| vendor-spi | NOT-SUPPORTED | NOT-RUN | COMPILE-ONLY | Compiled adapter; not one of the 15 qualified board-suite entries. |
| vendor-hps_mailbox | NOT-SUPPORTED | NOT-RUN | COMPILE-ONLY | Compiled adapter; not one of the 15 qualified board-suite entries. |

## Legacy 25.1 Simics

| Example | QEMU | Simics | Hardware | Scope |
|---|---|---|---|---|
| hello-world | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| uart | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| dma | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| timer | NOT-SUPPORTED | [FAIL](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| watchdog | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| i2c | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| i3c | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| spi | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| sdmmc | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| xgmac | NOT-SUPPORTED | [FAIL](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| mmu_el3 | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| smmu | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| ccu | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| clkmgr | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| ecc | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |
| hps_mailbox | NOT-SUPPORTED | [FAIL](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26/legacy25-compatibility/results.json) | NOT-RUN | Pinned legacy reference; modeled peripherals/targets differ from the physical SOM. |

## Shared CPU and practice labs

| Example | QEMU | Simics | Hardware | Scope |
|---|---|---|---|---|
| Hello / NEON / memory copy | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/tutorial/results.json) | NOT-RUN | NOT-RUN | Original QEMU smoke exercise. |
| startup | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Shared checks with platform-specific startup/UART/memory map. |
| corruption | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Shared checks with platform-specific startup/UART/memory map. |
| exception | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Shared checks with platform-specific startup/UART/memory map. |
| timer | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Ten actual secure timer FIQs through GIC; not a calibrated speed benchmark. |
| mmu | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Shared checks with platform-specific startup/UART/memory map. |
| uart | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Eleven command, editing, boundary and recovery input cases. |
| multicore | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/qemu-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/simics-practice/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-practice/results.json) | Three secondary execution/identity records; platform-specific release; not PSCI CPU_ON. |

## Additional diagnostics and integration

| Example | QEMU | Simics | Hardware | Scope |
|---|---|---|---|---|
| smc-guard | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/qemu/results.json) | NOT-RUN | NOT-RUN | Precondition/failure-detection control; counted once, not each assertion. |
| perf-zero-clock | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/qemu/results.json) | NOT-RUN | NOT-RUN | Precondition/failure-detection control; counted once, not each assertion. |
| Lightweight bridge control | NOT-SUPPORTED | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/results.json) | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-runtime/results.json) | Enable/disable only; no fabric-memory access. |
| OCRAM UART Hello | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/../../docs/examples/ocram.md) | Standalone physical-board UART, no DDR prerequisite. Historical execution documented; raw OCRAM UART trace not packaged. |
| DDR bootstrap and Hello | NOT-SUPPORTED | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform/hardware-runtime/restore-bootstrap.log) | Matching physical handoff; 64 MiB patterns and DDR execution. Not full 8 GiB qualification. |
| OCRAM semihosting Hello | NOT-RUN | NOT-RUN | REFERENCE | Source reference, not qualified execution. |
| PSCI CPU_ON wrapper | NOT-RUN | NOT-RUN | COMPILE-ONLY | Requires a resident PSCI firmware and nonsecure caller. |
| Fault probe | NOT-SUPPORTED | NOT-RUN | COMPILE-ONLY | Built diagnostic; separate execution qualification not established. |
| UDP / TCP bandwidth | NOT-RUN | NOT-RUN | [PASS](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/ethernet/README.md) | Custom lwIP/XGMAC2 adapter; actual physical link, distinct from legacy XGMAC sample. |
| ADD fabric IP / C driver | NOT-RUN | NOT-RUN | NOT-RUN | Verilator C-driver/RTL co-simulation passed; physical deployment and simulator MMIO models unqualified. |
| XOR fabric IP / C driver | NOT-RUN | NOT-RUN | NOT-RUN | Verilator C-driver/RTL co-simulation passed; physical deployment and simulator MMIO models unqualified. |
| Partial reconfiguration persona swap | REFERENCE | REFERENCE | REFERENCE | Reference integration workflow; no live PR qualification. |
