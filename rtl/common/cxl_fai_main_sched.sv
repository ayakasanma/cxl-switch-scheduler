// cxl_fai_main_sched.sv — Block: FAI-inspired Main policy (policy slot part B of switch_top,
//                         POLICY_FAI_MAIN) and, with INTERP=1, the supplementary Algorithm-2
//                         interpretation (POLICY_FAI_ALG2)
// Spec: specs/CXL_SPEC.md v1.0 sections 4, 5, 6, 8.1-8.5 (Q1-Q3), 8.6; specs/DECISIONS.md D08,
//       D12, D25-D27, D33, D35; docs/phase-3-uarch/fai_main.md and fai_alg2.md (binding
//       implementation derivations)
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// Policy state (the only registers of this block, all packed so they are VPI-readable as vectors):
//   cls_q  [N_SRC][2]      : per-source Main four-state class, fai_cls_e, source h = cls_q[h]
//                            (bits [2h+1:2h] of the flat vector). Encoding: bit0 = effective Low,
//                            bit1 = pending (buffer) change:
//                              CLS_H = 2'b00, CLS_L = 2'b01, CLS_B_H = 2'b10, CLS_B_L = 2'b11
//                            Effective High iff H or B_H (bit0 = 0); effective Low iff L or B_L.
//   idx_q  [L_IDX_W]       : window index 0..W-1, L_IDX_W = $clog2(W) (23 bits at W=5,000,000,
//                            6 at W=64, 8 at W=256).
//   b_q    [N_SRC][L_BS_W] : window-local successful fires of source h, b_q[h]
//                            (bits [h*L_BS_W +: L_BS_W]); L_BS_W = $clog2(W+1) (23 / 7 / 9 bits).
//   s_q    [L_BS_W]        : window-local successful fires of all sources, s_q = sum(b_q) always.
//   turn_q                 : class of the current visit, 0 = High, 1 = Low.
//   used_q [L_USED_W]      : fires already charged to the current visit, 0..L_QUOTA-1 (4 bits).
//   Stable hierarchical names for simulation-only observation inside switch_top:
//     switch_top.gen_policy_fai_main.u_fai_sched.cls_q
//     switch_top.gen_policy_fai_main.u_fai_sched.idx_q
//     switch_top.gen_policy_fai_main.u_fai_sched.b_q
//     switch_top.gen_policy_fai_main.u_fai_sched.s_q
//     switch_top.gen_policy_fai_main.u_fai_sched.turn_q
//     switch_top.gen_policy_fai_main.u_fai_sched.used_q
//   The in-class oldest-head selector is switch_top.gen_policy_fai_main.u_fai_sched.u_fcfs_sel.
//   There is no debug, preload or bypass port.
//
// Grant context (L_CTX_W = 5 bits, opaque to cxl_out_hold): {cls, used} = fai_ctx_t
//   ctx[4]   cls  : class of the visit the transfer is charged to, 0 = High, 1 = Low
//   ctx[3:0] used : fires already charged to that visit before this transfer, 0..9
//
// Reset (spec 5, Q1; fai_main.md 4): an edge with rst_n=0 sets every cls_q[h] = CLS_H, idx_q = 0,
// b_q = 0, s_q = 0, turn_q = High, used_q = 0. Reset edges are not window cycles. (With INTERP=1
// the same 2'b00 encoding is A2_STABLE_HIGH, no pending Buffer.)
//
// Candidate (combinational; beginning-of-cycle i_head_valid, i_head_ts and policy state ONLY,
// never i_fire / pop of the same cycle; spec 5, 8.3, fai_main.md 3):
//   elig_hi = i_head_valid & effective-High, elig_lo = i_head_valid & effective-Low
//   1. turn_q class has an eligible head : class turn_q, o_cand_ctx = {turn_q, used_q}
//   2. else the other class has one      : class !turn_q, o_cand_ctx = {!turn_q, 0} (new visit,
//                                          renewed quota, the empty visit's quota is relinquished)
//   3. else                              : o_cand_valid = 0 (both empty retains the turn)
//   o_cand_source = cxl_fcfs_sel over i_head_valid restricted to the chosen class (modular-oldest
//   timestamp, ascending source ID on ties). elig_hi | elig_lo = i_head_valid, so o_cand_valid =
//   |i_head_valid: no control-only bubble while any head is valid.
//
// Visit/quota update (spec 8.3 Q2, fai_main.md 4), ONLY on an edge with i_fire=1, charged to the
// grant actually offered (g = i_grant_source, {Cg, Ug} = i_grant_ctx; a held grant may differ from
// this cycle's candidate):
//   n          = Ug + 1
//   pop[h]     = i_fire && g == h
//   class_live = some h with current (pre-edge) effective class == Cg has post-edge occupancy
//                i_fifo_count[h] + i_push[h] - pop[h] > 0
//   n == 10     : turn_q <= !Cg, used_q <= 0 (expiry, even with replacement / live class)
//   !class_live : turn_q <= !Cg, used_q <= 0 (emptied class relinquishes its quota)
//   otherwise   : turn_q <= Cg,  used_q <= n
//   i_fire=0 (idle, both empty, stall/held): turn_q, used_q unchanged. Window edges never change
//   turn_q / used_q. At a closing edge class_live uses the class map of the closing cycle.
//
// Window accounting (spec 8.1, 8.4, Q3), on EVERY non-reset edge including stalls and idle:
//   b_close[h] = b_q[h] + pop[h], s_close = s_q + i_fire
//   non-closing (idx_q != W-1): idx_q <= idx_q + 1, b_q <= b_close, s_q <= s_close
//   closing     (idx_q == W-1): all N_SRC sources classified IN PARALLEL in this edge from b_close /
//                               s_close and the current cls_q, then b_q <= 0, s_q <= 0, idx_q <= 0.
//                               The new classes are visible from the next cycle.
//   Evidence, unsigned L_THR_W = 32-bit intermediates, operands zero-extended BEFORE multiplying:
//     UP   iff (10*N_SRC) * b_close[h] < 3 * s_close
//     DOWN iff N_SRC * b_close[h] > s_close
//     KEEP otherwise (including equality); S0 iff s_close == 0 (explicit Main cancellation)
//   Main table (spec 8.2), see cls_next():
//     cur  | UP  | DOWN | KEEP / S0
//     H    | H   | B_H  | H
//     B_H  | H   | L    | H
//     L    | B_L | L    | L
//     B_L  | H   | L    | L
//   Bounds: 0 <= b_q[h] <= s_q <= W and 10*N_SRC*W < 2^32 (elaboration check), so the 32-bit
//   products are exact. No division, rounding, truncation, sign extension or multicycle classifier.
//
// Interpretation selector INTERP (compile-time; docs/phase-3-uarch/fai_alg2.md):
//   0 = Main (default, spec 8.2 table above; switch_top POLICY_FAI_MAIN)
//   1 = Algorithm-2 supplement (spec 8.6; switch_top POLICY_FAI_ALG2), see alg2_next(). The SAME
//       candidate, visit/quota, B/S, window index, 32-bit thresholds, context and FCFS selector are
//       used; only the closing-edge transition and the meaning of cls_q differ. Algorithm-2 reuses
//       the 2-bit register with bit0 = effective class = stored target p and bit1 = Buffer, under
//       its own names (alg2_cls_e):
//         A2_STABLE_HIGH = 2'b00, A2_STABLE_LOW = 2'b01, A2_BUFFER_P_HIGH = 2'b10,
//         A2_BUFFER_P_LOW = 2'b11
//       A Buffer is serviced immediately in its target class p. Reset: every source A2_STABLE_HIGH
//       (= the same 2'b00 encoding as CLS_H), visit High. A zero-service window is KEEP (no S0
//       cancellation):
//         cur            | UP             | DOWN            | KEEP / zero-service
//         STABLE_HIGH    | STABLE_HIGH    | BUFFER_P_LOW    | STABLE_HIGH
//         STABLE_LOW     | BUFFER_P_HIGH  | STABLE_LOW      | STABLE_LOW
//         BUFFER_P_HIGH  | STABLE_HIGH    | STABLE_LOW      | BUFFER_P_HIGH
//         BUFFER_P_LOW   | STABLE_HIGH    | STABLE_LOW      | BUFFER_P_LOW
//   Any other value fails elaboration.
//
// N_SRC must be a power of two >= 2 (switch_top allows 4, 8, 16) and W one of 64, 256 (stress) or
// 5,000,000 (production); both are checked at elaboration.
module cxl_fai_main_sched #(
  parameter  int unsigned N_SRC    = 4,
  parameter  int unsigned W        = 5000000,
  parameter  int unsigned INTERP   = 0,
  parameter  int unsigned TS_W     = cxl_sched_pkg::L_TS_W,
  parameter  int unsigned CNT_W    = $bits(cxl_sched_pkg::fifo_count_t),
  // Fixed by spec 8.3 (High/Low quotas 10/10), not overridable: context = {class, used}
  localparam int unsigned L_QUOTA  = 10,
  localparam int unsigned L_USED_W = $clog2(L_QUOTA),
  localparam int unsigned L_CTX_W  = 1 + L_USED_W
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
  localparam logic [L_USED_W-1:0] L_QUOTA_V    = L_USED_W'(L_QUOTA);

  // Visit / effective class encoding of turn_q and the context class bit
  localparam logic L_CLS_HIGH = 1'b0;
  localparam logic L_CLS_LOW  = 1'b1;
  // Bit of the four-state encoding that holds the effective class (1 = Low)
  localparam int unsigned L_EFF_LOW_BIT = 0;

  // Interpretation selector values
  localparam int unsigned L_INTERP_MAIN = 0;
  localparam int unsigned L_INTERP_ALG2 = 1;

  // --- Types ---
  // Main four-state class: bit0 = effective Low, bit1 = pending (buffer) change
  typedef enum logic [1:0] {
    CLS_H   = 2'b00,  // stable High
    CLS_L   = 2'b01,  // stable Low
    CLS_B_H = 2'b10,  // buffer, effective High, decrease pending
    CLS_B_L = 2'b11   // buffer, effective Low, increase pending
  } fai_cls_e;

  // Algorithm-2 state (INTERP = L_INTERP_ALG2): bit0 = effective class = target p, bit1 = Buffer
  typedef enum logic [1:0] {
    A2_STABLE_HIGH   = 2'b00,  // stable High
    A2_STABLE_LOW    = 2'b01,  // stable Low
    A2_BUFFER_P_HIGH = 2'b10,  // Buffer, serviced immediately in target class High
    A2_BUFFER_P_LOW  = 2'b11   // Buffer, serviced immediately in target class Low
  } alg2_cls_e;

  // Grant context carried through cxl_out_hold, {cls, used} (cls is the most significant bit)
  typedef struct packed {
    logic                cls;   // 0 = High, 1 = Low
    logic [L_USED_W-1:0] used;  // fires already charged to the visit, 0..L_QUOTA-1
  } fai_ctx_t;

  // --- Functions ---
  // Main closing-edge transition (spec 8.2 table). Pure: uses only its arguments.
  // s0 (no service in the window) cancels a pending change and keeps the effective class.
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

  // Algorithm-2 closing-edge transition (spec 8.6 table). Pure: uses only its arguments.
  // Neither up nor down (KEEP, including a zero-service window) retains the state and target.
  function automatic alg2_cls_e alg2_next(input alg2_cls_e cur, input logic up,
                                          input logic down);
    case (cur)
      A2_STABLE_HIGH: begin
        if (down)    alg2_next = A2_BUFFER_P_LOW;
        else         alg2_next = A2_STABLE_HIGH;
      end
      A2_STABLE_LOW: begin
        if (up)      alg2_next = A2_BUFFER_P_HIGH;
        else         alg2_next = A2_STABLE_LOW;
      end
      A2_BUFFER_P_HIGH, A2_BUFFER_P_LOW: begin
        if (up)        alg2_next = A2_STABLE_HIGH;
        else if (down) alg2_next = A2_STABLE_LOW;
        else           alg2_next = cur;
      end
      default: alg2_next = A2_STABLE_HIGH;  // unreachable: all four encodings are states
    endcase
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
      $fatal(1, "cxl_fai_main_sched: N_SRC=%0d must be a power of two >= 2", N_SRC);
    end
    if ((W != L_W_PRODUCTION) && (W != L_W_STRESS_64) && (W != L_W_STRESS_256))
    begin : gen_bad_w
      $fatal(1, "cxl_fai_main_sched: W=%0d is not supported (5000000, or stress 64 / 256)", W);
    end
    if (L_UP_MAX_PRODUCT > L_THR_MAX) begin : gen_bad_thr_range
      $fatal(1, "cxl_fai_main_sched: 10*N_SRC*W (N_SRC=%0d, W=%0d) exceeds %0d-bit thresholds",
             N_SRC, W, L_THR_W);
    end
    if ((INTERP != L_INTERP_MAIN) && (INTERP != L_INTERP_ALG2)) begin : gen_bad_interp
      $fatal(1, "cxl_fai_main_sched: INTERP=%0d is not supported (0 Main, 1 Algorithm-2)",
             INTERP);
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
  assign visit_end      = (used_new == L_QUOTA_V) || !class_live;

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
  // Kept apart from the fire-dependent terms below so the candidate path has no dependency, not
  // even a structural one, on i_fire / i_grant_* of the same cycle.
  always_comb begin
    for (int unsigned h = 0; h < N_SRC; h++) begin
      eff_low[h] = cls_q[h][L_EFF_LOW_BIT];
    end
  end

  // --- Per-source charge terms: pop, post-edge occupancy, closing counts, evidence ---
  // All N_SRC sources are evaluated in parallel (constant loop bounds, no iteration dependency).
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

  // --- Closing-edge classification of every source in parallel (the only INTERP difference) ---
  generate
    if (INTERP == L_INTERP_ALG2) begin : gen_interp_alg2
      // Zero service is ordinary KEEP for Algorithm-2: ev_s0 is deliberately not consumed
      logic unused_alg2;

      assign unused_alg2 = &{1'b0, ev_s0};

      always_comb begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          cls_cl[h] = fai_cls_e'(alg2_next(alg2_cls_e'(cls_q[h]), ev_up[h], ev_down[h]));
        end
      end
    end else begin : gen_interp_main
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
