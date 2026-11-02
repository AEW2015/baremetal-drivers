# Hello World on QEMU, Simics and hardware

Start with [the portable quickstart](quickstart.md). All commands below start
from the repository root. `lab.py` finds this checkout using its own location;
there is no required clone name, personal home directory or external bench repo.
Use `py -3` in native PowerShell or `python3` in Linux/WSL. See
[host OS routes](host-support.md) for vendor support and execution requirements.

## Where the files are

| Relative to the repository | Purpose |
|---|---|
| `lab.py` | Cross-platform entry point |
| `examples/agilex5-modular/qemu/hello.c` | QEMU first lesson |
| `examples/hello/hello_selftest.c` | Shared Simics/hardware Hello command |
| `examples/agilex5-modular/simics/` | Current SDK build and Simics scripts |
| `examples/agilex5-modular/hardware-candidates/` | Physical-board Hello wrapper |
| `examples/agilex5-modular/build/local.json` | Ignored local configuration |
| `examples/agilex5-modular/build/boot/` | Generated DDR firmware and merged SOF |

## QEMU: no board needed

With a configured Linux-container engine on the host:

```sh
python3 lab.py image
python3 lab.py qemu
```

With native Linux/WSL tools already installed:

```sh
python3 lab.py --backend native configure
python3 lab.py qemu
```

Expected guest output and runner verdict:

```text
QEMU VIRT AARCH64 BEGIN
PASS EL3
PASS NEON: 11 22 33 44
PASS MEMORY: 4096-byte CPU copy
QEMU EXAMPLE COMPLETE
PASS QEMU_CHECK: all required markers and exit status zero
```

The runner exits 0. Next run `python3 lab.py qemu --experiment` for deliberate
corruption and recovery in scratch copies. The failed guests exit 1; the complete
experiment exits 0 when those failures and recovery are verified.
The [GDB lesson](qemu.md) uses `main` and `qemu_done`; keep the debugger inside
the same execution environment. For a named tool container, configure it and
attach VS Code as described in [the container guide](container.md).

## Simics: Agilex virtual HPS

Install the model using [the Simics guide](simics.md), in Linux/WSL or a tool
container. The vendor installer and model are separate downloads. Native route:

```sh
python3 lab.py --backend native configure
# SIMICS_FPGA_ROOT identifies the user's vendor installation, outside the repo.
python3 lab.py simics --setup
```

For a model already deployed under `examples/agilex5-modular/build/simics26`:

```sh
python3 lab.py simics
```

This builds the OCRAM console and runs `hello_selftest`. Captured guest output:

```text
SoCFPGA Bare-Metal > hello_selftest
Hello, Baremetal World!
```

Require `PASS hello` and exit zero, rather than the console's generic command
completion alone. [Captured Simics UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/stack-26.3-20261101/simics/upstream-console/hello/uart.txt).

## Hardware: qualify the inputs first

Follow [the hardware input checklist](hardware-inputs.md) to prepare the matching
Modular ES image, tool environment, UART and shared mutex. The public command is:

```sh
python3 lab.py hardware doctor
python3 lab.py hardware hello --build
```

Use the Linux execution host for the runner, including a configured WSL2 route
on Windows. The compiler/Quartus commands run in the configured native tools or
named container. No external `--bench` or `--mcp-client` path is required.

Captured physical output includes:

```text
CANDIDATE_BEGIN name=hello
CANDIDATE_EL=3 SCTLR=0x30C51838
PASS STANDALONE_EL3_MMU_DCACHE_OFF
CANDIDATE_COMMAND hello_selftest
Hello, Baremetal World!
CANDIDATE_COMPLETE status=0
```

Require both `hello: pass` and `DDR Hello restoration: pass`. Each bootstrap has
a 400-second bound; visible stages distinguish discovery, DDR checks, payload
loading and restoration. Read [the quiet-run troubleshooting note](troubleshooting.md#hardware-hello-appears-quiet-after-printing-its-evidence-directory)
before interrupting or starting a second board operator.

## Continue from the result

Use [the finder](example-finder.md) to select another verified lab and open its
source, expected output, execution evidence and [associated diagram](architecture.md).
The [coding standard](educational-coding-standard.md) explains how the first
lesson separates computation, independent checks and the final verdict.
