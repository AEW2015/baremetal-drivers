# GIC: secure software interrupt

`gic` · `build/gic_sgi.elf` · recorded entry `0x82300000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/gic_sgi.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/gic-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=board%2Fgic){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=board%2Fgic" data-example-id="board/gic">board/gic</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=board%2Fgic" title="HPS and fabric diagram for examples/gic.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "What it does"

    Power up and wake the boot core’s GIC-600 redistributor, configure secure Group-0 SGI0, send it to A55.0 and poll the interrupt-acknowledge register.

    1. Wait for the redistributor power transition and clear its power-down request.

    2. Clear the redistributor sleep request, enable SGI0 and the secure CPU interface.

    3. Issue the SGI, require acknowledgement ID 0 and write end-of-interrupt.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_gic.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only gic
    ```

    Requires exclusive ownership of the GIC. The runner reboots the diagnostic before the next ELF.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Boot affinity | MPIDR affinity fields all zero | This program is specifically for boot core A55.0. |
    | Acknowledged interrupt | SGI ID 0 | Timeout or a different interrupt does not pass. |
    | Result marker | PASS GIC_SGI | Confirms the polled path completed. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS GIC SGI EXAMPLE BEGIN
    PASS GIC_SGI: core 0 received and acknowledged SGI 0
    ```

    There is no timing or performance threshold in the expected output.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    Interrupt acknowledgement is polled. This does not test a C exception handler, vector entry, IRQ latency, external interrupts or cross-core interrupt delivery. The test temporarily owns GIC configuration.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
