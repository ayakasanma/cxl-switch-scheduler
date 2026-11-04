"""Sealed source-bound fixtures, never production simulation."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import analyze_revision_results as analysis
import index_revision_evidence as evidence
from revision_matrix import CONFIRMATION, EXPLORATION
import test_index_revision_evidence as index_tests
from run_revision_experiments import Traffic


def distribution(cycles, count):
    if count == 0:
        return dict(histogram={}, count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None)
    return dict(histogram={str(cycles): count},
                **analysis.histogram_summary({str(cycles): count}))


def metrics(job, cycles=20, lane="trained"):
    cohorts, phases = {}, {}
    names = ("training", "A", "A_guard", "B", "B_guard", "drain")
    for name in names:
        active = name in ("A", "B") and (lane == "trained" or lane == "cold-" + name)
        guard = name.endswith("_guard") and (lane == "trained" or lane == "cold-" + name[0])
        n = job["n_src"]
        slots = (100_000 if name == "A" else 102_400) if active else 1024 if guard else 0
        fires = 2 if active else 1 if guard else 0
        summary = dict(count=slots, mean=1 if slots else None, min=0 if slots else None,
                       max=2 if slots else None, end=1 if active else 0 if guard else None)
        gap = dict(count=1, mean=4, p99_nearest_rank=4, min=4, max=4,
                   distinct_values=1, histogram={"4": 1})
        phases[name] = dict(
            cycles=slots, ready=slots, generated=[3 if active else 0] * n,
            offered=[4 if active else 0] * n, accepted=[3 if active else 0] * n,
            fired=[fires] * n, eligible_ready_opportunities=fires * n,
            avoidable_bubbles=0, eligible_ready_utilization=1.0 if slots else None,
            backlog=[copy.deepcopy(summary) for _ in range(n)],
            occupancy=[copy.deepcopy(summary) for _ in range(n)],
            gaps=[dict(empty_terminated_episodes=0, samples={
                "inter_service": dict(wall_cycles=copy.deepcopy(gap),
                                      eligible_ready_opportunities=copy.deepcopy(gap))} if slots else {})
                  for _ in range(n)])
    for name in ("cold", "A", "B"):
        active = name in ("A", "B") and (lane == "trained" or lane == "cold-" + name)
        count = 3 if active else 0
        stage_cycles = dict(zip(analysis.STAGES, (2, cycles - 2, cycles)))
        sources = [{stage: distribution(stage_cycles[stage], count) for stage in analysis.STAGES}
                   for _ in range(job["n_src"])]
        cohorts[name] = dict(
            generated=[count] * n, completed=[count] * n,
            completed_by_phase={p: [2 if active and p == name else
                                     1 if active and p == name + "_guard" else 0] * n for p in names},
            per_source=sources,
            pooled_sparse={stage: distribution(stage_cycles[stage], count * (n - 1))
                           for stage in analysis.STAGES})
    return dict(cohorts=cohorts, phases=phases)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.fixture = index_tests.EvidenceIndexTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.jobs = evidence.current_matrix()
        self.root = self.fixture.root
        self.serial = 0

    def bundle(self, policy="FCFS", seed=529, lane="trained", group="n4-confirmation", cycles=20, case=None):
        job = next(j for j in self.jobs if j["policy"] == policy and j["seed"] == seed
                   and j["group"] == group and (case is None or j.get("case") == case))
        self.fixture.row = job
        path = self.fixture.bundle(lane)
        target = self.root / str(self.serial)
        self.serial += 1
        path.rename(target)
        cfg = evidence.expected_config(job, lane)
        rel = evidence.expected_result_path(cfg, job)

        def populate(value):
            value["metrics"] = metrics(job, cycles, lane)
            value["cold"] = lane != "trained"
        self.fixture.mutate(target, rel, populate)
        return target

    def result_path(self, path):
        return next((path / "results").glob("*.json"))

    def rows(self, seeds, policy, cycles=20, profile="trained-A"):
        job = next(j for j in self.jobs if j["group"] == "n4-confirmation"
                   and j["policy"] == policy)
        config = analysis.configuration(job, "trained")
        if tuple(seeds) == EXPLORATION:
            config["seed_role"] = "exploration"
        return [dict(policy=policy, seed=seed, profile=profile,
                     configuration=copy.deepcopy(config), status="PASS", production_evidence=True,
                     source_sha256="a" * 64, trace_sha256=f"{seed:064x}",
                     **distribution(cycles, 9)) for seed in seeds]

    def test_sealed_bundle_normalizes_all_sources_stages_and_partial_coverage(self):
        path = self.bundle()
        report, originals = analysis.analyze([path])
        self.assertEqual(report["core_trained_jobs"]["accepted"], 1)
        self.assertEqual(report["core_trained_jobs"]["planned"], 120)
        self.assertEqual(len(report["endpoints"]), 2)
        row = report["endpoints"][0]
        self.assertEqual(len(row["per_source"]), 4)
        self.assertEqual(set(row["pooled_sparse"]), set(analysis.STAGES))
        self.assertEqual((row["p50"], row["p90"], row["p99"], row["p999"], row["max"], row["count"]),
                         (20, 20, 20, 20, 20, 9))
        self.assertEqual(len(originals), 6)
        comparison = next(c for c in report["comparisons"] if c["profile"] == "trained-A"
                          and c["baseline"] == "FCFS" and c["candidate_configuration"]["group"] == "n4-confirmation")
        self.assertEqual(comparison["missing_seeds"]["baseline"], list(range(530, 549)))
        self.assertEqual(comparison["missing_seeds"]["candidate"], list(CONFIRMATION))
        self.assertNotIn("paired_bootstrap", comparison)

    def test_fixed_seed_bootstrap_and_descriptive_exploration(self):
        a = self.rows(CONFIRMATION, "FCFS")
        b = self.rows(CONFIRMATION, "MAIN", 18)
        paired = analysis.compare_cohort(a, b, CONFIRMATION)
        self.assertEqual(paired["n"], 20)
        self.assertEqual(paired["paired_bootstrap"],
                         dict(replicates=10000, rng_seed=20261023, percentile95=[-2, -2]))
        self.assertEqual(paired, analysis.compare_cohort(a[::-1], b, CONFIRMATION))
        desc = analysis.compare_cohort(self.rows(EXPLORATION, "FCFS"),
                                       self.rows(EXPLORATION, "MAIN", 18), EXPLORATION)
        self.assertNotIn("paired_bootstrap", desc)
        self.assertEqual(desc["interval_status"], "NOT_COMPUTED_EXPLORATION_ONLY")
        partial = analysis.compare_cohort(a[:-1], b, CONFIRMATION)
        self.assertEqual(partial["missing_seeds"]["baseline"], [548])
        self.assertNotIn("mean_p99_delta_cycles", partial)

    def dac_rows(self, seeds, ready="always"):
        baseline, candidate = [], []
        shared = {name: "a" * 64 for name in analysis.core_source_paths()}
        for seed in seeds:
            job = next(j for j in self.jobs if j["policy"] == "INSIGHT_WINNER"
                       and j["seed"] == seed and j["ready"] == ready)
            main = analysis.dac_main_job(job, self.jobs)
            for rows, policy, selected, hashes, cycles in (
                (baseline, "MAIN", main, shared, 20),
                (candidate, "DAC2", job, dict(shared, **{"rtl/experimental/dac.sv": "b" * 64}), 18),
            ):
                rows.append(dict(
                    policy=policy, matrix_job_id=selected["id"], seed=seed, profile="trained-A",
                    configuration=analysis.configuration(selected, "trained"),
                    status="PASS", production_evidence=True, source_hashes=hashes,
                    source_sha256=evidence.canonical_sha(hashes),
                    trace_sha256=f"{seed:064x}", trace_config=dict(seed=seed, ready=ready),
                    **distribution(cycles, 9)))
        return baseline, candidate

    def test_dac_pairs_shared_core_superset_without_equating_full_manifests(self):
        a, b = self.dac_rows(CONFIRMATION)
        self.assertNotEqual(a[0]["source_sha256"], b[0]["source_sha256"])
        result = analysis.compare_dac_cohort(a, b, CONFIRMATION, self.jobs)
        self.assertEqual(result["n"], 20)
        self.assertEqual(result["paired_bootstrap"]["percentile95"], [-2, -2])
        self.assertEqual(b[0]["configuration"]["group"], "insight-confirmation")
        with patch.object(analysis, "paired_runs", side_effect=AssertionError("unexpected inference")):
            partial = analysis.compare_dac_cohort(a, b[:-1], CONFIRMATION, self.jobs)
        self.assertEqual(partial["missing_seeds"]["candidate"], [548])
        self.assertNotIn("paired_bootstrap", partial)
        for ready in ("bernoulli-0.75", "periodic-48/64"):
            a, b = self.dac_rows(EXPLORATION, ready)
            result = analysis.compare_dac_cohort(a, b, EXPLORATION, self.jobs)
            self.assertEqual(result["n"], 5)
            self.assertNotIn("paired_bootstrap", result)

    def test_dac_pairing_rejects_source_trace_config_and_policy_mismatches(self):
        for mutation in (
            lambda r: r["source_hashes"].update({"scripts/run_verify.py": "c" * 64}),
            lambda r: r.update(trace_sha256="c" * 64),
            lambda r: r.update(trace_config=dict(seed=529, ready="different")),
            lambda r: r.update(policy="DAC1"),
            lambda r: r["configuration"].update(depth=32),
        ):
            a, b = self.dac_rows(CONFIRMATION[:1])
            mutation(b[0])
            with self.assertRaises(ValueError):
                analysis.compare_dac_cohort(a, b, CONFIRMATION, self.jobs)
        a, b = self.dac_rows(CONFIRMATION[:1])
        a[0]["source_hashes"].pop("scripts/run_verify.py")
        with self.assertRaisesRegex(ValueError, "shared core source closure"):
            analysis.compare_dac_cohort(a, b, CONFIRMATION, self.jobs)

    def dac_bundle(self, jobs, policy="DAC2", pilot=False):
        path = self.fixture.dac_bundle(policy=policy, pilot=pilot, jobs=jobs)
        scope = evidence.load_json(path / "dac_performance_scope.json")
        for run in scope["runs"]:
            result_path = path / run["result"]
            result = evidence.load_json(result_path)
            traffic = Traffic(result["job"])
            result.update(metrics=metrics(result["job"], 18), trace_sha256=traffic.sha256,
                          trace_config=traffic.config)
            run["trace_sha256"] = traffic.sha256
            self.fixture.write(result_path, result)
        self.fixture.write(path / "dac_performance_scope.json", scope)
        self.fixture.seal(path)
        return path

    def matching_main(self, dac_path, job):
        main = analysis.dac_main_job(job, self.jobs)
        path = self.bundle("MAIN", main["seed"], group=main["group"], case=main.get("case"))
        shared = {}
        with (
            zipfile.ZipFile(dac_path / "sources.zip") as source,
            zipfile.ZipFile(path / "sources.zip", "w") as target,
        ):
            for name in analysis.core_source_paths():
                raw = source.read(name)
                shared[name] = evidence.sha256_bytes(raw)
                target.writestr(name, raw)
        for name in ("source_hashes_before.json", "source_hashes_after.json"):
            self.fixture.write(path / name, shared)
        spec = evidence.load_json(path / "frozen-spec.json")
        spec["source_sha256"] = evidence.canonical_sha(shared)
        self.fixture.write(path / "frozen-spec.json", spec)
        scope = evidence.load_json(path / "revision_scope.json")
        traffic = Traffic(main)
        scope["source_hashes"] = shared
        scope["runs"][0]["trace_sha256"] = traffic.sha256
        self.fixture.write(path / "revision_scope.json", scope)
        result_path = self.result_path(path)
        result = evidence.load_json(result_path)
        result.update(trace_config=traffic.config, trace_sha256=traffic.sha256)
        self.fixture.write(result_path, result)
        self.fixture.seal(path)
        return path

    def test_dac_strict_partial_saved_index_keeps_core_and_candidate_counts_separate(self):
        job = next(j for j in self.jobs if j["group"] == "insight-confirmation")
        dac = self.dac_bundle([job])
        main = self.matching_main(dac, job)
        index = self.root / "dac-index.json"
        saved = evidence.build_index([main, dac])
        self.assertEqual(len(saved["performance"]["accepted_records"]), 2)
        self.fixture.write(index, saved)
        with patch.object(analysis, "paired_runs", side_effect=AssertionError("unexpected inference")):
            report, originals = analysis.analyze(index=index)
        self.assertEqual(report["core_trained_jobs"]["accepted"], 1)
        self.assertEqual(report["conditional_dac"]["confirmation"]["accepted"], 1)
        self.assertEqual(report["conditional_dac"]["robustness"]["accepted"], 0)
        self.assertEqual(report["core_trained_jobs"]["planned"], 120)
        self.assertEqual(len(report["conditional_dac"]["endpoints"]), 2)
        self.assertTrue(all("paired_bootstrap" not in c for c in report["conditional_dac"]["comparisons"]))
        dac_record = next(r for r in saved["performance"]["accepted_records"] if r.get("selected_policy"))
        result_raw = (dac / dac_record["result"]).read_bytes()
        self.assertEqual(originals[str(dac / dac_record["result"])], result_raw)
        for key in ("selected_policy", "declared_job_id", "result_sha256", "core_source_sha256",
                    "acceptance_binding_sha256", "matrix_contribution"):
            corrupted = copy.deepcopy(saved)
            row = next(r for r in corrupted["performance"]["accepted_records"] if r.get("selected_policy"))
            row[key] = "forged"
            self.fixture.write(index, corrupted)
            with self.subTest(key=key), self.assertRaises(ValueError):
                analysis.analyze(index=index)
        corrupted = copy.deepcopy(saved)
        row = next(r for r in corrupted["performance"]["accepted_records"] if r.get("selected_policy"))
        row["matrix_contribution"] = True
        self.fixture.write(index, corrupted)
        with self.assertRaisesRegex(ValueError, "matrix_contribution mismatch"):
            analysis.analyze(index=index)
        corrupted = copy.deepcopy(saved)
        row = next(r for r in corrupted["performance"]["accepted_records"] if r.get("selected_policy"))
        corrupted["performance"]["accepted_records"].remove(row)
        corrupted["performance"]["descriptive_records"].append(row)
        self.fixture.write(index, corrupted)
        with self.assertRaisesRegex(ValueError, "classification mismatch"):
            analysis.analyze(index=index)
        self.fixture.mutate(main, str(self.result_path(main).relative_to(main)),
                            lambda v: v["trace_config"].update(forged=True))
        with self.assertRaisesRegex(ValueError, "arrival trace_config"):
            analysis.analyze([main, dac])
        self.fixture.mutate(dac, "frozen-spec.json",
                            lambda v: v["configs"][0]["params"].update(HIGH_WEIGHT=1))
        with self.assertRaisesRegex(ValueError, "strict bundle acceptance"):
            analysis.analyze([dac])

    def test_empty_dac_plan_lists_missing_seeds_without_inference(self):
        with patch.object(analysis, "paired_runs", side_effect=AssertionError("unexpected inference")):
            report, _ = analysis.analyze()
        self.assertEqual(report["core_trained_jobs"]["planned"], 120)
        self.assertEqual(report["conditional_dac"]["confirmation"]["planned"], 20)
        self.assertEqual(report["conditional_dac"]["robustness"]["planned"], 10)
        self.assertEqual(len(report["conditional_dac"]["confirmation"]["missing_job_ids"]), 20)
        self.assertEqual(len(report["conditional_dac"]["robustness"]["missing_job_ids"]), 10)
        self.assertEqual(report["conditional_dac"]["endpoints"], [])
        comparisons = report["conditional_dac"]["comparisons"]
        self.assertEqual(len(comparisons), 6)
        self.assertTrue(all(c["status"] == "INCOMPLETE" and "paired_bootstrap" not in c for c in comparisons))

    def test_dac_strict_complete_confirmation_and_robustness_use_seed_runs(self):
        for group in ("insight-confirmation", "insight-robustness"):
            jobs = [j for j in self.jobs if j["group"] == group]
            dac = self.dac_bundle(jobs)
            mains = [self.matching_main(dac, job) for job in jobs]
            report, _ = analysis.analyze([dac, *mains])
            conditional = report["conditional_dac"]
            name = "confirmation" if group == "insight-confirmation" else "robustness"
            self.assertEqual(conditional[name]["accepted"], len(jobs))
            self.assertEqual(report["core_trained_jobs"]["accepted"],
                             20 if name == "confirmation" else 0)
            complete = [c for c in conditional["comparisons"] if c["status"] == "COMPLETE"]
            self.assertEqual(len(complete), 2 if name == "confirmation" else 4)
            for comparison in complete:
                self.assertEqual(comparison["n"], 20 if name == "confirmation" else 5)
                if name == "confirmation":
                    self.assertEqual(comparison["paired_bootstrap"]["replicates"], 10000)
                    self.assertEqual(comparison["paired_bootstrap"]["percentile95"], [-2, -2])
                else:
                    self.assertNotIn("paired_bootstrap", comparison)

    def test_dac1_and_w256_strict_descriptive_index_never_contribute(self):
        jobs = [j for j in self.jobs if j["group"] == "insight-confirmation"][:2]
        for policy, pilot in (("DAC1", False), ("DAC2", True), ("DAC1", True)):
            path = self.dac_bundle(jobs, policy, pilot)
            saved = evidence.build_index([path])
            self.assertEqual(saved["performance"]["accepted_records"], [])
            self.assertEqual(len(saved["performance"]["descriptive_records"]), 1 if pilot else 2)
            index = self.root / "descriptive-index.json"
            self.fixture.write(index, saved)
            with patch.object(analysis, "paired_runs", side_effect=AssertionError("unexpected inference")):
                report, _ = analysis.analyze(index=index)
            self.assertEqual(report["core_trained_jobs"]["accepted"], 0)
            self.assertEqual(report["conditional_dac"]["confirmation"]["accepted"], 0)
            self.assertEqual(report["conditional_dac"]["robustness"]["accepted"], 0)
            rows = report["descriptive_dac"]["endpoints"]
            self.assertEqual(len(rows), 2 if pilot else 4)
            self.assertTrue(all(r["matrix_job_id"] is None and r["matrix_contribution"] == 0 for r in rows))
            self.assertEqual(report["descriptive_dac"]["matrix_contribution"], 0)

    def test_complete_source_bound_confirmation_pipeline(self):
        paths = [self.bundle(policy, seed, cycles=cycles)
                 for policy, cycles in (("FCFS", 20), ("MAIN", 18)) for seed in CONFIRMATION]
        report, originals = analysis.analyze(paths, comparisons=[("FCFS", "MAIN")])
        self.assertEqual(report["core_trained_jobs"]["accepted"], 40)
        self.assertEqual(len(originals), 240)
        complete = [c for c in report["comparisons"] if c["status"] == "COMPLETE"]
        self.assertEqual([c["profile"] for c in complete], ["trained-A", "trained-B"])
        self.assertTrue(all(c["n"] == 20 and c["paired_bootstrap"]["percentile95"] == [-2, -2]
                            for c in complete))
        # A complete single policy must not bootstrap itself while its counterpart is absent.
        with patch.object(analysis, "paired_runs", side_effect=AssertionError("unexpected inference")):
            partial, _ = analysis.analyze(paths[:20], comparisons=[("FCFS", "MAIN")])
        self.assertTrue(all(c["status"] == "INCOMPLETE" for c in partial["comparisons"]))

    def test_complete_source_bound_exploration_pipeline(self):
        paths = [self.bundle(policy, seed, group="n-expansion", cycles=cycles)
                 for policy, cycles in (("FCFS", 20), ("MAIN", 18)) for seed in EXPLORATION]
        report, _ = analysis.analyze(paths, comparisons=[("FCFS", "MAIN")])
        complete = [c for c in report["comparisons"] if c["status"] == "COMPLETE"]
        self.assertEqual(len(complete), 2)
        self.assertTrue(all(c["n"] == 5 and not c["confirmation"]
                            and "paired_bootstrap" not in c for c in complete))
        self.assertEqual(report["core_trained_jobs"]["accepted"], 0)

    def test_unpaired_and_heterogeneous_even_when_incomplete(self):
        for mutation, message in (
            (lambda rows: rows[0].update(trace_sha256="b" * 64), "unpaired"),
            (lambda rows: rows[0].update(source_sha256="b" * 64), "heterogeneous"),
            (lambda rows: rows[0]["configuration"].update(depth=32), "heterogeneous"),
            (lambda rows: rows[0].update(policy="RR10"), "heterogeneous"),
            (lambda rows: rows.append(copy.deepcopy(rows[0])), "duplicate"),
        ):
            a, b = self.rows(CONFIRMATION[:2], "FCFS"), self.rows(CONFIRMATION[:2], "MAIN", 18)
            mutation(b)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                analysis.compare_cohort(a, b, CONFIRMATION)

    def test_corrupt_histograms_and_population_rejected_after_valid_acceptance(self):
        changes = (
            lambda v: v["pooled_sparse"]["generation_to_fire"].update(p99=999),
            lambda v: v["per_source"][1]["acceptance_to_fire"]["histogram"].update({"20": -1}),
            lambda v: v["pooled_sparse"].update(generation_to_fire=distribution(19, 9)),
            lambda v: v["completed"].__setitem__(1, 2),
            lambda v: v["per_source"][0]["generation_to_acceptance"]["histogram"].update({"020": 3}),
        )
        for change in changes:
            path = self.bundle()
            rel = str(self.result_path(path).relative_to(path))
            self.fixture.mutate(path, rel, lambda value: change(value["metrics"]["cohorts"]["A"]))
            self.assertEqual(evidence.inspect_performance_bundle(
                path, {j["id"]: j for j in self.jobs})["status"], "PASS")
            with self.assertRaises(ValueError):
                analysis.analyze([path])

    def test_saved_index_reinspects_and_binds_hashes(self):
        path = self.bundle()
        index = self.root / "index.json"
        saved = evidence.build_index([path])
        self.fixture.write(index, saved)
        report, originals = analysis.analyze(index=index)
        self.assertEqual(len(originals), 7)
        self.assertEqual(report["core_trained_jobs"]["accepted"], 1)
        saved["performance"]["accepted_records"][0]["result_sha256"] = "0" * 64
        self.fixture.write(index, saved)
        with self.assertRaisesRegex(ValueError, "result_sha256 mismatch"):
            analysis.analyze(index=index)
        saved = evidence.build_index([path])
        extra = dict(saved["performance"]["accepted_records"][0], matrix_job_id="absent")
        saved["performance"]["accepted_records"].append(extra)
        self.fixture.write(index, saved)
        with self.assertRaisesRegex(ValueError, "accepted rows absent"):
            analysis.analyze(index=index)
        self.fixture.write(index, evidence.build_index([path]))
        self.result_path(path).write_text("{}")
        with self.assertRaisesRegex(ValueError, "strict bundle acceptance"):
            analysis.analyze(index=index)

    def test_zip_config_job_exit_and_model_boundaries_are_not_bypassed(self):
        for filename, change in (
            ("summary.json", lambda v: v["steps"][1].update(exit_codes={"sim": 1})),
            ("frozen-spec.json", lambda v: v["configs"][0]["params"].update(FAI_W=256)),
        ):
            path = self.bundle()
            self.fixture.mutate(path, filename, change)
            with self.assertRaisesRegex(ValueError, "strict bundle acceptance"):
                analysis.analyze([path])
        for field, value in (("evidence_kind", "MODEL_ONLY"), ("production_evidence", False),
                             ("job", {})):
            path = self.bundle()
            self.fixture.mutate(path, str(self.result_path(path).relative_to(path)),
                                lambda v: v.update({field: value}))
            with self.assertRaisesRegex(ValueError, "strict bundle acceptance"):
                analysis.analyze([path])
        path = self.bundle()
        (path / "sources.zip").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "strict bundle acceptance"):
            analysis.analyze([path])

    def test_optional_cold_real_payload_and_separate_job_count(self):
        paths = [self.bundle(lane=lane) for lane in ("cold-A", "cold-B")]
        for path in paths:
            inspected = evidence.inspect_performance_bundle(path, {j["id"]: j for j in self.jobs})
            self.assertEqual(inspected["status"], "PASS", inspected["failures"])
            result = evidence.load_json(self.result_path(path))
            self.assertIs(result["cold"], True)
            inactive = "B" if result["cold_cohort"] == "A" else "A"
            self.assertEqual(result["metrics"]["cohorts"][inactive]["generated"], [0] * 4)
        report, _ = analysis.analyze(paths, include_cold=True)
        self.assertEqual(report["core_trained_jobs"]["accepted"], 0)
        self.assertEqual(report["core_trained_jobs"]["planned"], 120)
        self.assertEqual([r["profile"] for r in report["endpoints"]], ["cold-A", "cold-B"])
        self.assertTrue(all(r["configuration"]["training_cycles"] == 0 for r in report["endpoints"]))
        excluded, _ = analysis.analyze(paths)
        self.assertEqual(excluded["endpoints"], [])
        index = self.root / "cold-index.json"
        self.fixture.write(index, evidence.build_index(paths))
        saved, _ = analysis.analyze(index=index, include_cold=True)
        self.assertEqual(saved["endpoints"], report["endpoints"])
        trained = self.bundle()
        combined, _ = analysis.analyze([trained, *paths], include_cold=True)
        self.assertEqual(combined["core_trained_jobs"]["accepted"], 1)
        self.assertEqual(len(combined["endpoints"]), 4)

    def test_heavy_id3_uses_physical_source_indices(self):
        path = self.bundle(seed=509, group="trained-robustness", case="heavy-id3")
        def permuted(value):
            for name, cohort in value["metrics"]["cohorts"].items():
                if not sum(cohort["generated"]):
                    continue
                cohort["generated"] = cohort["completed"] = [2, 3, 4, 11]
                for phase in cohort["completed_by_phase"]:
                    cohort["completed_by_phase"][phase] = [2, 3, 4, 11] if phase == name else [0] * 4
                for source, (cycles, count) in enumerate(zip((7, 20, 40, 1000), (2, 3, 4, 11))):
                    cohort["per_source"][source] = {
                        stage: distribution(t, count)
                        for stage, t in zip(analysis.STAGES, (2, cycles - 2, cycles))}
                for stage in analysis.STAGES:
                    hist = analysis.Counter()
                    for source in (0, 1, 2):
                        hist.update(cohort["per_source"][source][stage]["histogram"])
                    cohort["pooled_sparse"][stage] = dict(histogram=dict(hist),
                                                          **analysis.histogram_summary(hist))
                phase = value["metrics"]["phases"][name]
                phase.update(generated=[2, 3, 4, 11], offered=[3, 4, 5, 12],
                             accepted=[2, 3, 4, 11], fired=[2, 3, 4, 11],
                             eligible_ready_opportunities=20)
                value["metrics"]["phases"][name + "_guard"].update(
                    fired=[0] * 4, eligible_ready_opportunities=0, eligible_ready_utilization=None)
        self.fixture.mutate(path, str(self.result_path(path).relative_to(path)), permuted)
        report, _ = analysis.analyze([path])
        row = report["endpoints"][0]
        self.assertEqual(row["configuration"]["heavy_source"], 3)
        self.assertEqual(row["per_source"][0]["generation_to_fire"]["p99"], 7)
        self.assertEqual(row["per_source"][3]["generation_to_fire"]["p99"], 1000)
        self.assertEqual((row["count"], row["p50"], row["p99"]), (9, 20, 40))

    def test_zero_source_and_empty_selected_cohort_are_distinguished(self):
        path = self.bundle()
        def empty_source(value):
            cohort = value["metrics"]["cohorts"]["A"]
            cohort["generated"][1] = cohort["completed"][1] = 0
            for counts in cohort["completed_by_phase"].values():
                counts[1] = 0
            cohort["per_source"][1] = {s: distribution(0, 0) for s in analysis.STAGES}
            for stage, cycles in zip(analysis.STAGES, (2, 18, 20)):
                cohort["pooled_sparse"][stage] = distribution(cycles, 6)
            for name in ("A", "A_guard"):
                phase = value["metrics"]["phases"][name]
                phase["eligible_ready_opportunities"] -= phase["fired"][1]
                for key in ("generated", "offered", "accepted", "fired"):
                    phase[key][1] = 0
        rel = str(self.result_path(path).relative_to(path))
        self.fixture.mutate(path, rel, empty_source)
        report, _ = analysis.analyze([path])
        self.assertEqual(report["endpoints"][0]["per_source"][1]["generation_to_fire"]["count"], 0)
        self.assertEqual(report["endpoints"][0]["count"], 6)
        def empty_selected(value):
            value["metrics"]["cohorts"]["A"] = copy.deepcopy(value["metrics"]["cohorts"]["cold"])
        self.fixture.mutate(path, rel, empty_selected)
        with self.assertRaisesRegex(ValueError, "no sparse population"):
            analysis.analyze([path])

    def test_phase_metrics_are_preserved_without_changing_cohort_denominators(self):
        path = self.bundle()
        original = evidence.load_json(self.result_path(path))
        report, _ = analysis.analyze([path])
        for row, name in zip(report["endpoints"], ("A", "B")):
            phase = original["metrics"]["phases"][name]
            cohort = original["metrics"]["cohorts"][name]
            self.assertEqual(row["phase_metrics"], phase)
            self.assertEqual(row["completed_by_phase"], cohort["completed_by_phase"])
            self.assertEqual(phase["offered"], [4] * 4)
            self.assertEqual(phase["accepted"], [3] * 4)
            self.assertEqual(phase["fired"], [2] * 4)
            self.assertEqual(cohort["completed"], [3] * 4)
            self.assertEqual(row["count"], 9)
            self.assertIn("eligible_ready_opportunities",
                          row["phase_metrics"]["gaps"][0]["samples"]["inter_service"])
        self.assertEqual(report["core_trained_jobs"]["accepted"], 1)

    def test_adaptation_is_explicitly_excluded_from_hog_analysis(self):
        path = self.bundle(policy="MAIN", seed=509, group="adaptation")
        report, _ = analysis.analyze([path])
        self.assertEqual(report["endpoints"], [])
        self.assertIn("not full matrix analysis", report["scope"])
        excluded = [j for j in report["excluded_matrix_jobs"] if j["group"] == "adaptation"]
        self.assertEqual(len(excluded), 9)
        original = evidence.load_json(self.result_path(path))
        with self.assertRaisesRegex(ValueError, "excludes continuous adaptation"):
            analysis.normalize(original, {"lane": "trained"}, {})

    def test_output_preserves_original_bytes_and_refuses_overwrite(self):
        path = self.bundle()
        output = self.root / "analysis"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analysis.main(["--bundle", str(path), "--out", str(output)]), 0)
        raw = self.result_path(path).read_bytes()
        self.assertEqual((output / "inputs" / (evidence.sha256_bytes(raw) + ".json")).read_bytes(), raw)
        before = (output / "analysis.json").read_bytes()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            analysis.main(["--bundle", str(path), "--out", str(output)])
        self.assertEqual((output / "analysis.json").read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analysis.analyze([path, path])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            analysis.main(["--bundle", str(path), "--out", str(path / "would-change-evidence")])
        self.assertFalse((path / "would-change-evidence").exists())


if __name__ == "__main__":
    unittest.main()
