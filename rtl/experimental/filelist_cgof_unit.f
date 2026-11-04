// RTL Source Filelist — EXPERIMENTAL CGOF (Credit-Gated Oldest-First) standalone verification top
// Usage: -f rtl/experimental/filelist_cgof_unit.f (verilator), from the repository root.
// Accepted common blocks are reused unchanged; cxl_cgof_sched / cgof_unit_top are experimental.
// Integration into rtl/experimental/filelist.f / switch_experiment_top is not done here.

// --- Packages ---
rtl/include/cxl_sched_pkg.sv

// --- Accepted common modules (unchanged) ---
rtl/common/cxl_desc_fifo.sv
rtl/common/cxl_out_hold.sv
rtl/common/cxl_fcfs_sel.sv

// --- Experimental modules ---
rtl/experimental/cxl_cgof_sched.sv

// --- Experimental standalone top ---
rtl/experimental/cgof_unit_top.sv
