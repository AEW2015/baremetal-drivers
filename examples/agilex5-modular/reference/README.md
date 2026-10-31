# Physical reference checks

The unchanged semihost assembly, OCRAM UART payload and read-only fault probe
have physical captures in the full campaign. The separate [PSCI harness](psci/README.md)
requires resident BL31 and a nonsecure caller.

Build from the example-pack directory:

```sh
bash reference/build.sh
bash bootstrap/ocram/build_uart.sh
```

The host uses `reference/run_hardware.py --bench ... --mcp-client ...` for
semihost and the register probe; add `--ocram-uart` to run the UART payload alone.
The runner holds the established shared hardware mutex, validates the board,
uses fresh matching bootstraps and restores DDR Hello. It uses Tcl files and
parses the descriptive CSW response before restoring the numeric pattern.

Semihost runs at OCRAM0x20004 and requires debugger output plus breakpoint
PC0x20010 and full binary readback. The register probe reads exception state;
it does not inject or recover a fault. The OCRAM UART payload replays the
bench-specific handoff tables and programs divisor54 for the verified100MHz
UART profile. Do not copy that configuration to an unrelated design. That
run entered through JTAG after bootstrap; it does not independently qualify a
cold start with DDR absent.

[Full results](../validation/full-campaign-20261031/hardware/results.json) retain
source, ELF, binary and load/readback identities and restoration results.
