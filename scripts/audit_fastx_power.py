#!/usr/bin/env python3
"""Read-only FastX input inventory. This is not a power acceptance checker."""

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

from index_revision_evidence import sha256_file, safe_relpath

ROOT = Path(__file__).resolve().parents[1]
CGOF_SOURCES = (
    "rtl/include/cxl_sched_pkg.sv", "rtl/common/cxl_desc_fifo.sv",
    "rtl/common/cxl_out_hold.sv", "rtl/common/cxl_fcfs_sel.sv",
    "rtl/experimental/cxl_cgof_sched.sv", "rtl/experimental/cgof_unit_top.sv",
    "rtl/experimental/filelist_cgof_unit.f",
)
CGOF_BUNDLES = {
    "cgof1-n4": "cgof-ppa-dcpt-cgof1-n4-20261028",
    "cgof2-n4": "cgof-ppa-dcpt-20261028T0723",
}
BASELINE = (".setup-logs/implementation/revision-20261024/"
            "trained-power-results-20261026/analysis-output/matched-power-acceptance.json")
BASELINE_SHA = "9d26aa70fa688c068311b70c20c9a2583eae4a9c63e7abba0a9355e3d895c61e"
FORMAL_BUNDLES = ("cgof-ppa-formal-cgof1-n4-20261028", "cgof-ppa-formal-20261028T0727")


def no_links(path):
    for component in (path, *path.parents):
        if component.is_symlink() or (hasattr(component, "is_junction") and component.is_junction()):
            raise ValueError(f"linked path rejected: {component}")
    return path


def repo_file(root, name):
    if not safe_relpath(name):
        raise ValueError(f"unsafe relative path: {name!r}")
    return no_links(root / name)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def read_json(path):
    no_links(path)
    return json.loads(path.read_text(encoding="utf-8-sig"),
                      object_pairs_hook=unique_object, parse_constant=reject_constant)


def file_record(path):
    no_links(path)
    return dict(exists=path.is_file(), sha256=sha256_file(path) if path.is_file() else None)


def source_comparison(root, expected):
    records = {}
    for name, digest in expected.items():
        record = file_record(repo_file(root, name))
        record.update(expected_sha256=digest, matches=record["sha256"] == digest)
        records[name] = record
    return records


