# Upstream 26.3 example campaign

Sources: upstream 66bdcc347564c5698a8997169bce83a31647d618 on fork base
73c996bdeff901b523efd9249c39f65fc51d4187, plus the separately hashed
upstream-lab adapter. The upstream example sources were not modified.

- QEMU: CRC and memory-performance/readback passed; no Agilex peripheral models.
- Simics: CRC, performance/readback, Combo PHY identification, NoC and reset passed.
  IOSSM partial: image readback matched, injection event counts stayed zero.
  Bridge and reboot failed at smc_call in this standalone EL3 boot environment.
- Physical Modular ES: CRC, memory correctness, Combo PHY identification, six NoC
  checks and SD/MMC reset/status passed. CNTFRQ_EL0 was zero, so performance
  timing remains unavailable. No physical ECC injection or system reboot.
- Final DDR Hello restoration passed. Fresh bootstrap per payload. Each loaded
  payload was dumped through the memory AP and compared byte-for-byte.
- Baseline QEMU labs: six positive cases, six negative controls and two GDB
  walkthroughs passed. All 45 regression checks passed, including real QEMU.

results.json files retain source/artifact hashes; hardware/*-readback.json
records payload verification. Raw UART/model/debugger logs are unchanged.
failed-checksum-attempt and failed-tcl-attempt preserve unsuccessful loader
attempts, including successful DDR restoration. These did not execute payloads.
Simics setup metadata identifies the separately installed model; no proprietary
model files, simulator installers or executable binaries are included here.

See docs/upstream-examples-validation.md for the table, command reproduction,
captured output, test scope and troubleshooting. Manifest hashes cover every
file in this folder except manifest.json itself.
