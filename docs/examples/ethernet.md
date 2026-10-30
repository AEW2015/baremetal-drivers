# Ethernet bandwidth: UDP and TCP

This lab adds actual packet TX/RX to the earlier [PHY identification](interfaces.md)
example. It targets the **SOM HPS Ethernet jack**, EMAC2 and Marvell 88E1512 on
the established Modular ES bench, connected directly to a Linux PC.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](../assets/architecture/design.html?example=custom%2Fethernet){ .md-button }
[Full architecture guide](../architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../../assets/architecture/design.html?example=custom%2Fethernet" data-example-id="custom/ethernet">custom/ethernet</a></p>
<iframe class="example-diagram" src="../../assets/architecture/design.html?example=custom%2Fethernet" title="HPS and fabric diagram for examples/ethernet.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

=== "Purpose"

    Run a freestanding lwIP stack on A55.0, validate payloads, and measure
    application throughput in both directions. Start with the smoke test before
    interpreting bandwidth. A 1 Gb/s PHY link is not a promise of 1 Gb/s payload
    throughput from this software adapter.

    The pinned 25.1 reference’s `xgmac_send`/`xgmac_recv` are stubs. This lab supplies a
    separate single-queue DMA adapter; it does not mistake the register test or
    internal loopback sample for external network traffic.

=== "Memory and driver"

    | Region | Purpose |
    |---|---|
    | `0x82600000` to below `0x83400000` | Network code, lwIP heap, validation bitmap and globals |
    | Below `0x83fff000` | Reserved CPU stack |
    | `0x85000000` / `0x85001000` | TX/RX descriptor rings, 64 entries each |
    | `0x85100000` / `0x85200000` | TX/RX buffers, 2048-byte strides |
    | `0x10830000` | EMAC2 registers |

    These scratch ranges are exclusive to the diagnostic session. The default
    build caches CPU RAM, while `0x85000000`–`0x853fffff` remains normal
    noncacheable memory. Address-translation probes check code and both DMA
    blocks before traffic. DMA descriptors are published with barriers and
    returned to hardware only after the input packet has been copied.

    `NET_CACHED=0` provides a noncacheable CPU baseline. Both builds use software
    checksums, copied buffers, one polling core and MTU 1500. They do not test
    coherent DMA or claim a zero-copy implementation.

=== "Build"

    In the configured compiler environment, from `examples/agilex5-modular`:

    ```sh
    ./ethernet/build.sh
    ```

    Requires Arm GNU 13.2.Rel1's `aarch64-none-elf-*` tools and Git. The script
    fetches lwIP tag `STABLE-2_2_1_RELEASE`, requires commit
    `77dcd25a72509eb83f72b033d219b1d40cd8eb95`, and writes
    `build/network.elf`, its map and `build/network.json` with source/ELF hashes.
    A changed dependency checkout is rejected. Its BSD license stays with the
    downloaded sources. The compact linker layout can emit the documented
    [RWX warning](../troubleshooting.md#rwx-linker-warning).

    Captured output from the cached build (final size report):

    ```text
       text	   data	    bss	    dec	    hex	filename
     139680	   3192	5785896	5928768	 5a7740	build/network.elf
    ```

    The [full build log](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/ethernet/build-all.log) also records the expected RWX
    warning. Addresses and memory use can change with source/tool versions.

    To compare CPU memory configurations:

    ```sh
    NET_CACHED=0 ./ethernet/build.sh
    # Run and retain that result before rebuilding the default:
    NET_CACHED=1 ./ethernet/build.sh
    ```

=== "Connect and run"

    First complete [hardware setup](../hardware.md), including the matching
    FPGA/DDR image and host/container mapping. Close serial terminals and other
    board debuggers. The host runner requires Docker access to the configured
    hardware container, including its root account for temporary NIC addressing.
    Start that container with `--network host --cap-add NET_ADMIN` as described
    in [Ethernet container access](../container.md#ethernet-access).

    On the **Linux host**, inspect `ip -br address` and `ethtool YOUR_WIRED_NIC`.
    Select the directly connected NIC explicitly:

    ```sh
    source "$HOME/.config/agilex5/hardware.env"
    cd /host/path/to/baremetal-drivers/examples/agilex5-modular
    python3 ethernet/run.py --interface YOUR_WIRED_NIC --smoke
    python3 ethernet/run.py --interface YOUR_WIRED_NIC
    ```

    The NIC must have no IPv4 address, or already have only `192.168.50.1/24`.
    The runner adds that address temporarily when needed and rejects overlapping
    routes. The firmware uses `192.168.50.2/24`. It does not replace a default
    route or change Wi-Fi configuration. Other clones sharing the board should
    participate in the same ownership scheme via `--coordination-lock PATH`.

    A short exploratory run is:

    ```sh
    python3 ethernet/run.py --interface YOUR_WIRED_NIC --quick --seconds 5 --soak-seconds 0
    ```

=== "Expected results"

    These are **captured terminal excerpts** from the 24 October 2026 hardware
    campaign, not invented sample output. Boot chatter and intervening benchmark
    repetitions are omitted. UART and host output are shown separately because
    they can interleave in the terminal. Interface names, paths, timings and
    throughput will vary; compare PASS markers, payload checks and restoration.

    **1. Firmware startup — SOM UART**

    ```text
    MEMORY MODE: cached CPU, noncacheable DMA
    HPS NETWORK BENCH BEGIN
    Counter frequency0x0000000017d78400
    PER0MODRST0x0000000000000000
    SYSMGR_EMAC20x0000000000000001
    EMAC2_USEFPGA0x0000000000000000
    PHY control0x0000000000001140
    PHY status0x000000000000796d
    PHY resolved0x000000000000bc08
    PHY RGMII timing before0x0000000000001076
    PASS NETWORK_LINK: 1000 Mbps full duplex
    READY NETWORK: 192.168.50.2 UDP control=5001 echo=5002 sink=5003 TCP sink=5004 source=5005
    ```

    The default cached build must identify normal-noncacheable DMA memory,
    establish 1000 Mb/s full duplex, and print `READY NETWORK`. The recorded PHY
    timing value is the original setting before this bench's volatile adjustment.

    **2. Functional checks — host runner**

    ```text
    PASS ARP_PING
    PASS counter_calibration
    PASS udp_echo
    PASS udp_sequence_and_corruption_controls
    PASS tcp_board_receive
    PASS tcp_board_transmit
    ```

    `--smoke` runs these checks without the bandwidth campaign. `udp_echo`
    verifies exact payloads at 64, 256, 512, 1024 and 1472 bytes. The sequence
    check deliberately injects duplicates, reordered packets and one corrupt
    payload; PASS means those cases were classified correctly. Both TCP
    directions verify their payload patterns. Counter calibration independently
    compares the configured 400 MHz counter with the host clock.

    **3. Ping — saved `ping.log`**

    ```text
    PING 192.168.50.2 (192.168.50.2) from 192.168.50.1 enp111s0: 56(84) bytes of data.
    64 bytes from 192.168.50.2: icmp_seq=1 ttl=255 time=0.041 ms
    64 bytes from 192.168.50.2: icmp_seq=2 ttl=255 time=0.055 ms
    64 bytes from 192.168.50.2: icmp_seq=3 ttl=255 time=0.048 ms

    --- 192.168.50.2 ping statistics ---
    3 packets transmitted, 3 received, 0% packet loss, time 2053ms
    rtt min/avg/max/mdev = 0.041/0.048/0.055/0.005 ms
    ```

    The runner saves ping output instead of echoing it to the terminal. Expect
    three replies and zero loss; the round-trip timings are measurements from
    this direct connection, not required exact values.

    **4. UDP saturation — host runner**

    This contiguous excerpt corresponds to requested rates of 100, 250, 500
    and 900 Mb/s into the SOM. The printed Mb/s value is receiver payload
    goodput; `loss` is the fraction of sent datagrams not received.

    ```text
    MEASURE udp_ramp pc_to_som 99.998 Mbps loss=0.000000
    MEASURE udp_ramp pc_to_som 197.864 Mbps loss=0.208529
    MEASURE udp_ramp pc_to_som 197.876 Mbps loss=0.604243
    MEASURE udp_ramp pc_to_som 197.875 Mbps loss=0.779977
    ```

    This shows receive saturation, not a successful loss-free 900 Mb/s receive
    test. In the other direction, the last two three-second sweep steps were:

    ```text
    MEASURE udp_ramp som_to_pc 500.044 Mbps loss=0.000000
    MEASURE udp_ramp som_to_pc 900.134 Mbps loss=0.000000
    ```

    The benchmark also checks all five payload sizes, then repeats conservative
    UDP rates and single-stream TCP three times for 30 seconds. Selected captured
    lines below show the first repeat in each direction; intervening tests are
    omitted between these two excerpts.

    **5. Sustained UDP and TCP — host runner**

    ```text
    MEASURE udp_repeat pc_to_som 79.998 Mbps loss=0.000000
    START TCP pc_to_som streams=1 seconds=30
    MEASURE tcp_repeat pc_to_som 229.516 Mbps loss=0.000000
    ```

    ```text
    MEASURE udp_repeat som_to_pc 720.025 Mbps loss=0.000000
    START TCP som_to_pc streams=1 seconds=30
    MEASURE tcp_repeat som_to_pc 949.254 Mbps loss=0.000000
    ```

    For TCP, the console's `loss=0.000000` is a generic formatter field, **not
    a measured TCP packet-loss or retransmission count**. TCP payload/count
    mismatches fail the run. The JSON contains byte counts and local-sender
    retransmission statistics; those do not count the board sender's retries.

    **6. Ten-minute soak and restoration — host runner**

    The final lines of the default campaign were:

    ```text
    PROGRESS tcp_bidir pc_to_som: 600s, 258.396 Mbps
    PROGRESS tcp_bidir som_to_pc: 600s, 68.922 Mbps
    MEASURE tcp_soak completed
    [restore] Restoring DDR Hello; inspect restore.log for live stages.
    DDR Hello restoration: pass
    ```

    `--smoke` and `--quick --soak-seconds 0` do not print the soak lines.
    Require successful restoration as well as test completion. The runner also
    removes any host address it added; confirm `host_address_restored: true`
    and the before/after interface state in `results.json`. High-rate UDP loss
    remains recorded even when the campaign completes.

    Read the complete [terminal capture](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/ethernet/attempts/ethernet-20261024T154231.864079Z/terminal.log),
    [UART capture](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/ethernet/attempts/ethernet-20261024T154231.864079Z/server-uart.txt),
    [ping log](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/ethernet/attempts/ethernet-20261024T154231.864079Z/ping.log) and
    [structured results](https://github.com/AEW2015/baremetal-drivers/blob/main/examples/agilex5-modular/validation/ethernet/attempts/ethernet-20261024T154231.864079Z/results.json).
    New run evidence is under `runs/ethernet-<UTC>/`.

=== "Measured hardware results"

    The complete 24 October 2026 campaign passed all 40 measurements and the
    ten-minute simultaneous TCP soak on the direct SOM-to-PC connection.

    | Receiver payload goodput | PC → SOM | SOM → PC |
    |---|---:|---:|
    | UDP, conservative rate with no measured loss | 80 Mb/s | 720 Mb/s |
    | TCP, mean of three 30-second single-stream tests | 230 Mb/s | 949 Mb/s |
    | TCP, 600 seconds simultaneously | 258 Mb/s | 69 Mb/s |

    These are measurements for the recorded board, handoff and software, not
    minimum performance requirements. UDP receive saturates near 198 Mb/s and
    loses packets at higher offered rates. Read the
    [full results, plots, failures and raw evidence](../ethernet-validation.md)
    before comparing a different setup.

=== "Protocol and files"

    | Port | Firmware endpoint |
    |---|---|
    | UDP 5001 | Fixed-size binary control; JSON statistics reply |
    | UDP 5002 | Payload echo |
    | UDP 5003 | Sequence-numbered, pattern-checked receive sink |
    | TCP 5004 | Pattern-checked receive sink |
    | TCP 5005 | Pattern-producing transmit source |

    The host uses ordinary Python sockets with this custom protocol.
    **iperf2 and iperf3 clients are not compatible with these endpoints.**
    The protocol is a test interface for this dedicated link, not a general
    authenticated network service.

    Source: [Ethernet example folder](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/ethernet).
    lwIP supplies ARP, IPv4, ICMP, UDP and TCP; `mac.c` handles descriptors,
    `platform.c` handles memory attributes/time, `main.c` supplies endpoints,
    `peer.py` checks traffic and `run.py` owns programming and recovery.

=== "Troubleshooting"

    - **Link is down or 100 Mb/s:** verify the SOM jack, peer, cable and PHY
      negotiation. This version requires 1000 Mb/s full duplex.
    - **TX works, RX has CRC errors:** inspect PHY timing and the actual handoff.
      On this bench, the extra page-2/register-21 RX/TX delay bits had to be
      cleared for its RGMII configuration. The original value is retained and
      restored on stop. Do not treat this as a universal setting for other PCBs.
    - **Small packets work but larger packets fail:** verify both directions,
      PHY timing, CRC counters, descriptor ownership, buffer lengths and payload
      checks. A PHY ID or small ping alone is insufficient.
    - **Control timeout:** the runner requests a UART register dump before
      restoration. Inspect `server-uart.txt`, `load.log`, packet capture and
      host NIC counters. The first bare-metal attempts are retained as failures.
    - **Low throughput with zero corruption:** compare cache modes and offered
      versus received rate. CPU polling, software checksums, buffer copies,
      noncacheable DMA access and host packet generation all have costs.
    - **Busy hardware or uncertain cancellation:** respect ownership records
      and the shared lock. Do not delete them or start another programmer.

    The upstream XGMAC register layout and Marvell PHY definitions were checked
    against [U-Boot v2025.10](https://github.com/u-boot/u-boot/tree/v2025.10/drivers/net).
    No clock NVM, EEPROM array, SD media or flash writes are part of this test.
