#!/usr/bin/env python3
"""Run the v2 engineering pilot: 30 model jobs for one seed, frozen matrix."""
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
from run_dynamic_role_switch_a2 import CASES


def matrix(window: int, seed: int, profile: str = "near") -> list:
    jobs = []
    for case, depth, sources, ready in CASES:
        for policy in ("FAI-inspired", "CGOF(1:1)", "CGOF(2:1)"):
            weight = None if policy == "FAI-inspired" else (1 if policy == "CGOF(1:1)" else 2)
            for lane in ("mixed", "isolated"):
                cap = 24_000_000 if window == 5_000_000 else 8*window
                job = diag.make_job("finite-heavy", lane, seed, window, weight, 4,
                                    7*window//2, profile, cap, depth=depth,
                                    heavy_sources=sources, ready_pattern=ready)
                if policy == "FAI-inspired":
                    job["policy"] = policy
                jobs.append(dict(case=case, policy=policy, lane=lane, job=job))
    assert len(jobs) == 30
    return jobs


def one(payload) -> dict:
    entry, directory = payload
    name = f"{entry['case']}-{entry['lane']}-{entry['policy'].replace('(', '_').replace(':', '_').replace(')', '')}"
    path = directory / f"{name}.json"
    start = time.monotonic()
    result = model_run(entry["job"])
    with path.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    return dict(name=name, path=path, status=result.get("status"), wall_s=time.monotonic()-start,
                result=result, case=entry["case"], policy=entry["policy"], lane=entry["lane"])


def run_seed(seed: int, window: int, profile: str, workers: int, directory: Path) -> dict:
    jobs = matrix(window, seed, profile)
    started = time.time()
    # Separate processes: the reference model is pure Python, so threads would serialise on the GIL.
    with futures.ProcessPoolExecutor(workers) as pool:
        rows = list(pool.map(one, [(entry, directory) for entry in jobs]))
    elapsed = time.time() - started
    bad = [row["name"] for row in rows if row["status"] != "PASS"]
    drains = sorted({r["result"].get("drain_cycles") for r in rows if r["result"].get("drain_cycles")})
    manifest = dict(schema="cxl-dynamic-role-switch-pilot-v1", seed=seed, window=window,
                    profile=profile, workers=workers, jobs=len(rows), failed=bad,
                    wall_s=elapsed, job_wall_sum_s=sum(r["wall_s"] for r in rows),
                    job_wall_max_s=max(r["wall_s"] for r in rows),
                    peak_rss="NOT_MEASURED",
                    drain_cycles_observed=drains,
                    confirmation_seeds=seed >= 7401,
                    results=[dict(name=r["name"], path=r["path"].name, case=r["case"],
                                  policy=r["policy"], lane=r["lane"], wall_s=r["wall_s"],
                                  active_cycles=r["result"].get("active_cycles"),
                                  drain_cycles=r["result"].get("drain_cycles"),
                                  trace_sha256=r["result"].get("trace_sha256")) for r in rows])
    with (directory/"manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(json.dumps(dict(seed=seed, jobs=len(rows), failed=bad, wall_s=round(elapsed, 1))))
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7301])
    parser.add_argument("--profile", choices=("under", "near", "over"), default="near")
    parser.add_argument("--window", type=int, default=5_000_000)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    if args.window not in (256, 5_000_000):
        parser.error("pilot windows are 256 (dry run) or 5,000,000")
    forbidden = {7291, 9901}
    if set(args.seeds) & forbidden:
        parser.error(f"seed {sorted(set(args.seeds) & forbidden)} is excluded from every run")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("duplicate seed in the requested cohort")
    if args.window != 5_000_000 and any(seed >= 7401 for seed in args.seeds):
        parser.error("held-out seeds may only run at the production window")
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
              for name in diag.source_paths()}
    failed = []
    for seed in args.seeds:
        directory = args.output if len(args.seeds) == 1 else args.output/f"seed{seed}"
        directory.mkdir(parents=True, exist_ok=True)
        manifest = run_seed(seed, args.window, args.profile, args.workers, directory)
        manifest["source_hashes"] = hashes
        failed += manifest["failed"]
    (args.output/"cohort.json").write_text(json.dumps(
        dict(seeds=args.seeds, profile=args.profile, window=args.window, source_hashes=hashes,
             failed=failed), indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
