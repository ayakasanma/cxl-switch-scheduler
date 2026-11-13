"""CGOF-only payload/replay/SAIF/PT checks; semantic power acceptance remains manual."""
from __future__ import annotations

import argparse
import datetime as dt
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path
import re
import socket
import zipfile

import export_cgof_power_vectors as cgof
from check_power_replay import check_pt, expected_result_v2

CELL_MODEL_SHA = "d4bf5a3e6279b7ef9814a5ddf68028bcb0f7cf61233f03c8dab8c8cd5381b286"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
require = cgof.require
sha = cgof.sha


def check_metadata(metadata, weight, allow_fixture=False):
    cgof.check_contract(metadata)
    require(type(weight) is int and weight in (1, 2) and metadata["high_weight"] == weight,
            "payload weight differs from requested mapped case")
    require(allow_fixture or metadata["production_evidence"] is True,
            "fixture vectors are not production power evidence")
    require(metadata.get("status") == "MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN"
            and type(metadata.get("exit")) is int and metadata["exit"] == 0
            and type(metadata.get("vectors_rows")) is int
            and metadata["vectors_rows"] == metadata["total_cycles"],
            "CGOF export is incomplete")
    for key in ("audit_sha256", "source_archive_sha256", "vectors_text_sha256", "vectors_gzip_sha256"):
        require(isinstance(metadata.get(key), str) and re.fullmatch(r"[a-f0-9]{64}", metadata[key]),
                f"invalid completed export {key}")
    require(metadata.get("profile_canonical_sha256") == cgof.trained.legacy.PROFILE_SHA
            and metadata.get("library_sha256") == cgof.DB_SHA
            and metadata.get("baseline_index_sha256") == cgof.inventory.BASELINE_SHA,
            "profile/library/baseline differs")
    for phase in ("warmup", "measured"):
        stats = metadata[phase]
        cycles = metadata[f"{phase}_cycles"]
        require(type(stats["cycles"]) is int and stats["cycles"] == cycles, "phase cycles differ")
        for key in ("accepted_per_source", "fires_per_source"):
            require(type(stats[key]) is list and len(stats[key]) == 4
                    and all(type(value) is int and 0 <= value <= cycles for value in stats[key]),
                    "invalid phase source counts")
        require(sum(stats["fires_per_source"]) <= cycles, "single-output capacity exceeded")
    warmup, measured = metadata["warmup"], metadata["measured"]
    cut = [accepted-fired for accepted, fired in zip(warmup["accepted_per_source"], warmup["fires_per_source"])]
    end = [prior+accepted-fired for prior, accepted, fired in
           zip(cut, measured["accepted_per_source"], measured["fires_per_source"])]
    require(all(type(metadata[key]) is list and len(metadata[key]) == 4
                and all(type(value) is int for value in metadata[key])
                for key in ("outstanding_at_cut", "outstanding_at_end"))
            and metadata["outstanding_at_cut"] == cut and metadata["outstanding_at_end"] == end
            and all(type(value) is int and 0 <= value <= 16 for value in cut+end),
            "source conservation differs")
    expected = dict(cycles=metadata["total_cycles"],
                    accepted=sum(warmup["accepted_per_source"])+sum(measured["accepted_per_source"]),
                    fires=sum(warmup["fires_per_source"])+sum(measured["fires_per_source"]))
    require(all(type(metadata["all"].get(key)) is int and metadata["all"][key] == value
                for key, value in expected.items()), "all-phase totals differ")
    if metadata["production_evidence"]:
        closings = metadata.get("closings")
        require(type(closings) is list and len(closings) == 2, "two production training closings required")
        old = ["H"]*4
        for closing, cycle, classes in zip(closings, (4_999_999, 9_999_999),
                (["B_H", "H", "H", "H"], ["L", "H", "H", "H"])):
            fixed = dict(cycle=cycle, phase="warmup", window_position=4_999_999,
                         old_classes=old, next_cycle_classes=classes, b_s_index_cleared_after=True)
            require(all(type(closing.get(key)) is type(value) and closing[key] == value
                        for key, value in fixed.items()), "training class trajectory differs")
            counts, previous = closing["b_close"], closing["pre_edge_b"]
            require(all(type(values) is list and len(values) == 4 and
                        all(type(value) is int and 0 <= value <= 5_000_000 for value in values)
                        for values in (counts, previous)), "invalid closing counts")
            source = closing["closing_fire_source"]
            require(source is None or type(source) is int and 0 <= source < 4, "invalid closing source")
            total, pre_total = closing["s_close"], closing["pre_edge_s"]
            require(type(total) is type(pre_total) is int and 0 < total <= 5_000_000
                    and sum(counts) == total and sum(previous) == pre_total
                    and counts == [value+int(index == source) for index, value in enumerate(previous)]
                    and total == pre_total+int(source is not None), "closing fire/conservation differs")
            evidence = ["UP" if 40*value < 3*total else "DOWN" if 4*value > total else "KEEP" for value in counts]
            require(closing["evidence"] == evidence and
                    [("B_H" if state == "H" else "L") if item == "DOWN" else "H"
                     for state, item in zip(old, evidence)] == classes, "closing evidence differs")
            old = classes


