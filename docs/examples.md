# Example catalog

Choose an example in the **Examples** navigation. Each page has **What it does**, **Build and run**, **Expected results**, and **Limits** subtabs, with source links and captured output.

Use the [clickable HPS and fabric map](architecture.md) to locate catalog
entries by block, then open their source, expected results and platform evidence.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](assets/architecture/design.html){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p>Select an example in the diagram to locate its hardware blocks.</p>
<iframe class="example-diagram" src="../assets/architecture/design.html" title="HPS and fabric diagram for examples.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Start here

| Example | Runs on | Expected result |
|---|---|---|
| [QEMU CPU/NEON/RAM](examples/qemu.md) | Generic QEMU virt | EL3, vector `{11,22,33,44}`, verified 4 KiB copy, exit 0 |
| [Shared CPU practice labs](examples/qemu-labs.md) | QEMU, Agilex Simics and the Modular kit | Startup, watchpoint, exception, timer, permissions, UART and multicore checks |
| [Simics current and legacy suites](simics.md) | Agilex 5 virtual platform | Current 26.3 console checks and separately pinned 25.1 samples |
| [OCRAM Hello](examples/ocram.md) | Modular SOM | Repeated OCRAM UART Hello; no DDR initialization |
| [DDR bring-up](examples/ddr.md) | Modular SOM | Four 64 MiB patterns, payload readback, fresh Hello and DDR PC |

The [26.3 API migration guide](upstream-26.3.md) explains the new source layout
and command catalog. The board suite below retains its pinned legacy API.

## The 15 hardware suite entries

Complete [hardware setup](hardware.md), build the selected image inside the development container, then run the selector from the configured **Linux host**:

```sh
python3 run_suite.py --only core
```

The runner freshly initializes DDR before each program and restores DDR Hello afterward. Example pages provide their exact command, ELF and recorded entry. The generic CPU practice labs also run on QEMU; SoC peripheral examples need the corresponding Agilex model or hardware profile.

| Selector | Detailed example | What to expect |
|---|---|---|
| `core` | [CPU, NEON and core checks](examples/core.md) | CPU/NEON, 64 KiB CPU copy, GPIO/counter/GIC snapshots |
| `dma` | [DMA: 4096-byte transfer](examples/dma.md) | DMAC0 completion plus 4096-byte readback |
| `gic` | [GIC: secure software interrupt](examples/gic.md) | Core 0 acknowledges secure SGI0 |
| `mmu` | [MMU: EL3 translation and readback](examples/mmu.md) | EL3 AT/PAR translation and DDR store/read |
| `multicore` | [Multicore: release A55/A76 secondaries](examples/multicore.md) | A55.1 and both A76 cores publish verified records |
| `som` | [SOM: timer, watchdog, SPI and GPIO](examples/som.md) | Timer, watchdog IRQ-first, SPI loopback, LED pad and IDs |
| `som-i2c` | [GPIO I2C: temperature sensor and EEPROM](examples/som-i2c.md) | TMP464 manufacturer 0x5449 and 16 EEPROM bytes |
| `som-i3c` | [I3C1 controller: legacy-I2C reads](examples/som-i3c.md) | Same targets through I3C1 legacy-I2C commands |
| `interfaces` | [Ethernet PHY, SD and USB identification](examples/interfaces.md) | Marvell PHY, SD controller/card detect and USB1 ID |
| Separate `ethernet/run.py` | [Ethernet UDP/TCP bandwidth](examples/ethernet.md) | Actual SOM EMAC2 packets, payload checks, rate sweeps and sustained traffic with a dedicated PC peer |
| `mailbox` | [SDM mailbox: read FPGA IDCODE](examples/mailbox.md) | SDM returns matching 0x0364f0dd device ID |
| `vendor-uart` | [Vendor UART transmit example](examples/vendor-uart.md) | Hello, World! and zero return code |
| `vendor-ccu` | [Vendor CCU register checks](examples/vendor-ccu.md) | CCU register checks complete; version warnings retained |
| `vendor-clkmgr` | [Vendor clock-manager register readout](examples/vendor-clkmgr.md) | Clock-register reads complete; default-value warnings retained |
| `vendor-smmu` | [Vendor SMMU identity check](examples/vendor-smmu.md) | Exact SOM IIDR 0x4832243b |
| `vendor-ecc` | [Vendor ECC register/default checks](examples/vendor-ecc.md) | ECC register/default checks complete; no fault injection |

## How to judge a result

Every page distinguishes fixed acceptance criteria from recorded snapshots. Temperature, EEPROM contents, counter deltas, GPIO values and SD presence can change. CCU and clock-manager PASS results can include explicitly nonfatal reference-value warnings; inspect them. A controller ID is not an end-to-end traffic test.

Require a fresh begin marker, every required result, no failure marker, a successful debugger operation and `DDR Hello restoration: pass`. The runner saves UART/debug/bootstrap logs and an ELF hash under `runs/<UTC timestamp>/`. Rebuilt binaries do not inherit the original hashes’ hardware results.

The original [15-entry hardware record](validation.md) and [tutorial debugger checks](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/tutorial) remain separate. The supplied hardware F5 launch targets the `core` ELF; use each page’s runner command for the other entries.

## Additional validation and remaining dependencies

The [2026-10-31 campaign](full-validation-2026-10-31.md) records rebuilt board-suite
results alongside QEMU, Simics and additional physical tests. The separate
[cached DSU/L3 and HPS DDR labs](memory-fabric-labs.md) now have physical results;
those capabilities are not inferred from the 15 register/SOM entries above.

The [PSCI harness](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/reference/psci)
uses `secondary_core.c` under resident BL31 from nonsecure EL2. Native Simics
verified CPU_ON, the secondary context/identity/stack, CPU_OFF and final OFF
affinity. Its physical and native Simics tests passed; the 15-entry standalone EL3 bootstrap
remains a different environment.

The [automated physical reference checks](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/hardware/references/results.json)
passed OCRAM semihost output with load/readback and stopped-PC proof, plus the
read-only `fault_probe.c` register snapshot. The latter does not inject or recover
a fault. The [USB lab](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/usb-bringup)
reaches a source-built U-Boot prompt on hardware, but xHCI CNR still times out
before enumeration. Linux boot/media recipes remain separate references.

Ethernet uses its peer-dependent runner above. USB enumeration, SD media access,
native I3C protocols, physical SMMU translation and ECC injection/recovery still
need their own passing evidence. Native model translation/fault tests are
recorded separately from physical-board qualification.

## Fabric IP extension

The optional [ADD/XOR fabric lesson](fabric-ip.md) adds a memory map, RTL,
a common bare-metal driver and full-image deployment steps. Both cores pass
RTL/driver simulation; the new fabric integration is not included in the
historical 15 board passes. The [PR integration lab](partial-reconfiguration.md)
then describes live persona replacement and its continuity checks.
