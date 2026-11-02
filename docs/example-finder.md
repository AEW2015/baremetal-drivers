# Find an example

Choose a verified platform, then search by topic, example ID or hardware block.
**Passed on both** requires a full PASS on Simics and hardware; partial results
are excluded. Results describe the linked runs and their stated scope.

New here? [Run Hello World on each platform](hello-world.md), then try
[the debugger walkthrough](qemu.md) or [the clickable HPS map](architecture.md).

<div id="example-finder" data-catalog-url="../assets/architecture/examples.json" data-diagram-url="../assets/architecture/design.html">
  <p id="finder-coverage"></p>
  <div class="finder-controls">
    <label>Search <input id="finder-query" type="search" placeholder="hello, DMA, SDM mailbox…"></label>
    <label>Passed on <select id="finder-verified"><option value="all">Any result</option><option value="qemu">QEMU</option><option value="simics">Simics</option><option value="hardware">Hardware</option><option value="both">Both Simics + hardware</option><option value="all-three">All three</option></select></label>
    <label>Family <select id="finder-family"><option value="">All families</option></select></label>
    <button id="finder-reset" type="button">Clear filters</button>
  </div>
  <p id="finder-count" role="status" aria-live="polite">Loading the example catalog…</p>
  <div id="finder-results"></div>
</div>

<noscript>Enable JavaScript for filters, or use the <a href="../example-catalog/">complete example catalog</a>.</noscript>

The [complete catalog](example-catalog.md) is also available without JavaScript.
Every card links to a tutorial, source, diagram and recorded execution evidence.
Use the [educational coding standard](educational-coding-standard.md) to review
or extend a lab. [Read the audit findings](education-audit.md).

The [movable lab-ready release](https://github.com/AEW2015/baremetal-drivers/releases/tag/lab-ready)
identifies the tested snapshot and its remaining limitations.