def check_compute(path, hostname=None, now=None):
    cgof.inventory.no_links(Path(path))
    approval = json.loads(Path(path).read_text())
    hostname = hostname or socket.getfqdn()
    now = now or dt.datetime.now(dt.timezone.utc)
    require(approval.get("schema") == "cxl-fastx-compute-approval-v1"
            and approval.get("approved_for_long_eda") is True
            and approval.get("hostname") == hostname,
            "approved compute receipt missing or hostname differs")
    require(all(isinstance(approval.get(key), str) and approval[key].strip()
                for key in ("authority", "evidence", "launch_command", "valid_until_utc")),
            "compute receipt needs authority, evidence, launch command and expiry")
    expires = dt.datetime.fromisoformat(approval["valid_until_utc"].replace("Z", "+00:00"))
    require(expires.tzinfo is not None and expires > now, "compute approval expired or timezone missing")
    return approval


def check_payload(root, case_root, weight, cell_model, database, compute_approval, destination):
    check_compute(compute_approval)
    cgof.inventory.no_links(Path(root))
    cgof.inventory.no_links(Path(case_root))
    root, case_root = Path(root).resolve(), Path(case_root).resolve()
    metadata = json.loads(cgof.inventory.repo_file(root, "metadata.json").read_text())
    check_metadata(metadata, weight)
    require(cgof.sources() == metadata["source_sha256"], "payload source inventory differs")
    required = {"scripts/check_cgof_power_replay.py", "scripts/run_cgof_power_pilot.sh",
                "sim/power/tb_power.sv", "sta/power_pt.tcl"}
    require(required.issubset(metadata["source_sha256"]), "runtime sources are not frozen")
    bindings = {str(cgof.inventory.repo_file(root, name)): digest
                for name, digest in metadata["source_sha256"].items()}
    mapping = metadata["mapping"]["files"]
    require(set(mapping) == set(cgof.MAPPED_FILES) and
            tuple(mapping[name] for name in cgof.MAPPED_FILES[4:6]) == cgof.MAPPING_PINS[weight],
            "mapped input pins differ")
    bindings.update({str(cgof.inventory.repo_file(case_root, name)): digest for name, digest in mapping.items()})
    for name, key in (("audit.json", "audit_sha256"), ("vectors.txt.gz", "vectors_gzip_sha256"),
                      ("source-freeze.zip", "source_archive_sha256")):
        bindings[str(cgof.inventory.repo_file(root, name))] = metadata[key]
    for path, digest in bindings.items():
        require(sha(Path(path)) == digest, f"input hash differs: {path}")
    audit = json.loads((root / "audit.json").read_text())
    require(audit.get("status") == "MODEL_AND_INDEPENDENT_CREDIT_LEDGER_CHECKED_NOT_RTL_OR_POWER"
            and type(audit.get("rows")) is int and audit["rows"] == metadata["total_cycles"]
            and audit.get("power_status") == "NOT_RUN", "serialized audit receipt differs")
    require(sha(cell_model) == CELL_MODEL_SHA and sha(database) == cgof.DB_SHA, "library/model hash differs")
    archive_files = dict(metadata["source_sha256"])
    archive_files.update({f"mapped/{name}": digest for name, digest in mapping.items()})
    archive_files["baseline-acceptance.json"] = cgof.inventory.BASELINE_SHA
    require(metadata["archive_files"] == archive_files, "archive bindings differ")
    with zipfile.ZipFile(root / "source-freeze.zip") as archive:
        require(len(archive.namelist()) == len(archive_files)
                and set(archive.namelist()) == set(archive_files), "archive entries differ")
        for name, digest in archive_files.items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == digest, f"archive entry differs: {name}")
    require(metadata["trace"]["sha256"] == cgof.TRACE_PINS[f"{metadata['seed']}-{metadata['arm']}"],
            "matched production trace differs")
    digest = hashlib.sha256()
    with gzip.open(root / "vectors.txt.gz", "rb") as source, Path(destination).open("xb") as target:
        header = source.readline()
        require(header == (cgof.trained.header(metadata)+"\n").encode("ascii"), "vector header differs")
        digest.update(header)
        target.write(header)
        for block in iter(lambda: source.read(1024*1024), b""):
            digest.update(block)
            target.write(block)
    require(digest.hexdigest() == metadata["vectors_text_sha256"], "uncompressed vector hash differs")
    for path in (cell_model, database, compute_approval, root / "metadata.json", Path(destination)):
        cgof.inventory.no_links(Path(path))
        bindings[str(Path(path).resolve())] = sha(path)
    return dict(status="PAYLOAD_INPUTS_CHECKED_NOT_EDA_OR_POWER", file_sha256=bindings,
                compute=check_compute(compute_approval), power_status="NOT_RUN")


