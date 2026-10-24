# Example catalog

Choose an example in the **Examples** navigation. Each page has **What it does**, **Build and run**, **Expected results**, and **Limits** subtabs, with source links and captured output.

## Start here

| Example | Runs on | Expected result |
|---|---|---|
| [QEMU CPU/NEON/RAM](examples/qemu.md) | Generic QEMU virt | EL3, vector `{11,22,33,44}`, verified 4 KiB copy, exit 0 |
| [Six QEMU practice labs](examples/qemu-labs.md) | Generic QEMU virt | Startup, watchpoint, exception, timer, permissions and UART checks |
| [OCRAM Hello](examples/ocram.md) | Modular SOM | Repeated OCRAM UART Hello; no DDR initialization |
| [DDR bring-up](examples/ddr.md) | Modular SOM | Four 64 MiB patterns, payload readback, fresh Hello and DDR PC |

## The 15 hardware suite entries

Complete [hardware setup](hardware.md), build the selected image inside the development container, then run the selector from the configured **Linux host**:

```sh
python3 run_suite.py --only core
```

The runner freshly initializes DDR before each program and restores DDR Hello afterward. Example pages provide their exact command, ELF and recorded entry. Only the separate QEMU exercise runs on generic QEMU virt.

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

## Supporting and deferred examples

`secondary_core.c` is a compile-only PSCI wrapper requiring resident BL31 and a nonsecure caller, absent in the current EL3 bootstrap. `fault_probe.c` is a manual diagnostic utility, not a peripheral qualification test. The U-Boot/Linux recipes are unexecuted setup references. Ethernet traffic, USB enumeration, SD media access, native I3C protocols, SMMU translation, ECC injection and coherent multicore sharing are not claimed by these tests.

## Fabric IP extension

The optional [ADD/XOR fabric lesson](fabric-ip.md) adds a memory map, RTL,
a common bare-metal driver and full-image deployment steps. Both cores pass
RTL/driver simulation; the new fabric integration is not included in the
historical 15 board passes. The [PR integration lab](partial-reconfiguration.md)
then describes live persona replacement and its continuity checks.
