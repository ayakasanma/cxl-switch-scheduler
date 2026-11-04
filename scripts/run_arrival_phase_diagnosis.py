#!/usr/bin/env python3
"""MODEL_ONLY finite-work screening for arrival phase and near-load capacity.

Each phase rotates the same deterministic Sparse events within a fixed work horizon.
The Sparse event multiset, Heavy events, ready trace, policy quota and Heavy work are
therefore held fixed; only Sparse arrival phase changes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refc.cxl_model.diagnosis import (  # noqa: E402
    ARRIVAL_COMMON_GENERATION_CONTRACT,
    CONFIRMATION_SEEDS,
    EXPLORATION_SEEDS,
    LOAD_PROFILES,
    MODEL_SCOPE,
    DiagnosisScenario,
    _cycle_fraction,
    _descriptor,
    config_identity,
    digest_json,
    endpoint_metrics,
    heavy_fire_lag_summary,
    jsonable,
    paired_bootstrap,
    policy_configs,
    run_lane,
    seed_role_for,
)
from scripts.run_diagnosis import REQUIRED_SOURCE_PATHS, validate_source_paths  # noqa: E402
from scripts.run_diagnosis import write_json  # noqa: E402

SCHEMA = "cxl-arrival-phase-model-v2"
MANIFEST_SCHEMA = "cxl-arrival-phase-manifest-v2"
W256 = 256
W5M = 5_000_000
BOOTSTRAP_REPLICATES = 10_000
DEFAULT_POLICIES = ("CGOF_w1_oldest-first", "CGOF_w2_oldest-first")
ARRIVAL_REQUIRED_SOURCE_PATHS = tuple(sorted({
    *REQUIRED_SOURCE_PATHS,
    "scripts/run_arrival_phase_diagnosis.py",
    "scripts/test_run_arrival_phase_diagnosis.py",
}))


class ArrivalPhaseScenario(DiagnosisScenario):
    """Profile scenario with a fixed-work rotation of the Sparse arrival stream."""

    def __init__(self, *, phase: int, phase_horizon: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if type(phase) is not int or phase < 0:
            raise ValueError("phase must be a nonnegative integer")
        if type(phase_horizon) is not int or phase_horizon < 1:
            raise ValueError("phase_horizon must be a positive integer")
        self.phase, self.phase_horizon = phase, phase_horizon

    @classmethod
    def load_profile(
        cls, seed: int, profile: str, *, phase: int, phase_horizon: int, **kwargs: Any
    ) -> "ArrivalPhaseScenario":
        if profile not in LOAD_PROFILES:
            raise ValueError(f"load profile must be one of {sorted(LOAD_PROFILES)}")
        values = dict(LOAD_PROFILES[profile])
        values.update({key: value for key, value in kwargs.items() if value is not None})
        scenario = cls(
            seed=seed, phase=phase, phase_horizon=phase_horizon, **values
        )
        scenario.load_profile_name = profile
        return scenario

    def sparse_events(self, k: int) -> List[tuple[int, int]]:
        if k < 0 or k >= self.phase_horizon:
            return []
        source_cycle = (k - self.phase) % self.phase_horizon
        return [
            (h, _descriptor(self.seed, "sparse", source_cycle, h))
            for h in range(self.n_src)
            if h != self.heavy_source(k)
            and _cycle_fraction(self.seed, "sparse", source_cycle, h) < self.sparse_p
        ]

    def config(self) -> Dict[str, Any]:
        result = super().config()
        result.update(
            sparse_arrival_rotation="(cycle - phase) modulo phase_horizon",
            sparse_phase=self.phase,
            sparse_phase_horizon=self.phase_horizon,
            sparse_stop="declared phase horizon",
        )
        return result

    def sparse_work_sha256(self) -> str:
        events = []
        for k in range(self.phase_horizon):
            events.extend((k, source, desc) for source, desc in self.sparse_events(k))
        # Rotation changes release cycle but not the source/descriptor multiset.
        return digest_json(sorted((source, desc) for _k, source, desc in events))


def _source_hashes(root: Path = ROOT) -> Dict[str, str]:
    root = Path(root)
    validate_source_paths(root, ARRIVAL_REQUIRED_SOURCE_PATHS)
    return {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in ARRIVAL_REQUIRED_SOURCE_PATHS
    }


def _policies(identities: Sequence[str]) -> List[Dict[str, Any]]:
    index = {config_identity(row): row for row in policy_configs()}
    unknown = set(identities) - set(index)
    if unknown:
        raise ValueError(f"unknown policy identities: {sorted(unknown)}")
    return [index[name] for name in identities]


def _summary_row(pair: Dict[str, Any]) -> Dict[str, Any]:
    mixed, isolated = pair["mixed"], pair["isolated"]
    if mixed["status"] != "PASS" or isolated["status"] != "PASS":
        unavailable = {
            key: None
            for key in (
                "heavy_completion_cycle_mixed",
                "heavy_completion_cycle_isolated",
                "full_cohort_last_fire_cycle_mixed",
                "full_cohort_last_fire_cycle_isolated",
                "heavy_completion_delta_mixed_minus_isolated",
                "heavy_completed",
                "sparse_wait_mean",
                "sparse_wait_p99",
                "sparse_censored_at_cut",
                "heavy_completion_time_ratio_mixed_over_isolated",
                "completion_ratio",
                "throughput_ratio",
                "heavy_max_service_gap",
                "heavy_lag_max",
                "heavy_lag_endpoint",
                "heavy_lag_recovery_cycle",
                "heavy_lag_right_censored",
                "conservation",
            )
        }
        return {
            "status": mixed["status"] if mixed["status"] != "PASS" else isolated["status"],
            "mixed_status": mixed["status"],
            "isolated_status": isolated["status"],
            "generation_end_exclusive": mixed.get("generation_end_exclusive"),
            "active_cycles_mixed": mixed.get("active_cycles"),
            "active_cycles_isolated": isolated.get("active_cycles"),
            "timeout_cycle_mixed": mixed.get("timeout_cycle"),
            "timeout_cycle_isolated": isolated.get("timeout_cycle"),
            "generated_total_mixed": mixed.get("generated_total"),
            "accepted_total_mixed": mixed.get("accepted_total"),
            "fired_total_mixed": mixed.get("fired_total"),
            "uncompleted_mixed": (mixed.get("drain") or {}).get("uncompleted"),
            "uncompleted_isolated": (isolated.get("drain") or {}).get("uncompleted"),
            **unavailable,
        }
    metrics = endpoint_metrics(pair)
    sparse_latency = mixed["generation_roles"]["latency"]["sparse"]["generation_to_fire"]
    lag = pair["heavy_fire_lag"]
    return {
        "status": "PASS",
        "generation_end_exclusive": mixed["generation_end_exclusive"],
        "generated_demand": mixed["generated_total"],
        "sparse_generated": sum(mixed["phase_metrics"]["active"]["generated"][1:]),
        "ready_opportunities": mixed["phase_metrics"]["active"]["ready_cycles"],
        "empty_fifo_ready_bubbles": mixed["phase_metrics"]["active"]["idle_ready_cycles"],
        "nonempty_fifo_not_ready_bubbles": mixed["phase_metrics"]["active"][
            "output_stall_cycles"
        ],
        "avoidable_bubbles": mixed["phase_metrics"]["active"]["avoidable_bubbles"],
        "active_cycles": mixed["active_cycles"],
        "drain_cycles": mixed["drain_cycles"],
        "full_cohort_last_fire_cycle_mixed": mixed["full_cohort_last_fire_cycle"],
        "full_cohort_last_fire_cycle_isolated": isolated["full_cohort_last_fire_cycle"],
        "heavy_completion_cycle_mixed": mixed["heavy"]["actual_completion_cycle"],
        "heavy_completion_cycle_isolated": isolated["heavy"]["actual_completion_cycle"],
        "heavy_completion_delta_mixed_minus_isolated": (
            mixed["heavy"]["actual_completion_cycle"]
            - isolated["heavy"]["actual_completion_cycle"]
            if mixed["heavy"]["actual_completion_cycle"] is not None
            and isolated["heavy"]["actual_completion_cycle"] is not None
            else None
        ),
        "heavy_completed": mixed["heavy"]["completed"] and isolated["heavy"]["completed"],
        "sparse_wait_mean": sparse_latency["mean"],
        "sparse_wait_p99": sparse_latency["p99_nearest_rank"],
        "sparse_censored_at_cut": metrics["sparse_censored_at_cut"],
        "heavy_completion_time_ratio_mixed_over_isolated": metrics[
            "heavy_completion_ratio_mixed_over_isolated"
        ],
        "completion_ratio": metrics["heavy_completion_ratio_mixed_over_isolated"],
        "throughput_ratio": metrics["heavy_throughput_ratio_mixed_over_isolated"],
        "heavy_max_service_gap": metrics["heavy_max_service_gap"],
        "heavy_lag_max": lag["max_lag"],
        "heavy_lag_endpoint": lag["endpoint_lag"],
        "heavy_lag_recovery_cycle": lag["recovery_cycle"],
        "heavy_lag_right_censored": lag["right_censored"],
        "conservation": (
            mixed["conservation"]["final_generated_eq_accepted_eq_fired"]
            and isolated["conservation"]["final_generated_eq_accepted_eq_fired"]
        ),
    }


def _full_input_pairing(
    scenario: ArrivalPhaseScenario,
    generation_end_exclusive: int,
    mixed: Dict[str, Any],
    isolated: Dict[str, Any],
) -> Dict[str, Any]:
    expected_heavy = scenario.declared_heavy_arrivals(generation_end_exclusive)
    expected_sparse = scenario.declared_sparse_work_multiset(generation_end_exclusive)
    expected_ready = scenario.declared_ready_schedule(generation_end_exclusive)
    errors: List[str] = []
    if not expected_heavy:
        errors.append("declared Heavy arrival sequence is empty")
    if not expected_sparse:
        errors.append("declared Sparse work multiset is empty")

    lane_payloads = {}
    for lane_name, lane in (("mixed", mixed), ("isolated", isolated)):
        common = lane.get("common_generation")
        if not isinstance(common, dict):
            errors.append(f"{lane_name} lacks common-generation evidence")
            continue
        if common.get("contract_version") != ARRIVAL_COMMON_GENERATION_CONTRACT:
            errors.append(f"{lane_name} uses an incompatible arrival contract")
        if common.get("generation_end_exclusive") != generation_end_exclusive:
            errors.append(f"{lane_name} generation horizon differs")
        if common.get("generation_observed_cycles") != generation_end_exclusive:
            errors.append(f"{lane_name} did not observe the complete generation horizon")
        emitted_heavy = common.get("emitted_heavy_arrivals")
        if emitted_heavy != expected_heavy:
            errors.append(f"{lane_name} emitted Heavy arrivals differ from declaration")
        active_ready = common.get("active_ready_schedule")
        if active_ready != expected_ready:
            errors.append(f"{lane_name} active ready sequence differs from declaration")
        drain_ready = common.get("drain_ready_schedule") or []
        expected_drain_cycles = [
            generation_end_exclusive + offset
            for offset in range(lane.get("drain_cycles", 0))
        ]
        if [cycle for cycle, _ready in drain_ready] != expected_drain_cycles:
            errors.append(f"{lane_name} drain ready sequence is incomplete")
        for cycle, ready in drain_ready:
            if ready != scenario.ready(cycle):
                errors.append(f"{lane_name} drain replaced scenario.ready at cycle {cycle}")
                break
        lane_payloads[lane_name] = {
            "emitted_heavy_arrivals": emitted_heavy,
            "active_ready_schedule": active_ready,
            "emitted_sparse_work_multiset": common.get(
                "emitted_sparse_work_multiset"
            ),
        }

    mixed_payload = lane_payloads.get("mixed", {})
    isolated_payload = lane_payloads.get("isolated", {})
    if mixed_payload.get("emitted_sparse_work_multiset") != expected_sparse:
        errors.append("mixed Sparse work differs from the declared full multiset")
    if isolated_payload.get("emitted_sparse_work_multiset") != []:
        errors.append("isolated lane emitted Sparse work")
    if (
        mixed_payload.get("emitted_heavy_arrivals")
        != isolated_payload.get("emitted_heavy_arrivals")
    ):
        errors.append("mixed/isolated full Heavy arrival sequences differ")
    if (
        mixed_payload.get("active_ready_schedule")
        != isolated_payload.get("active_ready_schedule")
    ):
        errors.append("mixed/isolated full active ready sequences differ")
    actual_heavy = mixed_payload.get("emitted_heavy_arrivals") or []
    actual_ready = mixed_payload.get("active_ready_schedule") or []
    actual_sparse = mixed_payload.get("emitted_sparse_work_multiset") or []

    return {
        "valid": not errors,
        "errors": errors,
        "contract_version": ARRIVAL_COMMON_GENERATION_CONTRACT,
        "generation_end_exclusive": generation_end_exclusive,
        "heavy_arrivals_count": len(actual_heavy),
        "ready_cycles_checked": len(actual_ready),
        "sparse_work_count": len(actual_sparse),
        "declared_heavy_arrivals_count": len(expected_heavy),
        "declared_sparse_work_count": len(expected_sparse),
        "heavy_arrivals_match": (
            mixed_payload.get("emitted_heavy_arrivals") == expected_heavy
            == isolated_payload.get("emitted_heavy_arrivals")
        ),
        "ready_sequence_match": (
            mixed_payload.get("active_ready_schedule") == expected_ready
            == isolated_payload.get("active_ready_schedule")
        ),
        "sparse_work_multiset_match": (
            mixed_payload.get("emitted_sparse_work_multiset") == expected_sparse
        ),
        "heavy_arrivals": actual_heavy,
        "ready_schedule": actual_ready,
        "sparse_work_multiset": actual_sparse,
    }


def run_pair(
    config: Dict[str, Any],
    *,
    seed: int,
    profile: str,
    phase: int,
    phase_horizon: int,
    n_src: int,
    depth: int,
    window: int,
    heavy_work: int,
    subwindow: int,
    completion_margin_cycles: float,
    throughput_margin_fraction: float,
) -> Dict[str, Any]:
    scenario = ArrivalPhaseScenario.load_profile(
        seed,
        profile,
        phase=phase,
        phase_horizon=phase_horizon,
        n_src=n_src,
        window=window,
        windows=3,
        heavy_work=heavy_work,
        subwindow=subwindow,
    )
    effective = {**config, "depth": depth}
    generation_end_exclusive = max(
        phase_horizon, scenario.heavy_release_end_exclusive()
    )
    max_active = max(
        generation_end_exclusive,
        4 * heavy_work + 4 * window,
        phase_horizon + window,
    )
    max_drain = 4 * (heavy_work + n_src * window) + 1024
    mixed = run_lane(
        effective,
        scenario,
        True,
        max_active,
        max_drain,
        common_generation_horizon=generation_end_exclusive,
    )
    isolated = run_lane(
        effective,
        scenario,
        False,
        max_active,
        max_drain,
        common_generation_horizon=generation_end_exclusive,
    )
    input_pairing = _full_input_pairing(
        scenario, generation_end_exclusive, mixed, isolated
    )
    last_fire_cycles = [
        value + 1
        for value in (
            mixed.get("full_cohort_last_fire_cycle"),
            isolated.get("full_cohort_last_fire_cycle"),
            mixed["heavy"].get("actual_completion_cycle"),
            isolated["heavy"].get("actual_completion_cycle"),
        )
        if value is not None
    ]
    observation_end_exclusive = max([
        generation_end_exclusive,
        mixed["generation_observed_cycles"] + mixed["drain_cycles"],
        isolated["generation_observed_cycles"] + isolated["drain_cycles"],
        *last_fire_cycles,
    ])
    lag = heavy_fire_lag_summary(
        mixed["common_generation"]["post_edge_heavy_fire_change_points"],
        isolated["common_generation"]["post_edge_heavy_fire_change_points"],
        observation_end_exclusive=observation_end_exclusive,
        mixed_complete=mixed["heavy"]["completed"],
        isolated_complete=isolated["heavy"]["completed"],
    )
    pair = {
        "schema": SCHEMA,
        "scope": MODEL_SCOPE,
        "seed": seed,
        "profile": profile,
        "phase": phase,
        "phase_horizon": phase_horizon,
        "generation_end_exclusive": generation_end_exclusive,
        "config_id": config_identity(config),
        "config": jsonable(effective),
        "model_config": mixed["model_config"],
        "scenario": scenario.config(),
        "scenario_sha256": digest_json(scenario.config()),
        "mixed": mixed,
        "isolated": isolated,
        "input_pairing": input_pairing,
        "heavy_fire_lag": lag,
        "equivalence_margin_declared_before_run": {
            "completion_cycles": completion_margin_cycles,
            "throughput_fraction": throughput_margin_fraction,
        },
    }
    lane_statuses = (mixed["status"], isolated["status"])
    if lane_statuses == ("PASS", "PASS") and input_pairing["valid"]:
        pair["status"] = "PASS"
    elif "FAIL" not in lane_statuses and "TIMEOUT" in lane_statuses:
        pair["status"] = "TIMEOUT"
    else:
        pair["status"] = "FAIL"
    pair["summary"] = _summary_row(pair)
    summary = pair["summary"]
    if pair["status"] == "PASS":
        summary["within_declared_equivalence_margin"] = (
            abs(summary["heavy_completion_delta_mixed_minus_isolated"])
            <= completion_margin_cycles
            and abs(summary["throughput_ratio"] - 1.0)
            <= throughput_margin_fraction
        )
    return pair


def _phase_effects(
    records: Sequence[Dict[str, Any]],
    seeds: Sequence[int],
    *,
    smoke: bool = False,
) -> List[Dict[str, Any]]:
    index = {
        (row["config_id"], row["profile"], row["phase"], row["seed"]): row
        for row in records if row["status"] == "PASS"
    }
    full_cohort = tuple(sorted(seeds)) in (EXPLORATION_SEEDS, CONFIRMATION_SEEDS)
    phases = sorted({row["phase"] for row in records})
    results = []
    for config_id in sorted({row["config_id"] for row in records}):
        for profile in sorted({row["profile"] for row in records}):
            for phase in phases:
                missing = [
                    seed for seed in seeds
                    if (config_id, profile, phase, seed) not in index
                ]
                result = {
                    "id": f"{config_id}:{profile}:phase{phase}-vs-phase0",
                    "estimand": "phase_minus_phase0",
                    "candidate": f"phase{phase}",
                    "baseline": "phase0",
                    "policy": config_id,
                    "profile": profile,
                    "phase": phase,
                    "baseline_phase": 0,
                    "self_comparison": phase == 0,
                    "status": "PASS" if not missing else "MISSING",
                    "missing_seeds": missing,
                    "metrics": {},
                }
                if not missing and phase == 0:
                    for metric in (
                        "sparse_wait_p99",
                        "heavy_completion_delta_mixed_minus_isolated",
                        "heavy_completion_time_ratio_mixed_over_isolated",
                        "throughput_ratio",
                        "heavy_max_service_gap",
                    ):
                        result["metrics"][metric] = {
                            "status": "NOT_APPLICABLE",
                            "reason": "phase0 self-comparison",
                        }
                elif not missing:
                    rows = [index[(config_id, profile, phase, seed)] for seed in seeds]
                    base = [index[(config_id, profile, 0, seed)] for seed in seeds]
                    for metric in (
                        "sparse_wait_p99",
                        "heavy_completion_delta_mixed_minus_isolated",
                        "heavy_completion_time_ratio_mixed_over_isolated",
                        "throughput_ratio",
                        "heavy_max_service_gap",
                    ):
                        candidate = [row["summary"][metric] for row in rows]
                        baseline = [row["summary"][metric] for row in base]
                        if not smoke and full_cohort and all(
                            value is not None for value in candidate + baseline
                        ):
                            result["metrics"][metric] = {
                                "status": "COMPLETE",
                                **paired_bootstrap(
                                    candidate,
                                    baseline,
                                    seeds,
                                    replicates=BOOTSTRAP_REPLICATES,
                                ),
                            }
                        else:
                            result["metrics"][metric] = {
                                "status": "DESCRIPTIVE_ONLY",
                                "paired_deltas": [
                                    None if x is None or y is None else x - y
                                    for x, y in zip(candidate, baseline)
                                ],
                            }
                results.append(result)
    return results


def _paired_effects(
    records: Sequence[Dict[str, Any]],
    seeds: Sequence[int],
    *,
    smoke: bool = False,
) -> List[Dict[str, Any]]:
    """Deprecated name for the phase-minus-phase0 estimand."""
    return _phase_effects(records, seeds, smoke=smoke)


def _mixed_isolated_effects(
    records: Sequence[Dict[str, Any]],
    seeds: Sequence[int],
    *,
    smoke: bool = False,
) -> List[Dict[str, Any]]:
    """Paired mixed-minus-isolated endpoint contrasts within each phase."""
    index = {
        (row["config_id"], row["profile"], row["phase"], row["seed"]): row
        for row in records if row["status"] == "PASS"
    }
    full_cohort = tuple(sorted(seeds)) in (EXPLORATION_SEEDS, CONFIRMATION_SEEDS)
    results = []
    for config_id in sorted({row["config_id"] for row in records}):
        for profile in sorted({row["profile"] for row in records}):
            for phase in sorted({row["phase"] for row in records}):
                missing = [
                    seed for seed in seeds
                    if (config_id, profile, phase, seed) not in index
                ]
                result = {
                    "id": f"{config_id}:{profile}:phase{phase}:mixed-vs-isolated",
                    "estimand": "mixed_minus_isolated",
                    "candidate": "mixed",
                    "baseline": "isolated",
                    "policy": config_id,
                    "profile": profile,
                    "phase": phase,
                    "status": "PASS" if not missing else "MISSING",
                    "missing_seeds": missing,
                    "metrics": {},
                }
                if not missing:
                    rows = [
                        index[(config_id, profile, phase, seed)] for seed in seeds
                    ]
                    for metric, mixed_key, isolated_key in (
                        (
                            "heavy_completion_cycles",
                            "heavy_completion_cycle_mixed",
                            "heavy_completion_cycle_isolated",
                        ),
                        (
                            "heavy_completion_time_ratio_mixed_over_isolated",
                            "heavy_completion_time_ratio_mixed_over_isolated",
                            None,
                        ),
                    ):
                        if isolated_key is None:
                            values = [row["summary"][mixed_key] for row in rows]
                            paired = [None if value is None else value - 1.0 for value in values]
                            result["metrics"][metric] = {
                                "status": "DESCRIPTIVE_ONLY",
                                "interpretation": "ratio minus 1; lower is better",
                                "paired_deltas": paired,
                            }
                            continue
                        candidate = [row["summary"][mixed_key] for row in rows]
                        baseline = [row["summary"][isolated_key] for row in rows]
                        if not smoke and full_cohort and all(
                            value is not None for value in candidate + baseline
                        ):
                            result["metrics"][metric] = {
                                "status": "COMPLETE",
                                **paired_bootstrap(
                                    candidate,
                                    baseline,
                                    seeds,
                                    replicates=BOOTSTRAP_REPLICATES,
                                ),
                            }
                        else:
                            result["metrics"][metric] = {
                                "status": "DESCRIPTIVE_ONLY",
                                "paired_deltas": [
                                    None if x is None or y is None else x - y
                                    for x, y in zip(candidate, baseline)
                                ],
                            }
                results.append(result)
    return results


def _input_pairing(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    errors: List[str] = []
    by_case: Dict[tuple[str, str, int], List[Dict[str, Any]]] = {}
    for row in records:
        pairing = row.get("input_pairing") or {}
        if not pairing.get("valid"):
            errors.append(f"{row.get('id', '<unknown>')} has invalid full input pairing")
        if not pairing.get("heavy_arrivals_count"):
            errors.append(f"{row.get('id', '<unknown>')} has empty Heavy arrivals")
        if not pairing.get("sparse_work_count"):
            errors.append(f"{row.get('id', '<unknown>')} has empty Sparse work")
        key = (row["profile"], row["config_id"], row["seed"])
        by_case.setdefault(key, []).append(pairing)
    cross_phase_match = bool(by_case)
    for rows in by_case.values():
        first = rows[0] if rows else None
        if first is None or any(
            row.get("heavy_arrivals") != first.get("heavy_arrivals")
            or row.get("ready_schedule") != first.get("ready_schedule")
            or row.get("sparse_work_multiset") != first.get("sparse_work_multiset")
            for row in rows[1:]
        ):
            cross_phase_match = False
            errors.append("phase cases do not share the full common input sequences")
    heavy_ready_match = bool(records) and all(
        (row.get("input_pairing") or {}).get("heavy_arrivals_match", False)
        and (row.get("input_pairing") or {}).get("ready_sequence_match", False)
        for row in records
    )
    sparse_multiset_match = bool(records) and all(
        (row.get("input_pairing") or {}).get("sparse_work_multiset_match", False)
        and bool((row.get("input_pairing") or {}).get("sparse_work_multiset"))
        for row in records
    )
    return {
        "valid": not errors
        and heavy_ready_match
        and sparse_multiset_match
        and cross_phase_match,
        "all_heavy_ready_pairs_match": heavy_ready_match,
        "all_phase_sets_share_sparse_work": cross_phase_match,
        "all_sparse_work_multisets_match": sparse_multiset_match,
        "cases_checked": len(by_case),
        "records_checked": len(records),
        "errors": sorted(set(errors)),
    }


def _manifest(
    output: Path,
    command: Sequence[str],
    *,
    smoke: bool,
    seeds: Sequence[int],
    profiles: Sequence[str],
    phases: Sequence[int],
    policies: Sequence[Dict[str, Any]],
    settings: Dict[str, Any],
    jobs: Sequence[Dict[str, Any]],
    source_hashes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "scope": MODEL_SCOPE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": list(command),
        "output": str(output),
        "smoke": smoke,
        "seeds": list(seeds),
        "profiles": list(profiles),
        "phases": list(phases),
        "policies": jsonable(policies),
        "settings": settings,
        "jobs": jsonable(jobs),
        "source_hashes": _source_hashes() if source_hashes is None else source_hashes,
        "bootstrap": {
            "unit": "paired seed/run",
            "replicates": BOOTSTRAP_REPLICATES,
            "enabled": not smoke and tuple(sorted(seeds)) in (
                EXPLORATION_SEEDS,
                CONFIRMATION_SEEDS,
            ),
        },
    }
    manifest["manifest_sha256"] = digest_json(manifest)
    return manifest


def _job_id(profile: str, config_id: str, phase: int, seed: int) -> str:
    return f"{profile}__{config_id}__p{phase}__s{seed}".replace("/", "_")


def run_matrix(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    window = W256 if args.smoke else W5M
    if not args.smoke and not args.production_reviewed:
        raise ValueError("W5M requires --production-reviewed")
    seeds = tuple(args.seeds or (EXPLORATION_SEEDS if not args.smoke else [6101]))
    if args.smoke and not set(seeds).issubset(EXPLORATION_SEEDS):
        raise ValueError("smoke seeds must be exploration seeds")
    if not args.smoke:
        seed_role_for(seeds)
    profiles = tuple(sorted(args.profiles))
    phases = tuple(sorted(set(args.phases)))
    if 0 not in phases:
        raise ValueError("phase 0 baseline is required")
    heavy_work = args.heavy_work if args.heavy_work is not None else (
        512 if args.smoke else 20_000
    )
    if heavy_work < 1:
        raise ValueError("heavy work must be positive")
    phase_horizon = args.phase_horizon if args.phase_horizon is not None else heavy_work
    if phase_horizon < 1:
        raise ValueError("phase horizon must be positive")
    policies = _policies(args.policies)
    jobs = [
        {
            "id": _job_id(profile, config_identity(config), phase, seed),
            "profile": profile,
            "phase": phase,
            "seed": seed,
            "config_id": config_identity(config),
            "config": jsonable(config),
        }
        for profile in profiles
        for config in policies
        for phase in phases
        for seed in seeds
    ]
    settings = {
        "window": window,
        "n_src": args.n_src,
        "depth": args.depth,
        "heavy_work": heavy_work,
        "phase_horizon": phase_horizon,
        "subwindow": max(1, window // 4),
        "measurement_mode": "common_generation",
        "arrival_contract": ARRIVAL_COMMON_GENERATION_CONTRACT,
        "drain": "bounded scenario.ready drain after policy-independent horizon",
        "completion_equivalence_margin_cycles": args.completion_margin_cycles,
        "throughput_equivalence_margin_fraction": args.throughput_margin_fraction,
        "source_ready_pattern": "bernoulli",
    }
    source_hashes_before = _source_hashes()
    output.mkdir(parents=True, exist_ok=False)
    manifest = _manifest(
        output,
        sys.argv,
        smoke=args.smoke,
        seeds=seeds,
        profiles=profiles,
        phases=phases,
        policies=policies,
        settings=settings,
        jobs=jobs,
        source_hashes=source_hashes_before,
    )
    write_json(output / "manifest.json", manifest)
    records = []
    for index, job in enumerate(jobs):
        directory = output / "jobs" / f"{index:04d}-{job['id']}"
        directory.mkdir(parents=True)
        pair = run_pair(
            job["config"],
            seed=job["seed"],
            profile=job["profile"],
            phase=job["phase"],
            phase_horizon=phase_horizon,
            n_src=args.n_src,
            depth=args.depth,
            window=window,
            heavy_work=heavy_work,
            subwindow=settings["subwindow"],
            completion_margin_cycles=args.completion_margin_cycles,
            throughput_margin_fraction=args.throughput_margin_fraction,
        )
        write_json(directory / "pair.json", pair)
        records.append({
            "id": job["id"],
            "status": pair["status"],
            "seed": pair["seed"],
            "profile": pair["profile"],
            "phase": pair["phase"],
            "config_id": pair["config_id"],
            "generation_end_exclusive": pair["generation_end_exclusive"],
            "summary": pair["summary"],
            "input_pairing": pair["input_pairing"],
            "heavy_fire_lag": pair["heavy_fire_lag"],
        })
    after_hashes = _source_hashes()
    phase_effects = _phase_effects(records, seeds, smoke=args.smoke)
    mixed_isolated_effects = _mixed_isolated_effects(
        records, seeds, smoke=args.smoke
    )
    pairing = _input_pairing(records)
    passed = all(row["status"] == "PASS" for row in records)
    source_stable = after_hashes == manifest["source_hashes"]
    summary = {
        "schema": SCHEMA,
        "scope": MODEL_SCOPE,
        "production_evidence": False,
        "smoke": args.smoke,
        "overall_status": "PASS" if passed and source_stable and all((
            pairing["valid"],
            pairing["all_heavy_ready_pairs_match"],
            pairing["all_phase_sets_share_sparse_work"],
            pairing["all_sparse_work_multisets_match"],
        )) else "FAIL",
        "manifest_sha256": manifest["manifest_sha256"],
        "settings": settings,
        "seeds": list(seeds),
        "profiles": list(profiles),
        "phases": list(phases),
        "jobs_expected": len(jobs),
        "jobs_completed": sum(row["status"] == "PASS" for row in records),
        "input_pairing": pairing,
        "phase_effects": phase_effects,
        "mixed_isolated_effects": mixed_isolated_effects,
        "paired_effects": phase_effects,
        "deprecated_field_aliases": {
            "completion_ratio": (
                "use heavy_completion_time_ratio_mixed_over_isolated"
            ),
            "paired_effects": "use phase_effects",
        },
        "runs": records,
        "source_stable": source_stable,
        "source_hashes_after": after_hashes,
        "notes": [
            "MODEL_ONLY; fire is not memory bandwidth",
            "generation-to-fire is not memory-response latency",
            "Sparse arrival phases rotate one fixed descriptor multiset",
            "equivalence margins were recorded before execution",
            "W256 smoke is never inference evidence",
        ],
    }
    summary["summary_sha256"] = digest_json(summary)
    write_json(output / "summary.json", summary)
    print(json.dumps({
        "output": str(output),
        "overall_status": summary["overall_status"],
        "jobs": summary["jobs_expected"],
        "manifest_sha256": summary["manifest_sha256"],
        "summary_sha256": summary["summary_sha256"],
    }, indent=2))
    return 0 if summary["overall_status"] == "PASS" else 1


def self_check() -> Dict[str, Any]:
    base = dict(
        seed=6101,
        profile="near",
        phase_horizon=256,
        n_src=4,
        window=256,
        windows=3,
        heavy_work=512,
        subwindow=64,
    )
    scenarios = [
        ArrivalPhaseScenario.load_profile(phase=phase, **base) for phase in (0, 1, 2)
    ]
    horizons = {
        max(base["phase_horizon"], scenario.heavy_release_end_exclusive())
        for scenario in scenarios
    }
    if len(horizons) != 1:
        raise AssertionError("arrival phase rotation changed the generation horizon")
    horizon = next(iter(horizons))
    heavy = [scenario.declared_heavy_arrivals(horizon) for scenario in scenarios]
    sparse = [
        scenario.declared_sparse_work_multiset(horizon) for scenario in scenarios
    ]
    generated = [len(events) for events in sparse]
    if any(row != heavy[0] for row in heavy) or any(
        row != sparse[0] for row in sparse
    ):
        raise AssertionError("arrival phase rotation did not preserve inputs/work")
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
    if pair["status"] != "PASS" or not pair["input_pairing"]["valid"]:
        raise AssertionError("self-check paired run failed")
    return {
        "status": "PASS",
        "arrival_contract": ARRIVAL_COMMON_GENERATION_CONTRACT,
        "generation_end_exclusive": horizon,
        "phases": [0, 1, 2],
        "full_common_heavy_ready_match": pair["input_pairing"][
            "heavy_arrivals_match"
        ] and pair["input_pairing"]["ready_sequence_match"],
        "full_sparse_work_multiset_match": pair["input_pairing"][
            "sparse_work_multiset_match"
        ],
        "sparse_generated_by_phase": generated,
        "pair_status": pair["status"],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output")
    result.add_argument("--self-check", action="store_true")
    result.add_argument("--smoke", action="store_true", help="W256 subset; no inference")
    result.add_argument("--production-reviewed", action="store_true")
    result.add_argument("--seeds", type=int, nargs="+")
    result.add_argument(
        "--profiles", nargs="+", choices=tuple(LOAD_PROFILES),
        default=["under", "near", "over"],
    )
    result.add_argument("--phases", type=int, nargs="+", default=[0, 1, 2])
    result.add_argument("--policies", nargs="+", default=list(DEFAULT_POLICIES))
    result.add_argument("--n-src", type=int, default=4)
    result.add_argument("--depth", type=int, default=16)
    result.add_argument("--heavy-work", type=int)
    result.add_argument("--phase-horizon", type=int)
    result.add_argument("--completion-margin-cycles", type=float)
    result.add_argument("--throughput-margin-fraction", type=float)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.self_check:
            print(json.dumps(self_check(), indent=2))
            return 0
        if not args.output:
            raise ValueError("--output is required unless --self-check is used")
        if args.completion_margin_cycles is None or args.throughput_margin_fraction is None:
            raise ValueError("declared equivalence margins are required")
        if args.completion_margin_cycles < 0 or args.throughput_margin_fraction < 0:
            raise ValueError("declared equivalence margins must be nonnegative")
        return run_matrix(args)
    except (ValueError, FileExistsError) as exc:
        print(f"run_arrival_phase_diagnosis: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
