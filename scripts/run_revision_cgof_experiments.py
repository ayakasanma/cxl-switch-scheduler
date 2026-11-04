#!/usr/bin/env python3
"""Explicit CGOF(2:1) conditional RTL performance; CGOF(1:1) is a separate ablation."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
import zipfile

import run_revision_experiments as common
import run_revision_cgof as native
import screen_scheduler_insights as screen

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/implementation/revision-cgof-performance"
FILELIST = "rtl/experimental/filelist_cgof_unit.f"
SCHEMA = "cxl-revision-cgof-performance-v1"
GROUPS = ("insight-confirmation", "insight-robustness")
rv = common.rv


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def select_jobs(group, seeds, pilot=False):
    require(bool(seeds) and len(seeds) == len(set(seeds)), "explicit unique seeds required")
    if pilot:
        require(group is None and len(seeds) == 1 and seeds[0] in range(509, 514),
                "pilot requires one exploration seed 509..513 and no production group")
        template = next(r for r in common.matrix() if r["group"] == "insight-confirmation")
        return [dict(template, id=f"cgof-pilot-s{seeds[0]}-w256", group="cgof-pilot",
                     seed=seeds[0], seed_role="exploration", window=256, training_cycles=512)]
    require(group in GROUPS, "only the two approved conditional groups are supported")
    rows = [r for r in common.matrix() if r["group"] == group and r["seed"] in seeds]
    require(bool(rows) and {r["seed"] for r in rows} == set(seeds),
            "requested seeds are outside the approved group")
    require(all(r.get("conditional") and r["policy"] == "INSIGHT_WINNER" for r in rows),
            "conditional matrix identity changed")
    return rows


def parameters(job, selected_policy):
    require(selected_policy in ("CGOF(2:1)", "CGOF(1:1)"), "CGOF(2:1) candidate or CGOF(1:1) ablation only")
    return dict(N_SRC=job["n_src"], DEPTH=job["depth"], FAI_W=job["window"],
                HIGH_WEIGHT=2 if selected_policy == "CGOF(2:1)" else 1, ELIGIBLE_RR=0)


def config(job, selected_policy="CGOF(2:1)"):
    params = parameters(job, selected_policy)
    return dict(name=f"{job['id']}-cgof-hw{params['HIGH_WEIGHT']}-trained", top="cgof_unit_top",
                filelist=FILELIST, params=params, default_params={},
                test_dir="sim/experimental", test_module="test_cgof_performance",
                seeds=[job["seed"]], expect_tests=1, timeout_s=172800,
                env=dict(CXL_REVISION_JOB=json.dumps(job, sort_keys=True),
                         CXL_CGOF_SELECTED_POLICY=selected_policy,
                         CXL_CGOF_PARAMS=json.dumps(params, sort_keys=True),
                         COCOTB_TEST_FILTER=r"(^|\.)cgof_performance$"),
                artifacts=[dict(file="cgof_performance.json", required=True),
                           dict(file="cgof_performance_failure.json", required=False)])


def source_paths():
    # Reused validators/tests import the baseline modules: retain their full closure.
    paths = set(common.source_paths()) | set(native.source_paths()) | set(screen.source_hashes())
    paths.update(("scripts/run_revision_cgof_experiments.py",
                  "scripts/test_revision_cgof_experiments.py",
                  "sim/experimental/test_cgof_performance.py"))
    return sorted(paths)


def verify_zip(path, hashes):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and set(names) == set(hashes),
                "source archive member mismatch")
        require(all(hashlib.sha256(archive.read(n)).hexdigest() == h
                    for n, h in hashes.items()), "source archive bytes differ")


def verify_screen(summary_path):
    """Re-ingest the sealed reports and recompute the sole candidate gate, without simulation."""
    summary_path = Path(summary_path).resolve()
    saved = load(summary_path)
    require(saved.get("scope") == "MODEL_ONLY" and saved.get("kind") == "evaluate"
            and saved.get("exit_code") == saved.get("validation_exit") == 0
            and saved.get("partial") is False and not saved.get("failures"),
            "sealed model evaluation is incomplete or failed")
    require(saved.get("source_hashes") == screen.source_hashes(), "model screen sources changed")
    archive = saved["source_archive"]
    require(archive["file"] == "sources.zip"
            and archive["files"] == saved["source_hashes"]
            and sha(summary_path.parent / "sources.zip") == archive["sha256"],
            "model screen source archive binding failed")
    verify_zip(summary_path.parent / "sources.zip", saved["source_hashes"])
    require(sha(summary_path.parent / "validation.json") == saved["validation_sha256"],
            "model evaluation validation record changed")
    checks = load(summary_path.parent / "validation.json")
    require(len(checks) == 2 and all(c["exit_code"] == 0 for c in checks),
            "model evaluation units failed")
    hog, feedback, seen = [], [], set()
    ingested = saved.get("ingested_evidence", [])
    require(len(ingested) == 68, "sealed screen requires 60 HOG and eight feedback reports")
    for item in ingested:
        path = Path(item["path"]).resolve()
        require(path not in seen and sha(path) == item["sha256"],
                "duplicate or changed sealed report")
        seen.add(path)
        kind = load(path.parent / "summary.json")["kind"]
        require(kind in ("hog", "feedback"), "unexpected sealed report kind")
        row = screen.load_evidence(path, kind)
        (hog if kind == "hog" else feedback).append(row)
    require(len(hog) == 60 and len(feedback) == 8, "incomplete model screen")
    gate = screen.evaluate_gate(hog, 0, feedback)
    require(gate == saved["gate"] and gate["status"] == "PASS"
            and gate["frozen_candidate"] == "CGOF(2:1)", "sole CGOF(2:1) gate did not reproduce")
    bindings = {str(summary_path): sha(summary_path)}
    for path in (summary_path.parent / "sources.zip", summary_path.parent / "validation.json"):
        bindings[str(path)] = sha(path)
    for item in ingested:
        path = Path(item["path"]).resolve()
        for member in (path, path.parent / "summary.json", path.parent / "sources.zip",
                       path.parent / "validation.json"):
            bindings[str(member)] = sha(member)
    return bindings


def verify_native(directory):
    directory = Path(directory).resolve()
    model_tests = unittest.defaultTestLoader.loadTestsFromName(native.MODEL_TEST_MODULE).countTestCases()
    scope, summary = load(directory / "cgof_scope.json"), load(directory / "summary.json")
    require(scope.get("complete_matrix") is True and scope.get("selected_cases") == list(range(len(native.configurations())))
            and scope.get("stable") is True and scope.get("runner_exit") == scope.get("exit_code") == 0
            and scope["model_unittest"]["pass"] is True
            and scope["model_unittest"]["exit"] == 0
            and scope["model_unittest"]["tests"] == model_tests,
            "native full correctness is incomplete or failed")
    hashes = common.hash_sources(native.source_paths())
    require(scope["source_hashes_before"] == scope["source_hashes_after"] == hashes,
            "native correctness sources differ from current sources")
    require(sha(directory / "sources.zip") == scope["source_archive_sha256"],
            "native correctness archive hash mismatch")
    verify_zip(directory / "sources.zip", hashes)
    require(summary.get("overall") == "PASS", "native strict summary failed")
    expected = {}
    for kind, configs in (("lint", native.lint_configurations()),
                          ("elab_reject", native.reject_configurations()),
                          ("cocotb", native.configurations())):
        for cfg in configs:
            suffix = "_seed509" if kind == "cocotb" else ""
            expected[f"{kind}:{cfg['name']}{suffix}"] = (kind, cfg)
    expected["pytest:cgof_runner"] = ("pytest", dict(expect_tests=native.runner_test_count()))
    steps = summary["steps"]
    require(len(steps) == len(expected) and {s["name"] for s in steps} == set(expected),
            "native correctness step coverage mismatch")
    for step in steps:
        kind, cfg = expected[step["name"]]
        require(step["kind"] == kind, "native correctness step kind differs")
        if kind == "elab_reject":
            require(step["status"] == "XREJECT" and step["exit_codes"]["verilator"] != 0
                    and step["expect_message"] == cfg["expect_message"]
                    and step["userfatal_hits"] == 1 and not step["unexpected_diagnostics"]
                    and step["undriven_policy_slot_pins"] == cfg["expect_undriven"]
                    and step["unused_policy_slot_pins"] == cfg["expect_unused"]
                    and not step["reason"], "native expected rejection did not qualify")
        else:
            keys = ({"verilate", "make", "simulation"} if kind == "cocotb" else
                    {"pytest"} if kind == "pytest" else {"verilator"})
            require(step["status"] == "PASS" and set(step["exit_codes"]) == keys
                    and all(v == 0 for v in step["exit_codes"].values()),
                    "native correctness step failed")
        if kind in ("pytest", "cocotb"):
            counts = rv.junit_counts(directory / step["junit"])
            require(not rv.judge_counts(counts, expect_tests=cfg["expect_tests"]), "native raw JUnit failed")
            if kind == "cocotb":
                require(str(counts["xml_random_seed"]) == "509", "native JUnit seed differs")
    paths = [directory / n for n in ("cgof_scope.json", "summary.json", "sources.zip")]
    paths += [directory / s["junit"] for s in steps if "junit" in s]
    paths += [directory / s["log"] for s in steps]
    model_log = ROOT / scope["model_unittest"]["log"]
    require(model_log.resolve().is_relative_to(directory), "native model log outside accepted run")
    text = model_log.read_text()
    require(f"Ran {model_tests} tests in " in text
            and text.strip().endswith("\nOK"), "native model log does not confirm its test record")
    paths.append(model_log)
    return {str(p.resolve()): sha(p) for p in paths}


def verify_release(path, hashes, native_bindings, screen_bindings):
    release = load(path)
    require(release.get("schema") == "cxl-cgof-performance-release-v1"
            and release.get("native_released") is True
            and release.get("parent_correctness_accepted") is True,
            "native release and parent correctness acceptance are pending")
    require(release.get("source_hashes") == hashes, "new performance source freeze differs")
    require(release.get("native_bindings") == native_bindings
            and release.get("screen_bindings") == screen_bindings,
            "release does not bind accepted native correctness and sealed CGOF(2:1) gate")


def verify_pilot(directory, hashes, native_bindings, screen_bindings, selected_policy):
    directory = Path(directory).resolve()
    scope, spec = load(directory / "cgof_performance_scope.json"), load(directory / "frozen-spec.json")
    require(scope.get("status") == "PASS" and scope.get("sensitivity_evidence") is True
            and scope.get("source_hashes") == hashes
            and scope.get("selected_policy") == selected_policy
            and scope.get("native_bindings") == native_bindings
            and scope.get("screen_bindings") == screen_bindings,
            "reviewed CGOF pilot is failed, incomplete, or from different sources/gates")
    require(load(directory / "source_hashes_after.json") == hashes
            and load(directory / "source_hashes_before.json") == hashes,
            "pilot source hashes changed")
    with zipfile.ZipFile(directory / "sources.zip") as archive:
        require(all(hashlib.sha256(archive.read(n)).hexdigest() == h for n, h in hashes.items()),
                "pilot archived source bytes differ")
    configs = spec["configs"]
    require(len(configs) == len(scope["runs"]) == scope["expected_jobs"] == 1,
            "pilot must contain exactly one selected CGOF policy")
    job = json.loads(configs[0]["env"]["CXL_REVISION_JOB"])
    require(job["group"] == "cgof-pilot" and job["window"] == 256
            and job["seed"] in range(509, 514)
            and job == select_jobs(None, [job["seed"]], pilot=True)[0]
            and configs[0] == config(job, selected_policy),
            "reviewed pilot is not the expected W256 CGOF configuration")
    require(spec.get("schema") == "cxl-cgof-performance-spec-v1" and spec.get("pilot") is True
            and spec.get("source_sha256") == common.canonical_sha(hashes)
            and spec.get("jobs_sha256") == common.canonical_sha(configs),
            "pilot frozen spec does not bind its sources/configuration")
    summary = load(directory / "summary.json")
    require(summary["overall"] == "PASS", "pilot strict summary failed")
    common.check_steps(configs, summary["steps"])
    for step in summary["steps"]:
        if step["kind"] in ("pytest", "cocotb"):
            counts = rv.junit_counts(directory / step["junit"])
            require(not rv.judge_counts(counts, expect_tests=1 if step["kind"] == "cocotb" else None),
                    "pilot raw JUnit failed")
    replay = common.Traffic(job)
    for k in range(replay.end):
        replay.step(k)
    result_path = directory / "results" / f"cocotb_{configs[0]['name']}_seed{job['seed']}__cgof_performance.json"
    validate_result(load(result_path), job, selected_policy, replay)
    paths = [directory / name for name in (
        "cgof_performance_scope.json", "frozen-spec.json", "summary.json", "sources.zip",
        "source_hashes_before.json", "source_hashes_after.json")]
    paths += [directory / s["junit"] for s in summary["steps"] if "junit" in s]
    paths.append(result_path)
    return {str(p): sha(p) for p in paths}


def archive_bindings(output, bindings):
    """Copy acceptance inputs by content hash so the final evidence is self-contained."""
    directory = Path(output) / "acceptance"
    directory.mkdir()
    manifest = {}
    for entries in bindings.values():
        for name, digest in entries.items():
            data = Path(name).read_bytes()
            require(hashlib.sha256(data).hexdigest() == digest, "acceptance input changed before archive")
            target = directory / digest
            if not target.exists():
                target.write_bytes(data)
            manifest[name] = dict(sha256=digest, archived_as=target.relative_to(output).as_posix())
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")


def validate_result(data, job, selected_policy, replay):
    expected = dict(schema=SCHEMA, evidence_kind="RTL", status="PASS", job=job,
                    selected_policy=selected_policy, params=parameters(job, selected_policy),
                    cold=False, cold_cohort=None, trace_sha256=replay.sha256,
                    trace_config=replay.config, generated_per_source=replay.generated,
                    ready_cycles=replay.ready_count, active_cycles=replay.end,
                    training_cycles=replay.training, outstanding_after_drain=0,
                    producer_backlog_after_drain=0, sparse_guard_complete=True,
                    production_evidence=job["window"] == 5_000_000,
                    sensitivity_evidence=job["window"] == 256,
                    matrix_contribution=int(selected_policy == "CGOF(2:1)" and job["group"] in GROUPS))
    for key, value in expected.items():
        require(data.get(key) == value, f"incorrect CGOF result field {key}")
    require(type(data.get("peak_rss_kib")) is int and data["peak_rss_kib"] > 0,
            "missing simulator high-water RSS")
    require(0 < data["drain_cycles"] <= data["drain_bound"]
            and data["real_non_reset_cycles"] == replay.end + data["drain_cycles"],
            "invalid actual edge/drain accounting")
    phases, cohorts = data["metrics"]["phases"], data["metrics"]["cohorts"]
    require(set(phases) == set(replay.phases) and set(cohorts) == set(replay.cohorts),
            "missing phases/cohorts")
    edges = (0, *replay.bounds)
    lengths = [b-a for a, b in zip(edges, edges[1:])] + [data["drain_cycles"]]
    require([phases[p]["cycles"] for p in replay.phases] == lengths, "incorrect phase lengths")
    totals = {key: [0]*replay.n for key in ("generated", "accepted", "fired")}
    for p in replay.phases:
        row = phases[p]
        cycles, ready, eligible = row["cycles"], row["ready"], row["eligible_ready_opportunities"]
        fires = sum(row["fired"])
        require(0 <= fires <= eligible <= ready <= cycles
                and row["avoidable_bubbles"] == eligible-fires == 0
                and row["eligible_ready_utilization"] == (fires/eligible if eligible else None),
                "invalid joint eligible-ready utilization")
        for key in ("generated", "offered", "accepted", "fired"):
            require(len(row[key]) == replay.n
                    and all(type(v) is int and v >= 0 for v in row[key]), "invalid per-source counters")
        for h in range(replay.n):
            require(row["accepted"][h] <= row["offered"][h] <= cycles, "invalid offers")
            for key, values in totals.items():
                values[h] += row[key][h]
            require(totals["fired"][h] <= totals["accepted"][h] <= totals["generated"][h],
                    "per-source conservation failed")
            for key in ("backlog", "occupancy"):
                require(len(row[key]) == replay.n and row[key][h]["count"] == cycles,
                        "missing backlog/occupancy samples")
    require(totals["generated"] == totals["accepted"] == totals["fired"] == replay.generated,
            "generated population was not completely drained")
    require(all(data[key] == sum(replay.generated) for key in totals), "global conservation failed")
    for name, cohort in cohorts.items():
        require(cohort["generated"] == cohort["completed"]
                and len(cohort["per_source"]) == replay.n, "incomplete cohort")
        require([sum(v[h] for v in cohort["completed_by_phase"].values()) for h in range(replay.n)]
                == cohort["completed"], "incorrect cohort phase accounting")
        for h, row in enumerate(cohort["per_source"]):
            require(all(row[s]["count"] == cohort["completed"][h] for s in common.STAGES),
                    "missing cohort latency samples")
        for row in cohort["per_source"] + [cohort["pooled_sparse"]]:
            for stage in common.STAGES:
                hist = row[stage]["histogram"]
                stats = common.histogram_summary(hist) if hist else dict(
                    count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None)
                require({k: v for k, v in row[stage].items() if k != "histogram"} == stats,
                        "incorrect direct histogram statistics")
        for stage in common.STAGES:
            pooled = Counter()
            for h, row in enumerate(cohort["per_source"]):
                if h != job["heavy_source"]:
                    pooled.update({int(k): v for k, v in row[stage]["histogram"].items()})
            require(dict(pooled) == {int(k): v for k, v in cohort["pooled_sparse"][stage]["histogram"].items()},
                    "incorrect sparse pooling")
    require(len(data["windows"]) == data["real_non_reset_cycles"] // job["window"],
            "missing actual window closes")
    for i, row in enumerate(data["windows"]):
        total, n = sum(row["counts"]), job["n_src"]
        evidence = ["S0" if not total else "UP" if 10*n*b < 3*total else
                    "DOWN" if n*b > total else "KEEP" for b in row["counts"]]
        require(row["closing_cycle"] == (i+1)*job["window"]-1
                and row["total"] == total and row["evidence"] == evidence,
                "incorrect closing-edge evidence")
    return data


class CgofPerformanceRun(rv.Run):
    def __init__(self, args, configs, hashes, bindings):
        self.args, self.repo, self.milestone = args, ROOT, "revision-cgof-performance"
        self.entry = dict(description="Single sealed CGOF candidate performance", implemented=True,
                          lint=[{k: c[k] for k in ("name", "top", "filelist", "params")} for c in configs],
                          cocotb=configs, pytest=[
                              dict(name="cgof_performance_runner", target="scripts/test_revision_cgof_experiments.py",
                                   min_tests=1),
                              dict(name="revision_traffic", target="sim/experimental/test_revision_traffic.py",
                                   min_tests=1)])
        self.run_id, self.milestone_dir, self.out = args.output.name, BASE, args.output
        self.out.mkdir(parents=True, exist_ok=False)
        for name in ("logs", "junit"):
            (self.out / name).mkdir()
        cache = Path(os.environ.get("CXL_BUILD_ROOT") or "~/.cache/cxl-scheduler/build").expanduser()
        self.build_root = cache / self.milestone / self.run_id
        self.steps, self.lock, self.abort = [], threading.Lock(), threading.Event()
        self.t0, self.smoke, self.seeds_override, self.n_filter = time.time(), False, None, None
        self.configs, self.hashes, self.bindings = configs, hashes, bindings

    def write_summary(self, final):
        overall = super().write_summary(final)
        path = self.out / "summary.json"
        data = load(path)
        passed = any(s["kind"] == "scope" and s["status"] == "PASS" for s in self.steps)
        data.update(selected_policy=self.args.selected_policy,
                    sensitivity_evidence=self.args.pilot and passed and overall == "PASS",
                    production_evidence=not self.args.pilot and passed and overall == "PASS",
                    matrix_contribution=(len(self.configs) if passed and not self.args.pilot
                                         and self.args.selected_policy == "CGOF(2:1)" else 0),
                    full_498_matrix_executed=False)
        path.write_text(json.dumps(data, indent=2)+"\n")
        return overall

    def execute(self):
        problems, accepted = [], []
        memory = common.available_kib()
        minimum, stop = [memory], threading.Event()

        def sample():
            while not stop.wait(.25):
                current = common.available_kib()
                if current is not None and minimum[0] is not None:
                    minimum[0] = min(minimum[0], current)
                    if memory-current > .70*memory:
                        self.abort.set()  # Active jobs finish; pending jobs must not start.

        monitor = threading.Thread(target=sample, daemon=True)
        try:
            before = common.freeze_sources(self.out, source_paths())
            require(before == self.hashes, "sources changed after release verification")
            archive_bindings(self.out, self.bindings)
            spec = dict(schema="cxl-cgof-performance-spec-v1", configs=self.configs,
                        jobs_sha256=common.canonical_sha(self.configs),
                        source_sha256=common.canonical_sha(before), command=sys.argv,
                        selected_policy=self.args.selected_policy, pilot=self.args.pilot,
                        jobs=self.args.jobs, make_jobs=self.args.make_jobs, **self.bindings)
            (self.out / "frozen-spec.json").write_text(json.dumps(spec, indent=2)+"\n")
            require(memory is not None and memory > 0, "WSL/Linux memory measurement required")
            monitor.start()
            code = self.run_strict()
            require(code == 0, f"strict runner exit {code}")
            common.check_steps(self.configs, self.steps)
            for cfg in self.configs:
                job = json.loads(cfg["env"]["CXL_REVISION_JOB"])
                replay = common.Traffic(job)
                for k in range(replay.end):
                    replay.step(k)
                name = f"{cfg['name']}_seed{job['seed']}"
                path = self.out / "results" / f"cocotb_{name}__cgof_performance.json"
                data = validate_result(load(path), job, self.args.selected_policy, replay)
                accepted.append(dict(name=name, matrix_job_id=job["id"],
                                     selected_policy=self.args.selected_policy, result=str(path.relative_to(self.out)),
                                     trace_sha256=replay.sha256, peak_rss_kib=data["peak_rss_kib"],
                                     real_non_reset_cycles=data["real_non_reset_cycles"]))
            require(sum(sorted((r["peak_rss_kib"] for r in accepted), reverse=True)[:self.args.jobs])
                    <= .70*memory, "simulator RSS exceeds 70% of starting available memory")
        except Exception as exc:
            problems.append(f"{type(exc).__name__}: {exc}")
        finally:
            stop.set()
            if monitor.ident is not None:
                monitor.join()
        try:
            after = common.hash_sources(source_paths())
            (self.out / "source_hashes_after.json").write_text(json.dumps(after, indent=2)+"\n")
            require(after == self.hashes, "performance sources changed during execution")
            for entries in self.bindings.values():
                require(all(sha(p) == h for p, h in entries.items()), "bound acceptance evidence changed")
        except Exception as exc:
            problems.append(f"{type(exc).__name__}: {exc}")
        if memory is None or minimum[0] is None or memory-minimum[0] > .70*memory:
            problems.append("memory measurement unavailable or system growth exceeds 70%")
        passed = not problems and len(accepted) == len(self.configs)
        scope = dict(schema="cxl-cgof-performance-scope-v1", status="PASS" if passed else "FAIL",
                     sensitivity_evidence=passed and self.args.pilot,
                     production_evidence=passed and not self.args.pilot,
                     selected_policy=self.args.selected_policy,
                     matrix_contribution=(len(accepted) if passed and not self.args.pilot
                                          and self.args.selected_policy == "CGOF(2:1)" else 0),
                     expected_jobs=len(self.configs), runs=accepted, problems=problems,
                     source_hashes=self.hashes, available_memory_kib=memory,
                     minimum_available_memory_kib=minimum[0], max_memory_fraction=.70,
                     **self.bindings)
        (self.out / "cgof_performance_scope.json").write_text(json.dumps(scope, indent=2)+"\n")
        self.add_step(dict(order=len(self.steps)+1, kind="scope", name="scope:cgof-performance",
                           status=scope["status"], reason="; ".join(problems),
                           log="cgof_performance_scope.json"))
        self.write_summary(final=True)
        common.archive_evidence(self.out)
        return 0 if passed else 1

    def run_strict(self):
        return super().execute()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true")
    mode.add_argument("--group", choices=GROUPS)
    p.add_argument("--seed", required=True, help="explicit seed/range, e.g. 529..548")
    p.add_argument("--selected-policy", choices=("CGOF(2:1)", "CGOF(1:1)"), default="CGOF(2:1)")
    p.add_argument("--ablation", action="store_true", help="required for CGOF(1:1); contributes zero matrix rows")
    p.add_argument("--screen-summary", type=Path, required=True)
    p.add_argument("--native-correctness", type=Path, required=True)
    p.add_argument("--release", type=Path, required=True, help="parent acceptance and new source freeze receipt")
    p.add_argument("--source-ready", action="store_true")
    p.add_argument("--production-reviewed", action="store_true")
    p.add_argument("--reviewed-pilot", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("-j", "--jobs", type=int, default=1)
    p.add_argument("--make-jobs", type=int, default=2)
    args = p.parse_args(argv)
    try:
        require(not sys.flags.optimize, "optimized Python disables native/model assertion checks")
        require(args.source_ready, "native source release is pending")
        require(args.ablation == (args.selected_policy == "CGOF(1:1)"), "CGOF(1:1) requires --ablation; CGOF(2:1) is sole candidate")
        require(1 <= args.jobs <= 3 and args.make_jobs == 2, "at most three workers and exactly two build jobs")
        require(args.pilot or (args.production_reviewed and args.reviewed_pilot),
                "parent production review and a matching CGOF pilot are required")
        args.output = args.output.resolve()
        require(args.output != BASE.resolve() and args.output.is_relative_to(BASE.resolve())
                and not args.output.exists(), "output must be a fresh strict child of revision-cgof-performance")
        rows = select_jobs(args.group, rv.parse_seeds(args.seed), args.pilot)
        hashes = common.hash_sources(source_paths())
        screen_bindings = verify_screen(args.screen_summary)
        native_bindings = verify_native(args.native_correctness)
        verify_release(args.release, hashes, native_bindings, screen_bindings)
        bindings = dict(native_bindings=native_bindings, screen_bindings=screen_bindings,
                        release_binding={str(args.release.resolve()): sha(args.release)})
        if not args.pilot:
            bindings["pilot_bindings"] = verify_pilot(
                args.reviewed_pilot, hashes, native_bindings, screen_bindings, args.selected_policy)
        args.lint_only, args.keep_going, args.cocotb_timeout, args.cycles = False, False, None, None
        return CgofPerformanceRun(args, [config(r, args.selected_policy) for r in rows], hashes, bindings).execute()
    except (AssertionError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
