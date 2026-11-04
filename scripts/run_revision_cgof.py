#!/usr/bin/env python3
"""Run the EXPERIMENTAL CGOF (Credit-Gated Oldest-First) correctness checks with the accepted
strict run_verify engine: CGOF(2:1) / CGOF(1:1) x oldest-first / credit-gated eligible
round-robin. Correctness only; not production performance or PPA.

The complete correctness matrix is defined, but a run executes only an explicitly labeled subset
(--subset) or explicit case indices (--case); --complete-matrix must be requested on purpose.
Lint and elaboration-rejection coverage always run in full."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

import run_verify as rv

ROOT = Path(__file__).resolve().parents[1]
NAME = "revision-cgof"
TOP = "cgof_unit_top"
FILELIST = "rtl/experimental/filelist_cgof_unit.f"
TEST_MODULE = "test_cgof_sched"
RESULT_FILE = "cgof_checks.json"
W5M = 5_000_000
WINDOWS = (64, 256, W5M)
HIGH_WEIGHTS = (2, 1)
ORDERINGS = {0: "oldest-first", 1: "eligible-round-robin"}
BASE_TESTS = (
    "test_structure_and_reset", "test_full_before_pop_no_bypass",
    "test_refill_exhaust_inactive_overwrite", "test_reentry_and_held_refill_across_push",
    "test_shares_fixed_classes", "test_stall_hold_and_mid_traffic_reset", "test_long_stall",
    "test_timestamp_wrap", "test_reversed_rotation_order", "test_eligible_rr_pointer", "test_random",
)
SMALL_W_TESTS = ("test_class_change_held_across_close", "test_window_threshold_boundaries")
W5M_TESTS = ("test_w5m_threshold_injection",)
MODEL_TEST_MODULE = "refc.tests.test_experimental"
RUNNER_TESTS = "scripts/test_revision_cgof.py"
# Invalid parameters: each must be rejected by exactly its own intentional $fatal.
REJECTS = (
    ("N_SRC", 2, "cgof_unit_top: N_SRC=2 is not supported (4, 8 or 16)"),
    ("N_SRC", 32, "cgof_unit_top: N_SRC=32 is not supported (4, 8 or 16)"),
    ("DEPTH", 4, "cgof_unit_top: DEPTH=4 is not supported (8, 16 or 32)"),
    ("FAI_W", 128, "cxl_cgof_sched: W=128 is not supported (5000000, or stress 64 / 256)"),
    ("HIGH_WEIGHT", 0, "cxl_cgof_sched: HIGH_WEIGHT=0 is not supported (2 for 2:1, or 1 for 1:1)"),
    ("HIGH_WEIGHT", 3, "cxl_cgof_sched: HIGH_WEIGHT=3 is not supported (2 for 2:1, or 1 for 1:1)"),
    ("ELIGIBLE_RR", 2, "cxl_cgof_sched: ELIGIBLE_RR=2 is not supported (0 oldest-first, 1 eligible RR)"),
)


def row(n=4, depth=16, window=64, hw=2, rr=0):
    return dict(N_SRC=n, DEPTH=depth, FAI_W=window, HIGH_WEIGHT=hw, ELIGIBLE_RR=rr)


def tag(p):
    return f"n{p['N_SRC']}_d{p['DEPTH']}_w{p['FAI_W']}_hw{p['HIGH_WEIGHT']}_rr{p['ELIGIBLE_RR']}"


def identity(p):
    """Explicit configuration identity: allocation x ordering."""
    return f"CGOF({p['HIGH_WEIGHT']}:1)/{ORDERINGS[p['ELIGIBLE_RR']]}"


def identities():
    return [(hw, rr) for hw in HIGH_WEIGHTS for rr in ORDERINGS]


def lint_configurations():
    """Strict positive lint of every supported parameter combination (W5M included)."""
    return [dict(name=f"cgof_{tag(p)}", top=TOP, filelist=FILELIST, params=p)
            for p in (row(n, d, w, hw, rr) for hw, rr in identities() for n in (4, 8, 16)
                      for d in (8, 16, 32) for w in WINDOWS)]


def reject_configurations():
    return [dict(name=f"cgof_bad_{k.lower()}_{v}", top=TOP, filelist=FILELIST, params={k: v},
                 expect_message=msg, allowed_undriven=[], allowed_unused=[],
                 expect_undriven=[], expect_unused=[]) for k, v, msg in REJECTS]


def configurations():
    """Correctness matrix per identity: N4/8/16 at W64 and W5M, W256, depths 8/32."""
    params = []
    for hw, rr in identities():
        for n in (4, 8, 16):
            params += [row(n, 16, 64, hw, rr), row(n, 16, W5M, hw, rr)]
        params += [row(4, 16, 256, hw, rr), row(4, 8, 64, hw, rr), row(8, 32, 256, hw, rr)]
    result = []
    for i, p in enumerate(params):
        tests = BASE_TESTS + (SMALL_W_TESTS if p["FAI_W"] <= 256 else W5M_TESTS)
        result.append(dict(
            name=f"cgof_{i:02d}_{tag(p)}", top=TOP, filelist=FILELIST, params=p,
            default_params={}, test_dir="sim/experimental", test_module=TEST_MODULE,
            seeds=[509], expect_tests=len(tests),
            env={"COCOTB_TEST_FILTER": "(" + "|".join(tests) + ")$"},
            artifacts=[{"file": RESULT_FILE, "required": True}],
            timeout_s=3600,
        ))
    return result


def _select(pred):
    return [i for i, c in enumerate(configurations()) if pred(c["params"])]


# Explicitly labeled bounded subsets (representative W64 D16 diagnosis; never the whole matrix).
SUBSETS = {
    "w64-n4-d16-all-identities": lambda p: p["FAI_W"] == 64 and p["DEPTH"] == 16 and p["N_SRC"] == 4,
    "w64-n8n16-d16-all-identities": lambda p: (p["FAI_W"] == 64 and p["DEPTH"] == 16
                                               and p["N_SRC"] in (8, 16)),
}


def subset_cases(label):
    return _select(SUBSETS[label])


def runner_test_count():
    text = (ROOT / RUNNER_TESTS).read_text()
    return len(re.findall(r"^    def test_\w+\(self\)", text, re.M))


def source_paths():
    """Every source byte the run depends on: RTL filelist, testbench, oracle, runner, engine."""
    paths = {"scripts/run_revision_cgof.py", RUNNER_TESTS, "scripts/run_verify.py",
             "scripts/run_verify.sh", "scripts/wsl_env.sh", f"sim/experimental/{TEST_MODULE}.py",
             "sim/common/hier_util.py", FILELIST, "refc/tests/test_experimental.py"}
    for line in (ROOT / FILELIST).read_text().splitlines():
        line = line.strip()
        if line.endswith(".sv"):
            paths.add(line)
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "refc/cxl_model").glob("*.py"))
    return sorted(paths)


def run_model_tests(log):
    """The model tests use unittest subTests, whose pytest-9 JUnit totals the strict engine rejects;
    run them under unittest. The expected count is discovered from the suite itself (the parent may
    add tests), then the run must report exactly that count, exit 0 and a plain OK."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    count_cmd = [sys.executable, "-c",
                 "import unittest; print(unittest.defaultTestLoader.loadTestsFromName("
                 f"{MODEL_TEST_MODULE!r}).countTestCases())"]
    disc = subprocess.run(count_cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    discovered = int(disc.stdout.strip()) if disc.returncode == 0 and disc.stdout.strip().isdigit() else None
    cmd = [sys.executable, "-m", "unittest", "-v", MODEL_TEST_MODULE]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    log.write_text(f"$ {' '.join(count_cmd)}\nexit={disc.returncode}\n{disc.stdout}{disc.stderr}\n"
                   f"$ {' '.join(cmd)}\nexit={proc.returncode}\n{proc.stdout}{proc.stderr}")
    text = proc.stderr.strip().splitlines()
    ran = re.search(r"^Ran (\d+) tests? in ", proc.stderr, re.M)
    tests = int(ran.group(1)) if ran else None
    ok = (proc.returncode == 0 and discovered is not None and discovered > 0 and tests == discovered
          and bool(text) and text[-1] == "OK")
    return dict(discover_command=count_cmd, discover_exit=disc.returncode, discovered_tests=discovered,
                command=cmd, exit=proc.returncode, tests=tests,
                final_line=text[-1] if text else None, log=log.relative_to(ROOT).as_posix(),
                **{"pass": ok})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs", type=int, choices=(1, 2), default=2)
    sel = p.add_mutually_exclusive_group(required=True)
    sel.add_argument("--subset", choices=sorted(SUBSETS), help="explicitly labeled bounded subset")
    sel.add_argument("--case", type=int, action="append", help="explicit diagnostic case indices")
    sel.add_argument("--complete-matrix", action="store_true", help="every correctness case")
    args = p.parse_args(argv)
    all_configs = configurations()
    if args.case and any(i < 0 or i >= len(all_configs) for i in args.case):
        p.error("case index is outside the correctness matrix")
    if args.subset:
        cases, label = subset_cases(args.subset), args.subset
    elif args.case:
        cases, label = sorted(set(args.case)), "explicit-cases"
    else:
        cases, label = list(range(len(all_configs))), "complete-matrix"
    configs = [all_configs[i] for i in cases]
    runner_tests = runner_test_count()
    rv.MILESTONES[NAME] = dict(
        description=f"Experimental CGOF correctness, subset {label}; not production performance",
        implemented=True,
        lint=lint_configurations(),
        elab_reject=reject_configurations(),
        pytest=[dict(name="cgof_runner", target=RUNNER_TESTS, expect_tests=runner_tests)],
        cocotb=configs,
    )
    # Existing strict runner owns lint, rejection, compilation, exits and zero-skip JUnit checks.
    command = [NAME, "-j", str(args.jobs), "--make-jobs", "2", "--keep-going"]
    contents = {s: (ROOT / s).read_bytes() for s in source_paths()}
    before = {s: hashlib.sha256(data).hexdigest() for s, data in contents.items()}
    code = rv.main(command)
    folder = ROOT / "artifacts/implementation" / NAME
    latest = (folder / "latest.txt").read_text().strip()
    out = folder / latest
    model = run_model_tests(out / "logs" / "unittest_experimental_model.log")
    after = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in before}
    stable = before == after
    archive = out / "sources.zip"
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
        for s, data in contents.items():
            z.writestr(s, data)
    record = dict(subset_label=label, selected_cases=cases,
                  selected_configs=[dict(name=c["name"], identity=identity(c["params"]),
                                         params=c["params"]) for c in configs],
                  complete_matrix=len(cases) == len(all_configs), matrix_size=len(all_configs),
                  identities=[identity(row(hw=hw, rr=rr)) for hw, rr in identities()],
                  runner_tests_expected=runner_tests,
                  source_hashes_before=before, source_hashes_after=after, stable=stable,
                  source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  model_unittest=model, runner_exit=code,
                  exit_code=int(bool(code or not stable or not model["pass"])),
                  production_performance=False,
                  production_w5m_full_duration="NOT_RUN", production_w5m_confirmation="NOT_RUN",
                  ppa="NOT_RUN")
    (out / "cgof_scope.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(dict(output=str(out), **{k: record[k] for k in (
        "subset_label", "complete_matrix", "stable", "runner_exit", "exit_code")},
        model_pass=model["pass"], model_tests=model["tests"])))
    return record["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
