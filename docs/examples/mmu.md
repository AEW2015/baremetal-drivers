# MMU: EL3 translation and readback

`mmu` · `build/mmu_translation.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/mmu_translation.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/mmu-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=board%2Fmmu){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=board%2Fmmu" data-example-id="board/mmu">board/mmu</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=board%2Fmmu" title="HPS and fabric diagram for examples/mmu.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "What it does"

    Build a minimal EL3 identity map, enable translation, translate a DDR address using AT S1E3R and verify a memory store/read while the MMU is on. Restore the original SCTLR afterward.

    1. Map the low 2 GiB as device memory and the upper part of the 4 GiB window as normal noncacheable memory.

    2. Translate virtual address `0x85200000` and inspect `PAR_EL1`.

    3. Write/read `0x12345678abcdef01` at that address, disable the temporary map and invalidate translations.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only mmu
    ```

    Starts with MMU and D-cache disabled; uses one DDR scratch word at 0x85200000.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Translation fault flag | PAR bit 0 clear | The AT operation succeeded. |
    | Translated address | 0x85200000 | Compare the physical-address field, not every attribute bit. |
    | Readback | 0x12345678abcdef01 | Confirms actual DDR access while translation is enabled. |
    | Observed PAR snapshot | 0x4400000085200900 | Includes memory-attribute/status bits. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS MMU EXAMPLE BEGIN
    PAR_EL1 = 0x4400000085200900
    PASS MMU_TRANSLATION: EL3 translation and DDR readback
    ```

    PAR attribute bits describe the mapping. The implementation checks the physical-address field and fault bit explicitly.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    This is an EL3 identity-map example with D-cache off. It does not exercise paging, EL1 process isolation, access faults, virtual-address remapping or cache coherency.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
