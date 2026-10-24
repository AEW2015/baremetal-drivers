# 4. Run on the Agilex 5 Modular kit

The supported bench is the Modular ES kit with FPGA JTAG ID `0x0364f0dd`.
These instructions use volatile programming and scratch RAM. They replace the
running HPS diagnostic application, while leaving flash and SD contents alone.
Use one board owner/debugger at a time.

Before connecting, use the [container recipe and host/container map](container.md)
and [FPGA artifact onboarding](fpga-design.md). The latter identifies the exact
recorded design, its upstream origin, and the current new-kit qualification gap.

## 1. Connect the actual SOM UART and JTAG

Connect carrier JTAG and the separate **J2 HPS_UART on the small SOM**. The
carrier FTDI connection is a different interface. On the tested SOM, FT4232H
channel C was the 115200 8N1 console, with flow control disabled.

On the **Linux host**:

```sh
ls -l /dev/serial/by-path/
docker exec -u dev agilex-xrdp jtagconfig
```

Select the UART's persistent by-path device after identifying the SOM channel.
Do not copy another PC's USB topology or assume `ttyUSB7`. The runner requires
**Modular carrier as cable 1** and checks its name and FPGA ID. The FPGA's device
position changes when the ARM DAP appears; it is derived from the current chain.
The working JTAG speed is 6 MHz. A different board on another cable is unrelated.

## 2. Supply the matching FPGA design and tools

The container needs Quartus Programmer/PFG and the Quartus OpenOCD build with
`aji_client` and ADIv6 support. The tested installation provides OpenOCD under
`/opt/altera/quartus/bin`. A generic distribution OpenOCD is not a substitute
unless its adapter/DAP capabilities have been verified.

In a **container terminal**:

```sh
source /etc/profile.d/baremetal-tools.sh
command -v quartus_pfg
command -v quartus_pgm
openocd --version
```

Supply the HPS-enabled Modular SOF and its matching handoff from your FPGA
project. The tested configuration uses bank 3A, 8 GiB DDR4-1600 and a 150 MHz EMIF
reference. The Premium kit's SOF/pinmux is not interchangeable. The repository
cannot reconstruct your board-specific FPGA design from the C examples alone.

## 3. Build the volatile DDR initializer

In the **container**, from `examples/agilex5-modular`:

```sh
./build_all.sh
export AGILEX_SOF=/absolute/path/to/your/matching-memory_test.sof
./bootstrap/ddr/build_ddr.sh
```

The script pins ATF to commit `2ea5afda7f34774ddcc677fb3a728fa57f780a1e`,
patches a dedicated clone, and runs the included diagnostic hook after DDR
initialization but before storage boot. It creates the HPS RBF and a merged
recovery SOF locally. Neither generated image is committed to GitHub.

## 4. Configure host/container paths

On the **host**, change to the bind-mounted copy of the example directory:

```sh
cd /host/path/to/baremetal-drivers/examples/agilex5-modular
export AGILEX_CONTAINER=agilex-xrdp
export AGILEX_CONTAINER_USER=dev
export AGILEX_CONTAINER_ROOT=/home/dev/baremetal-drivers/examples/agilex5-modular
export AGILEX_UART=/dev/serial/by-path/YOUR-VERIFIED-SOM-UART
```

`AGILEX_CONTAINER_ROOT` is that same directory's path **inside** the container.
Use the actual clone name; it may differ from this example. The root must have
no whitespace or Tcl metacharacters. The UART path belongs to the **host**;
serial capture stays on the host so USB hotplug does not rely on stale container
serial nodes.

Persist these exports in `~/.config/agilex5/hardware.env` using
`env-hardware.sh.example` as a template. In each new **host** terminal, source
that file and change to the host example directory. Keep the learning environment
inside the compiler/container environment; the hardware environment belongs on
the host.

Before programming, check configuration without changing board state:

```sh
python3 doctor.py --target hardware
# When checking the recorded instructor pair, also supply its HOST paths:
# python3 doctor.py --target hardware --sof /host/path/memory_test.sof \
#   --handoff /host/path/hps_bootloader_handoff.bin
```

