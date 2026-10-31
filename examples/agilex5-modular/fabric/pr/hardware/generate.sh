#!/usr/bin/env bash
# Platform Designer generation only. Does not synthesize, fit, assemble or program.
set -Eeuo pipefail
script_dir=$(cd "$(dirname "$0")" && pwd)
project=$(realpath "${1:?Pass the isolated staged project directory}")
cd "$project"
search="$project/custom_ip,$project/custom_ip/baremetal/fabric/pr,\$"
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
qsys-script --quartus-project=baseline_a55.qpf --script="$script_dir/prune_unused.tcl" --search-path="$search" > prune-unused.log 2>&1
python3 - <<'PY_PRUNE'
from pathlib import Path
s=Path('prune-unused.log').read_text()
assert 'PR_UNUSED_INSTANCES_REMOVED' in s and 'Error:' not in s,s[-4000:]
PY_PRUNE
qsys-generate niosv_subsys.qsys --synthesis=VERILOG --part=A5ED065BB32AE6SR0 > generate-niosv-final.log 2>&1
python3 - <<'PY_FINAL'
from pathlib import Path
s=Path('generate-niosv-final.log').read_text()
assert 'Error:' not in s,s[-4000:]
PY_FINAL
# The custom clock/reset RTL instantiates these IPs outside the Qsys graph.
for ip in clks_and_rsts sys_pll user_rst_clkgate;do
 qsys-generate "ip/shell_subsys/$ip.ip" --clear-output-directory --synthesis=VERILOG --part=A5ED065BB32AE6SR0 --search-path="$search" > "generate-$ip.log" 2>&1
 python3 - "$ip" <<'PY_LEAF'
from pathlib import Path
import sys
s=Path('generate-'+sys.argv[1]+'.log').read_text()
assert 'Error:' not in s,s[-4000:]
PY_LEAF
done
python3 "$script_dir/register_generated.py" "$project"
echo 'PASS PR_PLATFORM_GENERATION: no whole-board compilation or programming'
