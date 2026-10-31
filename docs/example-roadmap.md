# Missing-example TODO roadmap

Use **HPS DDR bank 3A** for memory-backed labs. Separate fabric DDR/EMIF is
excluded. This checklist tracks the **23 architecture blocks** originally marked
without an associated example in the [clickable diagram](architecture.md).
Some are parent groups or parts of one subsystem, so they do not require 23
independent applications. The checkboxes below track example implementation and
its stated model/bench evidence, not blanket physical-block qualification.
The new [memory and fabric labs](memory-fabric-labs.md) have source, captured
outputs and separate platform results. Physical acceptance remains a separate
checklist below; source association in the diagram does not imply hardware PASS.

## 1. Review existing evidence and associations

Estimated effort: a few days including the basic diagnostics in phase 2.
An association update must identify the exact existing binary, result and path
exercised; it must not introduce a new hardware PASS.

- [x] **SOM UART connection** (`/SOM_IO/UART_USB`): associate the existing SOM
  J2 HPS UART transmit/Hello evidence with the UART side of this combined
  UART/USB node. This supports console transmission at J2; it does not cover
  USB or UART receive. See the [mapping review](example-mapping-audit.md).
- [ ] **Ethernet PHY interface** (`/HPS/PSS/Peripherals/EMAC_PHY_interface`):
  the recorded board Ethernet route is EMAC2 RGMII/MDIO to the SOM Marvell
  88E1512, represented by the distinct
  `/HPS/PSS/Peripherals/EMAC_RGMII_interface` diagram node and backed by the
  physical Ethernet example. The architectural SERDES/PHY option remains uncovered;
  do not transfer RGMII evidence to it. This review remains open for the
  separate PHY/SERDES node.
- [x] **PSI** (`/HPS/PSS/PSI`): associate the existing mailbox/SDM service path
  with PSI. The result proves that those mailbox requests completed over the
  service path; it is not a dedicated PSI protocol or link test. See the
  [mapping review](example-mapping-audit.md).
- [x] **Simics modeled RAM** (`/Fabric/Simics_reference/RAM`): identify the
  configured behavioral target as `example_design.design_memory`, a 1 MiB
  array of 32-bit read/write registers connected behind the Simics HPS2FPGA
  loopback at `0xC0000000` within a 256 MiB bridge window. The captured test
  writes and verifies 16 64-bit words (128 bytes) at the route base; it
  qualifies only those transactions, not the entire memory or physical fabric.
  See the [mapping review](example-mapping-audit.md) and
  [captured bridge transcript](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/bridge/uart.txt).
- [x] **Simics fabric parent** (`/Fabric/Simics_reference`): associate only
  the supported RAM and PIO child-model coverage. This is a derived parent
  mapping, not an additional standalone test or blanket coverage of the fabric.

## 2. Add basic configuration and memory labs

- [x] **Pin mux** (`/HPS/PSS/Pin_mux`): recorded read-only snapshots pass in
  Simics and on the physical Modular ES. `PIN2SEL`, `PIN3SEL`, and
  `UART0_USEFPGA` match the supplied matching big-endian handoff. This checks
  three UART-route fields, not every pin/clock route. The negative control also
  confirms unstable reads are rejected. See the
  [configuration audit](config-audit.md) and its
  [separate evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/config-audit).
- [x] **System Manager** (`/HPS/PSS/System_Modules/System_Manager`): recorded
  Simics and physical read-only snapshots show three selected fields are
  readable and stable, with `SILICONID1=0x30000`, `SILICONID2=0`, and
  `MPU_STATUS=0`. This is a snapshot report, not full System Manager
  qualification. See the [configuration audit](config-audit.md) and its
  [separate evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/config-audit).
- [x] **DSU / shared L3 prototype** (`/HPS/MPU/DSU`): cached producer/consumer,
  full payload verification, per-core MMU/cache attributes, corruption/timeout
  controls and contention pass in QEMU, Agilex Simics and physical Modular ES.
  The physical L3 policy run verifies `PARTCR` 0→`0x1e`→0, per-core policy
  restoration and secondary quiescence. This qualifies functional coherency and
  policy readback/restoration, but not cache-way occupancy or a statistical
  speedup. Keep the performance comparison unchecked until matched repeated
  baseline/partitioned measurements are analyzed. Raw evidence: [four DSU
  cases](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/hardware/memory-dsu/)
  and [L3 partition](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/hardware/l3-partition/).
