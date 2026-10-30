# Clickable architecture browser validation

Actual headless Chromium execution on 2026-10-30 UTC, with networking disabled.
The pinned FPGA Project Analyzer renderer and RTL parser produced the diagram;
the Agilex adapter supplied 61 curated architecture blocks and all 81 catalog
associations. This is UI/model validation, not a new hardware qualification.

`results.json` records the browser version, exact generated-HTML hash and eleven
passing checks, including all 81 example selections, source/tutorial links,
platform result cards, actual RTL drill-down, keyboard selection, overlapping
layout requests, deep links, mobile layout and SVG/PNG export. It records zero
JavaScript errors and zero external network requests.

Screenshots show the system overview, mailbox hardware result, parsed RTL and
mobile details panel. `overview.svg` is the actual browser-exported diagram;
`diagram-build.json` records input/output hashes and the analyzer revision.
Screenshots illustrate the state at execution; future generated assets may have
different hashes after a source/catalog change.

Reproduce from the repository root:

```sh
python3 tools/architecture/build_diagram.py
python3 tools/architecture/build_diagram.py --check
python3 -m pip install -r tools/architecture/requirements-test.txt
python3 -m playwright install chromium
python3 tools/architecture/test_browser.py
```

The standalone asset works without a web server or CDN. Documentation, source
and evidence links remain online destinations. No FPGA was programmed or accessed
for these checks. See [the guide](../../../../docs/architecture.md) for provenance
and the distinction between architectural context, proposed fabric integration,
Simics behavioral models and real parsed RTL.

## Embedded example-page follow-up

`example-pages-results.json` records checks of all 28 contextual page embeds and
all 81 catalog diagram links. Chromium also expanded the inline viewer on the
DMA, QEMU-practice, runtime and fabric pages and verified their selected example
cards. All four browser checks passed without JavaScript exceptions. Run
`python3 tools/architecture/test_example_pages.py --browser-checks` after building
MkDocs to repeat this integration check.
