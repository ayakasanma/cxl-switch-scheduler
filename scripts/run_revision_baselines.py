#!/usr/bin/env python3
"""Run native-authored experimental correctness tests with the accepted strict engine."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import run_verify as rv

ROOT = Path(__file__).resolve().parents[1]
NAME = "revision-baseline"
BASE_TESTS = (
    "test_structure_and_reset", "test_full_before_pop_no_bypass",
    "test_stall_hold_and_mid_traffic_reset", "test_timestamp_wrap", "test_random",
)


def configurations():
    params = []

    def add(**overrides):
        row = dict(N_SRC=4, POLICY=0, DEPTH=16, RR_QUANTUM=10, FAI_W=256,
                   HIGH_QUOTA=10, MAIN_1W=0)
        row.update(overrides)
        if row not in params:
            params.append(row)

    for n in (4, 8, 16):
        for policy in range(5):
            add(N_SRC=n, POLICY=policy)
    for depth in (8, 32):
        for policy in range(5):
            add(DEPTH=depth, POLICY=policy)
    for q in (1, 4, 8, 16):
        add(POLICY=1, RR_QUANTUM=q)
    for q in (5, 10, 20):
        for one in (0, 1):
            add(POLICY=2, HIGH_QUOTA=q, MAIN_1W=one)
    for policy in (2, 3):
        add(POLICY=policy, FAI_W=5_000_000)
    result = []
    for i, row in enumerate(params):
        tests = list(BASE_TESTS)
        if row["POLICY"] == 4:
            tests += ["test_bliss_streak_and_priority", "test_bliss_clear_boundaries",
                      "test_bliss_clear_applied_then_wiped_and_held"]
        if row["POLICY"] == 2:
            tests += ["test_quota_high_only"]
            if row["FAI_W"] <= 256:
                tests += ["test_quota_high_low_alternation", "test_main_1w_classification"]
        result.append(dict(
            name=f"baseline_{i:02d}_n{row['N_SRC']}_p{row['POLICY']}_d{row['DEPTH']}",
            top="switch_experiment_top", filelist="rtl/experimental/filelist.f",
            params=row, default_params={}, test_dir="sim/experimental",
            test_module="test_experiment_top", seeds=[509], expect_tests=len(tests),
            env={"COCOTB_TEST_FILTER": "(" + "|".join(tests) + ")$"},
            timeout_s=1800,
        ))
    return result


def source_paths():
    paths = {"scripts/run_revision_baselines.py", "scripts/run_verify.py",
             "scripts/wsl_env.sh", "sim/experimental/test_experiment_top.py",
             "sim/experimental/test_baseline_models.py", "sim/common/hier_util.py",
             "rtl/experimental/filelist.f"}
    for line in (ROOT / "rtl/experimental/filelist.f").read_text().splitlines():
        line = line.strip()
        if line.endswith(".sv"):
            paths.add(line)
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "refc/cxl_model").glob("*.py")
                 if p.name != "experimental.py")
    return sorted(paths)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs", type=int, choices=(1, 2, 3), default=3)
    p.add_argument("--case", type=int, action="append", help="explicit diagnostic subset; not full acceptance")
    args = p.parse_args(argv)
    all_configs = configurations()
    if args.case and any(i < 0 or i >= len(all_configs) for i in args.case):
        p.error("case index is outside the correctness matrix")
    configs = [c for i, c in enumerate(all_configs) if not args.case or i in args.case]
    rv.MILESTONES[NAME] = dict(
        description="Experimental baseline correctness; not production performance",
        implemented=True,
        lint=[{k: c[k] for k in ("name", "top", "filelist", "params")} for c in configs],
        pytest=[dict(name="native_models", target="sim/experimental/test_baseline_models.py",
                     expect_tests=15)],
        cocotb=configs,
    )
    # Existing strict runner owns compilation, subprocess exits and zero-skip JUnit checks.
    command = [NAME, "-j", str(args.jobs), "--make-jobs", "2", "--keep-going"]
    contents = {s: (ROOT / s).read_bytes() for s in source_paths()}
    before = {s: hashlib.sha256(data).hexdigest() for s, data in contents.items()}
    code = rv.main(command)
    folder = ROOT / "artifacts/implementation" / NAME
    latest = (folder / "latest.txt").read_text().strip()
    out = folder / latest
    after = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in before}
    stable = before == after
    archive = out / "sources.zip"
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for s, data in contents.items():
            z.writestr(s, data)
    record = dict(selected_cases=args.case, complete_matrix=not args.case,
                  source_hashes_before=before, source_hashes_after=after, stable=stable,
                  source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  runner_exit=code, exit_code=int(bool(code or not stable)),
                  production_performance=False)
    (out / "baseline_scope.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(dict(output=str(out), **{k: record[k] for k in (
        "complete_matrix", "stable", "runner_exit", "exit_code")})))
    return record["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
