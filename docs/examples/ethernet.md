# Ethernet bandwidth: UDP and TCP

This lab adds actual packet TX/RX to the earlier [PHY identification](interfaces.md)
example. It targets the **SOM HPS Ethernet jack**, EMAC2 and Marvell 88E1512 on
the established Modular ES bench, connected directly to a Linux PC.

=== "Purpose"

    Run a freestanding lwIP stack on A55.0, validate payloads, and measure
    application throughput in both directions. Start with the smoke test before
    interpreting bandwidth. A 1 Gb/s PHY link is not a promise of 1 Gb/s payload
    throughput from this software adapter.

    The supplied upstream `xgmac_send`/`xgmac_recv` are stubs. This lab supplies a
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

    Smoke checks require:

    - `PASS NETWORK_LINK: 1000 Mbps full duplex` and `READY NETWORK` on fresh UART.
    - Successful ARP/ping and an independently checked 400 MHz counter rate.
    - Exact UDP echoes for 64, 256, 512, 1024 and 1472-byte payloads.
    - Correct duplicate, out-of-order and deliberately corrupted UDP detection.
    - Verified TCP payloads into and out of the board.

    The normal benchmark sweeps requested UDP payload rates from 1 to 900 Mb/s
    at 1472 bytes, characterizes all five payload sizes, then repeats conservative
    stable UDP rates and single-stream TCP three times for 30 seconds. It also
    runs four-stream TCP, simultaneous TCP and a ten-minute simultaneous TCP soak.

    Each run records requested rate, actual offered rate, receiver goodput, loss,
    duplicates, reordering, corruption, source errors and board statistics.
    High-rate UDP loss is a measured result, not hidden by a PASS marker. TCP
    payload/count mismatches fail the run. TCP retransmissions reported by the
    host describe its local sender; they do not count the board sender's retries.

    A successful completion requires DDR Hello restoration and removal of any
    host address added by the runner. Evidence is under `runs/ethernet-<UTC>/`.

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