def saif_records(text, duration):
    stack, records, roots = [], {}, []
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    for token in re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text):
        if token == "(":
            stack.append(dict(head=None, args=[], fields={}))
        elif token == ")":
            require(bool(stack), "SAIF unbalanced close")
            frame = stack.pop()
            head = frame["head"]
            if head in ("T0", "T1", "TX", "TZ", "TC", "IG") and not frame["fields"]:
                require(len(frame["args"]) == 1 and bool(stack) and head not in stack[-1]["fields"],
                        "invalid/duplicate SAIF field")
                try:
                    value = Decimal(frame["args"][0])
                except InvalidOperation as exc:
                    raise ValueError("nonnumeric SAIF field") from exc
                require(value.is_finite() and value >= 0 and value == value.to_integral_value(),
                        "invalid SAIF numeric value")
                stack[-1]["fields"][head] = value
            elif frame["fields"]:
                fields = frame["fields"]
                require({"T0", "T1", "TX", "TC"}.issubset(fields), "SAIF signal fields missing")
                path = "/".join([entry["args"][0] for entry in stack if entry["head"] == "INSTANCE"]
                                + [head]).replace("\\", "")
                require(path.startswith("tb/dut/") and path[7:] not in records, "SAIF scope/duplicate path")
                require(sum(fields.get(key, 0) for key in ("T0", "T1", "TX", "TZ")) == duration,
                        "SAIF residency differs")
                require(fields["TX"] in (0, duration) and fields.get("TZ", 0) == 0,
                        "transient X or Z activity")
                records[path[7:]] = fields
            if not stack:
                roots.append(head)
        else:
            require(bool(stack), "SAIF token outside root")
            if stack[-1]["head"] is None:
                stack[-1]["head"] = token
            else:
                stack[-1]["args"].append(token)
    require(not stack and roots == ["SAIFILE"] and bool(records), "SAIF empty/unbalanced root")
    return records


