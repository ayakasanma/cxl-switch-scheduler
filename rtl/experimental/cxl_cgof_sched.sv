// cxl_cgof_sched.sv — Block: EXPERIMENTAL CGOF (Credit-Gated Oldest-First) scheduler (opt-in only)
// Spec: specs/CXL_SPEC.md v1.0 sections 4, 5, 6, 8.1, 8.2, 8.4, 8.5 (classification only);
//       independent model refc/cxl_model/experimental.py ExperimentalSwitchModel
//       (policy "CGOF", high_weight 1 / 2, ordering "oldest-first" / "eligible-round-robin")
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// This block is NOT an accepted policy. CGOF keeps the FAI-inspired four-state B/S classification
// of the primary class scheduler and gates source selection with per-source credits. The
// High:Low allocation is HIGH_WEIGHT:1, i.e. CGOF(2:1) (HIGH_WEIGHT=2) or CGOF(1:1) (HIGH_WEIGHT=1).
//
//   active[h]   = i_head_valid[h] (beginning-of-cycle local FIFO head; no producer backlog,
//                 no future arrival is ever observed)
//   eligible[h] = active[h] && credit_q[h] != 0
//   refill      = no eligible source. The candidate then uses the refill credit vector of THIS
//                 cycle, rf[h] = (effective class of h is High) ? HIGH_WEIGHT : 1, for every
//                 source (active or not), and every active source is eligible: same-selection
//                 refill, no bubble.
//   candidate   = one eligible head, o_cand_valid = |active, chosen by the ordering control:
//     ELIGIBLE_RR = 0 (default, oldest-first): oldest eligible head (accepted cxl_fcfs_sel:
//                 modular 32-bit timestamp order, ascending source ID on ties).
//     ELIGIBLE_RR = 1 (credit-gated eligible round-robin): first eligible source in the circular
//                 order rr_ptr_q, rr_ptr_q+1, ... (mod N_SRC). rr_ptr_q resets to 0 and changes
//                 only on a fire, to (i_grant_source + 1) mod N_SRC, i.e. the source after the
//                 last fired grant. Timestamps are still stored by the common FIFOs (unchanged
//                 boundary) but not used for selection. This is not standard WRR: credits,
//                 refill, weights and accounting are identical to the oldest-first ordering.
//
// Credit charge (only on an edge with i_fire=1, using the grant ACTUALLY offered by
// cxl_out_hold, i.e. i_grant_source / i_grant_ctx, which is the latched grant while held):
//   base[h]       = grant_refill ? rf_grant[h] : credit_q[h]
//   credit_d[h]   = base[h] - (h == i_grant_source)
// so a refill overwrites unused credits of every source, inactive sources never block a refill,
// and a source that re-enters within a round keeps the credit it had (no extra credit). Stalls,
// idle cycles, held cycles, window closing and reset never charge credit. The class weights of a
// round are frozen in credit_q at the refill fire; class changes inside a round take effect at
// the next refill only.
//
// Held context (opaque to cxl_out_hold, latched with the source on a stall):
//   ctx[0]       = refill      : the offer was a refill offer
//   ctx[N_SRC:1] = class_high  : effective-class snapshot (1 = High), HIGH_WEIGHT > 1 only
// With HIGH_WEIGHT = 1 the refill vector is all-ones and ctx is the single refill bit.
// This reproduces the model's Choice.credits snapshot exactly: a non-refill offer's snapshot is
// credit_q itself (credit_q cannot change while the grant is held, because only a fire changes
// it and only the held grant can fire); a refill offer's snapshot is rf of the latch cycle, kept
// in ctx through any number of stall cycles, pushes, and closing-edge class changes. Without the
// refill bit a held grant could not distinguish a refill from a later push of a credited source;
// without the class snapshot a closing edge during the hold would change the committed weights.
// The round-robin pointer needs no context: it only changes on a fire, so it is constant while a
// grant is held.
//
// Classification (identical logic to the accepted FAI-inspired classifier, cxl_fai_main_sched
// INTERP=0): every non-reset edge advances the window index; every fire (closing fire included)
// adds 1 to B[grant source] and S; on the closing edge (idx_q == W-1) every source is classified in
// parallel with UP iff 10*N*B < 3*S, DOWN iff N*B > S, S0 iff S == 0, using zero-extended 32-bit
// unsigned intermediates (spec 8.5), through the spec 8.2 four-state table; B, S and the index
// clear. New classes are visible next cycle.
//
// Policy state (all real flip-flops; nothing replaces FIFO storage or arrival metadata):
//   cls_q    [N_SRC][2]        : class per source, H=0, L=1, B_H=2, B_L=3 (bit0 = effective Low)
//   idx_q    [L_IDX_W]         : window index 0..W-1
//   b_q      [N_SRC][L_BS_W]   : window-local successful fires per source
//   s_q      [L_BS_W]          : window-local successful fires of all sources, s_q = sum(b_q)
//   credit_q [N_SRC][L_CRED_W] : remaining credits of the current round, 0..HIGH_WEIGHT
//   rr_ptr_q [L_SRC_W]         : ELIGIBLE_RR = 1 only, in generate scope gen_order_rr
//   Stable hierarchical names inside cgof_unit_top:
//     u_cgof_sched.{cls_q,idx_q,b_q,s_q,credit_q}, u_cgof_sched.gen_order_rr.rr_ptr_q
// With HIGH_WEIGHT = 1 the classification state has no consumer (every refill is 1); it is kept
// so CGOF(1:1) is the same structure with the weight as the only difference and so the
// verification compares it with the model. A synthesis tool may remove it for CGOF(1:1); PPA must
// report what the tool actually retained.
//
// N_SRC must be a power of two >= 2, W one of 64, 256, 5,000,000, HIGH_WEIGHT 1 or 2 and
// ELIGIBLE_RR 0 or 1; all are checked at elaboration (cgof_unit_top relies on these checks for W,
// HIGH_WEIGHT and ELIGIBLE_RR).
module cxl_cgof_sched #(
  parameter  int unsigned N_SRC       = 4,
  parameter  int unsigned W           = 5000000,
  parameter  int unsigned HIGH_WEIGHT = 2,
  parameter  int unsigned ELIGIBLE_RR = 0,
  parameter  int unsigned TS_W        = cxl_sched_pkg::L_TS_W,
  // Grant context: {class snapshot, refill} when weighted, else {refill}
  localparam int unsigned L_CTX_W     = (HIGH_WEIGHT > 1) ? (N_SRC + 1) : 1
) (
  input  logic                     clk,
  input  logic                     rst_n,
  // Beginning-of-cycle FIFO state (source h occupies the h-th slice)
  input  logic [N_SRC-1:0]         i_head_valid,
  input  logic [N_SRC*TS_W-1:0]    i_head_ts,
  // Edge event of this cycle and the grant actually offered (possibly held)
  input  logic                     i_fire,
  input  logic [$clog2(N_SRC)-1:0] i_grant_source,
  input  logic [L_CTX_W-1:0]       i_grant_ctx,
  // Candidate for this cycle
  output logic                     o_cand_valid,
  output logic [$clog2(N_SRC)-1:0] o_cand_source,
  output logic [L_CTX_W-1:0]       o_cand_ctx
);

  // --- Local parameters ---
  localparam int unsigned L_SRC_W  = $clog2(N_SRC);
  localparam int unsigned L_IDX_W  = $clog2(W);            // window index 0..W-1
  localparam int unsigned L_BS_W   = $clog2(W + 1);        // B/S counts 0..W
  // Credits 0..HIGH_WEIGHT (an unsupported HIGH_WEIGHT=0 still gets a 1-bit field so that the
  // only elaboration diagnostic is the intentional $fatal below)
  localparam int unsigned L_CRED_MAX = (HIGH_WEIGHT < 1) ? 1 : HIGH_WEIGHT;
  localparam int unsigned L_CRED_W   = $clog2(L_CRED_MAX + 1);
  // Threshold intermediates: common 32-bit unsigned representation (spec 8.5)
  localparam int unsigned L_THR_W  = 32;

  // Supported windows (spec 8.1, 8.5): production and the two stress-verification variants
  localparam int unsigned L_W_PRODUCTION = 5000000;
  localparam int unsigned L_W_STRESS_64  = 64;
  localparam int unsigned L_W_STRESS_256 = 256;

  // High:Low allocation: Low is always 1; High is 2 (CGOF(2:1)) or 1 (CGOF(1:1))
  localparam int unsigned L_LOW_WEIGHT     = 1;
  localparam int unsigned L_WEIGHT_EQUAL   = 1;
  localparam int unsigned L_WEIGHT_DOUBLE  = 2;
  localparam bit          L_WEIGHTED       = (HIGH_WEIGHT > L_LOW_WEIGHT);

  // Eligible-source ordering control
  localparam int unsigned L_ORDER_OLDEST   = 0;
  localparam int unsigned L_ORDER_RR       = 1;

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
  localparam logic [L_CRED_W-1:0] L_HIGH_CRED  = L_CRED_W'(HIGH_WEIGHT);
  localparam logic [L_CRED_W-1:0] L_LOW_CRED   = L_CRED_W'(L_LOW_WEIGHT);

  // Bit of the four-state encoding that holds the effective class (1 = Low)
  localparam int unsigned L_EFF_LOW_BIT = 0;
  // Context bit holding the refill flag
  localparam int unsigned L_CTX_REFILL  = 0;

  // --- Types ---
  // FAI-inspired four-state class: bit0 = effective Low, bit1 = pending (buffer) change
  typedef enum logic [1:0] {
    CLS_H   = 2'b00,  // stable High
    CLS_L   = 2'b01,  // stable Low
    CLS_B_H = 2'b10,  // buffer, effective High, decrease pending
    CLS_B_L = 2'b11   // buffer, effective Low, increase pending
  } fai_cls_e;

  // --- Functions ---
  // Closing-edge transition (spec 8.2 table), identical to cxl_fai_main_sched cls_next().
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
  logic [N_SRC-1:0][L_CRED_W-1:0]   credit_q;
  logic [N_SRC-1:0][L_CRED_W-1:0]   credit_d;

  // Candidate
  logic [N_SRC-1:0]                 has_credit;   // credit_q[h] != 0
  logic [N_SRC-1:0]                 elig_credit;  // active with credit
  logic                             refill;       // no active source has credit
  logic [N_SRC-1:0]                 cand_mask;

  // Charge of the fired grant
  logic                             grant_refill;
  logic [N_SRC-1:0][L_CRED_W-1:0]   refill_credit;  // refill vector of the fired grant's snapshot
  logic [N_SRC-1:0][L_CRED_W-1:0]   base_credit;    // credit snapshot of the fired grant
  logic [N_SRC-1:0]                 pop;

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
      $fatal(1, "cxl_cgof_sched: N_SRC=%0d must be a power of two >= 2", N_SRC);
    end
    if ((W != L_W_PRODUCTION) && (W != L_W_STRESS_64) && (W != L_W_STRESS_256))
    begin : gen_bad_w
      $fatal(1, "cxl_cgof_sched: W=%0d is not supported (5000000, or stress 64 / 256)", W);
    end
    if (L_UP_MAX_PRODUCT > L_THR_MAX) begin : gen_bad_thr_range
      $fatal(1, "cxl_cgof_sched: 10*N_SRC*W (N_SRC=%0d, W=%0d) exceeds %0d-bit thresholds",
             N_SRC, W, L_THR_W);
    end
    if ((HIGH_WEIGHT != L_WEIGHT_EQUAL) && (HIGH_WEIGHT != L_WEIGHT_DOUBLE))
    begin : gen_bad_high_weight
      $fatal(1, "cxl_cgof_sched: HIGH_WEIGHT=%0d is not supported (2 for 2:1, or 1 for 1:1)",
             HIGH_WEIGHT);
    end
    if ((ELIGIBLE_RR != L_ORDER_OLDEST) && (ELIGIBLE_RR != L_ORDER_RR))
    begin : gen_bad_eligible_rr
      $fatal(1, "cxl_cgof_sched: ELIGIBLE_RR=%0d is not supported (0 oldest-first, 1 eligible RR)",
             ELIGIBLE_RR);
    end
  endgenerate

  // --- Candidate (beginning-of-cycle state only) ---
  assign elig_credit = i_head_valid & has_credit;
  assign refill      = !(|elig_credit);
  // Refill: every active source is eligible in the same selection (no bubble)
  assign cand_mask   = refill ? i_head_valid : elig_credit;

  // --- Eligible-source ordering ---
  generate
    if (ELIGIBLE_RR == L_ORDER_RR) begin : gen_order_rr
      // Credit-gated eligible round-robin: first eligible source from rr_ptr_q (circular)
      logic [L_SRC_W-1:0] rr_ptr_q;
      logic [L_SRC_W-1:0] rr_ptr_d;
      logic [L_SRC_W-1:0] rr_pick;
      logic               rr_found;
      logic               unused_ts;  // arrival metadata is stored but not used by this ordering

      assign o_cand_valid  = |cand_mask;
      assign o_cand_source = rr_pick;
      assign unused_ts     = &{1'b0, i_head_ts};
      // Advance only on a fire, to the source after the fired (possibly held) grant; N_SRC is a
      // power of two, so the L_SRC_W-bit sum wraps mod N_SRC
      assign rr_ptr_d      = i_fire ? (i_grant_source + L_SRC_W'(1)) : rr_ptr_q;

      always_comb begin
        rr_pick  = rr_ptr_q;
        rr_found = 1'b0;
        for (int unsigned k = 0; k < N_SRC; k++) begin
          if (!rr_found && cand_mask[rr_ptr_q + L_SRC_W'(k)]) begin
            rr_pick  = rr_ptr_q + L_SRC_W'(k);
            rr_found = 1'b1;
          end
        end
      end

      // Synchronous active-low reset: polling starts at source 0
      always_ff @(posedge clk) begin
        if (!rst_n) begin
          rr_ptr_q <= '0;
        end else begin
          rr_ptr_q <= rr_ptr_d;
        end
      end
    end else begin : gen_order_oldest
      // Oldest eligible head (spec 6)
      cxl_fcfs_sel #(
        .N_SRC (N_SRC),
        .TS_W  (TS_W)
      ) u_fcfs_sel (
        .i_eligible (cand_mask),
        .i_head_ts  (i_head_ts),
        .o_valid    (o_cand_valid),
        .o_source   (o_cand_source)
      );
    end
  endgenerate

  // --- Grant context and the refill vector of the fired grant's snapshot ---
  assign grant_refill = i_grant_ctx[L_CTX_REFILL];

  generate
    if (L_WEIGHTED) begin : gen_ctx_weighted
      // CGOF(2:1): the refill vector depends on the class map, so the snapshot travels with the
      // offer
      logic [N_SRC-1:0] class_high;  // current effective class, 1 = High
      logic [N_SRC-1:0] grant_high;  // class snapshot of the offered (possibly held) grant

      assign o_cand_ctx = {class_high, refill};
      assign grant_high = i_grant_ctx[L_CTX_W-1:1];

      // Candidate-side and grant-side terms in separate blocks: the grant context is derived from
      // the candidate through cxl_out_hold, so one shared block would form a false comb. loop.
      always_comb begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          class_high[h] = !cls_q[h][L_EFF_LOW_BIT];
        end
      end

      always_comb begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          refill_credit[h] = grant_high[h] ? L_HIGH_CRED : L_LOW_CRED;
        end
      end
    end else begin : gen_ctx_equal
      // CGOF(1:1): every refill credit is 1, the refill flag is the complete snapshot
      assign o_cand_ctx = refill;

      always_comb begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          refill_credit[h] = L_LOW_CRED;
        end
      end
    end
  endgenerate

  // --- Window position and closing-window totals ---
  assign closing  = (idx_q == L_IDX_LAST);
  assign s_close  = s_q + L_BS_W'(i_fire);
  assign up_rhs   = L_UP_S_MUL * L_THR_W'(s_close);
  assign down_rhs = L_THR_W'(s_close);
  assign ev_s0    = (s_close == '0);

  // --- Per-source candidate term: credit presence (state only, kept apart from grant terms) ---
  always_comb begin
    for (int unsigned h = 0; h < N_SRC; h++) begin
      has_credit[h] = (credit_q[h] != '0);
    end
  end

  // --- Per-source grant terms: pop, credit snapshot, closing counts, evidence ---
  always_comb begin
    for (int unsigned h = 0; h < N_SRC; h++) begin
      pop[h]         = i_fire && (i_grant_source == L_SRC_W'(h));
      base_credit[h] = grant_refill ? refill_credit[h] : credit_q[h];
      b_close[h]     = b_q[h] + L_BS_W'(pop[h]);
      // Zero-extend to 32 bits before multiplying (spec 8.5)
      up_lhs[h]      = L_UP_B_MUL * L_THR_W'(b_close[h]);
      down_lhs[h]    = L_DOWN_B_MUL * L_THR_W'(b_close[h]);
      ev_up[h]       = up_lhs[h] < up_rhs;
      ev_down[h]     = down_lhs[h] > down_rhs;
      cls_cl[h]      = cls_next(cls_q[h], ev_up[h], ev_down[h], ev_s0);
    end
  end

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

  // --- Next state: only a fire commits the snapshot and charges one credit ---
  // base_credit[grant source] >= 1 by construction (the offer was eligible or a refill).
  always_comb begin
    credit_d = credit_q;
    if (i_fire) begin
      for (int unsigned h = 0; h < N_SRC; h++) begin
        credit_d[h] = base_credit[h] - L_CRED_W'(pop[h]);
      end
    end
  end

  // --- Policy state: synchronous active-low reset (spec 5, Q1): credits 0, classes H ---
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      for (int unsigned h = 0; h < N_SRC; h++) begin
        cls_q[h] <= CLS_H;
      end
      idx_q    <= '0;
      b_q      <= '0;
      s_q      <= '0;
      credit_q <= '0;
    end else begin
      cls_q    <= cls_d;
      idx_q    <= idx_d;
      b_q      <= b_d;
      s_q      <= s_d;
      credit_q <= credit_d;
    end
  end

endmodule
