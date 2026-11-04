// RTL Source Filelist — common framework blocks (descriptor package + per-source FIFO + output hold
// + shared oldest-head FCFS selector + FAI Main policy block + Round Robin policy block)
// Usage: -f rtl/filelist_common.f (verilator/vcs/xrun/questa) or parsed by run_sim.sh (iverilog)
// Convention: packages first, then modules in dependency order
// Paths are relative to the repository root.

// --- Packages ---
rtl/include/cxl_sched_pkg.sv

// --- Common modules ---
rtl/common/cxl_desc_fifo.sv
rtl/common/cxl_out_hold.sv
rtl/common/cxl_fcfs_sel.sv
rtl/common/cxl_fai_main_sched.sv
rtl/common/cxl_rr_sched.sv
