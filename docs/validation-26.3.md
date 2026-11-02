# Fresh validation on the 26.3 stack

The Agilex 5 Modular ES kit was retested with **Quartus 26.3 Build 114**, saved
**HPS 14.1.0 / HPS EMIF 5.1.0** configurations, and the matching 26.3 ATF and
U-Boot release sources. The actual board remains `A5ED065BB32AE6SR0`, JTAG ID
`0364F0DD`, using HPS DDR bank 3A. Recorded timestamps are UTC on 2026-11-02.

| Runtime | Passed | Partial | Failed | Not executed on this runtime |
|---|---:|---:|---:|---:|
| QEMU | 16 | 0 | 0 | 78 |
| Simics | 49 | 7 | 8 | 30 |
| Modular hardware | 50 | 6 | 0 | 38 |

**89 of 94 registered rows were exercised on at least one runtime.** Two further
standalone fabric rows passed host C/Verilator checks. Three frozen physical
adapters were not executed: the original watchdog, external-EEPROM SPI and
legacy mailbox bodies need separate safe physical ports. Their corresponding
model or modern board examples remain distinct rows.

A pass applies to the stated exercise, rather than every capability of an IP
block. Partial is not a full feature pass. The USB runner still exits 1 because
external devices do not enumerate; that raw outcome is retained. FCS and ECC
also retain their narrower capability verdicts.

Browse the [all-94 coverage ledger](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/stack-26.3-20261101/COVERAGE.md),
[machine-readable coverage](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/stack-26.3-20261101/coverage.json),
and [captured evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/stack-26.3-20261101).
The [migration tutorial](stack-26.3.md) explains rebuilding and selecting the
matched tools and images. Historical results retain their original artifacts.

## Versions and rebuilds

| Component | Qualified source / version |
|---|---|
| Quartus | 26.3.0 Build 114 |
| HPS / HPS EMIF | 14.1.0 / 5.1.0 |
| Driver upstream base | `66bdcc347564c5698a8997169bce83a31647d618`, still upstream HEAD; fork fixes retained |
| ATF 26.3 base | `09c4dc6628810d8570af69db43918d344f9e80e9`, TF-A 2.15.1 |
| U-Boot 26.3 base | `5ba74aeda63ed07e98670f8c2f0135de06543ba0`, U-Boot 2026.07 |
| Bare-metal compiler | Arm GNU 13.2.Rel1 |
| Debugger on hardware | Quartus OpenOCD `0.12.0+quartus-gc58ca4ebc` |
| Simics | Base 7.89.0; FPGA model `263000013` |

ATF and U-Boot use vendor tag `QPDS26.3_REL_BASELINE_PR`. Their `-dirty` banner
reflects the reproducible diagnostic hooks and guarded USB configuration.
Actual source and artifact hashes accompany the results; an upstream base hash
alone does not describe the fork's local fixes.

The new Ubuntu learning image passed its full board-free check. In that fresh
image, both current SDK console targets, BL31, the USB monitor, U-Boot and both
DDR BL2 variants built successfully. The hardware reference image passed tool
smoke checks. See the [container evidence](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/stack-26.3-20261101/container/results.json)
and [Dockerfile instructions](container.md). The 26.3 hardware base is supplied
by the user; no public `alterafpga/quartus-pro:26.3-all` tag was available.

The base, ADD and XOR builds passed synthesis, fitting, timing analysis and
assembly. Each final timing report has **2.221 ns minimum setup slack**,
nonnegative hold/recovery/removal/minimum-pulse-width slack, and no ignored or
unmatched timing constraints. Timing signoff Design Assistant rules passed.
Both partial images passed compatibility checks against the exact merged full
SOF used on hardware.

## Physical results and actual terminal output

All 15 board-suite entries have passing evidence on the new stack. The initial
suite was **14/15**: GPIO EEPROM access failed at its address stage. The example
now separates line timeout from NACK diagnostics, bounds retries, and avoids a
broad address scan. Two fresh rebuilt runs passed; both succeeded on their first
attempt, so the original failure's cause remains unproven. The initial failure
and both retests are retained. This is accumulated evidence, not a claim that
the original full-suite run was all green.

The seven practice labs and their deliberate failure controls passed. Current
CRC/performance/Combo-PHY/NoC/reset checks, firmware-backed mailbox and bridge
control, configuration audits, PSCI CPU_ON/OFF, OCRAM UART, semihosting, fault
probe, timer, DSU coherency/contention/partitioning and the DDR sweep also passed
within their recorded scopes.

These excerpts are from the captured runs:

