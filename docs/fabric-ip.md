# 5. Build a fabric IP core and its driver

This lesson adds a small arithmetic IP behind the HPS lightweight FPGA bridge.
You get synthesizable RTL, a Platform Designer component, a documented register
ABI, an AArch64 driver/application, a Verilator test and a guarded deployment
entry point. Two compile-time personas use the same ABI: **ADD1** and **XOR1**.

!!! info "Validation boundary"
    The RTL and actual C driver have passed simulation for both personas, and
    the bare-metal application and optional ATF bridge path have been compiled.
    A new Modular FPGA design containing this IP has **not** been fitted or
    deployed on the board. The deployment steps below are the integration lab;
    they do not inherit the earlier HPS-only hardware PASS results. Live partial
    reconfiguration is a separate [advanced lesson](partial-reconfiguration.md).

[Captured check manifest and logs](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/fabric-ip)
keep these results separate from physical-board validation.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](assets/architecture/design.html?example=fabric%2Fadd){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=fabric%2Fadd" data-example-id="fabric/add">fabric/add</a> · <a href="../assets/architecture/design.html?example=fabric%2Fxor" data-example-id="fabric/xor">fabric/xor</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=fabric%2Fadd" title="HPS and fabric diagram for fabric-ip.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Follow the transaction

```text
A55 bare-metal application
    → lab_driver.c → ordered 32-bit MMIO
    → LWH2F bridge → Platform Designer AXI/Avalon interconnect
    → lab_ip registers → u_persona (ADD1 or XOR1)
```

No external pins, DMA, IRQ or fabric DDR are needed. HPS DDR holds the program;
the fabric core only sees two 32-bit operands. Keeping the first IP small makes
address decoding, byte enables, reset and driver mistakes visible.

[Browse all lesson sources](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/fabric).

## Memory map: distinguish three addresses

| Address | Tutorial value | Where it comes from |
|---|---|---|
| HPS LWH2F aperture base | `0x20000000` | Agilex 5 HPS map |
| IP offset within that bridge | **example** `0x00020000` | Your Platform Designer address assignment |
| CPU-visible IP base | **example** `0x20020000` | Aperture base + assigned IP offset |
| Driver entry in HPS DDR | `0x82100000` | Existing core linker/startup |

The IP offset is a **proposed allocation**, not a claim about the current bench
SOF. Check the master-view address map and every intervening bridge translation;
choose another free 64-byte aligned slot if necessary. Export the actual map
and use its CPU address when building the driver. Altera's
[hardware-to-software tutorial](https://altera-fpga.github.io/rel-26.1/embedded-designs/agilex-5/e-series/premium-065b/hw2sw-flow/ug-hw2sw-flow-agx5e-premium-065b/)
uses the same aperture-plus-offset calculation; its Premium design is a reference
for the method, not the Modular pinout or an image to program here.

### Register ABI 1.0

All registers are little-endian 32-bit words. CPU offsets below are **bytes**;
the RTL's 4-bit Avalon `avs_address` is a **word index**, so offset `0x14`
arrives as address `5`. The component declares `addressUnits WORDS`, a 64-byte
span and fixed one-cycle read latency. Reserved reads return zero.

| Byte offset | Register | Access / reset | Meaning |
|---|---|---|---|
| `0x00` | ID | RO `0x4c414231` | `LAB1` shell signature |
| `0x04` | ABI | RO `0x00010000` | Exact driver ABI version |
| `0x08` | PERSONA | RO | `0x41444431` ADD1 or `0x584f5231` XOR1; zero while quiesced |
| `0x0c` | CONTROL | RW `0` | Bit 0 START strobe (reads zero); bit 1 QUIESCE retained |
| `0x10` | STATUS | mixed `0` | Bit 0 DONE W1C; bit 1 QUIESCED RO; bit 2 REJECTED W1C |
| `0x14` | A | RW `0` | First operand; byte enables honored |
| `0x18` | B | RW `0` | Second operand; byte enables honored |
| `0x1c` | RESULT | RO `0` | Last accepted result |
| `0x20` | SEQUENCE | RO `0` | Incremented modulo 2^32 for each accepted START |
| `0x24–0x3c` | reserved | read zero | Writes ignored |

START captures the combinational arithmetic result at the accepting clock edge
and sets sticky DONE. There is no multi-cycle job or BUSY bit. A START while
quiesced is rejected without changing RESULT/SEQUENCE. Setting QUIESCE and START
together also rejects START. To resume, write CONTROL=0 first, then issue a
separate START. Clearing DONE does not clear RESULT. Only byte lane 0 writes
CONTROL/STATUS bits; writes to read-only registers are ignored.

=== "ADD1"

    Set component `MODE=1`. Addition wraps modulo 2^32.

    | A | B | RESULT |
    |---|---|---|
    | `7` | `5` | `12` (`0x0000000c`) |
    | `0xffffffff` | `1` | `0` |
    | `0xaaaaaaaa` | `0x55555555` | `0xffffffff` |
    | `0` | `0` | `0` |

=== "XOR1"

    Set component `MODE=2`. The interface and driver stay the same.

    | A | B | RESULT |
    |---|---|---|
    | `7` | `5` | `2` (`0x00000002`) |
    | `0xffffffff` | `1` | `0xfffffffe` |
    | `0xaaaaaaaa` | `0x55555555` | `0xffffffff` |
    | `0` | `0` | `0` |

## 1. Test the RTL and C driver before building an FPGA

In the **development container or native Linux compiler environment**, from the
saved example directory:

```sh
source "$HOME/.config/agilex5/learning.env"
cd "$AGILEX_EXAMPLES"
./fabric/test.sh
```

Install `verilator`, `g++` and `make` in that environment if missing. The existing
bench container already provides Verilator. VS Code also has **Test fabric RTL
and driver (no board)** under Run Task.

Expected results:

```text
PASS FABRIC_RTL_DRIVER: persona 41444431, vectors, byte enables, W1C, read-only, quiesce, timeout, reset
PASS FABRIC_RTL_DRIVER: persona 584f5231, vectors, byte enables, W1C, read-only, quiesce, timeout, reset
```

The test connects the actual `lab_driver.c` API to the actual generated RTL
model, exercises both compile-time personas, and uses temporary build directories.
It also injects a missing DONE response to test bounded polling. This is a local
register-bus simulation; it does not model HPS bridge enable, CDC, FPGA timing or
bitstream delivery. Generic QEMU `virt` does not contain this custom IP.

## 2. Integrate the component into your Modular project

Work in an isolated copy/revision of your known matching Modular FPGA project.
Keep its board constraints, HPS configuration, DDR handoff and clock setup.
The bare-metal repository provides the component, not a replacement whole-board
project. Do not edit generated interconnect HDL as your source of truth.

1. Add the absolute `fabric/` directory to the Platform Designer IP search path
   and refresh the IP catalog. Choose **Agilex 5 Lab → Bare-metal lab arithmetic IP**.
2. Add one instance named `lab_0`; set `MODE=1` for the first image.
3. Connect `clock` to the existing LWH2F/interconnect clock domain and `reset`
   to its properly synchronized reset. Preserve the HPS bridge clock/reset
   wiring and configuration reset-release sequencing. If you choose another
   clock, insert a supported clock-crossing bridge; do not wire the bus across
   asynchronous clocks directly.
4. Connect the HPS LWH2F manager path to `lab_0.csr`. Platform Designer supplies
   the AXI-to-Avalon adaptation where required. Assign a free offset, for example
   `0x00020000`, and verify the effective CPU address/span in the master view.
5. Validate and generate the system. Confirm word addressing, 32-bit data,
   four byte enables and one-cycle registered reads. Save the `.qsys`, generated
   address report and constraints with your FPGA project.
6. Compile the full project with Quartus Pro. Require timing closure for the
   bridge/CSR paths and retain the matching SOF/handoff. A component-discovery
   check alone is not a successful whole-design compile.

You can check component discovery and synthesis-wrapper generation in the
Quartus container before editing the full project:

```sh
./fabric/check_component.sh
```

It exports the component clock/reset/CSR ports in a temporary system for the
exact ES part. It does not synthesize, place, route or time the full board.
Both discovery and generation need the custom-IP search path; the script sets
it for both commands.

Build a second full-image revision with `MODE=2`, preserving the same address
and ports. These are two separately compiled implementations. `MODE` is not a
runtime selector and changing it does not itself perform PR.

## 3. Build the AArch64 driver/application

After confirming your assigned address, in the **development environment**:

```sh
LAB_CPU_BASE=0x20020000 ./fabric/build.sh
```

Use your actual address. Output is `build/fabric_example.elf` plus
`build/fabric-build.json` pairing that ELF hash with its CPU base. The image uses
the existing EL3 startup, fault output, stack and linker placement at
`0x82100000`; it is separate from `core_examples.elf`.

The driver checks ID and ABI before use, detects ADD/XOR identity, clears old
sticky status, writes operands, starts, and requires DONE plus a **new sequence
number** before reading RESULT. `lab_mmio.c` uses volatile 32-bit accesses and
AArch64 ordering barriers. This boot environment has MMU/data cache off. If you
later enable an MMU, map the CSR aperture as Device memory and use the appropriate
privilege/security access; `volatile` alone does not establish memory attributes.
The poll bound cannot rescue a CPU bus read that never completes.

## 4. Package the matching full image and enable LWH2F

The existing DDR diagnostic hook branches to Hello **before** ATF's ordinary
bridge-enable path. For this lesson, explicitly enable only LWH2F after the DDR
checks, using the pinned ATF bridge routine and its FPGA-ready check.

First save a copy of your known-good generated DDR images and their build
metadata outside `bootstrap/ddr/`. Then, in the **container**, package the new
full SOF that actually contains `lab_0`:

```sh
export AGILEX_SOF=/absolute/container/path/to/your/lab_add.sof
AGILEX_ENABLE_LWH2F=1 ./bootstrap/ddr/build_ddr.sh
```

This overwrites local `ddr_probe.hps.rbf`, `ddr_recovery.sof` and
`build-manifest.json` as a matched set. It records the source SOF hash, generated
image hashes and bridge policy. The full SOF carries its matching handoff;
retain that handoff and your exported address map with it. `AGILEX_ENABLE_LWH2F`
is a build option, not a runtime bridge command. The default HPS-only build
omits the added bridge step.

Do not pair an older SOF, newly generated HPS RBF and unrelated handoff just
because their filenames match. The included compiler/packaging check used the
existing bench SOF to verify tools and syntax; it did not add the arithmetic IP
to that SOF or establish bridge operation on hardware.

## 5. Deploy and verify the ADD image

On the configured **Linux host**, change to the same mounted example directory,
source your hardware environment and close your debugger/UART terminal:

```sh
source "$HOME/.config/agilex5/hardware.env"
python3 doctor.py --target hardware
python3 fabric/run.py --persona add
python3 fabric/run.py --persona add --run
```

The first fabric command checks metadata without programming. The `--run`
command takes the shared hardware lock, repeats the checks under that lock,
uses the matching **full recovery SOF** for its first bootstrap, requires fresh
fabric application markers and expected persona ID, and restores DDR Hello with
the same packaged initializer. It uses the existing timestamped evidence and
owned-process cleanup. It is intentionally separate from the ordinary 15-entry
suite; adding the tutorial does not make that suite assume this IP exists.

Expected output from the new FPGA design, **not yet observed on the kit**:

```text
LOCAL FABRIC: LWH2F enabled
HPS FABRIC IP BEGIN
PERSONA = 0x0000000041444431
RESULT = 0x000000000000000c
RESULT = 0x0000000000000000
RESULT = 0x00000000ffffffff
RESULT = 0x0000000000000000
PASS FABRIC_MATH: four vectors and fresh sequence checks
PASS FABRIC_QUIESCE: blocked start rejected; resumed identity valid
HPS FABRIC IP COMPLETE
```

The bridge line appears in bootstrap UART evidence; the application lines appear
in the fabric UART log. Require the fabric result **and** `restoration: pass` in
`runs/<timestamp>/results.json`. Restoration leaves DDR Hello running while the
lab fabric image remains configured; it does not reinstall the original fabric.
To return to the original design, restore its saved **complete matched artifact
set** and use the normal full-recovery procedure.

## 6. Swap to XOR with a full image first

Stop the current run. Repackage `lab_xor.sof` with the same explicit bridge
option, then use `python3 fabric/run.py --persona xor` followed by its `--run`
form on the host. Expect persona `0x584f5231`; the first result becomes `2` and
the wraparound test becomes `0xfffffffe`. The driver executable can be reused
when the address and ABI are unchanged.

A successful full-image change proves both cores and the common driver before
PR adds static-region preservation and reconfiguration control. Continue to
[swap personas with partial reconfiguration](partial-reconfiguration.md).

## Troubleshooting checkpoints

| Symptom | Check | Recovery proof |
|---|---|---|
| IP absent from catalog | Search path, `lab_ip_hw.tcl`, Quartus/qsys version | Component appears with MODE 1/2; generation succeeds |
| ID read aborts or CPU stalls | New full image, actual map, LWH2F clock/reset/security, explicit bridge-enabled bootstrap | Fresh LAB1 and ABI read on the new design |
| Correct ID, wrong operation | Printed PERSONA vs chosen SOF and MODE | Expected persona and all four vectors |
| Old DONE causes apparent success | Clear W1C and require sequence delta | Fresh SEQUENCE increments exactly once |
| Metadata/hash rejection | Rebuild ELF or repackage SOF as a complete set | File checks pass; map still independently reviewed |
| Simulation passes, board fails | Bus adaptation, registered read latency, reset and timing reports | New physical run + restore evidence, not simulation alone |

For UART, JTAG ownership and failed restoration, use the
[main troubleshooting guide](troubleshooting.md).
