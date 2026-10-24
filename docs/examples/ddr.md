# DDR bring-up and Hello World

Hardware prerequisite used before every DDR suite entry; this is not a `--only` selector.

[Source](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/bootstrap/ddr/local_ddr_probe.inc.in)

=== "What it does"

    Build the pinned ATF initializer with a local hook immediately after DDR initialization and before storage boot. The hook fills/checks a 64 MiB region using four address-dependent patterns, copies the UART payload into DDR, verifies its bytes, invalidates the instruction cache and jumps to it.

    The host runner watches fresh UART output and then checks that the CPU PC lies in the DDR payload. The application stays running after a successful check.

    | Range | Use |
    |---|---|
    | `0x84000000`–`0x87ffffff` | 64 MiB temporary test region |
    | `0x82000000` | DDR Hello payload entry |
    | `0x82000000`–`0x820000ff` | Accepted payload PC range (upper bound excluded at 0x82000100) |

=== "Build and run"

    Complete the [matching FPGA/handoff and host/container setup](../hardware.md). In the **container**:

    ```sh
    export AGILEX_SOF=/absolute/path/to/matching-memory_test.sof
    ./bootstrap/ddr/build_ddr.sh
    ```

    From the configured **host** directory:

    ```sh
    python3 bootstrap/ddr/run_ddr.py
    ```

    Use `--full-recovery` only when loading the matching merged volatile SOF is needed to establish the board configuration, as explained in the hardware tutorial. Stop other debuggers and serial readers first.

=== "Expected results"

    The **host runner summary** in the passing tutorial check was:

    ```text
    PASS: HPS DDR bank 3A initialized; four 64 MiB patterns and payload readback passed.
    Hello, World! executing from HPS DDR bank 3A @ 0x82000000
    CPU PC confirmed in DDR: 0x82000014. Application left running.
    ```

    The saved `bootstrap/ddr/uart-<timestamp>.bin` contains the underlying checks, including:

    ```text
    NOTICE:  ###DDR:init success###
    NOTICE:  LOCAL DDR: 64 MiB uncached test at 0x84000000, four address-dependent patterns
    NOTICE:  LOCAL DDR: pattern 0 PASS (67108864 bytes)
    NOTICE:  LOCAL DDR: pattern 1 PASS (67108864 bytes)
    NOTICE:  LOCAL DDR: pattern 2 PASS (67108864 bytes)
    NOTICE:  LOCAL DDR: pattern 3 PASS (67108864 bytes)
    NOTICE:  LOCAL DDR: payload readback PASS, entering DDR code at 0x82000000
    ```

    All four pattern markers, payload readback, successful programming and at least three **fresh** Hello messages after the payload marker are required. The debugger must confirm the PC is in the payload; an exact instruction address such as `0x82000014` or `0x82000024` is a snapshot, not a fixed expected PC.

    [Recorded restoration proof](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/tutorial/hardware-restore.txt).

=== "Limits"

    The board’s HPS bank 3A is 8 GiB; this checks only a 64 MiB scratch region and payload execution. The vendor configured-2-GiB/detected-8-GiB warning remains relevant. This is not memory-margin, retention, full-bank, cache-coherency or performance qualification.

    It overwrites the scratch region and replaces volatile execution. It does not access SD/flash contents. The hook runs before storage/combo-PHY initialization and does not provide resident BL31/PSCI services to the application.