def inspect_attempt(directory, source_root):
    record = dict(directory=directory.name, job_json_count=0, problems=[])
    match = re.search(r"_seed(\d+)$", directory.name)
    record["seed"] = int(match[1]) if match else None
    paths = sorted(directory.glob("*.json"))
    jobs = [path for path in paths if path.name not in {"manifest.json", "cohort.json"}]
    record["job_json_count"] = len(jobs)
    record["files"] = {path.name: file_record(path) for path in paths}
    record["status"] = "INCOMPLETE_EXCLUDED_ATTEMPT"
    if not all((directory / name).is_file() for name in ("manifest.json", "cohort.json")):
        return record
    try:
        manifest = read_json(directory / "manifest.json")
        cohort = read_json(directory / "cohort.json")
        seed = record["seed"]
        if (manifest["seed"] != seed or cohort["seeds"] != [seed]
                or manifest["jobs"] != 30 or len(jobs) != 30
                or manifest["failed"] != [] or cohort["failed"] != []
                or manifest["window"] != 5000000 or cohort["window"] != 5000000
                or manifest["profile"] != "near" or cohort["profile"] != "near"
                or manifest["confirmation_seeds"] is not True):
            raise ValueError("incomplete or mismatched seed identity")
        results = manifest["results"]
        names = [result["path"] for result in results]
        if len(names) != 30 or len(set(names)) != 30 or set(names) != {p.name for p in jobs}:
            raise ValueError("manifest job paths do not bijectively match this directory")
        for result in results:
            job = read_json(repo_file(directory, result["path"]))
            if (job["status"] != "PASS" or job["job"]["seed"] != seed
                    or job["trace_sha256"] != result["trace_sha256"]
                    or job["job"]["window"] != manifest["window"]
                    or job["policy"] != result["policy"]
                    or job["lane"] != result["lane"]):
                raise ValueError(f"job identity/result mismatch: {result['path']}")
        if not cohort["source_hashes"]:
            raise ValueError("empty source inventory")
        record["current_source_comparison"] = source_comparison(source_root, cohort["source_hashes"])
        record["status"] = "COMPLETE_FILES_OBSERVED"
        record["source_drift"] = [name for name, value in record["current_source_comparison"].items()
                                  if not value["matches"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        record["problems"].append(str(exc))
    return record


def confirmation_inventory(root):
    base = root / "artifacts/implementation/dynamic-role-switch-v2-confirm"
    attempts = [inspect_attempt(no_links(path), root) for path in sorted(base.glob("*"))
                if path.is_dir()]
    complete = Counter(row["seed"] for row in attempts if row["status"] == "COMPLETE_FILES_OBSERVED")
    return dict(attempts=attempts, complete_directory_count=sum(complete.values()),
                missing_seeds=[seed for seed in range(7401, 7421) if complete[seed] == 0],
                duplicate_complete_seeds=[seed for seed, count in complete.items() if count > 1],
                scope="Files and embedded identities only; no new campaign acceptance or simulation")


def inspect_mapping(root, bundle):
    directory = root / "artifacts/fastx" / bundle
    record = dict(bundle=bundle, status="INCOMPLETE", problems=[])
    try:
        receipt = read_json(directory / "download-manifest.json")
        manifest = read_json(directory / "manifest.json")
        if receipt["transfer_exit"] != 0:
            raise ValueError("nonzero download status")
        record["download_receipt"] = file_record(directory / "download-manifest.json")
        record["files"] = source_comparison(directory, receipt["files"])
        required = {"manifest.json", "profile.json", "run_config.tcl", "parameters.json",
                    "output/cgof_unit_top.syn.v", "output/cgof_unit_top.syn.sdc",
                    "reports/area.rpt", "reports/pt_timing_max.rpt", "reports/pt_timing_min.rpt",
                    "reports/pt_constraints.rpt", "reports/pt_status.rpt"}
        if not required.issubset(record["files"]):
            raise ValueError("download receipt lacks required inputs/reports")
        if not all(item["matches"] for item in record["files"].values()):
            raise ValueError("ARTIFACT_HASH_MISMATCH")
        record["parameters"] = manifest["parameters"]
        record["profile_canonical_sha256"] = manifest["profile_canonical_sha256"]
        record["library_sha256"] = read_json(directory / "profile.json")["library"]["sha256"]
        record["current_rtl"] = source_comparison(root, {name: manifest["file_sha256"][name]
                                                        for name in CGOF_SOURCES})
        record["status"] = ("SOURCE_DRIFT" if not all(value["matches"] for value in record["current_rtl"].values())
                            else "HASH_BOUND_INPUTS_OBSERVED")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        record["problems"].append(str(exc))
    return record


def baseline_inventory(root):
    path = root / BASELINE
    record = dict(path=BASELINE, status="INCOMPLETE", problems=[])
    try:
        record.update(file_record(path))
        if record["sha256"] != BASELINE_SHA:
            raise ValueError("baseline acceptance index pin mismatch")
        value = read_json(path)
        identities = [(case["policy"], case["seed"], case["arm"]) for case in value["cases"]]
        expected = {(policy, seed, arm) for policy in ("fcfs", "rr", "fai-main")
                    for seed in (509, 510, 511) for arm in ("A", "B")}
        if len(identities) != 18 or set(identities) != expected:
            raise ValueError("baseline identities are incomplete or duplicate")
        record.update(status="PINNED_ACCEPTANCE_INDEX_OBSERVED", identities=identities,
                      scope="Historical acceptance index only; raw captures not revalidated by this audit")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        record["problems"].append(str(exc))
    return record


def formal_inventory(root, bundle):
    directory = root / "artifacts/fastx" / bundle
    record = dict(bundle=bundle, status="INCOMPLETE", problems=[])
    try:
        receipt = read_json(directory / "download-manifest.json")
        record["files"] = source_comparison(directory, receipt["files"])
        if (receipt["transfer_exit"] != 0 or not record["files"]
                or not {"reports/status.rpt", "reports/verify.rpt"}.issubset(record["files"])
                or not all(value["matches"] for value in record["files"].values())):
            raise ValueError("incomplete or changed formal download")
        record["status"] = "HASH_BOUND_REPORTS_OBSERVED_NOT_REACCEPTED"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        record["problems"].append(str(exc))
    return record


def audit(root):
    confirmation = confirmation_inventory(root)
    capacity = []
    for directory in sorted((root / "artifacts/implementation/capacity-absorption").glob("*")):
        if directory.is_dir():
            paths = sorted(directory.glob("*.json"))
            capacity.append(dict(directory=directory.name, files={p.name: file_record(p) for p in paths},
                                 status="OBSERVED_ONLY_NOT_ACCEPTED"))
    return dict(schema="cxl-fastx-power-input-audit-v1",
                observed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                status="INCOMPLETE", ready_for_saif_power=False, power="NOT_RUN",
                cohort_status="OWNER_FROZEN_509_511_AB_20261107",
                cohort=dict(seeds=[509, 510, 511], arms=["A", "B"],
                            policies=["fcfs", "rr", "fai-main", "cgof1", "cgof2"],
                            decision_date="2026-11-07"),
                harness_status="UNSUPPORTED_TOP_MODULE",
                blockers=["Frozen cohort requires hash-bound matched CGOF captures",
                          "CGOF adapter and gate-level pilot require validation",
                          "Approved compute location and actual power license checkout unverified"],
                confirmation=confirmation, capacity=capacity,
                cgof={key: inspect_mapping(root, bundle) for key, bundle in CGOF_BUNDLES.items()},
                formal=[formal_inventory(root, bundle) for bundle in FORMAL_BUNDLES],
                baseline=baseline_inventory(root))


def write_report(root, out):
    no_links(out.absolute())
    target = out.resolve()
    allowed = (ROOT / "artifacts").resolve()
    evidence_artifacts = (root / "artifacts").resolve()
    if (target == allowed or not target.is_relative_to(allowed)
            or target.is_relative_to(evidence_artifacts)):
        raise ValueError("output must be a fresh worktree artifacts child outside input artifacts")
    if target.exists():
        raise ValueError("output directory already exists")
    report = audit(root)
    target.mkdir(parents=True, exist_ok=False)
    data = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    with (target / "audit.json").open("xb") as stream:
        stream.write(data)
    with (target / "SHA256SUMS").open("x", encoding="ascii") as stream:
        stream.write(hashlib.sha256(data).hexdigest() + "  audit.json\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True, help="read-only repository root")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = no_links(args.evidence_root.absolute()).resolve(strict=True)
        report = write_report(root, args.out)
    except (OSError, ValueError, TypeError) as exc:
        print(f"INCOMPLETE: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(dict(status=report["status"], power=report["power"],
                          complete_directories=report["confirmation"]["complete_directory_count"])))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
