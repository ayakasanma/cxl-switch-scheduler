#!/usr/bin/env python3
"""Run the four v2 A3 Main W5M RTL anchors for the engineering pilot seed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import run_rtl_diagnosis as diag

ROOT = Path(__file__).resolve().parents[1]
NAME = "dynamic-role-switch-v2-a3"
WINDOW = 5_000_000
HEAVY = 17_500_000
ACTIVE_CAP = 24_000_000
ANCHORS = (
    ("role-switch", 16, [0, 0, 1, 1], "bernoulli", "mixed"),
    ("role-switch", 16, [0, 0, 1, 1], "bernoulli", "isolated"),
    ("multi-window", 16, [0], "bernoulli", "mixed"),
    ("depth8-bursty", 8, [0], "bursty", "mixed"),
)


def configs(window: int, heavy: int, cap: int) -> list:
    rows = []
    for case, depth, sources, ready, lane in ANCHORS:
        job = diag.make_job("finite-heavy", lane, 7301, window, None, 4, heavy, "near", cap,
                            depth=depth, heavy_sources=sources, ready_pattern=ready)
        job["policy"] = "FAI-inspired"
        cfg = diag.config(job)
        cfg["name"] = f"a3-{case}-{cfg['name']}"
        rows.append(cfg)
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=2)
    args = parser.parse_args(argv)
    if args.dry_run == args.production:
        parser.error("choose exactly one of --dry-run or --production")
    window, heavy, cap = ((256, 896, 8*256) if args.dry_run
                          else (WINDOW, HEAVY, ACTIVE_CAP))
    rows = configs(window, heavy, cap)
    lint = []
    for row in rows:
        lint.append(dict(name=row["name"], top=row["top"], filelist=row["filelist"], params=row["params"]))
    lint.append(dict(name="a3_production_params", top="switch_experiment_top",
                     filelist="rtl/experimental/filelist.f",
                     params=dict(rows[0]["params"], FAI_W=WINDOW)))
    diag.rv.MILESTONES[NAME] = dict(
        description="v2 A3 Main W5M anchors: role-switch, multi-window, depth8-bursty",
        implemented=True, lint=lint,
        pytest=[dict(name="source_book", target="sim/experimental/test_diagnosis_source_book.py", expect_tests=3)],
        cocotb=rows)
    before = diag.freeze_sources()
    run = diag.rv.Run(argparse.Namespace(
        milestone=NAME, infra_smoke=False, jobs=args.jobs, make_jobs=1, keep_going=False,
        lint_only=False, seed_list=None, n_src_list=None, cocotb_timeout=None, cycles=None), ROOT)
    diag.archive_sources(run.out/"sources.zip", before)
    code = run.execute()
    stable = before == diag.freeze_sources()
    if code or not stable:
        print(json.dumps(dict(status="FAIL", code=code, source_stable=stable, output=str(run.out))))
        return 1
    results = diag.load_results(run.out, rows)
    scope = dict(schema="cxl-dynamic-role-switch-a3-v1", status="PASS", dry_run=args.dry_run,
                 production=args.production, seed=7301, window=window, heavy_work=heavy,
                 source_stable=stable, source_hashes=before,
                 anchors=[dict(case=case, lane=lane, depth=depth) for case, depth, _s, _r, lane in ANCHORS],
                 results=[dict(job=r["job"], path=r["path"], active_cycles=r["data"]["active_cycles"],
                               drain_cycles=r["data"]["drain_cycles"],
                               sparse_p99=r["data"]["generation_roles"]["latency"]["sparse"]
                               ["generation_to_fire"].get("p99_nearest_rank"),
                               physical_sources=r["data"].get("physical_sources") is not None)
                          for r in results],
                 confirmation_seeds_used=[], drain="NOT_EXERCISED",
                 limitations="four Main W5M anchors, one engineering seed; no confirmation claim")
    with (run.out/"a3_scope.json").open("x", encoding="utf-8") as f:
        json.dump(scope, f, indent=2)
    print(json.dumps(dict(status="PASS", jobs=len(results), output=str(run.out))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
