"""Offline adapter tests; no simulator, network or commercial tool invocation."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_revision_cgof_ppa as cgof

LIBRARY = "/remote/existing/saed32rvt_tt0p78v25c.db"


class AdapterTests(unittest.TestCase):
    def test_declared_state_includes_metadata_credits_and_held_context(self):
        p = cgof.parameters()
        self.assertEqual(p["elab_parameters"], "N_SRC=4,DEPTH=16,FAI_W=5000000,HIGH_WEIGHT=2")
        self.assertNotIn("POLICY", p)
        self.assertNotIn("RR_QUANTUM", p)
        self.assertEqual(p["declared_total_state_bits"], 9014)
        self.assertEqual(p["expected"]["min_register_bits"], 8768)
        self.assertEqual(p["declared_state_bits"]["hold_context"], 5)
        self.assertEqual(p["declared_state_bits"]["credits"], 8)
        self.assertEqual(p["declared_state_bits"]["per_source_fire_counters"], 92)
        self.assertEqual(sum(p["expected"]["port_bits"].values()), 539)
        self.assertEqual(p["expected"]["timed_input_bits"], 426)
        self.assertEqual(p["threshold_arithmetic_bits"], 32)

    def test_parameterized_matrix_keeps_widths_and_names_consistent(self):
        for n_src, high_weight in ((4, 1), (8, 1), (8, 2), (16, 1), (16, 2)):
            p = cgof.parameters(n_src, high_weight)
            self.assertEqual(p["N_SRC"], n_src)
            self.assertEqual(p["HIGH_WEIGHT"], high_weight)
            self.assertEqual(p["elab_parameters"],
                             f"N_SRC={n_src},DEPTH=16,FAI_W=5000000,HIGH_WEIGHT={high_weight}")
            self.assertEqual(p["declared_state_bits"]["hold_source"],
                             (n_src - 1).bit_length())
            self.assertEqual(p["declared_state_bits"]["hold_context"],
                             n_src + 1 if high_weight > 1 else 1)
            self.assertEqual(p["declared_state_bits"]["credits"],
                             n_src * high_weight.bit_length())
            self.assertEqual(cgof.run_name(n_src, high_weight),
                             f"cxl-ppa-syn-cgof{high_weight}-n{n_src}")
            self.assertIn(f"HIGH_WEIGHT{high_weight}", cgof.reference(n_src, high_weight))
        with self.assertRaisesRegex(ValueError, "N_SRC=4/8/16"):
            cgof.parameters(2, 2)

    def test_rendered_config_keeps_every_matched_profile_value(self):
        profile, _ = cgof.base.load_profile(cgof.ROOT / cgof.PROFILE, LIBRARY)
        original = cgof.base.run_config(
            "syn", cgof.RUN, cgof.base.parameters("fai-main", 4),
            LIBRARY, cgof.SOURCES, profile, cgof.PROFILE_SHA).decode()
        config = cgof.render_config(cgof.parameters(), LIBRARY, profile).decode()
        # Constraint/methodology lines are shared bytes, not independently retyped numbers.
        tail = original[original.index("set PROFILE_ID"):]
        self.assertTrue(config.startswith(config.split("set PROFILE_ID")[0] + tail))
        self.assertIn("set TOP_MODULE {cgof_unit_top}", config)
        self.assertIn("set EXPECT_POLICY_MODULE {cxl_cgof_sched}", config)
        self.assertIn("set MAX_CAPACITANCE_SCALE 0.75", config)
        self.assertNotIn("PARAM_POLICY", config)
        self.assertNotIn("PARAM_RR_QUANTUM", config)
        self.assertNotIn("switch_top", config)

    def test_formal_uses_the_real_audited_bridge_and_no_exclusions(self):
        template = (cgof.ROOT / cgof.TEMPLATE).read_bytes()
        text = cgof.render_formal(template).decode()
        self.assertIn(cgof.REFERENCE, text)
        self.assertIn("set_svf $base/default.svf", text)
        self.assertIn("read_sverilog -r -define SYNTHESIS $sources", text)
        self.assertIn("set_top -parameter $ELAB_PARAMETERS r:/WORK/cgof_unit_top", text)
        self.assertIn("read_verilog -i $base/output/cgof_unit_top.syn.v", text)
        self.assertIn("set ::synopsys_auto_setup false", text)
        self.assertIn("report_undriven_nets", text)
        self.assertIn("report_setup_status -all", text)
        for command in ("set_constant ", "set_dont_verify_points ", "set_black_box ",
                        "set_user_match ", "set_constraint "):
            self.assertNotIn(command, text)
        self.assertNotIn("switch_top", text)
        self.assertNotIn("CXL_FM_", text.replace("CXL_FM_ERROR", "").replace(
            "CXL_FM_COMMANDS_COMPLETED_REVIEW_REQUIRED", ""))

    def test_template_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "template hash"):
            cgof.render_formal((cgof.ROOT / cgof.TEMPLATE).read_bytes()+b"\n")
        with self.assertRaisesRegex(ValueError, "shared template changed"):
            cgof.replace_once("two two", "two", "one")

    def test_dc_pt_runner_binds_svf_and_exact_new_top(self):
        profile, _ = cgof.base.load_profile(cgof.ROOT / cgof.PROFILE, LIBRARY)
        text = cgof.render_dc_pt_runner(LIBRARY, profile).decode()
        self.assertIn("module[[:space:]]+cgof_unit_top", text)
        self.assertIn('sha256sum -- "$NETLIST" "$SDC" default.svf > logs/dc-handoff.sha256', text)
        self.assertIn("pt-handoff-verification.log", text)
        self.assertIn("COMMANDS_COMPLETED_REVIEW_REQUIRED", text)
        self.assertNotIn("switch_top", text)

    def test_formal_wrapper_is_separate_and_requires_unchanged_handoff(self):
        text = cgof.FORMAL_RUNNER
        self.assertIn("test ! -e formal", text)
        self.assertEqual(text.count("sha256sum --strict -c logs/dc-handoff.sha256"), 2)
        self.assertEqual(text.count("sha256sum --strict -c SHA256SUMS"), 2)
        self.assertIn("/usr/bin/timeout 15m fm_shell", text)
        self.assertIn('test "$rc" -eq 0', text)
        self.assertIn("verify_return=1", text)
        self.assertIn("cmp formal/source-before.sha256 formal/source-after.sha256", text)

    def test_incomplete_correctness_cannot_prepare_ppa(self):
        with tempfile.TemporaryDirectory(prefix="cgof-ppa-gate-") as tmp:
            native = Path(tmp) / "correctness"
            native.mkdir()
            (native / "cgof_scope.json").write_text(json.dumps(dict(complete_matrix=False)))
            (native / "summary.json").write_text(json.dumps(dict(overall="PASS")))
            output = Path(tmp) / "prepared"
            with self.assertRaisesRegex(ValueError, "incomplete"):
                cgof.prepare(LIBRARY, output, native)
            self.assertFalse(output.exists())

    def test_script_imports_repo_packages_without_cwd_on_sys_path(self):
        code = (
            "import os, sys, tempfile, unittest\n"
            f"os.chdir(tempfile.mkdtemp())\n"
            f"sys.path.insert(0, {str(cgof.ROOT / 'scripts')!r})\n"
            "import prepare_revision_cgof_ppa as p\n"
            "print(unittest.defaultTestLoader.loadTestsFromName("
            "p.gates.native.MODEL_TEST_MODULE).countTestCases())\n"
        )
        done = subprocess.run([sys.executable, "-B", "-c", code],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "17")

    def test_nonmatched_profile_is_rejected_before_native_gate(self):
        profile, raw = cgof.base.load_profile(cgof.ROOT / cgof.PROFILE, LIBRARY)
        profile["clock"]["period"] = 24
        with patch.object(cgof.base, "load_profile", return_value=(profile, raw)), \
                patch.object(cgof.gates, "verify_native") as gate:
            with self.assertRaisesRegex(ValueError, "frozen matched"):
                cgof.prepare(LIBRARY, cgof.OUTPUT_ROOT / "must-not-exist", Path("unrun"))
            gate.assert_not_called()

    def test_native_rejection_creates_no_payload(self):
        output = cgof.OUTPUT_ROOT / "rejected-native-must-not-exist"
        with patch.object(cgof.gates, "verify_native", side_effect=ValueError("native changed")):
            with self.assertRaisesRegex(ValueError, "native changed"):
                cgof.prepare(LIBRARY, output, Path("unrun"))
        self.assertFalse(output.exists())

    def test_config_is_valid_tcl_with_only_native_cgof_parameters(self):
        import tkinter
        profile, _ = cgof.base.load_profile(cgof.ROOT / cgof.PROFILE, LIBRARY)
        interp = tkinter.Tcl()
        interp.eval(cgof.render_config(cgof.parameters(), LIBRARY, profile).decode())
        self.assertEqual(interp.eval("set TOP_MODULE"), cgof.TOP)
        self.assertEqual(interp.eval("set ELAB_PARAMETERS"), cgof.parameters()["elab_parameters"])
        self.assertEqual(interp.eval("set CLOCK_PERIOD"), "25.0")
        self.assertEqual(interp.eval("info exists PARAM_POLICY"), "0")
        self.assertEqual(interp.eval("llength $RTL_FILES"), "6")
        self.assertEqual(interp.eval("set EXPECT_FIFO_INSTANCES"), "4")
        self.assertEqual(interp.eval("set EXPECT_OUT_HOLD_INSTANCES"), "1")

    def test_generated_shells_parse_and_formal_tcl_is_complete(self):
        import tkinter
        profile, _ = cgof.base.load_profile(cgof.ROOT / cgof.PROFILE, LIBRARY)
        bash = Path("C:/Program Files/Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")
        self.assertTrue(bash and Path(bash).is_file(), "local bash required for syntax check")
        with tempfile.TemporaryDirectory(prefix="cgof-shell-syntax-") as tmp:
            for name, contents in (
                ("run.sh", cgof.render_dc_pt_runner(LIBRARY, profile)),
                ("formal.sh", cgof.FORMAL_RUNNER.replace("@@INPUTS@@", "'example'").replace(
                    "@@LIBRARY@@", LIBRARY).replace("@@LIBRARY_SHA@@", "a"*64).encode()),
            ):
                script = Path(tmp) / name
                script.write_bytes(contents)
                done = subprocess.run([str(bash), "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)
        interp = tkinter.Tcl()
        formal = cgof.render_formal((cgof.ROOT / cgof.TEMPLATE).read_bytes()).decode()
        self.assertEqual(interp.call("info", "complete", formal), 1)


if __name__ == "__main__":
    unittest.main()
