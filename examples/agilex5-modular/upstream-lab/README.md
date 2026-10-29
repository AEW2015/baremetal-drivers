# Testing the 26.3 examples across environments

This adapter invokes the unchanged upstream CRC, performance, Combo PHY, NoC,
IOSSM, bridge, reset and reboot example sources. It supplies bounded command
selection, UART output and startup for the established Modular ES bench.
It does not boot the stock DDR console or establish a resident BL31 service.

Inside the configured tool container, from `examples/agilex5-modular`:

```sh
./simics/build.sh OCRAM
./simics/build.sh DDR
bash upstream-lab/build.sh qemu
python3 upstream-lab/run.py qemu
bash upstream-lab/build.sh agilex5
python3 simics/setup.py --simics-root "$SIMICS_FPGA_ROOT"
python3 upstream-lab/run.py simics --only crc,perf,combophy,noc,iossm,bridge,reset,reboot
```

The full Simics selection currently returns nonzero: bridge/reboot encounter
an SMC exception; IOSSM memory readback passes but its ECC event counters stay
zero after injection requests. These outcomes must remain visible.

QEMU `virt` supports the **software CRC** and CPU memory-performance examples.
Its PL011 replaces only the output sink. It does not model Agilex bridge,
IOSSM, Combo PHY, reset-manager or NoC hardware. Its printed throughput is
emulator timing, not an estimate of physical DDR bandwidth.

The Simics adapter boots the existing OCRAM console, runs `ddr_selftest`, loads
the new image into DDR and jumps to its entry point. Each test gets a fresh
model. A fallback to OCRAM is rejected. Its timing values likewise describe
the virtual platform.

| Address / area | Use |
|---|---|
| A5 `0x82400000` | Adapter code/data/BSS, bounded below `0x82500000` |
| A5 `0x83fff000` | Stack top |
| A5 `0x85000000`–`0x8501ffff` | Performance source/destination, 64 KiB each |
| Simics `0x83000000`–`0x83ffffff` | Prior OCRAM console's DDR validation |
| Simics IOSSM `0x90000000`, `0xa0000000` | Upstream demo image and injection targets |
| QEMU `0x40200000`, `0x41000000` | Image and stack top |
| QEMU `0x42000000`–`0x4201ffff` | Performance source/destination |

CRC requires all four good/corrupt/partial/oversized cases to pass. Performance
also requires a separate comparison of **all 16,384 words** in both buffers
against the final source pattern. Completion text alone is insufficient.
`TIMING_UNAVAILABLE` means the counter frequency was zero; memory correctness
can still pass, but the reported timing/rate must not be used.

The linker may emit an RWX-segment warning for this small diagnostic's combined
RAM region. A successful link still produces the ELF and binary. This adapter
does not establish MMU permission isolation.

## Physical bench

The host runner uses the established DDR initializer, UART and OpenOCD profile.
It holds the shared hardware lock, rediscovers JTAG using Programmer MCP before
every programming operation, boots DDR afresh for each payload, verifies every
loaded byte through the memory debug port, and restores DDR Hello afterward.

```sh
python3 upstream-lab/hardware.py \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --artifacts /home/lada/quartus26-mcp-demos/baremetal-simics-cleancheck-20261028/examples/agilex5-modular/build/upstream-lab-agilex5 \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py
```

These paths describe this bench. Read the kit hardware profile before adapting
them. If the current image has no HPS debug TAP, restore the matching HPS-enabled
volatile image under the shared hardware lock before using this runner. Do not
substitute a Premium-kit handoff.

The physical selection permits CRC, performance, Combo PHY identification,
NoC and SD/MMC peripheral-reset checks. It never dispatches storage writes,
IOSSM ECC injection, bridge loopback or system reboot. Bridge needs matching
fabric endpoints; the SiP calls need an appropriate secure-firmware/caller flow.
No flash, SD contents, EEPROM or clock NVM is written by the selected commands.

OpenOCD's `verify_image` checksum helper is unsupported on this A55 target.
The runner instead uses `dump_image` through `hps.sys_bus` and compares the
loaded payload byte-for-byte before resuming. The failed checksum attempt and
its successful DDR restoration are retained with the validation evidence.

ELF/binary hashes, source/build metadata, per-case UART and debugger/model logs
are saved under ignored `runs/`. See the tutorial validation report for captured
results and the limits of each test.

## Secure firmware follow-up

For bridge/reboot/mailbox services, build the pinned runtime with `bash upstream-lab/build_bl31.sh` and pass `--bl31 build/runtime-atf/agilex5/debug/bl31.bin` to the Simics runner. The adapter then runs at EL2 through resident BL31. Bridge loopback and observed warm reboot pass in this mode. Mailbox remains partial (model rejects GET_IDCODE), and IOSSM rejects actual command-error responses instead of misreporting PASS. See `docs/runtime-fixes.md` for commands and captured evidence; the earlier standalone results above are historical.

The hardware runner accepts `--wait-for-hardware`, recording atomic per-run mutex state while waiting. `--only perf,mailbox,bridge-control --bl31 PATH` selects the secure-runtime hardware checks. `bridge-control` enables/disables only the lightweight bridge; it never writes the upstream example's unverified physical loopback address. A missing HPS TAP selects the matching full volatile DDR recovery image. Create `CANCEL` inside a waiting run folder to cancel before hardware access.
