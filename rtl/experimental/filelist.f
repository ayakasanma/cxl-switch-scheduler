// RTL Source Filelist — EXPERIMENTAL opt-in switch (revision study 2026-10-23)
// Usage: -f rtl/experimental/filelist.f (verilator), from the repository root.
// Accepted common/policy blocks are reused unchanged; only the files under rtl/experimental/
// are new. The accepted rtl/filelist_switch.f / switch_top are not affected.

// --- Packages ---
rtl/include/cxl_sched_pkg.sv

// --- Accepted common and policy modules (unchanged) ---
rtl/common/cxl_desc_fifo.sv
rtl/common/cxl_out_hold.sv
rtl/common/cxl_fcfs_sel.sv
rtl/common/cxl_fai_main_sched.sv
rtl/common/cxl_rr_sched.sv

// --- Experimental modules ---
rtl/experimental/cxl_fai_variant_sched.sv
rtl/experimental/cxl_bliss_sched.sv

// --- Experimental top ---
rtl/experimental/switch_experiment_top.sv
