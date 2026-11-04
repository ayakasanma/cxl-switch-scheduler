#!/usr/bin/env python3
"""Run the Main/CGOF scheduler-boundary diagnosis cases through the strict verifier.

This runner adds only the traffic/collector layer around the existing
``test_cgof_sched.Harness``.  It does not alter the sealed revision gates and
does not claim memory-system or application measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_verify as rv  # noqa: E402

NAME = "cgof-rtl-diagnosis"
TOP = "cgof_unit_top"
FILELIST = "rtl/experimental/filelist_cgof_unit.f"
TEST_MODULE = "test_cgof_diagnosis"
TEST_NAME = "cgof_diagnosis_rtl"
RESULT_SUFFIX = ".json"
ORDERING_CODE = {"oldest-first": 0, "eligible-round-robin": 1}
ORDERING_TAG = {"oldest-first": "rr0", "eligible-round-robin": "rr1"}


def row(window: int, high_weight: int, depth: int = 16,
        ordering: str = "oldest-first") -> dict:
    if ordering not in ORDERING_CODE:
        raise ValueError(f"unsupported ordering {ordering!r}")
    return dict(
        N_SRC=4,
        DEPTH=depth,
        FAI_W=window,
        HIGH_WEIGHT=high_weight,
        ELIGIBLE_RR=ORDERING_CODE[ordering],
    )


def params(job: dict) -> dict:
    if job.get("policy") == "FAI-inspired":
        return dict(N_SRC=job["n_src"], POLICY=2, DEPTH=job["depth"],
                    RR_QUANTUM=10, FAI_W=job["window"], HIGH_QUOTA=10, MAIN_1W=0)
    return row(
        job["window"],
        job["high_weight"],
        job["depth"],
        job.get("ordering", "oldest-first"),
    )


def job_id(job: dict) -> str:
    ordering = job.get("ordering", "oldest-first")
    if ordering not in ORDERING_TAG:
        raise ValueError(f"unsupported ordering {ordering!r}")
    policy_tag = "main" if job.get("policy") == "FAI-inspired" else f"hw{job['high_weight']}"
    return (f"{job['mode']}-{job['lane']}-w{job['window']}-d{job['depth']}"
            f"-{policy_tag}-{ORDERING_TAG[ordering]}")


def output_name(job: dict) -> str:
    return f"cgof_diagnosis_{job_id(job)}{RESULT_SUFFIX}"


def make_job(mode: str, lane: str, seed: int, window: int, high_weight: int,
             windows: int, heavy_work: int | None, profile: str | None,
             max_active_cycles: int | None, depth: int = 16,
             heavy_sources=None, ready_pattern="bernoulli", ready_period=100,
             ordering="oldest-first") -> dict:
    if ordering not in ORDERING_CODE:
        raise ValueError(f"unsupported ordering {ordering!r}")
    job = dict(
        mode=mode,
        lane=lane,
        seed=seed,
        n_src=4,
        depth=depth,
        window=window,
        high_weight=high_weight,
        windows=windows,
        heavy_work=heavy_work,
        profile=profile,
        heavy_sources=heavy_sources,
        ready_pattern=ready_pattern,
        ready_period=ready_period,
        ordering=ordering,
    )
    if max_active_cycles is not None:
        job["max_active_cycles"] = max_active_cycles
    return job


def config(job: dict) -> dict:
    output = output_name(job)
    main = job.get("policy") == "FAI-inspired"
    return dict(
        name=f"{job_id(job)}-seed{job['seed']}",
        top="switch_experiment_top" if main else TOP,
        filelist="rtl/experimental/filelist.f" if main else FILELIST,
        params=params(job),
        default_params={},
        test_dir="sim/experimental",
        test_module="test_main_diagnosis" if main else TEST_MODULE,
        seeds=[job["seed"]],
        expect_tests=1,
        timeout_s=172800,
        env={
            "CXL_DIAGNOSIS_JOB": json.dumps(job, sort_keys=True),
            "CXL_DIAGNOSIS_OUTPUT": output,
            "CXL_DIAGNOSIS_FAILURE": output.replace(".json", "_failure.json"),
            "COCOTB_TEST_FILTER": rf"(^|\.){'main_diagnosis_rtl' if main else TEST_NAME}$",
        },
        artifacts=[
            dict(file=output, required=True),
            dict(file=output.replace(".json", "_failure.json"), required=False),
        ],
    )


def configs(args) -> list[dict]:
    weights = (0, 1, 2) if args.policy == "all" else (0,) if args.policy == "main" else (1, 2) if args.policy == "both" else (
        (1,) if args.policy == "1:1" else (2,)
    )
    orderings = (
        ("oldest-first", "eligible-round-robin")
        if args.ordering == "both" else (args.ordering,)
    )
    rows = []
    for weight in weights:
        for ordering in orderings:
            if args.mode in ("common-demand", "both"):
                rows.append(make_job(
                    "common-demand", "mixed", args.seed, args.window, weight,
                    args.windows, args.windows * args.window, None, None,
                    depth=args.depth, ordering=ordering,
                ))
            if args.mode in ("finite-heavy", "both"):
                for lane in ("mixed", "isolated"):
                    rows.append(make_job(
                        "finite-heavy", lane, args.seed, args.window, weight,
                        args.windows, args.heavy_work, args.profile,
                        args.max_active_cycles,
                        depth=args.depth, heavy_sources=args.heavy_sources,
                        ready_pattern=args.ready_pattern, ready_period=args.ready_period,
                        ordering=ordering,
                    ))
    for job in rows:
        if job["high_weight"] == 0:
            job.update(policy="FAI-inspired", high_weight=None)
    return [config(job) for job in rows]


def source_paths() -> list[str]:
    paths = {
        "scripts/run_rtl_diagnosis.py",
        "scripts/run_verify.py",
        "scripts/run_verify.sh",
        "scripts/wsl_env.sh",
        "scripts/run_dynamic_role_switch_a2.py",
        "scripts/compare_diagnosis_results.py",
        "scripts/analyze_dynamic_role_switch.py",
        "scripts/run_dynamic_role_switch_pilot.py",
        "scripts/run_dynamic_role_switch_a3.py",
        f"sim/experimental/{TEST_MODULE}.py",
        "sim/experimental/cgof_diagnosis_traffic.py",
        "sim/experimental/cgof_diagnosis_accounting.py",
        "sim/experimental/cgof_diagnosis_model.py",
        "sim/experimental/diagnosis_source_book.py",
        "sim/experimental/test_diagnosis_source_book.py",
        "sim/experimental/test_main_diagnosis.py",
        "sim/experimental/test_experiment_top.py",
        "sim/experimental/test_cgof_diagnosis_traffic.py",
        "sim/experimental/test_cgof_sched.py",
        "sim/experimental/revision_traffic.py",
        "sim/performance/hog_sparse.py",
        "sim/performance/followup.py",
        "sim/switch_top_fai/fai_stream.py",
        "sim/common/hier_util.py",
        "scripts/revision_statistics.py",
        FILELIST,
    }
    for filelist in (FILELIST, "rtl/experimental/filelist.f"):
        paths.add(filelist)
        for line in (ROOT / filelist).read_text().splitlines():
            line = line.strip()
            if line.endswith(".sv"):
                paths.add(line)
    paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "refc/cxl_model").glob("*.py"))
    return sorted(paths)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_sources() -> dict:
    return {name: sha(ROOT / name) for name in source_paths()}


def archive_sources(path: Path, hashes: dict) -> None:
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, digest in hashes.items():
            data = (ROOT / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest
            archive.writestr(name, data)


def load_results(directory: Path, rows: list[dict]) -> list[dict]:
    result_dir = directory / "results"
    results = []
    for row in rows:
        job = json.loads(row["env"]["CXL_DIAGNOSIS_JOB"])
        name = f"cocotb_{row['name']}_seed{job['seed']}__{output_name(job)}"
        path = result_dir / name
        if not path.is_file():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text())
        if data.get("status") != "PASS" or data.get("evidence_kind") != "SCHEDULER_RTL":
            raise ValueError(f"{path} is not a passing scheduler-RTL result")
        if data.get("job") != job:
            raise ValueError(f"{path} result job differs from its configured job")
        if data.get("params") != params(job):
            raise ValueError(f"{path} result parameters differ from the ordering build")
        results.append(dict(job=job, path=path.relative_to(directory).as_posix(), data=data))
    return results


def paired_results(results: list[dict]) -> list[dict]:
    grouped = {}
    for item in results:
        job = item["job"]
        if job["mode"] != "finite-heavy":
            continue
        key = (
            job["seed"],
            job["window"],
            0 if job.get("policy") == "FAI-inspired" else job["high_weight"],
            job["depth"],
            job["ordering"],
            job["heavy_work"],
            job["profile"],
            job.get("max_active_cycles"),
            tuple(job.get("heavy_sources") or [0]),
            job.get("ready_pattern", "bernoulli"),
            job.get("ready_period", 100),
        )
        lanes = grouped.setdefault(key, {})
        if job["lane"] in lanes:
            raise ValueError(f"duplicate finite-Heavy lane for {key}")
        lanes[job["lane"]] = item
    pairs = []
    for key, lanes in sorted(grouped.items()):
        if set(lanes) != {"mixed", "isolated"}:
            raise ValueError(f"incomplete finite-Heavy pair for {key}")
        mixed, isolated = lanes["mixed"], lanes["isolated"]
        pairs.append({
            "seed": key[0],
            "window": key[1],
            "high_weight": mixed["job"]["high_weight"],
            **({"policy": "FAI-inspired"} if mixed["job"].get("policy") == "FAI-inspired" else {}),
            "depth": key[3],
            "ordering": key[4],
            "heavy_work": key[5],
            "profile": key[6],
            "max_active_cycles": key[7],
            "heavy_sources": list(key[8]),
            "ready_pattern": key[9],
            "ready_period": key[10],
            "mixed_active_cycles": mixed["data"]["active_cycles"],
            "isolated_active_cycles": isolated["data"]["active_cycles"],
            "heavy_active_cycle_ratio_mixed_over_isolated": (
                mixed["data"]["active_cycles"] / isolated["data"]["active_cycles"]
            ),
            # Deprecated: this is an active-cycle ratio, not a fired/generated ratio.
            "completion_ratio_mixed_over_isolated": (
                mixed["data"]["active_cycles"] / isolated["data"]["active_cycles"]
            ),
            "mixed_heavy_fired": mixed["data"]["heavy"]["fired"],
            "isolated_heavy_fired": isolated["data"]["heavy"]["fired"],
        })
    return pairs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="run the bounded W256 smoke")
    parser.add_argument("--production-reviewed", action="store_true",
                        help="explicitly approve a W5M production run")
    parser.add_argument("--mode", choices=("common-demand", "finite-heavy", "both"),
                        default="both")
    parser.add_argument("--policy", choices=("1:1", "2:1", "both", "main", "all"), default="both")
    parser.add_argument("--ordering",
                        choices=("oldest-first", "eligible-round-robin", "both"),
                        default="oldest-first")
    parser.add_argument("--seed", type=int, default=6201)
    parser.add_argument("--window", type=int, default=256)
    parser.add_argument("--windows", type=int, default=1)
    parser.add_argument("--depth", type=int, choices=(8, 16, 32), default=16)
    parser.add_argument("--heavy-sources", type=int, nargs="+",
                        help="Heavy physical source per generation window; last entry repeats")
    parser.add_argument("--ready-pattern", choices=("bernoulli", "spread", "bursty"),
                        default="bernoulli")
    parser.add_argument("--ready-period", type=int, default=100)
    parser.add_argument("--heavy-work", type=int, default=256)
    parser.add_argument("--profile", choices=("under", "near", "over"), default="near")
    parser.add_argument("--max-active-cycles", type=int)
    parser.add_argument("--jobs", type=int, choices=(1, 2), default=1)
    parser.add_argument("--make-jobs", type=int, choices=(1, 2), default=1)
    args = parser.parse_args(argv)

    if args.smoke == args.production_reviewed:
        parser.error("choose exactly one of --smoke or --production-reviewed")
    if args.smoke and args.window not in (64, 256):
        parser.error("smoke runs must use --window 64 or 256")
    if args.policy in ("main", "all") and args.ordering != "oldest-first":
        parser.error("Main uses class-quota oldest-first ordering")
    if args.production_reviewed and args.window != 5_000_000:
        parser.error("production runs must use --window 5000000")
    if args.windows < 1 or args.heavy_work < 1:
        parser.error("windows and heavy-work must be positive")
    if (args.heavy_sources is not None
            and any(not 0 <= source < 4 for source in args.heavy_sources)):
        parser.error("heavy sources must be in 0..3")
    if args.ready_period < 1:
        parser.error("ready period must be positive")

    rows = configs(args)
    if not rows:
        parser.error("no cases selected")
    test_count = len(re.findall(r"^    def test_\w+\(self\)", (
        ROOT / "sim/experimental/test_cgof_diagnosis_traffic.py"
    ).read_text(), re.M))
    rv.MILESTONES[NAME] = dict(
        description="CGOF scheduler-boundary fairness and finite-Heavy diagnosis",
        implemented=True,
        lint=[dict(name=(f"diagnosis_{row['params']['FAI_W']}_d{row['params']['DEPTH']}"
                         f"_hw{row['params'].get('HIGH_WEIGHT', 'main')}"
                         f"_rr{row['params'].get('ELIGIBLE_RR', 0)}"),
                   top=row["top"], filelist=row["filelist"], params=row["params"])
              for row in {json.dumps(row["params"], sort_keys=True): row
                          for row in rows}.values()],
        pytest=[dict(name="cgof_diagnosis_traffic", target=(
            "sim/experimental/test_cgof_diagnosis_traffic.py"), expect_tests=test_count)],
        cocotb=rows,
    )
    before = freeze_sources()
    run = rv.Run(argparse.Namespace(
        milestone=NAME, infra_smoke=False, jobs=args.jobs, make_jobs=args.make_jobs,
        keep_going=True, lint_only=False, seed_list=None, n_src_list=None,
        cocotb_timeout=None, cycles=None,
    ), ROOT)
    directory = run.out
    archive_sources(directory / "sources.zip", before)
    code = run.execute()
    after = freeze_sources()
    stable = before == after
    results = load_results(directory, rows)
    pairs = paired_results(results)
    scope = dict(
        schema="cxl-cgof-rtl-diagnosis-scope-v1",
        evidence_kind="SCHEDULER_RTL",
        status="PASS" if code == 0 and stable and len(results) == len(rows) else "FAIL",
        smoke=args.smoke,
        production_reviewed=args.production_reviewed,
        source_hashes=before,
        source_hashes_after=after,
        source_stable=stable,
        configs=rows,
        results=results,
        finite_heavy_pairs=pairs,
        limitations=(
            "scheduler-boundary evidence only; no completed memory bytes, "
            "CXL issue-to-response latency, application slowdown, or calibrated system"
        ),
    )
    (directory / "diagnosis_scope.json").write_text(json.dumps(scope, indent=2) + "\n")
    print(json.dumps({
        "output": str(directory),
        "status": scope["status"],
        "runs": len(results),
        "pairs": len(pairs),
        "source_stable": stable,
    }, sort_keys=True))
    return 0 if scope["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

