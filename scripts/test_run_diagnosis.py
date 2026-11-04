"""Runner gates for the frozen model-only diagnosis matrix."""
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import run_diagnosis as runner
from refc.cxl_model.diagnosis import (
    CONFIRMATION_SEEDS,
    EXPLORATION_SEEDS,
    comparison_specs,
    config_identity,
    policy_configs,
)


class SelectionTests(unittest.TestCase):
    def test_declared_seed_cohorts_and_smoke_subsets(self):
        self.assertEqual(runner.select_seeds("exploration", None, False), EXPLORATION_SEEDS)
        self.assertEqual(runner.select_seeds("confirmation", None, False), CONFIRMATION_SEEDS)
        self.assertEqual(runner.select_seeds("exploration", [6103, 6101], True), (6101, 6103))
        for role, seeds, smoke in (
            ("exploration", [6101], False),
            ("exploration", [6201], True),
            ("confirmation", [6101, 6102], True),
            ("exploration", [6101, 6101], True),
        ):
            with self.subTest(role=role, seeds=seeds, smoke=smoke):
                with self.assertRaises(ValueError):
                    runner.select_seeds(role, seeds, smoke)

    def test_policy_selection_and_identity_order(self):
        configured = policy_configs()
        self.assertEqual(len(configured), 9)
        identities = [config_identity(row) for row in configured]
        self.assertEqual(runner.policies_by_identity(None), configured)
        selected = runner.policies_by_identity([identities[3], identities[1]])
        self.assertEqual(
            [config_identity(row) for row in selected],
            [identities[1], identities[3]],
        )
        with self.assertRaises(ValueError):
            runner.policies_by_identity(["unknown"])
        with self.assertRaises(ValueError):
            runner.policies_by_identity([identities[0], identities[0]])
        self.assertEqual(runner.BOOTSTRAP_REPLICATES, 10_000)


