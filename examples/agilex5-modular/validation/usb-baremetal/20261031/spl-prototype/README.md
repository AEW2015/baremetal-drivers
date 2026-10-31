# Failed SPL boot investigation

These are archived experimental sources, build logs, configuration, FIT recipe
and diagnostics, not an executable tutorial or a validated loader. Do not run
this archived host runner from this location: its ROOT calculation assumed its
original development path. Its FIT-load and second-stage launch paths never
ran on hardware and are unqualified. The existing USB runner remains unchanged.

The HPS-only reload and full matching merged-SOF load both missed the SPL
ready marker. In the full-image attempt secure JTAG register and stack reads
established PC 0xd1b0 (`hang`), stack caller 0x1290: the branch after a nonzero
`spl_early_init()` return, before clock/pinmux/DDR/USB initialization. The exact
return code and root cause were not captured. This does not test USB or prove
that a complete normal U-Boot boot cannot detect the drive.

The normal-entry BL31, RAM FIT and SPL compiled; SHA-256 identities are in
metadata.json. The FIT contains BL31 and guarded U-Boot only, no FPGA payload.
SPL was derived from the pinned A0 Modular defconfig with simulation targets
disabled, a bounded OCRAM wait added after DDR setup, and RAM-only boot order.
The complete chain never reached that wait. Both attempts restored DDR Hello.

Failed direct-command diagnostics are retained alongside the successful
file-based diagnostic. The vendor OpenOCD launcher can mishandle Tcl command
quoting; its apcsw query returns descriptive text, which must be parsed before
restoring CSW. The archived experimental runner still inherits the unvalidated
direct-command second-stage path. No second-stage launch success is claimed.
