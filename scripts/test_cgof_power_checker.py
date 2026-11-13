"""Synthetic parser/guard contracts only; these fixtures contain no measured power."""
import copy
import datetime as dt
import gzip
import hashlib
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys
from unittest.mock import patch
import zipfile

import check_cgof_power_replay as checker


def metadata():
    result = checker.cgof.plan(2, 509, "A", 256, 64)
    stats = {}
    for _ in checker.cgof.replay(result, stats):
        pass
    result.update(stats, status="MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN", exit=0,
                  vectors_rows=result["total_cycles"], audit_sha256="a"*64, source_archive_sha256="b"*64,
                  vectors_text_sha256="c"*64, vectors_gzip_sha256="d"*64,
                  profile_canonical_sha256=checker.cgof.trained.legacy.PROFILE_SHA,
                  library_sha256=checker.cgof.DB_SHA, baseline_index_sha256=checker.cgof.inventory.BASELINE_SHA)
    return result


def saif(extra="", clock="(T0 800) (T1 800) (TX 0) (TC 127)"):
    return f"(SAIFILE (TIMESCALE 1 ns) (DURATION 1600) (INSTANCE tb (INSTANCE dut (NET (clk {clock}) {extra}))))"


class ReplayAndActivity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = metadata()
        self.result = self.root / "result.txt"
        self.result.write_text("\n".join(checker.expected_result_v2(self.metadata))+"\n")
        self.activity = self.root / "activity.saif"
        self.activity.write_text(saif())

    def test_fixture_refused_by_production_and_semantics_never_granted(self):
        with self.assertRaisesRegex(ValueError, "not production"):
            checker.check_replay(self.metadata, self.result, self.activity)
        report = checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)
        self.assertEqual(report["method_acceptance"], "NOT_GRANTED_BY_THIS_AUDIT")
        self.assertEqual(report["signal_records"], 1)
        self.assertEqual(report["duration_ns"], "1600")

    def test_metadata_weight_statistics_and_totals_reject_mutations(self):
        with self.assertRaises(ValueError):
            checker.check_metadata(self.metadata, 1, allow_fixture=True)
        for key, value in (("policy_id", 2), ("seed", 512), ("vectors_rows", 0),
                           ("exit", False), ("audit_sha256", "bad"), ("outstanding_at_cut", [0]*4)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                checker.check_metadata(dict(self.metadata, **{key: value}), 2, allow_fixture=True)
        broken = copy.deepcopy(self.metadata)
        broken["warmup"]["fires_per_source"][0] += 1
        with self.assertRaises(ValueError):
            checker.check_metadata(broken, 2, allow_fixture=True)
        self.result.write_text(self.result.read_text()+"extra\n")
        with self.assertRaisesRegex(ValueError, "totals differ"):
            checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)

    def test_all_nets_and_pins_checked_with_constant_x_inventory(self):
        self.activity.write_text(saif("(unused (T0 0) (T1 0) (TX 1600) (TC 0))"))
        report = checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)
        self.assertEqual(report["always_x_paths"], ["unused"])
        for extra in ("(unused (T0 1599) (T1 0) (TX 1) (TC 0))",
                      "(unused (T0 1599) (T1 0) (TX 0) (TZ 1) (TC 0))",
                      "(unused (T0 1599) (T1 0) (TX 0) (TC 0))",
                      "(unused (T0 -1) (T1 1601) (TX 0) (TC 0))",
                      "(unused (T0 1600) (T1 0) (TX 0))",
                      "(unused (T0 1600) (T1 0) (TX 0) (TC 0) (TC 0))",
                      "(unused (T0 1600) (T1 0) (TX 0) (TC 0)) (unused (T0 1600) (T1 0) (TX 0) (TC 0))",
                      "(clk (T0 1600) (T1 0) (TX 0) (TC 0))"):
            self.activity.write_text(saif(extra))
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)

    def test_saif_signal_name_can_match_activity_field(self):
        activity = saif("(TC (T0 1600) (T1 0) (TX 0) (TC 0))")
        self.activity.write_text(activity)
        report = checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)
        self.assertEqual(report["signal_records"], 2)

    def test_synthetic_production_training_closing_contract_and_mutations(self):
        for weight in (1, 2):
            for seed in checker.cgof.SEEDS:
                for arm in ("A", "B"):
                    info = dict(self.metadata, **checker.cgof.plan(weight, seed, arm))
                    info["vectors_rows"] = info["total_cycles"]
                    info["warmup"] = dict(cycles=info["warmup_cycles"], accepted_per_source=[9_999_998, 0, 0, 0],
                                          fires_per_source=[9_999_998, 0, 0, 0])
                    info["measured"] = dict(cycles=info["measured_cycles"], accepted_per_source=[0]*4, fires_per_source=[0]*4)
                    info.update(all=dict(cycles=info["total_cycles"], accepted=9_999_998, fires=9_999_998),
                                outstanding_at_cut=[0]*4, outstanding_at_end=[0]*4, closings=[])
                    old = ["H"]*4
                    for cycle, classes in ((4_999_999, ["B_H", "H", "H", "H"]), (9_999_999, ["L", "H", "H", "H"])):
                        info["closings"].append(dict(cycle=cycle, phase="warmup", window_position=4_999_999,
                            old_classes=old, next_cycle_classes=classes, b_s_index_cleared_after=True,
                            b_close=[4_999_999, 0, 0, 0], pre_edge_b=[4_999_998, 0, 0, 0],
                            s_close=4_999_999, pre_edge_s=4_999_998, closing_fire_source=0,
                            evidence=["DOWN", "UP", "UP", "UP"]))
                        old = classes
                    checker.check_metadata(info, weight)
                    for key, value in (("cycle", 5_000_000), ("old_classes", ["L"]*4),
                            ("evidence", ["KEEP"]*4), ("b_s_index_cleared_after", False),
                            ("closing_fire_source", None), ("pre_edge_s", 0)):
                        broken = copy.deepcopy(info)
                        broken["closings"][0][key] = value
                        with self.subTest(weight=weight, seed=seed, arm=arm, key=key), self.assertRaises(ValueError):
                            checker.check_metadata(broken, weight)

    def test_scope_clock_duration_and_structure_rejected(self):
        for text in (saif().replace("dut", "wrong"), saif()+")", saif()+"(SAIFILE)",
                     saif().replace("DURATION 1600", "DURATION 1601"),
                     saif().replace("TC 127", "TC 126"),
                     saif().replace("TIMESCALE 1 ns", "TIMESCALE 1 ps"),
                     saif().replace("(DURATION 1600)", "(DURATION 1600) (DURATION 1600)"),
                     saif().replace("TX 0", "TX NaN")):
            self.activity.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)

    def test_compute_receipt_expiry_and_exact_host(self):
        path = self.root / "compute.json"
        approval = dict(schema="cxl-fastx-compute-approval-v1", approved_for_long_eda=True,
                        hostname="synthetic-compute", authority="SYNTHETIC TEST ONLY",
                        evidence="No real compute permission", launch_command="synthetic",
                        valid_until_utc="2026-11-08T00:00:00Z")
        now = dt.datetime(2026, 11, 7, tzinfo=dt.timezone.utc)
        path.write_text(json.dumps(approval))
        checker.check_compute(path, hostname="synthetic-compute", now=now)
        for key, value in (("hostname", "other"), ("approved_for_long_eda", 1),
                           ("evidence", ""), ("valid_until_utc", "2026-11-06T00:00:00Z"),
                           ("valid_until_utc", "2026-11-08T00:00:00")):
            path.write_text(json.dumps(dict(approval, **{key: value})))
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                checker.check_compute(path, hostname="synthetic-compute", now=now)

    def test_zero_exit_logs_with_tool_errors_refused(self):
        path = self.root / "compile.log"
        for text in ("", "Error-[SYNTAX] invalid input", "Fatal: failed",
                     "License checkout failed", "EDA_FAILURE: compile"):
            path.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                checker.check_tool_logs(self.root, ("compile",))
        path.write_text("SYNTHETIC clean compiler log\n")
        checker.check_tool_logs(self.root, ("compile",))
        path.write_text('        error "echoed Tcl source"\n')
        checker.check_tool_logs(self.root, ("compile",))


