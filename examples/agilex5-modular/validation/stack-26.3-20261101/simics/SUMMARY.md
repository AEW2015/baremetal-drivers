# Fresh Simics campaign

**64 of 94 distinct catalog rows exercised:** 49 pass, 7 partial, 8 fail. Remaining: 28 not-run, 0 reference, 2 not-supported, 0 blocked.

The remaining rows have no matching distinct model runner, require unavailable model features, or are references. No historical pass was silently reused as a fresh execution. Build manifests and per-case artifact hashes accompany the raw terminal captures.

## Current upstream DDR console

| Example | Result | Limit |
|---|---|---|
| upstream/bridge | pass |  |
| upstream/ccu | pass | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/clk_mngr | partial | Clock init/getters worked; SOFT_PHY and CS_CLK divisor getters return -EINVAL, no physical frequency claim. |
| upstream/combophy | pass |  |
| upstream/crc | pass |  |
| upstream/ddr | pass | upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification |
| upstream/dma | pass | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/ecc | fail | OCRAM ECC initialization timed out before error injection. |
| upstream/fcs | fail | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
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
| upstream/seu | fail | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/smmu | pass | Current source DDR CLI on native Simics model, isolated instance per command; media/injection writes are virtual only |
| upstream/spi | partial | Internal SPI loopback passed; full command status queries fail after the API auto-closes. |
| upstream/timer | pass | upstream 26.3 OCRAM console on the Agilex 5 virtual platform; no physical-board qualification |

Native PSCI and all eight fabric routes have fresh execution evidence. See results.json and the command ledgers for partial capabilities and model limitations.
