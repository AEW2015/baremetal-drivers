# QEMU: AArch64 CPU, NEON and RAM

A board-free exercise for generic QEMU `virt`; separate from the hardware suite.

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/qemu/hello.c)

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=custom%2Fqemu-hello){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=custom%2Fqemu-hello" data-example-id="custom/qemu-hello">custom/qemu-hello</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=custom%2Fqemu-hello" title="HPS and fabric diagram for examples/qemu.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "What it does"

    Start at EL3 on a Cortex-A53 model, initialize a stack and BSS, output through the virtual PL011 UART, perform a four-lane NEON addition and compare a 4096-byte CPU memory copy. The program reports its exit status through AArch64 semihosting.

    Code starts at `0x40200000`, above QEMU’s device-tree area. Its stack is at `0x41000000` and its UART is at `0x09000000`. These are QEMU platform addresses.

=== "Build and run"

    After [installing the tools](../setup.md), run in the **development environment** (native Linux or attached container):

    ```sh
    ./qemu/build.sh
    python3 qemu/run.py --check
    ```

    Or open the supplied workspace, select **QEMU: AArch64 hello (no board)** and press F5. Set a breakpoint at `qemu_done` to inspect the finished checks. See the [debugger walkthrough](../qemu.md).

=== "Expected results"

    ```text
    QEMU VIRT AARCH64 BEGIN
    PASS EL3
    PASS NEON: 11 22 33 44
    PASS MEMORY: 4096-byte CPU copy
    QEMU EXAMPLE COMPLETE
    ```

    | Check | Expected result |
    |---|---|
    | Exception level | EL3; checked in the program |
    | Vector result | `{11, 22, 33, 44}` |
    | Memory copy | All 512 64-bit destination words match source |
    | `failures` at `qemu_done` | `0` |
    | `status` at `qemu_done` | `0` |
    | Process exit | Zero after semihosted exit |

    The checked runner requires every expected marker and a successful process exit. At the final breakpoint, `print source[511] == destination[511]` should print `1`. [Captured run and GDB results](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/tutorial/results.json).

=== "Limits"

    This does not emulate the Agilex 5 Modular board. It does not test HPS DMA, DDR training, SOM I2C/I3C, real GIC-600 integration or the external connectors. The CPU is a single Cortex-A53 model, not the mixed A55/A76 HPS. Follow the hardware pages for the physical examples.
