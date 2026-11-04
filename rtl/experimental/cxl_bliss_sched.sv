// cxl_bliss_sched.sv — Block: EXPERIMENTAL BLISS-inspired descriptor scheduler (opt-in only)
// Spec: specs/CXL_SPEC.md v1.0 sections 4, 5, 6 (common cycle contract, FCFS ordering);
//       adaptation declared in docs/experiments/revision-20261023/BASELINES.md (ISSUE_LEDGER F4)
// Source: L. Subramanian et al., "The Blacklisting Memory Scheduler", ICCD 2014, section IV-A
//         (p. 4), as checked by the parent task. Only the blacklisting rule is adapted here.
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// Declared adaptation (this is NOT the original DRAM controller):
//   - There are no DRAM rows, so there is no row-hit priority level.
//   - Priority: any valid NON-blacklisted head first; within the chosen group the oldest arrival
//     timestamp, lowest source ID on equal timestamps (the shared cxl_fcfs_sel). When every valid
//     head is blacklisted, FCFS over all valid heads.
//   - Service streak (ICCD14 IV-A): on a successful fire of source g, the consecutive-service
//     counter is incremented when g equals the last serviced source and reset to 0 when the
//     source changes (or when there is no previous source since reset). When the incremented
//     count EXCEEDS THRESHOLD (count > 4, not count >= 4), g is blacklisted and the counter is
//     reset to 0. Consequently, with THRESHOLD = 4 and no interleaving, the 6th consecutive fire
//     of one source blacklists it (counter values 0,1,2,3,4 then 5 > 4).
//   - Only a successful fire (i_fire) counts. Idle cycles, stalls and held cycles do not reset or
//     advance the streak; the hold controller, not this block, decides what fires.
//   - Clearing: every CLEAR_INTERVAL non-reset cycles the whole blacklist is cleared. The edge
//     with clr_q == CLEAR_INTERVAL-1 (the CLEAR_INTERVAL-th, 2*CLEAR_INTERVAL-th, ... non-reset
//     edge after reset) is a clearing edge. A clear wins over a same-edge new blacklisting; the
//     last-source and streak registers are still updated by a same-edge fire.
//   - Selection uses the pre-edge (beginning-of-cycle) blacklist; a change becomes visible in the
//     next cycle. A held grant (cxl_out_hold) is never altered by a blacklist set or clear.
//
// Policy state (the only registers of this block, all counted):
//   bl_q         [N_SRC]       : blacklist bit per source
//   last_valid_q               : 1 once a fire has happened since reset (a previous source exists)
//   last_src_q   [L_SRC_W]     : last successfully serviced source
//   streak_q     [L_STREAK_W]  : consecutive-service counter, stored range 0..THRESHOLD
//                                (minimal width: $clog2(THRESHOLD+2) holds the transient value
//                                THRESHOLD+1 that triggers blacklisting, so it never wraps)
//   clr_q        [L_CLR_W]     : non-reset cycles since the last clear/reset, 0..CLEAR_INTERVAL-1
//   Stable hierarchical names inside switch_experiment_top:
//     switch_experiment_top.gen_policy_bliss.u_bliss_sched.{bl_q, last_valid_q, last_src_q,
//                                                           streak_q, clr_q}
//
// Reset (spec 5): an edge with rst_n=0 clears every register (empty blacklist, no previous source,
// streak 0, clear counter 0). Reset edges are not counted as cycles.
//
// Candidate (combinational; beginning-of-cycle i_head_valid, i_head_ts and bl_q ONLY):
//   elig_ok      = i_head_valid & ~bl_q
//   cand_mask    = |elig_ok ? elig_ok : i_head_valid
//   o_cand_*     = cxl_fcfs_sel(cand_mask, i_head_ts); o_cand_valid = |i_head_valid
//
// N_SRC must be >= 2, THRESHOLD >= 1, CLEAR_INTERVAL >= 2; checked at elaboration.
module cxl_bliss_sched #(
  parameter int unsigned N_SRC          = 4,
  parameter int unsigned THRESHOLD      = 4,
  parameter int unsigned CLEAR_INTERVAL = 10000,
  parameter int unsigned TS_W           = cxl_sched_pkg::L_TS_W
) (
  input  logic                     clk,
  input  logic                     rst_n,
  // Beginning-of-cycle FIFO heads (source h occupies the h-th slice)
  input  logic [N_SRC-1:0]         i_head_valid,
  input  logic [N_SRC*TS_W-1:0]    i_head_ts,
  // Edge event of this cycle and the grant actually offered (possibly held)
  input  logic                     i_fire,
  input  logic [$clog2(N_SRC)-1:0] i_grant_source,
  // Candidate for this cycle
  output logic                     o_cand_valid,
  output logic [$clog2(N_SRC)-1:0] o_cand_source
);

  // --- Local parameters ---
  localparam int unsigned L_SRC_W    = $clog2(N_SRC);
  localparam int unsigned L_STREAK_W = $clog2(THRESHOLD + 2);   // 0..THRESHOLD+1
  localparam int unsigned L_CLR_W    = $clog2(CLEAR_INTERVAL);  // 0..CLEAR_INTERVAL-1

  localparam logic [L_STREAK_W-1:0] L_THRESHOLD_V = L_STREAK_W'(THRESHOLD);
  localparam logic [L_CLR_W-1:0]    L_CLR_LAST    = L_CLR_W'(CLEAR_INTERVAL - 1);

  // --- Signal declarations ---
  // Policy state
  logic [N_SRC-1:0]      bl_q;
  logic [N_SRC-1:0]      bl_d;
  logic                  last_valid_q;
  logic                  last_valid_d;
  logic [L_SRC_W-1:0]    last_src_q;
  logic [L_SRC_W-1:0]    last_src_d;
  logic [L_STREAK_W-1:0] streak_q;
  logic [L_STREAK_W-1:0] streak_d;
  logic [L_CLR_W-1:0]    clr_q;
  logic [L_CLR_W-1:0]    clr_d;

  // Candidate
  logic [N_SRC-1:0]      elig_ok;      // valid and not blacklisted
  logic [N_SRC-1:0]      cand_mask;

  // Charge of the fired grant
  logic                  repeat_src;   // fire of the same source as the last fire
  logic [L_STREAK_W-1:0] streak_new;
  logic                  fire_bl;      // this fire blacklists i_grant_source
  logic [N_SRC-1:0]      grant_onehot;
  logic                  clearing;

  // --- Elaboration-time parameter check ---
  generate
    if ((N_SRC < 2) || (THRESHOLD < 1) || (CLEAR_INTERVAL < 2)) begin : gen_bad_param
      $fatal(1, "cxl_bliss_sched: N_SRC=%0d >= 2, THRESHOLD=%0d >= 1, CLEAR_INTERVAL=%0d >= 2",
             N_SRC, THRESHOLD, CLEAR_INTERVAL);
    end
  endgenerate

  // --- Candidate (beginning-of-cycle state only) ---
  assign elig_ok   = i_head_valid & ~bl_q;
  assign cand_mask = (|elig_ok) ? elig_ok : i_head_valid;

  cxl_fcfs_sel #(
    .N_SRC (N_SRC),
    .TS_W  (TS_W)
  ) u_fcfs_sel (
    .i_eligible (cand_mask),
    .i_head_ts  (i_head_ts),
    .o_valid    (o_cand_valid),
    .o_source   (o_cand_source)
  );

  // --- Service streak of the grant actually offered (meaningful only when i_fire=1) ---
  assign repeat_src = last_valid_q && (i_grant_source == last_src_q);
  assign streak_new = repeat_src ? (streak_q + L_STREAK_W'(1)) : '0;
  assign fire_bl    = i_fire && (streak_new > L_THRESHOLD_V);
  assign clearing   = (clr_q == L_CLR_LAST);

  generate
    for (genvar h = 0; h < N_SRC; h++) begin : gen_src
      assign grant_onehot[h] = (i_grant_source == L_SRC_W'(h));
    end
  endgenerate

  // --- Next state: streak / last source change only on a fire ---
  always_comb begin
    last_valid_d = last_valid_q;
    last_src_d   = last_src_q;
    streak_d     = streak_q;
    if (i_fire) begin
      last_valid_d = 1'b1;
      last_src_d   = i_grant_source;
      streak_d     = fire_bl ? '0 : streak_new;
    end
  end

  // --- Next state: blacklist and clear counter (every non-reset edge; clear wins) ---
  always_comb begin
    if (clearing) begin
      bl_d  = '0;
      clr_d = '0;
    end else begin
      bl_d  = fire_bl ? (bl_q | grant_onehot) : bl_q;
      clr_d = clr_q + L_CLR_W'(1);
    end
  end

  // --- Policy state: synchronous active-low reset (spec 5) ---
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      bl_q         <= '0;
      last_valid_q <= 1'b0;
      last_src_q   <= '0;
      streak_q     <= '0;
      clr_q        <= '0;
    end else begin
      bl_q         <= bl_d;
      last_valid_q <= last_valid_d;
      last_src_q   <= last_src_d;
      streak_q     <= streak_d;
      clr_q        <= clr_d;
    end
  end

endmodule
