# Direct SOM Type-C-controller diagnostic

This is an isolated FPGA diagnostic for the **Modular ES
A5ED065BB32AE6SR0**, using the qualified 26.3 platform as its input. It adds
open-drain I2C access on SOM **BR28 (SCL)** and **BR31 (SDA)**, the bus containing
HD3SS3220 `0x47`. The HPS management GPIO bus is a separate route.
The HPS, DDR, USB controller and existing handoff configuration are retained.
The original platform directory is never edited.

By default, `cc_reader.sv` sets the register pointer with **0x8e, 0x00**,
sends repeated START and **0x8f**, and receives 11 bytes from address `0x47`.
The default build cannot send target-register configuration data. An initial
hardware prototype obtained a valid first capture with a direct read, but its
repeat capture failed the identity check. The maintained reader explicitly
resets the pointer for every capture. See
[TI HD3SS3220, sections 6.5.3 and 6.6](https://www.ti.com/lit/ds/symlink/hd3ss3220.pdf).

The reader waits for an idle bus, uses clock-stretch-aware open-drain outputs,
checks arbitration while transmitting released bits, ACKs ten bytes, NACKs
the final byte, and sends STOP. A 40-ms transaction watchdog releases both
lines; a busy bus fails after 2 ms. Source inputs pass through two registers.
At the platform's 100-MHz clock, the bit state machine produces
about 13.3-kHz SCL without stretching (three ticks per data bit, 25 us/tick).
No Type-C power role, VBUS switch, reset net, clock configuration or NVM is
changed by a read. An explicitly enabled second variant supports the limited
volatile mode procedure below.

## Build and verify

Run from `examples/agilex5-modular` in the configured compiler environment:

```sh
verilator --lint-only --top-module cc_reader -Wall usb-linux/cc-probe/cc_reader.sv
iverilog -g2012 -s test_cc_reader -o build/usb-linux/cc-reader-test \
  usb-linux/cc-probe/cc_reader.sv usb-linux/cc-probe/test_cc_reader.sv
vvp build/usb-linux/cc-reader-test
```

The testbench exercises an I2C slave model with a retained, initially nonzero
pointer, checks the exact pointer/read sequence, verifies all 11 data bytes
and the final NACK/STOP, and injects
clock stretching, an address NACK, an occupied bus, arbitration loss and a
stuck clock. It requires `CC_READER_TEST_PASS`.

Create a fresh copy of the matching local platform, with generated IP products
already present:

```sh
python3 usb-linux/cc-probe/prepare.py \
  --source "$QUALIFIED_MODULAR_ES_PLATFORM" \
  --output build/usb-cc26.3/platform
```

Compile that copy with Quartus 26.3. Inspect the fitted pin assignments, final
timing and the checked SDC collections before deployment. The custom qualified
platform is an external bench prerequisite; this small overlay alone is not a
complete independently qualified public FPGA build. `cc-probe-manifest.json`
records the input platform and diagnostic hashes.

The fitted SOF must be paired with the matching DDR boot firmware with
**LWH2F enabled**, loaded under the hardware mutex and verified through the
normal DDR bootstrap. Preserve the existing known-good recovery image.
A source simulation pass does not qualify a new physical image.

## Register access

The diagnostic reuses the existing LED and switch PIO registers, behind the
HPS lightweight bridge:

| CPU address | Diagnostic use |
|---|---|
| `0x20010080` | LED PIO output: toggle bit 31 to start; command 10:8 (0=read); bits 7:4 select byte 0..10; selector 15 returns signature `0xcc`; LED bit 0 retains its function |
| `0x20010070` | Switch PIO input: done 31, busy 30, error 29:26, fault_n 25, VBUS detector 24, ID 23, SCL 22, SDA 21, accepted trigger 20, signature 19:16=`0xc`, write capability 15, accepted command 10:8, selected byte 7:0 |

This variant replaces the physical DIP-switch readout with the diagnostic
status. Error values: 1 target NACK; 2 bus never became idle; 3 arbitration
lost; 4 watchdog; 5 invalid FSM state; 6 rejected command. The other values are reserved.

After loading and qualifying the matching image:

```sh
python3 usb-linux/cc-probe/read.py
```

The host runner acquires the shared mutex, verifies the fresh Modular ES JTAG
identity and mount, and uses the HPS memory AP without halting Linux. It checks
the diagnostic signature and trigger PIO readback, requires a fresh busy-to-done
transition, then requires every register and the HD3SS3220 identity before
decoding role. Selecting a byte retains the trigger toggle, so it does not
start another transfer. A missed busy transition fails conservatively.

A successful CC capture establishes controller identity and sampled attach
state. It does not qualify the USB hub, storage, HID, Ethernet, connector
voltage or USB-PD messages. Those need their own observed transactions.

## Optional host-mode experiment

The initial read-only hardware capture found `ATTACHED_STATE=2` (UFP/sink),
despite Linux running as USB host. This is a measured role mismatch, not yet
proof that it is the only problem or that this dock can attach without PD.

The explicit `--enable-mode-writes` preparation flag builds a variant with
`ALLOW_MODE_WRITES=1`. It additionally permits only address **0x47**, register
**0x0a**, values **0x01, 0x21, 0x20, 0x00**. No arbitrary target/register/value,
I2C soft-reset command or NVM operation is exposed. Commands 1/2 select default/
DFP mode with termination disabled; commands 3/4 enable DFP/default mode.

TI section 6.3.1 documents disabling termination, selecting DFP, then
re-enabling termination. Section 6.6.4 requires mode changes while unattached.
Physically unplug the dock from the SOM before this experiment. The host
tool checks a fresh controller identity, write capability, unattached state
and known General Control value before the sequence. It verifies every write
by a separate read. Unexpected fields are rejected rather than overwritten.
Both host tools check the LWH2F reset bit before fabric access and track their
owned OpenOCD process so cancellation can finish before releasing the mutex.
`configure.py --mode dfp --check-only` performs only the read/eligibility check
and reports a plan if eligible; it sends no mode write.

After fitting, timing-checking, pairing and loading the explicit variant:

```sh
python3 usb-linux/cc-probe/configure.py --mode dfp
```

Only reconnect the dock after verified completion, then use `read.py` and the
Linux inventory/class tests to determine what actually attached. Successful
configuration alone is not a successful dock test. To restore the original
General Control `0x00`, unplug the dock again and run:

```sh
python3 usb-linux/cc-probe/configure.py --mode default
```

Failure records are retained. An uncertain write needs a fresh read; the tool
does not change modes behind an attached peer to conceal a failed experiment.
