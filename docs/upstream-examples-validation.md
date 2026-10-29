# New upstream examples: QEMU, Simics and hardware

This campaign tests the 26.3 sources merged from upstream `66bdcc3`, on fork
base `73c996b` with the separately hashed adapter added here. The adapter invokes
unchanged upstream example handlers, uses a reserved memory window and preserves
the Modular ES board's bootstrapped clocks/UART. It does **not** qualify the stock
DDR console, a complete BL33 boot, or resident BL31 services.

| Example | QEMU virt | Simics 26.3 | Modular ES hardware |
|---|---|---|---|
| CRC image validation | PASS | PASS | PASS |
| Memory performance | PASS | PASS | PASS memory; timing unavailable |
| Combo PHY identification | Not modeled | PASS | PASS |
| NoC / firewalls | Not modeled | PASS | PASS |
| IOSSM image / ECC demo | Not modeled | PARTIAL | Not run |
| Bridge loopback | Not modeled | FAIL | Not run |
| Peripheral reset manager | Not modeled | PASS | PASS |
| Warm reboot | Not modeled | FAIL | Not run |

QEMU supports the software CRC and CPU memory exercise. It has no model of the
Agilex peripherals listed above. Simics used fresh model instances and completed
DDR initialization and its 16 MiB memory validation before loading each adapter.
The full Simics command returns **1**, preserving the two SMC failures and partial
IOSSM result. Completion alone is never a PASS.

The hardware runner programs volatile SRAM only, boots DDR afresh per payload,
loads at `0x82400000`, and compares every loaded byte through the memory debug
port before execution. Performance uses `0x85000000`–`0x8501ffff`, outside code,
stack and bootstrap scratch space. No SD contents, flash, EEPROM or clock NVM is
written. The peripheral reset check resets the SD/MMC controller only.

Final DDR Hello restoration: **PASS**.

The physical counter frequency was zero. Memory correctness passed, but the printed zero-time/rate values are **not valid bandwidth measurements**. Counter-clock calibration remains necessary before reporting hardware rates.

The existing QEMU Hello/NEON/copy check, all six practice labs, six deliberate
failure controls and two GDB exercises also passed. All **45** regression checks
passed, including the real QEMU subprocess test.

## Captured terminal output

These blocks are copied from actual UART/model logs. For each case, the caption
identifies whether the output is from physical hardware or Simics. The full logs,
ELF/binary hashes, build-source hashes, per-load readback results and failed
attempts are in the [evidence bundle](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/upstream26-examples).

