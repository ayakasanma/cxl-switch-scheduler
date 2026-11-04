#!/usr/bin/env python3
"""Index accepted declared runs without converting plans or model screens into acceptance.

The input paths are deliberately explicit.  The indexer only looks for the named
revision artifacts below those paths; it does not walk the repository.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import zipfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from revision_matrix import canonical_sha, matrix as current_matrix  # noqa: E402


MATRIX_SCHEMA = "cxl-revision-matrix-v1"
RUN_SPEC_SCHEMA = "cxl-revision-run-spec-v1"
PERFORMANCE_SCHEMA = "cxl-revision-performance-v1"
SCOPE_SCHEMA = "cxl-revision-performance-scope-v1"
INSIGHT_SCHEMA = "cxl-insight-screen-v1"

POLICY = dict(FCFS=0, RR=1, RR1=1, RR10=1, MAIN=2, MAIN1W=2, ALG2=3, BLISS=4)
LANES = ("trained", "cold-A", "cold-B")
STATUSES = ("NOT_RUN", "RUNNING", "PASS", "FAIL", "UNRESOLVED")
SKIP_DIRS = {".git", "build", "__pycache__", ".pytest_cache"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")

POWER_MANIFEST = "cxl-matched-trained-power-acceptance-v1"
POWER_SOURCE_SHA = "52311700ace139bbbae6ed2f324b17404291322c60ed18df4247a71e86f61918"
POWER_MAPPED_SHA = {
    "fcfs": "04368dbe0433e9a4e541bbdd1a2a0fa322701fc9b972e0737bfd6ef9421a5a69",
    "rr": "da987825c96c48f19261eb745cd65a2196d9c3bf2304670f4396ddf2f8375d91",
    "fai-main": "cbcb8f5699214c39c860cdae6f9d442149c03e96086db98d301b09efc5ec45c3",
}
# Parent review must pin each semantic release after independent review.
# An input manifest cannot nominate its own trust anchor.
POWER_REVIEW_RELEASE_SHA256 = frozenset({
    "5b58cbf94de2ffb16f4841f4621dc0ec694a353d520d94330db53c557ac65aff",  # detached RR511A
    "9d5b5148caf27be893edd450690d7224aca2dc6c59725eeffaada574ce2a8cca",  # detached RR511B
    "c97c90c0205085e2228c10cb1dfb82ee80e8d652cde40b5ac1ab7729f4ce739d",  # detached Main511A
    "0ef576f6744ed94371e317d3c2b282dd97e441471ecde05b6e8dba3b8bf4f7f4",  # detached Main511B
    "2b6888ef0c6a3a87ba3c05b069514e5e30a860af7082e41050aa8e7344df280f",  # detached FCFS511B
    "b401165cc68e36c0cf29601f95de4ae6bfa9218f4af6cfb7903415edaff7c89f",  # detached FCFS511A only
    "a99c7cb934407753df9ed1d394b314c08d05f26c998f4d7228071c9b420a2f92",  # recovered Main510B
    "63d1278c39245511d136f4d6413c6eed49b2274f04325d9ec75f594cad655c66",  # recovered Main510A
    "4158918ed4d602d5f0427f904a9074b14e6ff44b6af926808814395179abca22",  # Main509A only
    "846560b2efffdb832d417b5e95adbc77cf3660a187258eaf75b7b75dec09c008",  # recovered FCFS509A
    "cf4211b15b16df0024b511b40370a80cb1801c593555e3e95f08b18ab69cf92f",  # FCFS509B
    "6c522abdb73c562ab510ece17b71be2dd671c3bdfafb11e193609ef1f7843d54",  # RR509A
    "8651b8b42391ad9628be00cd9fa71bc16c0cbc0d643212d51cdc61e44fcf28fd",  # RR509B
    "7f0477ea451d003355c4e8af064408e41b58b21e58fe500959f388feaa2ef82e",  # recovered Main509B
    "607dd4a59a50a00405c98a566ef37f5a600e378eb79a87bd2ef5081568ff77be",  # FCFS510A
    "fab86204015b85623eb40c15c96a421e1394277ce02003990a38423d2a98b2eb",  # FCFS510B
    "e1f32b3575df13039aeeed10dfaf1181d34e39028c716164d1f62c75aaaf595e",  # RR510A
    "3be1c1bbec8fc7ca472858643b2af72e36d59394f24dcd30af9089cd5fc6857b",  # RR510B
})
POWER_RECOVERED_REVIEW_SHA256 = "a0494a4f23daf63e8d3dc3475f365c4c8d890c3eb3420ad8be7f8de078ae4b82"
POWER_MAINB_ADAPTER_SHA = "09cb90b693515baac71134e5317e6aa621089898bdb41343d4b06127916d48d0"
POWER_MAINB_CALLER_SHA = "53e49f6dcf97412a32503f9d505869836f1acade03176773e04494ceb021f87a"
POWER_MAINB_FROZEN_REVIEWER_SHA = "0e1b764b144ebcfc2021936dc75c664816a8ee3bacce02bbb28a0e33e1060fb1"
POWER_MAINB_BASE_SHA = "42169bc28f1040a1233857d096e79734d46af68c88140a3132aba43004271dd0"
POWER_MAIN510A_ADAPTER_SHA = "53a5e41e4dfc370bad4ceb81ae8eed45b961eeb04863bdc5a9a557cc1bf2dc44"
POWER_MAIN510A_REVIEW_SHA = "b60278ea85b72aef3d88eb89c863e4600b2b9fd731d84478fdc91629b6ed8336"
POWER_MAIN510B_ADAPTER_SHA = "835a09407e31ed3e9e93bbd1a994756630e35c250d265e18767b2adc747e4fa8"
POWER_DETACHED_REVIEWER_SHA = "4d04b00deac1a2b19cd24abab70f2cdeb1439daed407674bdd127d9f52fcf4e2"
POWER_DETACHED_PLAN_SHA = "f5d3a1f3f486e2e00e7cbffe952010c3695d837474ae0264029c908c67a9be78"
POWER_POLICY = {"FCFS": "fcfs", "RR10": "rr", "MAIN": "fai-main"}
POWER_RUNTIME = ("scripts/check_power_replay.py", "scripts/run_power_pilot.sh",
                 "sim/power/tb_power.sv", "sta/power_pt.tcl")

# Parent-released 2026-10-24 freeze and independently accepted gate inputs.
# These anchors prevent a self-consistent, fabricated release from granting acceptance.
DAC_SPEC_SCHEMA = "cxl-dac-performance-spec-v1"
DAC_SOURCE_SHA = "4eca15454a0ba1c75a88e5f0431f32730a50c02bc047fa8ca3a899715b206227"
DAC_CORE_SHA = "800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86"
DAC_BINDING_SHA = {
    "native_bindings": "a34fa32ecacb213d39e0d1b6f53c5da18bc457b71769a419e391fa4ac48d6c18",
    "screen_bindings": "28e3dc360df2104f79804e3e4e326c0c9629176fbd89243bb9bb6b354c978e9e",
}
DAC_PILOT_SHA = {
    "DAC2": "dcb4d4b9d423dacdbf4c0c43ff3c9bf9c3da5214e57f3c3977aa4a13cda7147b",
    "DAC1": "0b9688703b90039666a7e8de6a74cbab741ca8b09c34444ca3213bfb64e93161",
}
DAC_CORE_PATHS = tuple("""
AGENTS.md
refc/cxl_model/__init__.py
refc/cxl_model/common_ctrl_model.py
refc/cxl_model/fai_alg2_model.py
refc/cxl_model/fai_main_model.py
refc/cxl_model/fcfs_model.py
refc/cxl_model/fifo_model.py
refc/cxl_model/revision_baselines.py
refc/cxl_model/rr_model.py
rtl/common/cxl_desc_fifo.sv
rtl/common/cxl_fai_main_sched.sv
rtl/common/cxl_fcfs_sel.sv
rtl/common/cxl_out_hold.sv
rtl/common/cxl_rr_sched.sv
rtl/experimental/cxl_bliss_sched.sv
rtl/experimental/cxl_fai_variant_sched.sv
rtl/experimental/filelist.f
rtl/experimental/switch_experiment_top.sv
rtl/include/cxl_sched_pkg.sv
scripts/revision_matrix.py
scripts/revision_statistics.py
scripts/run_revision_experiments.py
scripts/run_verify.py
scripts/test_revision_experiments.py
scripts/wsl_env.sh
sim/common/hier_util.py
sim/common/traffic_trace.py
sim/experimental/Makefile
sim/experimental/revision_traffic.py
sim/experimental/test_baseline_models.py
sim/experimental/test_experiment_top.py
sim/experimental/test_revision_performance.py
sim/experimental/test_revision_traffic.py
sim/performance/followup.py
sim/performance/hog_sparse.py
sim/switch_top_fai/fai_stream.py
specs/APPROVAL.md
specs/CXL_SPEC.md
specs/DECISIONS.md
""".split())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def safe_relpath(name: str) -> bool:
    if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or ":" in name:
        return False
    parts = Path(name).parts
    return bool(parts) and ".." not in parts and not any(p in ("", ".") for p in parts)


def hash64(value) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def expected_params(row: dict) -> dict:
    if row.get("policy") not in POLICY:
        raise ValueError(f"policy {row.get('policy')!r} has no production parameter mapping")
    return dict(
        N_SRC=row["n_src"],
        POLICY=POLICY[row["policy"]],
        DEPTH=row["depth"],
        RR_QUANTUM=row["rr_quantum"],
        FAI_W=row["window"],
        HIGH_QUOTA=row["high_quota"],
        MAIN_1W=int(row["policy"] == "MAIN1W"),
    )


def lane_cold(lane: str):
    if lane == "trained":
        return False
    if lane == "cold-A":
        return "A"
    if lane == "cold-B":
        return "B"
    raise ValueError(f"unknown lane {lane!r}")


def lane_training(row: dict, lane: str) -> int:
    return row["training_cycles"] if lane == "trained" else 0


def expected_lanes(row: dict) -> tuple[str, ...]:
    if row.get("evidence_kind") != "RTL_REQUIRED":
        return ()
    # Each matrix row is one declared run; cold replays are separate benefit evidence.
    return ("trained",)


def expected_config(row: dict, lane: str) -> dict:
    params = expected_params(row)
    cold = lane_cold(lane)
    name = row["id"] + (f"-cold{cold}" if cold else "-trained")
    return dict(
        name=name,
        top="switch_experiment_top",
        filelist="rtl/experimental/filelist.f",
        params=params,
        default_params={},
        test_dir="sim/experimental",
        test_module="test_revision_performance",
        seeds=[row["seed"]],
        env=dict(
            CXL_REVISION_JOB=json.dumps(row, sort_keys=True),
            CXL_REVISION_PARAMS=json.dumps(params, sort_keys=True),
            CXL_REVISION_COLD=json.dumps(cold),
        ),
        expect_tests=1,
        timeout_s=172800,
        artifacts=[
            dict(file="revision_performance.json", required=True),
            dict(file="revision_failure.json", required=False),
        ],
    )


def expected_result_path(config: dict, row: dict) -> str:
    return f"results/cocotb_{config['name']}_seed{row['seed']}__revision_performance.json"


def result_payload_check(result: dict, row: dict, lane: str, config: dict) -> list[str]:
    problems: list[str] = []
    expected = expected_config(row, lane)
    cold = lane_cold(lane)
    required = dict(
        schema=PERFORMANCE_SCHEMA,
        evidence_kind="RTL",
        status="PASS",
        job=row,
        params=expected_params(row),
        cold=bool(cold),
        cold_cohort=cold or None,
        training_cycles=lane_training(row, lane),
        production_evidence=True,
        sensitivity_evidence=False,
    )
    for key, value in required.items():
        if result.get(key) != value:
            problems.append(f"result.{key} mismatch or missing")
    if type(result.get("cold")) is not bool:
        problems.append("result.cold must be a boolean")
    if not hash64(result.get("trace_sha256")):
        problems.append("result.trace_sha256 is missing or not a SHA256")
    if not isinstance(result.get("metrics"), dict):
        problems.append("result.metrics missing")
    if not isinstance(result.get("windows"), list):
        problems.append("result.windows missing")
    if result.get("job", {}).get("id") != row["id"]:
        problems.append("result job id does not match matrix row")
    if result.get("params") != expected["params"]:
        problems.append("result params do not match matrix row")
    return problems


def config_payload_check(config: dict, row: dict, lane: str) -> list[str]:
    problems: list[str] = []
    expected = expected_config(row, lane)
    for key in (
        "name", "top", "filelist", "params", "default_params", "test_dir",
        "test_module", "seeds", "env", "expect_tests", "timeout_s", "artifacts",
    ):
        if config.get(key) != expected[key]:
            problems.append(f"frozen config {key} does not match exact matrix job")
    try:
        encoded = json.loads(config["env"]["CXL_REVISION_JOB"])
    except (KeyError, TypeError, json.JSONDecodeError):
        problems.append("frozen config CXL_REVISION_JOB is not valid JSON")
    else:
        if encoded != row:
            problems.append("frozen config job differs from matrix row")
    try:
        encoded_params = json.loads(config["env"]["CXL_REVISION_PARAMS"])
    except (KeyError, TypeError, json.JSONDecodeError):
        problems.append("frozen config CXL_REVISION_PARAMS is not valid JSON")
    else:
        if encoded_params != expected_params(row):
            problems.append("frozen config params differ from matrix row")
    return problems


def _read_zip_bytes(path: Path) -> tuple[dict[str, bytes], list[str]]:
    """Read a small archive with duplicate, traversal and link checks."""
    problems: list[str] = []
    entries: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name = info.filename
                if not safe_relpath(name):
                    problems.append(f"unsafe archive member {name!r}")
                    continue
                if info.is_dir():
                    continue
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    problems.append(f"archive member is a link: {name}")
                    continue
                if name in entries:
                    problems.append(f"duplicate archive member: {name}")
                    continue
                entries[name] = archive.read(info)
    except (OSError, zipfile.BadZipFile) as exc:
        problems.append(f"unreadable archive: {exc}")
    return entries, problems


def _bundle_files(bundle: Path) -> list[Path]:
    files: list[Path] = []
    for base, dirs, names in os.walk(bundle):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            path = Path(base) / name
            if path.name == "evidence.zip":
                continue
            files.append(path)
    return files


def _manifest_problems(name: str, manifest, archive_bytes: dict[str, bytes]) -> list[str]:
    problems: list[str] = []
    if not isinstance(manifest, dict) or not manifest:
        return [f"{name} is missing or empty"]
    for member, digest in manifest.items():
        if not safe_relpath(member):
            problems.append(f"{name} contains unsafe member {member!r}")
            continue
        if not hash64(digest):
            problems.append(f"{name} has invalid digest for {member}")
            continue
        if member not in archive_bytes:
            problems.append(f"{name} member absent from sources.zip: {member}")
        elif sha256_bytes(archive_bytes[member]) != digest:
            problems.append(f"{name} bytes disagree with sources.zip: {member}")
    return problems


def _step_problems(summary: dict, configs: list[dict]) -> list[str]:
    problems: list[str] = []
    steps = summary.get("steps")
    if not isinstance(steps, list):
        return ["summary.steps missing"]
    names = [s.get("name") for s in steps if isinstance(s, dict)]
    if len(names) != len(set(names)):
        problems.append("summary has duplicate step names")
    by_name = {s.get("name"): s for s in steps if isinstance(s, dict)}
    expected_cocotb = {f"cocotb:{c['name']}_seed{c['seeds'][0]}" for c in configs}
    expected_lint = {f"lint:{c['name']}" for c in configs}
    for name in sorted(expected_cocotb | expected_lint):
        step = by_name.get(name)
        if not step:
            problems.append(f"summary missing step {name}")
            continue
        if step.get("status") != "PASS":
            problems.append(f"summary step {name} is {step.get('status')}")
        exits = step.get("exit_codes")
        if not isinstance(exits, dict) or not exits:
            problems.append(f"summary step {name} has no tool exits")
        elif any(v != 0 for v in exits.values()):
            problems.append(f"summary step {name} has a nonzero tool exit")
        if name.startswith("cocotb:"):
            if step.get("tests", 0) < 1:
                problems.append(f"summary step {name} has no tests")
            if any(step.get(k, 0) for k in ("failures", "errors", "skipped")):
                problems.append(f"summary step {name} has failed/error/skipped tests")
    pytest_steps = [s for s in steps if isinstance(s, dict) and s.get("kind") == "pytest"]
    if not pytest_steps:
        problems.append("summary has no pytest step")
    for step in pytest_steps:
        if step.get("status") != "PASS" or step.get("tests", 0) < 1:
            problems.append(f"pytest step {step.get('name')} did not pass with tests")
        if not isinstance(step.get("exit_codes"), dict) or not step["exit_codes"]:
            problems.append(f"pytest step {step.get('name')} has no exits")
        elif any(v != 0 for v in step["exit_codes"].values()):
            problems.append(f"pytest step {step.get('name')} has a nonzero exit")
    scope_steps = [s for s in steps if isinstance(s, dict) and s.get("kind") == "scope"]
    if not scope_steps:
        problems.append("summary has no scope step")
    elif any(s.get("status") != "PASS" for s in scope_steps):
        problems.append("summary scope step did not pass")
    return problems


def inspect_performance_bundle(bundle: Path, rows_by_id: dict[str, dict]) -> dict:
    """Inspect one runner directory.  Every absent key is reported explicitly."""
    bundle = bundle.resolve()
    try:
        if load_json(bundle / "frozen-spec.json").get("schema") == DAC_SPEC_SCHEMA:
            return inspect_dac_bundle(bundle, rows_by_id)
    except (OSError, ValueError, AttributeError):
        pass
    record = dict(
        path=str(bundle),
        status="UNRESOLVED",
        schema=None,
        problems=[],
        failures=[],
        configs=[],
        runs=[],
        file_hashes={},
        source_archive=None,
        evidence_archive=None,
        accepted_configs=[],
        matrix_job_ids=[],
        running=False,
        incompatible_schema=False,
    )

    def problem(message: str) -> None:
        if message not in record["problems"]:
            record["problems"].append(message)

    def failure(message: str) -> None:
        if message not in record["failures"]:
            record["failures"].append(message)

    frozen_path = bundle / "frozen-spec.json"
    scope_path = bundle / "revision_scope.json"
    summary_path = bundle / "summary.json"
    before_path = bundle / "source_hashes_before.json"
    after_path = bundle / "source_hashes_after.json"
    sources_zip = bundle / "sources.zip"
    evidence_zip = bundle / "evidence.zip"
    known = [
        frozen_path, scope_path, summary_path, before_path, after_path,
        sources_zip, evidence_zip,
    ]
    for path in known:
        if path.is_file():
            record["file_hashes"][str(path.relative_to(bundle))] = sha256_file(path)

    frozen = None
    if not frozen_path.is_file():
        problem("missing frozen-spec.json")
    else:
        try:
            frozen = load_json(frozen_path)
        except (OSError, json.JSONDecodeError) as exc:
            problem(f"invalid frozen-spec.json: {exc}")
    if isinstance(frozen, dict):
        record["schema"] = frozen.get("schema")
        if frozen.get("schema") != RUN_SPEC_SCHEMA:
            record["incompatible_schema"] = True
            problem("frozen-spec.json schema is not cxl-revision-run-spec-v1")
        if frozen.get("pilot") is not False:
            problem("frozen spec is not a production run")
        if frozen.get("production_review_acknowledged") is not True:
            problem("production review is not acknowledged in frozen spec")

    scope = None
    if not scope_path.is_file():
        problem("missing revision_scope.json")
    else:
        try:
            scope = load_json(scope_path)
        except (OSError, json.JSONDecodeError) as exc:
            problem(f"invalid revision_scope.json: {exc}")
    if isinstance(scope, dict):
        if scope.get("schema") != SCOPE_SCHEMA:
            record["incompatible_schema"] = True
            problem("revision_scope.json schema is not cxl-revision-performance-scope-v1")
        if scope.get("status") == "FAIL":
            failure("revision_scope status is FAIL")
        elif scope.get("status") != "PASS":
            problem("revision_scope status is not PASS")
        if scope.get("production_evidence") is not True:
            problem("revision_scope production_evidence is not true")
        if scope.get("sensitivity_evidence") is not False:
            problem("revision_scope sensitivity_evidence is not false")
        if scope.get("problems"):
            failure("revision_scope records problems")

    summary = None
    if not summary_path.is_file():
        problem("missing summary.json")
    else:
        try:
            summary = load_json(summary_path)
        except (OSError, json.JSONDecodeError) as exc:
            problem(f"invalid summary.json: {exc}")
    if isinstance(summary, dict):
        overall = summary.get("overall")
        if overall == "FAIL":
            failure("summary overall is FAIL")
        elif overall == "RUNNING":
            record["running"] = True
            problem("summary overall is RUNNING")
        elif overall != "PASS":
            problem("summary overall is not PASS")
        if summary.get("production_evidence") is not True:
            problem("summary production_evidence is not true")
        if summary.get("sensitivity_evidence") is not False:
            problem("summary sensitivity_evidence is not false")
        if summary.get("milestone_acceptance_scope") is not True:
            problem("summary milestone_acceptance_scope is not true")
        counts = summary.get("counts")
        if not isinstance(counts, dict):
            problem("summary.counts missing")
        else:
            for key in ("fail", "not_run"):
                if counts.get(key, 0) != 0:
                    failure(f"summary counts.{key} is nonzero")
            for key in ("failures", "errors", "skipped"):
                if counts.get(key, 0) != 0:
                    failure(f"summary counts.{key} is nonzero")

    before = None
    after = None
    for label, path in (("before", before_path), ("after", after_path)):
        if not path.is_file():
            problem(f"missing source_hashes_{label}.json")
            continue
        try:
            value = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            problem(f"invalid source_hashes_{label}.json: {exc}")
            continue
        if not isinstance(value, dict):
            problem(f"source_hashes_{label}.json is not an object")
        elif label == "before":
            before = value
        else:
            after = value
    if isinstance(before, dict) and isinstance(after, dict) and before != after:
        failure("source hashes changed before/after the run")
    if isinstance(frozen, dict) and isinstance(before, dict):
        record["source_sha256"] = canonical_sha(before)
        shared = {name: before.get(name) for name in DAC_CORE_PATHS}
        if canonical_sha(shared) == DAC_CORE_SHA:
            record["core_source_sha256"] = DAC_CORE_SHA
        if frozen.get("source_sha256") != canonical_sha(before):
            failure("frozen-spec source_sha256 does not bind source_hashes_before.json")
    if isinstance(scope, dict) and isinstance(before, dict):
        if scope.get("source_hashes") != before:
            failure("revision_scope source hashes differ from source_hashes_before.json")

    source_bytes: dict[str, bytes] = {}
    if not sources_zip.is_file():
        problem("missing sources.zip")
    else:
        source_bytes, zip_problems = _read_zip_bytes(sources_zip)
        for message in zip_problems:
            failure(f"sources.zip: {message}")
        record["source_archive"] = dict(
            path=str(sources_zip),
            sha256=sha256_file(sources_zip),
            members=sorted(source_bytes),
        )
        if isinstance(before, dict):
            for message in _manifest_problems("source_hashes_before.json", before, source_bytes):
                failure(message)
            extra = set(source_bytes) - set(before)
            allowed_context = {name for name in extra if name.startswith("context/")}
            unexpected = sorted(extra - allowed_context)
            if unexpected:
                failure(f"sources.zip has unmanifested members: {unexpected}")
            required_sources = {
                "rtl/experimental/filelist.f", "scripts/revision_matrix.py",
                "scripts/run_revision_experiments.py", "scripts/run_verify.py",
                "sim/experimental/revision_traffic.py",
                "sim/experimental/test_revision_performance.py",
                "refc/cxl_model/revision_baselines.py",
            }
            filelist = source_bytes.get("rtl/experimental/filelist.f", b"").decode("utf-8")
            for line in filelist.splitlines():
                name = line.split("//", 1)[0].strip()
                if name:
                    if not safe_relpath(name) or not name.endswith(".sv"):
                        failure(f"invalid source filelist entry: {name}")
                    else:
                        required_sources.add(name)
            if required_sources - set(before):
                failure(f"source manifest missing dependencies: {sorted(required_sources - set(before))}")

    configs = []
    if isinstance(frozen, dict):
        raw_configs = frozen.get("configs")
        if not isinstance(raw_configs, list) or not raw_configs:
            problem("frozen-spec configs missing or empty")
        else:
            configs = raw_configs
            if frozen.get("jobs_sha256") != canonical_sha(configs):
                failure("frozen-spec jobs_sha256 does not bind its configs")
    else:
        problem("cannot validate configs without frozen-spec.json")

    if isinstance(scope, dict):
        if scope.get("expected_jobs") != len(configs):
            failure("revision_scope expected_jobs does not equal frozen config count")
        if scope.get("valid_jobs") != len(scope.get("runs", [])):
            failure("revision_scope valid_jobs does not equal its run count")
        if scope.get("expected_jobs") != scope.get("valid_jobs"):
            failure("revision_scope expected_jobs != valid_jobs")
    if isinstance(summary, dict):
        if summary.get("expected_jobs") != len(configs):
            failure("summary expected_jobs does not equal frozen config count")
        if summary.get("scope") == "W256-sensitivity":
            problem("W256 sensitivity run is not matrix production evidence")
        if summary.get("full_498_matrix_executed") is True:
            problem("run claims full-matrix execution; index does not infer matrix completion")

    config_records: list[dict] = []
    config_by_name: dict[str, dict] = {}
    lanes_in_bundle: set[str] = set()
    for raw in configs:
        cfg_record = dict(config=raw, problems=[], lane=None, row_id=None, name=None)
        if not isinstance(raw, dict):
            cfg_record["problems"].append("config is not an object")
            config_records.append(cfg_record)
            continue
        name = raw.get("name")
        cfg_record["name"] = name
        if not isinstance(name, str):
            cfg_record["problems"].append("config name missing")
        elif name in config_by_name:
            failure(f"duplicate frozen config name {name}")
        else:
            config_by_name[name] = raw
        job = None
        try:
            job = json.loads(raw["env"]["CXL_REVISION_JOB"])
        except (KeyError, TypeError, json.JSONDecodeError):
            cfg_record["problems"].append("config env CXL_REVISION_JOB is invalid")
        cold = None
        try:
            cold = json.loads(raw["env"]["CXL_REVISION_COLD"])
        except (KeyError, TypeError, json.JSONDecodeError):
            cfg_record["problems"].append("config env CXL_REVISION_COLD is invalid")
        if isinstance(cold, bool):
            lane = "trained" if cold is False else None
        elif cold in ("A", "B"):
            lane = f"cold-{cold}"
        else:
            lane = None
        cfg_record["lane"] = lane
        if lane is None:
            cfg_record["problems"].append("config cold lane is not trained/A/B")
        else:
            lanes_in_bundle.add(lane)
        row = None
        if isinstance(job, dict) and job.get("id") in rows_by_id:
            row = rows_by_id[job["id"]]
            cfg_record["row_id"] = row["id"]
            if row["id"] not in record["matrix_job_ids"]:
                record["matrix_job_ids"].append(row["id"])
            cfg_record["problems"].extend(config_payload_check(raw, row, lane) if lane else [])
        else:
            cfg_record["problems"].append("config job is not an exact current matrix row")
        if row is not None and lane:
            try:
                expected = expected_config(row, lane)
            except ValueError as exc:
                cfg_record["problems"].append(str(exc))
                expected = None
            if expected is not None:
                if name != expected["name"]:
                    cfg_record["problems"].append("config name does not match exact job/lane")
                if raw.get("seeds") != [row["seed"]]:
                    cfg_record["problems"].append("config seed does not match exact job seed")
                if raw.get("params") != expected["params"]:
                    cfg_record["problems"].append("config params do not match exact job")
        config_records.append(cfg_record)
        for message in cfg_record["problems"]:
            problem(f"config {name or '<unnamed>'}: {message}")

    if len(lanes_in_bundle) > 1:
        problem("one bundle mixes trained/cold lanes")
    if isinstance(scope, dict):
        scope_runs = scope.get("runs")
        if not isinstance(scope_runs, list):
            problem("revision_scope runs missing")
        else:
            run_by_name = {}
            for run in scope_runs:
                if not isinstance(run, dict) or not isinstance(run.get("name"), str):
                    problem("revision_scope has malformed run")
                    continue
                if run["name"] in run_by_name:
                    failure(f"revision_scope duplicate run {run['name']}")
                run_by_name[run["name"]] = run
            expected_names = {f"{c['name']}_seed{c['seeds'][0]}" for c in configs
                              if isinstance(c, dict) and isinstance(c.get("seeds"), list) and c["seeds"]}
            if set(run_by_name) != expected_names:
                failure("revision_scope run names do not equal frozen config names")
            for cfg_record in config_records:
                raw = cfg_record.get("config")
                if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
                    continue
                expected_name = f"{raw['name']}_seed{raw['seeds'][0]}" if raw.get("seeds") else None
                run = run_by_name.get(expected_name)
                if not run:
                    problem(f"revision_scope missing run {expected_name}")
                    continue
                record["runs"].append(dict(
                    name=expected_name,
                    matrix_job_id=cfg_record.get("row_id"),
                    lane=cfg_record.get("lane"),
                    result=run.get("result"),
                    trace_sha256=run.get("trace_sha256"),
                    n_src=run.get("n_src"),
                    policy=run.get("policy"),
                ))

    result_records = []
    if isinstance(scope, dict):
        scope_runs = scope.get("runs") if isinstance(scope.get("runs"), list) else []
        run_by_name = {r.get("name"): r for r in scope_runs if isinstance(r, dict)}
    else:
        run_by_name = {}
    for cfg_record in config_records:
        raw = cfg_record.get("config")
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            continue
        row = rows_by_id.get(cfg_record.get("row_id")) if cfg_record.get("row_id") else None
        lane = cfg_record.get("lane")
        if row is None or lane is None:
            continue
        expected_name = f"{raw['name']}_seed{row['seed']}"
        scope_run = run_by_name.get(expected_name)
        result_rel = expected_result_path(raw, row)
        result_path = bundle / result_rel
        result_record = dict(
            matrix_job_id=row["id"],
            lane=lane,
            seed=row["seed"],
            cohort=("trained" if lane == "trained" else lane[-1]),
            name=expected_name,
            result=result_rel,
            result_sha256=None,
            trace_sha256=None,
            exit_codes=None,
            failures=[],
            missing=[],
            production_evidence=False,
            status="UNRESOLVED",
        )
        if not scope_run:
            result_record["missing"].append("revision_scope run")
        else:
            if scope_run.get("result") != result_rel:
                result_record["failures"].append("scope result path differs from exact runner path")
            if scope_run.get("trace_sha256") and not hash64(scope_run["trace_sha256"]):
                result_record["failures"].append("scope trace hash invalid")
            result_record["trace_sha256"] = scope_run.get("trace_sha256")
            if scope_run.get("n_src") != row["n_src"]:
                result_record["failures"].append("scope n_src differs from matrix")
            if scope_run.get("policy") != row["policy"]:
                result_record["failures"].append("scope policy differs from matrix")
        if not result_path.is_file():
            result_record["missing"].append("result file")
            problem(f"missing result file {result_rel}")
        else:
            result_record["result_sha256"] = sha256_file(result_path)
            try:
                result = load_json(result_path)
            except (OSError, json.JSONDecodeError) as exc:
                result_record["failures"].append(f"invalid result JSON: {exc}")
                result = None
            if isinstance(result, dict):
                result_record["production_evidence"] = result.get("production_evidence") is True
                result_record["trace_sha256"] = result.get("trace_sha256")
                result_problems = result_payload_check(result, row, lane, raw)
                if result.get("status") == "FAIL":
                    result_record["failures"].append("result status is FAIL")
                elif result.get("status") != "PASS":
                    result_record["missing"].append("result status is not PASS")
                if result.get("production_evidence") is not True:
                    result_record["missing"].append("result production_evidence is not true")
                if result.get("sensitivity_evidence") is not False:
                    result_record["missing"].append("result is sensitivity/W256 evidence")
                if scope_run and result.get("trace_sha256") != scope_run.get("trace_sha256"):
                    result_record["failures"].append("result trace hash differs from scope")
                if result_problems:
                    result_record["failures"].extend(result_problems)
                if cfg_record.get("problems"):
                    result_record["failures"].append("result belongs to a mismatched frozen config")
                if isinstance(summary, dict):
                    step_name = f"cocotb:{raw['name']}_seed{row['seed']}"
                    step = next((s for s in summary.get("steps", [])
                                 if isinstance(s, dict) and s.get("name") == step_name), None)
                    if not step:
                        result_record["missing"].append("summary cocotb step")
                    else:
                        result_record["exit_codes"] = step.get("exit_codes")
                        result_record["failures"].extend(
                            f"step {step_name}: failures/errors/skipped"
                            for key in ("failures", "errors", "skipped")
                            if step.get(key, 0)
                        )
        if result_record["failures"]:
            result_record["status"] = "FAIL"
            for message in result_record["failures"]:
                failure(f"{expected_name}: {message}")
        elif result_record["missing"]:
            result_record["status"] = "UNRESOLVED"
            for message in result_record["missing"]:
                problem(f"{expected_name}: {message}")
        elif not cfg_record.get("problems") and scope_run:
            result_record["status"] = "PASS"
            cfg_record["accepted"] = True
            record["accepted_configs"].append(expected_name)
        result_records.append(result_record)
    record["configs"] = config_records
    record["runs"] = result_records

    if isinstance(summary, dict):
        for message in _step_problems(summary, [c for c in configs if isinstance(c, dict)]):
            if "FAIL" in message or "nonzero" in message or "failed" in message:
                failure(message)
            else:
                problem(message)

    if evidence_zip.is_file():
        evidence_bytes, evidence_problems = _read_zip_bytes(evidence_zip)
        for message in evidence_problems:
            failure(f"evidence.zip: {message}")
        record["evidence_archive"] = dict(
            path=str(evidence_zip),
            sha256=sha256_file(evidence_zip),
            members=sorted(evidence_bytes),
        )
        current = {}
        for path in _bundle_files(bundle):
            current[path.relative_to(bundle).as_posix()] = path.read_bytes()
        missing_from_archive = sorted(set(current) - set(evidence_bytes))
        extra_in_archive = sorted(set(evidence_bytes) - set(current))
        if missing_from_archive:
            failure(f"evidence.zip omits current files: {missing_from_archive}")
        if extra_in_archive:
            failure(f"evidence.zip has non-current members: {extra_in_archive}")
        changed = sorted(name for name in set(current) & set(evidence_bytes)
                         if current[name] != evidence_bytes[name])
        if changed:
            failure(f"evidence.zip bytes differ from current files: {changed}")
    else:
        problem("missing evidence.zip")

    if record["failures"]:
        record["status"] = "FAIL"
    elif record["running"]:
        record["status"] = "RUNNING"
    elif record["problems"]:
        record["status"] = "UNRESOLVED"
    elif config_records and all(c.get("accepted") for c in config_records):
        record["status"] = "PASS"
    else:
        record["status"] = "UNRESOLVED"
    return record


def expected_dac_config(job: dict, policy: str) -> dict:
    params = dict(N_SRC=job["n_src"], DEPTH=job["depth"], FAI_W=job["window"],
                  HIGH_WEIGHT=2 if policy == "DAC2" else 1)
    return dict(
        name=f"{job['id']}-{policy}-trained", top="dac_unit_top",
        filelist="rtl/experimental/filelist_dac_unit.f", params=params, default_params={},
        test_dir="sim/experimental", test_module="test_dac_performance",
        seeds=[job["seed"]], expect_tests=1, timeout_s=172800,
        env=dict(CXL_REVISION_JOB=json.dumps(job, sort_keys=True),
                 CXL_DAC_SELECTED_POLICY=policy,
                 CXL_DAC_PARAMS=json.dumps(params, sort_keys=True),
                 COCOTB_TEST_FILTER=r"(^|\.)dac_performance$"),
        artifacts=[dict(file="dac_performance.json", required=True),
                   dict(file="dac_performance_failure.json", required=False)],
    )


def inspect_dac_bundle(bundle: Path, rows_by_id: dict[str, dict]) -> dict:
    """Accept only the parent-released DAC freeze; never execute archived code.

    Anchored gate maps bind the already reviewed native/model evidence, including
    its source ZIPs and raw exits. Content-addressed blobs make this independent
    of the original WSL absolute paths. New releases need explicit anchor review.
    """
    bundle = bundle.resolve()
    record = dict(path=str(bundle), status="UNRESOLVED", schema=DAC_SPEC_SCHEMA,
                  problems=[], failures=[], configs=[], runs=[], file_hashes={},
                  source_archive=None, evidence_archive=None, accepted_configs=[],
                  matrix_job_ids=[], running=False, incompatible_schema=False,
                  selected_policy=None, matrix_contribution=0)

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def read(name):
        require(safe_relpath(name), f"unsafe evidence path {name!r}")
        path = bundle / name
        if not path.is_file():
            raise FileNotFoundError(f"missing {name}")
        require(not path.is_symlink() and bundle in path.resolve().parents,
                f"evidence path escapes bundle: {name}")
        record["file_hashes"][name] = sha256_file(path)
        value = load_json(path)
        require(isinstance(value, dict), f"{name} must be an object")
        return value

    try:
        spec = read("frozen-spec.json")
        configs = spec.get("configs")
        policy, pilot = spec.get("selected_policy"), spec.get("pilot")
        record["selected_policy"] = policy
        require(policy in ("DAC2", "DAC1") and type(pilot) is bool,
                "invalid selected policy or pilot flag")
        require(isinstance(configs, list) and bool(configs), "missing frozen DAC configs")
        require(spec.get("jobs_sha256") == canonical_sha(configs), "DAC jobs hash mismatch")
        jobs = []
        for config in configs:
            job = json.loads(config["env"]["CXL_REVISION_JOB"])
            require(isinstance(job, dict), "DAC job must be an object")
            row = rows_by_id.get(job.get("id"))
            eligible = not pilot and policy == "DAC2" and row is not None
            if eligible:
                record["matrix_job_ids"].append(row["id"])
            record["configs"].append(dict(config=config, row_id=row["id"] if eligible else None,
                                          lane="trained", name=config.get("name"), problems=[]))
            if pilot:
                template = next(r for r in rows_by_id.values()
                                if r["group"] == "insight-confirmation")
                expected_job = dict(template, id=f"dac-pilot-s{job['seed']}-w256",
                                    group="dac-pilot", seed=job["seed"], seed_role="exploration",
                                    window=256, training_cycles=512)
                require(type(job["seed"]) is int and job["seed"] in range(509, 514)
                        and canonical_json(job) == canonical_json(expected_job),
                        "DAC pilot is not the exact approved W256 job")
            else:
                require(row is not None and canonical_json(job) == canonical_json(row)
                        and row.get("conditional") is True
                        and row["policy"] == "INSIGHT_WINNER"
                        and row["group"] in ("insight-confirmation", "insight-robustness")
                        and row["window"] == 5_000_000 and row["training_cycles"] == 10_000_000,
                        "DAC job is not an exact approved conditional matrix row")
            require(canonical_json(config) == canonical_json(expected_dac_config(job, policy)),
                    "DAC frozen config mismatch")
            jobs.append(job)
        require(len({j["id"] for j in jobs}) == len(jobs), "duplicate DAC job")
        require(not pilot or len(jobs) == 1, "pilot must contain exactly one job")
        record["matrix_job_ids"] = sorted(set(record["matrix_job_ids"]))

        summary = read("summary.json")
        record["running"] = summary.get("overall") == "RUNNING"
        scope = read("dac_performance_scope.json")
        before, after = read("source_hashes_before.json"), read("source_hashes_after.json")
        require(before == after == scope.get("source_hashes"), "DAC source hashes changed")
        require(spec.get("source_sha256") == canonical_sha(before) == DAC_SOURCE_SHA,
                "DAC sources are not the approved performance freeze")
        shared = {name: before.get(name) for name in DAC_CORE_PATHS}
        require(canonical_sha(shared) == DAC_CORE_SHA, "DAC shared core39 hashes mismatch")
        record["source_sha256"] = canonical_sha(before)
        record["core_source_sha256"] = canonical_sha(shared)

        for filename, field in (("sources.zip", "source_archive"),
                                ("evidence.zip", "evidence_archive")):
            if not (bundle / filename).is_file():
                raise FileNotFoundError(f"missing {filename}")
            members, problems = _read_zip_bytes(bundle / filename)
            require(not problems, f"{filename}: {problems}")
            record[field] = dict(path=str(bundle / filename), sha256=sha256_file(bundle / filename),
                                 members=sorted(members))
            if filename == "sources.zip":
                require(not _manifest_problems("DAC source manifest", before, members),
                        "DAC source ZIP bytes mismatch")
                require(set(members) - set(before) <= {"context/EXECUTION.md"},
                        "DAC source ZIP has unexpected members")
            else:
                current = {}
                for path in _bundle_files(bundle):
                    require(not path.is_symlink() and bundle in path.resolve().parents,
                            "linked or escaping bundle file")
                    current[path.relative_to(bundle).as_posix()] = path.read_bytes()
                require(members == current, "DAC evidence ZIP missing/extra/changed files")

        manifest = read("acceptance/manifest.json")
        binding_groups = ["native_bindings", "screen_bindings", "release_binding"]
        if not pilot:
            binding_groups.append("pilot_bindings")
        all_bindings = {}
        for group in binding_groups:
            entries = spec.get(group)
            require(isinstance(entries, dict) and bool(entries), f"missing DAC {group}")
            require(scope.get(group) == entries, f"scope/spec {group} mismatch")
            if group in DAC_BINDING_SHA:
                require(canonical_sha(entries) == DAC_BINDING_SHA[group],
                        f"unapproved {group}: candidate/native gate binding mismatch")
            if group == "pilot_bindings":
                require(canonical_sha(entries) == DAC_PILOT_SHA[policy],
                        "production lacks the accepted matching-policy W256 pilot binding")
            for original, digest in entries.items():
                require(isinstance(original, str) and hash64(digest), "invalid acceptance binding")
                require(original not in all_bindings or all_bindings[original] == digest,
                        "conflicting acceptance bindings")
                all_bindings[original] = digest
        require(set(manifest) == set(all_bindings), "acceptance manifest binding set mismatch")
        for original, digest in all_bindings.items():
            require(manifest[original] == dict(sha256=digest, archived_as=f"acceptance/{digest}"),
                    "acceptance manifest path/hash mismatch")
            path = bundle / "acceptance" / digest
            require(path.is_file() and not path.is_symlink() and sha256_file(path) == digest,
                    "missing/tampered acceptance blob")
        require(len(spec["release_binding"]) == 1, "exactly one parent release required")
        release_digest = next(iter(spec["release_binding"].values()))
        release = read(f"acceptance/{release_digest}")
        require(release.get("schema") == "cxl-dac-performance-release-v1"
                and release.get("native_released") is True
                and release.get("parent_correctness_accepted") is True
                and release.get("source_hashes") == before
                and all(release.get(g) == spec[g] for g in DAC_BINDING_SHA),
                "parent release does not bind approved sources/native/model gates")
        record["acceptance_binding_sha256"] = {
            group: canonical_sha(spec[group]) for group in binding_groups}

        contribution = len(configs) if not pilot and policy == "DAC2" else 0
        for value, label in ((scope, "scope"), (summary, "summary")):
            require(value.get("selected_policy") == policy, f"{label} selected policy mismatch")
            require(value.get("production_evidence") is (not pilot)
                    and value.get("sensitivity_evidence") is pilot,
                    f"{label} production/sensitivity claim mismatch")
            require(type(value.get("matrix_contribution")) is int
                    and value["matrix_contribution"] == contribution,
                    f"{label} matrix contribution mismatch")
        require(scope.get("schema") == "cxl-dac-performance-scope-v1"
                and scope.get("status") == "PASS" and scope.get("problems") == [],
                "DAC scope failed or incomplete")
        require(summary.get("overall") == "PASS" and summary.get("scope") == "full"
                and summary.get("milestone_acceptance_scope") is True
                and summary.get("full_498_matrix_executed") is False,
                "DAC strict selected summary failed or falsely claims global completion")
        require(type(scope.get("expected_jobs")) is int
                and scope["expected_jobs"] == len(configs), "DAC selected job count mismatch")
        counts = summary.get("counts")
        require(isinstance(counts, dict)
                and all(type(counts.get(k)) is int and counts[k] == 0
                        for k in ("fail", "not_run", "failures", "errors", "skipped")),
                "DAC summary failed/missing counts")
        require(not _step_problems(summary, configs), "DAC strict steps/exits failed or missing")
        steps = summary["steps"]
        expected_steps = {f"lint:{c['name']}" for c in configs}
        expected_steps |= {f"cocotb:{c['name']}_seed{j['seed']}" for c, j in zip(configs, jobs)}
        expected_steps |= {"pytest:dac_performance_runner", "pytest:revision_traffic",
                           "scope:dac-performance"}
        require({s["name"] for s in steps} == expected_steps, "DAC declared step set mismatch")
        for step in steps:
            kind = step["kind"]
            require(kind == step["name"].split(":", 1)[0], "DAC step kind/name mismatch")
            exits = {"lint": {"verilator"}, "pytest": {"pytest"},
                     "cocotb": {"verilate", "make", "simulation"}}.get(kind)
            if exits:
                require(set(step.get("exit_codes", {})) == exits
                        and all(type(v) is int and v == 0 for v in step["exit_codes"].values()),
                        "DAC tool exits absent/nonzero/not numeric")
            if kind in ("pytest", "cocotb"):
                name = step.get("junit")
                require(safe_relpath(name), "missing/unsafe raw JUnit")
                tree = ET.fromstring((bundle / name).read_bytes())
                cases = list(tree.iter("testcase"))
                require(len(cases) == step.get("tests") and len(cases) > 0
                        and not any(list(tree.iter(tag)) for tag in ("failure", "error", "skipped"))
                        and all(int(node.get(k, "0")) == 0 for node in tree.iter()
                                for k in ("failures", "errors", "skipped")),
                        "DAC raw JUnit failed/skipped/count mismatch")
                if kind == "cocotb":
                    require(len(cases) == 1 and cases[0].get("name") == "dac_performance",
                            "DAC raw JUnit test identity mismatch")
                    config = next(c for c in configs if
                                  step["name"] == f"cocotb:{c['name']}_seed{c['seeds'][0]}")
                    seed = str(config["seeds"][0])
                    require([p.get("value") for p in cases[0].iter("property")
                             if p.get("name") == "random_seed"] == [seed],
                            "DAC raw JUnit seed mismatch")
        runs = scope.get("runs")
        require(isinstance(runs, list) and len(runs) == len(configs), "DAC missing selected runs")
        require(len({r["name"] for r in runs}) == len(runs), "duplicate DAC scope run")
        by_name = {r["name"]: r for r in runs}
        require(set(by_name) == {f"{c['name']}_seed{j['seed']}" for c, j in zip(configs, jobs)},
                "DAC scope/frozen run set mismatch")
        for config, job, cfg_record in zip(configs, jobs, record["configs"]):
            name = f"{config['name']}_seed{job['seed']}"
            run = by_name[name]
            rel = f"results/cocotb_{name}__dac_performance.json"
            result = read(rel)
            expected = dict(schema="cxl-revision-dac-performance-v1", evidence_kind="RTL",
                            status="PASS", job=job, selected_policy=policy, params=config["params"],
                            cold=False, cold_cohort=None, training_cycles=job["training_cycles"],
                            production_evidence=not pilot, sensitivity_evidence=pilot,
                            matrix_contribution=int(not pilot and policy == "DAC2"),
                            outstanding_after_drain=0, producer_backlog_after_drain=0,
                            sparse_guard_complete=True)
            require(all(k in result and type(result[k]) is type(v)
                        and canonical_json(result[k]) == canonical_json(v)
                        for k, v in expected.items()), "DAC result identity/acceptance mismatch")
            require(run.get("matrix_job_id") == job["id"] and run.get("selected_policy") == policy
                    and run.get("result") == rel and hash64(result.get("trace_sha256"))
                    and run.get("trace_sha256") == result["trace_sha256"],
                    "DAC scope/result binding mismatch")
            require(isinstance(result.get("metrics"), dict)
                    and isinstance(result.get("windows"), list)
                    and isinstance(result.get("trace_config"), dict), "DAC raw metrics/trace missing")
            step = next(s for s in steps if s["name"] == f"cocotb:{name}")
            cfg_record["accepted"] = True
            record["accepted_configs"].append(name)
            record["runs"].append(dict(
                name=name, matrix_job_id=cfg_record["row_id"], declared_job_id=job["id"],
                lane="trained", seed=job["seed"], cohort="trained", selected_policy=policy,
                policy=job["policy"], n_src=job["n_src"], result=rel,
                result_sha256=sha256_file(bundle / rel), trace_sha256=result["trace_sha256"],
                trace_config=result["trace_config"], exit_codes=step["exit_codes"],
                production_evidence=not pilot, matrix_contribution=int(bool(cfg_record["row_id"])),
                failures=[], missing=[], status="PASS",
            ))
        record["matrix_contribution"] = contribution
        record["status"] = "PASS"
    except FileNotFoundError as exc:
        record["problems"].append(str(exc))
        record["status"] = "RUNNING" if record["running"] else "UNRESOLVED"
    except (ValueError, KeyError, TypeError, AttributeError, OSError, ET.ParseError) as exc:
        record["failures"].append(str(exc))
        record["status"] = "FAIL"
    if record["status"] != "PASS":
        existing = {r["matrix_job_id"] for r in record["runs"]}
        for cfg in record["configs"]:
            row = rows_by_id.get(cfg["row_id"])
            if row and row["id"] not in existing:
                record["runs"].append(dict(
                    matrix_job_id=row["id"], lane="trained", seed=row["seed"], cohort="trained",
                    selected_policy=record["selected_policy"], status=record["status"],
                    failures=list(record["failures"]), missing=list(record["problems"]),
                    production_evidence=False,
                ))
    return record


def power_bound_file(base: Path, ref: dict) -> Path:
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"} or not hash64(ref["sha256"]):
        raise ValueError("invalid power file reference")
    path = base / ref["path"]
    if not path.is_file() or sha256_file(path) != ref["sha256"]:
        raise ValueError(f"missing/tampered power file: {path.name}")
    return path


def inspect_power_recovery(case: dict, base: Path, remote: Path, prepared: dict,
                           transcript: dict, original_exits: dict) -> tuple[Path, dict, dict]:
    """Inspect a separately fetched result without replacing the original transport failure."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    main_b = (case["policy"], case["seed"], case["arm"]) == ("fai-main", 509, "B")
    main_a = (case["policy"], case["seed"], case["arm"]) == ("fai-main", 510, "A")
    main_510b = (case["policy"], case["seed"], case["arm"]) == ("fai-main", 510, "B")
    case_id = "fai-main-B-s510" if main_510b else "fai-main-A-s510" if main_a else "fai-main-B-s509" if main_b else "fcfs-A-s509"
    require((case["policy"], case["seed"], case["arm"]) in (("fcfs", 509, "A"), ("fai-main", 509, "B"), ("fai-main", 510, "A"), ("fai-main", 510, "B"))
            and original_exits == dict(preflight=0, upload=0, power=255, fetch=255),
            "recovery requires an exact approved case with original transport255")
    refs = case["recovery"]
    require(isinstance(refs, dict) and set(refs) == {
        "plan", "inspection", "result", "inspect_exit", "fetch_exit", "fetch_archive", "reviewer_receipt"},
        "missing/unknown explicit power recovery references")
    paths = {k: power_bound_file(base, v) for k, v in refs.items()}
    plan, inspection, result = (load_json(paths[k]) for k in ("plan", "inspection", "result"))
    root = transcript["remote_root"]
    require(plan.get("schema") == ("cxl-inspect-fetch-existing-main510b-v1" if main_510b else "cxl-inspect-fetch-existing-main510a-v1" if main_a else "cxl-inspect-fetch-existing-main509b-v1" if main_b else "cxl-inspect-fetch-existing-fcfs509a-v1")
            and plan.get("case_id") == transcript.get("case_id") == case_id
            and plan.get("remote_root") == root
            and plan.get("expected_members") == prepared["member_sha256"]
            and plan.get("payload_sha256") == transcript.get("payload_sha256") == prepared["payload_sha256"]
            and transcript.get("prepared_sha256") == sha256_file(remote / "prepared.json"),
            "recovery original case/payload/prepared binding mismatch")
    for path in (remote / "prepared.json", remote / "command-transcript.json",
                 remote / "transport/power.exit.json", remote / "transport/fetch.exit.json"):
        require(plan["bindings"].get(str(path)) == sha256_file(path), "recovery original history hash mismatch")
    for name in ("inspect_exit", "fetch_exit"):
        code = load_json(paths[name]).get("outer_exit")
        require(type(code) is int and code == 0, f"recovery {name} failed/incomplete")
    owed = dict(compile=0, sim=0, pt=0, shell_exit=0)
    actual = inspection.get("actual_exits")
    require(inspection.get("status") == "CLEAN_COMPLETED_READY_TO_FETCH"
            and inspection.get("processes") == [] and inspection.get("remote_root") == root
            and type(inspection.get("EDA_exit")) is int and inspection["EDA_exit"] == 0
            and inspection.get("payload_and_source_match") is True
            and actual == owed and all(type(v) is int for v in actual.values()),
            "recovery inspection is not a completed idle job with actual EDA exit0")
    require(result.get("status") == ("EXISTING_MAIN510B_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED" if main_510b else "EXISTING_MAIN510A_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED" if main_a else "EXISTING_MAIN509B_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED" if main_b else "EXISTING_FCFS509A_DOWNLOADED_SEMANTIC_REVIEW_REQUIRED")
            and type(result.get("actual_EDA_exit")) is int and result["actual_EDA_exit"] == 0
            and result.get("payload_and_source_match") is True
            and result.get("inspected_manifest_sha256") == sha256_file(paths["inspection"])
            and result.get("archive_sha256") == sha256_file(paths["fetch_archive"])
            and result.get("files") == inspection.get("files"), "recovered result/inspection/archive mismatch")
    files = result["files"]
    require(len(files) == 28 and set(files) == set(plan["required_outputs"])
            and set(files) <= set(plan["allowed_outputs"]), "recovery exact28 output inventory mismatch")
    with tarfile.open(paths["fetch_archive"]) as archive:
        seen = set()
        for member in archive:
            require(member.isfile() and safe_relpath(member.name) and member.name in files
                    and member.name not in seen and member.size <= 64 * 1024 * 1024,
                    "unsafe/duplicate/unexpected recovery archive member")
            seen.add(member.name)
            require(sha256_bytes(archive.extractfile(member).read()) == files[member.name],
                    "recovery fetched member hash mismatch")
        require(seen == set(files), "recovery archive missing reports")
    results = paths["result"].parent / "results"
    source = (results / "reports/source.sha256").read_text().splitlines()
    pairs = [line.split(maxsplit=1) for line in source]
    require(all(len(p) == 2 for p in pairs) and len(pairs) == len({p[1] for p in pairs}),
            "invalid/duplicate recovered source records")
    expected = {n: h for n, h in plan["remote_inputs"].items() if not n.endswith("/manifest.json")}
    expected.update({root + "/" + n: prepared["member_sha256"][n]
                     for n in ("metadata.json", "vectors.txt.gz", *POWER_RUNTIME)})
    require(plan["expected_source_record"] == expected == {p: h for h, p in pairs},
            "recovery remote source path/hash binding mismatch")
    mapped = transcript["mapped"]
    require(all(plan["remote_inputs"].get(mapped["remote_root"] + "/" + n) == h
                for n, h in mapped["hashes"].items()), "recovery mapped input paths mismatch")
    return results, result, dict(original_transport_exits=original_exits,
        original_history_sha256={str(remote / "command-transcript.json"): sha256_file(remote / "command-transcript.json"),
            **{str(remote / f"transport/{s}.exit.json"): sha256_file(remote / f"transport/{s}.exit.json")
               for s in original_exits}}, recovery_actual_eda_exits=actual,
        recovery_evidence={k: dict(path=str(paths[k]), sha256=sha256_file(paths[k])) for k in paths})


