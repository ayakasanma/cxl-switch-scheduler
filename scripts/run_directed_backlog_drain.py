#!/usr/bin/env python3
"""Run the SCHEDULER_RTL_DIRECTED_BACKLOG_DRAIN cases through the strict verifier.

Three separate configurations on the unchanged RTL, N4/D16/full105/FAI_W=5,000,000:
CGOF(1:1) oldest-first, CGOF(2:1) oldest-first, and Main (FAI-inspired, HIGH_QUOTA 10).
Engineering fixture seed 7301 only (not power seeds 509-511, not confirmation seeds 7401-7420).
Short bounded directed sequence from reset/all-High: no window closes, so production W
parameters do not imply long production training. No latency/fairness/power claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "sim" / "experimental"))
import run_rtl_diagnosis as diag  # noqa: E402

NAME = "fastx-power-20261107/directed-drain"
SCOPE = "SCHEDULER_RTL_DIRECTED_BACKLOG_DRAIN"
SEED = 7301
SEEDS_FORBIDDEN = (509, 510, 511, *range(7401, 7421))
WINDOW = 5_000_000
GEN_CYCLES = 512
RATES = [0.75, 0.5, 0.375, 0.25]
TEST_MODULE = "test_directed_backlog_drain"
TEST_NAME = "directed_backlog_drain_rtl"
NEW_SOURCES = (
    "sim/experimental/test_directed_backlog_drain.py",
    "scripts/run_directed_backlog_drain.py",
    "scripts/test_directed_backlog_drain.py",
)
PYTEST_EXPECT = 9
assert SEED not in SEEDS_FORBIDDEN


def make_job(high_weight):
    main = high_weight is None
    return dict(
        scope=SCOPE, seed=SEED, n_src=4, depth=16, window=WINDOW,
        policy="FAI-inspired" if main else f"CGOF({high_weight}:1)",
        high_weight=high_weight, ordering="oldest-first",
        gen_cycles=GEN_CYCLES, rates=list(RATES),
    )


def tag(job):
    return "main" if job["high_weight"] is None else f"hw{job['high_weight']}"


def config(job):
    main = job["policy"] == "FAI-inspired"
    out = f"directed_drain_{tag(job)}.json"
    fail = out.replace(".json", "_failure.json")
    return dict(
        name=f"directed-drain-{tag(job)}-w{job['window']}-d{job['depth']}-seed{job['seed']}",
        top="switch_experiment_top" if main else diag.TOP,
        filelist="rtl/experimental/filelist.f" if main else diag.FILELIST,
        params=diag.params(job),
        default_params={},
        test_dir="sim/experimental",
        test_module=TEST_MODULE,
        seeds=[job["seed"]],
        expect_tests=1,
        timeout_s=1800,
        env={
            "CXL_DRAIN_JOB": json.dumps(job, sort_keys=True),
            "CXL_DRAIN_OUTPUT": out,
            "CXL_DRAIN_FAILURE": fail,
            "COCOTB_TEST_FILTER": rf"(^|\.){TEST_NAME}$",
        },
        artifacts=[dict(file=out, required=True), dict(file=fail, required=False)],
    )


def configs():
    return [config(make_job(hw)) for hw in (1, 2, None)]


def source_paths():
    return sorted(set(diag.source_paths()) | set(NEW_SOURCES))


def freeze():
    return {name: diag.sha(ROOT / name) for name in source_paths()}


def drain_module():
    """The sim accounting module, loaded by path (its name collides with the pytest file)."""
    import importlib.util
    name = "cxl_directed_backlog_drain_sim"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / NEW_SOURCES[0])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def expected(job):
    return drain_module().run_model_only(job)


def compare(data, pred):
    """Fields that must match the independent model-only replay exactly."""
    problems = []
    for key in ("producer_backlog", "fifo_occupancy", "generated", "accepted", "fired",
                "pending", "cycle"):
        if data["cutoff"][key] != pred["cutoff"][key]:
            problems.append(f"cutoff.{key} {data['cutoff'][key]} != model {pred['cutoff'][key]}")
    for key in ("start_cycle", "end_cycle", "cycles", "limit"):
        if data["drain"][key] != pred["drain"][key]:
            problems.append(f"drain.{key} {data['drain'][key]} != model {pred['drain'][key]}")
    for key in ("generated", "accepted", "fired"):
        if data["final"][key] != pred["final"][key]:
            problems.append(f"final.{key} differs from model")
    if data["input_hold_checks"] != pred["input_hold_checks"]:
        problems.append("input_hold_checks differ from model")
    return problems


def judge(data, job):
    cut, drain, final = data["cutoff"], data["drain"], data["final"]
    checks = {
        "status_pass": data.get("status") == "PASS",
        "scope": data.get("scope") == SCOPE and data.get("evidence_kind") == "SCHEDULER_RTL",
        "job_matches": data.get("job") == job,
        "params_match": data.get("params") == diag.params(job),
        "positive_backlog_each_source": all(b > 0 for b in cut["producer_backlog"]),
        "positive_fifo_each_source": all(f > 0 for f in cut["fifo_occupancy"]),
        "accepted_not_fired_at_cutoff": cut["fired_total"] == 0
        and cut["accepted"] == cut["fifo_occupancy"],
        "drain_gt_10": drain["cycles"] > 10,
        "drain_within_limit": drain["cycles"] <= drain["limit"]
        and drain["limit"] == 2 * cut["pending"] + 128,
        "held_grant_fired_first": drain["released_held_grant_fired_first"] is True,
        "conservation_total": final["generated_total"] == final["accepted_total"]
        == final["fired_total"] == cut["generated_total"],
        "conservation_per_source": final["generated"] == final["accepted"] == final["fired"],
        "outstanding_zero": final["outstanding_total"] == 0
        and not any(final["producer_outstanding"]) and not any(final["fifo_outstanding"]),
        "quiescent": final["quiescent"] is True and final["quiescent_cycles"] >= 2,
        "no_window_closed": data["windows_closed"] == 0,
        "input_hold_checks_positive": data["input_hold_checks"] > 0,
    }
    return checks


def verdict(code, stable, problems, results, summary) -> str:
    """Final scope verdict: run_verify exit 0 AND summary.json ``overall`` PASS AND stable
    sources AND three per-result PASS records with no problems."""
    ok = (code == 0 and summary.get("overall") == "PASS" and stable and not problems
          and len(results) == 3 and all(r.get("status") == "PASS" for r in results))
    return "PASS" if ok else "FAIL"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--execute", action="store_true", help="run lint, pytest and cocotb")
    parser.add_argument("--jobs", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args(argv)
    rows = configs()
    if not args.execute:
        print(json.dumps(rows, indent=2))
        return 0
    lint = [dict(name=f"directed_drain_{tag(json.loads(r['env']['CXL_DRAIN_JOB']))}",
                 top=r["top"], filelist=r["filelist"], params=r["params"]) for r in rows]
    diag.rv.MILESTONES[NAME] = dict(
        description=f"{SCOPE}: N4/D16/W5M directed long-backlog drain (CGOF hw1, hw2, Main)",
        implemented=True, lint=lint,
        pytest=[dict(name="directed_drain_accounting",
                     target="scripts/test_directed_backlog_drain.py",
                     expect_tests=PYTEST_EXPECT)],
        cocotb=rows)
    before = freeze()
    run = diag.rv.Run(argparse.Namespace(
        milestone=NAME, infra_smoke=False, jobs=min(args.jobs, 2), make_jobs=1,
        keep_going=True, lint_only=False, seed_list=None, n_src_list=None,
        cocotb_timeout=None, cycles=None), ROOT)
    diag.archive_sources(run.out / "sources.zip", before)
    code = run.execute()
    after = freeze()
    stable = before == after
    results, problems = [], []
    for row in rows:
        job = json.loads(row["env"]["CXL_DRAIN_JOB"])
        base = run.out / "results" / f"cocotb_{row['name']}_seed{job['seed']}__"
        path = Path(str(base) + row["env"]["CXL_DRAIN_OUTPUT"])
        fpath = Path(str(base) + row["env"]["CXL_DRAIN_FAILURE"])
        item = dict(name=row["name"], job=job, path=path.relative_to(run.out).as_posix())
        if fpath.is_file():
            item["failure"] = json.loads(fpath.read_text())
            item["failure_path"] = fpath.relative_to(run.out).as_posix()
        if not path.is_file():
            item.update(status="FAIL", reason="result JSON missing")
            problems.append(f"{row['name']}: result missing")
            results.append(item)
            continue
        data = json.loads(path.read_text())
        checks = judge(data, job)
        model_diff = compare(data, expected(job))
        ok = all(checks.values()) and not model_diff
        item.update(status="PASS" if ok else "FAIL", checks=checks, model_prediction_diff=model_diff,
                    cutoff=data["cutoff"], drain=data["drain"], final=data["final"],
                    input_hold_checks=data["input_hold_checks"],
                    held_continuity_checks=data["held_continuity_checks"],
                    occupancy_checks=data["occupancy_checks"],
                    reset_cycles=data["reset_cycles"], nonreset_cycles=data["nonreset_cycles"],
                    untracked_initial_reset_edges=data["untracked_initial_reset_edges"],
                    windows_closed=data["windows_closed"])
        if not ok:
            problems.append(f"{row['name']}: checks/model mismatch")
        results.append(item)
    summary = json.loads((run.out / "summary.json").read_text()) if (run.out / "summary.json").is_file() else {}
    status = verdict(code, stable, problems, results, summary)
    if summary.get("overall") != "PASS":
        problems.append(f"run_verify summary overall {summary.get('overall')!r}")
    scope = dict(
        schema="cxl-directed-backlog-drain-scope-v1", scope=SCOPE, status=status,
        run_verify_exit=code, run_verify_status=summary.get("overall"),
        source_stable=stable, source_hashes=before, source_hashes_after=after,
        seed=SEED, seed_role="engineering fixture; not power seeds 509-511, "
                              "not confirmation seeds 7401-7420",
        initial_state="reset, all sources High", window=WINDOW, gen_cycles=GEN_CYCLES,
        rates=RATES, results=results, problems=problems,
        a3_historical="existing A3 drain_cycles 0/0/0/2 untouched and not used",
        limitations=("short bounded directed sequence with production W parameters; no window "
                     "closes, no trained-class evidence; no latency, fairness, classification "
                     "adaptation or power claim"),
    )
    with (run.out / "directed_drain_scope.json").open("x", encoding="utf-8") as f:
        json.dump(scope, f, indent=2)
        f.write("\n")
    print(json.dumps(dict(status=status, run_verify_exit=code, source_stable=stable,
                          problems=problems, output=str(run.out))))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
