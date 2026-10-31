# FCS response-buffer lifetime fix

The original physical FCS run completed CHIP_ID in the SDM, then branched to
`0xC15565BC`, the returned chip-ID low word, and raised an EL2 exception.
The failure capture is `runs/upstream26-hardware-20261031T191906.463594Z`.
The final corrected physical run is
`runs/upstream26-hardware-20261031T193005.659836Z`; its ELF SHA-256 is
`23950ef44cd3a4b4719544b02be698ee77af345efc04c878bf95cf4b793c4754`.
Neither historical result was overwritten.

The bug was in the HAL's asynchronous response lifetime, not a wrapper ABI:

1. `run_fcs_get_chip_id()` passed a local three-word response array to
   `sip_svc_send()`. The send registered that pointer and returned after enqueue.
2. The HAL immediately read zero-initialized words and returned, ending the
   response array's lifetime.
3. The API's later `fcs_api_poll_drain()` consumed the SDM response.
   `mbox_poll_once()` copied the response into the expired HAL stack location,
   which had been reused. A saved return address became the chip-ID low word.

The pinned [TF-A CHIP_ID callback](https://github.com/altera-fpga/arm-trusted-firmware/blob/2ea5afda7f34774ddcc677fb3a728fa57f780a1e/plat/intel/soc/common/socfpga_sip_svc.c#L894)
returns X0=SiP success, X1=SDM error, X2=chip low and X3=chip high. The existing
`smc_call()` shifts X1..X11 into its response array. Thus the HAL's three-word
shape and wrapper's two `uint32_t *` output arguments were correct; returning
before the queued response arrived was the fault.

The fix is restricted to the demo's seven exercised HAL paths: chip ID, JTAG
ID, open session, UUID generation's internal RNG request, external RNG, close
session and read-only provisioning query. A private FCS submit/wait helper
keeps each local response array alive through bounded polling. It initializes
the status to `UINT64_MAX`, outside the SDM status range, and waits for that
specific response to change. Another transaction's completion cannot satisfy
the wait, and an untouched zero-filled array cannot appear successful.

Every wait exit detaches the caller's pointer and length through
`mbox_detach_response_buffer()`. On timeout, the pending job ID remains
allocated until its eventual response is drained. The old response then has
no application pointer to write through, and its job ID cannot be reused for a
new local array before completion. Successful completion also detaches the
now-inactive mapping. The existing shared client stays open across FCS
init/deinit; the regression checks that this preserves timeout quarantine
across an API deinit/reinit cycle too.

`sip_svc_send()` remains asynchronous for other callers. No existing generic
send/completion behavior changed. The helper is for this SDK's cooperative,
single-threaded bare-metal polling flow. Explicit client destruction, unrelated
HAL operations and concurrent RTOS callers are not newly qualified by this fix.
The other FCS key-management, digest, MAC, AES, attestation and signing paths
still use their existing transport paths and require a separate lifetime audit.

The patch also propagates actual RNG response errors, and a failed UUID RNG
request attempts to close the newly opened remote session rather than reporting
a formatted but empty UUID. The test wrapper independently zeros the requested
16-byte RNG output, so a zero-returning API that writes nothing cannot pass
using stale stack contents. These checks do not establish RNG entropy quality.

Builds remain separate from the baseline:

```sh
UPSTREAM_BUILD_DIR=build/upstream26-fcs-fixed bash simics/build.sh DDR
FCS_SDK_BUILD=build/upstream26-fcs-fixed \
SERVICE_CANDIDATE_BUILD=build/service-candidates-fcs-fixed \
  bash service-candidates/build.sh
bash service-candidates/tests/test_fcs_transport.sh
```

The native host regression compiles the real FCS HAL, API and mailbox queue,
modeling only SiP firmware responses. It checks delayed identity data, actual
error propagation, the full session/RNG/close path, UUID-failure cleanup,
timeout followed by a late old reply and a different new reply, and an owned
canary that a detached late reply must leave unchanged. The old bug fails the
first delayed-data assertion before any dangling-stack write is needed; ASan
or undefined behavior is not required to demonstrate the defect.

Physical retest established identity/read-only services and clean control flow,
then reported SDM `0x85` session denial. That is PARTIAL, not a successful crypto
session or RNG test. The native Simics model returns controlled SDM error 3 and
also exits cleanly; it remains a failed capability test rather than a hardware
substitute. Exact final evidence, source hashes and regression outcomes are in
`validation/fcs-lifetime-fixed-20261031/`.
