#!/usr/bin/env python3
"""Paired-run analysis; exploration summaries never masquerade as confirmation intervals."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

from revision_matrix import CONFIRMATION, EXPLORATION


def histogram_summary(histogram):
    hist = {int(k): v for k, v in histogram.items()}
    if not hist or any(k < 0 or type(v) is not int or v <= 0 for k, v in hist.items()):
        raise ValueError("histogram must have nonnegative cycles and positive integer counts")
    count = sum(hist.values())
    result = dict(count=count, mean=sum(k * v for k, v in hist.items()) / count, max=max(hist))
    for name, numerator, denominator in (
        ("p50", 1, 2), ("p90", 9, 10), ("p99", 99, 100), ("p999", 999, 1000)
    ):
        rank, seen = (numerator * count + denominator - 1) // denominator, 0
        for value, frequency in sorted(hist.items()):
            seen += frequency
            if seen >= rank:
                result[name] = value
                break
    return result


def paired_runs(baseline, candidate, confirmation=False):
    """HOG rows are one metric per seed, with independent reset-start cold profiles."""
    def index(rows):
        if any(type(r["seed"]) is not int for r in rows):
            raise ValueError("seed must be an integer")
        result = {r["seed"]: r for r in rows}
        if len(result) != len(rows):
            raise ValueError("duplicate seed/run: no request or source pseudoreplication")
        signatures = set()
        for row in rows:
            config = row.get("configuration")
            if (row.get("status") != "PASS" or not isinstance(config, dict)
                    or not row.get("policy") or not row.get("profile")
                    or not {"n_src", "window", "training_cycles"} <= config.keys()):
                raise ValueError("passed run, policy and exact configuration required")
            if row["profile"] not in ("trained-A", "trained-B", "cold-A", "cold-B"):
                raise ValueError("unknown HOG profile")
            training = 0 if row["profile"].startswith("cold-") else 10_000_000
            if (config["window"] != 5_000_000 or config["training_cycles"] != training
                    or row.get("production_evidence") is not True):
                raise ValueError("paired HOG analysis requires actual W5M production training")
            stats = histogram_summary(row["histogram"])
            if stats["p99"] != row["p99"] or stats["count"] != row["count"]:
                raise ValueError("P99/count disagrees with direct histogram")
            signatures.add((row["policy"], row["profile"],
                            json.dumps(config, sort_keys=True)))
        if len(signatures) != 1:
            raise ValueError("heterogeneous policy/profile/configuration within seed cohort")
        return result

    a, b = index(baseline), index(candidate)
    required = set(CONFIRMATION if confirmation else EXPLORATION)
    if set(a) != required or set(b) != required:
        raise ValueError("incomplete or mismatched prespecified seed cohort")
    deltas, reductions = [], []
    for seed in sorted(required):
        left, right = a[seed], b[seed]
        if not left.get("trace_sha256") or left["trace_sha256"] != right.get("trace_sha256"):
            raise ValueError("unpaired intended trace")
        if left.get("profile") != right.get("profile") or not left.get("profile"):
            raise ValueError("cold/trained or A/B profile mismatch")
        for field in ("n_src", "window", "training_cycles"):
            if left["configuration"][field] != right["configuration"][field]:
                raise ValueError("unpaired experimental boundary")
        x, y = left["p99"], right["p99"]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (x, y)):
            raise ValueError("P99 must be a positive finite cycle count")
        deltas.append(y - x)
        reductions.append(100 * (1 - y / x))
    result = dict(unit="paired seed/run", seeds=sorted(required), n=len(deltas),
                  delta_convention="candidate minus baseline; negative is lower waiting",
                  mean_p99_delta_cycles=statistics.mean(deltas),
                  mean_baseline_p99_cycles=statistics.mean(a[s]["p99"] for s in sorted(required)),
                  mean_candidate_p99_cycles=statistics.mean(b[s]["p99"] for s in sorted(required)),
                  mean_paired_p99_reduction_percent=statistics.mean(reductions),
                  paired_deltas_cycles=deltas, improved_seeds=sum(d < 0 for d in deltas),
                  confirmation=confirmation, inference="prespecified synthetic generator only")
    if confirmation:
        rng = random.Random(20261023)
        n = len(deltas)
        samples = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(10_000))
        result["paired_bootstrap"] = dict(replicates=10_000, rng_seed=20261023,
                                         percentile95=[samples[249], samples[9749]])
    else:
        result["interval_status"] = "NOT_COMPUTED_EXPLORATION_ONLY"
    return result


def legacy_hog(directory):
    """Recompute archived metrics only; this function runs zero RTL simulation cycles."""
    directory = Path(directory)
    inputs, rows = {}, {}
    for path in sorted((directory / "results").glob("*__hog_sparse_metrics.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if (data["window"] != 5_000_000 or data["training_cycles"] != 10_000_000
                or not data["production_evidence"] or data["n_src"] != 4):
            raise ValueError("legacy HOG source is not the expected production scope")
        key = data["policy"], data["seed"]
        if key in rows:
            raise ValueError("duplicate legacy run")
        inputs[path.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows[key] = data
    if set(rows) != {(p, s) for p in ("FCFS", "RR", "FAI_MAIN") for s in EXPLORATION}:
        raise ValueError("expected exactly fifteen archived policy/seed runs")
    endpoints, comparisons = [], {}
    for cohort in ("A", "B"):
        by_policy = {p: [] for p in ("FCFS", "RR", "FAI_MAIN")}
        for (policy, seed), data in rows.items():
            stage = data["metrics"]["cohorts"][cohort]["pooled_sparse"]["generation_to_fire"]
            stats = histogram_summary(stage["histogram"])
            if (stats["count"] != stage["count"] or stats["p99"] != stage["p99_nearest_rank"]
                    or stats["max"] != stage["max"] or min(map(int, stage["histogram"])) != stage["min"]
                    or not math.isclose(stats["mean"], stage["mean"], rel_tol=1e-12, abs_tol=1e-12)):
                raise ValueError("archive histogram disagrees with reported rank/count/extrema/mean")
            phase = data["metrics"]["phases"][cohort]
            fires = phase["fired"]
            row = dict(policy=policy, seed=seed, profile="trained-" + cohort,
                       trace_sha256=data["trace_sha256"], **stats,
                       status="PASS", production_evidence=True, histogram=stage["histogram"],
                       configuration=dict(n_src=data["n_src"], window=data["window"],
                                          training_cycles=data["training_cycles"], depth=16,
                                          rr_quantum=10, high_quota=10, low_quota=10),
                       heavy_service_fraction=fires[0] / sum(fires))
            by_policy[policy].append(row)
            endpoints.append(row)
        comparisons[cohort] = {
            p: paired_runs(by_policy[p], by_policy["FAI_MAIN"]) for p in ("FCFS", "RR")
        }
    return dict(schema="cxl-revision-statistics-v1", status="ARCHIVED_ARITHMETIC_RECOMPUTED",
                material_passport=dict(origin=str(directory), verification_status="RECOMPUTED_METRICS",
                                       evidence_kind="ARCHIVE_ANALYSIS_ZERO_NEW_RTL_CYCLES"),
                inputs_sha256=inputs, endpoints=endpoints, comparisons=comparisons,
                p999_and_max="descriptive only", scope="five exploration seeds; no confirmatory interval")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-hog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output JSON; refuses overwrite")
    args = parser.parse_args()
    data = legacy_hog(args.legacy_hog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(json.dumps(data["comparisons"], indent=2))


if __name__ == "__main__":
    main()
