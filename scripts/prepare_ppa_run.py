#!/usr/bin/env python3
"""Prepare one self-contained CXL scheduler DC/PT run directory for later upload to the EDA host.

Local preparation only: Python standard library, no network, SSH, credentials or EDA execution.
The generated run.sh runs on the EDA host after upload. Its best final status is
COMMANDS_COMPLETED_REVIEW_REQUIRED, never PASS, timing closure or accepted PPA.

  probe: real DC library read, analysis, parameterized elaboration and link; no compile.
  syn:   probe steps plus a reviewed explicit profile, compile, DC reports, netlist/SDC and PT.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA = "cxl-scheduler-ppa-profile/v1"
TOP_MODULE = "switch_top"
FILELIST = "rtl/filelist_switch.f"
TOP_SOURCE = "rtl/top/switch_top.sv"
APPROVAL = "specs/APPROVAL.md"
DC_SCRIPT = "syn/ppa_dc.tcl"
PT_SCRIPT = "sta/ppa_pt.tcl"
NETLIST = "output/switch_top.syn.v"
SDC = "output/switch_top.syn.sdc"

# Primary nine (Spec v1.0 section 11); Algorithm-2 N4 requires an explicit separate opt-in.
POLICIES = {"fcfs": 0, "rr": 1, "fai-main": 2}
ALG2_PROFILE_SHA256 = "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d"
N_VALUES = (4, 8, 16)
RR_QUANTUM = 10
FAI_W = 5_000_000
FIFO_DEPTH = 16
DESC_W = 105
TS_W = 32
POLICY_MODULE = {"fcfs": "cxl_fcfs_sel", "rr": "cxl_rr_sched", "fai-main": "cxl_fai_main_sched", "fai-alg2": "cxl_fai_main_sched"}
FORBIDDEN_MODULES = {
    "fcfs": ["cxl_rr_sched", "cxl_fai_main_sched"],
    "rr": ["cxl_fcfs_sel", "cxl_fai_main_sched"],
    "fai-main": ["cxl_rr_sched"],
    "fai-alg2": ["cxl_rr_sched"],
}

DC_REQUIRED_PROBE = [
    "reports/dc_steps.rpt", "reports/dc_versions.rpt", "reports/dc_commands.rpt",
    "reports/dc_app_vars.rpt", "reports/lib_list.rpt", "reports/lib_metadata.rpt",
    "reports/dc_units.rpt", "reports/elab_design.rpt", "reports/elab_hierarchy.rpt",
    "reports/elab_ports.rpt", "reports/elab_check_design.rpt", "reports/elab_structure.rpt",
    "reports/dc_status.rpt",
]
DC_REQUIRED_SYN = DC_REQUIRED_PROBE + [
    "reports/profile_applied.rpt", "reports/check_design_pre.rpt", "reports/check_timing_pre.rpt",
    "reports/check_design_post.rpt", "reports/check_timing_post.rpt", "reports/area.rpt",
    "reports/area_hier.rpt", "reports/area_summary.rpt", "reports/reference.rpt", "reports/qor.rpt",
    "reports/dc_timing_max.rpt", "reports/dc_timing_min.rpt", "reports/dc_constraints.rpt",
    "reports/dc_clocks.rpt", "reports/syn_design.rpt", "reports/syn_structure.rpt", NETLIST, SDC,
]
PT_REQUIRED = [
    "reports/pt_steps.rpt", "reports/pt_versions.rpt", "reports/pt_commands.rpt",
    "reports/pt_app_vars.rpt", "reports/pt_structure.rpt", "reports/pt_units.rpt", "reports/pt_design.rpt",
    "reports/pt_check_timing.rpt", "reports/pt_timing_max.rpt", "reports/pt_timing_min.rpt",
    "reports/pt_constraints.rpt", "reports/pt_coverage.rpt", "reports/pt_coverage_untested.rpt",
    "reports/pt_coverage_summary.rpt", "reports/pt_disable_timing.rpt", "reports/pt_clocks.rpt",
    "reports/pt_status.rpt",
]

SOURCE_SUFFIXES = {".sv", ".svh", ".v", ".vh"}
PAYLOAD_SUFFIXES = SOURCE_SUFFIXES | {".f", ".md", ".tcl", ".json", ".sh", ".txt", ".rpt", ""}
FORBIDDEN_SUFFIXES = {".db", ".lib", ".gz", ".liberty", ".lef", ".def", ".gds", ".ndm", ".tf",
                      ".sldb", ".lic", ".license", ".so", ".a", ".exe", ".dll", ".pem", ".key"}
MAX_PAYLOAD_FILE_BYTES = 8 * 1024 * 1024
SAFE_REMOTE_PATH = re.compile(r"/[A-Za-z0-9._+\-/]+\.db")
TCL_WORD = re.compile(r"[A-Za-z0-9_.+\-/=,]+")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
LIB_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+\-]{0,127}")

PROFILE_KEYS = {"schema", "profile_id", "status", "review", "library", "units", "clock", "io",
                "wire_load", "compile", "power"}
PROFILE_SECTIONS = {
    "review": {"reviewed_by", "reviewed_on", "evidence"},
    "library": {"db_basename", "sha256", "name", "operating_conditions"},
    "units": {"time", "capacitance", "evidence"},
    "clock": {"port", "name", "period", "setup_uncertainty", "hold_uncertainty", "transition"},
    "io": {"input_delay_min", "input_delay_max", "output_delay_min", "output_delay_max",
           "input_transition", "output_load"},
    "compile": {"command", "map_effort"},
    "power": {"status"},
}
WIRE_LOAD_KEYS = {"fixed_model": {"method", "model", "mode", "rationale"},
                  "zero_wireload": {"method", "rationale"}}


def fail(message: str) -> None:
    raise ValueError(message)


def portable_component(name: str) -> bool:
    """Names storable as ordinary files on Windows and Linux; same rule as remote_eda.py."""
    if not name or name in {".", ".."} or name.endswith((".", " ")) or re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
        return False
    base = name.split(".", 1)[0].rstrip(" ").upper()
    if base in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}:
        return False
    return re.fullmatch(r"(?:COM|LPT)[1-9]", base) is None


def relative_name(name: str, what: str) -> PurePosixPath:
    if not isinstance(name, str) or "\\" in name or not name:
        fail(f"{what} must be a forward-slash relative path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(not portable_component(part) for part in name.split("/")):
        fail(f"{what} must be a plain relative path without '..', empty or special components: {name}")
    return path


def safe_repo_file(root: Path, name: str) -> Path:
    """Return a regular, non-symlinked file strictly inside root whose real path is exactly name."""
    path = relative_name(name, "repository input")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            fail(f"Symlinked or junctioned inputs are forbidden: {name}")
    real_root = root.resolve()
    real = current.resolve()
    if not real.is_relative_to(real_root) or real.relative_to(real_root).as_posix() != name:
        fail(f"Input resolves outside the workspace or to a different name: {name}")
    if not real.is_file():
        fail(f"Input is not a regular file inside the workspace: {name}")
    return real


def parse_filelist(root: Path, name: str = FILELIST) -> list[str]:
    """Exact explicit source list in file order; packages must precede modules, top last."""
    text = safe_repo_file(root, name).read_bytes().decode("utf-8")
    if "/*" in text:
        fail(f"{name}: block comments are not supported")
    files: list[str] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-", "+")) or len(line.split()) != 1:
            fail(f"{name}:{number}: only one plain source path per line is supported: {line}")
        if PurePosixPath(line).suffix.lower() not in SOURCE_SUFFIXES:
            fail(f"{name}:{number}: not an HDL source: {line}")
        safe_repo_file(root, line)
        if line in files:
            fail(f"{name}:{number}: duplicate source {line}")
        files.append(line)
    packages = [i for i, f in enumerate(files)
                if f.startswith("rtl/include/") or PurePosixPath(f).stem.endswith("_pkg")]
    if not packages or packages != list(range(len(packages))):
        fail(f"{name}: package sources must exist and precede all module sources")
    if files[-1] != TOP_SOURCE:
        fail(f"{name}: {TOP_SOURCE} must be the last (top-level) source")
    return files


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git(root: Path, *args: str) -> str:
    executable = shutil.which("git")
    if not executable:
        fail("git is required to attribute the exported source revision")
    done = subprocess.run([executable, "-C", str(root), *args], capture_output=True, check=False)
    if done.returncode:
        raise LookupError(done.stderr.decode("utf-8", errors="replace").strip())
    return done.stdout.decode("utf-8", errors="replace")


def source_state(root: Path) -> dict:
    try:
        head = git(root, "rev-parse", "--verify", "HEAD").strip()
        commit_time = int(git(root, "log", "-1", "--format=%ct", head).strip())
        status = [line for line in git(root, "status", "--porcelain=v1", "--untracked-files=all").splitlines() if line]
    except LookupError as error:
        fail(f"Cannot read git state: {error}")
    return {"head": head, "head_commit_time": commit_time, "worktree_clean": not status,
            "worktree_status_porcelain": status}


def head_blob(root: Path, head: str, name: str) -> str | None:
    try:
        return git(root, "rev-parse", "--verify", "--quiet", f"{head}:{name}").strip() or None
    except LookupError:
        return None


def export_file(root: Path, head: str, name: str, role: str) -> tuple[bytes, dict]:
    """Accepted sources must equal HEAD byte-for-byte; flow scripts are recorded if uncommitted."""
    data = safe_repo_file(root, name).read_bytes()
    blob = git_blob_id(data)
    committed = head_blob(root, head, name)
    record = {"path": name, "role": role, "sha256": hashlib.sha256(data).hexdigest(),
              "git_blob": blob, "head_blob": committed, "matches_head": committed == blob}
    if role in {"rtl", "filelist", "approval"} and not record["matches_head"]:
        fail(f"{name} is untracked or differs from HEAD {head}; accepted source must be committed and unmodified")
    if role == "flow" and b"\r" in data:
        fail(f"{name} must use LF line endings")
    return data, record


def approval_record(data: bytes) -> dict:
    text = data.decode("utf-8-sig")
    fields = {}
    for key in ("Architecture status", "Specification", "Approved by", "Approved on"):
        match = re.search(rf"^{key}:[ \t]*(\S[^\r\n]*)$", text, re.M)
        fields[key] = match.group(1).strip() if match else None
    if fields["Architecture status"] != "APPROVED" or not fields["Specification"] or not fields["Approved on"]:
        fail(f"{APPROVAL} must record an APPROVED architecture, specification and approval date")
    return fields


def validate_library(value: str) -> str:
    if not isinstance(value, str) or not SAFE_REMOTE_PATH.fullmatch(value):
        fail("--library must be an absolute Linux .db path using only letters, digits and . _ + - /")
    parts = PurePosixPath(value).parts
    if ".." in parts or "." in value.split("/") or "//" in value:
        fail("--library must not contain '.', '..' or empty path components")
    return value


# ---------------------------------------------------------------- profile schema

def reject_constant(name: str) -> None:
    fail(f"Non-finite JSON number {name} is not allowed in the profile")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            fail(f"Duplicate profile key {key!r} is contradictory")
        result[key] = value
    return result


def exact_keys(obj: object, keys: set[str], where: str) -> dict:
    if not isinstance(obj, dict):
        fail(f"profile {where} must be an object")
    missing, extra = keys - set(obj), set(obj) - keys
    if missing or extra:
        fail(f"profile {where}: missing {sorted(missing)} / unexpected {sorted(extra)}")
    return obj


def number(obj: dict, key: str, where: str, positive: bool = False) -> float | int:
    value = obj[key]
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        fail(f"profile {where}.{key} must be a finite JSON number, not {value!r}")
    if value < 0 or (positive and value == 0):
        fail(f"profile {where}.{key} must be {'positive' if positive else 'nonnegative'}: {value}")
    return value


def text(obj: dict, key: str, where: str, pattern: re.Pattern | None = None) -> str:
    value = obj[key]
    if not isinstance(value, str) or not value.strip() or len(value) > 1000 or any(ord(c) < 32 for c in value):
        fail(f"profile {where}.{key} must be a nonempty single-line string")
    if pattern is not None and not pattern.fullmatch(value):
        fail(f"profile {where}.{key} has unsupported characters: {value!r}")
    return value


def load_profile(path: Path, library: str) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    try:
        profile = json.loads(raw.decode("utf-8-sig"), parse_constant=reject_constant,
                             object_pairs_hook=unique_object)
    except json.JSONDecodeError as error:
        fail(f"profile is not valid JSON: {error}")
    validate_profile(profile, library)
    return profile, raw


def validate_profile(profile: object, library: str) -> None:
    """Explicit measurement values; the optional optimization overlay defaults to no change."""
    keys = PROFILE_KEYS | {"optimization"} if isinstance(profile, dict) and "optimization" in profile else PROFILE_KEYS
    exact_keys(profile, keys, "top level")
    if "optimization" in profile:
        opt = exact_keys(profile["optimization"], {"max_capacitance_scale"}, "optimization")
        if number(opt, "max_capacitance_scale", "optimization", positive=True) > 1:
            fail("profile optimization.max_capacitance_scale must be <= 1 (tightening only)")
    if profile["schema"] != PROFILE_SCHEMA:
        fail(f"profile schema must be {PROFILE_SCHEMA!r}")
    text(profile, "profile_id", "", re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"))
    if profile["status"] not in {"PILOT", "FROZEN"}:
        fail("profile status must be PILOT or FROZEN")
    for section, keys in PROFILE_SECTIONS.items():
        exact_keys(profile[section], keys, section)

    review = profile["review"]
    text(review, "reviewed_by", "review")
    text(review, "evidence", "review")
    try:
        dt.date.fromisoformat(text(review, "reviewed_on", "review", re.compile(r"\d{4}-\d{2}-\d{2}")))
    except ValueError:
        fail("profile review.reviewed_on is not a valid date")

    lib = profile["library"]
    if text(lib, "db_basename", "library", LIB_TOKEN) != PurePosixPath(library).name:
        fail("profile library.db_basename contradicts the --library path")
    text(lib, "sha256", "library", re.compile(r"[0-9a-f]{64}"))
    text(lib, "name", "library", LIB_TOKEN)
    text(lib, "operating_conditions", "library", LIB_TOKEN)

    units = profile["units"]
    text(units, "time", "units", re.compile(r"(?:1|10|100)(?:ps|ns)"))
    text(units, "capacitance", "units", re.compile(r"(?:1|10|100)(?:ff|pf)"))
    text(units, "evidence", "units")

    clock = profile["clock"]
    if clock["port"] != "clk":
        fail("profile clock.port must be clk, the single scheduler clock")
    text(clock, "name", "clock", IDENTIFIER)
    period = number(clock, "period", "clock", positive=True)
    if number(clock, "setup_uncertainty", "clock") >= period:
        fail("profile clock.setup_uncertainty must be smaller than clock.period")
    number(clock, "hold_uncertainty", "clock")
    number(clock, "transition", "clock")

    io_ = profile["io"]
    for direction in ("input", "output"):
        low = number(io_, f"{direction}_delay_min", "io")
        high = number(io_, f"{direction}_delay_max", "io")
        if low > high:
            fail(f"profile io.{direction}_delay_min exceeds io.{direction}_delay_max")
        if high >= period:
            fail(f"profile io.{direction}_delay_max must be smaller than clock.period")
    number(io_, "input_transition", "io")
    number(io_, "output_load", "io")

    wire = profile["wire_load"]
    if not isinstance(wire, dict) or wire.get("method") not in WIRE_LOAD_KEYS:
        fail("profile wire_load.method must be fixed_model or zero_wireload (no automatic area-based selection)")
    exact_keys(wire, WIRE_LOAD_KEYS[wire["method"]], "wire_load")
    text(wire, "rationale", "wire_load")
    if wire["method"] == "fixed_model":
        text(wire, "model", "wire_load", LIB_TOKEN)
        if wire["mode"] != "top":
            fail("profile wire_load.mode must be top: one fixed model for the whole switch hierarchy")

    comp = profile["compile"]
    if comp["command"] != "compile":
        fail("profile compile.command must be compile (same method for all nine configurations)")
    if comp["map_effort"] not in {"tool_default", "medium", "high"}:
        fail("profile compile.map_effort must be tool_default, medium or high")
    if profile["power"]["status"] != "NOT_RUN":
        fail("profile power.status must be NOT_RUN until activity-annotated capability is established")


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def profile_template() -> dict:
    """Placeholders only: this template is intentionally rejected until reviewed values are filled."""
    fill = None
    return {
        "schema": PROFILE_SCHEMA, "profile_id": "FILL", "status": "PILOT",
        "review": {"reviewed_by": "FILL", "reviewed_on": "FILL", "evidence": "FILL probe run/report"},
        "library": {"db_basename": "FILL", "sha256": "FILL", "name": "FILL", "operating_conditions": "FILL"},
        "units": {"time": "FILL", "capacitance": "FILL", "evidence": "FILL reports/dc_units.rpt"},
        "clock": {"port": "clk", "name": "core_clk", "period": fill, "setup_uncertainty": fill,
                  "hold_uncertainty": fill, "transition": fill},
        "io": {"input_delay_min": fill, "input_delay_max": fill, "output_delay_min": fill,
               "output_delay_max": fill, "input_transition": fill, "output_load": fill},
        "wire_load": {"method": "fixed_model", "model": "FILL", "mode": "top", "rationale": "FILL"},
        "compile": {"command": "compile", "map_effort": "FILL"},
        "power": {"status": "NOT_RUN"},
    }


# ---------------------------------------------------------------- generated files

def tcl_word(value: object) -> str:
    word = str(value)
    if not TCL_WORD.fullmatch(word):
        fail(f"Refusing to place unsafe text in Tcl: {word!r}")
    return "{" + word + "}"


def tcl_number(value: float | int) -> str:
    rendered = str(value) if isinstance(value, int) else repr(float(value))
    if not re.fullmatch(r"-?[0-9.]+(?:e[-+]?[0-9]+)?", rendered):
        fail(f"Cannot render profile number {value!r}")
    return rendered


def parameters(policy: str, n_src: int) -> dict:
    ts_enabled = policy in {"fcfs", "fai-main", "fai-alg2"}
    code = 3 if policy == "fai-alg2" else POLICIES[policy]
    desc_bits = n_src * FIFO_DEPTH * DESC_W
    ts_bits = n_src * FIFO_DEPTH * TS_W
    return {
        "top_module": TOP_MODULE, "policy_name": policy, "N_SRC": n_src, "POLICY": code,
        "RR_QUANTUM": RR_QUANTUM, "FAI_W": FAI_W, "D": FIFO_DEPTH, "M": 1, "DESC_W": DESC_W,
        "elab_parameters": f"N_SRC={n_src},POLICY={code},RR_QUANTUM={RR_QUANTUM},FAI_W={FAI_W}",
        "arrival_metadata": ts_enabled,
        "expected": {
            "fifo_instances": n_src, "out_hold_instances": 1,
            "descriptor_storage_bits": desc_bits,
            "timestamp_storage_bits": ts_bits if ts_enabled else 0,
            # Lower bound: full descriptor (+ timestamp) storage must exist before compile.
            "min_register_bits": desc_bits + (ts_bits if ts_enabled else 0),
            # RR upper bound: no per-entry timestamp bank can be hidden in the design.
            "max_register_bits_exclusive": None if ts_enabled else desc_bits + ts_bits,
            "policy_module": POLICY_MODULE[policy], "forbidden_modules": FORBIDDEN_MODULES[policy],
            "port_bits": {"clk": 1, "rst_n": 1, "i_in_valid": n_src, "o_in_ready": n_src,
                          "i_in_desc": n_src * DESC_W, "o_out_valid": 1, "i_out_ready": 1,
                          "o_out_desc": DESC_W, "o_out_source": (n_src - 1).bit_length()},
            "timed_input_bits": n_src + n_src * DESC_W + 2,
        },
    }


def run_config(mode: str, run_name: str, params: dict, library: str, sources: list[str],
               profile: dict | None, profile_sha: str | None) -> bytes:
    exp = params["expected"]
    lines = [
        "# Generated by scripts/prepare_ppa_run.py: resolved configuration for one run.",
        "# Paths and reviewed values only; no library content.",
        f"set PPA_MODE {tcl_word(mode)}",
        f"set RUN_NAME {tcl_word(run_name)}",
        f"set TOP_MODULE {tcl_word(TOP_MODULE)}",
        f"set POLICY_NAME {tcl_word(params['policy_name'])}",
        f"set PARAM_N_SRC {params['N_SRC']}",
        f"set PARAM_POLICY {params['POLICY']}",
        f"set PARAM_RR_QUANTUM {params['RR_QUANTUM']}",
        f"set PARAM_FAI_W {params['FAI_W']}",
        f"set ELAB_PARAMETERS {tcl_word(params['elab_parameters'])}",
        f"set TARGET_LIBRARY {tcl_word(library)}",
        f"set TARGET_LIBRARY_BASENAME {tcl_word(PurePosixPath(library).name)}",
        "set RTL_FILES [list " + " ".join(tcl_word(s) for s in sources) + "]",
        f"set NETLIST_FILE {tcl_word(NETLIST)}",
        f"set SDC_FILE {tcl_word(SDC)}",
        f"set EXPECT_FIFO_INSTANCES {exp['fifo_instances']}",
        f"set EXPECT_OUT_HOLD_INSTANCES {exp['out_hold_instances']}",
        f"set EXPECT_MIN_REGISTER_BITS {exp['min_register_bits']}",
        f"set EXPECT_MAX_REGISTER_BITS_EXCLUSIVE {exp['max_register_bits_exclusive'] or 0}",
        f"set EXPECT_POLICY_MODULE {tcl_word(exp['policy_module'])}",
        "set FORBIDDEN_POLICY_MODULES [list " + " ".join(tcl_word(m) for m in exp["forbidden_modules"]) + "]",
        "set EXPECT_PORT_BITS [list " + " ".join(f"{p} {b}" for p, b in exp["port_bits"].items()) + "]",
        f"set EXPECT_TIMED_INPUT_BITS {exp['timed_input_bits']}",
    ]
    if profile is not None:
        lib, units, clock, io_ = profile["library"], profile["units"], profile["clock"], profile["io"]
        wire, comp = profile["wire_load"], profile["compile"]
        lines += [
            f"set PROFILE_ID {tcl_word(profile['profile_id'])}",
            f"set PROFILE_STATUS {tcl_word(profile['status'])}",
            f"set PROFILE_SHA256 {tcl_word(profile_sha)}",
            f"set LIB_NAME {tcl_word(lib['name'])}",
            f"set OPERATING_CONDITIONS {tcl_word(lib['operating_conditions'])}",
            f"set UNIT_TIME {tcl_word(units['time'])}",
            f"set UNIT_CAP {tcl_word(units['capacitance'])}",
            f"set CLOCK_PORT {tcl_word(clock['port'])}",
            f"set CLOCK_NAME {tcl_word(clock['name'])}",
            f"set CLOCK_PERIOD {tcl_number(clock['period'])}",
            f"set CLOCK_SETUP_UNCERTAINTY {tcl_number(clock['setup_uncertainty'])}",
            f"set CLOCK_HOLD_UNCERTAINTY {tcl_number(clock['hold_uncertainty'])}",
            f"set CLOCK_TRANSITION {tcl_number(clock['transition'])}",
            f"set INPUT_DELAY_MIN {tcl_number(io_['input_delay_min'])}",
            f"set INPUT_DELAY_MAX {tcl_number(io_['input_delay_max'])}",
            f"set OUTPUT_DELAY_MIN {tcl_number(io_['output_delay_min'])}",
            f"set OUTPUT_DELAY_MAX {tcl_number(io_['output_delay_max'])}",
            f"set INPUT_TRANSITION {tcl_number(io_['input_transition'])}",
            f"set OUTPUT_LOAD {tcl_number(io_['output_load'])}",
            f"set WIRE_LOAD_METHOD {tcl_word(wire['method'])}",
            f"set WIRE_LOAD_MODEL {tcl_word(wire.get('model', 'NONE'))}",
            f"set WIRE_LOAD_MODE {tcl_word(wire.get('mode', 'NONE'))}",
            f"set COMPILE_MAP_EFFORT {tcl_word(comp['map_effort'])}",
        ]
        if "optimization" in profile:
            lines.append(f"set MAX_CAPACITANCE_SCALE {tcl_number(profile['optimization']['max_capacitance_scale'])}")
    return ("\n".join(lines) + "\n").encode("ascii")


def dc_marker(mode: str, run_name: str, params: dict) -> bytes:
    return (f"DC_STATUS: COMMANDS_COMPLETED\nMODE: {mode}\nRUN: {run_name}\nTOP: {TOP_MODULE}\n"
            f"ELAB_PARAMETERS: {params['elab_parameters']}\n").encode("ascii")


def pt_marker(run_name: str) -> bytes:
    return (f"PT_STATUS: COMMANDS_COMPLETED\nRUN: {run_name}\nTOP: {TOP_MODULE}\n"
            f"NETLIST: {NETLIST}\nSDC: {SDC}\n").encode("ascii")


RUN_SH = r"""#!/usr/bin/env bash
# Generated by scripts/prepare_ppa_run.py for @@RUN_NAME@@ (mode @@MODE@@).
# Run on the EDA host AFTER upload and extraction, once per prepared directory:
#   bash ./run.sh          (optional: EDA_MODULE=<site module> bash ./run.sh)
# execution-status.txt is COMMANDS_COMPLETED_REVIEW_REQUIRED only when every tool command
# finished and every automatic failure check passed. That is never PASS, timing closure or
# accepted PPA; the reports still need review. Power is NOT_RUN.
set -uo pipefail
umask 022
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 90

