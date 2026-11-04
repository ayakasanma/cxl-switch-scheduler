// tb_ts_older_equiv.sv — simulation-only self-check of the cxl_fcfs_sel ts_older rewrite.
// Not synthesizable RTL; never part of a filelist. Driven by scripts/check_ts_older_equiv.sh.
//
// Instantiates, side by side and with identical inputs:
//   u_dut  : the working-tree rtl/common/cxl_fcfs_sel.sv (edited ts_older)
//   u_base : the baseline module from git (cxl_fcfs_sel at the recorded commit, renamed
//            cxl_fcfs_sel_head_base by the runner; original diff = b - a form)
// and checks on every applied vector:
//   (1) u_dut outputs == u_base outputs (o_valid, o_source), bit for bit;
//   (2) o_valid == |i_eligible and, when valid, o_source is eligible;
//   (3) N_SRC == 2: o_source equals the spec-6 definition evaluated with 64-bit integer
//       arithmetic (independent of both RTL expressions): right (source 1) wins iff it is
//       eligible and (left ineligible or 0 < (ts0 - ts1) mod 2^TS_W < 2^(TS_W-1));
//   (4) clustered vectors (all eligible timestamps within one half-range window, the spec-6
//       environment): o_source is the lowest-ID oldest eligible source by unwrapped age.
//
// Modes (parameter MODE):
//   0 EXHAUSTIVE : every i_head_ts value (2^(N_SRC*TS_W)); every eligible mask too when
//                  N_SRC*TS_W + N_SRC <= EXH_MASK_BITS, else the all-eligible mask plus
//                  RAND_MASKS random masks per timestamp vector.
//   1 BOUNDARY   : TS_W = 32 structured boundary pairs (N_SRC = 2), all eligible masks.
//   2 RANDOM     : N_RAND uniformly random vectors + N_RAND clustered vectors (fixed SEED).
module tb_ts_older_equiv #(
  parameter int unsigned N_SRC         = 2,
  parameter int unsigned TS_W          = 4,
  parameter int unsigned MODE          = 0,
  parameter int unsigned N_RAND        = 1000,
  parameter int unsigned SEED          = 1,
  parameter int unsigned EXH_MASK_BITS = 22,
  parameter int unsigned RAND_MASKS    = 2
);

  localparam int unsigned L_SRC_W = $clog2(N_SRC);
  localparam int unsigned L_TOT_W = N_SRC * TS_W;

  logic [N_SRC-1:0]   eligible;
  logic [L_TOT_W-1:0] head_ts;
  logic               dut_valid;
  logic [L_SRC_W-1:0] dut_source;
  logic               base_valid;
  logic [L_SRC_W-1:0] base_source;

  longint unsigned n_vec;
  longint unsigned n_spec;
  longint unsigned n_clust;
  longint unsigned n_err;

  cxl_fcfs_sel #(
    .N_SRC (N_SRC),
    .TS_W  (TS_W)
  ) u_dut (
    .i_eligible (eligible),
    .i_head_ts  (head_ts),
    .o_valid    (dut_valid),
    .o_source   (dut_source)
  );

  cxl_fcfs_sel_head_base #(
    .N_SRC (N_SRC),
    .TS_W  (TS_W)
  ) u_base (
    .i_eligible (eligible),
    .i_head_ts  (head_ts),
    .o_valid    (base_valid),
    .o_source   (base_source)
  );

  // TS_W-bit modulus mask, as a 64-bit integer (TS_W <= 32 in this harness)
  function automatic longint unsigned ts_mask();
    return (longint'(1) << TS_W) - 1;
  endfunction

  // Spec 6, integer form: a strictly older than b iff 0 < (b - a) mod 2^TS_W < 2^(TS_W-1)
  function automatic bit spec_older(input longint unsigned a, input longint unsigned b);
    longint unsigned d;
    d = (b - a) & ts_mask();
    return (d != 0) && (d < (longint'(1) << (TS_W - 1)));
  endfunction

  function automatic longint unsigned ts_of(input int unsigned h);
    return longint'(head_ts[h*TS_W +: TS_W]);
  endfunction

  task automatic fail(input string what);
    n_err++;
    if (n_err <= 20) begin
      $display("MISMATCH %s: eligible=%b head_ts=%h dut=(%0d,%0d) base=(%0d,%0d)", what,
               eligible, head_ts, dut_valid, dut_source, base_valid, base_source);
    end
  endtask

  // Apply the current eligible/head_ts, settle, check (1)-(3)
  task automatic apply_and_check();
    #1;
    n_vec++;
    if ((dut_valid !== base_valid) || (dut_source !== base_source)) fail("dut!=base");
    if (dut_valid !== (|eligible)) fail("valid!=|eligible");
    if (dut_valid && !eligible[dut_source]) fail("ineligible winner");
    if (N_SRC == 2) begin
      logic exp_src;
      n_spec++;
      exp_src = eligible[1] && (!eligible[0] || spec_older(ts_of(1), ts_of(0)));
      if (dut_valid && (dut_source !== L_SRC_W'(exp_src))) fail("spec6 reference");
    end
  endtask

  // Clustered vector: all timestamps = base + age offset < 2^(TS_W-1) - 1 behind 'now'
  // (unwrapped order is well defined); check (4) in addition to (1)-(3).
  task automatic clustered_vector(input longint unsigned now_v, input longint unsigned span);
    longint unsigned age [N_SRC];
    longint unsigned best_age;
    int              best_src;
    for (int unsigned h = 0; h < N_SRC; h++) begin
      age[h]                    = longint'($urandom) % span;
      head_ts[h*TS_W +: TS_W]   = TS_W'((now_v - age[h]) & ts_mask());
      eligible[h]               = (int'($urandom) % 4) != 0;
    end
    apply_and_check();
    n_clust++;
    best_src = -1;
    best_age = 0;
    for (int unsigned h = 0; h < N_SRC; h++) begin
      if (eligible[h] && ((best_src < 0) || (age[h] > best_age))) begin
        best_src = int'(h);
        best_age = age[h];
      end
    end
    if ((best_src >= 0) && (dut_source !== L_SRC_W'(best_src))) fail("clustered oldest/lowest-ID");
  endtask

  initial begin
    longint unsigned ts_count;
    n_vec   = 0;
    n_spec  = 0;
    n_clust = 0;
    n_err   = 0;
    void'($urandom(SEED));
    eligible = '0;
    head_ts  = '0;

    if (MODE == 0) begin : exhaustive
      ts_count = longint'(1) << L_TOT_W;
      for (longint unsigned k = 0; k < ts_count; k++) begin
        head_ts = L_TOT_W'(k);
        if (L_TOT_W + N_SRC <= EXH_MASK_BITS) begin
          for (int unsigned m = 0; m < (1 << N_SRC); m++) begin
            eligible = N_SRC'(m);
            apply_and_check();
          end
        end else begin
          eligible = '1;
          apply_and_check();
          for (int unsigned r = 0; r < RAND_MASKS; r++) begin
            eligible = N_SRC'($urandom);
            apply_and_check();
          end
        end
      end
    end else if (MODE == 1) begin : boundary
      longint unsigned vals [$];
      longint unsigned dels [$];
      longint unsigned half;
      int              n_pos;
      if (N_SRC != 2) $fatal(1, "MODE 1 (boundary) requires N_SRC = 2");
      half = longint'(1) << (TS_W - 1);
      // Values: extremes, half-range neighbourhood, alternating patterns, 2^k and 2^k - 1
      vals = '{0, 1, 2, 3, half - 2, half - 1, half, half + 1, half + 2,
               ts_mask(), ts_mask() - 1, ts_mask() - 2, 64'h5555_5555 & ts_mask(),
               64'hAAAA_AAAA & ts_mask(), 64'h0123_4567 & ts_mask(), 64'hFEDC_BA98 & ts_mask()};
      for (int unsigned k = 0; k < TS_W; k++) begin
        vals.push_back(longint'(1) << k);
        vals.push_back((longint'(1) << k) - 1);
      end
      // Differences b - a: 0, +-1, +-2, half and its neighbours, +-2^k, +-(2^k - 1)
      dels = '{0, 1, 2, half - 1, half, half + 1};
      for (int unsigned k = 0; k < TS_W; k++) begin
        dels.push_back(longint'(1) << k);
        dels.push_back((longint'(1) << k) - 1);
      end
      n_pos = dels.size();
      for (int i = 0; i < n_pos; i++) begin
        dels.push_back((longint'(0) - dels[i]) & ts_mask());
      end
      // All value pairs, and every value against value+delta, both orientations, all masks
      for (int i = 0; i < vals.size(); i++) begin
        for (int j = 0; j < vals.size() + dels.size(); j++) begin
          logic [TS_W-1:0] a;
          logic [TS_W-1:0] b;
          a = TS_W'(vals[i]);
          b = (j < vals.size()) ? TS_W'(vals[j]) : TS_W'(vals[i] + dels[j - vals.size()]);
          for (int o = 0; o < 2; o++) begin
            head_ts = (o == 0) ? L_TOT_W'({a, b}) : L_TOT_W'({b, a});  // MODE 1 runs N_SRC = 2
            for (int unsigned m = 0; m < (1 << N_SRC); m++) begin
              eligible = N_SRC'(m);
              apply_and_check();
            end
          end
        end
      end
    end else begin : random
      for (int r = 0; r < int'(N_RAND); r++) begin
        for (int unsigned h = 0; h < N_SRC; h++) begin
          head_ts[h*TS_W +: TS_W] = TS_W'($urandom);
        end
        eligible = N_SRC'($urandom);
        if ((r % 8) == 0) eligible = '1;
        apply_and_check();
      end
      for (int r = 0; r < int'(N_RAND); r++) begin
        // Mix of tiny spans (many ties) and spans up to the half range. 'now' is just past the
        // 2^TS_W wrap (window straddles it), just below it, or uniformly random.
        longint unsigned span;
        longint unsigned now_v;
        unique case (r % 4)
          0:       span = 2;
          1:       span = 17;
          2:       span = longint'(1) << (TS_W - 2);
          default: span = (longint'(1) << (TS_W - 1)) - 1;
        endcase
        unique case (r % 3)
          0:       now_v = (longint'($urandom) % 8);
          1:       now_v = ts_mask() - (longint'($urandom) % 8);
          default: now_v = longint'($urandom) & ts_mask();
        endcase
        clustered_vector(now_v, span);
      end
    end

    $display("RESULT N_SRC=%0d TS_W=%0d MODE=%0d vectors=%0d spec6_checked=%0d clustered=%0d errors=%0d",
             N_SRC, TS_W, MODE, n_vec, n_spec, n_clust, n_err);
    if (n_err != 0) $fatal(1, "ts_older equivalence FAILED");
    $display("PASS");
    $finish;
  end

endmodule
