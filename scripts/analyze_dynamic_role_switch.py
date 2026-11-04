#!/usr/bin/env python3
"""Frozen v2 statistics and seed audit for the multi-window diagnosis jobs.

One primary endpoint: the mixed-lane, generation-time Sparse whole-run
generation-to-fire nearest-rank P99. Three contrasts, exact one-sided sign
test, Holm step-down at FWER .05, and a descriptive paired bootstrap. Model
outputs stay MODEL_ONLY; this tool never relabels them as RTL evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import statistics
import sys

EXPECTED_SEEDS = tuple(range(7401, 7421))
PILOT_SEED = 7301
EXCLUDED_SEEDS = (7291, PILOT_SEED, 9901)
WINDOW = 5_000_000
CASES = {
    "multi-window": dict(depth=16, heavy_sources=(0,), ready_pattern="bernoulli"),
    "role-switch": dict(depth=16, heavy_sources=(0, 0, 1, 1), ready_pattern="bernoulli"),
    "ready-spread": dict(depth=16, heavy_sources=(0,), ready_pattern="spread"),
    "ready-bursty": dict(depth=16, heavy_sources=(0,), ready_pattern="bursty"),
    "depth8-bursty": dict(depth=8, heavy_sources=(0,), ready_pattern="bursty"),
}
CONTRASTS = (
    ("P1", "role-switch", "FAI-inspired", "CGOF(2:1)"),
    ("P2", "role-switch", "CGOF(2:1)", "CGOF(1:1)"),
    ("P3", "multi-window", "FAI-inspired", "CGOF(2:1)"),
)
ALPHA = 0.05
MARGIN = 1
BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261103


def case_of(job: dict) -> str:
    key = (job["depth"], tuple(job.get("heavy_sources") or ()), job.get("ready_pattern"))
    matches = [name for name, spec in CASES.items()
               if (spec["depth"], spec["heavy_sources"], spec["ready_pattern"]) == key]
    if len(matches) != 1:
        raise ValueError(f"job does not match exactly one frozen case: {key}")
    return matches[0]


def endpoint(result: dict) -> int:
    if result.get("status") != "PASS":
        raise ValueError("only passing jobs enter the endpoint")
    if result.get("evidence_kind") != "MODEL_ONLY":
        raise ValueError("the v2 primary endpoint is model-derived, not RTL")
    job, lane = result["job"], result["lane"]
    if lane != "mixed" or job["window"] != WINDOW or job.get("windows") != 4:
        raise ValueError("primary endpoint requires mixed W5M four-window jobs")
    sparse = result["generation_roles"]["latency"]["sparse"]["generation_to_fire"]
    value = sparse.get("p99_nearest_rank")
    if type(value) is not int or value <= 0 or sparse.get("count", 0) <= 0:
        raise ValueError("missing nearest-rank Sparse generation-to-fire P99")
    return value


def index(paths) -> dict:
    rows = {}
    for path in paths:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        seed, case, policy = result["job"]["seed"], case_of(result["job"]), result["policy"]
        key = (seed, case, policy)
        if key in rows:
            raise ValueError(f"duplicate run for {key}")
        rows[key] = dict(endpoint=endpoint(result), path=str(path), lane=result["lane"])
    return rows


def audit(rows: dict, seeds=EXPECTED_SEEDS) -> dict:
    seeds = tuple(seeds)
    if len(set(seeds)) != len(seeds):
        raise ValueError("duplicate seed in the requested cohort")
    used = {seed for seed, _case, _policy in rows}
    overlap = used & set(EXCLUDED_SEEDS)
    if overlap:
        raise ValueError(f"excluded seed used: {sorted(overlap)}")
    if used != set(seeds):
        raise ValueError(f"seed cohort mismatch: missing {sorted(set(seeds)-used)}, "
                         f"extra {sorted(used-set(seeds))}")
    for seed in seeds:
        for case in ("role-switch", "multi-window"):
            for policy in ("FAI-inspired", "CGOF(1:1)", "CGOF(2:1)"):
                if (seed, case, policy) not in rows:
                    raise ValueError(f"missing {case} {policy} for seed {seed}")
    return dict(seeds=list(seeds), n=len(seeds), excluded_not_used=sorted(EXCLUDED_SEEDS),
                jobs=len(rows), audit="PASS")


def sign_p_value(successes: int, n: int) -> float:
    """Exact one-sided binomial P(X >= K) with p = 1/2."""
    if not 0 <= successes <= n:
        raise ValueError("successes outside 0..n")
    tail = sum(math.comb(n, k) for k in range(successes, n+1))
    return tail / (1 << n)


def contrast(rows: dict, seeds, case: str, left: str, right: str) -> dict:
    deltas = [rows[(seed, case, left)]["endpoint"] - rows[(seed, case, right)]["endpoint"]
              for seed in seeds]
    k = sum(d >= MARGIN for d in deltas)
    return dict(case=case, left=left, right=right, n=len(deltas), deltas=deltas,
                successes=k, exact_p=sign_p_value(k, len(deltas)),
                mean_delta=statistics.mean(deltas))


def holm(contrasts: list) -> list:
    order = sorted(range(len(contrasts)), key=lambda i: contrasts[i]["exact_p"])
    remaining = len(contrasts)
    rejected = True
    for index in order:
        row = contrasts[index]
        threshold = ALPHA / remaining
        row["holm_threshold"] = threshold
        row["holm_rejected"] = bool(rejected and row["exact_p"] <= threshold)
        rejected = row["holm_rejected"]
        remaining -= 1
    return contrasts


def bootstrap(deltas: list) -> dict:
    rng = random.Random(BOOTSTRAP_SEED)
    means = []
    for _ in range(BOOTSTRAP):
        means.append(statistics.mean(rng.choice(deltas) for _ in deltas))
    means.sort()
    def pick(q):
        return means[min(len(means)-1, max(0, math.ceil(q*len(means))-1))]
    return dict(unit="paired seed block", resamples=BOOTSTRAP, rng_seed=BOOTSTRAP_SEED,
                mean=statistics.mean(deltas), low=pick(.025), high=pick(.975),
                descriptive_only=True)


def analyze(rows: dict, seeds=EXPECTED_SEEDS) -> dict:
    seeds = tuple(seeds)
    report = audit(rows, seeds)
    contrasts = holm([contrast(rows, seeds, case, left, right)
                      for _id, case, left, right in CONTRASTS])
    for (ident, *_rest), row in zip(CONTRASTS, contrasts):
        row["id"] = ident
        row["bootstrap"] = bootstrap(row["deltas"])
        row["verdict"] = ("SUPPORTED_WITHIN_PROTOCOL"
                          if row["holm_rejected"] and row["mean_delta"] >= MARGIN
                          else "NOT_CONFIRMED")
    return dict(schema="cxl-dynamic-role-switch-analysis-v1", status="COMPLETE",
                endpoint="mixed generation-time Sparse whole-run G->F nearest-rank P99",
                margin_cycles=MARGIN, alpha=ALPHA, multiplicity="Holm step-down",
                seed_audit=report, contrasts=contrasts,
                note="MODEL_ONLY statistics with RTL anchors; a supported contrast is not a universal winner")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", nargs="+", required=True, type=Path)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(EXPECTED_SEEDS))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = analyze(index(args.results), tuple(args.seeds))
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps({row["id"]: [row["successes"], row["n"], row["verdict"]]
                      for row in report["contrasts"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
