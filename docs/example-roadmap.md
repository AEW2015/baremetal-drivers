# Missing-example TODO roadmap

Use **HPS DDR bank 3A** for memory-backed labs. Separate fabric DDR/EMIF is
excluded. This checklist tracks the **23 architecture blocks** currently marked
without an associated example in the [clickable diagram](architecture.md).
Some are parent groups or parts of one subsystem, so they do not require 23
independent applications. All tasks below remain pending.

## 1. Review existing evidence and associations

Estimated effort: a few days including the basic diagnostics in phase 2.
An association update must identify the exact existing binary, result and path
exercised; it must not introduce a new hardware PASS.

- [ ] **SOM UART connection** (`/SOM_IO/UART_USB`): review the captured J2 UART
  runs and associate the appropriate UART/Hello examples if justified.
- [ ] **Ethernet PHY interface** (`/HPS/PSS/Peripherals/EMAC_PHY_interface`):
  determine which interface the SOM PHY actually uses in the tested design;
  associate evidence only with that path, not every architectural PHY option.
- [ ] **PSI** (`/HPS/PSS/PSI`): document the existing mailbox/SDM service path
  and its evidence; distinguish service completion from dedicated PSI testing.
- [ ] **Simics modeled RAM** (`/Fabric/Simics_reference/RAM`): establish the
  exact bridge-loopback target, address and configured model before associating
  an existing example or adding a dedicated memory test.
- [ ] **Simics fabric parent** (`/Fabric/Simics_reference`): review its coverage
  after the RAM/PIO children have justified mappings. This is a parent group,
  not an additional standalone peripheral test.

## 2. Add basic configuration and memory labs

- [ ] **Pin mux** (`/HPS/PSS/Pin_mux`): add a read-only routing report compared
  with the matching handoff and SOM wiring. Do not change live clock/pin routes
  merely to produce a demonstration.
- [ ] **System Manager** (`/HPS/PSS/System_Modules/System_Manager`): select
  documented readable configuration/status fields and report meaningful values.
- [ ] **DSU / shared L3** (`/HPS/MPU/DSU`): build a multicore shared-memory lab
  with explicit cache/MMU attributes, synchronization and data-integrity checks.
  Identification alone does not qualify cache coherency.
- [ ] **MPFE NoC** (`/DDR_IO96/MPFE/NoC`): add controlled HPS-DDR throughput and
  latency measurements with stated working-set sizes, cache state and timing
  method. Describe effective software throughput rather than claiming peak
  physical DDR bandwidth.
- [ ] **Simics PIO** (`/Fabric/Simics_reference/PIO`): exercise documented
  switch/button/LED model registers and record input/output readback. Physical
  PIO execution needs a matching FPGA design and separate evidence.

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

The [Simics/Verilator walkthrough TODO](https://github.com/AEW2015/baremetal-drivers/blob/main/TODO.md) remains a separate guided
session. Simics and the current host-compiled driver/Verilator harness are not
connected to one another.
