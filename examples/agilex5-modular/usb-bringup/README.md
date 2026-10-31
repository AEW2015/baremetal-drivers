# Volatile U-Boot preparation for SOM USB bring-up

This directory prepares an existing reviewed vendor U-Boot payload and an
isolated TF-A monitor for a **bare-metal USB demonstration without booting an
operating system or reconfiguring the FPGA fabric**. Preparation alone does not establish hardware behavior. The source-built image
has reached the board prompt; USB enumeration currently fails as recorded below. The main hardware
runner owns the shared mutex, programming/readback, UART capture and restoration.

## Prepared inputs and addresses

The reviewed input is the 26.1.1 baseline-A55 `u-boot.itb`, SHA-256
`9015fb9f50559364cd0e888e445e10f64b9e38dc7b219efedad033b8bbd0a6ef`.
The existing bench copy is outside this repository:

```text
/home/lada/altera-agilex/home/agilex5-litedram-phylite/
  integration/hps-ethernet-v1/boot-assets/boot-files/u-boot.itb
```

`prepare.py` extracts only the raw U-Boot component and its separate U-Boot DTB,
checks their exact SHA-256 values and FIT CRC fields, and verifies the AArch64
image header and A0 Modular DTB model. It does not execute a FIT configuration,
extract/load its FPGA component, mount media, or write physical devices.

| Item | Address / result |
|---|---|
| Pinned TF-A BL31 monitor | load/enter `0x80000000`, secure EL3 |
| U-Boot proper | load/BL33 entry `0x80200000`, nonsecure EL2 |
| Raw U-Boot payload | 867600 bytes, `_end_ofs=0x000d3d10` |
| Appended patched DTB | `0x802d3d10`, exactly after the raw payload |
| Initial BL31 arguments | `x0=x1=x2=x3=0` |
| Memory used | Existing initialized HPS DDR; no fabric DDR required |

The raw payload contains no embedded DTB magic; its `_TEXT_BASE` and `_end_ofs`
header words confirm the separate-DTB append boundary. The combined output is
`build/usb-bringup/u-boot-usb-volatile.bin`, with extraction/patch identities in
`build/usb-bringup/prepare.json`.

## Offline preparation and monitor build

From the repository root on a host with `dumpimage`, `fdtget` and `fdtput`:

```sh
python3 examples/agilex5-modular/usb-bringup/prepare.py \
  --fit /path/to/reviewed/u-boot.itb
```

In the Quartus development container, from `examples/agilex5-modular`:

```sh
./usb-bringup/build_monitor.sh
```

This requires the existing clean `.deps/runtime-atf-26.1.1` checkout at commit
`2ea5afda7f34774ddcc677fb3a728fa57f780a1e`. It preserves that shared source, creates the separate pinned local checkout
`.deps/usb-atf-source`, applies `patch_monitor.py`, and uses its own
`BUILD_BASE=build/usb-bringup-atf`, with `RESET_TO_BL31=1`,
`PRELOADED_BL33_BASE=0x80200000`, `SPD=none`, debug logs and the established
400 MHz counter definition. The default compiler prefix is
`aarch64-linux-gnu-`; `UPSTREAM_CROSS_COMPILE` can override it.

Monitor outputs:

```text
build/usb-bringup-atf/agilex5/debug/bl31.bin
build/usb-bringup-atf/agilex5/debug/usb-monitor.json
```

The monitor metadata records its exact source pin, binary hash and entry. The
source/build recipe does not modify the shared runtime source or monitor used by
other examples. Only the isolated USB monitor restores the normal vendor USB3
PIPE-power-present initialization described below.

## Autoboot guard and review boundary

The vendor image defaults to `bootdelay=5` and `bootcmd=run distro_bootcmd`.
Running that boot command could scan media and execute a configuration that
loads an FPGA image. The prepared DTB therefore adds:

```text
/config/bootdelay = <0xffffffff>;   /* signed -1 */
```

The vendor U-Boot source's `bootdelay_process()` reads the OF_CONTROL `/config`
value after the environment value. `autoboot_command()` skips `bootcmd` when the
stored delay is `-1`. This override does **not** rewrite the environment: a
later `printenv bootdelay` may still report `5`. Inspect the control DTB rather
than treating that environment value as evidence that the override failed.
The reviewed raw binary has no `preboot` literal; preparation rejects an image
containing it or any different reviewed identity.

