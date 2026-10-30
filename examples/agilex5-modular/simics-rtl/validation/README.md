# Recorded Simics-to-Verilator execution

Executed 2026-10-30 in the existing agilex26-mcp-demos development container.
The actual Arm guest and actual Verilator RTL passed ADD, XOR and the explicit
missing-DONE adapter fault-injection test. Positive cases each performed 63
Arm-core-0 MMIO transactions / 128 RTL cycles; the negative control performed
20 transactions / 42 RTL cycles and required the guest driver to return -3.
Every recorded transaction identifies the simulated Arm core as its initiator.

results.json records source/ELF/backend/bootstrap hashes, Simics version,
process results and exact adapter/transport/runner identities. Complete terminal,
UART, generated scripts and per-transaction traces are retained for every case.
The raw terminal output includes the model's standard no-SD warning, object tree
and configured-2-GiB/detected-8-GiB warning; these are not removed from evidence.
The runner requires successful modeled DDR bootstrap and rejects OCRAM fallback.

simics-rtl-protocol.json records 10 host-only protocol/arithmetic checks against
actual Verilator RTL. simics-rtl-transport.json records five separate host-only
failure-injection checks: child disconnect, response timeout, malformed response,
and invalid offsets, including bounded failure and child reaping. They do not
claim additional Simics guest coverage.

The Linux cross-compiler was separately compile-checked with static non-PIE
flags. linux-compile-only-readelf.txt confirms ET_EXEC and no INTERP segment;
that compiler variant is not claimed to have executed in this capture. The
actual Simics campaign used the Arm GNU 13.2.rel1 freestanding compiler.

Reproduce with the commands in ../README.md. Runtime paths in scripts identify
the actual installed/deployed model used for this record; use --project/--boot
for another installation. No proprietary model/runtime sources, FPGA bitstreams,
licenses or generated ELF executables are distributed here.

This direct CPU-address-space attachment does not qualify the physical HPS
bridge, interconnect, FPGA timing, DDR hardware, IRQs, DMA or live PR. No physical
board was accessed. Verilator advances only on MMIO transactions; this is a
functional transaction-stepped demonstration, not cycle-synchronized HPS/FPGA
simulation or bandwidth measurement. Questa/ModelSim is not implemented.

The final three-case campaign was repeated using an OCRAM bootstrap built from
this checkout. Its compiler/source identity and image hash are retained in
bootstrap-build.json; results.json and per-case traces describe that repeat.
