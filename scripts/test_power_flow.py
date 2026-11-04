"""Local vector/audit contracts. No claim of commercial-tool validation."""
import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_power_vectors as vectors
from check_power_replay import check_replay, check_pt, check_power_report
from traffic_trace import Trace, make_trace

CHECK_INFORMATION = ("Information: Checking 'out_of_table_range'.\n"
                     "Information: Checking 'missing_table'.\n"
                     "Information: Checking 'missing_function'.\n")
CLEAN_CHECK = CHECK_INFORMATION + "check_power succeeded.\n1\n"
# Actual pilot1 W-2024.09 shape; these are diagnostic lines, not library tables.
RANGE_CHECK = """# command: check_power -verbose
Information: Checking 'out_of_table_range'.
  ramp 0.00 at pin 'A1' of cell 'u_out_hold/U13' is out of ramp range (0.02, 1.02) of lib_cell 'AO22X1_RVT'
  load 0.00 at pin 'Y' of cell 'u_out_hold/U13' is out of load range (0.10, 8.00) of lib_cell 'AO22X1_RVT'
  ramp 0.00 at pin 'A4' of cell 'u_out_hold/U14' is out of ramp range (0.02, 1.02) of lib_cell 'AO22X1_RVT'
Warning: There are 2 out_of_range ramps.
Warning: There are 1 out_of_range loads.
Information: Checking 'missing_table'.
Information: Checking 'missing_function'.
0

# return:
"""


class ReplayContracts(unittest.TestCase):
    def test_hold_full_plus_pop_and_no_bypass(self):
        trace = Trace(509, 4, 100, "primary")
        trace.gen = [[(0, k + 1)] for k in range(100)]
        trace.ready = bytearray([0] * 40 + [1] * 60)
        trace.reset = bytearray(100)
        for policy in vectors.POLICIES:
            stats = {}
            rows = list(vectors.replay(trace, policy, stats))
            self.assertEqual(rows[0][5], 0)  # first accepted descriptor cannot bypass
            self.assertEqual(rows[1][5:], (1, 0, 1))
            self.assertTrue(all(row[7] == 1 for row in rows[1:41]))
            self.assertEqual(rows[40][4] & 1, 0)  # full rejects even with closing-edge pop
            self.assertEqual(rows[41][4] & 1, 1)
            self.assertEqual(rows[41][7], 2)
            self.assertEqual(stats["fires"], 60)
            self.assertEqual(stats["accepted"] - 60, stats["outstanding_at_cut"][0])
            self.assertGreater(stats["input_hold_checks"], 0)
            self.assertEqual(stats["drain_cycles"], 0)

    def test_same_intended_trace_across_policies_all_sizes(self):
        for n in (4, 8, 16):
            trace = make_trace(509, n, 1000, "primary")
            original = copy.deepcopy(trace)
            for policy in vectors.POLICIES:
                stats = {}
                rows = list(vectors.replay(trace, policy, stats))
                self.assertEqual([r[3] for r in rows], list(trace.ready))
                self.assertEqual(trace, original)
                self.assertEqual(len(rows), 1000)
                self.assertEqual(stats["accepted"] + stats["generated_but_unaccepted"], trace.generated)
                if policy == "fai-main":
                    self.assertIn("untrained all-H", stats["fai_state_scope"])

    def test_reject_config_or_reset(self):
        for policy, n in (("alg2", 4), ("rr", 2), ("rr", 32)):
            with self.assertRaises(ValueError):
                list(vectors.replay(make_trace(509, n, 10, "primary"), policy, {}))
        trace = make_trace(509, 4, 10, "primary")
        trace.reset[3] = 1
        with self.assertRaises(ValueError):
            list(vectors.replay(trace, "rr", {}))

    def test_primary_export_determinism_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = vectors.export("rr", 4, Path(tmp) / "a")
            b = vectors.export("rr", 4, Path(tmp) / "b")
            self.assertEqual(a["trace_sha256"], "98db926f8e630f817d20d462253e09175c35c8983cacb811d0ff25b66b0a477e")
            self.assertEqual(a["vectors_gzip_sha256"], b["vectors_gzip_sha256"])
            self.assertEqual((a["accepted"], a["fires"]), (72698, 72634))
            self.assertEqual(a["duration_ns"], 2_500_000)
            content = gzip.decompress((Path(tmp) / "a/vectors.txt.gz").read_bytes()).decode().splitlines()
            self.assertEqual(len(content), 100001)
            self.assertEqual(content[0], "43585031 4 100000 509 1 25000 3")
            self.assertEqual([int(content[1].split()[0]), int(content[-1].split()[0])], [0, 99999])
            with self.assertRaises(FileExistsError):
                vectors.export("rr", 4, Path(tmp) / "a")


