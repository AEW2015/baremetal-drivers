# Secure runtime and diagnostic fixes

Fork base: 64eb8a9dd9535056b903c67f70c1a7e5dbfda5ee, plus the source hashes
recorded in each build manifest. TF-A: 2ea5afda7f34774ddcc677fb3a728fa57f780a1e.
BL31 uses RESET_TO_BL31=1, BL31 at 0x80000000 and preloaded BL33 at 0x82400000.

QEMU: CRC, performance/readback, EL3 SMC rejection/IOSSM response checks, and
zero-counter unavailable-timing checks passed. All 49 Python regressions passed.

Simics: CRC, performance/readback with 400 MHz counter, Combo PHY identification,
NoC, peripheral reset, HPS2FPGA 16-word loopback, LWHPS2FPGA control and warm
reboot passed through BL31/EL2. Warm reboot requires a fresh banner/prompt after
the guest request; a returned reset request cannot pass.

Mailbox is partial: NOOP and CONFIG_STATUS pass, GET_IDCODE is rejected with
SDM error 0x3. IOSSM is partial: all eight image words match, but its ECC counter
register offset 0x300 is unmapped in the model, and injection/clear commands
return error-bearing response status. The fixed driver now rejects those
responses instead of calling response-ready success. No ECC recovery is claimed.

Hardware validation of these new fixes is queued on the existing shared bench
mutex. Queue JSON files are submission-time snapshots, not physical results or
a live status feed. Previous hardware results remain in upstream26-examples.
The queued run freezes image hashes, checks the counter against a one-second
host interval, exercises mailbox services and bridge control, and restores DDR
Hello. It does not run physical ECC injection, system reboot or fabric loopback.

Raw UART/model logs, scripts, source/ELF hashes and pinned firmware metadata are
included. No proprietary model sources, runtime packages or executable binaries
are committed. See docs/runtime-fixes.md for commands, results and limits.
