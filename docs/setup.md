# 1. Install the tools

## Choose where the tools run

Use the existing `agilex-xrdp` container when working on the established bench.
It already has Arm GNU 13.2.Rel1, Quartus 26.1.1 and the Quartus OpenOCD build.
The container image is a local development asset, not a public Docker Hub image.

For a new machine, the compiler/QEMU portion can run directly on Ubuntu without
Quartus or a kit. Hardware work additionally needs your licensed Quartus
installation, USB/JTAG access, a suitable OpenOCD and a matching FPGA design.

| Tool | Purpose | Needed for QEMU? |
|---|---|---|
| `aarch64-none-elf-gcc`, binutils | Compile and inspect bare-metal ELFs | Yes |
| `gdb-multiarch` | Source debugging from the CLI or VS Code | For debugging |
| `qemu-system-aarch64` | Emulate the tutorial's generic board | Yes |
| CMake, Ninja, make, git | Build upstream drivers and board adapters | For the full pack |
| Quartus `quartus_pfg`, `quartus_pgm`, `jtagconfig` | Package and load hardware images | No |
| Quartus OpenOCD with `aji_client` and ADIv6 | HPS JTAG/GDB server | No |

## Existing container

Run these commands on the **Linux host**:

```sh
docker ps --filter name=agilex-xrdp
docker exec -u root agilex-xrdp bash -lc \
  'apt-get update && apt-get install -y --no-install-recommends qemu-system-arm gdb-multiarch'
docker exec -it -u dev agilex-xrdp bash -l
```

Inside the container, confirm the tool versions:

```sh
source /etc/profile.d/baremetal-tools.sh
aarch64-none-elf-gcc --version
gdb-multiarch --version
qemu-system-aarch64 --version
```

Installation changes the running container. Add the same packages to your own
container definition if you recreate it later. Tutorial checks used QEMU 8.2.2
and GDB 15.1; record your versions when reporting a problem.

## Fresh Ubuntu compiler/QEMU environment

Run on the Linux machine **where you will compile and run QEMU**:

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
aarch64-none-elf-gcc --version
```

Use the x86-64 **AArch64 bare-metal** toolchain, rather than an Arm 32-bit compiler.
The pinned version follows the [Altera compiler setup](https://altera-fpga.github.io/rel-25.1/baremetal-embedded/agilex-5/e-series/premium/ug-baremetal-agx5e-premium/).
Keep this PATH in your development shell or shell profile, then start VS Code
from that shell so its compiler and tasks see the same environment.

## Clone and build

In the development environment (the container for the established bench):

```sh
git clone https://github.com/AEW2015/baremetal-drivers.git
cd baremetal-drivers/examples/agilex5-modular
./qemu/build.sh
python3 qemu/run.py --check
```

You should see `PASS EL3`, `PASS NEON: 11 22 33 44`,
`PASS MEMORY: 4096-byte CPU copy`, and `QEMU EXAMPLE COMPLETE`.
The process exits with status zero through semihosting.

Build the board examples separately:

```sh
./build_all.sh
./bootstrap/ocram/build_uart.sh
```

The full build fetches the upstream CMake dependencies on first use. This
**compiles** the original simulation references and the board adaptations; it
does not run all the original Simics tests on the kit. See the
[pack README](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/README.md)
for cached-dependency options and individual build scripts.

Next: [set up VS Code](vscode.md).
