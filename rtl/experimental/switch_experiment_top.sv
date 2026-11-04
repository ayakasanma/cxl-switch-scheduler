// switch_experiment_top.sv — Block: EXPERIMENTAL opt-in policy-selectable switch (revision study)
// Spec: specs/CXL_SPEC.md v1.0 sections 3, 4, 5, 6, 7, 8; derived from rtl/top/switch_top.sv;
//       revision experiment docs/experiments/revision-20261023/BASELINES.md
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// This top is an opt-in experiment harness. The accepted rtl/top/switch_top.sv and its
// policies 0-3 are unchanged and remain the primary design; nothing here replaces them.
//
// Common framework, identical for every policy and identical to switch_top:
//   N_SRC cxl_desc_fifo instances (DEPTH entries, full 105-bit descriptors) -> one cxl_out_hold
//   -> memory output. The common FIFO / output-hold boundary is the only buffering: no
//   policy-dependent pipeline, bypass or extra output stage. Synchronous active-low reset.
//   Only the FIFO arrival-metadata option (TS_EN), the context width and the policy slot contents
//   depend on the configuration. RR elaborates no timestamp storage and no arrival counter.
//
// Parameters (overridable with Verilator -G):
//   N_SRC      : 4, 8 or 16 request sources.
//   POLICY     : 0 FCFS, 1 RR, 2 FAI Main, 3 FAI Algorithm-2 (cxl_sched_pkg::policy_e values),
//                4 BLISS-inspired descriptor scheduler (experimental, local encoding L_POLICY_BLISS;
//                the accepted 2-bit package enum is not changed).
//   DEPTH      : per-source FIFO depth, 8, 16 (accepted value) or 32.
//   RR_QUANTUM : RR fires per source turn, 1, 4, 8, 10 (accepted primary) or 16.
//   FAI_W      : FAI window, 64 / 256 (stress) or 5000000 (production).
//   HIGH_QUOTA : FAI Main High visit quota, 5, 10 (accepted) or 20; Low quota stays 10.
//   MAIN_1W    : 0 accepted four-state Main classification, 1 Main-1W (immediate UP->H, DOWN->L,
//                KEEP/S0 retain). Independent of HIGH_QUOTA.
//   Every parameter is range-checked for every POLICY (same convention as switch_top).
//   HIGH_QUOTA != 10 or MAIN_1W != 0 is accepted ONLY with POLICY = 2; any other combination
//   fails elaboration so that a variant flag can never be silently ignored.
//
// Scheduler selection (exactly one branch elaborates):
//   POLICY 0               : accepted cxl_fcfs_sel           (gen_policy_fcfs.u_fcfs_sel)
//   POLICY 1               : accepted cxl_rr_sched           (gen_policy_rr.u_rr_sched)
//   POLICY 2, default flags: accepted cxl_fai_main_sched     (gen_policy_fai_main.u_fai_sched)
//   POLICY 2, variant flags: cxl_fai_variant_sched           (gen_policy_fai_variant.u_fai_sched)
//   POLICY 3               : accepted cxl_fai_main_sched INTERP=1 (gen_policy_fai_alg2.u_fai_sched)
//   POLICY 4               : cxl_bliss_sched                 (gen_policy_bliss.u_bliss_sched)
// With DEPTH=16 and RR_QUANTUM / FAI_W / HIGH_QUOTA / MAIN_1W at their accepted values, policies
// 0-3 instantiate exactly the accepted blocks with the parameters switch_top passes. Pin-level
// agreement with switch_top is checked by simulation (sim/experimental); that is simulation
// evidence, not a formal equivalence proof.
//
// Flattened ports (identical to switch_top): source h occupies bit h of i_in_valid/o_in_ready and
// bits [h*105 +: 105] of i_in_desc.
module switch_experiment_top #(
  parameter int unsigned N_SRC      = 4,
  parameter int unsigned POLICY     = 0,
  parameter int unsigned DEPTH      = 16,
  parameter int unsigned RR_QUANTUM = 10,
  parameter int unsigned FAI_W      = 5000000,
  parameter int unsigned HIGH_QUOTA = 10,
  parameter int unsigned MAIN_1W    = 0
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
  // Per-source occupancy 0..DEPTH (the package fifo_count_t is fixed to the accepted D16)
  localparam int unsigned L_CNT_W = $clog2(DEPTH + 1);

  // Integer encodings of policy_e, comparable with the POLICY parameter
  localparam int unsigned L_POLICY_FCFS     = {{(32-L_POLICY_W){1'b0}}, POLICY_FCFS};
  localparam int unsigned L_POLICY_RR       = {{(32-L_POLICY_W){1'b0}}, POLICY_RR};
  localparam int unsigned L_POLICY_FAI_MAIN = {{(32-L_POLICY_W){1'b0}}, POLICY_FAI_MAIN};
  localparam int unsigned L_POLICY_FAI_ALG2 = {{(32-L_POLICY_W){1'b0}}, POLICY_FAI_ALG2};
  // Experimental-only encoding (outside the accepted 2-bit policy_e)
  localparam int unsigned L_POLICY_BLISS    = 4;

  // Supported values
  localparam int unsigned L_DEPTH_8           = 8;
  localparam int unsigned L_DEPTH_16          = 16;
  localparam int unsigned L_DEPTH_32          = 32;
  localparam int unsigned L_RR_QUANTUM_1      = 1;
  localparam int unsigned L_RR_QUANTUM_4      = 4;
  localparam int unsigned L_RR_QUANTUM_8      = 8;
  localparam int unsigned L_RR_QUANTUM_10     = 10;
  localparam int unsigned L_RR_QUANTUM_16     = 16;
  localparam int unsigned L_FAI_W_PRODUCTION  = 5000000;
  localparam int unsigned L_FAI_W_STRESS_64   = 64;
  localparam int unsigned L_FAI_W_STRESS_256  = 256;
  localparam int unsigned L_HIGH_QUOTA_5      = 5;
  localparam int unsigned L_HIGH_QUOTA_ACCEPT = 10;
  localparam int unsigned L_HIGH_QUOTA_20     = 20;
  localparam int unsigned L_MAIN_1W_OFF       = 0;
  localparam int unsigned L_MAIN_1W_ON        = 1;

  // BLISS adaptation constants (ICCD14 IV-A threshold 4, clearing interval 10,000 cycles)
  localparam int unsigned L_BLISS_THRESHOLD = 4;
  localparam int unsigned L_BLISS_CLEAR     = 10000;

  // Variant flags differ from the accepted Main configuration
  localparam bit L_MAIN_VARIANT = (HIGH_QUOTA != L_HIGH_QUOTA_ACCEPT) ||
                                  (MAIN_1W != L_MAIN_1W_OFF);
  localparam bit L_USE_VARIANT  = (POLICY == L_POLICY_FAI_MAIN) && L_MAIN_VARIANT;

  // Arrival metadata exists for FCFS, both FAI interpretations and BLISS; RR has none.
  localparam bit L_TS_EN = (POLICY == L_POLICY_FCFS) || (POLICY == L_POLICY_FAI_MAIN) ||
                           (POLICY == L_POLICY_FAI_ALG2) || (POLICY == L_POLICY_BLISS);

  // Opaque grant context width carried through cxl_out_hold:
  //   accepted Main / Algorithm-2 : {class, used 0..9} = 1 + $clog2(10) = 5 bits (as switch_top)
  //   variant Main                : 1 + $clog2(max(HIGH_QUOTA, 10)) (5 bits, or 6 for HIGH_QUOTA 20)
  //   FCFS / RR / BLISS           : 1 (driven 0)
  localparam int unsigned L_FAI_QUOTA     = 10;
  localparam int unsigned L_FAI_CTX_W     = 1 + $clog2(L_FAI_QUOTA);
  localparam int unsigned L_VAR_MAX_QUOTA = (HIGH_QUOTA > L_FAI_QUOTA) ? HIGH_QUOTA : L_FAI_QUOTA;
  localparam int unsigned L_VAR_CTX_W     = 1 + $clog2(L_VAR_MAX_QUOTA);
  localparam int unsigned L_CTX_W         = L_USE_VARIANT ? L_VAR_CTX_W :
                                            ((POLICY == L_POLICY_FAI_MAIN) ||
                                             (POLICY == L_POLICY_FAI_ALG2)) ? L_FAI_CTX_W : 1;
  // cxl_fai_main_sched interpretation selector value for Algorithm-2 (Main uses the default 0)
  localparam int unsigned L_FAI_INTERP_ALG2 = 1;

  // --- Signal declarations ---
  // FIFO status, beginning-of-cycle state (source h occupies the h-th slice)
  logic [N_SRC-1:0]          head_valid;
  logic [N_SRC*L_DESC_W-1:0] head_desc;
  logic [N_SRC*L_TS_W-1:0]   head_ts;     // all-zero when L_TS_EN=0
  logic [N_SRC*L_CNT_W-1:0]  fifo_count;
  logic [N_SRC-1:0]          push;        // input handshakes completing at this edge
  logic [N_SRC-1:0]          pop;         // one-hot or zero, from the hold controller

  // Arrival timestamp written with every push of this cycle (same value for all sources)
  ts_t                       arrival_ts;

  // Policy slot outputs: combinational candidate for this cycle
  logic                      cand_valid;
  logic [L_SRC_W-1:0]        cand_source;
  logic [L_CTX_W-1:0]        cand_ctx;

  // Policy slot inputs from the hold controller: grant actually offered this cycle
  logic [L_SRC_W-1:0]        grant_source;
  logic [L_CTX_W-1:0]        grant_ctx;
  logic                      grant_held;
  logic                      fire;

  // --- Continuous assignments ---
  assign push         = i_in_valid & o_in_ready;
  assign o_out_source = grant_source;

  // --- Elaboration-time parameter checks ---
  generate
    if ((N_SRC != 4) && (N_SRC != 8) && (N_SRC != 16)) begin : gen_bad_n_src
      $fatal(1, "switch_experiment_top: N_SRC=%0d is not supported (4, 8 or 16)", N_SRC);
    end
    if ((DEPTH != L_DEPTH_8) && (DEPTH != L_DEPTH_16) && (DEPTH != L_DEPTH_32))
    begin : gen_bad_depth
      $fatal(1, "switch_experiment_top: DEPTH=%0d is not supported (8, 16 or 32)", DEPTH);
    end
    if ((RR_QUANTUM != L_RR_QUANTUM_1) && (RR_QUANTUM != L_RR_QUANTUM_4) &&
        (RR_QUANTUM != L_RR_QUANTUM_8) && (RR_QUANTUM != L_RR_QUANTUM_10) &&
        (RR_QUANTUM != L_RR_QUANTUM_16)) begin : gen_bad_rr_quantum
      $fatal(1, "switch_experiment_top: RR_QUANTUM=%0d is not supported (1, 4, 8, 10 or 16)",
             RR_QUANTUM);
    end
    if ((FAI_W != L_FAI_W_PRODUCTION) && (FAI_W != L_FAI_W_STRESS_64) &&
        (FAI_W != L_FAI_W_STRESS_256)) begin : gen_bad_fai_w
      $fatal(1, "switch_experiment_top: FAI_W=%0d is not supported (5000000, or stress 64 / 256)",
             FAI_W);
    end
    if ((HIGH_QUOTA != L_HIGH_QUOTA_5) && (HIGH_QUOTA != L_HIGH_QUOTA_ACCEPT) &&
        (HIGH_QUOTA != L_HIGH_QUOTA_20)) begin : gen_bad_high_quota
      $fatal(1, "switch_experiment_top: HIGH_QUOTA=%0d is not supported (5, 10 or 20)",
             HIGH_QUOTA);
    end
    if ((MAIN_1W != L_MAIN_1W_OFF) && (MAIN_1W != L_MAIN_1W_ON)) begin : gen_bad_main_1w
      $fatal(1, "switch_experiment_top: MAIN_1W=%0d is not supported (0 or 1)", MAIN_1W);
    end
    if (L_MAIN_VARIANT && (POLICY != L_POLICY_FAI_MAIN)) begin : gen_bad_variant_policy
      $fatal(1, "switch_experiment_top: HIGH_QUOTA=%0d / MAIN_1W=%0d require POLICY=2 (got %0d)",
             HIGH_QUOTA, MAIN_1W, POLICY);
    end
  endgenerate

  // --- Common per-source descriptor FIFOs (identical for every policy except TS_EN) ---
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

  // --- Common output hold/stall controller (identical for every policy) ---
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

  // ===========================================================================================
  // POLICY SLOT BEGIN — the only policy-dependent logic (same interface rules as switch_top):
  //   cand_* are functions of beginning-of-cycle state only; only fire is charged, to
  //   grant_source / grant_ctx; non-fire updates (reset, window index/classification, BLISS clear,
  //   arrival counter) never alter a held grant.
  // ===========================================================================================

  // --- Policy slot part A: shared arrival metadata (FCFS / FAI / BLISS only) ---
  generate
    if (L_TS_EN) begin : gen_arrival_ts
      // Shared free-running 32-bit arrival cycle counter (spec 6), identical to switch_top.
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
      // RR: no arrival counter and no timestamp storage. The FIFOs ignore i_in_ts when TS_EN=0.
      assign arrival_ts = '0;
    end
  endgenerate

  // --- Policy slot part B: scheduler (exactly one branch elaborates) ---
  generate
    if (POLICY == L_POLICY_FCFS) begin : gen_policy_fcfs
      // Accepted FCFS: oldest valid head, ascending source ID on equal timestamps (spec 6).
      logic unused_fcfs;

      assign cand_ctx    = '0;
      assign unused_fcfs = &{1'b0, fifo_count, push, fire, grant_ctx, grant_held};

      cxl_fcfs_sel #(
        .N_SRC (N_SRC),
        .TS_W  (L_TS_W)
      ) u_fcfs_sel (
        .i_eligible (head_valid),
        .i_head_ts  (head_ts),
        .o_valid    (cand_valid),
        .o_source   (cand_source)
      );
    end else if (POLICY == L_POLICY_RR) begin : gen_policy_rr
      // Accepted RR with an experimental quantum (spec 7). No arrival metadata.
      logic unused_rr;

      assign cand_ctx  = '0;
      assign unused_rr = &{1'b0, head_ts, grant_ctx, grant_held};

      cxl_rr_sched #(
        .N_SRC   (N_SRC),
        .QUANTUM (RR_QUANTUM),
        .CNT_W   (L_CNT_W)
      ) u_rr_sched (
        .clk            (clk),
        .rst_n          (rst_n),
        .i_head_valid   (head_valid),
        .i_fifo_count   (fifo_count),
        .i_push         (push),
        .i_fire         (fire),
        .i_grant_source (grant_source),
        .o_cand_valid   (cand_valid),
        .o_cand_source  (cand_source)
      );
    end else if ((POLICY == L_POLICY_FAI_MAIN) && !L_USE_VARIANT) begin : gen_policy_fai_main
      // Accepted FAI Main (spec 8.1-8.5), High/Low 10/10, four-state classification.
      logic unused_fai_main;

      assign unused_fai_main = &{1'b0, grant_held};

      cxl_fai_main_sched #(
        .N_SRC (N_SRC),
        .W     (FAI_W),
        .TS_W  (L_TS_W),
        .CNT_W (L_CNT_W)
      ) u_fai_sched (
        .clk            (clk),
        .rst_n          (rst_n),
        .i_head_valid   (head_valid),
        .i_head_ts      (head_ts),
        .i_fifo_count   (fifo_count),
        .i_push         (push),
        .i_fire         (fire),
        .i_grant_source (grant_source),
        .i_grant_ctx    (grant_ctx),
        .o_cand_valid   (cand_valid),
        .o_cand_source  (cand_source),
        .o_cand_ctx     (cand_ctx)
      );
    end else if (POLICY == L_POLICY_FAI_MAIN) begin : gen_policy_fai_variant
      // EXPERIMENTAL Main variant (HIGH_QUOTA 5/20 and/or Main-1W); opt-in only.
      logic unused_fai_variant;

      assign unused_fai_variant = &{1'b0, grant_held};

      cxl_fai_variant_sched #(
        .N_SRC      (N_SRC),
        .W          (FAI_W),
        .HIGH_QUOTA (HIGH_QUOTA),
        .MAIN_1W    (MAIN_1W),
        .TS_W       (L_TS_W),
        .CNT_W      (L_CNT_W)
      ) u_fai_sched (
        .clk            (clk),
        .rst_n          (rst_n),
        .i_head_valid   (head_valid),
        .i_head_ts      (head_ts),
        .i_fifo_count   (fifo_count),
        .i_push         (push),
        .i_fire         (fire),
        .i_grant_source (grant_source),
        .i_grant_ctx    (grant_ctx),
        .o_cand_valid   (cand_valid),
        .o_cand_source  (cand_source),
        .o_cand_ctx     (cand_ctx)
      );
    end else if (POLICY == L_POLICY_FAI_ALG2) begin : gen_policy_fai_alg2
      // Accepted FAI Algorithm-2 supplement (spec 8.6): cxl_fai_main_sched with INTERP=1.
      logic unused_fai_alg2;

      assign unused_fai_alg2 = &{1'b0, grant_held};

      cxl_fai_main_sched #(
        .N_SRC  (N_SRC),
        .W      (FAI_W),
        .INTERP (L_FAI_INTERP_ALG2),
        .TS_W   (L_TS_W),
        .CNT_W  (L_CNT_W)
      ) u_fai_sched (
        .clk            (clk),
        .rst_n          (rst_n),
        .i_head_valid   (head_valid),
        .i_head_ts      (head_ts),
        .i_fifo_count   (fifo_count),
        .i_push         (push),
        .i_fire         (fire),
        .i_grant_source (grant_source),
        .i_grant_ctx    (grant_ctx),
        .o_cand_valid   (cand_valid),
        .o_cand_source  (cand_source),
        .o_cand_ctx     (cand_ctx)
      );
    end else if (POLICY == L_POLICY_BLISS) begin : gen_policy_bliss
      // EXPERIMENTAL BLISS-inspired descriptor scheduler (cxl_bliss_sched header): non-blacklisted
      // valid heads first, FCFS timestamp / source ID within the group, threshold 4 (count > 4),
      // blacklist clear every 10,000 non-reset cycles. No grant context.
      //   fifo_count, push : BLISS needs head presence only, no occupancy
      //   grant_ctx        : no context (cand_ctx is constant 0)
      //   grant_held       : only fire is counted; the held grant is replayed by cxl_out_hold
      logic unused_bliss;

      assign cand_ctx     = '0;
      assign unused_bliss = &{1'b0, fifo_count, push, grant_ctx, grant_held};

      cxl_bliss_sched #(
        .N_SRC          (N_SRC),
        .THRESHOLD      (L_BLISS_THRESHOLD),
        .CLEAR_INTERVAL (L_BLISS_CLEAR),
        .TS_W           (L_TS_W)
      ) u_bliss_sched (
        .clk            (clk),
        .rst_n          (rst_n),
        .i_head_valid   (head_valid),
        .i_head_ts      (head_ts),
        .i_fire         (fire),
        .i_grant_source (grant_source),
        .o_cand_valid   (cand_valid),
        .o_cand_source  (cand_source)
      );
    end else begin : gen_policy_unknown
      $fatal(1, "switch_experiment_top: POLICY=%0d is not supported (0, 1, 2, 3 or 4)", POLICY);
    end
  endgenerate

  // ===========================================================================================
  // POLICY SLOT END
  // ===========================================================================================

endmodule
