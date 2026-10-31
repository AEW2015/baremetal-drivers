# Physical PR build and deployment status

Implemented: synthesizable static shell, ADD/XOR partition entities, Platform
Designer component/overlay, isolated baseline importer, revision generator and
bare-metal guest build. The Modular ES base, ADD and XOR implementations have passed synthesis, fitting,
timing analysis and assembly in Quartus 26.3. Physical ADD→XOR→ADD swaps passed with one HPS invocation.
[Captured evidence and real UART](../validation/20261031-hardware/README.md).
The matching Modular ES source/handoff must be retained; a production-kit
reference cannot replace it.

## Prepare without changing the original project

```sh
python3 fabric/pr/hardware/prepare.py \
  --baseline /path/to/matching/Modular-ES/vendor \
  --output /path/to/new/pr-project
bash fabric/pr/hardware/generate.sh /path/to/new/pr-project
```

The importer records SHA-256 hashes of source inputs. It copies source inputs,
not previous compiler outputs. Generation fails if logs contain errors, even
when a Quartus wrapper exits zero. One initial address-map attempt exceeded the
128 KiB peripherals bridge; the corrected overlay attaches the new 256-byte
agent directly to the upstream LW bridge at `0x20000`.

The generated wrapper adds an extra `u_lab_pr` hierarchy level. Confirm the
actual generated HDL and synthesized hierarchy; this bench's candidate is
`u_baseline_top|u_fabric_subsys|u_lab_pr|u_lab_pr|slot`.

After reviewing a legal core-only placement and routing region for this exact
part, create revisions:

```sh
python3 fabric/pr/hardware/configure.py --project /path/to/new/pr-project \
  --slot 'u_baseline_top|u_fabric_subsys|u_lab_pr|u_lab_pr|slot' \
  --place-region 'X... Y... X... Y...' --route-region 'X... Y... X... Y...'
```

Coordinates above deliberately require real reviewed values. The official
Agilex 5 PCIe simulation tutorial's coordinates are for A5EC065; they are not
silently applied to this A5ED065 Modular ES board.

## Compile in dependency order

The tested Modular ES region is placement `X62 Y61 X81 Y80`, routing
`X61 Y60 X82 Y81`. It was reviewed against the reference and validated by the
actual ES Fitter, including final partition and LogicLock usage reports.
These coordinates belong to this exact device/platform.

Run complete compilation for each revision in order:

```sh
quartus_sh --flow compile baseline_a55 -c baseline_a55
quartus_sh --flow compile baseline_a55 -c pr_add
quartus_sh --flow compile baseline_a55 -c pr_xor
```

The base must finish **assembly**, not just fitting: `pr_static.qdb` preserves
the static implementation, while `output_files/baseline_a55.lab_pr_partition.pmsf`
provides the region mask used to verify implementation images. Skipping base
assembly causes error 16019. Discard artifacts emitted by a failed assembler.

Generation deliberately prunes unused Nios CPU, on-chip RAM and JTAG UART
**after** generating the parent system, then generates the child last. Parent
snapshots otherwise restore old child content. The final explicit generated-QIP
registration avoids missing child IP definitions. The standalone platform also
restores Reset Release IP ownership; the integrated baseline expected an outer
wrapper to supply it. No unrelated Nios DDR-writing application runs in this lab.

## Package and load

Build the physical guest with `bash fabric/pr/hardware/build_guest.sh`.
Build isolated DDR boot variants using a local clone of pinned ATF:

```sh
bash fabric/pr/hardware/build_boot.sh /new/boot-output /path/to/pinned/atf
```

The script verifies ATF commit `2ea5afda7f34774ddcc677fb3a728fa57f780a1e`.
Use the ADD implementation full image as the initial persona:

```sh
quartus_pfg -c output_files/pr_add.sof base-boot.sof -o hps_path=/new/boot-output/bl2-bridge.hex
quartus_pfg -c output_files/pr_add.lab_pr_partition.pmsf pr_add.rbf
quartus_pfg -c output_files/pr_xor.lab_pr_partition.pmsf pr_xor.rbf
```

This lab sets `HPS_INITIALIZATION "AFTER INIT_DONE"` before assembly, so the
full fabric is configured before HPS starts. The bridge-enabled bootstrap runs
after that. The host additionally requires the decoded "Device has entered user mode" state and `CONF_DONE=1, INIT_DONE=1`
before any fabric MMIO. Keep original DDR recovery artifacts separate.

