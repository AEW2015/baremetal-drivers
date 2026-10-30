# Run the same practice exercises on three platforms

The practice suite shares its C checks and exception vectors across QEMU `virt`,
the Agilex 5 Simics model and the physical Modular ES kit. Platform adapters
select UART access, load addresses, GIC configuration and core release. The
[catalog](example-catalog.md) separates these exercises from the older and newer
vendor implementations and links their recorded results.

The 2026-10-30 campaign passed **all seven normal exercises and all six expected
failure controls on each of the three platforms**. QEMU also passed both GDB
exercises. Each physical campaign restored DDR Hello successfully.

| Exercise | What must happen |
|---|---|
| Startup | Copy initialized data from a different load address, clear poisoned BSS and verify stack alignment |
| Corruption | Detect exactly the damaged word at index 37, repair it and check all 512 words |
| Exception | Capture the expected BRK syndrome and fault PC, then return past that instruction |
| Timer/GIC | Deliver and acknowledge ten secure physical timer FIQs; execute the WFI idle loop |
| MMU | Read/write normal memory, reject a write to a read-only block, capture its address and resume |
| UART | Exercise all eleven command, editing, length-boundary and recovery cases |
| Multicore | Execute on three secondary CPUs and validate their affinity, CPU identification and EL3 state |

Multicore uses QEMU's loader to start its vCPUs and the established matching
TF-A reset/power sequence on Agilex. This is execution/readback coverage;
it does not qualify PSCI CPU_ON or cache coherency. Secondaries on Agilex park
outside the reloadable application after publishing their records.

## Build and run

From `examples/agilex5-modular` in the compiler container:

```sh
bash qemu/labs/build.sh qemu
python3 qemu/labs/run.py --negative --gdb

bash qemu/labs/build.sh agilex5
./simics/build.sh OCRAM
python3 practice/run.py --project /path/to/deployed/simics-project --negative
```

The QEMU command executes seven normal guests, six deliberate failures and two
GDB exercises. Simics executes seven normal guests and six deliberate failures.
The deliberately broken guests must fail for the expected reason; an unrelated
exception or a successful guest does not satisfy that control.

For physical hardware, run the existing host runner with the established bench
and MCP-client paths. It owns the shared mutex, freshly initializes DDR before
each guest, verifies every file-backed load segment, captures UART and restores
DDR Hello. Copy the build outputs before queueing so a concurrent rebuild cannot
change the requested artifacts:

```sh
cp -a build/practice-agilex5 build/practice-frozen
python3 upstream-lab/hardware.py --suite practice \
  --bench /path/to/baremetal-guide-validation \
  --artifacts "$PWD/build/practice-frozen" \
  --mcp-client /path/to/quartus26-mcp-demos/mcp_client.py \
  --port /dev/serial/by-path/YOUR-SOM-J2-UART \
  --wait-for-hardware
```

Practice labs run at standalone **EL3**. Omit `--bl31`; these exercises own the
exception vectors and, for the timer test, secure interrupt routing. The firmware
service examples below instead enter **EL2 through resident BL31**.

To practise a failure on hardware, select an explicit variant, for example
`--only exception-wrong-brk,mmu-writable-ro`. The allowed six variants are
`startup-no-bss`, `startup-no-data`, `corruption-no-injection`,
`exception-wrong-brk`, `timer-wrong-ppi` and `mmu-writable-ro`.

## Memory maps and actual output

| Region | QEMU | Agilex Simics / Modular hardware |
|---|---|---|
| Code entry | `0x40200000` | `0x82400000` |
| Initial data load address | `0x40300000` | `0x82500000` |
| Data runtime address | `0x40400000` | `0x82600000` |
| Primary stack top | `0x41000000` | `0x83fff000` |
| MMU read-only scratch block | `0x44000000` | `0x85000000` |
| MMU writable scratch block | `0x44200000` | `0x85200000` |

Each secondary uses its own stack below the primary stack. These are exclusive
diagnostic RAM windows, not allocations suitable for a concurrent OS.

Actual physical timer output:

```text
LAB BEGIN timer
PASS TIMER_FREQUENCY
PASS GIC_POWER_TRANSITION
PASS TIMER_10_INTERRUPTS
PASS WFI_IDLE_LOOP
TICKS=0x000000000000000a
WFI_ENTRIES=0x000000000000000a
LAB COMPLETE
```

