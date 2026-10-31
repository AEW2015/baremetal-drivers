# Physical reference eligibility review

Source/evidence audit for candidate physical runs; not a request to operate the
bench. The physical target is the Agilex 5 Modular ES (A5ED065 ES R0) with its
matched HPS/DDR handoff. Preserve the shared board lock and restoration flow.
QEMU and Simics evidence cannot qualify physical execution or reproduce board
fixtures.

## Candidates and prerequisites

| Catalog item | Current physical evidence / eligibility | Missing dependencies or limit |
|---|---|---|
| `reference/semihost` | **Passed on physical OCRAM** in `runs/reference-hardware-20261031T183919.447168Z/results.json`: verified payload readback, semihost output and completion PC; DDR Hello restoration passed. The semihost payload executes from OCRAM. | This is a narrow OCRAM/semihost check, not full HPS boot or DDR qualification. Requires the matching HPS DDR bootstrap/debug path, JTAG DAP and licensed OpenOCD; keep its exact payload and restoration evidence with the catalog update. |
| `reference/psci` | **Passed with the new resident-BL31 adapter.** Actual CPU_ON, secondary context/identity records and CPU_OFF/AFFINITY_INFO were verified; see `hardware/psci/results.json`. | Needs resident matching BL31/PSCI firmware, an EL1/EL2 nonsecure caller, and the corresponding boot/entry contract. The standalone EL3 demo is not a PSCI implementation. Existing direct reset/power release and multicore identity tests do not substitute for PSCI. |
| `reference/pr` | **Reference workflow only; no physical PR result.** | Needs the exact board/project PR-capable static image, defined PR partition, generated and fitted base/persona revisions, matching partial-reconfiguration bitstreams, compatible clocks/resets/interfaces, and a safe recovery image/sequence. A DSU cache partition experiment is unrelated to FPGA partial reconfiguration. |
| `legacy/*` (16) | **Not eligible unchanged.** Existing 25.1 Simics results are model-specific, not physical evidence. | Replace modeled startup, addresses and peripheral targets with reviewed Modular ES adapters. Additional hazards: legacy SPI may write EEPROM; SDMMC writes blocks; I2C/I3C assume modeled targets/addresses; XGMAC needs actual EMAC2/PHY setup; timer/watchdog require matching interrupt/timeout setup; HPS mailbox uses modeled offsets. Do not run media or SOM-bus writers unchanged. See `simics/hardware-eligibility.md`. |
| Additional board vendor adapters (4): `vendor-timer`, `vendor-watchdog`, `vendor-spi`, `vendor-hps_mailbox` | **`vendor-timer` now passed via the optional board adapter.** The other three remain compile-only. | Need source review and per-IP physical adaptation: timer/watchdog clock, reset and GIC routing; SPI controller/target and explicitly safe transfer mode; HPS mailbox's real service/IP and address map. Build success and the other five pinned vendor wrappers' register checks are not execution proof for these four. |
| Fabric examples / custom core suite | **All 15 core board-suite entries rebuilt and passed in this campaign.** Fabric candidates require a matched design. | For fabric MMIO/DDR/DMA, require the actual fitted SOF, generated HPS handoff, compatible bridge/reset/clock state, address map, and verification that the selected route reaches the expected DDR/endpoint. Simics native paths, Verilator RTL and synthetic errors are model-only. The current catalog marks physical `fabric/add`, `fabric/xor` not run and full `fabric-ddr` deployment blocked. |
| `custom/fault-probe` | **Read-only exception-register probe passed** in `runs/reference-hardware-20261031T183919.447168Z/results.json`; it reports ESR/ELR/FAR/SCTLR/CPTR and restores DDR Hello. | It does not inject a fault, test handler entry, or recover from an abort. A fault-injection qualification needs an explicitly reserved safe address/region, a bounded handler/recovery path, debug/UART capture and proof that guard data plus board state are restored. Do not infer fault-injection coverage from the probe or Simics injected-error tests. |

## Final campaign status

The final catalog and `COVERAGE.md` supersede the provisional review notes.
Physical DSU coherency and partition-control/readback tests passed, including
restoration; DDR calibrated-path and negative-control checks passed. PSCI passed
with resident BL31, while OCRAM semihost and the read-only fault probe passed
through the matching board bootstrap. The optional vendor timer passed.

The current-upstream candidate adapter completed nine original C commands;
strict reviewed evidence qualifies six as pass and three as partial (CCU,
clock and SPI coverage limitations). FCS completed safely after the response
lifetime fix, but session opening was denied: partial, not full crypto coverage.
USB controller readiness still failed. See the campaign report and individual
results for exact scope, original failed attempts and restoration evidence.

The three remaining vendor adapters and FPGA PR remain unexecuted. Fabric
transfers still require matching fitted images; native Verilator passes are not
physical coverage. The detailed source audit is in `simics/hardware-eligibility.md`.
