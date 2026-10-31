# Cached multicore and DSU/L3 laboratory

This laboratory adds cached shared-memory transfers to the established EL3
startup. The normal image makes **no DSU policy-register accesses**. Its three
consumers each check all 512 words in each of 256 transfers from the primary:
131072 words per consumer. Acquire/release sequence and acknowledgement flags
protect the ordinary C payload accesses; no payload cache clean/invalidate is
performed during those transfers.

| Image | QEMU | Agilex 5 Simics | Modular ES hardware |
|---|---|---|---|
| `normal` | Passed, functional model | Passed, functional model | Passed: cached multicore integrity/coherency |
| `corrupt` | Expected data failure detected | Expected data failure detected | Passed: injected payload corruption detected and secondaries quiesced |
| `stalled` | Expected protocol timeout detected | Expected protocol timeout detected | Passed: producer timeout detected and secondaries quiesced |
| `contention` | Passed, workload/control flow only | Passed, workload/control flow only | Passed: shared-policy workload and integrity |
| `partitioned` | Unsupported; not built | Do not run without modeled DSU registers | Passed: policy readback, workload, and restoration |

QEMU TCG and native Simics do not establish physical cache coherency, L3
partition behavior or memory latency. Physical evidence now establishes the
functional cached-coherency workload and successful DSU policy readback and
restoration on Modular ES. It does not prove cache-way occupancy or a statistical
speedup. The captured hardware result records, UART output, debug output and
readbacks are in
[normal](../../validation/full-campaign-20261031/hardware/memory-dsu/normal-uart.txt),
[corruption](../../validation/full-campaign-20261031/hardware/memory-dsu/corrupt-uart.txt),
[stalled](../../validation/full-campaign-20261031/hardware/memory-dsu/stalled-uart.txt),
[contention](../../validation/full-campaign-20261031/hardware/memory-dsu/contention-uart.txt),
and [partitioned](../../validation/full-campaign-20261031/hardware/l3-partition/partitioned-uart.txt)
UART logs; `results.json`, raw policy readbacks, debug output, bootstrap and
chain records are alongside them. Model logs and exact compiler/source/artifact identities remain in
[validation/](validation/).

## Build and execute the functional checks

From `examples/agilex5-modular`, in the configured compiler container:

```sh
bash memory-labs/dsu/build.sh qemu
python3 memory-labs/dsu/run.py
bash memory-labs/dsu/build.sh agilex5
```

With the installed native Agilex Simics project deployed to `build/simics26`,
the same Agilex-target images run without policy-register accesses:

```sh
python3 memory-labs/dsu/run_simics.py --only normal,corrupt,stalled,contention
```

The runner first boots the pinned OCRAM command image and requires successful
completion of `ddr_selftest` before loading each guest. It bounds each process
at 180 host seconds and rejects `partitioned`. Actual runs are recorded in
[simics-initial](validation/simics-initial/results.json) and
[simics-controls](validation/simics-controls/results.json). Normal completed in
16.8 host seconds; the corruption, contention and stalled-consumer cases took
15.5, 18.4 and 49.5 host seconds respectively. Every guest reached the expected
completion/failure and secondary-quiescence markers. These host durations are
execution evidence, not simulated or physical workload performance.

The build reuses `qemu/labs/start.S`, `runtime.c`, `lab.h` and `link.ld`; it does
not modify those shared files. Artifacts go to ignored `build/dsu-qemu/` and
`build/dsu-agilex5/`. The QEMU runner starts four Cortex-A53 model CPUs at the
same ELF entry; MPIDR selects primary versus secondary startup. This is not
PSCI CPU_ON. The Agilex build uses the existing qualified reset/power-release
sequence for the two A55 and two A76 cores, and requires a fresh matching DDR
bootstrap before execution.

The standalone completion leaves translation and caching enabled. Secondary
cores clean their owned channel, stack and optional hammer buffer to PoC,
publish completion through a statically noncacheable mailbox, and park outside
the reloadable image on hardware. **Use the fresh matching HPS/DDR bootstrap
before another program; do not reload an unrelated ELF into this live state.**

The parent hardware runner integrates this oracle through
`run.py:assess_target(name, body, process_code)`. A captured deliberately failing
guest has process code zero in the JTAG/Simics runner, whereas QEMU semihosting
returns one. The oracle handles that distinction and requires the intended
failure plus successful secondary quiescence.

## Translation and memory ownership

Each core installs the same 4 KiB-granule EL3 identity translation tables. Low
MMIO is Device-nGnRnE; the selected 128 MiB RAM window is Normal Write-Back,
Read/Write Allocate, Inner Shareable. One separate 2 MiB block contains the
Normal Noncacheable quiescence flags. `AT S1E3R` and `PAR_EL1` verify the
payload physical address, shareability and memory attribute on every consumer;
SCTLR readback requires M, C and I enabled.

| Region | QEMU | Agilex 5 |
|---|---|---|
| Code entry | `0x40200000` | `0x82400000` |
| Initial data load address | `0x40300000` | `0x82500000` |
| Runtime data/BSS/tables | `0x40400000` | `0x82600000` |
| Primary stack top; 16 KiB per core | `0x41000000` | `0x83fff000` |
| CPU2 hammer, 2 MiB | `0x44000000` | `0x84000000` |
| CPU3 hammer, 2 MiB | `0x44800000` | `0x84800000` |
| CPU1 pointer probe, 384 KiB | `0x45000000` | `0x85000000` |
| NC quiescence flags, four 64-byte slots | `0x46000000` | `0x86000000` |

