"""Hand-derived checks for the passive primary phase recorder (no simulator needed)."""

from collections import Counter
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim" / "common"))
from primary_phase_metrics import PrimaryPhaseMetrics, histogram_stats  # noqa: E402


def legacy(generated, accepted, fires, waits, gen_waits):
    return {"generated": generated, "generated_but_unaccepted": generated - accepted,
            "input_push_count": accepted, "fires_measurement": fires,
            "wait_acceptance_to_fire": {"all_completed": histogram_stats(Counter(waits))},
            "generation_to_acceptance": histogram_stats(Counter(gen_waits))}


def hand_trace():
    recorder = PrimaryPhaseMetrics([(0, 2, "A"), (2, 1, "B"), (3, 2, "A")], 2, 5)
    recorder.observe(0, [(0, 101), (1, 202)], [(0, 101)], None, 0, 1)
    recorder.observe(1, [(0, 303), (1, 404)], [(0, 303), (1, 202)], (0, 101), 1, 1)
    recorder.observe(2, [(0, 505)], [], (1, 202), 1, 1)
    recorder.observe(3, [], [(1, 404)], (0, 303), 1, 1)
    recorder.observe(4, [(0, 606)], [], None, 1, 0)
    recorder.freeze()
    recorder.drain_fire(5, 1, 404)
    return recorder


def test_boundaries_carryover_same_edge_cohorts_and_drain():
    r = hand_trace().result(legacy(6, 4, 3, [1, 1, 2, 2], [0, 0, 1, 2]))
    a, b, c = r["segments"]
    assert [(s["generated"], s["accepted"], s["fires"]) for s in (a, b, c)] == [(4, 3, 1), (1, 0, 1), (1, 1, 1)]
    assert a["generated_per_source"] == [2, 2]
    assert a["accepted_per_source"] == [2, 1]
    assert b["fires_per_source"] == [0, 1]
    assert a["acceptance_to_fire_completed"]["histogram"] == {"1": 2, "2": 1}
    assert b["acceptance_to_fire_completed"]["mean"] is None
    assert c["acceptance_to_fire_drain_completed"]["histogram"] == {"2": 1}
    # Generated in the first phase, accepted in the third: belongs to the first gen cohort.
    assert a["generation_to_acceptance_completed"]["histogram"] == {"0": 2, "1": 1, "2": 1}
    assert a["generation_censored_at_phase_end"]["histogram"] == {"1": 1}
    assert a["generation_censored_at_measurement_end"]["count"] == 0
    assert b["generation_censored_at_phase_end"]["histogram"] == {"1": 1}
    assert b["generation_censored_at_measurement_end"]["histogram"] == {"3": 1}
    assert c["generation_censored_at_measurement_end"]["histogram"] == {"1": 1}
    # This frozen age remains even after the accepted request completes in drain.
    assert c["acceptance_censored_at_measurement_end"]["histogram"] == {"2": 1}
    assert a["acceptance_censored_at_phase_end"]["histogram"] == {"1": 2}
    assert b["fifo_occupancy_pre_edge"]["sum_per_source"] == [1, 1]
    assert c["producer_backlog_after_generation"]["sum_total"] == 4
    assert c["producer_backlog_post_edge"]["sum_total"] == 3
    pooled = r["by_kind"]["A"]
    assert pooled["cycles"] == 4 and pooled["ready_cycles"] == 3
    assert pooled["fifo_occupancy_pre_edge"]["sum_total"] == 3
    assert pooled["fifo_occupancy_pre_edge"]["mean_total"] == 0.75
    assert pooled["fifo_occupancy_pre_edge"]["min_total"] == 0
    assert pooled["fifo_occupancy_pre_edge"]["max_total"] == 1
    assert pooled["producer_backlog_after_generation"]["max_total"] == 3
    assert pooled["stall_cycles"] == 1 and pooled["idle_ready_cycles"] == 1
    assert pooled["acceptance_to_fire_completed"]["histogram"] == {"1": 2, "2": 2}


def test_boundary_held_drain_only_excluded_and_empty_statistics():
    p = PrimaryPhaseMetrics([(0, 1, "idle")], 1, 1)
    p.observe(0, [(0, 77)], [], None, 0, 0)
    p.freeze()
    # A later boundary-held push is deliberately never passed to the recorder.
    r = p.result(legacy(1, 0, 0, [], []))["segments"][0]
    assert r["idle_not_ready_cycles"] == 1
    assert r["generated"] == 1 and r["accepted"] == r["fires"] == 0
    assert r["generation_censored_at_measurement_end"]["histogram"] == {"1": 1}
    assert r["acceptance_to_fire_completed"] == {
        "count": 0, "sum": 0, "mean": None, "p99_nearest_rank": None,
        "min": None, "max": None, "histogram": {}}


def test_exact_nearest_rank_and_count_weighted_pooling():
    assert histogram_stats(Counter(range(1, 101)))["p99_nearest_rank"] == 99
    assert histogram_stats(Counter({2: 99, 900: 1}))["p99_nearest_rank"] == 2
    assert histogram_stats(Counter({2: 99, 900: 1}))["sum"] == 1098


@pytest.mark.parametrize("phases", [[], [(1, 2, "x")], [(0, 0, "x")],
                                      [(0, 1, "x"), (0, 1, "x")], [(0, 2, "")]])
def test_malformed_phase_partition_rejected(phases):
    with pytest.raises(AssertionError):
        PrimaryPhaseMetrics(phases, 2, 2)


@pytest.mark.parametrize("generated,pushes,fire,valid,ready", [
    ([(2, 1)], [], None, 0, 1),
    ([(0, -1)], [], None, 0, 1),
    ([(0, 1), (1, 1)], [], None, 0, 1),
    ([], [(0, 1)], None, 0, 1),
    ([(0, 1)], [(0, 2)], None, 0, 1),
    ([(0, 1)], [(0, 1), (0, 1)], None, 0, 1),
    ([(0, 1)], [(0, 1)], (0, 1), 1, 1),
    ([], [], None, 1, 1),
    ([], [], (0, 1), 1, 0),
])
def test_malformed_events_rejected(generated, pushes, fire, valid, ready):
    p = PrimaryPhaseMetrics([(0, 2, "x")], 2, 2)
    with pytest.raises(AssertionError):
        p.observe(0, generated, pushes, fire, valid, ready)


def test_full_same_edge_push_pop_rejected():
    p = PrimaryPhaseMetrics([(0, 2, "x")], 1, 2, depth=1)
    p.observe(0, [(0, 1)], [(0, 1)], None, 0, 1)
    with pytest.raises(AssertionError, match="full FIFO"):
        p.observe(1, [(0, 2)], [(0, 2)], (0, 1), 1, 1)


def test_freeze_drain_sequence_and_legacy_mismatch_rejected():
    p = PrimaryPhaseMetrics([(0, 1, "x")], 1, 1)
    with pytest.raises(AssertionError):
        p.freeze()
    with pytest.raises(AssertionError):
        p.observe(1, [], [], None, 0, 1)
    p.observe(0, [(0, 1)], [(0, 1)], None, 0, 1)
    with pytest.raises(AssertionError):
        p.drain_fire(1, 0, 1)
    p.freeze()
    with pytest.raises(AssertionError):
        p.result(legacy(1, 1, 0, [], [0]))
    with pytest.raises(AssertionError):
        p.observe(1, [], [], None, 0, 1)
    p.drain_fire(1, 0, 1)
    with pytest.raises(AssertionError):
        p.result(legacy(1, 1, 1, [1], [0]))
