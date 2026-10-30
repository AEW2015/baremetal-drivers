# HPS-DDR-only diagram scope

Actual Chromium execution on 2026-10-30 with external networking disabled.
All 16 browser checks passed with zero JavaScript errors, including all 81
example selections and 147 pointer/navigation records: 68 overview targets,
77 architecture blocks and two parsed RTL children. Up destinations, retained
selection and missing-example markers passed the exhaustive checks.

The separate fabric-DDR/EMIF group and its child definitions were removed.
HPS DDR bank 3A remains visible. No new example or hardware PASS is claimed.
All 23 remaining unmapped architecture paths are included in the new Markdown
checklist at docs/example-roadmap.md; phase dependencies and acceptance evidence
are recorded there. Earlier architecture-ddr-coverage evidence retains its
historical scope and is superseded for the current diagram by this record.

The strict MkDocs build and checks of 28 contextual embeds, 81 catalog links
and four representative browser embeds passed. Reproduce using
tools/architecture/README.md. Source/asset hashes and actual screenshots are
retained here. No hardware was accessed.
