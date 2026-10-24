# I3C1 controller: legacy-I2C reads

`som-i3c` · `build/som_i3c.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_i3c.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/som-i3c-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Exercise the native I3C1 controller’s legacy-I2C transfer path against the same SOM TMP464 and EEPROM, using its command/response queues rather than GPIO bit-banging.

    1. Save IOA9/10 selection and select function 0 for I3C1. Reset/configure the controller and conservative bus timings.

    2. Create a legacy-I2C target entry and queue pointer-write/repeated-read commands.

    3. Require successful response status, the read transaction ID and the requested byte count.

    4. Check the manufacturer, read 16 EEPROM bytes, disable the controller and restore the pin selection on the successful path.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only som-i3c
    ```

    On this SOM, IOA9/10 function 0 is I3C1. Function 9 is HCLK and must not be substituted.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | TMP464 manufacturer | 0x5449 | Required after a successful two-byte controller read. |
    | Read response | TID 1, lengths 2 then 16, no error | Observed response words include 0x01000002 and 0x01000010. |
    | EEPROM | 16 bytes successfully returned | Snapshot was all 0xff; contents are not a pass condition. |
    | I3C1 version snapshot | 0x3130302a | Diagnostic readout. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS NATIVE I3C EXAMPLE BEGIN
    I3C1 pin selection = 0x0000000400000004
    I3C1 version = 0x000000003130302a
    I3C1 DAT pointer = 0x00000000000b0280
    I3C response = 0x0000000000000000
    I3C response = 0x0000000001000002
    TMP464 manufacturer = 0x0000000000005449
    PASS NATIVE_I3C_TEMP: legacy I2C read via I3C1
    I3C response = 0x0000000000000000
    I3C response = 0x0000000001000010
    PASS NATIVE_I3C_EEPROM: 16-byte read, no data writes
    HPS NATIVE I3C EXAMPLE COMPLETE
    (Capture also prints all 16 EEPROM bytes; see full UART log.)
    ```

    EEPROM data and response diagnostic snapshots should be interpreted using the documented fields. Initial printed pin selection is the saved handoff value before switching to I3C1.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    Targets communicate using legacy I2C, not native I3C. No dynamic address assignment, CCC, IBI, hot-join or native-I3C target transfer is tested. The script’s fresh bootstrap is important after any early failure, including a reset timeout.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