readonly RUN_NAME='@@RUN_NAME@@'
readonly MODE='@@MODE@@'
readonly TARGET_LIBRARY='@@TARGET_LIBRARY@@'
readonly EXPECTED_LIBRARY_SHA256='@@LIBRARY_SHA256@@'
readonly PROFILE_STATUS='@@PROFILE_STATUS@@'
readonly NETLIST='@@NETLIST@@'
readonly SDC='@@SDC@@'
readonly EDA_MODULE_NAME="${EDA_MODULE:-Synopsys_x86-64/2024}"
readonly MESSAGE_RE='(^|[^A-Za-z0-9_])(Error|ERROR|Fatal|FATAL)[[:space:]]*:|EDA_FAILURE'
readonly UNRESOLVED_RE='unable to resolve|unresolved reference|creating black[ _-]?box'
# PrimeTime ends its log with this summary; errors inside redirected reports are counted there too.
readonly DIAGNOSTICS_RE='Diagnostics summary:[[:space:]]*[1-9][0-9]*[[:space:]]+errors?'
readonly RELEASE_RE='[A-Z]-[0-9]{4}\.[0-9]{2}(-SP[0-9]+(\.[0-9]+)?)?'
readonly EXCEPTION_RE='^[[:space:]]*(set_false_path|set_multicycle_path|set_disable_timing|set_case_analysis|set_max_delay|set_min_delay|set_clock_groups)([[:space:]]|$)'

