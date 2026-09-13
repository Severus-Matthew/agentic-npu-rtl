cd [file dirname [info script]]
set_param general.maxThreads 1
read_verilog -sv {rtl/stream_matvec_int8.sv}
synth_design -top {stream_matvec_int8} -part {CONFIGURE_PART} -mode out_of_context
if {[llength [get_clocks -quiet]] == 0} {create_clock -name primary -period {CONFIGURE_PERIOD} [get_ports {CONFIGURE_CLOCK}]}
report_utilization -file synthesis_utilization.rpt
opt_design
place_design
phys_opt_design
route_design
report_route_status -file route_status.rpt
report_utilization -file utilization.rpt
report_timing_summary -report_unconstrained -file timing_summary.rpt
report_timing -max_paths 10 -path_type full_clock_expanded -file critical_paths.rpt
report_power -file power.rpt
report_drc -file drc.rpt
set critical_drc_count 0
foreach violation [get_drc_violations] {set severity [get_property SEVERITY $violation]; if {[string equal -nocase $severity "Error"] || [string equal -nocase $severity "Critical Warning"]} {incr critical_drc_count}}
write_checkpoint -force implemented.dcp
set f [open timing.tsv w]
puts $f "vivado_version	[version -short]"
puts $f "clock_count	[llength [get_clocks]]"
puts $f "routed_fully	[report_route_status -boolean_check ROUTED_FULLY]"
puts $f "routing_errors	[report_route_status -boolean_check ERRORS_IN_ROUTES]"
puts $f "critical_drc_count	$critical_drc_count"
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $setup] != 1 || [llength $hold] != 1} {error "Missing constrained timing paths"}
puts $f "wns_ns	[get_property SLACK $setup]"
puts $f "whs_ns	[get_property SLACK $hold]"
puts $f "critical_path_delay_ns	[get_property DATAPATH_DELAY $setup]"
close $f
set f [open completed.marker w]
puts $f "VIVADO_OOC_COMPLETE"
close $f
