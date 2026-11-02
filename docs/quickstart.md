# Portable quickstart

The same repository entry point works from supported Windows and Linux hosts.
See [vendor OS support and execution routes](host-support.md) before installing
Quartus or Simics. Run these commands from the clone's root; no personal bench
paths or globally installed agent skills are required. Install Git, Python 3.10+
and a configured Linux-container engine for the container route. Native mode
requires the compiler/emulator on PATH instead.

=== "Linux / Bash"

    ```sh
    git clone https://github.com/AEW2015/baremetal-drivers.git
    cd baremetal-drivers
    python3 lab.py image
    python3 lab.py qemu
    ```

=== "Windows / PowerShell"

    With a configured Linux-container engine:

    ```powershell
    git clone https://github.com/AEW2015/baremetal-drivers.git
    cd baremetal-drivers
    py -3 lab.py image
    py -3 lab.py qemu
    ```

=== "Installed Linux or WSL tools"

    With the compiler and QEMU already on PATH:

    ```sh
    git clone https://github.com/AEW2015/baremetal-drivers.git
    cd baremetal-drivers
    python3 lab.py --backend native configure
    python3 lab.py qemu
    ```

The container route builds the public learning recipe, bind-mounts the actual
clone at `/work` and runs the lesson. It does not require Quartus, a board,
Simics or a pre-existing named container. Native mode uses installed tools;
[setup](setup.md) lists the Ubuntu learning packages and compiler installation.
Other supported Linux hosts can use the same learning container rather than
copying Ubuntu package commands into a different distribution.

Expected final lines:

```text
PASS EL3
PASS NEON: 11 22 33 44
PASS MEMORY: 4096-byte CPU copy
QEMU EXAMPLE COMPLETE
PASS QEMU_CHECK: all required markers and exit status zero
```

Try the deliberate failure/recovery exercise:

```sh
python3 lab.py qemu --experiment
```

Use the same Python spelling as your host (`py -3` in PowerShell, `python3` in
Linux/WSL). A successful experiment observes expected failures and exits zero.
`python3 lab.py --dry-run qemu` prints the commands without running them;
`python3 lab.py paths` shows paths derived from this clone.

## Continue in the HTML lab

1. [Hello on QEMU, Simics and hardware](hello-world.md).
2. [VS Code and the GDB walkthrough](vscode.md).
3. [Find an example](example-finder.md), including full passes on **both Simics
   and hardware**, then open its [clickable block diagram](architecture.md).
4. [Prepare the hardware inputs](hardware-inputs.md) before programming.

[Portable workflow validation](portable-validation.md) records the actual
QEMU, Simics, physical Hello and PR checks, with their limits.

The [lab-ready GitHub release](https://github.com/AEW2015/baremetal-drivers/releases/tag/lab-ready)
is a **movable reference tag**. Its release notes identify the actual commit,
checks and limitations. Main remains editable; there is no separate freeze or
presentation-material tree. For an exact repeat, record the commit shown in the
release rather than assuming the moving tag stays at the same revision.
