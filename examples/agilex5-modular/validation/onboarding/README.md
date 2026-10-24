# Onboarding and desktop follow-up evidence

See the [public report](https://aew2015.github.io/baremetal-drivers/feedback-followup/).
These are actual agent-operated technical trials, not real student observations.
The clean-container trial used a clean public clone of the recorded commit;
the current prediction exercise was separately tested read-only in that image.
The hardware tools image was built and version-checked without USB/JTAG access.

Actual Linux VS Code rendered under Xvfb inside the existing bench container.
Keyboard/mouse actions launched the workspace configs; the small local probe
recorded debugger events and evaluations. Raw events preserve earlier failed
attempts and normal stop-time transport errors. Expressions have their debugger
result type in the `type` field, while lifecycle entries use event names.
Failures included implicit architecture, missing ELF selection and the correctly
rejected attempt to bootstrap before a debug stop had released the lock.

The last physical checks ran the core twice, then restored DDR Hello and verified
ports/lock released. UART evidence includes prior Hello output; require the new
core BEGIN/PASS/COMPLETE sequence. PNGs are unedited; text paths/whitespace are
normalized. Build summaries filter actual full local output for provenance lines.

No fresh-kit/new-PC human test, new-image USB qualification, Dev Containers attach
GUI, new fabric hardware or live PR is claimed. The complete custom FPGA project
is still an instructor-supplied dependency; upstream sources alone do not recreate
its exact qualified SOF. `manifest.json` identifies checked source and artifact hashes.
