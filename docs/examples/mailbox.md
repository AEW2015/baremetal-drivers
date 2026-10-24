# SDM mailbox: read FPGA IDCODE

`mailbox` · `build/mailbox_status.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/mailbox_status.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/mailbox-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Send an SDM GET_IDCODE command using the current mailbox ring pointers and validate the returned response header and FPGA device ID.

    1. Require command and response rings to be idle; do not consume someone else’s pending messages.

    2. Submit the client/job-tagged read-only ID request and ring the doorbell.

    3. Check error/length/client fields, then read and check the IDCODE.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only mailbox
    ```

    No external peripherals are needed, but the mailbox must not have another active owner.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Response header snapshot | 0x1e001000 | Correct tag, one payload word, no error. |
    | Device ID snapshot | 0x0364f0dd | Code compares the lower 28 bits to this Modular ES ID. |
    | Final marker | PASS MAILBOX_IDCODE | Requires both response validation and matching device identity. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS MAILBOX EXAMPLE BEGIN
    SDM response header = 0x000000001e001000
    SDM device IDCODE = 0x000000000364f0dd
    PASS MAILBOX_IDCODE: SDM returned matching Agilex 5 device ID
    ```

    Do not blindly replace the expected ID on different hardware. Verify its documented device/revision fields and board profile.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    This is one read-only management command. It does not test secure services, FPGA reconfiguration, sensor mailbox commands, authentication or error recovery. A busy ring causes a failure without consuming existing messages.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

