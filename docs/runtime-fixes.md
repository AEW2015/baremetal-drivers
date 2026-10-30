# Runtime fixes, simulator results and queued hardware tests

**2026-10-30 hardware follow-up:** the secure-debug loader correction now passes
BL31 readback and EL2 entry on the Modular kit. Performance (including host
counter calibration), TF-A mailbox and lightweight bridge control all passed;
DDR Hello restoration passed. See the [loading explanation and actual output](cross-platform.md).
The queue submission notes below retain the earlier campaign history.

This follow-up fixes the standalone EL3/firmware mismatch and misleading
performance/ECC diagnostics found in the [earlier campaign](upstream-examples-validation.md).
It uses pinned TF-A `2ea5afda7f34774ddcc677fb3a728fa57f780a1e` with
`RESET_TO_BL31=1`: after the established DDR bootstrap, BL31 is loaded at
`0x80000000` and enters the preloaded diagnostic at `0x82400000` as nonsecure EL2.
This preloaded workflow uses no SD image or storage writes. It is separate from
qualification of a complete Boot ROM/BL2/FIP/BL33 storage boot.

| Exercise | QEMU | Simics through BL31/EL2 | New physical validation |
|---|---|---|---|
| CRC validation | PASS | PASS | Previous version passed |
| Memory performance/readback | PASS | PASS; 400 MHz counter | PASS; host interval 1.008 s |
| Missing counter frequency | PASS: reports unavailable | Counter initialized by BL31 | Previous bootstrap frequency was zero |
| EL3 SMC precondition | PASS: rejected without exception | Services called from EL2 | EL2 service path passed; standalone guard not rerun |
| Combo PHY identification | Not modeled | PASS | Previous version passed |
| NoC / firewalls | Not modeled | PASS | Previous version passed |
| SD/MMC peripheral reset/status | Not modeled | PASS | Previous version passed |
| HPS2FPGA 16-word loopback | Not modeled | PASS | Matching physical fabric endpoint still required |
| LWHPS2FPGA enable/disable | Not modeled | PASS | PASS; no fabric-memory writes |
| Warm reboot | Not modeled | PASS: new boot banner and prompt | Not run |
| SDM mailbox | Not modeled | PARTIAL: NOOP/configuration status pass; GET_IDCODE rejected | PASS: NOOP, GET_IDCODE and configuration status |
| IOSSM image/ECC | Not modeled | PARTIAL: image readback passes; ECC unsupported/unqualified | No physical injection |

