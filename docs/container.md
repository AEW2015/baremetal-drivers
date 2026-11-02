# Recreate the Linux development container

The [public source recipe](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/container)
supports a learning image based on Ubuntu 24.04 and a hardware image based on
a user-supplied **apt-based** Quartus 26.3 installation image. Both install the SHA-256-verified
Arm GNU 13.2.Rel1 archive, QEMU, GDB, Verilator, Icarus and U-Boot build dependencies
(including `bc`, `bison`, `flex`, `libssl-dev`, Python `pyelftools`, and device-tree
compiler). The learning build needs no Quartus bundle or license. The hardware build
requires your own installed Quartus base; credentials remain outside image layers. FPGA compilation still requires your own applicable license.

The recipe targets an x86-64 Linux host because the pinned Arm archive is
x86-64. The default learning image does not install Quartus or Simics. The
hardware variant selects your installed Quartus distribution image; Simics is a
separate, user-installed licensed product. Supply installations and licenses
through your own environment, never by baking credentials into this image.

The [physical partial-reconfiguration lab](partial-reconfiguration.md) was built
and tested with **Quartus 26.3 Build 114**. Use that matching tool release for its
FPGA images and the current HPS 14.1 / EMIF 5.1 sources. See the
[26.3 stack migration](stack-26.3.md).
The public learning image runs the PR C-driver/RTL checks without Quartus.

## Portable entry point

The [quickstart](quickstart.md) runs the learning recipe from Linux or PowerShell:
`python3 lab.py image` followed by `python3 lab.py qemu` (`py -3` on Windows).
The launcher derives the host mount path and maps it at `/work`. It does not
require a particular clone name or a pre-existing container. For vendor Windows
Server and Simics routes, see [host OS support](host-support.md).

The low-level Linux commands below remain available for users building and
managing their own named tool container. On RHEL/SUSE hosts, use an appropriate
container engine installation rather than the Ubuntu host package commands.

## Clone on the x86-64 Linux host

Prerequisites are working Docker, network access and disk space. The complete
Quartus base is substantially larger than the learning image. Accept applicable
vendor tool terms; this repository does not supply tool licenses.

```sh
mkdir -p "$HOME/agilex-lab"
cd "$HOME/agilex-lab"
git clone https://github.com/AEW2015/baremetal-drivers.git
cd baremetal-drivers
```

Clone on the host first so both the container and host UART runner see the same
files. Existing students should use their existing clone instead.

## Build one image

=== "QEMU / no board"

    From the repository root on the host:

    ```sh
    docker build --build-arg USER_UID="$(id -u)" --build-arg USER_GID="$(id -g)" \
      -t agilex-learning:13.2 examples/agilex5-modular/container
    ```

    This image needs no Quartus, board or USB devices.

=== "Hardware tools"

    Use your local Quartus 26.3 base image. On the established bench it is
    `altera-agilex-dev:26.3`; substitute your own installed image elsewhere:

    ```sh
    docker build --build-arg USER_UID="$(id -u)" --build-arg USER_GID="$(id -g)" \
      --build-arg BASE_IMAGE=altera-agilex-dev:26.3 \
      -t agilex-hardware:26.3-reference examples/agilex5-modular/container
    ```

    Complete any registry authentication/terms acceptance required by the image
    provider. This is a tool distribution; it contains no qualified Modular SOF.

The compiler and hardware base are pinned. Distribution package updates mean
rebuilds are not a promise of byte-for-byte identical images. Record your image
ID and tool versions with the run evidence.

The `agilex-hardware:26.3-reference` variant was built locally and smoke-checked
with Quartus 26.3 Build 114, its vendor OpenOCD, Arm GNU 13.2.Rel1, QEMU 8.2.2
and Verilator 5.020. `xvfb` and `xauth` support headless GUI tool operations.
The public registry had no `alterafpga/quartus-pro:26.3-all` tag at verification;
this recipe does not claim that a local base image is publicly downloadable.
The earlier pinned public 26.1.1 build remains historical evidence in
[the previous container report](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/container/evidence.json).

A tool smoke check does not qualify USB permissions or an FPGA design. Supply
your own applicable license and matching Modular hardware project.

## Start the learning container

From the **repository root on the host**:

```sh
docker run -d --name agilex-learning \
  --mount type=bind,src="$PWD",dst=/home/dev/baremetal-drivers \
  agilex-learning:13.2
docker exec -it -u dev agilex-learning bash
```

Inside the **container**:

```sh
cd /home/dev/baremetal-drivers/examples/agilex5-modular
python3 doctor.py --target qemu
./qemu/build.sh
python3 qemu/run.py --check
```

