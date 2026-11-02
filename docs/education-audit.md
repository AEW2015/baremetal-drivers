# Education and example discovery audit

This review inventories all 94 registered source entries and manually examines
representative first lessons, hardware checks and host orchestration. It does
**not** certify every implementation against a formal coding standard. Historical
execution results remain attached to their original artifacts.

The [educational coding standard](educational-coding-standard.md) defines a
lesson contract, readable C/Python, explicit platform assumptions, independent
verification, bounded waits and useful failure/recovery messages.

## Findings and changes

| Finding | Action and scope |
|---|---|
| First QEMU lesson compressed register I/O, loops and checks into single lines | Reworked `qemu/hello.c` with named addresses/masks, four-space indentation, braces and arrange/act/verify phases; kept GDB symbols and completion markers |
| Peripheral polling in the first lesson had no guest-side bound | Added a bounded PL011 transmit wait with nonzero semihosted exit if output stalls; the host runner retains its independent timeout |
| Corruption exercise depended on exact dense loop text | Added explicit injection anchors and a checked single-replacement helper; retained independent NEON/memory failure cases and final-word corruption |
| Website's original overview covered mainly the original SOM suite | Added a finder for all 94 entries with topic, family and verified-platform filters; tutorial, source, diagram and evidence links share the existing catalog |
| Diagram platform control only emphasized badges | Kept that control and added a distinct full-PASS filter, including the intersection of Simics and hardware, plus a browsable matching-example list |
| New students had to infer directories and host/container context | Added a three-platform Hello page with current bench paths, build/run commands, expected output and recovery requirements |
| Landing page still described live PR as unvalidated | Linked the matched 26.3 ADD–XOR–ADD qualification while retaining the separate proposed core's unqualified scope |
| Advanced local C and host scripts use dense one-line code | Recorded for incremental refactoring; this change does not rewrite hardware algorithms or renew their physical execution claims |

The finder and diagram use the same exact-PASS predicate. Partial, build-only,
reference and unexecuted rows never satisfy a “Passed on” filter. Search includes
scope and block paths, and the finder URL preserves filters for sharing. Empty
results and a JavaScript-free catalog fallback are explicit.

## Manual review sample

| Source | Useful teaching property | Remaining concern |
|---|---|---|
| `qemu/hello.c` | Separate NEON and full-copy checks, observable GDB variables, explicit QEMU-only MMIO | This is a generic CPU lesson, not an Agilex peripheral model |
| `qemu/experiment.py` | Isolated scratch copies, required guest exit and contradictory-result rejection | Additional advanced experiment scripts still use compact Python |
| `core/dma_copy.c` | Cache precondition, bounded completion polling and full destination readback | Register bit encodings and multiple statements need a focused readability pass |
| `core/mailbox_status.c` | Idle-ring precondition, bounded response reads and exact response validation | Short names and inline register offsets obscure the queue protocol |
| `memory-labs/ddr/ddr.c` | Explicit cache/timer state, readback and restored translation state; no peak-bandwidth claim | Dense setup code should be split into annotated setup/measure/restore helpers |
| `upstream-lab/hardware.py` | Ownership, fresh bootstrap, byte-for-byte readback and restoration; discovery cancellation tests | Large orchestration function should be split incrementally with lifecycle regressions |
| `examples/hello/hello_selftest.c` | Small shared upstream command | Registration macro is implicit for beginners; the new Hello page identifies the wrapper/build path |

## Validation of this change

The rewritten QEMU lesson passed its positive run, deliberate NEON and last-word
corruptions, corrected expectation and recovery. GDB stopped at `main` and
`qemu_done`, showing status 0, failures 0, `{11, 22, 33, 44}` and matching final
memory words. All 109 unit tests passed with the real-QEMU check enabled.

Chromium checks cover all 94 diagram selections, navigation and the new PASS
filter, plus the finder platform intersections, family/topic search, URL reload,
empty state, source/diagram links and mobile width. Strict MkDocs and catalog
consistency checks pass. [Captured validation](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/education-20261102)
records the fresh QEMU artifact. Hardware and Simics were not rerun for this
presentation change; their original results and limitations remain distinct.

## Prioritized follow-up

1. Refactor the local DMA and mailbox lessons with named register fields and
   annotated protocol steps, then rebuild and rerun their physical checks.
2. Split DDR setup/measurement/restoration and hardware orchestration into
   readable helpers while preserving timeouts, ownership and independent checks.
3. Add explicit prerequisites, resources and a deliberate failure exercise to
   each advanced lesson. Review external-device/storage effects per exercise.
4. Keep vendor/reference snapshots unchanged; teach adaptations in local wrappers
   and link to the upstream implementation and tested artifact separately.

The metrics below flag review candidates. Long lines may be valid register
expressions, generated command strings or declarations; they are not proof of a
bug. Conversely, short lines are not proof of clear or correct teaching code.

<!-- source-inventory:start -->
## Source inventory

