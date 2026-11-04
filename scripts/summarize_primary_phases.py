"""Audit an instrumented primary replay against its accepted archive; no simulation.

Usage: python scripts/summarize_primary_phases.py --runs FCFS_ID RR_ID MAIN_ID --output DIR
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from audit_descriptor_performance import (ROOT, PRIMARY, accepted_run, check, ci,
                                          csv_write, read, sha)
from primary_phase_metrics import histogram_stats

KINDS = {"balanced", "burst_one", "idle", "light", "overload", "saturate"}
LATENCIES = ("generation_to_acceptance_completed", "acceptance_to_fire_completed",
             "acceptance_to_fire_drain_completed", "generation_censored_at_phase_end",
             "acceptance_censored_at_phase_end", "generation_censored_at_measurement_end",
             "acceptance_censored_at_measurement_end")
SAMPLES = ("fifo_occupancy_pre_edge", "producer_backlog_after_generation",
           "producer_backlog_post_edge")


def validate_bucket(b, n):
    cycles = b["cycles"]
    check(cycles > 0, "empty phase")
    for name in LATENCIES:
        h = b[name]
        hist = {int(k): v for k, v in h["histogram"].items()}
        check(all(k >= 0 and isinstance(v, int) and v > 0 for k, v in hist.items()), name)
        check(histogram_stats(hist) == h, f"invalid histogram: {name}")
    for field, per in [("generated", "generated_per_source"), ("accepted", "accepted_per_source"),
                       ("fires", "fires_per_source")]:
        check(len(b[per]) == n and all(x >= 0 for x in b[per]), per)
        check(sum(b[per]) == b[field], field)
    check(b["fires"] + b["stall_cycles"] + b["idle_ready_cycles"] + b["idle_not_ready_cycles"] == cycles,
          "cycle partition")
    check(b["ready_cycles"] == b["fires"] + b["idle_ready_cycles"], "ready partition")
    check(b["accepted"] == b["acceptance_to_fire_completed"]["count"], "accepted cohort")
    check(b["generated"] == b["generation_to_acceptance_completed"]["count"] +
          b["generation_censored_at_measurement_end"]["count"], "generated cohort")
    check(b["acceptance_to_fire_drain_completed"]["count"] ==
          b["acceptance_censored_at_measurement_end"]["count"], "drained cohort")
    for name in SAMPLES:
        s = b[name]
        check(s["samples"] == cycles and len(s["sum_per_source"]) == n, name)
        check(sum(s["sum_per_source"]) == s["sum_total"], name)
        check(s["mean_total"] == s["sum_total"] / cycles, name)
        for i in range(n):
            check(0 <= s["min_per_source"][i] <= s["mean_per_source"][i] <= s["max_per_source"][i], name)
            check(s["mean_per_source"][i] == s["sum_per_source"][i] / cycles, name)
            if name == "fifo_occupancy_pre_edge":
                check(s["max_per_source"][i] <= 16, "FIFO depth")


def validate_metrics(d, old):
    legacy = {k: v for k, v in d.items() if k not in ("primary_phase_metrics", "wall_time_s")}
    check(legacy == {k: v for k, v in old.items() if k != "wall_time_s"}, "legacy field changed")
    p, n = d["primary_phase_metrics"], d["n_src"]
    check(p["schema"] == "cxl-primary-phase-metrics-v1" and set(p["by_kind"]) == KINDS, "schema/kinds")
    end = 0
    for b in p["segments"]:
        check(b["start"] == end and b["length"] == b["cycles"], "phase partition")
        end += b["length"]
        validate_bucket(b, n)
    check(end == 100000, "measurement length")
    check(len(p["segments"]) == d["trace"]["phase_count"], "stimulus phase count")
    check({k: b["cycles"] for k, b in p["by_kind"].items()} == d["trace"]["phase_cycles_by_kind"], "stimulus phase durations")
    check(sum(b["ready_cycles"] for b in p["segments"]) == d["trace"]["ready_cycles"], "stimulus ready count")
    for kind, b in p["by_kind"].items():
        validate_bucket(b, n)
        parts = [x for x in p["segments"] if x["kind"] == kind]
        for name in LATENCIES:
            pooled = Counter()
            for part in parts:
                pooled.update({int(k): v for k, v in part[name]["histogram"].items()})
            check(histogram_stats(pooled) == b[name], "pooled histogram")
        for key in ("cycles", "ready_cycles", "stall_cycles", "idle_ready_cycles", "idle_not_ready_cycles", "generated", "accepted", "fires"):
            check(sum(x[key] for x in parts) == b[key], f"pooled {key}")
        for key in ("generated_per_source", "accepted_per_source", "fires_per_source"):
            check([sum(x[key][h] for x in parts) for h in range(n)] == b[key], f"pooled {key}")
        for name in SAMPLES:
            check(sum(x[name]["sum_total"] for x in parts) == b[name]["sum_total"], "pooled occupancy")
    for field, legacy_key in [("generated", "generated"), ("accepted", "input_push_count"), ("fires", "fires_measurement")]:
        check(sum(b[field] for b in p["segments"]) == d[legacy_key], field)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs=3, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = args.output
    check(not out.exists() or not any(out.iterdir()), "preserve previous audit; use fresh output")
    out.mkdir(parents=True, exist_ok=True)
    rows, sources, provenance, costs = [], [], [], []
    for (policy, (scope, old_id, _param, suffix)), run_id in zip(PRIMARY.items(), args.runs):
        base, summary, jobs = accepted_run(scope, run_id, 60)
        check(read(base / "primary_summary.json")["full_scope"] is True, "incomplete primary")
        keys = set()
        for step in jobs:
            name = f"cocotb_{step['name'].split(':', 1)[1]}__{suffix}"
            f = base / "results" / name
            oldf = ROOT / "artifacts/implementation" / scope / old_id / "results" / name
            d = read(f)
            p = validate_metrics(d, read(oldf))
            n, seed = d["n_src"], d["seed"]
            check((n, seed) not in keys, "duplicate run")
            keys.add((n, seed))
            provenance.append({"policy": policy, "N": n, "seed": seed,
                               "metrics": str(f.relative_to(ROOT)), "sha256": sha(f),
                               "legacy_metrics_sha256": sha(oldf), "trace_sha256": d["trace_sha256"]})
            costs.append(step["sim_wall_time_s"])
            for kind, b in p["by_kind"].items():
                row = {"policy": policy, "N": n, "seed": seed, "phase": kind, "cycles": b["cycles"],
                       "generated": b["generated"], "accepted": b["accepted"], "fires": b["fires"],
                       "offered_per_cycle": b["generated"] / b["cycles"],
                       "accepts_per_cycle": b["accepted"] / b["cycles"],
                       "fires_per_cycle": b["fires"] / b["cycles"],
                       "stall_fraction": b["stall_cycles"] / b["cycles"]}
                for name in LATENCIES:
                    for stat in ("count", "mean", "p99_nearest_rank", "max"):
                        row[name + "_" + stat] = b[name][stat]
                for name in SAMPLES:
                    for stat in ("mean_total", "max_total"):
                        row[name + "_" + stat] = b[name][stat]
                rows.append(row)
                for h in range(n):
                    sources.append({"policy": policy, "N": n, "seed": seed, "phase": kind, "source": h,
                                    "generated": b["generated_per_source"][h], "accepted": b["accepted_per_source"][h],
                                    "fires": b["fires_per_source"][h],
                                    "offered_share": b["generated_per_source"][h] / b["generated"] if b["generated"] else None,
                                    "service_share": b["fires_per_source"][h] / b["fires"] if b["fires"] else None})
        check(keys == {(n, s) for n in (4, 8, 16) for s in range(509, 529)}, "matrix")
    lookup = {(r["policy"], r["N"], r["seed"], r["phase"]): r for r in rows}
    metrics = [k for k in rows[0] if k not in ("policy", "N", "seed", "phase")]
    for n in (4, 8, 16):
        for seed in range(509, 529):
            for kind in KINDS:
                check(all(lookup["Main", n, seed, kind][m] == lookup["FCFS", n, seed, kind][m] for m in metrics), "all-High phase equivalence")
    stats, deltas = [], []
    for n in (4, 8, 16):
        for kind in sorted(KINDS):
            for policy in PRIMARY:
                for metric in metrics:
                    values = [lookup[policy, n, s, kind][metric] for s in range(509, 529)]
                    if all(v is not None for v in values):
                        stats.append({"policy": policy, "N": n, "phase": kind, "metric": metric, **ci(values)})
                if policy != "FCFS":
                    for metric in metrics:
                        values = [(lookup[policy, n, s, kind][metric], lookup["FCFS", n, s, kind][metric]) for s in range(509, 529)]
                        if all(a is not None and b is not None for a, b in values):
                            deltas.append({"contrast": policy + " minus FCFS", "N": n, "phase": kind, "metric": metric,
                                           **ci([a - b for a, b in values])})
    csv_write(out / "phase_runs.csv", rows)
    csv_write(out / "phase_sources.csv", sources)
    csv_write(out / "phase_seed_summary.csv", stats)
    csv_write(out / "phase_paired_differences.csv", deltas)
    audit = {"status": "PASS", "runs": args.runs, "rtl_runs": len(provenance), "measured_cycles": 18000000,
             "legacy_fields_identical_except_host_wall_time": True, "phases_per_run": 6,
             "stats": "20 run-level means; sampleSD and t19 95% CI. Mean runP99 is not pooled requestP99. Undefined cohort means remain blank in raw CSV; no partial-seed CI.",
             "sum_job_sim_wall_seconds": sum(costs), "inputs": provenance}
    (out / "phase-audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"PASS {len(provenance)} RTL replays; {len(rows)} pooled-kind rows; legacy fields unchanged")


if __name__ == "__main__":
    main()
