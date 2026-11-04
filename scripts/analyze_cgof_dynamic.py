#!/usr/bin/env python3
"""Validate dynamic scheduler evidence separately from the static confirmation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jain(values):
    denominator = len(values) * sum(value * value for value in values)
    return sum(values) ** 2 / denominator if denominator else None


def validate_data(data):
    assert data["status"] == "PASS" and data["evidence_kind"] == "SCHEDULER_RTL"
    assert data["job"].get("ordering", "oldest-first") == "oldest-first"
    assert data["params"]["ELIGIBLE_RR"] == 0
    assert sum(data["generated"]) == data["accepted"] == data["fired"]
    heavy = data["heavy"]
    assert heavy["completed"] and heavy["generated"] == heavy["fired"] == heavy["work"]
    roles = data["generation_roles"]
    for counts in roles["counts"].values():
        assert counts["generated"] == counts["accepted"] == counts["fired"]
    assert [sum(counts["generated"][source] for counts in roles["counts"].values())
            for source in range(data["job"]["n_src"])] == data["generated"]
    for key in ("accepted", "fired"):
        assert sum(sum(counts[key]) for counts in roles["counts"].values()) == data[key]
    for role, counts in roles["counts"].items():
        for stage in roles["latency"][role].values():
            assert stage["count"] == sum(counts["fired"])
            assert sum(stage["histogram"].values()) == stage["count"]
    for burst in roles["bursts"]:
        assert burst["generated"] == burst["completed"]
        assert burst["last_fire"] >= burst["last_release"]
    assert sum(b["completed"] for b in roles["bursts"]) == heavy["work"]
    active = [row for row in data["classifier"] if row["phase"] == "active"]
    assert len(active) >= 4, "fewer than four actual active classifier boundaries"
    assert all(row["closing_cycle"] + 1 == (row["window"] + 1) * data["job"]["window"]
               for row in active)
    return active


def validate_run(directory, source_hashes, expected_job=None):
    directory = directory.resolve()
    scope = read(directory / "diagnosis_scope.json")
    summary = read(directory / "summary.json")
    assert scope["status"] == "PASS" and scope["source_stable"]
    assert scope["source_hashes"] == scope["source_hashes_after"] == source_hashes
    assert summary["overall"] == "PASS"
    assert all(summary["counts"].get(key, 0) == 0
               for key in ("fail", "not_run", "failures", "errors", "skipped"))
    with zipfile.ZipFile(directory / "sources.zip") as archive:
        assert set(archive.namelist()) == set(source_hashes)
        for name, value in source_hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == value
    assert len(scope["results"]) == 4 and len(scope["finite_heavy_pairs"]) == 2
    lanes = {}
    bindings = {}
    for item in scope["results"]:
        job, data = item["job"], item["data"]
        path = directory / item["path"]
        assert read(path) == data and data["job"] == job
        if expected_job is not None:
            assert {k: job[k] for k in expected_job} == expected_job
        validate_data(data)
        key = job["high_weight"], job["lane"]
        assert key not in lanes
        lanes[key] = data
        bindings[path.relative_to(ROOT).as_posix()] = digest(path)
    assert set(lanes) == {(w, lane) for w in (1, 2) for lane in ("mixed", "isolated")}
    rows = []
    for weight in (1, 2):
        mixed, isolated = (lanes[weight, lane] for lane in ("mixed", "isolated"))
        mconfig, iconfig = (dict(item["trace_config"]) for item in (mixed, isolated))
        mconfig.pop("include_sparse")
        iconfig.pop("include_sparse")
        assert mconfig == iconfig, "unpaired Heavy/ready traces"
        signature = lambda data: [
            [b[k] for k in ("burst_id", "source", "generated", "first_release", "last_release")]
            for b in data["generation_roles"]["bursts"]]
        assert signature(mixed) == signature(isolated)
        assert mixed["heavy"]["first_release_cycle"] == isolated["heavy"]["first_release_cycle"]
        roles = mixed["generation_roles"]
        sparse = roles["at_cut"]["sparse"]
        ratios = [f / g for f, g in zip(sparse["active_fired"], sparse["generated"]) if g]
        gaps = mixed["heavy"]["gaps"]
        active = validate_data(mixed)
        role_schedule = mixed["job"].get("heavy_sources") or [0]
        for row in active:
            index = min(row["window"], len(role_schedule) - 1)
            assert row["heavy_source_at_close"] == role_schedule[index]
        rows.append(dict(
            policy=f"CGOF ({weight}:1)", seed=mixed["job"]["seed"],
            depth=mixed["job"]["depth"], ready_pattern=mixed["job"]["ready_pattern"],
            active_cycles=mixed["active_cycles"],
            ready_cycles=mixed["ready_cycles"],
            realized_ready_fraction=mixed["ready_cycles"] / mixed["active_cycles"],
            completion_ratio=mixed["active_cycles"] / isolated["active_cycles"],
            extra_completion_cycles=mixed["active_cycles"] - isolated["active_cycles"],
            heavy_span_ratio=(mixed["heavy"]["first_release_to_last_fire"] + 1) / (
                isolated["heavy"]["first_release_to_last_fire"] + 1),
            heavy_fire_per_active_cycle=mixed["heavy"]["fired"] / mixed["active_cycles"],
            heavy_wall_gap=gaps["wall_cycles"],
            heavy_ready_opportunity_gap=gaps["eligible_ready"],
            latency=roles["latency"],
            sparse_censored_at_cut=sum(sparse["generated"]) - sum(sparse["active_fired"]),
            raw_jain=mixed["fairness"]["raw_jain_all"],
            demand_share_l1=mixed["fairness"]["demand_share_l1_error"],
            sparse_raw_jain=roles["sparse_fairness"]["active_service_jain"],
            sparse_demand_share_l1=roles["sparse_fairness"]["demand_share_l1_error"],
            sparse_demand_normalized_jain=jain(ratios),
            active_boundaries=len(active),
            effective_class_transitions=sum(
                sum((old in ("H", "B_H")) != (new in ("H", "B_H"))
                    for old, new in zip(row["old_classes"], row["classes"]))
                for row in active),
            classifier=active, bursts=roles["bursts"],
            phase_metrics=mixed["metrics"]["phases"],
            backlog_condition="Heavy generation role; same physical FIFO; no gaps across empty episodes",
            censoring="at-cut counts preserved; active-generation latency includes completions in drain",
        ))
    bindings[(directory / "diagnosis_scope.json").relative_to(ROOT).as_posix()] = digest(
        directory / "diagnosis_scope.json")
    bindings[(directory / "summary.json").relative_to(ROOT).as_posix()] = digest(
        directory / "summary.json")
    return rows, bindings


def analyze_batch(batch):
    manifest = read(batch / "manifest.json")
    completed = [json.loads(line) for line in (batch / "completed-runs.jsonl").read_text().splitlines()]
    expected = {case["case"]: case for case in manifest["cases"]}
    assert len(completed) == len(expected) and {r["case"] for r in completed} == set(expected)
    rows, bindings = [], {}
    for record in completed:
        case = expected[record["case"]]
        data, files = validate_run(ROOT / record["run"], manifest["source_hashes"], case["job"])
        for row in data:
            row["case"] = record["case"]
        rows.extend(data)
        assert not set(bindings).intersection(files)
        bindings.update(files)
    assert len(rows) * 2 == manifest["expected_rtl_results"]
    assert all(digest(ROOT / path) == value for path, value in manifest["protected_documents"].items())
    result = dict(
        status="PASS", evidence_kind="SCHEDULER_RTL",
        stage="single-seed production diagnostic probe", seeds=[manifest["seed"]],
        result_count=len(rows) * 2, mixed_isolated_pairs=len(rows),
        manifest_sha256=digest(batch / "manifest.json"), source_stable=True,
        bindings=bindings, rows=rows,
        confidence_intervals=None,
        inference_limit="single fresh seed, no seed-level confidence interval; not held-out confirmation",
        not_measured=["real CXL completed bandwidth", "CXL response latency",
                      "application slowdown", "APR/signoff", "broad backpressure sweep"],
    )
    with (batch / "aggregate.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def self_check(directory):
    scope = read(directory / "diagnosis_scope.json")
    rows, _ = validate_run(directory, scope["source_hashes"])
    assert len(rows) == 2
    sample = scope["results"][0]["data"]
    bad = copy.deepcopy(sample)
    bad["generation_roles"]["counts"]["heavy"]["fired"][0] -= 1
    try:
        validate_data(bad)
    except AssertionError:
        pass
    else:
        raise AssertionError("role conservation corruption accepted")
    bad = copy.deepcopy(sample)
    bad["classifier"] = bad["classifier"][:2]
    try:
        validate_data(bad)
    except AssertionError:
        pass
    else:
        raise AssertionError("nominal windows accepted as multi-window evidence")
    assert jain([1, 1]) == 1 and jain([0, 0]) is None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--self-check", type=Path)
    args = parser.parse_args()
    if args.self_check:
        self_check(args.self_check)
        print("dynamic analyzer self-check PASS")
    if args.batch:
        output = analyze_batch(args.batch)
        print(json.dumps({key: output[key] for key in ("status", "result_count", "mixed_isolated_pairs")}))
