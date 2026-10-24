# Fresh-clone validation of the remote repository

On 24 October 2026 UTC, the public fork was cloned into a new bind-mounted
checkout and tested at `0daff10b3ea2d1075fa75c8f5c16526ed99b2e98`.
That was the remote `main` head at the start; there were no newer remote branches
or open pull requests. Builds fetched their upstream dependencies rather than
reusing another checkout's build directory.

## Results

| Check | Observed result |
|---|---|
| QEMU Hello: EL3, NEON, 4096-byte CPU copy | PASS, exit 0 |
| Predict/change/corrupt/recover experiment | All six stages behaved as expected |
| Hello CLI GDB | Main breakpoint, instruction step, `qemu_done`, status 0, vector `{11,22,33,44}` and all 512 copied words verified |
| Six QEMU practice labs | All six normal cases, six negative controls and both GDB exercises passed with Arm GNU 13.2.Rel1 |
| UART parser | All 11 input/editing/overflow/recovery cases passed |
| Full hardware/reference build | PASS, including upstream dependencies and all 15 registered suite ELFs |
| OCRAM ELF, binary, HEX and HPS-RBF packaging | PASS |
| ADD/XOR fabric RTL and C driver | Both personas passed Verilator checks; AArch64 driver build passed |
| Regression suite | Original 29 passed; 30 passed after adding the early-cancellation regression |
| Skill package and website | Skill validation and strict MkDocs build passed; baseline 36 HTML pages had no broken local paths |

The tools were Arm GNU 13.2.Rel1, QEMU 8.2.2, GDB 15.1, Quartus 26.1.1 and
Quartus OpenOCD. The separate Ubuntu compiler check used
`aarch64-linux-gnu-gcc` 13.3.0. The evidence manifest records dependency revisions,
source revision, ELF hashes and the matching FPGA/DDR artifact hashes.

## Two defects found and corrected

### Early cancellation could reject the owned launcher

The original launcher wrote its PID record after setting a Python environment
variable, but before exec. A deterministic test held it at that point. Its
`/proc` initial environment did not yet expose the token, so cancellation
incorrectly reported an ownership mismatch. This explains the earlier
intermittent CI cancellation failure.

Commit `65182bc` sets the token through `env` before the Python launcher starts
and publishes its PID. Exact PID/token checks remain in place. The new regression
forces the former failure window. All 30 regressions passed, as did three real
Docker cancellation checks and a normal captured command completion.

### The Ubuntu compiler's PIE defaults broke relocated labs

Adding the six labs to GitHub Actions exposed failures that the pinned
bare-metal compiler did not show. A local Ubuntu-compiler replay reproduced them:
GOT sections lay outside the minimal startup's `.data` relocation, leaving
references to linker symbols and exception labels incorrect at runtime. A
successful link concealed failures in startup, exception, timer and MMU lessons.

Commit `c943a0b` explicitly builds these fixed-address ELFs with
`-fno-pie -no-pie`. Both compilers then passed all 14 normal/negative/GDB checks.
The runner now prints failed guest/debugger diagnostics, and CI runs the labs
with `gdb-multiarch` installed. The
[expanded remote CI run](https://github.com/AEW2015/baremetal-drivers/actions/runs/40054538908)
passed without a retry. Both lessons are included in the repository skill.

## Physical Modular ES campaign

All 15 registered entries passed in one fresh-clone run at `0daff10`, using
newly built ELFs and a newly built DDR initializer:

| Entries | Result |
|---|---|
| `core`, `dma`, `gic`, `mmu` | PASS |
| `som`, `som-i2c`, `multicore`, `som-i3c` | PASS |
| `mailbox`, `interfaces` | PASS |
| `vendor-uart`, `vendor-ccu`, `vendor-clkmgr`, `vendor-smmu`, `vendor-ecc` | PASS |

Every example received a fresh DDR bootstrap. The final restoration passed
four 64 MiB patterns, payload readback and fresh Hello output, with PC
`0x82000028` inside the DDR payload. CCU/clock default-value warnings and the
configured-2-GiB/detected-8-GiB warning remain visible; they were not suppressed.
The SMMU wrapper checked the exact SOM IIDR `0x4832243b`.

The same checkout was then fast-forwarded to `c943a0b` for the OCRAM and
corrected-launcher follow-up. The hardware example C/assembly sources were
unchanged by those fixes. OCRAM's fresh HPS RBF produced three exact
`Hello, World! Agilex 5 HPS OCRAM UART` lines, with PC `0x138` inside its code
region. Its capture contains older DDR Hello lines too; those are not counted
as OCRAM evidence.

Both core and DMA then passed with the corrected launcher. Final DDR restoration
passed again, with PC `0x82000024`. Debug ports and all three checkout locks were
released; no QEMU/OpenOCD process, UART reader or unresolved ownership record
remained. DDR Hello was left running.

## Evidence and scope

The [raw logs and structured results](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/remote-audit)
retain the clean-clone build, QEMU/GDB transcripts, compiler failure and recovery,
forced cancellation failure, physical UART/debug/bootstrap logs and hashes.
Serial captures retain their original bytes under `.txt` extensions for viewing
on GitHub. Absolute paths and helper scripts describe this bench. The OCRAM
helper adapts the original bench runner to the new image/path and exact UART
marker, using the corrected owned-process wrapper under shared hardware locks.
It is audit tooling rather than a new packaged OCRAM runner.

The first custom Hello GDB audit timed out using per-element remote evaluation.
Its failed log is retained; a repeat with clean GDB startup and bulk memory
comparison passed. No Hello source change was needed.

This campaign does not qualify a new FPGA design, a live PR swap, the full 8 GiB
bank, cache coherency, Ethernet traffic, USB enumeration, SD media access,
native I3C target protocols or ECC injection/recovery. U-Boot/Linux recipes and
the PSCI example remain outside the executed suite. The existing desktop GUI
was not rerun during this CLI/hardware campaign; its separate evidence is in
[the desktop follow-up](feedback-followup.md).
