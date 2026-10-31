#!/usr/bin/env bash
# Platform Designer generation only. Does not synthesize, fit, assemble or program.
set -Eeuo pipefail
project=$(realpath "${1:?Pass the isolated staged project directory}")
cd "$project"
search="$project/custom_ip/baremetal/fabric/pr,\$"
qsys-script --quartus-project=baseline_a55.qpf --script=overlay.tcl --search-path="$search" > overlay.log 2>&1
python3 - <<'PY'
from pathlib import Path
s=Path('overlay.log').read_text()
assert 'PR_OVERLAY_COMPLETE' in s and 'Error:' not in s,s[-4000:]
PY
for system in fabric_subsys baseline_top;do
 qsys-generate "$system.qsys" --synthesis=VERILOG --search-path="$search" --part=A5ED065BB32AE6SR0 > "generate-$system.log" 2>&1
 python3 - "$system" <<'PY'
import sys
from pathlib import Path
name=sys.argv[1];s=Path('generate-'+name+'.log').read_text()
assert 'Error:' not in s,s[-4000:]
assert Path(name+'/synth/'+name+'.v').is_file(),'No generated top-level HDL'
PY
done
echo 'PASS PR_PLATFORM_GENERATION: no whole-board compilation or programming'
