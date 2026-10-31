# OCRAM UART Hello World

A local-memory hardware example that does not initialize DDR. UART programming is separate from the 15-entry DDR suite. A separate automated semihosting check now has physical load/readback and stopped-PC evidence.

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/bootstrap/ocram/uart_local.c)

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=custom%2Focram-hello){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=custom%2Focram-hello" data-example-id="custom/ocram-hello">custom/ocram-hello</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=custom%2Focram-hello" title="HPS and fabric diagram for examples/ocram.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "What it does"

    Start from HPS OCRAM address zero, use a local stack at `0x70000`, apply the tested handoff’s pin configuration, initialize UART0 and repeatedly transmit a Hello message through SOM J2.

    This source uses the bench-specific handoff layout at `0x7f000` and UART divisor 54. These are hardware-design assumptions, not settings to copy to every Agilex board.

=== "Build and run"

    In the **container**, using the same matching SOF profile:

    ```sh
    export AGILEX_SOF=/absolute/path/to/matching-memory_test.sof
    ./bootstrap/ocram/build_uart.sh
    jtagconfig
    ```

    The build produces `bootstrap/ocram/build/hello_uart.elf`, `.bin`, `.hex`, and, when `AGILEX_SOF` is set, `hello_uart.hps.rbf`.

    For a **manual volatile load**, inspect the fresh chain and verify the Modular ES carrier/name/ID. Substitute the full verified cable name and the FPGA’s current device position:

    ```sh
    quartus_pgm -c 'YOUR-VERIFIED-MODULAR-CARRIER-CABLE' -m jtag \
      -o 'p;/absolute/container/path/bootstrap/ocram/build/hello_uart.hps.rbf@VERIFIED-FPGA-POSITION'
    ```

    The quoted placeholders must be replaced; they are not literal executable values. Use the **host UART monitor** described in the [hardware tutorial](../hardware.md) to observe the output. The DDR `run_suite.py` commands and F5 core configuration do not run this OCRAM image.

    Stop the UART reader afterward and use the matching DDR bootstrap to return to DDR examples. This manual programming path remains distinct from the automated semihosting test below.

=== "Expected results"

    The UART should repeatedly print:

    ```text
    Hello, World! Agilex 5 HPS OCRAM UART
    ```

    | Check | Expected result |
    |---|---|
    | Console | SOM J2 HPS_UART, 115200 8N1, no flow control |
    | Execution | HPS OCRAM, beginning at address zero |
    | DDR | Not initialized by this application |
    | Persistent writes | None from this example |

    Fresh repeated UART messages are the useful observation; programming success alone is insufficient. OCRAM UART execution passed on the original bench. The [latest campaign](../full-validation-2026-10-31.md) distinguishes that UART path from the new automated physical semihosting test.

    The separate semihosting run captured these actual debugger lines:

    ```text
    Hello, World! Agilex 5 HPS executing from OCRAM.
    pc 0x0000000000020010
    REFERENCE_SEMIHOST_STOP_COMPLETE
    ```

    That test loads the reference at `0x20000`, enters at `0x20004`, verifies all binary bytes, and stops at the completion breakpoint `0x20010`. [Recorded results and artifact hashes](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/full-campaign-20261031/hardware/references/results.json) also show the separate DDR exception-register snapshot and successful DDR Hello restoration. Neither result is a UART receive or fault-recovery test.

=== "Limits"

    The handoff layout and UART divisor must match the hardware image and input clock. This is UART transmit only, without receive/flow-control testing. The separate `hello_semihost.S` is now exercised by `reference/build.sh` and the host `reference/run_hardware.py`; it uses debugger semihosting rather than SOM UART. Its automated pass does not qualify an arbitrary SOF or replace the UART transmit check. The ELF executes from OCRAM, while the host recovery workflow can initialize DDR before and after the test.
