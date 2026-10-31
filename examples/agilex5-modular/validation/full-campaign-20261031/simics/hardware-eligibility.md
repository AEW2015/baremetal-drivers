# Additional hardware eligibility review

This is a source audit, not hardware execution evidence. The existing Modular
adapter startup is required; the full upstream DDR startup uses its own clocks,
UART, link layout and runtime. Do not load unadapted legacy/DDR ELFs on the bench.
A status query is narrower than a functional transfer test.

| Current upstream example | Hardware route / dependency |
|---|---|
| `mmu` | Straightforward read-only candidate: `mmu_selftest 3` calls `mmu_api_is_enabled(3, ...)`. Only establishes enable state; shared practice MMU already tests translation and permission faults. |
| `smmu` | Straightforward read-only candidate: `smmu_selftest` calls `smmu_api_is_enabled`. Only CR0 enable state, not translated DMA. |
| `spi` | Candidate after standard adapter: current `spi_api_loopback_test` opens the controller, sets internal loopback, transfers pattern and uses `memcmp`, restores loopback and closes. Require exact `SPI0 loopback PASS` and no helper error. Its top-level 3/3 counter is unconditional and insufficient. The loopback helper closes the API before the command status phase, which then reports not open; retain a partial label for the full command while identifying the genuine loopback subset. This differs from the old vendor SPI EEPROM-writing reference. |
| `ccu` | Candidate after standard adapter: ID + error-status reads plus CCU L3 flush with timeout. All three helpers must succeed; outer 3/3 PASS counter increments even after a helper error. Flush is a real state change, requires cache/EL setup and matching base. |
| `clk_mngr` | Changes divisors through `clk_mngr_api_init`, sets L4_SP divisor 4 and checks 99 rejection. Requires UART/clock restoration plan; not a read-only query. Clock values in the model are not physical-frequency measurements. |
| `dma` | RAM-only candidate after controller reset, valid descriptor/cache and IRQ review. Demonstrates 256-byte sync fill/readback plus 1024-byte asynchronous transfer/callback; callback/IRQ completion must be checked. Existing local 4096-byte DMA copy tests a different implementation. |
| `gpio` | Unchanged source never opens a GPIO handle: uses NULL in direction/write/read calls, ignores return codes, prints uninitialized `value`. Needs source repair and a schematic-selected non-reset pad before functional hardware testing. |
| `i2c` | Not safe unchanged for a shared SOM bus: scans broadly, combined pointer reads, write-NACK, target write/readback and auto-detected P3T configuration/threshold writes. Even restoration is not enough to assume EEPROM/sensor writes authorized. Use existing target-specific TMP464/EEPROM read adapters or add explicitly read-only mode. |
| `i3c` | Target dependency: default instance/address differs from SOM management wiring and private transfer assumes an already assigned dynamic address. Outer PASS counter is unconditional despite inner transfer errors. Existing SOM native I3C1 legacy-I2C read test is valid narrower coverage; no I3C target/DAA setup established. |
| `sdmmc` | Destructive unchanged: `TEST_BLOCK_ADDR=0`, count 2, writes 1024 bytes before readback. Never run on user's SD card. Needs read-only mode or explicit disposable media authorization. |
| `ecc` | Default injects OCRAM SBE and DBE. `ecc_selftest status` also calls init, poll and deinit: these write volatile ECC interrupt masks, register/enable GIC handlers, clear pending ECC status and consume/update software counters. It is not read-only. A separate getter-only/raw-register comparison must avoid init/poll/deinit and remain a distinct subset; neither status path qualifies injection/recovery. Need reserved memory, fault handler, cache/ECC granule and recovery before full hardware execution. |
| `seu` | Default injects FPGA CRAM errors and LSM Nios RAM errors. Requires explicit fault-injection scope, compatible FPGA image/sector, licensing and recovery; not routine example-running authorization. No fuse programming is requested or needed. |
| `fcs` | Identity/session/RNG demo, not key/fuse provisioning. Needs resident BL31 at nonsecure EL1/EL2 and SDM service support; an unowned-device denial skips session/RNG. Do not claim full crypto demonstration from expected denial. No owner-key provisioning should be introduced. |
| `bridge` | Requires matching HPS/fabric endpoint, address and bridge state. Simics bridge model loopback is not proof of loaded physical core. Root's existing fabric lab has separate design/profile prerequisites. |
| `reboot_mngr` | Needs nonsecure entry with resident BL31. EL3 diagnostic correctly rejects SMC; do not count as hardware reset proof. Warm-reset test disrupts test state and needs explicit reset/recovery expectations. |

Legacy 25.1 native scripts use modeled startup and several modeled addresses,
peripheral targets and test oracles. Use the existing board wrappers where
available rather than loading legacy ELFs directly. Legacy SPI can issue EEPROM
writes; legacy SDMMC writes modeled media; legacy I2C/I3C assume simulated target
addresses; timer/watchdog may require interrupt-controller and timeout adaptation;
XGMAC needs the actual EMAC2/PHY wiring; HPS mailbox expects simulated offsets.
CCU/clock/ECC legacy wrappers on this bench qualify register/default access only.

Primary source files reviewed are `examples/*/*_selftest.c`,
`api/spi/spi_api.c`, and the pinned legacy checkout at commit
`1419101568f1a9034630b632634fe9fe71773266`.


## Concrete I3C reset defect

At baseline commit `14f7982`, `api/i3c/i3c_api.c:20` and `:23` use
`#ifdef RST_I3C0` / `#ifdef RST_I3C1`. Those identifiers are enum members
(`drivers/reset_mngr/socfpga_rst_mngr.h:74` / `:75`), not preprocessor macros.
Consequently both switch cases compile out and the API selects
`SOCFPGA_I3C_RESET_NONE` for either instance. The native model then rejects
an access to held-reset I3C0. A future fix should use an explicit platform
feature macro or unconditional supported enum cases, then validate the selected
reset ID and actual controller reset release. Shared driver sources were left
unchanged so this campaign's baseline and artifact hashes stay consistent.


## ECC status-command correction

`examples/ecc/ecc_selftest.c:339` (`ecc_demo_status`) initializes the ECC driver,
polls status and deinitializes it. `drivers/ecc/socfpga_ecc.c:524` masks
System Manager ECC interrupts, clears stale SBE/DBE status and wires/enables
GIC handlers; polling consumes/clears pending status through the block handlers,
and deinit masks the System Manager paths again. The original audit incorrectly
called this command read-only; that description is corrected above. A getter-only
adapter is a separate test and must not be reported as full ECC injection or as
execution of the unchanged status command.
