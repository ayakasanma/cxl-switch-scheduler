#!/usr/bin/env python3
"""Freeze the approved revision matrix and evidence audit without editing the manuscript."""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXPLORATION = tuple(range(509, 514))
CONFIRMATION = tuple(range(529, 549))
POLICIES = ("FCFS", "RR1", "RR10", "MAIN", "ALG2", "BLISS")
PRIMARY = "759f86b24f13ed5984c19034eeeea2ca43b0e971"
CURRENT = "c8e7ea8c0e4530572b3abf5b14ea9958e24f1789"
PROFILE = "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d"


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def matrix():
    """One HOG job contains both A/B cohorts; power activity is separate per cohort."""
    jobs = []

    def add(group, policy, n, seed, **overrides):
        row = dict(group=group, policy=policy, n_src=n, seed=seed, depth=16,
                   window=5_000_000, training_cycles=10_000_000, ready="always",
                   heavy_rate=1, heavy_source=0, burst_size=8, burst_period=1024,
                   rr_quantum=1 if policy == "RR1" else 10,
                   high_quota=10, low_quota=10, cohorts=["A", "B"],
                   execution_status="NOT_RUN", evidence_kind="RTL_REQUIRED",
                   prerequisite="verified experimental harness; frozen source and parameters")
        row.update(overrides)
        # Include all experimental dimensions in the identity, never transient status.
        row["id"] = f"{group}-{policy}-n{n}-s{seed}-{canonical_sha(row)[:12]}"
        jobs.append(row)

    for policy in POLICIES:
        for seed in CONFIRMATION:
            add("n4-confirmation", policy, 4, seed, seed_role="confirmation")
        for n in (8, 16):
            for seed in EXPLORATION:
                add("n-expansion", policy, n, seed, seed_role="exploration",
                    sparse_rate_per_source="1/128")
        cases = (
            dict(case="ready075", ready="bernoulli-0.75"),
            dict(case="ready48of64", ready="periodic-48/64"),
            dict(case="heavy050", heavy_rate=.5),
            dict(case="heavy090", heavy_rate=.9),
            dict(case="burst32", burst_size=32, burst_period=4096),
            dict(case="heavy-id3", heavy_source=3),
        )
        for case in cases:
            for seed in EXPLORATION:
                add("trained-robustness", policy, 4, seed, seed_role="exploration",
                    perturbation_after_training=case["case"] != "heavy-id3",
                    **case)
    for q in (1, 4, 8, 10, 16):
        for seed in EXPLORATION:
            add("rr-quantum", "RR", 4, seed, rr_quantum=q, seed_role="exploration")
    for q in (5, 10, 20):
        for seed in EXPLORATION:
            add("high-quota", "MAIN", 4, seed, high_quota=q, seed_role="exploration")
    for policy in ("FCFS", "RR10", "MAIN"):
        for depth in (8, 16, 32):
            for seed in EXPLORATION:
                add("depth", policy, 4, seed, depth=depth, seed_role="exploration")
        for seed in EXPLORATION[:3]:
            add("matched-power", policy, 4, seed, seed_role="exploration",
                evidence_kind="VCS_SAIF_PT_REQUIRED", activity_cohorts_separate=True,
                prerequisite="matched trained HOG activity; current FastX licenses")
    for policy in ("MAIN", "ALG2", "MAIN1W"):
        for seed in EXPLORATION[:3]:
            add("adaptation", policy, 4, seed, seed_role="exploration", heavy_rate=.8,
                cohorts=["role0", "role3", "role0-return"], training_cycles=0,
                measured_cycles=30_000_000, role_change_period=10_000_000)
    for seed in EXPLORATION:
        add("one-window-causal", "MAIN1W", 4, seed, seed_role="exploration")
    for seed in CONFIRMATION:
        add("insight-confirmation", "INSIGHT_WINNER", 4, seed, seed_role="confirmation",
            prerequisite="complete validated production model gate; ONE frozen winner",
            conditional=True)
    for ready in ("bernoulli-0.75", "periodic-48/64"):
        for seed in EXPLORATION:
            add("insight-robustness", "INSIGHT_WINNER", 4, seed, ready=ready,
                seed_role="exploration", conditional=True,
                prerequisite="complete validated production model gate; ONE frozen winner")
    if len({r["id"] for r in jobs}) != len(jobs):
        raise ValueError("duplicate experiment identities")
    return jobs


