// cxl_fcfs_sel.sv — Block: shared oldest-eligible-head selector (FCFS; reusable by FAI per class)
// Spec: specs/CXL_SPEC.md v1.0 section 6; docs/phase-3-uarch/common_framework.md item 3
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, IEEE 1800-2009)
//
// Purely combinational: no clock, no reset, no registers.
//
// Inputs are a generic per-source eligible mask and the flattened head arrival timestamps
// (source h occupies bit h of i_eligible and bits [h*TS_W +: TS_W] of i_head_ts). switch_top FCFS
// passes the FIFO head-valid mask; a later FAI milestone may pass a class-filtered mask. This
// block contains no policy logic of its own.
//
// Ordering (spec 6): for unequal a, b, a is older than b iff 0 < ((b - a) mod 2^TS_W) < 2^(TS_W-1),
// i.e. the TS_W-bit modular difference b - a is non-zero and its MSB is 0. Only unsigned TS_W-bit
// modular arithmetic is used. Exactly-half-range differences are outside the valid environment
// assumption (spec 6) and are given no special meaning.
//
// Algorithm: balanced binary reduction tree, ceil(log2(N_SRC)) comparator levels. Leaves are the
// sources in ascending ID order, padded with ineligible leaves up to a power of two. Each internal
// node receives a left (lower-ID range) and a right (higher-ID range) child and keeps the LEFT
// child unless the right child is eligible and either the left child is ineligible or the right
// timestamp is STRICTLY older than the left one. A node is eligible iff either child is eligible.
//
// Why this equals "oldest eligible head, ascending-ID ties":
//   - Under the spec 6 assumption every outstanding head is younger than 2^(TS_W-1) cycles, so all
//     eligible timestamps lie in one half-range window behind the free-running counter. Inside such
//     a window the modular "older" relation coincides with the order of the unwrapped arrival
//     times; it is therefore a strict weak order (transitive), and "equal timestamp" is the only
//     incomparable case.
//   - Induction over the tree: each node outputs the lowest-ID source among the oldest eligible
//     sources of its contiguous ID range. A leaf trivially does. At an internal node, if the right
//     minimum is strictly older it is older than every left source, so it is the oldest of the
//     whole range; otherwise the left minimum is at least as old as every right source, and on an
//     equal timestamp the left one has the lower ID. Ineligible children are never chosen when an
//     eligible sibling exists, so an ineligible source never wins.
//   - Hence o_valid = |i_eligible, and whenever o_valid=1, o_source names an eligible source.
//     When o_valid=0, o_source is 0 (don't-care for the consumer).
//
// N_SRC must be >= 2 (o_source is $clog2(N_SRC) bits). TS_W must be >= 2.
module cxl_fcfs_sel #(
  parameter int unsigned N_SRC = 4,
  parameter int unsigned TS_W  = cxl_sched_pkg::L_TS_W
) (
  input  logic [N_SRC-1:0]         i_eligible,
  input  logic [N_SRC*TS_W-1:0]    i_head_ts,
  output logic                     o_valid,
  output logic [$clog2(N_SRC)-1:0] o_source
);

  // --- Local parameters ---
  localparam int unsigned L_SRC_W  = $clog2(N_SRC);
  localparam int unsigned L_LEAVES = 1 << L_SRC_W;       // N_SRC rounded up to a power of two
  localparam int unsigned L_NODES  = 2 * L_LEAVES - 1;   // heap-ordered tree, root at index 0
  localparam int unsigned L_FIRST_LEAF = L_LEAVES - 1;   // heap index of leaf (source) 0

  // --- Functions ---
  // a is strictly older than b: (b - a) mod 2^TS_W is non-zero and below 2^(TS_W-1).
  // Pure: uses only its arguments.
  // Computed without forming the full difference d = (b - a) mod 2^TS_W:
  //   - d != 0  <=>  a != b (subtraction mod 2^TS_W is a bijection), a parallel equality test;
  //   - d[TS_W-1] = b[TS_W-1] ^ a[TS_W-1] ^ borrow, where borrow is the borrow into bit TS_W-1,
  //     i.e. borrow = (b[TS_W-2:0] < a[TS_W-2:0]) as (TS_W-1)-bit unsigned values.
  // Identical to (d != 0) && !d[TS_W-1] for every bit vector a, b, including a == b and
  // exactly-half-range differences. Needs TS_W >= 2 (checked below).
  function automatic logic ts_older(input logic [TS_W-1:0] a, input logic [TS_W-1:0] b);
    logic borrow;  // borrow into bit TS_W-1 of b - a
    logic d_msb;   // bit TS_W-1 of (b - a) mod 2^TS_W
    borrow   = (b[TS_W-2:0] < a[TS_W-2:0]);
    d_msb    = b[TS_W-1] ^ a[TS_W-1] ^ borrow;
    ts_older = (a != b) && !d_msb;
  endfunction

  // --- Signal declarations ---
  // Heap-ordered tree nodes: node i has children 2i+1 (lower IDs) and 2i+2 (higher IDs);
  // leaves occupy indices L_FIRST_LEAF .. L_NODES-1 in ascending source order.
  logic               node_valid [0:L_NODES-1];
  logic [TS_W-1:0]    node_ts    [0:L_NODES-1];
  logic [L_SRC_W-1:0] node_src   [0:L_NODES-1];

  // --- Elaboration-time parameter check ---
  generate
    if ((N_SRC < 2) || (TS_W < 2)) begin : gen_bad_param
      $fatal(1, "cxl_fcfs_sel: N_SRC=%0d and TS_W=%0d must both be >= 2", N_SRC, TS_W);
    end
  endgenerate

  // --- Outputs: root of the tree ---
  assign o_valid  = node_valid[0];
  assign o_source = node_valid[0] ? node_src[0] : '0;

  // --- Reduction tree (constant loop bounds; one comparator level per tree level) ---
  always_comb begin
    // Leaves: real sources, then ineligible padding up to a power of two
    for (int unsigned j = 0; j < L_LEAVES; j++) begin
      if (j < N_SRC) begin
        node_valid[L_FIRST_LEAF + j] = i_eligible[j];
        node_ts[L_FIRST_LEAF + j]    = i_head_ts[j*TS_W +: TS_W];
      end else begin
        node_valid[L_FIRST_LEAF + j] = 1'b0;
        node_ts[L_FIRST_LEAF + j]    = '0;
      end
      node_src[L_FIRST_LEAF + j] = L_SRC_W'(j);
    end
    // Internal nodes, bottom-up (children always have a higher heap index than their parent).
    // Keep the lower-ID (left) child unless the right child is eligible and the left one is not,
    // or the right child is strictly older.
    for (int i = int'(L_FIRST_LEAF) - 1; i >= 0; i--) begin
      if (node_valid[2*i+2] &&
          (!node_valid[2*i+1] || ts_older(node_ts[2*i+2], node_ts[2*i+1]))) begin
        node_valid[i] = 1'b1;
        node_ts[i]    = node_ts[2*i+2];
        node_src[i]   = node_src[2*i+2];
      end else begin
        node_valid[i] = node_valid[2*i+1];
        node_ts[i]    = node_ts[2*i+1];
        node_src[i]   = node_src[2*i+1];
      end
    end
  end

endmodule