Require no FAIL results. A missing DAP warning requires the full-recovery route
below. The doctor verifies the same bind-mounted checkout using a temporary
nonce, compares artifact hashes and queries the selected JTAG chain. It does
not program the board or consume UART bytes.

**Choose the initial state before the first run:** after a power cycle, when
HPS DAP is missing, or when another FPGA design is loaded, use:

```sh
python3 run_suite.py --only core --full-recovery
```

This uses your matching merged image for the first bootstrap and replaces
volatile fabric/HPS state. If the matching design and DAP are already present,
use the normal command below. If you cannot establish the image/handoff
provenance, stop and obtain it from the FPGA project owner.

Close any UART terminal before running the automated capture:

```sh
python3 run_suite.py --only core
```

A successful run shows fresh DDR initialization, four 64 MiB pattern checks,
payload readback, core-example PASS markers and a final DDR Hello restoration.
Evidence goes to `runs/<UTC timestamp>/` with ELF hashes, UART and debug logs.
Bootstrap can take several minutes. Stage messages identify live log paths;
use `tail -f runs/<timestamp>/core-bootstrap.log` in a second host terminal.
Read `results.json`: each requested example and `restoration` must pass. A
restoration error is a STOP condition; follow [troubleshooting](troubleshooting.md)
before starting another debugger.

The DDR test is a scratch-region check, not full-bank qualification; the original
ATF also reports a configured-2-GiB versus detected-8-GiB warning.

If the board has no HPS DAP after a power cycle or holds a different FPGA design,
use the **matching merged image** for the first initialization:

```sh
python3 bootstrap/ddr/run_ddr.py --full-recovery
```

This replaces volatile fabric configuration as well as HPS state. Inspect the
programmer result, new DDR markers and PC proof before proceeding.

## 5. Debug the core example in VS Code

After the automated runner has exited, initialize a fresh DDR session from the
**host** before each new load/debug session:

```sh
python3 bootstrap/ddr/run_ddr.py
```

In the VS Code window attached to the **container**:

1. Open `core/core_examples.c` and set a source breakpoint on the first statement in `example_main` (F9 or click the gutter).
2. Select **Hardware: HPS core (initialize DDR first)** and press F5.
3. The configuration starts OpenOCD, loads the ELF, sets PC to `0x82100000` and continues to your `example_main` source breakpoint.
4. Inspect `pc`, `sp` and `cpsr` with `-exec info registers pc sp cpsr` in Debug Console.
5. Step through the source or instructions, then continue to execute the checks.

To see UART output while manually debugging, use another **host** terminal:

```sh
stty -F "$AGILEX_UART" raw -echo 115200 cs8 -cstopb -parenb -ixon -ixoff -crtscts
cat "$AGILEX_UART"
```

Stop `cat` with Ctrl+C before automated capture. Stop the debugger completely
before running a host runner again: OpenOCD, the standalone DDR bootstrap and `run_suite.py` share the same
example-tree `hardware.lock`. Never delete the lockfile to bypass an active owner. Separate checkouts still need a single human
or automation owner; the file lock does not coordinate arbitrary other tools.

Restore the diagnostic after stopping the debugger and UART reader:

```sh
python3 bootstrap/ddr/run_ddr.py
```

Require fresh pattern checks, Hello output and a PC inside the payload, rather
than assuming the debug adapter's disconnect behavior leaves the application
running in a particular state.

## 6. Run the remaining board examples

From the configured **host** terminal:

```sh
python3 run_suite.py --list
python3 run_suite.py --only dma,gic,mmu,som,som-i2c,som-i3c,interfaces,mailbox,multicore
python3 run_suite.py --only vendor-uart,vendor-ccu,vendor-clkmgr,vendor-smmu,vendor-ecc
```

Each selected ELF gets a fresh DDR bootstrap. Do not substitute a loop over all
original Simics tests: some write modeled EEPROMs/media or assume different
clock/reset behavior. Read [the example catalog](examples.md) before extending
these tests to external devices.

For OCRAM without DDR, use `bootstrap/ocram/build_uart.sh` and the
[OCRAM notes](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/README.md).
That source uses the tested handoff layout and clock-specific UART divisor; the
F5 hardware configuration in this tutorial is specifically for the DDR core ELF.
