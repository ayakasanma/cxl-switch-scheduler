#!/usr/bin/env python3
"""MODEL_ONLY closed-loop Buffer screening for CGOF(2:1) and CGOF(1:1).

The model reuses the accepted common FIFO/hold/controller and CGOF credit path.
Arrival and ready traces are generated once per seed/scenario and replayed by
every classifier variant.  The output is scheduler-model evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import deque
from pathlib import Path
import sys
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sim/common"))

from refc.cxl_model.experimental import (
    CLASSIFIERS,
    ExperimentalSwitchModel,
)
from refc.cxl_model.fai_main_model import EFFECTIVE_CLASS, HIGH, LOW
from refc.cxl_model.diagnosis import jsonable
from sim.performance.followup import Gaps, StreamStats, stats as stream_stats

SCHEMA = "cxl-buffer-closed-loop-screen-v1"
CONTRACT = "cxl-buffer-closed-loop-v1"
MODEL_SCOPE = "MODEL_ONLY"
N_SRC = 4
WINDOW = 256
DEPTH = 16
READY_P = 0.90
HEAVY_P = 1.00
SPARSE_P = 0.05
BASELINE_WINDOWS = 3
TAIL_WINDOWS = 4
PERSISTENT_WINDOWS = 4
MAX_DRAIN_WINDOWS = 4
SOURCE_PATHS = (
    "scripts/run_buffer_closed_loop.py",
    "scripts/test_run_buffer_closed_loop.py",
    "refc/cxl_model/experimental.py",
    "refc/cxl_model/diagnosis.py",
    "refc/cxl_model/common_ctrl_model.py",
    "refc/cxl_model/fifo_model.py",
    "refc/cxl_model/fcfs_model.py",
    "refc/cxl_model/fai_main_model.py",
    "refc/cxl_model/revision_baselines.py",
    "sim/performance/followup.py",
    "sim/switch_top_fai/fai_stream.py",
    "sim/common/traffic_trace.py",
    "refc/tests/test_experimental.py",
    "refc/tests/test_diagnosis.py",
    "specs/CXL_SPEC.md",
    "docs/reviews/buffer-closed-loop-plan-20261101.md",
)
STAGES = ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire")


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _fraction(seed: int, stream: str, cycle: int, source: int = 0) -> float:
    raw = hashlib.sha256(
        f"cxl-buffer-closed-loop-v1:{seed}:{stream}:{cycle}:{source}".encode("ascii")
    ).digest()
    return int.from_bytes(raw[:8], "big") / float(1 << 64)


def _descriptor(seed: int, cycle: int, source: int) -> int:
    raw = hashlib.sha256(
        f"cxl-buffer-closed-loop-desc-v1:{seed}:{cycle}:{source}".encode("ascii")
    ).digest()
    return int.from_bytes(raw[:16], "big") & ((1 << 105) - 1)


def _percentile(values: Sequence[int], fraction: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def stats(values: Iterable[int]) -> Dict[str, Any]:
    samples = list(values)
    if not samples:
        return {
            "count": 0, "mean": None, "p50": None, "p90": None,
            "p95": None, "p99": None, "max": None,
        }
    return {
        "count": len(samples),
        "mean": sum(samples) / len(samples),
        "p50": _percentile(samples, 0.50),
        "p90": _percentile(samples, 0.90),
        "p95": _percentile(samples, 0.95),
        "p99": _percentile(samples, 0.99),
        "max": max(samples),
    }


class Request:
    __slots__ = (
        "generation_cycle", "source", "generation_role", "description",
        "event_index", "hot", "accepted_cycle", "fired_cycle",
    )

    def __init__(
        self,
        generation_cycle: int,
        source: int,
        generation_role: str,
        description: int,
        event_index: int,
        hot: bool,
    ) -> None:
        self.generation_cycle = generation_cycle
        self.source = source
        self.generation_role = generation_role
        self.description = description
        self.event_index = event_index
        self.hot = hot
        self.accepted_cycle: Optional[int] = None
        self.fired_cycle: Optional[int] = None


class BufferScenario:
    """Deterministic arrivals plus a continuous role schedule."""

    def __init__(
        self,
        seed: int,
        phase: int = 0,
        duration: Optional[int] = None,
        direction: str = "down",
        window: int = WINDOW,
    ) -> None:
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if window not in (64, 256):
            raise ValueError("window must be W64 or W256")
        if type(phase) is not int or not 0 <= phase < window:
            raise ValueError("phase must be in [0,W)")
        if duration is not None and (type(duration) is not int or duration <= 0):
            raise ValueError("duration must be positive or None")
        if direction not in ("down", "up"):
            raise ValueError("direction must be down or up")
        self.seed, self.window, self.phase = seed, window, phase
        self.duration, self.direction = duration, direction
        # down: R0 -> R3; up: R3 -> R0.
        self.initial_hot = 0 if direction == "down" else 3
        self.switched_hot = 3 if direction == "down" else 0
        self.role_change = BASELINE_WINDOWS * window + phase
        if duration is None:
            self.role_end = self.role_change + PERSISTENT_WINDOWS * window
            self.end_exclusive = self.role_end
        else:
            self.role_end = self.role_change + duration
            self.end_exclusive = self.role_end + TAIL_WINDOWS * window

        self.hot_sources = []
        for cycle in range(self.end_exclusive):
            if cycle < self.role_change:
                hot = self.initial_hot
            elif cycle < self.role_end:
                hot = self.switched_hot
            else:
                hot = self.initial_hot
            self.hot_sources.append(hot)

        self.events = [
            {
                "start": 0,
                "stop": self.role_change,
                "target_effective": LOW,
                "hot_source": self.initial_hot,
                "role_id": f"R{self.initial_hot}",
                "name": "baseline",
            },
            {
                "start": self.role_change,
                "stop": self.role_end,
                "target_effective": LOW,
                "hot_source": self.switched_hot,
                "role_id": f"R{self.switched_hot}",
                "name": "switched",
            },
        ]
        if duration is not None:
            self.events.append({
                "start": self.role_end,
                "stop": self.end_exclusive,
                "target_effective": LOW,
                "hot_source": self.initial_hot,
                "role_id": f"R{self.initial_hot}_return",
                "name": "return",
            })
        else:
            self.events[1]["stop"] = self.end_exclusive

        self.arrivals: List[List[Tuple[int, int]]] = []
        for cycle in range(self.end_exclusive):
            row = []
            for source in range(N_SRC):
                probability = HEAVY_P if source == self.hot_sources[cycle] else SPARSE_P
                if _fraction(seed, "arrival", cycle, source) < probability:
                    row.append((source, _descriptor(seed, cycle, source)))
            self.arrivals.append(row)
        self.ready_trace = [
            int(_fraction(seed, "ready", cycle) < READY_P)
            for cycle in range(self.end_exclusive + MAX_DRAIN_WINDOWS * window)
        ]
    def generation_role(self, cycle: int, source: int) -> str:
        return self.events[self.event_index(cycle)]["role_id"]

    def ready(self, cycle: int) -> bool:
        return bool(self.ready_trace[cycle])

    def config(self) -> Dict[str, Any]:
        return {
            "generator": CONTRACT, "seed": self.seed, "window": self.window,
            "n_src": N_SRC, "depth": DEPTH, "ordering": "oldest-first",
            "profile": "over", "hot_p": HEAVY_P, "other_p": SPARSE_P,
            "ready_p": READY_P, "phase": self.phase, "duration": self.duration,
            "direction": self.direction, "role_change_cycle": self.role_change,
            "generation_end_exclusive": self.end_exclusive,
            "max_drain_cycles": MAX_DRAIN_WINDOWS * self.window,
            "role_schedule": self.events,
            "sampling": "sha256(seed,stream,cycle,source); no periodic slots",
        }

    def input_hashes(self) -> Dict[str, str]:
        if len(self.arrivals) != self.end_exclusive:
            raise ValueError("arrival trace does not match the common horizon")
        if len(self.ready_trace) != self.end_exclusive + MAX_DRAIN_WINDOWS * self.window:
            raise ValueError("ready trace does not cover the active and drain horizons")
        parts = {
            "arrival_sha256": digest(self.arrivals),
            "ready_sha256": digest(self.ready_trace),
            "role_schedule_sha256": digest(self.events),
        }
        return {**parts, "scenario_sha256": digest({"config": self.config(), **parts})}

    @property
    def input_sha256(self) -> str:
        return self.input_hashes()["scenario_sha256"]

    def event_index(self, cycle: int) -> int:
        for index, event in enumerate(self.events):
            if event["start"] <= cycle < event["stop"]:
                return index
        raise ValueError(f"cycle {cycle} outside active event interval")


def _event_timing(
    scenario: BufferScenario,
    event: Dict[str, Any],
    event_index: int,
    timeline: Sequence[Tuple[int, Tuple[str, ...]]],
    windows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    start, stop = event["start"], event["stop"]
    source = event["hot_source"]
    target = event["target_effective"]
    initial = next(state for cycle, state in reversed(timeline) if cycle <= start)
    samples = [(start, initial)] + [
        (cycle, state) for cycle, state in timeline if start < cycle < stop
    ]
    effective_visible = settled = None
    for cycle, state in samples:
        effective = EFFECTIVE_CLASS[state[source]]
        if effective == target and effective_visible is None:
            effective_visible = cycle
        if effective == target and state[source] in ("H", "L"):
            if settled is None:
                settled = cycle
        else:
            settled = None
    # A close at the exact end is a boundary, not an observed dwell period.
    terminal = next((state for cycle, state in timeline if cycle == stop), None)
    if terminal is not None and EFFECTIVE_CLASS[terminal[source]] == target:
        if effective_visible is None:
            effective_visible = stop
        if terminal[source] in ("H", "L") and settled is None:
            settled = stop
    post_settle = None if settled is None else stop - settled
    if effective_visible is None:
        reason = "NO_TARGET_CLASS"
    elif settled is None:
        reason = "NO_STABLE_SETTLE"
    elif post_settle < scenario.window:
        reason = "POST_SETTLE_LT_W"
    else:
        reason = None
    support = "DOWN" if target == LOW else "UP"
    closes = [row for row in windows if start <= row["closing_cycle"] < stop]
    supporting = next((row for row in closes if row["evidence"][source] == support), None)
    changes = sum(
        start <= cycle < stop
        and EFFECTIVE_CLASS[state[source]] != EFFECTIVE_CLASS[timeline[index - 1][1][source]]
        for index, (cycle, state) in enumerate(timeline) if index > 0
    )
    return {
        "event_index": event_index,
        "event": event["name"],
        "role_change_cycle": start,
        "role_id": event["role_id"],
        "hot_source": source,
        "end_exclusive": stop,
        "observations_cycles": stop - start,
        "target_effective": target,
        "already_target": EFFECTIVE_CLASS[initial[source]] == target,
        "first_support_close": (
            None if supporting is None else supporting["closing_cycle"]
        ),
        "first_effective_visible": effective_visible,
        "target_effective_observed": (
            effective_visible is not None and effective_visible < stop
        ),
        "first_stable_visible": settled,
        "stable_suffix_start": settled,
        "target_stable_observed": settled is not None and settled < stop,
        "post_settle_cycles": post_settle,
        "effective_change_count": changes,
        "close_cycles": [row["closing_cycle"] for row in closes],
        "status": "COMPLETE" if reason is None else "INCOMPLETE",
        "reason": reason,
    }


def _cohort_metrics(rows: Sequence[Request], active_end: int, role_end: int) -> Dict[str, Any]:
    accepted = [row for row in rows if row.accepted_cycle is not None]
    fired = [row for row in rows if row.fired_cycle is not None]
    at_active = sum(row.accepted_cycle < active_end for row in accepted)
    fired_active = sum(row.fired_cycle < active_end for row in fired)
    result = {
        "generated": len(rows), "accepted": len(accepted), "fired": len(fired),
        "fired_active": fired_active, "fired_drain": len(fired) - fired_active,
        "censored": len(rows) - len(fired),
        "unaccepted_at_cut": len(rows) - len(accepted),
        "accepted_unfired_at_cut": len(accepted) - len(fired),
        "unaccepted_at_active_end": len(rows) - at_active,
        "accepted_unfired_at_active_end": at_active - fired_active,
        "completed_after_role_end": sum(row.fired_cycle >= role_end for row in fired),
        "stage_censored": {
            "generation_to_acceptance": len(rows) - len(accepted),
            "acceptance_to_fire": len(accepted) - len(fired),
            "generation_to_fire": len(rows) - len(fired),
        },
        "generation_to_acceptance": stats(
            row.accepted_cycle - row.generation_cycle for row in accepted
        ),
        "acceptance_to_fire": stats(
            row.fired_cycle - row.accepted_cycle for row in fired
        ),
        "generation_to_fire": stats(
            row.fired_cycle - row.generation_cycle for row in fired
        ),
    }
    assert result["generated"] == result["accepted"] + result["unaccepted_at_cut"]
    assert result["accepted"] == result["fired"] + result["accepted_unfired_at_cut"]
    return result


def _latency_block(
    rows: Sequence[Request], active_end: int, role_end: int,
) -> Dict[str, Any]:
    return {
        **_cohort_metrics(rows, active_end, role_end),
        "hot": _cohort_metrics([row for row in rows if row.hot], active_end, role_end),
        "sparse": _cohort_metrics([row for row in rows if not row.hot], active_end, role_end),
        "by_source": [
            {"source": source, **_cohort_metrics(
                [row for row in rows if row.source == source], active_end, role_end
            )} for source in range(N_SRC)
        ],
    }


def _queue_metrics() -> Dict[str, Any]:
    return {
        "cycles": 0, "ready": 0, "fires": 0, "held_cycles": 0,
        "output_stall_cycles": 0, "avoidable_bubbles": 0,
        "occupancy": [StreamStats() for _ in range(N_SRC)],
        "producer_backlog": [StreamStats() for _ in range(N_SRC)],
        "gaps": [Gaps() for _ in range(N_SRC)],
    }


def _queue_result(row: Dict[str, Any]) -> Dict[str, Any]:
    return jsonable({
        **{key: value for key, value in row.items()
           if key not in ("occupancy", "producer_backlog", "gaps")},
        "occupancy": [stream_stats(value) for value in row["occupancy"]],
        "producer_backlog": [stream_stats(value) for value in row["producer_backlog"]],
        "gaps": [value.as_dict() for value in row["gaps"]],
    })


def run_lane(
    scenario: BufferScenario,
    classifier: str,
    high_weight: int,
) -> Dict[str, Any]:
    if classifier not in CLASSIFIERS:
        raise ValueError(f"unknown classifier {classifier!r}")
    if type(high_weight) is not int or high_weight not in (1, 2):
        raise ValueError("high_weight must be 1 or 2")
    policy = f"CGOF({high_weight}:1)"
    inputs = scenario.input_hashes()
    model = ExperimentalSwitchModel(
        n_src=N_SRC, policy=policy, window=scenario.window, depth=DEPTH,
        classifier=classifier,
    )
    model.commit(rst_n=False)
    pending: List[Deque[Request]] = [deque() for _ in range(N_SRC)]
    shadow: List[Deque[Request]] = [deque() for _ in range(N_SRC)]
    requests: List[Request] = []
    windows: List[Dict[str, Any]] = []
    timeline: List[Tuple[int, Tuple[str, ...]]] = [(0, model.classes())]
    pin_hash = hashlib.sha256()
    active_end = scenario.end_exclusive
    queue_metrics = {event["role_id"]: _queue_metrics() for event in scenario.events}
    queue_metrics["drain"] = _queue_metrics()
    previous_phase = None
    snapshots = {}
    executed = 0
    for cycle in range(active_end + MAX_DRAIN_WINDOWS * scenario.window):
        active = cycle < active_end
        if not active and not (any(pending) or any(shadow)):
            break
        index = scenario.event_index(cycle) if active else None
        phase = scenario.events[index]["role_id"] if active else "drain"
        metrics = queue_metrics[phase]
        if phase != previous_phase:
            if previous_phase is not None:
                for gap in queue_metrics[previous_phase]["gaps"]:
                    gap.boundary(False)
            for source, gap in enumerate(metrics["gaps"]):
                gap.boundary(bool(shadow[source]))
            previous_phase = phase
        for source, description in scenario.arrivals[cycle] if active else ():
            request = Request(
                cycle, source, scenario.generation_role(cycle, source),
                description, index, source == scenario.events[index]["hot_source"],
            )
            pending[source].append(request)
            requests.append(request)
        valid = [bool(row) for row in pending]
        descriptions = [row[0].description if row else 0 for row in pending]
        ready = scenario.ready(cycle)
        view = model.view(ready)
        occupancy = [len(row) for row in shadow]
        assert tuple(occupancy) == view.count
        assert view.out_valid == any(occupancy)
        metrics["cycles"] += 1
        metrics["ready"] += int(ready)
        metrics["held_cycles"] += int(view.held)
        metrics["output_stall_cycles"] += int(view.out_valid and not ready)
        metrics["avoidable_bubbles"] += int(ready and any(occupancy) and not view.fire)
        assert not metrics["avoidable_bubbles"], "avoidable output bubble"
        for source in range(N_SRC):
            metrics["occupancy"][source].add(occupancy[source])
            metrics["producer_backlog"][source].add(len(pending[source]))
        if classifier == "frozen":
            assert model.classes() == ("H",) * N_SRC, "frozen changed before edge"
        edge = model.commit(ready, valid, descriptions, rst_n=True)
        if classifier == "frozen":
            assert model.classes() == ("H",) * N_SRC, "frozen changed after edge"
        fired = None if edge.fired is None else edge.fired.source
        assert view.fire == (fired is not None)
        metrics["fires"] += int(fired is not None)
        pushed = []
        if fired is not None:
            if not shadow[fired]:
                raise AssertionError("model fired without a shadow head")
            request = shadow[fired].popleft()
            if request.description != edge.fired.entry.desc:
                raise AssertionError("shadow descriptor differs from model head")
            request.fired_cycle = cycle
        for source, entry in enumerate(edge.pushed):
            if entry is not None:
                if not pending[source]:
                    raise AssertionError("model accepted without a pending request")
                request = pending[source].popleft()
                if request.description != entry.desc:
                    raise AssertionError("pending descriptor differs from model push")
                request.accepted_cycle = cycle
                shadow[source].append(request)
                pushed.append((source, entry.desc))
        pin_hash.update((json.dumps([
            cycle, int(ready), valid, descriptions, list(view.in_ready), pushed,
            None if edge.fired is None else [fired, edge.fired.entry.desc],
            [view.out_source, view.out_desc] if view.held else None,
            [view.out_source, view.out_desc] if view.out_valid else None,
        ], separators=(",", ":")) + "\n").encode("ascii"))
        for source, gap in enumerate(metrics["gaps"]):
            assert model.occupancy(source) == len(shadow[source])
            gap.observe(bool(occupancy[source]), fired == source, ready, bool(shadow[source]))
        closing = edge.closing
        if closing is not None:
            closing_classes = tuple(closing["classes"])
            windows.append({
                "window": closing["window"],
                "phase": phase,
                "closing_cycle": cycle,
                "counts": list(closing["counts"]),
                "total": closing["total"],
                "evidence": list(closing["evidence"]),
                "classes_before": list(closing["old_classes"]),
                "classes_after": list(closing_classes),
                "effective_before": [
                    EFFECTIVE_CLASS[state] for state in closing["old_classes"]
                ],
                "effective_after": [
                    EFFECTIVE_CLASS[state] for state in closing_classes
                ],
                "effective_visible_cycle": cycle + 1,
            })
            assert sum(closing["counts"]) == closing["total"]
            timeline.append((cycle + 1, model.classes()))
        executed = cycle + 1
        if executed == active_end:
            snapshots["at_active_end"] = {
                "producer_backlog": [len(row) for row in pending],
                "fifo_occupancy": [len(row) for row in shadow],
            }
    for gap in queue_metrics[previous_phase]["gaps"]:
        gap.boundary(False)
    snapshots["at_final_cut"] = {
        "end_exclusive": executed,
        "producer_backlog": [len(row) for row in pending],
        "fifo_occupancy": [len(row) for row in shadow],
    }
    if inputs != scenario.input_hashes():
        raise AssertionError("scenario inputs changed during lane execution")

    event_metrics = []
    roles = {}
    for index, event in enumerate(scenario.events):
        timing = _event_timing(scenario, event, index, timeline, windows)
        event_requests = [row for row in requests if row.event_index == index]
        roles[event["role_id"]] = _latency_block(event_requests, active_end, event["stop"])
        timing["all_generations"] = roles[event["role_id"]]
        timing["class_observation_status"] = timing["status"]
        timing["censored_at_active_end"] = (
            timing["all_generations"]["unaccepted_at_active_end"]
            + timing["all_generations"]["accepted_unfired_at_active_end"]
        )
        if timing["all_generations"]["censored"]:
            timing["status"] = "INCOMPLETE"
            timing["completion_reason"] = "RIGHT_CENSORED_AT_DRAIN_BUDGET"
            if timing["reason"] is None:
                timing["reason"] = timing["completion_reason"]
        timing["completed_in_drain"] = timing["all_generations"]["fired_drain"]
        if timing["target_stable_observed"]:
            settle = timing["stable_suffix_start"]
            timing["post_settle_generations"] = _latency_block(
                [row for row in event_requests if row.generation_cycle >= settle],
                active_end, event["stop"],
            )
            timing["pre_settle_generations"] = _latency_block(
                [row for row in event_requests if row.generation_cycle < settle],
                active_end, event["stop"],
            )
        else:
            timing["post_settle_generations"] = None
            timing["pre_settle_generations"] = timing["all_generations"]
        event_metrics.append(timing)

    effective_changes = []
    for index, (cycle, state) in enumerate(timeline[1:], 1):
        for source in range(N_SRC):
            previous = EFFECTIVE_CLASS[timeline[index - 1][1][source]]
            current = EFFECTIVE_CLASS[state[source]]
            if current != previous:
                effective_changes.append({
                    "source": source, "effective_visible_cycle": cycle,
                    "from": previous, "to": current, "state": state[source],
                    "phase": "active" if cycle < active_end else "terminal_or_drain",
                })
    population = _latency_block(requests, active_end, active_end)
    assert population["unaccepted_at_cut"] == sum(len(row) for row in pending)
    assert population["accepted_unfired_at_cut"] == sum(len(row) for row in shadow)
    behavior = {
        "action_trace_sha256": pin_hash.hexdigest(),
        "population": population, "roles": roles,
        "queue_metrics": {phase: _queue_result(row) for phase, row in queue_metrics.items()},
        "snapshots": snapshots,
    }
    return {
        "schema": SCHEMA,
        "scope": MODEL_SCOPE,
        "policy": policy,
        "high_weight": high_weight,
        "classifier": classifier,
        "window": scenario.window,
        "phase": scenario.phase,
        "direction": scenario.direction,
        "duration_cycles": scenario.duration,
        "seed": scenario.seed,
        "inputs": inputs,
        "scenario_sha256": inputs["scenario_sha256"],
        **behavior,
        "behavior_sha256": digest(behavior),
        "cycles": active_end,
        "drain_cycles": executed - active_end,
        "max_drain_cycles": MAX_DRAIN_WINDOWS * scenario.window,
        "heavy_work": sum(row.hot for row in requests),
        "requests_generated": population["generated"],
        "requests_fired": population["fired"],
        "requests_censored": population["censored"],
        "context": {**event_metrics[0], "scope": "CONTEXT_ONLY"},
        "events": event_metrics[1:],
        "windows": windows,
        "effective_change_count": len(effective_changes),
        "effective_change_cycles": effective_changes,
        "latency_recovery": "NOT_DEFINED_THIS_ROUND",
        "execution_status": "COMPLETE",
        "drain_status": "COMPLETE" if not population["censored"] else "INCOMPLETE",
        "drain_reason": None if not population["censored"] else "RIGHT_CENSORED_AT_DRAIN_BUDGET",
        "evidence_status": (
            "COMPLETE" if all(row["status"] == "COMPLETE" for row in event_metrics[1:])
            else "INCOMPLETE"
        ),
    }


def _parse_seeds(value: str) -> Tuple[int, ...]:
    try:
        if "-" in value:
            parts = value.split("-")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise ValueError("invalid seed range")
            start, stop = map(int, parts)
            result = tuple(range(start, stop + 1))
        else:
            parts = value.split(",")
            if not all(part.isdigit() for part in parts):
                raise ValueError("invalid seed list")
            result = tuple(map(int, parts))
        if not result or len(set(result)) != len(result):
            raise ValueError("seeds must be nonempty and unique")
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    return result


def _source_hashes() -> Dict[str, str]:
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in SOURCE_PATHS
    }


def run_screen(
    seeds: Sequence[int] = (6101,),
    window: int = WINDOW,
    phases: Optional[Sequence[int]] = None,
    durations: Optional[Sequence[Optional[int]]] = None,
    directions: Sequence[str] = ("down", "up"),
) -> Dict[str, Any]:
    if window not in (64, 256):
        raise ValueError("window must be W64 or W256")
    if phases is None:
        phases = (0, window // 4, window - 1)
    if durations is None:
        durations = (window // 2, window, 3 * window // 2, None)
    for name, values in (("seeds", seeds), ("phases", phases),
                         ("durations", durations), ("directions", directions)):
        if not values or len(set(values)) != len(values):
            raise ValueError(f"{name} must be nonempty and unique")
    # Validate the entire grid before producing any measurements.
    for seed in seeds:
        for phase in phases:
            for duration in durations:
                for direction in directions:
                    BufferScenario(seed, phase, duration, direction, window)
    source_before = _source_hashes()
    scenarios = []
    results = []
    control_failures = []
    descriptive_differences = 0
    for seed in seeds:
        for phase in phases:
            for duration in durations:
                for direction in directions:
                    scenario = BufferScenario(
                        seed, phase, duration, direction, window
                    )
                    inputs = scenario.input_hashes()
                    scenarios.append({"config": scenario.config(), "inputs": inputs})
                    lane_results = [
                        run_lane(scenario, classifier, weight)
                        for weight in (2, 1)
                        for classifier in ("live", "1w", "frozen")
                    ]
                    if any(row["inputs"] != inputs for row in lane_results):
                        raise AssertionError("classifier variants used different inputs")
                    controls = [row for row in lane_results if row["high_weight"] == 1]
                    if len({row["behavior_sha256"] for row in controls}) != 1:
                        control_failures.append({
                            "seed": seed, "phase": phase, "duration": duration,
                            "direction": direction,
                        })
                    descriptive_differences += int(len({
                        row["action_trace_sha256"] for row in lane_results
                        if row["high_weight"] == 2
                    }) > 1)
                    results.extend(lane_results)
    if source_before != _source_hashes():
        raise RuntimeError("source changed during closed-loop screening")
    result = {
        "schema": SCHEMA,
        "contract_version": CONTRACT,
        "scope": MODEL_SCOPE,
        "status": "PASS" if not control_failures else "FAIL",
        "latency_recovery": "NOT_DEFINED_THIS_ROUND",
        "identity": {
            "seed": seeds[0] if len(seeds) == 1 else None,
            "seeds": list(seeds), "window": window, "n_src": N_SRC, "depth": DEPTH,
            "cohort": "smoke" if len(seeds) == 1 else "exploration",
        },
        "window": window,
        "seeds": list(seeds),
        "phases": list(phases),
        "durations": list(durations),
        "directions": list(directions),
        "configurations": [
            {"high_weight": weight, "classifier": classifier}
            for weight in (2, 1)
            for classifier in ("live", "1w", "frozen")
        ],
        "source_hashes": source_before,
        "scenarios": scenarios,
        "input_pairing": "PASS",
        "pairing": {
            "input_equal": True,
            "cgof1_control_equal": not control_failures,
            "cgof2_descriptive_only": True,
        },
        "negative_control": {
            "policy": "CGOF(1:1)",
            "status": "PASS" if not control_failures else "FAIL",
            "groups_checked": len(scenarios),
            "failures": control_failures,
        },
        "cgof2_descriptive": {
            "groups_with_action_difference": descriptive_differences,
            "groups_checked": len(scenarios),
            "ranking": "NOT_PERFORMED",
        },
        "summary": {
            "scenario_count": len(scenarios),
            "run_count": len(results),
            "generated": sum(row["requests_generated"] for row in results),
            "fired": sum(row["requests_fired"] for row in results),
            "censored": sum(row["requests_censored"] for row in results),
            "incomplete_drains": sum(row["drain_status"] == "INCOMPLETE" for row in results),
            "event_status_counts": {
                status: sum(event["status"] == status for row in results for event in row["events"])
                for status in ("COMPLETE", "INCOMPLETE")
            },
        },
        "variants": results,
        "limitations": [
            "MODEL_ONLY scheduler-service evidence; arrivals and ready are exogenous",
            "CGOF(1:1) is a negative control for classifier-dependent allocation",
            "classifier timing and generation-cohort latency are not queueing recovery proof",
            "no RTL, CXL response, application, PPA or W5M production evidence",
            "post_settle_generations are cohort distributions, not a scalar recovery bound",
        ],
        "notes": {
            "generation_role": "immutable generation interval R0/R3/R0_return or reversed",
            "drain": "no new arrivals; same scenario.ready(k); at most 4W cycles",
            "frozen": "all Effective classes fixed High; no transition table",
            "latency_recovery": "NOT_DEFINED_THIS_ROUND",
            "quantiles": "nearest-rank; only observed completions; missing latency is null",
            "queue_sampling": "beginning FIFO occupancy; producer backlog after current generation before acceptance",
            "gaps": "followup.Gaps; role and drain boundaries censor episodes",
        },
    }
    result["screen_sha256"] = digest(result)
    return result


def self_check(window: int = 64) -> Dict[str, Any]:
    screen = run_screen(
        seeds=(6101,), window=window, phases=(0,), directions=("down", "up"),
        durations=(None,),
    )
    if screen["status"] != "PASS" or screen["negative_control"]["status"] != "PASS":
        raise AssertionError("closed-loop self check failed")
    for row in screen["variants"]:
        if row["classifier"] == "frozen" and any(
            set(close["classes_after"]) != {"H"} for close in row["windows"]
        ):
            raise AssertionError("frozen classifier changed effective class")
    return screen


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--window", type=int, choices=(64, 256), default=256)
    result.add_argument("--seeds", type=_parse_seeds, default=(6101,))
    result.add_argument("--output", type=Path)
    result.add_argument("--self-check", action="store_true")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.output is not None and args.output.exists():
        raise FileExistsError(args.output)
    result = self_check(args.window) if args.self_check else run_screen(
        seeds=args.seeds, window=args.window
    )
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(text)
    else:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(text)
        print(json.dumps({
            "output": str(output),
            "status": result["status"],
            "sha256": result["screen_sha256"],
            "summary": result["summary"],
        }, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
