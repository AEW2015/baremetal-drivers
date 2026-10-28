# Upstream 26.3 drivers and examples

This fork merges Altera's **26.3 Release Update**, commit
[`66bdcc347564c5698a8997169bce83a31647d618`](https://github.com/altera-fpga/baremetal-drivers/commit/66bdcc347564c5698a8997169bce83a31647d618).
It is a substantial API/build rewrite, not a version change to the older tests.
`UPSTREAM-REVISION.json` records the merged release and the compatibility pin.

## Source layout and API changes

| Current directory | Role |
|---|---|
| `api/` | Public peripheral APIs and module guides; check these contracts first |
| `drivers/` | Low-level register access and peripheral implementation |
| `middleware/` | Shared control and coordination layers |
| `platform/agilex5`, `platform/agilex3` | Platform definitions, clocks and console setup |
| `src/` and `lib/` | Startup, vectors, C runtime, formatter and command console |
| `examples/<module>/` | Registered console commands and self-tests |
| `cmake/` and root `Makefile` | Current OCRAM/DDR build and artifact generation |
| `examples/agilex5-modular/` | This fork's independent QEMU, Simics and Modular ES labs |

The old `inc/`, `helpers/`, `target_aarch64.cmake` and `test/simics/` layout was
removed upstream. The old `/dev/...` open/ioctl examples are not source-compatible
with the new typed APIs. For example, the new timer flow is `timer_open(TIMER_SYS0)`
→ `timer_set_period_us()` → `timer_start()` → `timer_get_time_us()` → stop/close.
A NULL handle, errno-style status, module-specific status and a `void` operation
have different meanings. Read the upstream
[return-value contract](https://github.com/AEW2015/baremetal-drivers/blob/main/RETURN_VALUES.md)
and the module guide; do not assume every call returns zero on success.

Useful current guides:
[UART](https://github.com/AEW2015/baremetal-drivers/blob/main/api/uart/README.md),
[timer](https://github.com/AEW2015/baremetal-drivers/blob/main/api/timer/README.md),
[DMA](https://github.com/AEW2015/baremetal-drivers/blob/main/api/dma/README.md),
[GIC](https://github.com/AEW2015/baremetal-drivers/blob/main/api/gic/README.md),
[I2C](https://github.com/AEW2015/baremetal-drivers/blob/main/api/i2c/README.md),
[SPI](https://github.com/AEW2015/baremetal-drivers/blob/main/api/spi/README.md), and
[mailbox](https://github.com/AEW2015/baremetal-drivers/blob/main/api/mailbox/README.md).
The timer guide explicitly identifies an SP1-to-SP0 mapping limitation in this
release; the UART API currently accepts only instance 0. Driver presence is not
a promise that every hardware instance or operating mode is exposed by its API.

## Current command catalog

The application boots to `SoCFPGA Bare-Metal > `. Run `help` to inspect the
commands actually registered in that image. Generic console text such as
`command completed - CHECK DETAILED OUTPUT` is not a self-test PASS verdict.

| Profile / area | Commands registered by the current source |
|---|---|
| OCRAM minimal image | `hello_selftest`, `ddr_selftest`, `gic_selftest`, `timer_selftest` |
| DDR: data movement / memory | `dma_selftest`, `ddr_selftest`, `mmu_selftest`, `smmu_selftest`, `ecc_selftest`, `ecc_bist`, `crc_selftest` |
| DDR: serial / storage / GPIO | `i2c_selftest`, `i3c_selftest`, `spi_selftest`, `sdmmc_selftest`, `gpio_selftest` |
| DDR: platform / control | `clk_mngr_selftest`, `ccu_selftest`, `combophy_selftest`, `iossm_demo`, `noc_selftest`, `mailbox_selftest`, `bridge_selftest` |
| DDR: security / reset | `fcs_selftest`, `seu_selftest`, `reset_mngr_selftest`, `reboot_mngr_selftest` |
| Source present, excluded from default DDR build | `perf_selftest` |

DDR builds also retain the minimal commands. There is no current upstream
XGMAC bandwidth command equivalent to this fork's separate
[Ethernet lab](examples/ethernet.md). SD/MMC self-test writes media blocks;
reset, reboot, SEU and security commands have their own effects. These commands
are listed as source capabilities, not automatically run on the physical kit.

The OCRAM `ddr_selftest` first attempts DDR initialization. On unsupported JTAG
flows it may explicitly skip that stage and validate a 16 KiB OCRAM fallback.
The Simics runner records that distinction. A fallback PASS is not a DDR PASS.
The direct DDR validation window in this release is 16 MiB at `0x83000000`.

## Builds and validation

From `examples/agilex5-modular`, in the configured Linux environment:

```sh
./simics/build.sh OCRAM
./simics/build.sh DDR
```

This helper uses CMake 3.24+ (`--fresh`) and defaults to the installed
`aarch64-linux-gnu-*` tools. Override only this track with
`UPSTREAM_CROSS_COMPILE=aarch64-none-linux-gnu-` if using the vendor-recommended
Arm GNU toolchain. Upstream documents testing with Arm GNU 14.3.Rel1; the local
checks used Ubuntu's Linux-target compiler, recorded in each build manifest.
The existing newlib-based Ethernet/legacy labs continue using Arm GNU 13.2.Rel1.

During integration, the DDR profile failed with the 13.2 newlib headers under
`-ffreestanding`: `PRIu64`/`PRIx64` were not defined for the SD/MMC example.
Selecting the upstream-style Linux cross headers resolved this without changing
the SD/MMC driver. OCRAM and DDR builds are kept in distinct directories.

The fork excludes `examples/agilex5-modular` from the upstream recursive example
glob. Otherwise it would pull unrelated startup code, multiple `main` functions
and downloaded dependencies into the DDR application.

The current OCRAM image passed Simics checks for help, Hello World, timer, GIC
and memory validation. The DDR profile was compiled, not boot-qualified here.
See [Simics commands, captured output and evidence](simics.md). No current 26.3
image was programmed onto the physical Modular ES kit during this source sync.

## Preserve the qualified legacy workflow

The earlier physical-board adapters and native Simics references use the
25.1-era API. `legacy_source.py` fetches the immutable upstream commit
`1419101568f1a9034630b632634fe9fe71773266` into ignored
`examples/agilex5-modular/.deps/baremetal-25.1`. It verifies the commit and rejects
modified tracked files. The legacy library retains its own license.

`configure_vendor.sh`, `build_vendor.sh`, `build_board_vendor.py` and the local
DMA build now use that checkout. QEMU, the custom Ethernet adapter and the local
CPU/GIC/SOM diagnostics retain their own implementations. The recorded hardware
results remain historical evidence for their exact ELFs; merging upstream does
not transfer those results to new binaries or the new API.

The upstream board instructions target Premium/production and Altera A3 kits.
Our Modular ES handoff and the separate Atum board remain distinct. Continue to
use [the Modular hardware profile](hardware.md) and its qualified artifacts.
