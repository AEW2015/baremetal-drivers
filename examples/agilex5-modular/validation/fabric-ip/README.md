# Fabric IP tutorial validation

The actual C driver was connected to the Verilator model for separate ADD1 and
XOR1 builds. The tests exercise arithmetic, byte enables, W1C, read-only words,
quiesce/reject/resume, missing DONE and reset. Python checks cover deployment
metadata rejection plus the existing runner/QEMU failure regressions.

The fabric AArch64 application builds with the pinned compiler. The optional
LWH2F-enabled ATF hook compiles and packages against the pre-existing baseline
SOF; this checks tooling and code, not a new arithmetic FPGA integration. Known
generated bench images were restored after this local packaging check. No board
was programmed for this tutorial addition.

Component wrapper generation checks use the exact ES device and exported
clock/reset/CSR ports. They do not fit or time a whole-board project.

**Not qualified:** physical arithmetic IP access, HPS bridge operation on a new
image, static PR compilation, persona RBF generation/transport or live PR.
The documentation labels their expected results as future integration checks.
See `manifest.json` and the captured logs for precise checked source hashes.
