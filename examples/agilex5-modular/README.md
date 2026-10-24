# Agilex 5 Modular kit HPS examples

SOM-first bare-metal examples for the Agilex 5 E-Series Modular ES kit (FPGA ID
`0x0364f0dd`, A5ED065 ES R0), using the kit's JTAG and J2 HPS UART. These supplement
the repository's Simics reference tests with physical-board startup and checks.
They are independent of the Premium kit pinout.

The original bench campaign passed all 15 suite entries. See
[validation scope and evidence](VALIDATION.md) and [SOM/carrier mapping](HARDWARE.md).
Rebuilt binaries do not inherit those historical results. No FPGA programming
images, schematic PDFs, compiler binaries or proprietary tools are included.

## Examples

| Suite entry | Behavior checked |
|---|---|
| `core` | A55 identification, NEON addition, cache discovery, CPU DDR copy, GPIO snapshot, counter and GIC IDs |
| `dma` | DMAC0 linked-list 4096-byte copy, actual completion and full data readback |
| `gic` | GIC-600 redistributor power-up and secure Group-0 SGI0 polled acknowledgement |
| `mmu` | EL3 identity translation using AT/PAR and a DDR store/read |
| `som` | Peripheral timer expiry, watchdog interrupt-first mode, SPI internal loopback, LED pad toggle/readback, I2C controller IDs |
| `som-i2c` | GPIO open-drain I2C reads of SOM TMP464 manufacturer ID and 16 EEPROM bytes |
| `som-i3c` | Native I3C1 controller in legacy-I2C mode, same SOM sensor and EEPROM reads |
| `interfaces` | EMAC2 MDIO PHY identity, SD controller/card detect, USB1 DWC_usb31 identity |
| `mailbox` | Read-only SDM GET_IDCODE request and matching FPGA ID |
| `multicore` | Release three secondary A55/A76 cores and verify their MIDR/MPIDR records |
| `vendor-uart` | Vendor UART example with physical-kit startup/divisor preservation |
| `vendor-ccu` | Vendor CCU register-access checks; version warnings retained |
| `vendor-clkmgr` | Vendor clock-register reads; initialized/default-value warnings retained |
| `vendor-smmu` | Vendor ID example plus exact revision-2 SOM IIDR check |
| `vendor-ecc` | Vendor ECC register/default checks |

Sources are in [core/](core/). The separate PSCI example is compile-only: this
EL3 bootstrap does not provide resident BL31 for a nonsecure PSCI caller.
OCRAM UART and semihosting sources are in [bootstrap/ocram/](bootstrap/ocram/).

## Build

Use an AArch64 bare-metal GCC toolchain (validated: Arm GNU 13.2.Rel1), CMake,
Ninja, Python 3, make and git. Existing container users can run:

```sh
docker exec -u dev agilex-xrdp bash -lc \
  'cd /home/dev/baremetal-drivers/examples/agilex5-modular && ./build_all.sh'
```

Or run `./build_all.sh` directly in this directory with `aarch64-none-elf-*` on
PATH. If present, `/etc/profile.d/baremetal-tools.sh` supplies the existing bench
tools. `build/` contains local ELFs, while upstream reference ELFs use the
repository's existing `build/aarch64/out/` output convention.

`configure_vendor.sh` configures the repository in `build/vendor/` and accepts
additional CMake arguments. Upstream FetchContent downloads Arm Trusted Firmware
and GoogleTest; to reuse existing sources, pass
`-DFETCHCONTENT_SOURCE_DIR_ATF=/path/to/atf` and
`-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=/path/to/googletest`.
The build compiles 15 upstream reference targets, 11 local DDR programs, the
PSCI object, and 9 board-adapted vendor ELFs. Compilation does not run any tests.

To build only the custom DDR examples:

```sh
./build_core.sh
./build_dma.sh
./build_gic.sh
SKIP_VENDOR=1 ./build_board.sh
```

`bootstrap/ocram/build_uart.sh` separately builds OCRAM UART ELF/bin/hex. If
`AGILEX_SOF` is supplied it also packages a volatile HPS programming image. The
OCRAM code uses this bench's handoff layout and 54 UART divisor; verify the handoff
and input clock on a different design. `hello_semihost.S` is provided as a source
reference; it is not part of the automated DDR suite.

## DDR initialization prerequisite

The examples expect DDR already initialized by a **matching hardware handoff**.
The tested bank is HPS bank 3A, 8 GiB DDR4-1600, 150 MHz EMIF reference. The
original diagnostic reported a configured 2 GiB versus detected 8 GiB warning;
only 64 MiB is tested. Other SOM DDR banks are FPGA fabric interfaces.