The first hardware attempt retained the source baseline's **HPS First** setting.
DDR and Hello passed but the FPGA remained phase-1-only (`INIT_DONE=0`); its
first fabric read stalled. A successful program/DDR test did not establish
fabric readiness. The attempt was stopped and DDR Hello restored. Changing the
assembler boot-order setting corrected that prerequisite. An HPS-first system
instead needs an explicit phase-2 core configuration flow; loading HPS-only
bootstrap data does not perform that step. See the supported
[HPS_INITIALIZATION values](https://docs.altera.com/r/docs/683296/25.3/quartus-prime-pro-edition-settings-file-reference-manual/hps_initialization).

The current Programmer MCP conversion wrapper incorrectly adds flash options
to the PMSF→RBF command and can report outer success for an inner Quartus error.
Use direct PFG for that conversion, inspect the log, and require a successful
conversion before metadata/compatibility checks. HPS embedding also uses CLI
because the MCP conversion schema does not expose that operation.

## Deployment checks

1. Compile the base, verify the PR partition/floorplan and static timing, and
   export its final static QDB. Compile `pr_add` and `pr_xor` against that QDB.
2. Inspect the resulting SOF/PMSF/RBF metadata and check both partial images
   against the same base using Programmer MCP `check_pr_compatibility`.
3. Package the ADD-starting full image with its matching HPS bootloader/handoff
   and LW-bridge-enabled DDR bootstrap using FPGA-first configuration. Preserve known-good recovery artifacts.
4. Under the canonical board mutex, discover the current Modular cable and
   FPGA ID `0364F0DD`, set 6 MHz JTAG and program the matching full volatile base.
   Require FPGA user mode, bootstrap and verify DDR, then enter `guest-hardware.elf` **once**.
5. For each guest request, use only the new `u_pr_jtag` master service. Verify
   PRS1, isolated/FROZEN status and expected persona. Set host status BUSY, close
   the master service, then use the verified device index with
   `quartus_pgm -c <carrier> -m jtag --pr <matching-persona.rbf>@<index>`.
   Rediscover the chain before every programming operation. Require actual
   programmer success before host status DONE; on failure keep isolation and
   report ERROR. A process exit code alone is insufficient.
6. Require both math phases, unchanged DDR guard/static scratch, heartbeat
   progress and two releases from the same HPS invocation. Capture source/image
   hashes, UART, PR status and timing evidence; restore DDR Hello afterward.

`quartus_pgm --help=pr` confirms the dedicated `--pr` programming mode. A normal
full-image program, HPS-only RBF or restarting the application between personas
does not qualify this demonstration. No flash/media/fuse programming is needed.

Sources: [Altera PR simulation tutorial](https://docs.altera.com/r/docs/819958/current),
[PR user guide](https://docs.altera.com/r/docs/683834/current), and official
[intel/fpga-partial-reconfig](https://github.com/intel/fpga-partial-reconfig)
revision `bfb56b23790a54a766dc76a37e376cd270c5f5a3` (reviewed reference; not a
Modular board image).

## Guarded bench runner

`run.py` is the coordinator for this established two-container bench. Its
manifest names absolute host paths and SHA-256 hashes for `full_sof`,
`guest_bin`, `guest_elf`, `add` and `xor`. Each persona also has a
`compatibility` object containing `status: "pass"`, `parent_sha256`,
`child_sha256`, and the `path`/`sha256` of its captured successful Programmer
MCP check. The parent must be the final bootloader-embedded full SOF.

```sh
python3 fabric/pr/hardware/run.py --manifest /path/to/manifest.json \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py
```

The default only validates files; add `--run` to execute. A busy hardware mutex
fails before programming; `--wait-for-hardware` waits without interrupting its
owner. The runner records each programming job and fresh chain, guest readback,
UART and restoration result beneath `runs/pr-hardware-*`.

This coordinator uses the bench's matching OpenOCD configuration and recovery
runner. Adapt those paths/tool containers for another bench and preserve the
exact hardware profile. A learned application result is distinct from a
successful recovery; inspect both in `results.json`.

## Bring-up diagnostics

- **DDR Hello passes but the first fabric read stalls:** read device configuration
  status. The first attempt was phase-1-only (`INIT_DONE=0`) because the source
  baseline selected HPS First. This standalone lab selects After INIT_DONE.
  A bootloader bridge-enable message is insufficient to prove fabric readiness.
- **Configuration engine says `STATE=IDLE`:** that alone is not a failure.
  A successful FPGA-first load reported "Device has entered user mode" with
  `CONF_DONE=1, INIT_DONE=1` and still showed `STATE=IDLE`.
- **No PR master found among generic `phy_N/master` paths:** load the exact SOF
  using `design_load`, explicitly `design_link` to the freshly verified Modular
  FPGA, then select its `u_pr_jtag.master`. Do not choose the first master: this
  platform has a separate vendor master and the carrier MAX10 exposes services.
  Display cable `[1-4.2.1]` becomes `#1-4.2.1#` in service paths.
- **Guest times out immediately:** the diagnostic bootstrap can leave
  `CNTFRQ_EL0=0`, as printed by `PR_TIMER_HZ`. The guest delegates timeout control
  to the bounded host coordinator when that register is zero.
- **Recovery observes old output:** halt the previous HPS boot before starting
  the recovery runner. One early attempt accepted old DDR patterns while the new
  boot was still at PC `0x2760`. Fresh DDR Hello and PC `0x82000024` later confirmed
  recovery. The coordinator now pre-halts and requires the recovery runner's
  new UART/PC proof; a successful programming message alone is insufficient.
