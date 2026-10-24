#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
# Use the same lock as the host suite; the descriptor stays held across exec.
exec 9>hardware.lock
flock -n 9 || { echo 'Another process owns this example tree hardware.lock' >&2; exit 1; }
python3 - <<'PY'
import re,subprocess
from pathlib import Path
records=list(Path(".").glob(".agilex-process-*"))
if records: raise SystemExit(f"Unresolved hardware process record: {records[0]}; investigate before debugging")
chain=subprocess.check_output(['jtagconfig'],text=True)
first=chain.split('2)')[0]
if not re.search(r'^1\) Agilex_5E MDK Carrier ',first,re.M) or not re.search(r'^\s+0364F0DD\s',first,re.M):
 raise SystemExit('Expected Modular ES carrier/FPGA as cable 1; inspect jtagconfig before debugging')
PY
jtagconfig --setparam 1 JtagClock 6M
exec openocd -f bootstrap/ocram/agilex5.cfg -c 'hps.a55.0 configure -event halted {}; hps.a55.0 configure -event resumed {}; bindto 127.0.0.1; gdb port 3337; tcl port 6677; telnet port 4457'
