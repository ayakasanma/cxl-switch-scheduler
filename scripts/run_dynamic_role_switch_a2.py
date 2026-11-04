#!/usr/bin/env python3
"""Verify the v2 A2 engineering matrix, without running W5M traffic or held-out seeds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import run_rtl_diagnosis as diag
from compare_diagnosis_results import compare

ROOT = Path(__file__).resolve().parents[1]
NAME = "dynamic-role-switch-v2-a2"
CASES = (
    ("multi-window", 16, [0], "bernoulli"),
    ("role-switch", 16, [0, 0, 1, 1], "bernoulli"),
    ("ready-spread", 16, [0], "spread"),
    ("ready-bursty", 16, [0], "bursty"),
    ("depth8-bursty", 8, [0], "bursty"),
)
EXCLUDE = {
    "schema": "different RTL/model output schemas",
    "evidence_kind": "SCHEDULER_RTL versus MODEL_ONLY",
    "limitations": "evidence boundary text",
    "native_coverage": "DUT-only",
    "native_cgof": "DUT-only",
    "native_main": "DUT-only",
    "input_hold_checks": "DUT-only",
    "wall_s": "runtime",
}


def matrix():
    rows = []
    for window in (256, 64):
        for case, depth, sources, ready in CASES:
            if window == 64 and case != "role-switch":
                continue
            for policy in ("FAI-inspired", "CGOF(1:1)", "CGOF(2:1)"):
                for lane in ("mixed", "isolated"):
                    weight = None if policy == "FAI-inspired" else (1 if policy == "CGOF(1:1)" else 2)
                    job = diag.make_job("finite-heavy", lane, 7301, window, weight,
                                        4, 7*window//2, "near", 8*window, depth=depth,
                                        heavy_sources=sources, ready_pattern=ready)
                    if policy == "FAI-inspired":
                        job["policy"] = policy
                    cfg = diag.config(job)
                    cfg["name"] = f"{case}-{cfg['name']}"
                    rows.append(cfg)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lint-only", action="store_true")
    args = parser.parse_args()
    import sys
    sys.path.insert(0, str(ROOT / "sim/experimental"))
    from cgof_diagnosis_model import run as model_run

    rows = matrix()
    lint = {}
    for cfg in rows:
        for window in (cfg["params"]["FAI_W"], 5_000_000):
            params = dict(cfg["params"], FAI_W=window)
            key = json.dumps((cfg["top"], params), sort_keys=True)
            if key not in lint:
                lint[key] = dict(name=f"a2_{len(lint)}", top=cfg["top"],
                                 filelist=cfg["filelist"], params=params)
    directed = []
    for window in (64, 256):
        for depth in (8, 16):
            cfg = next(c for c in rows if c["top"] == "switch_experiment_top"
                       and c["params"]["FAI_W"] == window)
            cfg = dict(cfg, name=f"main_held_close_w{window}_d{depth}",
                       params=dict(cfg["params"], DEPTH=depth),
                       env={"COCOTB_TEST_FILTER": r"(^|\.)main_hold_crosses_class_close$"},
                       artifacts=[dict(file="main_held_close.json", required=True)])
            directed.append(cfg)
    diag.rv.MILESTONES[NAME] = dict(
        description="v2 A2: Main/CGOF four-window diagnosis and physical-source accounting",
        implemented=True, lint=list(lint.values()),
        pytest=[dict(name="source_book", target="sim/experimental/test_diagnosis_source_book.py", expect_tests=3)],
        cocotb=rows+directed,
    )
    before = diag.freeze_sources()
    run = diag.rv.Run(argparse.Namespace(
        milestone=NAME, infra_smoke=False, jobs=2, make_jobs=1, keep_going=False,
        lint_only=args.lint_only, seed_list=None, n_src_list=None, cocotb_timeout=None, cycles=None,
    ), ROOT)
    diag.archive_sources(run.out / "sources.zip", before)
    code = run.execute()
    stable = before == diag.freeze_sources()
    if code or not stable:
        print(json.dumps(dict(status="FAIL", code=code, source_stable=stable, output=str(run.out))))
        return 1
    if args.lint_only:
        with (run.out / "a2_lint_scope.json").open("x", encoding="utf-8") as f:
            json.dump(dict(status="PASS", source_stable=stable, source_hashes=before,
                           configurations=list(lint.values())), f, indent=2)
        print(json.dumps(dict(status="PASS", lint_configurations=len(lint), output=str(run.out))))
        return 0
    results = diag.load_results(run.out, rows)
    checks = []
    for index, item in enumerate(results):
        result = model_run(item["job"])
        output = run.out / "results" / f"model_{index:02d}.json"
        with output.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        candidate = json.loads(output.read_text())
        fields = compare(item["data"], candidate, EXCLUDE)
        bad = {k: v for k, v in fields.items() if v["status"] in ("DIFFERENT", "MISSING")}
        checks.append(dict(reference=item["path"], candidate=output.relative_to(run.out).as_posix(),
                           status="FAIL" if bad else "PASS", fields=fields))
        if bad:
            break
    passed = len(checks) == len(rows) and all(c["status"] == "PASS" for c in checks)
    scope = dict(schema="cxl-dynamic-role-switch-a2-v1", status="PASS" if passed else "FAIL",
                 seed=7301, w256_jobs=30, w64_jobs=6, production_traffic_run=False,
                 source_stable=stable, source_hashes=before,
                 g_eq_new=checks, finite_heavy_pairs=diag.paired_results(results),
                 directed_held_close_jobs=len(directed),
                 drain_evidence="NOT_EXERCISED", confirmation_seeds_used=[],
                 limitations="short-window anchor equality only; no W5M Main traffic or multi-seed RTL claim")
    with (run.out / "a2_scope.json").open("x", encoding="utf-8") as f:
        json.dump(scope, f, indent=2)
    print(json.dumps(dict(status=scope["status"], rtl_jobs=len(results),
                          g_eq_pass=sum(c["status"] == "PASS" for c in checks),
                          source_stable=stable, output=str(run.out))))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
