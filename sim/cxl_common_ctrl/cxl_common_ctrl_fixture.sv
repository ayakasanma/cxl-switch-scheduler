// cxl_common_ctrl_fixture.sv — SIMULATION-ONLY candidate-injection fixture (milestone M2)
// Spec: specs/CXL_SPEC.md v1.0 sections 3, 4, 5 (common FIFO / output-hold cycle contract)
//
// THIS IS NOT A POLICY AND NOT A FUNCTIONAL SWITCH BASELINE. It is a verification fixture that
// lives only under sim/, is listed in no rtl/ filelist and is never synthesized. It contains no
// scheduling, arbitration or selection logic of any kind.
//
// Purpose: verify the REAL common blocks together before any policy exists. It instantiates
//   N_SRC x cxl_desc_fifo (D16, 105-bit descriptors)  ->  one cxl_out_hold
// wired exactly as rtl/top/switch_top.sv wires them (same port-to-port connections, same
// parameters). The only difference from switch_top is that the signals switch_top leaves to its
// policy slot are brought out as ports:
//   - policy-slot OUTPUTS become fixture INPUTS driven by the cocotb test:
//       i_cand_valid / i_cand_source / i_cand_ctx  (candidate of this cycle)
//       i_arrival_ts                               (timestamp written with every push)
//   - policy-slot INPUTS become fixture observation OUTPUTS:
//       o_head_valid, o_head_desc, o_head_ts, o_fifo_count, o_push, o_pop, o_fire,
//       o_grant_ctx, o_grant_held (o_out_source is the grant source, as in switch_top)
// The observation outputs are plain wires of existing nets; they add no state and no logic.
//
// Parameters: N_SRC (4, 8 or 16), CTX_W (opaque grant-context width, switch_top currently uses 1),
// TS_EN (arrival-metadata option of the FIFOs, a per-policy constant in switch_top).
module cxl_common_ctrl_fixture #(
  parameter int unsigned N_SRC = 4,
  parameter int unsigned CTX_W = 4,
  parameter bit          TS_EN = 1'b0
) (
  input  logic                                                   clk,
  input  logic                                                   rst_n,
  // Per-source input handshake (as switch_top)
  input  logic [N_SRC-1:0]                                       i_in_valid,
  output logic [N_SRC-1:0]                                       o_in_ready,
  input  logic [N_SRC*cxl_sched_pkg::L_DESC_W-1:0]               i_in_desc,
  // Injected policy-slot outputs
  input  logic [cxl_sched_pkg::L_TS_W-1:0]                       i_arrival_ts,
  input  logic                                                   i_cand_valid,
  input  logic [$clog2(N_SRC)-1:0]                               i_cand_source,
  input  logic [CTX_W-1:0]                                       i_cand_ctx,
  // Single memory-output handshake (as switch_top)
  output logic                                                   o_out_valid,
  input  logic                                                   i_out_ready,
  output logic [cxl_sched_pkg::L_DESC_W-1:0]                     o_out_desc,
  output logic [$clog2(N_SRC)-1:0]                               o_out_source,
  // Observation of the policy-slot inputs
  output logic [CTX_W-1:0]                                       o_grant_ctx,
  output logic                                                   o_grant_held,
  output logic                                                   o_fire,
  output logic [N_SRC-1:0]                                       o_pop,
  output logic [N_SRC-1:0]                                       o_push,
  output logic [N_SRC-1:0]                                       o_head_valid,
  output logic [N_SRC*cxl_sched_pkg::L_DESC_W-1:0]               o_head_desc,
  output logic [N_SRC*cxl_sched_pkg::L_TS_W-1:0]                 o_head_ts,
  output logic [N_SRC*$bits(cxl_sched_pkg::fifo_count_t)-1:0]    o_fifo_count
);

  import cxl_sched_pkg::*;

  // --- Local parameters ---
  localparam int unsigned L_CNT_W = $bits(fifo_count_t);

  // --- Continuous assignments (observation only) ---
  assign o_push = i_in_valid & o_in_ready;

  // --- Elaboration-time parameter check (same rule as switch_top) ---
  generate
    if ((N_SRC != 4) && (N_SRC != 8) && (N_SRC != 16)) begin : gen_bad_n_src
      $fatal(1, "cxl_common_ctrl_fixture: N_SRC=%0d is not supported (4, 8 or 16)", N_SRC);
    end
  endgenerate

  // --- Common per-source descriptor FIFOs (connections identical to switch_top) ---
  generate
    for (genvar h = 0; h < N_SRC; h++) begin : gen_fifo
      cxl_desc_fifo #(
        .DEPTH  (L_FIFO_DEPTH),
        .DESC_W (L_DESC_W),
        .TS_EN  (TS_EN),
        .TS_W   (L_TS_W)
      ) u_fifo (
        .clk          (clk),
        .rst_n        (rst_n),
        .i_in_valid   (i_in_valid[h]),
        .o_in_ready   (o_in_ready[h]),
        .i_in_desc    (i_in_desc[h*L_DESC_W +: L_DESC_W]),
        .i_in_ts      (i_arrival_ts),
        .i_pop        (o_pop[h]),
        .o_head_valid (o_head_valid[h]),
        .o_head_desc  (o_head_desc[h*L_DESC_W +: L_DESC_W]),
        .o_head_ts    (o_head_ts[h*L_TS_W +: L_TS_W]),
        .o_count      (o_fifo_count[h*L_CNT_W +: L_CNT_W])
      );
    end
  endgenerate

  // --- Common output hold/stall controller (connections identical to switch_top) ---
  cxl_out_hold #(
    .N_SRC  (N_SRC),
    .DESC_W (L_DESC_W),
    .CTX_W  (CTX_W)
  ) u_out_hold (
    .clk           (clk),
    .rst_n         (rst_n),
    .i_cand_valid  (i_cand_valid),
    .i_cand_source (i_cand_source),
    .i_cand_ctx    (i_cand_ctx),
    .i_head_valid  (o_head_valid),
    .i_head_desc   (o_head_desc),
    .o_out_valid   (o_out_valid),
    .i_out_ready   (i_out_ready),
    .o_out_desc    (o_out_desc),
    .o_out_source  (o_out_source),
    .o_grant_ctx   (o_grant_ctx),
    .o_grant_held  (o_grant_held),
    .o_fire        (o_fire),
    .o_pop         (o_pop)
  );

endmodule
