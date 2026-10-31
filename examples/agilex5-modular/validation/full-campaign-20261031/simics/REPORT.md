# Fresh Simics campaign

**63 of 94 distinct catalog rows exercised:** 49 pass, 6 partial, 8 fail. Remaining: 28 not-run, 1 reference, 2 not-supported, 0 blocked.

The remaining rows have no matching distinct model runner, require unavailable model features, or are references. No historical pass was silently reused as a fresh execution. Build manifests and per-case artifact hashes accompany the raw terminal captures.

## Current upstream DDR console

| Example | Result | Limit |
|---|---|---|
| upstream/bridge | pass |  |
| upstream/ccu | pass | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/clk_mngr | partial | Clock init, L4_SP divisor set/rejection and model frequencies passed, but SOFT_PHY and CS_CLK divisor queries returned -EINVAL (-22). No physical clock measurement. |
| upstream/combophy | pass |  |
| upstream/crc | pass |  |
| upstream/ddr | pass | upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification |
| upstream/dma | pass | Driver fell back to polling because GIC IRQ enable returned 1. Sync 256-byte and async 1024-byte readback and callback passed; hardware interrupt delivery is not qualified. |
| upstream/ecc | fail | OCRAM ECC initialization timed out before error injection. |
| upstream/fcs | fail | EL2/BL31 accepts CHIP_ID SiP call but model SDM returns error 0x3; console re-enters OCRAM bootstrap before any FCS identity/session/RNG completion. A returned prompt is not command success. |
| upstream/gic | pass | upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification |
| upstream/gpio | partial | Source never opens the GPIO handle; printed value cannot prove a GPIO operation |
| upstream/hello | pass | upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification |
| upstream/i2c | partial | Seven of nine phases passed; explicit target write/readback and P3T sensor phases skipped (no matching target supplied/found). |
| upstream/i3c | fail | Native model critical access to held-reset I3C0; enum names incorrectly tested with #ifdef in API reset selection. |
| upstream/iossm | partial | Model ECC counter register is unmapped; memory readback passes, injection command failure remains unqualified |
| upstream/mailbox | partial | Model rejects GET_IDCODE; NOOP and CONFIG_STATUS passed through BL31 |
| upstream/mmu | pass | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/noc | pass |  |
| upstream/perf | pass |  |
| upstream/reboot_mngr | pass |  |
| upstream/reset_mngr | pass |  |
| upstream/sdmmc | fail | SDMMC command/transfer timeout during initialization; no successful media transfer. |
| upstream/seu | fail | EL2/BL31 service entry works, but model SDM rejects every sector-stat query with error 0x3; no valid sector and no injection test. |
| upstream/smmu | pass | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/spi | partial | Controller version and 32-byte internal loopback passed. The subsequent status phase runs after the helper closes the API and reports not open; the unconditional 3/3 summary does not qualify full SPI selftest completion. |
| upstream/timer | pass | upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification |

## Native PSCI

Resident BL31 entered the unchanged helper at NS EL2. CPU_ON returned0; A55.1 published the exact context, MIDR/MPIDR, EL2, executable entry and private stack; CPU_OFF did not return and AFFINITY_INFO confirmed OFF. The original assessment rejected uppercase hex output; the corrected oracle accepts both cases with unchanged numeric checks and re-evaluates the same captured execution. Raw logs and initial assessment are retained.

## Remaining execution failures

* Legacy timer, XGMAC and HPS mailbox reproduce their recorded failures.
* Current ECC: OCRAM ECC initialization timeout before injection.
* Current I3C: native model critical access while the device is held in reset; source API enum/preprocessor bug documented in hardware-eligibility.md.
* Current SDMMC: command/transfer timeout during init; no successful virtual media write/read.
* Current SEU: resident BL31 accepts service entry, model SDM rejects every sector-stat command with error 0x3. No injection completed.
* Current FCS: model SDM CHIP_ID error 0x3, then unexpected OCRAM console re-entry; no complete FCS result.

The working additional native DDR examples are CCU (ID/error/L3 flush), DMA (polling fallback with full readback/callback), MMU status, SMMU status and the narrower SPI internal loopback. Clock manager, GPIO, I2C and the full SPI command are partial; SPI controller identification and its 32-byte internal loopback passed, but the status phase reported that the API was already closed.

See [hardware eligibility](hardware-eligibility.md), [all 94 row results](results.json), [exact command ledger](campaign-results.json), [native fabric retry ledger](fabric-retry-results.json) and [current DDR source/artifact identities](current-ddr-build.json).
