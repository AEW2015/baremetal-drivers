# 26.3 validation evidence

Fresh results: QEMU: 16 passes; Simics: 49 passes, 7 partial, 8 failures; hardware: 50 passes, 6 partial.
89/94 distinct rows were exercised on a runtime; two further standalone fabric
rows passed host C/Verilator checks. Partial capabilities retain their raw
nonzero exits and limits.

See [the readable report](../../../../docs/validation-26.3.md), [all 94 rows](COVERAGE.md)
and [structured coverage](coverage.json). Generated binaries and proprietary
tools are not included. Native FPGA compile/compatibility evidence is in
`build/`, fresh-image checks in `container/`, and runtime captures in
`qemu/`, `simics/` and `hardware/`.

The original GPIO EEPROM failure, missing-iproute2 preflight, failed SDC-order
attempts and corrected retries are retained. The 26.3 USB controller and USB3320
PHY now work, while external devices remain unenumerated even after a bounded
USB reset/rescan. Simics PR uses a simulated loader; hardware PR uses two real
partial bitstream loads in one HPS invocation.

`copied-evidence.json` retains original capture hashes and saved-text hashes.
UART text normalizes line endings and renders NUL bytes as visible escapes;
`text-normalization.json` records additional completed-text normalization.
`source-inputs.json` fingerprints the final source tree; individual build/run
records identify the exact artifacts executed, including pre-fix failures.

The final operation restored the matched 26.3 DDR Hello image and verified its
memory patterns, payload, FPGA user mode and CPU PC. The shared hardware mutex
was then confirmed free; see `final-board-state.json`.