def check_replay(metadata, result, saif, allow_fixture=False):
    check_metadata(metadata, metadata["high_weight"], allow_fixture)
    require(Path(result).read_text().splitlines() == expected_result_v2(metadata), "gate replay totals differ")
    activity = Path(saif).read_text()
    scales = re.findall(r"\(TIMESCALE\s+("+NUMBER+r")\s+(ps|ns|us|ms|s)\s*\)", activity)
    durations = re.findall(r"\(DURATION\s+("+NUMBER+r")\s*\)", activity)
    require(len(scales) == len(durations) == 1, "SAIF time units/duration missing or ambiguous")
    scale, unit = scales[0]
    duration = Decimal(durations[0])
    ns = Decimal(scale)*duration*dict(ps=Decimal(".001"), ns=1, us=1000, ms=1000000, s=1000000000)[unit]
    require(duration.is_finite() and duration > 0 and ns == metadata["duration_ns"], "SAIF measured duration differs")
    records = saif_records(activity, duration)
    clock = records.get("clk")
    edges = 2*metadata["measured_cycles"]
    require(clock is not None and clock["TX"] == clock.get("TZ", 0) == 0
            and clock["T0"]+clock["T1"] == duration and clock["TC"] in (edges-1, edges),
            "SAIF DUT clock unknown/incomplete")
    unknown = sorted(path for path, fields in records.items() if fields["TX"] == duration)
    return dict(status="CGOF_REPLAY_AND_ALL_SAIF_RECORDS_CHECKED_SEMANTIC_REVIEW_REQUIRED",
                duration_ns=str(ns), saif_duration_ticks=str(duration), saif_sha256=sha(saif),
                clock_fields={key: str(value) for key, value in clock.items()}, signal_records=len(records),
                always_x_count=len(unknown), always_x_paths=unknown, transient_x_or_z=0,
                method_acceptance="NOT_GRANTED_BY_THIS_AUDIT")


