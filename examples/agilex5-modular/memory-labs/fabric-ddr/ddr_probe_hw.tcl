# SPDX-License-Identifier: MIT-0
package require -exact qsys 26.1
set_module_property NAME ddr_probe
set_module_property VERSION 1.0
set_module_property GROUP "Agilex 5 Lab"
set_module_property DISPLAY_NAME "Guarded AXI DDR probe"
set_module_property AUTHOR "Agilex 5 Bare-Metal Lab"
set_module_property DESCRIPTION "Single-outstanding guarded memory exerciser; default zero address window disables transfers."
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
foreach {name type default} {ALLOWED_BASE STD_LOGIC_VECTOR 0 ALLOWED_END STD_LOGIC_VECTOR 0 MAX_WORDS INTEGER 65536 WATCHDOG_CYCLES INTEGER 1024 AXPROT INTEGER 0 AXUSER INTEGER 0} {
    add_parameter $name $type $default
    set_parameter_property $name HDL_PARAMETER true
}
set_parameter_property ALLOWED_BASE WIDTH 64
set_parameter_property ALLOWED_END WIDTH 64
set_parameter_property MAX_WORDS ALLOWED_RANGES {1:1048576}
set_parameter_property WATCHDOG_CYCLES ALLOWED_RANGES {16:2147483647}
set_parameter_property AXPROT ALLOWED_RANGES {0:7}
set_parameter_property AXUSER ALLOWED_RANGES {0:255}
add_fileset synth QUARTUS_SYNTH ""
set_fileset_property synth TOP_LEVEL ddr_probe
add_fileset_file rtl/ddr_probe.sv SYSTEM_VERILOG PATH rtl/ddr_probe.sv TOP_LEVEL_FILE
add_interface clock clock end
add_interface_port clock clk clk Input 1
add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges BOTH
add_interface_port reset reset reset Input 1
add_interface csr avalon end
set_interface_property csr associatedClock clock
set_interface_property csr associatedReset reset
set_interface_property csr addressUnits WORDS
set_interface_property csr bitsPerSymbol 8
set_interface_property csr readLatency 1
set_interface_property csr maximumPendingReadTransactions 0
add_interface_port csr csr_address address Input 6
add_interface_port csr csr_read read Input 1
add_interface_port csr csr_write write Input 1
add_interface_port csr csr_writedata writedata Input 32
add_interface_port csr csr_byteenable byteenable Input 4
add_interface_port csr csr_readdata readdata Output 32
add_interface memory axi4 start
set_interface_property memory associatedClock clock
set_interface_property memory associatedReset reset
foreach {signal role direction width} {
 m_awaddr awaddr Output 40 m_araddr araddr Output 40
 m_awid awid Output 1 m_arid arid Output 1
 m_awlen awlen Output 8 m_arlen arlen Output 8
 m_awsize awsize Output 3 m_arsize arsize Output 3
 m_awburst awburst Output 2 m_arburst arburst Output 2
 m_awprot awprot Output 3 m_arprot arprot Output 3
 m_awcache awcache Output 4 m_arcache arcache Output 4
 m_awuser awuser Output 8 m_aruser aruser Output 8
 m_awvalid awvalid Output 1 m_arvalid arvalid Output 1
 m_awready awready Input 1 m_arready arready Input 1
 m_wdata wdata Output 64 m_wstrb wstrb Output 8
 m_wlast wlast Output 1 m_wvalid wvalid Output 1 m_wready wready Input 1
 m_bresp bresp Input 2 m_bid bid Input 1 m_bvalid bvalid Input 1 m_bready bready Output 1
 m_rdata rdata Input 64 m_rresp rresp Input 2 m_rid rid Input 1
 m_rlast rlast Input 1 m_rvalid rvalid Input 1 m_rready rready Output 1
} {add_interface_port memory $signal $role $direction $width}
add_interface interrupt interrupt sender
set_interface_property interrupt associatedClock clock
set_interface_property interrupt associatedReset reset
set_interface_property interrupt associatedAddressablePoint csr
add_interface_port interrupt irq irq Output 1
