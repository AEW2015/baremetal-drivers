# Ethernet execution evidence

The complete sustained campaign is `ethernet-20261024T154231.864079Z`:
40 measurements, a 600-second simultaneous TCP soak, no normal payload
corruption, successful DDR Hello restoration and peer-address removal.
The later `ethernet-20261024T160302.077834Z` checks the updated host runner.

See [the plotted report](../../../../docs/ethernet-validation.md) for goodput,
measurement definitions, configuration and limits. This is actual SOM HPS
EMAC2 traffic with a direct Linux peer, using a custom protocol rather than
iperf2/iperf3. High-rate UDP loss remains visible in the measurements.

## Attempts, including failures

| UTC run | Result | Saved measurement cases | DDR restoration |
|---|---|---:|---|
| [ethernet-20261024T151305.508553Z](attempts/ethernet-20261024T151305.508553Z/results.json) | TimeoutError: timed out | 0 | pass |
| [ethernet-20261024T151515.725556Z](attempts/ethernet-20261024T151515.725556Z/results.json) | TimeoutError: timed out | 0 | pass |
| [ethernet-20261024T151724.452900Z](attempts/ethernet-20261024T151724.452900Z/results.json) | TimeoutError: timed out | 0 | pass |
| [ethernet-20261024T151927.732984Z](attempts/ethernet-20261024T151927.732984Z/results.json) | TimeoutError: timed out | 0 | pass |
| [ethernet-20261024T152200.325935Z](attempts/ethernet-20261024T152200.325935Z/results.json) | pass | 0 | pass |
| [ethernet-20261024T152427.553137Z](attempts/ethernet-20261024T152427.553137Z/results.json) | pass | 29 | pass |
| [ethernet-20261024T152828.512115Z](attempts/ethernet-20261024T152828.512115Z/results.json) | TimeoutError: timed out | 30 | pass |
| [ethernet-20261024T154029.165530Z](attempts/ethernet-20261024T154029.165530Z/results.json) | pass | 3 | pass |
| [ethernet-20261024T154231.864079Z](attempts/ethernet-20261024T154231.864079Z/results.json) | pass | 40 | pass |
| [ethernet-20261024T160302.077834Z](attempts/ethernet-20261024T160302.077834Z/results.json) | pass | 3 | pass |

The first three attempts used the original extra PHY delays and failed packet
RX. The fourth removed only the RX delay and failed at a larger payload. The
fifth cleared both extra delays and passed the functional checks. The sixth
is the uncached quick baseline. The first cached full attempt timed out at
four-stream receive; its partial rate measurements remain available. Queue
bounds/pool size and socket-stall handling changed before the later passing
stress and sustained runs. Those changes do not isolate a sole cause.

## Files

- The sustained campaign's `terminal.log` preserves the complete host terminal
  capture, including interleaved boot/UART chatter and all measurement lines.
- Per-attempt JSON, fresh server UART, load, ping, DDR programmer, raw DDR UART,
  PC proof and restoration logs preserve outcomes with their recorded hashes.
- `network-final.json` identifies the sustained campaign ELF and source hashes;
  `hardware-artifacts.json` and `ddr-build-manifest.json` identify the matching
  SOF/handoff and DDR bootstrap. Hardware images and dependency sources are
  not distributed here.
- `campaign-source.json`, `campaign-run.py` and `campaign-peer.py` preserve the
  host sources used by the sustained campaign (`5077adf`). `remote-source-check.json`
  verifies firmware sources against a pushed revision. Later host-only changes
  add metadata capture and immediate failure cancellation; C/assembly are unchanged.
- `metrics.json` summarizes measured goodput. The original per-run JSON/CSV are
  the primary data, rather than values rounded in the report.
- `bringup.pcap.gz` contains 662 functional bring-up ARP/IPv4 packets. It was
  captured before the bandwidth campaign; it is not a sustained/soak trace.
- `host-context.json` is a read-only snapshot taken during the campaign, with
  cumulative NIC counters and offload/driver information, not a pre-run baseline.
- Build/QEMU/regression logs and `ci-75b621e.json` record software checks.
  The before/after bidirectional-corruption regression demonstrates cancellation
  of the other sender. These localhost tests do not substitute for board results.
- `manifest.json` lists SHA-256 and size for every evidence file except itself.

The runner now archives its actual ELF under the ignored run directory. Public
records carry binary hashes; the early historical attempts did not all retain
complete source/binary snapshots. Their logs establish the observed failures,
not independently reproducible binary packages. Captured CRLF bytes are preserved.
