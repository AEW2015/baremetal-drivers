# Agilex example architecture adapter

This adapter uses [FPGA Project Analyzer](https://github.com/al-nafisah/fpga-project-analyzer)
at `954b91dd39fcd24bd53b1038161e04ea030074dc` through its Python design-model,
RTL parser and renderer APIs. The unmodified `fpalib` package and license notices
are pinned under `tools/vendor/fpga-project-analyzer`; every vendored file is
checked against its recorded SHA-256 before generation.

Run from the repository root:

```sh
python3 tools/architecture/build_diagram.py
python3 tools/architecture/build_diagram.py --check
python3 tools/architecture/link_example_pages.py --check
```

`agilex5.json` is a manually curated educational model, not a Quartus netlist.
Every catalog ID maps explicitly to one or more architecture paths. Connections
are functional paths, without inferred clock rates or bus widths. The generator
adds the real `lab_ip`/`lab_persona` structural hierarchy using the upstream RTL
parser with Vivado disabled; no XDC/DRC or timing findings are applied to Agilex.

`explorer.js`, `explorer.css` and `explorer-bar.html` add example navigation,
result cards, web source links and explicit provenance to the renderer without
modifying its vendored source. Exact template hooks fail loudly if the upstream
version changes. The generated HTML includes ELK, data and license texts, so it
works offline; documentation/source/evidence links are online destinations.

Generated files live in ignored `docs/assets/architecture/`; CI builds them before
MkDocs. The published `build.json` records source and artifact hashes. No global
skill/MCP registration, proprietary FPGA model or physical board access is needed.

Browser checks:

```sh
python3 -m pip install -r tools/architecture/requirements-test.txt
python3 -m playwright install chromium
python3 tools/architecture/test_browser.py
```

Pass `--browser /path/to/chromium` to use an existing browser. Screenshots,
exported SVG and the JSON result go under ignored `examples/agilex5-modular/runs/`.
The tests exercise all 81 example selections and reject external network
dependencies and JavaScript exceptions. They also test keyboard navigation,
actual RTL drill-down, platform emphasis, search, SVG export and mobile layout.

The existing example pages include managed contextual links and expandable,
lazy-loaded diagrams. Update those sections with
`python3 tools/architecture/link_example_pages.py`; `--check` detects stale or
missing sections. After building MkDocs, run
`python3 tools/architecture/test_example_pages.py --browser-checks` to validate
all page URLs and catalog links and open representative embedded viewers.

`trm-layout.json` and `trm-overview.js` independently draw the system overview
following TRM Figure 1 grouping and colors. Nested views use the analyzer layout.
The model stores 48 exact TRM topic URLs with content IDs from the official
26.1.1 topic index; each HPS block requires a direct reference. Old architecture
paths are retained as aliases. Back restores the prior level and selection;
Up opens the parent. No vendor illustration is bundled.
