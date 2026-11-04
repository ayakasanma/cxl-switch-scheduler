"""Directed contracts for the model-only measurement/diagnosis harness."""
from pathlib import Path
import json
import math
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model.diagnosis import (
    ARRIVAL_COMMON_GENERATION_CONTRACT,
    CONFIRMATION_SEEDS,
    EXPLORATION_SEEDS,
    QUOTA_BACKLOG_HISTORY_CONTRACT,
    DiagnosisScenario,
    RoleBook,
    IwrrSwitchModel,
    WrrSwitchModel,
    comparison_specs,
    endpoint_metrics,
    fairness_summary,
    heavy_fire_lag_summary,
    jain_index,
    paired_bootstrap,
    policy_configs,
    pooled_stage_summary,
    quota_summary,
    run_job,
    run_lane,
    validate_seed_groups,
)


def policy(family="CGOF", high_weight=2, ordering="oldest-first"):
    return next(
        row for row in policy_configs()
        if row["family"] == family
        and (family != "CGOF" or (
            row["high_weight"] == high_weight and row["ordering"] == ordering
        ))
    )


def weighted_sequence(model):
    model.commit(rst_n=False)
    model.commit(False, [True] * model.n_src, list(range(model.n_src)))
    sources = []
    for _ in range(10):
        edge = model.commit(True, [True] * model.n_src, list(range(model.n_src)))
        sources.append(None if edge.fired is None else edge.fired.source)
    return sources


class FixedReadyScenario(DiagnosisScenario):
    def __init__(self, *, ready_at, **kwargs):
        super().__init__(**kwargs)
        self.ready_at = ready_at

    def ready(self, k):
        return int(k >= self.ready_at)


class SparseAt63Scenario(DiagnosisScenario):
    def sparse_events(self, k):
        if k != 63:
            return []
        return [(source, 0xABC000 + source) for source in range(1, self.n_src)]


def quota_history(**overrides):
    history = {
        "contract_version": QUOTA_BACKLOG_HISTORY_CONTRACT,
        "expected_cycles": 64,
        "observed_cycles": 64,
        "active_cycles": 64,
        "drain_cycles": 0,
        "ready_cycles": 64,
        "held_cycles": 0,
        "idle_cycles": 0,
        "output_stall_cycles": 0,
        "all_source_fifo_nonempty_cycles": 64,
        "source_fifo_nonempty_cycles": [64, 64, 64, 64],
    }
    history.update(overrides)
    return history


def quota_row(*, phase="active", producer=(0, 0, 0, 0), fifo=(1, 1, 1, 1),
              history=True, counts=(4, 2, 1, 1)):
    row = {
        "window": 0,
        "closing_cycle": 63,
        "phase": phase,
        "counts": list(counts),
        "total": sum(counts),
        "old_classes": ["H", "L", "L", "L"],
        "producer_backlog": list(producer),
        "fifo_occupancy": list(fifo),
    }
    if history is not False:
        row["quota_backlog_history"] = quota_history() if history is True else history
    return row


def quota_result(*rows):
    return {
        "model_config": {"family": "CGOF", "high_weight": 2, "n_src": 4, "window": 64},
        "n_src": 4,
        "window": 64,
        "classifier_trajectory": list(rows),
    }


