// switch_top.sv — Block: the one policy-selectable CXL scheduler switch top
// Spec: specs/CXL_SPEC.md v1.0 sections 3, 4, 5; docs/phase-3-uarch/common_framework.md item 5
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// Common framework, identical for every policy:
//   N_SRC cxl_desc_fifo instances (D16, 105-bit descriptors) -> one cxl_out_hold -> memory output.
//   Only the arrival-metadata option of the FIFOs (TS_EN) and the contents of the policy slot
//   depend on POLICY. There is no policy-dependent pipeline, bypass or buffering.
//
// Parameters (all overridable with Verilator -G, e.g. -GN_SRC=8 -GPOLICY=1 -GRR_QUANTUM=1):
//   N_SRC      : number of request sources, 4, 8 or 16.
//   POLICY     : integer encoding of cxl_sched_pkg::policy_e
//                0 = POLICY_FCFS, 1 = POLICY_RR, 2 = POLICY_FAI_MAIN, 3 = POLICY_FAI_ALG2.
//   RR_QUANTUM : RR successful transfers per source turn (spec 7): 10 = primary configuration,
//                1 = supplementary variant (D32). Any other value fails elaboration. It is checked
//                for every POLICY but only the POLICY_RR branch consumes it.
//   FAI_W      : FAI window length in cycles (spec 8.1, 8.5): 5000000 = production/primary,
//                64 and 256 = stress-verification variants. Any other value fails elaboration. It
//                is checked for every POLICY but only the two FAI branches consume it.
//
// Flattened ports: source h occupies bit h of i_in_valid/o_in_ready and bits
// [h*105 +: 105] of i_in_desc.
//
// MILESTONE M6 STATUS: POLICY_FCFS (POLICY=0, M3), POLICY_RR (POLICY=1, M4),
// POLICY_FAI_MAIN (POLICY=2, M5) and the supplementary POLICY_FAI_ALG2 (POLICY=3, M6) are
// implemented.
//   FCFS: the shared 32-bit arrival cycle counter (policy slot part A, gen_arrival_ts.arrival_cnt_q)
//         and the common oldest-eligible-head selector cxl_fcfs_sel (gen_policy_fcfs.u_fcfs_sel).
//   RR  : cxl_rr_sched (gen_policy_rr.u_rr_sched; state ptr_q / used_q). RR has no arrival
//         metadata: gen_no_arrival_ts, FIFOs with TS_EN=0, no cxl_fcfs_sel.
//   FAI Main: the same shared arrival counter (gen_arrival_ts.arrival_cnt_q) and cxl_fai_main_sched
//         (gen_policy_fai_main.u_fai_sched; state cls_q / idx_q / b_q / s_q / turn_q / used_q,
//         in-class selector gen_policy_fai_main.u_fai_sched.u_fcfs_sel). Its 5-bit grant context
//         {class, used} is carried by the unchanged cxl_out_hold (L_CTX_W = 5).
//   FAI Algorithm-2: the same arrival counter, FIFOs, cxl_out_hold and cxl_fai_main_sched module
//         with INTERP=1 (gen_policy_fai_alg2.u_fai_sched, same state names and 5-bit context);
//         only the closing-edge transition differs (spec 8.6, fai_alg2.md).
// Any unknown POLICY encoding fails elaboration with an explicit $fatal in the policy slot below.
// There is no default, dummy or pass-through scheduler.
module switch_top #(
  parameter int unsigned N_SRC      = 4,
  parameter int unsigned POLICY     = 0,
  parameter int unsigned RR_QUANTUM = 10,
  parameter int unsigned FAI_W      = 5000000
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
  localparam int unsigned L_CNT_W = $bits(fifo_count_t);

  // Integer encodings of policy_e, comparable with the POLICY parameter
  localparam int unsigned L_POLICY_FCFS     = {{(32-L_POLICY_W){1'b0}}, POLICY_FCFS};
  localparam int unsigned L_POLICY_RR       = {{(32-L_POLICY_W){1'b0}}, POLICY_RR};
  localparam int unsigned L_POLICY_FAI_MAIN = {{(32-L_POLICY_W){1'b0}}, POLICY_FAI_MAIN};
  localparam int unsigned L_POLICY_FAI_ALG2 = {{(32-L_POLICY_W){1'b0}}, POLICY_FAI_ALG2};

  // Arrival metadata exists only for FCFS and both FAI interpretations; RR has structurally none.
  localparam bit L_TS_EN = (POLICY == L_POLICY_FCFS) || (POLICY == L_POLICY_FAI_MAIN) ||
                           (POLICY == L_POLICY_FAI_ALG2);

  // Width of the opaque grant context carried through cxl_out_hold; the hold controller itself
  // does not change. Both FAI interpretations carry {class (1 bit), visit fires already charged
  // 0..9 ($clog2(10) = 4 bits)} = 5 bits (spec 8.3, fai_main.md 1, fai_alg2.md 1). FCFS and RR
  // need no context and keep the minimum width of 1 (driven 0).
  localparam int unsigned L_FAI_QUOTA  = 10;
  localparam int unsigned L_FAI_CTX_W  = 1 + $clog2(L_FAI_QUOTA);
  localparam int unsigned L_CTX_W      = ((POLICY == L_POLICY_FAI_MAIN) ||
                                          (POLICY == L_POLICY_FAI_ALG2)) ? L_FAI_CTX_W : 1;
  // cxl_fai_main_sched interpretation selector value for Algorithm-2 (Main uses the default 0)
  localparam int unsigned L_FAI_INTERP_ALG2 = 1;

  // Supported RR quanta (spec 7): primary 10, supplementary 1 (D32)
  localparam int unsigned L_RR_QUANTUM_PRIMARY = 10;
  localparam int unsigned L_RR_QUANTUM_SUPP    = 1;

  // Supported FAI windows (spec 8.1, 8.5): production 5,000,000, stress 64 / 256
  localparam int unsigned L_FAI_W_PRODUCTION = 5000000;
  localparam int unsigned L_FAI_W_STRESS_64  = 64;
  localparam int unsigned L_FAI_W_STRESS_256 = 256;

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

  // --- Elaboration-time parameter check ---
  generate
    if ((N_SRC != 4) && (N_SRC != 8) && (N_SRC != 16)) begin : gen_bad_n_src
      $fatal(1, "switch_top: N_SRC=%0d is not supported (4, 8 or 16)", N_SRC);
    end
    if ((RR_QUANTUM != L_RR_QUANTUM_PRIMARY) && (RR_QUANTUM != L_RR_QUANTUM_SUPP))
    begin : gen_bad_rr_quantum
      $fatal(1, "switch_top: RR_QUANTUM=%0d is not supported (10 primary or 1 supplementary)",
             RR_QUANTUM);
    end
    if ((FAI_W != L_FAI_W_PRODUCTION) && (FAI_W != L_FAI_W_STRESS_64) &&
        (FAI_W != L_FAI_W_STRESS_256)) begin : gen_bad_fai_w
      $fatal(1, "switch_top: FAI_W=%0d is not supported (5000000 production, or stress 64 / 256)",
             FAI_W);
    end
  endgenerate

  // --- Common per-source descriptor FIFOs (identical for every policy except TS_EN) ---
  generate
    for (genvar h = 0; h < N_SRC; h++) begin : gen_fifo
      cxl_desc_fifo #(
        .DEPTH  (L_FIFO_DEPTH),
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
  // POLICY SLOT BEGIN — the only policy-dependent logic in the switch
  //
  // Uniform internal policy interface (all signals are declared above):
  //   inputs  : clk, rst_n
  //             head_valid [N_SRC]          head present, beginning-of-cycle
  //             fifo_count [N_SRC*L_CNT_W]  occupancy 0..D, beginning-of-cycle
  //             head_ts    [N_SRC*L_TS_W]   head arrival timestamps (meaningful only if L_TS_EN)
  //             push       [N_SRC]          input handshake completing at this edge
  //             fire                        output transfer completing at this edge
  //             grant_source [L_SRC_W]      source offered this cycle (the one that fires/pops)
  //             grant_ctx  [L_CTX_W]        context offered this cycle
  //             grant_held                  1: the offered grant is a latched, stalled grant
  //   outputs : cand_valid, cand_source [L_SRC_W], cand_ctx [L_CTX_W]
  //             arrival_ts [L_TS_W]         part A, only when L_TS_EN
  //
  // Rules for a policy implementation:
  //   - cand_* are combinational functions of beginning-of-cycle state only; they must not depend
  //     on i_out_ready, fire or pop of the same cycle. A candidate must name a source whose
  //     head_valid is 1 whenever any eligible head exists (no control-only bubbles).
  //   - Only fire=1 consumes quota, increments service counts (B/S) and dequeues. Such
  //     fire-driven accounting is charged to grant_source/grant_ctx, never to the policy's own
  //     candidate: while grant_held=1 the candidate is ignored by the hold controller and may
  //     differ from the held grant.
  //   - Approved state updates that are not caused by fire remain allowed: synchronous reset
  //     (spec 5), the FAI window index advancing on every non-reset cycle and the closing-edge
  //     classification with B/S clear (spec 8.1, 8.4), empty-turn / empty-class visit advance and
  //     quota renewal without service consumption (spec 7 Q2, 8.3 Q2), and the free-running
  //     arrival counter (spec 6). None of them may alter a held grant (spec 4 stall
  //     clarification); they take effect for unlocked selections only.
  //   - Post-edge occupancy of source h is fifo_count[h] + push[h] - (fire && grant_source==h).
  // ===========================================================================================

  // --- Policy slot part A: shared arrival metadata (FCFS / FAI only) ---
  generate
    if (L_TS_EN) begin : gen_arrival_ts
      // Shared free-running arrival cycle counter (spec 6, spec 5 reset). Synchronous active-low
      // reset to 0; +1 on every non-reset edge, including output stalls; natural 32-bit wrap.
      // arrival_ts is the current (pre-edge) value, so every push of a cycle stores the same
      // timestamp. Stable hierarchical name for simulation-only access:
      //   switch_top.gen_arrival_ts.arrival_cnt_q
      // There is no synthesized preload/debug port.
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
      // No arrival counter and no timestamp storage. The FIFOs ignore i_in_ts when TS_EN=0.
      assign arrival_ts = '0;
    end
  endgenerate

  // --- Policy slot part B: scheduler (exactly one branch elaborates) ---
  generate
    case (POLICY)
      L_POLICY_FCFS: begin : gen_policy_fcfs
        // FCFS: the oldest valid FIFO head wins, ascending source ID on equal timestamps (spec 6).
        // The candidate is a combinational function of beginning-of-cycle head state only.
        // Policy-slot inputs FCFS does not consume, reduced into a deliberately unused net
        // (same idiom as cxl_desc_fifo gen_no_ts):
        //   fifo_count : FCFS needs only head presence, not occupancy
        //   push       : arrival order is carried entirely by the stored timestamps
        //   fire       : FCFS keeps no service/quota accounting
        //   grant_ctx  : FCFS uses no grant context (cand_ctx is constant 0)
        //   grant_held : FCFS state is unaffected by a held grant (no per-grant state)
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
      end
      L_POLICY_RR: begin : gen_policy_rr
        // RR: first nonempty head circularly from the polling pointer, at most RR_QUANTUM fires
        // per source turn, advance on quantum expiry or post-edge emptiness (spec 7, Q2/D26).
        // The candidate depends on beginning-of-cycle head_valid and RR state only; the state is
        // charged with fire to grant_source (the grant actually offered, possibly held).
        // L_TS_EN=0 for RR: gen_no_arrival_ts, no timestamp storage, no arrival counter and no
        // oldest-head selector. cand_ctx stays 0 (L_CTX_W=1).
        // Policy-slot inputs RR does not consume, reduced into a deliberately unused net
        // (same idiom as gen_policy_fcfs):
        //   head_ts    : constant 0 (TS_EN=0); RR uses no arrival metadata
        //   grant_ctx  : RR uses no grant context (cand_ctx is constant 0)
        //   grant_held : RR charges only fire; a held grant changes nothing until it fires
        // Stable simulation-only state names:
        //   switch_top.gen_policy_rr.u_rr_sched.ptr_q, switch_top.gen_policy_rr.u_rr_sched.used_q
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
      end
      L_POLICY_FAI_MAIN: begin : gen_policy_fai_main
        // FAI-inspired Main (spec 8.1-8.5, fai_main.md): four-state per-source classes from
        // window-local B/S thresholds, High/Low 10/10 visits, shared FCFS selection inside the
        // chosen effective class. The candidate depends on beginning-of-cycle head state and
        // policy state only; quota and B/S are charged with fire to grant_source / grant_ctx
        // (the grant actually offered, possibly held, with its retained {class, used} context).
        // The window index and closing-edge classification advance on every non-reset edge.
        // cand_ctx / grant_ctx = {class (0 = High, 1 = Low), used (0..9)}, L_CTX_W = 5.
        // Policy-slot input FAI Main does not consume, reduced into a deliberately unused net
        // (same idiom as gen_policy_fcfs):
        //   grant_held : FAI charges only fire; the held grant is replayed by cxl_out_hold
        // Stable simulation-only state names (see cxl_fai_main_sched header):
        //   switch_top.gen_policy_fai_main.u_fai_sched.{cls_q, idx_q, b_q, s_q, turn_q, used_q}
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
      end
      L_POLICY_FAI_ALG2: begin : gen_policy_fai_alg2
        // FAI Algorithm-2 supplement (spec 8.6, fai_alg2.md): the SAME cxl_fai_main_sched block
        // with INTERP=1. Identical candidate, 10/10 visits, window-local B/S, 32-bit thresholds,
        // FCFS in-class selector, 5-bit {class, used} context, FIFOs, arrival counter and
        // cxl_out_hold as gen_policy_fai_main; only the closing-edge state transition differs
        // (stable High/Low or Buffer with target p serviced immediately, KEEP/idle retain Buffer).
        // Policy-slot input not consumed, reduced into a deliberately unused net:
        //   grant_held : FAI charges only fire; the held grant is replayed by cxl_out_hold
        // Stable simulation-only state names:
        //   switch_top.gen_policy_fai_alg2.u_fai_sched.{cls_q, idx_q, b_q, s_q, turn_q, used_q}
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
      end
      default: begin : gen_policy_unknown
        $fatal(1, "switch_top: POLICY=%0d is not a cxl_sched_pkg::policy_e encoding", POLICY);
      end
    endcase
  endgenerate

  // ===========================================================================================
  // POLICY SLOT END
  // ===========================================================================================

endmodule
