#!/usr/bin/env python3
"""Read-only aggregation of the current CGOF scheduler-RTL evidence."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_rtl_diagnosis import fairness, heavy_metrics, jain_index  # noqa: E402

EXPLORATION = tuple(range(509, 514))
CONFIRMATION = tuple(range(529, 549))
PERFORMANCE_GROUPS = ("insight-robustness", "insight-confirmation")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_partial_run_all_pass(summary, directory):
    counts = summary.get("counts", {})
    require(summary.get("overall") in {"PASS", "RUNNING"},
            f"{directory}: unexpected partial summary status")
    require(counts.get("fail", 0) == 0 and counts.get("errors", 0) == 0
            and counts.get("not_run", 0) == 0,
            f"{directory}: partial run contains failures")
    require(summary.get("steps")
            and all(step.get("status") == "PASS" for step in summary["steps"]),
            f"{directory}: partial run contains a non-PASS step")


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def source_variant_summary(source_hashes_by_run):
    """Accept only a documentation-only source drift between evidence runs."""
    require(source_hashes_by_run, "source hashes are required")
    first = next(iter(source_hashes_by_run.values()))
    keys = set(first)
    for path, hashes in source_hashes_by_run.items():
        require(set(hashes) == keys, f"{path}: source file set changed")
    differing = sorted(
        key for key in keys
        if len({hashes[key] for hashes in source_hashes_by_run.values()}) > 1
    )
    require(set(differing) <= {"AGENTS.md"},
            f"source drift outside AGENTS.md: {differing}")
    variants = sorted({canonical_sha(hashes) for hashes in source_hashes_by_run.values()})
    return dict(
        source_sha256=variants[0],
        source_variants=variants,
        source_drift_files=differing,
        source_hashes_by_run={
            str(Path(path).resolve()): canonical_sha(hashes)
            for path, hashes in source_hashes_by_run.items()
        },
    )


def require_complete_finite_stages(seeds):
    exploration_seeds = seeds & set(EXPLORATION)
    confirmation_seeds = seeds & set(CONFIRMATION)
    require(exploration_seeds in (set(), set(EXPLORATION)),
            "finite-Heavy exploration seeds are incomplete")
    require(confirmation_seeds in (set(), set(CONFIRMATION)),
            "finite-Heavy confirmation seeds are incomplete")
    require(exploration_seeds or confirmation_seeds, "finite-Heavy seeds are unavailable")
    require(seeds <= set(EXPLORATION) | set(CONFIRMATION),
            "unexpected finite-Heavy seed")
    return exploration_seeds, confirmation_seeds


def bootstrap_mean(values, key, replicates=10_000, interval_status="BOOTSTRAP"):
    values = [float(value) for value in values]
    require(values and all(math.isfinite(value) for value in values), "bootstrap values required")
    if len(values) == 1:
        return dict(n=1, mean=values[0], percentile95=[values[0], values[0]],
                    interval_status="SINGLE_SAMPLE")
    rng = random.Random(int(canonical_sha(key)[:16], 16))
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n
                     for _ in range(replicates))
    return dict(n=n, mean=statistics.fmean(values),
                percentile95=[samples[249], samples[9749]],
                interval_status=interval_status)


def summarize_rows(rows, fields, inference, key):
    result = dict(
        seeds=sorted({row["seed"] for row in rows}),
        n=len(rows),
        mean_service_share=[
            statistics.fmean(row["fairness"]["service_share"][source] for row in rows)
            for source in range(len(rows[0]["fairness"]["service_share"]))
        ],
    )
    for field in fields:
        values = [row[field] for row in rows]
        require(all(value is not None for value in values), f"missing aggregate field {field}")
        result[field] = bootstrap_mean(values, (key, field)) if inference else dict(
            n=len(values), mean=statistics.fmean(values),
            percentile95=None, interval_status="NOT_COMPUTED_EXPLORATION_ONLY")
    return result


def performance_rows(directories):
    inputs, source_hashes_by_run, rows, seen, partial_splits = {}, {}, [], set(), []
    for directory in directories:
        directory = Path(directory).resolve()
        summary = load(directory / "summary.json")
        before = load(directory / "source_hashes_before.json")
        frozen = load(directory / "frozen-spec.json")
        require(canonical_sha(before) == frozen.get("source_sha256"),
                f"{directory}: source hashes do not match frozen spec")
        scope_path = directory / "cgof_performance_scope.json"
        if scope_path.exists():
            scope = load(scope_path)
            after = load(directory / "source_hashes_after.json")
            require(summary.get("overall") == "PASS",
                    f"{directory}: complete summary is not PASS")
            require(scope.get("status") == "PASS" and not scope.get("problems"),
                    f"{directory}: scope is not PASS")
            require(before == after and scope.get("source_hashes") == before,
                    f"{directory}: source hashes changed")
        else:
            counts = summary.get("counts", {})
            require(summary.get("overall") == "RUNNING",
                    f"{directory}: incomplete run is not RUNNING")
            require(counts.get("fail", 0) == 0 and counts.get("errors", 0) == 0
                    and counts.get("not_run", 0) == 0,
                    f"{directory}: incomplete run contains failures")
            require(all(step.get("status") == "PASS" for step in summary.get("steps", [])),
                    f"{directory}: incomplete run contains a non-PASS step")
            partial_splits.append(str(directory))
        source_hashes_by_run[directory] = before
        inputs[str(directory / "summary.json")] = sha(directory / "summary.json")
        if scope_path.exists():
            inputs[str(scope_path)] = sha(scope_path)
        inputs[str(directory / "source_hashes_before.json")] = sha(
            directory / "source_hashes_before.json")
        result_paths = sorted((directory / "results").glob("*__cgof_performance.json"))
        require(result_paths, f"{directory}: no CGOF performance results")
        for path in result_paths:
            data = load(path)
            job = data["job"]
            require(data.get("status") == "PASS" and data.get("evidence_kind") == "RTL",
                    f"{path}: failed or non-RTL result")
            require(data.get("selected_policy") == "CGOF(2:1)"
                    and data.get("production_evidence") is True
                    and job.get("window") == 5_000_000,
                    f"{path}: unexpected policy or evidence scope")
            require(job.get("group") in PERFORMANCE_GROUPS and job.get("cohorts") == ["A", "B"],
                    f"{path}: unexpected group or cohorts")
            inputs[str(path)] = sha(path)
            for cohort_name in job["cohorts"]:
                identity = (job["group"], job["ready"], job["seed"], cohort_name)
                require(identity not in seen, f"duplicate endpoint identity {identity}")
                seen.add(identity)
                phase = data["metrics"]["phases"][cohort_name]
                cohort = data["metrics"]["cohorts"][cohort_name]
                require(cohort["generated"] == cohort["completed"],
                        f"{path}: incomplete {cohort_name} generation cohort")
                require(
                    [sum(values[source] for values in cohort["completed_by_phase"].values())
                     for source in range(job["n_src"])] == cohort["completed"],
                    f"{path}: phase completions differ from completed cohort")
                row_fairness = fairness(phase["fired"], phase["generated"], job["heavy_source"])
                row_heavy = heavy_metrics(dict(phase_metrics=phase, configuration=job))
                sparse_p99 = cohort["pooled_sparse"]["generation_to_fire"]["p99"]
                require(sparse_p99 is not None, f"{path}: missing sparse P99")
                rows.append(dict(
                    group=job["group"], ready=job["ready"], seed=job["seed"],
                    cohort=cohort_name, profile=f"{job['ready']}-{cohort_name}",
                    source_sha256=canonical_sha(before), trace_sha256=data["trace_sha256"],
                    fairness=row_fairness, heavy=row_heavy, sparse_p99=sparse_p99,
                    raw_jain=row_fairness["raw_jain_all"],
                    active_jain=row_fairness["active_service_jain"],
                    sparse_jain=row_fairness["sparse_service_jain"],
                    demand_l1=row_fairness["generated_share_reference_error"]["l1_error"],
                    heavy_service_fraction=row_heavy["service_fraction"],
                    heavy_wall_gap_p99=row_heavy["inter_service_wall_cycles"]["p99_nearest_rank"],
                    heavy_wall_gap_max=row_heavy["inter_service_wall_cycles"]["max"],
                ))
    source_summary = source_variant_summary(source_hashes_by_run)

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["group"], row["ready"], row["cohort"])].append(row)
    for group, ready, cohort in grouped:
        seeds = {row["seed"] for row in grouped[(group, ready, cohort)]}
        expected = set(CONFIRMATION if group == "insight-confirmation" else EXPLORATION)
        require(seeds == expected, f"incomplete seed coverage for {group}/{ready}/{cohort}")
    robustness = {row["seed"] for row in rows if row["group"] == "insight-robustness"}
    require(robustness == set(EXPLORATION), "robustness seed coverage changed")
    require({row["ready"] for row in rows if row["group"] == "insight-robustness"}
            == {"bernoulli-0.75", "periodic-48/64"},
            "robustness ready-profile coverage changed")

    fields = ("raw_jain", "active_jain", "sparse_jain", "demand_l1",
              "heavy_service_fraction", "heavy_wall_gap_p99", "heavy_wall_gap_max",
              "sparse_p99")
    cohorts = []
    for key in sorted(grouped):
        members = grouped[key]
        cohorts.append(dict(
            group=key[0], ready=key[1], cohort=key[2],
            inference=key[0] == "insight-confirmation",
            **summarize_rows(members, fields, key[0] == "insight-confirmation", key),
        ))
    return dict(
        run_directories=[str(Path(path).resolve()) for path in directories],
        **source_summary,
        partial_splits=partial_splits,
        endpoint_count=len(rows), inputs_sha256=inputs,
        coverage=dict(
            confirmation_seeds=list(CONFIRMATION),
            exploration_seeds=list(EXPLORATION),
            confirmation_endpoints=sum(row["group"] == "insight-confirmation" for row in rows),
            robustness_endpoints=sum(row["group"] == "insight-robustness" for row in rows),
        ),
        cohorts=cohorts, rows=rows,
        comparison_boundary="Current-source CGOF(2:1) only; no fresh same-source RTL FAI baseline.",
    )


def finite_rows(directories):
    inputs, source_hashes_by_run, results, scopes = {}, {}, {}, {}
    partial_runs, known_source_hashes = [], {}
    for directory in directories:
        directory = Path(directory).resolve()
        scope_path = directory / "diagnosis_scope.json"
        summary = load(directory / "summary.json")
        if scope_path.exists():
            scope = load(scope_path)
            require(scope.get("status") == "PASS" and scope.get("source_stable") is True,
                    f"{directory}: diagnosis scope is not stable PASS")
            require(scope.get("results"), f"{directory}: no scoped results")
            known_source_hashes[directory] = scope["source_hashes"]
            scopes[str(directory)] = sha(scope_path)
        else:
            require_partial_run_all_pass(summary, directory)
            partial_runs.append(str(directory))
        inputs[str(directory / "summary.json")] = sha(directory / "summary.json")
        for path in sorted((directory / "results").glob("*.json")):
            data = load(path)
            job = data["job"]
            require(data.get("status") == "PASS"
                    and data.get("evidence_kind") == "SCHEDULER_RTL"
                    and data.get("mode") == "finite-heavy",
                    f"{path}: failed or non-RTL finite-Heavy result")
            require(job.get("ordering", "oldest-first") == "oldest-first",
                    f"{path}: this frozen aggregator accepts oldest-first only")
            key = (job["seed"], job["high_weight"], job["lane"])
            require(key not in results, f"duplicate finite-Heavy result {key}")
            results[key] = data
            inputs[str(path)] = sha(path)
    require(known_source_hashes, "finite-Heavy source hashes are unavailable")
    source_variants = {
        canonical_sha(hashes) for hashes in known_source_hashes.values()
    }
    require(len(source_variants) == 1,
            "cannot bind partial finite-Heavy runs across multiple source variants")
    source_basis = next(iter(known_source_hashes.values()))
    source_hashes_by_run.update(known_source_hashes)
    source_hashes_by_run.update({Path(path): source_basis for path in partial_runs})
    source_summary = source_variant_summary(source_hashes_by_run)
    seeds = {key[0] for key in results}
    require_complete_finite_stages(seeds)
    expected_keys = {(seed, weight, lane) for seed in seeds for weight in (1, 2)
                     for lane in ("mixed", "isolated")}
    require(set(results) == expected_keys, "finite-Heavy mixed/isolated quota grid is incomplete")

    pairs = []
    for seed in sorted(seeds):
        for weight in (1, 2):
            mixed, isolated = results[(seed, weight, "mixed")], results[(seed, weight, "isolated")]
            for data in (mixed, isolated):
                require(sum(data["generated"]) == data["accepted"] == data["fired"],
                        "finite-Heavy generated/accepted/fired conservation failed")
                require(data["heavy"]["completed"] is True, "Heavy burst did not complete")
            mixed_config = dict(mixed["trace_config"])
            isolated_config = dict(isolated["trace_config"])
            mixed_config.pop("include_sparse", None)
            isolated_config.pop("include_sparse", None)
            require(mixed_config == isolated_config,
                    "finite-Heavy mixed/isolated trace differs")
            cohort = mixed["metrics"]["cohorts"]["finite-heavy"]
            sparse_p99 = cohort["pooled_sparse"]["generation_to_fire"]["p99"]
            transitions = sum(
                old != new
                for window in mixed["classifier"]
                for old, new in zip(window["old_classes"], window["classes"])
            )
            heavy_source = mixed["trace_config"]["scenario"]["heavy_source"]
            sparse_sources = [
                source for source in range(mixed["trace_config"]["n_src"])
                if source != heavy_source
            ]
            pairs.append(dict(
                seed=seed, high_weight=weight,
                completion_ratio=mixed["active_cycles"] / isolated["active_cycles"],
                throughput_ratio=isolated["active_cycles"] / mixed["active_cycles"],
                mixed_active_cycles=mixed["active_cycles"],
                isolated_active_cycles=isolated["active_cycles"],
                heavy_completion_delta_cycles=(
                    mixed["heavy"]["completion_cycle"] - isolated["heavy"]["completion_cycle"]),
                heavy_wall_gap_p99=mixed["heavy"]["gaps"]["wall_cycles"]["p99_nearest_rank"],
                heavy_wall_gap_max=mixed["heavy"]["max_wall_gap"],
                isolated_heavy_wall_gap_max=isolated["heavy"]["max_wall_gap"],
                sparse_p99=sparse_p99,
                raw_jain=mixed["fairness"]["raw_jain_all"],
                sparse_jain=jain_index([
                    mixed["service_shares"][str(source)] for source in sparse_sources
                ]),
                demand_l1=mixed["fairness"]["demand_share_l1_error"],
                heavy_service_fraction=mixed["service_shares"][str(heavy_source)],
                classifier_transitions=transitions,
            ))

    grouped = defaultdict(list)
    for row in pairs:
        stage = "exploration" if row["seed"] in EXPLORATION else "confirmation"
        grouped[(stage, row["high_weight"])].append(row)
    fields = ("completion_ratio", "throughput_ratio", "heavy_completion_delta_cycles",
              "heavy_wall_gap_p99", "heavy_wall_gap_max", "sparse_p99", "raw_jain",
              "sparse_jain", "demand_l1", "heavy_service_fraction",
              "classifier_transitions")
    groups = []
    for key in sorted(grouped):
        members = grouped[key]
        inference = key[0] == "confirmation" and set(
            row["seed"] for row in members) == set(CONFIRMATION)
        summary = dict(stage=key[0], high_weight=key[1],
                       seeds=sorted(row["seed"] for row in members), n=len(members))
        for field in fields:
            values = [row[field] for row in members]
            summary[field] = bootstrap_mean(values, ("finite", key, field)) if inference else dict(
                n=len(values), mean=statistics.fmean(values),
                percentile95=None, interval_status="NOT_COMPUTED_EXPLORATION_ONLY")
        groups.append(summary)

    quota_deltas = []
    for stage, expected in (("exploration", EXPLORATION), ("confirmation", CONFIRMATION)):
        available = [seed for seed in expected if seed in seeds]
        if not available:
            continue
        require(set(available) == set(expected) if stage == "confirmation" else True,
                "finite-Heavy confirmation seeds are incomplete")
        by_seed = {(row["seed"], row["high_weight"]): row for row in pairs}
        for field in ("completion_ratio", "heavy_wall_gap_max", "heavy_wall_gap_p99", "sparse_p99"):
            values = [by_seed[(seed, 2)][field] - by_seed[(seed, 1)][field]
                      for seed in available]
            summary = (bootstrap_mean(values, ("quota-delta", stage, field),
                                      interval_status="PAIRED_BOOTSTRAP")
                       if stage == "confirmation" else dict(
                           n=len(values), mean=statistics.fmean(values),
                           percentile95=None,
                           interval_status="NOT_COMPUTED_EXPLORATION_ONLY"))
            quota_deltas.append(dict(
                stage=stage, metric=field, delta="CGOF(2:1) minus CGOF(1:1)",
                **summary))
    return dict(
        run_directories=[str(Path(path).resolve()) for path in directories],
        **source_summary,
        pair_count=len(pairs), inputs_sha256=inputs, scopes_sha256=scopes,
        partial_runs=partial_runs,
        source_hash_basis=(
            "Partial runs are bound to the single stable source variant "
            "recorded by completed scopes; all present steps are PASS."
        ),
        coverage=dict(
            exploration_seeds=sorted(seeds & set(EXPLORATION)),
            confirmation_seeds=sorted(seeds & set(CONFIRMATION)),
        ),
        groups=groups, quota_deltas=quota_deltas, rows=pairs,
        comparison_boundary="Scheduler RTL finite work only; completion is fire, not memory completion.",
    )


def self_check():
    require(abs(jain_index([1, 1, 1, 1]) - 1.0) < 1e-12, "Jain equal-share check failed")
    require(jain_index([2, 1, 1, 1]) < 0.91, "Jain unequal-share check failed")
    sample = bootstrap_mean([1, 2, 3], "self-check")
    require(sample["n"] == 3 and abs(sample["mean"] - 2) < 1e-12,
            "bootstrap self-check failed")
    require_partial_run_all_pass(
        {"overall": "RUNNING", "counts": {"fail": 0, "errors": 0, "not_run": 0},
         "steps": [{"status": "PASS"}]},
        "partial-self-check",
    )
    base = {"AGENTS.md": "old", "rtl/cgof.sv": "same"}
    drifted = {"AGENTS.md": "new", "rtl/cgof.sv": "same"}
    summary = source_variant_summary({"run-a": base, "run-b": drifted})
    require(summary["source_drift_files"] == ["AGENTS.md"],
            "documentation-only source drift check failed")
    require(require_complete_finite_stages(set(CONFIRMATION))
            == (set(), set(CONFIRMATION)),
            "confirmation-only seed coverage check failed")
    require(require_complete_finite_stages(set(EXPLORATION))
            == (set(EXPLORATION), set()),
            "exploration-only seed coverage check failed")
    try:
        source_variant_summary(
            {"run-a": base, "run-b": {"AGENTS.md": "new", "rtl/cgof.sv": "changed"}}
        )
    except ValueError:
        pass
    else:
        raise AssertionError("RTL source drift was not rejected")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--performance-run", type=Path, action="append", required=True)
    parser.add_argument("--finite-heavy-run", type=Path, action="append", required=True)
    parser.add_argument("--require-finite-heavy-confirmation", action="store_true")
    parser.add_argument("--out", type=Path, required=True, help="new JSON path")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"refusing existing output: {args.out}")
    try:
        self_check()
        performance = performance_rows(args.performance_run)
        finite = finite_rows(args.finite_heavy_run)
        if args.require_finite_heavy_confirmation:
            require(finite["coverage"]["confirmation_seeds"] == list(CONFIRMATION),
                    "20-seed held-out finite-Heavy confirmation is incomplete")
        result = dict(
            schema="cxl-cgof-diagnosis-aggregate-v1",
            scope="SCHEDULER_RTL only",
            performance=performance,
            finite_heavy=finite,
            unavailable=dict(
                completed_memory_bandwidth="No calibrated CXL completed-byte measurement.",
                memory_response_latency="Generation-to-fire is scheduler waiting, not CXL response.",
                application_slowdown="No calibrated application/system harness.",
                maximum_application_slowdown="Same boundary as application slowdown.",
            ),
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(dict(
        performance_endpoints=performance["endpoint_count"],
        finite_heavy_pairs=finite["pair_count"],
        confirmation_seeds=finite["coverage"]["confirmation_seeds"],
        source_sha256=performance["source_sha256"],
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
