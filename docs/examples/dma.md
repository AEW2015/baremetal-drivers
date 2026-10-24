# DMA: 4096-byte transfer

`dma` · `build/dma_copy.elf` · recorded entry `0x82200000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/dma_copy.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/dma-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Exercise HPS DMAC0 channel 0 using a linked descriptor. The CPU prepares source/destination buffers; the DMA engine transfers the data, and the CPU verifies all 512 destination words.

    1. Initialize source `0x85100000`, destination `0x85110000` and a linked-list descriptor at `0x85120000`.

    2. Configure 64-bit transfer widths and one block of 512 transfers.

    3. Wait for the actual completion bit using AND, then compare every transferred word.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_dma.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only dma
    ```

    No external peripheral is needed. Do not run alongside another DMA user.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Transfer length | 4096 bytes | 512 × 8-byte words. |
    | Channel completion | Status bit 0x2 is set | Recorded status was 0x2; completion is a bit test. |
    | Destination | All 512 words equal source | A completion flag alone is insufficient. |
    | Controller snapshots | ID 0x746a1, version 0x3230302a | Observed values, printed as diagnostics. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS DMA EXAMPLE BEGIN
    DMAC0 ID = 0x00000000000746a1
    DMAC0 version = 0x000000003230302a
    DMA channel status = 0x0000000000000002
    PASS DMA_COPY: 4096 bytes transferred by DMAC0 and verified
    ```

    Controller revision snapshots may differ on other hardware. The required result is completion plus full readback, not a fixed transfer duration.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    The current test requires D-cache disabled and an idle controller. It does not establish coherent DMA, cache maintenance, scatter/gather across multiple descriptors or peripheral-to-memory transfers.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

