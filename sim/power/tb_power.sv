// Common pin replay; POWER_RTL_FIXTURE is local infrastructure-only, never mapped power evidence.
`timescale 1ns/1ps
`ifndef POWER_N_SRC
`define POWER_N_SRC 4
`endif
module tb;
  localparam integer N = `POWER_N_SRC;
  logic clk = 0, rst_n = 0;
  logic [N-1:0] i_in_valid = 0;
  logic [N*105-1:0] i_in_desc = 0;
  logic i_out_ready = 0;
  wire [N-1:0] o_in_ready;
  wire o_out_valid;
  wire [104:0] o_out_desc;
  wire [$clog2(N)-1:0] o_out_source;
`ifdef POWER_RTL_FIXTURE
  switch_top #(.N_SRC(N), .POLICY(`POWER_FIXTURE_POLICY), .FAI_W(256)) dut (.*);
`else
  switch_top dut (.*);
`endif
  always #12.5 clk = ~clk;

  integer fd, result_fd, rc, magic, vector_n, cycles, seed, policy, period_ps, resets;
  integer mode_id = 0, warmup = 0, measured = 100000, phase;
  integer index, row_index;
  integer accepted [2], fires [2];
  integer per_source_accept [2][N], per_source_fire [2][N];
  integer outstanding_at_cut [N];
  logic [N-1:0] expected_ready;
  logic expected_valid;
  logic [$clog2(N)-1:0] expected_source;
  logic [104:0] expected_desc;
  string vector_path, result_path, saif_path, extra;
  reg [8191:0] line; // Maximum N16 row is below 512 ASCII bytes; one bounded line buffer.
  realtime start_time;

  initial begin
    if (!(N == 4 || N == 8 || N == 16)) $fatal(1, "unsupported N");
    if (!$value$plusargs("vectors=%s", vector_path) ||
        !$value$plusargs("result=%s", result_path) ||
        !$value$plusargs("saif=%s", saif_path)) $fatal(1, "vectors/result/saif plusargs required");
    fd = $fopen(vector_path, "r");
    if (fd == 0) $fatal(1, "cannot open vectors");
    rc = $fgets(line, fd);
    if (rc == 0) $fatal(1, "missing power header");
    rc = $sscanf(line, "%h", magic);
    if (rc != 1) $fatal(1, "missing power magic");
    if (magic === 'h43585031) begin
      rc = $sscanf(line, "%h %d %d %d %d %d %d", magic, vector_n, cycles, seed, policy, period_ps, resets);
      if (rc != 7 || cycles != 100000 || seed != 509) $fatal(1, "invalid primary power header");
      if ($sscanf(line, "%h %d %d %d %d %d %d %s", magic, vector_n, cycles, seed, policy, period_ps, resets, extra) == 8)
        $fatal(1, "extra primary header fields");
    end else if (magic === 'h43585032) begin
      rc = $sscanf(line, "%h %d %d %d %d %d %d %d %d %d", magic, mode_id, vector_n,
                   cycles, warmup, measured, seed, policy, period_ps, resets);
      if (rc != 10 || cycles != warmup + measured)
        $fatal(1, "invalid supplementary power header fields=%0d total=%0d warmup=%0d measured=%0d", rc, cycles, warmup, measured);
      if ($sscanf(line, "%h %d %d %d %d %d %d %d %d %d %s", magic, mode_id, vector_n,
                   cycles, warmup, measured, seed, policy, period_ps, resets, extra) == 11)
        $fatal(1, "extra supplementary header fields");
      case (mode_id)
        1: if (warmup != 0 || measured != 100000 || !(seed == 510 || seed == 511))
             $fatal(1, "invalid cold-seed header");
        2: if (vector_n != 4 || seed != 509 || warmup != 9999500 || measured != 100000)
             $fatal(1, "invalid boundary header");
        12: if (vector_n != 4 || seed < 509 || seed > 513 || warmup != 10000000 || measured != 100000)
              $fatal(1, "invalid trained A header");
        13: if (vector_n != 4 || seed < 509 || seed > 513 || warmup != 10101024 || measured != 102400)
              $fatal(1, "invalid trained B header");
`ifdef POWER_RTL_FIXTURE
`ifdef POWER_NO_SAIF
        9: if (warmup < 0 || warmup > 100000 || measured <= 0 || measured > 100000)
             $fatal(1, "invalid local fixture header");
`endif
`endif
        default: $fatal(1, "unsupported power mode (fixture refused by production)");
      endcase
    end else $fatal(1, "invalid power magic");
    if ((^{magic, vector_n, cycles, seed, policy, period_ps, resets, mode_id, warmup, measured} === 1'bx) ||
        vector_n != N || policy < 0 || policy > 2 || period_ps != 25000 || resets != 3)
      $fatal(1, "invalid power configuration");
    if (mode_id == 12 || mode_id == 13) begin
      // Reject integer overflow aliases accepted by the fixed-width sscanf destinations.
      extra = line;
      if (extra != $sformatf("43585032 %0d %0d %0d %0d %0d %0d %0d %0d %0d\n",
          mode_id, vector_n, cycles, warmup, measured, seed, policy, period_ps, resets))
        $fatal(1, "noncanonical trained power header");
    end
`ifdef POWER_RTL_FIXTURE
    if (policy != `POWER_FIXTURE_POLICY) $fatal(1, "fixture policy does not match compiled RTL");
`endif
    for (integer p = 0; p < 2; p++) begin
      accepted[p] = 0;
      fires[p] = 0;
      for (integer h = 0; h < N; h++) begin
        per_source_accept[p][h] = 0;
        per_source_fire[p][h] = 0;
        outstanding_at_cut[h] = 0;
      end
    end
    repeat (3) @(negedge clk);
    if (o_in_ready !== {N{1'b0}} || o_out_valid !== 1'b0)
      $fatal(1, "handshake active/unknown during synchronous reset");
`ifndef POWER_NO_SAIF
    $set_toggle_region(tb.dut);
`endif
    for (index = 0; index < cycles; index++) begin
      if (index == warmup) begin
        for (integer h = 0; h < N; h++)
          outstanding_at_cut[h] = per_source_accept[0][h] - per_source_fire[0][h];
`ifndef POWER_NO_SAIF
        $toggle_start();
`else
        $display("POWER_LOCAL_TOGGLE_START checked_cycles=%0d", index);
`endif
        start_time = $realtime;
      end
      if (index == 0) rst_n = 1;
      rc = $fgets(line, fd);
      if (rc == 0) $fatal(1, "missing vector row %0d", index);
      rc = $sscanf(line, "%d %h %h %h %h %h %h %h", row_index, i_in_valid,
                    i_in_desc, i_out_ready, expected_ready, expected_valid, expected_source, expected_desc);
      if (rc != 8 || row_index !== index) $fatal(1, "bad vector row %0d", index);
      if ($sscanf(line, "%d %h %h %h %h %h %h %h %s", row_index, i_in_valid,
                    i_in_desc, i_out_ready, expected_ready, expected_valid, expected_source, expected_desc, extra) == 9)
        $fatal(1, "extra fields in vector row %0d", index);
      if ((^{i_in_valid, i_in_desc, i_out_ready, expected_ready, expected_valid, expected_source, expected_desc} === 1'bx))
        $fatal(1, "X/Z in vector row %0d", index);
      #12;
      if (clk !== 1'b0 || rst_n !== 1'b1) $fatal(1, "unknown/invalid replay clock or reset");
      if (o_in_ready !== expected_ready || o_out_valid !== expected_valid)
        $fatal(1, "cycle %0d ready/valid mismatch actual=%h/%b expected=%h/%b",
               index, o_in_ready, o_out_valid, expected_ready, expected_valid);
      if (expected_valid && (o_out_source !== expected_source || o_out_desc !== expected_desc))
        $fatal(1, "cycle %0d valid source/full105 mismatch", index);
      phase = (index < warmup) ? 0 : 1;
      for (integer h = 0; h < N; h++) begin
        if (i_in_valid[h] && o_in_ready[h]) begin
          accepted[phase]++;
          per_source_accept[phase][h]++;
        end
      end
      if (o_out_valid && i_out_ready) begin
        fires[phase]++;
        per_source_fire[phase][o_out_source]++;
      end
      @(negedge clk);
      if (warmup > 0 && (index + 1) % 1000000 == 0)
        $display("POWER_REPLAY_PROGRESS checked_cycles=%0d phase=%s", index + 1,
                 (index < warmup) ? "warmup" : "measured");
    end
`ifndef POWER_NO_SAIF
    $toggle_stop();
    $toggle_report(saif_path, 1.0e-9, tb.dut);
`else
    $display("POWER_LOCAL_TOGGLE_STOP checked_cycles=%0d measured_cycles=%0d", cycles, measured);
`endif
    if ($realtime - start_time != 25.0 * measured) $fatal(1, "wrong measured activity duration");
    while ($fgets(line, fd) != 0) begin
      if ($sscanf(line, "%s", extra) == 1) $fatal(1, "extra vector rows/content");
    end
    $fclose(fd);
    result_fd = $fopen(result_path, "w");
    if (result_fd == 0) $fatal(1, "cannot open result file");
    if (mode_id == 0) begin
      $fdisplay(result_fd, "GATE_REPLAY_COMPLETE cycles=%0d n=%0d policy=%0d seed=%0d duration_ns=2500000 accepted=%0d fires=%0d",
                cycles, N, policy, seed, accepted[1], fires[1]);
      for (integer h = 0; h < N; h++)
        $fdisplay(result_fd, "source=%0d accepted=%0d fires=%0d outstanding=%0d", h,
                  per_source_accept[1][h], per_source_fire[1][h], per_source_accept[1][h] - per_source_fire[1][h]);
    end else begin
      $fdisplay(result_fd, "GATE_REPLAY_V2_COMPLETE mode=%0d n=%0d policy=%0d seed=%0d total_cycles=%0d warmup_cycles=%0d measured_cycles=%0d duration_ns=%0d",
                mode_id, N, policy, seed, cycles, warmup, measured, 25 * measured);
      $fdisplay(result_fd, "phase=warmup accepted=%0d fires=%0d", accepted[0], fires[0]);
      $fdisplay(result_fd, "phase=measured accepted=%0d fires=%0d", accepted[1], fires[1]);
      $fdisplay(result_fd, "phase=all accepted=%0d fires=%0d", accepted[0] + accepted[1], fires[0] + fires[1]);
      for (integer h = 0; h < N; h++)
        $fdisplay(result_fd, "source=%0d warmup_accepted=%0d warmup_fires=%0d measured_accepted=%0d measured_fires=%0d outstanding_at_cut=%0d outstanding_at_end=%0d",
                  h, per_source_accept[0][h], per_source_fire[0][h], per_source_accept[1][h],
                  per_source_fire[1][h], outstanding_at_cut[h], per_source_accept[0][h] + per_source_accept[1][h] -
                  per_source_fire[0][h] - per_source_fire[1][h]);
    end
    $fclose(result_fd);
    $display("GATE_REPLAY_COMPLETE checked_cycles=%0d measured_cycles=%0d ZERO_DELAY_NO_SDF", cycles, measured);
    $finish;
  end
endmodule
