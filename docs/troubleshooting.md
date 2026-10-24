# Troubleshooting

Start in the environment that runs the failing command. Compiler/QEMU/GDB checks
belong in the native Ubuntu or attached-container terminal; USB capture and board
runners belong on the Linux host. Preserve the first error and the run directory.
Do not repeatedly program the board to diagnose a missing compiler or wrong path.

## First checks

In the **development environment**:

```sh
source "$HOME/.config/agilex5/learning.env"
cd "$AGILEX_EXAMPLES"
python3 doctor.py --target qemu
./qemu/build.sh
python3 qemu/run.py --check
```

Recovery means all doctor requirements pass (an unbuilt ELF initially warns),
followed by `PASS QEMU_CHECK` and exit status zero. For the **host hardware**
track, source `~/.config/agilex5/hardware.env`, change to the host example
directory, and run `python3 doctor.py --target hardware`. This checks access,
mount identity, hashes, tools, JTAG identity and ports without programming or
reading UART bytes. Read warnings as well as the final status.

## Compiler, source paths or VS Code tasks fail

**Symptoms:** command not found, missing ELF, source lookup failure, or F5 fails
before connecting. In the terminal where the task runs, inspect:

```sh
pwd
uname -m
command -v aarch64-none-elf-gcc
command -v qemu-system-aarch64
command -v gdb-multiarch
```

Source the learning environment in every new terminal. Host installations are
separate from container installations. Open the supplied `.code-workspace`
rooted at `examples/agilex5-modular`; launch native VS Code from the configured
shell. The downloadable toolchain in the tutorial is for x86-64 Linux. An ARM
host needs an archive built for that host, not the x86-64 executable. Use
`gdb-multiarch` if the toolchain's GDB needs unavailable host libraries.

**Recovery check:** the doctor reports compiler/QEMU/GDB versions, then the
build creates `build/qemu/hello.elf`. In VS Code run **Check QEMU setup**, then
**Run QEMU checks**. F5 performs the setup check and build before launching.

## Docker unavailable or the wrong checkout is mounted

**Symptoms:** Docker permission/connection errors, missing container files, or
“mapping is not verified.” On the host:

```sh
docker ps -a --format 'table {{.Names}}\t{{.Status}}'
docker inspect agilex-xrdp --format '{{json .Mounts}}'
printf '%s\n' "$AGILEX_CONTAINER" "$AGILEX_CONTAINER_ROOT"
```

Start your intended existing container if stopped. Resolve Docker access using
your host's administrator policy. Identify a bind mount containing the clone;
set `AGILEX_CONTAINER_ROOT` to this exact clone's container path. Equal-looking
paths in two independent clones are insufficient. Do not copy files into an
unmounted container directory to silence this check.

**Recovery check:** host hardware doctor passes **same bind-mounted checkout**
and **core/image hashes**. Rebuild stale artifacts in that same checkout. A
hash-change error during a run means the ELF changed after preflight: stop other
builds, rebuild once, then start a new run. Keep the failed run's evidence.

## QEMU

**Symptoms:** missing emulator/ELF, silence, timeout or an incomplete PASS list.
Run `python3 qemu/run.py --check`; errors identify missing tools/files and retain
partial emulator output. A zero emulator exit alone is insufficient: the runner
requires every expected marker. Timeout uses a bounded child process and returns
failure. Read the preceding emulator diagnostic before changing timeout limits.

With `--debug`, silence before GDB continues is expected. Wait for
`QEMU GDB ready on 127.0.0.1:3338`, connect, set `hbreak main`, then `continue`.
At `qemu_done`, expect `failures=0`, vector `{11,22,33,44}` and matching copied
words. A deliberate NEON failure should still report PASS for an intact memory
copy and overall failure. Restore your edit and rebuild before the next lesson.

Use the supplied runner: its `virt` settings, EL3 startup, PL011 UART, ELF address
and semihosted exit belong together. Physical-HPS ELFs use different MMIO and
cannot run unchanged here. See the [QEMU lesson](qemu.md).

## Debugger port already in use or F5 attaches incorrectly

QEMU uses port 3338 in the development environment. OpenOCD uses 3337, 6677 and
4457 in the container. Inspect listeners **there**, not in a different network
namespace:

```sh
ss -ltnp | rg ':(3338|3337|6677|4457)\b'
```

Stop your own previous VS Code debug session or emulator and inspect again.
Never kill all OpenOCD, Quartus or Python processes: another board may be active.
The QEMU runner now reserves its own listening socket before launching, so an
occupied listener produces failure instead of a false READY message.

**Recovery check:** the listener is free before launch; one new debug session
reaches the expected source breakpoint and variables. Terminal shows build/task
output; Debug Console is for GDB commands. Program output routing can vary with
the C/C++ extension; use the CLI QEMU lesson when you need an unambiguous console.
Optimized hardware variables may be unavailable: inspect registers/disassembly
and step instructions. The QEMU exercise uses `-Og -g3`.

## Hardware busy or cancellation cannot be verified

