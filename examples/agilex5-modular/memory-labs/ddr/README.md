# HPS DDR path: working-set latency and throughput

This bare-metal EL3 lab runs bounded scalar CPU transfers and dependent loads
over five working-set sizes: **64 KiB, 256 KiB, 1 MiB, 4 MiB and 16 MiB**.
It checks all written/copied words, checks a read checksum, follows a complete
dependent-load ring and restores its translation registers afterward.

| Target | Status |
|---|---|
| QEMU `virt` / TCG | Normal sweep passed; corrupted-copy and invalid-frequency controls rejected |
| Agilex 5 Modular ES | Compiled; physical execution and timing not tested |
| Agilex 5 Simics | Normal 20-sample sweep passed; both deliberate failures correctly rejected. Model timing only. |

The [recorded QEMU results](validation/qemu-final/results.json) include every
sample, the exact ELF hashes, build source identities and commands. Raw terminal
logs are beside that JSON. Numbers in these captures describe emulator execution,
**not Agilex DDR performance**.
The [Simics normal capture](validation/simics-initial/results.json) and
[negative controls](validation/simics-negatives/results.json) also record actual
execution. They use the same Agilex-target ELFs; their counter values describe
the model and do not qualify physical DDR/MPFE timing.

## What is measured

The guest enables EL3 translation with device attributes for low MMIO and
**normal noncacheable, Inner Shareable** attributes for its owned DDR window.
Data cache must already be off; the program rejects a cached or translated
entry state. It uses the same proven startup and NC mapping recipe as the
existing MMU practice lab. It does not fake a cache flush, change DDR clocks or
claim a cold/warm write-back-cache comparison.

Each operation runs twice. Samples record working-set bytes, elapsed counter
ticks, payload bytes, accesses and checksum. Read/write/copy are explicit
volatile 64-bit scalar loops. The copy byte count is payload size, even though
copying performs both a read and a write. The pointer chase visits one 8-byte
value per 64-byte line in a full ring using odd stride 257, and each next address
depends on the previous load.

Timestamps execute `DSB SY; ISB` before reading `CNTPCT_EL0`, so the write/copy
measurement includes completion to the architectural barrier. Periodic deadline
checks and scalar-loop work are included in the measured time. Integrity scans
and UART printing are outside the timed interval. Therefore this reports
**effective software memory-path performance**, not isolated MPFE latency, a
DDR-pin bandwidth measurement or theoretical peak DDR bandwidth.

For a sample with `ticks`, declared counter frequency `F`, payload `B` and
dependent-load count `N`:

- Effective payload bytes/s = `B * F / ticks`.
- Dependent-load ns/load = `ticks * 1e9 / (F * N)`.

The guest checks the declared frequency range and that the counter advances.
The Agilex build additionally requires the established bootstrap's 400 MHz
`CNTFRQ_EL0` value. The shared startup fills that declaration if it was zero.
**This is a consistency check, not independent oscillator calibration.** Before
publishing hardware timings, record the matching handoff/clock configuration and
validate the counter rate against an independent time reference. The benchmark
does not use CPU clock frequency as a substitute for the counter frequency.

## Memory ownership

| Region | QEMU | Agilex target |
|---|---|---|
| Code entry | `0x40200000` | `0x82400000` |
| Initial data load / data runtime | `0x40300000` / `0x40400000` | `0x82500000` / `0x82600000` |
| Stack top | `0x41000000` | `0x83fff000` |
| Source, up to 16 MiB | `0x45000000..0x46000000` | `0x85000000..0x86000000` |
| Destination, up to 16 MiB | `0x46000000..0x47000000` | `0x86000000..0x87000000` |

Ranges use exclusive upper bounds. The target scratch memory lies inside the
existing diagnostic's 64 MiB DDR test window. It requires exclusive ownership:
do not run concurrently with an OS, DMA user, debugger or another memory lab.
It uses HPS DDR bank 3A; there is no fabric EMIF dependency. No MMIO outside the
shared UART implementation is written by the benchmark.

## Build and run

From `examples/agilex5-modular` with the established Arm cross compiler and
QEMU on PATH:

```sh
bash memory-labs/ddr/build.sh qemu
python3 memory-labs/ddr/run.py
bash memory-labs/ddr/build.sh agilex5
# With the existing configured Simics 26.3 project and OCRAM bootstrap:
python3 memory-labs/ddr/run_simics.py
```

