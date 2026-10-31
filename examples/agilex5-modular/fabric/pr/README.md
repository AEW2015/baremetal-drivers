# Runtime ADD → XOR → ADD PR lab

The **Simics guest + Verilator transition model now runs**. It keeps one Arm
application alive through two persona transitions, verifies the original C
arithmetic driver, static scratch/heartbeat and a 256-word DDR guard, and tests
loader-error and wrong-persona rejection. The loader is explicitly simulated:
this does not parse RBFs, exercise SDM PR or qualify the physical board.

Four-state Icarus tests inject unknown register/output values, check isolation
and reset recovery, and deliberately omit reset to prove the test sees the
unknown state. The synthesizable physical wrapper has a separate JTAG-host
handshake and **no simulation-loader register**.

From `examples/agilex5-modular`, in the tool container:

```sh
bash fabric/pr/build.sh
python3 fabric/pr/run_simics.py
bash fabric/pr/hardware/build_guest.sh  # compile only; no deployment
```

Requires Verilator, Icarus (`iverilog`, `vvp`), g++, Python and the Arm compiler.
Simics additionally needs the separately licensed 26.3 runtime and the existing
`build/simics26` platform plus `build/upstream26-ocram/baremetal.bin`; see
[setup](../../../../docs/simics.md). The guest link can emit the existing
freestanding RWX-segment warning; successful execution is checked separately.

## Static register map

The region is `lab_ip`, with its existing ABI at offsets `0x00..0x3f`.
The current staged HPS map is **0x20020000**, accessed through LWH2F.
The independent JTAG Avalon manager maps this agent at **0x00020000**.

| Offset | Static register | Meaning |
|---|---|---|
| `0x40` | Control/status | Write 1 to drain/freeze. Write 0 releases only READY. Read bit 0 isolated, bit 1 READY, bit 2 ERROR, bit 3 loader busy seen, bit 4 reset active; state at bits 11:8. |
| `0x44` | Heartbeat | Advances on static clock edges, including during modeled reconfiguration. |
| `0x48` | Scratch | Preserved outside the PR partition. |
| `0x4c` | Expected persona | ADD1 `0x41444431` or XOR1 `0x584f5231`. |
| `0x50` | Successful swaps | Increments when software releases a validated persona. |
| `0x54` | Observed persona | Captured after reset, before release. |
| `0x58` | Static signature | `0x50525331` (PRS1). |
| `0x60` | Physical host status | Physical wrapper only: bit 0 loading, bit 1 completed, bit 2 failed. Written by the JTAG coordinator around a real PR programming operation. |
| `0x80` | Simulated load request | **Model only**: 1 ADD / 2 XOR. Absent from the physical RTL. |

The shell closes reads/writes, drains at least two static cycles, requires an observed
loader-busy phase, holds reset for four cycles, probes identity, then waits for
software release. Isolated reads return `0xdec0f001`. Failed loads or mismatched
identity remain isolated; a new load can recover them. This custom isolation
contract applies only to this fixed-latency, nonbursting, single-clock agent;
it is not a general AXI/Avalon freeze bridge.

## Physical build preparation

[Hardware preparation](hardware/README.md) stages source from the matching ES
HPS baseline, adds the static shell and independent JTAG manager, generates the
platform and creates PR revisions for a reviewed partition/floorplan. Generated
IP has been checked for the exact ES part; full PR fitting and hardware swapping
are still pending. Preserve the matching HPS DDR handoff and bootstrap.

The physical guest prints `PR_HOST_LOAD_REQUEST` and waits up to 120 seconds.
It never writes the model's load register. The host must check compatibility,
freeze acknowledgement and actual `quartus_pgm --pr` completion before writing
host-done. The ordinary board runner reloads its bootstrap between programs and
therefore cannot establish PR application continuity.