class DynamicScenarioTests(unittest.TestCase):
    def test_default_trace_stays_identical_and_periodic_ready_counts_match(self):
        original = DiagnosisScenario.load_profile(
            6101, "near", window=256, windows=4, heavy_work=768)
        self.assertEqual(original.input_prefix_sha256(512),
                         "724df6b9123bddddde37aa5fd2dc12ffe9b76769c81d6fc5d585f62005111a18")
        spread = DiagnosisScenario.load_profile(6101, "near", window=64,
                                                ready_pattern="spread")
        bursty = DiagnosisScenario.load_profile(6101, "near", window=64,
                                                ready_pattern="bursty")
        self.assertNotEqual([spread.ready(k) for k in range(100)],
                            [bursty.ready(k) for k in range(100)])
        for start in (0, 100, 200):
            self.assertEqual(sum(spread.ready(k) for k in range(start, start+100)), 90)
            self.assertEqual(sum(bursty.ready(k) for k in range(start, start+100)), 90)
        with self.assertRaises(ValueError):
            DiagnosisScenario(6101, ready_p=.91, ready_pattern="bursty", ready_period=64)
        for sources in ([], [4], [-1]):
            with self.assertRaises(ValueError):
                DiagnosisScenario(6101, heavy_sources=sources)

    def test_pending_requests_keep_generation_roles_after_a_switch(self):
        scenario = DiagnosisScenario(6101, window=64, heavy_sources=(0, 1))
        roles = RoleBook(scenario)
        roles.observe(62, [(1, 1)], [], None, 1)
        roles.observe(63, [(0, 2)], [(62, 1)], None, 1)
        roles.observe(64, [], [(63, 0)], (62, 63, 1), 1)
        roles.observe(65, [], [], (63, 64, 0), 1)
        roles.snapshot_cut()
        data = roles.as_dict()
        self.assertEqual(data["counts"]["heavy"]["fired"], [1, 0, 0, 0])
        self.assertEqual(data["counts"]["sparse"]["fired"], [0, 1, 0, 0])
        self.assertEqual(data["bursts"][0]["last_fire"], 65)
        self.assertEqual(data["latency"]["sparse"]["generation_to_fire"]["count"], 1)

    def test_multi_window_roles_complete_and_censor_sparse_at_cut(self):
        result = run_job(policy(), 6101, "exploration", window=64, windows=4,
                         heavy_work=256, profile="near", depth=8,
                         heavy_sources=(0, 0, 1, 1), ready_pattern="bursty")
        self.assertEqual(result["status"], "PASS", result["mixed"].get("failure"))
        mixed = result["mixed"]
        self.assertGreaterEqual(len([r for r in mixed["classifier_trajectory"]
                                     if r["phase"] == "active"]), 4)
        self.assertEqual(sum(mixed["generation_roles"]["counts"]["heavy"]["fired"]), 256)
        for lane in (mixed, result["isolated"]):
            for counts in lane["generation_roles"]["counts"].values():
                self.assertEqual(counts["generated"], counts["accepted"])
                self.assertEqual(counts["accepted"], counts["fired"])
        sparse = mixed["generation_roles"]["at_cut"]["sparse"]
        self.assertEqual(endpoint_metrics(result)["sparse_censored_at_cut"],
                         sum(sparse["generated"]) - sum(sparse["fired"]))

    def test_common_generation_stall_extends_into_scenario_ready_drain(self):
        scenario = FixedReadyScenario(
            ready_at=7,
            seed=6101,
            n_src=2,
            window=64,
            heavy_work=2,
            heavy_p=1.0,
            sparse_p=0.0,
            ready_p=1.0,
            subwindow=16,
        )
        result = run_lane(
            policy("CGOF", high_weight=1),
            scenario,
            False,
            max_active_cycles=4,
            max_drain_cycles=10,
            common_generation_horizon=4,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["arrival_contract"], ARRIVAL_COMMON_GENERATION_CONTRACT)
        self.assertEqual(result["generation_end_exclusive"], 4)
        self.assertEqual(result["heavy"]["actual_completion_cycle"], 8)
        self.assertEqual(result["drain_start_cycle"], 4)
        self.assertEqual(result["drain_cycles"], 5)
        self.assertEqual(result["drain"]["phase"], "scenario-ready bounded drain")
        self.assertEqual(result["drain"]["ready"], "scenario.ready(k)")
        self.assertGreater(
            result["phase_metrics"]["drain"]["output_transfers"], 0
        )
        self.assertIn([8, 1], result["common_generation"]["drain_ready_schedule"])

    def test_common_generation_timeout_retains_measured_progress(self):
        scenario = FixedReadyScenario(
            ready_at=100,
            seed=6101,
            n_src=2,
            window=64,
            heavy_work=2,
            heavy_p=1.0,
            sparse_p=0.0,
            ready_p=1.0,
            subwindow=16,
        )
        result = run_lane(
            policy("CGOF", high_weight=1),
            scenario,
            False,
            max_active_cycles=4,
            max_drain_cycles=3,
            common_generation_horizon=4,
        )
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertEqual(result["timeout_cycle"], 7)
        self.assertEqual(result["generated_total"], 2)
        self.assertEqual(result["accepted_total"], 2)
        self.assertEqual(result["fired_total"], 0)
        self.assertEqual(result["drain"]["uncompleted"]["producer_pending"], 0)
        self.assertEqual(result["drain"]["uncompleted"]["fifo_backlog"], 2)
        self.assertEqual(result["conservation"]["final_fifo_occupancy"], [2, 0])
        endpoints = endpoint_metrics({"status": "TIMEOUT"})
        self.assertTrue(endpoints["incomplete_endpoints"])
        self.assertIsNone(endpoints["heavy_completion_ratio_mixed_over_isolated"])
        self.assertIsNone(endpoints["sparse_completed_generation_to_fire_p99"])

    def test_legacy_default_does_not_use_common_generation(self):
        scenario = DiagnosisScenario(
            6101,
            n_src=4,
            window=64,
            heavy_work=8,
            heavy_p=1.0,
            sparse_p=1.0,
            ready_p=1.0,
            subwindow=16,
        )
        default = run_lane(policy("CGOF", high_weight=1), scenario, True)
        explicit_legacy = run_lane(
            policy("CGOF", high_weight=1),
            scenario,
            True,
            common_generation_horizon=None,
        )
        self.assertEqual(default, explicit_legacy)
        self.assertEqual(default["measurement_mode"], "finite_heavy")
        self.assertEqual(default["arrival_contract"], "legacy-finite-heavy-v1")
        self.assertIsNone(default["common_generation"])
        self.assertEqual(default["drain"]["phase"], "forced-ready drain")
        self.assertEqual(default["drain"]["ready"], 1)
        with self.assertRaisesRegex(ValueError, "incompatible"):
            run_lane(
                policy("CGOF", high_weight=1),
                scenario,
                True,
                max_active_cycles=8,
                max_drain_cycles=8,
                fixed_horizon=True,
                common_generation_horizon=8,
            )