- [x] **MPFE NoC benchmark software** (`/DDR_IO96/MPFE/NoC`): 64 KiB–16 MiB
  read/write/copy and dependent-load sweeps pass all 20 samples and both failure
  controls in QEMU and Simics, and the physical Modular ES `ddr-calibrated` and
  `ddr-path` sweeps pass all 20 samples with both fault controls rejected. The
  independent host interval is 0.9920008089 s for the nominal one-second
  counter interval (0.9–1.1 s gate). Cache state and raw ticks are explicit.
  This is scalar Normal Noncacheable CPU-path evidence; no peak MPFE throughput
  or DDR-pin bandwidth result is claimed. See [physical DDR evidence](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/hardware/memory-ddr/).
- [x] **Simics PIO** (`/Fabric/Simics_reference/PIO`): the recorded Simics
  guest reads modeled button/switch inputs (static zero values), checks two
  LED patterns by readback, and restores the initial LED state. A negative
  case rejects an intentionally incorrect expected mask. This establishes
  model register access only; no physical buttons, switches, or LEDs were
  qualified. See the [model audit source and validation](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/model-audit/validation).

See the [memory/fabric results](memory-fabric-labs.md) for commands and evidence.

## 3. Add real USB communication

- [ ] **SOM USB connection** (`/SOM_IO/USB_port`): identify the connector, role,
  cable, power requirements and known test device/host; add enumeration and
  checked data transfers. A source-built U-Boot bare-metal image has booted on
  the board using a bounded 128 MiB DDR window; its xHCI controller-not-ready
  timeout currently prevents external USB enumeration. No Linux OS was booted.
  The maintained U-Boot USB stack has intended hub, HID, storage, and candidate
  USB-Ethernet support, but enumeration and class traffic remain unproven. In
  the latest controlled retry, normal vendor USB3 PIPE-power bit 14 was restored
  (`USB3_MISC0` `0x07c00c11` → `0x07c04c11`, `PER0MODRST=0`); xHCI still timed
  out waiting for CNR with `USBSTS=0x00000801` and error `-110`. The change did
  not resolve the issue or identify its cause. PHY, PIPE-clock, and board-control
  behavior remain under investigation. Clean-power-cycle and flash retries
  reproduced the CNR and ULPI failures. A full-SPL experiment stopped at
  `spl_early_init`; the established DDR Hello was restored. No enumeration or
  transfer passed. The standalone
  SDK currently has only a USB controller-ID result.
  See the [USB bring-up record](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/usb-bringup/README.md).
- [ ] **USB PHY interface** (`/HPS/PSS/Peripherals/USB_PHY_interface`): establish
  the actual PHY path used by that setup and associate its physical evidence.
  Controller identification is not PHY or external-device communication.
  The current xHCI CNR timeout blocks external enumeration, so this PHY
  association is also pending; the PIPE-power retry above did not identify the
  root cause. See the
  [USB bring-up record](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/usb-bringup/README.md).

This work requires a suitable external USB setup. Enumeration, checked HID
reports, USB-Ethernet traffic, and read-only storage access each need separate
evidence. Simulator coverage must state which device behavior is actually
modeled.

## 4. Exercise translation and fabric access to HPS DDR

Estimated effort: several weeks, depending on FPGA integration and board
availability. One shared translation harness may cover several entries, but
each transaction source/path needs its own evidence.

- [x] **TCU model lab** (`/HPS/APS/TCU`): nonidentity stage-2 translation and
  unmapped faults pass with real QEMU SMMUv3/EDU DMA and native Agilex Simics
  TBU paths. Simics tests use cache-disabled fresh walks; architectural queue
  acknowledgement/TLBI and physical TCU qualification remain separate gates.
- [ ] **I/O TBU** (`/HPS/PSS/IO_TBU`): identify a supported transaction source
  and prove it uses the intended translation path.
- [x] **DMA TBU model lab** (`/HPS/PSS/DMA_TBU`): an Arm guest programs the real
  Simics DMAC0 model for a nonidentity 4096-byte copy and destination fault.
  Native fault SID/address, full guards, no false completion and controller
  cleanup pass. The host configures model tables; this is not a physical driver
  port or a Python-issued DMA substitute.
- [ ] **EMAC TBU** (`/HPS/PSS/EMAC_TBU`): extend Ethernet tests to cover the
  intended translated DMA path and checked descriptor/buffer access.