if [[ -e execution-status.txt || -e reports || -e logs || -e output || -e work ]]; then
  echo "run.sh: $RUN_NAME was already used in this directory; prepare and upload a new run" >&2
  exit 91
fi
mkdir reports logs output || exit 92

STAGE=start
DONE=0
on_exit() {
  local rc=$?
  if [[ $DONE -ne 1 ]]; then
    [[ $rc -ne 0 ]] || rc=1
    printf 'FAILED\nSTAGE: %s\nEXIT: %s\nRUN: %s\nMODE: %s\n' "$STAGE" "$rc" "$RUN_NAME" "$MODE" > execution-status.txt
  fi
  exit "$rc"
}
trap on_exit EXIT
die() { printf 'RUN_FAILURE [%s]: %s\n' "$STAGE" "$*" | tee -a logs/run.log >&2; exit 1; }
note() { printf '%s\n' "$*" | tee -a logs/run.log; }

check_outputs() {  # tool, file listing required outputs
  local tool=$1 list=$2 path
  while IFS= read -r path; do
    [[ -n $path ]] || continue
    [[ -f $path && ! -L $path && -s $path ]] || die "$tool required output missing or empty: $path"
    if [[ $path == *.rpt ]] && grep -Eq -- "$MESSAGE_RE" "$path"; then
      die "$tool report contains Error/Fatal/EDA_FAILURE lines: $path"
    fi
  done < "$list"
}

