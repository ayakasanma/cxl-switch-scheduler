"""Runner gates and source archive checks; no RTL evidence is generated here."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from run_revision_experiments import (
    BASE, RevisionRun, check_steps, config, freeze_sources, hash_sources, main, matrix, parameters, select_jobs,
    source_paths, validate_result,
)
from revision_traffic import STAGES
from revision_statistics import histogram_summary


class RunnerTests(unittest.TestCase):
    def test_build_directory_uses_existing_runner_cache_convention(self):
        BASE.mkdir(parents=True, exist_ok=True)
        for configured in ("", "/tmp/cxl-owned-build-cache"):
            with tempfile.TemporaryDirectory(dir=BASE) as tmp:
                args = SimpleNamespace(output=Path(tmp) / "fresh")
                with patch.dict(os.environ, CXL_BUILD_ROOT=configured):
                    run = RevisionRun(args, [])
                cache = Path(configured or "~/.cache/cxl-scheduler/build").expanduser()
                self.assertEqual(run.build_root, cache / "revision-performance" / "fresh")
                self.assertNotEqual(run.build_root, run.out / "build")

    def test_pilot_six_policies_and_exact_parameters(self):
        rows = select_jobs(None, [509], pilot=True)
        self.assertEqual({r["policy"] for r in rows}, {"FCFS", "RR1", "RR10", "MAIN", "ALG2", "BLISS"})
        self.assertEqual(len(rows), 6)
        for row in rows:
            cfg = config(row)
            self.assertEqual(set(cfg["params"]), {"N_SRC", "POLICY", "DEPTH", "RR_QUANTUM", "FAI_W", "HIGH_QUOTA", "MAIN_1W"})
            self.assertEqual(cfg["params"]["FAI_W"], 256)
            self.assertEqual(cfg["seeds"], [509])
            self.assertEqual(json.loads(cfg["env"]["CXL_REVISION_JOB"]), row)

    def test_all_unconditional_rtl_rows_configure(self):
        for row in matrix():
            if row["evidence_kind"] == "RTL_REQUIRED" and not row.get("conditional"):
                cfg = config(row)
                self.assertEqual(parameters(row), cfg["params"])
                self.assertEqual(cfg["params"]["MAIN_1W"], int(row["policy"] == "MAIN1W"))

    def test_explicit_selection_and_rejections(self):
        self.assertEqual(len(select_jobs("n4-confirmation", [529])), 6)
        self.assertEqual(len(select_jobs("depth", [509])), 9)
        self.assertEqual(len(select_jobs("rr-quantum", [509])), 5)
        for group, seeds in (("n4-confirmation", [509]), ("unknown", [509]), ("depth", [509, 509]),
                             ("matched-power", [509]), ("insight-confirmation", [529])):
            with self.assertRaises(ValueError):
                select_jobs(group, seeds)
        with self.assertRaises(ValueError):
            select_jobs("depth", [509], policies=["BLISS"])
        for seed in (508, 514, 529):
            with self.assertRaises(ValueError):
                select_jobs(None, [seed], pilot=True)

    def test_cold_lanes_are_independent_and_explicit(self):
        row = select_jobs(None, [509], pilot=True)[0]
        for cohort in ("A", "B"):
            cfg = config(row, cohort)
            self.assertTrue(cfg["name"].endswith("-cold"+cohort))
            self.assertEqual(json.loads(cfg["env"]["CXL_REVISION_COLD"]), cohort)
        for cold in (True, "AB"):
            with self.assertRaisesRegex(ValueError, "independent A or B"):
                config(row, cold)

    def test_n16_resource_pilot_and_expansion_filter(self):
        rows = select_jobs(None, [509], pilot=True, policies=["FCFS", "MAIN", "BLISS"], n_src=16)
        self.assertEqual(len(rows), 3)
        self.assertEqual({parameters(r)["N_SRC"] for r in rows}, {16})
        self.assertEqual(len(select_jobs("n-expansion", [509], n_src=16)), 6)
        with self.assertRaises(ValueError):
            select_jobs("n4-confirmation", [529], n_src=16)

    def test_missing_duplicate_failed_notrun_never_pass(self):
        cfg = config(select_jobs(None, [509], pilot=True)[0])
        good = [dict(kind="cocotb", name=f"cocotb:{cfg['name']}_seed509", status="PASS",
                     exit_codes=dict(verilate=0, make=0, simulation=0), tests=1),
                dict(kind="lint", name=f"lint:{cfg['name']}", status="PASS", exit_codes=dict(verilator=0)),
                dict(kind="pytest", name="pytest:units", status="PASS", exit_codes=dict(pytest=0), tests=2)]
        check_steps([cfg], good)
        bad_cases = [good[1:], good+[good[0]], good[:1]+good[2:], good[:2]]
        for changes in (dict(status="NOT_RUN"), dict(status="FAIL"), dict(tests=0),
                        dict(exit_codes=dict(simulation=1)), dict(exit_codes={}), dict(skipped=1)):
            bad_cases.append([dict(good[0], **changes)]+good[1:])
        for bad in bad_cases:
            with self.assertRaises(ValueError):
                check_steps([cfg], bad)

    def test_archive_contains_exact_bytes_and_is_immutable(self):
        BASE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BASE) as tmp:
            root = Path(tmp)
            (root / "input.py").write_bytes(b"exact bytes\r\n")
            context = root / "docs/experiments/revision-20261023/EXECUTION.md"
            context.parent.mkdir(parents=True)
            context.write_text("progress before")
            out = root / "out"
            out.mkdir()
            before = freeze_sources(out, ["input.py"], root)
            self.assertEqual(before, hash_sources(["input.py"], root))
            with zipfile.ZipFile(out / "sources.zip") as archive:
                self.assertEqual(archive.read("input.py"), b"exact bytes\r\n")
                self.assertEqual(archive.read("context/EXECUTION.md"), b"progress before")
            context.write_text("progress after")
            self.assertEqual(before, hash_sources(["input.py"], root))
            with self.assertRaises(FileExistsError):
                freeze_sources(out, ["input.py"], root)
            (root / "input.py").write_bytes(b"changed")
            self.assertNotEqual(before, hash_sources(["input.py"], root))

    def test_source_archive_includes_native_hierarchy_helper(self):
        paths = source_paths()
        self.assertIn("sim/common/hier_util.py", paths)
        BASE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BASE) as tmp:
            hashes = freeze_sources(tmp, paths)
            with zipfile.ZipFile(Path(tmp) / "sources.zip") as archive:
                self.assertEqual(set(paths), set(hashes))
                self.assertEqual(archive.read("sim/common/hier_util.py"),
                                 (Path(__file__).resolve().parents[1] / "sim/common/hier_util.py").read_bytes())

    def test_isolated_files_do_not_enter_runtime_freeze(self):
        BASE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BASE) as tmp:
            root = Path(tmp)
            filelist = root / "rtl/experimental/filelist.f"
            filelist.parent.mkdir(parents=True)
            filelist.write_text("rtl/experimental/switch_experiment_top.sv\n")
            before = source_paths(root)
            for name in ("sim/common/isolated_dac.py", "refc/cxl_model/isolated_dac.py",
                         "rtl/experimental/cxl_cgof_sched.sv"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("isolated")
            self.assertEqual(source_paths(root), before)
            self.assertIn("sim/common/traffic_trace.py", before)
            self.assertNotIn("sim/common/fifo_tb.py", before)

    def test_no_default_or_unreviewed_production_launch(self):
        for argv in ([], ["--group", "depth", "--seed", "509", "--output", str(BASE / "must-not-exist")],
                     ["--group", "depth", "--seed", "509", "--output", str(BASE / "must-not-exist"), "--source-ready"]):
            with self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2)
        self.assertFalse((BASE / "must-not-exist").exists())

    def test_result_gate_checks_actual_counts_histograms_and_rtl_label(self):
        row = select_jobs(None, [509], pilot=True)[0]
        replay = SimpleNamespace(n=4, sha256="e"*64, config={}, generated=[0, 1, 0, 0],
                                 ready_count=1, end=1, training=0, phases=("A", "drain"), cohorts=("A",),
                                 bounds=(1,))
        def stages(count):
            return {s: dict(histogram={1: 1} if count else {},
                            **(histogram_summary({1: 1}) if count else
                               dict(count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None)))
                    for s in STAGES}
        data = dict(schema="cxl-revision-performance-v1", evidence_kind="RTL", status="PASS",
                    job=row, params=parameters(row), cold=False, cold_cohort=None,
                    trace_sha256=replay.sha256, trace_config={}, generated_per_source=[0, 1, 0, 0],
                    ready_cycles=1, active_cycles=1, training_cycles=0, production_evidence=False,
                    sensitivity_evidence=True, outstanding_after_drain=0, producer_backlog_after_drain=0,
                    sparse_guard_complete=True, drain_cycles=1, drain_bound=128, real_non_reset_cycles=2,
                    generated=1, accepted=1, fired=1, windows=[],
                    metrics=dict(phases={
                        "A": dict(cycles=1, generated=[0, 1, 0, 0], accepted=[0, 1, 0, 0], fired=[0]*4),
                        "drain": dict(cycles=1, generated=[0]*4, accepted=[0]*4, fired=[0, 1, 0, 0])},
                        cohorts={"A": dict(generated=[0, 1, 0, 0], completed=[0, 1, 0, 0],
                                           completed_by_phase={"A": [0]*4, "drain": [0, 1, 0, 0]},
                                           per_source=[stages(0), stages(1), stages(0), stages(0)],
                                           pooled_sparse=stages(1))}))
        for phase, pr in data["metrics"]["phases"].items():
            pr.update(ready=1, offered=list(pr["accepted"]),
                      eligible_ready_opportunities=int(phase == "drain"), avoidable_bubbles=0,
                      eligible_ready_utilization=1.0 if phase == "drain" else None,
                      backlog=[dict(count=1) for _ in range(4)],
                      occupancy=[dict(count=1) for _ in range(4)])
        validate_result(data, row, False, replay)
        cases = []
        for key, value in (("evidence_kind", "MODEL"), ("status", "NOT_RUN"),
                           ("trace_sha256", "wrong"), ("fired", 0), ("real_non_reset_cycles", 1)):
            cases.append(dict(data, **{key: value}))
        bad = copy.deepcopy(data)
        bad["metrics"]["cohorts"]["A"]["per_source"][1]["generation_to_fire"]["p99"] = 9
        cases.append(bad)
        bad = copy.deepcopy(data)
        del bad["metrics"]["phases"]["drain"]
        cases.append(bad)
        for phase, key, value in (
            ("drain", "eligible_ready_opportunities", 0),
            ("drain", "avoidable_bubbles", 1),
            ("drain", "eligible_ready_utilization", .5),
            ("A", "eligible_ready_utilization", 0),
            ("A", "offered", [0]*4),
            ("A", "backlog", [dict(count=0)]*4),
            ("drain", "fired", [1, 0, 0, 0]),
        ):
            bad = copy.deepcopy(data)
            bad["metrics"]["phases"][phase][key] = value
            cases.append(bad)
        for bad in cases:
            with self.assertRaises(ValueError):
                validate_result(bad, row, False, replay)

        # Under static permutation source0 is sparse even in the training cold cohort.
        permuted = copy.deepcopy(data)
        permuted_row = dict(row, heavy_source=3)
        permuted["job"] = permuted_row
        permuted["generated_per_source"] = [1, 0, 0, 0]
        for phase in permuted["metrics"]["phases"].values():
            for key in ("generated", "offered", "accepted", "fired"):
                phase[key][0], phase[key][1] = phase[key][1], phase[key][0]
        cohort = permuted["metrics"]["cohorts"].pop("A")
        permuted["metrics"]["cohorts"]["cold"] = cohort
        for values in (cohort["generated"], cohort["completed"], cohort["per_source"],
                       *cohort["completed_by_phase"].values()):
            values[0], values[1] = values[1], values[0]
        permuted_replay = SimpleNamespace(**{**vars(replay), "generated": [1, 0, 0, 0], "cohorts": ("cold",)})
        validate_result(permuted, permuted_row, False, permuted_replay)
        cohort["pooled_sparse"] = stages(0)
        with self.assertRaisesRegex(ValueError, "sparse pooling"):
            validate_result(permuted, permuted_row, False, permuted_replay)


if __name__ == "__main__":
    unittest.main()
