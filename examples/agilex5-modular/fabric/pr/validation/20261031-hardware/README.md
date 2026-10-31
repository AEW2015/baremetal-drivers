# Physical partial reconfiguration — 2026-10-31

**PASS: real ADD → XOR → ADD PR on the Agilex 5 Modular ES kit.** One HPS
application stayed alive across two `quartus_pgm --pr` loads, with no application
restart between personas. DDR Hello was restored afterward, including fresh
UART, four 64 MiB patterns, payload readback and CPU-PC proof.

Board: `A5ED065BB32AE6SR0`, FPGA JTAG ID `0364F0DD`, HPS DDR bank 3A.
Quartus Prime Pro 26.3 Build 114; Arm GNU 13.2.Rel1; pinned ATF
`2ea5afda7f34774ddcc677fb3a728fa57f780a1e`. No flash, media, EEPROM, clock NVM or
fuses were written. Hardware ran under the canonical board mutex at 6 MHz JTAG.

[Reproduce the build and deployment](../../hardware/README.md).
The deployed image uses **FPGA first / After INIT_DONE**, not the source
baseline's HPS-first phase-1-only boot.

## Actual terminal output

Captured from [the final hardware UART](hardware/guest-uart.txt):

```text
PR_LAB_BEGIN jtag_loader=1
PASS INITIAL_ADD_ID
PASS INITIAL_ADD_VECTORS
PASS ISOLATED_READ_RESPONSE
PR_TIMER_HZ=0x0000000000000000
PR_HOST_LOAD_REQUEST=0x00000000584f5231
PR_PERSONA=0x00000000584f5231
PASS SWAP_RESET_AND_ID
PASS XOR_VECTORS
PASS STATIC_SCRATCH_CONTINUITY
PASS STATIC_HEARTBEAT_PROGRESS
PASS DDR_GUARD_256_WORDS
PASS ISOLATED_READ_RESPONSE
PR_TIMER_HZ=0x0000000000000000
PR_HOST_LOAD_REQUEST=0x0000000041444431
PR_PERSONA=0x0000000041444431
PASS SWAP_RESET_AND_ID
PASS RETURN_ADD_VECTORS
PASS STATIC_SCRATCH_CONTINUITY
PASS STATIC_HEARTBEAT_PROGRESS
PASS DDR_GUARD_256_WORDS
PASS TWO_RUNTIME_SWAPS
PR_LAB_COMPLETE status=0
```

Both programmer logs show positive partial-programming completion:
[XOR](hardware/xor-pr.log), [return ADD](hardware/add-pr.log).
The independent JTAG master checks PRS1, frozen state, scratch and intended
persona before setting BUSY. After each actual load, DONE permits reset,
identity verification and application release. The physical wrapper has no
simulation-loader register.

## Evidence

- [Hardware results and artifact SHA-256 hashes](hardware/results.json),
  [device user-mode status](hardware/base-config-status.json),
  [guest binary readback](hardware/guest-readback.json),
  [restoration](hardware/restore.log).
- [ADD compatibility](add-fpga-first-compatibility.json) and
  [XOR compatibility](xor-fpga-first-compatibility.json) against the exact
  bootloader-embedded base; [metadata](base-fpga-first-analysis.json).
- [Compiler job IDs](build-jobs.json), synthesis/fitter/assembler logs here,
  final [partition placement report](baseline_a55.fit.place.rpt), and
  [timing summaries](timing-minimum-slack-ns.json).
- [Simics actual results](simics/results.json): positive swap, loader error and
  wrong persona all passed. [Platform assessment](simics/assessment.json) stays
  **partial** because the loader is simulated; no SDM/RBF parser is modeled.
- [Fresh learning-container check](learning-container.log) at commit `b7393de`,
  plus [final model build](final-model-build.log). [Final clean-clone check](final-clean-clone-learning-check.log) at `253af02`
  also passed, including all six host/evidence guard tests. Proprietary tools are installed
  outside the public learning image.

| Revision | Setup ns | Hold ns | Recovery ns | Removal ns |
|---|---:|---:|---:|---:|
| baseline_a55 | 2.221 | 0.0 | 4.31 | 0.164 |
| pr_add | 2.221 | 0.0 | 4.373 | 0.164 |
| pr_xor | 2.221 | 0.0 | 4.02 | 0.164 |

All values are minimum reported slack; zero hold slack is nonnegative.
The base passed 88/88 enabled final Design Assistant checks (10 disabled), with
no unmatched timing constraints. ES timing/uncertainty remains preliminary.
An intermediate Fitter region-node warning is retained; final PR/LogicLock
reports show the reviewed placement X62 Y61–X81 Y80 and routing X61 Y60–X82 Y81.
The boot-order correction reran ADD assembly against unchanged fitted data;
the assembler report confirms After INIT_DONE. Both final partials were
rechecked against that new full image.

## Failed attempts retained

1. [HPS First](attempt1-hps-first/results.json): DDR passed, but fabric stayed
   phase-1-only (`INIT_DONE=0`) and the first fabric read stalled. Stopped the
   owned runner and restored DDR Hello.
2. [Status parser](attempt2-status-parser/results.json): corrected image reached
   user mode, but the guard wrongly expected `STATE=USER_MODE`; the engine
   correctly reports IDLE with `INIT_DONE=1`. Recovery initially checked PC too
   early; [fresh recovery confirmation](attempt2-recovery-confirm/results.json)
   proved DDR Hello and PC `0x82000024`. Recovery now pre-halts the prior boot.
3. [Unlinked master](attempt3-unlinked-master/xor-begin.log): raw service paths
   omitted instance names. Explicit SOF design loading/linking supplies them.
4. [Cable formatting](attempt4-cable-path-format/xor-begin.log): display brackets
   differ from service-path delimiters; binding now matches both cable name and
   USB location plus device index.
5. [Endpoint suffix](attempt5-service-name-suffix/xor-begin.log): linked service
   ends in `u_pr_jtag.master`; selection now accepts the dot separator.

Hardware also confirmed `CNTFRQ_EL0=0`. The physical guest stays isolated while
waiting, and the host enforces the wall-clock bound. Regression tests cover the
observed status and service formats, wrong devices/identity/state, modified
artifacts, failed compatibility evidence and false success markers.

The 256-word guard proves continuity during these swaps; the 64 MiB boot test
is not full-bank DDR qualification. Physical load-error/wrong-persona injection
was not attempted; those controls were tested in RTL and Simics. The custom
single-clock, nonbursting agent is not a general AXI/Avalon freeze bridge.
Programming binaries, QDBs and licensed tool payloads remain local; the repo
tracks reproducible source, hashes and text evidence.
