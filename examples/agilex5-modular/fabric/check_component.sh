#!/usr/bin/env bash
# Generate an exported component wrapper for the exact bench part; no fitter/JTAG.
set -Eeuo pipefail
cd "$(dirname "$0")"
command -v qsys-script >/dev/null || { echo 'Run in the Quartus development container/environment' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cat > "$work/lab_component.tcl" <<'TCL'
package require -exact qsys 26.1
create_system lab_component_validation
set_project_property DEVICE_FAMILY "Agilex 5"
set_project_property DEVICE A5ED065BB32AE6SR0
add_instance dut lab_ip 1.0
set_instance_parameter_value dut MODE 1
add_interface clock clock sink
set_interface_property clock EXPORT_OF dut.clock
add_interface reset reset sink
set_interface_property reset EXPORT_OF dut.reset
add_interface csr avalon slave
set_interface_property csr EXPORT_OF dut.csr
save_system {@WORK@/lab_component_validation.qsys}
TCL
python3 - "$work" <<'PY_PATH'
from pathlib import Path
import sys
p=Path(sys.argv[1])/'lab_component.tcl'
p.write_text(p.read_text().replace('@WORK@',sys.argv[1]))
PY_PATH
qsys-script --script="$work/lab_component.tcl" --search-path="$PWD,\$" \
  > "$work/catalog.log" 2>&1 || { cat "$work/catalog.log"; exit 1; }
# Search path is needed at BOTH discovery and generation, including child IPs.
qsys-generate "$work/lab_component_validation.qsys" --synthesis=VERILOG \
  --search-path="$PWD,\$" > "$work/generate.log" 2>&1 || { cat "$work/generate.log"; exit 1; }
test -f "$work/lab_component_validation/synth/lab_component_validation.v"
echo 'PASS FABRIC_COMPONENT: Quartus Platform Designer wrapper generated for A5ED065BB32AE6SR0; no whole-board fit or programming'
