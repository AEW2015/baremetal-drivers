# Full validation campaign — 31 October 2026

All **94 registered exercises** have a recorded disposition. **88 were exercised
on QEMU, Simics or the physical Modular ES board**, and two additional fabric
exercises passed native C/Verilator tests. Four were deliberately not executed:
the three remaining legacy board adapters and the FPGA partial-reconfiguration
workflow. A partial result does not count as a pass.

| Target | Exercised rows | Passed | Partial | Failed |
|---|---:|---:|---:|---:|
| QEMU | 16 | 16 | 0 | 0 |
| Native Agilex Simics | 63 | 49 | 6 | 8 |
| Physical Agilex 5 Modular ES | 55 | 49 | 5 | 1 |

These are named catalog rows, not assertion counts or claims that each example
runs on every target. Legacy, current upstream, board adapters and integration
profiles are separate implementations. Negative controls count within their
exercise; their expected rejection is a passing control.

[All 94 entries and evidence](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/COVERAGE.md) ·
[Machine-readable coverage and skip reasons](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/coverage.json) ·
[Updated platform catalog](example-catalog.md)

## Reproduce the public container

The [reference Dockerfile](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/container/Dockerfile)
built successfully with both the Ubuntu learning base and the pinned public
Quartus Pro 26.1.1 base. The learning image is approximately 1.38 GB; the hardware
image's reported layered size is approximately 45 GB. Compiler, QEMU, GDB,
Verilator, device-tree and hardware-tool versions are captured in the
[container record](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/container/evidence.json).

From the repository root:

```sh
docker build -t agilex-learning:13.2 examples/agilex5-modular/container
docker run --rm --mount type=bind,src="$PWD",dst=/repo \
  agilex-learning:13.2 bash -lc \
  'cd /repo/examples/agilex5-modular && bash container/check-learning.sh'
```

The complete learning check passed from a disposable clone with the original
source mounted read-only. It covers QEMU hello, seven practice programs, six
negative controls, GDB, DSU, DDR, SMMUv3/PCI EDU and both Verilator suites.
The hardware image passed tool-version checks without a board or license
mounted. Physical tests used the existing qualified bench container and matching
SOF/handoff. Simics remains a separately installed licensed runtime/model.
See [container setup](container.md) for UID/GID, hardware base, USB and licensing
configuration.

## Previously untested examples now checked on hardware

| Exercise | Observed result and limit |
|---|---|
| Semihost reference | Original assembly ran in OCRAM; exact greeting, full payload readback and completion PC verified. |
| PSCI reference | Exact CPU_ON helper ran under resident BL31/NS EL2; A55.1 identity, context, entry and stack matched; CPU_OFF and OFF affinity confirmed. Also passed native Simics. |
| Fault probe | ESR/ELR/FAR/SCTLR/CPTR readout completed. This does not inject a fault or demonstrate recovery. |
| DSU cached sharing | Three consumers checked 131072 words each; corruption and stalled-consumer controls were rejected; all secondaries quiesced. |
| L3 partition policy | PARTCR changed `0 → 0x1e → 0`; per-core policy restoration and the contention workload passed. No cache-way occupancy measurement or statistically established speedup. |
| HPS DDR sweep | All 20 NC scalar read/write/copy/dependent-load samples and two negative controls passed. A declared 400 MHz counter interval measured 0.9920 host seconds within the coarse ±10% gate; no peak-MPFE claim. |
| Current DMA | Original 256-byte sync and 1024-byte async copies plus a 4096-byte API copy passed full comparisons. Callback used the documented polling fallback; no DMA interrupt-delivery claim. |
| Current GIC | Masked SGI stayed masked; enabled Group-0 SGI 1 reached the actual ISR. Group-1 CPU interfaces were disabled and verified for this standalone test. |
| Current hello, MMU/SMMU status, timer | Completed with strict output and register/counter checks; status-only examples do not establish translation or calibrated timing. |
| Legacy vendor timer adapter | Unchanged timer body set, started, observed expiration and returned success. This is separate from the native legacy Simics timer failure. |

All 15 established board-suite entries also passed fresh builds and execution.
The seven shared practice labs and their six negative controls passed. Fresh
OCRAM UART, configuration snapshots, CRC, NoC, reset, BL31 mailbox and bridge
control runs passed. Bridge control does not establish fabric data transfers.

Actual physical PSCI output:

```text
PSCI_CPU_ON_RESULT=0
PASS PSCI_SECONDARY_IDENTITY_CONTEXT_AND_STACK
PSCI_FINAL_AFFINITY=1 OFF_ATTEMPT=1 OFF_RETURNED=0 OFF_RESULT=0
PASS PSCI_CPU_OFF_AFFINITY_CONFIRMED
PSCI_COMPLETE status=0
```

