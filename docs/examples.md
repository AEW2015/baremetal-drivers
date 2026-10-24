# Example catalog

All commands here are **host-side hardware commands**, after the
[hardware setup](hardware.md). Only the separately ported `qemu/` exercise runs
on QEMU `virt`. Controller names shared between platforms do not imply identical
addresses, integration or behavior.

## CPU, memory and interrupt foundations

| `--only` entry | Open this source | Successful observation |
|---|---|---|
| `core` | [core_examples.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/core_examples.c) | CPU/NEON, cache geometry, CPU copy, GPIO snapshot, advancing counter, GIC ID |
| `dma` | [dma_copy.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/dma_copy.c) | Real completion bit plus all 4096 bytes match |
| `gic` | [gic_sgi.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/gic_sgi.c) | Redistributor powered, SGI0 acknowledged by polling |
| `mmu` | [mmu_translation.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/mmu_translation.c) | AT/PAR translation and DDR access with EL3 MMU enabled |
| `multicore` | [multicore.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/multicore.c) | Three secondary MIDR/MPIDR records verified |

Start with `core`, then `dma,gic,mmu`, then multicore. Generic-counter advancement
has no calibrated-delay claim because CNTFRQ was zero in the diagnostic boot.
DMA runs with D-cache off. Secondary cores park outside reloadable example code.
The separate PSCI wrapper requires resident BL31 and a nonsecure caller, absent
in this direct EL3 diagnostic.

## Actual SOM devices

| Entry | Source | Successful observation |
|---|---|---|
| `som` | [som_peripherals.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_peripherals.c) | Timer expiry, watchdog IRQ-first mode, SPI internal loopback, LED pad high/low and controller IDs |
| `som-i2c` | [som_i2c.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_i2c.c) | GPIO-I2C reads TMP464 manufacturer `0x5449` and 16 EEPROM bytes |
| `som-i3c` | [som_i3c.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_i3c.c) | I3C1 legacy-I2C mode reads the same devices |
| `interfaces` | [som_interfaces.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_interfaces.c) | Marvell PHY IDs, SD controller/card-detect and DWC_usb31 ID |
| `mailbox` | [mailbox_status.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/mailbox_status.c) | SDM returns matching FPGA IDCODE |

The management targets are SOM TMP464 `0x48` and EEPROM `0x57`; carrier devices
have other addresses. EEPROM pointer writes are used to select bytes for reading,
without writing the EEPROM array. Native I3C target protocols are not tested.
See the [schematic mapping](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/HARDWARE.md)
before changing pins or connecting another peripheral.

## Adapted vendor references

| Entry | Checked scope | Limitation |
|---|---|---|
| `vendor-uart` | Vendor UART example with board startup/divisor preservation | Transmit example, not an external loopback test |
| `vendor-ccu` | Register access and ID/default checks | ES/version warnings remain; no coherency test |
| `vendor-clkmgr` | Clock-register readout | Initialized/default warnings; no frequency measurement |
| `vendor-smmu` | Exact SOM revision-2 IIDR `0x4832243b` | No translated DMA transaction |
| `vendor-ecc` | ECC register/default checks | No injected error or recovery exercise |

The adapters establish a physical EL3 runtime, repair the libc write contract,
allow normal-memory unaligned library accesses, and report `main`'s result.
See [vendor_wrapper.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/vendor_wrapper.c)
and [porting lessons](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/PORTING.md).

Ethernet packet traffic, USB enumeration and SD media access need further setup.
The U-Boot/Linux recipes in the pack are separate, unexecuted references for a
properly configured board environment. They are not commands for the host
container. No populated NAND/eMMC was established on this SOM.
