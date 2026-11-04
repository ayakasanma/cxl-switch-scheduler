// cxl_fai_variant_sched.sv — Block: EXPERIMENTAL FAI-inspired Main variants (opt-in only)
// Spec: specs/CXL_SPEC.md v1.0 sections 4, 5, 6, 8.1-8.5; derived from the accepted
//       rtl/common/cxl_fai_main_sched.sv (INTERP=0 Main); revision experiment
//       docs/experiments/revision-20261023/BASELINES.md (F7 high-quota sweep, Main-1W arm)
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// This block is NOT the accepted Main scheduler and is never used for the default configuration.
// rtl/experimental/switch_experiment_top.sv elaborates it only for POLICY=2 with HIGH_QUOTA != 10
// or MAIN_1W = 1; default Main and Algorithm-2 use the unchanged accepted cxl_fai_main_sched.
// Algorithm-2 is deliberately not available here (Main-1W is distinct from Algorithm-2).
//
// Relative to the accepted Main block exactly three things differ; everything else (candidate,
// class-filtered FCFS selector, fire-only charging to the grant actually offered, class_live with
// post-edge occupancy, window index, B/S, closing fire inclusion, 32-bit thresholds, reset) is the
// same logic:
//   1. Quota context width: L_USED_W = $clog2(max(HIGH_QUOTA, L_LOW_QUOTA)), L_CTX_W = 1+L_USED_W.
//      HIGH_QUOTA 5 or 10 -> 4-bit used, 5-bit context; HIGH_QUOTA 20 -> 5-bit used, 6-bit
//      context. The context is carried opaque by the common cxl_out_hold, so a held grant keeps
//      its {class, used} across stalls and across closing-edge classification.
//   2. Per-class visit expiry: a High visit expires at HIGH_QUOTA fires, a Low visit at
//      L_LOW_QUOTA = 10 fires (the visit class is the charged context class, not the source's
//      current class).
//   3. Classification hook (closing edge only), selected by MAIN_1W:
//        MAIN_1W = 0 : accepted Main four-state table (spec 8.2), identical to cxl_fai_main_sched
//        MAIN_1W = 1 : Main-1W, independent one-support-window interpretation:
//                        UP   -> CLS_H (effective High immediately)
//                        DOWN -> CLS_L (effective Low immediately)
//                        KEEP / S0 -> retain the current effective class (CLS_H or CLS_L)
//                      Same UP/DOWN inequalities, same B/S and W, same quota rules. Under MAIN_1W
//                      only CLS_H / CLS_L are reachable from reset, so bit1 of every cls_q entry is
//                      structurally constant 0 (it is kept so the register map and the state
//                      encoding stay identical to the accepted block).
//
// Policy state (all counted; nothing replaces FIFO or arrival metadata):
//   cls_q  [N_SRC][2]      : per-source class, fai_cls_e, encoding as cxl_fai_main_sched
//   idx_q  [L_IDX_W]       : window index 0..W-1
//   b_q    [N_SRC][L_BS_W] : window-local successful fires per source
//   s_q    [L_BS_W]        : window-local successful fires of all sources, s_q = sum(b_q)
//   turn_q                 : class of the current visit, 0 = High, 1 = Low
//   used_q [L_USED_W]      : fires already charged to the current visit, 0..quota(turn_q)-1
//   Stable hierarchical names inside switch_experiment_top:
//     switch_experiment_top.gen_policy_fai_variant.u_fai_sched.{cls_q,idx_q,b_q,s_q,turn_q,used_q}
//
// Grant context (L_CTX_W bits, opaque to cxl_out_hold): {cls, used} = fai_ctx_t
//   ctx[L_USED_W]     cls  : class of the visit the transfer is charged to, 0 = High, 1 = Low
//   ctx[L_USED_W-1:0] used : fires already charged to that visit before this transfer
//
// Visit/quota update, ONLY on an edge with i_fire=1, charged to {Cg, Ug} = i_grant_ctx:
//   n = Ug + 1, quota(Cg) = (Cg == High) ? HIGH_QUOTA : L_LOW_QUOTA
//   n == quota(Cg) or !class_live : turn_q <= !Cg, used_q <= 0
//   otherwise                     : turn_q <= Cg,  used_q <= n
//
// N_SRC must be a power of two >= 2, W one of 64, 256, 5,000,000, HIGH_QUOTA one of 5, 10, 20 and
// MAIN_1W 0 or 1; all are checked at elaboration.
module cxl_fai_variant_sched #(
  parameter  int unsigned N_SRC       = 4,
  parameter  int unsigned W           = 5000000,
  parameter  int unsigned HIGH_QUOTA  = 10,
  parameter  int unsigned MAIN_1W     = 0,
  parameter  int unsigned TS_W        = cxl_sched_pkg::L_TS_W,
  parameter  int unsigned CNT_W       = $bits(cxl_sched_pkg::fifo_count_t),
  // Low quota is fixed at the spec 8.3 value; context = {class, used}
  localparam int unsigned L_LOW_QUOTA = 10,
  localparam int unsigned L_MAX_QUOTA = (HIGH_QUOTA > L_LOW_QUOTA) ? HIGH_QUOTA : L_LOW_QUOTA,
  localparam int unsigned L_USED_W    = $clog2(L_MAX_QUOTA),
  localparam int unsigned L_CTX_W     = 1 + L_USED_W
) (
  input  logic                     clk,
  input  logic                     rst_n,
  // Beginning-of-cycle FIFO state (source h occupies the h-th slice)
  input  logic [N_SRC-1:0]         i_head_valid,
  input  logic [N_SRC*TS_W-1:0]    i_head_ts,
  input  logic [N_SRC*CNT_W-1:0]   i_fifo_count,
  // Edge events of this cycle and the grant actually offered (possibly held)
  input  logic [N_SRC-1:0]         i_push,
  input  logic                     i_fire,
  input  logic [$clog2(N_SRC)-1:0] i_grant_source,
  input  logic [L_CTX_W-1:0]       i_grant_ctx,
  // Candidate for this cycle
  output logic                     o_cand_valid,
  output logic [$clog2(N_SRC)-1:0] o_cand_source,
  output logic [L_CTX_W-1:0]       o_cand_ctx
);

  // --- Local parameters ---
  localparam int unsigned L_SRC_W = $clog2(N_SRC);
  localparam int unsigned L_IDX_W = $clog2(W);       // window index 0..W-1
  localparam int unsigned L_BS_W  = $clog2(W + 1);   // B/S counts 0..W
  // post-edge occupancy: one bit wider than the count so count + push cannot overflow
  localparam int unsigned L_OCC_W = CNT_W + 1;
  // Threshold intermediates: common 32-bit unsigned representation (spec 8.5)
  localparam int unsigned L_THR_W = 32;

  // Supported windows (spec 8.1, 8.5): production and the two stress-verification variants
  localparam int unsigned L_W_PRODUCTION = 5000000;
  localparam int unsigned L_W_STRESS_64  = 64;
  localparam int unsigned L_W_STRESS_256 = 256;

  // Supported experimental High quotas (revision F7 sweep): 5, 10 (accepted value), 20
  localparam int unsigned L_HIGH_QUOTA_5  = 5;
  localparam int unsigned L_HIGH_QUOTA_10 = 10;
  localparam int unsigned L_HIGH_QUOTA_20 = 20;

  // Threshold coefficients (spec 8.1): UP iff 10*N*B < 3*S, DOWN iff N*B > S
  localparam int unsigned L_UP_B_COEF = 10;
  localparam int unsigned L_UP_S_COEF = 3;

  // Largest UP product 10*N*W, computed in 64 bits for the elaboration range check
  localparam logic [63:0] L_UP_MAX_PRODUCT = 64'(L_UP_B_COEF) * 64'(N_SRC) * 64'(W);
  localparam logic [63:0] L_THR_MAX        = (64'(1) << L_THR_W) - 64'(1);

  localparam logic [L_THR_W-1:0]  L_UP_B_MUL   = L_THR_W'(L_UP_B_COEF * N_SRC);
  localparam logic [L_THR_W-1:0]  L_UP_S_MUL   = L_THR_W'(L_UP_S_COEF);
  localparam logic [L_THR_W-1:0]  L_DOWN_B_MUL = L_THR_W'(N_SRC);
  localparam logic [L_IDX_W-1:0]  L_IDX_LAST   = L_IDX_W'(W - 1);
  localparam logic [L_USED_W-1:0] L_QUOTA_HI_V = L_USED_W'(HIGH_QUOTA);
  localparam logic [L_USED_W-1:0] L_QUOTA_LO_V = L_USED_W'(L_LOW_QUOTA);

  // Visit / effective class encoding of turn_q and the context class bit
  localparam logic L_CLS_HIGH = 1'b0;
  localparam logic L_CLS_LOW  = 1'b1;
  // Bit of the four-state encoding that holds the effective class (1 = Low)
  localparam int unsigned L_EFF_LOW_BIT = 0;

  // Classification hook selector values
  localparam int unsigned L_MAIN_4STATE = 0;
  localparam int unsigned L_MAIN_1W     = 1;

  // --- Types ---
  // Main four-state class: bit0 = effective Low, bit1 = pending (buffer) change
  typedef enum logic [1:0] {
    CLS_H   = 2'b00,  // stable High
    CLS_L   = 2'b01,  // stable Low
    CLS_B_H = 2'b10,  // buffer, effective High, decrease pending (unreachable under MAIN_1W)
    CLS_B_L = 2'b11   // buffer, effective Low, increase pending (unreachable under MAIN_1W)
  } fai_cls_e;

  // Grant context carried through cxl_out_hold, {cls, used} (cls is the most significant bit)
  typedef struct packed {
    logic                cls;   // 0 = High, 1 = Low
    logic [L_USED_W-1:0] used;  // fires already charged to the visit, 0..quota(cls)-1
  } fai_ctx_t;

  // --- Functions ---
  // Main closing-edge transition (spec 8.2 table), identical to cxl_fai_main_sched cls_next().
  // Pure: uses only its arguments. s0 cancels a pending change and keeps the effective class.
  function automatic fai_cls_e cls_next(input fai_cls_e cur, input logic up, input logic down,
                                        input logic s0);
    case (cur)
      CLS_H: begin
        if (s0)        cls_next = CLS_H;
        else if (up)   cls_next = CLS_H;
        else if (down) cls_next = CLS_B_H;
        else           cls_next = CLS_H;
      end
      CLS_B_H: begin
        if (s0)        cls_next = CLS_H;
        else if (up)   cls_next = CLS_H;
        else if (down) cls_next = CLS_L;
        else           cls_next = CLS_H;
      end
      CLS_L: begin
        if (s0)        cls_next = CLS_L;
        else if (up)   cls_next = CLS_B_L;
        else if (down) cls_next = CLS_L;
        else           cls_next = CLS_L;
      end
      CLS_B_L: begin
        if (s0)        cls_next = CLS_L;
        else if (up)   cls_next = CLS_H;
        else if (down) cls_next = CLS_L;
        else           cls_next = CLS_L;
      end
      default: cls_next = CLS_H;  // unreachable: all four encodings are states
    endcase
  endfunction

  // Main-1W closing-edge transition. Pure: uses only its arguments.
  // UP / DOWN take effect immediately; KEEP and the zero-service window retain the current
  // effective class as a stable state. UP and DOWN are mutually exclusive for 0 <= B <= S.
  function automatic fai_cls_e cls_next_1w(input fai_cls_e cur, input logic up, input logic down);
    if (up)                              cls_next_1w = CLS_H;
    else if (down)                       cls_next_1w = CLS_L;
    else if (cur[L_EFF_LOW_BIT] == 1'b1) cls_next_1w = CLS_L;
    else                                 cls_next_1w = CLS_H;
  endfunction

  // --- Signal declarations ---
  // Policy state
  fai_cls_e [N_SRC-1:0]             cls_q;
  fai_cls_e [N_SRC-1:0]             cls_d;
  logic [L_IDX_W-1:0]               idx_q;
  logic [L_IDX_W-1:0]               idx_d;
  logic [N_SRC-1:0][L_BS_W-1:0]     b_q;
  logic [N_SRC-1:0][L_BS_W-1:0]     b_d;
  logic [L_BS_W-1:0]                s_q;
  logic [L_BS_W-1:0]                s_d;
  logic                             turn_q;
  logic                             turn_d;
  logic [L_USED_W-1:0]              used_q;
  logic [L_USED_W-1:0]              used_d;

  // Candidate
  logic [N_SRC-1:0]                 eff_low;      // current effective class per source, 1 = Low
  logic [N_SRC-1:0]                 elig_hi;
  logic [N_SRC-1:0]                 elig_lo;
  logic                             turn_has_elig;
  logic                             cand_cls;
  logic [N_SRC-1:0]                 cand_mask;
  fai_ctx_t                         cand_ctx;

  // Charge of the fired grant
  fai_ctx_t                         grant_ctx;
  logic [N_SRC-1:0]                 pop;
  logic [N_SRC-1:0]                 live;         // post-edge occupancy > 0
  logic [N_SRC-1:0]                 grant_cls_mask;
  logic                             class_live;
  logic [L_USED_W-1:0]              used_new;
  logic [L_USED_W-1:0]              grant_quota;  // quota of the charged visit class
  logic                             visit_end;

  // Window accounting and parallel classification
  logic                             closing;
  logic [N_SRC-1:0][L_BS_W-1:0]     b_close;
  logic [L_BS_W-1:0]                s_close;
  logic [N_SRC-1:0][L_THR_W-1:0]    up_lhs;       // (10*N) * b_close[h]
  logic [N_SRC-1:0][L_THR_W-1:0]    down_lhs;     // N * b_close[h]
  logic [L_THR_W-1:0]               up_rhs;       // 3 * s_close
  logic [L_THR_W-1:0]               down_rhs;     // s_close
  logic [N_SRC-1:0]                 ev_up;
  logic [N_SRC-1:0]                 ev_down;
  logic                             ev_s0;
  fai_cls_e [N_SRC-1:0]             cls_cl;       // classification result of a closing edge

  // --- Elaboration-time parameter checks ---
  generate
    if ((N_SRC < 2) || (N_SRC != (1 << L_SRC_W))) begin : gen_bad_n_src
      $fatal(1, "cxl_fai_variant_sched: N_SRC=%0d must be a power of two >= 2", N_SRC);
    end
    if ((W != L_W_PRODUCTION) && (W != L_W_STRESS_64) && (W != L_W_STRESS_256))
    begin : gen_bad_w
      $fatal(1, "cxl_fai_variant_sched: W=%0d is not supported (5000000, or stress 64 / 256)", W);
    end
    if (L_UP_MAX_PRODUCT > L_THR_MAX) begin : gen_bad_thr_range
      $fatal(1, "cxl_fai_variant_sched: 10*N_SRC*W (N_SRC=%0d, W=%0d) exceeds %0d-bit thresholds",
             N_SRC, W, L_THR_W);
    end
    if ((HIGH_QUOTA != L_HIGH_QUOTA_5) && (HIGH_QUOTA != L_HIGH_QUOTA_10) &&
        (HIGH_QUOTA != L_HIGH_QUOTA_20)) begin : gen_bad_high_quota
      $fatal(1, "cxl_fai_variant_sched: HIGH_QUOTA=%0d is not supported (5, 10 or 20)",
             HIGH_QUOTA);
    end
    if ((MAIN_1W != L_MAIN_4STATE) && (MAIN_1W != L_MAIN_1W)) begin : gen_bad_main_1w
      $fatal(1, "cxl_fai_variant_sched: MAIN_1W=%0d is not supported (0 or 1)", MAIN_1W);
    end
  endgenerate

  // --- Candidate (beginning-of-cycle state only) ---
  assign elig_hi       = i_head_valid & ~eff_low;
  assign elig_lo       = i_head_valid & eff_low;
  assign turn_has_elig = (turn_q == L_CLS_LOW) ? |elig_lo : |elig_hi;
  // Continue the visit if its class has work, else open a visit of the other class
  assign cand_cls      = turn_has_elig ? turn_q : !turn_q;
  assign cand_mask     = (cand_cls == L_CLS_LOW) ? elig_lo : elig_hi;
  assign cand_ctx.cls  = cand_cls;
  assign cand_ctx.used = turn_has_elig ? used_q : '0;
  assign o_cand_ctx    = cand_ctx;

  // --- Charge of the grant actually offered (meaningful only when i_fire=1) ---
  assign grant_ctx      = i_grant_ctx;
  assign grant_cls_mask = (grant_ctx.cls == L_CLS_LOW) ? eff_low : ~eff_low;
  assign class_live     = |(live & grant_cls_mask);
  assign used_new       = grant_ctx.used + L_USED_W'(1);
  assign grant_quota    = (grant_ctx.cls == L_CLS_LOW) ? L_QUOTA_LO_V : L_QUOTA_HI_V;
  assign visit_end      = (used_new == grant_quota) || !class_live;

  // --- Window position and closing-window totals ---
  assign closing  = (idx_q == L_IDX_LAST);
  assign s_close  = s_q + L_BS_W'(i_fire);
  assign up_rhs   = L_UP_S_MUL * L_THR_W'(s_close);
  assign down_rhs = L_THR_W'(s_close);
  assign ev_s0    = (s_close == '0);

  // --- Oldest eligible head inside the chosen class (spec 6, 8.3) ---
  cxl_fcfs_sel #(
    .N_SRC (N_SRC),
    .TS_W  (TS_W)
  ) u_fcfs_sel (
    .i_eligible (cand_mask),
    .i_head_ts  (i_head_ts),
    .o_valid    (o_cand_valid),
    .o_source   (o_cand_source)
  );

  // --- Per-source effective class (policy state only; feeds the candidate) ---
  always_comb begin
    for (int unsigned h = 0; h < N_SRC; h++) begin
      eff_low[h] = cls_q[h][L_EFF_LOW_BIT];
    end
  end

  // --- Per-source charge terms: pop, post-edge occupancy, closing counts, evidence ---
  always_comb begin
    for (int unsigned h = 0; h < N_SRC; h++) begin
      pop[h]      = i_fire && (i_grant_source == L_SRC_W'(h));
      live[h]     = (L_OCC_W'(i_fifo_count[h*CNT_W +: CNT_W]) + L_OCC_W'(i_push[h]) -
                     L_OCC_W'(pop[h])) != '0;
      b_close[h]  = b_q[h] + L_BS_W'(pop[h]);
      // Zero-extend to 32 bits before multiplying (spec 8.5)
      up_lhs[h]   = L_UP_B_MUL * L_THR_W'(b_close[h]);
      down_lhs[h] = L_DOWN_B_MUL * L_THR_W'(b_close[h]);
      ev_up[h]    = up_lhs[h] < up_rhs;
      ev_down[h]  = down_lhs[h] > down_rhs;
    end
  end

  // --- Closing-edge classification of every source in parallel (the MAIN_1W hook) ---
  generate
    if (MAIN_1W == L_MAIN_1W) begin : gen_classify_1w
      // Zero service is ordinary KEEP for Main-1W: ev_s0 is deliberately not consumed
      logic unused_1w;

      assign unused_1w = &{1'b0, ev_s0};

      always_comb begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          cls_cl[h] = cls_next_1w(cls_q[h], ev_up[h], ev_down[h]);
        end
      end
    end else begin : gen_classify_main
      always_comb begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          cls_cl[h] = cls_next(cls_q[h], ev_up[h], ev_down[h], ev_s0);
        end
      end
    end
  endgenerate

  // --- Next state: window index, B/S and classes advance on every non-reset edge ---
  always_comb begin
    if (closing) begin
      idx_d = '0;
      b_d   = '0;
      s_d   = '0;
      cls_d = cls_cl;
    end else begin
      idx_d = idx_q + L_IDX_W'(1);
      b_d   = b_close;
      s_d   = s_close;
      cls_d = cls_q;
    end
  end

  // --- Next state: only a fire changes the visit ---
  always_comb begin
    turn_d = turn_q;
    used_d = used_q;
    if (i_fire) begin
      if (visit_end) begin
        turn_d = !grant_ctx.cls;
        used_d = '0;
      end else begin
        turn_d = grant_ctx.cls;
        used_d = used_new;
      end
    end
  end

  // --- Policy state: synchronous active-low reset (spec 5, Q1) ---
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      for (int unsigned h = 0; h < N_SRC; h++) begin
        cls_q[h] <= CLS_H;
      end
      idx_q  <= '0;
      b_q    <= '0;
      s_q    <= '0;
      turn_q <= L_CLS_HIGH;
      used_q <= '0;
    end else begin
      cls_q  <= cls_d;
      idx_q  <= idx_d;
      b_q    <= b_d;
      s_q    <= s_d;
      turn_q <= turn_d;
      used_q <= used_d;
    end
  end

endmodule
