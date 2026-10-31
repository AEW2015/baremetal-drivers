# Memory and fabric labs

These results separate functional guest tests, RTL checks and native Simics
model transactions from physical-board qualification. The board DDR results
use HPS DDR bank 3A. The OpenTPU R4 Quartus build reservation is active, so no
new full-board fit or bitstream is included here.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](assets/architecture/design.html?example=memory%2Fdsu){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=memory%2Fdsu" data-example-id="memory/dsu">memory/dsu</a> · <a href="../assets/architecture/design.html?example=memory%2Fl3-partition" data-example-id="memory/l3-partition">memory/l3-partition</a> · <a href="../assets/architecture/design.html?example=memory%2Fddr-sweep" data-example-id="memory/ddr-sweep">memory/ddr-sweep</a> · <a href="../assets/architecture/design.html?example=memory%2Fsmmu-qemu" data-example-id="memory/smmu-qemu">memory/smmu-qemu</a> · <a href="../assets/architecture/design.html?example=memory%2Fnative-tbu" data-example-id="memory/native-tbu">memory/native-tbu</a> · <a href="../assets/architecture/design.html?example=memory%2Fdma-tbu" data-example-id="memory/dma-tbu">memory/dma-tbu</a> · <a href="../assets/architecture/design.html?example=memory%2Ffabric-ddr" data-example-id="memory/fabric-ddr">memory/fabric-ddr</a> · <a href="../assets/architecture/design.html?example=custom%2Fusb-host" data-example-id="custom/usb-host">custom/usb-host</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=memory%2Fdsu" title="HPS and fabric diagram for memory-fabric-labs.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Current results

| Lab | Passed evidence | Still unqualified |
|---|---|---|
| HPS DDR path | QEMU: 20 samples and two negative controls. Native Agilex Simics: 20 samples and two negative controls. | No physical DDR timing run; model timing is not board timing. |
| DSU shared-cache handoff | Four cases pass in QEMU and four in native Simics: normal, corruption, timeout and contention. | Partitioned image compiled only; no L3 partition hardware run. |
| SMMUv3 DMA | QEMU PCI EDU: translated 4096-byte DMA round trip, unmapped S2 fault, intact guard and two negative controls. Native Simics: bare-metal guest drives DMAC0 for a translated 4096-byte copy and native SID 8 S2 fault; host configures the SMMU fixture and verifies memory. | No physical-board TCU/TBU run. Native TLB cache is disabled, so this checks fresh walks, not TLBI/ACK or full hardware-driver sequencing. |
| Fabric AXI memory probe | Verilator: actual RTL/C driver with behavioral RAM, three sizes, range/fault injection and five timeout/drain channels. Native Simics RAM: Arm C driver → Verilator AXI master, 64 writes/64 reads, CPU readback and three explicit injected failures. | No physical bridge or DDR qualification. |
| F2H / F2SDRAM translated fabric | Native Simics: actual RTL transactions through each native TBU route, with translated valid and unmapped/fault cases for both routes (four cases total). | Simics model transactions do not establish physical ingress wiring, AXUSER-to-SID mapping, board timing or fit. |
| USB host | Bare-metal controller-not-ready and ULPI PHY-ID timeout are captured. | Power cycle and fresh capture remain pending; no enumeration or transfer pass. |

## HPS DDR path

The CPU lab covers scalar read, write, copy and dependent loads across five
working sets from 64 KiB to 16 MiB. QEMU and native Simics each completed the
20-sample sweep and rejected corrupted-copy and invalid-frequency controls.
Simics runs the Agilex-target image against a model; neither emulator's timing
is physical DDR performance. The Agilex image compiled, but no physical timing
run was made.

Sources: [lab notes](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/ddr/README.md), [benchmark](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/ddr/ddr.c), [QEMU evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/ddr/validation/qemu-final), [Simics evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/ddr/validation/simics-negatives).

## DSU shared-cache handoff

Four functional cases pass on QEMU and native Simics: normal cached
producer/consumer handoff, deliberate corruption, stalled-consumer timeout and
contention workload. These are model execution results, not physical cache
coherency, L3 behavior or latency measurements. The optional partitioned image
has compiled only; it has not run on hardware.

Sources: [DSU lab and platform limits](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/dsu/README.md), [QEMU and Simics evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/dsu/validation).

## SMMUv3 translated DMA and faults

The QEMU `virt` guest programs QEMU's SMMUv3 and PCI EDU models and drives the
EDU DMA engine. It completes a nonidentity 4096-byte round trip, removes the
destination mapping, observes the real stage-2 translation fault at SID 8 and
IOVA `0x60200000`, and verifies the guard remains intact. Two deliberate
negative controls also pass. PCI EDU is not an Agilex HPS device.

A separate native Simics fixture issues host-side transactions through three
native TBU ingress models: DMA0, F2H and F2SDRAM. Each route transfers 512 bytes
from IOVA `0x85000000` to physical `0x86000000`, checks the untranslated alias
guard, then removes the mapping and observes an S2 translation fault with
guards intact. The model TLB cache is disabled, so these are fresh page-table
walk checks. They do not verify TLBI or command-queue acknowledgement: CR0ACK
remained zero. The fixture configures the modeled SMMU from the host; it does
not run the bare-metal TCU setup or perform DMA transactions itself.

A separate native DMAC0 test uses an Arm guest to program the actual modeled
DMA controller for a 4096-byte nonidentity-mapped copy, then checks every
physical destination word and raw-IOVA guards. The host fixture only configures
the SMMU tables/phase and observes the native event; Python does not issue the
DMA. After the host removes the destination mapping, the guest requires no
false DONE, a quiescent channel and the native SID 8 stage-2 fault at IOVA
`0x85200000`. The destination and raw-address guards remain unchanged, and the
guest verifies controller cleanup through register readback. This remains a
Simics model test with cache-disabled fresh walks, not a physical TCU driver,
TLBI/ACK or full hardware initialization qualification.

Sources: [QEMU and native fixture guide](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/README.md), [bare-metal QEMU guest](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/main.c), [host-side native fixture](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/native_fixture.py), [native fixture results](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/validation/simics-native-20261031T024350.917717Z/results.json), [native DMAC0 guide](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/dmac/README.md), [DMAC0 guest](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/dmac/main.c), [DMAC0 native evidence](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/smmu/dmac/validation/simics-final/results.json).

## Fabric AXI memory probe

The synthesizable probe is a bounded, single-outstanding AXI master with a
guarded range and timeout/drain handling. Verilator uses behavioral AXI RAM and
checks three sizes, range rejection, corrupted read data, BRESP/RRESP failures
and timeout behavior on AW, W, B, AR and R.

The native Simics integration runs the actual Arm C driver against the actual
Verilated master. Its 64 writes and 64 reads reach the model's native RAM, the
guest CPU independently checks the resulting words, and three injected failure
cases pass. This validates the software/RTL/model transaction path, not a
physical FPGA-to-DDR bridge or platform timing.

Sources: [probe guide and scope](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/README.md), [AXI RTL](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/rtl/ddr_probe.sv), [C driver](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/driver.c), [Verilator evidence](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/validation/native/results.json), [native Simics results](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/memory-labs/fabric-ddr/simics/validation).

## F2H and F2SDRAM translated fabric traffic

The native Simics fixture connects the same Arm-driven Verilator AXI master to
each native TBU ingress. F2H and F2SDRAM each passed one valid translated
64-word transaction and one unmapped-write fault case. The AXI security
attribute is nonsecure data (`PROT=0b010`). The model reports its native
ingress default SID 0; no AXUSER SID atom is supplied, so this does not qualify
physical AXUSER-to-SID wiring. Translation uses fresh walks with the model TLB
cache disabled, not a demonstrated invalidation sequence.

These results make a functional model path check, not a board implementation
claim. No Quartus fit or bitstream deployment is reported. A future physical
test still needs generated address/bridge evidence, a verified security and
stream-ID configuration, matched component wiring, bounded DDR ownership and
hardware readback/fault evidence. The related DMA0 engine test is now present
in native Simics, but it does not qualify the F2H/F2SDRAM hardware routes.

Sources: [native Simics adapter and limits](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/simics/README.md), [F2H valid](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/simics/validation/native-f2soc-valid/results.json), [F2H fault](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/simics/validation/native-f2soc-fault/results.json), [F2SDRAM valid](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/simics/validation/native-f2sdram-valid/results.json), [F2SDRAM fault](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/memory-labs/fabric-ddr/simics/validation/native-f2sdram-fault/results.json).

## USB status

The most recent bare-metal capture reports controller-not-ready and a ULPI
PHY-ID timeout. The user power cycle and fresh capture are still pending, so
USB enumeration, HID and storage behavior remain unverified.

Sources: [USB bring-up status](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/usb-bringup/README.md), [captured evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/usb-baremetal).
