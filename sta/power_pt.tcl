# Isolated activity-annotated prelayout pilot. Never sources/changes the accepted STA script.
proc power_write {name text} {
    set f [open [file join $::env(POWER_REPORT_DIR) $name] w]
    puts $f $text
    close $f
}
proc power_capture {name script} {
    set ::power_text ""
    if {[catch {uplevel #0 [list redirect -variable power_text $script]} result]} {
        error "$name raised: $result"
    }
    power_write $name "# command: $script\n$::power_text\n# return: $result"
    if {[regexp -line {^\s*(Error|Fatal)\s*:} $::power_text] ||
        [string trim $::power_text] eq ""} {error "$name empty or tool error"}
    return $result
}
proc power_main {} {
    foreach key {POWER_CASE_ROOT POWER_SAIF POWER_REPORT_DIR POWER_N POWER_POLICY POWER_DB} {
        if {![info exists ::env($key)]} {error "missing environment variable $key"}
    }
    set base [file normalize $::env(POWER_CASE_ROOT)]
    source [file join $base run_config.tcl]
    # Make generated configuration variables visible to captured global commands.
    foreach name [info locals] {
        if {[string match {[A-Z]*} $name]} {set ::$name [set $name]}
    }
    if {$::PROFILE_SHA256 ne "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d" ||
        $::PROFILE_STATUS ne "FROZEN" || $::CLOCK_PERIOD != 25.0 ||
        $::WIRE_LOAD_METHOD ne "fixed_model" || $::WIRE_LOAD_MODEL ne "ForQA" ||
        $::WIRE_LOAD_MODE ne "top" || $::PARAM_RR_QUANTUM != 10 || $::PARAM_FAI_W != 5000000 ||
        $::PARAM_N_SRC ni {4 8 16} || $::POLICY_NAME ni {fcfs rr fai-main} ||
        $::PARAM_N_SRC != $::env(POWER_N) || $::POLICY_NAME ne $::env(POWER_POLICY) ||
        $::TARGET_LIBRARY ne $::env(POWER_DB)} {
        error "unsupported/unfrozen power configuration"
    }
    set ::POWER_NETLIST [file join $base $::NETLIST_FILE]
    set ::POWER_SDC [file join $base $::SDC_FILE]
    set ::POWER_SAIF $::env(POWER_SAIF)
    foreach path [list $::TARGET_LIBRARY $::POWER_NETLIST $::POWER_SDC $::POWER_SAIF] {
        if {![file isfile $path] || [file size $path] == 0} {error "missing/empty $path"}
    }
    set_app_var power_enable_analysis true
    if {![get_app_var power_enable_analysis]} {error "power feature did not enable"}
    set_app_var power_analysis_mode averaged
    set_host_options -max_cores 1
    set_app_var link_path [list * $::TARGET_LIBRARY]
    set_app_var link_create_black_boxes false
    if {![read_verilog $::POWER_NETLIST]} {error "read_verilog failed"}
    if {![link_design $::TOP_MODULE]} {error "link failed (no black boxes permitted)"}
    read_sdc -version 2.1 $::POWER_SDC
    set_operating_conditions -library $::LIB_NAME $::OPERATING_CONDITIONS
    set_app_var auto_wire_load_selection false
    set_wire_load_mode $::WIRE_LOAD_MODE
    set_wire_load_model -name $::WIRE_LOAD_MODEL -library $::LIB_NAME
    power_capture design.rpt {report_design}
    # Selected metadata only: never dump or transfer proprietary library tables.
    power_write library.rpt "library=$::LIB_NAME\noperating_conditions=$::OPERATING_CONDITIONS\noriginal_db=$::TARGET_LIBRARY\ncorner=TT_0.78V_25C\nprofile=$::PROFILE_SHA256\nDB_SHA256=see_source.sha256"
    power_capture clocks.rpt {report_clock}
    power_capture units.rpt {report_units}
    # W-2024.09 help and actual parent smoke confirmed this scope syntax. The return is a
    # count, not a boolean: coverage is validated from saif-read.rpt and independent SAIF audit.
    power_capture saif-read.rpt {read_saif -strip_path tb/dut $POWER_SAIF}
    update_timing
    power_capture check-power.rpt {check_power -verbose}
    power_capture update-power.rpt {update_power}
    power_capture disable-timing.rpt {report_disable_timing}
    power_capture switching-coverage.rpt {report_switching_activity -coverage -hierarchy}
    power_capture not-annotated.rpt {report_switching_activity -list_not_annotated -show_pin}
    power_capture annotated.rpt {report_switching_activity -list_annotated -show_pin}
    # The overview tables in these reports distinguish Activity File, Clock, Default,
    # Propagated and Not Annotated. -coverage instead counts nets with >=1 toggle.
    power_capture power.rpt {report_power -verbose -nosplit}
    power_capture power-hierarchy.rpt {report_power -hierarchy -nosplit}
    set registers [all_registers]
    set f [open [file join $::env(POWER_REPORT_DIR) registers-and-clock-pins.rpt] w]
    puts $f "register_count=[sizeof_collection $registers]"
    foreach_in_collection object [all_registers -clock_pins] {
        set nets [get_nets -of_objects $object]
        set activity [get_switching_activity -toggle_rate $object]
        puts $f "clock_pin=[get_object_name $object] nets=[get_object_name $nets] activity=$activity"
    }
    close $f
    power_write pilot-status.rpt "POWER_PILOT_COMMANDS_COMPLETED\nSEMANTIC_REVIEW_REQUIRED\nprofile=$::PROFILE_SHA256\npolicy=$::POLICY_NAME N=$::PARAM_N_SRC\nSAIF_scope=tb/dut\nzero_delay_no_SDF_no_APR_no_clock_tree_signoff"
}
if {[catch {power_main} detail]} {
    puts "POWER_PILOT_ERROR: $detail"
    exit 1
}
exit 0