=== "CRC image validation"

    **Physical Modular ES** — Good image plus corrupt, partial and oversized inputs.

    ```text
    UPSTREAM_LAB_BEGIN case=0
    UPSTREAM_COMMAND crc_selftest

    ==== CRC API DEMO ====
      channel    : 0x0000000000001123
      image size : 32 bytes
      golden CRC : 0x1B61EFC6
    ======================
    [success] PASS | verdict=OK
      actual=32 expected=32 calc_crc=0x1B61EFC6 size_valid=yes crc_valid=yes
    [corrupt] CRC_MISMATCH | verdict=OK
      actual=32 expected=32 calc_crc=0x89824208 size_valid=yes crc_valid=no
    [partial] SIZE_MISMATCH | verdict=OK
      actual=27 expected=32 calc_crc=0x00000000 size_valid=no crc_valid=no
    [large] IMAGE_TOO_LARGE | verdict=OK
      actual=65 expected=65 calc_crc=0x00000000 size_valid=no crc_valid=no

    ==== CRC DEMO SUMMARY ====
      executed : 4 case(s)
      passed   : 4 case(s)
      failed   : 0 case(s)
    ==========================
    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "Memory performance"

    **Physical Modular ES** — Independent 16,384-word readback. Simulator timing is not hardware bandwidth.

    ```text
    UPSTREAM_LAB_BEGIN case=1
    COUNTER_HZ=0
    TIMING_UNAVAILABLE counter frequency is zero; memory correctness only
    UPSTREAM_COMMAND perf_selftest timer

    [PERF][TIMER] ARM generic counter frequency: 0 Hz
    [PERF][TIMER] timestamp overhead: min=0 us avg=0 us max=0 us
    UPSTREAM_COMMAND perf_selftest mem 0x85000000 65536 2

    [PERF][MEM] destructive DDR test
    [PERF][MEM] src=0x0000000085000000 dst=0x0000000085010000 size=65536 loops=2
    [PERF] mem-write: bytes=131072 time=0 us rate=0 KiB/s 0.000 Mbps
    [PERF] mem-read: bytes=131072 time=0 us rate=0 KiB/s 0.000 Mbps
    [PERF][MEM] read sink=0x00000000
    [PERF] mem-copy: bytes=131072 time=0 us rate=0 KiB/s 0.000 Mbps
    PASS PERF_MEMORY_READBACK words=16384 mismatches=0
    ```

=== "Combo PHY identification"

    **Physical Modular ES** — Version/features register access; no PHY transfer qualification.

    ```text
    UPSTREAM_LAB_BEGIN case=2
    UPSTREAM_COMMAND combophy_selftest
    Combo PHY version=0x61820107 features=0x00001FFF
    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "NoC / firewalls"

    **Physical Modular ES** — Six upstream firewall/probe checks; no throughput claim.

    ```text
    UPSTREAM_LAB_BEGIN case=3
    UPSTREAM_COMMAND noc_selftest

    +------------------------------------------------------------+
    |                  NOC SELF-TEST                             |
    +------------------------------------------------------------+

    Test 1 of 6 : NOC FIREWALL UART0
    ------------------------------------------------------------
    NOC firewall UART0 allow-nonsecure PASS
    PASS

    Test 2 of 6 : NOC FIREWALL PROBE
    ------------------------------------------------------------
    NOC firewall NOC probe allow-nonsecure PASS
    PASS

    Test 3 of 6 : NOC FIREWALL I2C0
    ------------------------------------------------------------
    NOC firewall I2C0 allow-nonsecure PASS
    PASS

    Test 4 of 6 : NOC PROBE ID
    ------------------------------------------------------------
    NOC probe core/id: 0xF49A0E07
    PASS

    Test 5 of 6 : NOC ERROR
    ------------------------------------------------------------
    NOC error valid: 0
    NOC probe is accessible; no captured error is currently latched.
    PASS

    Test 6 of 6 : NOC ERROR CLEAR
    ------------------------------------------------------------
    NOC error logger clear PASS
    PASS

    RESULT : 6 of 6 tests passed  -  SELF-TEST PASSED

    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "IOSSM image / ECC demo"

    **Simics 26.3** — Image readback matched all eight words. SBE/DBE event counts remained zero: injection/recovery unproven. Not injected on hardware.

    ```text
    UPSTREAM_LAB_BEGIN case=4
    UPSTREAM_COMMAND iossm_demo

    === IOSSM Image Load to DDR Demo ===

    [Step 1] Open IOSSM instance 0
    IOSSM MW: IRQ enable failed (1) - polling mode only
      [PASS] Instance opened
      [PASS] Enable ECC

    [Step 2] Load image to DDR (0x90000000)
      Loading 64-byte image to 0x90000000 ...
      [PASS] Image load

    [Step 3] Verify image
      Verifying image at 0x90000000 ...
      All 8 words match.
      [PASS] Image verify

    [Step 4] ECC status after image load
      [PASS] ECC error count = 0 (no errors during load)

    [Step 5] Inject single-bit (correctable) ECC error
      Target address: 0xA0000000
      [PASS] Inject SBE
      ECC error count after SBE injection: 0
      Interrupt acknowledged

    [Step 6] Inject double-bit (uncorrectable) ECC error
      Target address: 0xA0000008
      [PASS] Inject DBE
      ECC error count after DBE injection: 0
      Interrupt acknowledged

    [Step 7] Clear ECC error buffer
      [PASS] Clear error buffer
      ECC error count after clear: 0

    [Cleanup] Closing IOSSM instance 0
      [PASS] Close instance

    === IOSSM Demo complete ===

    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "Bridge loopback"

    **Simics 26.3** — Standalone EL3 SMC exception. Physical test needs matching fabric endpoints and a suitable SiP firmware/caller flow.

    ```text
    UPSTREAM_LAB_BEGIN case=5
    UPSTREAM_COMMAND bridge_selftest loopback 16

    === Bridge Loopback Transfer Demo ===
    Mode: control-plane + data-plane

    [Step 1] Open HPS2FPGA and FPGA2HPS bridges
      [PASS] HPS2FPGA opened
      [PASS] FPGA2HPS opened

    [Step 2] Configure routes
      [PASS] HPS2FPGA route
      [PASS] FPGA2HPS route

    [Step 3] Set flow control = BACKPRESSURE
      [PASS] HPS2FPGA flow ctrl
      [PASS] FPGA2HPS flow ctrl

    [Step 4] Enable bridges
    FAIL EXCEPTION ESR=0x5E000000 ELR=0x824069BC FAR=0x0
    UPSTREAM_LAB_COMPLETE status=1
    ```