```text
PASS: HPS DDR bank 3A initialized; four 64 MiB patterns and payload readback passed.
Hello, World! executing from HPS DDR bank 3A @ 0x82000000
CPU PC confirmed in DDR: 0x82000024. Application left running.
```

The retained firmware still warns about its configured 2 GiB versus detected
8 GiB capacity. These tests qualify their scratch ranges, not the entire bank.

```text
[MBOX][PASS] NOOP: ret=0
[MBOX][PASS] GET_IDCODE: ret=0 idcode=0x0364F0DD
[MBOX][PASS] CONFIG_STATUS: ret=0 state=0x00000000 pin=0xC000008F softfunc=0x00000003
```

The real **ADD → XOR → ADD** PR test entered the HPS application once. Both
partial loads preserved static scratch, heartbeat progress and the DDR guard:

```text
PASS INITIAL_ADD_VECTORS
PASS XOR_VECTORS
PASS STATIC_SCRATCH_CONTINUITY
PASS STATIC_HEARTBEAT_PROGRESS
PASS DDR_GUARD_256_WORDS
PASS RETURN_ADD_VECTORS
PASS TWO_RUNTIME_SWAPS
PR_LAB_COMPLETE status=0
```

The SOM HPS Ethernet jack passed at 1 Gb/s full duplex, including five UDP echo
sizes, corruption/sequence controls and 65,536-byte TCP transfers in both
directions. This was a new smoke run, not a repeated bandwidth/soak campaign.

```text
PASS NETWORK_LINK: 1000 Mbps full duplex
PASS ARP_PING
PASS counter_calibration
PASS udp_echo
PASS udp_sequence_and_corruption_controls
PASS tcp_board_receive
PASS tcp_board_transmit
```

## Six partial hardware capabilities

- **CCU:** current read-only identity/error APIs; the full DMI cache-flush example was excluded.
- **Clock manager:** current getters; initialization/divisor writes and physical frequency measurement were excluded.
- **SPI:** verified internal loopbacks; the full command's status phase remains partial after API auto-close. No external peer was tested.
- **FCS:** identity and read-only provision queries complete; SDM security policy denies a crypto session. RNG/session functionality remains unqualified.
- **ECC:** getters agree with raw registers; no clearing, injection or recovery qualification. Existing status is retained.
- **USB:** xHCI and the USB3320 PHY now initialize/read correctly, but external hub, flash, mouse and USB Ethernet remain unqualified.

USB is a material improvement over the earlier CNR/PHY-ID failures. Actual new
output includes:

```text
USB_PHY_ID vendor=0424 product=0007 expected=0424:0007
PASS USB_PHY_ID USB3320 ULPI register reads completed; enumeration not tested
```

```text
Bus usb31@11000000: 1 USB Device(s) found
       scanning usb for storage devices... 0 Storage Device(s) found
USB device tree:
  1  Hub (5 Gb/s, 0mA)
     U-Boot XHCI Host Controller
```

That is the controller's root hub. It does not demonstrate the attached hub or
USB class traffic. Read-only port snapshots and one bounded USB bus reset/rescan
are retained with the USB diagnostic evidence. The rescan again found only
the root hub and no storage. No media data writes were used.

## Remaining model limitations

Simics still fails the three frozen legacy timer/XGMAC/mailbox exercises and
the current ECC, I3C, SDMMC, SEU and FCS exercises. The evidence distinguishes
held-reset accesses, initialization timeouts and rejected model SDM services.
The FCS follow-up preserves control flow and completes its error reporting;
it does not claim unavailable crypto functionality.

The Simics PR transition and negative controls passed with a simulated loader.
They are partial PR coverage: the model does not parse RBFs or perform SDM
reconfiguration. Native translation/fault and fabric-route tests are model
results, not physical FPGA-to-DDR or DMA/SMMU routing qualification.

## Lessons captured in the tooling

- FPGA-first images require the complete merged SOF. PFG rejects HPS-only conversion for that configuration order.
- Imported partition/IP timing constraints must precede the top-level SDC files. An SDC-inclusive QDB export alone did not fix incorrect QSF ordering.
- Fresh UART proof begins after halting the previous boot; FPGA user mode and a PC in DDR are verified independently.
- All physical loaders share the canonical mutex. Alias coordination locks are acquired once, and nested bootstrap processes inherit the held descriptor.
- The existing bench container lacked `iproute2`; its first Ethernet attempt stopped before programming. Installing the package enabled the passing rerun. Its raw preflight failure is retained.

The scripts restore the matched current DDR Hello image after execution. Final
restoration logs include FPGA configuration state, fresh memory patterns,
payload readback and CPU-PC proof. Published UART text escapes NUL control bytes
and normalizes line endings; original-byte hashes are retained separately.