All **49 regression checks** passed, including queued-mutex cancellation without
hardware access. The four real QEMU selections passed. The Simics runs use
fresh model instances, DDR initialization and separately hashed BL31/guest images.
Simulator throughput is not a prediction of physical memory bandwidth.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](assets/architecture/design.html?example=upstream%2Fcrc){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=upstream%2Fcrc" data-example-id="upstream/crc">upstream/crc</a> · <a href="../assets/architecture/design.html?example=upstream%2Fperf" data-example-id="upstream/perf">upstream/perf</a> · <a href="../assets/architecture/design.html?example=upstream%2Fcombophy" data-example-id="upstream/combophy">upstream/combophy</a> · <a href="../assets/architecture/design.html?example=upstream%2Fnoc" data-example-id="upstream/noc">upstream/noc</a> · <a href="../assets/architecture/design.html?example=upstream%2Fiossm" data-example-id="upstream/iossm">upstream/iossm</a> · <a href="../assets/architecture/design.html?example=upstream%2Fbridge" data-example-id="upstream/bridge">upstream/bridge</a> · <a href="../assets/architecture/design.html?example=upstream%2Freset_mngr" data-example-id="upstream/reset_mngr">upstream/reset_mngr</a> · <a href="../assets/architecture/design.html?example=upstream%2Freboot_mngr" data-example-id="upstream/reboot_mngr">upstream/reboot_mngr</a> · <a href="../assets/architecture/design.html?example=upstream%2Fmailbox" data-example-id="upstream/mailbox">upstream/mailbox</a> · <a href="../assets/architecture/design.html?example=diagnostic%2Fsmc-guard" data-example-id="diagnostic/smc-guard">diagnostic/smc-guard</a> · <a href="../assets/architecture/design.html?example=custom%2Fbridge-control" data-example-id="custom/bridge-control">custom/bridge-control</a> · <a href="../assets/architecture/design.html?example=diagnostic%2Fperf-zero-clock" data-example-id="diagnostic/perf-zero-clock">diagnostic/perf-zero-clock</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=upstream%2Fcrc" title="HPS and fabric diagram for runtime-fixes.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## What changed

- The diagnostic startup supports EL3 and EL2. A resident BL31 handles the
  SiP/PSCI calls; simply jumping to the application at EL3 is insufficient.
- The common SMC helper checks its pointer and caller exception level. It rejects
  EL3 before the SMC instruction and explains the BL31 requirement.
- The Agilex 5 diagnostic initializes a missing EL3 counter frequency from the
  **pinned TF-A platform definition**, 400 MHz. BL31 initializes it for EL2. This
  value is not a universal board-clock guess; physical timing remains unqualified
  until the queued one-second counter interval matches host monotonic time.
- Performance printers/logs mark missing frequency or zero throughput interval
  as `TIMING_UNAVAILABLE`, with an error status. They no longer present those as
  successful zero-rate measurements. Memory correctness is checked independently.
- IOSSM response-ready no longer implies success: general/command errors cause
  `-EIO`, with the raw status printed. The Agilex 5 ECC counter mask uses the
  documented 16 bits. Injection acceptance, observed events and recovery remain
  separate claims. The demo now exposes unverified events.
- The reboot example requests warm reset only and reports a returned request as
  failure. The Simics runner requires a fresh post-request boot banner/prompt.
- The mailbox exercise rejects an empty/all-ones device ID even if the API reports
  success. Its scratch response remains in reserved firmware-accessible DDR.

## Reproduce the secure runtime

Inside the configured tool container, from `examples/agilex5-modular`:

```sh
./simics/build.sh OCRAM
./simics/build.sh DDR
bash upstream-lab/build_bl31.sh
bash upstream-lab/build.sh agilex5
python3 simics/setup.py --simics-root "$SIMICS_FPGA_ROOT"
python3 upstream-lab/run.py simics \
  --only crc,perf,combophy,noc,iossm,bridge,reset,reboot,mailbox,bridge-control \
  --bl31 build/runtime-atf/agilex5/debug/bl31.bin --timeout 70

bash upstream-lab/build.sh qemu
python3 upstream-lab/run.py qemu --only crc,perf,smc-guard,perf-zero-clock
```

The complete Simics selection intentionally exits nonzero while the two partial
features remain. `build_bl31.sh` fetches/verifies the immutable TF-A revision and
rejects tracked modifications. `AGILEX_RUNTIME_ATF` can select an existing clean
checkout at that exact pin; `AGILEX_RUNTIME_BUILD_DIR` separates build outputs.
Public CI builds BL31 and both diagnostic profiles and runs QEMU/regressions.
Actual Simics runs require the separately installed proprietary runtime/model.

The rebuilt OCRAM image also passed Hello, help, timer, GIC and DDR checks.
Bridge loopback and warm reboot passed again using that updated bootstrap.

## Actual terminal output

The excerpts below come from the recorded runs. Full logs, scripts, source and
binary hashes are in the [evidence bundle](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/runtime-fixes).

=== "Counter and memory"

    **Simics 26.3**

    ```text
    UPSTREAM_LAB_BEGIN case=1
    GUEST_EXCEPTION_LEVEL=2
    COUNTER_HZ=400000000
    COUNTER_INTERVAL_START
    COUNTER_INTERVAL_END ticks=400000017
    UPSTREAM_COMMAND perf_selftest timer

    [PERF][TIMER] ARM generic counter frequency: 400000000 Hz
    [PERF][TIMER] timestamp overhead: min=0 us avg=0 us max=0 us
    UPSTREAM_COMMAND perf_selftest mem 0x85000000 65536 2

    [PERF][MEM] destructive DDR test
    [PERF][MEM] src=0x0000000085000000 dst=0x0000000085010000 size=65536 loops=2
    [PERF] mem-write: bytes=131072 time=573 us rate=223385 KiB/s 1829.975 Mbps
    [PERF] mem-read: bytes=131072 time=328 us rate=390243 KiB/s 3196.878 Mbps
    [PERF][MEM] read sink=0x00000000
    [PERF] mem-copy: bytes=131072 time=409 us rate=312958 KiB/s 2563.755 Mbps
    PASS PERF_MEMORY_READBACK words=16384 mismatches=0
    ```

=== "Bridge loopback"

    **Simics 26.3**

    ```text
    UPSTREAM_LAB_BEGIN case=5
    GUEST_EXCEPTION_LEVEL=2
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
    BRIDGE LL: hps2fpga enabled successfully
      [PASS] Enable HPS2FPGA
    BRIDGE LL: fpga2hps enabled successfully
      [PASS] Enable FPGA2HPS
      HPS2FPGA status = 1, FPGA2HPS status = 1

    [Step 4.5] Data-plane write/read via HPS2FPGA window (16 words)
      Writing 16 64-bit words (0 KiB) to 0x00000000C0000000 via HPS2FPGA ...
      Reading back and verifying ...
      All 16 words verified.
      [PASS] Data loopback

    [Step 5] Pause / resume cycle
    BRIDGE LL: hps2fpga disabled successfully
      [PASS] Pause HPS2FPGA
      Backpressure after pause: 1
    BRIDGE LL: hps2fpga enabled successfully
      [PASS] Resume HPS2FPGA
      Backpressure after resume: 0

    [Step 6] Read back routes
      HPS2FPGA route: dir=0 base=0x00000000C0000000 window=0x0000000010000000
      FPGA2HPS route: dir=1 base=0x00000000D0000000 window=0x0000000010000000

    [Step 7] Disable + close bridges
    BRIDGE LL: hps2fpga disabled successfully
      [PASS] Disable HPS2FPGA
      [PASS] Close HPS2FPGA
    BRIDGE LL: fpga2hps disabled successfully
      [PASS] Disable FPGA2HPS
      [PASS] Close FPGA2HPS

    === Bridge demo complete ===

    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "Lightweight bridge control"

    **Simics 26.3**

    ```text
    UPSTREAM_LAB_BEGIN case=10
    GUEST_EXCEPTION_LEVEL=2
    BRIDGE LL: lwhps2fpga enabled successfully
    BRIDGE LL: lwhps2fpga disabled successfully
    PASS BRIDGE_CONTROL enable=0 disable=0 (no fabric memory access)
    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "Warm reboot"

    **Simics 26.3**

    ```text
    UPSTREAM_LAB_BEGIN case=7
    GUEST_EXCEPTION_LEVEL=2
    UPSTREAM_COMMAND reboot_mngr_selftest
    Reboot Manager Demo Start
    Triggering warm reboot (with callback)...
    Preparing for reboot...
    Saving logs...
    Stopping peripherals...
    Inititating Warm Reboot
    ```

    After the guest reset request:

    ```text
    Welcome to SoCFPGA Baremetal World for Agilex5 Platform

    Built: 04:03:39 Oct 29 2026

    Commit: 64eb8a9

    Running on Core 0

    Type 'help' for commands.

    SoCFPGA Bare-Metal >
    ```

=== "SDM mailbox"

    **Simics 26.3**

    ```text
    UPSTREAM_LAB_BEGIN case=8
    GUEST_EXCEPTION_LEVEL=2
    UPSTREAM_COMMAND mailbox_selftest
    MBOX client #2 opened, handle=0x000000008243A3D8
    [MBOX] init OK
    [MBOX][PASS] NOOP: ret=0
    INFO:    mailbox_poll_response_v3: SDM err code: 0x3

    ERROR: SDM mbox cmd 0x10 rejected (err=0x3)
    [MBOX][FAIL] GET_IDCODE: ret=-1 idcode=0x00000000
    [MBOX][PASS] CONFIG_STATUS: ret=0 state=0x00000000 pin=0x80000000 softfunc=0x00000003
    [MBOX] done
    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "IOSSM ECC"

    **Simics 26.3**

    ```text
    UPSTREAM_LAB_BEGIN case=4
    GUEST_EXCEPTION_LEVEL=2
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
    IOSSM_COMMAND_REJECTED status=0x00000021 general=0 command=1
      [FAIL] SBE injection request (not event proof) (rc=-5)

    [Step 6] Inject double-bit (uncorrectable) ECC error
      Target address: 0xA0000008
    IOSSM_COMMAND_REJECTED status=0x00000021 general=0 command=1
      [FAIL] DBE injection request (not event proof) (rc=-5)

    [Step 7] Clear ECC error buffer
    IOSSM_COMMAND_REJECTED status=0x00000003 general=1 command=0
      [FAIL] Clear error buffer (rc=-5)
      ECC error count after clear: 0

    [Cleanup] Closing IOSSM instance 0
      [PASS] Close instance
    IOSSM_ECC_RESULT observed=0 unverified=2; event type/recovery requires separate verification

    === IOSSM Demo complete ===

    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "Missing clock control"

    **QEMU**

    ```text
    UPSTREAM_LAB_BEGIN case=11
    GUEST_EXCEPTION_LEVEL=3
    COUNTER_HZ=0
    TIMING_UNAVAILABLE counter frequency is zero; memory correctness only
    UPSTREAM_COMMAND perf_selftest timer

    [PERF][TIMER] ARM generic counter frequency: 0 Hz
    [PERF][TIMER] TIMING_UNAVAILABLE: counter frequency is zero
    UPSTREAM_COMMAND perf_selftest mem 0x42000000 65536 2

    [PERF][MEM] destructive DDR test
    [PERF][MEM] src=0x0000000042000000 dst=0x0000000042010000 size=65536 loops=2
    [PERF] mem-write: TIMING_UNAVAILABLE (counter frequency or elapsed interval is zero)
    [PERF] mem-read: TIMING_UNAVAILABLE (counter frequency or elapsed interval is zero)
    [PERF][MEM] read sink=0x00000000
    [PERF] mem-copy: TIMING_UNAVAILABLE (counter frequency or elapsed interval is zero)
    PASS PERF_MEMORY_READBACK words=16384 mismatches=0
    UPSTREAM_COMMAND perf_selftest latency timer 100

    [PERF][LAT][TIMER] measuring perf_counter_ticks() overhead loops=100
    [PERF][LAT] timer-overhead: TIMING_UNAVAILABLE (counter frequency is zero)
    UPSTREAM_COMMAND perf_selftest log dump

    [PERF][LOG] entries=4 max=64
    [PERF][LOG] tag=mem-write TIMING_UNAVAILABLE status=-61
    [PERF][LOG] tag=mem-read TIMING_UNAVAILABLE status=-61
    [PERF][LOG] tag=mem-copy TIMING_UNAVAILABLE status=-61
    [PERF][LOG] tag=timer-overhead TIMING_UNAVAILABLE status=-61
    UPSTREAM_LAB_COMPLETE status=0
    ```

=== "EL3 precondition"

    **QEMU**

    ```text
    UPSTREAM_LAB_BEGIN case=9
    GUEST_EXCEPTION_LEVEL=3
    SMC_UNAVAILABLE: caller is EL3; enter EL1/EL2 through resident TF-A BL31
    PASS SMC_EL3_REJECTED_AND_IOSSM_STATUS_VALIDATED
    UPSTREAM_LAB_COMPLETE status=0
    ```

## Remaining simulator limits

**Mailbox:** the SDM model rejects opcode `0x10` (`GET_IDCODE`) with status `0x3`.
NOOP and CONFIG_STATUS succeed through the same BL31 service path. This is a
partial mailbox result; it does not inherit the earlier direct-register hardware
IDCODE proof. The pending hardware test exercises the current API through TF-A.

**IOSSM:** the model reports an unmapped ECC counter register at offset `0x300`.
Injection responses carry status `0x21` (command error), and clear carries `0x3`
(general error). The old driver ignored those error bits. The fixed driver
correctly returns `-EIO`. The model still validates all eight image words, but
ECC detection/type/recovery are not qualified. No vendor model code was changed
or synthetic ECC events inserted to make this pass.

## Hardware mutex and queued validation

The hardware runner uses the existing shared file mutex:

```text
/home/lada/altera-agilex/home/baremetal-guide-validation/examples/hardware.lock
```

`--wait-for-hardware` waits without interrupting the active owner. A per-run
`mutex.json` records `waiting`, `acquired`, `released` or `cancelled` state.
Create an empty `CANCEL` file inside the waiting run directory to cancel before
hardware access. Do not delete the shared lock file.

The submitted job freezes all ELFs/binaries and their manifest, plus BL31. It
will acquire the mutex, re-discover the Modular silicon through Programmer MCP,
boot DDR afresh, verify every loaded byte, then run counter/performance, mailbox
and lightweight bridge-control tests. It restores DDR Hello afterward. If the
HPS debug TAP is missing, it uses the matching volatile recovery image. The Atum
campaign and its restoration are left alone. Hardware queues are local; the
published submission snapshot is **not a claim of completed hardware testing**.

Example host invocation, with the established bench paths:

```sh
python3 upstream-lab/hardware.py \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --artifacts /path/to/frozen/upstream-lab-agilex5 \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py \
  --bl31 /path/to/frozen/bl31.bin \
  --only perf,mailbox,bridge-control --wait-for-hardware
```

The performance pass compares a one-second counter interval against host
monotonic UART receipt times, accepting 0.9–1.1 seconds. A failed interval check
invalidates hardware timing even if all memory words match. No flash, SD media,
EEPROM or clock NVM is written. Physical system reboot and ECC injection are not
part of this queued selection.