def evidence_audit(root=ROOT):
    """Recompute F1 and reference hash links; historical formal reports remain scoped."""
    root = Path(root)
    ppa_path = root / "docs/ppa/primary-20261021-v2.json"
    formal_path = root / "docs/ppa/formality-20261021.json"
    ppa, formal = (json.loads(p.read_text(encoding="utf-8")) for p in (ppa_path, formal_path))
    if ppa["profile_canonical_sha256"] != PROFILE:
        raise ValueError("unreviewed PPA profile")
    areas = {(row["policy"], row["N"]): row["cell_area"] for row in ppa["cases"]}
    arithmetic = []
    for n in (4, 8, 16):
        main, rr, fcfs = (areas[(p, n)] for p in ("fai-main", "rr", "fcfs"))
        arithmetic.append(dict(n_src=n, main_over_rr_percent=100 * (main / rr - 1),
                               rr_below_main_percent=100 * (1 - rr / main),
                               main_over_fcfs_percent=100 * (main / fcfs - 1)))
    bridges, missing = [], []
    for policy in ("fcfs", "rr", "fai-main"):
        for n in (4, 8, 16):
            found = [r for r in formal["cases"] if r["policy"] == policy and r["n_src"] == n
                     and r["reference_source_commit"] == CURRENT
                     and r["mapped_source_commit"] == PRIMARY]
            if not found:
                missing.append(dict(policy=policy, n_src=n, status="NOT_RUN_IN_OLD_MANIFEST"))
                continue
            row = found[0]
            mismatch = [name for name, sha in row["reference_rtl_sha256"].items()
                        if not (root / name).is_file() or digest(root / name) != sha]
            if mismatch:
                raise ValueError(f"current reference RTL hash mismatch: {mismatch}")
            if any(row[k] for k in ("failing", "aborted", "unverified", "unmatched", "active_black_boxes")):
                raise ValueError("nonpassing formal bridge")
            reports = root / row["evidence_directory"]
            wrong = [name for name, sha in row["report_sha256"].items()
                     if not (reports / name).is_file() or digest(reports / name) != sha]
            if wrong:
                raise ValueError(f"bridge report hash mismatch: {wrong}")
            bridges.append(dict(policy=policy, n_src=n, status="REUSED_HASH_CHECKED_BRIDGE",
                                reference_source=CURRENT, mapped_source=PRIMARY,
                                evidence_directory=row["evidence_directory"]))
    body = root / "docs/final-report/sections/hotnets-body-v3.tex"
    locators = []
    if body.is_file():
        for line, text in enumerate(body.read_text(encoding="utf-8").splitlines(), 1):
            if "38.22" in text or "smaller." in text:
                locators.append(dict(path=body.relative_to(root).as_posix(), line=line, text=text))
    return dict(arithmetic=arithmetic, reused_bridges=bridges, missing_in_old_manifest=missing,
                overclaim_locators=locators, manuscript_modified=False,
                source_files={p.relative_to(root).as_posix(): digest(p) for p in (ppa_path, formal_path)},
                expected_sparse_hog_heavy_residual=1 - 3 / 128,
                normalized_offered_heavy_share=128 / 131,
                residual_and_offered_share_are_different_quantities=True)


def snapshot(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = matrix()
    result = dict(schema="cxl-revision-matrix-v1", created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  material_passport=dict(origin="owner-approved revision plan 2026-10-23",
                                         verification_status="PLAN_FROZEN_NOT_EXECUTED",
                                         scope="single-output descriptor RTL slice"),
                  head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  jobs=rows, counts=dict(Counter(r["group"] for r in rows)),
                  total_planned_jobs=len(rows), core_unconditional_jobs=sum(not r.get("conditional") for r in rows),
                  matrix_sha256=canonical_sha(rows), observation_unit="paired seed/run",
                  bootstrap=dict(replicates=10_000, rng_seed=20261023),
                  resources=dict(max_sim_workers=6, build_jobs=2, max_available_memory_fraction=.70),
                  paper_revision="AWAITING_SEPARATE_APPROVAL",
                  independent_re_review="AFTER_APPROVED_MANUSCRIPT_REVISION",
                  model_screen="NOT_A_SUBSTITUTE_FOR_RTL",
                  candidate_ppa="at most one N4 candidate; own-netlist equivalence; 25ns TT profile",
                  evidence_audit=evidence_audit())
    (output / "matrix.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    sources = [Path(__file__), ROOT / "specs/CXL_SPEC.md", ROOT / "specs/APPROVAL.md"]
    sources += list((ROOT / "rtl").rglob("*.sv"))
    sources += list((ROOT / "refc/cxl_model").glob("*.py"))
    (output / "source-hashes.json").write_text(
        json.dumps({p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(sources)}, indent=2) + "\n",
        encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="fresh immutable snapshot directory")
    args = parser.parse_args()
    result = snapshot(args.output)
    print(json.dumps({k: result[k] for k in ("total_planned_jobs", "core_unconditional_jobs",
                                           "matrix_sha256", "counts")}, indent=2))


if __name__ == "__main__":
    main()