check_tool() {  # tool, exit status, log, marker, expected marker, required-output list
  local tool=$1 rc=$2 log=$3 marker=$4 expected=$5 list=$6
  printf '%s_exit=%s\n' "$tool" "$rc" >> logs/tool-exit.txt
  [[ $rc -eq 0 ]] || die "$tool exited with status $rc"
  [[ -s $log ]] || die "$tool log is empty"
  if grep -En -- "$MESSAGE_RE" "$log" > "logs/$tool-error-lines.txt"; then
    die "$tool log contains Error/Fatal/EDA_FAILURE lines (logs/$tool-error-lines.txt)"
  fi
  if grep -Ein -- "$UNRESOLVED_RE" "$log" > "logs/$tool-unresolved-lines.txt"; then
    die "$tool log reports unresolved references or black boxes (logs/$tool-unresolved-lines.txt)"
  fi
  if grep -En -- "$DIAGNOSTICS_RE" "$log" > "logs/$tool-diagnostics-errors.txt"; then
    die "$tool diagnostics summary counts errors (logs/$tool-diagnostics-errors.txt)"
  fi
  [[ -f $marker ]] && cmp -s -- "$marker" "$expected" || die "$tool completion marker missing or unexpected: $marker"
  check_outputs "$tool" "$list"
  { grep -Eo '\([A-Z][A-Z0-9]*-[0-9]+\)' "$log" | sort | uniq -c | sort -rn; } > "logs/$tool-message-id-counts.txt" || true
}