=== "Peripheral reset manager"

    **Physical Modular ES** — SD/MMC peripheral reset/status; UART reset skipped. No media writes.

    ```text
    UPSTREAM_LAB_BEGIN case=6
    UPSTREAM_COMMAND reset_mngr_selftest
    Reset Manager Demo Start
    UART0 reset SKIPPED (console in use)
    Resetting SDMMC...
    All resets done
        UART0: RELEASED
        SDMMC: RELEASED
    Reset Manager Example Done
    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "Warm reboot"

    **Simics 26.3** — Standalone EL3 SMC exception; a reboot request is not proof of a completed reset. No physical system reboot attempted.

    ```text
    UPSTREAM_LAB_BEGIN case=7
    UPSTREAM_COMMAND reboot_mngr_selftest
    Reboot Manager Demo Start
    Triggering cold reboot (no callback)...
    Triggering warm reboot (with callback)...
    Preparing for reboot...
    Saving logs...
    Stopping peripherals...
    Inititating Warm RebootFAIL EXCEPTION ESR=0x5E000000 ELR=0x824069BC FAR=0x0
    UPSTREAM_LAB_COMPLETE status=1
    ```

## Reproduce

Inside the existing tool container, from `examples/agilex5-modular`:

```sh
./simics/build.sh OCRAM
./simics/build.sh DDR
bash upstream-lab/build.sh qemu
python3 upstream-lab/run.py qemu
bash upstream-lab/build.sh agilex5
python3 upstream-lab/run.py simics --only crc,perf,combophy,noc,iossm,bridge,reset,reboot
```

The Simics model must already be installed/deployed as described in
[Simics setup](simics.md). See the
[adapter and physical-runner instructions](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/upstream-lab)
for the memory map, hardware command, matching handoff and lock requirements.
Public CI compiles the adapters and runs their QEMU selection; local Simics and
physical-board results are recorded evidence, not hosted CI execution.

## Failures and troubleshooting

- **OpenOCD `checksum_memory` unsupported:** the first hardware attempt failed
  before payload execution. `verify_image` requires a target helper absent here.
  The runner now dumps memory through `hps.sys_bus`, compares it in Python, then
  resumes through a second bounded OpenOCD invocation. Every payload byte must
  match. The initial attempt's DDR restoration passed.
- **Tcl `read ?-nonewline? chan` error:** the first attempt to compare dumped
  binaries inside this OpenOCD Tcl failed. Comparison now runs on the host before
  resume. That failed attempt and its restoration are retained separately.
- **Bridge/reboot `ESR=0x5E000000`:** symbolization locates the exception in
  `smc_call`, `drivers/sdm_mailbox/socfpga_sip_handler.c:44`. The EL3 diagnostic
  environment does not provide the required SiP caller/service path. Do not
  replace this failure with a completion-only PASS.
- **IOSSM prints injection PASS with zero events:** the request API returned
  success, but neither event count increased. The report marks this PARTIAL;
  image-load/readback is proven, error detection and recovery are not.
- **Counter frequency zero:** keep the memory-readback result separate from
  performance timing. Do not interpret zero elapsed time as unlimited bandwidth.
- **RWX linker warning:** expected for this combined diagnostic RAM region; the
  resulting ELF/binary still build. Permission isolation is outside this adapter.
