#!/usr/bin/env python3
"""Read-only current RTL analysis through the evidence indexer's strict acceptance."""
import argparse
from collections import Counter, defaultdict
import itertools
import json
import math
from pathlib import Path

import index_revision_evidence as evidence
from revision_matrix import CONFIRMATION, EXPLORATION, matrix
from revision_statistics import histogram_summary, paired_runs
from run_revision_experiments import source_paths as core_source_paths


STAGES = ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire")
POLICY_FIELDS = {"rr_quantum", "high_quota", "low_quota"}
IDENTITY_FIELDS = {"id", "seed", "policy", "execution_status", "prerequisite"}


def configuration(job, lane):
    return {**{k: v for k, v in job.items() if k not in IDENTITY_FIELDS},
            "training_cycles": evidence.lane_training(job, lane)}


def checked_distribution(value):
    hist = value["histogram"]
    if (not isinstance(hist, dict) or any(
            not isinstance(k, str) or not k.isascii() or not k.isdecimal()
            or str(int(k)) != k for k in hist)):
        raise ValueError("histogram keys must be canonical nonnegative integer cycles")
    if hist:
        stats = histogram_summary(hist)
    else:
        stats = dict(count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None)
    for key, expected in stats.items():
        actual = value.get(key)
        if key == "mean" and expected is not None:
            valid = (type(actual) in (int, float) and math.isfinite(actual)
                     and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))
        else:
            valid = actual == expected and type(actual) is type(expected)
        if not valid:
            raise ValueError(f"histogram disagrees with reported {key}")
    return dict(histogram=hist, **stats)


def normalize(result, run, bundle, source_hashes=None):
    job, lane = result["job"], run["lane"]
    if job["group"] == "adaptation" or job["cohorts"] != ["A", "B"]:
        raise ValueError("HOG A/B normalization excludes continuous adaptation")
    if result["cold"] is not (lane != "trained"):
        raise ValueError("result cold must be the actual RTL boolean")
    cohorts = result["metrics"]["cohorts"]
    selected = ("A", "B") if lane == "trained" else (lane[-1],)
    rows = []
    for cohort in selected:
        value = cohorts[cohort]
        sources = value["per_source"]
        counts = value["generated"]
        if (len(sources) != job["n_src"] or len(counts) != job["n_src"]
                or any(type(n) is not int or n < 0 for n in counts)
                or counts != value["completed"]):
            raise ValueError("incomplete generation cohort or source population")
        per_source = [{s: checked_distribution(v[s]) for s in STAGES} for v in sources]
        pooled = {s: checked_distribution(value["pooled_sparse"][s]) for s in STAGES}
        for stage in STAGES:
            merged = Counter()
            for source, distributions in enumerate(per_source):
                if distributions[stage]["count"] != counts[source]:
                    raise ValueError("per-source histogram count differs from completed population")
                if source != job["heavy_source"]:
                    merged.update(distributions[stage]["histogram"])
            if dict(merged) != pooled[stage]["histogram"]:
                raise ValueError("pooled sparse histogram differs from per-source populations")
        if not pooled["generation_to_fire"]["count"]:
            raise ValueError("selected cohort has no sparse population for a seed/run endpoint")
        rows.append(dict(
            matrix_job_id=run["matrix_job_id"], declared_job_id=job["id"],
            policy=result.get("selected_policy", job["policy"]), seed=job["seed"],
            profile=("trained-" if lane == "trained" else "cold-") + cohort,
            configuration=configuration(job, lane), status="PASS",
            production_evidence=result["production_evidence"],
            trace_sha256=result["trace_sha256"],
            source_sha256=bundle["file_hashes"]["source_hashes_before.json"],
            source_hashes=source_hashes, trace_config=result.get("trace_config"),
            result_sha256=run["result_sha256"], bundle=bundle["path"], result=run["result"],
            phase_metrics=result["metrics"]["phases"][cohort],
            completed_by_phase=value["completed_by_phase"],
            per_source=per_source, pooled_sparse=pooled, **pooled["generation_to_fire"],
        ))
    return rows


