# Simics 26.3 and upstream sync validation

The root now merges Altera's 26.3 release commit
`66bdcc347564c5698a8997169bce83a31647d618`. The checked source is merge commit
`cd74c90`, with both upstream and the existing fork as parents.

## Current 26.3 API and console

A clean local Git clone of that committed source compiled the OCRAM and DDR
profiles and executed all five selected OCRAM console checks on the Agilex 5
universal Simics model: Hello, help, timer, GIC and memory validation. Each case
started a fresh model, returned to its console prompt and matched the detailed
expected result. The DDR-init stage was not skipped in this recorded model run.
The compiled DDR profile was not booted as a TF-A/BL33 image.

See `upstream26-clean-checkout/results.json`, per-case `uart.txt`, `terminal.log`
and generated command scripts. Build manifests record compiler, binary/ELF and
source hashes. The raw terminal includes the correct committed-source banner.

## Legacy 25.1 references

The compatibility checkout was fetched and verified at
`1419101568f1a9034630b632634fe9fe71773266`. All selected OCRAM images compiled.
The suite obtained 13 PASS results; timer, XGMAC and mailbox failed. Their logs
and guest return values are preserved under `legacy25-compatibility`.
`LEGACY-LICENSE.txt` retains the original license for the adapted old scripts.

- Timer: model-critical access to a device still in reset, no guest completion;
  Simics exits 0 but the runner correctly rejects it.
- XGMAC: PHY helper rejects PHY ID2; guest returns 1.
- Mailbox: fixed response-buffer offsets disagree in iteration 3; guest returns
  `0xffffffff`, simulator process exits 255.

A new current timer PASS does not change the old timer result. Simics passing
register/default/loopback references does not qualify physical SOM I/O or the
new API on silicon. No hardware was programmed or inspected during this sync.

## Other checks

The complete existing example pack compiled through the new pinned compatibility
route, including local DMA and the physical-board wrappers. QEMU normal,
negative and recovery checks, all six practice labs and GDB exercises passed.
All 39 regression tests passed, as did both fabric RTL/driver personas. Public
CI now also compiles both new upstream profiles; it does not ship or run the
proprietary Simics model. The model installation was 26.3.0.14, Simics Base
7.89.0, in the Quartus 26.3 container. See `simics-packages.json`.

The first current DDR build using Arm GNU 13.2/newlib failed on missing PRIu64
macros under freestanding compilation. `newlib-ddr-build-failure.log` preserves
that failure. Selecting the upstream-style Linux cross compiler resolved it;
no SD/MMC source assertion or expected value was changed. Simulator deployment
was kept separate from CMake firmware roots, and each run has fresh coverage
output. Installer/model binaries, generated libraries, ELFs and coverage trees
are intentionally absent from this public evidence bundle.

`manifest.json` records SHA-256 and byte size of every evidence file except
itself. The build SHA values identify the exact tested artifacts; a later
rebuild with a different source commit/date stamp can legitimately differ.