Only the `contention` and `partitioned` images access the hammer/probe regions.
No fabric DDR controller is involved. These ranges are owned exclusively by
this lab; they overlap scratch used by other examples and cannot run alongside
another payload or an OS.

Memory attributes stay unchanged throughout the active test. This avoids the
cacheable-to-noncacheable-to-cacheable transition implicated in Agilex 5 ES DSU
erratum **1314123**, documented in the
[ES errata](https://docs.altera.com/r/docs/825514/current/agilex-5-es-device-errata-and-user-guidelines).

## Actual output and deliberate failures

The normal QEMU execution records, among other checks:

```text
PASS SECONDARY_WB_INNER_SHAREABLE_TRANSLATION
PASS CONSUMER_FULL_PAYLOAD_VERIFIED
CONSUMER=0x0000000000000001
WORDS_CHECKED=0x0000000000020000
CHECKSUM=0x0b18fc89d29b0000
```

Each of the three consumer records must pass. The run then records:

```text
PASS THREE_CACHED_CONSUMERS_VERIFIED
PASS SECONDARIES_CLEANED_AND_QUIESCENT
```

`corrupt` changes bit zero of CPU1's payload word 127 during transfer 37.
The captured failure identifies that exact corruption:

```text
ERROR_CPU=0x0000000000000001
ERROR_ROUND=0x0000000000000025
ERROR_WORD=0x000000000000007f
ACTUAL=0x168c8544d64f4763
EXPECTED=0x168c8544d64f4762
PASS SECONDARIES_CLEANED_AND_QUIESCENT_ON_FAILURE
FAIL DSU_PAYLOAD_MISMATCH
LAB FAILED
```

`stalled` holds CPU3 after announcing it online. The producer's five-second
counter-based watchdog must emit `FAIL DSU_PRODUCER_TIMEOUT`. Other consumers
have a longer grace period so they can respond to the producer's abort and
quiesce; a host timeout, crash or unrelated failure does not satisfy the test.

## Shared versus partitioned contention experiment

`contention` runs the same verified transfers, then makes CPU1 pointer-chase a
384 KiB ring while CPUs 2 and 3 write/read separate 2 MiB regions. Both hammers
must actually start before the probe begins. The probe executes 1024 batches
of 64 dependent loads and checks the final ring position. Output reports raw
minimum, maximum and total counter ticks; these include bounds checks, loop
instructions and barriers, **not raw L3 access latency**. QEMU validates this
workload's execution and stop/join protocol only. Native Simics also passed the
full workload and both hammer-participation checks; its captured minimum batch
counter delta was zero, reinforcing that these model values are not physical
cache-latency measurements.

The hardware-only `partitioned` image uses that identical contention workload
and applies the core1 partition policy from Altera's
[pinned RT helper](https://github.com/altera-fpga/meta-altera-rt/blob/7cf884ac5be93779f37b189c2720fa3f92955de5/recipes-bsp/arm-trusted-firmware/files/core1_nl3a_cp_qos_plat_helpers.S):

| Control | Exact encoding / change |
|---|---|
| `CLUSTERPARTCR_EL1` | `S3_0_C15_C4_3`; low byte `0x1e` |
| `CLUSTERTHREADSID_EL1` | `S3_0_C15_C4_0`; CPU1 scheme 1, other cores scheme 0 |
| `ACTLR_EL3` | Enable scheme/thread register access with bits 10 and 11 |

Altera describes this arrangement as four L3 ways for scheme 1 and twelve for
scheme 0. The code leaves CHI QoS and the no-L3-allocation control untouched,
so it changes one policy rather than combining several mitigations. See the
[cluster-latency guide](https://altera-fpga.github.io/rel-26.1/real-time/agilex5-hps-cpu-cluster-latency/agilex5_hps_cpu_cluster_latency/)
and [RT configuration guide](https://altera-fpga.github.io/rel-26.1/real-time/embedded-linux/yocto-kas/).

The explicit variant requires EL3 and the expected A55/A76 MIDRs. It saves all
touched registers, requires the original partition low byte and all thread
scheme IDs to be zero, applies policy before each core's first cached lab
traffic, and verifies readback. Each secondary restores its SID/ACTLR, cleans
owned dirty memory and parks; only after every NC quiescence flag is observed
does primary restore/read back the original cluster policy and its own
SID/ACTLR. Detected protocol failures request a coordinated abort. An
unexpected exception or failed quiescence requires the outer runner's fresh
HPS/DDR recovery; the lab does not claim restoration after a hard fault.

The physical `partitioned` run passed with readback from `PARTCR=0` to `0x1e`
and back to `0`; all per-core policy registers were restored. The UART transcript
includes the policy readback; the result JSON, debug output, bootstrap and chain records are in
[`partitioned UART output`](../../validation/full-campaign-20261031/hardware/l3-partition/partitioned-uart.txt)
and the [campaign result record](../../validation/full-campaign-20261031/hardware/l3-partition/results.json).
The four normal, corrupt, stalled and contention UART transcripts are linked above.
These runs qualify the functional workload, policy readback and restoration.
They do not measure cache-way occupancy or establish a statistical performance
improvement; raw counter ticks include software overhead and require matched,
repeated comparisons before any performance claim. Do not run the partitioned
variant on QEMU or assume the installed Simics model supports its DSU registers.