# The -version query is informational: W-2024.09 dc_shell prints a valid banner but exits 1. Its
# exit is recorded; acceptance requires the tool's own identity and a release token, and no
# Error/Fatal line. Batch dc_shell/pt_shell runs below still require exit 0.
check_version() {  # tool, exit status of "<tool> -version"
  local tool=$1 rc=$2 identity release base="logs/$1-version"
  case $tool in
    dc_shell) identity='dc_shell|Design Compiler' ;;
    pt_shell) identity='pt_shell|PrimeTime' ;;
    *) die "no version identity rule for $tool" ;;
  esac
  printf '%s_version_query_exit=%s\n' "$tool" "$rc" >> logs/environment.log
  cat -- "$base.stdout" "$base.stderr" > "$base.log"
  if grep -Eq -- "$MESSAGE_RE" "$base.log"; then die "$tool -version printed Error/Fatal lines (exit $rc)"; fi
  grep -Eq -- "$identity" "$base.log" || die "$tool -version output does not identify $tool (exit $rc)"
  release=$(grep -Eo -- "$RELEASE_RE" "$base.log" | head -n 1)
  [[ -n $release ]] || die "$tool -version output has no Synopsys release token (exit $rc)"
  printf '%s_release=%s\n' "$tool" "$release" >> logs/environment.log
  if [[ $rc -ne 0 ]]; then
    note "$tool -version exited $rc with a valid $release banner; recorded as informational"
  fi
}