For a broader board-free validation, run the repository's one-command check
from the same directory:

```sh
bash container/check-learning.sh
```

It builds and runs the hello mutation/recovery exercise, QEMU practice labs
with negative and GDB checks, QEMU-only DSU/DDR/SMMU suites, and both Verilator
fabric test suites. It does not build Agilex-target images, compile Quartus
projects, or access a board. Commands and per-step logs are saved under a new
`runs/learning-check-*` directory in the clone.

Require PASS tools and `PASS QEMU_CHECK`; an unbuilt ELF initially warns.
Continue to [VS Code](vscode.md) and attach to the actual container name.
XRDP is optional: desktop VS Code can use Dev Containers.

## Start the hardware container

On the host, choose a single JTAG owner. Start with the hardware image and USB
bus access:

```sh
docker run -d --name agilex-hardware \
  --mount type=bind,src="$PWD",dst=/home/dev/baremetal-drivers \
  --mount type=bind,src=/dev/bus/usb,dst=/dev/bus/usb \
  --device-cgroup-rule='c 189:* rmw' \
  --env LM_LICENSE_FILE \
  agilex-hardware:26.3-reference
```

`LM_LICENSE_FILE`, if needed, comes from your host shell and names your own
license server. For a local license file, add an explicit read-only file mount
and use its container path instead. Never copy licenses into image layers.
Host USB permissions still apply: install the appropriate vendor udev rules
or add the actual device group with `--group-add` as your host requires. A
cgroup rule alone does not grant Unix file access. Confirm `jtagconfig` inside
this container sees the intended Modular carrier before programming.

Host UART capture uses the host by-path device; serial-node mounts inside the
container are unnecessary. On the **host**, configure:

```sh
export AGILEX_CONTAINER=agilex-hardware
export AGILEX_CONTAINER_USER=dev
export AGILEX_CONTAINER_ROOT=/home/dev/baremetal-drivers/examples/agilex5-modular
export AGILEX_UART=/dev/serial/by-path/YOUR-VERIFIED-SOM-J2
cd examples/agilex5-modular
export AGILEX_BOOTSTRAP_DIR="$PWD/build/boot"
export AGILEX_MCP_CLIENT="$PWD/mcp_client.py"
python3 doctor.py --target hardware
```

Fix all FAIL items. You still need [matching FPGA artifacts](fpga-design.md)
before DDR initialization; a tool image does not establish board compatibility.

## Ethernet access

For the [Ethernet bandwidth lab](examples/ethernet.md), add these options to the
hardware container's `docker run` command:

```sh
--network host --cap-add NET_ADMIN
```

Create the container with those options before starting the lab. The runner
checks that host and container share the network namespace, then uses
`docker exec -u root` and `ip` to add and remove a temporary address on the
explicitly selected wired NIC. A bridge-network container cannot configure
that host NIC. Keep your Internet connection on a separate interface.

The peer and UART runner execute on the Linux host. They need Python 3 and
`ping` (`sudo apt-get install python3 iputils-ping` on Ubuntu); `ethtool` is
useful for checking negotiated link speed. No iperf installation is required.

## Persistent host/container map

```text
Linux host                                      Development container
$HOME/agilex-lab/baremetal-drivers  ──bind mount──▶ /home/dev/baremetal-drivers
  ├─ host Python: run_suite.py                       ├─ compiler, QEMU, GDB
  ├─ SOM J2 UART capture                             ├─ Quartus/OpenOCD (hardware image)
  └─ evidence files ◀──────────same files─────────────┘
/dev/bus/usb                     ──USB bind───────▶ JTAG access (hardware image)
/dev/serial/by-path/...          stays on host     no competing UART reader
```

| Purpose | Host | Container |
|---|---|---|
| Example directory | `$HOME/agilex-lab/baremetal-drivers/examples/agilex5-modular` | `/home/dev/baremetal-drivers/examples/agilex5-modular` |
| Tools | Docker CLI, host Python automation | Compiler, QEMU, GDB; Quartus/OpenOCD in hardware image |
| UART | Verified SOM J2 by-path device | Not used for automated capture |
| JTAG | Device permissions and USB mapping | `jtagconfig`, programmer and OpenOCD |
| Evidence | Host clone's `runs/` | Same files through the bind mount |

Persist host exports with `env-hardware.sh.example` and the development location
with `env-learning.sh.example`. Hardware doctor verifies the same mount using a
nonce, compares artifact hashes and checks UART/JTAG identity. Keep that check
when paths look similar. Use your actual paths if you changed the layout above.
