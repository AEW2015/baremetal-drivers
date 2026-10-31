# Translated DMA and an intentional SMMU fault

This lab runs an AArch64 bare-metal guest against **QEMU's actual SMMUv3 and
PCI EDU device models**. The guest programs translation tables and command/event
queues, drives the EDU DMA engine, then checks both data and the hardware-model
fault record. There is no software substitution for the address translation.

| Platform | Current scope |
|---|---|
| QEMU 8.2.2 `virt` | Passed: translated 4096-byte round trip, one-byte invalid DMA fault, two deliberately broken controls |
| Agilex Simics 26.3 | Passed separately: host-issued transactions through native DMA0, F2H and F2SDRAM TBU model ingresses; fresh walks with model TLB cache disabled |
| Agilex 5 hardware | Not ported or run; the existing DMA0 example does physical copying only |

These are generic SMMUv3 programming exercises. They do not qualify Agilex's
physical TCU, DMA TBU, F2H TBU or F2SDRAM TBU. The PCI EDU device does not exist in the
Agilex HPS. **Do not load this QEMU image onto the physical board.**

## Build and run

The established container has QEMU and the AArch64 compiler. From the host:

```sh
docker exec agilex26-mcp-demos bash -lc '
  cd /workspace/baremetal-fixes-20261029/examples/agilex5-modular
  bash memory-labs/smmu/build.sh
  python3 memory-labs/smmu/run.py
'
```

With the same tools installed directly, run those last two commands from
`examples/agilex5-modular`. `CROSS_COMPILE` overrides the compiler prefix;
`run.py --qemu /path/to/qemu-system-aarch64` overrides QEMU. Builds go into
ignored `build/memory-smmu/`. Every execution produces a new timestamped
`validation/qemu-*` directory, including UART logs, guest exits, invocation,
compiler/QEMU versions and ELF/source hashes. The host runner returns nonzero
if any expected outcome is missing, including a timeout in a negative control.

QEMU uses `virt,iommu=smmuv3,secure=on,virtualization=on,highmem=off`,
`-global arm-smmuv3.stage=2`, and
`-device edu,addr=1.0,dma_mask=4294967295`. The 32-bit DMA mask is explicit:
EDU otherwise defaults to 28 bits, which would truncate these test addresses.
The guest requires that the model actually advertises stage-2 support.

## Memory map and transaction path

| Resource | Address / setting |
|---|---|
| EL3 guest entry | `0x40200000` |
| Guest tables/queues | Linker-owned, aligned memory in the `.bss` region starting at `0x40400000` |
| QEMU SMMUv3 register aperture | `0x09050000` |
| PCI ECAM | `0x3f000000` (`highmem=off`) |
| EDU BDF / requester stream ID | `00:01.0` / `8` |
| EDU BAR0 | `0x10000000`, programmed by the guest |
| EDU internal DMA buffer | Device offset `0x40000`, 4096 bytes |
| Source DMA IOVA → CPU PA | `0x60000000` → `0x48000000` |
| Destination DMA IOVA → CPU PA | `0x60200000` → `0x48200000` |

```text
EDU DMA → PCI requester SID 8 → SMMUv3 stage-2 table walk → QEMU RAM
```

CPU MMU and data cache remain disabled throughout this exercise. The guest
requires that state, uses `DSB` barriers when publishing tables and data, and
never changes memory cacheability. This isolates address translation and fault
handling; it is not a cache-coherency or bandwidth test.

The stream table is linear with 32 entries. Unrelated entries are valid abort
entries; only SID 8 selects stage-2 translation. A 4 KiB granule and L1/L2 tables
provide two 2 MiB block mappings, with VMID 1 and a 32-bit input address space.
The verified transfer accesses only 4096 bytes within each block.

## What the guest verifies

1. Discover the expected PCI identity and BAR register liveness.
2. Build the stream table, translation tables and bounded command/event queues.
3. Enable queues, invalidate configuration/TLB state, then enable the SMMU and
   wait for its acknowledgment.
4. DMA all 4096 source bytes from source IOVA into EDU, then from EDU into
   destination IOVA. CPU reads the physical destination and compares every byte.
5. Require that the valid transfers generated no SMMU fault.
6. Fill the destination with guard byte `0xa5`, invalidate its page-table entry,
   then issue `TLBI_S12_VMALL` and `CMD_SYNC` and wait for consumption.
