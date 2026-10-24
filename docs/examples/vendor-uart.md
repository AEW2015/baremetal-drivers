# Vendor UART transmit example

`vendor-uart` · `build/vendor_uart.elf` · recorded entry `0x80200800`

[Board adapter](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/vendor_wrapper.c) · [Vendor sample](https://github.com/AEW2015/baremetal-drivers/blob/main/test/simics/uart/uart_test.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T232734.166542Z/vendor-uart-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Run the original vendor UART sample through the physical-board entry and UART adapter. Preserve the initialized UART divisor, repair the libc output contract and report the application return code.

    1. Install the board C runtime, EL3 stack/vectors and noncacheable identity map.

    2. Call the vendor sample with UART initialization wrapped to preserve its physical clock divisor.

    3. Print the wrapper PASS/FAIL marker and the original main return code.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_vendor.sh
    python3 build_board_vendor.py uart
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only vendor-uart
    ```

    Use SOM J2 HPS_UART at 115200 8N1. The carrier serial interface is different.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Text | Hello, World! | The sample does not add a trailing newline. |
    | Wrapper result | HPS_SUITE_PASS uart rc=0x00000000 | Required by the runner. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS_SUITE_BEGIN uart
    Hello, World!HPS_SUITE_PASS uart rc=0x00000000
    ```

    Hello and the wrapper result appear on one line in the captured output; that is expected.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    This is a transmit/driver sample. It does not test UART receive, flow control, an external loopback or every baud rate.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