class ManifestTests(unittest.TestCase):
    def manifest_args(self, output):
        seed = EXPLORATION_SEEDS[0]
        config = policy_configs()[3]
        settings = {
            "role": "exploration", "n_src": 4, "depth": 16,
            "window": 256, "windows": 1, "heavy_work": 4, "subwindow": 64,
            "heavy_source": 0, "sparse_stop": "finite Heavy completion",
            "drain": "forced-ready, cleanup only",
        }
        profiles = {"under": dict(runner.LOAD_PROFILES["under"])}
        jobs = runner.build_jobs((seed,), ("under",), (config,))
        return seed, config, settings, profiles, jobs

    def test_new_output_freezes_then_rejects_digest_tamper_and_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "run"
            seed, config, settings, profiles, jobs = self.manifest_args(output)
            manifest = runner.freeze_manifest(
                output, ["run_diagnosis.py"], "exploration", True, (seed,),
                settings, profiles, (config,), jobs,
            )
            self.assertEqual(len(manifest["manifest_sha256"]), 64)
            self.assertEqual(runner.load_manifest(output / "manifest.json")["jobs"], jobs)
            with self.assertRaises(FileExistsError):
                runner.freeze_manifest(
                    output, ["run_diagnosis.py"], "exploration", True, (seed,),
                    settings, profiles, (config,), jobs,
                )
            data = json.loads((output / "manifest.json").read_text())
            data["settings"]["window"] = 512
            runner.write_json(output / "manifest.json", data)
            with self.assertRaisesRegex(ValueError, "digest"):
                runner.load_manifest(output / "manifest.json")
            with self.assertRaises(SystemExit) as caught:
                runner.main(["--verify-manifest", str(output / "manifest.json")])
            self.assertEqual(caught.exception.code, 2)

    def test_cli_guards_never_launch_w5m_or_unlabeled_w256(self):
        for argv in (
            [],
            ["--output", "unused"],
            ["--output", "unused", "--window", "5000000"],
            ["--output", "unused", "--window", "256"],
            ["--output", "unused", "--window", "256", "--smoke"],
            ["--output", "unused", "--window", "5000000", "--smoke", "--heavy-work", "4"],
        ):
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit) as caught:
                    runner.main(argv)
                self.assertEqual(caught.exception.code, 2)

    def test_missing_required_sources_report_every_path_before_output_creation(self):
        root = Path(runner.__file__).resolve().parents[1]
        with self.assertRaisesRegex(ValueError, "nonempty"):
            runner.validate_source_paths(root, [])
        with tempfile.TemporaryDirectory() as folder:
            fixture_root = Path(folder) / "sources"
            for relative in runner.REQUIRED_SOURCE_PATHS:
                destination = fixture_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, destination)
            missing = [
                "refc/cxl_model/rr_model.py",
                "sim/performance/followup.py",
            ]
            for relative in missing:
                (fixture_root / relative).unlink()
            output = Path(folder) / "must-not-exist"
            stderr = io.StringIO()
            with patch.object(runner, "ROOT", fixture_root), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as caught:
                    runner.main([
                        "--output", str(output), "--smoke", "--window", "256",
                        "--heavy-work", "4", "--windows", "1",
                        "--seeds", "6101", "--profiles", "under",
                        "--policies", "CGOF_w2_oldest-first",
                    ])
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(output.exists())
            for relative in missing:
                self.assertIn(relative, stderr.getvalue())

    def test_fairness_cli_guards_reject_invalid_modes(self):
        suffixes = (
            ["--profiles", "under", "--fairness-horizon", "64"],
            ["--profiles", "equal", "--fairness-horizon", "0"],
            ["--profiles", "equal", "--fairness-horizon", "64", "--heavy-work", "64"],
            ["--profiles", "equal", "--initial-classes", "L", "H", "H", "H"],
            ["--profiles", "equal", "--fairness-horizon", "64", "--initial-classes", "L", "H", "H"],
            [
                "--profiles", "equal", "--fairness-horizon", "64",
                "--initial-classes", "L", "H", "H", "H",
                "--policies", "WRR_weights2-1-1-1",
            ],
        )
        for suffix in suffixes:
            with self.subTest(argv=suffix), tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / "invalid"
                argv = [
                    "--output", str(output), "--smoke", "--window", "256",
                    "--heavy-work", "65", "--seeds", "6101", *suffix,
                ]
                with self.assertRaises(SystemExit) as caught:
                    runner.main(argv)
                self.assertEqual(caught.exception.code, 2)
                self.assertFalse(output.exists())

    def test_fixed_horizon_equal_demand_smoke_records_classes(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "fixed-horizon"
            code = runner.main([
                "--output", str(output), "--smoke", "--window", "256",
                "--heavy-work", "65", "--fairness-horizon", "64",
                "--profiles", "equal", "--seeds", "6101",
                "--policies", "CGOF_w2_oldest-first",
                "--initial-classes", "L", "H", "H", "H",
            ])
            self.assertEqual(code, 0)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["settings"]["measurement_mode"], "fixed_horizon")
            self.assertEqual(manifest["settings"]["fairness_horizon"], 64)
            self.assertEqual(
                manifest["settings"]["initial_classes"], ["L", "H", "H", "H"]
            )
            result_path = next((output / "jobs").glob("*/result.json"))
            result = json.loads(result_path.read_text())["result"]
            self.assertEqual(result["mixed"]["measurement_mode"], "fixed_horizon")
            self.assertEqual(result["mixed"]["active_cycles"], 64)
            self.assertEqual(result["mixed"]["initial_classes"], ["L", "H", "H", "H"])