class PayloadBindings(unittest.TestCase):
    def test_isolated_payload_binds_sources_archive_mapping_and_vectors_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory(prefix="cgof-payload-synthetic-") as temporary:
            root = Path(temporary)
            mapping_root = root / "mapped"
            mapping = {}
            for name in checker.cgof.MAPPED_FILES:
                path = mapping_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SYNTHETIC MAPPING ONLY: "+name)
                mapping[name] = checker.sha(path)
            for name in checker.cgof.sources():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(checker.cgof.ROOT / name, path)
            model, database, approval = (root / name for name in ("synthetic-model", "synthetic-db", "compute.json"))
            model.write_text("SYNTHETIC MODEL; NO LIBRARY")
            database.write_text("SYNTHETIC DB; NO LIBRARY")
            approval.write_text(json.dumps(dict(schema="cxl-fastx-compute-approval-v1", approved_for_long_eda=True,
                hostname=checker.socket.getfqdn(), authority="SYNTHETIC TEST ONLY",
                evidence="No real compute permission", launch_command="synthetic", valid_until_utc="2099-01-01T00:00:00Z")))
            baseline = b"SYNTHETIC BASELINE RECEIPT"
            baseline_sha = hashlib.sha256(baseline).hexdigest()
            original_contract = checker.check_metadata
            def fixture_contract(value, weight):
                return original_contract(value, weight, allow_fixture=True)
            with patch.object(checker.cgof, "ROOT", root), \
                    patch.object(checker.cgof, "DB_SHA", checker.sha(database)), \
                    patch.object(checker, "CELL_MODEL_SHA", checker.sha(model)), \
                    patch.object(checker.cgof.inventory, "BASELINE_SHA", baseline_sha), \
                    patch.dict(checker.cgof.MAPPING_PINS, {2: tuple(mapping[name] for name in checker.cgof.MAPPED_FILES[4:6])}), \
                    patch.object(checker, "check_metadata", side_effect=fixture_contract):
                info = metadata()
                info.update(source_sha256=checker.cgof.sources(), mapping=dict(files=mapping))
                files = {name: (root / name).read_bytes() for name in info["source_sha256"]}
                files.update({"mapped/"+name: (mapping_root / name).read_bytes() for name in mapping})
                files["baseline-acceptance.json"] = baseline
                info["archive_files"] = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
                with zipfile.ZipFile(root / "source-freeze.zip", "x") as archive:
                    for name, data in files.items():
                        archive.writestr(name, data)
                content = (checker.cgof.trained.header(info)+"\n").encode("ascii")
                (root / "vectors.txt.gz").write_bytes(gzip.compress(content))
                (root / "audit.json").write_text(json.dumps(dict(status="MODEL_AND_INDEPENDENT_CREDIT_LEDGER_CHECKED_NOT_RTL_OR_POWER",
                    rows=info["total_cycles"], power_status="NOT_RUN")))
                for key, name in (("audit_sha256", "audit.json"), ("source_archive_sha256", "source-freeze.zip"),
                                  ("vectors_gzip_sha256", "vectors.txt.gz")):
                    info[key] = checker.sha(root / name)
                info["vectors_text_sha256"] = hashlib.sha256(content).hexdigest()
                info["trace"]["sha256"] = checker.cgof.TRACE_PINS["509-A"]
                (root / "metadata.json").write_text(json.dumps(info))
                result = checker.check_payload(root, mapping_root, 2, model, database, approval, root / "vectors.txt")
                self.assertEqual(result["power_status"], "NOT_RUN")
                self.assertEqual((root / "vectors.txt").read_bytes(), content)
                self.assertIn(str(model.resolve()), result["file_sha256"])
                for path in (root / "scripts/run_cgof_power_pilot.sh", mapping_root / checker.cgof.MAPPED_FILES[4],
                             root / "source-freeze.zip", root / "vectors.txt.gz", root / "audit.json"):
                    saved = path.read_bytes()
                    path.write_bytes(saved+b"TAMPER")
                    with self.subTest(path=path.name), self.assertRaises(ValueError):
                        checker.check_payload(root, mapping_root, 2, model, database, approval, root / "refused.txt")
                    path.write_bytes(saved)
                    self.assertFalse((root / "refused.txt").exists())


