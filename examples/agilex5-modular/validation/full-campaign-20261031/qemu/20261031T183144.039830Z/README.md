# QEMU and independent RTL campaign

All 15 previously passing QEMU catalog exercises passed again from current
sources. The unchanged semihost assembly additionally passed when relinked to
QEMU RAM and entered at hello_entry; its printed OCRAM wording is not a physical
OCRAM result. The new total is 16 named catalog exercises with QEMU evidence.

Positive cases, deliberate failure controls, UART command interaction, and GDB
walkthroughs are captured below. A failed first custom GDB harness is retained;
its printf escaping was corrected and the final walkthrough passed. No source
or guest failure was concealed by that rerun.

Actual Verilator RTL/C-driver tests also passed for add/xor personas and all
12 DDR-probe checks. Those are independent RTL tests, not QEMU runs of fabric
hardware. Physical cache/L3 timing, DDR bandwidth and Agilex peripheral paths
cannot be inferred from this campaign.

The root results.json maps catalog IDs to nested checked results, lists all
commands/versions, source and artifact hashes, and records non-QEMU dependencies.
The main unittest suite used AGILEX_TEST_REAL_QEMU=1. Config/model/USB helper and
Simics transport protocol tests ran without touching physical hardware.
