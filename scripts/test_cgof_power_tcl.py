"""Run actual Tcl configuration guards without invoking commercial EDA commands."""
from pathlib import Path
import tempfile
import unittest

try:
    import tkinter
except ImportError:
    tkinter = None

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d"


@unittest.skipIf(tkinter is None, "Python Tcl binding unavailable")
class PowerConfigurationGuards(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("test.db", "netlist.v", "design.sdc", "activity.saif"):
            (self.root / name).write_text("synthetic guard input", encoding="utf-8")
        self.configuration = dict(
            PROFILE_SHA256=PROFILE, PROFILE_STATUS="FROZEN", CLOCK_PERIOD=25.0,
            WIRE_LOAD_METHOD="fixed_model", WIRE_LOAD_MODEL="ForQA", WIRE_LOAD_MODE="top",
            PARAM_FAI_W=5000000, PARAM_N_SRC=4, TOP_MODULE="cgof_unit_top", POLICY_NAME="CGOF",
            PARAM_DEPTH=16, PARAM_HIGH_WEIGHT=1,
            ELAB_PARAMETERS="N_SRC=4,DEPTH=16,FAI_W=5000000,HIGH_WEIGHT=1",
            TARGET_LIBRARY=(self.root / "test.db").as_posix(),
            NETLIST_FILE="netlist.v", SDC_FILE="design.sdc")

    def guard(self, configuration=None, weight=1, policy="CGOF", n_src=4):
        configuration = configuration or self.configuration
        interpreter = tkinter.Tcl()
        text = (ROOT / "sta/power_pt.tcl").read_text(encoding="utf-8")
        interpreter.eval(text.rsplit("if {[catch {power_main}", 1)[0])
        interpreter.eval("proc set_app_var {args} {error TEST_REACHED_EDA_BOUNDARY}")
        values = dict(POWER_CASE_ROOT=self.root.as_posix(),
                      POWER_REPORT_DIR=self.root.as_posix(), POWER_N=n_src, POWER_POLICY=policy,
                      POWER_DB=(self.root / "test.db").as_posix(),
                      POWER_SAIF=(self.root / "activity.saif").as_posix())
        if weight is not None:
            values["POWER_HIGH_WEIGHT"] = weight
        else:
            interpreter.eval("unset -nocomplain ::env(POWER_HIGH_WEIGHT)")
        for key, value in values.items():
            interpreter.setvar("env(" + key + ")", str(value))
        (self.root / "run_config.tcl").write_text(
            "".join("set " + key + " {" + str(value) + "}\n" for key, value in configuration.items()),
            encoding="utf-8")
        try:
            interpreter.call("power_main")
        except tkinter.TclError as exc:
            return str(exc)
        self.fail("mock EDA boundary was not reached")

    def test_cgof_accepts_exact_weights_without_rr_quantum(self):
        for weight in (1, 2):
            configuration = dict(self.configuration, PARAM_HIGH_WEIGHT=weight,
                                 ELAB_PARAMETERS=f"N_SRC=4,DEPTH=16,FAI_W=5000000,HIGH_WEIGHT={weight}")
            self.assertEqual(self.guard(configuration, weight), "TEST_REACHED_EDA_BOUNDARY")

    def test_cgof_rejects_wrong_missing_or_unapproved_weights(self):
        for weight in (None, 2, 3):
            self.assertIn("unsupported/unfrozen CGOF", self.guard(weight=weight))

    def test_cgof_rejects_parameter_or_profile_drift(self):
        for key, value in (("PARAM_N_SRC", 8), ("PARAM_DEPTH", 8), ("PARAM_FAI_W", 256),
                           ("PROFILE_STATUS", "PILOT"), ("CLOCK_PERIOD", 20),
                           ("ELAB_PARAMETERS", "N_SRC=4,DEPTH=16,FAI_W=5000000,HIGH_WEIGHT=1,ELIGIBLE_RR=1")):
            with self.subTest(key=key):
                self.assertIn("unsupported/unfrozen", self.guard(dict(self.configuration, **{key: value})))

    def test_baseline_policy_and_quantum_guards_remain(self):
        for policy in ("fcfs", "rr", "fai-main"):
            for n_src in (4, 8, 16):
                configuration = dict(self.configuration, TOP_MODULE="switch_top", POLICY_NAME=policy,
                                     PARAM_N_SRC=n_src, PARAM_RR_QUANTUM=10)
                self.assertEqual(self.guard(configuration, policy=policy, n_src=n_src),
                                 "TEST_REACHED_EDA_BOUNDARY")
                configuration["PARAM_RR_QUANTUM"] = 1
                self.assertIn("unsupported/unfrozen", self.guard(configuration, policy=policy, n_src=n_src))

    def test_unknown_top_is_rejected(self):
        self.assertIn("unsupported top", self.guard(dict(self.configuration, TOP_MODULE="unknown_top")))


if __name__ == "__main__":
    unittest.main()
