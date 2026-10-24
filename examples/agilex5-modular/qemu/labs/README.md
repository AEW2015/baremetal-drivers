# QEMU practice labs

These six independent freestanding AArch64 programs run at secure EL3 on
QEMU `virt`, Cortex-A53, one core, GICv3 and 128 MiB RAM.

From `examples/agilex5-modular`, with `aarch64-none-elf-gcc`,
`qemu-system-aarch64` and optionally `gdb-multiarch` on `PATH`:

```sh
bash qemu/labs/build.sh
python3 qemu/labs/run.py --negative --gdb
python3 qemu/labs/run.py --only timer
python3 qemu/labs/run.py --interactive
```

Read the [six lessons](../../../../docs/examples/qemu-labs.md) for expected
results, manual debugger steps and failure experiments. Override tools through
`CROSS_COMPILE`, `QEMU` and `GDB`. Build outputs go to `build/qemu-labs/`;
timestamped logs and JSON go to `runs/qemu-labs-*/`.

`start.S`, `link.ld`, `runtime.c` and `lab.h` provide shared startup, vectors,
UART output and semihosted exit. Each named C file is one lesson.
`build.sh` also builds six deliberately broken variants. `run.py` checks
success markers, failure rejection, UART interaction and optional GDB checks.

The timer uses secure physical timer PPI 29, delivered as an EL3 FIQ.
The MMU exercise uses identity mapping with normal noncacheable RAM; it does
not test caches or an Agilex peripheral. This is QEMU evidence only.
