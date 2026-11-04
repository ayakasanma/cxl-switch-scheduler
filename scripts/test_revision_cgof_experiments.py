"""Pure orchestration/adapter tests. Synthetic records below are not RTL evidence."""
import ast
import asyncio
import copy
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import run_revision_cgof_experiments as cgof


def write_json(path, data):
    path.write_text(json.dumps(data))


def native_fixture(directory):
    hashes = cgof.common.hash_sources(cgof.native.source_paths())
    with zipfile.ZipFile(directory / "sources.zip", "w") as z:
        for name in hashes:
            z.writestr(name, (cgof.ROOT / name).read_bytes())
    (directory / "logs").mkdir()
    (directory / "junit").mkdir()
    steps = []
    for kind, configs in (("lint", cgof.native.lint_configurations()),
                          ("elab_reject", cgof.native.reject_configurations()),
                          ("cocotb", cgof.native.configurations())):
        for cfg in configs:
            suffix = "_seed509" if kind == "cocotb" else ""
            step = dict(kind=kind, name=f"{kind}:{cfg['name']}{suffix}",
                        status="PASS", exit_codes={"verilator": 0},
                        log=f"logs/{kind}_{cfg['name']}.log")
            if kind == "elab_reject":
                step.update(status="XREJECT", exit_codes={"verilator": 1},
                            expect_message=cfg["expect_message"], userfatal_hits=1,
                            unexpected_diagnostics=[], undriven_policy_slot_pins=[],
                            unused_policy_slot_pins=[], reason="")
            if kind == "cocotb":
                step.update(exit_codes=dict(verilate=0, make=0, simulation=0),
                            junit=f"junit/{cfg['name']}.xml")
                xml_fixture(directory / step["junit"], cfg["expect_tests"], seed=509)
            (directory / step["log"]).write_text(step.get("expect_message", "synthetic unit fixture"))
            steps.append(step)
    step = dict(kind="pytest", name="pytest:cgof_runner", status="PASS",
                exit_codes={"pytest": 0}, junit="junit/runner.xml", log="logs/runner.log")
    xml_fixture(directory / step["junit"], cgof.native.runner_test_count())
    (directory / step["log"]).write_text("synthetic runner unit fixture")
    steps.append(step)
    model_log = directory / "logs/model.log"
    model_log.write_text(f"Ran {cgof.unittest.defaultTestLoader.loadTestsFromName(cgof.native.MODEL_TEST_MODULE).countTestCases()} tests in 0.01s\n\nOK\n")
    scope = dict(complete_matrix=True, selected_cases=list(range(len(cgof.native.configurations()))), stable=True, runner_exit=0, exit_code=0,
                 source_hashes_before=hashes, source_hashes_after=hashes,
                 source_archive_sha256=cgof.sha(directory / "sources.zip"),
                 model_unittest=dict(**{"pass": True}, exit=0, tests=cgof.unittest.defaultTestLoader.loadTestsFromName(cgof.native.MODEL_TEST_MODULE).countTestCases(),
                                            log=str(model_log)))
    write_json(directory / "cgof_scope.json", scope)
    summary = dict(overall="PASS", steps=steps)
    write_json(directory / "summary.json", summary)
    return scope, summary


def xml_fixture(path, count, seed=None, skipped=False):
    prop = f'<properties><property name="random_seed" value="{seed}"/></properties>' if seed else ""
    cases = "".join(f'<testcase name="unit{i}">{"<skipped/>" if skipped and i == 0 else ""}</testcase>'
                    for i in range(count))
    path.write_text(f'<testsuite tests="{count}">{prop}{cases}</testsuite>')


