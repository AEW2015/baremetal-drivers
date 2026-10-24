# Simulated student reviews and improvements

Three agent personas reviewed the tutorial as fictional students. This is a
**simulated review, not a study with real students**. The reviewers inspected
instructions and source; the debugger persona additionally reproduced two safe
configuration failures. The primary agent performed the automated, emulator and
physical-board checks listed separately below. No desktop VS Code F5 session
was exercised.

## Personas and feedback

| Student | Task and difficulty | Finding | Improvement |
|---|---|---|---|
| New embedded developer, no board | Install tools, build, debug QEMU | Repeated relative paths and fresh terminals lost the working directory/PATH; x86 toolchain assumption unclear | Persistent environment template, absolute workspace path, explicit architecture and no-board route |
| Developer learning GDB | Occupied port, missing tools, deliberate failed check | Missing tools raised tracebacks; an unrelated listener could produce false READY; NEON failure mislabeled the separate memory result | Actionable errors, owned GDB socket, bounded output-preserving checks, independent result labels |
| Hardware lab student | Identify UART, mount checkout, initialize DDR, stop debugger | Wrong clone could be loaded; standalone bootstrap bypassed debugger lock; fresh-board decision was too late | Same-mount nonce and artifact hashes, shared lock, preflight doctor, early full-recovery choice |
| All three, follow-up review | Recover from failure | Long stages looked silent; restoration error could obscure original error; remote process cleanup needed stronger proof | Live log paths, durable separate restoration result, exact owned-PID cleanup and unresolved-record guard |

The debugger review reproduced a missing QEMU executable and an invalid UART/
unset hardware configuration. Other findings initially came from source review.
Follow-up reviews checked the revised learner sequence and caught additional
cleanup gaps before publication. These were review findings, not observations
of real student behavior.

## Executed checks

- **18 automated tests passed** with the real-QEMU option enabled in the existing
  Agilex container. Tests cover missing tools/files, missing markers, nonzero
  exits, timeout output and child cleanup, occupied ports, wrong mounts, UART
  validation, inherited locks, durable restoration errors, unresolved-process
  guards and exact process ownership. An isolated process that ignores TERM is
  killed and verified stopped even when its simulated Docker transport exited;
  unrelated processes are preserved.
- The real emulator test builds temporary source copies, runs the passing
  exercise, deliberately changes one NEON operand, rebuilds, and requires
  overall failure while the independent memory copy still passes.
- Current QEMU ELF was debugged with command-line GDB: `qemu_done(status=0)`,
  `failures=0`, vector `{11,22,33,44}` and matching copied words.
- The revised host runner was checked on the physical Modular ES kit using
  **core + DDR Hello restoration**. This exercises fresh DDR initialization,
  loading/capture and the revised owned-process lifecycle. The complete
  historical 15-entry campaign was not repeated for these runner changes.

[Machine-readable manifest and captured logs](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/student-review)
record the checked files, artifacts and results separately from older evidence.

## Repeat the software checks

From `examples/agilex5-modular`, in a Python 3 Linux development environment:

```sh
python3 -m unittest discover -s tests -v
```

This default run uses temporary fake tools and processes; the real emulator test
is skipped. With compiler and QEMU installed in this same environment:

```sh
AGILEX_TEST_REAL_QEMU=1 python3 -m unittest discover -s tests -v
```

Both commands avoid hardware. GitHub Actions runs the real-QEMU option and strict
website build on each change. Physical checks require the [hardware prerequisites](hardware.md).

## Remaining limits and reporting a problem

Desktop VS Code extension behavior and Windows/macOS hosts remain unverified.
The supported walkthrough is Linux, with an existing board-specific container
for hardware. The per-checkout lock cannot coordinate separate clones or arbitrary
JTAG tools; assign one bench owner. Physical USB disconnect, power loss and
stuck kernel/device drivers were not fault-injected. Unverified cancellation
blocks further programming until an owner investigates the preserved record.

Use [troubleshooting](troubleshooting.md) first. For actionable feedback, record
the lesson URL/step, host versus container, architecture, tool versions, exact
command, expected and actual output, doctor results and the failed run's
`results.json`/logs. Identify the image/handoff checksum when relevant. Remove
credentials and personal paths before sharing. State whether the failure is
repeatable and whether DDR restoration passed; do not report an older PASS log
as the outcome of the failing attempt.
