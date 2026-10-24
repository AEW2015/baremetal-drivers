# SOM Ethernet packets and bandwidth

Use the checkout's `docs/examples/ethernet.md` and
`examples/agilex5-modular/ethernet/README.md`. Commands below are relative to
`examples/agilex5-modular`. This is a standalone lwIP program on A55.0, not a
Linux network command running in the development container.

## Build and select the peer

Build `./ethernet/build.sh` with Arm GNU 13.2.Rel1 `aarch64-none-elf` and its
newlib. The Linux cross compiler used by the QEMU CI lab is not the supported
libc for this program. The build pins lwIP 2.2.1 by commit and rejects changed
dependency sources. Retain `build/network.json` alongside the ELF.

Confirm the SOM HPS jack, dedicated Linux peer interface and topology. The SOM
uses EMAC2/Marvell 88E1512; carrier Ethernet is different. The runner explicitly
requires an interface and uses board `192.168.50.2/24`, peer `192.168.50.1/24`.
It rejects a differently addressed NIC or an overlapping route. The existing
hardware container must share host networking and have NET_ADMIN for temporary
address changes via its root account; see `docs/container.md`. Preserve the
user's Internet/default route and other interfaces.

On the configured Linux host:

```sh
python3 ethernet/run.py --interface YOUR_WIRED_NIC --smoke
python3 ethernet/run.py --interface YOUR_WIRED_NIC
```

Coordinate other checkouts through repeated `--coordination-lock PATH`, in
addition to the project lock. Each run performs a fresh qualified DDR bootstrap,
loads at `0x82600000`, captures UART, stops the firmware, restores DDR Hello
and removes only an IP address that it added. Require both test results and
successful cleanup. Keep failed attempts.

## Demonstrated board-specific lessons

- Upstream `xgmac_send`/`xgmac_recv` were stubs. The local adapter supplies real
  descriptor-driven TX/RX. Do not infer traffic support from register tests.
- On the established Modular ES handoff, Marvell page 2/register 21 initially
  read `0x1076`. ARP transmission reached the peer but RX reported CRC errors.
  Disabling just the extra RX delay (`0x1056`) allowed small packets but failed
  at larger payloads. Clearing both extra delay bits (`0x1046`) passed all five
  echo sizes and TCP. The firmware retains/restores the original volatile PHY
  setting. This is a measured remedy for this PCB/handoff, not a universal PHY
  timing rule. No PHY EEPROM/NVM write is involved.
- Fresh bootstrap left CNTFRQ_EL0 zero. This image programs the profile's
  400 MHz value, then the host independently checks ticks against wall time.
- Cache mode materially changes throughput. Default CPU RAM is write-back;
  DMA descriptors/buffers at `0x85000000`–`0x853fffff` stay normal noncacheable.
  Translation probes verify attributes. `NET_CACHED=0` gives the baseline.
  This copy-based design does not qualify coherent DMA or zero-copy networking.
- An initial parallel receive test stalled with the smaller pool and unbounded
  out-of-order buffering. The revised configuration bounds per-connection
  out-of-order pbufs, increases the pool, reports resource counters and allows
  ten seconds for a socket stall. Keep this as the tested configuration; the
  first failure alone did not isolate which change resolved it. lwIP already
  checks out-of-order pool reclamation in `sys_check_timeouts()`.

## Interpret results

Start with ping, counter calibration, exact echoes at 64/256/512/1024/1472
bytes, duplicate/reordering/corruption controls, and TCP pattern validation.
Use `--tcp-stress --seconds 10 --soak-seconds 0` to isolate four-stream and
simultaneous TCP. The default campaign then performs UDP rate/payload sweeps,
three 30-second repeats, four-stream tests and a 600-second simultaneous soak.

This uses a custom protocol on UDP 5001–5003 and TCP 5004–5005. iperf2/iperf3
clients do not interoperate. Report receiver payload goodput, actual offered
rate and loss separately. High-rate UDP loss is a saturation measurement;
payload corruption is a failure. Host TCP retransmission counters describe
only the local sender. A 1 Gb/s link is not a measured application bandwidth.
See timestamped `bandwidth.json`, CSV, `results.json`, UART, bootstrap and restore
logs; do not turn one short sweep into a sustained or theoretical maximum claim.
