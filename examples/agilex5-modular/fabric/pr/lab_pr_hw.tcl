package require qsys
set_module_property NAME lab_pr
set_module_property VERSION 1.0
set_module_property GROUP "Agilex 5 Lab"
set_module_property DISPLAY_NAME "Bare-metal PR static shell and slot"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
add_fileset synth QUARTUS_SYNTH ""
set_fileset_property synth TOP_LEVEL lab_pr
add_fileset_file rtl/lab_pr.sv SYSTEM_VERILOG PATH rtl/lab_pr.sv TOP_LEVEL_FILE
add_fileset_file rtl/pr_static.sv SYSTEM_VERILOG PATH rtl/pr_static.sv
add_fileset_file rtl/pr_slot.sv SYSTEM_VERILOG PATH rtl/pr_slot.sv
add_fileset_file ../rtl/lab_ip.sv SYSTEM_VERILOG PATH ../rtl/lab_ip.sv
add_fileset_file ../rtl/lab_persona.sv SYSTEM_VERILOG PATH ../rtl/lab_persona.sv
add_interface clock clock end
add_interface_port clock clk clk Input 1
add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges DEASSERT
add_interface_port reset reset_n reset_n Input 1
add_interface csr avalon end
set_interface_property csr associatedClock clock
set_interface_property csr associatedReset reset
set_interface_property csr addressUnits WORDS
set_interface_property csr bitsPerSymbol 8
set_interface_property csr readLatency 1
set_interface_property csr maximumPendingReadTransactions 0
set_interface_property csr timingUnits Cycles
add_interface_port csr address address Input 6
add_interface_port csr read read Input 1
add_interface_port csr write write Input 1
add_interface_port csr writedata writedata Input 32
add_interface_port csr byteenable byteenable Input 4
add_interface_port csr readdata readdata Output 32
