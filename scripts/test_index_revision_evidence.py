"""Small sealed fixtures exercise acceptance and fail-closed evidence boundaries."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
import zipfile
from unittest import mock

import index_revision_evidence as ix


class EvidenceIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.row = next(r for r in ix.current_matrix() if r["evidence_kind"] == "RTL_REQUIRED"
                        and r["group"] != "adaptation")

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def seal(self, path):
        archive = path / "evidence.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "x") as stream:
            for item in ix._bundle_files(path):
                stream.write(item, item.relative_to(path).as_posix())

    def bundle(self, lane="trained"):
        path = self.root / lane
        path.mkdir()
        cfg = ix.expected_config(self.row, lane)
        sources = {
            "rtl/experimental/filelist.f": b"rtl/experimental/top.sv\n",
            "rtl/experimental/top.sv": b"module top; endmodule\n",
            "scripts/revision_matrix.py": b"# frozen fixture\n",
            "scripts/run_revision_experiments.py": b"# frozen fixture\n",
            "scripts/run_verify.py": b"# frozen fixture\n",
            "sim/experimental/revision_traffic.py": b"# frozen fixture\n",
            "sim/experimental/test_revision_performance.py": b"# frozen fixture\n",
            "refc/cxl_model/revision_baselines.py": b"# frozen fixture\n",
        }
        hashes = {name: ix.sha256_bytes(data) for name, data in sources.items()}
        with zipfile.ZipFile(path / "sources.zip", "x") as stream:
            for name, data in sources.items():
                stream.writestr(name, data)
        self.write(path / "source_hashes_before.json", hashes)
        self.write(path / "source_hashes_after.json", hashes)
        self.write(path / "frozen-spec.json",
                   dict(schema=ix.RUN_SPEC_SCHEMA, pilot=False,
                        production_review_acknowledged=True, configs=[cfg],
                        jobs_sha256=ix.canonical_sha([cfg]), source_sha256=ix.canonical_sha(hashes)))
        result = dict(schema=ix.PERFORMANCE_SCHEMA, evidence_kind="RTL", status="PASS",
                      job=self.row, params=ix.expected_params(self.row),
                      cold=bool(ix.lane_cold(lane)), cold_cohort=ix.lane_cold(lane) or None,
                      training_cycles=ix.lane_training(self.row, lane),
                      production_evidence=True, sensitivity_evidence=False,
                      trace_sha256="a" * 64, metrics={}, windows=[])
        rel = ix.expected_result_path(cfg, self.row)
        self.write(path / rel, result)
        name = f"{cfg['name']}_seed{self.row['seed']}"
        self.write(path / "revision_scope.json",
                   dict(schema=ix.SCOPE_SCHEMA, status="PASS", production_evidence=True,
                        sensitivity_evidence=False, expected_jobs=1, valid_jobs=1,
                        source_hashes=hashes, problems=[],
                        runs=[dict(name=name, result=rel, trace_sha256="a" * 64,
                                   n_src=self.row["n_src"], policy=self.row["policy"])]))
        steps = [dict(name=f"lint:{cfg['name']}", kind="lint", status="PASS",
                      exit_codes={"lint": 0}),
                 dict(name=f"cocotb:{name}", kind="cocotb", status="PASS",
                      exit_codes={"sim": 0}, tests=1),
                 dict(name="pytest:native", kind="pytest", status="PASS",
                      exit_codes={"pytest": 0}, tests=1),
                 dict(name="scope:revision-performance", kind="scope", status="PASS")]
        self.write(path / "summary.json",
                   dict(overall="PASS", scope="selected-production-subset", production_evidence=True,
                        sensitivity_evidence=False, milestone_acceptance_scope=True,
                        full_498_matrix_executed=False,
                        counts={"fail": 0, "not_run": 0}, expected_jobs=1, steps=steps))
        self.seal(path)
        return path

    def inspect(self, path):
        return ix.inspect_performance_bundle(path, {self.row["id"]: self.row})

    def mutate(self, path, filename, change):
        value = ix.load_json(path / filename)
        change(value)
        self.write(path / filename, value)
        self.seal(path)

    def test_trained_completes_row_cold_is_separate(self):
        paths = [self.bundle(lane) for lane in ix.LANES]
        self.assertEqual(self.inspect(paths[0])["status"], "PASS")
        trained = ix.build_index(paths[:1])
        self.assertEqual(trained["matrix"]["rows"][self.row["id"]]["status"], "PASS")
        full = ix.build_index(paths)
        rec = full["matrix"]["rows"][self.row["id"]]
        self.assertEqual(rec["status"], "PASS")
        self.assertEqual(rec["evidence"][0]["bundle"], str(paths[0]))
        self.assertEqual(rec["expected_lanes"], ["trained"])
        self.assertEqual(len(rec["optional_lane_evidence"]), 2)
        self.assertEqual(ix.build_index(paths[1:])["matrix"]["rows"][self.row["id"]]["status"],
                         "NOT_RUN")
        self.mutate(paths[1], "summary.json", lambda v: v.update(overall="FAIL"))
        self.assertEqual(ix.build_index(paths)["matrix"]["rows"][self.row["id"]]["status"],
                         "PASS")
        self.assertEqual(sum(full["matrix"]["counts"].values()), 498)
        self.assertEqual(set(full["matrix"]["counts"]), set(ix.STATUSES))

    def test_n4_is_120_declared_runs_and_adaptation_is_continuous(self):
        rows = ix.current_matrix()
        n4 = [r for r in rows if r["group"] == "n4-confirmation"]
        self.assertEqual(len(n4), 120)
        self.assertEqual(sum(len(ix.expected_lanes(r)) for r in n4), 120)
        self.assertTrue(all(r["training_cycles"] == 10_000_000
                            and r["cohorts"] == ["A", "B"] for r in n4))
        for row in rows:
            if row["group"] == "adaptation":
                self.assertEqual(ix.expected_lanes(row), ("trained",))
                self.assertEqual(row["training_cycles"], 0)
                self.assertEqual(row["measured_cycles"], 30_000_000)

    def test_real_boolean_cold_a_b_acceptance_keeps_core_trained_separate(self):
        paths = [self.bundle(lane) for lane in ("cold-A", "cold-B")]
        for path, cohort in zip(paths, ("A", "B")):
            inspected = self.inspect(path)
            self.assertEqual(inspected["status"], "PASS", inspected["failures"])
            self.assertEqual(inspected["runs"][0]["lane"], f"cold-{cohort}")
            result = ix.load_json(path / inspected["runs"][0]["result"])
            self.assertIs(result["cold"], True)
            self.assertEqual(result["cold_cohort"], cohort)
            self.assertEqual(result["training_cycles"], 0)
        index = ix.build_index(paths)
        self.assertEqual(len(index["performance"]["accepted_records"]), 2)
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 498)
        row = index["matrix"]["rows"][self.row["id"]]
        self.assertEqual(row["expected_lanes"], ["trained"])
        self.assertEqual(row["missing_lanes"], ["trained"])
        self.assertEqual(len(row["optional_lane_evidence"]), 2)
        trained = self.bundle()
        index = ix.build_index([trained, *paths])
        self.assertEqual(index["matrix"]["counts"]["PASS"], 1)
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 497)
        self.assertEqual(index["matrix"]["completion"]["planned"], 498)
        self.assertEqual(index["matrix"]["by_group"]["n4-confirmation"]["planned"], 120)

    def test_cold_boolean_cohort_and_training_mismatches_rejected(self):
        path = self.bundle("cold-A")
        rel = self.inspect(path)["runs"][0]["result"]
        result = ix.load_json(path / rel)
        for field, value in [("cold", "A"), ("cold", 1), ("cold", False),
                             ("cold_cohort", "B"), ("training_cycles", 10_000_000)]:
            with self.subTest(field=field, value=value):
                self.write(path / rel, dict(result, **{field: value}))
                self.seal(path)
                self.assertEqual(self.inspect(path)["status"], "FAIL")

    def test_complete_selected_production_bundle_passes_only_declared_row(self):
        path = self.bundle()
        index = ix.build_index([path])
        self.assertEqual(self.inspect(path)["status"], "PASS")
        self.assertEqual(index["matrix"]["rows"][self.row["id"]]["status"], "PASS")
        self.assertEqual(index["matrix"]["counts"]["PASS"], 1)
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 497)
        self.assertFalse(index["matrix"]["completion"]["complete"])
        self.assertEqual(len(index["performance"]["accepted_records"]), 1)

    def test_selected_scope_cannot_hide_incomplete_or_false_claims(self):
        path = self.bundle()
        summary = ix.load_json(path / "summary.json")
        for field, value in [("milestone_acceptance_scope", False),
                             ("production_evidence", False),
                             ("full_498_matrix_executed", True),
                             ("expected_jobs", 2), ("scope", "W256-sensitivity")]:
            with self.subTest(field=field):
                changed = dict(summary, **{field: value})
                self.write(path / "summary.json", changed)
                self.seal(path)
                self.assertNotEqual(self.inspect(path)["status"], "PASS")
        missing = dict(summary)
        del missing["milestone_acceptance_scope"]
        self.write(path / "summary.json", missing)
        self.seal(path)
        self.assertNotEqual(self.inspect(path)["status"], "PASS")
        self.write(path / "summary.json", summary)
        self.mutate(path, "revision_scope.json", lambda v: v.update(valid_jobs=0, runs=[]))
        self.assertEqual(self.inspect(path)["status"], "FAIL")

    def test_exit_failure_and_missing_exit(self):
        path = self.bundle()
        self.mutate(path, "summary.json",
                    lambda v: v["steps"][1].update(exit_codes={"sim": 1}))
        self.assertEqual(self.inspect(path)["status"], "FAIL")
        self.mutate(path, "summary.json",
                    lambda v: v["steps"][1].update(exit_codes=None))
        self.assertEqual(self.inspect(path)["status"], "UNRESOLVED")

    def test_running_with_frozen_configs(self):
        path = self.bundle()
        self.mutate(path, "summary.json", lambda v: v.update(overall="RUNNING"))
        (path / "revision_scope.json").unlink()
        (path / "evidence.zip").unlink()
        self.assertEqual(self.inspect(path)["status"], "RUNNING")
        self.assertEqual(ix.build_index([path])["matrix"]["rows"][self.row["id"]]["status"],
                         "RUNNING")

    def test_tampered_and_missing_archives(self):
        path = self.bundle()
        (path / "source_hashes_after.json").write_text("{}")
        self.assertEqual(self.inspect(path)["status"], "FAIL")
        path2 = self.bundle("cold-A")
        (path2 / "sources.zip").unlink()
        (path2 / "evidence.zip").unlink()
        self.assertEqual(self.inspect(path2)["status"], "UNRESOLVED")

    def test_source_zip_bytes_and_frozen_config_must_match(self):
        path = self.bundle()
        with zipfile.ZipFile(path / "sources.zip", "w") as stream:
            stream.writestr("scripts/revision_matrix.py", b"altered")
        self.seal(path)
        self.assertEqual(self.inspect(path)["status"], "FAIL")
        path = self.bundle("cold-A")
        self.mutate(path, "frozen-spec.json",
                    lambda v: v["configs"][0]["params"].update(N_SRC=16))
        self.assertEqual(self.inspect(path)["status"], "FAIL")

    def test_model_gate_pass_is_separate_and_hash_checked(self):
        path = self.root / "model"
        path.mkdir()
        sources = {"model.py": b"# fixture\n"}
        with zipfile.ZipFile(path / "sources.zip", "x") as stream:
            stream.writestr("model.py", sources["model.py"])
        self.write(path / "summary.json",
                   dict(schema=ix.INSIGHT_SCHEMA, scope="MODEL_ONLY", kind="evaluate",
                        gate=dict(status="PASS", frozen_candidate="DAC2",
                                  validated_feedback=[{}] * 8),
                        completed=60, window=5_000_000, exit_code=0, validation_exit=0,
                        source_archive=dict(file="sources.zip",
                                            sha256=ix.sha256_file(path / "sources.zip"),
                                            files={"model.py": ix.sha256_bytes(sources["model.py"])})))
        index = ix.build_index([path])
        insight = index["insight_screen"]["artifacts"][0]
        self.assertEqual(insight["problems"], [])
        self.assertEqual(insight["gate_status"], "PASS")
        self.assertEqual(insight["feedback_count"], 8)
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 498)
        (path / "sources.zip").write_bytes(b"corrupt")
        self.assertTrue(ix.inspect_insight(path / "summary.json")["problems"])

    def test_wrong_job_seed_cohort_and_old_schema(self):
        for field, value in [("schema", "old"), ("job", {}),
                             ("params", {}), ("cold_cohort", "B"),
                             ("production_evidence", False)]:
            with self.subTest(field=field):
                result = dict(schema=ix.PERFORMANCE_SCHEMA, evidence_kind="RTL", status="PASS",
                              job=self.row, params=ix.expected_params(self.row), cold=False,
                              cold_cohort=None, training_cycles=self.row["training_cycles"],
                              production_evidence=True, sensitivity_evidence=False,
                              trace_sha256="a" * 64, metrics={}, windows=[])
                result[field] = value
                self.assertTrue(ix.result_payload_check(result, self.row, "trained",
                                                       ix.expected_config(self.row, "trained")))

    def test_historical_same_id_changed_row_is_not_current(self):
        rows = ix.current_matrix()
        old = copy.deepcopy(rows)
        old[0]["training_cycles"] += 1
        path = self.root / "matrix.json"
        self.write(path, dict(schema=ix.MATRIX_SCHEMA, jobs=old,
                              total_planned_jobs=498, matrix_sha256=ix.canonical_sha(old)))
        provenance = ix.matrix_provenance([path], rows)
        self.assertTrue(provenance["snapshot_pending"])
        self.assertIn(old[0]["id"], provenance["historical_snapshots"][0]["same_id_changed_rows"])
        self.assertEqual(ix.build_index([path])["matrix"]["counts"]["NOT_RUN"], 498)

    def test_baseline_running_separate_from_performance(self):
        path = self.root / "baseline" / "run" / "summary.json"
        self.write(path, dict(overall="RUNNING", scope="full", counts={}))
        self.write(path.parent / "baseline_scope.json", {})
        index = ix.build_index([path.parent])
        self.assertEqual(index["baseline_correctness"]["artifacts"][0]["status"], "RUNNING")
        self.assertEqual(index["performance"]["bundles"], [])
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 498)

    def test_missing_input_and_no_overwrite(self):
        with self.assertRaises(ValueError):
            ix.build_index([self.root / "absent"])
        sentinel = self.root / "sentinel"
        sentinel.write_bytes(b"keep")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ix.main(["--input", str(self.root), "--out", str(self.root)])
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_archive_traversal_duplicate_and_link_rejected(self):
        path = self.root / "unsafe.zip"
        with zipfile.ZipFile(path, "x") as stream:
            stream.writestr("../escape", b"x")
            stream.writestr("C:/escape", b"x")
            info = zipfile.ZipInfo("link")
            info.external_attr = 0o120777 << 16
            stream.writestr(info, b"target")
        members, problems = ix._read_zip_bytes(path)
        self.assertEqual(members, {})
        self.assertEqual(len(problems), 3)

    def dac_bundle(self, policy="DAC2", pilot=False, jobs=None):
        """Small source-bound DAC fixture; replace only immutable audit anchors.

        The JSON/config/JUnit/archive shapes are the released runner's schema.
        Real retained pilot blobs are independently checked outside this fixture.
        """
        jobs = copy.deepcopy(jobs or [next(r for r in ix.current_matrix()
                                         if r["group"] == "insight-confirmation")])
        if pilot:
            jobs = [dict(jobs[0], id="dac-pilot-s509-w256", group="dac-pilot", seed=509,
                         seed_role="exploration", window=256, training_cycles=512)]
        path = self.root / f"dac-{policy}-{pilot}-{len(list(self.root.iterdir()))}"
        path.mkdir()
        configs = [ix.expected_dac_config(job, policy) for job in jobs]
        sources = {name: f"# fixture {name}\n".encode() for name in ix.DAC_CORE_PATHS}
        sources["rtl/experimental/filelist.f"] = (
            ix.ROOT / "rtl/experimental/filelist.f").read_bytes()
        sources["scripts/run_revision_dac_experiments.py"] = b"# separate DAC closure\n"
        sources["sim/experimental/test_dac_performance.py"] = b"# native adapter\n"
        hashes = {name: ix.sha256_bytes(data) for name, data in sources.items()}
        shared = {name: hashes[name] for name in ix.DAC_CORE_PATHS}
        with zipfile.ZipFile(path / "sources.zip", "x") as stream:
            for name, data in sources.items():
                stream.writestr(name, data)
            stream.writestr("context/EXECUTION.md", b"# historical context\n")
        blobs = {
            "/accepted/native.json": dict(status="PASS", complete_matrix=True),
            "/accepted/screen.json": dict(scope="MODEL_ONLY", gate=dict(
                status="PASS", frozen_candidate="DAC2")),
            "/accepted/pilot.json": dict(status="PASS", selected_policy=policy, window=256),
        }
        encoded = {name: json.dumps(data).encode() for name, data in blobs.items()}
        digests = {name: ix.sha256_bytes(data) for name, data in encoded.items()}
        bindings = dict(native_bindings={"/accepted/native.json": digests["/accepted/native.json"]},
                        screen_bindings={"/accepted/screen.json": digests["/accepted/screen.json"]})
        release = dict(schema="cxl-dac-performance-release-v1", native_released=True,
                       parent_correctness_accepted=True, source_hashes=hashes, **bindings)
        encoded["/accepted/release.json"] = json.dumps(release).encode()
        bindings["release_binding"] = {
            "/accepted/release.json": ix.sha256_bytes(encoded["/accepted/release.json"])}
        pilot_bindings = {"/accepted/pilot.json": digests["/accepted/pilot.json"]}
        if not pilot:
            bindings["pilot_bindings"] = pilot_bindings
        for name, value in (
            ("DAC_SOURCE_SHA", ix.canonical_sha(hashes)),
            ("DAC_CORE_SHA", ix.canonical_sha(shared)),
            ("DAC_BINDING_SHA", {g: ix.canonical_sha(bindings[g]) for g in ix.DAC_BINDING_SHA}),
            ("DAC_PILOT_SHA", {policy: ix.canonical_sha(pilot_bindings)}),
        ):
            patcher = mock.patch.object(ix, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        manifest = {}
        for entries in bindings.values():
            for original, digest in entries.items():
                target = path / "acceptance" / digest
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(encoded[original])
                manifest[original] = dict(sha256=digest, archived_as=f"acceptance/{digest}")
        self.write(path / "acceptance/manifest.json", manifest)
        self.write(path / "source_hashes_before.json", hashes)
        self.write(path / "source_hashes_after.json", hashes)
        self.write(path / "frozen-spec.json", dict(
            schema=ix.DAC_SPEC_SCHEMA, configs=configs, jobs_sha256=ix.canonical_sha(configs),
            source_sha256=ix.canonical_sha(hashes), selected_policy=policy, pilot=pilot,
            jobs=1, make_jobs=2, **bindings))
        runs, steps = [], []
        for cfg, job in zip(configs, jobs):
            name = f"{cfg['name']}_seed{job['seed']}"
            rel = f"results/cocotb_{name}__dac_performance.json"
            self.write(path / rel, dict(
                schema="cxl-revision-dac-performance-v1", evidence_kind="RTL", status="PASS",
                job=job, selected_policy=policy, params=cfg["params"], cold=False, cold_cohort=None,
                training_cycles=job["training_cycles"], production_evidence=not pilot,
                sensitivity_evidence=pilot, matrix_contribution=int(not pilot and policy == "DAC2"),
                outstanding_after_drain=0, producer_backlog_after_drain=0,
                sparse_guard_complete=True, trace_sha256="a"*64, trace_config={"seed": job["seed"]},
                metrics={}, windows=[]))
            runs.append(dict(name=name, matrix_job_id=job["id"], selected_policy=policy,
                             result=rel, trace_sha256="a"*64))
            junit = f"junit/{name}.xml"
            (path / "junit").mkdir(exist_ok=True)
            (path / junit).write_text(
                '<testsuite tests="1"><testcase name="dac_performance"><properties>'
                f'<property name="random_seed" value="{job["seed"]}"/>'
                '</properties></testcase></testsuite>')
            steps.extend([
                dict(name=f"lint:{cfg['name']}", kind="lint", status="PASS",
                     exit_codes={"verilator": 0}),
                dict(name=f"cocotb:{name}", kind="cocotb", status="PASS", tests=1,
                     exit_codes=dict(verilate=0, make=0, simulation=0), junit=junit),
            ])
        for test in ("dac_performance_runner", "revision_traffic"):
            junit = f"junit/{test}.xml"
            (path / junit).write_text('<testsuite tests="1"><testcase name="unit"/></testsuite>')
            steps.append(dict(name=f"pytest:{test}", kind="pytest", status="PASS", tests=1,
                              exit_codes={"pytest": 0}, junit=junit))
        steps.append(dict(name="scope:dac-performance", kind="scope", status="PASS"))
        contribution = len(jobs) if not pilot and policy == "DAC2" else 0
        common = dict(selected_policy=policy, production_evidence=not pilot,
                      sensitivity_evidence=pilot, matrix_contribution=contribution)
        self.write(path / "dac_performance_scope.json", dict(
            schema="cxl-dac-performance-scope-v1", status="PASS", expected_jobs=len(jobs),
            runs=runs, source_hashes=hashes, problems=[], **common, **bindings))
        self.write(path / "summary.json", dict(
            overall="PASS", scope="full", milestone_acceptance_scope=True,
            full_498_matrix_executed=False, steps=steps,
            counts=dict(fail=0, not_run=0, failures=0, errors=0, skipped=0), **common))
        self.seal(path)
        return path

    def test_dac_source_superset_and_all_30_trained_rows(self):
        jobs = [r for r in ix.current_matrix() if r.get("conditional")]
        self.assertEqual(len(jobs), 30)
        path = self.dac_bundle(jobs=jobs)
        index = ix.build_index([path])
        bundle = index["performance"]["bundles"][0]
        self.assertEqual(bundle["status"], "PASS", bundle["failures"])
        self.assertGreater(len(ix.load_json(path / "source_hashes_before.json")), 39)
        self.assertEqual(bundle["core_source_sha256"], ix.DAC_CORE_SHA)
        self.assertEqual(index["matrix"]["counts"]["PASS"], 30)
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 468)
        self.assertEqual(index["matrix"]["by_group"]["n4-confirmation"]["planned"], 120)
        self.assertEqual(index["matrix"]["by_group"]["n4-confirmation"]["PASS"], 0)
        self.assertEqual(index["matrix"]["by_group"]["insight-confirmation"]["PASS"], 20)
        self.assertEqual(index["matrix"]["by_group"]["insight-robustness"]["PASS"], 10)
        self.assertFalse(index["matrix"]["completion"]["complete"])
        run = index["performance"]["accepted_records"][0]
        self.assertEqual(run["selected_policy"], "DAC2")
        self.assertEqual(run["lane"], "trained")
        self.assertEqual(run["matrix_contribution"], 1)
        self.assertEqual(run["result_sha256"], ix.sha256_file(path / run["result"]))
        self.assertEqual(run["core_source_sha256"], ix.DAC_CORE_SHA)

    def test_dac_selected_row_does_not_require_other_29(self):
        path = self.dac_bundle()
        index = ix.build_index([path])
        self.assertEqual(index["performance"]["bundles"][0]["status"], "PASS")
        self.assertEqual(index["matrix"]["counts"]["PASS"], 1)
        self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 497)

    def test_insight_completion_counts_accepted_rows_and_never_w256(self):
        jobs = [r for r in ix.current_matrix() if r.get("conditional")]
        production = self.dac_bundle(jobs=jobs)
        pilot = self.dac_bundle(pilot=True)
        for inputs, accepted in (([], 0), ([pilot], 0), ([production], 30),
                                 ([production, production, pilot], 30)):
            with self.subTest(accepted=accepted, inputs=len(inputs)):
                completion = ix.build_index(inputs)["matrix"]["completion"]
                self.assertEqual(completion["matrix_contribution_from_insight"], accepted)
                self.assertEqual(completion["matrix_contribution_from_w256"], 0)
                self.assertEqual(completion["pass"],
                                 completion["core_unconditional_pass"] + accepted)

    def test_dac_pilots_and_dac1_production_zero_contribution(self):
        for policy, pilot in (("DAC2", True), ("DAC1", True), ("DAC1", False)):
            with self.subTest(policy=policy, pilot=pilot):
                path = self.dac_bundle(policy, pilot)
                index = ix.build_index([path])
                self.assertEqual(index["performance"]["bundles"][0]["status"], "PASS",
                                 index["performance"]["bundles"][0]["failures"])
                self.assertEqual(index["matrix"]["counts"]["NOT_RUN"], 498)
                self.assertEqual(index["performance"]["accepted_records"], [])
                self.assertEqual(len(index["performance"]["descriptive_records"]), 1)
                self.assertEqual(index["performance"]["descriptive_records"][0]["matrix_contribution"], 0)

    def test_dac_forged_gate_maps_rejected_even_when_scope_agrees(self):
        for group in ("native_bindings", "screen_bindings", "pilot_bindings"):
            with self.subTest(group=group):
                path = self.dac_bundle()
                for filename in ("frozen-spec.json", "dac_performance_scope.json"):
                    self.mutate(path, filename, lambda v: v.update(
                        **{group: {"/forged/gate.json": "a"*64}}))
                result = ix.inspect_performance_bundle(path, {r["id"]: r for r in ix.current_matrix()})
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(ix.build_index([path])["matrix"]["counts"]["PASS"], 0)

    def test_dac_source_result_summary_false_claims_rejected(self):
        mutations = [
            ("source_hashes_after.json", lambda v: v.update({"AGENTS.md": "f"*64})),
            ("frozen-spec.json", lambda v: v.update(selected_policy="DAC1")),
            ("dac_performance_scope.json", lambda v: v.update(expected_jobs=2)),
            ("dac_performance_scope.json", lambda v: v.update(runs=[])),
            ("summary.json", lambda v: v.update(matrix_contribution=30)),
            ("summary.json", lambda v: v.update(full_498_matrix_executed=True)),
            ("summary.json", lambda v: v["steps"][1].update(exit_codes={"simulation": False})),
            ("summary.json", lambda v: v["steps"][1].update(skipped=1)),
            ("summary.json", lambda v: v.pop("milestone_acceptance_scope")),
        ]
        for filename, change in mutations:
            with self.subTest(filename=filename):
                path = self.dac_bundle()
                self.mutate(path, filename, change)
                self.assertNotEqual(ix.build_index([path])["performance"]["bundles"][0]["status"],
                                    "PASS")
        for field, value in (("selected_policy", "DAC1"), ("cold", 0),
                             ("training_cycles", 512), ("production_evidence", False)):
            with self.subTest(result_field=field):
                path = self.dac_bundle()
                rel = ix.load_json(path / "dac_performance_scope.json")["runs"][0]["result"]
                self.mutate(path, rel, lambda v: v.update(**{field: value}))
                self.assertEqual(ix.build_index([path])["performance"]["bundles"][0]["status"], "FAIL")

    def test_dac_missing_or_tampered_acceptance_blob_and_raw_junit(self):
        for mode in ("missing", "tampered", "manifest_path", "junit_skip", "junit_seed",
                     "release", "missing_pilot"):
            with self.subTest(mode=mode):
                path = self.dac_bundle()
                manifest = ix.load_json(path / "acceptance/manifest.json")
                blob = path / manifest["/accepted/screen.json"]["archived_as"]
                if mode == "missing":
                    blob.unlink()
                elif mode == "tampered":
                    blob.write_text('{"gate":{"status":"PASS","frozen_candidate":"DAC1"}}')
                elif mode == "manifest_path":
                    self.mutate(path, "acceptance/manifest.json", lambda v: v[
                        "/accepted/screen.json"].update(archived_as="../escape"))
                elif mode == "missing_pilot":
                    for filename in ("frozen-spec.json", "dac_performance_scope.json"):
                        self.mutate(path, filename, lambda v: v.pop("pilot_bindings"))
                elif mode == "release":
                    spec = ix.load_json(path / "frozen-spec.json")
                    digest = next(iter(spec["release_binding"].values()))
                    release = ix.load_json(path / "acceptance" / digest)
                    release["parent_correctness_accepted"] = False
                    data = json.dumps(release).encode()
                    new_digest = ix.sha256_bytes(data)
                    (path / "acceptance" / new_digest).write_bytes(data)
                    for filename in ("frozen-spec.json", "dac_performance_scope.json"):
                        self.mutate(path, filename, lambda v: v.update(
                            release_binding={"/accepted/release.json": new_digest}))
                    manifest["/accepted/release.json"] = dict(
                        sha256=new_digest, archived_as=f"acceptance/{new_digest}")
                    self.write(path / "acceptance/manifest.json", manifest)
                elif mode == "junit_skip":
                    summary = ix.load_json(path / "summary.json")
                    junit = summary["steps"][1]["junit"]
                    (path / junit).write_text(
                        '<testsuite><testcase name="dac_performance"><skipped/></testcase></testsuite>')
                else:
                    summary = ix.load_json(path / "summary.json")
                    junit = path / summary["steps"][1]["junit"]
                    junit.write_text(junit.read_text().replace('value="529"', 'value="530"'))
                self.seal(path)
                self.assertNotEqual(ix.build_index([path])["performance"]["bundles"][0]["status"],
                                    "PASS")

    def test_dac_incomplete_production_is_running_not_accepted(self):
        path = self.dac_bundle()
        self.mutate(path, "summary.json", lambda v: v.update(overall="RUNNING"))
        (path / "dac_performance_scope.json").unlink()
        (path / "evidence.zip").unlink()
        index = ix.build_index([path])
        self.assertEqual(index["performance"]["bundles"][0]["status"], "RUNNING")
        self.assertEqual(index["matrix"]["counts"]["RUNNING"], 1)
        self.assertEqual(index["performance"]["accepted_records"], [])


class MatchedPowerIndexTests(unittest.TestCase):
    setUp = EvidenceIndexTests.setUp
    write = EvidenceIndexTests.write
    def power_fixture(self, arms=("A", "B"), policy="fcfs", seed=509):
        import check_power_replay as power
        from test_power_extension import trained_metadata
        base = self.root / "power"
        base.mkdir()
        cases = []
        sources = {n: (ix.ROOT / n).read_bytes() for n in ix.POWER_RUNTIME}
        sources["scripts/fixture.py"] = b"# synthetic source closure\n"
        hashes = {n: ix.sha256_bytes(v) for n, v in sources.items()}
        mapped_bytes = {n: n.encode() for n in
                        ("manifest.json", "run_config.tcl", "output/switch_top.syn.v", "output/switch_top.syn.sdc")}
        mapped = {n: ix.sha256_bytes(v) for n, v in mapped_bytes.items()}
        pinned = set()
        for arm in arms:
            exp, rem = base / f"export-{arm}", base / f"remote-{arm}"
            exp.mkdir(); rem.mkdir()
            reports = rem / "results/reports"
            reports.mkdir(parents=True)
            m = trained_metadata(policy, seed, arm)
            m.update(source_sha256=hashes, accepted_case_sha256=mapped,
                     accepted_source_revision="759f86b24f13ed5984c19034eeeea2ca43b0e971",
                     profile_canonical_sha256="6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d")
            with zipfile.ZipFile(exp / "source-freeze.zip", "x") as z:
                for n, v in {**sources, **{f"mapped/{n}": v for n, v in mapped_bytes.items()}}.items():
                    z.writestr(n, v)
            (exp / "vectors.txt.gz").write_bytes(b"fixture vector bytes")
            m["source_archive_sha256"] = ix.sha256_file(exp / "source-freeze.zip")
            m["vectors_gzip_sha256"] = ix.sha256_file(exp / "vectors.txt.gz")
            m["trace"] = dict(sha256="a" * 64, config=dict(
                generator="cxl-hog-sparse-traffic-v1", seed=seed, n_src=4, depth=16, desc_w=105,
                window=5_000_000, heavy_source=0, heavy_per_cycle=1, ready=1, sparse_probability=[1,128],
                burst_size=8, burst_blocks=100, burst_block_cycles=1024, burst_offset_inclusive=[0,1023],
                phase_cycles=dict(training=10_000_000, A=100_000, A_guard=1024, B=102_400, B_guard=1024)))
            phases = dict(training=10_000_000, A=100_000)
            if arm == "B": phases.update(A_guard=1024, B=102_400)
            audit = dict(status="INDEPENDENT_MODEL_AND_PIN_FIFO_CHECKED", exit=0, rows=m["total_cycles"],
                         warmup=m["warmup"], measured=m["measured"], outstanding_at_end=[0]*4,
                         traffic_phase_cycles=phases, traffic_phase_pin_sha256={k: "b"*64 for k in phases})
            if policy == "fai-main":
                audit["main_closings"] = [{k: c[k] for k in
                    ("cycle", "b_close", "s_close", "evidence", "old_classes", "next_cycle_classes")}
                    for c in m["closings"]]
            self.write(exp / "audit.json", audit)
            m["audit_sha256"] = ix.sha256_file(exp / "audit.json")
            self.write(exp / "metadata.json", m)
            self.write(base / f"native-{arm}.json", dict(exit_code=0))
            native = base / f"native-{arm}.json"
            members = {n: ix.sha256_file(exp / n) for n in
                       ("metadata.json", "audit.json", "source-freeze.zip", "vectors.txt.gz")}
            runtime = {n: hashes[n] for n in ix.POWER_RUNTIME}
            members.update(runtime)
            (rem / "payload.tar").write_bytes(b"fixture payload")
            prepared = dict(member_sha256=members, runtime_sha256=runtime,
                            payload_sha256=ix.sha256_file(rem / "payload.tar"))
            self.write(rem / "prepared.json", prepared)
            transcript = dict(runtime_sha256=runtime, stages={s:dict(exit=0) for s in
                              ("preflight", "upload", "power", "fetch")})
            self.write(rem / "command-transcript.json", transcript)
            for stage in transcript["stages"]:
                self.write(rem / f"transport/{stage}.exit.json", dict(outer_exit=0))
            for name in ("design.rpt", "library.rpt", "clocks.rpt", "units.rpt", "update-power.rpt",
                         "disable-timing.rpt", "switching-coverage.rpt", "not-annotated.rpt", "annotated.rpt",
                         "power-hierarchy.rpt", "registers-and-clock-pins.rpt", "pilot-status.rpt",
                         "pt.log", "compile.log", "sim.log"):
                (reports / name).write_text("fixture raw report\n")
            (reports / "power.rpt").write_text("Total Power = 0.001 W\n")
            (reports / "check-power.rpt").write_text("\n".join([
                f"Information: Checking '{k}'." for k in
                ("out_of_table_range", "missing_table", "missing_function")])+"\ncheck_power succeeded.\n1\n")
            (reports / "saif-read.rpt").write_text("\n".join(f"{k} = 1" for k in
                ("Total number of nets", "Number of annotated nets", "Total number of leaf cells",
                 "Number of fully annotated leaf cells")))
            (reports / "replay.txt").write_text("\n".join(power.expected_result_v2(m))+"\n")
            duration = m["duration_ns"]
            (rem / "results/activity.saif").write_text(
                f"(TIMESCALE 1 ns)(DURATION {duration})(INSTANCE tb (INSTANCE dut "
                f"(clk (T0 {duration//2})(T1 {duration//2})(TX 0)(TC {2*m['measured_cycles']-1}))))")
            replay = power.check_replay(m, reports / "replay.txt", rem / "results/activity.saif")
            self.write(reports / "replay-audit.json", replay)
            self.write(reports / "pilot-audit.json", dict(replay, pt=power.check_pt(reports)))
            (reports / "exits.txt").write_text("compile=0\nsim=0\npt=0\nshell_exit=0\n")
            digests = ["d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286",
                       "844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094",
                       *[mapped[n] for n in ("run_config.tcl", "output/switch_top.syn.v", "output/switch_top.syn.sdc")],
                       members["metadata.json"], members["vectors.txt.gz"], *runtime.values()]
            for name in ("source.sha256", "source-after.sha256"):
                (reports / name).write_text("\n".join(f"{h}  /fixture/{j}" for j,h in enumerate(digests)))
            files = {p.relative_to(rem / "results").as_posix(): ix.sha256_file(p)
                     for p in (rem / "results").rglob("*") if p.is_file()}
            self.write(rem / "remote-result.json", dict(remote_exit=0, files=files))
            bindings = dict(metadata=members["metadata.json"], audit=members["audit.json"],
                source_archive=members["source-freeze.zip"], vectors=members["vectors.txt.gz"],
                native_exit=ix.sha256_file(native), prepared=ix.sha256_file(rem / "prepared.json"),
                payload=prepared["payload_sha256"], remote_result=ix.sha256_file(rem / "remote-result.json"),
                transcript=ix.sha256_file(rem / "command-transcript.json"))
            receipt = base / f"semantic-{arm}.json"
            review = base / f"independent-{arm}.json"
            self.write(review, dict(status="ADOPTED_SYNTHETIC_FIXTURE", blocking_issues=[],
                downloaded_hashes=files, checker_replay=replay, checker_pt=power.check_pt(reports)))
            self.write(receipt, dict(schema="cxl-trained-power-semantic-acceptance-v1",
                case=dict(policy=policy,seed=seed,arm=arm), decision="ADOPT_PRE_LAYOUT_TT25NS_MATCHED_POWER",
                problems=[], bindings=bindings, reports=files, independent_review=str(review),
                independent_review_sha256=ix.sha256_file(review),
                limitations=["synthetic fixture; not measured evidence"]))
            pinned.add(ix.sha256_file(receipt))
            cases.append(dict(policy=policy,seed=seed,arm=arm,export_dir=str(exp),remote_dir=str(rem),
                native_exit=dict(path=str(native),sha256=ix.sha256_file(native)),native_exit_field="exit_code",
                semantic_receipt=dict(path=str(receipt),sha256=ix.sha256_file(receipt))))
        self.write(base / "matched-power-acceptance.json", dict(schema=ix.POWER_MANIFEST, cases=cases))
        for name, val in (("POWER_SOURCE_SHA", ix.canonical_sha(hashes)),
                          ("POWER_MAPPED_SHA", dict(ix.POWER_MAPPED_SHA,**{policy:ix.canonical_sha(mapped)})),
                          ("POWER_REVIEW_RELEASE_SHA256",frozenset(pinned))):
            patcher=mock.patch.object(ix,name,val);patcher.start();self.addCleanup(patcher.stop)
        return base / "matched-power-acceptance.json"

    def detached_fixture(self, arm="A", with_pair=False, policy="fcfs"):
        """Reuse native/raw fixtures; mock only the separately tested pinned transport module."""
        path=self.power_fixture(('A','B') if with_pair else (arm,),policy,511)
        cases=ix.load_json(path)['cases']
        case=next(c for c in cases if c['arm']==arm)
        case_id=f'{policy}-{arm}-s511'
        remote=Path(case['remote_dir']);reports=remote/'results/reports'
        (remote/'transport/power.exit.json').unlink()
        plan=path.parent/'detached-plan.json';self.write(plan,dict(jobs=[dict(id=case_id)]))
        reviewer=path.parent/'review_detached.py';reviewer.write_text('# immutable fixture reviewer\n')
        inspection=remote/'inspection.json';self.write(inspection,dict(actual_EDA_exit=0))
        result=ix.load_json(remote/'remote-result.json')
        result.update(transport_contract='cxl-detached-trained-power-v1',foreground_power_ssh=False,wrapper_exit=0)
        self.write(remote/'remote-result.json',result)
        proof=dict(transport_contract='cxl-detached-trained-power-v1',foreground_power_ssh=False,
                   actual_EDA_exits=dict(compile=0,sim=0,pt=0,shell_exit=0),wrapper_exit=0)
        context={str(inspection):ix.sha256_file(inspection)}
        native=ix.load_json(reports/'pilot-audit.json')
        meta=ix.load_json(Path(case['export_dir'])/'metadata.json')
        semantic=dict(status='REVIEWED_DETACHED_CASE_PARENT_ADOPTION_REQUIRED',raw_semantic_status='ADOPTED_FIXTURE',
            case_id=case_id,policy=policy,blocking_issues=[],downloaded_hashes=result['files'],
            measured_cycles=meta['measured_cycles'],total_checked_cycles=meta['total_cycles'],
            replay=ix.load_json(reports/'replay-audit.json'),pt=native['pt'],detached_transport=proof,
            launch_context_sha256=context,reviewer_source_sha256=ix.sha256_file(reviewer),
            calibration_caller_sha256=ix.POWER_MAINB_CALLER_SHA,base_reviewer_sha256=ix.POWER_MAINB_BASE_SHA,
            continuation_plan_sha256=ix.sha256_file(plan),
            original_transcript_sha256=ix.sha256_file(remote/'command-transcript.json'),
            remote_result_sha256=ix.sha256_file(remote/'remote-result.json'))
        parent=path.parent/'parent-detached.json';independent=path.parent/'independent-detached.json'
        self.write(parent,dict(semantic,checked_utc='parent'));self.write(independent,dict(semantic,checked_utc='independent'))
        ref=lambda p:dict(path=str(p),sha256=ix.sha256_file(p))
        receipt=Path(case['semantic_receipt']['path'])
        release=dict(schema='cxl-detached-trained-power-semantic-release-v1',status='PARENT_ACCEPTED_DETACHED_TRAINED_POWER_CASE',
            case_id=case_id,policy=policy,seed=511,arm=arm,transport_contract='cxl-detached-trained-power-v1',
            foreground_power_ssh=False,actual_EDA_exit=0,semantic_receipt=str(parent),semantic_sha256=ix.sha256_file(parent),
            independent_semantic_receipt=ref(independent),independent_reviewer=str(reviewer),reviewer_sha256=ix.sha256_file(reviewer),
            controller_plan=ref(plan),remote_result=ref(remote/'remote-result.json'),inspection=ref(inspection),
            independent_release=ref(independent),writer_release=ref(reviewer))
        self.write(receipt,release)
        case.update(semantic_receipt=ref(receipt),transport_contract='cxl-detached-trained-power-v1')
        self.write(path,dict(schema=ix.POWER_MANIFEST,cases=cases))
        module=mock.Mock()
        module.bindings.return_value=(dict(jobs=[dict(id=case_id)]),{})
        module.ready.return_value=True
        def transport(folder,export,r,transcript,job,original):
            if (folder/'transport/power.exit.json').exists() or r.get('wrapper_exit') != 0:
                raise ValueError('invalid detached transport fixture')
            return copy.deepcopy(proof)
        module.validate_transport.side_effect=transport
        module.launch_context.return_value=context
        module.review_case.side_effect=AssertionError('output-producing review must not run')
        for key,value in [('POWER_REVIEW_RELEASE_SHA256',ix.POWER_REVIEW_RELEASE_SHA256|{ix.sha256_file(receipt)}),
                          ('POWER_DETACHED_REVIEWER_SHA',ix.sha256_file(reviewer)),
                          ('load_power_detached_reviewer',mock.Mock(return_value=module))]:
            patcher=mock.patch.object(ix,key,value);patcher.start();self.addCleanup(patcher.stop)
        return path,case,module

    def test_detached_exact_rr_main511_arms_pair_and_identity_regression(self):
        # Separate fixtures and patch stacks keep each policy/arm isolated.
        for policy in ('rr','fai-main'):
            for arm in ('A','B'):
                with self.subTest(policy=policy,arm=arm):
                    fixture=type(self)();fixture.setUp()
                    try:
                        path,case,module=fixture.detached_fixture(arm,with_pair=True,policy=policy)
                        result=ix.inspect_power_case(case,path.parent)
                        self.assertEqual(result['status'],'PASS',result)
                        self.assertEqual(result['measured_cycles'],100000 if arm=='A' else 102400)
                        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],1)
                        manifest=ix.load_json(path)
                        for remaining in ('A','B'):
                            fixture.write(path,dict(manifest,cases=[c for c in manifest['cases'] if c['arm']==remaining]))
                            self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)
                        for key,value in [('policy','fcfs'),('arm','B' if arm=='A' else 'A'),('seed',510)]:
                            self.assertNotEqual(ix.inspect_power_case(dict(case,**{key:value}),path.parent)['status'],'PASS')
                        receipt=Path(case['semantic_receipt']['path']);release=ix.load_json(receipt)
                        parent=Path(release['semantic_receipt']);review=ix.load_json(parent);review['policy']='fcfs'
                        fixture.write(parent,review);release['semantic_sha256']=ix.sha256_file(parent)
                        fixture.write(receipt,release);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
                        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
                            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
                        module.review_case.assert_not_called()
                    finally:
                        fixture.doCleanups()

    def test_detached_fcfs511b_pair_closure_and_missing_arm(self):
        path,case,module=self.detached_fixture('B',with_pair=True)
        result=ix.inspect_power_case(case,path.parent)
        self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['measured_cycles'],102400)
        manifest=ix.load_json(path)
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],1)
        for arm in ('A','B'):
            self.write(path,dict(manifest,cases=[c for c in manifest['cases'] if c['arm']==arm]))
            index=ix.build_index([path])
            self.assertEqual(index['matched_power']['accepted_rows'],0)
            self.assertEqual(index['matrix']['by_group']['matched-power']['UNRESOLVED'],1)
        self.assertNotEqual(ix.inspect_power_case(dict(case,arm='A'),path.parent)['status'],'PASS')
        # Parent digest/pin rebinding cannot hide disagreement with independent B semantics.
        receipt=Path(case['semantic_receipt']['path']);release=ix.load_json(receipt)
        parent=Path(release['semantic_receipt']);review=ix.load_json(parent);review['case_id']='fcfs-A-s511'
        self.write(parent,review);release['semantic_sha256']=ix.sha256_file(parent);self.write(receipt,release)
        case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        module.review_case.assert_not_called()

    def test_detached_single_actual_contract_arm_does_not_complete_pair(self):
        path,case,module=self.detached_fixture()
        result=ix.inspect_power_case(case,path.parent)
        self.assertEqual(result['status'],'PASS',result)
        self.assertFalse(result['foreground_power_ssh'])
        self.assertFalse((Path(case['remote_dir'])/'transport/power.exit.json').exists())
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)
        self.assertEqual(ix.build_index([path])['matrix']['by_group']['matched-power']['UNRESOLVED'],1)
        module.review_case.assert_not_called()

    def test_detached_rejects_unreleased_identity_and_missing_explicit_contract(self):
        path,case,module=self.detached_fixture()
        for key,value in [('arm','B'),('seed',510),('policy','rr'),('transport_contract','standard')]:
            with self.subTest(key=key):
                self.assertNotEqual(ix.inspect_power_case(dict(case,**{key:value}),path.parent)['status'],'PASS')
        missing=dict(case);del missing['transport_contract']
        self.assertNotEqual(ix.inspect_power_case(missing,path.parent)['status'],'PASS')
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset()):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_detached_rebound_parent_release_cannot_forge_semantics_or_identity(self):
        path,case,module=self.detached_fixture();receipt=Path(case['semantic_receipt']['path']);before=receipt.read_bytes()
        for key,value in [('status','PASS'),('actual_EDA_exit',False),('foreground_power_ssh',True),
                          ('case_id','fcfs-B-s511'),('transport_contract','foreground'),
                          ('remote_result',ix.load_json(receipt)['inspection'])]:
            with self.subTest(key=key):
                release=ix.load_json(receipt);release[key]=value;self.write(receipt,release)
                changed=dict(case,semantic_receipt=dict(path=str(receipt),sha256=ix.sha256_file(receipt)))
                with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
                    self.assertNotEqual(ix.inspect_power_case(changed,path.parent)['status'],'PASS')
                receipt.write_bytes(before)
        release=ix.load_json(receipt);parent=Path(release['semantic_receipt']);review=ix.load_json(parent)
        review['blocking_issues']=['failed'];self.write(parent,review);release['semantic_sha256']=ix.sha256_file(parent)
        self.write(receipt,release);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_detached_requires_real_transport_and_launch_context_proof(self):
        path,case,module=self.detached_fixture()
        module.ready.return_value=False
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        module.ready.return_value=True
        module.launch_context.return_value={'different':'a'*64}
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        module.launch_context.side_effect=ValueError('PID/startticks or launch claim drift')
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        module.validate_transport.side_effect=ValueError('terminal poll/wrapper incomplete')
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_detached_rejects_fake_foreground_and_changed_raw_files(self):
        path,case,module=self.detached_fixture();remote=Path(case['remote_dir'])
        fake=remote/'transport/power.exit.json';self.write(fake,dict(outer_exit=0))
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS');fake.unlink()
        for p in [remote/'payload.tar',remote/'results/activity.saif',remote/'results/reports/source.sha256',
                  remote/'results/reports/exits.txt',remote/'inspection.json']:
            with self.subTest(path=str(p)):
                before=p.read_bytes();p.write_bytes(before+b'changed')
                self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
                p.write_bytes(before)
        self.assertEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_detached_loader_rejects_unpinned_code_before_import(self):
        reviewer=self.root/'unreleased.py';reviewer.write_text("raise AssertionError('must not execute')\n")
        plan=self.root/'plan.json';self.write(plan,{})
        with self.assertRaisesRegex(ValueError,'unreleased detached'):
            ix.load_power_detached_reviewer(reviewer,plan)

    def test_power_both_arms_required_and_separate_from_rtl(self):
        path = self.power_fixture()
        index = ix.build_index([path])
        self.assertEqual(index["matched_power"]["accepted_rows"],1)
        self.assertEqual(index["matrix"]["counts"]["PASS"],1)
        self.assertEqual(index["performance"]["accepted_records"],[])
        m=ix.load_json(path);m["cases"]=m["cases"][:1];self.write(path,m)
        index=ix.build_index([path])
        self.assertEqual(index["matched_power"]["accepted_rows"],0)
        self.assertEqual(index["matrix"]["counts"]["UNRESOLVED"],1)

    def test_power_bad_identity_source_window_and_unpinned_pass(self):
        path=self.power_fixture(("A",));m=ix.load_json(path);original=copy.deepcopy(m)
        mutations=[("arm","B"),("seed",510),("seed",True),("policy","rr")]
        for key,value in mutations:
            m=copy.deepcopy(original);m["cases"][0][key]=value;self.write(path,m)
            r=ix.inspect_power_manifest(path,{x['id']:x for x in ix.current_matrix()})
            self.assertNotEqual(r['cases'][0]['status'],'PASS')
        self.write(path,original);case=original['cases'][0];meta=Path(case['export_dir'])/'metadata.json'
        saved=ix.load_json(meta)
        for key,value in [('fai_window',256),('schema','cxl-power-replay-v1'),('source_sha256',{}),
                          ('trace',dict(saved['trace'],sha256='bad'))]:
            self.write(meta,dict(saved,**{key:value}))
            self.assertFalse(ix.inspect_power_case(case,path.parent)['raw_contract_checked'])
        self.write(meta,saved)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset()):
            r=ix.inspect_power_case(case,path.parent)
        self.assertTrue(r['raw_contract_checked']);self.assertNotEqual(r['status'],'PASS')

    def test_power_tampered_hash_stage_audit_and_semantic_rejected(self):
        path=self.power_fixture(("A",));case=ix.load_json(path)['cases'][0];rem=Path(case['remote_dir'])
        for rel in ('transport/power.exit.json','results/reports/power.rpt','results/activity.saif',
                    'results/reports/source-after.sha256','payload.tar'):
            p=rem/rel;before=p.read_bytes();p.write_bytes(b'bad')
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS',rel)
            p.write_bytes(before)
        receipt=Path(case['semantic_receipt']['path']);v=ix.load_json(receipt);v['decision']='PASS';self.write(receipt,v)
        case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_power_first_adapter_release_accepts_only_main509a_zero_rows(self):
        path=self.power_fixture(("A",),"fai-main");case=ix.load_json(path)['cases'][0]
        rem=Path(case['remote_dir']);old=ix.load_json(Path(case['semantic_receipt']['path']))
        release=dict(schema='cxl-main509a-semantic-release-v1',
            status='PARENT_ACCEPTED_MAIN509A_SEMANTICS_RELEASE_REMAINING17',case_id='fai-main-A-s509',
            local_files={n:ix.sha256_file(Path(case['export_dir'])/n) for n in
                         ('metadata.json','audit.json','source-freeze.zip','vectors.txt.gz')},
            reviewed_files=old['reports'],**{k+'_sha256':old['bindings'][k] for k in
                                           ('prepared','payload','remote_result','transcript')},
            independent_review=old['independent_review'],
            independent_review_sha256=old['independent_review_sha256'])
        receipt=Path(case['semantic_receipt']['path']);self.write(receipt,release)
        case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        self.write(path,dict(schema=ix.POWER_MANIFEST,cases=[case]))
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            r=ix.inspect_power_case(case,path.parent);self.assertEqual(r['status'],'PASS',r)
            self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)
            release['payload_sha256']='0'*64;self.write(receipt,release)
            case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
            with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
                self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_power_duplicate_case_and_rebound_native_failure_rejected(self):
        path=self.power_fixture(("A",));m=ix.load_json(path);case=m['cases'][0]
        m['cases'].append(copy.deepcopy(case));self.write(path,m)
        result=ix.inspect_power_manifest(path,{r['id']:r for r in ix.current_matrix()})
        self.assertEqual(result['rows'],[]);self.assertIn('duplicate',result['problems'][0])
        native=Path(case['native_exit']['path']);self.write(native,dict(exit_code=1))
        case['native_exit']['sha256']=ix.sha256_file(native)
        result=ix.inspect_power_case(case,path.parent)
        self.assertFalse(result['raw_contract_checked']);self.assertIn('native exporter',result['problems'][0])

    def recovered_fixture(self, policy="fcfs", arm="A", with_pair=False, seed=509):
        """The original failed transport and recovered reports are distinct artifacts."""
        path = self.power_fixture(("A", "B") if with_pair else (arm,), policy, seed)
        cases = ix.load_json(path)["cases"]
        case = next(c for c in cases if c["arm"] == arm)
        main_b = policy == "fai-main" and seed == 509 and arm == "B"
        main_a = policy == "fai-main" and seed == 510 and arm == "A"
        main_510b = policy == "fai-main" and seed == 510 and arm == "B"
        case_id = f"{policy}-{arm}-s{seed}"
        original = Path(case["remote_dir"])
        recovery = path.parent / "recovery"
        recovery.mkdir()
        (original / "results").rename(recovery / "results")
        reports = recovery / "results/reports"
        for name in ("start-utc.txt", "tool-paths.txt", "run-status.txt"):
            (reports / name).write_text("fixture\n")
        prepared = ix.load_json(original / "prepared.json")
        remote_root, mapped_root = "/existing/" + case_id, "/mapped/" + policy
        transcript = ix.load_json(original / "command-transcript.json")
        transcript.update(case_id=case_id, remote_root=remote_root,
            prepared_sha256=ix.sha256_file(original / "prepared.json"),
            payload_sha256=prepared["payload_sha256"],
            mapped=dict(remote_root=mapped_root, hashes=ix.load_json(Path(case["export_dir"])/"metadata.json")["accepted_case_sha256"]))
        for stage in ("power", "fetch"):
            transcript["stages"][stage]["exit"] = 255
            self.write(original / f"transport/{stage}.exit.json", dict(outer_exit=255))
        self.write(original / "command-transcript.json", transcript)
        source_record = {remote_root+"/"+n: prepared["member_sha256"][n] for n in
                         ("metadata.json", "vectors.txt.gz", *ix.POWER_RUNTIME)}
        inputs = {mapped_root+"/"+n:h for n,h in transcript["mapped"]["hashes"].items()}
        inputs.update({"/model.v":"d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286",
                       "/tt.db":"844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094"})
        source_record.update({n:h for n,h in inputs.items() if not n.endswith("/manifest.json")})
        for name in ("source.sha256", "source-after.sha256"):
            (reports / name).write_text("\n".join(f"{h}  {n}" for n,h in source_record.items()))
        files = {p.relative_to(recovery/"results").as_posix():ix.sha256_file(p)
                 for p in (recovery/"results").rglob("*") if p.is_file()}
        plan = dict(schema="cxl-inspect-fetch-existing-main510b-v1" if main_510b else "cxl-inspect-fetch-existing-main510a-v1" if main_a else "cxl-inspect-fetch-existing-main509b-v1" if main_b else "cxl-inspect-fetch-existing-fcfs509a-v1",case_id=case_id,
            remote_root=remote_root,expected_members=prepared["member_sha256"],
            payload_sha256=prepared["payload_sha256"],remote_inputs=inputs,
            expected_source_record=source_record,required_outputs=list(files),allowed_outputs=list(files),
            bindings={str(p):ix.sha256_file(p) for p in [original/"prepared.json", original/"command-transcript.json",
                *[original/f"transport/{s}.exit.json" for s in ("power","fetch")]]})
        self.write(recovery / "plan.json",plan)
        inspection=dict(status="CLEAN_COMPLETED_READY_TO_FETCH",remote_root=remote_root,processes=[],
            EDA_exit=0,actual_exits=dict(compile=0,sim=0,pt=0,shell_exit=0),payload_and_source_match=True,files=files)
        self.write(recovery/"inspection.json",inspection)
        with tarfile.open(recovery/"fetch.tar","w") as archive:
            for n in files:archive.add(recovery/"results"/n,arcname=n)
        result=dict(status="EXISTING_MAIN510B_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED" if main_510b else "EXISTING_MAIN510A_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED" if main_a else "EXISTING_MAIN509B_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED" if main_b else "EXISTING_FCFS509A_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED",files=files,
            actual_EDA_exit=0,payload_and_source_match=True,
            inspected_manifest_sha256=ix.sha256_file(recovery/"inspection.json"),
            archive_sha256=ix.sha256_file(recovery/"fetch.tar"))
        self.write(recovery/"result.json",result)
        for name in ("inspect-exit.json","fetch-exit.json"):
            self.write(recovery/name,dict(outer_exit=0))
        reviewer = recovery/"reviewer.py";reviewer.write_text("# reviewed fixture\n")
        meta=ix.load_json(Path(case['export_dir'])/'metadata.json')
        review=dict(status="ADOPTED_SINGLE_TRAINED_PRELAYOUT_CASE" if main_b or main_a or main_510b else "ADOPTED_QUALIFIED_TABLE_RANGE_PRELAYOUT_CASE",case_id=case_id,
            policy=policy,measured_cycles=meta['measured_cycles'],total_checked_cycles=meta['total_cycles'],
            downloaded_hashes=files,blocking_issues=[],replay=ix.load_json(reports/"replay-audit.json"),
            pt=ix.load_json(reports/"pilot-audit.json")["pt"],reviewer_sha256=ix.sha256_file(reviewer),
            original_transport_exits=dict(preflight=0,upload=0,power=255,fetch=255),
            recovery_inspection_exit=0,recovery_fetch_exit=0,stage_exits={s:"0" for s in inspection["actual_exits"]},
            recovery_result_sha256=ix.sha256_file(recovery/"result.json"),
            original_transcript_sha256=ix.sha256_file(original/"command-transcript.json"))
        self.write(recovery/"review.json",review)
        self.write(recovery/"parent-review.json",dict(review,checked_utc="parent"))
        release=dict(schema="cxl-recovered-main510b-semantic-release-v1" if main_510b else "cxl-recovered-main510a-semantic-release-v1" if main_a else "cxl-recovered-main509b-semantic-release-v1" if main_b else "cxl-recovered-fcfs509a-semantic-release-v1",
            status="PARENT_ACCEPTED_RECOVERED_MAIN510B_RELEASE_REMAINING6" if main_510b else "PARENT_ACCEPTED_RECOVERED_MAIN510A_RELEASE_REMAINING7" if main_a else "PARENT_ACCEPTED_RECOVERED_MAIN509B_RELEASE_REMAINING12" if main_b else "PARENT_ACCEPTED_RECOVERED_FCFS509A_RELEASE_REMAINING16",case_id=case_id,
            semantic_receipt=str(recovery/"parent-review.json"),semantic_sha256=ix.sha256_file(recovery/"parent-review.json"),
            independent_reviewer=str(reviewer),reviewer_sha256=ix.sha256_file(reviewer),
            original_transport_exits_preserved=dict(power=255,fetch=255),actual_EDA_exit=0,
            recovery_transport_exit=0,qualified_table_range_warnings=0,matrix_contribution=0)
        if main_b:
            adapter=recovery/'semantic-remaining/continuation/review_recovered_mainb.py'
            adapter.parent.mkdir(parents=True);adapter.write_text('# immutable MainB adapter\n')
            caller=adapter.parent.parent/'calibration-review-1657/review_calibrated.py'
            caller.parent.mkdir();caller.write_text('# immutable calibrated caller\n')
            frozen=adapter.parent.parent.parent/'semantic-recovery-fcfs509a/review_recovery.py'
            frozen.parent.mkdir();frozen.write_text('# immutable recovery reviewer\n')
            base=adapter.parent.parent/'review.py';base.write_text('# immutable base\n')
            review.update(reviewer_sha256=ix.sha256_file(frozen),frozen_recovery_reviewer_sha256=ix.sha256_file(frozen),
                          recovery_adapter_sha256=ix.sha256_file(adapter),calibrated_caller_sha256=ix.sha256_file(caller))
            self.write(recovery/'review.json',review);self.write(recovery/'parent-review.json',dict(review,checked_utc='parent'))
            release.update(semantic_receipt=str(recovery/'review.json'),semantic_sha256=ix.sha256_file(recovery/'review.json'),
                parent_semantic_receipt=str(recovery/'parent-review.json'),parent_semantic_sha256=ix.sha256_file(recovery/'parent-review.json'),
                independent_reviewer=str(adapter),reviewer_sha256=ix.sha256_file(adapter),
                recovery_result=dict(path=str(recovery/'result.json'),sha256=ix.sha256_file(recovery/'result.json')),
                recovery_inspection=dict(path=str(recovery/'inspection.json'),sha256=ix.sha256_file(recovery/'inspection.json')))
            for name,val in [('POWER_MAINB_ADAPTER_SHA',ix.sha256_file(adapter)),('POWER_MAINB_CALLER_SHA',ix.sha256_file(caller)),
                             ('POWER_MAINB_FROZEN_REVIEWER_SHA',ix.sha256_file(frozen)),('POWER_MAINB_BASE_SHA',ix.sha256_file(base))]:
                patcher=mock.patch.object(ix,name,val,create=True);patcher.start();self.addCleanup(patcher.stop)
        if main_a or main_510b:
            adapter=recovery/('semantic-main510b/review_main510b.py' if main_510b else 'semantic-main510a/review_main510a.py')
            adapter.parent.mkdir();adapter.write_text('# immutable Main510A adapter\n')
            sem=adapter.parent.parent/'power-sol/remote-preparation/continuation-1258/semantic-remaining'
            caller=sem/'calibration-review-1657/review_calibrated.py'
            caller.parent.mkdir(parents=True);caller.write_text('# immutable calibrated caller\n')
            frozen=sem.parent/'semantic-recovery-fcfs509a/review_recovery.py'
            frozen.parent.mkdir();frozen.write_text('# immutable recovery reviewer\n')
            base=sem/'review.py';base.write_text('# immutable base\n')
            plan['continuation_plan_sha256']='c'*64;self.write(recovery/'plan.json',plan)
            review.update(reviewer_sha256=ix.sha256_file(frozen),frozen_recovery_reviewer_sha256=ix.sha256_file(frozen),
                recovery_adapter_sha256=ix.sha256_file(adapter),calibration_caller_sha256=ix.sha256_file(caller),
                base_reviewer_sha256=ix.sha256_file(base),recovery_plan_sha256=ix.sha256_file(recovery/'plan.json'),
                continuation_plan_sha256=plan['continuation_plan_sha256'])
            if main_510b:
                main510a=recovery/'semantic-main510a-20261025t1550/review_main510a.py'
                main510a.parent.mkdir();main510a.write_text('# immutable prior Main510A adapter\n')
                review['adapted_from_main510a_sha256']=ix.sha256_file(main510a)
                patcher=mock.patch.object(ix,'POWER_MAIN510A_ADAPTER_SHA',ix.sha256_file(main510a))
                patcher.start();self.addCleanup(patcher.stop)
            self.write(recovery/'review.json',review);self.write(recovery/'parent-review.json',dict(review,checked_utc='parent'))
            release.pop('qualified_table_range_warnings')
            release.update(semantic_sha256=ix.sha256_file(recovery/'parent-review.json'),
                independent_reviewer=str(adapter),reviewer_sha256=ix.sha256_file(adapter),
                recovery_result=dict(path=str(recovery/'result.json'),sha256=ix.sha256_file(recovery/'result.json')),
                recovery_inspection=dict(path=str(recovery/'inspection.json'),sha256=ix.sha256_file(recovery/'inspection.json')))
            if main_510b:
                release['independent_semantic_receipt']=dict(path=str(recovery/'review.json'),sha256=ix.sha256_file(recovery/'review.json'))
            for name,val in [('POWER_MAIN510B_ADAPTER_SHA' if main_510b else 'POWER_MAIN510A_ADAPTER_SHA',ix.sha256_file(adapter)),
                             ('POWER_MAIN510A_REVIEW_SHA',ix.sha256_file(recovery/'review.json')),
                             ('POWER_MAINB_CALLER_SHA',ix.sha256_file(caller)),
                             ('POWER_MAINB_FROZEN_REVIEWER_SHA',ix.sha256_file(frozen)),('POWER_MAINB_BASE_SHA',ix.sha256_file(base))]:
                patcher=mock.patch.object(ix,name,val,create=True);patcher.start();self.addCleanup(patcher.stop)
        self.write(recovery/"parent-release.json",release)
        case["semantic_receipt"]=dict(path=str(recovery/"parent-release.json"),sha256=ix.sha256_file(recovery/"parent-release.json"))
        case["recovery"]={k:dict(path=str(recovery/n),sha256=ix.sha256_file(recovery/n)) for k,n in
            dict(plan="plan.json",inspection="inspection.json",result="result.json",inspect_exit="inspect-exit.json",
                 fetch_exit="fetch-exit.json",fetch_archive="fetch.tar",reviewer_receipt="review.json").items()}
        self.write(path,dict(schema=ix.POWER_MANIFEST,cases=cases))
        patcher=mock.patch.object(ix,"POWER_REVIEW_RELEASE_SHA256",ix.POWER_REVIEW_RELEASE_SHA256 | {case["semantic_receipt"]["sha256"]})
        patcher.start();self.addCleanup(patcher.stop)
        patcher=mock.patch.object(ix,"POWER_RECOVERED_REVIEW_SHA256",ix.sha256_file(recovery/"review.json"),create=True)
        patcher.start();self.addCleanup(patcher.stop)
        return path,case,recovery

    def test_recovered_main510b_pairs_with_main510a_and_missing_b_zero(self):
        path,case,recovery=self.recovered_fixture('fai-main','B',with_pair=True,seed=510)
        result=ix.inspect_power_case(case,path.parent)
        self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['original_transport_exits'],dict(preflight=0,upload=0,power=255,fetch=255))
        self.assertEqual(result['recovery_actual_eda_exits'],dict(compile=0,sim=0,pt=0,shell_exit=0))
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],1)
        manifest=ix.load_json(path);manifest['cases']=[c for c in manifest['cases'] if c['arm']=='A']
        self.write(path,manifest)
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)

    def test_recovered_main510b_rejects_wrong_identity_release_and_original_zero(self):
        path,case,recovery=self.recovered_fixture('fai-main','B',seed=510)
        for key,value in [('arm','A'),('seed',509),('seed',511),('policy','rr')]:
            with self.subTest(key=key,value=value):
                self.assertNotEqual(ix.inspect_power_case(dict(case,**{key:value}),path.parent)['status'],'PASS')
        receipt=Path(case['semantic_receipt']['path']);before=receipt.read_bytes()
        for key,value in [('case_id','fai-main-A-s510'),('status','PENDING'),('actual_EDA_exit',False),
                          ('schema','cxl-recovered-main510a-semantic-release-v1'),
                          ('qualified_table_range_warnings',1),
                          ('recovery_result',ix.load_json(receipt)['recovery_inspection'])]:
            with self.subTest(key=key):
                release=ix.load_json(receipt);release[key]=value;self.write(receipt,release)
                changed=dict(case,semantic_receipt=dict(path=str(receipt),sha256=ix.sha256_file(receipt)))
                with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
                    self.assertNotEqual(ix.inspect_power_case(changed,path.parent)['status'],'PASS')
                receipt.write_bytes(before)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset()):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        original=Path(case['remote_dir']);transcript=ix.load_json(original/'command-transcript.json')
        for stage in ['power','fetch']:
            transcript['stages'][stage]['exit']=0
            self.write(original/f'transport/{stage}.exit.json',dict(outer_exit=0))
        self.write(original/'command-transcript.json',transcript)
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_main510b_requires_dual_receipt_and_frozen_reviewer_chain(self):
        path,case,recovery=self.recovered_fixture('fai-main','B',seed=510)
        receipt=Path(case['semantic_receipt']['path']);release=ix.load_json(receipt)
        adapter=Path(release['independent_reviewer'])
        sem=adapter.parent.parent/'power-sol/remote-preparation/continuation-1258/semantic-remaining'
        for p in [Path(release['semantic_receipt']),recovery/'review.json',adapter,
                  sem/'calibration-review-1657/review_calibrated.py',
                  sem.parent/'semantic-recovery-fcfs509a/review_recovery.py',sem/'review.py',
                  adapter.parent.parent/'semantic-main510a-20261025t1550/review_main510a.py']:
            with self.subTest(path=str(p)):
                before=p.read_bytes();p.write_bytes(b'changed')
                self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS',str(p))
                p.write_bytes(before)
        # Even a rebound parent hash/pin cannot replace independently accepted semantic content.
        parent=Path(release['semantic_receipt']);review=ix.load_json(parent);review['blocking_issues']=['bad']
        self.write(parent,review);release['semantic_sha256']=ix.sha256_file(parent)
        self.write(receipt,release);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_main510b_rejects_changed_actual_payload_source_and_archive(self):
        path,case,recovery=self.recovered_fixture('fai-main','B',seed=510)
        self.assertEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        original=Path(case['remote_dir'])
        for p in [recovery/'fetch.tar',original/'payload.tar',recovery/'results/reports/source.sha256',
                  recovery/'results/activity.saif',recovery/'inspection.json',recovery/'result.json']:
            with self.subTest(path=str(p)):
                before=p.read_bytes();p.write_bytes(before+b'changed')
                self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
                p.write_bytes(before)
        plan=ix.load_json(recovery/'plan.json');plan['continuation_plan_sha256']='e'*64
        self.write(recovery/'plan.json',plan)
        case['recovery']['plan']['sha256']=ix.sha256_file(recovery/'plan.json')
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_main510a_preserves255_without_adding_unpaired_row(self):
        path,case,recovery=self.recovered_fixture('fai-main','A',seed=510)
        result=ix.inspect_power_case(case,path.parent)
        self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['original_transport_exits'],dict(preflight=0,upload=0,power=255,fetch=255))
        self.assertEqual(result['recovery_actual_eda_exits'],dict(compile=0,sim=0,pt=0,shell_exit=0))
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)

    def test_recovered_main510a_rejects_wrong_case_pending_release_and_synthetic_zero(self):
        path,case,recovery=self.recovered_fixture('fai-main','A',seed=510)
        for key,value in [('arm','B'),('seed',509),('policy','rr')]:
            with self.subTest(key=key):
                self.assertNotEqual(ix.inspect_power_case(dict(case,**{key:value}),path.parent)['status'],'PASS')
        receipt=Path(case['semantic_receipt']['path']);before=receipt.read_bytes()
        for key,value in [('case_id','fai-main-B-s509'),('status','PENDING'),('actual_EDA_exit',False),
                          ('schema','cxl-recovered-main509b-semantic-release-v1'),
                          ('qualified_table_range_warnings',1),
                          ('recovery_result',ix.load_json(receipt)['recovery_inspection'])]:
            with self.subTest(key=key):
                v=ix.load_json(receipt);v[key]=value;self.write(receipt,v)
                case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
                with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
                    self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
                receipt.write_bytes(before)
        case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset()):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        no_release=copy.deepcopy(case);del no_release['semantic_receipt']
        self.assertNotEqual(ix.inspect_power_case(no_release,path.parent)['status'],'PASS')
        original=Path(case['remote_dir']);transcript=ix.load_json(original/'command-transcript.json')
        for stage in ('power','fetch'):
            transcript['stages'][stage]['exit']=0;self.write(original/f'transport/{stage}.exit.json',dict(outer_exit=0))
        self.write(original/'command-transcript.json',transcript)
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_main510a_rejects_rebound_active_failed_source_payload_and_plan(self):
        path,case,recovery=self.recovered_fixture('fai-main','A',seed=510)
        mutations=[('inspection','processes',[dict(pid=7)]),('inspection','status','PENDING'),
            ('inspection','actual_exits',dict(compile=0,sim=1,pt=0,shell_exit=0)),
            ('result','status','EXISTING_MAIN509B_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED'),
            ('result','actual_EDA_exit',1),('plan','payload_sha256','0'*64),
            ('plan','expected_source_record',{}),('plan','continuation_plan_sha256','0'*64),
            ('plan','schema','cxl-inspect-fetch-existing-main509b-v1')]
        for field,key,value in mutations:
            with self.subTest(field=field,key=key):
                p=Path(case['recovery'][field]['path']);before=p.read_bytes();old=case['recovery'][field]['sha256']
                v=ix.load_json(p);v[key]=value;self.write(p,v);case['recovery'][field]['sha256']=ix.sha256_file(p)
                self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
                p.write_bytes(before);case['recovery'][field]['sha256']=old
        for p in [Path(case['export_dir'])/'source-freeze.zip',Path(case['remote_dir'])/'payload.tar',
                  recovery/'results/reports/exits.txt',recovery/'results/activity.saif']:
            before=p.read_bytes();p.write_bytes(b'changed')
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS',str(p));p.write_bytes(before)

    def test_recovered_main510a_requires_dual_review_and_exact_reviewer_sources(self):
        path,case,recovery=self.recovered_fixture('fai-main','A',seed=510)
        release=ix.load_json(Path(case['semantic_receipt']['path']));adapter=Path(release['independent_reviewer'])
        sem=adapter.parent.parent/'power-sol/remote-preparation/continuation-1258/semantic-remaining'
        for p in [Path(release['semantic_receipt']),recovery/'review.json',adapter,
                  sem/'calibration-review-1657/review_calibrated.py',
                  sem.parent/'semantic-recovery-fcfs509a/review_recovery.py',sem/'review.py']:
            before=p.read_bytes();p.write_bytes(b'changed')
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS',str(p));p.write_bytes(before)
        # Rebind the parent digest and release pin: semantic disagreement must still fail.
        parent=Path(release['semantic_receipt']);review=ix.load_json(parent);review['blocking_issues']=['bad']
        self.write(parent,review);release['semantic_sha256']=ix.sha256_file(parent)
        receipt=Path(case['semantic_receipt']['path']);self.write(receipt,release)
        case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_mainb_pairs_with_main_a_and_missing_b_does_not_pass(self):
        path,case,recovery=self.recovered_fixture('fai-main','B',with_pair=True)
        result=ix.inspect_power_case(case,path.parent);self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['original_transport_exits']['power'],255)
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],1)
        m=ix.load_json(path);m['cases']=[c for c in m['cases'] if c['arm']=='A'];self.write(path,m)
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)

    def test_recovered_mainb_rejects_altered_receipt_wrong_case_and_synthetic_zero(self):
        path,case,recovery=self.recovered_fixture('fai-main','B')
        for key,value in [('arm','A'),('policy','rr'),('seed',510)]:
            wrong=dict(case,**{key:value});self.assertNotEqual(ix.inspect_power_case(wrong,path.parent)['status'],'PASS')
        receipt=Path(case['semantic_receipt']['path']);old=receipt.read_bytes();v=ix.load_json(receipt)
        v['case_id']='fai-main-A-s509';self.write(receipt,v);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        receipt.write_bytes(old);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        original=Path(case['remote_dir']);transcript=ix.load_json(original/'command-transcript.json')
        for stage in ['power','fetch']:
            transcript['stages'][stage]['exit']=0;self.write(original/f'transport/{stage}.exit.json',dict(outer_exit=0))
        self.write(original/'command-transcript.json',transcript)
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_mainb_requires_both_reviews_and_calibrated_source_guards(self):
        path,case,recovery=self.recovered_fixture('fai-main','B');release=ix.load_json(Path(case['semantic_receipt']['path']))
        adapter=Path(release['independent_reviewer'])
        for p in [Path(release['parent_semantic_receipt']),adapter,
                  adapter.parent.parent/'calibration-review-1657/review_calibrated.py',
                  adapter.parent.parent.parent/'semantic-recovery-fcfs509a/review_recovery.py',adapter.parent.parent/'review.py']:
            before=p.read_bytes();p.write_bytes(b'changed')
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS',str(p));p.write_bytes(before)

    def test_recovered_power_accepts_actual_eda_preserving_original255_and_zero_rows(self):
        path,case,recovery=self.recovered_fixture()
        result=ix.inspect_power_case(case,path.parent)
        self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(result['original_transport_exits'],dict(preflight=0,upload=0,power=255,fetch=255))
        self.assertEqual(result['recovery_actual_eda_exits'],dict(compile=0,sim=0,pt=0,shell_exit=0))
        self.assertEqual(ix.build_index([path])['matched_power']['accepted_rows'],0)
        self.assertFalse((Path(case['remote_dir'])/'results').exists())

    def test_recovered_power_rejects_rebound_mutations_not_just_stale_hashes(self):
        path,case,recovery=self.recovered_fixture()
        mutations=[('inspection','processes',[dict(pid=1)]),('inspection','remote_root','/wrong'),
            ('inspection','actual_exits',dict(compile=0,sim=1,pt=0,shell_exit=0)),
            ('result','actual_EDA_exit',False),('result','files',{}),('inspect_exit','outer_exit',255),
            ('fetch_exit','outer_exit',255),('plan','case_id','rr-A-s509'),
            ('plan','payload_sha256','0'*64),('reviewer_receipt','blocking_issues',['bad'])]
        for field,key,value in mutations:
            with self.subTest(field=field,key=key):
                p=Path(case['recovery'][field]['path']);original=p.read_bytes();v=ix.load_json(p);v[key]=value
                self.write(p,v);old=case['recovery'][field]['sha256'];case['recovery'][field]['sha256']=ix.sha256_file(p)
                self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
                p.write_bytes(original);case['recovery'][field]['sha256']=old
        original=Path(case['remote_dir'])/'transport/power.exit.json';self.write(original,dict(outer_exit=0))
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_recovered_power_cannot_pass_without_reports_archive_or_approved_parent(self):
        path,case,recovery=self.recovered_fixture()
        for p in [recovery/'results/activity.saif', recovery/'results/reports/exits.txt',
                  recovery/'results/reports/source-after.sha256', recovery/'fetch.tar']:
            before=p.read_bytes();p.write_bytes(b'bad')
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS',str(p))
            p.write_bytes(before)
        missing=copy.deepcopy(case);del missing['recovery']
        self.assertNotEqual(ix.inspect_power_case(missing,path.parent)['status'],'PASS')
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset()):
            self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def reseal_recovery(self, case, recovery, duplicate=False):
        """Rebind all mutable transport hashes so rejection must inspect the actual content."""
        inspection=ix.load_json(recovery/'inspection.json')
        inspection['files']={p.relative_to(recovery/'results').as_posix():ix.sha256_file(p)
                            for p in (recovery/'results').rglob('*') if p.is_file()}
        self.write(recovery/'inspection.json',inspection)
        with tarfile.open(recovery/'fetch.tar','w') as archive:
            for n in inspection['files']:archive.add(recovery/'results'/n,arcname=n)
            if duplicate:archive.add(recovery/'results/activity.saif',arcname='activity.saif')
        result=ix.load_json(recovery/'result.json')
        result.update(files=inspection['files'],inspected_manifest_sha256=ix.sha256_file(recovery/'inspection.json'),
                      archive_sha256=ix.sha256_file(recovery/'fetch.tar'))
        self.write(recovery/'result.json',result)
        for ref in case['recovery'].values():ref['sha256']=ix.sha256_file(Path(ref['path']))

    def test_recovered_power_actual_eda_failure_rejected_even_with_rebound_fetch0(self):
        path,case,recovery=self.recovered_fixture()
        (recovery/'results/reports/exits.txt').write_text('compile=0\nsim=1\npt=0\nshell_exit=0\n')
        self.reseal_recovery(case,recovery)
        result=ix.inspect_power_case(case,path.parent)
        self.assertNotEqual(result['status'],'PASS')
        self.assertIn('remote stage exit mismatch',result['problems'][0])

    def test_recovered_power_duplicate_tar_and_changed_accepted_reviewer_rejected(self):
        path,case,recovery=self.recovered_fixture()
        self.reseal_recovery(case,recovery,duplicate=True)
        result=ix.inspect_power_case(case,path.parent)
        self.assertIn('unsafe/duplicate',result['problems'][0])
        self.reseal_recovery(case,recovery)
        # Restore the review's exact result binding after rebuilding the fixture tar.
        (recovery/'reviewer.py').write_text('# changed accepted reviewer\n')
        result=ix.inspect_power_case(case,path.parent)
        self.assertNotEqual(result['status'],'PASS')
        self.assertIn('accepted reviewer guard',result['problems'][0])

    def calibrated_fixture(self):
        path=self.power_fixture()
        manifest=ix.load_json(path)
        caller=path.parent/'calibration/caller/review_calibrated.py'
        caller.parent.mkdir(parents=True)
        caller.write_text('# immutable calibrated caller fixture\n')
        base=caller.parent.parent/'review.py';base.write_text('# immutable base reviewer fixture\n')
        pins=set()
        for case in manifest['cases']:
            receipt=Path(case['semantic_receipt']['path']);wrapper=ix.load_json(receipt)
            review_path=Path(wrapper['independent_review']);review=ix.load_json(review_path)
            review['replay']=review.pop('checker_replay');review['pt']=review.pop('checker_pt')
            review.update(calibration_caller_sha256=ix.sha256_file(caller),
                          base_reviewer_sha256=ix.sha256_file(base),reviewer_sha256=ix.sha256_file(base))
            self.write(review_path,review)
            wrapper.update(review_contract='calibrated-replay-pt-v1',calibrated_reviewer=str(caller),
                calibrated_reviewer_sha256=ix.sha256_file(caller),base_reviewer_sha256=ix.sha256_file(base),
                independent_review_sha256=ix.sha256_file(review_path))
            self.write(receipt,wrapper);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
            pins.add(ix.sha256_file(receipt))
        self.write(path,manifest)
        patcher=mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset(pins));patcher.start();self.addCleanup(patcher.stop)
        return path,manifest['cases'],caller,base

    def test_calibrated_actual_fields_accept_pair_and_missing_b_is_unresolved(self):
        path,cases,caller,base=self.calibrated_fixture()
        index=ix.build_index([path]);self.assertEqual(index['matched_power']['accepted_rows'],1)
        self.write(path,dict(schema=ix.POWER_MANIFEST,cases=cases[:1]))
        index=ix.build_index([path]);self.assertEqual(index['matched_power']['accepted_rows'],0)
        self.assertEqual(index['matrix']['counts']['UNRESOLVED'],1)

    def test_calibrated_rebound_contract_caller_base_and_actual_audits_rejected(self):
        path,cases,caller,base=self.calibrated_fixture();case=cases[1]
        wrapper_path=Path(case['semantic_receipt']['path']);wrapper=ix.load_json(wrapper_path)
        review_path=Path(wrapper['independent_review']);review=ix.load_json(review_path)
        for target,key,value in [('wrapper','review_contract','unknown'),
                ('wrapper','calibrated_reviewer_sha256','0'*64),('wrapper','base_reviewer_sha256','0'*64),
                ('review','calibration_caller_sha256','0'*64),('review','base_reviewer_sha256','0'*64),
                ('review','reviewer_sha256','0'*64),('review','replay',{}),('review','pt',{}),
                ('review','blocking_issues',['bad'])]:
            with self.subTest(target=target,key=key):
                w,r=copy.deepcopy(wrapper),copy.deepcopy(review)
                (w if target=='wrapper' else r)[key]=value
                self.write(review_path,r);w['independent_review_sha256']=ix.sha256_file(review_path)
                self.write(wrapper_path,w);case['semantic_receipt']['sha256']=ix.sha256_file(wrapper_path)
                with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(wrapper_path)])):
                    self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        self.write(wrapper_path,wrapper);self.write(review_path,review)

    def test_calibrated_changed_source_and_wrong_native_field_fail_closed(self):
        path,cases,caller,base=self.calibrated_fixture();case=cases[0]
        for p in [caller,base]:
            before=p.read_bytes();p.write_bytes(b'# changed\n')
            result=ix.inspect_power_case(case,path.parent)
            self.assertNotEqual(result['status'],'PASS');p.write_bytes(before)
        case['native_exit_field']='native_exit'
        self.assertNotEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')

    def test_calibrated_release_exact_pin_rejects_tamper_and_wrong_binding(self):
        path,cases,caller,base=self.calibrated_fixture();case=cases[0]
        self.assertEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')
        receipt=Path(case['semantic_receipt']['path']);original=receipt.read_bytes()
        wrapper=ix.load_json(receipt);wrapper['case']['seed']=510;self.write(receipt,wrapper)
        # Even a caller-updated reference cannot replace the independently pinned release.
        case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        result=ix.inspect_power_case(case,path.parent)
        self.assertNotEqual(result['status'],'PASS');self.assertIn('not pinned',result['problems'][0])
        # Inspect the binding guard independently of the allowlist check.
        with mock.patch.object(ix,'POWER_REVIEW_RELEASE_SHA256',frozenset([ix.sha256_file(receipt)])):
            result=ix.inspect_power_case(case,path.parent)
            self.assertNotEqual(result['status'],'PASS');self.assertIn('binding mismatch',result['problems'][0])
        receipt.write_bytes(original);case['semantic_receipt']['sha256']=ix.sha256_file(receipt)
        self.assertEqual(ix.inspect_power_case(case,path.parent)['status'],'PASS')


if __name__ == "__main__":
    unittest.main()
