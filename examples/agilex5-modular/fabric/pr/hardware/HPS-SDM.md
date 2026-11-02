# HPS-controlled partial reconfiguration

The optional `hps` loader keeps the bare-metal Arm application running while the
HPS sends the persona RBFs to the Secure Device Manager (SDM). The existing
`jtag` loader remains available. Both use the same matched static base and
partial images; no FPGA recompilation is required to select the loader.

## Build and run

From `examples/agilex5-modular`, in the configured Arm compiler environment:

```sh
bash fabric/pr/hardware/build_guest.sh hps
```

This produces `build/pr/guest-hps.elf` and `.bin`. The existing freestanding RWX
linker warning does not indicate a failed build. From the repository root,
with the local tool backend and UART configured as described in
[portable setup](../../../../../docs/setup.md):

```sh
python3 lab.py hardware pr --loader hps --manifest build/pr/hardware-manifest.json
```

The manifest argument is relative to `examples/agilex5-modular`; its artifact paths are
relative to the manifest directory. Supply your matched manifest, full SOF,
partial RBFs and compatibility proofs as for the JTAG PR exercise. The HPS mode
uses the newly built `build/pr/guest-hps.*` instead of the manifest's JTAG guest.
It records their actual hashes in the new run's `results.json`.

The runner holds the shared hardware mutex, verifies the Modular ES JTAG ID,
programs the initial full image, waits for DDR and bridge bring-up, then stages
both RBFs and a descriptor in HPS DDR. It verifies every staged byte through the
memory AP before starting the guest. The HPS copies one RBF at a time into a
preserved OCRAM window for the SDM to read. Each persona is limited to 483,328
bytes (`0x76000`), the size of the currently qualified images.

| CPU physical address | Reserved use |
|---|---|
| `0x82100000` | HPS guest code |
| `0x83fff000` | Guest stack top |
| `0x83ffe000` | Independent EL3 fault-report stack top |
| `0x85000000` | 256-word DDR continuity guard |
| `0x88000000` | ADD RBF staging slot |
| `0x88100000` | XOR RBF staging slot |
| `0x88200000` | Magic, address, length and CRC32 descriptors |
| `0x88400000` | Backup of the overwritten OCRAM bytes |
| `0x00001000..0x00076fff` | Temporary SDM-readable RBF window in OCRAM |

## What the HPS does

1. Probe ADD, run arithmetic vectors, save static scratch and initialize the DDR guard.
2. Freeze and drain the PR region; confirm its isolated read response.
3. Deliberately reject a corrupted CRC and confirm that the region remains
   isolated; then verify the selected RBF's length, reserved address and CRC32.
4. Confirm secure EL3 execution with MMU and data cache disabled, and obtain the SDM IDCODE.
5. Save the borrowed OCRAM bytes in DDR, copy the entire RBF to OCRAM and
   verify its CRC again. Send the Agilex 5 configuration-complete handshake
   (`0x45`), then start `RECONFIG` (`0x06`), read SDM credits and maximum block length, then
   submit indirect `RECONFIG_DATA` (`0x08`) descriptors. Only one block is in
   flight; each acknowledgement precedes the next descriptor.
6. Poll `RECONFIG_STATUS` (`0x09`) for positive configuration completion.
7. Restore and verify the borrowed OCRAM bytes, signal loader completion through the static shell's `0x60` register, wait
   for reset/identity validation, release isolation and check XOR arithmetic.
8. Repeat for ADD and verify scratch, heartbeat and DDR continuity after each swap.

The HPS owns the mailbox during the exercise. The loader refuses nonempty
queues and preserves an unexpected client's response. It does not cancel or
reset another client's transaction. On loader failure it reports an error and
leaves the PR region isolated. The runner restores the ordinary DDR Hello
image afterward and records restoration separately from the PR verdict.

JTAG is still used to install the initial full image, stage DDR data and restore
the board. With `--loader hps`, neither swap uses host `quartus_pgm --pr` or
System Console completion writes. This is a DDR-staged lab, not yet an SD-card
bootloader or a persistent firmware-update system.

## Address translation and execution context

The successful transport uses SDM address `0x1000`, backed by the same HPS
OCRAM address. The entire RBF is submitted, including the Quartus PR envelope.
Earlier direct-DDR trials using the legacy TF-A address subtraction returned
`RECONFIG_DATA` error `0x3ff` with status `0xf0030003` (invalid MAIN descriptor).
Passing the raw CPU DDR address returned error `0x0c`. Skipping the 32-byte PR
envelope and adding the firmware handshake did not fix that DDR path. These
failures do not establish that SDM can never access DDR; its mapping remains
unqualified in this diagnostic boot environment.

The loader consequently does not change the SDM DDR remapper or the SMMU.
It preserves the boot handoff at `0x7f000`. Reusing OCRAM is valid here because
the matched diagnostic BL2 has handed execution to DDR and there is no resident
OCRAM service. Do not apply this workspace borrowing to firmware that still
executes from OCRAM. After an uncertain DMA response, the source buffer remains
intact until board recovery.

This direct mailbox implementation is specific to the lab's secure EL3,
MMU-off, data-cache-off environment. An EL1/EL2 application running under resident TF-A should
use the firmware's FPGA configuration SMC service, including cache maintenance
and its ownership rules. Do not run this direct driver concurrently with it.

Protocol references: [Altera HPS boot guide, partial reconfiguration](https://docs.altera.com/r/docs/813762/current),
TF-A `QPDS26.3_REL_BASELINE_PR` commit
`09c4dc6628810d8570af69db43918d344f9e80e9`, files
`plat/intel/soc/common/{socfpga_sip_svc.c,soc/socfpga_mailbox.c}`.

## Evidence

See the [hardware report and real terminal output](../validation/20261102-hps-sdm/README.md). A successful CRC or mailbox response alone is not a
PR pass: require both persona arithmetic checks, two swaps, continuity checks
and a successful final restoration. Simics' external RTL transition model does
not implement these SDM commands or parse RBF bitstreams; QEMU does not model
the Agilex 5 configuration hardware.
