# Educational coding standard

A student should be able to locate the entry point, predict one operation, step
through it, and explain how the result was checked. This is a local teaching
standard for authored labs, rather than a claim of MISRA, CERT or functional
safety certification. Existing upstream and vendor snapshots retain their own
style and licenses so that their provenance and behavior remain reviewable.

## Each lesson has a contract

Before presenting register operations, document:

- **Goal:** the single concept being demonstrated and what is outside its scope.
- **Environment:** QEMU `virt`, the exact Simics model or the physical board;
  CPU exception level, clocks and required firmware where relevant.
- **Resources:** memory ranges, peripheral instance, cache/MMU state, interrupts,
  external wiring and any state changed by the exercise.
- **Commands:** working directory, host versus container, build command, run
  command, expected output and completion/exit status.
- **Verification:** an independently computed expectation, complete readback,
  a useful deliberately wrong input and a recovery step.
- **Evidence:** actual captured output and its tested artifact scope. A successful
  compilation, generic completion line or model result is not a hardware PASS.

For a first example, follow [Hello World](hello-world.md). Use the
[example finder](example-finder.md) to find its source and execution evidence.

## C and assembly students can step through

Use four spaces, braces around conditional/loop bodies, one operation per line,
descriptive names and functions with one visible purpose. Aim for 100 columns.
The local [`.clang-format`](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/.clang-format)
records this preference; apply it to authored files being changed, after reviewing
the diff. Generated outputs and unchanged vendor fixtures are excluded.

Name MMIO bases, register offsets, masks, sizes and time budgets. Explain where
an address comes from. Use fixed-width types for register/data formats and
`uintptr_t` for address conversion. `volatile` describes device accesses or
observable storage; it does not replace cache maintenance or synchronization.
Explain barriers and cache assumptions beside the operation that needs them.

Organize each check as **arrange → act → verify → report**. Keep verification
outside the implementation it checks. Give NEON and memory independent failure
counts; combine them only for the final outcome. Verify every transferred word
when claiming a complete copy. Do not weaken a check to get a PASS.

Bound peripheral waits and print actionable failures. If the output UART itself
stalls, a bounded nonzero host exit is useful even when the UART cannot print an
error. A final WFI park loop after completion is an intentional terminal state,
not a peripheral polling timeout. Keep breakpoint symbols and result variables
stable when they are part of a published debugger lesson.

Introduce abstractions when they explain the hardware or remove distracting
repetition. Keep the first lab small enough to read in one sitting; avoid adding
a framework before the student understands the underlying operation.

## Python, shell and RTL support the lesson

Python follows four-space indentation and readable functions. Separate argument
validation, resource acquisition, operation, verification and cleanup. Print long
running stages. Use explicit timeouts, preserve failure evidence, and clean up
only owned resources. Do not interpolate student input into shell commands.

Shell scripts fail on errors, quote paths and identify their working directory
and required tools. RTL states its interface, reset behavior, register ABI and
backpressure assumptions. Tests cover the public behavior, including wrong
inputs and stalled peers, rather than merely repeating implementation formulas.

## Adoption and review

The QEMU first lesson now applies this standard. Existing advanced examples have
stronger verification than their compressed presentation suggests, but they are
**not all style-compliant**. The [audit](education-audit.md) records the inventory,
manual findings and remaining work. Reformat/refactor board-specific code in
small changes and rerun the supported targets before renewing execution claims.
Never transfer a historical ELF's PASS to a rebuilt ELF solely because a change
looks cosmetic.

For each teaching change, review the lesson contract, inspect the diff, rebuild,
run the supported positive/negative exercises, and check the website/diagram
links. Hardware changes additionally use the existing mutex and restoration
checks. Use a fresh runtime result rather than replacing historical evidence.
