# SOM and carrier mapping used for the tests

Sources: Altera [SOM schematic 836174](https://docs.altera.com/v/u/docs/836174/agilextm-5-fpga-e-series-065b-modular-fpga-development-kit-board-som-board-schematic), document 150-0330723-B1 rev 2.1, and [carrier schematic 836175](https://docs.altera.com/v/u/docs/836175/agilextm-5-fpga-e-series-065b-modular-fpga-development-kit-board-carrier-board-schematic), 150-0330724-B1 rev 2.1. The source PDFs remain on the publisher site; they are not redistributed here. The connected FPGA is ES R0; revision-dependent BOM differences remain possible.

| Function | SOM evidence | Carrier distinction |
|---|---|---|
| HPS UART | Sheet 12 IOA3/4, sheet 44 FT4232H, J2 | Carrier FTDI is separate and was not the HPS console. |
| HPS LED | Sheet 12 IOA1 / GPIO0 bit0, DS17 via transistor, active high | Do not substitute carrier status LEDs. |
| HPS button | Sheet 12 IOB5 / GPIO1 bit4, S7, pullup | Requires physical press to validate input transition. |
| Management I2C bus | Sheet 7 topology; IOA9/10 (GPIO0 8/9), buffers on 47 | Bus connects through B2B and is shared with BMC; not all targets on it are SOM devices. |
| Temperature | Sheet 45 TMP464 EU11, address 0x48 | Carrier TMP464 address 0x4b, sheet 58. |
| EEPROM | Sheet 45 U44 24AA64, annotated address 0x57 | Carrier 24AA64 address 0x51. Read-address probing is not proof of a particular EEPROM's identity. |
| Ethernet | Sheets 38/39 88E1512 PHY, HPS EMAC2 RGMII, MDIO2 IOA7/8 | Carrier has two separate 88E2110 PHYs, sheets 29–33. |
| USB | Sheets 40–42 USB3320 USB2 PHY, USB3 path/mux and Type-C connector | Carrier USB hub/JTAG interface is separate. UART J2 is not a USB host test. |
| MicroSD | Sheet 43 removable-card socket, level shifter and power path; HPS IOB1/2/3/6/7/8 | Media insertion/content still needs runtime verification; no soldered eMMC or parallel NAND established on this SOM schematic. |
| DDR | Sheets 31/32 bank 3A attached to HPS | Other SOM DDR banks 2B/3B belong to the FPGA fabric. |

## Pinmux values

The authoritative installed Quartus table is `/opt/altera/ip/altera/intel_hps/sm/hps/sm_handoff.tcl`, `pinsel_value_map`. Values are **per pin**. For IOA9/10: 0 = I3C1, 4 = I2C_EMAC1, 8 = GPIO0, 9 = HCLK. The existing handoff uses 4. For the SOM LED IOA1, GPIO is also 8. Do not use GUI dropdown indices as register values.

A failed experimental selector-9 trial routed a clock input and disrupted the HPS domain. The corrected native I3C source uses 0. The failure is retained in run `20261023T225305.410146Z`; the original bench retained its programming failures and failed restoration. That failed run is not included in this selected passing-evidence export. Memory-AP recovery and a merged SOF could not restore that state; physical power-cycle was requested. See the validation report for subsequent recovery evidence.

GPIO I2C reads identified TMP464 (manufacturer 0x5449). An initial EEPROM read failed before the repeated-START fix described below.

Recovery was subsequently verified after the user power-cycled the kit: the merged matching SOF programmed successfully, DDR tests passed, and CPU PC was confirmed at 0x82000024. See [recovery proof](validation/post-powercycle.txt). Native I3C1 uses selector 0 on IOA9/10; this is distinct from the current handoff's selector-4 I2C_EMAC1.

Both GPIO-I2C and native I3C1 legacy-I2C tests subsequently read the SOM TMP464 manufacturer (0x5449) and 16 bytes from EEPROM 0x57. Correct repeated-START sequencing fixed the GPIO EEPROM read. The current read bytes at offset zero were all 0xff; this is a read observation, not an EEPROM write-test result.
