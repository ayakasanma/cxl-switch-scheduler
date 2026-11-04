"""Generate v2-only PGFPlots data from the accepted HOG-SPARSE evidence.

Run with Python 3 from any directory. Existing manuscript/data files are read-only.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "docs/performance"
SEEDS = set(range(509, 514))
POLICIES = {"FCFS": "FCFS", "RR": "RR", "FAI_MAIN": "Main"}


def read_csv(name):
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def render():
    audit = json.loads((DATA / "hog-sparse-audit.json").read_text(encoding="utf-8"))
    assert audit["status"] == "PASS" and audit["actual_runs"] == 15
    assert audit["matched_trace_groups"] == 5 and not audit["pilot"]
    assert audit["real_non_reset_cycles"] == 156657531
    assert len(audit["inputs"]) == 15
    for item in audit["inputs"]:
        path = (ROOT / item["path"]).resolve()
        assert path.is_relative_to(ROOT.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["production_evidence"] and not raw["sensitivity_evidence"]
        assert raw["n_src"] == 4 and raw["window"] == 5000000
        assert raw["training_cycles"] == raw["cold_pin_cycles"] == 10000000
        assert raw["sparse_guard_complete"]
        assert raw["outstanding_after_drain"] == 0
        assert raw["generated_unaccepted_after_drain"] == 0

    runs = read_csv("hog-sparse-runs.csv")
    assert len(runs) == 15
    assert {(r["policy"], int(r["seed"])) for r in runs} == {
        (p, s) for p in POLICIES for s in SEEDS
    }
    assert sum(int(r["real_non_reset_cycles"]) for r in runs) == audit["real_non_reset_cycles"]
    for seed in SEEDS:
        paired = {r["policy"]: r for r in runs if int(r["seed"]) == seed}
        assert len({r["trace_sha256"] for r in paired.values()}) == 1
        assert paired["FCFS"]["cold_pin_sha256"] == paired["FAI_MAIN"]["cold_pin_sha256"]

    records = read_csv("hog-sparse-profiles.csv")
    assert len(records) == 45
    by_key = {(r["policy"], r["profile"], int(r["seed"])): r for r in records}
    assert len(by_key) == 45
    assert set(by_key) == {(p, f, s) for p in POLICIES for f in ("cold", "A", "B") for s in SEEDS}
    for row in records:
        assert row["sparse_generated"] == row["sparse_completed"]
        assert row["generation_to_fire_count"] == row["sparse_generated"]
        direct = float(row["generation_to_fire_mean"])
        stages = float(row["generation_to_acceptance_mean"]) + float(row["acceptance_to_fire_mean"])
        assert math.isclose(direct, stages, abs_tol=1e-10)
        if row["profile"] != "cold":
            assert float(row["fires_per_cycle"]) == 1.0

    summaries = json.loads((DATA / "hog-sparse-summary.json").read_text(encoding="utf-8"))
    assert summaries["status"] == "ACCEPTED_DESCRIPTIVE_RESULTS"
    for item in summaries["summary"]:
        rows = [by_key[item["policy"], item["profile"], s] for s in sorted(SEEDS)]
        for metric in ("generation_to_fire_mean", "generation_to_fire_p99_nearest_rank"):
            assert math.isclose(mean(float(r[metric]) for r in rows), item[metric]["mean"], abs_tol=1e-10)

    pairs = read_csv("hog-sparse-paired.csv")
    assert len(pairs) == 20
    assert {(r["profile"], r["baseline"], int(r["seed"])) for r in pairs} == {
        (f, p, s) for f in ("A", "B") for p in ("FCFS", "RR") for s in SEEDS
    }
    for row in pairs:
        key = row["profile"], int(row["seed"])
        base = float(by_key[row["baseline"], *key]["generation_to_fire_p99_nearest_rank"])
        main = float(by_key["FAI_MAIN", *key]["generation_to_fire_p99_nearest_rank"])
        assert float(row["baseline_p99"]) == base and float(row["main_p99"]) == main
        assert float(row["reduction_cycles"]) == base - main
        assert math.isclose(float(row["reduction_percent"]), 100 * (base - main) / base, abs_tol=1e-10)

    lines = ["% Deterministic output of generate_hog_sparse_results.py; accepted five-seed RTL data."]

    def macro(name, content):
        lines.append("\\newcommand{\\" + name + "}{" + content + "}")

    def table(name, rows):
        # Asymmetric bars show the observed seed range, never a confidence interval.
        body = "x y lo hi\\\\\n" + "".join(
            f"{x} {y:.10f} {lo:.10f} {hi:.10f}\\\\\n" for x, y, lo, hi in rows
        )
        lines.append("\\pgfplotstableread[row sep=\\\\]{\n" + body + "}\\" + name)

    for policy, label in POLICIES.items():
        for metric, prefix in (("generation_to_fire_mean", "HSMean"),
                               ("generation_to_fire_p99_nearest_rank", "HSPtail"),
                               ("heavy_fires_per_cycle", "HSHeavy")):
            points = []
            for x, profile in enumerate(("A", "B"), 1):
                values = [float(by_key[policy, profile, s][metric]) for s in sorted(SEEDS)]
                avg = mean(values)
                points.append((x, avg, avg - min(values), max(values) - avg))
            table(prefix + label, points)

    paired_points = []
    seed_points = []
    for x, (profile, baseline) in enumerate((("A", "FCFS"), ("A", "RR"), ("B", "FCFS"), ("B", "RR")), 1):
        rows = sorted((r for r in pairs if r["profile"] == profile and r["baseline"] == baseline),
                      key=lambda r: int(r["seed"]))
        values = [float(r["reduction_percent"]) for r in rows]
        avg = mean(values)
        paired_points.append((x, avg, avg - min(values), max(values) - avg))
        for offset, value in zip((-.12, -.06, 0, .06, .12), values):
            seed_points.append(f"({x + offset:.2f},{value:.10f})")
        suffix = profile + ("FCFS" if baseline == "FCFS" else "RR")
        macro("HSReduction" + suffix, f"{avg:.2f}")
    table("HSPaired", paired_points)
    macro("HSPairedSeeds", " ".join(seed_points))

    for profile in ("A", "B"):
        for policy, label in POLICIES.items():
            rows = [by_key[policy, profile, s] for s in sorted(SEEDS)]
            macro("HSMean" + profile + label, f"{mean(float(r['generation_to_fire_mean']) for r in rows):.4f}")
            macro("HSPtail" + profile + label, f"{mean(float(r['generation_to_fire_p99_nearest_rank']) for r in rows):.1f}")
    for filename in ("hog-sparse-audit.json", "hog-sparse-profiles.csv", "hog-sparse-paired.csv", "hog-sparse-runs.csv"):
        digest = hashlib.sha256((DATA / filename).read_bytes()).hexdigest()
        lines.append(f"% Source SHA-256 {filename}: {digest}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    output = render()
    target = HERE / "generated/hog_sparse_results.tex"
    target.write_text(output, encoding="ascii", newline="\n")
    assert target.read_text(encoding="ascii") == render(), "Nondeterministic output"
    print("PASS: 15 raw digests, matched traces, complete cohorts, 30 capacity intervals; deterministic v2 data.")
