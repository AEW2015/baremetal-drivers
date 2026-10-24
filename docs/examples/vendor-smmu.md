# Vendor SMMU identity check

`vendor-smmu` · `build/vendor_smmu.elf` · recorded entry `0x80200800`

[Board adapter](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/vendor_wrapper.c) · [Vendor sample](https://github.com/AEW2015/baremetal-drivers/blob/main/test/simics/smmu/smmu_test.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T233101.494937Z/vendor-smmu-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Run the vendor SMMU ID sample, then strengthen its bitwise-AND identity test with the wrapper’s exact comparison against the recorded Modular SOM IIDR.

    1. Release the sample’s selected reset and open the SMMU driver.

    2. Read IIDR through the vendor API.

    3. Print and require exact IIDR `0x4832243b` in the board wrapper.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_vendor.sh
    python3 build_board_vendor.py smmu
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only vendor-smmu
    ```

    No external peer is needed. Use the exact wrapper result, not the sample’s standalone “IIDR is accurate” line.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Exact SOM IIDR | 0x4832243b | Product 0x483, variant 2, revision 2, implementer 0x43b. |
    | Original sample expectation | 0x4832143b remains printed | Its revision-1 reference and weak AND check are not the final criterion. |
    | Return marker | HPS_SUITE_PASS smmu rc=0x00000000 | Requires the wrapper’s exact revision-2 value as well as vendor success. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS_SUITE_BEGIN smmu
    Starting Basic SMMU Test
    Verify if IIDR value equals 0x4832143b
    SMMU IIDR value is accurate
    SMMU exact IIDR = 0x4832243b
    HPS_SUITE_PASS smmu rc=0x00000000
    ```

    A new silicon revision can legitimately change IIDR. Decode the primary field definitions before qualifying a different expected value.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    No stream table, context descriptor or translated DMA transaction is installed. This is identification, not SMMU translation or isolation validation. The expected ID is specific to the documented SOM profile.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
