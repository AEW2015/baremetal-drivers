# Vendor CCU register checks

`vendor-ccu` · `build/vendor_ccu.elf` · recorded entry `0x80200800`

[Board adapter](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/core/vendor_wrapper.c) · [Vendor sample](https://github.com/altera-fpga/baremetal-drivers/blob/1419101568f1a9034630b632634fe9fe71773266/test/simics/ccu/ccu_test.c) · [Captured UART](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/20261023T232734.166542Z/vendor-ccu-uart.txt) · [Hardware setup](../hardware.md)

All hardware commands assume the matching Modular ES profile and host/container environment from the tutorial. Register snapshots below distinguish fixed checks from values that can vary.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=board%2Fvendor-ccu){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=board%2Fvendor-ccu" data-example-id="board/vendor-ccu">board/vendor-ccu</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=board%2Fvendor-ccu" title="HPS and fabric diagram for examples/vendor-ccu.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "What it does"

    Read the CCU DSU/NCAIU/DCE/DMI/DII/DVE/global identification and configuration fields through the vendor driver. Compare against its reference values and retain nonfatal version warnings.

    1. Run the physical-board startup/UART adapter and open the vendor CCU device.

    2. Read the selected register groups; report successful accesses and differences from simulation defaults.

    3. Close the device and require main to return zero.

=== "Build and run"

    **Container/development terminal:**

    ```sh
    ./build_vendor.sh
    python3 build_board_vendor.py ccu
    ```

    **Configured Linux host terminal**, from the bind-mounted example directory:

    ```sh
    python3 run_suite.py --only vendor-ccu
    ```

    Requires the initialized HPS/CCU environment and exclusive bare-metal ownership.

    The runner loads the ELF at its own entry, requires fresh results and restores DDR Hello afterward. Close other UART readers and debug sessions first. The supplied hardware F5 configuration is for `core` only; use the runner for this selection, or adapt the ELF and entry deliberately when debugging another image.

=== "Expected results"

    **Acceptance checks and interpretation**

    | Item | Expected or recorded value | How to interpret it |
    |---|---|---|
    | Initial checks | Read DSU CAIUIDR default value SUCCESSFUL! and Read DSU CAIUTCR SUCCESSFUL! | Observed successful checks. |
    | Version warning example | Expected 0x80020348; observed 0x80020323 | A retained diagnostic, not a discarded line. |
    | Return marker | HPS_SUITE_PASS ccu rc=0x00000000 | Means the vendor register test completed under its own criteria. |

    **Captured passing output** (selected excerpt; original bench, not a promise that every snapshot is constant):

    ```text
    HPS_SUITE_BEGIN ccu
    CCU open
    Read DSU CAIUIDR default value SUCCESSFUL!
    Read DSU CAIUTCR SUCCESSFUL!
    Warning: DSU CAIUUEVIR expected: 0x80020348, observerd: 0x80020323!
    Warning: NCAIU XAIUINFOR expected: 0x80011348, observerd: 0x80021323!
    ... (additional version warnings omitted) ...
    CCU close
    HPS_SUITE_PASS ccu rc=0x00000000
    ```

    Version/default-value warnings are expected on the recorded ES bench. Inspect them on other designs instead of requiring a byte-for-byte warning list.

    Require the selected test’s result plus `DDR Hello restoration: pass`. Old Hello lines before its begin marker are not evidence of the new program. A failure marker or missing completion makes the run fail even if another subcheck passed.

=== "Limits"

    Register access and the vendor’s return code do not establish cache coherency or correct data sharing between CPUs/DMA. Warning-only comparisons do not turn into strict equality checks just because the wrapper reports PASS.

    If the test fails, keep `results.json`, its ELF SHA-256, UART, debug and bootstrap logs. Check [troubleshooting](../troubleshooting.md) before changing expected values or retrying with altered pinmux.