def result_fixture():
    job = cgof.select_jobs(None, [509], pilot=True)[0]
    replay = SimpleNamespace(n=4, sha256="e"*64, config={}, generated=[0, 1, 0, 0],
                             ready_count=1, end=1, training=0, phases=("A", "drain"),
                             cohorts=("A",), bounds=(1,))

    def stages(count):
        return {s: dict(histogram={1: 1} if count else {},
                        **(cgof.common.histogram_summary({1: 1}) if count else dict(
                            count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None)))
                for s in cgof.common.STAGES}

    phases = {
        "A": dict(cycles=1, generated=[0, 1, 0, 0], accepted=[0, 1, 0, 0], fired=[0]*4),
        "drain": dict(cycles=1, generated=[0]*4, accepted=[0]*4, fired=[0, 1, 0, 0])}
    for name, row in phases.items():
        row.update(ready=1, offered=list(row["accepted"]), eligible_ready_opportunities=int(name == "drain"),
                   avoidable_bubbles=0, eligible_ready_utilization=1.0 if name == "drain" else None,
                   backlog=[dict(count=1) for _ in range(4)], occupancy=[dict(count=1) for _ in range(4)])
    data = dict(schema=cgof.SCHEMA, evidence_kind="RTL", status="PASS", job=job,
                selected_policy="CGOF(2:1)", params=cgof.parameters(job, "CGOF(2:1)"),
                cold=False, cold_cohort=None, matrix_contribution=0,
                trace_sha256=replay.sha256, trace_config={}, generated_per_source=replay.generated,
                ready_cycles=1, active_cycles=1, training_cycles=0, production_evidence=False,
                sensitivity_evidence=True, outstanding_after_drain=0, producer_backlog_after_drain=0,
                sparse_guard_complete=True, drain_cycles=1, drain_bound=128, real_non_reset_cycles=2,
                generated=1, accepted=1, fired=1, windows=[], peak_rss_kib=2048,
                metrics=dict(phases=phases, cohorts={"A": dict(
                    generated=[0, 1, 0, 0], completed=[0, 1, 0, 0],
                    completed_by_phase={"A": [0]*4, "drain": [0, 1, 0, 0]},
                    per_source=[stages(0), stages(1), stages(0), stages(0)], pooled_sparse=stages(1))}))
    return job, replay, data


