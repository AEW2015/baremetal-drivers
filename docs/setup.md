# 1. Install the tools

## Choose a track before you begin

| Track | You need | First success checkpoint |
|---|---|---|
| **No board / QEMU** | An x86-64 Linux development environment | QEMU prints its PASS lines and exits zero |
| **Physical Modular kit** | The learning tools plus the kit, Quartus/JTAG access, mounted source and a matching FPGA image | Hardware doctor passes, then fresh DDR Hello and core PASS results |

This walkthrough uses Ubuntu 24.04 on **x86-64**. Check `uname -m` before
installing the compiler below. An ARM64 host needs a compiler archive built for
that host; an x86-64 download can fail with `Exec format error` there. Native
Windows/macOS USB/JTAG flows are not validated by this tutorial. Desktop VS Code
can instead connect to the documented Linux environment.

!!! info "Hardware instructor prerequisite"
    Cloning this repository does not provide a board-specific FPGA design.
    Before hardware work, obtain the matching Modular ES SOF/handoff, its
    provenance/checksum and the expected board/DDR configuration from the FPGA
    project or instructor. See [FPGA design onboarding](fpga-design.md) for the exact reference, recorded
    pair checker and remaining new-kit qualification gap. If these are not available, complete the QEMU track
    first. The Premium kit image is not interchangeable.

## Option A: development container

A public-source [container recipe](container.md) now supports a new Linux
machine: use its learning image for QEMU or its Quartus-based image for hardware.
The existing XRDP container below remains an alternative for this bench.

### Use the existing bench container

The established `agilex-xrdp` container has Arm GNU 13.2.Rel1, Quartus 26.1.1
and Quartus OpenOCD. Its image is a local bench asset, not a public Docker Hub
image. On the **Linux host**, first inspect the container and bind mounts:

```sh
docker ps --filter name=agilex-xrdp
docker inspect --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' agilex-xrdp
```

For example, `/host/agilex-home -> /home/dev` means a clone under
`/home/dev/src` inside the container is also available under
`/host/agilex-home/src` on the host. Choose a writable bind mount before cloning.
A container-only directory will compile, but the host hardware runner cannot use
it. On the established bench `/home/dev` is the shared mount; verify your own
output rather than assuming it.

Install emulator/debugger packages in the **running container**, then enter it:

```sh
docker exec -u root agilex-xrdp bash -lc \
  'apt-get update && apt-get install -y --no-install-recommends qemu-system-arm gdb-multiarch'
docker exec -it -u dev agilex-xrdp bash -l
```

Add those packages to your own container definition if you recreate it later.
Installing a tool on the host does not install it in the attached container.

## Option B: fresh native Ubuntu compiler/QEMU environment

Skip this section if using the existing compiler container. On the **native
Linux development machine**:

```sh
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build git curl xz-utils \
  ca-certificates python3 python3-venv qemu-system-arm gdb-multiarch \
  device-tree-compiler
mkdir -p "$HOME/tools"
cd "$HOME/tools"
curl -fL \
  https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-x86_64-aarch64-none-elf.tar.xz \
  -o arm-gnu-13.2.tar.xz
tar -xf arm-gnu-13.2.tar.xz
export PATH="$HOME/tools/arm-gnu-toolchain-13.2.Rel1-x86_64-aarch64-none-elf/bin:$PATH"
export CROSS_COMPILE=aarch64-none-elf-
```

Use the AArch64 **bare-metal** toolchain, not an Arm 32-bit compiler. The version
follows the [Altera compiler setup](https://altera-fpga.github.io/rel-25.1/baremetal-embedded/agilex-5/e-series/premium/ug-baremetal-agx5e-premium/).
Hardware work additionally needs your licensed Quartus installation and the
adapter/DAP-capable OpenOCD described in the [hardware chapter](hardware.md).

## Clone into a known location

In the **development environment** (native shell or container), choose a project
folder. For a container, this must be inside the bind mount verified above:

```sh
export AGILEX_PROJECTS="$HOME/src"
mkdir -p "$AGILEX_PROJECTS"
cd "$AGILEX_PROJECTS"
git clone https://github.com/AEW2015/baremetal-drivers.git
cd baremetal-drivers/examples/agilex5-modular
export AGILEX_EXAMPLES="$PWD"
pwd
```

Already have a clone? Skip `git clone`; change to its example directory and set
`AGILEX_EXAMPLES` to that absolute path. Do not clone a second copy by accident.
All subsequent commands use this example directory, whose children include
`qemu/`, `core/`, `doctor.py` and `build_all.sh`.

## Keep the environment across new terminals

From that **development** example directory:

```sh
mkdir -p "$HOME/.config/agilex5"
cp env-learning.sh.example "$HOME/.config/agilex5/learning.env"
printf '\nexport AGILEX_EXAMPLES=%q\n' "$PWD" >> "$HOME/.config/agilex5/learning.env"
source "$HOME/.config/agilex5/learning.env"
```

In **each new development terminal**, source that file and return to the saved
absolute path:

```sh
source "$HOME/.config/agilex5/learning.env"
cd "$AGILEX_EXAMPLES"
python3 doctor.py --target qemu
```

The doctor checks compiler, QEMU, GDB and the default debugger port without
starting an emulator or touching hardware. A missing ELF is a normal warning
before your first build. Fix any `FAIL` item in this same environment; the final
`NEXT` line tells you what to do. Use `--json` when attaching diagnostics to a
feedback report. The doctor does not install or change system packages.

## First no-board checkpoint

```sh
./qemu/build.sh
python3 qemu/run.py --check
```

Require `PASS EL3`, `PASS NEON: 11 22 33 44`,
`PASS MEMORY: 4096-byte CPU copy`, `QEMU EXAMPLE COMPLETE`, and
`PASS QEMU_CHECK: all required markers and exit status zero`.
The process should exit successfully; it does not stay silently running.

**No-board students can stop setup here and go directly to [VS Code](vscode.md).**
They do not need a kit, Quartus, a SOF or the full vendor reference build.

## Hardware track only: compile the hardware pack

For the hardware track, in the **development environment**:

```sh
./build_all.sh
./bootstrap/ocram/build_uart.sh
```

The full build fetches upstream CMake dependencies on first use and compiles the
simulation references plus board adaptations. It does not run the references on
the kit. OCRAM packaging calls Quartus only if `AGILEX_SOF` is supplied; compiling
its ELF alone does not initialize the board. See the
[pack README](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/README.md)
for cached-dependency and individual-build options.
