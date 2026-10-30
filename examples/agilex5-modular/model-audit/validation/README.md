# Native Simics PIO execution

Both pio and mask-negative passed on 2026-10-30 using the current checkout's
built OCRAM bootstrap and the installed Agilex 5 universal platform. Canonical
results.json records build/source/binary/runner/bootstrap identities and case
status. Each case retains actual UART, full terminal output and generated script.

PIO coverage is model-only: stable bit-0 button/switch inputs, a stable sysid
window read, two 32-bit LED-data write/readback patterns and restoration of the
saved LED value. The bad-mask case proves a wrong expected mask is rejected
against a known-good modeled value. No external input transitions, physical
board LEDs, interrupts or real FPGA RTL are qualified by this test.

The installed model register metadata was inspected before selecting write
masks and is retained in ../model-register-info.txt. See docs/model-audit.md and
../README.md for commands. No proprietary model sources or executables are
redistributed. The source runner uses the shared bounded Simics process helper
with owned process-group cleanup and records new evidence under ignored runs/.
