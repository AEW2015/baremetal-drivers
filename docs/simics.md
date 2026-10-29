# Simics 26.3: Agilex HPS examples alongside QEMU

The [secure-runtime follow-up](runtime-fixes.md) adds verified BL31/EL2 bridge
loopback and warm reboot, counter/diagnostic fixes, mailbox coverage and queued
hardware validation. Earlier tables below retain their original campaign scope.

For additional DDR-loaded example handlers, physical-board comparisons and
captured output, see the [new upstream example campaign](upstream-examples-validation.md).

=== "Choose a track"

    | Track | Source and target | What the result establishes |
    |---|---|---|
    | [QEMU](qemu.md) | Local freestanding CPU labs on generic `virt` | Startup, CPU, RAM, exceptions, UART and GDB lessons |
    | Current upstream Simics | Root 26.3 APIs, Agilex 5 universal model | Real execution of the new command console and selected HPS model self-tests |
    | Legacy Simics | Pinned 25.1 native sample suite | Compatibility regression for the older API; separate PASS/failure record |
    | [Hardware](hardware.md) | Modular ES kit with matching images | Actual DDR/peripheral/physical-I/O evidence for the recorded binary |

    Simics models HPS peripherals that generic QEMU `virt` does not. It does not
    establish the physical SOM wiring, PHY timing or achievable Ethernet
    bandwidth. QEMU and the hardware labs remain available with their existing
    commands. Read [the new upstream API and example catalog](upstream-26.3.md)
    before treating an older `/dev/...` sample as a current 26.3 example.