Actual physical exception output:

```text
LAB BEGIN exception
ESR_EL3=0x00000000f2000123
ELR_EL3=0x0000000082401250
FAR_EL3 is not meaningful for BRK
PASS BRK_SYNDROME_AND_RETURN
PASS FAULT_PC_CAPTURED
LAB COMPLETE
```

Instruction addresses can change after a rebuild. The checker compares the fault
PC against the labels in that exact guest, rather than hardcoding this transcript.

## Correct BL31 loading for firmware-service examples

The prior physical failure happened while writing BL31 at `0x80000000`, before
any guest ran. The pinned BL2 DDR initialization protects the first DDR MiB
(`0x80000000–0x800fffff`) as secure. The installed debugger's AXI5 memory-port
default uses nonsecure transactions. Loading a normal application at `0x82400000`
therefore worked while loading BL31 produced a sticky debug-port error.

The runner now temporarily selects **secure, privileged** AXI5 accesses for the
BL31 download and full readback. It preserves unrelated CSW pattern bits, restores
the original pattern after the transfer and leaves the DDR firewall policy intact.
The relevant OpenOCD commands, after connecting and halting, are:

```tcl
hps.dap apsel 0x4000
set old_csw [hps.dap apcsw]
hps.dap apcsw 0x10000000 0x30000000
# load_image and dump_image of BL31 through hps.sys_bus
hps.dap apcsw $old_csw
```

Here AXI CSW bit 29 is Non-secure and bit 28 is Privileged. The AP address is
specific to the verified bench configuration. This is a development debug load,
separate from the normal BL2/FIP storage boot. Consult the
[OpenOCD DAP command reference](https://openocd.org/doc/html/TAP-Declaration.html),
[AXI CSW definitions](https://github.com/openocd-org/openocd/blob/master/src/target/arm_adi_v5.h)
and the [pinned TF-A DDR initialization](https://github.com/altera-fpga/arm-trusted-firmware/blob/2ea5afda7f34774ddcc677fb3a728fa57f780a1e/plat/intel/soc/agilex5/soc/agilex5_ddr.c).

BL31 is built separately with `RESET_TO_BL31=1` and
`PRELOADED_BL33_BASE=0x82400000`. The runner zeroes its handoff arguments and
enters BL31 at `0x80000000`, which enters the application at nonsecure EL2.
The corrected physical run passed performance, mailbox and lightweight bridge
control, with full BL31 readback and final DDR Hello restoration.

Actual physical mailbox output through BL31:

```text
GUEST_EXCEPTION_LEVEL=2
[MBOX] init OK
[MBOX][PASS] NOOP: ret=0
[MBOX][PASS] GET_IDCODE: ret=0 idcode=0x0364F0DD
[MBOX][PASS] CONFIG_STATUS: ret=0 state=0x00000000 pin=0xC000008F softfunc=0x00000001
[MBOX] done
UPSTREAM_LAB_COMPLETE status=0
```

The one-second physical counter interval measured **1.008 seconds** on the host,
within the runner's 0.9–1.1 second acceptance window. Memory readback verified all
16,384 words. These diagnostic, uncached transfer rates are not optimized DDR
bandwidth measurements.

## Troubleshooting

- **JTAG transfer times out on the relocation lesson:** use the practice runner.
  Its ELF-segment loader skips the flat binary's unused 1 MiB gap and verifies
  each actual segment at its physical load address. Loading data at its runtime
  address would bypass the relocation exercise.
- **Simics shows the correct guest output but the checker rejects it:** use the
  current runner, which handles the boot prompt sharing the first lab line.
- **Simics UART input gets out of step:** its console maps LF to CR. The runner
  translates the CRLF input case to one simulated newline while preserving the
  raw CRLF test on QEMU and physical UART.
- **BL31 write fails while the application loads:** inspect debug AP security
  attributes and the matching BL2 firewall configuration. The secure readback
  requirement remains mandatory before execution.
- **Timer stalls:** verify the platform GIC addresses, GIC-600 redistributor power
  handshake and secure FIQ routing. A timer status bit alone does not establish
  exception delivery.
- **A rebuilt or queued image has a hash mismatch:** freeze a fresh artifact
  directory and rerun. A historical PASS cannot qualify changed binaries.

Full terminal output, source/ELF hashes, negative controls and restoration logs
are in the [cross-platform evidence bundle](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/cross-platform).
