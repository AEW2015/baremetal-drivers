# SPDX-License-Identifier: MIT-0
# The pins have no source-synchronous clock. Only the first synchronizer stage
# receives the asynchronous exception; normal internal timing remains checked.
set cc_ports [get_ports {cc_i2c_scl cc_i2c_sda}]
set cc_first_stage [get_registers {u_cc_reader|input_meta[*]}]
set cc_usb_status [get_ports {usb31_io_flt_bar usb31_io_vbus_det usb31_io_usb31_id}]
if {[get_collection_size $cc_ports] != 2 || [get_collection_size $cc_first_stage] != 5 || [get_collection_size $cc_usb_status] != 3} {
    error "CC probe port/synchronizer constraints did not bind"
}
set cc_inputs [get_ports {cc_i2c_scl cc_i2c_sda usb31_io_flt_bar usb31_io_vbus_det usb31_io_usb31_id}]
# These are asynchronous levels. Declare zero external timing requirements,
# then except only the first synchronizer stage. Source latency is included
# explicitly because the reference is the existing virtual board clock.
set_input_delay -source_latency_included -clock [get_clocks MAIN_CLOCK_virt] -min 0 $cc_inputs
set_input_delay -source_latency_included -clock [get_clocks MAIN_CLOCK_virt] -max 0 $cc_inputs
set_false_path -from $cc_ports -to $cc_first_stage
set_false_path -from $cc_usb_status -to $cc_first_stage
# 10-kHz open-drain control; constrain OE launch against the existing 100-MHz
# virtual board clock as well as checking all internal state/control paths.
set_output_delay -source_latency_included -clock [get_clocks MAIN_CLOCK_virt] -min 0 $cc_ports
set_output_delay -source_latency_included -clock [get_clocks MAIN_CLOCK_virt] -max 1 $cc_ports
