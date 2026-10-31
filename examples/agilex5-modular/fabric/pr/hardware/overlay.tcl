# Run on an isolated COPY of the matching Modular HPS baseline.
package require qsys
load_system fabric_subsys.qsys
if {[lsearch -exact [get_instances] u_lab_pr]>=0} {error "PR component already present"}
add_instance u_lab_pr lab_pr 1.0
if {[lsearch -exact [get_instances] u_lab_pr]<0} {error "PR IP discovery failed; refuse to save"}
add_connection u_system_clock.out_clk u_lab_pr.clock
add_connection u_system_reset.out_reset u_lab_pr.reset
add_connection u_lwhps2fpga_bridge.m0 u_lab_pr.csr
set_connection_parameter_value u_lwhps2fpga_bridge.m0/u_lab_pr.csr baseAddress 0x00020000
set_connection_parameter_value u_lwhps2fpga_bridge.m0/u_lab_pr.csr arbitrationPriority 1
add_instance u_pr_jtag altera_jtag_avalon_master
add_connection u_system_clock.out_clk u_pr_jtag.clk
add_connection u_system_reset.out_reset u_pr_jtag.clk_reset
add_connection u_pr_jtag.master u_lab_pr.csr
set_connection_parameter_value u_pr_jtag.master/u_lab_pr.csr baseAddress 0x00020000
if {[lsearch -exact [get_instances] u_pr_jtag]<0} {error "PR JTAG manager discovery failed"}
save_system fabric_subsys.qsys
puts "PR_OVERLAY_COMPLETE"
