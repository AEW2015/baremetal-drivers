# Hardware inputs and first-run checklist

This is the single checklist before moving from QEMU/Simics to the physical kit.
Use [host OS routes](host-support.md) to choose where tools and USB devices run.
Cloning the C repository does not supply a universal FPGA image.

| Input | Requirement / repository location |
|---|---|
| Board | Agilex 5 Modular **ES** `A5ED065BB32AE6SR0`; FPGA ID `0364F0DD` |
| Connections | Carrier JTAG plus separate SOM **J2 HPS_UART**, 115200 8N1 |
| FPGA design | HPS-enabled Modular ES design with the correct SOM pinmux, clocks and HPS DDR bank 3A |
| DDR | Recorded kit: 8 GiB DDR4-1600, 150 MHz reference; diagnostics test bounded scratch ranges |
| Source programming file | Place your qualified source SOF at `examples/agilex5-modular/build/fpga/base.sof` |
| Handoff/provenance | Matching source project's handoff, exact part/clock/DDR settings, source revision and file hashes; keep under `build/fpga/` |
| FPGA tools | User-installed matched Quartus/PFG/Programmer and its ADIv6/`aji_client` OpenOCD on PATH, or a configured tool container |
| Firmware | DDR builder uses `stack-versions.json` and writes `build/boot/` |
| UART | User-selected Linux device in `build/local.json`; no USB topology is hardcoded |
| Mutex | Repo-relative `hardware.lock`, or one configured shared lock for all checkouts/debuggers using this board |
| Optional PR | Matching full SOF, ADD/XOR partials, guest ELF/bin and compatibility proofs in `build/pr/`; do not mix bases/personas |

The [FPGA design page](fpga-design.md) records the reference source and the
historical qualified pair. The [26.3 migration](stack-26.3.md) describes matching
IP and firmware. An arbitrary SOF cannot be qualified by copying its hash into a
profile. Preserve logs and stop on an identity/image mismatch.

## Build in the tool environment

From the repository root, enter the examples directory. Every relative path
below is relative to that directory:

```sh
cd examples/agilex5-modular
export AGILEX_SOF=build/fpga/base.sof
bash bootstrap/ddr/build_ddr.sh
bash simics/build.sh DDR
bash hardware-candidates/build.sh
```

The DDR builder writes `build/boot/ddr_recovery.sof`, the boot manifest and
intermediate files. Dependencies stay in `build/deps/`. The default 26.3 flow
is FPGA-first and requires the complete merged SOF. An HPS-only RBF is not a
substitute. Do not write flash/SD to run this volatile lab.

## Configure and check

Back at the repository root, on the Linux execution host:

```sh
python3 lab.py --backend native --uart /dev/serial/by-path/YOUR-SOM-UART configure
python3 lab.py hardware doctor
python3 lab.py hardware hello
```

For an existing container, configure its name and this checkout's location
inside it instead:

```sh
python3 lab.py --backend container --container YOUR-TOOLS \
  --container-root /work/examples/agilex5-modular \
  --uart /dev/serial/by-path/YOUR-SOM-UART configure
python3 lab.py hardware doctor
python3 lab.py hardware hello --build
```

For a container with a different account, add `--container-user USER` when
configuring it. The recipe creates `dev`; an arbitrary vendor image may not.

`build/local.json` is ignored, contains local settings, and is not a credential
store. Relative paths resolve from `examples/agilex5-modular`, even when the
launcher is called from another working directory. The UART path and installed
tool locations are external resources and must be supplied by the user.
The built-in programmer client needs no external bench/MCP checkout. It labels
CLI discovery as CLI; `AGILEX_PROGRAMMER_MCP_COMMAND` can optionally select a
vendor MCP server using a JSON argv array in the tool environment.

The doctor checks inputs and may read JTAG identity; it does not program. A
normal run prints discovery, DDR bootstrap, payload/readback and restoration
stages. Require `hello: pass` **and** `DDR Hello restoration: pass`. A busy mutex
waits; do not start a second operator or delete its lock. See
[troubleshooting](troubleshooting.md).
