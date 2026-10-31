# Memory, SMMU and fabric labs

These labs extend the HPS examples using **HPS DDR bank 3A**. They do not use
a separate fabric EMIF. Platform results distinguish functional model execution,
hardware compilation, physical transactions and measured hardware timing.

| Lab | Start here | Current evidence |
|---|---|---|
| Cached multicore handoff and contention | [DSU](dsu/README.md) | Four QEMU and four Agilex Simics cases pass |
| L3 way partitioning | [DSU policy variant](dsu/README.md) | Opt-in Agilex image compiles; hardware comparison pending |
| DDR read/write/copy and dependent loads | [DDR sweeps](ddr/README.md) | 20 samples plus two failure controls pass in QEMU and Simics; no physical timing result |
| Translated DMA and an unmapped destination | [SMMU](smmu/README.md) | Actual QEMU PCI EDU DMA, table walks and fault events pass |
| Native DMA0/F2H/F2SDRAM TBU model paths | [SMMU model fixture](smmu/README.md) | Host-issued native translated requests/faults pass; not an Arm DMAC driver result |
| Fabric traffic generator | [AXI core and C driver](fabric-ddr/README.md) | Native RTL/driver tests and Platform Designer component generation pass |
| Arm driver → RTL → DDR and native TBUs | [Simics/Verilator](fabric-ddr/simics/README.md) | Model DDR and both fabric TBU translation/fault routes pass |
| SOM USB host | [USB bring-up](../usb-bringup/README.md) | Firmware boots; CNR and PHY-ID timeouts still block enumeration |

## Build and practise without a board

In the compiler container, from `examples/agilex5-modular`:

```sh
bash memory-labs/build_all.sh
python3 memory-labs/dsu/run.py
python3 memory-labs/ddr/run.py
python3 memory-labs/smmu/run.py
bash memory-labs/fabric-ddr/test.sh
```

Some GNU linker versions emit an RWX LOAD-segment warning for these flat
bare-metal linker scripts. With exit status zero and the expected ELF output,
that warning does not mean the build failed. The loader still checks executable
entry coverage and owned load/runtime bounds.

The first command builds QEMU and Agilex DSU/DDR guests and the QEMU-specific
SMMU guest. The following commands execute positive and deliberate-failure
controls. **Never load the QEMU SMMU/PCI EDU image onto Agilex.** Its memory
map and DMA device belong to QEMU `virt`.

With the licensed Simics installation/project already configured:

```sh
python3 memory-labs/dsu/run_simics.py
python3 memory-labs/ddr/run_simics.py
```

See each lab for the native-TBU and Simics/Verilator commands, dependencies,
captured terminal output, source/artifact hashes and model limitations. Model
counter values do not qualify physical DDR or L3 performance. The native Simics
SMMU tests use the recorded cache-disabled model setting and fresh page-table walks;
they do not demonstrate command-queue TLB invalidation.

## Physical DSU and DDR checks

Physical execution requires an available Modular ES kit, the matching
HPS-enabled SOF/handoff and the established JTAG/UART bench. The host runner
holds the shared hardware mutex, freshly initializes DDR for every image,
loads/verifies file-backed ELF segments, bounds capture and restores DDR Hello.
SMMU and fabric model fixtures are not substitutes for physical routing setup.

From this example pack on the host, freeze artifacts before queueing:

```sh
cp -a build/memory-ddr-agilex5 build/memory-ddr-frozen
python3 upstream-lab/hardware.py --suite memory-ddr --only ddr-path \
  --bench /path/to/baremetal-guide-validation \
  --artifacts "$PWD/build/memory-ddr-frozen" \
  --mcp-client /path/to/quartus26-mcp-demos/mcp_client.py

cp -a build/dsu-agilex5 build/dsu-frozen
python3 upstream-lab/hardware.py --suite memory-dsu --only normal \
  --bench /path/to/baremetal-guide-validation \
  --artifacts "$PWD/build/dsu-frozen" \
  --mcp-client /path/to/quartus26-mcp-demos/mcp_client.py
```

Memory labs default to a 180-second UART deadline. The runner rejects QEMU-target
memory builds before hardware access. Begin with `normal`; DSU `contention`
and the explicitly selected `partitioned` variant are separate later runs.
Partitioning keeps DDR-backed cacheable memory; it does not turn L3 into SRAM.
Use `--only ddr-calibrated` for the later DDR timing run: it requires both the
guest calibration checks and an independent host-measured interval of 0.9–1.1
seconds. A plain `ddr-path` pass establishes functional results, not calibrated
physical rates. The calibrated image has only been compiled so far.

No new physical result is claimed here. USB's clean-start retry awaits the
requested board power cycle. The fabric core's full-board fit/deployment awaits
the reserved OpenTPU R4 build window and a verified master-view address map.
The fitted image, stream-ID assignment, security, cache state and timing results
must each be recorded before qualifying a hardware route.
