# Exercise the native Simics fabric PIO models

This lab uses the Agilex universal platform's existing behavioral PIO models.
It is separate from the [actual RTL connected through Verilator](simics-rtl.md).
The guest reads modeled button/switch inputs and the system-ID window, writes
two LED-data patterns, checks readback and restores the original LED value.
It does not exercise physical SOM buttons, LEDs, or FPGA RTL.

<!-- example-architecture:start -->
[Open this example in the HPS / fabric diagram](assets/architecture/design.html?example=model%2Fpio){ .md-button }
[Full architecture guide](architecture.md)

<details class="example-architecture">
<summary>Show the clickable HPS / fabric diagram here</summary>
<p>Click blocks for related examples, platform results, source and evidence. This is a TRM-based functional map; proposed fabric and Simics models are labeled separately.</p>
<p class="example-diagram-links"><a href="../assets/architecture/design.html?example=model%2Fpio" data-example-id="model/pio">model/pio</a></p>
<iframe class="example-diagram" src="../assets/architecture/design.html?example=model%2Fpio" title="HPS and fabric diagram for model-audit.md" width="100%" height="680" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>
</details>
<!-- example-architecture:end -->

## Address map and scope

| Target | Guest address | What the test establishes |
|---|---|---|
| System-ID window | `0x20010000`, 8 bytes | Stable read of the configured model memory, not a nonzero identity requirement |
| Button DATA | `0x20010060` | Stable modeled bit-0 input; no external transition or interrupt claim |
| DIP-switch DATA | `0x20010070` | Stable modeled bit-0 input; no external switch stimulus claim |
| LED DATA | `0x20010080` | 32-bit modeled output-data readback and restoration |

These addresses are the modeled lightweight-HPS-to-FPGA aperture
`0x20000000` plus the peripheral subsystem's local offsets. The model's
32-bit LED-data register does not imply that the physical board has 32 LEDs.
Use the matching Platform Designer address map for a physical design.

The [mapping audit](example-mapping-audit.md) also identifies the separate
1 MiB behavioral memory behind the existing HPS2FPGA bridge-loopback test.
That memory is distinct from HPS DDR bank 3A and from this PIO register map.

## Run the guest

In the Linux development container, from `examples/agilex5-modular`, first
deploy Simics and build its OCRAM bootstrap using [the Simics setup](simics.md).
Then build the two PIO guest variants and run them:

```sh
bash model-audit/build.sh
python3 model-audit/run.py --only pio,mask-negative
```

The build uses the AArch64 compiler prefix `UPSTREAM_CROSS_COMPILE`, defaulting
to `aarch64-linux-gnu-`. The runner accepts `--project` and `--boot` to select
an existing deployment and bootstrap. Each case starts a fresh model, performs
the modeled DDR initialization, and loads the guest at `0x82100000`.

The `pio` case must check both LED patterns and restoration before completing.
The `mask-negative` case additionally writes a known-good value with bit 31
set and demonstrates that an expectation using a mask which omits that bit
must reject the value. This is a deliberate bad-expectation exercise, not a
hardware fault or a failed physical register read.

## Captured output and evidence

The positive case produced this actual UART output:

```text
PIO_AUDIT_BEGIN
BUTTON_DATA=0x0000000000000000
DIPSW_DATA=0x0000000000000000
SYSID_DATA=0x0000000000000000
PASS BUTTON_INPUT stable, field=bit0
PASS DIPSW_INPUT stable, field=bit0
PASS SYSID 64-bit read stable
LED_DATA_SAVED=0x0000000000000000
LED_READBACK_A=0x00000000a55aa55b
PASS LED pattern A readback
LED_READBACK_B=0x000000005aa55aa5
PASS LED pattern B readback
PASS LED original value restored
PIO_AUDIT_COMPLETE status=0
```


The [recorded PIO execution evidence](https://github.com/AEW2015/baremetal-drivers/tree/main/examples/agilex5-modular/model-audit/validation)
contains actual UART and terminal logs, build/source hashes, register metadata,
and per-case results. A simulator exit code of zero alone is insufficient:
the runner requires the input, LED-pattern and restore markers plus guest
completion. The negative case must also report the bad-mask rejection.

If a new model version changes its PIO mapping, widths or access semantics,
inspect the installed model's register information and component map before
changing expectations. Do not relax readback checks to force a PASS. Physical
execution remains unqualified until a matching design and separate board run
are available.
