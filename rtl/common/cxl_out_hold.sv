// cxl_out_hold.sv — Block: common output hold/stall controller (shared by every policy)
// Spec: specs/CXL_SPEC.md v1.0 sections 4, 5, 8.3; docs/phase-3-uarch/common_framework.md item 4
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// Cycle contract (cycle c is the interval before its closing rising edge):
//   - Not held: the offered grant is the policy candidate of this cycle (i_cand_*). The descriptor
//     is taken combinationally from the selected FIFO head: there is no output register stage.
//   - Held: the offered grant is the latched source/context. i_cand_* is ignored completely, so
//     later pushes or classification changes cannot alter or preempt the pending transfer.
//   - o_out_valid = rst_n && (held || i_cand_valid) && head_valid[offered source].
//   - o_fire = o_out_valid && i_out_ready. Only o_fire produces a pop, and only for the offered
//     source (o_pop is one-hot or zero). Selection without acceptance never pops.
//   - Edge with o_out_valid && !i_out_ready while not held (stall): the offered source/context are
//     latched and the grant becomes held from the next cycle on.
//   - Held validity is released EXPLICITLY and only by an edge with o_fire=1 or with rst_n=0. It
//     is never released because the selected head appears invalid, because the candidate changed
//     or disappeared, or because of any policy state update.
//   - rst_n=0 forces o_out_valid, o_fire and o_pop inactive combinationally.
//
// Selected-head invariant (relied upon, not enforced by extra storage): a FIFO pops only on its
// o_pop bit, o_pop is one-hot-or-zero for the offered source and only on o_fire, and a grant can
// become held only when its head was valid. Therefore the head of a held source cannot pop
// before the common fire: it stays valid and its descriptor stays stable for the whole hold, so
// no descriptor copy is needed and o_out_valid stays 1 while held. This requires that i_head_*
// come from FIFOs popped exclusively by this block's o_pop and reset together with it. If an
// integration broke the invariant (held source with an invalid head), o_out_valid would be 0 and
// the grant would remain held until reset rather than being silently dropped or re-selected.
//
// Policy interface rules:
//   - i_cand_* must be derived from beginning-of-cycle state only (never from i_out_ready,
//     o_fire or o_pop of the same cycle).
//   - Only o_fire consumes quota, increments service counts (B/S) and dequeues. Such fire-driven
//     accounting must use o_out_source / o_grant_ctx (the grant actually offered), not the
//     policy's own candidate, which is ignored while held and may differ from the held grant.
//   - This does not forbid the approved state updates that are not caused by fire: synchronous
//     reset (spec 5), the FAI window index advancing on every non-reset cycle and the
//     closing-edge classification with B/S clear (spec 8.1, 8.4), empty-turn / empty-class visit
//     advance and quota renewal without service consumption (spec 7 Q2, 8.3 Q2), and the
//     free-running arrival counter (spec 6). None of them may alter a held grant: the held
//     source/context are replayed from this block's own registers (spec 4 stall clarification).
//
// CTX_W is the generic, opaque grant context (e.g. the FAI class/quota context of the pending
// transfer). It is latched and replayed with the source; this block never interprets it.
// N_SRC must be >= 2. For a non-power-of-two N_SRC an out-of-range candidate source matches no
// head and is therefore never offered valid.
module cxl_out_hold #(
  parameter int unsigned N_SRC  = 4,
  parameter int unsigned DESC_W = cxl_sched_pkg::L_DESC_W,
  parameter int unsigned CTX_W  = 1
) (
  input  logic                     clk,
  input  logic                     rst_n,
  // Policy candidate for this cycle (combinational, beginning-of-cycle state only)
  input  logic                     i_cand_valid,
  input  logic [$clog2(N_SRC)-1:0] i_cand_source,
  input  logic [CTX_W-1:0]         i_cand_ctx,
  // FIFO heads (source h occupies the h-th slice)
  input  logic [N_SRC-1:0]         i_head_valid,
  input  logic [N_SRC*DESC_W-1:0]  i_head_desc,
  // Memory output handshake
  output logic                     o_out_valid,
  input  logic                     i_out_ready,
  output logic [DESC_W-1:0]        o_out_desc,
  output logic [$clog2(N_SRC)-1:0] o_out_source,
  // Grant actually offered this cycle (source is o_out_source), for policy accounting
  output logic [CTX_W-1:0]         o_grant_ctx,
  output logic                     o_grant_held,
  output logic                     o_fire,
  // Per-source pop to the FIFOs
  output logic [N_SRC-1:0]         o_pop
);

  // --- Local parameters ---
  localparam int unsigned L_SRC_W = $clog2(N_SRC);

  // --- Signal declarations ---
  logic               held_q;
  logic               held_d;
  logic [L_SRC_W-1:0] held_source_q;
  logic [CTX_W-1:0]   held_ctx_q;

  logic               sel_valid;
  logic [L_SRC_W-1:0] sel_source;
  logic [CTX_W-1:0]   sel_ctx;
  logic [N_SRC-1:0]   sel_onehot;
  logic               sel_head_valid;
  logic               stall;

  logic [DESC_W-1:0]  head_desc [0:N_SRC-1];

  // --- Offered grant: latched grant while held, policy candidate otherwise ---
  assign sel_valid      = held_q || i_cand_valid;
  assign sel_source     = held_q ? held_source_q : i_cand_source;
  assign sel_ctx        = held_q ? held_ctx_q : i_cand_ctx;
  assign sel_head_valid = |(i_head_valid & sel_onehot);

  // --- Output handshake (inactive during reset) ---
  assign o_out_valid  = rst_n && sel_valid && sel_head_valid;
  assign o_fire       = o_out_valid && i_out_ready;
  assign stall        = o_out_valid && !i_out_ready;

  // --- Output data: straight from the selected FIFO head, no register stage ---
  assign o_out_desc   = head_desc[sel_source];
  assign o_out_source = sel_source;
  assign o_grant_ctx  = sel_ctx;
  assign o_grant_held = held_q;

  // --- Held validity: explicit set/release ---
  //   not held : set by a stalled offer (o_out_valid && !i_out_ready)
  //   held     : cleared only by o_fire (reset clears it in the register below); never released
  //              by the selected head appearing invalid
  assign held_d = held_q ? !o_fire : stall;

  // --- Per-source decode, head unpacking and pop ---
  generate
    for (genvar h = 0; h < N_SRC; h++) begin : gen_src
      assign sel_onehot[h] = (sel_source == L_SRC_W'(h));
      assign head_desc[h]  = i_head_desc[h*DESC_W +: DESC_W];
      assign o_pop[h]      = o_fire && sel_onehot[h];
    end
  endgenerate

  // --- Held grant state: synchronous active-low reset ---
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      held_q        <= 1'b0;
      held_source_q <= '0;
      held_ctx_q    <= '0;
    end else begin
      held_q <= held_d;
      if (stall && !held_q) begin
        held_source_q <= i_cand_source;
        held_ctx_q    <= i_cand_ctx;
      end
    end
  end

endmodule