STAGE=payload
sha256sum --strict -c SHA256SUMS > logs/payload-verification.log 2>&1 || die "payload SHA256SUMS verification failed"

STAGE=environment
{
  echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "hostname=$(hostname)"
  echo "kernel=$(uname -srm)"
  echo "bash=$BASH_VERSION"
  echo "mode=$MODE"
  echo "profile_status=$PROFILE_STATUS"
  echo "eda_module_requested=$EDA_MODULE_NAME"
} > logs/environment.log
if type module > /dev/null 2>&1; then
  module load "$EDA_MODULE_NAME" > logs/module-load.log 2>&1 || die "module load $EDA_MODULE_NAME failed"
  module list > logs/module-list.log 2>&1 || true
  grep -Fq -- "$EDA_MODULE_NAME" logs/module-list.log || die "module list does not show $EDA_MODULE_NAME"
else
  note "module command unavailable in this shell; no module init file is guessed; using PATH" >> logs/environment.log
fi
for setup in .synopsys_dc.setup .synopsys_pt.setup; do
  if [[ -f $HOME/$setup ]]; then
    echo "home_$setup sha256=$(sha256sum < "$HOME/$setup" | cut -d' ' -f1)"
  else
    echo "home_$setup absent"
  fi
done >> logs/environment.log

STAGE=tools
tools=(dc_shell)
[[ $MODE == syn ]] && tools+=(pt_shell)
for tool in "${tools[@]}"; do
  tool_path=$(command -v "$tool") || die "$tool not found; load the site Synopsys module first"
  echo "${tool}_path=$tool_path" >> logs/environment.log
  "$tool" -version < /dev/null > "logs/$tool-version.stdout" 2> "logs/$tool-version.stderr"
  check_version "$tool" "$?"
done

STAGE=library
[[ -f $TARGET_LIBRARY ]] || die "target library is not a regular file: $TARGET_LIBRARY"
[[ -r $TARGET_LIBRARY ]] || die "target library is not readable: $TARGET_LIBRARY"
library_sha=$(sha256sum -- "$TARGET_LIBRARY" | cut -d' ' -f1) || die "cannot hash target library"
{
  echo "path=$TARGET_LIBRARY"
  echo "size_bytes=$(stat -Lc %s -- "$TARGET_LIBRARY")"
  echo "sha256=$library_sha"
  echo "expected_sha256=${EXPECTED_LIBRARY_SHA256:-NOT_PINNED_IN_PROBE}"
} > logs/library.log
if [[ -n $EXPECTED_LIBRARY_SHA256 && $library_sha != "$EXPECTED_LIBRARY_SHA256" ]]; then
  die "target library sha256 differs from the reviewed profile"
fi

STAGE=dc
dc_shell -f syn/ppa_dc.tcl < /dev/null > logs/dc.log 2>&1
dc_rc=$?
check_tool dc "$dc_rc" logs/dc.log reports/dc_status.rpt expected/dc_status.rpt expected/dc_required.txt

if [[ $MODE == syn ]]; then
  STAGE=dc-handoff
  if grep -En -- "$EXCEPTION_RE" "$SDC" > logs/sdc-exception-lines.txt; then
    die "generated SDC contains timing exceptions (logs/sdc-exception-lines.txt)"
  fi
  grep -Eq '^[[:space:]]*create_clock([[:space:]]|$)' "$SDC" || die "generated SDC has no create_clock"
  grep -Eq '^[[:space:]]*module[[:space:]]+switch_top([[:space:](;]|$)' "$NETLIST" || die "netlist has no switch_top module"
  sha256sum -- "$NETLIST" "$SDC" > logs/dc-handoff.sha256 || die "cannot hash DC netlist/SDC"

  STAGE=pt
  pt_shell -f sta/ppa_pt.tcl < /dev/null > logs/pt.log 2>&1
  pt_rc=$?
  check_tool pt "$pt_rc" logs/pt.log reports/pt_status.rpt expected/pt_status.rpt expected/pt_required.txt
  sha256sum --strict -c logs/dc-handoff.sha256 > logs/pt-handoff-verification.log 2>&1 || die "netlist/SDC changed after DC"
fi

