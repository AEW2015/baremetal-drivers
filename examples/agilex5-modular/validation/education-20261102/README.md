# Education and discovery validation

The QEMU lesson was rebuilt and executed with the existing Arm GNU 13.2.Rel1
compiler in the Quartus 26.3 tool container. Positive, deliberate corruption,
recovery and GDB checks passed. All 109 unit tests passed with real QEMU enabled.
The fresh QEMU ELF and exact input hashes are recorded in `qemu/results.json`.

Chromium checks cover all 94 diagram selections, block/Up navigation and full
PASS filtering, plus 32 embedded pages and the finder. Browser reports and
strict MkDocs output are retained here. Historical hardware/Simics results were
not rerun or reassigned to new artifacts by this education/UI change.
