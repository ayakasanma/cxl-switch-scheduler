#!/usr/bin/env python3
"""Execute an explicit revision subset through run_verify; never run the 498-row plan by default."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import zipfile

import run_verify as rv
from revision_matrix import EXPLORATION, canonical_sha, matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim/experimental"))
from revision_traffic import STAGES, Traffic
from revision_statistics import histogram_summary

POLICY = dict(FCFS=0, RR=1, RR1=1, RR10=1, MAIN=2, MAIN1W=2, ALG2=3, BLISS=4)
FILELIST = "rtl/experimental/filelist.f"
BASE = ROOT / "artifacts/implementation/revision-performance"


def parameters(job):
    return dict(N_SRC=job["n_src"], POLICY=POLICY[job["policy"]], DEPTH=job["depth"],
                RR_QUANTUM=job["rr_quantum"], FAI_W=job["window"],
                HIGH_QUOTA=job["high_quota"], MAIN_1W=int(job["policy"] == "MAIN1W"))


def select_jobs(group, seeds, pilot=False, policies=None, n_src=None):
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("explicit unique seeds required")
    if pilot:
        if len(seeds) != 1 or seeds[0] not in EXPLORATION:
            raise ValueError("pilot requires exactly one exploration seed 509..513")
        rows = [dict(r, window=256, training_cycles=512, seed=seeds[0],
                     seed_role="exploration", group="pilot", n_src=n_src or 4)
                for r in matrix() if r["group"] == "n4-confirmation" and r["seed"] == 529]
        for row in rows:
            row["id"] = f"pilot-{row['policy']}-n{row['n_src']}-s{row['seed']}-w256"
    else:
        groups = {r["group"] for r in matrix()}
        if group not in groups:
            raise ValueError(f"unknown group {group!r}")
        rows = [r for r in matrix() if r["group"] == group and r["seed"] in seeds]
        if not rows or set(seeds) != {r["seed"] for r in rows}:
            raise ValueError("requested seeds are missing from the planned group")
        if any(r.get("conditional") or r["evidence_kind"] != "RTL_REQUIRED" for r in rows):
            raise ValueError("conditional insight/power jobs require their own reviewed runner")
        if n_src is not None:
            rows = [r for r in rows if r["n_src"] == n_src]
            if set(seeds) != {r["seed"] for r in rows}:
                raise ValueError("requested N/seed is missing from the planned group")
    if policies:
        if set(policies) - {r["policy"] for r in rows}:
            raise ValueError("requested policy missing from selected group")
        rows = [r for r in rows if r["policy"] in policies]
    if not rows:
        raise ValueError("empty selection")
    return rows


def config(job, cold=False):
    params = parameters(job)
    if cold is not False and cold not in ("A", "B"):
        raise ValueError("cold replay must select independent A or B")
    if cold:
        if job["group"] == "adaptation":
            raise ValueError("adaptation is measured continuously, not cold replay")
    name = job["id"] + (f"-cold{cold}" if cold else "-trained")
    return dict(name=name, top="switch_experiment_top", filelist=FILELIST,
                params=params, default_params={}, test_dir="sim/experimental",
                test_module="test_revision_performance", seeds=[job["seed"]],
                env=dict(CXL_REVISION_JOB=json.dumps(job, sort_keys=True),
                         CXL_REVISION_PARAMS=json.dumps(params, sort_keys=True),
                         CXL_REVISION_COLD=json.dumps(cold)),
                expect_tests=1, timeout_s=172800,
                artifacts=[dict(file="revision_performance.json", required=True),
                           dict(file="revision_failure.json", required=False)])


def source_paths(root=ROOT):
    """All imported Python modules plus the exact RTL filelist and source dependencies."""
    root = Path(root)
    paths = {FILELIST, "specs/CXL_SPEC.md", "specs/APPROVAL.md", "specs/DECISIONS.md",
             "AGENTS.md",
             "scripts/run_verify.py", "scripts/revision_matrix.py", "scripts/revision_statistics.py",
             "scripts/wsl_env.sh", "scripts/run_revision_experiments.py",
             "scripts/test_revision_experiments.py", "sim/experimental/revision_traffic.py",
             "sim/experimental/test_revision_traffic.py", "sim/experimental/test_revision_performance.py",
             "sim/experimental/test_baseline_models.py", "sim/experimental/test_experiment_top.py",
             "sim/experimental/Makefile", "sim/performance/hog_sparse.py", "sim/performance/followup.py",
             "sim/switch_top_fai/fai_stream.py", "sim/common/traffic_trace.py",
             "sim/common/hier_util.py"}
    for line in (root / FILELIST).read_text().splitlines():
        line = line.split("//", 1)[0].strip()
        if line:
            if not line.endswith(".sv") or line.startswith(("/", "-")) or ".." in Path(line).parts:
                raise ValueError(f"unrecognized filelist entry {line!r}")
            paths.add(line)
    # Explicit import closure keeps isolated experimental writers outside this freeze.
    paths.update(f"refc/cxl_model/{name}.py" for name in (
        "__init__", "common_ctrl_model", "fifo_model", "fcfs_model", "rr_model",
        "fai_main_model", "fai_alg2_model", "revision_baselines"))
    return sorted(paths)


def hash_sources(paths, root=ROOT):
    return {name: hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() for name in paths}


def freeze_sources(output, paths, root=ROOT):
    """Archive the bytes being hashed; fail closed if a writer changes any dependency."""
    hashes = {}
    with zipfile.ZipFile(Path(output) / "sources.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name in paths:
            data = (Path(root) / name).read_bytes()
            hashes[name] = hashlib.sha256(data).hexdigest()
            archive.writestr(name, data)
        context = Path(root) / "docs/experiments/revision-20261023/EXECUTION.md"
        if context.is_file():
            archive.writestr("context/EXECUTION.md", context.read_bytes())
    if hashes != hash_sources(paths, root):
        raise ValueError("source writer changed files during freeze")
    (Path(output) / "source_hashes_before.json").write_text(json.dumps(hashes, indent=2)+"\n")
    return hashes


def check_steps(configs, steps):
    expected = {f"cocotb:{c['name']}_seed{s}" for c in configs for s in c["seeds"]}
    actual = [s["name"] for s in steps if s["kind"] == "cocotb"]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("missing, unexpected or duplicate simulation jobs")
    expected_lint = {f"lint:{c['name']}" for c in configs}
    actual_lint = [s["name"] for s in steps if s["kind"] == "lint"]
    if len(actual_lint) != len(set(actual_lint)) or set(actual_lint) != expected_lint:
        raise ValueError("missing, unexpected or duplicate lint jobs")
    for s in steps:
        if s["status"] != "PASS":
            raise ValueError(f"{s['name']}: {s['status']}")
        if s["kind"] in ("lint", "pytest", "cocotb"):
            if not s.get("exit_codes") or any(v != 0 for v in s["exit_codes"].values()):
                raise ValueError(f"{s['name']}: missing/nonzero tool exits")
        if s["kind"] in ("pytest", "cocotb"):
            if s.get("tests", 0) < 1 or any(s.get(k, 0) for k in ("failures", "errors", "skipped")):
                raise ValueError("empty/failed/skipped tests")
    if not any(s["kind"] == "pytest" for s in steps):
        raise ValueError("missing unit checks")


def validate_result(data, job, cold, replay):
    for key, value in dict(schema="cxl-revision-performance-v1", evidence_kind="RTL", status="PASS", job=job,
                           params=parameters(job), cold=bool(cold), cold_cohort=cold or None,
                           trace_sha256=replay.sha256,
                           trace_config=replay.config, generated_per_source=replay.generated,
                           ready_cycles=replay.ready_count, active_cycles=replay.end,
                           training_cycles=replay.training, outstanding_after_drain=0,
                           producer_backlog_after_drain=0, sparse_guard_complete=True,
                           production_evidence=job["window"] == 5_000_000,
                           sensitivity_evidence=job["window"] == 256).items():
        if data.get(key) != value:
            raise ValueError(f"incorrect result field {key}")
    if not 0 < data["drain_cycles"] <= data["drain_bound"]:
        raise ValueError("invalid final drain")
    if data["real_non_reset_cycles"] != replay.end + data["drain_cycles"]:
        raise ValueError("skipped actual simulation edges")
    phases, cohorts = data["metrics"]["phases"], data["metrics"]["cohorts"]
    if set(phases) != set(replay.phases) or set(cohorts) != set(replay.cohorts):
        raise ValueError("missing phases/cohorts")
    totals = [sum(sum(row[key]) for row in phases.values()) for key in ("generated", "accepted", "fired")]
    if not totals[0] == totals[1] == totals[2] == data["generated"] == data["accepted"] == data["fired"]:
        raise ValueError("generated population not conserved")
    if sum(r["cycles"] for r in phases.values()) != data["real_non_reset_cycles"]:
        raise ValueError("missing measured cycles")
    edges = (0, *replay.bounds)
    expected_cycles = [b-a for a, b in zip(edges, edges[1:])] + [data["drain_cycles"]]
    if [phases[p]["cycles"] for p in replay.phases] != expected_cycles:
        raise ValueError("incorrect phase lengths")
    if [sum(r["generated"][h] for r in phases.values()) for h in range(replay.n)] != replay.generated:
        raise ValueError("trace population differs")
    generated, accepted, fired = ([0]*replay.n for _ in range(3))
    for phase in replay.phases:
        row = phases[phase]
        cycles, ready = row["cycles"], row["ready"]
        eligible = row["eligible_ready_opportunities"]
        fires = sum(row["fired"])
        if not 0 <= fires <= eligible <= ready <= cycles:
            raise ValueError("incorrect joint eligible-ready opportunities")
        if row["avoidable_bubbles"] != eligible-fires or row["avoidable_bubbles"]:
            raise ValueError("avoidable eligible-ready bubbles")
        if row["eligible_ready_utilization"] != (fires/eligible if eligible else None):
            raise ValueError("incorrect eligible-ready utilization")
        for key in ("generated", "offered", "accepted", "fired"):
            if len(row[key]) != replay.n or any(type(v) is not int or v < 0 for v in row[key]):
                raise ValueError("invalid per-source accounting")
        for h in range(replay.n):
            if not row["accepted"][h] <= row["offered"][h] <= cycles:
                raise ValueError("incorrect offered/accepted accounting")
            generated[h] += row["generated"][h]
            accepted[h] += row["accepted"][h]
            fired[h] += row["fired"][h]
            if not fired[h] <= accepted[h] <= generated[h]:
                raise ValueError("per-source population not conserved")
            for key in ("backlog", "occupancy"):
                if len(row[key]) != replay.n or row[key][h]["count"] != cycles:
                    raise ValueError("missing backlog/occupancy samples")
    if not generated == accepted == fired:
        raise ValueError("per-source population not drained")
    for cohort, cr in cohorts.items():
        if cr["generated"] != cr["completed"]:
            raise ValueError("incomplete cohort")
        if [sum(v[h] for v in cr["completed_by_phase"].values()) for h in range(replay.n)] != cr["completed"]:
            raise ValueError("incorrect completion phase counts")
        for h, row in enumerate(cr["per_source"]):
            if any(row[s]["count"] != cr["completed"][h] for s in STAGES):
                raise ValueError("latency sample count mismatch")
        for row in cr["per_source"] + [cr["pooled_sparse"]]:
            for stage in STAGES:
                r = row[stage]
                expected = (histogram_summary(r["histogram"]) if r["histogram"] else
                            dict(count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None))
                if {k: v for k, v in r.items() if k != "histogram"} != expected:
                    raise ValueError("incorrect direct histogram statistics")
        heavy = (3 if cohort == "role3" else 0 if cohort in ("role0", "role0-return")
                 else job["heavy_source"])
        for stage in STAGES:
            combined = Counter()
            for h, row in enumerate(cr["per_source"]):
                if h != heavy:
                    combined.update({int(k): v for k, v in row[stage]["histogram"].items()})
            if dict(combined) != {int(k): v for k, v in cr["pooled_sparse"][stage]["histogram"].items()}:
                raise ValueError("incorrect sparse pooling")
    windows = data["windows"]
    if len(windows) != data["real_non_reset_cycles"] // job["window"]:
        raise ValueError("missing actual window closes")
    for i, row in enumerate(windows):
        if row["closing_cycle"] != (i+1)*job["window"]-1 or row["total"] != sum(row["counts"]):
            raise ValueError("incorrect closing-edge accounting")
        total, n = row["total"], job["n_src"]
        expected = ["S0" if not total else "UP" if 10*n*b < 3*total else
                    "DOWN" if n*b > total else "KEEP" for b in row["counts"]]
        if row["evidence"] != expected:
            raise ValueError("incorrect widened classification evidence")
    return data


def available_kib():
    path = Path("/proc/meminfo")
    if path.exists():
        return int(next(s.split()[1] for s in path.read_text().splitlines() if s.startswith("MemAvailable:")))
    return None


def archive_evidence(output):
    """Bundle source bytes, exact commands/config, raw checks and retained failures."""
    paths = [p for p in output.rglob("*") if p.is_file() and
             "build" not in p.relative_to(output).parts and p.name != "evidence.zip"]
    with zipfile.ZipFile(output / "evidence.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, path.relative_to(output).as_posix())


class RevisionRun(rv.Run):
    def __init__(self, args, configs):
        self.args, self.repo, self.milestone = args, ROOT, "revision-performance"
        self.entry = dict(description="Explicit frozen revision RTL subset", implemented=True,
                          lint=[{k: c[k] for k in ("name", "top", "filelist", "params")} for c in configs],
                          cocotb=configs, pytest=[
                              dict(name="revision_traffic", target="sim/experimental/test_revision_traffic.py", min_tests=1),
                              dict(name="revision_runner", target="scripts/test_revision_experiments.py", min_tests=1),
                              dict(name="native_baselines", target="sim/experimental/test_baseline_models.py", min_tests=1)])
        self.run_id = args.output.name
        self.milestone_dir, self.out = BASE, args.output
        self.out.mkdir(parents=True, exist_ok=False)
        for name in ("logs", "junit"):
            (self.out / name).mkdir()
        build_root = Path(os.environ.get("CXL_BUILD_ROOT") or "~/.cache/cxl-scheduler/build").expanduser()
        self.build_root = build_root / self.milestone / self.run_id
        self.steps, self.lock, self.abort = [], threading.Lock(), threading.Event()
        self.t0, self.smoke, self.seeds_override, self.n_filter = time.time(), False, None, None
        self.configs = configs
        self.memory_kib = available_kib()
        self.minimum_available_kib = self.memory_kib
        self.memory_samples = 0

    def write_summary(self, final):
        overall = super().write_summary(final)
        path = self.out / "summary.json"
        summary = json.loads(path.read_text())
        gate = any(s["kind"] == "scope" and s["status"] == "PASS" for s in self.steps)
        summary.update(scope="W256-sensitivity" if self.args.pilot else "selected-production-subset",
                       sensitivity_evidence=self.args.pilot and gate and overall == "PASS",
                       production_evidence=not self.args.pilot and gate and overall == "PASS",
                       milestone_acceptance_scope=gate and overall == "PASS",
                       full_498_matrix_executed=False, expected_jobs=len(self.configs))
        path.write_text(json.dumps(summary, indent=2)+"\n")
        return overall

    def execute(self):
        problems, accepted = [], []
        paths = []
        stop_memory = threading.Event()
        def sample_memory():
            while not stop_memory.wait(.25):
                current = available_kib()
                if current is not None and self.minimum_available_kib is not None:
                    self.minimum_available_kib = min(self.minimum_available_kib, current)
                    self.memory_samples += 1
        monitor = threading.Thread(target=sample_memory, daemon=True)
        try:
            paths = source_paths()
            before = freeze_sources(self.out, paths)
            spec = dict(schema="cxl-revision-run-spec-v1", configs=self.configs,
                        jobs_sha256=canonical_sha(self.configs), source_sha256=canonical_sha(before),
                        command=sys.argv, pilot=self.args.pilot, available_memory_kib=self.memory_kib,
                        max_memory_fraction=.70, jobs=self.args.jobs, make_jobs=self.args.make_jobs,
                        production_review_acknowledged=self.args.production_reviewed)
            (self.out / "frozen-spec.json").write_text(json.dumps(spec, indent=2)+"\n")
            if not self.args.pilot:
                pilot = json.loads((self.args.reviewed_pilot / "revision_scope.json").read_text())
                if not pilot.get("sensitivity_evidence") or pilot["source_hashes"] != before:
                    raise ValueError("reviewed pilot is failed, incomplete or from different source bytes")
                if max(r["n_src"] for r in pilot["runs"]) < max(c["params"]["N_SRC"] for c in self.configs):
                    raise ValueError("production N requires a reviewed resource pilot at least that large")
            monitor.start()
            rc = super().execute()
            if rc:
                problems.append(f"strict runner exit {rc}")
            check_steps(self.configs, self.steps)
            replays, pairings = {}, {}
            for cfg in self.configs:
                job = json.loads(cfg["env"]["CXL_REVISION_JOB"])
                cold = json.loads(cfg["env"]["CXL_REVISION_COLD"])
                t = Traffic(job, cold=cold)
                key = canonical_sha(t.config)
                if key not in replays:
                    for k in range(t.end):
                        t.step(k)
                    replays[key] = t
                t = replays[key]
                name = f"{cfg['name']}_seed{job['seed']}"
                result_path = self.out / "results" / f"cocotb_{name}__revision_performance.json"
                data = validate_result(json.loads(result_path.read_text()), job, cold, t)
                accepted.append(dict(name=name, trace_sha256=t.sha256, result=str(result_path.relative_to(self.out)),
                                     n_src=job["n_src"], policy=job["policy"],
                                     producer_peak_backlog=data["producer_peak_backlog"],
                                     peak_rss_kib=data["peak_rss_kib"]))
                pairings.setdefault(key, []).append(dict(policy=job["policy"], trace_sha256=t.sha256,
                                                         training_pin_sha256=data["training_pin_sha256"]))
            (self.out / "trace-pairings.json").write_text(json.dumps(pairings, indent=2)+"\n")
            for rows in pairings.values():
                default = {r["policy"]: r for r in rows if r["policy"] in ("FCFS", "MAIN")}
                if set(default) == {"FCFS", "MAIN"}:
                    if len({r["training_pin_sha256"] for r in default.values()}) != 1:
                        raise ValueError("FCFS/Main pre-demotion training pins differ")
            peaks = sorted((r["peak_rss_kib"] for r in accepted if r["peak_rss_kib"]), reverse=True)
            if self.memory_kib is None or len(peaks) != len(accepted):
                raise ValueError("pilot resource measurement unavailable")
            if sum(peaks[:self.args.jobs]) > .70*self.memory_kib:
                raise ValueError("pilot exceeds 70% of starting available memory")
        except (AssertionError, OSError, ValueError, KeyError, StopIteration) as exc:
            problems.append(f"{type(exc).__name__}: {exc}")
        finally:
            stop_memory.set()
            if monitor.ident is not None:
                monitor.join()
        if self.memory_kib is not None and self.minimum_available_kib is not None:
            if self.memory_kib-self.minimum_available_kib > .70*self.memory_kib:
                problems.append("measured system memory growth exceeds 70% of starting available memory")
        try:
            after = hash_sources(paths)
            (self.out / "source_hashes_after.json").write_text(json.dumps(after, indent=2)+"\n")
            if "before" not in locals() or before != after:
                problems.append("frozen source bytes changed during run")
        except OSError as exc:
            problems.append(f"source recheck failed: {exc}")
        passed = not problems and len(accepted) == len(self.configs)
        if len(accepted) != len(self.configs):
            problems.append(f"valid results {len(accepted)} of expected {len(self.configs)}")
        gate = dict(schema="cxl-revision-performance-scope-v1", status="PASS" if passed else "FAIL",
                    sensitivity_evidence=self.args.pilot and passed,
                    production_evidence=not self.args.pilot and passed,
                    expected_jobs=len(self.configs), valid_jobs=len(accepted), problems=problems,
                    runs=accepted, source_hashes=locals().get("before", {}),
                    available_memory_kib=self.memory_kib, max_memory_fraction=.70,
                    minimum_available_memory_kib=self.minimum_available_kib,
                    system_memory_growth_peak_kib=(self.memory_kib-self.minimum_available_kib
                                                  if self.memory_kib is not None else None),
                    memory_samples=self.memory_samples, memory_sample_period_s=.25)
        (self.out / "revision_scope.json").write_text(json.dumps(gate, indent=2)+"\n")
        self.add_step(dict(order=len(self.steps)+1, kind="scope", name="scope:revision-performance",
                           status=gate["status"], reason="; ".join(problems), log="revision_scope.json"))
        overall = self.write_summary(final=True)
        archive_evidence(self.out)
        self.print_table(overall)
        return 0 if passed else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true", help="six N4 policies, W256 sensitivity only")
    mode.add_argument("--group", help="one planned group; explicit --seed required")
    p.add_argument("--seed", required=True, help="explicit seed or comma/range as in run_verify")
    p.add_argument("--policy", help="optional comma-separated policy subset")
    p.add_argument("--n-src", type=int, choices=(4, 8, 16), help="explicit N subset; pilot defaults to N4")
    p.add_argument("--cold", choices=("A", "B"), default=False,
                   help="independent reset-start cold A or cold B with corresponding exact arrivals")
    p.add_argument("--output", type=Path, required=True, help="fresh directory under revision-performance")
    p.add_argument("--source-ready", action="store_true", help="native source writer has finished and released the freeze")
    p.add_argument("--production-reviewed", action="store_true", help="parent reviewed and authorized production")
    p.add_argument("--reviewed-pilot", type=Path, help="accepted W256 pilot with identical source bytes")
    p.add_argument("-j", "--jobs", type=int, default=3)
    p.add_argument("--make-jobs", type=int, default=2)
    args = p.parse_args(argv)
    try:
        if not args.source_ready:
            raise ValueError("native source freeze is required (--source-ready)")
        if not args.pilot and (not args.production_reviewed or not args.reviewed_pilot):
            raise ValueError("parent production review and accepted --reviewed-pilot are required")
        if not 1 <= args.jobs <= 3 or args.make_jobs != 2:
            raise ValueError("start with 1..3 simulations and exactly two build jobs")
        args.output = args.output.resolve()
        if not args.output.is_relative_to(BASE.resolve()) or args.output == BASE.resolve():
            raise ValueError("output must be a fresh child of artifacts/implementation/revision-performance")
        if args.output.exists():
            raise ValueError("refusing duplicate output directory")
        rows = select_jobs(args.group, rv.parse_seeds(args.seed), args.pilot,
                           args.policy.split(",") if args.policy else None, args.n_src)
        configs = [config(r, args.cold) for r in rows]
        args.lint_only, args.keep_going, args.cocotb_timeout, args.cycles = False, True, None, None
        return RevisionRun(args, configs).execute()
    except (ValueError, OSError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
