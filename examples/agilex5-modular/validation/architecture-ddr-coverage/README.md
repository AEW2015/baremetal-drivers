# DDR separation, example coverage and complete block navigation

Executed on 2026-10-30 using Chromium with external networking disabled.
All 16 browser checks passed with zero JavaScript errors. The report includes
153 pointer/navigation records: every one of the 71 overview shapes, all 80
architecture blocks in their hierarchy, and two parsed RTL children.

Each overview shape was pointer-clicked at an exposed point belonging to that
exact node, including container frames and repeated CPU/PHY targets. The test
then used Show in hierarchy and verified the selected path. Every architectural
block was pointer-clicked in its parent view, checked for its coverage marker,
opened when it contained children, and tested with Up. Up was checked to retain
the subsystem just left selected in the correct parent view. At the system
level Up is intentionally disabled and labeled top.

The checks exposed and fixed missing selection when returning to the custom
system overview, including the formerly absent HPS DDR root target. Generation
now requires an overview target for every root subsystem.

HPS DDR bank 3A and fabric DDR are explicitly distinct. Fabric DDR and its EMIF
and external-memory children have no mapped bare-metal example. The 26 uncovered
architecture paths are listed in blocks-without-examples.json. Markers use the
complete catalog independently of example/platform filters; a subsystem can be
associated through its children without every function being exercised.

All 81 example selections and all 28 embedded pages/81 catalog links passed.
Four representative embedded viewers were also exercised. Reproduce with the
commands in tools/architecture/README.md. Source/asset hashes, real screenshots,
exported SVG and detailed reports are retained here. No hardware was accessed;
these results do not qualify fabric DDR or extend physical-board coverage.