- [ ] **SDM TBU** (`/HPS/PSS/SDM_TBU`): first establish supported software control
  and a usable transaction source; document limitations if independent testing
  is unavailable.
- [x] **F2H TBU model lab** (`/HPS/APS/F2H_TBU`): actual Verilator AXI traffic
  driven by an Arm C driver passes nonidentity translation and unmapped faults
  through the native Simics ingress, with destination and alias guards checked.
- [x] **F2SDRAM TBU model lab** (`/DDR_IO96/MPFE/F2SDRAM_TBU`): the same actual
  RTL/driver passes the separate native ingress's valid and fault cases. The
  observed model default SID is not proof of physical AXUSER-to-SID wiring.
- [x] **FPGA-to-SDRAM initiator prototype** (`/DDR_IO96/MPFE/FPGA2SDRAM`): the
  guarded AXI master, C driver, CSR map, Platform Designer component and
  Simics/Verilator memory tests are implemented. Matching full-board fit,
  physical bridge integration and hardware readback remain pending.

The fabric memory path for these labs is:

```text
Fabric traffic generator → FPGA-to-SDRAM bridge → MPFE → HPS DDR bank 3A
```

No separate fabric DDR controller is required for this scope. CPU loads or
ordinary DMA completing successfully do not establish TBU translation coverage.
Keep generated traffic within the reserved scratch range, preserve the matching
handoff, and use the shared hardware mutex for physical execution.

## 5. Resolve conditional interfaces and hardware

- [ ] **Serial Controller** (`/HPS/PSS/System_Modules/Serial_Controller`): identify
  its documented software interface and supported operations before promising
  a standalone lab; this is not another UART controller example.
- [ ] **Secure Manager** (`/HPS/PSS/System_Modules/Secure_Manager`): establish the
  documented access/firmware requirements and choose a supported nonpersistent
  operation with meaningful completion checks.
- [ ] **NAND** (`/HPS/PSS/Peripherals/NAND`): verify whether usable NAND is
  connected on this SOM/design. If absent, document that dependency and assess
  simulator coverage; do not claim a physical NAND example from an ID read.

## Physical acceptance still pending

- [x] Run cached multicore integrity and shared-versus-partitioned contention
  on Modular ES with policy restoration and secondary cleanup. This establishes
  functional coherency and policy readback/restoration, not cache-way occupancy
  or a statistical performance difference.
- [x] Run the HPS DDR sweep with the independent host counter-rate check. The
  physical coarse interval passed; retain raw ticks and scope results to the
  scalar noncacheable path, without peak MPFE or DDR-pin bandwidth claims.
- [ ] Analyze matched repeated baseline/partitioned measurements before making
  any DSU performance comparison or speedup claim.
- [ ] Port SMMU setup to the supported hardware initialization/queue sequence
  and verify real DMAC0 translation/fault routing and stream assignment.
- [ ] Fit and deploy the fabric initiator after the reserved OpenTPU build
  window, using a verified CSR/master map and the matching HPS handoff.
- [ ] Verify both physical fabric TBU paths, faults and guards on HPS DDR bank 3A.
- [ ] Resolve USB controller/PHY startup and obtain actual hub/class traffic.
  Clean-power-cycle and flash retries reproduced CNR/ULPI failures; full SPL
  stopped at `spl_early_init`. DDR Hello was restored, but enumeration and
  transfers remain unqualified.

## Completion evidence for each lab

- [ ] Add source, build/run commands, dependencies and platform support limits.
- [ ] Include actual terminal output, artifact/source identity and expected
  success/failure status; add a meaningful negative control where applicable.
- [ ] Record QEMU, Simics and hardware outcomes separately. A build is not an
  execution PASS; modeled behavior is not a physical I/O measurement.
- [ ] Update the catalog, exact block associations, tutorial and diagram tests.
  Remove a missing-example marker only when an association is justified.
- [ ] Restore the established hardware state after physical tests and retain
  the restoration result with the run evidence.

## Separate Simics and Verilator example

The [Simics-to-Verilator tutorial](simics-rtl.md) and working example now run
the unchanged AArch64 fabric driver against the actual ADD/XOR RTL. The Simics
I/O-memory callback sends synchronous MMIO transactions to a Verilator child;
the recorded positive and fault-injection cases pass. It does not provide
continuous-cycle HPS/RTL simulation, physical bridge validation, or a Questa
backend. A separate guided-user walkthrough remains a documentation task; the
example and its validation are available now.