class WeightedModelTests(unittest.TestCase):
    def test_exact_wrr_and_iwrr_sequences(self):
        self.assertEqual(
            weighted_sequence(WrrSwitchModel(4, (2, 1, 1, 1), window=64)),
            [0, 0, 1, 2, 3, 0, 0, 1, 2, 3],
        )
        self.assertEqual(
            weighted_sequence(IwrrSwitchModel(4, (2, 1, 1, 1), window=64)),
            [0, 1, 2, 3, 0, 0, 1, 2, 3, 0],
        )

    def test_empty_models_and_singleton_drain_do_not_invent_work(self):
        for factory in (WrrSwitchModel, IwrrSwitchModel):
            with self.subTest(model=factory.__name__):
                model = factory(4, (2, 1, 1, 1), window=64, depth=2)
                model.commit(rst_n=False)
                for _ in range(8):
                    edge = model.commit(True, [False] * 4, [0] * 4)
                    self.assertIsNone(edge.fired)
                    self.assertEqual(
                        sum(model.occupancy(source) for source in range(4)), 0
                    )
                model.commit(False, [True, True, False, False], [11, 22, 0, 0])
                for _ in range(8):
                    before = sum(model.occupancy(source) for source in range(4))
                    edge = model.commit(True, [False] * 4, [0] * 4)
                    if before == 0:
                        self.assertIsNone(edge.fired)
                        break
                    self.assertIsNotNone(edge.fired)
                self.assertEqual(
                    sum(model.occupancy(source) for source in range(4)), 0
                )

    def test_held_plan_survives_stall_refill_and_push(self):
        model = WrrSwitchModel(2, (1, 1), window=64, depth=2)
        model.commit(rst_n=False)
        model.commit(False, [True, False], [11, 0])
        model.commit(False, [False, False], [0, 0])
        self.assertEqual(model.held_choice(), 0)
        model.commit(False, [False, True], [0, 22])
        self.assertEqual(model.held_choice(), 0)
        edge = model.commit(True, [False, True], [0, 33])
        self.assertEqual(edge.fired.source, 0)


