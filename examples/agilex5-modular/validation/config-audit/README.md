# Read-only configuration audit evidence

Executed on 2026-10-30. System Manager and pinmux snapshots and the deliberate
unstable-read control passed in both the Agilex 5 Simics model and the physical
Modular ES kit. The negative control passes when the guest reports status=1
for the injected mismatch; it is not a failing physical register observation.

The physical runner held the shared hardware mutex, checked the JTAG identity,
initialized HPS DDR before each guest, verified the loaded payload by readback,
and restored DDR Hello successfully. Results include ELF/source hashes, UART,
bootstrap/debug logs and restoration status. No system-manager or pinmux
configuration registers were written by the guests; UART output uses writes.

Read-only snapshot PASS means the named registers were readable and stable,
not that every field or peripheral function was correct. The separate handoff
comparison matched PIN2SEL=5, PIN3SEL=5 and UART0_USEFPGA=0 against the recorded
profile's big-endian handoff (SHA in the comparison reports). The private
handoff binary is not redistributed. A deliberately changed expected-route
snapshot is rejected; parser/assessor tests also reject malformed or incomplete
captures. See docs/config-audit.md for commands and limitations.

Simics and physical results are distinct. Neither result qualifies all pinmux
routes, System Manager functionality, or new security/clock configuration.
