# HPS-to-SDM partial reconfiguration: Modular ES, 26.3

The HPS programmed **ADD → XOR → ADD** through the SDM mailbox while the same
bare-metal application kept running. Both persona arithmetic tests, reset and
identity, static scratch/heartbeat, DDR continuity and OCRAM restoration passed.
A deliberate bad CRC was rejected before programming and left the PR region
isolated. The coordinator recorded both completed loads and restored DDR Hello.

[Complete real UART](guest-uart.txt) · [machine-readable result](results.json) ·
[build and run instructions](../../hardware/HPS-SDM.md)

This uses the matched Quartus 26.3 Build 114 Modular ES full image, HPS 14.1,
HPS EMIF 5.1 and pinned 26.3 diagnostic BL2. Both compatible partial RBFs are
483,328 bytes. The guest runs at `0x82100000` in HPS DDR. It copies each RBF
through OCRAM `0x1000..0x76fff`, which the SDM reads using one indirect descriptor.
It restores and verifies that OCRAM window after each completed configuration.

The host uses JTAG for the initial full image, DDR staging/readback and final
recovery. **Neither persona swap uses host JTAG PR or System Console writes.**
The HPS sends `RECONFIG`, `RECONFIG_DATA` and `RECONFIG_STATUS`, then signals the
static shell's loader status itself. The run holds the shared hardware mutex.
No flash, SD, EEPROM or fuse writes were performed.

An excerpt from the captured UART is:

```text
PASS PR_BAD_CRC_REJECTED
PASS PR_BAD_CRC_REMAINS_ISOLATED
PASS PR_SDM_BUFFER_CRC32
PASS PR_SDM_OCRAM_READBACK
PR_SDM_CREDITS=0x0000000000000004
PR_SDM_BLOCK_BYTES=0x00000000000ffff0
PR_SDM_DMA_ADDRESS=0x0000000000001000
PR_SDM_DMA_BYTES=0x0000000000076000
PR_SDM_ACKNOWLEDGED_BLOCKS=0x0000000000000001
PASS PR_SDM_OCRAM_RESTORED
PASS PR_SDM_RECONFIG_COMPLETE
PR_PERSONA=0x00000000584f5231
PASS SWAP_RESET_AND_ID
PASS XOR_VECTORS
```

After the second SDM transfer:

```text
PR_PERSONA=0x0000000041444431
PASS SWAP_RESET_AND_ID
PASS RETURN_ADD_VECTORS
PASS STATIC_SCRATCH_CONTINUITY
PASS STATIC_HEARTBEAT_PROGRESS
PASS DDR_GUARD_256_WORDS
PASS TWO_RUNTIME_SWAPS
PR_LAB_COMPLETE status=0
```

The full UART contains each continuity check after both swaps. The displayed
excerpts omit command tracing and intervening output; no values are invented.
Artifact paths in exported JSON are normalized relative to
`examples/agilex5-modular`. UART bytes and artifact SHA-256 values are unchanged.
The original unmodified run is identified in `provenance.json`.

## Bring-up findings and retained failures

| Attempt | Observed result | Resolution or limit |
|---|---|---|
| [Read SDM DDR remapper](attempts/remapper-read/guest-uart.txt) | External abort at `0x10d12284` | Avoided in the OCRAM transport. The exception reporter now has a valid independent EL3 stack. |
| [DDR address minus `0x80000000`](attempts/ddr-offset/guest-uart.txt) | `RECONFIG_DATA` error `0x3ff`; status `0xf0030003` | Direct SDM reads from DDR remain unqualified in this diagnostic environment. Removing the 32-byte PR envelope or adding the firmware handshake did not fix this DDR path. |
| [Raw CPU DDR address](attempts/ddr-cpu-address/guest-uart.txt) | Descriptor error `0x0c`, configuration still in progress | Rejected; the working transport uses an SDM-visible OCRAM address. |
| [First OCRAM transfer](attempts/ocram-first-swap/guest-uart.txt) | XOR programmed and passed; second descriptor read faulted at `0x88200004` | Whole-struct copy produced an unaligned access with the MMU off. Replaced it with individual volatile 32-bit reads. |
| [Coordinator bookkeeping](attempts/coordinator-bookkeeping/guest-uart.txt) | Guest completed both swaps; host verdict failed because its load list was empty | Fixed HPS completion collection and added a regression test. This attempt retains its original failed host verdict. |

Every selected attempt's JSON retains its recorded verdict and restoration
status. The final successful run is separate; earlier failures are not relabeled.

## Validation limits

This qualifies the fixed Modular ES diagnostic-boot profile and these matched
images. It does not qualify SDM DMA from DDR, an arbitrary larger RBF, borrowing
OCRAM from resident firmware, or an EL1/EL2 application bypassing TF-A. The
current reserved OCRAM capacity is `0x76000` bytes; larger personas need a reviewed
streaming or DDR-mapping extension. QEMU does not model this hardware path;
Simics' PR exercise remains the separate RTL transition model.
