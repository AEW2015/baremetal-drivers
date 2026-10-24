package require -exact qsys 26.1
set_module_property NAME lab_ip
set_module_property VERSION 1.0
set_module_property GROUP "Agilex 5 Lab"
set_module_property DISPLAY_NAME "Bare-metal lab arithmetic IP"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
add_parameter MODE INTEGER 1
set_parameter_property MODE ALLOWED_RANGES {1 2}
set_parameter_property MODE HDL_PARAMETER true
add_fileset synth QUARTUS_SYNTH ""
set_fileset_property synth TOP_LEVEL lab_ip
add_fileset_file rtl/lab_ip.sv SYSTEM_VERILOG PATH rtl/lab_ip.sv TOP_LEVEL_FILE
add_fileset_file rtl/lab_persona.sv SYSTEM_VERILOG PATH rtl/lab_persona.sv
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
add_interface_port csr avs_address address Input 4
add_interface_port csr avs_read read Input 1
add_interface_port csr avs_write write Input 1
add_interface_port csr avs_writedata writedata Input 32
add_interface_port csr avs_byteenable byteenable Input 4
add_interface_port csr avs_readdata readdata Output 32