STAGE=finalize
for report in reports/*.rpt; do
  if grep -Eq -- "$MESSAGE_RE" "$report"; then die "report contains Error/Fatal/EDA_FAILURE lines: $report"; fi
done
printf 'POWER_STATUS: NOT_RUN\nREASON: activity-annotated power capability and coverage are not established; no vectorless value is reported as workload power.\n' > reports/power_status.rpt
# Review facts only: violations and untested checks never fail or pass the run automatically.
review_facts=''
for report in reports/dc_constraints.rpt reports/pt_constraints.rpt; do
  if [[ -f $report ]]; then
    review_facts+="$(basename "$report" .rpt)_violated_lines: $(grep -c '(VIOLATED)' "$report" || true)"$'\n'
  fi
done
if [[ -f reports/pt_coverage_summary.rpt ]]; then
  coverage=$(grep -m 1 '^ANALYSIS_COVERAGE = ' reports/pt_coverage_summary.rpt | cut -d' ' -f3)
  review_facts+="pt_analysis_coverage: ${coverage:-NOT_FOUND}"$'\n'
fi
find reports output logs -type f -print0 | sort -z | xargs -0 sha256sum > RESULT_SHA256SUMS || die "cannot hash results"
DONE=1
printf 'COMMANDS_COMPLETED_REVIEW_REQUIRED\nRUN: %s\nMODE: %s\nPROFILE_STATUS: %s\nPOWER: NOT_RUN\n%sNOTE: commands finished and automatic failure checks found nothing; not PASS, timing closure or accepted PPA.\n' \
  "$RUN_NAME" "$MODE" "$PROFILE_STATUS" "$review_facts" > execution-status.txt
echo COMMANDS_COMPLETED_REVIEW_REQUIRED
"""


def render_run_sh(values: dict[str, str]) -> bytes:
    script = RUN_SH
    for key, value in values.items():
        if not re.fullmatch(r"[A-Za-z0-9._+\-/]*", value):
            fail(f"Refusing unsafe value for run.sh {key}: {value!r}")
        script = script.replace(f"@@{key}@@", value)
    if "@@" in script:
        fail("run.sh template has an unresolved placeholder")
    return script.encode("ascii")


# ---------------------------------------------------------------- payload output

def check_payload(files: dict[str, bytes]) -> None:
    for name, data in files.items():
        path = relative_name(name, "payload member")
        lowered = [part.lower() for part in path.parts]
        if ".git" in lowered or any(part.startswith(".") for part in path.parts):
            fail(f"Hidden or .git payload members are forbidden: {name}")
        suffixes = {s.lower() for s in path.suffixes}
        if suffixes & FORBIDDEN_SUFFIXES or path.suffix.lower() not in PAYLOAD_SUFFIXES:
            fail(f"Refusing non-allowlisted payload file type (possible proprietary asset): {name}")
        if len(data) > MAX_PAYLOAD_FILE_BYTES:
            fail(f"Payload file is unexpectedly large: {name}")


def claim_output(output: Path, root: Path) -> Path:
    """Create the new output directory exclusively; existing paths are never reused."""
    if not portable_component(output.name):
        fail("--output must end in a plain directory name")
    if os.path.lexists(output):
        fail(f"Refusing to overwrite existing output: {output}")
    parent = output.parent.resolve()
    if not parent.is_dir():
        fail(f"Output parent directory does not exist: {output.parent}")
    target = parent / output.name
    real_root = root.resolve()
    if target.is_relative_to(real_root) and not target.is_relative_to(real_root / "artifacts"):
        fail("Inside the repository, --output must be below the ignored artifacts/ directory")
    os.mkdir(target)
    return target


def write_tar(path: Path, top: str, files: dict[str, bytes], mtime: int) -> None:
    directories = sorted({str(PurePosixPath(name).parent) for name in files} - {"."})
    with path.open("xb") as handle, tarfile.open(fileobj=handle, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        def entry(name: str, kind: bytes, mode: int, size: int = 0) -> tarfile.TarInfo:
            info = tarfile.TarInfo(f"{top}/{name}" if name else top)
            info.type, info.mode, info.size, info.mtime = kind, mode, size, mtime
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            return info
        archive.addfile(entry("", tarfile.DIRTYPE, 0o755))
        expanded = set()
        for directory in directories:
            parts = PurePosixPath(directory).parts
            for index in range(1, len(parts) + 1):
                prefix = "/".join(parts[:index])
                if prefix not in expanded:
                    expanded.add(prefix)
                    archive.addfile(entry(prefix, tarfile.DIRTYPE, 0o755))
        for name in sorted(files):
            data = files[name]
            mode = 0o755 if name == "run.sh" else 0o644
            archive.addfile(entry(name, tarfile.REGTYPE, mode, len(data)), io.BytesIO(data))


def prepare(mode: str, policy: str, n_src: int, library: str, profile_path: Path | None,
            output: Path, root: Path = ROOT, *, supplementary_alg2: bool = False) -> dict:
    if supplementary_alg2:
        if policy != "fai-alg2" or n_src != 4:
            fail("--supplementary-alg2 applies only to fai-alg2 N4")
    elif policy == "fai-alg2":
        fail("fai-alg2 N4 requires explicit --supplementary-alg2 opt-in")
    if policy not in (*POLICIES, "fai-alg2") or n_src not in N_VALUES or mode not in {"probe", "syn"}:
        fail("Only the primary nine configurations (fcfs|rr|fai-main x N4/8/16) in probe|syn mode are supported")
    library = validate_library(library)
    profile = profile_raw = None
    if mode == "syn":
        if profile_path is None:
            fail("syn mode requires --profile with reviewed explicit values")
        profile, profile_raw = load_profile(profile_path, library)
    elif profile_path is not None:
        fail("probe mode applies no profile; omit --profile")
    profile_sha = hashlib.sha256(canonical_json(profile)).hexdigest() if profile else None
    if supplementary_alg2 and mode == "syn" and profile_sha != ALG2_PROFILE_SHA256:
        fail("supplementary Algorithm-2 requires the frozen saed32-rvt-tt-25ns-forqa-cap075-v2 profile")

    state = source_state(root)
    head = state["head"]
    sources = parse_filelist(root)
    exported: dict[str, bytes] = {}
    records = []
    for name, role in ([(s, "rtl") for s in sources] + [(FILELIST, "filelist"), (APPROVAL, "approval"),
                       (DC_SCRIPT, "flow")] + ([(PT_SCRIPT, "flow")] if mode == "syn" else [])):
        data, record = export_file(root, head, name, role)
        exported[name] = data
        records.append(record)
    approval = approval_record(exported[APPROVAL])
    generator = safe_repo_file(root, "scripts/prepare_ppa_run.py").read_bytes()

    params = parameters(policy, n_src)
    if supplementary_alg2:
        params["supplementary"] = True
        params["interpretation"] = "Algorithm-2 target-priority Buffer (Spec 8.6)"
    run_name = f"cxl-ppa-{mode}-{policy}-n{n_src}"
    dc_outputs = list(DC_REQUIRED_SYN if mode == "syn" else DC_REQUIRED_PROBE)
    if profile and profile.get("optimization", {}).get("max_capacitance_scale", 1) < 1:
        dc_outputs.append("reports/dc_cap_optimization.rpt")

    files = dict(exported)
    files["run_config.tcl"] = run_config(mode, run_name, params, library, sources, profile, profile_sha)
    files["parameters.json"] = (json.dumps(params, indent=2) + "\n").encode("ascii")
    files["expected/dc_status.rpt"] = dc_marker(mode, run_name, params)
    files["expected/dc_required.txt"] = ("\n".join(dc_outputs) + "\n").encode("ascii")
    if mode == "syn":
        files["profile.json"] = (json.dumps(profile, indent=2, sort_keys=True) + "\n").encode("ascii")
        files["expected/pt_status.rpt"] = pt_marker(run_name)
        files["expected/pt_required.txt"] = ("\n".join(PT_REQUIRED) + "\n").encode("ascii")
    files["run.sh"] = render_run_sh({
        "RUN_NAME": run_name, "MODE": mode, "TARGET_LIBRARY": library,
        "LIBRARY_SHA256": profile["library"]["sha256"] if profile else "",
        "PROFILE_STATUS": profile["status"] if profile else "NONE", "NETLIST": NETLIST, "SDC": SDC,
    })
    manifest = {
        "generator": "scripts/prepare_ppa_run.py",
        "generator_sha256": hashlib.sha256(generator).hexdigest(),
        "prepared_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "run_name": run_name, "mode": mode, "parameters": params,
        "source": {**state, "exported_files": records, "filelist_order": sources},
        "approval": {"path": APPROVAL, **approval},
        "target_library": {"remote_path": library, "basename": PurePosixPath(library).name,
                           "expected_sha256": profile["library"]["sha256"] if profile else None,
                           "content_bundled": False},
        "profile": None if profile is None else {
            "profile_id": profile["profile_id"], "status": profile["status"],
            "canonical_sha256": profile_sha, "source_file_sha256": hashlib.sha256(profile_raw).hexdigest()},
        "required_outputs": {"dc": dc_outputs,
                             "pt": PT_REQUIRED if mode == "syn" else []},
        "power": "NOT_RUN",
        "status_semantics": ("COMMANDS_COMPLETED_REVIEW_REQUIRED means the commands finished and automatic failure "
                             "checks found nothing; it is not PASS, timing closure or accepted PPA."),
        "file_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("ascii")
    files["SHA256SUMS"] = "".join(f"{hashlib.sha256(files[name]).hexdigest()}  {name}\n"
                                  for name in sorted(files)).encode("ascii")
    check_payload(files)

    target = claim_output(output, root)
    try:
        payload_dir = target / "payload" / run_name
        for name, data in sorted(files.items()):
            path = payload_dir.joinpath(*PurePosixPath(name).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
            if name == "run.sh":
                path.chmod(0o755)
        tar_path = target / "payload.tar"
        write_tar(tar_path, run_name, files, state["head_commit_time"])
        tar_sha = hashlib.sha256(tar_path.read_bytes()).hexdigest()
        (target / "payload.tar.sha256").write_bytes(f"{tar_sha}  payload.tar\n".encode("ascii"))
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return {"output": str(target), "run_name": run_name, "mode": mode, "policy": policy, "N_SRC": n_src,
            "elab_parameters": params["elab_parameters"], "source_head": head,
            "worktree_clean": state["worktree_clean"], "payload_tar_sha256": tar_sha,
            "profile_canonical_sha256": profile_sha,
            "uncommitted_flow_files": [r["path"] for r in records if not r["matches_head"]],
            "remote_steps": [f"mkdir <new remote run root> && tar -xf payload.tar -C <that root> --no-same-owner",
                             f"cd <that root>/{run_name} && bash ./run.sh"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=("probe", "syn"))
    parser.add_argument("--policy", choices=(*POLICIES, "fai-alg2"))
    parser.add_argument("--supplementary-alg2", action="store_true", help="explicit opt-in for supplementary fai-alg2 N4 only")
    parser.add_argument("--n-src", type=int, choices=N_VALUES)
    parser.add_argument("--library", help="absolute .db path on the EDA host (never read locally)")
    parser.add_argument("--profile", type=Path, help="reviewed local profile JSON (syn only)")
    parser.add_argument("--output", type=Path, help="new local run directory (must not exist)")
    parser.add_argument("--print-profile-template", action="store_true",
                        help="print a placeholder profile that is rejected until reviewed values are filled")
    args = parser.parse_args(argv)
    if args.print_profile_template:
        if args.supplementary_alg2:
            parser.error("--supplementary-alg2 requires a fai-alg2 N4 run")
        print(json.dumps(profile_template(), indent=2))
        return 0
    if None in (args.mode, args.policy, args.n_src, args.library, args.output):
        parser.error("--mode, --policy, --n-src, --library and --output are required")
    try:
        summary = prepare(args.mode, args.policy, args.n_src, args.library, args.profile, args.output,
                          supplementary_alg2=args.supplementary_alg2)
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f"prepare_ppa_run: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
