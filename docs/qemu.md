# 3. Run and debug QEMU

## Run the exercise

From the example directory, in the compiler environment:

```sh
./qemu/build.sh
python3 qemu/run.py --check
```

Expected output:

```text
QEMU VIRT AARCH64 BEGIN
PASS EL3
PASS NEON: 11 22 33 44
PASS MEMORY: 4096-byte CPU copy
QEMU EXAMPLE COMPLETE
```

This runs a freestanding ELF using QEMU's software CPU emulator (TCG), so no
KVM device or physical ARM CPU is required. Semihosting reports the program's
success/failure status to QEMU and exits. No guest Linux image is involved.

## Break and inspect in VS Code

1. Open `qemu/hello.c` and set a breakpoint at `qemu_done`.
2. Select **QEMU: AArch64 hello (no board)** and press F5.
3. At `main`, inspect the call stack and step over the first output/check.
4. Continue to `qemu_done`.
5. Add `failures`, `vector_result`, `source[511]` and `destination[511]` to Watch.

At the final breakpoint, `status` and `failures` should both be zero,
`vector_result` should be `{11, 22, 33, 44}`, and the source/destination words
should match. Continue to let semihosting terminate the exercise. Restart the
debug configuration for a fresh run; it creates a new emulator process.

## Try the same workflow in GDB

In one development terminal:

```sh
python3 qemu/run.py --debug
```

Wait for `QEMU GDB ready on 127.0.0.1:3338`. In another terminal in the same
container or native environment:

```sh
gdb-multiarch build/qemu/hello.elf
```

Then enter:

```gdb
set architecture aarch64
target remote 127.0.0.1:3338
hbreak main
continue
info line
stepi
hbreak qemu_done
continue
print failures
print vector_result
print source[511] == destination[511]
detach
quit
```

The last expression should print `1`. This sequence was checked with the pinned
Arm compiler, QEMU 8.2.2 and GDB 15.1. QEMU's
[GDB documentation](https://www.qemu.org/docs/master/system/gdb.html) explains the
remote stub and paused-start behavior.

## Understand what changes on hardware

| Detail | QEMU exercise | Modular kit |
|---|---|---|
| CPU | One Cortex-A53 model | Two A55 and two A76 cores |
| Code entry | `0x40200000` | Core example `0x82100000` |
| UART | PL011 at `0x09000000` | HPS UART0 at `0x10c02000` |
| Memory setup | QEMU supplies RAM | Matching ATF/handoff initializes DDR |
| Completion | Semihosted process exit | UART markers and debugger checks |
| Debug connection | QEMU GDB stub | Quartus OpenOCD via JTAG |

The ELF is placed above the QEMU device-tree region, and the linker reserves a
stack at `0x41000000`. The example's EL3 startup enables FP/SIMD and clears BSS.
Do not reuse these addresses or its UART driver on the physical SOM.

See [the QEMU sources](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/qemu)
and [QEMU's generic platform documentation](https://www.qemu.org/docs/master/system/arm/virt.html).

Next: [run on the Modular kit](hardware.md).
