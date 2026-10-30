# Missing-example TODO roadmap

Use **HPS DDR bank 3A** for memory-backed labs. Separate fabric DDR/EMIF is
excluded. This checklist tracks the **23 architecture blocks** originally marked
without an associated example in the [clickable diagram](architecture.md).
Some are parent groups or parts of one subsystem, so they do not require 23
independent applications. Seven coverage items are now supported by recorded
evidence, leaving **16 of the original 23 tasks** open. Coverage associations
are scoped below; a model or snapshot result does not establish full block
qualification.

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
- [ ] **DSU / shared L3** (`/HPS/MPU/DSU`): build a multicore shared-memory lab
  with explicit cache/MMU attributes, synchronization and data-integrity checks.
  Identification alone does not qualify cache coherency.
- [ ] **MPFE NoC** (`/DDR_IO96/MPFE/NoC`): add controlled HPS-DDR throughput and
  latency measurements with stated working-set sizes, cache state and timing
  method. Describe effective software throughput rather than claiming peak
  physical DDR bandwidth.
- [x] **Simics PIO** (`/Fabric/Simics_reference/PIO`): the recorded Simics
  guest reads modeled button/switch inputs (static zero values), checks two
  LED patterns by readback, and restores the initial LED state. A negative
  case rejects an intentionally incorrect expected mask. This establishes
  model register access only; no physical buttons, switches, or LEDs were
  qualified. See the [model audit source and validation](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/model-audit/validation).

Allow roughly another week for meaningful memory/model labs once their setup
is established. These are planning estimates, not completion dates.

## 3. Add real USB communication

- [ ] **SOM USB connection** (`/SOM_IO/USB_port`): identify the connector, role,
  cable, power requirements and known test device/host; add enumeration and
  checked data transfers.
- [ ] **USB PHY interface** (`/HPS/PSS/Peripherals/USB_PHY_interface`): establish
  the actual PHY path used by that setup and associate its physical evidence.
  Controller identification is not PHY or external-device communication.

This work requires a suitable external USB setup. Simulator coverage must state
which device behavior is actually modeled.

## 4. Exercise translation and fabric access to HPS DDR

Estimated effort: several weeks, depending on FPGA integration and board
availability. One shared translation harness may cover several entries, but
each transaction source/path needs its own evidence.

- [ ] **TCU** (`/HPS/APS/TCU`): configure a controlled translation context and
  prove a valid mapping plus an intentional translation/permission fault.
- [ ] **I/O TBU** (`/HPS/PSS/IO_TBU`): identify a supported transaction source
  and prove it uses the intended translation path.
- [ ] **DMA TBU** (`/HPS/PSS/DMA_TBU`): compare valid translated DMA with a
  deliberately invalid mapping and check fault/completion results.
- [ ] **EMAC TBU** (`/HPS/PSS/EMAC_TBU`): extend Ethernet tests to cover the
  intended translated DMA path and checked descriptor/buffer access.
- [ ] **SDM TBU** (`/HPS/PSS/SDM_TBU`): first establish supported software control
  and a usable transaction source; document limitations if independent testing
  is unavailable.
- [ ] **F2H TBU** (`/HPS/APS/F2H_TBU`): integrate a controlled fabric traffic
  source for the corresponding fabric-to-HPS path and verify translated access.
- [ ] **F2SDRAM TBU** (`/DDR_IO96/MPFE/F2SDRAM_TBU`): establish the applicable
  translation configuration and test valid/faulting transactions from fabric.
- [ ] **FPGA-to-SDRAM bridge** (`/DDR_IO96/MPFE/FPGA2SDRAM`): build a small
  fabric traffic generator that writes/reads an explicitly reserved region of
  HPS DDR bank 3A and checks payload integrity and completion.

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
