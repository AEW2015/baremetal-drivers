# Follow-up tasks

- [ ] Walk through the Simics and Verilator workflows together in a guided session.
  - Run `fabric/test.sh` and explain both ADD/XOR PASS lines.
  - Trace one driver read/write through the callbacks in `lab_driver.c`, the
    Avalon bus harness in `fabric/tests/test_lab.cpp`, and the actual RTL.
  - Demonstrate the missing-DONE failure and bounded polling; inspect signals
    with a waveform trace if added for the session.
  - Build/run an AArch64 example in Simics and compare that execution path with
    the host-compiled driver/RTL harness.
  - Review the physical MMIO backend, HPS bridge setup, and checks still needed
    before deploying the arithmetic IP to the Modular kit.
  - Decide whether to implement a Simics-to-Verilator MMIO adapter afterward;
    define address mapping, clock/time coordination, reset and error handling.

Paths above are relative to `examples/agilex5-modular/`. The current Simics and
Verilator tests run separately; a combined adapter is not implemented.

Preparation: [fabric lab](docs/fabric-ip.md), [Simics lab](docs/simics.md), and
[harness source](examples/agilex5-modular/fabric/tests/test_lab.cpp).

- [ ] Complete the [HPS DDR and missing-example roadmap](docs/example-roadmap.md).
  Track evidence/mapping fixes separately from new examples and physical-board
  qualification. Separate fabric DDR/EMIF is excluded from this work.