Actual physical DMA output:

```text
DMA_STRICT_READBACK bytes=4096 mismatches=0
PASS DMA_STRICT_4096_READBACK
PASS DMA_STRICT_CHANNEL_IDLE
```

[Physical results and raw captures](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/hardware/results.json) ·
[Current adapter commands and scopes](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/hardware-candidates/README.md) ·
[PSCI commands](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/reference/psci/README.md)

## Partial results and real failures

The five physical partial rows are current CCU, clock manager, SPI, ECC and FCS.
CCU and clock tests intentionally cover getter/readback subsets. SPI's 32-byte
and 256-byte internal loopbacks passed, but the original status phase runs after
the API closes and prints a misleading success summary. ECC getter/raw reads
matched `SERR=0x00010000`, `DERR=0`; the nonzero flag was left unchanged. No ECC
initialization, clearing, injection or recovery was qualified by that snapshot.

FCS initially corrupted its stack after receiving the real chip ID. The HAL
registered a local response array with an asynchronous mailbox operation and
returned before the callback copied into it. The driver now waits for its own
response before that array expires. Timeout cleanup detaches the pointer while
reserving the pending job ID until its late response is drained. Delayed-response,
timeout/reinit/late-response and unchanged-canary regressions passed.

The corrected physical FCS run completed identity and a 36-byte read-only
provisioning query, then handled SDM session denial `0x85` without a crash:

```text
SERVICE_FCS_API open rc=-5
SERVICE_PARTIAL FCS_SDM_SECURITY_DENIED_0x85
SERVICE_FCS_API get_provision rc=0 bytes=36 (read-only)
SERVICE_FCS_API deinit rc=0
SERVICE_COMPLETE status=0
```

Session/RNG coverage remains partial. No key, owner-state or fuse programming
was performed. The native Simics SDM still rejects these services with error
`0x3`; after the fix, that example finishes with controlled API errors instead
of an unexpected restart. The fix covers seven exercised HAL paths, not the
entire FCS/key-management API.

[FCS failure, fix and scope](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/service-candidates/FCS_LIFETIME_FIX.md) ·
[Delayed-response regression evidence](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/service-candidates/validation/fcs-lifetime-fixed-20261031/results.json)

The sole physical failed row is USB. U-Boot starts, but xHCI still reports:

```text
USB_LAB_RESET stage=cnr-return rc=-110 USBCMD=00000000 USBSTS=00000801
No USB controllers found
```

No hub, mouse, flash or USB Ethernet traffic was qualified. The separate HPS
EMAC2 Ethernet example passed at 1 Gb/s: ARP/ping, five UDP echo sizes,
sequence/corruption controls and TCP receive/transmit. This campaign reran smoke
traffic; its historical bandwidth figures were not remeasured.

The eight Simics failed rows are legacy timer, XGMAC and mailbox, plus current
ECC, FCS, I3C, SD/MMC and SEU. The model report retains exact causes. I3C has a
concrete enum/`#ifdef` reset-selection defect; GPIO and SPI also have weak
upstream selftest phases. Those unrelated upstream issues were recorded rather
than silently converted to passes.

[Simics report](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/simics/REPORT.md) ·
[Hardware eligibility and source audit](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/simics/hardware-eligibility.md)

## What remains a reference

The original SPI adapter can write an external EEPROM; the original watchdog
needs a dedicated reset/recovery adaptation; the original mailbox adapter has
unported queue/offset assumptions. Their safer counterparts were tested under
separate catalog rows. The partial-reconfiguration workflow needs a matching
fitted static design and persona images. Fabric ADD/XOR passed host Verilator;
the new DDR initiator also passed native Simics/Verilator, but physical fabric
integration still needs a matched fit after the reserved build window.

The original SD/MMC selftest writes blocks 0–1, shared-bus I2C can write targets,
and SEU/ECC injection require specific fixtures/recovery. Those commands were
not blindly loaded onto the user's board. Each skipped platform has a concrete
reason in the complete coverage ledger.

## Evidence checks

The main regression suite passed **98 tests with real QEMU enabled**. Both
Docker variants built; the final public learning image passed its full check
from a disposable clone. Original verdicts, failed attempts and artifact/source
hashes remain available. Candidate transcript checkers were corrected for real
logger prefixes, hexadecimal case and debug-line interleaving; separate reviewed
results retain the original verdicts and unchanged firmware hashes. Missing
callbacks, corrupt data, enabled Group-1 interrupts and incomplete/stale captures
remain rejected.

Every physical group recorded successful DDR Hello restoration. Generated
executables, programming images, licensed simulator binaries and credentials
are excluded from the repository.
