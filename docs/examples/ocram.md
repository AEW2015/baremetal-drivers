# OCRAM UART Hello World

A local-memory hardware example that does not initialize DDR. Build support is included; manual programming is separate from the automated DDR suite.

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/bootstrap/ocram/uart_local.c)

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

    Stop the UART reader afterward and use the matching DDR bootstrap to return to DDR examples. This manual programming recipe was not rerun during the tutorial’s follow-up checks.

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

    Fresh repeated UART messages are the useful observation; programming success alone is insufficient. OCRAM UART execution passed on the original bench, and the packaged source was separately compiled. The later tutorial debugger smoke check targeted the DDR core example, not this manual load path.

=== "Limits"

    The handoff layout and UART divisor must match the hardware image and input clock. This is UART transmit only, without receive/flow-control testing. The separate `hello_semihost.S` is a reference source, not an additional automated test. OCRAM build support alone does not establish that an arbitrary supplied SOF can boot this program.