Inside the tool container:

```sh
export AGILEX_SOF=/absolute/path/to/matching-hps-enabled-memory_test.sof
./bootstrap/ddr/build_ddr.sh
```

This fetches the pinned ATF commit, applies the included diagnostic hook after DDR
initialization and before storage boot, builds the DDR Hello payload, and uses
Quartus PFG to create `bootstrap/ddr/ddr_probe.hps.rbf` and a merged recovery SOF.
An optional `AGILEX_ATF_DIR` selects a dedicated clone; the build patches that
clone. The expected commit is checked before modifying it. The matching SOF must
be supplied by your FPGA project; generated images are deliberately untracked.

## Run from the Linux host

The source tree must be mounted into the container, with Quartus Programmer,
OpenOCD with `aji_client`/ADIv6 support, and AArch64 binutils available there.
Set the **container path to this example directory**, and the host's actual SOM
J2 UART device:

```sh
export AGILEX_CONTAINER=agilex-xrdp
export AGILEX_CONTAINER_USER=dev
export AGILEX_CONTAINER_ROOT=/home/dev/baremetal-drivers/examples/agilex5-modular
export AGILEX_UART=/dev/serial/by-path/YOUR-SOM-J2-UART-CHANNEL
cd examples/agilex5-modular
python3 run_suite.py --list
python3 run_suite.py --only core,dma,gic,mmu,som,som-i2c,som-i3c,interfaces,mailbox,multicore
# After reviewing the vendor adapters:
python3 run_suite.py --only vendor-uart,vendor-ccu,vendor-clkmgr,vendor-smmu,vendor-ecc
```

The bootstrap requires the verified Modular carrier as cable 1; it checks its name
and FPGA ID before programming and derives the FPGA position from the current
chain. The selected cable's full enumerated name is used; USB topology suffixes
are not hardcoded. Another board on another cable must remain untouched.

Each test freshly initializes DDR to avoid stale I-cache reloads, captures a new
begin marker and required results, records the ELF SHA-256, and restores DDR Hello
in `finally`. `runs/<UTC timestamp>/results.json` and UART/debug/bootstrap logs
are the evidence. A restore PASS is separate from a test PASS. Set `--port` to
override `AGILEX_UART`. Use a persistent USB-by-path device after verifying it;
on the tested SOM, FT4232H channel C was HPS UART, at 115200 8N1.

The runner replaces the current volatile application and uses scratch RAM. It
holds a local advisory `hardware.lock`; every other debugger/runner must also
respect exclusive ownership. No flash/SD/EEPROM-array or clock-NVM writes occur
in these selected board tests. Do not blindly execute every original Simics test:
several model EEPROMs, write media, reset hardware or assume simulation timing.

## Memory and test limits

Local program entry addresses are 0x82100000, 0x82200000, 0x82300000 and
0x82400000; fault probe uses 0x82500000. Stack is below 0x84000000. Vendor board
adapters use text 0x80200000/data 0x80400000. Reserve 0x82000000 for DDR Hello,
0x82010000 for parked secondary cores, 0x84000000–0x87ffffff for bootstrap tests,
and scratch buffers 0x85000000–0x85300080 (reused after the bootstrap test).
These are isolated EL3 diagnostics, with data cache disabled, not concurrent OS
applications. The MMU example and vendor adapters enable translation separately.

Polled SGI acknowledgement does not test exception delivery. Cache discovery,
secondary execution and CCU reads do not establish cache coherency. The SMMU test
checks identity, not DMA translation. ECC register checks do not inject errors.
Watchdog testing stops before a system reset. Counter advancement does not prove
a calibrated frequency (CNTFRQ was zero). I3C legacy-I2C does not establish native
I3C DAA/CCC/IBI behavior. EEPROM reads use address-pointer writes only; no array
write-test is claimed. PHY/controller IDs and SD card detect do not establish
Ethernet traffic, USB enumeration or SD media access.

The U-Boot/Linux commands in [recipes/](recipes/) are for a separately configured
board environment and external peers, not for the host container. They were not
run in this campaign. NAND/eMMC population is not established on this SOM.

For manual debugging, initialize DDR first, then run `debug-server.sh` inside the
container and use [recipes/debug.gdb](recipes/debug.gdb) from this directory with
an AArch64-capable GDB in the same container. It binds local debugger ports only.
The interactive recipe has not been separately hardware-qualified; the batch
OpenOCD ELF load and PC checks have.

See [PORTING.md](PORTING.md) for demonstrated startup, libc and recovery lessons.
