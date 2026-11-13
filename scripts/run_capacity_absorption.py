#!/usr/bin/env python3
"""Capacity-absorption pairs: mixed vs isolated heavy completion at under/over load."""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim/experimental"))
import run_rtl_diagnosis as diag
from cgof_diagnosis_model import run as model_run

POLICIES = (("FAI-inspired", None), ("CGOF(1:1)", 1), ("CGOF(2:1)", 2))
LANES = ("mixed", "isolated")
# Heavy work is scaled per profile so the burst completes inside the 24M active cap.
# under heavy_p is 0.25, so a 17.5M burst would need ~70M cycles and never complete.
HEAVY_AT_W5M = {"under": 4_000_000, "near": 17_500_000, "over": 17_500_000}


def matrix(window: int, seed: int, profile: str, heavy: int | None = None) -> list:
    cap = 24_000_000 if window == 5_000_000 else 8 * window
    if heavy is None:
        heavy = HEAVY_AT_W5M[profile] * window // 5_000_000
    jobs = []
    for policy, weight in POLICIES:
        for lane in LANES:
            job = diag.make_job("finite-heavy", lane, seed, window, weight, 4, heavy, profile,
                                cap, depth=16, heavy_sources=(0,), ready_pattern="bernoulli")
            if policy == "FAI-inspired":
                job["policy"] = policy
            jobs.append(dict(policy=policy, lane=lane, job=job))
    assert len(jobs) == 6
    return jobs


def one(payload) -> dict:
    entry, directory = payload
    profile = entry["job"].get("profile", "na")
    name = (f"seed{entry['job']['seed']}-{profile}-{entry['policy'].replace('(', '_').replace(':', '_').replace(')', '')}"
            f"-{entry['lane']}")
    path = directory / f"{name}.json"
    start = time.monotonic()
    result = model_run(entry["job"])
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    heavy = result.get("heavy") or {}
    return dict(name=name, policy=entry["policy"], lane=entry["lane"],
                status=result.get("status"), wall_s=time.monotonic() - start,
                completion_cycle=heavy.get("completion_cycle"),
                completed=heavy.get("completed"),
                fired=result.get("fired"), accepted=result.get("accepted"),
                generated=result.get("generated"),
                sparse_p99=sparse_p99(result))


def sparse_p99(result: dict):
    roles = result.get("generation_roles") or {}
    latency = roles.get("latency") or {}
    sparse = latency.get("sparse") or {}
    window = sparse.get("generation_to_fire") or {}
    return window.get("p99_nearest_rank")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", type=int, nargs="+", default=[8101, 8102, 8103, 8104, 8105])
    parser.add_argument("--profiles", nargs="+", default=["under", "over"],
                        choices=("under", "near", "over"))
    parser.add_argument("--window", type=int, default=5_000_000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--heavy-work", type=int, default=None,
                        help="override the per-profile heavy burst size")
    args = parser.parse_args(argv)
    if args.window not in (256, 5_000_000):
        parser.error("windows are 256 (smoke) or 5,000,000")
    if len(set(args.seeds)) != len(args.seeds) or len(set(args.profiles)) != len(args.profiles):
        parser.error("duplicate seeds or profiles are not allowed")
    if args.workers < 1 or (args.heavy_work is not None and args.heavy_work < 1):
        parser.error("workers and heavy-work must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in diag.source_paths()}
    hashes["scripts/run_capacity_absorption.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary, failed = [], []
    for profile in args.profiles:
        for seed in args.seeds:
            jobs = matrix(args.window, seed, profile, args.heavy_work)
            started = time.time()
            with futures.ProcessPoolExecutor(args.workers) as pool:
                rows = list(pool.map(one, [(entry, args.output) for entry in jobs]))
            bad = [row["name"] for row in rows if row["status"] != "PASS"]
            failed += bad
            by = {(row["policy"], row["lane"]): row for row in rows}
            for policy, _weight in POLICIES:
                m, i = by[(policy, "mixed")], by[(policy, "isolated")]
                if m["completion_cycle"] is None or i["completion_cycle"] is None:
                    gap = ratio = None
                else:
                    gap = m["completion_cycle"] - i["completion_cycle"]
                    ratio = m["completion_cycle"] / i["completion_cycle"]
                conserved = all(r["status"] == "PASS" and r["fired"] is not None
                                and r["generated"] is not None
                                and r["fired"] == r["accepted"] == sum(r["generated"])
                                for r in (m, i))
                if not conserved or not all(r["completed"] for r in (m, i)):
                    failed.append(f"seed{seed}-{profile}-{policy}: incomplete or conservation failed")
                summary.append(dict(profile=profile, seed=seed, policy=policy,
                                    mixed_completion=m["completion_cycle"],
                                    isolated_completion=i["completion_cycle"],
                                    gap_cycles=gap, ratio=ratio,
                                    mixed_sparse_p99=m["sparse_p99"],
                                    isolated_sparse_p99=i["sparse_p99"],
                                    conservation=conserved))
            print(json.dumps({"profile": profile, "seed": seed, "failed": bad,
                              "wall_s": round(time.time() - started, 1)}), flush=True)
    drift = [name for name, digest in hashes.items()
             if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    failed.extend(f"source changed: {name}" for name in drift)
    manifest = dict(schema="cxl-capacity-absorption-v2", seeds=args.seeds,
                    heavy_work={p: (args.heavy_work if args.heavy_work else
                                    HEAVY_AT_W5M[p] * args.window // 5_000_000)
                                for p in args.profiles},
                    heavy_scaling_note="per-profile heavy burst so the burst completes inside the 24M active cap; "
                                       "under load cannot finish 17.5M at heavy_p 0.25",
                    profiles=args.profiles, window=args.window, workers=args.workers,
                    jobs=len(summary) * 2, failed=failed, source_hashes=hashes,
                    pairs=summary)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"pairs": len(summary), "failed": len(failed)}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