def check_power(reports, metadata, replay):
    reports = Path(reports)
    result = check_pt(reports)
    check_tool_logs(reports, ("compile", "sim", "pt"))
    read = lambda name: (reports / name).read_text()
    power = read("power.rpt")
    for text in ("Dynamic Power Units = 1 W", "Leakage Power Units = 1 W", "Time Units = 1 ns",
                 "tt0p78v25c", "ForQA", "Wire Load Model Mode: top"):
        require(text in power, f"power units/profile missing: {text}")
    require(re.search(r"Time_unit\s*:\s*1e-09 Second", read("units.rpt"))
            and re.search(r"core_clk\s+25.00\s+\{0 12.5\}.*\{clk\}", read("clocks.rpt")), "PT clock/time units differ")
    require("profile="+metadata["profile_canonical_sha256"] in read("library.rpt"), "PT profile differs")
    labels = ("Cell Internal Power", "Net Switching Power", "Cell Leakage Power", "Total Power")
    values = []
    for label in labels:
        found = re.findall(re.escape(label)+r"\s*=\s*("+NUMBER+r")", power)
        require(len(found) == 1, f"power component missing/ambiguous: {label}")
        value = Decimal(found[0])
        require(value.is_finite() and value >= 0, "invalid power component")
        values.append(value)
    rounding = lambda value: Decimal(5).scaleb(value.as_tuple().exponent-1)
    require(abs(sum(values[:3])-values[3]) <= sum(rounding(value) for value in values), "power total inconsistent")
    roots = re.findall(r"^cgof_unit_top\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")",
                       read("power-hierarchy.rpt"), re.M)
    require(len(roots) == 1, "CGOF hierarchy root missing/ambiguous")
    require(all(abs(original-printed) <= rounding(original)+rounding(printed)
                for original, printed in zip(values, map(Decimal, roots[0]))), "hierarchy power inconsistent")
    text = read("registers-and-clock-pins.rpt")
    count = re.findall(r"^register_count=(\d+)$", text, re.M)
    rows = re.findall(r'^clock_pin=(.*?) nets=(.*?) activity=\s*\{"(.*?)" ('+NUMBER+r') (\w+)\}', text, re.M)
    require(len(count) == 1 and int(count[0]) > 0
            and len(rows) == len({row[0] for row in rows}) == int(count[0])
            and len(re.findall(r"^clock_pin=", text, re.M)) == len(rows), "FF clock inventory incomplete")
    rate = Decimal(format(Decimal(replay["clock_fields"]["TC"])/Decimal(replay["duration_ns"]), ".6g"))
    require(all(pin == echoed and (net == "clk" or net.endswith("/clk")) and source == "file"
                and Decimal(value) == rate for pin, net, echoed, value, source in rows), "FF clock source/rate differs")
    counts = result["saif_annotation_counts"]
    require(0 < counts["Number of annotated nets"] <= counts["Total number of nets"]
            and 0 <= counts["Number of fully annotated leaf cells"] <= counts["Total number of leaf cells"],
            "invalid annotation coverage counts")
    result.update(status="CGOF_PILOT_COMMAND_EVIDENCE_CHECKED_SEMANTIC_REVIEW_REQUIRED",
                  power_W=dict(zip(("internal", "switching", "leakage", "total"), map(str, values))),
                  units="W", ff_clock_pins=len(rows), calibrated_clock_rate=str(rate),
                  report_sha256={path.name: sha(path) for path in sorted(reports.glob("*.rpt"))},
                  annotation_source_tables={name: read(name) for name in ("not-annotated.rpt", "switching-coverage.rpt")},
                  disabled_arcs_report="disable-timing.rpt; retained for semantic review",
                  pt_warnings=[line for line in read("pt.log").splitlines() if line.startswith("Warning:")])
    return result


def check_tool_logs(reports, stages):
    bindings = {}
    for stage in stages:
        require(stage in ("compile", "sim", "pt"), "unknown EDA log stage")
        path = Path(reports) / f"{stage}.log"
        text = path.read_text()
        require(bool(text.strip()) and not re.search(
            r"^\s*(?:Error(?:-\[[^]]+\]|:)|Fatal:)|^POWER_PILOT_ERROR:|^EDA_FAILURE:|licen[cs]e[^\n]*(?:fail|denied|unavailable)",
            text, re.M | re.I), f"tool error/empty {stage}.log")
        bindings[path.name] = sha(path)
    return dict(status="TOOL_LOGS_CHECKED_NOT_METHOD_ACCEPTANCE", sha256=bindings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    payload = modes.add_parser("payload")
    for name in ("root", "case-root", "cell-model", "database", "compute-approval", "destination"):
        payload.add_argument("--"+name, type=Path, required=True)
    payload.add_argument("--weight", type=int, choices=(1, 2), required=True)
    replay = modes.add_parser("replay")
    for name in ("metadata", "result", "saif"):
        replay.add_argument("--"+name, type=Path, required=True)
    replay.add_argument("--pt-reports", type=Path)
    logs = modes.add_parser("logs")
    logs.add_argument("--reports", type=Path, required=True)
    logs.add_argument("--stage", choices=("compile", "sim", "pt"), required=True)
    args = parser.parse_args()
    if args.mode == "payload":
        result = check_payload(args.root, args.case_root, args.weight, args.cell_model,
                               args.database, args.compute_approval, args.destination)
    elif args.mode == "logs":
        result = check_tool_logs(args.reports, (args.stage,))
    else:
        metadata = json.loads(args.metadata.read_text())
        result = check_replay(metadata, args.result, args.saif)
        if args.pt_reports:
            result["pt"] = check_power(args.pt_reports, metadata, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
