#!/usr/bin/env python3
"""MODEL_ONLY replay of shared B/S counts; no queues or latency measurement."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refc.cxl_model.fai_alg2_model import (  # noqa: E402
    ALG2_EFFECTIVE_CLASS,
    ALG2_TRANSITIONS,
    STABLE_HIGH,
    STABLE_LOW,
)
from refc.cxl_model.fai_main_model import (  # noqa: E402
    EFFECTIVE_CLASS,
    MAIN_TRANSITIONS,
    threshold_evidence,
)
from refc.cxl_model.revision_baselines import MAIN_1W_TRANSITIONS  # noqa: E402

SCHEMA = "cxl-buffer-transition-screen-v2"
SPARSE_SLOTS = [0] + [1] * 5 + [2] * 5 + [3] * 5
HEAVY_SLOTS = [0] * 13 + [1, 2, 3]
VARIANTS = {
    "Main": {
        "initial": "H",
        "transitions": MAIN_TRANSITIONS,
        "effective": EFFECTIVE_CLASS,
        "stable": {"H", "L"},
    },
    "Main-1W": {
        "initial": "H",
        "transitions": MAIN_1W_TRANSITIONS,
        "effective": EFFECTIVE_CLASS,
        "stable": {"H", "L"},
    },
    "Algorithm-2": {
        "initial": STABLE_HIGH,
        "transitions": ALG2_TRANSITIONS,
        "effective": ALG2_EFFECTIVE_CLASS,
        "stable": {STABLE_HIGH, STABLE_LOW},
    },
}
SOURCE_PATHS = (
    "scripts/run_buffer_transition_screen.py",
    "scripts/test_run_buffer_transition_screen.py",
    "refc/cxl_model/fai_main_model.py",
    "refc/cxl_model/fai_alg2_model.py",
    "refc/cxl_model/revision_baselines.py",
    "refc/cxl_model/common_ctrl_model.py",
    "refc/cxl_model/fcfs_model.py",
    "refc/cxl_model/fifo_model.py",
    "specs/CXL_SPEC.md",
)


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_parameters(
    window: int,
    phase: int = 0,
    duration: int | None = None,
    direction: str = "down",
) -> None:
    if type(window) is not int or window not in (64, 256):
        raise ValueError("transition screen supports W64 or W256")
    if type(phase) is not int or not 0 <= phase < window:
        raise ValueError("phase must be an integer in [0, W)")
    if duration is not None and (type(duration) is not int or duration <= 0):
        raise ValueError("duration must be a positive integer or None")
    if direction not in ("down", "up"):
        raise ValueError("direction must be down or up")


def make_case(
    window: int = 256,
    phase: int = 0,
    duration: int | None = None,
    direction: str = "down",
) -> Dict[str, Any]:
    """Build realizable exogenous service counts, independent of classifiers."""
    check_parameters(window, phase, duration, direction)
    change = 3 * window + phase
    target = "Low" if direction == "down" else "High"
    events = [{"cycle": change, "target_effective": target}]
    end = change + 4 * window
    if duration is not None:
        events.append({
            "cycle": change + duration,
            "target_effective": "High" if direction == "down" else "Low",
        })
        end += duration
    end = ((end + window - 1) // window) * window
    counts = [[0] * 4 for _ in range(end // window)]
    for cycle in range(end):
        switched = cycle >= change and (
            duration is None or cycle < change + duration
        )
        is_heavy = switched if direction == "down" else not switched
        source = (HEAVY_SLOTS if is_heavy else SPARSE_SLOTS)[cycle % 16]
        counts[cycle // window][source] += 1
    return {
        "name": f"{direction}_p{phase}_{'persistent' if duration is None else duration}",
        "window": window,
        "phase": phase,
        "direction": direction,
        "duration_cycles": duration,
        "role_events": events,
        "counts": counts,
    }


def run_case(variant_name: str, case: Dict[str, Any]) -> Dict[str, Any]:
    window = case["window"]
    check_parameters(window, case["phase"], case["duration_cycles"], case["direction"])
    if variant_name not in VARIANTS:
        raise ValueError(f"unknown variant {variant_name!r}")
    counts = case["counts"]
    if not counts:
        raise ValueError("counts must contain at least one complete window")
    for b in counts:
        if (not isinstance(b, (list, tuple)) or len(b) != 4
                or any(type(value) is not int or value < 0 for value in b)
                or sum(b) > window):
            raise ValueError("counts require four nonnegative integers with sum <= W")
    end = len(counts) * window
    role_events = case["role_events"]
    if not role_events:
        raise ValueError("at least one role event is required")
    previous_cycle = -1
    for event in role_events:
        if not isinstance(event, dict):
            raise ValueError("role events must be records with cycle and target_effective")
        cycle = event.get("cycle")
        if (type(cycle) is not int or not previous_cycle < cycle < end
                or event.get("target_effective") not in ("High", "Low")):
            raise ValueError("role events require ordered cycles in [0, end) and High/Low")
        previous_cycle = cycle

    spec = VARIANTS[variant_name]
    effective_map = spec["effective"]
    states = [spec["initial"]] * 4
    rows = []
    timeline = [(0, states[0])]
    flips = []
    for index, b in enumerate(counts):
        before = states
        evidence = [threshold_evidence(4, value, sum(b)) for value in b]
        states = [spec["transitions"][state, value]
                  for state, value in zip(before, evidence)]
        visible = (index + 1) * window
        if (role_events[0]["cycle"] <= visible < end
                and effective_map[before[0]] != effective_map[states[0]]):
            flips.append(visible)
        rows.append({
            "window": index,
            "b_close": list(b),
            "s_close": sum(b),
            "evidence": evidence,
            "states_before": list(before),
            "states_after": list(states),
            "effective_before": [effective_map[state] for state in before],
            "effective_after": [effective_map[state] for state in states],
            "evidence_close_cycle": visible - 1,
            "effective_visible_cycle": visible,
        })
        timeline.append((visible, states[0]))

    events = []
    for index, event in enumerate(role_events):
        start = event["cycle"]
        stop = role_events[index + 1]["cycle"] if index + 1 < len(role_events) else end
        target = event["target_effective"]
        initial = next(state for cycle, state in reversed(timeline) if cycle <= start)
        samples = [(start, initial)] + [
            (cycle, state) for cycle, state in timeline
            if start < cycle < stop
        ]
        effective_visible = first_stable = settled = None
        for cycle, state in samples:
            if effective_map[state] == target and effective_visible is None:
                effective_visible = cycle
            if effective_map[state] == target and state in spec["stable"]:
                if first_stable is None:
                    first_stable = cycle
                if settled is None:
                    settled = cycle
            else:
                settled = None
        # The terminal snapshot has zero dwell and cannot undo an observed suffix.
        if stop == end:
            terminal = timeline[-1][1]
            if effective_map[terminal] == target:
                if effective_visible is None:
                    effective_visible = end
                if terminal in spec["stable"]:
                    if first_stable is None:
                        first_stable = end
                    if settled is None:
                        settled = end
        post_stable = None if settled is None else stop - settled
        reason = None
        if effective_visible is None:
            reason = "target effective class never became visible"
        elif settled is None:
            reason = "target stable state was not retained to the role observation end"
        elif post_stable < window:
            reason = "fewer than one observed window after target stable state"
        supporting = "DOWN" if target == "Low" else "UP"
        events.append({
            "role_change_cycle": start,
            "role_end_exclusive": stop,
            "target_effective": target,
            "already_target": effective_map[initial] == target,
            "first_supporting_evidence_close_cycle": next((
                row["evidence_close_cycle"] for row in rows
                if start <= row["evidence_close_cycle"] < stop
                and row["evidence"][0] == supporting
            ), None),
            "target_effective_visible_cycle": effective_visible,
            "target_effective_observed": effective_visible is not None and effective_visible < stop,
            "target_first_stable_visible_cycle": first_stable,
            "target_stable_visible_cycle": settled,
            "target_stable_observed": settled is not None and settled < stop,
            "post_target_stable_observation_cycles": post_stable,
            "status": "COMPLETE" if reason is None else "INCOMPLETE",
            "incomplete_reason": reason,
        })
    return {
        "variant": variant_name,
        "case": case["name"],
        "window": window,
        "phase": case["phase"],
        "direction": case["direction"],
        "duration_cycles": case["duration_cycles"],
        "counts_sha256": digest(counts),
        "rows": rows,
        "events": events,
        "effective_change_count": len(flips),
        "effective_change_cycles": flips,
        "observation_end_exclusive": end,
        "status": "COMPLETE" if all(e["status"] == "COMPLETE" for e in events)
                  else "INCOMPLETE",
        "latency_recovery": "NOT_MEASURED",
    }


def source_hashes() -> Dict[str, str]:
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in SOURCE_PATHS}


def run_screen(window: int = 256) -> Dict[str, Any]:
    check_parameters(window)
    sources_before = source_hashes()
    cases = [
        make_case(window, phase, duration, direction)
        for direction in ("down", "up")
        for phase in (0, window // 4, window - 1)
        for duration in (window // 2, window, 3 * window // 2, None)
    ]
    for name, neutral in (("down_then_keep", [window // 4] * 4),
                          ("down_then_idle", [0] * 4)):
        cases.append({
            "name": name, "window": window, "phase": 0, "direction": "down",
            "duration_cycles": None,
            "role_events": [{"cycle": 0, "target_effective": "Low"}],
            "counts": [[13 * window // 16, window // 16, window // 16, window // 16]]
                      + [neutral] * 3,
        })
    results = [run_case(variant, case) for case in cases for variant in VARIANTS]
    for case in cases:
        group = [row for row in results if row["case"] == case["name"]]
        if (len(group) != len(VARIANTS)
                or len({row["counts_sha256"] for row in group}) != 1):
            raise AssertionError("classifier variants did not replay identical B/S counts")
    if sources_before != source_hashes():
        raise RuntimeError("sources changed during transition replay")
    result = {
        "schema": SCHEMA,
        "scope": "MODEL_ONLY",
        "replay_status": "PASS",
        "window": window,
        "sources_sha256": sources_before,
        "input_pairing": "PASS",
        "results": results,
        "summary": {
            "input_case_count": len(cases),
            "case_count": len(results),
            "complete_count": sum(row["status"] == "COMPLETE" for row in results),
            "incomplete_count": sum(row["status"] == "INCOMPLETE" for row in results),
        },
        "contract": {
            "input": "synthetic exogenous service roles, not arrivals or closed-loop service",
            "n_src": 4,
            "observed_source": 0,
            "warmup_cycles": 3 * window,
            "seed": None,
            "reset": "all four source classifiers start High before cycle 0",
            "sparse_period16_counts": [1, 5, 5, 5],
            "heavy_period16_counts": [13, 1, 1, 1],
            "service_slots_period16": {"sparse": SPARSE_SLOTS, "heavy": HEAVY_SLOTS},
            "slot_index_rule": "absolute cycle modulo 16, including the role-change cycle",
            "phase_cycles": [0, window // 4, window - 1],
            "noise_duration_cycles": [window // 2, window, 3 * window // 2],
            "persistent_min_duration_cycles": 4 * window,
            "settle": "target stable state retained to the role observation end",
            "complete": "at least W executed cycles after settle in that role",
            "flip_count": "source0 effective changes after first role change, visible before end",
            "terminal_snapshot": "next-cycle state at end, with zero observed dwell",
        },
        "limitations": [
            "classifier transition timing only; deterministic input, no seed replicates",
            "INCOMPLETE describes target-settle observability, not replay failure",
            "directed KEEP/S0 controls use shared window counts without role warmup",
            "no queueing, latency recovery, CXL response or application evidence",
        ],
    }
    result["screen_sha256"] = digest(result)
    return result


def self_check(window: int = 256) -> Dict[str, Any]:
    result = run_screen(window)
    case = {
        "name": "persistent_control", "window": window, "phase": 0,
        "direction": "down", "duration_cycles": None,
        "role_events": [{"cycle": 0, "target_effective": "Low"}],
        "counts": [[13 * window // 16, window // 16, window // 16, window // 16]] * 3,
    }
    for variant, first_effective in (
        ("Main", 2 * window), ("Main-1W", window), ("Algorithm-2", window)
    ):
        observed = run_case(variant, case)["events"][0]
        if observed["target_effective_visible_cycle"] != first_effective:
            raise AssertionError(f"{variant} target-effective timing changed")
        expected_stable = window if variant == "Main-1W" else 2 * window
        if observed["target_stable_visible_cycle"] != expected_stable:
            raise AssertionError(f"{variant} stable-state timing changed")
    case["counts"] = case["counts"][:2]
    terminal = run_case("Main", case)["events"][0]
    if terminal["status"] != "INCOMPLETE" or terminal["post_target_stable_observation_cycles"] != 0:
        raise AssertionError("terminal snapshot manufactured a post-settle window")
    for row in result["results"]:
        if row["case"] in ("down_then_keep", "down_then_idle"):
            expected = 0 if row["variant"] == "Main" else 1
            if row["effective_change_count"] != expected:
                raise AssertionError("single-window filtering behavior changed")
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--window", type=int, choices=(64, 256), default=256)
    result.add_argument("--output", type=Path)
    result.add_argument("--self-check", action="store_true")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    result = self_check(args.window) if args.self_check else run_screen(args.window)
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
            "replay_status": result["replay_status"],
            "summary": result["summary"],
            "sha256": result["screen_sha256"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
