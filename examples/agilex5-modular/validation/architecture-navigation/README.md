# TRM layout and navigation validation

Actual Chromium execution on 2026-10-30, with external networking disabled.
All 14 browser checks passed, including all 81 example selections, Back/Up
restoration of level and selection, keyboard shortcuts, exact TRM topic IDs,
legacy deep links, parsed RTL drill-down, SVG/PNG export and mobile layout.
No JavaScript errors occurred. The integration check also passed all 28 embedded
example pages, 81 catalog links and four representative browser embeds.

The independent system redraw follows TRM Figure 1 grouping and colors, with
77 architecture blocks and 48 direct TRM topic references. Official artwork is
not bundled. Screenshots and the exported SVG record the actual rendered UI;
`diagram-build.json` records the generated asset and source hashes. Earlier
`../architecture/` evidence describes the previous 61-block layout.

Reproduce using the commands in `tools/architecture/README.md`, including the
browser and embedded-page checks after a strict MkDocs build. These checks
validate the UI and mappings; they do not add hardware qualification.
