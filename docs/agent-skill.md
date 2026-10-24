# Use the Agilex 5 Codex skill

The repository now carries the
[agilex5-baremetal skill](https://github.com/AEW2015/baremetal-drivers/tree/main/skills/agilex5-baremetal),
including its instructions, UI metadata, hardware profile and recovery reference.
It adapts the original bench skill to this fork's actual paths and runners.
It helps a coding agent build, debug and assess these examples while preserving
the distinction between compilation, QEMU results and physical-board evidence.

## Install from your checkout

In a terminal with this repository checked out, start at the **repository root**:

```sh
skill_dir="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_dir"
if [ -e "$skill_dir/agilex5-baremetal" ]; then
    echo "Already installed: compare and back up the existing skill before updating."
else
    cp -R skills/agilex5-baremetal "$skill_dir/"
fi
```

Copy the whole folder so its `references/` and `agents/` resources stay together.
This leaves an existing installation untouched. For an update, review the diff
against `skills/agilex5-baremetal`, back up your local changes, and replace the
installed folder deliberately. Start a new Codex session after installation so
it can discover the skill. Installing a skill does not install the compiler,
QEMU, Quartus, repository checkout or FPGA images; follow [tool setup](setup.md)
and [FPGA onboarding](fpga-design.md) for those inputs.

## Give the agent a concrete task

Include the checkout's absolute path and the intended track. Examples:

```text
Use $agilex5-baremetal in /absolute/path/to/baremetal-drivers.
Build and run the QEMU exercise and corruption/recovery practice.
Report the exit statuses and leave my source unchanged.
```

```text
Use $agilex5-baremetal in /absolute/path/to/baremetal-drivers.
Check my configured Modular kit environment, then run the core and DMA tests.
Use the matching SOF/handoff and verified SOM UART, preserve the other board,
and report fresh results plus DDR restoration.
```

For hardware, first configure the host environment as described in
[the hardware tutorial](hardware.md). The skill instructs the agent to verify
board identity, artifact compatibility, container mapping and ownership before
programming. Its original-bench USB paths and clock/pinmux lessons are reference
observations, not settings to apply blindly to a different board.

## Keep it reproducible

The installed skill is a copy; `git pull` updates the repository copy only.
Record the repository commit used for the skill and the examples when reporting
a run. Keep fixes in `skills/agilex5-baremetal/` with the corresponding workflow
change so other users can receive them. The local global skill is not modified
by adding this package to the repository.

The skill includes the independent NEON/memory diagnostic lesson, expected RWX
warning, managed VS Code breakpoints, and owned-process/lock recovery guidance.
It also marks fabric integration and live partial reconfiguration as requiring
further target qualification; installing it does not establish new hardware
results. See [validation and limits](validation.md).
