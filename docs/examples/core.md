# CPU, NEON and core checks

`core` · `build/core_examples.elf` · recorded entry `0x82100000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/core_examples.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/core-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=board%2Fcore){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=board%2Fcore" data-example-id="board/core">board/core</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=board%2Fcore" title="HPS and fabric diagram for examples/core.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "What it does"

    A first hardware smoke test for A55.0. It reads CPU/exception-level and cache registers, adds two four-lane vectors, copies 64 KiB in DDR using the CPU, reads GPIO0 inputs and checks that the physical counter advances. It also reads the GIC identification registers.

    1. Add `{1,2,3,4}` and `{10,20,30,40}` using NEON; require `{11,22,33,44}`.

    2. Fill 8192 64-bit source words at `0x85000000`, copy them to `0x85010000`, and compare each destination word.

    3. Read GPIO0 without changing its direction, and compare successive physical-counter values.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_core.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only core
    ```

    No external peer or button press is needed. Reserve both 64 KiB DDR buffers.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | NEON result | 11, 22, 33, 44 | All four lanes are checked in code. |
    | CPU copy | 65536 bytes, every word correct | CPU copy; separate from the DMA example. |
    | Execution level | CurrentEL printed as 0xc on this bench | EL3 is the bootstrap prerequisite; the register is reported. |
    | Counter | After > before | The precise delta varies; no fixed elapsed time is asserted. |
    | Boot CPU snapshot | MIDR 0x412fd050, MPIDR 0x81000000 | Recorded A55.0 values; other silicon revisions can differ. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS CORE EXAMPLES BEGIN (DDR 0x82100000)
    MIDR_EL1 = 0x00000000412fd050
    MPIDR_EL1 = 0x0000000081000000
    CurrentEL = 0x000000000000000c
    PASS CPU_NEON: four vector additions
    CTR_EL0 = 0x0000000084448004
    CLIDR_EL1 = 0x00000000c3000123
    SCTLR_EL3 = 0x0000000030c5183a
    PASS CACHE_INFO: configuration read; cache coherency is a separate test
    PASS DDR_BUFFERS: CPU copied and verified 64 KiB
    GPIO0 direction = 0x0000000000000000
    GPIO0 external inputs = 0x0000000000490f48
    PASS GPIO_READ: no output pin direction changed
    CNTFRQ_EL0 = 0x0000000000000000
    Counter delta = 0x00000000027ac52e
    PASS COUNTER: generic timer increments
    GICD_TYPER = 0x00000000007b0411
    GICD_IIDR = 0x000000000201743b
    PASS GIC_INFO: identification only; interrupt delivery is a separate example
    HPS CORE EXAMPLES COMPLETE
    ```

    Counter delta, GPIO inputs and some control-register snapshots vary. Match the six PASS markers and completion marker, rather than byte-comparing the entire capture.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    Cache registers describe configuration; they do not prove coherency or cache performance. GPIO input values depend on board state. GIC ID reads are not interrupt delivery. CNTFRQ was zero, so this test does not establish a usable delay calibration.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
