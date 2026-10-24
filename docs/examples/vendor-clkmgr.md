# Vendor clock-manager register readout

`vendor-clkmgr` · `build/vendor_clkmgr.elf` · recorded entry `0x80200800`

[Board adapter](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/vendor_wrapper.c) · [Vendor sample](https://github.com/AEW2015/baremetal-drivers/blob/main/test/simics/clkmgr/clkmgr_test.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T232734.166542Z/vendor-clkmgr-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Read common, main-PLL, peripheral-PLL and control-group registers using the vendor clock-manager driver. The sample prints differences from its expected reset/simulation register values.

    1. Open the clock manager and read each selected register group.

    2. Print a warning with offset, expected/actual value and differing bit positions for each mismatch.

    3. Require successful driver reads and a zero return code.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_vendor.sh
    python3 build_board_vendor.py clkmgr
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only vendor-clkmgr
    ```

    Use the matching initialized board design; do not treat simulation defaults as settings to write into the live clock tree.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Observed CTRL example | Expected 0x3, actual 0x0 | An already initialized clock tree differs from reset assumptions. |
    | Observed STAT example | Expected 0x031c1c00, actual 0x02030300 | A recorded snapshot, not a frequency measurement. |
    | Return marker | HPS_SUITE_PASS clkmgr rc=0x00000000 | Access test completed; warnings remain visible. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS_SUITE_BEGIN clkmgr
    [Warning] IOCTL_CLKMGR_REGS_READ at offset 0x0: expected: 0x3, actual: 0x0. bit diff location: 0, 1,
    [Warning] IOCTL_CLKMGR_REGS_READ at offset 0x4: expected: 0x31c1c00, actual: 0x2030300. bit diff location: 8, 9, 10, 11, 12, 16, 17, 18, 19, 20, 24,
    [Warning] IOCTL_CLKMGR_REGS_READ at offset 0x8: expected: 0x100808, actual: 0x0. bit diff location: 3, 11, 20,
    ... (additional register warnings omitted) ...
    HPS_SUITE_PASS clkmgr rc=0x00000000
    ```

    Clock state follows the FPGA/handoff/ATF design. Expect warning differences when the design changes, and review them with the clock configuration.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    The test does not measure clock frequency, jitter, stability or tolerance, and does not reconfigure the external clock generator. Zero return status does not assert equality with every reference register.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