class PowerReports(unittest.TestCase):
    setUp = ReplayAndActivity.setUp

    def test_units_components_hierarchy_clock_and_coverage(self):
        for name in ("design.rpt", "library.rpt", "clocks.rpt", "units.rpt", "saif-read.rpt",
                     "check-power.rpt", "update-power.rpt", "disable-timing.rpt", "switching-coverage.rpt",
                     "not-annotated.rpt", "annotated.rpt", "power.rpt", "power-hierarchy.rpt",
                     "registers-and-clock-pins.rpt", "pilot-status.rpt", "pt.log", "compile.log", "sim.log"):
            (self.root / name).write_text("SYNTHETIC TEST ONLY\n")
        (self.root / "check-power.rpt").write_text(
            "Information: Checking 'out_of_table_range'.\nInformation: Checking 'missing_table'.\n"
            "Information: Checking 'missing_function'.\ncheck_power succeeded.\n1\n")
        (self.root / "saif-read.rpt").write_text("Total number of nets = 2\nNumber of annotated nets = 2\n"
            "Total number of leaf cells = 2\nNumber of fully annotated leaf cells = 1\n")
        (self.root / "units.rpt").write_text("Time_unit : 1e-09 Second\n")
        (self.root / "clocks.rpt").write_text("core_clk 25.00 {0 12.5} {clk}\n")
        (self.root / "library.rpt").write_text("profile="+self.metadata["profile_canonical_sha256"])
        power = ("Dynamic Power Units = 1 W\nLeakage Power Units = 1 W\nTime Units = 1 ns\n"
                 "tt0p78v25c ForQA Wire Load Model Mode: top\nCell Internal Power = 1.000e-3\n"
                 "Net Switching Power = 2.000e-3\nCell Leakage Power = 3.000e-3\nTotal Power = 6.000e-3\n")
        (self.root / "power.rpt").write_text(power)
        (self.root / "power-hierarchy.rpt").write_text("cgof_unit_top 1.000e-3 2.000e-3 3.000e-3 6.000e-3\n")
        clock = 'register_count=1\nclock_pin=ff/CLK nets=clk activity={"ff/CLK" 0.079375 file}\n'
        (self.root / "registers-and-clock-pins.rpt").write_text(clock)
        replay = checker.check_replay(self.metadata, self.result, self.activity, allow_fixture=True)
        report = checker.check_power(self.root, self.metadata, replay)
        self.assertEqual(Decimal(report["power_W"]["total"]), Decimal(".006"))
        self.assertEqual(report["method_acceptance"], "NOT_GRANTED_BY_THIS_AUDIT")
        for filename, old, new in (("power.rpt", "1 W", "1 mW"),
                ("power.rpt", "6.000e-3", "9.000e-3"),
                ("power-hierarchy.rpt", "cgof_unit_top", "switch_top"),
                ("registers-and-clock-pins.rpt", "file", "default"),
                ("registers-and-clock-pins.rpt", "0.079375", "0.079374"),
                ("saif-read.rpt", "annotated nets = 2", "annotated nets = 3")):
            path = self.root / filename
            original = path.read_text()
            path.write_text(original.replace(old, new))
            with self.subTest(filename=filename, old=old), self.assertRaises(ValueError):
                checker.check_power(self.root, self.metadata, replay)
            path.write_text(original)


