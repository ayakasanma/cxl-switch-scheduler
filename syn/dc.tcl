# Template only: never run until the architecture and constraints are approved.
# Execute through scripts/remote_eda.py to generate run_config.tcl.
set RUN_ROOT [file dirname [file dirname [file normalize [info script]]]]
cd $RUN_ROOT
source [file join $RUN_ROOT run_config.tcl]

set_app_var search_path [concat [list $RUN_ROOT [file dirname $TARGET_LIBRARY]] $search_path]
set_app_var target_library [list $TARGET_LIBRARY]
set_app_var link_library [concat [list *] [list $TARGET_LIBRARY]]
file mkdir work
define_design_lib WORK -path [file join $RUN_ROOT work]

if {[catch {
    if {![analyze -format sverilog $RTL_FILES]} {error "RTL analysis failed"}
    elaborate $TOP_MODULE
    current_design $TOP_MODULE
    if {![link]} {error "Design linking failed"}
    foreach constraint $CONSTRAINT_FILES {source $constraint}
    redirect reports/check_design.rpt {check_design}
    redirect reports/check_timing.rpt {check_timing}
    compile
    redirect reports/area.rpt {report_area -hierarchy}
    redirect reports/timing_max.rpt {report_timing -delay_type max -max_paths 20}
    redirect reports/qor.rpt {report_qor}
    write -format verilog -hierarchy -output [file join output "${TOP_MODULE}.syn.v"]
    write_sdc [file join output "${TOP_MODULE}.syn.sdc"]
    set status_file [open reports/run_status.rpt w]
    puts $status_file "STATUS: SUCCESS"
    puts $status_file "OPERATION: syn"
    close $status_file
} detail]} {
    puts stderr "EDA_FAILURE: Synthesis failed: $detail"
    exit 1
}
exit 0