=== "Install and deploy"

    The tested bench uses Quartus 26.3, **Simics for Altera FPGAs 26.3.0.14**,
    Simics Base **7.89.0**, and `agilex5e-universal`. The runtime is proprietary
    and is not bundled in this repository or downloaded by GitHub Actions.

    Obtain the Linux installer from the
    [Altera Download Center](https://www.altera.com/downloads/), choosing
    Simulation Tools → Altera Simics Simulator → the desired release.
    For a new installation in the configured container, on the host:

    ```sh
    docker cp "$HOME/Downloads/AlteraSimicsSetup-intel-fpga-ext_26.3.0.14-linux.run" \
      agilex26-mcp-demos:/tmp/simics.run
    docker exec -u root agilex26-mcp-demos chmod +x /tmp/simics.run
    docker exec -u dev agilex26-mcp-demos /tmp/simics.run \
      --mode unattended --accept_eula 1 \
      --installdir /home/dev/altera_pro/intel-fpga-ext_26.3
    ```

    The unattended command accepts the vendor EULA. Substitute your actual
    container and installer path. Existing installations do not need reinstalling.
    Files installed in a container layer survive restarts; recreating that
    container requires repeating installation or using your own derived image.

    In the **container**, from `examples/agilex5-modular`:

    ```sh
    export SIMICS_FPGA_ROOT=/home/dev/altera_pro/intel-fpga-ext_26.3/simics
    python3 simics/setup.py
    ```

    This deploys the model into ignored `build/simics26`, builds its component
    modules, and records their package versions. The installer, model source and
    generated libraries stay out of Git. Keep deployment separate from the C
    source root: Simics project setup writes its own `CMakeLists.txt`.

=== "Build and run current upstream"

    Install `gcc-aarch64-linux-gnu`, `libc6-dev-arm64-cross`, CMake 3.24+, Ninja, Python 3, make and g++.
    They are included by the updated learning-container recipe. In the container:

    ```sh
    ./simics/build.sh OCRAM
    python3 simics/run.py --only hello
    python3 simics/run.py --only hello,help,timer,gic,ddr
    ```

    Every selected check starts a fresh model. The runner waits for the console
    prompt, sends one command, requires return to the prompt, and checks its
    detailed output. A simulator exit code zero or the console's generic
    `command completed` message is insufficient by itself.

    The `ddr` selector is a simulated scratch-memory/init test. If the program
    explicitly falls back to OCRAM, the runner records `ddr_stage_skipped` and
    labels the result as fallback-only. It never substitutes a physical DDR claim.

    To compile the larger upstream profile separately:

    ```sh
    ./simics/build.sh DDR
    ```

    The DDR ELF is compiled here; this runner boots the standalone OCRAM image.
    Native upstream DDR boot requires a separate TF-A/BL33 flow. See
    [the migration/build guide](upstream-26.3.md). Set `UPSTREAM_CROSS_COMPILE`
    to select this track's compiler; `CROSS_COMPILE` for QEMU/legacy tools is
    independent. Each build records compiler and image/source hashes.

    VS Code tasks include **Build upstream 26.3 OCRAM**, **Setup Simics Agilex 5
    model**, **Run Simics upstream Hello** and **Run Simics upstream OCRAM checks**.
    Attach to the development container and export `SIMICS_FPGA_ROOT` in its
    environment. The underlying CLI commands were tested; the desktop task GUI
    was not exercised. Existing QEMU build/debug tasks remain unchanged.

=== "Expected results: real output"

    The current 26.3 OCRAM console produced these captured runner lines. Extra
    serial blank lines are collapsed in the excerpts below:

    ```text
    PASS hello
    PASS help
    PASS timer
    PASS gic
    PASS ddr
    ```

    The Hello command prints:

    ```text
      Run command ............................... Hello, Baremetal World!
    DONE
    ------------------------------------------------------------
    ```

    The detailed timer and GIC summaries each report:

    ```text
    RESULT : 2 of 2 tests passed  -  SELF-TEST PASSED
    ```

    The memory-validation summary reports:

    ```text
    RESULT : 4 of 4 tests passed  -  SELF-TEST PASSED
    ```

    These excerpts come from model execution, not compiler output. The source,
    image hashes, complete UART/terminal logs, command scripts and measured run
    results are retained in the
    [Simics validation record](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/simics26).
    New runs write `runs/simics-upstream26-<UTC>/results.json` and per-case
    `uart.txt`/`terminal.log`. Paths, build timestamps and timing values vary.

=== "Legacy examples and known failures"

    To reproduce the older native samples with the same Simics installation:

    ```sh
    python3 simics/legacy.py --build --only hello-world
    python3 simics/legacy.py --build --all
    ```

    This fetches verified commit `1419101568f1a9034630b632634fe9fe71773266` into
    ignored `.deps/baremetal-25.1`, builds the required OCRAM images with the
    pinned Arm GNU 13.2.Rel1 tools, and adapts copies of their test scripts.
    Original source scripts and C code remain unchanged.

    The recorded compatibility run has **13 passing and three failing cases**:

    | Cases | Observed outcome |
    |---|---|
    | Hello, UART, DMA, watchdog, I2C, I3C, SPI, SD/MMC, MMU EL3, SMMU, CCU, clock manager, ECC | PASS, guest completion and return zero |
    | Legacy timer | Model stops on access to a timer still in reset; simulator exits 0 without guest completion; runner reports FAIL |
    | Legacy XGMAC | PHY helper reports `Invalid phy2 value`; guest returns 1 |
    | Legacy HPS mailbox | Expected COUT/ROUT/RIN offset checks fail; guest returns `0xffffffff` |

    Thus `--all` currently exits **1**. It is not an all-green suite. A legacy
    timer failure does not contradict the separately recorded current 26.3
    timer PASS. Driver register checks, modeled loopbacks and simulation-default
    comparisons retain their own scope; they do not establish board connectivity.

=== "Troubleshooting and limits"

    - **Old target path missing:** 26.3 deploys
      `targets/agilex5e-universal/agilex5e-universal.simics`; the older
      `targets/sm-hps/...` location is absent. The wrappers use `sim->project`.
    - **Unknown `sm-universal-system-comp`:** run `simics/setup.py`; deploying
      files alone is insufficient until the component modules are built.
    - **ELF missing:** current checks need `./simics/build.sh OCRAM`; legacy
      checks need `--build` and their own pinned source, not the DDR variants.
    - **Coverage output is already a directory:** the older exporter could stop
      on repeat runs. The runner creates a fresh directory for every case/run.
    - **Hello prints PASS but X0 looks like `0x10c02000`:** the old console
      breakpoint fired inside UART printing. The legacy adapter captures X0 at
      `exit`, before `puts` changes it. A zero low byte of a register is not proof
      of a successful guest exit.
    - **Simulator exits 0 after a model critical message:** require completion,
      actual guest status for legacy tests, and detailed command results for the
      current console. Regression tests cover this observed false-success case.
    - **Model warnings:** upstream pinmux/default-value and PHY warnings remain
      visible in the raw logs; they are not silently removed or reclassified.

    GitHub CI compiles both current profiles and runs QEMU plus the simulation
    wrapper regressions. Actual Simics execution is recorded from the licensed
    local installation, not claimed as a public hosted CI job. Simulated time
    and packet rates are not hardware bandwidth measurements. The new 26.3 API
    has not been deployed to this physical Modular ES board by this sync.