7. Issue a **one-byte** DMA write to the now-unmapped destination. Require an
   actual `F_TRANSLATION` event with SID 8, stage-2 flag and exact faulting IOVA.
8. Require every byte of the 4096-byte guard to remain unchanged and require
   no SMMU global error. Disable PCI bus mastering and the SMMU before completion.

The invalid DMA is intentionally one byte. A larger invalid transfer can be
split into many faulting accesses by QEMU, flooding a small event queue. An
earlier development run exposed precisely that queue error; the final test
requires exactly one event and a zero global error rather than accepting an
overflow as successful fault handling. EDU clears its DMA busy bit even when
the model rejects an access, so DMA completion alone cannot establish success.

## Actual terminal output

The passing run records these lines:

```text
PASS translated EDU DMA round trip verifies all 4096 bytes
PASS valid transfers produced no SMMU fault
event word0=0x0000000800000010
event word1=0x0000008000000000
event address=0x0000000060200000
event auxiliary=0x0000000000000000
PASS event is F_TRANSLATION
PASS event identifies EDU stream 8
PASS event identifies stage-2 fault
PASS event identifies unmapped destination IOVA
PASS one-byte invalid DMA produced exactly one event
PASS faulting DMA left all 4096 guard bytes unchanged
SMMU GERROR=0x0000000000000000
SMMU GERRORN=0x0000000000000000
PASS no unacknowledged SMMU global error
PASS SMMU_TRANSLATED_DMA_AND_FAULT QEMU SMMUv3/EDU models only
LAB COMPLETE
```

The host checks event type/SID/address independently of the final PASS line.
The deliberate `bypass` build selects bypass in the STE: because the IOVAs are
different from physical RAM addresses, the data comparison fails. The
`keep-mapping` build leaves the destination mapping valid: the required fault
never arrives. Both guest exits must be **1**, for their specific expected
reason. The normal guest exit must be **0**. The aggregate host result is 0
only when all three outcomes match.

## Native Agilex Simics TBU transactions

`native_fixture.py` configures the installed `sm_hps_smmu_600` model and issues
transactions through the platform's existing native memory-space routes. It
does not compute translated addresses in Python or replace native faults with
software results. `native_cases.py` verifies 64 write/read beats, all physical
target words, an untouched untranslated-alias guard, then an actual native
translation fault after removing the mapping.

| Route | Native ingress / TBU index | Observed SID source |
|---|---|---|
| DMA0 | `dmac_smmu_mem_space_0` / 0 | System Manager DMA0 read/write stream-ID register `0x10d121a8=0x00080008`, control `0x10d1217c=3`; fault reports SID 8 |
| F2H | `f2soc_smmu_mem_space` / 4 | Native ingress default SID 0, confirmed by the fault record; no SID atom injected |
| F2SDRAM | `f2sdram_smmu_mem_space` / 5 | Native ingress default SID 0, confirmed by the fault record; no SID atom injected |

These fabric model defaults do **not** establish a physical AXUSER-to-SID bit
mapping. The source of each SID is recorded in the result. Incoming accesses
are explicitly nonsecure and unprivileged data transactions, corresponding to
AXI `PROT=0b010`; security attributes must match the actual initiator when this
fixture is used with an RTL transactor.

The native test maps IOVA `0x85000000` to physical `0x86000000`, using tables
at `0x85400000`. It verifies all 512 bytes at the translated target and verifies
that the physical memory at the original IOVA remains an unchanged guard.
Removing the 2 MiB mapping then causes an invalid 8-byte write to return a native
bus error, produce `F_TRANSLATION` with the expected SID, stage-2 flag and IOVA,
and leave all target and alias guard words unchanged.

This is **host-configured, host-issued native-model traffic**, not an Arm guest
programming a DMA controller. The OCRAM guest is used only to initialize modeled
DDR. A separate guest-DMAC/RTL integration must establish its own initiator
behavior; these checks do not inherit such a result.

The tested model has `tlb_cache_enable=False`. Its `CR0` configuration reads
back, but `CR0ACK` remains zero and command-queue completion was not established.
The fixture therefore tests **fresh page-table walks**, not TLB invalidation or
ordinary driver initialization sequencing. It never fabricates an ACK, updates
a consumer register to claim completion, or substitutes Python translation.
An enabled model TLB cache causes this fixture to reject the run until a real
invalidation path has been qualified. Each isolated session pulses only the
Simics SMMU model's reset interface; it never accesses physical board reset.

