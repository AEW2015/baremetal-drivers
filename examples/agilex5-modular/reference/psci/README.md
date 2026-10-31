# Physical PSCI CPU_ON / CPU_OFF reference harness

This harness calls the unchanged `core/secondary_core.c` helper under resident
TF-A BL31 from nonsecure EL2. It is a separate entry from the standalone EL3
suite. Build success is not an execution result.

A55.1 target MPIDR `0x100` comes from the established Modular board topology;
MPIDR affinity fields are compared with mask `0xff00ffffff` so the MPIDR U bit
does not masquerade as affinity. The target must report OFF through PSCI
AFFINITY_INFO before the helper is called. Already ON, unavailable firmware
features or an unsuitable boot environment are reported as BLOCKED, never PASS.
No secondary is forcibly reset or taken over.

The primary checks PSCI_VERSION and PSCI_FEATURES for CPU_ON64, CPU_OFF and
AFFINITY_INFO64. It requires cache/MMU-off NS EL2, an advancing counter, and
bounded waits. A zero CNTFRQ uses the monitor's declared 400 MHz only to bound
timeouts; this does not calibrate or measure CPU bring-up performance.

The exact helper receives a physical executable entry and context ID
`0x5053434943545854`. The secondary has its own startup, EL2 exception vectors
and stack; it publishes actual context, MIDR, MPIDR, EL, SCTLR, entry and stack
into reserved DDR, then writes its ready magic last after DSB. The primary
verifies all fields. It releases the secondary, which calls PSCI CPU_OFF. A
passing test requires the secondary's off-attempt record, no return from
CPU_OFF, and actual PSCI AFFINITY_INFO reporting OFF. A completion banner alone
is insufficient.

| Resource | Address |
|---|---|
| Primary ELF / entry | `0x82400000` |
| Primary stack top | `0x83fff000` |
| Secondary stack top | `0x83ffb000` |
| Shared record | `0x85000000` |
| BL31 | Existing verified RESET_TO_BL31 image at `0x80000000`, BL33 entry `0x82400000` |

From `examples/agilex5-modular` in the existing compiler container:

```sh
./reference/psci/build.sh
```

The host operator then selects the existing verified resident monitor:

```sh
python3 upstream-lab/hardware.py --suite psci \
  --bench /home/lada/altera-agilex/home/baremetal-guide-validation \
  --artifacts build/reference-psci \
  --mcp-client /home/lada/quartus26-mcp-demos/mcp_client.py \
  --bl31 /path/to/verified/reset-to-bl31-entry-82400000.bin
```

The shared runner verifies all ELF/bin hashes, owned ELF segments and load
readback, holds the shared hardware mutex, starts a fresh DDR bootstrap,
installs BL31 and captures actual UART evidence. It restores DDR Hello after
the test. Do not substitute the USB monitor, whose BL33 entry is `0x80200000`.
No storage, EEPROM, clock NVM or fuse writes occur.

## Captured execution

Native Simics and the Modular ES board both passed the complete identity/context
and CPU_OFF affinity checks. Physical evidence is in
[the campaign](../../validation/full-campaign-20261031/hardware/psci/results.json).
The test used the matching resident monitor, not the standalone EL3 suite.
