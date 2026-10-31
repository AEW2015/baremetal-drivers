# Seven QEMU practice labs

These exercises extend the [first QEMU lesson](../qemu.md). Each is a separate
freestanding C program with shared AArch64 startup and exception vectors.
You need no board: use QEMU `virt`, secure EL3, Cortex-A53, GICv3,
128 MiB RAM and TCG. These addresses and peripherals belong to QEMU, not Agilex.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](../assets/architecture/design.html?example=practice%2Fstartup){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=practice%2Fstartup" data-example-id="practice/startup">practice/startup</a> · <a href="../../assets/architecture/design.html?example=practice%2Fcorruption" data-example-id="practice/corruption">practice/corruption</a> · <a href="../../assets/architecture/design.html?example=practice%2Fexception" data-example-id="practice/exception">practice/exception</a> · <a href="../../assets/architecture/design.html?example=practice%2Ftimer" data-example-id="practice/timer">practice/timer</a> · <a href="../../assets/architecture/design.html?example=practice%2Fmmu" data-example-id="practice/mmu">practice/mmu</a> · <a href="../../assets/architecture/design.html?example=practice%2Fuart" data-example-id="practice/uart">practice/uart</a> · <a href="../../assets/architecture/design.html?example=practice%2Fmulticore" data-example-id="practice/multicore">practice/multicore</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=practice%2Fstartup" title="HPS and fabric diagram for examples/qemu-labs.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Build and run

Use the [installed tools](../setup.md), then from `examples/agilex5-modular`:

```sh
bash qemu/labs/build.sh
python3 qemu/labs/run.py --negative --gdb
```

The build produces seven normal ELFs and six deliberate failure variants in
`build/qemu-labs/`. It uses `aarch64-none-elf-gcc` with debug information and
warnings treated as errors. The runner needs `qemu-system-aarch64`; `--gdb`
also needs `gdb-multiarch` with Python support. Set `CROSS_COMPILE`, `QEMU` or
`GDB` to override tool names. The compiler is also queried for the result manifest.

Expected host summary: seven normal PASS results, six negative-control PASS
results, and `startup-gdb: PASS` plus `corruption-gdb: PASS`. A negative-control
PASS means the broken guest exited with failure and the checker rejected it.
The overall command exits zero only when every selected check passes.

The build explicitly disables PIE (`-fno-pie -no-pie`) for these fixed-address,
freestanding ELFs. This matters with Ubuntu's `aarch64-linux-gnu-gcc`, whose
PIE defaults can otherwise add GOT entries outside the startup's `.data` copy.
A successful link alone would then hide runtime failures in startup, exceptions,
timer and MMU lessons. Both that compiler and Arm GNU 13.2.Rel1 are checked.
Failed runs print their guest/debugger diagnostics as well as saving the logs.

Run one exercise with `python3 qemu/labs/run.py --only startup`, replacing
`startup` with `corruption`, `exception`, `timer`, `mmu`, `uart` or `multicore`.
The runner writes guest logs, exact QEMU commands, tool versions, source and
ELF hashes, UART cases and `results.json` under `runs/qemu-labs-<UTC timestamp>/`.
It requires a fresh begin marker, every required PASS marker, `LAB COMPLETE`,
no FAIL line and QEMU exit zero. Batch guests have a ten-second host timeout.

## 1. Prove startup initialized memory

Read [startup.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/startup.c),
then inspect `start.S` and `link.ld` in the same directory.
Predict the value of `initialized` before and after `_start` copies `.data`.

The linker gives `.data` a load address of `0x40300000` and runtime address of
`0x40400000`. Startup copies between them. It poisons BSS with `0xa5` before
clearing it, so QEMU's initially zero RAM cannot conceal a missing clear loop.
The stack top is `0x41000000` and must remain 16-byte aligned.

Expected markers are `DATA_RELOCATED`, `DISTINCT_LOAD_AND_RUNTIME_ADDRESSES`,
`BSS_ZERO` and `STACK_ALIGNED_IN_RANGE`. Each appears prefixed with `PASS`.
The two failure variants omit copying or clearing and fail the matching check.

For manual inspection, start a paused guest in one terminal:

```sh
python3 qemu/labs/run.py --debug --only startup
```

In another terminal, from the same directory:

```sh
gdb-multiarch build/qemu-labs/startup.elf
```

```text
target remote 127.0.0.1:3339
p/x initialized
x/gx &__data_load
hbreak main
continue
p/x initialized
p/x $sp
```

Before startup, `initialized` is zero while its load image contains
`0x123456789abcdef0`. At `main`, it contains that value and BSS is zero.
`--gdb` automates these assertions, including checking the whole BSS range.
Detach and quit GDB to let the guest finish.

## 2. Find the corrupted word with a watchpoint

[corruption.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/corruption.c)
copies 512 words, deliberately flips one bit in destination word 37, locates
the mismatch, then repairs and verifies the entire copy. Predict the changed
value before running it.

Expected: index 37, expected `0x1234567800000025`, actual
`0x1234567800000024`, followed by `PASS REPAIRED_COPY_512_WORDS`.
The omitted-injection variant must fail because the expected mismatch is absent.

Start `--debug --only corruption`, open `build/qemu-labs/corruption.elf` in
GDB, and connect to port 3339 as above:

```text
hbreak copy_complete
continue
watch destination[37]
continue
bt
p/x source[37]
p/x destination[37]
```

The watchpoint must stop inside `inject_corruption`. The automatic GDB exercise
also continues to `lab_done`, checks status zero and compares all 512 words.

## 3. Capture a synchronous exception and resume

[exception.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/exception.c)
executes `BRK #0x123`. Its handler checks the exception class, immediate value
and exact fault PC, then advances `ELR_EL3` to a known resume label.

Expected `ESR_EL3=0x00000000f2000123`, `PASS BRK_SYNDROME_AND_RETURN` and
`PASS FAULT_PC_CAPTURED`. `ELR_EL3` depends on the build. `FAR_EL3` does not
identify a meaningful data address for BRK. The wrong-immediate variant executes
`BRK #0x124` and must fail syndrome validation.

Student checkpoint: explain why returning without changing `ELR_EL3` would
execute the same BRK again. Locate the saved registers and `eret` in `start.S`.

## 4. Wake from WFI using timer interrupts

[timer.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/timer.c)
configures GICv3 and the secure physical timer, then waits using `WFI`.
Secure Group 0 PPI 29 is delivered as an **FIQ at EL3**. The handler acknowledges
the interrupt, verifies its identity and timer status, rearms it and signals EOI.

Expected ten interrupts and `PASS TIMER_10_INTERRUPTS`, plus
`PASS TIMER_FREQUENCY` and `PASS WFI_IDLE_LOOP`. The interval is approximately
10 ms of guest counter time; this is not a host wall-clock timing qualification.
The wrong-PPI variant deliberately expects 28 and fails on the first interrupt.

Student checkpoint: identify the code that prevents an interrupt between the
loop condition and `WFI` from leaving the final iteration asleep indefinitely.

## 5. Catch an MMU write-permission fault

[mmu.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/mmu.c)
identity maps QEMU's low MMIO and 128 MiB RAM. RAM uses normal noncacheable
attributes; data caches remain disabled. A 2 MiB block at `0x44000000` is read-only;
the block at `0x44200000` remains writable.

The valid read and write checks must pass before a deliberate store to the
read-only block. Expected `ESR_EL3=0x000000009600004e`,
`FAR_EL3=0x0000000044000000`, and `PASS MMU_WRITE_PERMISSION_FAULT`.
The handler verifies a same-level data abort, write access and level-2 permission
fault, records the fault PC, then resumes after the store. The original read-only
value must remain unchanged, and the MMU is disabled before completion.

The writable-permission variant allows the store, so the required exception is
absent and the checker must fail. Student checkpoint: find the AP bit that changes
this result, and distinguish a permission fault from an unmapped-address fault.

## 6. Exercise a UART command parser

[uart.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/uart.c)
provides a PL011 receive loop. Run it directly in a terminal:

```sh
python3 qemu/labs/run.py --interactive
```

At `lab>`, enter `help`, `status`, `memcheck` and `exit`. Backspace and Delete
edit input; CR, LF and CRLF terminate commands. The 32-byte buffer accepts 31
printable characters. Longer input is discarded through the next newline and
reports `ERROR line too long`; the next valid command must work.

The batch runner tests 11 cases, including both editing characters, unknown and
empty commands, 31/32/80-character boundaries, overflow recovery and clean exit.
`memcheck` verifies 32 words and prints `PASS UART_MEMCHECK`; `exit` prints
`PASS UART_SESSION`. Interactive input times out after 60 seconds without a byte.

## 7. Verify secondary-core execution

[multicore.c](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/labs/multicore.c)
runs with four virtual cores. Each secondary records its MPIDR, MIDR and exception
level in shared RAM. The primary checks three distinct core identities and EL3,
then prints `PASS THREE_SECONDARIES_EXECUTED`. Run it with
`python3 qemu/labs/run.py --only multicore`.

This is a secondary execution and identity exercise. QEMU startup differs from
the Agilex reset sequence; this lesson does not establish PSCI or cache coherency.
The dedicated DSU and PSCI examples test those separately.

## Scope and evidence

The [recorded validation](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/qemu-labs)
contains actual QEMU and GDB output. These exercises test emulator behavior and
software checks; they do not qualify Agilex MMIO, DDR bring-up, physical serial
ports, cache coherency or real-time interrupt latency. The EL3 exception setup
and addresses are specific to this QEMU configuration.
