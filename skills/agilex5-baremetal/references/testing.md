# Testing, adaptation, and recovery

## Bootstrap sequence

Use host serial capture before programming the volatile HPS RBF. Preserve the selected Modular FPGA configuration/handoff. `quartus_pfg -c <matching SOF> <output.rbf> -o hps_path=<ihex> -o hps=1` generates an HPS RBF plus other outputs; program the `.hps.rbf` to the verified FPGA position. Don't accidentally load a fabric-only helper that removes the HPS debug TAP.

The local `bootstrap/ddr` initializer uses ATF 26.1.1 commit `2ea5afda7f34774ddcc677fb3a728fa57f780a1e`. Its small diagnostic hook runs immediately after successful DDR initialization and before storage/combo-PHY boot. It tests scratch DDR with MMU/data cache off, copies the UART payload to 0x82000000, checks readback, invalidates instruction cache and branches there. This is an EL3 diagnostic, not a complete resident BL31/PSCI environment. Successful DDR bring-up does not establish SD/USB/other PHY initialization.

The pinned baremetal-drivers tag is `QPDS25.1_REL_GSRD_PR`, commit `1419101568f1a9034630b632634fe9fe71773266`. The guide's 25.1.1 tag was absent for that repository. Keep pinning explicit. Driver sources are under `test/simics/`; the prefix is meaningful.

## Load and verify

`bootstrap/ocram/agilex5.cfg` supports ADIv6 A55/A76 debug with `aji_client`. Default is A55.0. In early standalone boot, override the `halted`/`resumed` watchdog CTI handlers with empty events; they otherwise access peripherals not necessarily ready. Disable unused GDB/TCL/telnet servers for batch operations. For interactive debugging bind locally and avoid occupied ports; `debug-server.sh` and `recipes/debug.gdb` are starting points.

Load the ELF, resume at its actual entry, and collect new UART output. Require a begin marker from that image, test-specific completion/readback, no failure/fault marker, and a successful debugger operation. Old DDR Hello lines during debugger connection are expected and are not evidence of the new image.

Reloading changed code at the same address can execute stale instruction-cache contents. Use the fresh DDR bootstrap before each diagnostic instead of diagnosing corrupted output as a UART problem prematurely. Use the per-program linker/ELF entry rather than assuming all examples run at address zero.

Local programs use 0x82100000 (core), 0x82200000 (DMA), 0x82300000 (GIC), and 0x82400000 (isolated board examples), with stack below 0x84000000. Native vendor examples use text 0x80200000/data 0x80400000 and the board adapter's stack below 0x84000000. Its board entry initializes BSS before installing the separately tested EL3 identity map with normal noncacheable DDR; it leaves data cache off. It does not run the simulation startup hook. Secondary cores park in a stable loop at 0x82010000, outside reloadable example images. Buffers occupy 0x85000000–0x85300080; MMU tables are in the example ELF. Review source for additional scratch ranges. These ranges are not available to a concurrent OS/application.

Keep one live board runner. `run_suite.py` takes the project advisory hardware lock, bounds UART capture, saves timestamped logs plus ELF hashes, and restores DDR Hello in `finally`. Other/manual runners must also respect exclusive board ownership; an advisory lock does not block unrelated tools automatically. On bootstrap/USB disconnect/restore errors, stop board work and diagnose before starting another programming operation. Serial `select()` can be followed by EAGAIN: handle `BlockingIOError` by retrying, EOF by reporting disconnect. Clean up only the processes launched for this test.

## Demonstrated adaptations

