#!/usr/bin/env bash
# Low-memory component generation only; no full-board Quartus compile or JTAG.
set -Eeuo pipefail
cd "$(dirname "$0")"
out=$(realpath -m ../../build/fabric-ddr-component)
mkdir -p "$out"
cat > "$out/check.tcl" <<'TCL'
package require -exact qsys 26.1
create_system ddr_probe_component
set_project_property DEVICE_FAMILY "Agilex 5"
set_project_property DEVICE A5ED065BB32AE6SR0
add_instance dut ddr_probe 1.0
set_instance_parameter_value dut ALLOWED_BASE 268435456
set_instance_parameter_value dut ALLOWED_END 268468224
foreach {name type direction} {clock clock sink reset reset sink csr avalon slave memory axi4 master interrupt interrupt sender} {
    add_interface $name $type $direction
    set_interface_property $name EXPORT_OF dut.$name
}
save_system ddr_probe_component.qsys
TCL
(
 cd "$out"
 project=()
 if [[ -f check.qpf ]]; then project=(--quartus-project=check); fi
 qsys-script "${project[@]}" --script=check.tcl --search-path="$OLDPWD,\$" > catalog.log 2>&1 || { cat catalog.log; exit 1; }
 qsys-generate ddr_probe_component.qsys --synthesis=SYSTEM_VERILOG \
   --search-path="$OLDPWD,\$" > generate.log 2>&1 || { cat generate.log; exit 1; }
 test -f ddr_probe_component/synth/ddr_probe_component.v
)
echo 'PASS DDR_PROBE_COMPONENT: CSR + AXI4 + IRQ wrapper generated for Modular ES; no whole-board fit or bridge deployment'
