# Physical PR build and deployment status

Implemented: synthesizable static shell, ADD/XOR partition entities, Platform
Designer component/overlay, isolated baseline importer, revision generator and
bare-metal guest build. **No fitted PR images or physical swap have been
qualified yet.** Full compilation is held by the shared OpenTPU build reservation.
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

## Remaining deployment gates

1. Compile the base, verify the PR partition/floorplan and static timing, and
   export its final static QDB. Compile `pr_add` and `pr_xor` against that QDB.
2. Inspect the resulting SOF/PMSF/RBF metadata and check both partial images
   against the same base using Programmer MCP `check_pr_compatibility`.
3. Package the ADD-starting full image with its matching HPS bootloader/handoff
   and LW-bridge-enabled DDR bootstrap. Preserve known-good recovery artifacts.
4. Under the canonical board mutex, discover the current Modular cable and
   FPGA ID `0364F0DD`, set 6 MHz JTAG and program the matching full volatile base.
   Bootstrap and verify DDR, then enter `guest-hardware.elf` **once**.
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