class ScenarioAndMetricTests(unittest.TestCase):
    def test_declared_seed_groups_profiles_and_comparison_matrix(self):
        validate_seed_groups()
        self.assertEqual(EXPLORATION_SEEDS, tuple(range(6101, 6106)))
        self.assertEqual(CONFIRMATION_SEEDS, tuple(range(6201, 6221)))
        self.assertFalse(set(EXPLORATION_SEEDS) & set(CONFIRMATION_SEEDS))
        for name, heavy, sparse, ready in (
            ("under", 0.25, 0.02, 0.90),
            ("near", 0.80, 0.02, 0.90),
            ("over", 1.00, 0.05, 0.90),
            ("equal", 1.00, 1.00, 1.00),
        ):
            scenario = DiagnosisScenario.load_profile(6101, name, window=64)
            self.assertEqual(
                (scenario.heavy_p, scenario.sparse_p, scenario.ready_p),
                (heavy, sparse, ready),
            )
        self.assertEqual(len(policy_configs()), 9)
        self.assertEqual(
            {row["id"] for row in comparison_specs()},
            {
                "allocation-1-1-vs-2-1",
                "ordering-1-1",
                "ordering-2-1",
                "wrr-2-1-control",
                "iwrr-2-1-control",
                "fai-inspired-control",
            },
        )

    def test_jain_demand_error_and_weighted_entitlement_error(self):
        self.assertAlmostEqual(jain_index([9, 1]), 0.6097560975609756)
        plain = fairness_summary([9, 1], [10, 10])
        self.assertAlmostEqual(plain["active_service_jain"], 0.6097560975609756)
        self.assertAlmostEqual(plain["demand_share_l1_error"], 0.8)
        weighted = fairness_summary([8, 2], [10, 10], weights=[2, 1])
        self.assertAlmostEqual(weighted["weighted_jain_active"], 0.9)
        self.assertAlmostEqual(weighted["weighted_share_l1_error"], 4 / 15)
        empty = fairness_summary([0, 0], [0, 0], weights=[2, 1])
        self.assertIsNone(empty["active_service_jain"])
        self.assertIsNone(empty["weighted_share_l1_error"])

    def test_heavy_lag_recovery_and_right_censoring_use_full_change_points(self):
        recovered = heavy_fire_lag_summary(
            [
                {"cycle": 1, "cumulative_heavy_fires": 1},
                {"cycle": 3, "cumulative_heavy_fires": 2},
                {"cycle": 5, "cumulative_heavy_fires": 3},
            ],
            [
                {"cycle": 1, "cumulative_heavy_fires": 1},
                {"cycle": 2, "cumulative_heavy_fires": 2},
                {"cycle": 4, "cumulative_heavy_fires": 3},
            ],
            observation_end_exclusive=6,
            mixed_complete=True,
            isolated_complete=True,
        )
        self.assertEqual(recovered["max_lag"], 1)
        self.assertEqual(recovered["last_positive_lag_cycle"], 4)
        self.assertEqual(recovered["recovery_cycle"], 5)
        self.assertTrue(recovered["recovered"])
        self.assertFalse(recovered["right_censored"])
        self.assertEqual(recovered["endpoint_lag"], 0)

        censored = heavy_fire_lag_summary(
            [],
            [{"cycle": 2, "cumulative_heavy_fires": 1}],
            observation_end_exclusive=4,
            mixed_complete=False,
            isolated_complete=True,
        )
        self.assertEqual(censored["max_lag"], 1)
        self.assertIsNone(censored["recovery_cycle"])
        self.assertTrue(censored["right_censored"])
        self.assertEqual(
            censored["recovery_null_reason"],
            "observation_truncated_before_recovery",
        )
        with self.assertRaisesRegex(ValueError, "different Heavy totals"):
            heavy_fire_lag_summary(
                [{"cycle": 1, "cumulative_heavy_fires": 1}],
                [{"cycle": 1, "cumulative_heavy_fires": 2}],
                observation_end_exclusive=3,
                mixed_complete=True,
                isolated_complete=True,
            )

    def test_quota_summary_is_unavailable_without_predecision_history(self):
        summary = quota_summary(quota_result(quota_row(history=False)))
        self.assertEqual(summary["availability"], "UNAVAILABLE")
        self.assertEqual(summary["window_count"], 1)
        self.assertEqual(summary["eligible_window_count"], 0)
        self.assertIsNone(summary["observed_share_l1_error"])
        self.assertIsNone(summary["observed_share_max_error"])
        self.assertEqual(summary["windows"][0]["eligibility_status"], "UNAVAILABLE")
        self.assertTrue(
            summary["windows"][0]["closing_snapshot_all_sources_backlogged"]
        )

    def test_quota_history_excludes_external_only_or_transient_local_backlog(self):
        external_only = quota_row(
            producer=(8, 8, 8, 8),
            fifo=(0, 0, 0, 0),
            history=quota_history(
                ready_cycles=0,
                idle_cycles=64,
                all_source_fifo_nonempty_cycles=0,
                source_fifo_nonempty_cycles=[0, 0, 0, 0],
            ),
        )
        transient = quota_row(
            history=quota_history(
                all_source_fifo_nonempty_cycles=63,
                source_fifo_nonempty_cycles=[63, 63, 63, 63],
            )
        )
        summary = quota_summary(quota_result(external_only, transient))
        self.assertEqual(summary["eligible_window_count"], 0)
        self.assertIsNone(summary["observed_share_l1_error"])
        for row in summary["windows"]:
            self.assertEqual(row["eligibility_status"], "NOT_ALL_SOURCES_BACKLOGGED")
            self.assertTrue(row["closing_snapshot_all_sources_backlogged"])
            self.assertFalse(row["included_in_aggregate"])

    def test_quota_history_marks_partial_and_mixed_windows_ineligible(self):
        partial = quota_row(history=quota_history(
            observed_cycles=63,
            active_cycles=63,
            ready_cycles=63,
            all_source_fifo_nonempty_cycles=63,
            source_fifo_nonempty_cycles=[63, 63, 63, 63],
        ))
        mixed = quota_row(history=quota_history(
            active_cycles=32,
            drain_cycles=32,
        ))
        summary = quota_summary(quota_result(partial, mixed))
        self.assertEqual(
            [row["eligibility_status"] for row in summary["windows"]],
            ["PARTIAL_WINDOW", "MIXED_ACTIVE_DRAIN"],
        )
        self.assertEqual(summary["eligible_window_count"], 0)
        self.assertIsNone(summary["observed_share_l1_error"])

    def test_quota_history_rejects_malformed_counters_and_dimensions(self):
        malformed_cases = (
            quota_history(held_cycles=-1),
            quota_history(active_cycles=63),
            quota_history(source_fifo_nonempty_cycles=[64, 64, 64]),
            quota_history(all_source_fifo_nonempty_cycles=65),
        )
        for history in malformed_cases:
            with self.subTest(history=history):
                with self.assertRaises(ValueError):
                    quota_summary(quota_result(quota_row(history=history)))
        with self.assertRaisesRegex(ValueError, "source dimensions"):
            quota_summary(quota_result(quota_row(counts=(4, 2, 1))))
        with self.assertRaisesRegex(ValueError, "source dimensions"):
            quota_summary(quota_result(quota_row(producer=(1, 1, 1))))

    def test_pooled_latency_uses_per_source_histograms_and_nearest_rank(self):
        def stages(histogram):
            return {
                "generation_to_acceptance": {"histogram": {}},
                "acceptance_to_fire": {"histogram": {}},
                "generation_to_fire": {"histogram": histogram},
            }

        result = {
            "cohorts": {
                "0": {
                    "stages_by_source": [
                        stages({"0": 1000}),
                        stages({"1": 99, "9": 1}),
                        stages({"2": 100}),
                    ]
                }
            }
        }
        pooled = pooled_stage_summary(result, "generation_to_fire", (1, 2))
        self.assertEqual(pooled["count"], 200)
        self.assertEqual(pooled["p99_nearest_rank"], 2)
        self.assertEqual(pooled["max"], 9)

    def test_paired_bootstrap_is_seed_cohort_only(self):
        candidate = [2.0, 3.0, 4.0, 5.0, 6.0]
        baseline = [1.0, 1.0, 2.0, 2.0, 3.0]
        first = paired_bootstrap(
            candidate, baseline, EXPLORATION_SEEDS, replicates=10_000
        )
        second = paired_bootstrap(
            candidate, baseline, EXPLORATION_SEEDS, replicates=10_000
        )
        self.assertEqual(first, second)
        self.assertEqual(first["unit"], "paired seed/run")
        self.assertEqual(first["n"], 5)
        self.assertEqual(first["replicates"], 10_000)
        self.assertEqual(first["mean_paired_delta"], 2.2)
        self.assertTrue(first["descriptive_only"])
        with self.assertRaisesRegex(ValueError, "declared"):
            paired_bootstrap(candidate, baseline, (6101, 6102))
        with self.assertRaises(ValueError):
            paired_bootstrap(candidate[:-1], baseline, EXPLORATION_SEEDS)