These are offline source/header/DTB checks. Hardware execution must capture the
U-Boot prompt before sending commands, with UART attached before resuming the
CPU. Sending spaces during entry provides an additional interrupt guard.
Keep the normal autoboot/FIT command paths unused. Do not call `saveenv`, boot
scripts, `bootm`, `booti`, flash updates, SD writes or USB storage writes.

Reference source:

- [U-Boot autoboot control](https://github.com/altera-fpga/u-boot-socfpga/blob/e09d6fcc95f33b8a60377103f6e37e635660a3ee/common/autoboot.c)
- [AArch64 image header](https://github.com/altera-fpga/u-boot-socfpga/blob/e09d6fcc95f33b8a60377103f6e37e635660a3ee/arch/arm/cpu/armv8/start.S)
- [Separate control DTB handling](https://github.com/altera-fpga/u-boot-socfpga/blob/e09d6fcc95f33b8a60377103f6e37e635660a3ee/lib/fdtdec.c)

The source URLs document the reviewed vendor source flow; they are not a claim
that a binary was rebuilt from that newer branch commit. The extracted vendor
binary is identified by its independent hashes and header checks above.

## HPS entry procedure for the hardware operator

1. Hold the established exclusive hardware mutex and identify the Modular ES
   device through a fresh Programmer MCP JTAG scan.
2. Use the existing matching bootstrap to initialize/validate HPS DDR.
3. Load/read back the combined U-Boot image at `0x80200000` through the existing
   HPS memory debug access.
4. Load/read back BL31 at `0x80000000` using the proven **secure privileged AXI5**
   access: preserve CSW, set bit 28 and clear bit 29 using mask `0x30000000`, then
   restore the prior CSW. The first DDR MiB is protected from nonsecure debug
   writes; do not silently fall back to an unverified load.
5. With UART capture already active, set `x0..x3=0` and enter `0x80000000` on A55
   core 0. BL31 then enters the preloaded U-Boot at nonsecure EL2.
6. Require a fresh prompt, perform only the reviewed command whitelist, and
   restore DDR Hello through the existing bootstrap in a `finally` path.

## Initial USB demonstration scope

Start with `version`, `bdinfo`, `usb start`, `usb tree`, `usb info`, and
`usb storage`. The intended connector is SOM **J5**, not J2 UART. Record the
actual hub ports, USB speeds, VID/PID, interface classes and adapter identity.
Enumeration is separate from successful class traffic.

The existing binary contains DWC3/xHCI host, hub and storage support. It has no
obvious USB-Ethernet class-driver strings; inspect effective behavior before
claiming an adapter is supported. A rebuilt U-Boot may need `USB_HOST_ETHER`
and the driver for the actual adapter VID/PID. Its maintained xHCI driver also
implements interrupt transfers, so the source-built `usb_lab_mouse` command can consume
HID mouse reports without writing a new xHCI stack. Neither that command nor
USB-Ethernet traffic is claimed from offline preparation alone.

## Source-built bare-metal USB host demo

The extracted vendor payload reached its U-Boot banner on this bench, but
`dram_init()` then rejected the missing U-Boot SPL handoff. The existing
bare-metal/TF-A DDR bootstrap initializes DDR; it does not manufacture U-Boot
SPL's bloblist. This failure is distinct from DDR calibration failure.

`build_uboot.sh` builds the maintained vendor U-Boot host stack from pinned commit
`e09d6fcc95f33b8a60377103f6e37e635660a3ee`, targeting
`socfpga_agilex5_a0_modular_defconfig`. The derived lab profile disables
`CONFIG_HANDOFF`, `CONFIG_SPL_HANDOFF` and `CONFIG_BLOBLIST`, selecting the
platform's existing FDT-memory fallback in `dram_init()` and
`dram_init_banksize()`. It does not add a replacement DDR initializer or a fake
SPL handoff.

The derived control DTB describes only the known low **128 MiB** HPS DDR window
`[0x80000000, 0x88000000)`. Other root memory nodes are removed, and the first
MiB is reserved for TF-A. This is a deliberately bounded lab allocation, not a
claim that all 8 GiB is contiguous or qualified. Entry remains `0x80200000`;
the initial stack is `0x80600000`. The original matching FPGA design, HPS handoff
and external-memory calibration remain prerequisites.

Required firmware-build tools include the AArch64 Linux cross compiler,
`make`, host GCC, Bison, Flex, OpenSSL development headers, Python 3 development
headers, `setuptools`, `pyelftools`, SWIG, pkg-config and device-tree tools.
In the configured development container, from `examples/agilex5-modular`:

```sh
./usb-bringup/build_uboot.sh
```

The script fetches the exact source pin into ignored `.deps/usb-uboot-source`,
adds the repository's `usb_lab_mouse.c` command reproducibly, and builds only
U-Boot proper and its DTB. It does not build/program a new FPGA design or boot
an operating system. Outputs and checked configuration are isolated under
`build/usb-uboot-source/`:

```text
u-boot-usb-standalone.bin
usb-uboot-build.json
.config
u-boot
```

The metadata records compiler, source pin, command/config hashes, image hashes,
entry and bounded memory profile. Hardware execution is a separate recorded
step. The same `0x80200000` BL33-entry monitor can enter this image.

The lab build enables hub/storage plus the available ASIX, AX88179,
RTL8152/RTL8153, LAN75xx/LAN78xx, SMSC95xx and MCS7830 USB-Ethernet drivers.
It disables persistent environment backends, preboot, automatic boot commands,
`saveenv` and the FPGA command, and sets both compiled and DTB boot delay to
`-1`. These settings prevent automatic media boot/environment import; the
operator's command whitelist must still exclude media-writing commands such as
`usb write`. Matching an adapter VID/PID and completing checked traffic are
required before claiming its Ethernet path works.

The custom command is an application built into **U-Boot bare-metal firmware**,
using its maintained USB host stack. It is not a new USB API added to the
standalone `baremetal-drivers` SDK. After successful enumeration:

```text
usb_lab_mouse 1
```

Move or click a HID **boot-protocol mouse** as the command begins. It finds an
interrupt-IN endpoint, selects boot protocol, and accepts only successful
transfers with zero USB status and a fresh valid report length. It prints raw
report bytes and decoded buttons/deltas. A final success requires a nonzero
motion/button report; zero reports or only idle reports do not establish mouse
events. Non-boot HID formats are explicitly unsupported.

The optional attempt count is 1–8 (default 4). Start with one attempt: native
xHCI waits and abort cleanup can take several seconds if no report arrives.
The hardware runner's outer deadline provides the final bound and must restore
the established DDR Hello state even after a command failure or timeout.


## Recorded hardware results

### Physical USB and Ethernet topology

The SOM HPS USB Type-C port connects to a USB 3 hub. The hub currently has a
USB Ethernet adapter, a USB 2 mouse and a flash drive attached. The adapter's
Ethernet port connects through a network switch; it is not connected directly
to the PC. The PC is wired at `192.168.50.1`. The intended bare-metal board
address for a future test is `192.168.50.3`, subject to confirming that the
address is free before use. The PC and adapter must be on the same LAN and
VLAN for the direct PC ping and TFTP checks described below.

No USB NIC traffic has been measured. USB host initialization currently fails
at the CNR handshake before device enumeration, so this topology does not
establish that the adapter is detected, linked, or usable. The address plan is
static test configuration; it does not assume the board has DHCP support or
that the Ethernet link is up.

The vendor payload reached its banner but rejected the missing SPL handoff.
The source-built profile fixed that entry requirement and reached a U-Boot
prompt with the bounded 128 MiB DDR window. The first source run was
`runs/usb-uboot-20261030T233940.762675Z/`; USB1 probe returned `-110` and DDR
Hello restoration passed. Firmware entry is established; USB enumeration,
mouse events, flash reads and USB-Ethernet traffic are not established.

`patch_diagnostics.py` adds read-only `USB_LAB` snapshots around resource reset,
clock setup, PHY setup, DWC3 core initialization and xHCI registration.
`USB_LAB_RESET` records halt, host-controller-reset and controller-not-ready
(CNR) handshake results. Snapshots include CAPBASE, GSNPSID, GCTL, USB2PHYCFG,
USB3PIPECTL, USBCMD and USBSTS. The logging itself changes no register writes,
although timing can change. The current build also includes the explicit
DT-gated USB3 no-suspend experiment below; it must not be described as a wholly
read-only driver patch.

The inherited `CONFIG_MISC_INIT_R` A0 SDM/SMMU workaround remains enabled. Its
verbose SMMU-test banner belongs to the vendor A0 workaround and does not prove
USB functionality. The unused USB0 node remains unchanged. A successful
clock-resource API return or readable controller ID does not establish a
physically running PIPE clock.

### Follow-up PHY, clock and reset-pin snapshots (2026-10-31 UTC)

The `usb_lab_phy` diagnostic was compiled and exercised in hardware run
`runs/usb-uboot-20261031T020612.343236Z/`. `GHWPARAMS3=0x1042048a`,
`GUSB2PHYCFG=0x00102410`, and `GDBGLTSSM=0` were captured. Its first ULPI
register-0 read did not complete: the viewport command value was
`0x02800000` after 100 polls, and the run recorded no `PHYID PASS`. Launching
that ULPI read writes the DWC3 `GUSB2PHYACC` MMIO command register; the target
PHY ID register is read-only. This is an MMIO command write, not a ULPI PHY
register write. The timeout is not evidence of a PHY ID or an established
ULPI-clock frequency.

Clock snapshot run `runs/usb-uboot-20261031T020301.134353Z/` logged
`CLKMGR_STAT=0x02030300`, `USB31CTR=0x13`, and `EXTCNTRST=0`. Both PLL lock
indications were set and the counter reset indication was clear. These status
bits do not measure or prove the clock frequency at the USB controller.

The read-only reset-pin snapshot
`runs/usb-reset-20261031T021157.846665Z/` completed with `PIN10SEL=8`,
`GPIO0_DR=0`, `GPIO0_DDR=0`, and `GPIO0_EXT_PORTA=0x008d0f4c`. Selector 8
routes HPS_IOA_11 to GPIO0_IO10; DDR bit 10 is clear, so the pin is configured
as an input, and EXT_PORTA bit 10 reads high. Leave this reset net untouched:
it is shared with the FTDI UART and Ethernet reset paths. To collect the
snapshot again, from the repository root run:

```sh
python3 examples/agilex5-modular/usb-bringup/read_reset_snapshot.py \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py
```

The script performs read-only Memory AP register reads and does not halt or
resume the CPU or access USB PHY registers. Check `PIN10SEL` at `0x10d13028`
(PIN10SEL), not `PIN2SEL` at `0x10d13008`; PIN2SEL selects a different pad.
Earlier U-Boot diagnostic runs restored DDR Hello. The opt-in SPL reset-pulse
variant is an explicit experiment and is not enabled by default. Run
`runs/usb-uboot-20261031T021228.871394Z/` completed with:

```text
INFO:    USB_LAB_MONITOR EXPERIMENT=UBOOT_SPL_RESET_PULSE bit12=1; TF-A reverted for FreeRTOS enumeration
INFO:    USB_LAB_MONITOR USB3_MISC0 before=07c00c11 after=07c05c11 mask=00005000
USB_LAB_RESET stage=cnr-return rc=-110 USBCMD=00000000 USBSTS=00000801
FAIL USB_ULPI_TIMEOUT reg=0 viewport=02800000 polls=100
```

Enabling the override did not change the CNR timeout or the ULPI register-0
timeout; it is not a demonstrated fix. DDR Hello restoration passed for this
run, as recorded in its `results.json`. The archived follow-up evidence is in
[`validation/usb-baremetal/20261031`](../validation/usb-baremetal/20261031/).

The variant reproduces the bit12 setting in the pinned U-Boot SPL's
`sysmgr_config_usb3()`. TF-A deliberately reverted that setting after adverse
FreeRTOS enumeration results in
[commit e655389](https://github.com/ARM-software/arm-trusted-firmware/commit/e655389).
It therefore remains an isolated experiment, rather than the normal monitor:

```sh
# From examples/agilex5-modular in the firmware build container:
USB_SPL_RESET_PULSE=1 ./usb-bringup/build_monitor.sh
```

Its output is `build/usb-bringup-atf-spl-reset/agilex5/debug/bl31.bin`; select
that file explicitly with the hardware runner's `--monitor` option. The normal
build still uses `build/usb-bringup-atf/` and bit14 only. No GPIO reset pulse
was issued during this experiment.

### USB3 no-suspend experiment: no improvement observed

The diagnostic run isolated the timeout to CNR: halt and HCRST completed,
while USBSTS remained `0x00000801`. USB3PIPECTL `0x01029102` had SUSPHY bit 17
set; USB2 SUSPHY was clear. This identifies the failing handshake without
establishing its root cause.

The controlled candidate adds `snps,dis_u3_susphy_quirk` only to the derived
DTB node `/soc/usb31@11000000`. A host-driver hook clears
`DWC3_GUSB3PIPECTL_SUSPHY` when that property is present, matching the maintained
[DWC3 core implementation](https://github.com/altera-fpga/u-boot-socfpga/blob/e09d6fcc95f33b8a60377103f6e37e635660a3ee/drivers/usb/dwc3/core.c#L511).
The original host wrapper handles the analogous USB2 property but omits the
USB3 property. The [Agilex 5 USB controller clock requirements](https://docs.altera.com/r/docs/814346/26.1.1/hard-processor-system-technical-reference-manual-agilex-5-socs/usb-3.1-gen1-controller-clocks?contentId=kVpUO_Esi42~7mcKxp6cNQ)
require a running PIPE clock during internal reset propagation, including when
a USB2 device is attached.

The property cleared the observed SUSPHY bit to `0x01009102`, but CNR still
timed out. All halt/HCRST/CNR checks and finite timeouts remain; this experiment
is not a demonstrated fix.

### Restored vendor USB platform initialization: CNR still times out

The DDR-only bootstrap and `RESET_TO_BL31` entry skip normal vendor
[BL2 USB initialization](https://github.com/altera-fpga/arm-trusted-firmware/blob/2ea5afda7f34774ddcc677fb3a728fa57f780a1e/plat/intel/soc/agilex5/bl2_plat_setup.c#L163).
The isolated USB monitor now restores that exact read-modify-write:

```c
reg = mmio_read_32(SOCFPGA_SYSMGR(USB3_MISC_CTRL_REG0));
reg |= SYSMGR_USB3_MISC0_PORT_OVR_CURR_PIPE_PWR; /* BIT(14) */
mmio_write_32(SOCFPGA_SYSMGR(USB3_MISC_CTRL_REG0), reg);
```

The System Manager offset is `0x1f0`; other bits are preserved. Read-only
PER0MODRST snapshots surround the write. No additional peripheral resets are
released. `combo_phy_init()` elsewhere in skipped BL2 code only selects the
SDMMC/NAND DFI interface; it does not initialize the USB PHY.

The actual combined run is
`runs/usb-uboot-20261030T235620.021010Z/`. Its load/readback checks passed and
U-Boot reached the prompt. Exact terminal excerpts from `boot-uart.txt` and
`03-console.txt` are:

```text
INFO:    USB_LAB_MONITOR PER0MODRST before=00000000
INFO:    USB_LAB_MONITOR USB3_MISC0 before=07c00c11 after=07c04c11 mask=00004000
INFO:    USB_LAB_MONITOR PER0MODRST after=00000000
```

```text
USB_LAB stage=u3-no-suspend-quirk U3PIPE=01009102
USB_LAB_RESET stage=halt-return rc=0 USBCMD=00000000 USBSTS=00000801
USB_LAB_RESET stage=hcrst-return rc=0 USBCMD=00000000 USBSTS=00000801
USB_LAB_RESET stage=cnr-return rc=-110 USBCMD=00000000 USBSTS=00000801
USB_LAB stage=xhci-register-return rc=-110
Bus usb31@11000000: probe failed, error -110
No USB controllers found
       scanning usb for storage devices... 0 Storage Device(s) found
```

Artifacts loaded in that run:

| Artifact | SHA-256 |
|---|---|
| U-Boot, 934273 bytes | `3fe7c44649daf382dfad3f1d9eb750c88fe82cd63f5e2d3b96fddd5311658761` |
| Isolated BL31, 73816 bytes | `4d29a1edc7d3464d1730a558fe9e13d6cdf92a3d485391b197121c6c421cd28f` |

The power-present bit changed as intended and PER0MODRST read zero. Neither
change cleared CNR. The failure remains unresolved; these results do not identify
a defective hub, unsupported USB-Ethernet adapter or missing physical clock.
The run's `results.json` records DDR Hello restoration as `pass`. No USB class
traffic or storage reads were attempted after controller initialization failed.


## Run the guarded physical-board diagnostic

From the repository root on the established host:

```sh
python3 examples/agilex5-modular/usb-bringup/run.py \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py \
  --uboot examples/agilex5-modular/build/usb-uboot-source/u-boot-usb-standalone.bin
```

The host runner holds the shared hardware mutex through fresh board discovery,
DDR bootstrap, JTAG loading and complete binary readback, bounded console
commands, and restoration. It captures a new run under `runs/usb-uboot-*`.
The current controller timeout produces a nonzero process exit even when the
console returns and DDR Hello restoration succeeds. A successful future exit
would establish external enumeration only; class traffic needs its own evidence.
Archived terminal captures and final results for this investigation are under
[`validation/usb-baremetal/20261030`](../validation/usb-baremetal/20261030/).

After enumeration works, the intended demonstrations are:

| Exercise | Required evidence |
|---|---|
| Hub | USB tree, VID/PID, port topology and negotiated speed |
| Boot-protocol mouse | Fresh successful interrupt-IN report with motion/buttons |
| Flash drive | Two read-only 4 KiB reads into separate DDR buffers with equal SHA-256 |
| USB Ethernet | Explicit USB adapter selection, PC ping and generated 1 MiB TFTP download with matching RAM SHA-256 |

`tftp_peer.py` serves only generated data to an explicit board IP for a bounded
session. Its two loopback tests validate the helper, not the physical USB NIC.
Use `setenv autostart no`, `setenv ethrotate no` and the enumerated USB NIC's
`ethact` so a download cannot execute and the HPS Ethernet MAC cannot substitute
for the USB adapter. The runner allowlist limits downloads to `0x82000000`,
flash read buffers to `0x82200000`/`0x82300000`, and blocks media writes.
These exercises remain pending while controller initialization fails.


### Clean-power-cycle retest: failure reproduced

After the user confirmed a full board power cycle with the hub attached, run
`usb-uboot-20261031T132750.283585Z` repeated the normal bit14-only monitor
and source-built U-Boot diagnostics. The initial JTAG scan had no HPS DAP;
the runner selected the existing matching merged recovery SOF. DDR initialized,
all four 64 MiB patterns and payload readback passed, and the CPU PC was
confirmed in DDR. Both firmware images passed full JTAG load/readback checks.

The fresh U-Boot console reproduced:

```text
USB_LAB_RESET stage=halt-return rc=0 USBCMD=00000000 USBSTS=00000801
USB_LAB_RESET stage=hcrst-return rc=0 USBCMD=00000000 USBSTS=00000801
USB_LAB_RESET stage=cnr-return rc=-110 USBCMD=00000000 USBSTS=00000801
No USB controllers found
FAIL USB_ULPI_TIMEOUT reg=0 viewport=02800000 polls=100
```

The USB tree remained empty; no storage or USB NIC enumerated. `net list`
reported only the HPS Ethernet interfaces. This reproduces the failure after
a clean power cycle; it does not identify its root cause or qualify the
external devices. No shared GPIO reset pulse was issued. The runner returned
nonzero for the failed USB checks and successfully restored DDR Hello with a
fresh DDR bootstrap. Raw console, JTAG and bootstrap logs plus artifact hashes
are in [the archived run](../validation/usb-baremetal/20261031/usb-uboot-20261031T132750.283585Z/results.json).


### Flash-drive retry and complete-SPL-path investigation

The flash-drive retry `usb-uboot-20261031T133540.151557Z` reached the guarded
U-Boot prompt, then `usb start` again timed out with `USBSTS=00000801` and
`rc=-110`. `usb tree` was empty and `usb storage` found no devices. No block
reads or media writes were issued; DDR Hello restoration passed.

A separate experiment built the pinned Modular U-Boot SPL so initialization
could be compared with the DDR-initializer/direct-BL31 entry. Both HPS-only and
full matching volatile SOF attempts failed to reach the SPL ready marker.
The full-image diagnostic located the CPU in `hang()` after `spl_early_init()`
failed, before pinmux/clock/DDR/USB initialization. The root cause remains
unknown; neither attempt reached U-Boot proper or tested USB detection.
Both restored DDR Hello. Archived experimental sources and limitations are in
[the SPL investigation](../validation/usb-baremetal/20261031/spl-prototype/README.md).
This is not a completed test of normal SPL-to-U-Boot USB behavior.