All **94** registered entry paths exist. This census lists source coverage,
rather than certifying every implementation. Directory entries can overlap;
legacy loader entries do not include their fetched vendor dependency.

| Example | Source entry | Source files inventoried | Lines over 100 columns |
|---|---|---:|---:|
| `upstream/bridge` | [examples/bridge](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/bridge) | 1 | 0 |
| `upstream/ccu` | [examples/ccu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/ccu) | 1 | 0 |
| `upstream/clk_mngr` | [examples/clk_mngr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/clk_mngr) | 1 | 0 |
| `upstream/combophy` | [examples/combophy](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/combophy) | 1 | 1 |
| `upstream/crc` | [examples/crc](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/crc) | 1 | 0 |
| `upstream/ddr` | [examples/ddr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/ddr) | 1 | 0 |
| `upstream/dma` | [examples/dma](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/dma) | 1 | 0 |
| `upstream/ecc` | [examples/ecc](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/ecc) | 1 | 0 |
| `upstream/fcs` | [examples/fcs](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/fcs) | 1 | 0 |
| `upstream/gic` | [examples/gic](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/gic) | 1 | 0 |
| `upstream/gpio` | [examples/gpio](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/gpio) | 1 | 0 |
| `upstream/hello` | [examples/hello](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/hello) | 1 | 0 |
| `upstream/i2c` | [examples/i2c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/i2c) | 1 | 0 |
| `upstream/i3c` | [examples/i3c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/i3c) | 1 | 0 |
| `upstream/iossm` | [examples/iossm](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/iossm) | 1 | 3 |
| `upstream/mailbox` | [examples/mailbox](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/mailbox) | 1 | 0 |
| `upstream/mmu` | [examples/mmu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/mmu) | 1 | 0 |
| `upstream/noc` | [examples/noc](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/noc) | 2 | 0 |
| `upstream/perf` | [examples/perf](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/perf) | 1 | 5 |
| `upstream/reboot_mngr` | [examples/reboot_mngr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/reboot_mngr) | 1 | 0 |
| `upstream/reset_mngr` | [examples/reset_mngr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/reset_mngr) | 1 | 0 |
| `upstream/sdmmc` | [examples/sdmmc](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/sdmmc) | 1 | 0 |
| `upstream/seu` | [examples/seu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/seu) | 1 | 0 |
| `upstream/smmu` | [examples/smmu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/smmu) | 1 | 0 |
| `upstream/spi` | [examples/spi](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/spi) | 1 | 0 |
| `upstream/timer` | [examples/timer](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/timer) | 1 | 0 |
| `board/core` | [examples/agilex5-modular/core/core_examples.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/core_examples.c) | 1 | 3 |
| `board/dma` | [examples/agilex5-modular/core/dma_copy.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/dma_copy.c) | 1 | 2 |
| `board/gic` | [examples/agilex5-modular/core/gic_sgi.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/gic_sgi.c) | 1 | 0 |
| `board/interfaces` | [examples/agilex5-modular/core/som_interfaces.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/som_interfaces.c) | 1 | 3 |
| `board/mailbox` | [examples/agilex5-modular/core/mailbox_status.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/mailbox_status.c) | 1 | 2 |
| `board/mmu` | [examples/agilex5-modular/core/mmu_translation.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/mmu_translation.c) | 1 | 0 |
| `board/multicore` | [examples/agilex5-modular/core/multicore.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/multicore.c) | 1 | 1 |
| `board/som` | [examples/agilex5-modular/core/som_peripherals.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/som_peripherals.c) | 1 | 3 |
| `board/som-i2c` | [examples/agilex5-modular/core/som_i2c.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/som_i2c.c) | 1 | 3 |
| `board/som-i3c` | [examples/agilex5-modular/core/som_i3c.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/som_i3c.c) | 1 | 3 |
| `board/vendor-ccu` | [examples/agilex5-modular/core/vendor_wrapper.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/vendor_wrapper.c) | 1 | 3 |
| `board/vendor-clkmgr` | [examples/agilex5-modular/core/vendor_wrapper.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/vendor_wrapper.c) | 1 | 3 |
| `board/vendor-ecc` | [examples/agilex5-modular/core/vendor_wrapper.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/vendor_wrapper.c) | 1 | 3 |
| `board/vendor-smmu` | [examples/agilex5-modular/core/vendor_wrapper.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/vendor_wrapper.c) | 1 | 3 |
| `board/vendor-uart` | [examples/agilex5-modular/core/vendor_wrapper.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/vendor_wrapper.c) | 1 | 3 |
| `board/vendor-timer` | [examples/agilex5-modular/build_board_vendor.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/build_board_vendor.py) | 1 | 7 |
| `board/vendor-watchdog` | [examples/agilex5-modular/build_board_vendor.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/build_board_vendor.py) | 1 | 7 |
| `board/vendor-spi` | [examples/agilex5-modular/build_board_vendor.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/build_board_vendor.py) | 1 | 7 |
| `board/vendor-hps_mailbox` | [examples/agilex5-modular/build_board_vendor.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/build_board_vendor.py) | 1 | 7 |
| `legacy/hello-world` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/uart` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/dma` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/timer` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/watchdog` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/i2c` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/i3c` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/spi` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/sdmmc` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/xgmac` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/mmu_el3` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/smmu` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/ccu` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/clkmgr` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/ecc` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `legacy/hps_mailbox` | [examples/agilex5-modular/simics/legacy.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics/legacy.py) | 1 | 12 |
| `custom/qemu-hello` | [examples/agilex5-modular/qemu/hello.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/hello.c) | 1 | 0 |
| `practice/startup` | [examples/agilex5-modular/qemu/labs/startup.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/startup.c) | 1 | 1 |
| `practice/corruption` | [examples/agilex5-modular/qemu/labs/corruption.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/corruption.c) | 1 | 0 |
| `practice/exception` | [examples/agilex5-modular/qemu/labs/exception.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/exception.c) | 1 | 0 |
| `practice/timer` | [examples/agilex5-modular/qemu/labs/timer.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/timer.c) | 1 | 0 |
| `practice/mmu` | [examples/agilex5-modular/qemu/labs/mmu.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/mmu.c) | 1 | 0 |
| `practice/uart` | [examples/agilex5-modular/qemu/labs/uart.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/uart.c) | 1 | 0 |
| `practice/multicore` | [examples/agilex5-modular/qemu/labs/multicore.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu/labs/multicore.c) | 1 | 0 |
| `diagnostic/smc-guard` | [examples/agilex5-modular/upstream-lab/lab.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/upstream-lab/lab.c) | 1 | 2 |
| `diagnostic/perf-zero-clock` | [examples/agilex5-modular/upstream-lab/lab.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/upstream-lab/lab.c) | 1 | 2 |
| `custom/bridge-control` | [examples/agilex5-modular/upstream-lab/lab.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/upstream-lab/lab.c) | 1 | 2 |
| `custom/ocram-hello` | [examples/agilex5-modular/bootstrap/ocram/uart_local.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/bootstrap/ocram/uart_local.c) | 1 | 1 |
| `custom/ddr-hello` | [examples/agilex5-modular/bootstrap/ddr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/bootstrap/ddr) | 3 | 33 |
| `reference/semihost` | [examples/agilex5-modular/bootstrap/ocram/hello_semihost.S](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/bootstrap/ocram/hello_semihost.S) | 1 | 0 |
| `reference/psci` | [examples/agilex5-modular/core/secondary_core.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/secondary_core.c) | 1 | 0 |
| `custom/fault-probe` | [examples/agilex5-modular/core/fault_probe.c](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/core/fault_probe.c) | 1 | 0 |
| `custom/ethernet` | [examples/agilex5-modular/ethernet](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/ethernet) | 11 | 96 |
| `fabric/add` | [examples/agilex5-modular/fabric](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/fabric) | 44 | 192 |
| `fabric/xor` | [examples/agilex5-modular/fabric](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/fabric) | 44 | 192 |
| `reference/pr` | [examples/agilex5-modular/fabric/pr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/fabric/pr) | 31 | 170 |
| `config/sysmgr` | [examples/agilex5-modular/config-audit](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/config-audit) | 6 | 9 |
| `config/pinmux` | [examples/agilex5-modular/config-audit](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/config-audit) | 6 | 9 |
| `integration/simics-rtl-add` | [examples/agilex5-modular/simics-rtl](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics-rtl) | 8 | 44 |
| `integration/simics-rtl-xor` | [examples/agilex5-modular/simics-rtl](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/simics-rtl) | 8 | 44 |
| `model/pio` | [examples/agilex5-modular/model-audit](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/model-audit) | 4 | 9 |
| `memory/dsu` | [examples/agilex5-modular/memory-labs/dsu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/dsu) | 6 | 20 |
| `memory/l3-partition` | [examples/agilex5-modular/memory-labs/dsu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/dsu) | 6 | 20 |
| `memory/ddr-sweep` | [examples/agilex5-modular/memory-labs/ddr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/ddr) | 5 | 27 |
| `memory/smmu-qemu` | [examples/agilex5-modular/memory-labs/smmu](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/smmu) | 10 | 51 |
| `memory/native-tbu` | [examples/agilex5-modular/memory-labs/smmu/native_fixture.py](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/smmu/native_fixture.py) | 1 | 3 |
| `memory/dma-tbu` | [examples/agilex5-modular/memory-labs/smmu/dmac](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/smmu/dmac) | 4 | 23 |
| `memory/fabric-ddr` | [examples/agilex5-modular/memory-labs/fabric-ddr](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/fabric-ddr) | 14 | 92 |
| `custom/usb-host` | [examples/agilex5-modular/usb-bringup](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/usb-bringup) | 11 | 115 |

Regenerate with `python3 tools/education/audit_examples.py`.
The JSON record includes per-file source hashes and metrics.
<!-- source-inventory:end -->
