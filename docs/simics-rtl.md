# Run a bare-metal guest against RTL through Simics

This lesson connects a real AArch64 guest running in Simics to a Verilated
register block. A host-side transactor carries MMIO requests between the guest
and RTL using a synchronous stdin/stdout pipe. The guest, transactor, and RTL
have separate roles and build steps; this setup is a software and RTL
co-simulation, not a physical FPGA test.

The existing [fabric IP lesson](fabric-ip.md) explains the ADD/XOR register
block and its standalone Verilator/C-driver test. The [Simics lesson](simics.md)
covers the Agilex 5 virtual platform and its current upstream examples.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](assets/architecture/design.html?example=integration%2Fsimics-rtl-add){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=integration%2Fsimics-rtl-add" data-example-id="integration/simics-rtl-add">integration/simics-rtl-add</a> · <a href="../assets/architecture/design.html?example=integration%2Fsimics-rtl-xor" data-example-id="integration/simics-rtl-xor">integration/simics-rtl-xor</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=integration%2Fsimics-rtl-add" title="HPS and fabric diagram for simics-rtl.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## What runs where

```text
AArch64 guest in Simics
        │ MMIO request / response
        ▼
host transactor over stdin/stdout
        │ clocked register-bus transaction
        ▼
Verilator model of the fabric RTL
```

The AArch64 guest uses the existing fabric application's `lab_driver.c` and
`lab_mmio.c`, cross-compiled with `aarch64-none-elf-gcc` for the modeled target
and linked at `0x82100000`. The host side uses `g++` and Verilator to compile
the fabric RTL (`lab_ip.sv` and `lab_persona.sv`). Keep these compiler contexts
distinct: the Arm compiler builds the guest; the host compiler builds the
transactor and RTL model.

The Simics Python runner overlays a 64-byte I/O-memory region at guest address
`0x20020000`. Its callbacks forward each 32-bit little-endian access
synchronously to a Verilator child process over a bounded pipe. Each modeled
read or write advances the RTL for two clock cycles. No RTL runs in the
background between guest accesses.

## Prerequisites

Use the Linux development container with Verilator, `g++`, Python 3, and the
AArch64 bare-metal toolchain (`aarch64-none-elf-gcc` and `objcopy`). The working
route also needs the installed Altera Simics 26.3 model. Simics is proprietary
and is not included in this repository. Set `SIMICS_FPGA_ROOT` to its `simics`
directory, then deploy the model and build the current upstream OCRAM image as
described in [the Simics lesson](simics.md). This lesson does not require a
board, FPGA programming, JTAG access, or a host network connection.

## Build and run

In the Linux development container, from `examples/agilex5-modular`, prepare
the Simics model and OCRAM bootstrap. Replace the example install path with the
location of your 26.3 Simics installation:

```sh
export SIMICS_FPGA_ROOT=/path/to/intel-fpga-ext_26.3/simics
python3 simics/setup.py
./simics/build.sh OCRAM
```

Then build the Verilator models and both guest images:

```sh
./simics-rtl/build.sh
```

The build creates ADD1 and XOR1 host models and positive and negative AArch64
guest images under ignored `build/simics-rtl/`. `CROSS_COMPILE` can select a
different prefix; its default is `aarch64-none-elf-`. The Simics project
defaults to `build/simics26`; the boot image defaults to
`build/upstream26-ocram/baremetal.bin`. Run the positive ADD and XOR guests and
the negative missing-DONE case:

```sh
python3 simics-rtl/run.py --only add,xor,missing-done
```

To use other build locations, pass `--project PATH` and `--boot PATH`. The
runner starts a fresh Simics process per case, performs the modeled DDR
bootstrap, loads the guest at `0x82100000`, and records terminal, UART,
transaction, and result files in `runs/simics-rtl-<UTC>/`. It checks guest
completion and the transaction count; a Simics process exit code alone does
not make a case pass. The recorded campaign passed all three cases: ADD1,
XOR1, and the injected missing-DONE diagnostic.

The verified ADD run captured this guest UART excerpt:

```text
SIMICS_RTL_BEGIN: Arm guest -> MMIO -> Verilator RTL
PERSONA = 0x0000000041444431
RESULT = 0x000000000000000c
RESULT = 0x0000000000000000
RESULT = 0x00000000ffffffff
RESULT = 0x0000000000000000
PASS RTL_MATH: four vectors and fresh sequence checks
PASS RTL_QUIESCE: blocked start rejected; resumed identity valid
SIMICS_RTL_COMPLETE status=0
```

This guest ran after the Simics OCRAM console's modeled DDR initialization and
16 MiB validation. The complete [ADD UART trace](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/simics-rtl/validation/add/uart.txt), [terminal log](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/simics-rtl/validation/add/terminal.log),
and [MMIO transaction trace](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/simics-rtl/validation/add/transactions.jsonl) are retained with the run. The backend counted
128 RTL clock cycles in response to guest accesses. This is a Simics plus RTL
execution result; it does not validate a physical bridge or the board. The
[XOR UART trace](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/simics-rtl/validation/xor/uart.txt)
reports persona `0x584f5231` and results `2`, `0xfffffffe`, `0xffffffff`, and
`0`. The [negative-case trace](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/simics-rtl/validation/missing-done/uart.txt)
reports `PASS RTL_NEGATIVE: missing DONE rejected with driver rc=-3` and
completes with status 0. The complete campaign record is
[results.json](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/simics-rtl/validation/results.json):
ADD and XOR each made 63 MMIO transactions over 128 RTL cycles; the negative
case made 20 transactions over 42 cycles.

## Request and response protocol

The guest sees the RTL register block at `0x20020000` for `0x40` bytes. The
callback accepts aligned 32-bit accesses and presents them to the same register
ABI described in the [fabric IP lesson](fabric-ip.md#register-abi-10). The
pipe uses one ASCII request/response per line: `R <hex-offset>` reads a word;
`W <hex-offset> <hex-value>` writes one; `OK <hex-result> <hex-cycles>` returns
the result and cumulative RTL cycle count. The backend first prints `READY 1`
and exits on `Q` with `BYE`. Protocol responses use stdout; backend diagnostics
go to the per-case transaction log. Invalid requests, unaligned or unsupported
accesses, and a backend that does not answer within two seconds become errors.

The Simics callback waits for the corresponding pipe response before returning
the MMIO result to the guest. Reset advances two RTL cycles; each read and
write advances two more. This is a synchronous functional model; it does not
model concurrent hardware activity or physical bus latency.

## Time and measurement limits

Simulated execution and the two RTL clock steps per register access do not
establish physical FPGA timing or board-level throughput. The RTL advances
only when the guest accesses the mapped block, so timers or other logic that
depend on continuous fabric clocks are outside this model. Use the recorded
guest output to verify functional transactions; use hardware measurements for
physical timing and bandwidth. No host networking is part of this MMIO route.

## Failure exercises

The `missing-done` case uses the ADD model and the negative guest. Its adapter
fault injection masks the `DONE` bit returned to the guest on status reads;
the Verilated RTL itself still runs normally. The driver's bounded polling
must return `-3`; the guest reports failure if it does not observe the
timeout. The terminal log records the adapter's injection setting, and the
transaction JSON records both RTL and guest-visible read values. Run the
standalone host checks with `python3 simics-rtl/test_protocol.py` and
`python3 simics-rtl/test_transport.py`. The first has 10 protocol and
arithmetic checks across both RTL personas plus malformed requests. The second
has five host-only fault-injection checks for disconnect, timeout, bad
responses, and invalid offsets. These checks do not add Simics guest cases.

The recorded tools were Verilator 5.020, Arm GNU 13.2.1, Simics Base 7.89.0,
and Intel FPGA External 7.1.0 (`intel.fpga:263000013`), as reported by
the installed Simics runtime.

## Optional simulator backend

Questa is a possible future backend, but this lesson does not claim a working
Questa integration. The documented runnable path is the Verilator route.

## Troubleshooting

- **The model project is missing:** deploy it with `python3 simics/setup.py`
  after setting `SIMICS_FPGA_ROOT`.
- **The OCRAM boot image is missing:** build it with `./simics/build.sh OCRAM`
  or pass the actual image with `--boot`.
- **A source or built artifact changed since the Verilator build:** rerun
  `./simics-rtl/build.sh`; the runner checks hashes before simulation.
- **The RTL backend fails to start or stops answering:** inspect that case's
  `terminal.log` and `transactions.jsonl`. The adapter enforces a two-second
  response deadline and surfaces backend and protocol errors in the terminal.
- **A transaction has the wrong size or alignment:** the overlay supports only
  aligned 32-bit accesses in the 64-byte register range; other operations are
  rejected by the adapter.
