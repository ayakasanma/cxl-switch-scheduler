// SIMULATION-ONLY filelist: real common blocks + the M2 candidate-injection fixture.
// Usage: -f sim/cxl_common_ctrl/filelist_fixture.f (paths relative to the repository root).
// The fixture is not RTL: it is listed here only and must never be added to an rtl/ filelist.

// --- Packages ---
rtl/include/cxl_sched_pkg.sv

// --- Real common modules under test ---
rtl/common/cxl_desc_fifo.sv
rtl/common/cxl_out_hold.sv

// --- Sim-only fixture (no policy, no scheduling logic) ---
sim/cxl_common_ctrl/cxl_common_ctrl_fixture.sv