Outputs go to ignored `build/memory-ddr-qemu/` and `build/memory-ddr-agilex5/`.
The build emits ELF/bin files, linker maps, and `build.json` with source and
artifact identities. It reuses `qemu/labs/start.S`, `runtime.c`, `lab.h` and
the linker layout without modifying those files.

The host QEMU runner has a 90-second process bound per guest. Each guest has
fixed loop counts and a declared 30-second counter-based bound per timed
operation. The controls `ddr-copy-fault` and `ddr-clock-fault` respectively
corrupt the final destination word and supply an invalid frequency. A successful
normal run requires 20 distinct samples and all integrity/completion markers;
negative controls must exit nonzero for their specific expected failure.

The hardware image requires the existing matching DDR bootstrap and a fresh
standalone EL3 entry. Use the shared bench mutex and the existing verified ELF
segment loader rather than loading the flat binary's possible relocation gap.
The runner must restore DDR Hello in its finalizer. This subtree does not start
a physical-board run or claim hardware qualification.

## Hardware-only coarse counter calibration gate

`ddr-calibrated` is a separate hardware-target wrapper around the unchanged
`ddr.c` sweep. It **compiled successfully but has not run on hardware**. Its
[compile record](validation/build-agilex5-calibrated.json) includes the wrapper
hash and confirms that the original source and all existing QEMU/Agilex ELF/bin
images remained unchanged when this variant was added.

The wrapper checks EL3/cache-off entry, the pinned 400 MHz counter declaration,
and that the counter advances. It prints `COUNTER_INTERVAL_START`, waits for
400000000 architectural counter ticks, then prints `COUNTER_INTERVAL_END` and
the actual elapsed tick/poll counts. A fixed poll limit prevents an infinite
software loop. The markers occur **before** `LAB BEGIN ddr-path`; the subsequent
benchmark and its normal completion/integrity checks are unchanged.

Build it without rebuilding previously qualified images:

```sh
DDR_CALIBRATED_ONLY=1 bash memory-labs/ddr/build.sh agilex5
```

A normal `build.sh agilex5` also includes the wrapper. QEMU builds exclude it.
The hardware runner must independently timestamp the two markers using host
monotonic time and require **0.9–1.1 seconds** between them before setting
`timing_valid=true`. Guest output alone cannot pass that gate. It is a coarse
check that the declared counter rate agrees approximately with wall time, not
an oscillator calibration, a fine timing-accuracy claim or a proof of peak DDR
bandwidth. UART delivery and host scheduling contribute uncertainty. A failed
or missing interval must leave timing unqualified even if memory integrity
checks complete successfully.

The Simics runner reuses the configured `build/simics26` project and
`build/upstream26-ocram/baremetal.bin` bootstrap. It requires the DDR self-test
to return successfully before loading the guest, validates the compiled image
hashes, and waits for the guest's completion/failure marker. The process limit
is 180 seconds per case. `--project`, `--boot`, `--artifacts`, `--only` and
`--output` can select explicit existing inputs. It neither redeploys the model
nor accesses the physical board. For this OCRAM boot path, the model's
`No SD image supplied` startup warning does not mean the DDR test failed.

## Actual QEMU output

Excerpt from the checked-in `validation/qemu-initial/ddr-path.log`:

```text
DDR_SAMPLE op=read working_set_bytes=16777216 ticks=1975329 payload_bytes=33554432 accesses=4194304 checksum=3599992259633741824
DDR_SAMPLE op=dependent-load working_set_bytes=16777216 ticks=8562016 payload_bytes=4194304 accesses=524288 checksum=68719214592
PASS DDR_TRANSLATION_STATE_RESTORED
PASS DDR_SWEEP_COMPLETE
LAB COMPLETE
```

These are captured values, not expected timing thresholds. Repeated QEMU
runs can report different tick counts. Successful deliberate-failure exercises
produce `FAIL DDR_COPY_READBACK` and `FAIL DDR_DECLARED_TIMER_FREQUENCY_RANGE`
respectively; these failures are required by the host checker.

## References

- [Agilex 5 HPS TRM](https://docs.altera.com/r/docs/814346/26.1.1/hard-processor-system-technical-reference-manual-agilex-5-socs): MPU generic timer, memory subsystem and MPFE context.
- Existing [MMU practice source](../../qemu/labs/mmu.c): the reused EL3 normal-noncacheable mapping pattern.
- Repository [hardware guide](../../HARDWARE.md): tracked board profile and physical-bench prerequisites.
