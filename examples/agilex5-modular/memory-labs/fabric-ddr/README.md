# Guarded fabric AXI-to-DDR exerciser

`rtl/ddr_probe.sv` is a synthesizable fabric memory initiator with a 256-byte
Avalon-MM control/status agent and a 40-bit-address, 64-bit-data AXI4 master.
The same C driver runs against Verilator and, through the
[Simics adapter](simics/README.md), as actual AArch64 instructions.

The core writes deterministic 64-bit patterns, waits for every write response,
then reads and verifies every word. It reports the first failing address,
expected/observed data, verified count and cycle count. It supports one
outstanding single-beat transaction. This is a bring-up and fault-handling
design, not a peak-bandwidth generator.

## Run the checked RTL and driver

From `examples/agilex5-modular` in the existing development container:

```sh
bash memory-labs/fabric-ddr/test.sh
bash memory-labs/fabric-ddr/check_component.sh
```

These require Verilator, g++, make and, for the second command, Quartus
Platform Designer. Build output stays in ignored `build/fabric-ddr*` directories.
The component recipe generates an exported CSR/AXI/IRQ wrapper for the Modular
ES device; it does not fit or program a board image.

The captured native RTL run includes:

```text
PASS FABRIC_DDR words=4096 writes=4096 reads=4096 cycles=36839 randomized_backpressure=1
PASS FABRIC_RANGE software_and_RTL_guards no_AXI_transactions
PASS FABRIC_FAULT kind=corruption verified=37 error=2
PASS FABRIC_TIMEOUT channel=aw request_held_then_drained no_following_transactions
```

All 12 checks passed: three sizes, range guards, corruption/BRESP/RRESP failures
and timeout/drain checks on AW, W, B, AR and R. The peer checks request stability
while backpressured. [Evidence and source hashes](validation/native/results.json)
identify the exact tested RTL, driver and component metadata.

## Control map

CSR addresses are **byte offsets** for C and **word addresses** on the Avalon
interface. Reads return after one clock; writes honor byte enables.

| Offset | Register | Meaning |
|---|---|---|
| `0x00` / `0x04` | ID / ABI | `0x44445231` / `0x00010000` |
| `0x08` | CONTROL | Bit 0 starts; bit 1 clears idle status |
| `0x0c` | STATUS | Busy, done, fault, rejected, timeout in bits 0–4 |
| `0x10` / `0x14` | BASE | Master-view address, low/high halves |
| `0x18` / `0x1c` | WORDS / SEED | Number of 64-bit words and pattern seed |
| `0x20` | VERIFIED | Successfully compared words |
| `0x24` / `0x28` | FAIL_ADDRESS | First failing master address |
| `0x2c` / `0x30` | EXPECTED | Expected data |
| `0x34` / `0x38` | OBSERVED | Received data |
| `0x3c` / `0x40` | CYCLES | Core clock cycles while busy; no frequency implied |
| `0x44` / `0x48` | ALLOWED_BASE | Read-only synthesis-time lower bound |
| `0x4c` / `0x50` | ALLOWED_END | Read-only exclusive upper bound |
| `0x54` | WATCHDOG | Read-only per-channel stall budget in cycles |
| `0x58` | ERROR | 1 range, 2 mismatch, 3 AXI response/ID/last, 4 timeout |

The default allowed range is empty, so an unconfigured core issues no memory
requests. Both driver and RTL reject unaligned/out-of-range descriptors. The
RTL checks 65-bit end arithmetic and a synthesis-time maximum word count.
Configuration writes while busy are rejected without changing active addresses.

## Timeout and recovery contract

An AXI timeout sets FAULT/TIMEOUT immediately but **does not withdraw a valid
request**. The core drains the current accepted transaction and issues no next
transaction. If the peer never responds, BUSY remains asserted. After driver
return `-4`, use `ddr_probe_drain()` with a bounded budget and keep clocks/reset
stable. A remaining BUSY result requires bus-level recovery; do not reconfigure
the region or assume that returning from the C function aborted DMA.

## Deployment using HPS DDR bank 3A

```text
HPS CPU → lightweight HPS-to-FPGA bridge → probe.csr
probe.memory → AXI interconnect/width adapter → selected HPS ingress → HPS DDR
```

The selected ingress is either FPGA-to-SDRAM or FPGA-to-HPS, with its applicable
TBU configuration for a translated exercise. This design uses no fabric EMIF.

1. Add `ddr_probe_hw.tcl` to the component search path in an isolated copy of
   the matching Modular HPS design. Connect CSR to the CPU-visible control
   master and export/route the interrupt.
2. Connect the memory master to the selected ingress. The reference HPS
   subsystem exports `f2sdram` as an AXI4 slave with associated
   `f2sdram_axi_clock` and `f2sdram_axi_reset`; discover the actual instance names
   and address translation from that project's generated inventory. Its data
   width is 256 bits, so this 64-bit initiator needs the proper interconnect
   width adaptation. Do not wire mismatched data buses directly.
3. Supply a synchronized, sufficiently long reset in the selected clock
   domain. Add proper clock crossing when clocks differ. The RTL uses
   synchronous reset and does not implement a clock-domain crossing itself.
4. Reserve a small region of **HPS DDR bank 3A**, starting with 512 bytes.
   Determine its CPU physical address and the selected master's address or
   IOVA separately. Set `ALLOWED_BASE`/`ALLOWED_END` to that master-view range.
   The Simics/native-test addresses are not an approved physical board map.
5. Configure security and the actual route's stream ID/STE/page tables before
   enabling a translated test. `AXPROT` carries AXI security/privilege bits;
   `AXUSER` is a sideband value, not a portable SMMU stream-ID assignment.
6. Fit the matching design, check timing/reset requirements and record SOF,
   handoff and map hashes. Then load through the shared hardware mutex, inspect
   ID/ABI and read-only guard registers, and run one bounded transfer using
   `ddr_probe_mmio()` plus `ddr_probe_run()`.
7. Require both RTL verification and an independent CPU comparison of the
   reserved buffer. Use a noncacheable CPU mapping for this initial
   noncoherent test. For translated faults, also require the selected TBU's
   fault evidence and an unchanged destination/guard region.

The OpenTPU R4 build reservation currently prevents a new full-board Quartus
fit for this lab. No physical FPGA-to-DDR, F2H or F2SDRAM translation PASS is
claimed. The software, synthesizable core, component-generation check and
simulation evidence make the next deployment concrete and reviewable.