def load_power_detached_reviewer(path: Path, controller_plan: Path):
    """Load only the released local reviewer; never call its output-producing entry point."""
    if sha256_file(path) != POWER_DETACHED_REVIEWER_SHA or sha256_file(controller_plan) != POWER_DETACHED_PLAN_SHA:
        raise ValueError("unreleased detached reviewer/controller plan")
    matrix = path.parent.parent
    if controller_plan != matrix / "continue-remaining6-detached-20261026t0505/plan.json":
        raise ValueError("detached controller/reviewer path mismatch")
    plan, original = load_json(controller_plan), load_json(matrix / "plan.json")
    if sha256_file(matrix / "plan.json") != plan["original_plan_sha256"]:
        raise ValueError("detached original plan changed")
    # Check imported helper bytes before executing the pinned module, as well as its own import-time pins.
    for manifest in (plan, original, load_json(Path(original["original_plan"]))):
        for name, digest in manifest["bindings"].items():
            if sha256_file(Path(name)) != digest:
                raise ValueError("detached imported helper changed")
    if "adapter" in sys.modules and Path(sys.modules["adapter"].__file__) != matrix / "adapter.py":
        raise ValueError("different detached adapter already imported")
    spec = importlib.util.spec_from_file_location("revision_index_detached_reviewer", path)
    module = importlib.util.module_from_spec(spec)
    old_path, old_bytecode = list(sys.path), sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode
    return module


