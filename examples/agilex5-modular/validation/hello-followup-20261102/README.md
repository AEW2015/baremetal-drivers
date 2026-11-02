# Hardware Hello retry, 2026-11-02

The user ran the documented hardware command against source commit `e00edff`.
The first run was interrupted during initial Programmer MCP JTAG discovery;
no payload or bootstrap was attempted. Its older runner reported restoration
failure because the interrupted MCP connection had exited. The cause of the
initial discovery delay is unproven.

The second run discovered the board successfully, bootstrapped DDR, executed
`hello_selftest`, verified its completion and restored DDR Hello. The shared
mutex was free afterward. Captures retain both attempts and the actual payload
readback, debugger and bootstrap evidence. UART line endings/NUL bytes are
rendered for review; original/saved hashes are in `copied-evidence.json`.

The follow-up runner adds stage messages, releases its mutex on MCP startup
failure and skips restoration if initial discovery fails before any bootstrap
or payload attempt. Three injected connection/interruption regression tests
verify that restoration is still attempted once a bootstrap was started.
The full 109-test unit suite passed with one skip. These runner changes were
tested with injected failures; the physical retry above used the prior runner.
