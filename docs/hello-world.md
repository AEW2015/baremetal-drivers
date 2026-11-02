# Hello World on QEMU, Simics and hardware

Start with QEMU. Then run the upstream Hello command on the Agilex Simics model
or the Modular kit. Simics and hardware share `examples/hello/hello_selftest.c`;
QEMU has its own startup, UART and memory map.

## Where the files are on this bench

| Location | Path |
|---|---|
| Host checkout | `/home/lada/quartus26-mcp-demos/baremetal-fixes-20261029` |
| Same checkout in `agilex26-mcp-demos` | `/workspace/baremetal-fixes-20261029` |
| QEMU source | `examples/agilex5-modular/qemu/hello.c` |
| Shared upstream Hello source | `examples/hello/hello_selftest.c` |
| Simics scripts | `examples/agilex5-modular/simics/` |
| Physical-board wrapper | `examples/agilex5-modular/hardware-candidates/` |

These are the established bench paths. For a different checkout, configure the
[container mount](container.md) and [hardware environment](hardware.md) first.
The first QEMU lab uses the [educational coding standard](educational-coding-standard.md).

## QEMU: no board needed

In a **host terminal**, enter the existing tool container:

```sh
docker exec -it \
  -w /workspace/baremetal-fixes-20261029/examples/agilex5-modular \
  agilex26-mcp-demos bash
```

In that **container terminal**:

```sh
./qemu/build.sh
python3 qemu/run.py --check
```

Expected output from the exercised lesson:

```text
QEMU VIRT AARCH64 BEGIN
PASS EL3
PASS NEON: 11 22 33 44
PASS MEMORY: 4096-byte CPU copy
QEMU EXAMPLE COMPLETE
PASS QEMU_CHECK: all required markers and exit status zero
```

The runner exits 0. Next, [step through `main` and `qemu_done`](qemu.md) or run
`python3 qemu/experiment.py` to practise corruption and recovery in scratch
copies. Deliberately failed guests exit 1; the complete experiment exits 0
when all expected failures and recoveries are observed.

## Simics: Agilex virtual HPS

Use the same **container terminal**. The model is already deployed on this bench;
a new machine needs the [Simics installation and deployment](simics.md).

```sh
./simics/build.sh OCRAM
python3 simics/run.py --only hello
```

The guest command and captured response include:

```text
SoCFPGA Bare-Metal > hello_selftest
Hello, Baremetal World!
```

Require the runner's `PASS hello` and zero exit, rather than the console's generic
“command completed” message alone. [See the captured Simics UART output](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/stack-26.3-20261101/simics/upstream-console/hello/uart.txt).

## Hardware: use the Linux host

Exit the container terminal with `exit`. Leave JTAG and the SOM J2 UART connected.
On the **host**, this bench already has the matched images and built Hello ELF:

```sh
cd /home/lada/quartus26-mcp-demos/baremetal-fixes-20261029/examples/agilex5-modular
source /home/lada/quartus26-mcp-demos/agilex5-stack-20261101/current-stack-env.sh
python3 upstream-lab/hardware.py \
  --suite candidates --only hello \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --artifacts "$PWD/build/hardware-candidates" \
  --mcp-client "$AGILEX_MCP_CLIENT" \
  --port "$AGILEX_UART" --wait-for-hardware
```

This runs the existing built hardware adapter. To rebuild it, use the container
commands `./simics/build.sh DDR` and `bash hardware-candidates/build.sh` first.
A linker RWX-segment warning can accompany these diagnostic RAM ELFs; a successful
link produces the ELF, but does not establish memory permission isolation.

The runner acquires the shared mutex, discovers JTAG, boots DDR, loads and checks
the payload, captures its UART result and restores DDR Hello. Current runs print
each stage; a bootstrap can take up to its 400-second bound. If waiting, inspect
the evidence directory rather than starting a second board operator.

The successful physical retry captured:

```text
CANDIDATE_BEGIN name=hello
CANDIDATE_EL=3 SCTLR=0x30C51838
PASS STANDALONE_EL3_MMU_DCACHE_OFF
CANDIDATE_COMMAND hello_selftest
Hello, Baremetal World!
CANDIDATE_COMPLETE status=0
```

Require both `hello: pass` and `DDR Hello restoration: pass` from the runner.
[Recorded retry and recovery](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/validation/hello-followup-20261102)
include the earlier interrupted discovery. Read
[the quiet-run troubleshooting note](troubleshooting.md#hardware-hello-appears-quiet-after-printing-its-evidence-directory)
if discovery is interrupted.
