# SOM HPS Ethernet bandwidth lab

Real EMAC2 DMA + lwIP 2.2.1 on the Modular ES SOM, with custom UDP/TCP host
benchmarks. No OS runs on the HPS. The example uses the established matching
SOF/handoff and fresh DDR bootstrap. See [the tutorial](../../../docs/examples/ethernet.md).

From the example-pack directory, in the compiler container:

```sh
./ethernet/build.sh
# Optional noncacheable CPU baseline:
NET_CACHED=0 ./ethernet/build.sh
```

The default enables CPU cache while keeping all DMA buffers/descriptors in
separate normal-noncacheable DDR blocks. The firmware verifies translation
attributes. This does not establish hardware DMA cache coherency.

From the configured Linux host, after connecting the SOM HPS Ethernet jack
directly to a dedicated PC NIC:

```sh
python3 ethernet/run.py --interface YOUR_WIRED_NIC --smoke
python3 ethernet/run.py --interface YOUR_WIRED_NIC
```

The default run performs functional checks, UDP rate/payload sweeps, three
30-second TCP/UDP repeats in both directions, four-stream TCP, simultaneous
TCP and a 600-second simultaneous TCP soak. Allow around 20 minutes plus boot.
A shorter exploratory run is `--quick --seconds 5 --soak-seconds 0`.

The host runner uses the existing container's root user only to add/remove the
temporary address on the selected dedicated NIC; JTAG tools run as the
configured container user. A dedicated interface must be unaddressed, or already
have exactly `192.168.50.1/24`. The board is `192.168.50.2/24` with local MAC
`02:00:00:a5:05:02`. Default routes and other interfaces are not reconfigured.
Do not use this fixed-address example on a shared production subnet.

The runner holds hardware ownership, records binary hashes/UART/JSON/CSV,
restores the original PHY delay setting on firmware stop, restores DDR Hello,
and removes only an address it added. Use repeated `--coordination-lock PATH`
arguments to coordinate other checkouts sharing this same physical board.
Generated images and downloaded lwIP sources are ignored. The build checks the
exact upstream commit and writes `build/network.json`.