@unittest.skipUnless(sys.platform == "linux" and shutil.which("bash"), "Linux shell required")
class RunnerGuards(unittest.TestCase):
    def test_missing_compute_and_fixture_rejected_before_eda_and_rerun_refused(self):
        with tempfile.TemporaryDirectory(prefix="cgof-pilot-guard-") as temporary:
            root = Path(temporary)
            for name in checker.cgof.sources():
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(checker.cgof.ROOT / name, destination)
            (root / "metadata.json").write_text(json.dumps(metadata()))
            (root / "vectors.txt.gz").write_bytes(b"")
            approval = dict(schema="cxl-fastx-compute-approval-v1", approved_for_long_eda=True,
                hostname=checker.socket.getfqdn(), authority="SYNTHETIC TEST ONLY",
                evidence="No real permission; fixture guard must stop before tools",
                launch_command="synthetic", valid_until_utc="2099-01-01T00:00:00Z")
            for label, contents in (("missing", None), ("fixture", approval)):
                case = root / label
                case.mkdir()
                for name in ("metadata.json", "vectors.txt.gz"):
                    shutil.copyfile(root / name, case / name)
                shutil.copytree(root / "scripts", case / "scripts")
                shutil.copytree(root / "refc", case / "refc")
                shutil.copytree(root / "sim", case / "sim")
                if contents is not None:
                    (case / "approval.json").write_text(json.dumps(contents))
                command = ["bash", str(case / "scripts/run_cgof_power_pilot.sh"),
                           "/missing-mapped-case", "2", "/missing-model", "/missing-db", str(case / "approval.json")]
                result = subprocess.run(command, cwd=case, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                payload_log = case / "execution/reports/payload.log"
                expected = "No such file" if contents is None else "not production power evidence"
                self.assertIn(expected, payload_log.read_text())
                self.assertFalse((case / "execution/reports/compile.log").exists())
                before = payload_log.read_bytes()
                result = subprocess.run(command, cwd=case, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(payload_log.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
