# Read-only HPS configuration audit

See the [tutorial](../../../docs/config-audit.md) for actual output, hardware
commands, and the distinction between stable snapshots and full qualification.
Run in the Linux development container from `examples/agilex5-modular`:

```sh
bash config-audit/build.sh
python3 config-audit/run.py
```

The build uses `UPSTREAM_CROSS_COMPILE` (default `aarch64-linux-gnu-`). The runner
needs the deployed Simics project and built OCRAM bootstrap; `--project` and
`--boot` override their standard paths. Cases are `sysmgr`, `pinmux`, and the
deliberate `unstable` control. Guest images run at EL3 from `0x82400000`.

The physical runner uses the shared bench mutex and restores DDR Hello:
`upstream-lab/hardware.py --suite config` with the established bench/artifact
arguments. It does not write System Manager or pinmux configuration registers.

On the host, compare a captured `pinmux` snapshot against the matching handoff:

```sh
python3 config-audit/handoff.py --handoff /path/to/handoff.bin --snapshot /path/to/snapshot.json
python3 -m unittest discover -s config-audit -p 'test_*.py' -v
```

Comparison exits 0 for match, 1 for mismatch, 2 for malformed input. Only the
three named UART-route fields are checked. The [recorded evidence](../validation/config-audit/README.md)
keeps Simics, physical execution, negative controls and handoff comparison separate.
