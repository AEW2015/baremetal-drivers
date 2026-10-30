# Simics modeled RAM and PIO audit

This directory contains a small AArch64 guest and bounded Simics runner for the
installed Agilex 5 universal model. It exercises model register access through
LWHPS2FPGA. It does not qualify physical FPGA fabric, SOM inputs, or board LEDs.

## Model map checked before writes

The deployed `sm-ghrd-qsys-top-comp` connects `hps2fpga_0_down` to
`example_design.design_mem_conn`. That memory space maps local offset zero to
`example_design.design_memory.memory_bank`, a 1 MiB array of 32-bit modeled
registers. Existing successful bridge loopback evidence identifies this as the
RAM endpoint; see the [mapping audit](../../../docs/example-mapping-audit.md).

The deployed `sm-ghrd-subsys-periph-comp` maps the LWHPS2FPGA peripheral memory
space as follows:

| Guest address | Modeled target | Access checked |
|---|---|---|
| `0x20010000` | `sysid` RAM, 8-byte region | 64-bit read, stability only |
| `0x20010060` | `button_pio.DATA`, 32-bit register with bit 0 implemented | Read twice; no input stimulus |
| `0x20010070` | `dipsw_pio.DATA`, 32-bit register with bit 0 implemented | Read twice; no input stimulus |
| `0x20010080` | `led_pio.DATA`, 32-bit register with bits 31:0 implemented | Two write/readback patterns, then restore saved value |

Offsets are relative to the LWHPS2FPGA guest base `0x20000000`. The Simics
`print-device-reg-info` output is retained in
[`model-register-info.txt`](model-register-info.txt). The model exposes the
button and switch inputs through `input_io` and LEDs through `output_io`; only
the LED model is written. Unmodeled external input behavior is not inferred.

## Build and run

Run both commands inside the configured container, from `examples/agilex5-modular`:

```sh
./model-audit/build.sh
```

```sh
python3 model-audit/run.py --project /path/to/deployed/simics26
```

The runner defaults to `build/simics26` and
`build/upstream26-ocram/baremetal.bin`; use `--project` and `--boot` when those
artifacts live elsewhere in the container. It starts a fresh Simics process per
case, loads each guest at `0x82100000`, enforces a 90-second per-case limit,
and records terminal/UART output plus build, guest, script, and bootstrap hashes
under the standard ignored `runs/simics-model-audit-pio-*` directory. Override
the timeout with `--timeout` (1–300 seconds).

`pio` checks input reads and stability, reads the model sysid, writes and reads
back two LED patterns, and restores the original LED register value.
`mask-negative` repeats the positive checks and then applies a deliberately
incorrect expected mask to a known-good output value; the guest must detect
the mismatch. This is a checker negative control, not a simulated device fault.

## Recorded model result

The checked [run result](validation/results.json) and UART records under
[`validation/`](validation/) show both cases passing. Button and switch DATA
values were zero and stable in the run. No external input transitions were
stimulated, and no physical I/O was accessed.