class CgofPerformanceTests(unittest.TestCase):
    def test_exact_thirty_original_conditional_identities(self):
        original = [r for r in cgof.common.matrix() if r.get("conditional")]
        selected = cgof.select_jobs("insight-confirmation", list(range(529, 549)))
        selected += cgof.select_jobs("insight-robustness", list(range(509, 514)))
        self.assertEqual(len(selected), 30)
        self.assertEqual({r["id"] for r in selected}, {r["id"] for r in original})
        self.assertEqual(selected, [r for r in original if r["group"] == "insight-confirmation"]
                         + [r for r in original if r["group"] == "insight-robustness"])
        self.assertEqual(sum(r["group"] == "insight-confirmation" for r in selected), 20)
        self.assertEqual(sum(r["group"] == "insight-robustness" for r in selected), 10)
        self.assertTrue(all(r["policy"] == "INSIGHT_WINNER" for r in selected))

    def test_pilot_is_exploration_only_not_a_matrix_row(self):
        pilot = cgof.select_jobs(None, [509], pilot=True)[0]
        self.assertEqual((pilot["window"], pilot["training_cycles"], pilot["seed_role"]),
                         (256, 512, "exploration"))
        self.assertNotIn(pilot["id"], {r["id"] for r in cgof.common.matrix()})
        for seed in (508, 514, 529):
            with self.assertRaises(ValueError):
                cgof.select_jobs(None, [seed], pilot=True)

    def test_selection_refuses_duplicates_unapproved_groups_and_seeds(self):
        for group, seeds in (("n4-confirmation", [529]), ("insight-confirmation", [509]),
                             ("insight-robustness", [529]), ("insight-confirmation", []),
                             ("insight-confirmation", [529, 529])):
            with self.assertRaises(ValueError):
                cgof.select_jobs(group, seeds)
        with self.assertRaises(ValueError):
            cgof.select_jobs("insight-confirmation", [509], pilot=True)

    def test_actual_cgof_parameters_and_ablation_keep_matrix_job_immutable(self):
        job = cgof.select_jobs("insight-confirmation", [529])[0]
        before = copy.deepcopy(job)
        for policy, weight in (("CGOF(2:1)", 2), ("CGOF(1:1)", 1)):
            cfg = cgof.config(job, policy)
            self.assertEqual(cfg["params"], dict(N_SRC=4, DEPTH=16, FAI_W=5_000_000, HIGH_WEIGHT=weight, ELIGIBLE_RR=0))
            self.assertEqual(json.loads(cfg["env"]["CXL_REVISION_JOB"]), before)
            self.assertEqual(cfg["env"]["CXL_CGOF_SELECTED_POLICY"], policy)
            self.assertNotIn("POLICY", cfg["params"])
        self.assertEqual(job, before)
        with self.assertRaises(ValueError):
            cgof.parameters(job, "AGE_ONLY")

    def test_only_adapter_test_selected_even_with_native_imports(self):
        cfg = cgof.config(cgof.select_jobs(None, [509], pilot=True)[0])
        expr = cfg["env"]["COCOTB_TEST_FILTER"]
        self.assertTrue(re.search(expr, "test_cgof_performance.cgof_performance"))
        self.assertFalse(re.search(expr, "test_cgof_sched.test_random"))
        self.assertEqual(cfg["expect_tests"], 1)
        self.assertEqual(cfg["test_module"], "test_cgof_performance")

    def test_transitive_sources_include_native_and_reused_helpers(self):
        paths = set(cgof.source_paths())
        self.assertFalse(set(cgof.common.source_paths()) - paths)
        self.assertFalse(set(cgof.native.source_paths()) - paths)
        self.assertFalse(set(cgof.screen.source_hashes()) - paths)
        for name in ("sim/common/hier_util.py", "sim/experimental/test_cgof_sched.py",
                     "sim/experimental/test_cgof_performance.py", "refc/cxl_model/experimental.py",
                     "scripts/test_revision_cgof_experiments.py"):
            self.assertIn(name, paths)
        self.assertTrue(all((cgof.ROOT / p).is_file() for p in paths))

    def test_zip_rejects_missing_duplicate_and_changed_sources(self):
        for entries in ([("x.py", b"x")], [("x.py", b"bad")], [("y.py", b"x")]):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "sources.zip"
                with zipfile.ZipFile(p, "w") as z:
                    for name, data in entries:
                        z.writestr(name, data)
                hashes = {"x.py": __import__("hashlib").sha256(b"x").hexdigest()}
                if entries == [("x.py", b"x")]:
                    cgof.verify_zip(p, hashes)
                else:
                    with self.assertRaises(ValueError):
                        cgof.verify_zip(p, hashes)

    def test_parent_release_requires_exact_native_gate_and_new_freeze(self):
        good = dict(schema="cxl-cgof-performance-release-v1", native_released=True,
                    parent_correctness_accepted=True, source_hashes={"new.py": "hash"},
                    native_bindings={"native": "n"}, screen_bindings={"screen": "s"})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "release.json"
            write_json(p, good)
            cgof.verify_release(p, good["source_hashes"], good["native_bindings"], good["screen_bindings"])
            for key, value in (("native_released", False), ("parent_correctness_accepted", False),
                               ("source_hashes", {}), ("native_bindings", {}), ("screen_bindings", {})):
                write_json(p, {**good, key: value})
                with self.assertRaises(ValueError):
                    cgof.verify_release(p, good["source_hashes"], good["native_bindings"], good["screen_bindings"])

    def test_screen_gate_rejects_unresolved_wrong_winner_and_changed_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = b"sealed model"
            hashes = {"source.py": __import__("hashlib").sha256(source).hexdigest()}
            with zipfile.ZipFile(directory / "sources.zip", "w") as z:
                z.writestr("source.py", source)
            write_json(directory / "validation.json", [dict(exit_code=0), dict(exit_code=0)])
            gate = dict(status="PASS", frozen_candidate="CGOF(2:1)")
            ingested = []
            for i in range(68):
                report_dir = directory / f"report{i}"
                report_dir.mkdir()
                path = report_dir / "result.json"
                write_json(path, dict(index=i))
                write_json(report_dir / "summary.json", dict(kind="hog" if i < 60 else "feedback"))
                (report_dir / "validation.json").write_text("synthetic fixture")
                (report_dir / "sources.zip").write_bytes(b"synthetic fixture")
                ingested.append(dict(path=str(path), sha256=cgof.sha(path)))
            summary = dict(scope="MODEL_ONLY", kind="evaluate", exit_code=0, validation_exit=0,
                           partial=False, failures=[], source_hashes=hashes,
                           source_archive=dict(file="sources.zip", files=hashes,
                                               sha256=cgof.sha(directory / "sources.zip")),
                           validation_sha256=cgof.sha(directory / "validation.json"),
                           ingested_evidence=ingested, gate=gate)
            path = directory / "summary.json"
            fake_screen = SimpleNamespace(source_hashes=lambda: hashes, load_evidence=lambda p, k: cgof.load(p),
                                          evaluate_gate=lambda h, v, f: gate)
            with patch.object(cgof, "screen", fake_screen):
                write_json(path, summary)
                self.assertTrue(cgof.verify_screen(path))
                for bad in ({**summary, "partial": True},
                            {**summary, "gate": dict(status="PASS", frozen_candidate="CGOF(1:1)")},
                            {**summary, "ingested_evidence": ingested[:-1]}):
                    write_json(path, bad)
                    with self.assertRaises(ValueError):
                        cgof.verify_screen(path)
                write_json(path, summary)
                (directory / "sources.zip").write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    cgof.verify_screen(path)

    def test_pilot_gate_refuses_stale_sources_policy_and_native_acceptance(self):
        good = dict(status="PASS", sensitivity_evidence=True, source_hashes={"x": "h"},
                    selected_policy="CGOF(2:1)", native_bindings={"n": "h"}, screen_bindings={"s": "h"})
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_json(directory / "frozen-spec.json", {})
            for key, value in (("status", "FAIL"), ("source_hashes", {}),
                               ("selected_policy", "CGOF(1:1)"), ("native_bindings", {}),
                               ("screen_bindings", {})):
                write_json(directory / "cgof_performance_scope.json", {**good, key: value})
                with self.assertRaises(ValueError):
                    cgof.verify_pilot(directory, good["source_hashes"], good["native_bindings"],
                                     good["screen_bindings"], "CGOF(2:1)")

    def test_native_full_gate_accepts_expected_rejects_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            native_fixture(directory)
            bindings = cgof.verify_native(directory)
            self.assertIn(str((directory / "cgof_scope.json").resolve()), bindings)
            self.assertIn(str((directory / "junit/runner.xml").resolve()), bindings)

    def test_native_gate_rejects_partial_changed_sources_and_failed_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            good, _ = native_fixture(directory)
            for key, value in (("complete_matrix", False), ("selected_cases", [0]),
                               ("stable", False), ("source_hashes_after", {}), ("exit_code", 1),
                               ("model_unittest", {**good["model_unittest"], "tests": 12})):
                write_json(directory / "cgof_scope.json", {**good, key: value})
                with self.assertRaises(ValueError):
                    cgof.verify_native(directory)

    def test_native_gate_rejects_bad_expected_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            _, good = native_fixture(directory)
            index = next(i for i, s in enumerate(good["steps"]) if s["kind"] == "elab_reject")
            for changes in (dict(status="PASS"), dict(exit_codes={"verilator": 0}),
                            dict(userfatal_hits=0), dict(unexpected_diagnostics=["other error"])):
                bad = copy.deepcopy(good)
                bad["steps"][index].update(changes)
                write_json(directory / "summary.json", bad)
                with self.assertRaises(ValueError):
                    cgof.verify_native(directory)

    def test_native_gate_rejects_raw_junit_skip_and_wrong_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            _, good = native_fixture(directory)
            step = next(s for s in good["steps"] if s["kind"] == "cocotb")
            count = cgof.native.configurations()[0]["expect_tests"]
            for seed, skipped in ((509, True), (510, False)):
                xml_fixture(directory / step["junit"], count, seed=seed, skipped=skipped)
                with self.assertRaises(ValueError):
                    cgof.verify_native(directory)

    def test_native_gate_rejects_missing_exit_and_missing_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            _, good = native_fixture(directory)
            bad = copy.deepcopy(good)
            next(s for s in bad["steps"] if s["kind"] == "cocotb")["exit_codes"].pop("make")
            for summary in (bad, {**good, "steps": good["steps"][1:]}):
                write_json(directory / "summary.json", summary)
                with self.assertRaises(ValueError):
                    cgof.verify_native(directory)

    def test_acceptance_archive_copies_exact_bytes_and_detects_changed_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / "receipt.json"
            source.write_bytes(b"accepted")
            out = directory / "run"
            out.mkdir()
            bindings = dict(release_binding={str(source): cgof.sha(source)})
            cgof.archive_bindings(out, bindings)
            manifest = cgof.load(out / "acceptance/manifest.json")
            self.assertEqual((out / manifest[str(source)]["archived_as"]).read_bytes(), b"accepted")
            source.write_bytes(b"changed")
            other = directory / "other"
            other.mkdir()
            with self.assertRaises(ValueError):
                cgof.archive_bindings(other, bindings)

    def test_result_conservation_utilization_histograms_and_actual_policy(self):
        job, replay, data = result_fixture()
        cgof.validate_result(data, job, "CGOF(2:1)", replay)
        for key, value in (("selected_policy", "CGOF(1:1)"), ("matrix_contribution", 1),
                           ("evidence_kind", "MODEL_ONLY"), ("trace_sha256", "changed"),
                           ("real_non_reset_cycles", 1), ("peak_rss_kib", None), ("fired", 0)):
            bad = {**data, key: value}
            with self.assertRaises(ValueError):
                cgof.validate_result(bad, job, "CGOF(2:1)", replay)
        for phase, key, value in (("drain", "eligible_ready_opportunities", 0),
                                  ("drain", "eligible_ready_utilization", .5),
                                  ("A", "offered", [0]*4),
                                  ("A", "backlog", [dict(count=0)]*4),
                                  ("drain", "fired", [1, 0, 0, 0])):
            bad = copy.deepcopy(data)
            bad["metrics"]["phases"][phase][key] = value
            with self.assertRaises(ValueError):
                cgof.validate_result(bad, job, "CGOF(2:1)", replay)
        bad = copy.deepcopy(data)
        bad["metrics"]["cohorts"]["A"]["pooled_sparse"]["generation_to_fire"]["p99"] = 9
        with self.assertRaises(ValueError):
            cgof.validate_result(bad, job, "CGOF(2:1)", replay)

    def test_cgof1_is_valid_ablation_with_zero_matrix_contribution(self):
        job, replay, data = result_fixture()
        data.update(selected_policy="CGOF(1:1)", params=cgof.parameters(job, "CGOF(1:1)"))
        cgof.validate_result(data, job, "CGOF(1:1)", replay)
        data["matrix_contribution"] = 1
        with self.assertRaises(ValueError):
            cgof.validate_result(data, job, "CGOF(1:1)", replay)

    def test_cli_refuses_unreleased_source_before_any_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "never-created"
            argv = ["--pilot", "--seed", "509", "--screen-summary", "pending",
                    "--native-correctness", "pending", "--release", "pending",
                    "--output", str(out)]
            with self.assertRaises(SystemExit) as exc:
                cgof.main(argv)
            self.assertEqual(exc.exception.code, 2)
            self.assertFalse(out.exists())

    def test_cli_refuses_unreviewed_production(self):
        with self.assertRaises(SystemExit):
            cgof.main(["--group", "insight-confirmation", "--seed", "529", "--source-ready",
                      "--screen-summary", "pending", "--native-correctness", "pending",
                      "--release", "pending", "--output", str(cgof.BASE / "never-created")])
        self.assertFalse((cgof.BASE / "never-created").exists())

    def test_adapter_has_native_cycle_and_no_reimplemented_pin_oracle(self):
        source = (cgof.ROOT / "sim/experimental/test_cgof_performance.py").read_text()
        tree = ast.parse(source)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertTrue(any(isinstance(n.func, ast.Attribute) and n.func.attr == "cycle" for n in calls))
        self.assertFalse(any(isinstance(n.func, ast.Attribute) and n.func.attr in ("commit", "view")
                             for n in calls))
        self.assertNotIn("dut.clk.value", source)
        self.assertNotIn("dut.o_out", source)

    def test_sampled_cycle_uses_returned_preedge_sample(self):
        source = (cgof.ROOT / "sim/experimental/test_cgof_performance.py").read_text()
        tree = ast.parse(source)
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "sampled_cycle")
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "adapter-unit", "exec"), namespace)
        calls = []
        sample = dict(in_ready=3, out_valid=1, out_source=1, out_desc=123, fire=True)

        class Producer:
            def generate(self, k, events):
                calls.append(("generate", k, events))

            def offers(self):
                return {0: (17, 456)}

        class Harness:
            async def cycle(self, push, ready):
                calls.append(("cycle", push, ready))
                return sample

        class Metrics:
            def observe(self, *args):
                calls.append(("observe", *args))

        producer = Producer()
        result = asyncio.run(namespace["sampled_cycle"](Harness(), Metrics(), producer, 18, [(0, 456)], 1))
        self.assertEqual(result, (sample, {0: 456}))
        self.assertEqual(calls, [
            ("generate", 18, [(0, 456)]), ("cycle", {0: 456}, 1),
            ("observe", 18, [(0, 456)], producer, 1, 3, 1, 1, 123)])

    def test_strict_run_failure_is_archived_and_never_passes_scope(self):
        cfg = cgof.config(cgof.select_jobs(None, [509], pilot=True)[0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "input.py").write_text("frozen")
            hashes = cgof.common.hash_sources(["input.py"], root)
            args = SimpleNamespace(output=root / "fresh", pilot=True, selected_policy="CGOF(2:1)",
                                   jobs=1, make_jobs=2, keep_going=False)
            run = cgof.CgofPerformanceRun(args, [cfg], hashes, {})
            original_helpers = cgof.common
            # Patch this new module's boundary, never frozen module globals.
            with patch.object(cgof, "source_paths", return_value=["input.py"]), \
                 patch.object(cgof, "ROOT", root), \
                 patch.object(run, "write_summary", return_value="FAIL"):
                with patch.object(cgof, "common", wraps=original_helpers) as helpers:
                    helpers.hash_sources.side_effect = lambda paths: original_helpers.hash_sources(paths, root)
                    helpers.available_kib.return_value = 100000
                    # Fail in preflight, before invoking the inherited RTL engine.
                    helpers.freeze_sources.side_effect = ValueError("synthetic freeze failure")
                    code = run.execute()
            self.assertEqual(code, 1)
            scope = cgof.load(run.out / "cgof_performance_scope.json")
            self.assertEqual(scope["status"], "FAIL")
            self.assertEqual(scope["matrix_contribution"], 0)
            self.assertIn("synthetic freeze failure", ";".join(scope["problems"]))
            self.assertTrue((run.out / "evidence.zip").is_file())


if __name__ == "__main__":
    unittest.main()
