# Run AFTER parent generation: generic parent snapshots can restore child designs.
package require qsys
load_system niosv_subsys.qsys
foreach name {u_niosv_m u_niosv_onchip_memory u_jtag_uart} {
    if {[lsearch -exact [get_instances] $name]>=0} {remove_instance $name}
}
foreach name {u_niosv_m u_niosv_onchip_memory u_jtag_uart} {
    if {[lsearch -exact [get_instances] $name]>=0} {error "Unused instance remains: $name"}
}
save_system niosv_subsys.qsys
puts "PR_UNUSED_INSTANCES_REMOVED"
