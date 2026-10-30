# Roadmap integration browser validation

Actual Chromium execution on 2026-10-30, with external network access disabled.
All 16 browser checks passed for the 86-entry catalog and 79 architecture blocks.
All 151 pointer/navigation records passed: 70 overview targets, 79 architectural
blocks and two parsed RTL children. All 31 embedded example pages and 86 catalog
links passed; seven representative embedded viewers were also opened and checked.
No JavaScript errors occurred.

The diagram separates the proven SOM RGMII/MDIO path from the architectural
SERDES option and adds a separate actual-RTL Simics/Verilator context. Reviewed
associations plus new configuration and PIO labs reduce the original 23 missing
coverage items to 16. The missing markers remain independent of filters.

This is UI/mapping validation only. Physical configuration snapshots and modeled
PIO/RTL results retain their own execution evidence and validation boundaries.
Reproduce with tools/architecture/README.md.
