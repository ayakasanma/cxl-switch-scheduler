#!/usr/bin/env python3
"""Freeze and run the MODEL_ONLY FAI-inspired/CGOF diagnosis matrix.

W5M is never selected by the W256 smoke path.  Every job writes either result.json
or failure.json in its own directory, and inference is bootstrapped only over a
declared seed/run cohort.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import traceback
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refc.cxl_model.diagnosis import (  # noqa: E402
    CONFIRMATION_SEEDS,
    EXPLORATION_SEEDS,
    LOAD_PROFILES,
    MODEL_SCOPE,
    comparison_specs,
    config_identity,
    digest_json,
    endpoint_metrics,
    jsonable,
    paired_bootstrap,
    policy_configs,
    run_job,
)

SCHEMA = "cxl-model-diagnosis-run-v1"
MANIFEST_SCHEMA = "cxl-model-diagnosis-manifest-v1"
SUMMARY_SCHEMA = "cxl-model-diagnosis-summary-v1"
BOOTSTRAP_REPLICATES = 10_000
W256 = 256
W5M = 5_000_000
REQUIRED_SOURCE_PATHS = (
    "docs/MEASUREMENT_DIAGNOSIS_PLAN.md",
    "docs/experiments/diagnosis-20261027/LITERATURE.md",
    "docs/reviews/evidence-review-fixes-plan-20261101.md",
    "refc/cxl_model/__init__.py",
    "refc/cxl_model/common_ctrl_model.py",
    "refc/cxl_model/diagnosis.py",
    "refc/cxl_model/experimental.py",
    "refc/cxl_model/fai_alg2_model.py",
    "refc/cxl_model/fai_main_model.py",
    "refc/cxl_model/fcfs_model.py",
    "refc/cxl_model/fifo_model.py",
    "refc/cxl_model/rr_model.py",
    "refc/tests/test_diagnosis.py",
    "scripts/run_diagnosis.py",
    "scripts/test_run_diagnosis.py",
    "sim/common/traffic_trace.py",
    "sim/performance/followup.py",
    "sim/switch_top_fai/fai_stream.py",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_paths(root: Path = ROOT) -> List[str]:
    Path(root)
    return list(REQUIRED_SOURCE_PATHS)


def validate_source_paths(
    root: Path = ROOT,
    paths: Optional[Sequence[str]] = None,
) -> None:
    root = Path(root)
    required = tuple(source_paths(root) if paths is None else paths)
    if not required:
        raise ValueError("required source set must be nonempty")
    if len(required) != len(set(required)):
        raise ValueError("required source paths must be unique")
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        raise ValueError(
            "missing required source files: " + ", ".join(missing)
        )


def source_hashes(root: Path = ROOT) -> Dict[str, str]:
    root = Path(root)
    validate_source_paths(root)
    return {name: sha256_file(root / name) for name in source_paths(root)}


def declared_seeds(role: str) -> tuple:
    if role == "exploration":
        return EXPLORATION_SEEDS
    if role == "confirmation":
        return CONFIRMATION_SEEDS
    raise ValueError("role must be exploration or confirmation")


def select_seeds(role: str, seeds: Optional[Sequence[int]], smoke: bool) -> tuple:
    declared = declared_seeds(role)
    selected = tuple(sorted(declared if seeds is None else seeds))
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("seeds must be nonempty and unique")
    if not set(selected).issubset(declared):
        raise ValueError("seeds are outside the declared role cohort")
    if not smoke and selected != tuple(declared):
        raise ValueError("non-smoke runs require the complete declared seed cohort")
    return selected


def policies_by_identity(identities: Optional[Sequence[str]]) -> List[Dict[str, Any]]:
    configured = policy_configs()
    if not identities:
        return configured
    if len(identities) != len(set(identities)):
        raise ValueError("policy identities must be unique")
    index = {config_identity(row): row for row in configured}
    unknown = set(identities) - set(index)
    if unknown:
        raise ValueError(f"unknown policy identities: {sorted(unknown)}")
    wanted = set(identities)
    return [row for row in configured if config_identity(row) in wanted]


def profile_values(profiles: Sequence[str]) -> Dict[str, Dict[str, float]]:
    if not profiles or len(profiles) != len(set(profiles)):
        raise ValueError("profiles must be nonempty and unique")
    unknown = set(profiles) - set(LOAD_PROFILES)
    if unknown:
        raise ValueError(f"unknown load profiles: {sorted(unknown)}")
    return {name: dict(LOAD_PROFILES[name]) for name in sorted(profiles)}


def job_id(profile: str, config: Dict[str, Any], seed: int) -> str:
    value = f"{profile}__{config_identity(config)}__s{seed}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def build_jobs(
    seeds: Sequence[int],
    profiles: Sequence[str],
    policies: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    jobs = []
    for profile in profiles:
        for config in policies:
            for seed in seeds:
                jobs.append({
                    "id": job_id(profile, config, seed),
                    "profile": profile,
                    "seed": seed,
                    "config": jsonable(config),
                    "config_id": config_identity(config),
                })
    if len({job["id"] for job in jobs}) != len(jobs):
        raise ValueError("job identities are not unique")
    return jobs


def manifest_payload(
    output: Path,
    command: Sequence[str],
    role: str,
    smoke: bool,
    seeds: Sequence[int],
    settings: Dict[str, Any],
    profiles: Dict[str, Dict[str, float]],
    policies: Sequence[Dict[str, Any]],
    jobs: Sequence[Dict[str, Any]],
    *,
    source_root: Optional[Path] = None,
    source_hashes_value: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "scope": MODEL_SCOPE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": list(command),
        "output": str(output),
        "role": role,
        "smoke": smoke,
        "seeds": list(seeds),
        "settings": settings,
        "profiles": profiles,
        "policies": jsonable(list(policies)),
        "comparisons": jsonable(comparison_specs()),
        "jobs": jsonable(list(jobs)),
        "source_hashes": (
            source_hashes(ROOT if source_root is None else source_root)
            if source_hashes_value is None else source_hashes_value
        ),
        "bootstrap": {
            "unit": "paired seed/run",
            "replicates": BOOTSTRAP_REPLICATES,
            "enabled": not smoke and tuple(seeds) in (EXPLORATION_SEEDS, CONFIRMATION_SEEDS),
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def freeze_manifest(
    output: Path,
    command: Sequence[str],
    role: str,
    smoke: bool,
    seeds: Sequence[int],
    settings: Dict[str, Any],
    profiles: Dict[str, Dict[str, float]],
    policies: Sequence[Dict[str, Any]],
    jobs: Sequence[Dict[str, Any]],
    *,
    source_root: Optional[Path] = None,
) -> Dict[str, Any]:
    output = Path(output).resolve()
    root = ROOT if source_root is None else Path(source_root)
    frozen_source_hashes = source_hashes(root)
    output.mkdir(parents=True, exist_ok=False)
    manifest = manifest_payload(
        output, command, role, smoke, seeds, settings, profiles, policies, jobs,
        source_root=root,
        source_hashes_value=frozen_source_hashes,
    )
    manifest["manifest_sha256"] = digest_json(manifest)
    path = output / "manifest.json"
    write_json(path, manifest)
    validate_manifest(path)
    return manifest


def load_manifest(path: Path, *, check_sources: bool = True) -> Dict[str, Any]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be an object")
    claimed = data.pop("manifest_sha256", None)
    if not isinstance(claimed, str) or digest_json(data) != claimed:
        raise ValueError("manifest digest mismatch")
    if data.get("schema") != MANIFEST_SCHEMA or data.get("scope") != MODEL_SCOPE:
        raise ValueError("manifest schema/scope mismatch")
    if check_sources and data.get("source_hashes") != source_hashes():
        raise ValueError("source bytes differ from the frozen manifest")
    data["manifest_sha256"] = claimed
    return data


def validate_manifest(path: Path, *, check_sources: bool = True) -> Dict[str, Any]:
    return load_manifest(path, check_sources=check_sources)


def run_one_job(
    job: Dict[str, Any],
    settings: Dict[str, Any],
    directory: Path,
) -> Dict[str, Any]:
    try:
        result = run_job(
            job["config"],
            job["seed"],
            settings["role"],
            n_src=settings["n_src"],
            depth=settings["depth"],
            window=settings["window"],
            windows=settings["windows"],
            heavy_work=settings["heavy_work"],
            subwindow=settings["subwindow"],
            profile=job["profile"],
            max_active_cycles=settings.get("fairness_horizon"),
            fixed_horizon=settings.get("measurement_mode") == "fixed_horizon",
            initial_classes=settings.get("initial_classes"),
            heavy_sources=settings.get("heavy_sources"),
            ready_pattern=settings.get("ready_pattern", "bernoulli"),
            ready_period=settings.get("ready_period", 100),
        )
        endpoints = endpoint_metrics(result)
        if result["status"] != "PASS":
            payload = {
                "job": job,
                "status": result["status"],
                "endpoint_metrics": endpoints,
                "result": result,
            }
            write_json(directory / "failure.json", payload)
        else:
            write_json(directory / "result.json", {
                "job": job,
                "status": "PASS",
                "endpoint_metrics": endpoints,
                "result": result,
            })
        return {
            "id": job["id"],
            "profile": job["profile"],
            "seed": job["seed"],
            "config_id": job["config_id"],
            "status": result["status"],
            "endpoints": endpoints,
        }
    except Exception as exc:
        payload = {
            "job": job,
            "status": "FAIL",
            "failure": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
        write_json(directory / "failure.json", payload)
        return {
            "id": job["id"],
            "profile": job["profile"],
            "seed": job["seed"],
            "config_id": job["config_id"],
            "status": "FAIL",
            "endpoints": None,
        }


def comparison_summary(
    records: Sequence[Dict[str, Any]],
    seeds: Sequence[int],
    profiles: Sequence[str],
    *,
    smoke: bool,
) -> List[Dict[str, Any]]:
    index = {
        (row["config_id"], row["profile"], row["seed"]): row
        for row in records if row["status"] == "PASS" and row["endpoints"] is not None
    }
    full_cohort = tuple(sorted(seeds)) in (EXPLORATION_SEEDS, CONFIRMATION_SEEDS)
    results = []
    for spec in comparison_specs():
        for profile in profiles:
            result = {
                "id": spec["id"],
                "candidate": spec["candidate"],
                "baseline": spec["baseline"],
                "profile": profile,
                "metrics": {},
            }
            missing = [
                f"{config_id}:{profile}:s{seed}"
                for config_id in (spec["candidate"], spec["baseline"])
                for seed in seeds
                if (config_id, profile, seed) not in index
            ]
            if smoke or not full_cohort:
                result.update(
                    status="NOT_RUN",
                    reason="bootstrap requires a complete non-smoke declared seed cohort",
                    missing=missing,
                )
                results.append(result)
                continue
            if missing:
                result.update(
                    status="PARTIAL",
                    reason="one or more paired jobs did not complete",
                    missing=missing,
                )
                results.append(result)
                continue
            for metric in spec["metrics"]:
                candidate = [
                    index[(spec["candidate"], profile, seed)]["endpoints"].get(metric)
                    for seed in seeds
                ]
                baseline = [
                    index[(spec["baseline"], profile, seed)]["endpoints"].get(metric)
                    for seed in seeds
                ]
                if any(
                    value is None or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    for value in candidate + baseline
                ):
                    result["metrics"][metric] = {
                        "status": "UNAVAILABLE",
                        "reason": "metric is null or nonfinite for at least one paired run",
                    }
                    continue
                estimate = paired_bootstrap(
                    candidate,
                    baseline,
                    seeds,
                    replicates=BOOTSTRAP_REPLICATES,
                )
                result["metrics"][metric] = {"status": "COMPLETE", **estimate}
            result["status"] = (
                "COMPLETE"
                if all(row["status"] == "COMPLETE" for row in result["metrics"].values())
                else "PARTIAL"
            )
            results.append(result)
    return results


def write_summary(
    output: Path,
    manifest: Dict[str, Any],
    records: Sequence[Dict[str, Any]],
    after_hashes: Dict[str, str],
) -> Dict[str, Any]:
    failures = [row for row in records if row["status"] != "PASS"]
    source_stable = manifest["source_hashes"] == after_hashes
    summary = {
        "schema": SUMMARY_SCHEMA,
        "scope": MODEL_SCOPE,
        "production_evidence": False,
        "smoke": manifest["smoke"],
        "overall_status": "PASS" if not failures and source_stable else "FAIL",
        "manifest_sha256": manifest["manifest_sha256"],
        "settings": manifest["settings"],
        "profiles": manifest["profiles"],
        "seeds": manifest["seeds"],
        "jobs_expected": len(manifest["jobs"]),
        "jobs_completed": len(records) - len(failures),
        "failures": failures,
        "runs": list(records),
        "comparisons": comparison_summary(
            records,
            manifest["seeds"],
            tuple(manifest["profiles"]),
            smoke=manifest["smoke"],
        ),
        "source_stable": source_stable,
        "source_hashes_after": after_hashes,
        "notes": [
            "MODEL_ONLY; scheduler fire is not measured memory bandwidth",
            "generation-to-fire is not memory-response latency",
            "paired bootstrap resamples seeds/runs, never requests or sources",
        ],
    }
    summary["summary_sha256"] = digest_json(summary)
    write_json(output / "summary.json", summary)
    return summary


def execute(
    args: argparse.Namespace,
    command: Optional[Sequence[str]] = None,
) -> int:
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    seeds = select_seeds(args.role, args.seeds, args.smoke)
    profiles = tuple(sorted(args.profiles))
    policies = policies_by_identity(args.policies)
    jobs = build_jobs(seeds, profiles, policies)
    settings = {
        "role": args.role,
        "n_src": args.n_src,
        "depth": args.depth,
        "window": args.window,
        "windows": args.windows,
        "heavy_work": args.heavy_work if args.heavy_work is not None else args.windows * args.window,
        "subwindow": args.subwindow if args.subwindow is not None else max(1, args.window // 4),
        "heavy_source": 0,
        "sparse_stop": "finite Heavy completion",
        "drain": "forced-ready, cleanup only",
        "measurement_mode": "fixed_horizon" if args.fairness_horizon else "finite_heavy",
        "fairness_horizon": args.fairness_horizon,
        "initial_classes": args.initial_classes,
        "heavy_sources": args.heavy_sources,
        "ready_pattern": args.ready_pattern,
        "ready_period": args.ready_period,
    }
    if args.fairness_horizon is not None:
        if args.fairness_horizon < 1:
            raise ValueError("fairness horizon must be positive")
        if tuple(profiles) != ("equal",):
            raise ValueError("fairness horizon requires --profiles equal")
        if settings["heavy_work"] <= args.fairness_horizon:
            raise ValueError("heavy work must exceed the fairness horizon")
    if args.initial_classes is not None:
        if tuple(profiles) != ("equal",) or args.fairness_horizon is None:
            raise ValueError("initial classes require an equal-demand fairness run")
        if len(args.initial_classes) != args.n_src:
            raise ValueError("initial classes must contain one value per source")
        if any(config["family"] not in ("FAI-inspired", "CGOF") for config in policies):
            raise ValueError("initial classes require class-aware policies only")
    manifest = freeze_manifest(
        output,
        sys.argv if command is None else command,
        args.role,
        args.smoke,
        seeds,
        settings,
        profile_values(profiles),
        policies,
        jobs,
    )
    records = []
    for index, job in enumerate(manifest["jobs"]):
        directory = output / "jobs" / f"{index:04d}-{job['id']}"
        directory.mkdir(parents=True)
        records.append(run_one_job(dict(job), settings, directory))
    validate_manifest(output / "manifest.json", check_sources=False)
    after_hashes = source_hashes()
    write_json(output / "source_hashes_before.json", manifest["source_hashes"])
    write_json(output / "source_hashes_after.json", after_hashes)
    summary = write_summary(output, manifest, records, after_hashes)
    print(json.dumps({
        "output": str(output),
        "overall_status": summary["overall_status"],
        "jobs": summary["jobs_expected"],
        "manifest_sha256": summary["manifest_sha256"],
        "summary_sha256": summary["summary_sha256"],
    }, indent=2))
    return 0 if summary["overall_status"] == "PASS" else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", help="new output directory for a frozen run")
    result.add_argument("--verify-manifest", help="validate an existing manifest digest/source binding")
    result.add_argument("--role", choices=("exploration", "confirmation"), default="exploration")
    result.add_argument("--smoke", action="store_true", help="W256 subset; never inference evidence")
    result.add_argument("--window", type=int, choices=(W256, W5M))
    result.add_argument("--production-reviewed", action="store_true")
    result.add_argument("--seeds", type=int, nargs="+")
    result.add_argument(
        "--profiles", nargs="+", choices=tuple(LOAD_PROFILES),
        default=["under", "near", "over"],
    )
    result.add_argument("--policies", nargs="+", default=None)
    result.add_argument("--n-src", type=int, default=4)
    result.add_argument("--depth", type=int, default=16)
    result.add_argument("--heavy-sources", type=int, nargs="+")
    result.add_argument("--ready-pattern", choices=("bernoulli", "spread", "bursty"),
                        default="bernoulli")
    result.add_argument("--ready-period", type=int, default=100)
    result.add_argument("--windows", type=int, default=3)
    result.add_argument("--heavy-work", type=int)
    result.add_argument("--subwindow", type=int)
    result.add_argument(
        "--fairness-horizon", type=int,
        help="fixed active-cycle horizon for equal-demand fairness (requires --profiles equal)",
    )
    result.add_argument(
        "--initial-classes", nargs="+", choices=("L", "H"),
        help="model-only fixed class map for quota validation",
    )
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    try:
        if args.verify_manifest:
            if args.output:
                p.error("--verify-manifest and --output are mutually exclusive")
            manifest = validate_manifest(Path(args.verify_manifest))
            print(json.dumps({
                "status": "PASS",
                "manifest_sha256": manifest["manifest_sha256"],
            }, indent=2))
            return 0
        if not args.output:
            p.error("--output is required unless --verify-manifest is used")
        if args.window is None:
            p.error("--window must be explicitly set")
        if args.window == W5M and not args.production_reviewed:
            p.error("W5M requires --production-reviewed")
        if args.smoke:
            if args.window != W256:
                p.error("--smoke is restricted to W256")
            if (args.heavy_work is None or args.windows < 1
                    or not 0 < args.heavy_work <= args.windows * W256):
                p.error("--smoke requires explicit heavy-work <= windows * 256")
            if args.production_reviewed:
                p.error("--production-reviewed is invalid with --smoke")
        elif args.window == W256:
            p.error("W256 is restricted to explicit --smoke runs")
        command = [sys.argv[0], *(argv if argv is not None else sys.argv[1:])]
        return execute(args, command)
    except (ValueError, FileExistsError) as exc:
        p.exit(2, f"run_diagnosis: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