class AuditContracts(unittest.TestCase):
    def test_actual_check_power_zero_is_qualified_not_clean(self):
        clean = check_power_report(CLEAN_CHECK)
        self.assertEqual(clean["tool_result"], 1)
        self.assertEqual(clean["quality_status"], "NO_CHECK_POWER_ISSUES_REPORTED")
        issue = check_power_report(RANGE_CHECK)
        self.assertEqual(issue["tool_result"], 0)
        self.assertEqual(issue["quality_status"], "QUALIFIED_TABLE_RANGE_WARNINGS_REVIEW_REQUIRED")
        self.assertEqual(issue["range_issue_counts"], dict(ramp=2, load=1))
        self.assertEqual([(d["cell"], d["pin"]) for d in issue["range_issues"]],
                         [("u_out_hold/U13", "A1"), ("u_out_hold/U13", "Y"), ("u_out_hold/U14", "A4")])
        precise = RANGE_CHECK.replace("0.00 at pin", "0.000000000 at pin").replace("(0.02, 1.02)", "(0.016000001, 1.024000049)")
        self.assertEqual(check_power_report(precise)["range_issue_counts"], dict(ramp=2, load=1))

    def test_check_power_rejects_fatal_unknown_missing_or_inconsistent_diagnoses(self):
        failures = [CHECK_INFORMATION + "0\n", CLEAN_CHECK.replace("1\n", "0\n"),
                    RANGE_CHECK.replace("\n0\n", "\n1\n"), RANGE_CHECK.replace("\n0\n", "\n"),
                    RANGE_CHECK.replace("2 out_of_range ramps", "3 out_of_range ramps"),
                    RANGE_CHECK.replace("Information: Checking 'missing_function'.\n", ""),
                    RANGE_CHECK + "Warning: There are missing power tables.\n",
                    RANGE_CHECK + "Warning: Missing function for a library cell.\n",
                    RANGE_CHECK + "Warning: There is no base clock.\n",
                    RANGE_CHECK + "Error: License checkout failed.\n",
                    RANGE_CHECK + "Fatal: cannot calculate power\n",
                    RANGE_CHECK + "0\n",
                    RANGE_CHECK + "Warning: There are 2 out_of_range ramps.\n"]
        for text in failures:
            with self.subTest(text=text), self.assertRaises(ValueError):
                check_power_report(text)

    def test_pt_evidence_echo_is_not_an_emitted_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = ("design.rpt", "library.rpt", "clocks.rpt", "units.rpt", "saif-read.rpt",
                     "check-power.rpt", "update-power.rpt", "disable-timing.rpt", "switching-coverage.rpt",
                     "not-annotated.rpt", "annotated.rpt", "power.rpt", "power-hierarchy.rpt",
                     "registers-and-clock-pins.rpt", "pilot-status.rpt", "pt.log")
            for name in files:
                (root / name).write_text("synthetic stub report\n")
            (root / "saif-read.rpt").write_text("Total number of nets = 100\nNumber of annotated nets = 99\n"
                "Total number of leaf cells = 50\nNumber of fully annotated leaf cells = 49\n")
            (root / "check-power.rpt").write_text(CLEAN_CHECK)
            (root / "power.rpt").write_text("Total Power = 123 (synthetic units)\n")
            echoed = '    puts "POWER_PILOT_ERROR: $detail"\n'
            (root / "pt.log").write_text(echoed)
            self.assertEqual(check_pt(root)["saif_annotation_counts"]["Number of annotated nets"], 99)
            (root / "check-power.rpt").write_text(RANGE_CHECK)
            qualified = check_pt(root)
            self.assertIn("WITH_TABLE_RANGE_WARNINGS", qualified["status"])
            self.assertEqual(qualified["check_power"]["tool_result"], 0)
            self.assertEqual(qualified["method_acceptance"], "NOT_GRANTED_BY_THIS_AUDIT")
            for failure in ("POWER_PILOT_ERROR: actual failure\n", "Error: actual failure\n",
                            "License checkout failed\n", "License denied\n"):
                (root / "pt.log").write_text(echoed + failure)
                with self.assertRaises(ValueError):
                    check_pt(root)

    def test_replay_result_and_saif_reject_corruption(self):
        metadata = dict(measured_cycles=100000, n_src=4, policy_id=1, seed=509, duration_ns=2500000,
                        accepted=4, fires=3, accepted_per_source=[1, 1, 1, 1],
                        fires_per_source=[1, 1, 1, 0], outstanding_at_cut=[0, 0, 0, 1])
        result = "GATE_REPLAY_COMPLETE cycles=100000 n=4 policy=1 seed=509 duration_ns=2500000 accepted=4 fires=3\n"
        result += "\n".join(f"source={h} accepted=1 fires={int(h < 3)} outstanding={int(h == 3)}" for h in range(4)) + "\n"
        saif = "(SAIFILE (TIMESCALE 1 ns) (DURATION 2500000) (INSTANCE tb (INSTANCE dut (NET (clk (T0 1250000) (T1 1250000) (TX 0) (TC 200000))))))"
        with tempfile.TemporaryDirectory() as tmp:
            r, s = Path(tmp) / "result", Path(tmp) / "activity.saif"
            r.write_text(result)
            s.write_text(saif)
            self.assertEqual(check_replay(metadata, r, s)["duration_ns"], 2500000)
            for bad in (saif.replace("2500000", "2500"), saif.replace("INSTANCE dut", "INSTANCE wrong")):
                s.write_text(bad)
                with self.assertRaises(ValueError):
                    check_replay(metadata, r, s)
            s.write_text(saif)
            r.write_text(result.replace("accepted=4", "accepted=5"))
            with self.assertRaises(ValueError):
                check_replay(metadata, r, s)
            with self.assertRaises(ValueError):
                check_pt(tmp)  # no fabricated PASS from absent PT evidence

    def test_tcl_pilot_scope_constraints_and_no_library_dump(self):
        try:
            import tkinter
            tcl = tkinter.Tcl()
        except Exception:
            self.skipTest("tkinter Tcl not installed; commercial behavior remains parent calibration")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "output").mkdir()
            (root / "reports").mkdir()
            for name in ("original.db", "activity.saif", "output/switch_top.syn.v", "output/switch_top.syn.sdc"):
                (root / name).write_text("synthetic fixture, not a real cell library/netlist")
            config = dict(PROFILE_SHA256=vectors.PROFILE_SHA, PROFILE_STATUS="FROZEN", CLOCK_PERIOD="25.0",
                WIRE_LOAD_METHOD="fixed_model", WIRE_LOAD_MODEL="ForQA", WIRE_LOAD_MODE="top",
                PARAM_RR_QUANTUM="10", PARAM_FAI_W="5000000", PARAM_N_SRC="4", POLICY_NAME="rr",
                TARGET_LIBRARY=str(root / "original.db").replace("\\", "/"),
                NETLIST_FILE="output/switch_top.syn.v", SDC_FILE="output/switch_top.syn.sdc",
                LIB_NAME="synthetic_tt", OPERATING_CONDITIONS="synthetic_corner", TOP_MODULE="switch_top")
            (root / "run_config.tcl").write_text("\n".join(f"set {k} {{{v}}}" for k, v in config.items()))
            for key, value in dict(POWER_CASE_ROOT=root, POWER_REPORT_DIR=root / "reports",
                POWER_SAIF=root / "activity.saif", POWER_N=4, POWER_POLICY="rr", POWER_DB=root / "original.db").items():
                tcl.setvar(f"env({key})", str(value).replace("\\", "/"))
            tcl.eval('''
set calls {}
proc unknown {cmd args} {
    lappend ::calls [linsert $args 0 $cmd]
    switch $cmd {
        get_app_var {return true}
        all_registers {return ff0}
        get_nets {return clk}
        get_object_name {return [lindex $args 0]}
        get_switching_activity {return {0.08 activity_file}}
        default {return 1}
    }
}
proc redirect {flag var script} {
    uplevel #0 $script
    uplevel #0 [list set $var "synthetic report output"]
    return 1
}
proc foreach_in_collection {var objects script} {
    foreach item $objects {
        uplevel 1 [list set $var $item]
        uplevel 1 $script
    }
}
''')
            code = (vectors.ROOT / "sta/power_pt.tcl").read_text().split("if {[catch {power_main}")[0]
            tcl.eval(code)
            tcl.eval("power_main")
            calls = tcl.eval("join $calls \\n")
            self.assertIn("read_sdc -version 2.1", calls)
            self.assertIn("read_saif -strip_path tb/dut", calls)
            self.assertIn("set_host_options -max_cores 1", calls)
            self.assertNotIn("report_lib", calls)
            self.assertIn("SEMANTIC_REVIEW_REQUIRED", (root / "reports/pilot-status.rpt").read_text())
            tcl.setvar("env(POWER_POLICY)", "fcfs")
            with self.assertRaises(tkinter.TclError):
                tcl.eval("power_main")


if __name__ == "__main__":
    unittest.main()
