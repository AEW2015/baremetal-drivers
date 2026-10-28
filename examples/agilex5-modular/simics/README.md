# Simics Agilex 5 labs

Run these commands in the Linux tool container from `examples/agilex5-modular`:

```sh
export SIMICS_FPGA_ROOT=/path/to/installed/intel-fpga-ext_26.3/simics
python3 simics/setup.py
./simics/build.sh OCRAM
python3 simics/run.py --only hello,help,timer,gic,ddr
```

This exercises the current upstream 26.3 console. It uses the Linux cross
compiler (`aarch64-linux-gnu-` by default; override `UPSTREAM_CROSS_COMPILE`).
`./simics/build.sh DDR` compiles the larger profile into a separate directory;
DDR boot is not part of this OCRAM runner.

The previous 25.1 native references remain separately reproducible:

```sh
python3 simics/legacy.py --build --only hello-world
python3 simics/legacy.py --build --all
```

The recorded legacy full suite returns 1: 13 passed, timer/XGMAC/mailbox failed.
These are distinct from current API results. `legacy_source.py` verifies the
immutable dependency commit and rejects changes to tracked dependency files.

Read [the tutorial](../../../docs/simics.md) for actual terminal output, setup,
limits and troubleshooting, and [the upstream API guide](../../../docs/upstream-26.3.md)
for the rewrite. QEMU keeps its own `qemu/build.sh` and `qemu/run.py` commands.
Simulator installers, model source/libraries, ELFs, coverage and runs are ignored.
No physical UART, JTAG or host-network configuration is used by these runners.