- **GIC-600:** clear the redistributor's power-down request through GICR_PWRR and wait for group transition/power acknowledgement before clearing WAKER. The earlier wake-only sequence timed out; adding the power-up step allowed secure Group-0 SGI0 delivery and acknowledgement. This is a polled interrupt acknowledgement test, not an exception-vector delivery test.
- **Vendor startup/UART:** the original ELF startup stopped before `main` in this EL3 diagnostic environment. The board entry adapter enables FP/SIMD access, establishes exception vectors, and uses the reserved local stack. Preserve the bootstrapped UART divisor around vendor `uart_init`, which otherwise installs a simulation-clock divisor. The adapted vendor UART example then completed successfully. Do not hardcode that divisor for a different HPS clock tree.
- **DMA:** use valid linked descriptors, wait for actual completion with `status & DMA_TFR_DONE`, then compare all transferred data. The original sample's `status | DONE` check can falsely pass. Data cache must be off for the current local DMA example; cache-maintenance/coherent DMA is a separate test.
- **MMU:** the local EL3 example verifies AT S1E3R/PAR and a DDR store/read with translation enabled, using normal noncacheable DDR. This is not a cache-coherency test. The native vendor EL3 sample calls `fsbl_configuration`; do not rerun board-incompatible clock/pinmux setup blindly after DDR initialization.
- **Multicore:** the local test directly sets reset vectors and releases secondary cores through the matching ATF power-channel/reset sequence. Each secondary uses no C runtime and publishes MIDR/MPIDR in reserved DDR. It is not PSCI CPU_ON. The separate PSCI wrapper requires resident BL31 and a nonsecure caller, absent in the diagnostic bootstrap.
- **Timer/watchdog:** test peripheral timer expiry through status, not exact instantaneous count zero on a periodic timer. Watchdog1 is tested in interrupt-first mode then held in peripheral reset before its next timeout; no system-reset claim. CNTFRQ_EL0 was zero in this bootstrap; don't derive delays from it without programming/verifying the frequency.
- **Peripheral scope:** SPI internal loopback qualifies the controller path without an EEPROM or pinmux peer. Read-only GPIO snapshots and SMMU/CCU IDs do not establish output connectivity, DMA translation, or multicore cache coherency. ECC default-register tests do not establish injected-error recovery. Preserve those distinctions in results.

## Pinmux recovery

The Quartus `sm_handoff.tcl` has a **per-pin** `pinsel_value_map`, not one global function-number scheme. IOA9/10 use selector 0 for I3C1, 4 for I2C_EMAC1 and 8 for GPIO; selector 9 is HCLK. Do not infer a selector from the order shown in a schematic symbol or GUI dropdown. A trial selecting HCLK on the management-bus pins disrupted the HPS clock/UART and caused HPS-RBF programming errors. This is a demonstrated failure, not a valid I3C configuration.

The original bench's helper `examples/recovery/sysbus.cfg` (not bundled here) examines only the memory AP, avoiding clock-stalled core examination. Only use recovery writes justified by a known previous register value. If the AXI-AP itself cannot examine, do not assume debug writes succeeded. Record the failure and use the validated configuration/power-reset recovery applicable to the current bench.

A raw HPS-enabled SOF without an embedded bootloader is rejected as incomplete (19192). A merged volatile recovery image can be built using `quartus_pfg -c <matching.sof> <ddr_recovery.sof> -o hps_path=<bl2-ddr.hex>`; the host DDR runner supports `--full-recovery`. This replaces volatile fabric as well as HPS state. File generation success does not prove that a clock-stalled board accepted it; check the programmer log and new UART/PC proof.

## Storage and external devices

The vendor I2C example writes modeled target 0x54, and SPI can write an EEPROM. The vendor SD/MMC sample writes media and has simulated timing/init assumptions. Those are not suitable substitutions for SOM-specific read tests. USB/network recipes need the board's U-Boot/Linux environment and external peers; executing them in the host development container tests the wrong machine.

For SOM-first work, read the schematics and target actual SOM devices. Native I3C protocol testing requires an I3C target; reading TMP464/EEPROM via the I3C controller's legacy I2C mode tests that mode only. Reading Ethernet PHY IDs does not prove packet traffic. SD card-detect/controller ID does not prove media read/write. Record unsupported/unconnected cases with the exact dependency rather than classifying them as hardware failures or silently passing them.

If HCLK was mistakenly selected on IOA9/10, the observed failure included garbled UART, configuration error 18950/18948 at location 0x00011880, and memory-AP examination failure. A fabric helper could program, but subsequent merged HPS programming still failed. Stop repeating HPS programming at that point and request a physical kit power cycle; do not report restoration from a successful fabric-only programmer operation. Re-verify a fresh DDR test and PC after the power cycle.

The user power-cycled the kit and merged-SOF programming then succeeded, including all DDR patterns and PC at 0x82000024. Recovery evidence was retained in the original bench project (not bundled here). After a power cycle, verify the fabric/handoff match again; this bench initially returned with no HPS TAP and required the full matching merged SOF, not just an HPS-only update.