class ClosedLoopDiagnosisTests(unittest.TestCase):
    def test_fixed_horizon_equal_demand_uses_common_offered_work(self):
        result = run_job(
            policy("CGOF", high_weight=1),
            6101,
            "exploration",
            window=64,
            windows=1,
            heavy_work=65,
            heavy_p=1.0,
            sparse_p=1.0,
            ready_p=1.0,
            max_active_cycles=64,
            fixed_horizon=True,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mixed"]["measurement_mode"], "fixed_horizon")
        self.assertEqual(result["mixed"]["active_cycles"], 64)
        self.assertEqual(
            result["mixed"]["phase_metrics"]["active"]["generated"], [64] * 4
        )
        fairness = result["mixed"]["active_demand_fairness"]
        self.assertGreater(fairness["active_service_jain"], 0.999)
        fired = result["mixed"]["phase_metrics"]["active"]["fired"]
        self.assertLessEqual(max(fired) - min(fired), 1)
        self.assertLess(fairness["demand_share_l1_error"], 0.04)
        self.assertFalse(result["mixed"]["heavy"]["completed"])
        endpoints = endpoint_metrics(result)
        self.assertIsNone(endpoints["heavy_completion_ratio_mixed_over_isolated"])

    def test_fixed_classes_exercise_cgof_quota_on_equal_demand(self):
        result = run_job(
            policy("CGOF", high_weight=2),
            6102,
            "exploration",
            window=64,
            windows=1,
            heavy_work=65,
            heavy_p=1.0,
            sparse_p=1.0,
            ready_p=1.0,
            max_active_cycles=64,
            fixed_horizon=True,
            initial_classes=("L", "H", "H", "H"),
        )
        self.assertEqual(result["status"], "PASS")
        shares = result["mixed"]["active_service_shares"]
        self.assertAlmostEqual(shares["0"], 1 / 7, places=3)
        for source in ("1", "2", "3"):
            self.assertAlmostEqual(shares[source], 2 / 7, places=3)

    def test_finite_heavy_pairing_sparse_censoring_and_separate_phases(self):
        result = run_job(
            policy(),
            6101,
            "exploration",
            window=64,
            windows=2,
            heavy_work=20,
            heavy_p=1.0,
            sparse_p=0.2,
            ready_p=0.8,
        )
        self.assertEqual(result["status"], "PASS")
        mixed, isolated = result["mixed"], result["isolated"]
        self.assertGreater(mixed["cut_cycle"], isolated["cut_cycle"])
        self.assertTrue(result["pairing"]["same_scenario"])
        self.assertEqual(
            mixed["heavy"]["generated"], isolated["heavy"]["generated"]
        )
        self.assertEqual(
            mixed["heavy"]["first_release_cycle"],
            isolated["heavy"]["first_release_cycle"],
        )
        self.assertEqual(
            mixed["heavy"]["last_release_cycle"],
            isolated["heavy"]["last_release_cycle"],
        )
        self.assertGreater(mixed["generated"][1] + mixed["generated"][2] + mixed["generated"][3], 0)
        self.assertGreater(
            mixed["cut_censoring"]["accepted_unfired_total"],
            0,
        )
        self.assertGreater(
            sum(row["completed_after_cut_total"] for row in mixed["cohorts"].values()),
            0,
        )
        self.assertEqual(
            mixed["phase_metrics"]["labels"]["drain"],
            "cleanup and conservation evidence only",
        )
        self.assertFalse(mixed["drain"]["stability_evidence"])
        self.assertNotEqual(
            mixed["active_service_shares"], mixed["drain_service_shares"]
        )
        self.assertNotIn("heavy_release_cycles", mixed["heavy"])
        self.assertNotIn("heavy_fire_cycles", mixed["heavy"])
        endpoints = endpoint_metrics(result)
        sparse_censored = sum(
            sum(row["unaccepted_at_cut"][1:]) + sum(row["accepted_unfired_at_cut"][1:])
            for row in mixed["cohorts"].values()
        )
        self.assertEqual(endpoints["sparse_censored_at_cut"], sparse_censored)
        self.assertAlmostEqual(
            endpoints["heavy_completion_ratio_mixed_over_isolated"],
            (mixed["cut_cycle"] + 1) / (isolated["cut_cycle"] + 1),
        )
        self.assertIsNotNone(endpoints["heavy_max_service_gap"])

    def test_closing_cycle_is_retained_before_counter_reset(self):
        result = run_job(
            policy(),
            6102,
            "exploration",
            window=64,
            windows=1,
            heavy_work=64,
            heavy_p=1.0,
            sparse_p=0.0,
            ready_p=1.0,
        )
        self.assertEqual(result["status"], "PASS")
        row = result["mixed"]["classifier_trajectory"][0]
        self.assertEqual(row["phase"], "active")
        self.assertEqual(row["closing_cycle"], 63)
        self.assertEqual(row["generated"], [64, 0, 0, 0])
        self.assertEqual(row["fired"], [63, 0, 0, 0])
        self.assertEqual(row["counts"], [63, 0, 0, 0])
        self.assertEqual(result["mixed"]["heavy"]["last_fire_cycle"], 64)
        self.assertEqual(
            result["mixed"]["heavy"]["first_release_to_last_fire"], 64
        )

    def test_quota_writer_json_counterexample_excludes_closing_snapshot(self):
        scenario = SparseAt63Scenario(
            seed=6101,
            n_src=4,
            window=64,
            windows=2,
            heavy_work=65,
            heavy_p=1.0,
            sparse_p=0.0,
            ready_p=1.0,
            subwindow=16,
        )
        lane = run_lane(
            policy("CGOF", high_weight=1),
            scenario,
            True,
            max_active_cycles=64,
            fixed_horizon=True,
        )
        self.assertEqual(lane["status"], "PASS")
        row = lane["classifier_trajectory"][0]
        self.assertEqual(row["counts"], [63, 0, 0, 0])
        self.assertEqual(row["fifo_occupancy"], [1, 1, 1, 1])
        history = row["quota_backlog_history"]
        self.assertEqual(history["observed_cycles"], 64)
        self.assertEqual(history["active_cycles"], 64)
        self.assertEqual(history["drain_cycles"], 0)
        self.assertEqual(history["all_source_fifo_nonempty_cycles"], 0)
        self.assertEqual(history["source_fifo_nonempty_cycles"], [63, 0, 0, 0])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quota-lane.json"
            path.write_text(json.dumps(lane, sort_keys=True), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))
        summary = quota_summary(loaded)
        self.assertEqual(summary["availability"], "UNAVAILABLE")
        self.assertEqual(summary["window_count"], 1)
        self.assertEqual(summary["eligible_window_count"], 0)
        self.assertIsNone(summary["observed_share_l1_error"])
        self.assertIsNone(summary["observed_share_max_error"])
        self.assertEqual(
            summary["windows"][0]["eligibility_status"],
            "NOT_ALL_SOURCES_BACKLOGGED",
        )
        self.assertTrue(
            summary["windows"][0]["closing_snapshot_all_sources_backlogged"]
        )
        endpoints = endpoint_metrics({
            "status": "PASS",
            "mixed": loaded,
            "isolated": loaded,
            "model_config": loaded["model_config"],
        })
        self.assertIsNone(endpoints["quota_share_l1_error"])
        self.assertFalse(endpoints["incomplete_endpoints"])

    def test_complete_later_quota_window_uses_predecision_history(self):
        scenario = DiagnosisScenario.load_profile(
            6101,
            "equal",
            window=64,
            windows=2,
            heavy_work=129,
            sparse_p=1.0,
            ready_p=1.0,
            subwindow=16,
        )
        lane = run_lane(
            policy("CGOF", high_weight=1),
            scenario,
            True,
            max_active_cycles=128,
            fixed_horizon=True,
        )
        rows = {row["window"]: row for row in lane["classifier_trajectory"]}
        self.assertEqual(
            rows[0]["quota_backlog_history"]["all_source_fifo_nonempty_cycles"],
            63,
        )
        self.assertEqual(
            rows[1]["quota_backlog_history"]["all_source_fifo_nonempty_cycles"],
            64,
        )
        summary = quota_summary(lane)
        eligible = {
            row["window"]: row for row in summary["windows"]
            if row["included_in_aggregate"]
        }
        self.assertEqual(set(eligible), {1})
        self.assertEqual(summary["eligible_window_count"], 1)
        self.assertEqual(eligible[1]["eligibility_status"], "ELIGIBLE")
        self.assertIsNotNone(summary["observed_share_l1_error"])
        drain_rows = [row for row in summary["windows"] if row["phase"] == "drain"]
        self.assertTrue(drain_rows)
        self.assertTrue(all(
            row["eligibility_status"] == "MIXED_ACTIVE_DRAIN" for row in drain_rows
        ))

    def test_quota_history_observes_stalled_cycle_before_backlog_forms(self):
        scenario = FixedReadyScenario(
            ready_at=2,
            seed=6101,
            n_src=4,
            window=64,
            windows=1,
            heavy_work=65,
            heavy_p=1.0,
            sparse_p=1.0,
            ready_p=1.0,
            subwindow=16,
        )
        lane = run_lane(
            policy("CGOF", high_weight=1),
            scenario,
            True,
            max_active_cycles=64,
            fixed_horizon=True,
        )
        row = lane["classifier_trajectory"][0]
        history = row["quota_backlog_history"]
        self.assertEqual(history["observed_cycles"], 64)
        self.assertEqual(history["idle_cycles"], 1)
        self.assertEqual(history["ready_cycles"], 62)
        self.assertGreater(history["held_cycles"], 0)
        self.assertGreater(history["output_stall_cycles"], 0)
        self.assertEqual(history["all_source_fifo_nonempty_cycles"], 63)
        self.assertTrue(all(value > 0 for value in row["fifo_occupancy"]))
        summary = quota_summary(lane)
        self.assertEqual(
            summary["windows"][0]["eligibility_status"],
            "NOT_ALL_SOURCES_BACKLOGGED",
        )
        self.assertIsNone(summary["observed_share_l1_error"])


if __name__ == "__main__":
    unittest.main()
