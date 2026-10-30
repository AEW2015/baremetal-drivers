# Shared practice-lab runner

This directory runs the existing `qemu/labs` sources on Agilex 5 Simics. Physical
hardware uses the shared, mutex-protected `upstream-lab/hardware.py --suite practice`.
Read the [platform guide](../../../docs/cross-platform.md) for commands, expected
terminal output, memory maps, deliberate failures and the BL31 loading distinction.

The suite runs at secure EL3 and does not require BL31. Platform-specific code
is confined to startup, UART, MMU addresses, GIC setup and core release; the
functional checks and negative-control expectations are shared.