def dac_main_job(job, jobs):
    """Match only the declared default MAIN comparison, not a quota/depth sweep."""
    group = job["group"]
    if group == "insight-confirmation":
        target, case = "n4-confirmation", None
    elif group == "insight-robustness":
        target = "trained-robustness"
        case = {"bernoulli-0.75": "ready075", "periodic-48/64": "ready48of64"}[job["ready"]]
    else:
        raise ValueError("DAC comparison requires a conditional production matrix job")
    matches = [j for j in jobs if j["policy"] == "MAIN" and j["group"] == target
               and j["seed"] == job["seed"] and j.get("case") == case]
    if len(matches) != 1:
        raise ValueError("DAC comparison requires one exact trained MAIN job")
    ignored = IDENTITY_FIELDS | {"group", "conditional", "case", "perturbation_after_training"}
    boundary = lambda j: {k: v for k, v in j.items() if k not in ignored}
    if boundary(job) != boundary(matches[0]):
        raise ValueError("DAC and MAIN configured experimental boundaries differ")
    return matches[0]


def compare_dac_cohort(baseline, candidate, expected, jobs):
    # Retain each side's full freeze identity within seeds before projecting shared dependencies.
    index_cohort(baseline, expected)
    index_cohort(candidate, expected)
    if not baseline or not candidate:
        return compare_cohort(baseline, candidate, expected)
    projected = []
    core_names = set(core_source_paths())
    for rows, is_candidate in ((baseline, False), (candidate, True)):
        selected = []
        for row in rows:
            hashes = row["source_hashes"]
            if (not isinstance(hashes, dict) or not core_names <= hashes.keys()
                    or not is_candidate and set(hashes) != core_names):
                raise ValueError("DAC pairing requires the exact shared core source closure")
            if row["policy"] != ("DAC2" if is_candidate else "MAIN") or not row["profile"].startswith("trained-"):
                raise ValueError("DAC pairing requires DAC2 versus trained MAIN")
            if not isinstance(row.get("trace_config"), dict):
                raise ValueError("DAC pairing requires explicit arrival trace_config")
            config = row["configuration"]
            if is_candidate:
                job = next(j for j in jobs if j["id"] == row["matrix_job_id"])
                if config != configuration(job, "trained") or row["seed"] != job["seed"]:
                    raise ValueError("unpaired DAC matrix configuration or seed")
                config = configuration(dac_main_job(job, jobs), "trained")
            selected.append(dict(row, configuration=config,
                                 source_sha256=evidence.canonical_sha(
                                     {name: hashes[name] for name in sorted(core_names)})))
        projected.append(selected)
    left, right = ({r["seed"]: r for r in rows} for rows in projected)
    for seed in left.keys() & right.keys():
        if (left[seed]["configuration"] != right[seed]["configuration"]
                or left[seed]["trace_config"] != right[seed]["trace_config"]):
            raise ValueError("unpaired DAC/MAIN configuration or arrival trace_config")
    return compare_cohort(*projected, expected)


def cohort_key(row):
    return row["policy"], row["profile"], evidence.canonical_json(row["configuration"])


