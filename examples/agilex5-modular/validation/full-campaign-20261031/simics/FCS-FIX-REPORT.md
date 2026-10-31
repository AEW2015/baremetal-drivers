# FCS response-lifetime fix: native model follow-up

This is a supplemental run, not a replacement for the frozen 63-row baseline.
The original FCS HAL queued asynchronous responses into local stack arrays and
returned before those arrays were filled. A later API poll could overwrite saved
stack state; the baseline model run re-entered the OCRAM console unexpectedly.

The fixed HAL keeps each response array alive through a bounded wait for that
specific response. Timeout/error paths detach the pointer while leaving the
pending job ID reserved until its late response is drained. The shared mailbox
send and completion paths are unchanged; the new detach function is called only
by the patched FCS wrappers. Its host regression tests exercise delayed replies,
timeouts, stale replies, untouched canaries and propagated SDM errors.

The final fixed service harness executes from `0x82400000` at NS EL2 under the
matching resident BL31. Actual native-model results are:

```text
SERVICE_FCS_API chip rc=-1 hi=0x00000000 lo=0x00000000
SERVICE_FCS_API jtag rc=-1 value=0x00000000
SERVICE_FCS_API open rc=-1
SERVICE_FCS_API deinit rc=0
SERVICE_COMPLETE status=1
```

Raw SiP traces report SDM status `0x3` for these unsupported native services.
There is no unexpected bootstrap-console re-entry or exception. All eight
control-flow/error-propagation checks passed. The FCS capability result remains
**FAIL**: identity, session and RNG did not succeed. This distinguishes the
memory-lifetime fix from model support and from a physical hardware result.

See [final evidence](fcs-fixed-20261031T193009Z/results.json), [all raw UART output](fcs-fixed-20261031T193009Z/uart.txt)
and [supplemental summary](fcs-fixed-results.json). An earlier fixed variant is
also retained; the final wrapper additionally zeroes the RNG destination before
calling the real API. No RNG request was reached on this native model.
