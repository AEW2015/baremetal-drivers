# Established Modular ES bench

Verified board identity: Agilex_5E MDK Carrier, FPGA JTAG ID `0364F0DD`, ARM DAP `4BA06477`, MAX10 VTAP `020D10DD`. SOM FPGA is ES `A5ED065BB32AE6SR0`. The carrier cable has appeared as `Agilex_5E MDK Carrier [1-4.2.1]`; another cable is Atum A3 Nano. Derive the FPGA position from fresh `jtagconfig`: adding/removing the HPS DAP changes its index.

JTAG works reliably at 6 MHz; 24 MHz gave inconsistent reads. Set `jtagconfig --setparam <verified-carrier-index> JtagClock 6M` inside the container.

J2 HPS_UART is on the small SOM, FT4232H channel C, 115200 8N1 with no flow control. Established host path `/dev/serial/by-path/pci-0000:74:00.0-usb-0:11:1.2-port0` (then ttyUSB7). Carrier FTDI channels are different. Both FTDI devices lack unique serials, so by-id links can collide. Re-discover after moving cables; old container device nodes may not track host hotplug. Capture serial on the host.

## Hardware artifacts

The original bench used the `agilex-xrdp` container with Arm GNU 13.2.Rel1
and Quartus 26.1.1. Configure your own host/container roots using the repository's
environment examples. Source `/etc/profile.d/baremetal-tools.sh` when available;
`gdb-multiarch` was the usable debugger. See `docs/container.md` for a public
container recipe. Historical device paths below identify the bench, not defaults
for a new machine.

HPS-enabled SOF: `agilex5-litedram-phylite/build/dual_ddr1600_hps_lw_r3/memory_test.sof`, matching `hps_bootloader_handoff.bin` in that directory. Reuse these when the requested task is software-only. The stock Premium board image/pinmux is not interchangeable.

HPS DDR is SOM bank 3A: 8 GiB DDR4-1600, 800 MHz CK and 150 MHz reference. Do not confuse bank 2B/3B fabric DDR with HPS DDR. The diagnostic tests 64 MiB; vendor ATF still emits a configured-2-GiB versus detected-8-GiB warning. It is not full-bank qualification. The prior Si5332 inspection was read-only and found enabled outputs 6/7/8 at 150 MHz; no NVM writes.

## Schematics

Official [SOM schematic, 836174](https://docs.altera.com/v/u/docs/836174/agilextm-5-fpga-e-series-065b-modular-fpga-development-kit-board-som-board-schematic) and [carrier schematic, 836175](https://docs.altera.com/v/u/docs/836175/agilextm-5-fpga-e-series-065b-modular-fpga-development-kit-board-carrier-board-schematic). The original bench downloaded v2.1 PDFs/text; those files are not bundled with this skill or repository. Confirm the physical PCB revision for revision-dependent changes; this bench's ES identity alone does not prove that every newer-sheet BOM matches.

Useful SOM sheets (PDF page equals sheet): 7 I2C topology, 12 HPS pin mapping, 31/32 HPS DDR, 35 configuration flash/JTAG, 38/39 Ethernet, 40–42 USB, 43 microSD, 44 FT4232H/UART, 45 TMP464/EEPROM, 46 LED/buttons, 47 bus buffers. Carrier sheet 2 is its index, 29–33 its Ethernet, 55–57 its FTDI/USB hub, 58 its temperature/EEPROM.

SOM management targets: TMP464 `0x48`, 24AA64 EEPROM `0x57`; carrier targets have different addresses (`0x4b`, `0x51`). HPS IOA9/10 (GPIO0 bits 8/9; N135/AK120) connect to the SOM bus through buffers; those pins can select I2C_EMAC1, I3C1, or GPIO. The established handoff selects I2C_EMAC1 (selector 4), not I3C1. GPIO is selector 8; native I3C1 is selector 0 on these two pins. Selector 9 is HCLK and must not be used for this bus. Derive per-pin selectors from `/opt/altera/ip/altera/intel_hps/sm/hps/sm_handoff.tcl`, not the GUI combo-box ordering or a function number on another pin. Conventional I2C0/1 are not this physical wiring. GPIO open-drain I2C is a useful separate board test, but does not qualify native I3C transfers. Buffer OEs and the BMC/shared bus matter. Use known register-pointer reads; don't send arbitrary writes or broad scans to shared clock/power devices.

SOM Ethernet is Marvell 88E1512 on HPS EMAC2, with MDIO/MDC on IOA7/8 (GPIO0 6/7). The carrier has separate Ethernet hardware. SOM microSD is a removable card, not soldered eMMC. No populated parallel NAND was established by these schematics. SOM USB PHY/connector is separate from J2 FTDI UART; enumeration needs an attached USB device and appropriate PHY/power/host configuration.
