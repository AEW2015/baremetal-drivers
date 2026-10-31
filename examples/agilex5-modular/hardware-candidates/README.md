# Current-upstream physical-board candidates

These isolated adapters compile the current 26.3 example command sources with
board startup instead of the upstream FSBL/main entry. They preserve the
bootstrapped clock tree, pinmux and UART divisor. Build success is not a hardware
pass. Exact runtime results and these scopes must be retained together.

| Candidate | Behavior and eligibility |
|---|---|
| hello | Unchanged hello command; fresh marker and exact greeting required. |
| ccu-readonly | Current CCU ID/error APIs, compared with raw MMIO. The original selftest prints unconditional PASS and flushes every enabled DMI; its flush is excluded. This is a subset, not a full upstream CCU selftest. |
| clkmgr-readonly | Current getter APIs for eight clock paths with nonzero rates, and unchanged NOCDIV snapshot. The original command calls platform clock init and changes L4_SP; those operations are excluded. Derived register rates do not physically measure frequency. |
| dma | Unchanged 256-byte synchronous and 1024-byte asynchronous demo, requiring full readback and callback text; additional current API 4096-byte copy verifies every byte and channel idle. The driver can invoke the callback through polling fallback, so this does not prove hardware DMA interrupt delivery. The SDK `dma_get_error()` stub is not accepted as error proof. |
| gic | Masked/enabled Group0 SGI test, actual callback IRQ1 and nonzero count. Startup supplies IRQ/FIQ vector dispatch and demonstrated GIC-600 redistributor power/wake preflight. A wrapper around SDK initialization disables both Group1 CPU-interface enables in `ICC_IGRPEN1_EL3` and checks readback before the command unmasks DAIF, matching the EL3 Group0 acknowledger. Requires exclusive GIC ownership. |
| mmu | Unchanged EL3 status command, cross-checked with API and entry SCTLR. No mapping exercise. |
| smmu | Unchanged enable-status command, cross-checked with raw CR0. No DMA translation exercise. |
| spi | Unchanged 32-byte internal-loopback command plus a 256-byte current API loopback with full API comparison. External SPI media and pin connectivity are not tested. |
| timer | Unchanged polling command; oracle checks actual changing values, all five samples and 2/2 completion. No period/frequency calibration. |

The current GPIO command uses an unopened NULL handle and attempts output
writes; it is excluded. I2C, I3C, SD/MMC, ECC injection, FCS and SEU commands
are outside this reviewed set. No storage, EEPROM, clock NVM or fuse writes are
part of these candidates. Timer/SPI/DMA/GIC operations change volatile peripheral
state; the physical runner starts fresh DDR before each ELF and restores DDR
Hello afterward.

From `examples/agilex5-modular` in the configured firmware container:

```sh
./hardware-candidates/build.sh
```

The build consumes read-only current DDR SDK libraries, verifies their complete
source hash manifest against this checkout, and records compiler, adapter and
ELF/bin identities in `build/hardware-candidates/build.json`. Only the SMMU API
file is additionally compiled unchanged with section garbage collection to
avoid linking unused multi-megabyte translation tables into a status-only ELF.

The host operator uses the existing locked runner:

```sh
python3 upstream-lab/hardware.py --suite candidates \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --artifacts build/hardware-candidates \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py \
  --only hello,ccu-readonly,clkmgr-readonly,dma,gic,mmu,smmu,spi,timer
```

This runner checks Agilex-target metadata, all artifact hashes and ELF segments
before hardware access, validates byte readback, captures UART, evaluates
`oracle.py`, and restores the established DDR image. A printed upstream summary
or a successful restoration alone does not qualify a test. CCU and clock
read-only results must stay labeled as subsets of the original examples.

## Physical capture review

The first nine-image physical campaign reached `CANDIDATE_COMPLETE status=0`
for every guest and restored DDR Hello. Five original host assessments rejected
valid output formatting: an unfinished DDR Hello prefix, uppercase hex, known
SDK logger prefixes without newlines, or timer clock-debug lines between a
sample label and its value. A parser-only review retains the original results
and captures in full and records the corrected assessment separately in
`validation/reviewed-results.json` with old/new statuses and hashes. Compiled
C/ASM and ELF hashes are unchanged; no hardware rerun is implied.

The reviewed declared scopes are eight PASS and SPI PARTIAL. Actual SPI32-byte
and256-byte internal loopbacks passed, but the original command's third status
phase says the API is not open despite its unconditional PASS summary. CCU and
clock getter subsets also remain partial when mapped to their full original
upstream examples. DMA completion used the SDK's explicit polling fallback;
its callback does not prove hardware DMA interrupt delivery.

`validation/oracle-fixtures.json` freezes the exact nine UART captures for
regression tests. Those tests reject truncated/duplicate captures, failed
debuggers, removed callbacks, corrupted copy readback, enabled Group1 control,
missing SGI delivery, stale/missing timer samples and missing SPI loopbacks.
