# Existing evidence for roadmap mappings

This audit reviews the evidence already checked into the repository for the first
phase of [`example-roadmap.md`](example-roadmap.md). An architecture association
means an example exercises or is related to that portion of the diagram. It does
not by itself claim a dedicated test of every architectural function represented
by a node. A build, a model result, and a physical result also remain distinct.

## `/SOM_IO/UART_USB`: J2 UART

**Association supported:** the checked physical HPS UART examples use the SOM's
J2 HPS UART connection. `board/vendor-uart` is the most direct mapping: its
[example documentation](examples/vendor-uart.md) specifies SOM J2, 115200 8N1,
and the transmit-only sample and completion marker. The [captured UART output](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T232734.166542Z/vendor-uart-uart.txt)
contains `HPS_SUITE_PASS uart rc=0x00000000`. The board profile's [SOM/carrier
mapping](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/HARDWARE.md) distinguishes J2 HPS UART from
the carrier FTDI serial interface.

This qualifies console transmission through the documented J2 path. It does not
qualify UART receive, flow control, USB, or USB enumeration. The existing
[UART example docs](examples/vendor-uart.md) state those limits. Association to
the combined SOM UART/USB node must be understood as the UART side only.

## `/HPS/PSS/Peripherals/EMAC_PHY_interface`: current diagram is SERDES

**No association to this existing node is justified by the external SOM PHY
evidence.** The architecture source labels this node `EMAC PHY / SERDES
interface` and labels its connection `SERDES` in
[`docs/assets/architecture/design.json`](assets/architecture/design.json). The
checked board Ethernet path is different: the [board profile](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/HARDWARE.md)
identifies HPS EMAC2 RGMII and MDIO2 wired to the SOM Marvell 88E1512. The
[`interfaces` example](examples/interfaces.md) reads that PHY over MDIO; its
[captured hardware UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/remote-audit/hardware-baseline/interfaces-uart.txt)
records the expected ID. The [`ethernet` example](examples/ethernet.md) exercises
actual packet TX/RX through the SOM jack. Its validation report is
[`docs/ethernet-validation.md`](ethernet-validation.md), with raw attempts under
[`validation/ethernet/`](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/ethernet).

These results support EMAC2's external RGMII/MDIO route and its connected SOM
PHY. They do not establish a SERDES PHY interface. Keep the roadmap checkbox
pending for the current node. To represent the verified route, add a distinct
RGMII/MDIO node associated with `board/interfaces` and `custom/ethernet`, or
refactor/rename the current node only if the architecture source is intentionally
changed to model that route. Do not attach these results to every PHY option or
to the separate ComboPHY identification example.

## `/HPS/PSS/PSI`: mailbox service path, with a narrow scope

**Related-path association is supportable; dedicated PSI coverage is not.**
[`board/mailbox`](examples/mailbox.md) directly submits an SDM GET_IDCODE request
and checks its response header and ID. Its [captured output](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/mailbox-uart.txt)
records a matching IDCODE. The upstream TF-A mailbox service example also has a
physical result: [`mailbox-uart.txt`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/cross-platform/hardware-runtime/mailbox-uart.txt)
shows NOOP, GET_IDCODE, and CONFIG_STATUS passing through mailbox client #2.

This is evidence of selected mailbox/SDM service transactions along the PSI
service path, as described by the architecture source's PSI context. It is not
a dedicated PSI protocol, throughput, or full-service qualification. Keep the
association label scoped to the mailbox path and preserve that limitation. The
Simics result is partial: the [runtime-fixes report](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/runtime-fixes/README.md)
and [mailbox transcript](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/mailbox/uart.txt)
show NOOP and CONFIG_STATUS passing while GET_IDCODE is rejected by the model
with SDM error 0x3. Do not report the Simics mailbox path as a full pass.

## `/Fabric/Simics_reference/RAM`: mapped behavioral memory

**Association supported for the modeled bridge target.** The checked Simics
bridge transcript ([`uart.txt`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/bridge/uart.txt))
shows 16 64-bit words written and verified through the HPS2FPGA aperture at
`0xC0000000`; the route window is `0x10000000`. Its runtime object tree and
connections in [`terminal.log`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/runtime-fixes/simics-services/bridge/terminal.log)
identify `system.board.fpga.soc_inst.example_design.design_memory` and connect
`hps2fpga_0_down` to `example_design.design_mem_conn`. In the deployed model,
`platforms/agilex5e-universal/modules/sm-ghrd-qsys-top-comp/sm_ghrd_qsys_top_comp.py`
connects the bridge to `example_design.design_mem_conn`; the corresponding
`sm-fabric-example-design-comp/sm_fabric_example_design_comp.py` maps local
`design_mem` offset 0 to `design_memory.memory_bank` for `0x100000` bytes; and
`sm-fabric-example-design/example_design.dml` defines that bank as a 1 MiB array
of 32-bit read/write registers. Thus the observed loopback reaches this
behavioral memory model through the bridge connection.
The bridge window is 256 MiB, while the modeled memory is 1 MiB; the evidence
qualifies the tested addresses beginning at the route base, not the whole
window. It is Simics behavior, not physical FPGA fabric, HPS DDR, or real fabric
logic coverage. The independent RTL audit target at `0x20020000` is a separate
model attachment and is not involved in this mapping.

## `/Fabric/Simics_reference/PIO`: modeled register exercise

**Simics association supported.** The installed
`platforms/agilex5e-universal/modules/sm-ghrd-subsys-periph-comp/sm_ghrd_subsys_periph_comp.py`
maps `periph_mem` under LWHPS2FPGA at local offsets `0x10000` (8-byte sysid
RAM), `0x10060` (button PIO), `0x10070` (DIP switch PIO), and `0x10080` (LED
PIO); the guest-visible base used by this model is `0x20000000`. The runtime
`print-device-reg-info` capture in
[`model-register-info.txt`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/model-audit/model-register-info.txt)
shows 32-bit `DATA` registers with only bit 0 implemented for button/switch
inputs and a 32-bit LED `DATA` field covering bits 31:0. The native model
exposes button/switch `input_io` and LED `output_io` ports.

The guest source is [`pio.c`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/model-audit/pio.c).
It reads button, switches, and sysid twice, checks stability and field widths,
writes and reads back two LED patterns, and restores the prior LED value. The
[positive UART record](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/model-audit/validation/pio/uart.txt)
records successful checks. A second run deliberately uses an incomplete
expected LED mask and confirms that the known-good value fails that bad
expectation; see the [negative-control UART record](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/model-audit/validation/mask-negative/uart.txt).
The frozen [run result and hashes](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/model-audit/validation/results.json)
record both cases as pass.

This exercises modeled register access and LED readback. Button and switch
inputs read zero in these runs; no external input transition, physical PIO, or
board-level LED behavior is qualified.

## `/Fabric/Simics_reference`: parent association with child scope

**Parent association supported through the RAM and PIO children.** The bridge
loopback and PIO guest establish modeled coverage for both child targets. This
parent association summarizes those two paths only; it does not claim physical
fabric memory, real FPGA logic, or external switch/button transitions.

## Evidence inventory

The pre-association architecture coverage snapshot recorded these five targets
without associated examples in
[`architecture-ddr-coverage/results.json`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/architecture-ddr-coverage/results.json).
That snapshot is a coverage inventory, not evidence that an example passed a
new test. The findings above use the existing checked-in run captures and their
example/platform documentation; they introduce no new hardware or simulation
results.