def index_cohort(rows, expected):
    if any(type(r["seed"]) is not int for r in rows):
        raise ValueError("seed must be an integer")
    indexed = {r["seed"]: r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError("duplicate seed/run")
    if rows and (len({cohort_key(r) for r in rows}) != 1
                 or len({r["source_sha256"] for r in rows}) != 1):
        raise ValueError("heterogeneous policy/profile/configuration/source cohort")
    if set(indexed) - set(expected):
        raise ValueError("unexpected seed in cohort")
    return indexed


def compare_cohort(baseline, candidate, expected):
    """Only seed/run endpoints enter inference; even partial pairs must match."""
    a, b = (index_cohort(rows, expected) for rows in (baseline, candidate))
    for seed in set(a) & set(b):
        left, right = a[seed], b[seed]
        boundary = lambda r: {k: v for k, v in r["configuration"].items()
                              if k not in POLICY_FIELDS}
        if (left["trace_sha256"] != right["trace_sha256"]
                or left["source_sha256"] != right["source_sha256"]
                or left["profile"] != right["profile"] or boundary(left) != boundary(right)):
            raise ValueError("unpaired trace/source/profile/experimental boundary")
    missing = dict(baseline=sorted(set(expected) - set(a)),
                   candidate=sorted(set(expected) - set(b)))
    if any(missing.values()):
        return dict(status="INCOMPLETE", missing_seeds=missing,
                    paired_seeds=sorted(set(a) & set(b)),
                    interval_status="NOT_COMPUTED_INCOMPLETE_COHORT")
    return dict(status="COMPLETE", missing_seeds=missing,
                **paired_runs(baseline, candidate, confirmation=tuple(expected) == CONFIRMATION))


def dac_analysis(endpoints, baseline_endpoints, jobs):
    planned = [j for j in jobs if j["policy"] == "INSIGHT_WINNER"]
    if len(planned) != 30:
        raise ValueError("conditional DAC plan requires 20 confirmation and 10 robustness jobs")
    grouped, main_grouped = defaultdict(list), defaultdict(list)
    for row in endpoints:
        grouped[cohort_key(row)].append(row)
    for row in baseline_endpoints:
        main_grouped[cohort_key(row)].append(row)
    expected_groups = {}
    for job in planned:
        for profile in ("trained-A", "trained-B"):
            key = "DAC2", profile, evidence.canonical_json(configuration(job, "trained"))
            expected_groups[key] = job
    if set(grouped) - set(expected_groups):
        raise ValueError("unexpected conditional DAC cohort")
    coverage, comparisons = [], []
    for key, job in sorted(expected_groups.items()):
        expected = CONFIRMATION if job["seed_role"] == "confirmation" else EXPLORATION
        rows = grouped[key]
        indexed = index_cohort(rows, expected)
        missing = sorted(set(expected) - indexed.keys())
        coverage.append(dict(policy="DAC2", profile=key[1], configuration=json.loads(key[2]),
                             seeds=sorted(indexed), missing_seeds=missing,
                             status="INCOMPLETE" if missing else "COMPLETE"))
        main_config = configuration(dac_main_job(job, jobs), "trained")
        main_key = "MAIN", key[1], evidence.canonical_json(main_config)
        comparisons.append(dict(
            baseline="MAIN", candidate="DAC2", profile=key[1],
            baseline_configuration=main_config, candidate_configuration=json.loads(key[2]),
            **compare_dac_cohort(main_grouped[main_key], rows, expected, jobs)))
    accepted = {r["matrix_job_id"] for r in endpoints}
    counts = {}
    for name, group in (("confirmation", "insight-confirmation"), ("robustness", "insight-robustness")):
        ids = {j["id"] for j in planned if j["group"] == group}
        counts[name] = dict(planned=len(ids), accepted=len(ids & accepted),
                            missing_job_ids=sorted(ids - accepted))
    return dict(policy="DAC2", scope="conditional candidate only; separate from core 120",
                **counts, endpoints=endpoints, cohorts=coverage, comparisons=comparisons)


def analyze(bundles=(), index=None, include_cold=False, comparisons=(("FCFS", "MAIN"), ("RR10", "MAIN"))):
    jobs = matrix()
    by_id = {r["id"]: r for r in jobs}
    snapshots, inspected, endpoints, dac_endpoints, descriptive = {}, [], [], [], []
    saved_records, verified_saved = None, 0
    saved_descriptive = []
    if index is not None:
        index = Path(index).resolve()
        raw = index.read_bytes()
        saved = json.loads(raw)
        if saved.get("schema") != "cxl-revision-evidence-index-v1":
            raise ValueError("explicit evidence index schema required")
        if saved["matrix"]["jobs"] != jobs:
            raise ValueError("saved index does not bind the current exact matrix")
        saved_descriptive = saved["performance"].get("descriptive_records", [])
        saved_records = saved["performance"]["accepted_records"] + saved_descriptive
        snapshots[str(index)] = raw
        bundles = sorted({r["bundle"] for r in saved_records})
        if any(not Path(p).is_absolute() for p in bundles):
            raise ValueError("saved index bundle paths must be absolute")
    seen = set()
    for supplied in bundles:
        path = Path(supplied).resolve()
        if path in seen:
            raise ValueError("duplicate explicit bundle")
        seen.add(path)
        bundle = evidence.inspect_performance_bundle(path, by_id)
        inspected.append(bundle)
        if bundle["status"] != "PASS":
            raise ValueError(f"strict bundle acceptance refused {path}: "
                             f"{bundle['status']} {bundle['failures']} {bundle['problems']}")
        for name, digest in bundle["file_hashes"].items():
            if name.endswith(".json"):
                raw = (path / name).read_bytes()
                if evidence.sha256_bytes(raw) != digest:
                    raise ValueError("bundle metadata changed after strict inspection")
                snapshots[str(path / name)] = raw
        for run in bundle["runs"]:
            is_dac = bundle["schema"] == "cxl-dac-performance-spec-v1"
            if saved_records is not None:
                matches = [r for r in saved_records if Path(r["bundle"]).resolve() == path
                           and r["matrix_job_id"] == run["matrix_job_id"] and r["lane"] == run["lane"]
                           and r["result"] == run["result"]]
                if len(matches) != 1:
                    raise ValueError("saved index accepted rows differ from inspected bundle")
                saved_run = matches[0]
                for key in ("status", "result", "result_sha256", "trace_sha256",
                            "production_evidence", "exit_codes", "seed"):
                    if evidence.canonical_json(saved_run.get(key)) != evidence.canonical_json(run.get(key)):
                        raise ValueError(f"saved index accepted row {key} mismatch")
                for key in ("source_archive", "evidence_archive"):
                    if saved_run.get(key + "_sha256") != bundle[key]["sha256"]:
                        raise ValueError("saved index archive hash mismatch")
                if is_dac:
                    for key in ("selected_policy", "declared_job_id", "matrix_contribution"):
                        if evidence.canonical_json(saved_run.get(key)) != evidence.canonical_json(run.get(key)):
                            raise ValueError(f"saved index DAC {key} mismatch")
                    for key in ("source_sha256", "core_source_sha256", "acceptance_binding_sha256"):
                        if saved_run.get(key) != bundle.get(key):
                            raise ValueError(f"saved index DAC {key} mismatch")
                    if (saved_run in saved_descriptive) != (run["matrix_contribution"] == 0):
                        raise ValueError("saved index DAC accepted/descriptive classification mismatch")
                verified_saved += 1
            if not is_dac:
                job = by_id[run["matrix_job_id"]]
                if job.get("conditional"):
                    raise ValueError("conditional results require strict DAC acceptance")
                if job["evidence_kind"] != "RTL_REQUIRED" or job["group"] == "adaptation":
                    continue
                if run["lane"] != "trained" and not include_cold:
                    continue
            raw = (path / run["result"]).read_bytes()
            if evidence.sha256_bytes(raw) != run["result_sha256"]:
                raise ValueError("result changed after strict inspection")
            result = json.loads(raw)
            snapshots[str(path / run["result"])] = raw
            rows = normalize(
                result, run, bundle,
                json.loads(snapshots[str(path / "source_hashes_before.json")]))
            if is_dac:
                for row in rows:
                    row["matrix_contribution"] = run["matrix_contribution"]
                if run["matrix_contribution"] == 1:
                    if (run["selected_policy"] != "DAC2" or not result["production_evidence"]
                            or result["job"] != by_id.get(run["matrix_job_id"])):
                        raise ValueError("conditional production requires exact accepted DAC2 job")
                    dac_endpoints.extend(rows)
                else:
                    descriptive.extend(rows)
            else:
                endpoints.extend(rows)
    if saved_records is not None and verified_saved != len(saved_records):
        raise ValueError("saved index contains accepted rows absent from inspected bundles")
    grouped = defaultdict(list)
    for row in endpoints:
        grouped[cohort_key(row)].append(row)
    coverage = []
    expected_groups = {}
    for job in jobs:
        if job["evidence_kind"] != "RTL_REQUIRED" or job["group"] == "adaptation" or job.get("conditional"):
            continue
        for profile in ("trained-A", "trained-B", "cold-A", "cold-B") if include_cold else ("trained-A", "trained-B"):
            lane = "trained" if profile.startswith("trained") else profile
            key = job["policy"], profile, evidence.canonical_json(configuration(job, lane))
            expected_groups[key] = CONFIRMATION if job["seed_role"] == "confirmation" else EXPLORATION
    for key, expected in sorted(expected_groups.items()):
        rows = grouped[key]
        indexed = index_cohort(rows, expected)
        missing = sorted(set(expected) - set(indexed))
        coverage.append(dict(policy=key[0], profile=key[1], configuration=json.loads(key[2]),
                             seeds=sorted(r["seed"] for r in rows),
                             missing_seeds=missing,
                             status="INCOMPLETE" if missing else "COMPLETE"))
    paired = []
    for baseline, candidate in comparisons:
        if baseline == candidate or not {baseline, candidate} <= {r["policy"] for r in jobs}:
            raise ValueError("comparison requires two different current policies")
        for left, right in itertools.product(coverage, coverage):
            if left["policy"] != baseline or right["policy"] != candidate:
                continue
            boundary = lambda c: {k: v for k, v in c["configuration"].items() if k not in POLICY_FIELDS}
            if left["profile"] != right["profile"] or boundary(left) != boundary(right):
                continue
            akey = baseline, left["profile"], evidence.canonical_json(left["configuration"])
            bkey = candidate, right["profile"], evidence.canonical_json(right["configuration"])
            expected = expected_groups[akey]
            paired.append(dict(baseline=baseline, candidate=candidate, profile=left["profile"],
                               baseline_configuration=left["configuration"],
                               candidate_configuration=right["configuration"],
                               **compare_cohort(grouped[akey], grouped[bkey], expected)))
    core_ids = {j["id"] for j in jobs if j["group"] == "n4-confirmation"}
    if len(core_ids) != 120:
        raise ValueError("current core must contain exactly 120 trained A/B jobs")
    accepted_core = {r["matrix_job_id"] for r in endpoints if r["profile"].startswith("trained")
                     and r["matrix_job_id"] in core_ids}
    report = dict(
        schema="cxl-current-result-analysis-v1", unit="paired seed/run",
        excluded_matrix_jobs=[
            dict(id=j["id"], group=j["group"],
                 reason="continuous role-change adaptation is not an A/B HOG endpoint"
                 if j["group"] == "adaptation" else "conditional DAC candidate analyzed separately"
                 if j.get("conditional") else "non-RTL-required evidence kind")
            for j in jobs if j["group"] == "adaptation" or j["evidence_kind"] != "RTL_REQUIRED"
            or j.get("conditional")],
        core_trained_jobs=dict(planned=len(core_ids), accepted=len(accepted_core),
                               missing_job_ids=sorted(core_ids - accepted_core)),
        endpoints=endpoints, cohorts=coverage, comparisons=paired, inspected_bundles=inspected,
        conditional_dac=dac_analysis(dac_endpoints, endpoints, jobs),
        descriptive_dac=dict(endpoints=descriptive, matrix_contribution=0,
                             scope="strictly inspected DAC1/W256 only; no paired inference or matrix completion"),
        input_sha256={p: evidence.sha256_bytes(raw) for p, raw in snapshots.items()},
        implementation_sha256={str(p): evidence.sha256_file(p) for p in
                               (Path(__file__), Path(evidence.__file__),
                                Path(__file__).with_name("revision_statistics.py"),
                                Path(__file__).with_name("revision_matrix.py"),
                                Path(__file__).with_name("run_revision_experiments.py"))},
        scope="HOG A/B subset only, not full matrix analysis; core 120, conditional DAC and optional cold are separate",
        inference="P99 only; 529-548 fixed 10000 bootstrap; 509-513 descriptive only",
        limitations="P999/max descriptive; synthetic generator only; adaptation excluded",
    )
    return report, snapshots


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--bundle", type=Path, action="append", help="exact runner directory; repeat")
    inputs.add_argument("--index", type=Path, help="saved current evidence index; bundles are reinspected")
    parser.add_argument("--include-cold", action="store_true")
    parser.add_argument("--compare", action="append", metavar="BASELINE:CANDIDATE")
    parser.add_argument("--out", type=Path, required=True, help="new directory; refuses overwrite")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"refusing existing output directory: {args.out}")
    try:
        comparisons = [tuple(s.split(":")) for s in args.compare] if args.compare else [("FCFS", "MAIN"), ("RR10", "MAIN")]
        if any(len(pair) != 2 for pair in comparisons):
            raise ValueError("--compare requires BASELINE:CANDIDATE")
        report, snapshots = analyze(args.bundle or (), args.index, args.include_cold, comparisons)
        if any(args.out.resolve().is_relative_to(Path(b["path"]))
               for b in report["inspected_bundles"]):
            raise ValueError("output must be outside input evidence bundles")
        args.out.mkdir(parents=True, exist_ok=False)
        originals = args.out / "inputs"
        originals.mkdir()
        for raw in snapshots.values():
            target = originals / (evidence.sha256_bytes(raw) + ".json")
            if not target.exists():
                target.write_bytes(raw)
        with (args.out / "analysis.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    core = report["core_trained_jobs"]
    print(json.dumps(dict(planned=core["planned"], accepted=core["accepted"],
                          missing=len(core["missing_job_ids"]))))
    return 0


if __name__ == "__main__":
    main()
