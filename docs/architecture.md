# Clickable HPS and fabric example map

Explore the examples by hardware block or select a named exercise to locate the
blocks it uses. Every one of the **81 catalog entries** has a mapping. The
diagram uses **FPGA Project Analyzer** with an Agilex-specific adapter and the
repository's recorded platform results.

[**Open the full-screen interactive diagram ↗**](assets/architecture/design.html){ .md-button .md-button--primary }
[Download the offline HTML](assets/architecture/design.html){ download="agilex5-examples.html" .md-button }

<iframe src="../assets/architecture/design.html" title="Clickable Agilex 5 HPS and fabric example map" width="100%" height="820" style="border:1px solid #b8c6d7;border-radius:8px" loading="lazy"></iframe>

## Use the diagram

- **Click a block** to see its role, related examples, platform results,
  tutorial/expected-output links, source and execution evidence.
- **Double-click**, or select **Open**, to drill into a subsystem. The breadcrumb
  and prominent **← Back**, **↑ Up one level**, and **⌂ System** controls navigate
  the hierarchy. Back restores the previous level and selection; Up opens the
  parent. Keyboard shortcuts are **Alt+Left** and **Alt+Up**. Scroll to zoom and drag to pan.
- The toolbar and **Direct reference pages** panel link to the selected block’s
  specific TRM section, including a content ID to distinguish repeated headings.
  The model includes **48 direct TRM section links**.
- Choose an **Example** to locate it and highlight related blocks. **Find**
  narrows the example list; **Results** emphasizes QEMU, Simics or hardware.
- Open **Fabric → Lab_proposed → lab_ip** for the register ABI, then open it
  again for the parsed register logic and ADD/XOR persona hierarchy.
- **Export** saves the current diagram level as SVG or PNG. The standalone HTML
  embeds its data and layout engine; viewing the diagram needs no server or CDN.
  Documentation, source and evidence links open their online destinations.

Individual example pages also have a preselected diagram button and an
expandable inline viewer. The viewer loads lazily when needed. The complete
catalog links each example name to its own selection in this map.

Try direct example links:

| Example | What to inspect |
|---|---|
| [SDM mailbox](assets/architecture/design.html?example=upstream%2Fmailbox) | Direct and TF-A paths; physical PASS versus partial model result |
| [Timer and GIC](assets/architecture/design.html?example=practice%2Ftimer) | Actual timer FIQ delivery; separate from peripheral timer checks |
| [Multicore](assets/architecture/design.html?example=practice%2Fmulticore) | A55/A76 execution and power/reset context |
| [Ethernet UDP/TCP](assets/architecture/design.html?example=custom%2Fethernet) | EMAC2 and the SOM PHY; actual traffic versus identification only |
| [ADD fabric core](assets/architecture/design.html?example=fabric%2Fadd) | Proposed address, real RTL hierarchy and unqualified physical deployment |
| [Partial reconfiguration](assets/architecture/design.html?example=reference%2Fpr) | Reference workflow; live PR remains unqualified |

## What the drawing represents

The **77 architecture blocks** are an educational grouping based on the HPS TRM,
our Modular ES bench profile and SOM schematic. The system overview follows
TRM Figure 1: MPU above APS, MPFE to the left, and PSS peripherals and
interconnect to the right. Colors and grouping follow that reference in an
independent redraw; the example fabric and SOM additions are clearly separated.
Wires represent functional access
paths, not an extracted Quartus netlist. Logical grouping is not a claim about
physical floorplan, exact internal bus wiring, clock frequency or timing closure.
The map focuses on blocks relevant to this example collection; it is not a full
replacement for the TRM.

| Context | Provenance and limits |
|---|---|
| HPS | TRM MPU, APS, PSS and CoreSight hierarchy, with block-specific chapter links |
| SDM | Configuration and firmware-service context outside the HPS CPU |
| DDR / IO96 | TRM IOBank 0/1 architecture context; this bench initializes HPS DDR bank 3A only; matching handoff required |
| SOM devices | Board schematic and established bench profile; no carrier connectivity inferred |
| Proposed ADD/XOR fabric | Actual repository RTL, parsed structurally; C-driver/RTL co-simulation passed, physical deployment unqualified |
| Simics reference fabric | Behavioral memory/PIO models; not simulation of our custom RTL |
| PR recipe | Reference integration workflow, not an implemented or tested static shell |

Results come from the [example catalog](example-catalog.md), including historical
artifact snapshots. A controller ID PASS is not a data-transfer PASS, and an ECC
register check is not injected-error recovery. Select the **R0** register map for
this Modular ES bench; production-part assumptions are not interchangeable.

## Sources and tool attribution

- [Agilex 5 HPS Technical Reference Manual, 26.1.1](https://docs.altera.com/r/docs/814346/26.1.1/hard-processor-system-technical-reference-manual-agilex-5-socs)
- [TRM Figure 1: HPS block diagram](https://docs.altera.com/r/docs/814346/26.1.1/hard-processor-system-technical-reference-manual-agilex-5-socs/hps-block-diagram?contentId=cSfnXaIdQVtkXwpvt5_ikQ)
- [HPS address map and register definitions, including R0](https://docs.altera.com/r/docs/814346/26.1.1/hard-processor-system-technical-reference-manual-agilex-5-socs/hps-address-map-and-register-definitions)
- [Modular SOM schematic](https://docs.altera.com/v/u/docs/836174/agilextm-5-fpga-e-series-065b-modular-fpga-development-kit-board-som-board-schematic)
- [Simics reference fabric model documentation](https://docs.altera.com/r/docs/786901/25.3/intel-simics-simulator-for-altera-fpgas-agilextm-5-and-agilextm-3-virtual-platform-user-guide/fpga-fabric)
- [FPGA Project Analyzer](https://github.com/al-nafisah/fpga-project-analyzer), pinned at `954b91dd39fcd24bd53b1038161e04ea030074dc`, MIT © 2026 Abdullah AlNafisah; ELK layout uses EPL-2.0. [Distributed notices and licenses](assets/architecture/THIRD_PARTY.txt).

The analyzer's current importers target Vivado. This adapter supplies its public
design-model API with curated Agilex architecture data; its actual RTL parser
extracts only `lab_ip.sv` and `lab_persona.sv`. Vivado/XDC lint findings are not
applied to this Quartus component. No Altera TRM illustrations or PDFs are
redistributed; the map is independently drawn and links to the references.

## Reproduce and check

From the repository root, with Python 3:

```sh
python3 tools/architecture/build_diagram.py
python3 tools/architecture/build_diagram.py --check
```

The renderer and dependencies are pinned in `tools/vendor/fpga-project-analyzer`;
the build needs no Quartus, Vivado, Node, network download or global MCP setup.
Source/renderer hashes and catalog coverage are recorded in the generated
[build manifest](assets/architecture/build.json). A new catalog entry requires an
explicit block mapping, so it cannot silently disappear from the diagram.

For the browser tests:

```sh
python3 -m pip install -r tools/architecture/requirements-test.txt
python3 -m playwright install chromium
python3 tools/architecture/test_browser.py
```

The browser checks all 81 example selections, result/evidence cards, actual RTL
drill-down, Back/Up navigation, direct TRM links, keyboard selection, SVG/PNG
export, search, legacy deep links and mobile layout.
It runs with networking disabled and rejects JavaScript errors. Website deployment
depends on this check. The feature does not program or access the physical board.
