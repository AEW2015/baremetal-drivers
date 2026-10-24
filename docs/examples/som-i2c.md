# GPIO I2C: temperature sensor and EEPROM

`som-i2c` · `build/som_i2c.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_i2c.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/som-i2c-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Use GPIO0 bits 8/9 as open-drain SDA/SCL on the actual SOM management bus. Read TMP464 manufacturer and raw local temperature, then read 16 bytes at EEPROM offset zero.

    1. Save IOA9/10 pinmux/GPIO state, select GPIO function 8 and require an idle released bus.

    2. Read two manufacturer bytes from TMP464 address `0x48`, register `0xfe`; optionally report its raw local temperature register.

    3. Write the two-byte address pointer to EEPROM `0x57`, issue repeated START and read 16 bytes.

    4. Restore saved pinmux/GPIO state.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only som-i2c
    ```

    Uses the onboard SOM TMP464 and EEPROM; no external wiring is needed. The bus is shared with the board management system.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Manufacturer | 0x5449 | Required device-ID read. |
    | Raw temperature | A two-byte raw register value if its optional read succeeds | Recorded 0x1541 is a snapshot, not a required temperature. |
    | EEPROM transfer | 16 bytes received from offset 0 | Contents are not compared to a fixed test pattern. |
    | EEPROM snapshot | 16 bytes of 0xff | Historical observation only; existing user data may differ. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS SOM I2C EXAMPLE BEGIN
    Original SDA/SCL pin selection = 0x0000000400000004
    TMP464 manufacturer = 0x0000000000005449
    PASS SOM_TEMP_ID: TMP464 manufacturer read
    TMP464 local temperature raw = 0x0000000000001541
    PASS SOM_EEPROM_READ: 16 bytes received; no data written
    HPS SOM I2C EXAMPLE COMPLETE
    (Capture also prints all 16 EEPROM bytes; see full UART log.)
    ```

    Temperature and EEPROM contents legitimately vary. Require the manufacturer and EEPROM transfer PASS markers; do not require 0xff contents.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    This qualifies GPIO-generated legacy I2C, not native I2C0/I2C1 controller transfers. EEPROM pointer writes select the read address; no array data is programmed. The raw temperature print is optional and is not a calibrated temperature-accuracy test.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

