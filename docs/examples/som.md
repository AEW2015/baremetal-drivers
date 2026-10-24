# SOM: timer, watchdog, SPI and GPIO

`som` · `build/som_peripherals.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_peripherals.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T230642.472989Z/som-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Run several on-chip and SOM-connected checks in one ELF: periodic timer expiry, watchdog1 interrupt-first expiry, SPIM0 internal loopback, heartbeat LED GPIO pad readback, and I2C/I3C identification snapshots.

    1. Start timer0 with load 100000, wait for expiry, stop it and clear the interrupt status.

    2. Start watchdog1 in interrupt-first mode and hold it in peripheral reset after observing expiry, before a second timeout.

    3. Loop back SPI bytes `a5 5a 12 ed` internally and compare each received byte.

    4. Drive GPIO0 bit 0 high/low three times, verify the pad input each time, then restore saved GPIO/pinmux state.

    5. Read both I2C component IDs plus I3C versions and the existing management-pin selection.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only som
    ```

    No Ethernet/USB peer or external SPI device is needed. This program changes volatile timer, reset and GPIO state.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Timer | Expiry observed and cleared | PASS HPS_TIMER. |
    | Watchdog1 | Expiry status observed, then peripheral reset | PASS WATCHDOG_IRQ; no system reset. |
    | SPI loopback | a5 5a 12 ed returned unchanged | PASS SPI_LOOPBACK. |
    | LED GPIO | Pad follows high and low | PASS GPIO_LED_PAD; not a visual-observer test. |
    | I2C0/I2C1 IDs | Both 0x44570140 | PASS I2C_IDENT. |
    | I3C snapshots | Version 0x3130302a; baseline pin selection 4/4 | Reported observations, not a bus transfer. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS SOM PERIPHERALS BEGIN
    PASS HPS_TIMER: periodic timer expiry and clear
    PASS WATCHDOG_IRQ: watchdog 1 expiry observed, peripheral reset
    SPI version = 0x000000003430302a
    PASS SPI_LOOPBACK: four bytes through internal loopback
    PASS GPIO_LED_PAD: SOM heartbeat output high/low readback
    I2C0 component type = 0x0000000044570140
    I2C1 component type = 0x0000000044570140
    PASS I2C_IDENT: two controller IDs; no bus transfer
    I3C0 version = 0x000000003130302a
    I3C1 version = 0x000000003130302a
    I3C1 pin 8 selection = 0x0000000000000004
    I3C1 pin 9 selection = 0x0000000000000004
    HPS SOM PERIPHERALS COMPLETE
    ```

    LED timing is not calibrated and may be too short to judge by eye. Initial GPIO/pinmux state follows the supplied handoff.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    The watchdog is not allowed to reset the system. SPI is internal loopback, so external pins/peers are not qualified. LED verification is electrical pad readback, not a claim of a visible blink. The controller-ID portion performs no I2C/I3C bus transfer.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

