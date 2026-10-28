# From your first breakpoint to the Agilex 5 SOM

Build an AArch64 bare-metal application, inspect it in VS Code, and then use the
same compiler and debugger workflow on an Agilex 5 Modular development kit.

Start with QEMU if you do not have a board connected. Use [Simics](simics.md) for the Agilex HPS model and the current upstream
command-console examples. Move to hardware to test
the HPS controllers and the devices actually populated on the SOM.

[Install the tools](setup.md){ .md-button .md-button--primary }
[Browse the examples](examples.md){ .md-button }

## What you will build

| Track | Runs where | What you learn |
|---|---|---|
| QEMU exercise | Generic `virt` machine, Cortex-A53 model | Startup, ELF addresses, EL3, NEON, RAM, UART output and GDB |
| Simics 26.3 | Agilex 5 universal virtual platform | Current upstream console, timer, GIC and memory self-tests |
| Hardware examples | Modular ES kit, A55/A76 HPS | DDR bring-up, source debugging, DMA, GIC and SOM peripherals |

QEMU `virt` is a generic virtual board. It does **not** reproduce this kit's
memory map, clocking, DDR initialization, DMA engine or SOM devices. The QEMU
exercise has its own linker script and PL011 UART code; the hardware examples use
the actual HPS addresses. An Agilex ELF cannot simply be passed to `qemu -kernel`.
See [QEMU's platform description](https://www.qemu.org/docs/master/system/arm/virt.html).

## Follow the tutorial

1. [Install the compiler, debugger and emulator](setup.md).
2. [Open the supplied VS Code workspace](vscode.md).
3. [Run, break and inspect the QEMU exercise](qemu.md).
4. [Initialize DDR and debug the physical kit](hardware.md).
5. [Explore the SOM examples](examples.md) and their [validation limits](validation.md).

The documented development host is x86-64 Linux, with Ubuntu 24.04 used for the
tool checks. VS Code can run locally or attach to the existing Linux development
container. Hardware automation uses the Linux host for UART capture and the
container for Quartus/OpenOCD. It does not require Linux running on the HPS.

## What is already verified?

The original SOM-first campaign passed all 15 registered hardware suite entries.
The repository preserves the selected logs and exact tested ELF hashes. The
packaged sources also build separately. This tutorial adds a tested QEMU exercise
and debugger walkthrough; consult [the validation record](validation.md) for the
precise distinction between tested commands, supplied GUI configuration and
untested end-to-end peripheral behavior.

## Extend the lab into the fabric

[Build a memory-mapped ADD/XOR IP and bare-metal driver](fabric-ip.md), then
follow the [partial-reconfiguration integration lab](partial-reconfiguration.md)
to plan live persona swaps. The software/RTL tests are executable now; the new
whole-board FPGA integration and live PR are explicitly marked unvalidated.
