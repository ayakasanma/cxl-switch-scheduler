# Template only: no timing result is implied by this file.
# Execute through scripts/remote_eda.py with an explicitly selected netlist and SDC.
set RUN_ROOT [file dirname [file dirname [file normalize [info script]]]]
cd $RUN_ROOT
source [file join $RUN_ROOT run_config.tcl]

set_app_var search_path [concat [list $RUN_ROOT [file dirname $TARGET_LIBRARY]] $search_path]
set_app_var link_path [concat [list *] [list $TARGET_LIBRARY]]

if {[catch {
    foreach netlist $STA_NETLIST_FILES {read_verilog $netlist}
    current_design $TOP_MODULE
    if {![link_design $TOP_MODULE]} {error "Design linking failed"}
    foreach constraint $STA_CONSTRAINT_FILES {read_sdc $constraint}
    update_timing
    redirect reports/check_timing.rpt {check_timing}
    redirect reports/timing_max.rpt {report_timing -delay_type max -max_paths 20}
    redirect reports/timing_min.rpt {report_timing -delay_type min -max_paths 20}
    redirect reports/constraints.rpt {report_constraint -all_violators}
    redirect reports/coverage.rpt {report_analysis_coverage}
    set status_file [open reports/run_status.rpt w]
    puts $status_file "STATUS: SUCCESS"
    puts $status_file "OPERATION: sta"
    close $status_file
} detail]} {
    puts stderr "EDA_FAILURE: STA failed: $detail"
    exit 1
}
exit 0
