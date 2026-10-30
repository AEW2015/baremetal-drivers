# Arm guest → Simics MMIO → actual Verilator RTL

This is a working transaction-stepped co-simulation example. An **AArch64 guest**
runs the unchanged `fabric/lab_driver.c` and physical-MMIO backend
`fabric/lab_mmio.c` on the Agilex 5 Simics platform. Its register accesses reach
actual `fabric/rtl/lab_ip.sv` / `lab_persona.sv` compiled by Verilator in a child
process. Unlike `fabric/test.sh`, the C driver here executes as Arm instructions
inside Simics, not as host-compiled code.

```text
Arm guest at 0x82100000 in modeled HPS DDR
  → volatile MMIO + AArch64 ordering barriers
  → Simics io_memory callback, 0x20020000..0x2002003f
  → bounded pipe protocol
  → Verilator-generated lab_ip / ADD1 or XOR1 RTL
```

## Prerequisites and commands

Run in the development container or an equivalent environment with the licensed
Agilex 5 Simics installation, Verilator, g++, make, Python 3 and an AArch64
freestanding compiler. The proprietary Simics runtime/model is not bundled.
From `examples/agilex5-modular`:

```sh
# Once, if the existing Simics project / bootstrap has not been built:
export SIMICS_FPGA_ROOT=/home/dev/altera_pro/intel-fpga-ext_26.3/simics
python3 simics/setup.py
./simics/build.sh OCRAM

# Compile native RTL backends and the AArch64 positive/negative guests:
CROSS_COMPILE=aarch64-none-elf- ./simics-rtl/build.sh

# No Simics license needed for these host protocol/error checks:
python3 simics-rtl/test_protocol.py
python3 simics-rtl/test_transport.py

# Actual Simics + Arm guest + Verilator execution, all three cases:
python3 simics-rtl/run.py
```

Select cases with `--only add,xor,missing-done`. Use `--project /path/to/project`
and `--boot /path/to/upstream26-ocram/baremetal.bin` to reuse a deployed model and
matching upstream console bootstrap. `--timeout` bounds each entire simulation
(default 60 seconds, allowed 1–300). Each case uses a fresh Simics process and
fresh Verilator backend. It boots the existing console, requires DDR initialization,
loads the guest at `0x82100000`, and starts core 0 there. OCRAM fallback is rejected.

The checked-in validation used Simics Base 7.89.0 / Intel FPGA External 7.1.0,
Verilator 5.020, and Arm GNU 13.2.rel1 (`aarch64-none-elf-gcc` 13.2.1).

## Actual recorded output

```text
PASS SIMICS_RTL_BUILD: ADD1, XOR1, positive/negative AArch64 guests
PASS SIMICS_RTL_PROTOCOL: 10 checks; actual ADD/XOR RTL and malformed requests
PASS SIMICS_RTL_TRANSPORT: 5 timeout/disconnect/protocol/offset checks; owned children reaped
PASS add
PASS xor
PASS missing-done
```

The ADD guest printed:

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

XOR reported persona `0x584f5231` and results `2`, `0xfffffffe`, `0xffffffff`, `0`.
Each positive case made 63 Arm-core-0 MMIO transactions and advanced 128 RTL
cycles. The missing-DONE exercise made 20 transactions / 42 cycles and printed:

```text
PASS RTL_NEGATIVE: missing DONE rejected with driver rc=-3
SIMICS_RTL_COMPLETE status=0
```

**Missing DONE is an explicit adapter fault injection:** the RTL really runs,
but its DONE bit is masked before delivery to the guest. It checks the real
Arm driver's bounded polling; it is not presented as an RTL defect. Host-only
transport tests separately inject a stalled child, disconnected child, malformed
reply and invalid offsets and verify bounded failure plus child cleanup.

## Adapter contract and limits

- The Simics Python device uses `confclass`, `io_memory.operation` and
  `memory-space.map`, referenced from the installed Simics Model Builder/API
  documentation. The implementation is independent; vendor sample code and
  proprietary model sources are not copied into the repository.
- Only aligned little-endian 32-bit MMIO is supported; invalid size/alignment
  returns an I/O error. Inquiry/debugger reads are rejected without advancing RTL.
- The mapping overlays exactly 64 bytes with priority -100. It intentionally
  attaches the example directly to the simulated CPU address space. This does
  **not** validate LWHPS2FPGA enable, AXI-to-Avalon adaptation or physical bridges.
- The backend resets for two cycles. Each read/write advances two cycles, using
  the RTL's fixed one-cycle registered reads and no-waitrequest interface.
  Between MMIO transactions RTL does not free-run. Simics time is not synchronized
  to FPGA clock timing; this cannot measure physical latency or bandwidth.
- The pipe protocol is ASCII: `READY 1`, then `R <hex-byte-offset>` or
  `W <hex-byte-offset> <hex-value>`; responses are `OK <hex-value> <hex-cycles>`.
  `Q` receives `BYE`. A response is limited to 512 bytes with a two-second deadline.
  The adapter checks cycle progression and closes/reaps its owned child on errors.
- No DMA, interrupt injection, asynchronous clocks, checkpoint/restore, live PR,
  post-fit timing or physical-board integration is implemented here. HPS DDR is
  modeled memory; no separate fabric DDR/EMIF is needed.
- Questa/ModelSim is not an implemented backend. A future DPI/VPI transactor could
  implement the same transaction contract, but that would need independent
  simulator/license, synchronization and execution validation.

## Evidence and troubleshooting

Generated builds are under ignored `build/simics-rtl`; runs are under ignored
`runs/simics-rtl-verilator-<UTC>`. The runner stores ELF/backend/source hashes,
Simics version, script, complete terminal/UART logs and transaction traces.
It requires completion output, checked results, a normal backend shutdown and
transaction initiators matching Arm core 0; process exit zero alone is insufficient.
A checked-in snapshot is under `validation/` in this directory.

- Missing model/bootstrap: run the setup and OCRAM build above or supply the two
  explicit paths. Do not initialize Simics in the C source root.
- Stale source/artifact manifest: rerun `./simics-rtl/build.sh`; changed bytes are
  rejected before simulation. Rebuild with the intended `CROSS_COMPILE` setting.
- `SIMICS_RTL_ADAPTER_ERROR`: inspect `transactions.jsonl` and `terminal.log`;
  errors are failures, even if the simulator itself exits zero.
- Response timeout/disconnection: the adapter terminates/reaps the backend.
  The outer runner also bounds simulation time and kills its owned process group.
- Expected negative control: `missing-done` passes only when the driver returns
  `-3`; an unexpected result or guest hang fails.