The corrected IOA9/10 selector-0 native I3C1 test subsequently passed legacy-I2C TMP464 manufacturer reads (0x5449) and 16-byte EEPROM reads at 0x57. The GPIO selector-8 version also passed both reads after ensuring SDA is released before SCL for a repeated START. Preserve that edge ordering: changing SDA/SCL together produced the earlier EEPROM-read failure. Both tests use pointer writes only, not EEPROM array writes. Native I3C DAA/CCC/IBI behavior remains untested without an I3C target.

## Vendor libc output contract

A stalled CCU adapter halted at `_write` (`mylibc.cpp:159`), not its register accessor. The reference `_write` inserts CR before LF and returns the UART's expanded transmitted count. Newlib expects the input byte count consumed; returning more than `len` breaks subsequent buffered output. The board adapter wraps `_write`, streams CRLF without a variable-length stack buffer, and returns the original `len`. Qualify rebuilt adapters on hardware; this diagnosis alone does not qualify their peripheral tests.

The next captured CCU exception had ESR_EL3 `0x96000021`, ELR in newlib AArch64 `memcpy` (`memcpy.S:117`), and an unaligned normal-memory FAR. The ATF diagnostic had left SCTLR_EL3.A enabled. The vendor adapter clears A and C when enabling its normal-noncacheable identity map, allowing newlib's normal-memory unaligned loads while device MMIO keeps device attributes. Select SP_EL3 before installing the C stack so exceptions have a valid stack; the earlier EL3T startup initialized only SP_EL0, and a fault recursively failed in its handler. The original bench recorded that failure before the corrected adapters.

After the output/alignment/exception-stack fixes, the CCU and clock-manager references completed with their nonfatal ES/default-value warnings, and the ECC register test completed. These are register-access/default checks only. SMMU IIDR on this SOM is `0x4832243b`: product `0x483`, variant 2, revision 2, implementer `0x43b`. The reference expects revision 1 (`0x4832143b`) but only uses bitwise AND, which cannot establish identity. The board wrapper requires the exact SOM value and prints it. Decode fields using the primary [Linux Arm SMMUv3 header](https://github.com/torvalds/linux/blob/master/drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3.h), not a guessed revision mask. Never change an expected ID solely to force PASS; verify which documented fields differ and record the hardware profile.

The original SOM-first campaign accumulated passing evidence for all 15
registered suite entries; this was not one all-green historical run. Consult
`examples/agilex5-modular/VALIDATION.md` in the checkout for the published scope
and provenance. New runs use their own hashes/logs and restoration outcome.

## QEMU diagnostics and teaching failures

A NEON-only corruption previously printed both FAIL NEON and FAIL MEMORY because
the copy diagnostic used accumulated failures. Preserve the current independent
memory check: compare failures before and after checking all 512 words.
`python3 qemu/experiment.py` tests input mismatch, corrected expectation,
vector-result-only corruption, last-copy-word corruption and restored success.
Require independent markers and guest/runner exits 1 for injected faults, 0 for
recovery. The experiment itself exits 0 only when its expectations hold.
Check actual guest stdout lines: the runner's stderr can mention a missing PASS
marker without the guest ever printing that marker.

The compact linker scripts can emit `has a LOAD segment with RWX permissions`
while producing a valid ELF and returning zero. Inspect `readelf -lW`; the hello
ELF has a combined text/data/BSS load segment. Do not suppress all warnings or
mistake successful compilation for runtime validation. Production memory
protection needs reviewed linker permissions and corresponding MMU mappings.

## Desktop debugging and ownership

Use managed VS Code source breakpoints. QEMU initially stops at `_start`;
continue to `main` and `qemu_done`. Hardware's workspace must select ARM64,
set GDB architecture AArch64 and select the ELF before target download. Set a
source breakpoint on the first statement of `example_main`. Let Stop finish
releasing ports and the hardware lock before a new DDR bootstrap; do not bypass
a legitimate busy rejection. See `docs/feedback-followup.md` for the recorded
GUI trials and `validation/student-feedback/` under the example directory for
independent corruption checks. Historical GUI evidence does not qualify native
Windows/macOS or the Dev Containers attach UI.

An early-cancellation race was reproduced with the launcher paused after writing
its PID record but before exec. Setting `AGILEX_RUN_OWNER` inside that Python
process did not make it part of the initial environment exposed by `/proc`.
The launcher now receives the token through `env` before Python starts and
publishes the record. Preserve that order; do not fix the symptom by weakening
the exact PID/token check or deleting unresolved ownership records.
