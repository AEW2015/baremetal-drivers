# 2. Set up VS Code

## Open the workspace where the tools live

Install [Visual Studio Code](https://code.visualstudio.com/download) and the
Microsoft **C/C++** extension (`ms-vscode.cpptools`). The supplied workspace
recommends it along with CMake Tools.

For native Linux development, start from the shell in which the compiler works:

```sh
cd baremetal-drivers/examples/agilex5-modular
code agilex5-modular.code-workspace
```

For the existing container:

1. Install **Dev Containers** (`ms-vscode-remote.remote-containers`) in desktop VS Code.
2. Use the Command Palette's **Dev Containers: Attach to Running Container** and select `agilex-xrdp`.
3. Use `dev` as the remote user in the attached-container configuration and reconnect if needed.
4. Open the cloned repository's `examples/agilex5-modular` directory inside the container.
5. Open `agilex5-modular.code-workspace`, and install C/C++ in the container when prompted.

The repository must be in a host bind mount for host-side UART automation. On
the established bench the clone is under `/home/dev` in the container. Inspect
`docker inspect agilex-xrdp` on the host to find the corresponding host directory;
a repository cloned into an unmounted container-only directory will not suffice.
See [VS Code's attach-container instructions](https://code.visualstudio.com/docs/devcontainers/attach-container).

## Check the integrated terminal

```sh
pwd
command -v aarch64-none-elf-gcc
command -v gdb-multiarch
command -v qemu-system-aarch64
```

The workspace folder is the example directory, not the repository root. It has
`core/`, `qemu/`, `bootstrap/` and `build_all.sh` directly underneath it.
The configurations use `/usr/bin/gdb-multiarch`; change `miDebuggerPath` if your
GDB is installed elsewhere.

## Supplied tasks and launch configurations

Use **Terminal → Run Task**:

| Task | Result |
|---|---|
| Build QEMU | `build/qemu/hello.elf` |
| Run QEMU checks | Console PASS checks and a process exit code |
| Build HPS core | `build/core_examples.elf` |
| Build all board examples | Full vendor/local compilation |

The **Run and Debug** selector has two configurations:

- **QEMU: AArch64 hello (no board)** builds the ELF, starts a paused emulator,
  connects GDB on loopback port 3338 and stops at `main`.
- **Hardware: HPS core (initialize DDR first)** builds the core ELF, starts
  OpenOCD on loopback port 3337, loads the image, sets its entry PC and breaks at
  `example_main`. Follow the [hardware prerequisites](hardware.md) first.

Use the C/C++ debugger's source breakpoints, **Step Over** (F10), **Step Into**
(F11), **Continue** (F5), Variables, Watch and Memory views. Register inspection
is also available through the Debug Console, for example
`-exec info registers pc sp cpsr`.
The configuration format follows the [C/C++ launch reference](https://code.visualstudio.com/docs/cpp/launch-json-reference).

The workspace is a starting configuration for the documented environment. The
underlying GDB operations are checked separately; automated validation does not
claim that a desktop F5 session was exercised.

Next: [run and debug QEMU](qemu.md).
