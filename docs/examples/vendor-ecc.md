# Vendor ECC register/default checks

`vendor-ecc` · `build/vendor_ecc.elf` · recorded entry `0x80200800`

[Board adapter](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/vendor_wrapper.c) · [Vendor sample](https://github.com/altera-fpga/baremetal-drivers/blob/1419101568f1a9034630b632634fe9fe71773266/test/simics/ecc/ecc_test.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T232734.166542Z/vendor-ecc-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Open the vendor ECC device, read its revision/status/control/counter fields and run the sample’s register/default comparisons. Close it and report the return status.

    1. Apply the sample’s volatile reset-manager setup and open the ECC driver.

    2. Read revision IDs and selected initialization, interrupt, counter, lookup and access-control registers.

    3. Complete the sample’s checks and require the wrapper’s zero return result.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_vendor.sh
    python3 build_board_vendor.py ecc
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only vendor-ecc
    ```

    Do not enable injection or alter persistent/active system state when following this readout example.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Revision snapshot | REV_ID=0; REV_ID_2=0x1500b | Values are printed in hexadecimal without a 0x prefix. |
    | Recorded initialization/error fields | INSTAT, error-enable/status and reported counters were zero | Inspect the full capture for the individual fields. |
    | Completion | ECC Tests successful!!! and HPS_SUITE_PASS ecc rc=0x00000000 | Required final result; a partial register dump is insufficient. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS_SUITE_BEGIN ecc
    Started Logging
    ECC Test Starts
    ECC successfully open
    REV_ID =0
    REV_ID_2=1500b
    INSTAT=0
    ERRINTEN=0
    ERRINTENS=0
    ERRINTENR=0
    ... (additional register readout omitted) ...
    ECC close: OK
    ECC Tests successful!!!
    HPS_SUITE_PASS ecc rc=0x00000000
    ```

    ECC status and counters can change after prior activity or faults; fresh bootstrap and the exact hardware profile matter.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    No single-bit/double-bit error is deliberately injected, and no interrupt handler, correction, syndrome decoding or recovery is tested. Register defaults alone do not establish that all HPS memories are ECC protected.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