The suite, standalone DDR initializer and supplied debug server share
`hardware.lock` within one checkout. Stop that checkout's current debug session
and UART reader, then retry. **Do not delete the lockfile**: a replacement inode
would bypass the existing lock. Separate checkouts and arbitrary tools still
require a common board owner; this lock cannot coordinate them.

`AGILEX_LOCK_FD` is internal inherited state. If you manually exported it in a
shell, `unset AGILEX_LOCK_FD` there; do not change it inside a running suite.

If shutdown is unverified, the runner preserves an `.agilex-process-*` ownership
record and skips further programming. Inspect the PID/token record and actual
container process with your bench owner. Do not delete it as a remedy. Automatic
cleanup targets only the recorded PID whose environment proves ownership;
Docker/USB failure can still require manual investigation. Continue only after
the old operation is confirmed stopped, the lock is released and hardware doctor
passes. No process-killing wildcard is a recovery procedure.

## UART absent, permission denied or no fresh output

On the **host**:

```sh
ls -l /dev/serial/by-path/
id
ls -l "$AGILEX_UART"
fuser "$AGILEX_UART"
```

Identify the separate **SOM J2 HPS_UART**, not merely the carrier's FTDI/JTAG
hub. Reconnect that cable and compare enumeration if necessary. The tested SOM
used FT4232H channel C, 115200 8N1, no flow control. Use the verified persistent
by-path device; USB topology is specific to your PC. An ordinary file or
`/dev/null` is rejected as a UART. Resolve serial group/access permissions using
your host's policy; a new group membership requires a new login session.

Close your own serial terminal before automated capture; two readers consume
each other's bytes. Host capture avoids stale container serial nodes after
hotplug. Old DDR Hello output does not prove the newly loaded application ran.

**Recovery check:** hardware doctor passes UART access, then a new core run
contains `HPS CORE EXAMPLES BEGIN`, every required core marker and COMPLETE.
Manual debug requires deliberate continue; disconnect alone is not completion.

## JTAG identity, image packaging or DDR initialization fails

Inspect `docker exec -u dev agilex-xrdp jtagconfig`. The runner requires the
Modular carrier as cable 1 and FPGA ID `0364F0DD`, and derives FPGA position from
the current chain. Never choose another board to bypass this guard. The Quartus
OpenOCD build must support `aji_client`/ADIv6; distribution OpenOCD may not.

A new learner needs the instructor's matching **Modular** SOF, handoff and
artifact provenance/checksums. The Premium kit image is not interchangeable.
After a power cycle or different fabric design, choose the matching merged
image **before** the first test:

```sh
python3 run_suite.py --only core --full-recovery
```

This replaces volatile fabric/HPS state. An HPS-enabled raw SOF without its
bootloader can be rejected as incomplete. If the FPGA owner has not provided a
matching design, stop here; installing C tools cannot reconstruct it.

Bootstrap takes minutes. Follow the stage's printed path using `tail -f` in a
second host terminal. Require four DDR patterns, payload readback and a PC in the
DDR payload. The 64 MiB scratch check does not qualify all 8 GiB; the configured
2 GiB/detected 8 GiB warning remains applicable.

An earlier wrong pinmux selector stalled HPS clocking; a physical power cycle
and corrected matching image recovered it. IOA9/10 selectors are **0 I3C1,
4 I2C_EMAC1, 8 GPIO, 9 HCLK** in the authoritative Quartus table. Do not infer
values from dropdown order or apply that incident as a fix for every failure.
See the [recorded porting lesson](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/PORTING.md).

## A test fails, or DDR restoration fails

Open the printed `runs/<timestamp>/results.json`, the selected test's UART/debug
logs, its bootstrap log and `restore.log`. The original test error and
`restoration_error` are separate; a successful restoration does not turn a
failed example into PASS. Restoration is recorded as pass, fail or error even
when it times out. Preserve the entire directory before another attempt.

If restoration is fail/error, stop debugging. Confirm no owned process or UART
reader remains, run hardware doctor, resolve the first error, then run the
standalone DDR initializer from the host (use `--full-recovery` only when its
matching design is needed). Require fresh patterns, Hello and PC proof before
loading another ELF. If process cancellation is uncertain, resolve that first;
do not start a competing initializer.

## PASS does not establish external-device operation

Read the [scope table](examples.md). An ID read does not establish USB
enumeration, Ethernet traffic, SD reads, SMMU translation or ECC recovery.
Preserve warnings and failing runs instead of changing expected values solely
to produce PASS. For a new chip revision, decode documented ID fields first.

## Custom fabric IP or PR fails

Check the [fabric register/map/deployment checkpoints](fabric-ip.md#troubleshooting-checkpoints)
and [PR swap diagnostics](partial-reconfiguration.md#troubleshoot-the-swap).
The standard DDR hook branches before normal bridge enable; a fabric build must
explicitly select `AGILEX_ENABLE_LWH2F=1`. A CPU poll timeout cannot recover a
stalled bus transaction. Never feed a persona RBF into the full-image or HPS-only
loader, and retain PR isolation after controller errors.
