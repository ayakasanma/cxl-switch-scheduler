// cxl_desc_fifo.sv — Block: common per-source descriptor FIFO
// Spec: specs/CXL_SPEC.md v1.0 sections 4, 5, 6; docs/phase-3-uarch/common_framework.md items 2, 3
// Coding style: lowRISC SV Style Guide + project overrides (i_/o_ prefix, clk, synchronous rst_n)
//
// Cycle contract (cycle c is the interval before its closing rising edge):
//   - o_in_ready depends only on beginning-of-cycle occupancy (and reset); it never predicts a
//     same-edge pop, so a full FIFO refuses a push even when its head pops on that edge.
//   - push = i_in_valid && o_in_ready; pop = i_pop && (occupancy != 0).
//   - No empty bypass: every output is a function of registered state only, so a descriptor
//     pushed at edge c is visible as head no earlier than cycle c+1.
//   - push only: +1, pop only: -1, push and pop: occupancy unchanged, both pointers advance.
//   - A rising edge with rst_n=0 clears occupancy and pointers; storage bits are not reset.
//
// Arrival metadata is an elaboration-time option. TS_EN=1 adds one TS_W-bit flip-flop entry per
// descriptor entry; TS_EN=0 elaborates no timestamp storage at all. The pointer, occupancy and
// handshake logic below is shared by both settings.
//
// Storage is a flip-flop array: it is part of the mapped complete-switch area and is never
// blackboxed. DEPTH may be any value >= 1 (pointers wrap by comparison, not by overflow).
module cxl_desc_fifo #(
  parameter int unsigned DEPTH  = cxl_sched_pkg::L_FIFO_DEPTH,
  parameter int unsigned DESC_W = cxl_sched_pkg::L_DESC_W,
  parameter bit          TS_EN  = 1'b0,
  parameter int unsigned TS_W   = cxl_sched_pkg::L_TS_W
) (
  input  logic                       clk,
  input  logic                       rst_n,
  // Input (push) side
  input  logic                       i_in_valid,
  output logic                       o_in_ready,
  input  logic [DESC_W-1:0]          i_in_desc,
  input  logic [TS_W-1:0]            i_in_ts,
  // Output (pop) side
  input  logic                       i_pop,
  output logic                       o_head_valid,
  output logic [DESC_W-1:0]          o_head_desc,
  output logic [TS_W-1:0]            o_head_ts,
  output logic [$clog2(DEPTH+1)-1:0] o_count
);

  // --- Local parameters ---
  localparam int unsigned L_CNT_W = $clog2(DEPTH + 1);
  localparam int unsigned L_PTR_W = (DEPTH > 1) ? $clog2(DEPTH) : 1;

  localparam logic [L_CNT_W-1:0] L_CNT_FULL = L_CNT_W'(DEPTH);
  localparam logic [L_PTR_W-1:0] L_PTR_LAST = L_PTR_W'(DEPTH - 1);

  // --- Signal declarations ---
  logic [L_CNT_W-1:0] count_q;
  logic [L_CNT_W-1:0] count_d;
  logic [L_PTR_W-1:0] wr_ptr_q;
  logic [L_PTR_W-1:0] wr_ptr_d;
  logic [L_PTR_W-1:0] rd_ptr_q;
  logic [L_PTR_W-1:0] rd_ptr_d;

  logic               push;
  logic               pop;

  logic [DESC_W-1:0]  desc_mem_q [0:DEPTH-1];

  // --- Handshake (beginning-of-cycle occupancy only) ---
  assign o_in_ready   = rst_n && (count_q != L_CNT_FULL);
  assign push         = i_in_valid && o_in_ready;
  assign pop          = i_pop && (count_q != '0);

  // --- Head outputs (registered state only, no bypass) ---
  assign o_head_valid = (count_q != '0);
  assign o_head_desc  = desc_mem_q[rd_ptr_q];
  assign o_count      = count_q;

  // --- Next-state: occupancy ---
  always_comb begin
    count_d = count_q;
    unique case ({push, pop})
      2'b10:   count_d = count_q + 1'b1;
      2'b01:   count_d = count_q - 1'b1;
      default: count_d = count_q;
    endcase
  end

  // --- Next-state: pointers (wrap by comparison; DEPTH need not be a power of two) ---
  always_comb begin
    wr_ptr_d = wr_ptr_q;
    if (push) begin
      wr_ptr_d = (wr_ptr_q == L_PTR_LAST) ? '0 : (wr_ptr_q + 1'b1);
    end
  end

  always_comb begin
    rd_ptr_d = rd_ptr_q;
    if (pop) begin
      rd_ptr_d = (rd_ptr_q == L_PTR_LAST) ? '0 : (rd_ptr_q + 1'b1);
    end
  end

  // --- Control state: synchronous active-low reset ---
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      count_q  <= '0;
      wr_ptr_q <= '0;
      rd_ptr_q <= '0;
    end else begin
      count_q  <= count_d;
      wr_ptr_q <= wr_ptr_d;
      rd_ptr_q <= rd_ptr_d;
    end
  end

  // --- Descriptor storage: written at the tail on push, not reset ---
  always_ff @(posedge clk) begin
    if (push) begin
      desc_mem_q[wr_ptr_q] <= i_in_desc;
    end
  end

  // --- Optional arrival-timestamp storage (elaboration-time) ---
  generate
    if (TS_EN) begin : gen_ts
      logic [TS_W-1:0] ts_mem_q [0:DEPTH-1];

      assign o_head_ts = ts_mem_q[rd_ptr_q];

      always_ff @(posedge clk) begin
        if (push) begin
          ts_mem_q[wr_ptr_q] <= i_in_ts;
        end
      end
    end else begin : gen_no_ts
      // No timestamp storage of any kind. The input is reduced into a deliberately unused net so
      // that the unconnected port is explicit; it drives nothing and creates no register.
      logic unused_in_ts;

      assign unused_in_ts = &{1'b0, i_in_ts};
      assign o_head_ts    = '0;
    end
  endgenerate

endmodule
