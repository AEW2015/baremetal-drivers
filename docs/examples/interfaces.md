# Ethernet PHY, SD and USB identification

`interfaces` · `build/som_interfaces.elf` · recorded entry `0x82400000`

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/som_interfaces.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T231719.793441Z/interfaces-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

=== "What it does"

    Identify three SOM interface paths without media access or traffic: reach the Marvell PHY over EMAC2 MDIO, read the SD controller revision/card state and read the USB1 Synopsys controller ID.

    1. Release the selected volatile peripheral resets and use the handoff’s MDIO2 pins.

    2. Probe PHY addresses 0–3 for the expected Marvell ID fields.

    3. Read SDMMC HRS29 and report card-detect bit 16 independently of the controller-ID result.

    4. Read USB1 GSNPSID and require its DWC_usb31 family field.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    SKIP_VENDOR=1 ./build_board.sh
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only interfaces
    ```

    Uses the SOM’s EMAC2/88E1512, SD socket and USB1 controller. J2 UART is unrelated to USB host enumeration.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Ethernet PHY | ID1 0x0141; ID2 masked with 0xfff0 equals 0x0dd0 | Recorded PHY address 0, ID2 0x0dd1. |
    | SD controller | HRS29 = 0x6061 | Required controller revision/magic. |
    | SD card presence | Informational; either inserted or not inserted is allowed | Recorded present-state 0x01f700f0 reported inserted. |
    | USB controller | GSNPSID upper 16 bits = 0x3331 | Recorded full value 0x33313130. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS SOM INTERFACES BEGIN
    EMAC2 MDIO pin selection = 0x0000000600000006
    PHY address = 0x0000000000000000
    PHY ID1 = 0x0000000000000141
    PHY ID2 = 0x0000000000000dd1
    PASS SOM_PHY_ID: EMAC2 MDIO reached Marvell 88E1512
    SDMMC HRS29 = 0x0000000000006061
    SD present state = 0x0000000001f700f0
    PASS SDMMC_IDENT: controller revision matches
    INFO SD_CARD: card-detect reports inserted; media not read
    USB1 GSNPSID = 0x0000000033313130
    PASS USB_IDENT: DWC_usb31 controller ID; enumeration not tested
    HPS SOM INTERFACES COMPLETE
    ```

    PHY revision nibble and SD presence depend on the board/media. An absent card is an INFO result, not a test failure.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    No Ethernet cable/peer is needed for PHY ID reads; packet traffic is not tested. SD card presence is not required to pass the controller check, and no media blocks are read or written. USB IDs do not test the PHY, connector power or device enumeration.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.

