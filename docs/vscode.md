# 2. Set up VS Code

## Open the workspace where the tools live

Install [Visual Studio Code](https://code.visualstudio.com/download) and the
Microsoft **C/C++** extension (`ms-vscode.cpptools`). The supplied workspace
recommends it along with CMake Tools.

For native Linux development, start from the shell in which the compiler works:

```sh
source "$HOME/.config/agilex5/learning.env"
code "$AGILEX_EXAMPLES/agilex5-modular.code-workspace"
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

Do not repeat a relative `cd baremetal-drivers/...` if the previous chapter already left you in the example directory. The saved absolute path above works from any directory.

Use **Terminal → Run Task**:

| Task | Result |
|---|---|
| Check QEMU setup | Tool/path diagnostics in this environment |
| Build QEMU | `build/qemu/hello.elf` |
| Run QEMU checks | Console PASS checks and a process exit code |
| Build HPS core | `build/core_examples.elf` |
| Build all board examples | Full vendor/local compilation |

The **Run and Debug** selector has two configurations:

- **QEMU: AArch64 hello (no board)** checks the environment, builds the ELF, starts a paused emulator,
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

## First-debug checklist

1. Open `qemu/hello.c` and put a breakpoint at the beginning of `qemu_done`.
2. Select **QEMU: AArch64 hello (no board)** and press F5. The first stop should show `main` in **Run and Debug → Call Stack**.
3. Expand **Variables** to inspect the current scope. Under **Watch**, press **+** and add `failures`, `vector_result`, `source[511]` and `destination[511]`.
4. Press Continue to reach `qemu_done`. Expect `status=0`, `failures=0`, vector `{11,22,33,44}`, and matching source/destination words.
5. Continue again to let semihosting exit. Use **Stop Debugging** to close a session early, then rerun for a fresh emulator.

Build and check tasks print to the **Terminal** panel. For an F5 session, inspect
**Debug Console** and the C/C++ output channel for debugger/server diagnostics;
the extension's presentation can vary. If UART output is not shown clearly, use
the explicit terminal commands in the [QEMU chapter](qemu.md). Physical HPS UART
output is read on the **Linux host**, not from the container debugger console.

A breakpoint stop is not program completion. Continue deliberately before
judging output, and close your own session before using a port again. The
[troubleshooting guide](troubleshooting.md) has checks for occupied ports, missing
tools, optimized-out variables and wrong workspace roots.