def inspect_power_detached(case: dict, base: Path, remote: Path, export: Path, transcript: dict) -> dict:
    """Explicit detached transport proof; no foreground power.exit.json is synthesized."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    identity = {k: case[k] for k in ("policy", "seed", "arm")}
    require(identity["policy"] in ("fcfs", "rr", "fai-main") and identity["seed"] == 511
            and identity["arm"] in ("A", "B") and "recovery" not in case,
            "unreleased detached case identity")
    receipt_path = power_bound_file(base, case["semantic_receipt"])
    require(sha256_file(receipt_path) in POWER_REVIEW_RELEASE_SHA256, "detached parent release not pinned")
    receipt = load_json(receipt_path)
    require(receipt.get("schema") == "cxl-detached-trained-power-semantic-release-v1"
            and receipt.get("status") == "PARENT_ACCEPTED_DETACHED_TRAINED_POWER_CASE"
            and {k:receipt.get(k) for k in identity} == identity
            and receipt.get("case_id") == f"{identity['policy']}-{identity['arm']}-s511"
            and receipt.get("transport_contract") == case["transport_contract"] == "cxl-detached-trained-power-v1"
            and receipt.get("foreground_power_ssh") is False
            and type(receipt.get("actual_EDA_exit")) is int and receipt["actual_EDA_exit"] == 0,
            "detached parent identity/contract/EDA mismatch")
    adapter = power_bound_file(base, dict(path=receipt["independent_reviewer"], sha256=receipt["reviewer_sha256"]))
    controller_plan = power_bound_file(base, receipt["controller_plan"])
    for name in ("independent_release", "writer_release"):
        power_bound_file(base, receipt[name])
    reviewer = load_power_detached_reviewer(adapter, controller_plan)
    plan, original = reviewer.bindings()
    require(reviewer.ready(receipt["case_id"], plan), "detached case not completed")
    job = next(j for j in plan["jobs"] if j["id"] == receipt["case_id"])
    result_path = power_bound_file(base, receipt["remote_result"])
    require(result_path == remote / "remote-result.json"
            and power_bound_file(base, receipt["inspection"]) == remote / "inspection.json",
            "detached parent result/inspection path mismatch")
    result = load_json(result_path)
    proof = reviewer.validate_transport(remote, export, result, transcript, job, original)
    context = reviewer.launch_context(remote)
    parent = load_json(power_bound_file(base, dict(path=receipt["semantic_receipt"], sha256=receipt["semantic_sha256"])))
    review = load_json(power_bound_file(base, receipt["independent_semantic_receipt"]))
    require({k:v for k,v in parent.items() if k != "checked_utc"}
            == {k:v for k,v in review.items() if k != "checked_utc"}, "detached parent/independent semantics differ")
    require(review.get("status") == "REVIEWED_DETACHED_CASE_PARENT_ADOPTION_REQUIRED"
            and isinstance(review.get("raw_semantic_status"), str) and review["raw_semantic_status"].startswith("ADOPTED_")
            and review.get("case_id") == receipt["case_id"] and review.get("policy") == identity["policy"]
            and review.get("reviewer_source_sha256") == sha256_file(adapter) == POWER_DETACHED_REVIEWER_SHA
            and review.get("calibration_caller_sha256") == POWER_MAINB_CALLER_SHA
            and review.get("base_reviewer_sha256") == POWER_MAINB_BASE_SHA
            and review.get("continuation_plan_sha256") == sha256_file(controller_plan)
            and review.get("detached_transport") == proof and review.get("launch_context_sha256") == context
            and review.get("original_transcript_sha256") == sha256_file(remote / "command-transcript.json")
            and review.get("remote_result_sha256") == sha256_file(result_path),
            "detached semantic/raw/source proof mismatch")
    return dict(receipt=receipt, review=review, proof=proof, launch_context=context)


def inspect_power_case(case: dict, base: Path) -> dict:
    """Recheck raw contracts; only a pinned parent release can grant semantic adoption."""
    record = dict(status="UNRESOLVED", problems=[], raw_contract_checked=False)

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    try:
        import check_power_replay as power

        identity = {k: case[k] for k in ("policy", "seed", "arm")}
        require(identity["policy"] in POWER_MAPPED_SHA and type(identity["seed"]) is int
                and identity["seed"] in (509, 510, 511) and identity["arm"] in ("A", "B"),
                "not a planned matched-power policy/seed/arm")
        record.update(identity)
        export, remote = base / case["export_dir"], base / case["remote_dir"]
        results, reports = remote / "results", remote / "results/reports"
        meta = load_json(export / "metadata.json")
        power.check_mode(meta)
        require(meta["schema"] == power.TRAINED_SCHEMA
                and all(type(meta.get(k)) is type(v) and meta.get(k) == v for k, v in identity.items()),
                "trained export identity/schema mismatch")
        sources, mapped = meta["source_sha256"], meta["accepted_case_sha256"]
        require(canonical_sha(sources) == POWER_SOURCE_SHA,
                "unreleased power source closure")
        require(canonical_sha(mapped) == POWER_MAPPED_SHA[meta["policy"]]
                and meta["accepted_source_revision"] == "759f86b24f13ed5984c19034eeeea2ca43b0e971"
                and meta["profile_canonical_sha256"] ==
                "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d",
                "mapped case/profile binding mismatch")
        archive = export / "source-freeze.zip"
        require(sha256_file(archive) == meta["source_archive_sha256"], "power source ZIP hash mismatch")
        frozen, issues = _read_zip_bytes(archive)
        require(not issues, "invalid power source ZIP")
        inventory = {**sources, **{f"mapped/{n}": h for n, h in mapped.items()}}
        require(set(frozen) == set(inventory)
                and all(sha256_bytes(frozen[n]) == h for n, h in inventory.items()),
                "power source ZIP inventory/bytes mismatch")
        require(all(sha256_file(ROOT / n) == sources[n] for n in POWER_RUNTIME),
                "current checker/runtime differs from frozen power sources")
        trace = meta["trace"]
        require(hash64(trace["sha256"]), "missing power trace hash")
        tc = trace["config"]
        trace_config = dict(generator="cxl-hog-sparse-traffic-v1", seed=meta["seed"], n_src=4,
                            depth=16, desc_w=105, window=5_000_000, heavy_source=0,
                            heavy_per_cycle=1, ready=1, sparse_probability=[1, 128], burst_size=8,
                            burst_blocks=100, burst_block_cycles=1024,
                            burst_offset_inclusive=[0, 1023],
                            phase_cycles=dict(training=10_000_000, A=100_000, A_guard=1024,
                                              B=102_400, B_guard=1024))
        require(all(type(tc.get(k)) is type(v) and tc.get(k) == v for k, v in trace_config.items()),
                "power traffic configuration mismatch")
        audit_path = export / "audit.json"
        require(sha256_file(audit_path) == meta["audit_sha256"], "native audit hash mismatch")
        audit = load_json(audit_path)
        require(audit.get("status") == "INDEPENDENT_MODEL_AND_PIN_FIFO_CHECKED"
                and type(audit.get("exit")) is int and audit["exit"] == 0
                and type(audit.get("rows")) is int and audit["rows"] == meta["total_cycles"],
                "native serialized audit incomplete")
        for phase in ("warmup", "measured"):
            require(audit[phase] == {k: meta[phase][k] for k in
                    ("cycles", "accepted_per_source", "fires_per_source")}, "native phase totals mismatch")
        require(audit["outstanding_at_end"] == meta["outstanding_at_end"], "native conservation mismatch")
        phase_cycles = {"training": 10_000_000, "A": 100_000}
        if meta["arm"] == "B":
            phase_cycles.update(A_guard=1024, B=102_400)
        require(audit["traffic_phase_cycles"] == phase_cycles
                and set(audit["traffic_phase_pin_sha256"]) == set(phase_cycles)
                and all(hash64(v) for v in audit["traffic_phase_pin_sha256"].values()),
                "native trace phase audit mismatch")
        if meta["policy"] == "fai-main":
            require(audit["main_closings"] == [{k: c[k] for k in
                    ("cycle", "b_close", "s_close", "evidence", "old_classes", "next_cycle_classes")}
                    for c in meta["closings"]], "native classification audit mismatch")
        native_path = power_bound_file(base, case["native_exit"])
        field = case["native_exit_field"]
        require(field in ("exit", "exit_code"), "unsupported native exit field")
        code = load_json(native_path).get(field)
        require(type(code) is int and code == 0, "native exporter process failed/pending")
        require(sha256_file(export / "vectors.txt.gz") == meta["vectors_gzip_sha256"],
                "power vector hash mismatch")
        prepared = load_json(remote / "prepared.json")
        members = prepared["member_sha256"]
        for name in ("metadata.json", "audit.json", "source-freeze.zip", "vectors.txt.gz"):
            require(members.get(name) == sha256_file(export / name), "prepared export binding mismatch")
        runtime = {n: sources[n] for n in POWER_RUNTIME}
        require(prepared["runtime_sha256"] == runtime
                and all(members.get(n) == h for n, h in runtime.items()), "prepared runtime mismatch")
        require(sha256_file(remote / "payload.tar") == prepared["payload_sha256"],
                "uploaded payload hash mismatch")
        transcript = load_json(remote / "command-transcript.json")
        detached = "transport_contract" in case
        recovered = "recovery" in case
        original_exits = {}
        if detached:
            detached_evidence = inspect_power_detached(case, base, remote, export, transcript)
            require(transcript.get("runtime_sha256") == runtime, "detached runtime mismatch")
            result_path = remote / "remote-result.json"
            remote_manifest = load_json(result_path)
            record.update(transport_contract=case["transport_contract"], foreground_power_ssh=False,
                          detached_transport=detached_evidence["proof"], launch_context_sha256=detached_evidence["launch_context"])
        else:
            for stage in ("preflight", "upload", "power", "fetch"):
                code = load_json(remote / f"transport/{stage}.exit.json").get("outer_exit")
                require(type(code) is int, f"remote {stage} exit missing/invalid")
                original_exits[stage] = code
            require(transcript.get("runtime_sha256") == runtime
                    and all(type(transcript["stages"][s]["exit"]) is int
                            and transcript["stages"][s]["exit"] == original_exits[s] for s in original_exits),
                    "remote transcript runtime/stage mismatch")
        if recovered:
            results, remote_manifest, history = inspect_power_recovery(case, base, remote, prepared, transcript, original_exits)
            reports = results / "reports"
            record.update(history)
            result_path = power_bound_file(base, case["recovery"]["result"])
        elif not detached:
            require(all(code == 0 for code in original_exits.values()), "remote transport incomplete/failed")
            result_path = remote / "remote-result.json"
            remote_manifest = load_json(result_path)
            require(type(remote_manifest.get("remote_exit")) is int
                    and remote_manifest["remote_exit"] == 0, "remote execution incomplete/failed")
        files = remote_manifest["files"]
        required = {f"reports/{n}" for n in (
            "compile.log", "sim.log", "pt.log", "exits.txt", "source.sha256", "source-after.sha256",
            "replay.txt", "replay-audit.json", "pilot-audit.json", "design.rpt", "library.rpt",
            "clocks.rpt", "units.rpt", "saif-read.rpt", "check-power.rpt", "update-power.rpt",
            "disable-timing.rpt", "switching-coverage.rpt", "not-annotated.rpt", "annotated.rpt",
            "power.rpt", "power-hierarchy.rpt", "registers-and-clock-pins.rpt", "pilot-status.rpt")}
        require(required | {"activity.saif"} <= set(files), "missing required remote evidence")
        require(all(safe_relpath(n) and hash64(h) and sha256_file(results / n) == h
                    for n, h in files.items()), "returned report hash mismatch")
        exits = (reports / "exits.txt").read_text().splitlines()
        require(exits == ["compile=0", "sim=0", "pt=0", "shell_exit=0"], "remote stage exit mismatch")
        before = (reports / "source.sha256").read_bytes()
        require(before == (reports / "source-after.sha256").read_bytes(), "remote source changed")
        source_lines = before.decode().splitlines()
        digests = [line.split(maxsplit=1)[0] for line in source_lines]
        expected_digests = [
            "d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286",
            "844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094",
            *[mapped[n] for n in ("run_config.tcl", "output/switch_top.syn.v", "output/switch_top.syn.sdc")],
            members["metadata.json"], members["vectors.txt.gz"], *runtime.values()]
        require(Counter(digests) == Counter(expected_digests), "remote mapped/library/runtime hashes differ")
        replay = power.check_replay(meta, reports / "replay.txt", results / "activity.saif")
        require(load_json(reports / "replay-audit.json") == replay, "replay audit differs from raw evidence")
        pilot = dict(replay, pt=power.check_pt(reports))
        require(load_json(reports / "pilot-audit.json") == pilot, "PT audit differs from raw evidence")
        record.update(raw_contract_checked=True, trace_sha256=trace["sha256"],
                      source_sha256=canonical_sha(sources), report_sha256=files,
                      measured_cycles=meta["measured_cycles"])
        if case.get("semantic_receipt") is None:
            raise ValueError("independent semantic receipt / pinned parent release pending")
        receipt_path = power_bound_file(base, case["semantic_receipt"])
        receipt = load_json(receipt_path)
        require(sha256_file(receipt_path) in POWER_REVIEW_RELEASE_SHA256,
                "parent semantic release is not pinned in indexer")
        bindings = {"metadata": members["metadata.json"], "audit": members["audit.json"],
                    "source_archive": members["source-freeze.zip"], "vectors": members["vectors.txt.gz"],
                    "native_exit": sha256_file(native_path), "prepared": sha256_file(remote / "prepared.json"),
                    "payload": prepared["payload_sha256"],
                    "remote_result": sha256_file(result_path),
                    "transcript": sha256_file(remote / "command-transcript.json")}
        if detached:
            review = detached_evidence["review"]
            require(review.get("blocking_issues") == [] and review.get("downloaded_hashes") == files
                    and review.get("replay") == replay and review.get("pt") == pilot["pt"]
                    and review.get("measured_cycles") == meta["measured_cycles"]
                    and review.get("total_checked_cycles") == meta["total_cycles"],
                    "detached semantic/native/raw replay/PT mismatch")
        elif recovered:
            main_b = identity == dict(policy="fai-main", seed=509, arm="B")
            main_a = identity == dict(policy="fai-main", seed=510, arm="A")
            main_510b = identity == dict(policy="fai-main", seed=510, arm="B")
            case_id = "fai-main-B-s510" if main_510b else "fai-main-A-s510" if main_a else "fai-main-B-s509" if main_b else "fcfs-A-s509"
            require(receipt.get("schema") == ("cxl-recovered-main510b-semantic-release-v1" if main_510b else "cxl-recovered-main510a-semantic-release-v1" if main_a else "cxl-recovered-main509b-semantic-release-v1" if main_b else "cxl-recovered-fcfs509a-semantic-release-v1")
                    and receipt.get("status") == ("PARENT_ACCEPTED_RECOVERED_MAIN510B_RELEASE_REMAINING6" if main_510b else "PARENT_ACCEPTED_RECOVERED_MAIN510A_RELEASE_REMAINING7" if main_a else "PARENT_ACCEPTED_RECOVERED_MAIN509B_RELEASE_REMAINING12" if main_b else "PARENT_ACCEPTED_RECOVERED_FCFS509A_RELEASE_REMAINING16")
                    and receipt.get("case_id") == case_id
                    and receipt.get("original_transport_exits_preserved") == dict(power=255, fetch=255)
                    and type(receipt.get("actual_EDA_exit")) is int and receipt["actual_EDA_exit"] == 0
                    and type(receipt.get("recovery_transport_exit")) is int and receipt["recovery_transport_exit"] == 0
                    and receipt.get("qualified_table_range_warnings", 0 if main_a or main_510b else None) == sum(pilot["pt"]["check_power"]["range_issue_counts"].values()),
                    "recovered parent semantic release identity/stage/qualification mismatch")
            parent_review = load_json(power_bound_file(base, dict(path=receipt["semantic_receipt"],
                                                                 sha256=receipt["semantic_sha256"])))
            review_path = power_bound_file(base, case["recovery"]["reviewer_receipt"])
            require(sha256_file(review_path) == (receipt["independent_semantic_receipt"]["sha256"] if main_510b else POWER_MAIN510A_REVIEW_SHA if main_a else receipt["semantic_sha256"] if main_b else POWER_RECOVERED_REVIEW_SHA256),
                    "unapproved recovered independent review")
            if main_510b:
                require(power_bound_file(base, receipt["independent_semantic_receipt"]) == review_path,
                        "Main510B independent receipt binding differs")
            review = load_json(review_path)
            if main_b:
                parent_review = load_json(power_bound_file(base, dict(path=receipt["parent_semantic_receipt"],
                    sha256=receipt["parent_semantic_sha256"])))
            if main_b or main_a or main_510b:
                for name in ("result", "inspection"):
                    require(power_bound_file(base, receipt["recovery_" + name])
                            == power_bound_file(base, case["recovery"][name]), "recovered Main release recovery binding differs")
            require({k:v for k,v in parent_review.items() if k != "checked_utc"}
                    == {k:v for k,v in review.items() if k != "checked_utc"},
                    "parent/recovered independent review mismatch")
            adapter = base / receipt["independent_reviewer"]
            require(sha256_file(adapter) == receipt["reviewer_sha256"]
                    == (review.get("recovery_adapter_sha256") if main_b or main_a or main_510b else review.get("reviewer_sha256")),
                    "recovered accepted reviewer guard mismatch")
            if main_b:
                require(sha256_file(adapter) == POWER_MAINB_ADAPTER_SHA
                        and sha256_file(adapter.parent.parent / "calibration-review-1657/review_calibrated.py")
                        == review.get("calibrated_caller_sha256") == POWER_MAINB_CALLER_SHA
                        and sha256_file(adapter.parent.parent.parent / "semantic-recovery-fcfs509a/review_recovery.py")
                        == review.get("frozen_recovery_reviewer_sha256") == review.get("reviewer_sha256")
                        == POWER_MAINB_FROZEN_REVIEWER_SHA
                        and sha256_file(adapter.parent.parent / "review.py") == POWER_MAINB_BASE_SHA,
                        "MainB calibrated/frozen recovery reviewer drift")
            if main_a or main_510b:
                sem = adapter.parent.parent / "power-sol/remote-preparation/continuation-1258/semantic-remaining"
                recovery_plan = power_bound_file(base, case["recovery"]["plan"])
                require(sha256_file(adapter) == (POWER_MAIN510B_ADAPTER_SHA if main_510b else POWER_MAIN510A_ADAPTER_SHA)
                        and sha256_file(sem / "calibration-review-1657/review_calibrated.py")
                        == review.get("calibration_caller_sha256") == POWER_MAINB_CALLER_SHA
                        and sha256_file(sem.parent / "semantic-recovery-fcfs509a/review_recovery.py")
                        == review.get("frozen_recovery_reviewer_sha256") == review.get("reviewer_sha256")
                        == POWER_MAINB_FROZEN_REVIEWER_SHA
                        and sha256_file(sem / "review.py") == review.get("base_reviewer_sha256") == POWER_MAINB_BASE_SHA
                        and review.get("recovery_plan_sha256") == sha256_file(recovery_plan)
                        and review.get("continuation_plan_sha256") == load_json(recovery_plan)["continuation_plan_sha256"],
                        "Main510 calibrated/frozen reviewer or recovery plan drift")
                if main_510b:
                    require(sha256_file(adapter.parent.parent / "semantic-main510a-20261025t1550/review_main510a.py")
                            == review.get("adapted_from_main510a_sha256") == POWER_MAIN510A_ADAPTER_SHA,
                            "Main510B frozen Main510A adapter drift")
            require(review.get("status") == ("ADOPTED_SINGLE_TRAINED_PRELAYOUT_CASE" if main_b or main_a or main_510b else "ADOPTED_QUALIFIED_TABLE_RANGE_PRELAYOUT_CASE")
                    and review.get("case_id") == case_id and review.get("policy") == identity["policy"]
                    and review.get("measured_cycles") == meta["measured_cycles"]
                    and review.get("total_checked_cycles") == meta["total_cycles"]
                    and review.get("blocking_issues") == [] and review.get("downloaded_hashes") == files
                    and review.get("replay") == replay and review.get("pt") == pilot["pt"]
                    and review.get("stage_exits") == {k:"0" for k in record["recovery_actual_eda_exits"]}
                    and review.get("original_transport_exits") == original_exits
                    and type(review.get("recovery_inspection_exit")) is int and review["recovery_inspection_exit"] == 0
                    and type(review.get("recovery_fetch_exit")) is int and review["recovery_fetch_exit"] == 0
                    and review.get("recovery_result_sha256") == bindings["remote_result"]
                    and review.get("original_transcript_sha256") == bindings["transcript"],
                    "recovered independent semantic/raw provenance mismatch")
            record.update(power_quality_status=pilot["pt"]["check_power"]["quality_status"],
                          qualified_range_issues=pilot["pt"]["check_power"]["range_issues"])
        elif receipt.get("schema") == "cxl-main509a-semantic-release-v1":
            require(identity == dict(policy="fai-main", seed=509, arm="A")
                    and receipt.get("status") == "PARENT_ACCEPTED_MAIN509A_SEMANTICS_RELEASE_REMAINING17"
                    and receipt.get("case_id") == "fai-main-A-s509"
                    and receipt.get("local_files") == {n: members[n] for n in
                        ("metadata.json", "audit.json", "source-freeze.zip", "vectors.txt.gz")}
                    and all(receipt.get(k + "_sha256") == bindings[k] for k in
                            ("prepared", "payload", "remote_result", "transcript"))
                    and receipt.get("reviewed_files") == files,
                    "first Main509A semantic release binding mismatch")
        else:
            require(receipt.get("schema") == "cxl-trained-power-semantic-acceptance-v1"
                    and receipt.get("case") == identity
                    and receipt.get("decision") == "ADOPT_PRE_LAYOUT_TT25NS_MATCHED_POWER"
                    and receipt.get("problems") == [] and receipt.get("bindings") == bindings
                    and receipt.get("reports") == files and bool(receipt.get("limitations")),
                    "semantic decision/identity/evidence binding mismatch")
        if not recovered and not detached:
            review_path = power_bound_file(base, dict(path=receipt["independent_review"],
                                                      sha256=receipt["independent_review_sha256"]))
            review = load_json(review_path)
            contract = receipt.get("review_contract")
            require(contract in (None, "calibrated-replay-pt-v1"), "unsupported semantic review contract")
            if contract == "calibrated-replay-pt-v1":
                caller = power_bound_file(base, dict(path=receipt["calibrated_reviewer"],
                                                     sha256=receipt["calibrated_reviewer_sha256"]))
                # The calibrated caller imports its immutable base from the parent directory.
                base_hash = sha256_file(caller.parent.parent / "review.py")
                require(review.get("calibration_caller_sha256") == sha256_file(caller)
                        and receipt.get("base_reviewer_sha256") == base_hash
                        == review.get("base_reviewer_sha256") == review.get("reviewer_sha256"),
                        "calibrated caller/immutable base reviewer mismatch")
                review_replay, review_pt = review.get("replay"), review.get("pt")
            else:
                review_replay, review_pt = review.get("checker_replay"), review.get("checker_pt")
            require(isinstance(review.get("status"), str) and review["status"].startswith("ADOPTED_")
                    and review.get("blocking_issues") == [] and review.get("downloaded_hashes") == files
                    and review_replay == replay and review_pt == pilot["pt"],
                    "independent semantic review missing/rejected/unbound")
        record.update(power_quality_status=pilot["pt"]["check_power"]["quality_status"],
                      qualified_range_issues=pilot["pt"]["check_power"]["range_issues"])
        record.update(status="PASS", semantic_receipt_sha256=sha256_file(receipt_path))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile, tarfile.TarError) as exc:
        record["problems"].append(str(exc))
    return record


def inspect_power_manifest(path: Path, rows_by_id: dict[str, dict]) -> dict:
    result = dict(path=str(path), status="UNRESOLVED", problems=[], cases=[], rows=[])
    try:
        value = load_json(path)
        if value.get("schema") != POWER_MANIFEST or not isinstance(value.get("cases"), list):
            raise ValueError("invalid matched-power acceptance manifest")
        seen = set()
        for case in value["cases"]:
            record = inspect_power_case(case, path.parent)
            key = tuple(record.get(k) for k in ("policy", "seed", "arm"))
            if key in seen:
                raise ValueError("duplicate matched-power case")
            seen.add(key)
            result["cases"].append(record)
        for row in rows_by_id.values():
            if row["group"] != "matched-power":
                continue
            cases = [c for c in result["cases"] if c.get("policy") == POWER_POLICY[row["policy"]]
                     and c.get("seed") == row["seed"]]
            if cases:
                accepted = sorted(c["arm"] for c in cases if c["status"] == "PASS")
                result["rows"].append(dict(matrix_job_id=row["id"], cases=cases,
                    accepted_arms=accepted, missing_arms=sorted({"A", "B"} - set(accepted)),
                    status="PASS" if accepted == ["A", "B"] else "UNRESOLVED"))
        if result["rows"] and not result["problems"] and all(r["status"] == "PASS" for r in result["rows"]):
            result["status"] = "PASS"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result["problems"].append(str(exc))
        result["rows"] = []
    return result


def bounded_files(root: Path, names: set[str], max_depth: int = 3) -> list[Path]:
    """Find only named files below an explicitly supplied root."""
    found: list[Path] = []
    queue = [(root, 0)]
    while queue:
        directory, depth = queue.pop(0)
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.as_posix())
        except OSError:
            continue
        for path in entries:
            if path.name in SKIP_DIRS:
                continue
            if path.is_file() and path.name in names:
                found.append(path)
            elif path.is_dir() and depth < max_depth:
                queue.append((path, depth + 1))
    return sorted(set(found))


def discover(inputs: list[Path]) -> dict:
    matrices: set[Path] = set()
    bundles: set[Path] = set()
    insights: set[Path] = set()
    bridges: set[Path] = set()
    baselines: set[Path] = set()
    power: set[Path] = set()
    input_records = []
    for supplied in inputs:
        path = supplied.resolve()
        input_records.append(dict(path=str(path), exists=path.exists(), kind="file" if path.is_file() else "dir"))
        if not path.exists():
            raise ValueError(f"explicit input does not exist: {path}")
        if path.is_file():
            if path.name == "matched-power-acceptance.json":
                power.add(path)
            elif path.name == "matrix.json":
                matrices.add(path)
            elif path.name == "BRIDGES.md":
                bridges.add(path)
            elif path.name == "summary.json":
                try:
                    value = load_json(path)
                except (OSError, json.JSONDecodeError):
                    value = {}
                if (path.parent / "baseline_scope.json").exists() or "baseline" in path.parent.parent.name:
                    baselines.add(path)
                elif value.get("scope") == "MODEL_ONLY" or value.get("schema") == INSIGHT_SCHEMA:
                    insights.add(path)
                else:
                    bundles.add(path.parent)
            elif path.name in ("frozen-spec.json", "revision_scope.json", "dac_performance_scope.json"):
                bundles.add(path.parent)
            continue
        for name in ("matrix.json", "frozen-spec.json", "revision_scope.json", "dac_performance_scope.json",
                     "summary.json", "BRIDGES.md", "matched-power-acceptance.json"):
            for found in bounded_files(path, {name}):
                if name == "matched-power-acceptance.json":
                    power.add(found)
                elif name == "matrix.json":
                    matrices.add(found)
                elif name == "BRIDGES.md":
                    bridges.add(found)
                elif name == "summary.json":
                    try:
                        value = load_json(found)
                    except (OSError, json.JSONDecodeError):
                        value = {}
                    if (found.parent / "baseline_scope.json").exists() or "baseline" in found.parent.parent.name:
                        baselines.add(found)
                    elif value.get("scope") == "MODEL_ONLY" or value.get("schema") == INSIGHT_SCHEMA:
                        insights.add(found)
                    else:
                        bundles.add(found.parent)
                else:
                    if not ((found.parent / "baseline_scope.json").exists()
                            or "baseline" in found.parent.parent.name):
                        bundles.add(found.parent)
    return dict(inputs=input_records, matrices=sorted(matrices), bundles=sorted(bundles),
                insights=sorted(insights), bridges=sorted(bridges), baselines=sorted(baselines),
                power=sorted(power))


def matrix_provenance(matrix_files: list[Path], rows: list[dict]) -> dict:
    rows_by_id = {r["id"]: r for r in rows}
    canonical = canonical_sha(rows)
    exact, historical = [], []
    for path in matrix_files:
        item = dict(path=str(path), file_sha256=sha256_file(path), historical_only=True,
                    accepted_new_matrix=False)
        try:
            value = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            item["error"] = f"invalid JSON: {exc}"
            historical.append(item)
            continue
        jobs = value.get("jobs")
        item.update(
            schema=value.get("schema"),
            declared_matrix_sha256=value.get("matrix_sha256"),
            computed_matrix_sha256=canonical_sha(jobs) if isinstance(jobs, list) else None,
            total_planned_jobs=value.get("total_planned_jobs"),
            core_unconditional_jobs=value.get("core_unconditional_jobs"),
            material_passport=value.get("material_passport"),
            head=value.get("head"),
            counts=value.get("counts"),
            jobs=jobs if isinstance(jobs, list) else [],
        )
        item["job_count"] = len(jobs) if isinstance(jobs, list) else 0
        item["ids_unique"] = isinstance(jobs, list) and len({j.get("id") for j in jobs if isinstance(j, dict)}) == len(jobs)
        item["declared_hash_matches"] = (
            isinstance(jobs, list) and value.get("matrix_sha256") == canonical_sha(jobs)
        )
        if isinstance(jobs, list):
            item["same_id_changed_rows"] = sorted(
                j["id"] for j in jobs if isinstance(j, dict)
                and j.get("id") in rows_by_id and j != rows_by_id[j["id"]]
            )
            item["historical_ids_not_in_current"] = sorted(
                {j.get("id") for j in jobs if isinstance(j, dict) and j.get("id") not in rows_by_id}
            )
            item["current_ids_not_in_snapshot"] = sorted(
                set(rows_by_id) - {j.get("id") for j in jobs if isinstance(j, dict)}
            )
            item["same_id_count"] = len(
                {j.get("id") for j in jobs if isinstance(j, dict) and j.get("id") in rows_by_id}
            )
        if (isinstance(jobs, list) and jobs == rows
                and value.get("schema") == MATRIX_SCHEMA
                and value.get("matrix_sha256") == canonical
                and value.get("total_planned_jobs") == len(rows)):
            item.update(historical_only=False, accepted_new_matrix=True)
            exact.append(item)
        else:
            historical.append(item)
    exact.sort(key=lambda x: x["path"])
    historical.sort(key=lambda x: x["path"])
    return dict(
        canonical_source="scripts/revision_matrix.py",
        canonical_source_sha256=sha256_file(ROOT / "scripts/revision_matrix.py"),
        canonical_matrix_sha256=canonical,
        canonical_job_count=len(rows),
        core_unconditional_jobs=sum(not r.get("conditional") for r in rows),
        conditional_jobs=sum(bool(r.get("conditional")) for r in rows),
        exact_current_snapshots=exact,
        historical_snapshots=historical,
        snapshot_pending=not bool(exact),
        selected_snapshot=exact[0]["path"] if exact else None,
        selected_matrix_sha256=exact[0]["declared_matrix_sha256"] if exact else canonical,
        heavy_id3_corrected_ids=sum(
            1 for r in rows if r.get("group") == "trained-robustness"
            and r.get("case") == "heavy-id3" and r.get("perturbation_after_training") is False
        ),
    )


def inspect_insight(path: Path) -> dict:
    record = dict(path=str(path), file_sha256=sha256_file(path), schema=None,
                  scope=None, gate_status=None, partial=None, completed=None,
                  window=None, policies=[], seeds=[], matrix_contribution=0,
                  problems=[])
    try:
        value = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        record["problems"].append(f"invalid JSON: {exc}")
        return record
    record.update(
        schema=value.get("schema"),
        scope=value.get("scope"),
        gate_status=(value.get("gate") or {}).get("status") if isinstance(value.get("gate"), dict) else None,
        partial=value.get("partial"),
        completed=value.get("completed"),
        window=value.get("window"),
        policies=value.get("policies", []),
        seeds=value.get("seeds", []),
        source_archive_sha256=(value.get("source_archive") or {}).get("sha256")
        if isinstance(value.get("source_archive"), dict) else None,
        kind=value.get("kind"),
        frozen_candidate=(value.get("gate") or {}).get("frozen_candidate"),
        feedback_count=len((value.get("gate") or {}).get("validated_feedback", [])),
        exit_code=value.get("exit_code"),
        validation_exit=value.get("validation_exit"),
        gate=value.get("gate"),
        report_hashes=value.get("report_hashes"),
    )
    archive = value.get("source_archive") or {}
    archive_name = archive.get("file")
    if not safe_relpath(archive_name):
        record["problems"].append("missing or unsafe source archive file")
    else:
        archive_path = path.parent / archive_name
        if not archive_path.is_file() or sha256_file(archive_path) != archive.get("sha256"):
            record["problems"].append("source archive missing or hash mismatch")
        else:
            members, problems = _read_zip_bytes(archive_path)
            record["problems"].extend(problems)
            record["problems"].extend(_manifest_problems("insight sources", archive.get("files"), members))
    for name, digest in (value.get("report_hashes") or {}).items():
        if not safe_relpath(name) or not (path.parent / name).is_file():
            record["problems"].append(f"missing or unsafe report: {name}")
        elif sha256_file(path.parent / name) != digest:
            record["problems"].append(f"report hash mismatch: {name}")
    if value.get("scope") != "MODEL_ONLY":
        record["problems"].append("insight summary is not MODEL_ONLY")
    if value.get("schema") != INSIGHT_SCHEMA:
        record["problems"].append("insight summary schema mismatch")
    if value.get("exit_code") != 0 or value.get("validation_exit") != 0:
        record["problems"].append("insight execution/validation exit missing or nonzero")
    return record


def inspect_baseline(path: Path) -> dict:
    value = load_json(path)
    scope_path = path.parent / "baseline_scope.json"
    config_path = path.parent / "config.json"
    archive_path = path.parent / "sources.zip"
    return dict(path=str(path), file_sha256=sha256_file(path),
                status=value.get("overall", "UNRESOLVED"), scope=value.get("scope"),
                counts=value.get("counts"), steps=value.get("steps"),
                config=load_json(config_path) if config_path.is_file() else None,
                scope_record=load_json(scope_path) if scope_path.is_file() else None,
                source_archive_sha256=sha256_file(archive_path) if archive_path.is_file() else None,
                file_hashes={p.name: sha256_file(p) for p in (scope_path, config_path)
                             if p.is_file()},
                matrix_contribution=0,
                acceptance="INVENTORY_ONLY_NOT_PERFORMANCE_ACCEPTANCE")


def inspect_bridges(path: Path) -> dict:
    record = dict(path=str(path), file_sha256=sha256_file(path), status="UNKNOWN",
                  accepted=0, total=6, executed=0, blocked=False,
                  matrix_contribution=0, problems=[])
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        record["problems"].append(str(exc))
        return record
    if re.search(r"Status:\s*\*\*BLOCKED", text, re.I):
        record.update(status="BLOCKED", blocked=True)
    if re.search(r"\b0/6\b", text):
        record["accepted"] = 0
    not_run = len(re.findall(r"\|\s*NOT_RUN\s*\|", text))
    if not_run:
        record["executed"] = 0
    if not record["blocked"]:
        record["problems"].append("BRIDGES.md does not declare BLOCKED")
    return record


def build_index(inputs: list[Path]) -> dict:
    rows = current_matrix()
    if len(rows) != 498:
        raise ValueError(f"current matrix has {len(rows)} rows, expected 498")
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("current matrix has duplicate IDs")
    rows_by_id = {r["id"]: r for r in rows}
    found = discover(inputs)
    provenance = matrix_provenance(found["matrices"], rows)
    bundles = [inspect_performance_bundle(p, rows_by_id) for p in found["bundles"]]
    insights = [inspect_insight(p) for p in found["insights"]]
    bridges = [inspect_bridges(p) for p in found["bridges"]]
    baselines = [inspect_baseline(p) for p in found["baselines"]]
    power = [inspect_power_manifest(p, rows_by_id) for p in found["power"]]

    row_records = {}
    lane_evidence = defaultdict(lambda: defaultdict(list))
    for bundle in bundles:
        for run in bundle["runs"]:
            row_id = run.get("matrix_job_id")
            lane = run.get("lane")
            if row_id not in rows_by_id or lane not in LANES:
                continue
            lane_evidence[row_id][lane].append((bundle["status"], run, bundle["path"]))

    for row in rows:
        row_id = row["id"]
        expected = expected_lanes(row)
        evidence = lane_evidence.get(row_id, {})
        accepted_lanes = []
        unresolved = []
        failed = []
        running = []
        for lane in expected:
            entries = evidence.get(lane, [])
            accepted = [x for x in entries if x[0] == "PASS" and x[1].get("status") == "PASS"]
            failed_entries = [x for x in entries if x[0] == "FAIL" or x[1].get("status") == "FAIL"]
            running_entries = [x for x in entries if x[0] == "RUNNING"]
            unresolved_entries = [x for x in entries if x[0] == "UNRESOLVED"
                                  or (x[0] == "PASS" and x[1].get("status") != "PASS")]
            if failed_entries:
                failed.extend(failed_entries)
            elif accepted:
                accepted_lanes.append(lane)
            elif running_entries:
                running.extend(running_entries)
            else:
                unresolved.extend(unresolved_entries)
        if not expected and evidence:
            unresolved.append((("UNRESOLVED", None, "evidence kind has no accepted matrix harness"), "", ""))
        if failed:
            status = "FAIL"
        elif expected and len(accepted_lanes) == len(expected):
            status = "PASS"
        elif unresolved:
            status = "UNRESOLVED"
        elif running:
            status = "RUNNING"
        elif any(evidence.get(lane) for lane in expected):
            status = "UNRESOLVED"
        else:
            status = "NOT_RUN"
        row_records[row_id] = dict(
            id=row_id,
            group=row.get("group"),
            policy=row.get("policy"),
            seed=row.get("seed"),
            n_src=row.get("n_src"),
            depth=row.get("depth"),
            window=row.get("window"),
            training_cycles=row.get("training_cycles"),
            evidence_kind=row.get("evidence_kind"),
            conditional=bool(row.get("conditional")),
            expected_lanes=list(expected),
            missing_lanes=[lane for lane in expected if lane not in evidence],
            accepted_lanes=accepted_lanes,
            status=status,
            evidence=[dict(bundle=path, bundle_status=status, run=run, lane=lane)
                      for lane in expected for status, run, path in evidence.get(lane, [])],
            optional_lane_evidence=[
                dict(bundle=path, bundle_status=status, run=run, lane=lane)
                for lane in LANES if lane not in expected
                for status, run, path in evidence.get(lane, [])
            ],
        )

    for row in rows:
        if row["group"] != "matched-power":
            continue
        evidence = [dict(manifest=p["path"], manifest_problems=p["problems"], **r)
                    for p in power for r in p["rows"] if r["matrix_job_id"] == row["id"]]
        accepted = [e for e in evidence if e["status"] == "PASS" and not e["manifest_problems"]]
        arms = max((e["accepted_arms"] for e in evidence if not e["manifest_problems"]),
                   key=len, default=[])
        rec = row_records[row["id"]]
        rec.update(expected_lanes=["A", "B"], missing_lanes=sorted({"A", "B"} - set(arms)),
                   accepted_lanes=arms, power_evidence=evidence,
                   status="PASS" if accepted else "UNRESOLVED" if evidence else "NOT_RUN")

    counts = Counter(r["status"] for r in row_records.values())
    by_group = {}
    for group in sorted({r.get("group") for r in rows}):
        members = [row_records[r["id"]] for r in rows if r.get("group") == group]
        by_group[group] = {status: sum(1 for m in members if m["status"] == status)
                           for status in STATUSES}
        by_group[group]["planned"] = len(members)

    accepted_records = []
    descriptive_records = []
    partial_records = []
    failed_records = []
    missing_records = []
    for bundle in bundles:
        for run in bundle["runs"]:
            item = dict(
                bundle=bundle["path"],
                matrix_job_id=run.get("matrix_job_id"),
                lane=run.get("lane"),
                seed=run.get("seed"),
                cohort=run.get("cohort"),
                result=run.get("result"),
                result_sha256=run.get("result_sha256"),
                trace_sha256=run.get("trace_sha256"),
                exit_codes=run.get("exit_codes"),
                failures=run.get("failures", []),
                missing=run.get("missing", []),
                production_evidence=run.get("production_evidence"),
                source_archive_sha256=(bundle.get("source_archive") or {}).get("sha256"),
                evidence_archive_sha256=(bundle.get("evidence_archive") or {}).get("sha256"),
                source_sha256=bundle.get("source_sha256"),
                core_source_sha256=bundle.get("core_source_sha256"),
                status=run.get("status"),
            )
            if bundle.get("schema") == DAC_SPEC_SCHEMA:
                item.update(
                    selected_policy=run.get("selected_policy"),
                    declared_job_id=run.get("declared_job_id"),
                    matrix_contribution=run.get("matrix_contribution", 0),
                    source_sha256=bundle.get("source_sha256"),
                    core_source_sha256=bundle.get("core_source_sha256"),
                    acceptance_binding_sha256=bundle.get("acceptance_binding_sha256"),
                )
            if (bundle["status"] == "PASS" and run.get("status") == "PASS"
                    and bundle.get("schema") == DAC_SPEC_SCHEMA
                    and not run.get("matrix_contribution")):
                descriptive_records.append(item)
            elif bundle["status"] == "PASS" and run.get("status") == "PASS":
                accepted_records.append(item)
            elif bundle["status"] == "FAIL" or run.get("status") == "FAIL":
                failed_records.append(item)
            elif bundle["status"] == "RUNNING":
                partial_records.append(dict(item, status="RUNNING"))
            else:
                partial_records.append(item)
    for row in rows:
        rec = row_records[row["id"]]
        if rec["status"] == "NOT_RUN":
            missing_records.append(dict(id=row["id"], group=row.get("group"),
                                        policy=row.get("policy"), seed=row.get("seed"),
                                        expected_lanes=list(rec["expected_lanes"])))

    unmatched = []
    for bundle in bundles:
        if not bundle["matrix_job_ids"]:
            unmatched.append(dict(kind="performance_bundle", path=bundle["path"],
                                  status=bundle["status"], reason="no current matrix job ID"))
    for item in provenance["historical_snapshots"]:
        unmatched.append(dict(kind="historical_matrix_snapshot", path=item["path"],
                              status="HISTORICAL_NOT_ACCEPTED",
                              historical_ids_not_in_current=item.get("historical_ids_not_in_current", [])))
    for insight in insights:
        if insight["problems"]:
            unmatched.append(dict(kind="insight_summary", path=insight["path"],
                                  status="UNRESOLVED", reasons=insight["problems"]))
    for item in power:
        if item["problems"]:
            unmatched.append(dict(kind="matched_power_manifest", path=item["path"],
                                  status="UNRESOLVED", reasons=item["problems"]))

    input_files = []
    for path in found["matrices"] + found["bridges"] + found["power"]:
        input_files.append(dict(path=str(path), sha256=sha256_file(path)))
    for path in found["insights"] + found["baselines"]:
        input_files.append(dict(path=str(path), sha256=sha256_file(path)))
    for bundle in bundles:
        input_files.append(dict(path=bundle["path"], kind="performance_bundle"))

    return dict(
        schema="cxl-revision-evidence-index-v1",
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        indexer_sha256=sha256_file(Path(__file__)),
        inputs=found["inputs"],
        matrix=dict(
            schema=MATRIX_SCHEMA,
            provenance=provenance,
            jobs=rows,
            rows=row_records,
            counts={status: counts[status] for status in STATUSES},
            by_group=by_group,
            completion=dict(
                planned=len(rows),
                **{"pass": counts.get("PASS", 0)},
                fail=counts.get("FAIL", 0),
                unresolved=counts.get("UNRESOLVED", 0),
                running=counts.get("RUNNING", 0),
                not_run=counts.get("NOT_RUN", 0),
                complete=counts.get("PASS", 0) == len(rows),
                core_unconditional_planned=sum(not r.get("conditional") for r in rows),
                core_unconditional_pass=sum(
                    row_records[r["id"]]["status"] == "PASS" for r in rows if not r.get("conditional")
                ),
                matrix_contribution_from_insight=sum(
                    r["conditional"] and r["status"] == "PASS" for r in row_records.values()
                ),
                matrix_contribution_from_w256=0,
            ),
        ),
        performance=dict(
            bundles=bundles,
            accepted_records=accepted_records,
            descriptive_records=descriptive_records,
            partial_records=partial_records,
            failed_records=failed_records,
            missing_records=missing_records,
            raw_inventory=input_files,
        ),
        matched_power=dict(manifests=power,
            accepted_rows=sum(r["status"] == "PASS" for r in row_records.values()
                              if r["group"] == "matched-power"),
            planned_rows=9, capture_alone_matrix_contribution=0,
            review_release_sha256=sorted(POWER_REVIEW_RELEASE_SHA256)),
        insight_screen=dict(
            scope="MODEL_ONLY",
            artifacts=insights,
            gate_counts=dict(Counter(i.get("gate_status") or "UNKNOWN" for i in insights)),
            matrix_contribution=0,
            note="Model-only insight evidence is inventoried separately and never counts toward the 468 core RTL rows.",
        ),
        baseline_correctness=dict(artifacts=baselines, matrix_contribution=0),
        formal_bridges=dict(
            f2_bridge="BLOCKED" if any(b["blocked"] for b in bridges) else "NOT_INDEXED",
            artifacts=bridges,
            matrix_contribution=0,
            note="Formal F2 bridge evidence is separate from the performance matrix.",
        ),
        unmatched_artifacts=unmatched,
        strict_acceptance=dict(
            exact_matrix_row=True,
            exact_frozen_config=True,
            exact_params=True,
            source_archive_required=True,
            evidence_archive_required=True,
            production_evidence_required=True,
            required_lanes=["trained"],
            optional_lanes=["cold-A", "cold-B"],
            candidate_cold_benefit_scope="SEPARATE_REVIEW_REQUIRED_NOT_MATRIX_COMPLETENESS",
            adaptation_lanes=["trained"],
            w256_never_completes_matrix=True,
            model_only_never_completes_matrix=True,
            old_schema_never_passes=True,
            subset_never_completes_matrix=True,
            complete_selected_bundle_can_pass_declared_rows=True,
            normalized_statistics_export="NOT_EMITTED_INDEX_ONLY",
            result_metric_recomputation="NOT_PERFORMED_INDEX_ONLY",
            dac_schema=DAC_SPEC_SCHEMA,
            dac_selected_candidate="DAC2",
            dac_released_source_sha256=DAC_SOURCE_SHA,
            dac_shared_core_source_sha256=DAC_CORE_SHA,
            dac_native_screen_pilot_bindings_required=True,
            dac1_matrix_contribution=0,
            power_requires_both_arms=True,
            power_requires_pinned_semantic_release=True,
        ),
    )


def write_markdown(index: dict, path: Path) -> None:
    m = index["matrix"]
    p = m["provenance"]
    c = m["completion"]
    lines = [
        "# Revision evidence index",
        "",
        f"Generated UTC: `{index['created_utc']}`.",
        "",
        "This index is read-only with respect to all inputs. It separates the frozen RTL matrix,",
        "model-only insight screens, and formal bridges. A model-only, W256, incomplete, or old-schema",
        "artifact is never evidence of matrix completion.",
        "",
        "## Matrix provenance",
        "",
        f"- Current canonical source: `{p['canonical_source']}`",
        f"- Current canonical jobs: `{p['canonical_job_count']}` (core unconditional `{p['core_unconditional_jobs']}`, conditional `{p['conditional_jobs']}`)",
        f"- Canonical matrix SHA256: `{p['canonical_matrix_sha256']}`",
        f"- Current exact snapshot: `{p['selected_snapshot'] or 'PENDING'}`",
        f"- Corrected `heavy-id3` rows with static reset permutation: `{p['heavy_id3_corrected_ids']}`",
        "",
        "Historical snapshots are retained below but are not accepted as the current matrix:",
    ]
    if p["historical_snapshots"]:
        for item in p["historical_snapshots"]:
            lines.append(
                f"- `{item['path']}`: {item.get('job_count', '?')} rows, "
                f"{len(item.get('historical_ids_not_in_current', []))} IDs not in current canonical matrix, "
                f"matrix hash matches declared: `{item.get('declared_hash_matches')}`"
            )
    else:
        lines.append("- None indexed.")
    lines += [
        "",
        "## Matrix coverage",
        "",
        f"`PASS={c['pass']}`, `FAIL={c['fail']}`, `UNRESOLVED={c['unresolved']}`, "
        f"`RUNNING={c['running']}`, `NOT_RUN={c['not_run']}`, planned `{c['planned']}`.",
        "",
        "| Group | Planned | PASS | FAIL | UNRESOLVED | RUNNING | NOT_RUN |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group, counts in m["by_group"].items():
        lines.append(
            f"| {group} | {counts['planned']} | {counts['PASS']} | {counts['FAIL']} | "
            f"{counts['UNRESOLVED']} | {counts['RUNNING']} | {counts['NOT_RUN']} |"
        )
    lines += [
        "",
        f"Core unconditional RTL completion: `{c['core_unconditional_pass']}/{c['core_unconditional_planned']}`.",
        f"Full 498-row completion: `{c['pass']}/{c['planned']}`; complete: `{c['complete']}`.",
        "",
        "## Separate evidence",
        "",
        f"- Model-only insight summaries indexed: `{len(index['insight_screen']['artifacts'])}`; "
        f"matrix contribution: `{index['insight_screen']['matrix_contribution']}`.",
        f"- F2 formal bridge: `{index['formal_bridges']['f2_bridge']}`; "
        f"matrix contribution: `{index['formal_bridges']['matrix_contribution']}`.",
        "- Complete selected production bundles can pass their exact declared rows; absent rows remain NOT_RUN.",
        "- W256 sensitivity and incomplete production bundles cannot establish production PASS.",
        "",
        "## Strict acceptance",
        "",
        "A matrix row is `PASS` only when all applicable production lanes have exact frozen job",
        "configuration, exact params/seed/cohort, PASS scope with `production_evidence=true`,",
        "verified `sources.zip` bytes, verified `evidence.zip` bytes, and matching result/scope/summary records.",
        "Each core RTL row requires its declared trained run (including both A/B cohorts);",
        "adaptation uses its continuous run. Optional cold-A/B replays are tracked separately",
        "and do not multiply core jobs. Candidate cold benefit scope requires separate review.",
        "Missing required lanes, W256 evidence, model-only evidence, old schemas, and hash",
        "mismatches cannot become PASS.",
        "",
        "Matched trained-power rows require A and B individually checked against native export",
        "audits, frozen project/mapped sources, remote exits, raw replay/SAIF/PT reports and",
        "independently reviewed semantic receipts pinned in the indexer. A single capture or",
        "single accepted arm contributes zero rows. Power records stay separate from RTL",
        "performance records and paired latency analysis.",
        "",
        "## Inputs and full detail",
        "",
    ]
    for item in index["insight_screen"]["artifacts"]:
        if item.get("kind") == "evaluate":
            lines.append(
                f"- MODEL_ONLY evaluation `{item['path']}`: completed HOG `{item['completed']}`, "
                f"feedback `{item['feedback_count']}`, gate `{item['gate_status']}`, "
                f"frozen candidate `{item['frozen_candidate']}`; matrix contribution `0`."
            )
    for item in index["baseline_correctness"]["artifacts"]:
        lines.append(f"- Baseline `{item['path']}`: `{item['status']}`, scope `{item['scope']}`; "
                     "correctness inventory only, matrix contribution `0`.")
    for item in index["performance"]["raw_inventory"]:
        lines.append(f"- `{item['path']}`" + (f" ({item.get('kind')})" if item.get("kind") else ""))
    lines += [
        "",
        "Full per-row statuses, per-run hashes/seeds/cohorts/exits/failures/missing fields, raw bundles,",
        "unmatched artifacts, and historical snapshots are in `matrix-coverage.json`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True,
                        help="explicit artifact file/directory; repeat for multiple roots")
    parser.add_argument("--out", type=Path, required=True,
                        help="new output directory (must not exist)")
    args = parser.parse_args(argv)
    output = args.out.resolve()
    if output.exists():
        parser.error(f"refusing existing output directory: {output}")
    try:
        index = build_index(args.input)
        output.mkdir(parents=True, exist_ok=False)
        (output / "matrix-coverage.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_markdown(index, output / "EVIDENCE_INDEX.md")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(index["matrix"]["completion"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
