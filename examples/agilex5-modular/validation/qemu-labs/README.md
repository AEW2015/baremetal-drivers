# QEMU practice lab validation

Actual local execution on 2026-10-24 UTC, against the new `qemu/labs` sources.
Base repository revision: `cd99b3090ee921c25b8758f97ae8e5f7a9d20806`;
the labs and tutorial changes were uncommitted when tested.

Commands, from `examples/agilex5-modular` with tools on `PATH`:

```sh
bash qemu/labs/build.sh
python3 qemu/labs/run.py --negative --gdb
```

Result: 14/14 host checks passed: six normal guests, six deliberately broken
guests rejected, and two GDB exercises. UART passed all 11 input cases.
The startup debugger verified data before/after relocation and the entire BSS.
The corruption watchpoint stopped in `inject_corruption`, then all 512 words
were verified after repair. The timer reported ten interrupts and ten WFI
entries. The MMU reported ESR `0x9600004e` and FAR `0x44000000`.

`results.json` records exact tool versions, commands, source hashes, ELF hashes,
return codes and UART cases. Individual `.log` files contain guest output;
`*-gdb.log` contain debugger output and `.gdb` files contain the executed scripts.
Absolute paths in these records refer to the test workspace. These are snapshots,
not evidence for binaries subsequently rebuilt with different sources or tools.

Tools: Arm GNU 13.2.Rel1 (GCC 13.2.1), QEMU 8.2.2 TCG and GDB 15.1.
Host: Ubuntu 24.04 x86_64. Guest: secure EL3 Cortex-A53, one CPU, GICv3,
128 MiB RAM. No physical hardware was used.

Additional checks: the original QEMU CPU/NEON/RAM smoke test passed;
`bash -n qemu/labs/build.sh`, Python syntax compilation, and
`mkdocs build --strict` passed. The original smoke ELF retains its pre-existing
RWX segment linker warning; the new labs link without that warning.

## Integration with upstream

Rebased the practice-lab commit onto upstream `main` at
`4cea446bec16b67d584e8582b455158bb977f911` and retained both the existing
README sections and the new lab section. A subsequent fetch found no newer commits.

Post-integration validation passed:

- `AGILEX_TEST_REAL_QEMU=1 python3 -m unittest discover -s tests -v`: 24 tests,
  including real emulator/compiler checks (`upstream-regressions.log`).
- `bash fabric/test.sh`: C-driver/RTL simulation passed for ADD and XOR personas,
  using Verilator 5.020 (`upstream-fabric-tests.log`).
- Rebuilt all practice labs and reran `python3 qemu/labs/run.py --negative --gdb`:
  all 14 checks passed again. The recorded source files remain unchanged.
- `mkdocs build --strict`: passed.

These software simulations do not validate physical fabric deployment or live
partial reconfiguration.