From `examples/agilex5-modular` in the Simics container:

```sh
python3 simics/setup.py \
  --simics-root /home/dev/altera_pro/intel-fpga-ext_26.3/simics
python3 memory-labs/smmu/native_run.py
```

`--project` and `--boot` override the deployed project and OCRAM bootstrap.
Actual results, invocation and source/model identities are in
[`validation/simics-native-20261031T024350.917717Z`](validation/simics-native-20261031T024350.917717Z/):

```text
PASS NATIVE_TBU_DATA route=dma0 words=64 SID=8
PASS NATIVE_TBU_UNMAP_FAULT route=dma0 SID=8 guard_words=64
PASS NATIVE_TBU_DATA route=f2h words=64 SID=0
PASS NATIVE_TBU_UNMAP_FAULT route=f2h SID=0 guard_words=64
PASS NATIVE_TBU_DATA route=f2sdram words=64 SID=0
PASS NATIVE_TBU_UNMAP_FAULT route=f2sdram SID=0 guard_words=64
PASS NATIVE_TBU_CASES count=3
```

The QEMU full guest/EDU-DMA results are separately recorded in
[`validation/qemu-20261031T022532.436895Z`](validation/qemu-20261031T022532.436895Z/).
Run-directory timestamps are UTC.

## Agilex port and qualification gates

The current repository supplies these useful starting points:

| Existing source | What it provides |
|---|---|
| `drivers/smmu/socfpga_smmu_reg.h` | Agilex SMMU register definitions; base `0x16000000` |
| `drivers/smmu/socfpga_smmu.h` | Vendor stream constants: DMA0 `8`, DMA1 `9`, SDM `0xa` |
| `drivers/smmu/socfpga_smmu.c` | Existing setup translates SDM; other streams currently bypass |
| `core/dma_copy.c` | Previously qualified physical DMA0 copy and full data readback |
| `platform/agilex5/include/socfpga_dma_reg_plat.h` | DMA0 base `0x10db0000` |

The coincidence between QEMU EDU SID 8 and the vendor DMA0 constant does not
establish equivalent routing. Before a physical test:

- Replace the PCI EDU adapter with the actual HPS DMA controller, including
  descriptor addresses and source/destination security attributes.
- Verify live System Manager stream IDs and bypass/security routing against
  the **R0 ES** register map and matching handoff. Verify the requested DMA
  channel really traverses the DMA TBU/TCU rather than bypassing it.
- Preserve or quiesce existing SDM/other users of the SMMU. The A0 firmware
  workaround may already own its tables. Do not replace a live global stream
  table or disable the whole SMMU underneath active firmware services.
- Use reserved HPS DDR bank 3A only, with owned buffers/tables, explicit cache
  maintenance or a fixed noncacheable mapping, and bounded fault handling.
- Require nonidentity data readback, fault SID/address, unchanged guards,
  no unexpected global error and restoration of all modified configuration.
- Qualify F2H and F2SDRAM independently with a real fabric initiator and each
  route's verified stream metadata. CPU or EDU traffic cannot qualify them.

Agilex clients have a documented 40-bit virtual-address limit; this QEMU
exercise deliberately uses only a 32-bit input space. The port must check
actual capability registers before selecting a translation stage and format.

## Primary references

- [QEMU EDU device specification](https://www.qemu.org/docs/master/specs/edu.html).
- [QEMU 8.2.2 SMMUv3 register/STE/event definitions](https://github.com/qemu/qemu/blob/v8.2.2/hw/arm/smmuv3-internal.h).
- [QEMU 8.2.2 SMMUv3 model](https://github.com/qemu/qemu/blob/v8.2.2/hw/arm/smmuv3.c).
- [QEMU 8.2.2 EDU DMA implementation](https://github.com/qemu/qemu/blob/v8.2.2/hw/misc/edu.c).
- [Linux 6.8 SMMUv3 architectural field definitions](https://github.com/torvalds/linux/blob/v6.8/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h).
- [Agilex 5 HPS TRM, SMMU integration and translation](https://docs.altera.com/r/docs/814346/25.3/hard-processor-system-technical-reference-manual-agilextm-5-socs).
- [Agilex 5 R0 ES register map](https://docs.altera.com/v/u/resources/864456/agilex-5-r0-suffix-opn-hps-register-map).
