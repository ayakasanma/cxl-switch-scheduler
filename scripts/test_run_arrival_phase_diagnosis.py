"""Focused tests for the MODEL_ONLY arrival-phase screening helper."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_arrival_phase_diagnosis import (  # noqa: E402
    ARRIVAL_REQUIRED_SOURCE_PATHS,
    ArrivalPhaseScenario,
    _full_input_pairing,
    _input_pairing,
    _manifest,
    _mixed_isolated_effects,
    _phase_effects,
    _source_hashes,
    _summary_row,
    run_pair,
    self_check,
)
from refc.cxl_model.diagnosis import CONFIRMATION_SEEDS  # noqa: E402


class ArrivalPhaseTests(unittest.TestCase):
    def test_rotation_preserves_heavy_ready_and_sparse_work(self):
        values = [
            ArrivalPhaseScenario.load_profile(
                seed=6101,
                profile="near",
                phase=phase,
                phase_horizon=256,
                n_src=4,
                window=256,
                windows=3,
                heavy_work=512,
                subwindow=64,
            )
            for phase in (0, 1, 2)
        ]
        heavy = [s.declared_heavy_arrivals(256) for s in values]
        ready = [s.declared_ready_schedule(256) for s in values]
        sparse = [s.declared_sparse_work_multiset(256) for s in values]
        self.assertTrue(heavy[0])
        self.assertTrue(sparse[0])
        self.assertTrue(all(row == heavy[0] for row in heavy))
        self.assertTrue(all(row == ready[0] for row in ready))
        self.assertTrue(all(row == sparse[0] for row in sparse))

    def test_paired_smoke_compares_full_common_inputs(self):
        pair = run_pair(
            {"family": "CGOF", "policy": "CGOF", "high_weight": 1,
             "ordering": "oldest-first"},
            seed=6101,
            profile="near",
            phase=1,
            phase_horizon=256,
            n_src=4,
            depth=16,
            window=256,
            heavy_work=512,
            subwindow=64,
            completion_margin_cycles=8,
            throughput_margin_fraction=0.05,
        )
        self.assertEqual(pair["status"], "PASS")
        self.assertTrue(pair["input_pairing"]["valid"])
        self.assertTrue(pair["input_pairing"]["heavy_arrivals_match"])
        self.assertTrue(pair["input_pairing"]["ready_sequence_match"])
        self.assertTrue(pair["input_pairing"]["sparse_work_multiset_match"])
        self.assertGreater(pair["input_pairing"]["heavy_arrivals_count"], 0)
        self.assertGreater(pair["input_pairing"]["sparse_work_count"], 0)
        self.assertTrue(pair["summary"]["conservation"])
        self.assertTrue(pair["summary"]["heavy_completed"])
        self.assertIn("within_declared_equivalence_margin", pair["summary"])
        self.assertEqual(
            pair["generation_end_exclusive"],
            pair["mixed"]["generation_end_exclusive"],
        )
        self.assertIn("post_edge_change_points", pair["heavy_fire_lag"])

    def test_heavy_finishes_first_but_sparse_generation_and_firing_continue(self):
        pair = run_pair(
            {"family": "CGOF", "policy": "CGOF", "high_weight": 1,
             "ordering": "oldest-first"},
            seed=6101,
            profile="near",
            phase=0,
            phase_horizon=128,
            n_src=4,
            depth=16,
            window=256,
            heavy_work=8,
            subwindow=64,
            completion_margin_cycles=8,
            throughput_margin_fraction=0.05,
        )
        self.assertEqual(pair["status"], "PASS")
        self.assertEqual(pair["generation_end_exclusive"], 128)
        self.assertEqual(pair["input_pairing"]["sparse_work_count"], 6)
        self.assertEqual(pair["summary"]["heavy_completion_cycle_mixed"], 11)
        scenario = ArrivalPhaseScenario.load_profile(
            6101,
            "near",
            phase=0,
            phase_horizon=128,
            n_src=4,
            window=256,
            windows=3,
            heavy_work=8,
            subwindow=64,
        )
        self.assertEqual(
            max(k for k in range(128) if scenario.sparse_events(k)),
            111,
        )
        self.assertGreater(
            pair["summary"]["full_cohort_last_fire_cycle_mixed"],
            pair["summary"]["heavy_completion_cycle_mixed"],
        )
        for cohort in pair["mixed"]["cohorts"].values():
            generated = cohort["generated_total"]
            self.assertEqual(
                cohort["stages"]["generation_to_acceptance"]["count"], generated
            )
            self.assertEqual(
                cohort["stages"]["acceptance_to_fire"]["count"], generated
            )
            self.assertEqual(
                cohort["stages"]["generation_to_fire"]["count"], generated
            )
        self.assertEqual(
            pair["summary"]["heavy_completion_time_ratio_mixed_over_isolated"],
            (pair["summary"]["heavy_completion_cycle_mixed"] + 1)
            / (pair["summary"]["heavy_completion_cycle_isolated"] + 1),
        )
        self.assertEqual(
            pair["summary"]["completion_ratio"],
            pair["summary"]["heavy_completion_time_ratio_mixed_over_isolated"],
        )

    def test_mismatch_and_empty_inputs_are_rejected(self):
        pair = run_pair(
            {"family": "CGOF", "policy": "CGOF", "high_weight": 1,
             "ordering": "oldest-first"},
            seed=6101,
            profile="near",
            phase=0,
            phase_horizon=32,
            n_src=4,
            depth=16,
            window=256,
            heavy_work=4,
            subwindow=64,
            completion_margin_cycles=8,
            throughput_margin_fraction=0.05,
        )
        scenario = ArrivalPhaseScenario.load_profile(
            6101,
            "near",
            phase=0,
            phase_horizon=32,
            n_src=4,
            window=256,
            windows=3,
            heavy_work=4,
            subwindow=64,
        )
        mismatch = _full_input_pairing(
            scenario,
            pair["generation_end_exclusive"],
            pair["mixed"],
            {
                **pair["isolated"],
                "common_generation": {
                    **pair["isolated"]["common_generation"],
                    "emitted_heavy_arrivals": pair["isolated"][
                        "common_generation"
                    ]["emitted_heavy_arrivals"][:-1],
                },
            },
        )
        self.assertFalse(mismatch["valid"])
        self.assertTrue(any("Heavy arrivals" in error for error in mismatch["errors"]))

        empty = _full_input_pairing(
            scenario,
            pair["generation_end_exclusive"],
            {
                **pair["mixed"],
                "common_generation": {
                    **pair["mixed"]["common_generation"],
                    "emitted_sparse_work_multiset": [],
                },
            },
            pair["isolated"],
        )
        self.assertFalse(empty["valid"])
        self.assertTrue(any("Sparse work" in error for error in empty["errors"]))

    def test_phase_input_pairing_compares_full_actual_sequences(self):
        config = {
            "family": "CGOF",
            "policy": "CGOF",
            "high_weight": 1,
            "ordering": "oldest-first",
        }
        pairs = [
            run_pair(
                config,
                seed=6101,
                profile="near",
                phase=phase,
                phase_horizon=128,
                n_src=4,
                depth=16,
                window=256,
                heavy_work=8,
                subwindow=64,
                completion_margin_cycles=8,
                throughput_margin_fraction=0.05,
            )
            for phase in (0, 1)
        ]
        records = [
            {
                "id": f"phase-{pair['phase']}",
                "profile": pair["profile"],
                "config_id": pair["config_id"],
                "seed": pair["seed"],
                "status": pair["status"],
                "input_pairing": pair["input_pairing"],
            }
            for pair in pairs
        ]
        pairing = _input_pairing(records)
        self.assertTrue(pairing["valid"])
        self.assertEqual(pairing["cases_checked"], 1)
        self.assertTrue(pairing["all_phase_sets_share_sparse_work"])

    def test_timeout_summary_keeps_progress_but_nulls_incomplete_endpoints(self):
        summary = _summary_row({
            "mixed": {
                "status": "TIMEOUT",
                "generation_end_exclusive": 8,
                "active_cycles": 6,
                "timeout_cycle": 10,
                "generated_total": 4,
                "accepted_total": 3,
                "fired_total": 1,
            },
            "isolated": {
                "status": "PASS",
                "generation_end_exclusive": 8,
                "active_cycles": 8,
                "timeout_cycle": None,
            },
        })
        self.assertEqual(summary["status"], "TIMEOUT")
        self.assertEqual(summary["generated_total_mixed"], 4)
        self.assertEqual(summary["accepted_total_mixed"], 3)
        self.assertEqual(summary["fired_total_mixed"], 1)
        self.assertIsNone(summary["completion_ratio"])
        self.assertIsNone(summary["sparse_wait_p99"])
        self.assertIsNone(summary["heavy_lag_max"])
        self.assertIsNone(summary["full_cohort_last_fire_cycle_mixed"])

    def test_run_pair_timeout_reports_failure_and_retains_uncompleted_work(self):
        with patch.object(ArrivalPhaseScenario, "ready", return_value=0):
            pair = run_pair(
                {"family": "CGOF", "policy": "CGOF", "high_weight": 1,
                 "ordering": "oldest-first"},
                seed=6101,
                profile="near",
                phase=0,
                phase_horizon=128,
                n_src=4,
                depth=16,
                window=64,
                heavy_work=8,
                subwindow=16,
                completion_margin_cycles=8,
                throughput_margin_fraction=0.05,
            )
        self.assertEqual(pair["status"], "TIMEOUT")
        self.assertTrue(pair["input_pairing"]["valid"])
        self.assertEqual(pair["summary"]["status"], "TIMEOUT")
        self.assertIsNone(pair["summary"]["heavy_completion_cycle_mixed"])
        self.assertEqual(
            pair["summary"]["generated_total_mixed"],
            pair["summary"]["accepted_total_mixed"],
        )
        self.assertEqual(pair["summary"]["fired_total_mixed"], 0)
        self.assertGreater(
            pair["summary"]["uncompleted_mixed"]["fifo_backlog"], 0
        )

    def test_self_check(self):
        self.assertEqual(self_check()["status"], "PASS")

    def test_confirmation_cohort_enables_bootstrap(self):
        manifest = _manifest(
            Path("unused"),
            [],
            smoke=False,
            seeds=CONFIRMATION_SEEDS,
            profiles=["under", "over"],
            phases=[0],
            policies=[],
            settings={},
            jobs=[],
        )
        self.assertEqual(manifest["schema"], "cxl-arrival-phase-manifest-v2")
        self.assertTrue(manifest["bootstrap"]["enabled"])

    def test_required_sources_are_complete_and_report_all_missing_paths(self):
        hashes = _source_hashes()
        self.assertEqual(set(hashes), set(ARRIVAL_REQUIRED_SOURCE_PATHS))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "sources"
            for relative in ARRIVAL_REQUIRED_SOURCE_PATHS:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            missing = [
                "scripts/run_arrival_phase_diagnosis.py",
                "scripts/test_run_arrival_phase_diagnosis.py",
            ]
            for relative in missing:
                (root / relative).unlink()
            with self.assertRaisesRegex(ValueError, "missing required source files") as caught:
                _source_hashes(root)
            for relative in missing:
                self.assertIn(relative, str(caught.exception))

    def test_phase_and_mixed_isolated_effects_have_explicit_estimands(self):
        def row(phase, seed, delta):
            return {
                "id": f"p{phase}-s{seed}",
                "config_id": "CGOF_w1_oldest-first",
                "profile": "near",
                "phase": phase,
                "seed": seed,
                "status": "PASS",
                "summary": {
                    "sparse_wait_p99": float(phase + delta),
                    "heavy_completion_delta_mixed_minus_isolated": delta,
                    "heavy_completion_cycle_mixed": 100 + delta,
                    "heavy_completion_cycle_isolated": 100,
                    "heavy_completion_time_ratio_mixed_over_isolated": 1 + delta / 100,
                    "throughput_ratio": 1.0,
                    "heavy_max_service_gap": 2.0,
                },
            }

        records = [row(0, 6101, 1), row(0, 6102, 2),
                   row(1, 6101, 3), row(1, 6102, 4)]
        phase_effects = _phase_effects(records, (6101, 6102), smoke=True)
        baseline = next(row for row in phase_effects if row["phase"] == 0)
        candidate = next(row for row in phase_effects if row["phase"] == 1)
        self.assertEqual(baseline["estimand"], "phase_minus_phase0")
        self.assertTrue(baseline["self_comparison"])
        self.assertEqual(
            baseline["metrics"]["sparse_wait_p99"]["status"],
            "NOT_APPLICABLE",
        )
        self.assertFalse(candidate["self_comparison"])
        self.assertEqual(
            candidate["metrics"]["sparse_wait_p99"]["status"],
            "DESCRIPTIVE_ONLY",
        )
        mixed = _mixed_isolated_effects(records, (6101, 6102), smoke=True)
        self.assertTrue(all(row["estimand"] == "mixed_minus_isolated" for row in mixed))
        self.assertTrue(all(
            row["metrics"]["heavy_completion_cycles"]["status"]
            == "DESCRIPTIVE_ONLY"
            for row in mixed
        ))


if __name__ == "__main__":
    unittest.main()
