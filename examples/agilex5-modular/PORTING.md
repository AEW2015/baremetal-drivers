# Demonstrated board adaptations

These notes describe the tested Modular ES profile. Keep matching FPGA/handoff,
ATF and software versions explicit when using a different kit revision.

- **Startup:** skip the simulation CPU-init hook after the diagnostic bootloader
  has initialized DDR. Establish BSS, FP/SIMD access, a reserved stack and EL3
  exception vectors. In the vendor adapter select SP_EL3 before setting the stack;
  otherwise an EL3T application can fault into an uninitialized SP_EL3 and hide
  the original exception with recursive faults.
- **UART:** preserve the bootstrapped divisor across vendor `uart_init`; its
  simulation divisor is inappropriate for this clock tree. The OCRAM-only source
  separately uses the tested handoff and divisor 54.
- **libc write contract:** the original `_write` inserts CR before LF but returns
  the expanded UART count. Newlib requires the number of input bytes consumed.
  The wrapper streams output without a variable-length stack array and returns
  the original `len`. This allowed CCU/ECC/SMMU output to advance past early lines.
- **Alignment:** a captured CCU exception had ESR_EL3 `0x96000021`, an ELR in
  newlib's AArch64 `memcpy.S:117`, and an unaligned normal-memory FAR. The
  diagnostic bootstrap had left SCTLR_EL3.A enabled. The vendor wrapper enables
  its verified identity map, clears alignment checking and data-cache enable,
  and uses normal noncacheable DDR with device attributes below 2 GiB. The
  library's unaligned normal-memory accesses then work; MMIO remains device memory.
- **DMA:** wait for an actual completion bit using AND, then compare every word.
  The sample's OR-based condition could falsely report completion. Reserve all
  descriptor/buffer ranges and keep D-cache off for this example.
- **GIC-600:** power up the redistributor through GICR_PWRR before clearing WAKER.
  The original wake-only sequence timed out; the corrected polled SGI test passes.
- **Multicore:** use the matching ATF power/reset sequence, publish MIDR/MPIDR and
  park secondary cores outside reloadable code at 0x82010000. This is direct EL3
  release, not PSCI or a cache-coherency test.
- **Management bus:** IOA9/10 selector 0 is I3C1, 4 is baseline I2C_EMAC1, 8 is
  GPIO0 and 9 is HCLK. These are per-pin values from Quartus `sm_handoff.tcl`.
  The GPIO repeated START must release SDA before raising SCL. The corrected
  GPIO and native I3C1 legacy-I2C tests both read TMP464 and EEPROM.
- **SMMU:** the sample checks IIDR with bitwise AND; the wrapper instead requires
  the exact SOM value `0x4832243b`. Relative to simulation `0x4832143b`, only the
  revision field differs (2 rather than 1). Field definitions are in the primary
  [Linux Arm SMMUv3 header](https://github.com/torvalds/linux/blob/master/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h).
  This does not establish working translation.
- **USB:** the SOM controller reports `0x33313130`, a DWC_usb31 ID. A USB3.0-only
  `0x5533` test incorrectly rejected it. Controller ID is not enumeration.
- **Timing:** CNTFRQ was zero, so the generic-counter example checks advancement
  only. Peripheral timer completion uses expiry status instead of expecting an
  instantaneous periodic counter value of zero. Watchdog1 is held in peripheral
  reset before its second interrupt-first timeout.

## Recovery lesson

An experimental selector 9 on the management pins selected HCLK and disrupted
HPS clocking/UART. HPS programming failed at location 0x00011880, and the memory
AP could not examine. Repeating HPS-only and merged programming did not recover
that clock-stalled state. A fabric-only helper could program but did not prove
HPS recovery.

A physical power cycle followed by the merged matching SOF restored the board.
All four DDR patterns passed and the PC was verified at 0x82000024. The selected
[recovery proof](validation/post-powercycle.txt) is included. Correct the pinmux
from the authoritative per-pin table before retrying. A raw HPS-enabled SOF
without an embedded bootloader was rejected as incomplete; the DDR build creates
an appropriate merged volatile recovery image. No flash/SD/EEPROM-array or clock
NVM writes were part of this recovery.

The host runner handles UART EAGAIN after select, EOF disconnects and owned
programmer cleanup. Always check fresh UART markers and a DDR PC, rather than
inferring recovery from a successful FPGA-only programmer operation.

## Source provenance

The vendor baseline is `altera-fpga/baremetal-drivers` commit
`1419101568f1a9034630b632634fe9fe71773266` (also upstream main at packaging time).
The initialization hook targets ATF 26.1.1 commit
`2ea5afda7f34774ddcc677fb3a728fa57f780a1e` and includes a small patch rather than a
copy of ATF. ATF retains its own upstream licensing. The OpenOCD configuration
and approach follow Altera's [25.1 bare-metal guide](https://altera-fpga.github.io/rel-25.1/baremetal-embedded/agilex-5/e-series/premium/ug-baremetal-agx5e-premium/).
Board pin mappings come from the publisher schematics linked in HARDWARE.md.
These example additions are provided under the repository's MIT license.
