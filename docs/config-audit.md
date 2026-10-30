# Read-only System Manager and pinmux audit

This lab runs a small AArch64 program on the Agilex 5 Simics platform. It reads
three System Manager fields or three pinmux fields twice, reports the observed
values, and checks that the reads are stable. A separate host tool can compare
three UART-route fields from the pinmux snapshot with the corresponding fields
in a supplied HPS handoff blob.

The guest does not write configuration registers. UART output is its only
peripheral output. A stable read means the value was readable and unchanged
across two adjacent reads; it does not prove that the value is correct for
every board or design. Only the three named UART-route fields are compared
with a handoff, and that comparison requires the matching handoff file.

<!-- example-architecture:start -->
[Open the HPS / fabric example diagram](assets/architecture/design.html?example=config%2Fsysmgr){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=config%2Fsysmgr" data-example-id="config/sysmgr">config/sysmgr</a> · <a href="../assets/architecture/design.html?example=config%2Fpinmux" data-example-id="config/pinmux">config/pinmux</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=config%2Fsysmgr" title="HPS and fabric diagram for config-audit.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Build and run in Simics

Run these commands in the Linux development container from
`examples/agilex5-modular`. The Simics model must be installed and deployed;
the upstream OCRAM bootstrap image must also be built. See the [Simics setup
guide](simics.md) for `SIMICS_FPGA_ROOT` and model deployment.

```sh
./config-audit/build.sh
python3 config-audit/run.py --only sysmgr,pinmux,unstable
```

`UPSTREAM_CROSS_COMPILE` selects the Arm compiler prefix used for these
freestanding guests; the default is `aarch64-linux-gnu-`. This is separate from
the host Python/Simics tools. The build places guests at `0x82400000` and
records the compiler and source and artifact hashes in ignored
`build/config-audit/build.json`.

The runner defaults to `build/simics26` and
`build/upstream26-ocram/baremetal.bin`. To use another Simics project or OCRAM
bootstrap, pass `--project PATH` or `--boot PATH`. Select individual cases with
`--only sysmgr`, `--only pinmux`, or `--only unstable`. Each case starts a fresh
Simics process, initializes and checks the model's DDR through the OCRAM
console, then loads the audit guest. Output and JSON snapshots are written to
`runs/simics-config-audit-<UTC>/`.

## Recorded output

The recorded Simics run passed all three runner cases. The normal System
Manager case printed:

```text
CONFIG_AUDIT_BEGIN sysmgr
CURRENT_EL=0x0000000000000003
SILICONID10x0000000000030000
SILICONID20x0000000000000000
MPU_STATUS0x0000000000000000
PASS READ_ONLY_SNAPSHOT registers=3
CONFIG_AUDIT_COMPLETE status=0
```

The normal pinmux case printed:

```text
CONFIG_AUDIT_BEGIN pinmux
CURRENT_EL=0x0000000000000003
PIN2SEL0x0000000000000005
PIN3SEL0x0000000000000005
UART0_USEFPGA0x0000000000000000
PASS READ_ONLY_SNAPSHOT registers=3
CONFIG_AUDIT_COMPLETE status=0
```

The negative control intentionally changes the second `PIN2SEL` value in the
guest. The guest detects the mismatch and returns a failure status; the
runner's test passes because it expected this failure:

```text
CONFIG_AUDIT_BEGIN pinmux
CURRENT_EL=0x0000000000000003
PIN2SEL0x0000000000000005
FAIL UNSTABLE_OR_UNAVAILABLE PIN2SEL
PIN3SEL0x0000000000000005
UART0_USEFPGA0x0000000000000000
CONFIG_AUDIT_COMPLETE status=1
```

These are snapshots from the recorded Agilex 5 virtual platform, not universal
register expectations. The full captured UART files and case results are
retained in the [config-audit validation record](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/config-audit).

The separate physical Modular ES run passed all three cases, including the
injected `unstable` control, then reported `DDR Hello restoration: pass`.
These physical results are recorded separately from Simics; the configuration
snapshot cases do not measure timing. See the [hardware result record](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/config-audit/hardware).

## Compare the pinmux snapshot with a handoff

The host-side `handoff.py` parser reads the big-endian HOFF binary format and
checks only these offsets:

| Register | Handoff section and byte offset | Simics address |
|---|---|---:|
| `PIN2SEL` | PMUX, `0x08` | `0x10d13008` |
| `PIN3SEL` | PMUX, `0x0c` | `0x10d1300c` |
| `UART0_USEFPGA` | FPGA, `0x38` | `0x10d13338` |

Use the snapshot from the same run and the handoff that matches the loaded
board design. For the recorded external handoff profile
`modular-es-ddr1600`, whose handoff SHA-256 is
`9f1a8035d71c5735f88be7763e4f68c9d11c7b4b4263e2632c69ee5da0945640`, the
expected values are `PIN2SEL=5`, `PIN3SEL=5`, and `UART0_USEFPGA=0`.
Substitute the actual handoff file path available in your environment. The
recorded Simics snapshot matched all three values; the physical snapshot also
matched them. The [comparison report](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/config-audit/simics-handoff-comparison.json)
contains the expected and observed values plus the handoff hash.

```sh
python3 config-audit/handoff.py \
  --handoff /path/to/matching/hps_bootloader_handoff.bin \
  --snapshot runs/simics-config-audit-<UTC>/pinmux/snapshot.json
```

Exit status `0` means all three values match; `1` means at least one valid
value differs; `2` means an input is malformed or missing. The JSON report
includes the handoff hash and each expected/actual pair. A match establishes
agreement for these three UART-route fields only. It does not validate all
pinmux settings, the full handoff, or the physical board wiring.

To exercise mismatch reporting without changing the captured snapshot, copy
the snapshot to a temporary file, change one value there, then compare that
copy. A valid mismatch should produce exit status `1`. The recorded deliberate
example changes `PIN2SEL` from 5 to 4 and reports a mismatch while the other
two values match; see the [mismatch report](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/config-audit/deliberate-route-mismatch.json).
To check malformed
input handling, use a JSON snapshot missing one of the required register names;
the tool reports `invalid_input` and exits `2`.

## Limits and troubleshooting

- This is a read-only snapshot lab. It does not configure or repair pin routes.
- A stable register read is not a correctness check by itself. Compare the
  named fields against the matching handoff when that evidence is available.
- The captured Simics values describe the tested model/profile only. They do
  not prove physical connectivity or board I/O behavior.
- If Simics cannot start, check that `SIMICS_FPGA_ROOT` points to the installed
  26.3 `simics` directory and that `python3 simics/setup.py` completed.
- If the bootstrap image is missing, build it with `./simics/build.sh OCRAM`
  or provide its path with `--boot`.
- If a run reports missing/duplicate register output or a `0xffffffff` value,
  inspect that case's `terminal.log` and `uart.txt`; the runner rejects
  incomplete snapshots and unavailable reads.
