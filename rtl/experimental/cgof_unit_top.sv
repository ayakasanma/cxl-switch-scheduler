// cgof_unit_top.sv — Block: EXPERIMENTAL CGOF standalone verification switch (opt-in only)
// Spec: specs/CXL_SPEC.md v1.0 sections 3, 4, 5, 6, 8.1, 8.2, 8.5; derived from
//       rtl/experimental/switch_experiment_top.sv; independent model
//       refc/cxl_model/experimental.py (policy "CGOF", high_weight 1 / 2, ordering
//       "oldest-first" / "eligible-round-robin")
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// Standalone top for CGOF (Credit-Gated Oldest-First); it is not integrated into the shared
// switch_experiment_top policy slot. The framework is the same common one as switch_top /
// switch_experiment_top: N_SRC cxl_desc_fifo instances (DEPTH entries, full 105-bit descriptors,
// 32-bit arrival timestamps) -> one cxl_out_hold -> memory output, with the shared free-running
// 32-bit arrival counter. No policy-dependent pipeline, bypass or extra output stage; the CGOF
// credit context travels through the unchanged cxl_out_hold. The ordering control does not change
// this boundary (timestamps are stored for both orderings).
//
// Parameters (overridable with Verilator -G):
//   N_SRC       : 4, 8 or 16 request sources.
//   DEPTH       : per-source FIFO depth, 8, 16 (accepted value) or 32.
//   FAI_W       : classification window, 64 / 256 (stress) or 5000000 (production);
//                 range-checked inside cxl_cgof_sched.
//   HIGH_WEIGHT : High:Low allocation, 2 = CGOF(2:1), 1 = CGOF(1:1); range-checked inside
//                 cxl_cgof_sched.
//   ELIGIBLE_RR : 0 = oldest-first (default), 1 = credit-gated eligible round-robin;
//                 range-checked inside cxl_cgof_sched.
//
// Ports are identical to switch_experiment_top: source h occupies bit h of i_in_valid/o_in_ready
// and bits [h*105 +: 105] of i_in_desc. Stable hierarchical names for verification:
//   gen_arrival_ts.arrival_cnt_q, u_out_hold, u_cgof_sched.{cls_q,idx_q,b_q,s_q,credit_q},
//   u_cgof_sched.gen_order_rr.rr_ptr_q (ELIGIBLE_RR = 1).
module cgof_unit_top #(
  parameter int unsigned N_SRC       = 4,
  parameter int unsigned DEPTH       = 16,
  parameter int unsigned FAI_W       = 5000000,
  parameter int unsigned HIGH_WEIGHT = 2,
  parameter int unsigned ELIGIBLE_RR = 0
) (
  input  logic                                     clk,
  input  logic                                     rst_n,
  // Per-source input handshake
  input  logic [N_SRC-1:0]                         i_in_valid,
  output logic [N_SRC-1:0]                         o_in_ready,
  input  logic [N_SRC*cxl_sched_pkg::L_DESC_W-1:0] i_in_desc,
  // Single memory-output handshake
  output logic                                     o_out_valid,
  input  logic                                     i_out_ready,
  output logic [cxl_sched_pkg::L_DESC_W-1:0]       o_out_desc,
  output logic [$clog2(N_SRC)-1:0]                 o_out_source
);

  import cxl_sched_pkg::*;

  // --- Local parameters ---
  localparam int unsigned L_SRC_W = $clog2(N_SRC);
  // Per-source occupancy 0..DEPTH
  localparam int unsigned L_CNT_W = $clog2(DEPTH + 1);

  // Supported values
  localparam int unsigned L_N_SRC_4  = 4;
  localparam int unsigned L_N_SRC_8  = 8;
  localparam int unsigned L_N_SRC_16 = 16;
  localparam int unsigned L_DEPTH_8  = 8;
  localparam int unsigned L_DEPTH_16 = 16;
  localparam int unsigned L_DEPTH_32 = 32;

  // CGOF keeps arrival metadata (oldest eligible head; stored for both orderings)
  localparam bit          L_TS_EN = 1'b1;

  // Grant context: {class snapshot, refill} for 2:1 (N_SRC+1 bits), {refill} for 1:1 (1 bit);
  // must equal cxl_cgof_sched L_CTX_W
  localparam int unsigned L_CTX_W = (HIGH_WEIGHT > 1) ? (N_SRC + 1) : 1;

  // --- Signal declarations ---
  // FIFO status, beginning-of-cycle state (source h occupies the h-th slice)
  logic [N_SRC-1:0]          head_valid;
  logic [N_SRC*L_DESC_W-1:0] head_desc;
  logic [N_SRC*L_TS_W-1:0]   head_ts;
  logic [N_SRC*L_CNT_W-1:0]  fifo_count;
  logic [N_SRC-1:0]          pop;         // one-hot or zero, from the hold controller

  // Arrival timestamp written with every push of this cycle (same value for all sources)
  ts_t                       arrival_ts;

  // Policy candidate for this cycle
  logic                      cand_valid;
  logic [L_SRC_W-1:0]        cand_source;
  logic [L_CTX_W-1:0]        cand_ctx;

  // Grant actually offered this cycle (latched while held)
  logic [L_SRC_W-1:0]        grant_source;
  logic [L_CTX_W-1:0]        grant_ctx;
  logic                      grant_held;
  logic                      fire;

  // Unused framework outputs: CGOF needs head presence only (no occupancy), counts only fires
  // (never pushes or held cycles); the held grant is replayed by cxl_out_hold.
  logic                      unused_cgof;

  // --- Continuous assignments ---
  assign o_out_source = grant_source;
  assign unused_cgof  = &{1'b0, fifo_count, grant_held};

  // --- Elaboration-time parameter checks (FAI_W, HIGH_WEIGHT, ELIGIBLE_RR: in cxl_cgof_sched) ---
  generate
    if ((N_SRC != L_N_SRC_4) && (N_SRC != L_N_SRC_8) && (N_SRC != L_N_SRC_16))
    begin : gen_bad_n_src
      $fatal(1, "cgof_unit_top: N_SRC=%0d is not supported (4, 8 or 16)", N_SRC);
    end
    if ((DEPTH != L_DEPTH_8) && (DEPTH != L_DEPTH_16) && (DEPTH != L_DEPTH_32))
    begin : gen_bad_depth
      $fatal(1, "cgof_unit_top: DEPTH=%0d is not supported (8, 16 or 32)", DEPTH);
    end
  endgenerate

  // --- Common per-source descriptor FIFOs ---
  generate
    for (genvar h = 0; h < N_SRC; h++) begin : gen_fifo
      cxl_desc_fifo #(
        .DEPTH  (DEPTH),
        .DESC_W (L_DESC_W),
        .TS_EN  (L_TS_EN),
        .TS_W   (L_TS_W)
      ) u_fifo (
        .clk          (clk),
        .rst_n        (rst_n),
        .i_in_valid   (i_in_valid[h]),
        .o_in_ready   (o_in_ready[h]),
        .i_in_desc    (i_in_desc[h*L_DESC_W +: L_DESC_W]),
        .i_in_ts      (arrival_ts),
        .i_pop        (pop[h]),
        .o_head_valid (head_valid[h]),
        .o_head_desc  (head_desc[h*L_DESC_W +: L_DESC_W]),
        .o_head_ts    (head_ts[h*L_TS_W +: L_TS_W]),
        .o_count      (fifo_count[h*L_CNT_W +: L_CNT_W])
      );
    end
  endgenerate

  // --- Common output hold/stall controller ---
  cxl_out_hold #(
    .N_SRC  (N_SRC),
    .DESC_W (L_DESC_W),
    .CTX_W  (L_CTX_W)
  ) u_out_hold (
    .clk           (clk),
    .rst_n         (rst_n),
    .i_cand_valid  (cand_valid),
    .i_cand_source (cand_source),
    .i_cand_ctx    (cand_ctx),
    .i_head_valid  (head_valid),
    .i_head_desc   (head_desc),
    .o_out_valid   (o_out_valid),
    .i_out_ready   (i_out_ready),
    .o_out_desc    (o_out_desc),
    .o_out_source  (grant_source),
    .o_grant_ctx   (grant_ctx),
    .o_grant_held  (grant_held),
    .o_fire        (fire),
    .o_pop         (pop)
  );

  // --- CGOF policy ---
  cxl_cgof_sched #(
    .N_SRC       (N_SRC),
    .W           (FAI_W),
    .HIGH_WEIGHT (HIGH_WEIGHT),
    .ELIGIBLE_RR (ELIGIBLE_RR),
    .TS_W        (L_TS_W)
  ) u_cgof_sched (
    .clk            (clk),
    .rst_n          (rst_n),
    .i_head_valid   (head_valid),
    .i_head_ts      (head_ts),
    .i_fire         (fire),
    .i_grant_source (grant_source),
    .i_grant_ctx    (grant_ctx),
    .o_cand_valid   (cand_valid),
    .o_cand_source  (cand_source),
    .o_cand_ctx     (cand_ctx)
  );

  // --- Shared free-running 32-bit arrival cycle counter (spec 6), as switch_experiment_top ---
  // (named generate scope kept so the counter path matches switch_experiment_top)
  generate
    if (L_TS_EN) begin : gen_arrival_ts
      ts_t arrival_cnt_q;

      assign arrival_ts = arrival_cnt_q;

      always_ff @(posedge clk) begin
        if (!rst_n) begin
          arrival_cnt_q <= '0;
        end else begin
          arrival_cnt_q <= arrival_cnt_q + 1'b1;
        end
      end
    end else begin : gen_no_arrival_ts
      assign arrival_ts = '0;  // unreachable: CGOF always stores arrival metadata
    end
  endgenerate

endmodule