class SummaryTests(unittest.TestCase):
    def test_smoke_comparisons_never_become_inference(self):
        rows = [
            {
                "id": "x", "profile": "under", "seed": EXPLORATION_SEEDS[0],
                "config_id": config_identity(policy_configs()[3]),
                "status": "PASS", "endpoints": {"x": 1.0},
            }
        ]
        result = runner.comparison_summary(
            rows, (EXPLORATION_SEEDS[0],), ("under",), smoke=True
        )
        self.assertTrue(result)
        self.assertTrue(all(row["status"] == "NOT_RUN" for row in result))

    def test_complete_paired_cohort_bootstraps_each_prespecified_metric(self):
        endpoints = {
            "sparse_completed_generation_to_fire_p99": 1.0,
            "sparse_censored_at_cut": 0.0,
            "active_service_jain": 0.9,
            "active_demand_share_l1_error": 0.1,
            "heavy_completion_time_ratio_mixed_over_isolated": 1.2,
            "heavy_completion_ratio_mixed_over_isolated": 1.2,
            "heavy_span_ratio_mixed_over_isolated": 1.2,
            "heavy_active_fire_rate": 0.5,
            "heavy_throughput_ratio_mixed_over_isolated": 0.8,
            "heavy_max_service_gap": 4.0,
            "quota_share_l1_error": 0.05,
        }
        required_metrics = {
            metric for spec in comparison_specs() for metric in spec["metrics"]
        }
        self.assertLessEqual(required_metrics, set(endpoints))
        rows = []
        for config in policy_configs():
            for offset, seed in enumerate(EXPLORATION_SEEDS):
                rows.append({
                    "id": f"{config_identity(config)}-{seed}",
                    "profile": "under",
                    "seed": seed,
                    "config_id": config_identity(config),
                    "status": "PASS",
                    "endpoints": {
                        key: value + offset * 0.01
                        for key, value in endpoints.items()
                    },
                })
        with patch.object(runner, "BOOTSTRAP_REPLICATES", 100):
            comparisons = runner.comparison_summary(
                rows, EXPLORATION_SEEDS, ("under",), smoke=False
            )
        self.assertEqual(len(comparisons), 6)
        self.assertTrue(all(row["status"] == "COMPLETE" for row in comparisons))
        for row in comparisons:
            self.assertTrue(row["metrics"])
            for metric in row["metrics"].values():
                self.assertEqual(metric["replicates"], 100)
                self.assertEqual(metric["unit"], "paired seed/run")

    def test_failed_job_keeps_directory_failure_and_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "failed-run"
            argv = [
                "--output", str(output), "--smoke", "--window", "256",
                "--heavy-work", "4", "--windows", "1", "--seeds", "6101",
                "--profiles", "under", "--policies", "CGOF_w2_oldest-first",
            ]
            with patch("run_diagnosis.run_job", side_effect=RuntimeError("directed boom")):
                code = runner.main(argv)
            self.assertEqual(code, 1)
            summaries = list((output / "jobs").glob("*/failure.json"))
            self.assertEqual(len(summaries), 1)
            failure = json.loads(summaries[0].read_text())
            self.assertEqual(failure["status"], "FAIL")
            self.assertIn("directed boom", failure["failure"])
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["overall_status"], "FAIL")
            self.assertEqual(summary["jobs_completed"], 0)

    def test_w256_smoke_end_to_end_is_model_only_and_not_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "smoke"
            code = runner.main([
                "--output", str(output), "--smoke", "--window", "256",
                "--heavy-work", "4", "--windows", "1", "--seeds", "6101",
                "--profiles", "under", "--policies", "CGOF_w2_oldest-first",
            ])
            self.assertEqual(code, 0)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["overall_status"], "PASS")
            self.assertEqual(summary["scope"], "MODEL_ONLY")
            self.assertFalse(summary["production_evidence"])
            self.assertTrue(summary["smoke"])
            self.assertTrue(summary["source_stable"])
            self.assertEqual(summary["jobs_completed"], 1)
            self.assertTrue(all(row["status"] == "NOT_RUN" for row in summary["comparisons"]))
            result_paths = list((output / "jobs").glob("*/result.json"))
            self.assertEqual(len(result_paths), 1)
            result = json.loads(result_paths[0].read_text())
            self.assertEqual(result["status"], "PASS")
            self.assertIn("sparse_censored_at_cut", result["endpoint_metrics"])
            runner.validate_manifest(output / "manifest.json")

    def test_legacy_run_remains_finite_heavy_with_forced_ready_drain(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "legacy"
            self.assertEqual(runner.main([
                "--output", str(output), "--smoke", "--window", "256",
                "--heavy-work", "16", "--windows", "1",
                "--seeds", "6101", "--profiles", "near",
                "--policies", "CGOF_w2_oldest-first",
            ]), 0)
            result = json.loads(
                next((output / "jobs").glob("*/result.json")).read_text()
            )["result"]
            self.assertEqual(result["measurement_mode"], "finite_heavy")
            self.assertEqual(
                result["mixed"]["arrival_contract"], "legacy-finite-heavy-v1"
            )
            self.assertIsNone(result["mixed"]["generation_end_exclusive"])
            self.assertIsNone(result["mixed"]["common_generation"])
            self.assertEqual(result["mixed"]["drain"]["phase"], "forced-ready drain")
            self.assertEqual(result["mixed"]["drain"]["ready"], 1)

    def test_dynamic_screen_records_roles_and_ready_without_production_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "dynamic"
            self.assertEqual(runner.main([
                "--output", str(output), "--smoke", "--window", "256",
                "--windows", "4", "--heavy-work", "896", "--seeds", "6101",
                "--profiles", "near", "--policies", "CGOF_w2_oldest-first",
                "--heavy-sources", "0", "0", "1", "1",
                "--ready-pattern", "bursty", "--depth", "8",
            ]), 0)
            data = json.loads(next((output / "jobs").glob("*/result.json")).read_text())
            self.assertEqual(data["result"]["scenario"]["heavy_sources_by_window"], [0, 0, 1, 1])
            self.assertEqual(data["result"]["scenario"]["ready_slots_per_period"], 90)
            self.assertFalse(data["result"]["production_evidence"])
            self.assertEqual(data["result"]["mixed"]["depth"], 8)


if __name__ == "__main__":
    unittest.main()
