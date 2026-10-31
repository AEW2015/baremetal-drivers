# Safe FCS and ECC status candidates

`fcs` runs the unchanged current `examples/fcs/fcs_selftest.c` command under
resident BL31 from nonsecure EL2. Linker wrappers call the real current API and
record its actual returns, chip/JTAG data, session UUID, RNG bytes and matching
close-session UUID. A summary count alone is insufficient. Full PASS requires
all seven steps, the Modular FPGA JTAG ID, nontrivial UUID/RNG data, and the
exact call sequence. UUID is the SDK session token built from an SDM RNG request
and local version/variant bits; formatting bits alone do not qualify a valid
UUID payload. SDM security denial `0x85` is PARTIAL only when identity
and deinitialization succeed and the read-only provisioning-status query returns
success or the same denial. Other API failures remain failures. No owner state
is inferred solely from denial, and no provisioning/key/fuse operation is sent.

The original FCS driver sends a volatile HPS OS-stage notification before
opening a session. That notification is best effort in the unchanged driver;
its rejection does not substitute for actual session/RNG success. Operation
buffers use DDR `0x83000000..0x83800000`; the original read-only GET_PROVISION
buffer uses `0x83800000..0x83800400`. Normal stack top is `0x83fff000`.

`ecc-readonly` runs only the current ECC SERR/DERR getter APIs, comparing them
with raw System Manager reads, at standalone EL3. It is always PARTIAL coverage
of the original ECC example. The original `ecc_selftest status` command is not
read-only: init masks and clears pending bits, poll clears status, and deinit
masks interrupts. Those functions, counter initialization, injections, OCRAM
probe reads and ECC block-enable writes are excluded here. No ECC recovery or
error-injection claim follows from a status snapshot.

From `examples/agilex5-modular` in the configured compiler container:

```sh
./service-candidates/build.sh
```

The build uses existing current DDR SDK libraries read-only and verifies all
source hashes against their manifest. The two profiles cannot be mixed in one
physical run:

```sh
# Host: add the usual --bench and --mcp-client paths.
python3 upstream-lab/hardware.py --suite services --only fcs \
  --artifacts build/service-candidates --bl31 /path/to/verified-bl31-entry-82400000.bin \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py
python3 upstream-lab/hardware.py --suite services --only ecc-readonly \
  --artifacts build/service-candidates \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py
```

The shared runner supplies fresh DDR, exclusive hardware ownership, validated
load/readback, bounded UART collection, the strict oracle and DDR Hello
restoration. Neither compile success nor restoration alone qualifies a service.
