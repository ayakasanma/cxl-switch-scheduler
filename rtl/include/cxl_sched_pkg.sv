// cxl_sched_pkg.sv — Shared types/constants for the CXL scheduler common framework
// Spec: specs/CXL_SPEC.md v1.0 (sections 3, 4, 6), docs/phase-3-uarch/common_framework.md item 1
// Coding style: lowRISC SV Style Guide + project overrides (IEEE 1800-2009, synthesizable)
//
// The descriptor is opaque to the scheduler: all 105 bits are stored and transported intact.
// No source, destination or tag-tracking field exists beyond these 105 bits.
package cxl_sched_pkg;

  // --- Descriptor field widths (spec section 3) ---
  localparam int unsigned L_TAG_W     = 32;
  localparam int unsigned L_ADDR_W    = 32;
  localparam int unsigned L_OPCODE_W  = 1;
  localparam int unsigned L_LENGTH_W  = 8;
  localparam int unsigned L_PAYLOAD_W = 32;

  // --- Approved packed slices, most to least significant ---
  //   Tag [104:73], Address [72:41], Opcode [40], Length [39:32], Payload [31:0]
  localparam int unsigned L_PAYLOAD_LSB = 0;
  localparam int unsigned L_LENGTH_LSB  = L_PAYLOAD_LSB + L_PAYLOAD_W;  // 32
  localparam int unsigned L_OPCODE_LSB  = L_LENGTH_LSB + L_LENGTH_W;    // 40
  localparam int unsigned L_ADDR_LSB    = L_OPCODE_LSB + L_OPCODE_W;    // 41
  localparam int unsigned L_TAG_LSB     = L_ADDR_LSB + L_ADDR_W;        // 73
  localparam int unsigned L_DESC_W      = L_TAG_LSB + L_TAG_W;          // 105

  // --- Common storage constants ---
  localparam int unsigned L_FIFO_DEPTH = 16;  // D: entries per source FIFO
  localparam int unsigned L_TS_W       = 32;  // arrival timestamp width (FCFS/FAI metadata only)

  // --- Types derived from the storage constants (shared by switch_top and the policy slot) ---
  typedef logic [$clog2(L_FIFO_DEPTH+1)-1:0] fifo_count_t;  // per-source occupancy, 0..D
  typedef logic [L_TS_W-1:0]                 ts_t;          // arrival timestamp
  typedef logic [L_DESC_W-1:0]               desc_vec_t;    // flat 105-bit descriptor vector

  // --- Descriptor: first member is the most significant, so desc_t is bit-identical to a
  //     logic [L_DESC_W-1:0] vector using the slices above ---
  typedef struct packed {
    logic [L_TAG_W-1:0]     tag;      // [104:73]
    logic [L_ADDR_W-1:0]    addr;     // [72:41]
    logic [L_OPCODE_W-1:0]  opcode;   // [40]
    logic [L_LENGTH_W-1:0]  length;   // [39:32]
    logic [L_PAYLOAD_W-1:0] payload;  // [31:0]
  } desc_t;

  // --- Policy identifiers (identifiers only; they do not imply that a policy is implemented) ---
  localparam int unsigned L_POLICY_W = 2;

  typedef enum logic [L_POLICY_W-1:0] {
    POLICY_FCFS     = 2'd0,  // first-come first-served, shared timestamp selector
    POLICY_RR       = 2'd1,  // round robin, no arrival metadata
    POLICY_FAI_MAIN = 2'd2,  // FAI-inspired Main four-state interpretation (spec section 8.1-8.5)
    POLICY_FAI_ALG2 = 2'd3   // FAI Algorithm-2 supplementary interpretation (spec section 8.6)
  } policy_e;

endpackage
