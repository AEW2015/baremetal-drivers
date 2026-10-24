# Multicore: release A55/A76 secondaries

`multicore` · `build/multicore.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/multicore.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/multicore-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Boot from A55.0, set the three secondary reset vectors, apply the matching ATF power/reset sequence and verify that the second A55 and both A76 cores publish identification records.

    1. Clear secondary records at `0x85300000` and install a stable parking loop at `0x82010000`.

    2. Release the secondaries and wait for their `0xcafe` ready flags.

    3. Verify each affinity and CPU part number, then leave secondaries parked.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only multicore
    ```

    Requires the A55 boot configuration and all CPU/scratch ranges under this test’s ownership.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | A55.1 record | Ready 0xcafe; MPIDR 0x81000100; MIDR 0x412fd050 | Recorded bench values; the code checks affinity and part number. |
    | A76.0 record | Ready 0xcafe; MPIDR 0x81000200; MIDR 0x414fd0b1 | Second secondary record. |
    | A76.1 record | Ready 0xcafe; MPIDR 0x81000300; MIDR 0x414fd0b1 | Third secondary record. |
    | Final result | All three secondary records verified | A missing or wrong record fails. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS MULTICORE EXAMPLE BEGIN
    MPIDR = 0x0000000081000000
    Boot config = 0x000000000070031e
    CPU in reset = 0x000000000000000f
    PCH control = 0x0000000000000003
    Secondary record = 0x000000000000cafe
    Secondary MPIDR = 0x0000000081000100
    Secondary MIDR = 0x00000000412fd050
    Secondary record = 0x000000000000cafe
    Secondary MPIDR = 0x0000000081000200
    Secondary MIDR = 0x00000000414fd0b1
    Secondary record = 0x000000000000cafe
    Secondary MPIDR = 0x0000000081000300
    Secondary MIDR = 0x00000000414fd0b1
    PASS MULTICORE: three secondary cores executed and published records
    ```

    CPU revision fields can vary; do not infer a hardware failure from a revised MIDR without inspecting the checked part/affinity fields.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    Direct EL3 reset/power control is used, not PSCI CPU_ON. The test does not establish shared-cache coherency, SMP scheduling, interprocessor messaging or multicore throughput. Secondaries remain parked until the next bootstrap.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

