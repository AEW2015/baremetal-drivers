# 6. Swap test IP with partial reconfiguration

The goal is to keep the HPS application, DDR and static fabric running while
replacing an **ADD1** accelerator with **XOR1**, then swapping back. Both expose
the [same register ABI](fabric-ip.md#register-abi-10), so the application probes
the current persona and reuses its driver.

!!! info "Advanced integration lab — live PR not yet validated"
    Agilex 5 is covered by Altera's PR design flow. This repository supplies the
    two tested arithmetic implementations, common driver and integration recipe;
    it does not yet supply a fitted Modular PR base, persona RBFs or a tested
    PR bitstream transport. Confirm support for the exact **A5ED065BB32AE6SR0 ES**
    device and installed Quartus/IP version in your project before proceeding.
    Family-level support does not establish that this specific bench build works.

Altera describes the device capability in its
[Agilex 5 overview](https://docs.altera.com/r/docs/762191/current/agilex-5-fpgas-and-socs-device-overview/partial-and-dynamic-configuration-of-agilex-5-fpgas-and-socs)
and the implementation flow in its
[PR user guide](https://docs.altera.com/r/docs/683834/current).

## What students will compare

| Method | What changes | What remains running | Status here |
|---|---|---|---|
| Compile-time MODE | Logic selected during synthesis | Not a runtime swap | ADD/XOR RTL + C driver simulated |
| Full SOF replacement | Whole volatile fabric; HPS bring-up repeated | No application-continuity claim | Guarded deployment recipe supplied; new fabric not board-qualified |
| Partial persona RBF | One planned PR region | Static shell/HPS/DDR by design | Integration lab; hardware demonstration pending |

The normal DDR runner programs a boot image and restarts the application.
It cannot demonstrate live PR continuity. Do not feed a persona RBF into
`fabric/run.py`, `run_suite.py` or the HPS-only `quartus_pfg -o hps=1` path.
Renaming a full image to `.rbf` does not make it a PR persona.

## 1. Define a small, stable PR boundary

For the first PR experiment, put the **entire `lab_ip` instance** inside the
PR partition, including its CSR registers and arithmetic core. Put the following
in the **static region**, outside that partition:

```text
HPS LWH2F manager
    ├── static PR control/status + bitstream transport
    ├── static heartbeat / scratch register
    └── Avalon-MM PR Freeze Bridge
          └── PR partition: lab_ip MODE=1 or MODE=2
```

Keep HPS, HPS DDR, bridge clock/reset infrastructure, PR controller, isolation,
and any configuration transport outside the changing region. The CSR interface
(width, address span, read timing and clock/reset) must match for every persona.
No native external IO pins or memory controllers are needed in the region.

Use the [Avalon-MM PR Freeze Bridge IP](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/avalon-mm-partial-reconfiguration-freeze-bridge-ip)
between the static Avalon interconnect and PR agent, with a static region
controller/sequencer appropriate to your installed IP. If you later place an AXI
interface across the boundary, use isolation that handles AXI's independent
channels and outstanding transactions; a simple data mux is insufficient.

The earlier lesson's QUIESCE bit stops this tiny core's starts, but it is
**not the vendor freeze handshake**. Its registers live inside this PR boundary,
so software must stop polling them while isolation is asserted. Put status
needed during reconfiguration in the static control block.

An alternative later exercise can keep the CSR bank static and partition only
`u_persona`; that requires a deliberately designed conduit isolation/reset
contract. The current `u_persona` is combinational, not a complete PR shell.

## 2. Build the base and two implementation revisions

First establish the two full-image results in [lesson 5](fabric-ip.md). Then work
in a separate PR project copy; keep the known-good non-PR images available.

1. Select the exact Modular ES part and installed Quartus Pro version. Confirm
   the PR controller/freeze IP can be generated for it. Validate the HPS and DDR
   settings against the original handoff.
2. Add the static controller, configuration transport, freeze bridge and a static
   heartbeat/scratch register. Allocate their own non-overlapping address windows;
   export the actual addresses instead of assuming offsets from an example.
3. In the Design Partitions window, make the complete `lab_ip` instance a PR
   partition. In Chip Planner, reserve an appropriate legal PR region/Logic Lock
   placement for the device, large enough for both personas. Keep clocks and
   static resources legal across the boundary. Do not copy coordinates from a
   different die or package.
4. Create a **base revision** with ADD1 (`MODE=1`). Compile and close timing.
   Export the root static partition's **final snapshot QDB**, including its
   entity-bound SDC files. Retain the base full SOF and matching handoff.
5. Create **ADD implementation** and **XOR implementation** revisions. Import
   that same static QDB for `root_partition`; rebind the PR partition to
   `lab_ip`, with MODE=1 or MODE=2 respectively. Compile both against that static
   snapshot and check PR legality plus timing reports.
6. Identify the persona RBF generated by the Agilex Assembler for each region
   from the compilation reports. Preserve its association with the exact base
   and partition. Keep the full base SOF separate from each partial RBF.

The source-backed details are Altera's
[static-region export](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/step-7-compile-the-base-revision-and-export-the-static-region),
[implementation setup](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/step-8-setup-pr-implementation-revisions)
and [Agilex PR file generation](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/generating-pr-bitstream-files).
These are FPGA build steps, not additional flags on the C compiler.

### Parameterized persona assignment

After defining the partition and importing the base QDB, use the **actual full
hierarchical path** from your generated design. For the XOR implementation's QSF:

```tcl
# Replace the example hierarchy with your exact PR partition instance.
set_instance_assignment -name RTL_PARAMETER "MODE=2" -to {system|lab_0}
set_instance_assignment -name ENTITY_REBINDING lab_ip -to {system|lab_0}
```

Use MODE=1 in the ADD implementation. The hierarchy above is illustrative and
will generally differ in generated Platform Designer systems. The repository
also contains `fabric/pr/persona_assignments.tcl.example`, which refuses to run
until its hierarchy placeholder is replaced. This fragment does not create the
partition, floorplan or static import. Altera documents these assignments for
[parameterized PR personas](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/method-2-set-qsf-assignment-for-a-parameterized-pr-persona).

## 3. Give the bitstream loader an explicit contract

Choose a supported route to deliver the partial bitstream to the **SDM**, such
as an instantiated PR controller with a tested host transport. Keep the transport
and its status registers in the static shell. Generate its documentation and
register headers from the actual IP version; do not invent SDM mailbox opcodes
or substitute writes to the arithmetic CSR window.

The current mailbox example proves IDCODE reads only. It is not a PR uploader.
Likewise, our diagnostic EL3 initializer is not a resident BL31/PSCI service;
do not assume a Linux FPGA-manager or SMC call is available. A Linux-host
container is also not the target HPS Linux system.

Before using a loader, define and verify:

| Input / event | Required behavior |
|---|---|
| Selected base and region | Match the loaded static build and intended partition |
| Persona file | Exact partial RBF, byte count, SHA-256 and intended persona ID |
| Stop/freeze request | Drain outstanding transfers; wait for acknowledgement |
| Configuration | Stream with the generated IP's handshake and required byte order |
| Completion | Check actual controller/SDM completion and error state, not just bytes sent |
| Timeout/error | Retain isolation; report diagnostics; avoid resuming the failed region |
| Successful restart | Apply region reset/start sequence, wait for readiness, then release access |

Quartus/SDM provides PR bitstream compatibility checking for Agilex devices as
[documented here](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/partial-reconfiguration-bitstream-compatibility-checking).
Keep it enabled; a file hash is provenance, not a replacement for compatibility
checking. Changing the static design produces a new base/persona family.

A useful lab artifact record contains: device/Quartus version, base SOF hash,
static QDB hash, region hierarchy, persona RBF hash and size, ABI/persona ID,
CSR/control addresses, timing result and loader version. The loader must reject
a mismatched pair before starting. This tutorial does not ship fabricated
hashes or a loader that claims compatibility without a compiled base.

## 4. Run the live ADD → XOR → ADD experiment

These are the acceptance steps for the **completed PR project**, not commands
the current HPS-only suite can execute. Use one bench owner and retain the
hardware lock for the complete experiment. Do not rerun DDR initialization or
load the HPS ELF between persona swaps; those would restart the experiment.

1. Program the matching **full PR base** once, initialize HPS DDR/LWH2F and load
   your resident test application once. Record the static build identity.
2. Read LAB1/ABI/ADD1. Execute `(7,5)` and require result `12` plus sequence delta
   one. Save a sentinel in static scratch RAM and in an HPS DDR buffer outside
   all loader/test scratch ranges; record the static heartbeat.
3. Call `lab_quiesce()` while the region is still reachable. Stop every other
   driver/thread/DMA master targeting it. Request the hardware freeze and wait
   for its acknowledgement through **static** status registers.
4. With the region isolated, load the matching XOR partial RBF through the
   tested transport. Poll only static controller state. Require successful
   controller/SDM completion and the documented region reset/start handshake.
5. Release isolation when the new region is ready. The CSR registers were
   inside the reconfigured region: treat all old state as lost, reinitialize
   operands/status, and probe ID/ABI again. Require XOR1 and `(7,5) → 2`.
6. Repeat stop/freeze/load/restart for the ADD partial RBF. Require ADD1 and
   `(7,5) → 12`. Repeat the four-vector checks for both personas.
7. Verify the HPS application never restarted, the DDR sentinel and static
   scratch value survived, and the static heartbeat continued. Record all
   controller events, hashes and result transitions before restoring the
   known-good complete design through the ordinary recovery path.

Expected acceptance record, **not a captured bench result**:

```text
BASE loaded once; application boot count = 1
ADD1: 7 + 5 = 12
freeze acknowledged → XOR RBF complete → region ready
XOR1: 7 ^ 5 = 2
freeze acknowledged → ADD RBF complete → region ready
ADD1: 7 + 5 = 12
static sentinel preserved; DDR sentinel preserved; heartbeat advanced
application boot count = 1
```

Altera's [PR process sequence](https://docs.altera.com/r/docs/683834/25.1/quartus-prime-pro-edition-user-guide-partial-reconfiguration/partial-reconfiguration-process-sequence)
defines the stop, freeze, reset and restart ordering. Follow the exact generated
controller's handshake rather than assuming one fixed delay is sufficient.

## Troubleshoot the swap

| Failure | Likely question | Next action |
|---|---|---|
| PR partition fails compilation | Exact device support, legal floorplan, static clocks, interfaces or resource fit? | Fix legality/timing before generating or loading images |
| Loader accepts bytes, persona unchanged | Correct region, actual completion, reset/start sequence and expected RBF? | Inspect controller/SDM status while isolation remains asserted |
| HPS bus hangs during swap | A master accessed the region while frozen, or outstanding transfer not drained? | Keep isolation, stop competing accesses and diagnose the freeze contract |
| Compatibility/CRC error | Persona belongs to another static snapshot or transport byte order is wrong? | Preserve status; verify the matched artifact set and loader |
| Sequence counter resets | CSR bank is in the PR partition | Expected; probe ABI/persona and initialize anew |
| Sentinel disappears or boot count increases | Full configuration/reboot occurred, or scratch ranges overlapped? | Do not call this live PR; fix the experiment's isolation and memory ownership |
| PR fails midstream | Region may contain incomplete logic | Keep it isolated; use documented controller recovery or reinstall the matching full base |

The hardware milestone is a repeated ADD/XOR/ADD transition with continuity
checks. Passing two separate Verilator builds is useful preparation, and is
recorded as simulation rather than as that milestone.
