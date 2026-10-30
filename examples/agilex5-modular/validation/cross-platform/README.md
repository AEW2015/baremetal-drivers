# Shared practice labs and corrected secure loading

Actual local executions on 2026-10-30 UTC, based on fork `85e2e89` plus the
source changes in this commit. Per-run records include the source/adapter hashes,
ELF/binary hashes, commands, UART output and debugger/process exit statuses.
These are snapshots of the tested artifacts, not qualifications of future builds.

| Campaign | Result |
|---|---|
| `qemu-practice` | Seven normal guests, six expected failures and two GDB exercises passed |
| `simics-practice` | Seven normal guests and six expected failures passed |
| `hardware-practice` | All seven normal guests passed; final DDR Hello restoration passed |
| `hardware-negative` | All six expected failures correctly rejected; restoration passed |
| `hardware-runtime` | Performance, TF-A mailbox and lightweight bridge control passed; restoration passed |
| `regressions.log` | 53 Python regression checks passed, including real QEMU execution |

The shared normal guests are startup/data relocation, corruption/repair,
synchronous exceptions, secure timer FIQ delivery, MMU write protection, UART
parser interaction and multicore execution/readback. UART checks eleven input
cases. Multicore checks three secondary records and parks the physical secondaries
outside reloadable application memory. It is not PSCI or cache-coherency proof.

`debug-investigation` preserves the original read-only comparison of the AXI5
debug attributes and active DDR firewall. The corrected runtime run verified all
73,816 BL31 bytes, entered the application at EL2 and obtained the physical FPGA
ID `0x0364F0DD` through TF-A. Its one-second counter interval took 1.007996 host
seconds. Memory correctness checked all 16,384 words; the diagnostic transfer
rates are not optimized memory bandwidth measurements.

`attempts` retains the failed BL31 load with default nonsecure debug attributes,
the practice flat-binary transfer timeout and the first Simics runner attempt.
In the latter, five normal guests and six failure variants reached the expected
guest results but the host checker rejected the prompt-prefixed first line;
the UART CRLF transport also required correction. The final independent Simics
run passed with the corrected checker and newline handling.

The physical runner held the global bench mutex throughout each campaign,
discovered the silicon through Programmer MCP before each programming operation,
used the matching volatile DDR bootstrap and verified loaded bytes before
execution. No SD/flash/EEPROM-array or clock-NVM writes were performed. The
physical full bridge loopback, native I3C, ECC recovery and live PR remain outside
these results. No proprietary Simics runtime/model, compiler or FPGA images are
included.

See [the guide](../../../../docs/cross-platform.md) for reproduction commands and
actual terminal excerpts, and [the catalog](../../catalog.json) for historical
and current results across all example families. `manifest.json` hashes every
published evidence file except itself.
