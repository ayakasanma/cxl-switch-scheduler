"""Fail closed on replay totals, SAIF duration/scope and an incomplete PT pilot.

Checks raw evidence only; a successful command audit is not power-method acceptance.
v1 metadata is the accepted cold primary seed-509 contract; v2 adds fixed supplementary modes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

# Fixed supplementary replay modes (v2 header 43585032). Neither replaces the accepted cold
# primary seed-509 v1 dataset. The exporter imports this table; the uploaded checker owns it.
SUPPLEMENTARY_MODES = {
    "cold-seed": dict(mode_id=1, seeds=(510, 511), n_src=(4, 8, 16), warmup=0, measured=100_000),
    "boundary-n4": dict(mode_id=2, seeds=(509,), n_src=(4,), warmup=9_999_500, measured=100_000),
}
FIXTURE_MODE_ID = 9  # local small-window fixtures only; never production evidence
TRAINED_SCHEMA = "cxl-revision-trained-power-v1"
TRAINED_MODES = {
    "trained-hog-A": dict(mode_id=12, arm="A", warmup=10_000_000, measured=100_000),
    "trained-hog-B": dict(mode_id=13, arm="B", warmup=10_101_024, measured=102_400),
}
POLICY_IDS = {"fcfs": 0, "rr": 1, "fai-main": 2}
PERIOD_PS, RESET_EDGES = 25_000, 3


def _check_trained(m, spec):
    expected = dict(arm=spec["arm"], training_cycles=10_000_000, n_src=4,
                    warmup_cycles=spec["warmup"], measured_cycles=spec["measured"],
                    production_evidence=True, sensitivity_only=False, smoke_cycles=None,
                    seed_role="exploration", planned_power_seed=m["seed"] <= 511,
                    replaces_primary_dataset=False, fai_window=5_000_000,
                    status="MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN", exit=0,
                    vectors_rows=m["total_cycles"])
    if m["seed"] not in range(509, 514) or any(
            k not in m or type(m[k]) is not type(v) or m[k] != v for k, v in expected.items()):
        raise ValueError("invalid completed trained W5M export contract")
    for key in ("audit_sha256", "source_archive_sha256", "vectors_text_sha256", "vectors_gzip_sha256"):
        if not isinstance(m.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", m[key]):
            raise ValueError(f"missing/invalid completed export {key}")
    # These are metadata guards; the exporter separately replays and hashes the serialized audit.
    try:
        for phase, cycles in (("warmup", m["warmup_cycles"]), ("measured", m["measured_cycles"])):
            c = m[phase]
            if type(c["cycles"]) is not int or c["cycles"] != cycles:
                raise ValueError("trained phase cycle count differs")
            for key in ("accepted_per_source", "fires_per_source"):
                if (type(c[key]) is not list or len(c[key]) != 4 or
                        any(type(v) is not int or not 0 <= v <= cycles for v in c[key])):
                    raise ValueError("invalid trained phase source counts")
            if sum(c["fires_per_source"]) > cycles:
                raise ValueError("trained phase exceeds single-output capacity")
        w, s = m["warmup"], m["measured"]
        for key, values in (("outstanding_at_cut", [a-f for a, f in zip(w["accepted_per_source"], w["fires_per_source"])]),
                            ("outstanding_at_end", [a+b-f-g for a, b, f, g in zip(
                                w["accepted_per_source"], s["accepted_per_source"],
                                w["fires_per_source"], s["fires_per_source"])])):
            if (type(m[key]) is not list or len(m[key]) != 4 or
                    any(type(v) is not int or not 0 <= v <= 16 for v in m[key]) or m[key] != values):
                raise ValueError("trained source conservation differs")
        for key, value in dict(cycles=m["total_cycles"],
                               accepted=sum(w["accepted_per_source"])+sum(s["accepted_per_source"]),
                               fires=sum(w["fires_per_source"])+sum(s["fires_per_source"])).items():
            if type(m["all"][key]) is not int or m["all"][key] != value:
                raise ValueError("trained all-phase totals differ")
        if m["policy"] == "fai-main":
            closes = m["closings"]
            if type(closes) is not list or len(closes) != 2:
                raise ValueError("trained Main requires exactly two actual closings")
            old = ["H"] * 4
            for c, cycle, classes in zip(closes, (4_999_999, 9_999_999),
                                         (["B_H", "H", "H", "H"], ["L", "H", "H", "H"])):
                required = dict(cycle=cycle, phase="warmup", window_position=4_999_999,
                                old_classes=old, next_cycle_classes=classes, b_s_index_cleared_after=True)
                if any(type(c[k]) is not type(v) or c[k] != v for k, v in required.items()):
                    raise ValueError("invalid trained Main closing trajectory")
                b, pre, total, src = c["b_close"], c["pre_edge_b"], c["s_close"], c["closing_fire_source"]
                if (any(type(v) is not list or len(v) != 4 for v in (b, pre)) or
                        any(type(v) is not int or not 0 <= v <= 5_000_000 for v in b+pre) or
                        type(total) is not int or not 0 <= total <= 5_000_000 or sum(b) != total or
                        type(c["pre_edge_s"]) is not int or sum(pre) != c["pre_edge_s"] or
                        not (src is None or type(src) is int and 0 <= src < 4) or
                        b != [v+int(h == src) for h, v in enumerate(pre)] or
                        total != c["pre_edge_s"]+int(src is not None) or
                        c["evidence"] != ["S0" if total == 0 else "UP" if 40*v < 3*total
                                          else "DOWN" if 4*v > total else "KEEP" for v in b]):
                    raise ValueError("invalid trained Main closing counts/evidence")
                # The two required closes start only in H/B_H (spec8.2), including idle cancellation.
                next_classes = [("B_H" if state == "H" else "L") if ev == "DOWN" else "H"
                                for state, ev in zip(old, c["evidence"])]
                if next_classes != classes:
                    raise ValueError("trained Main evidence does not produce declared next classes")
                old = classes
    except (KeyError, TypeError) as exc:
        raise ValueError("incomplete trained export statistics") from exc


def check_mode(metadata, allow_fixture=False):
    """Reject anything but the fixed supplementary modes (fixtures only when explicitly allowed)."""
    m = metadata
    for key in ("policy_id", "period_ps", "reset_edges_outside_window", "depth", "descriptor_bits",
                "rr_quantum", "total_cycles", "warmup_cycles", "measured_cycles", "duration_ns",
                "mode_id", "seed", "n_src", "fai_window"):
        if type(m.get(key)) is not int:
            raise ValueError(f"{key} must be an integer")
    if m.get("policy") not in POLICY_IDS or m.get("policy_id") != POLICY_IDS[m.get("policy")]:
        raise ValueError("unsupported policy/policy_id")
    if (m.get("period_ps"), m.get("reset_edges_outside_window")) != (PERIOD_PS, RESET_EDGES):
        raise ValueError("unsupported clock period or reset edges")
    if (m.get("depth"), m.get("descriptor_bits"), m.get("rr_quantum")) != (16, 105, 10):
        raise ValueError("unsupported FIFO/descriptor/quantum configuration")
    if m.get("total_cycles") != m.get("warmup_cycles", -1) + m.get("measured_cycles", -1):
        raise ValueError("total cycles must equal warmup plus measured cycles")
    if m.get("duration_ns") != m["measured_cycles"] * PERIOD_PS // 1000:
        raise ValueError("activity duration must cover the measured cycles only")
    if m.get("schema") == "cxl-power-replay-v2-fixture":
        if not allow_fixture:
            raise ValueError("fixture vectors are local test fixtures, not power evidence")
        if (m.get("mode"), m.get("mode_id"), m.get("production_evidence")) != ("fixture", FIXTURE_MODE_ID, False) \
                or m.get("fai_window") != 256 or not 0 < m["measured_cycles"] <= 100_000 \
                or not 0 <= m["warmup_cycles"] <= 100_000 or m.get("n_src") not in (4, 8, 16):
            raise ValueError("invalid fixture configuration")
        return
    trained = TRAINED_MODES.get(m.get("mode"))
    if (m.get("schema") == TRAINED_SCHEMA and trained is not None and
            m["mode_id"] == trained["mode_id"] and m["fai_window"] == 5_000_000):
        _check_trained(m, trained)
        return
    spec = SUPPLEMENTARY_MODES.get(m.get("mode"))
    if m.get("schema") != "cxl-power-replay-v2" or spec is None or m.get("mode_id") != spec["mode_id"]:
        raise ValueError("unsupported supplementary power mode")
    if (m.get("seed") not in spec["seeds"] or m.get("n_src") not in spec["n_src"] or
            (m["warmup_cycles"], m["measured_cycles"]) != (spec["warmup"], spec["measured"])):
        raise ValueError(f"{m['mode']} mode allows only its fixed seeds/N/warmup/measured cycles")
    if m.get("fai_window") != 5_000_000 or m.get("replaces_primary_dataset") is not False:
        raise ValueError("supplementary mode must keep W=5000000 and the primary dataset")


def check_payload_mode(metadata, n, policy):
    """Production runner guard; fixture allowance deliberately unavailable here."""
    m = metadata
    if m.get("schema") == "cxl-power-replay-v1":
        if m.get("mode") in TRAINED_MODES or m.get("mode_id") in (12, 13):
            raise ValueError("trained mode cannot use the legacy schema")
        if (m.get("seed"), m.get("measured_cycles"), m.get("period_ps"), m.get("duration_ns"),
                m.get("reset_edges_outside_window"), m.get("depth"), m.get("descriptor_bits"),
                m.get("rr_quantum"), m.get("fai_window")) != (509, 100_000, 25_000, 2_500_000, 3, 16, 105, 10, 5_000_000):
            raise ValueError("unsupported legacy primary payload")
    else:
        check_mode(m)
    if (n not in (4, 8, 16) or policy not in POLICY_IDS or
            (m.get("n_src"), m.get("policy"), m.get("policy_id")) != (n, policy, POLICY_IDS[policy])):
        raise ValueError("payload policy/N does not match requested mapped case")


def expected_result_v2(metadata):
    """Exact gate-replay result lines owed for a v2 run (warmup and measured kept separate)."""
    m, n = metadata, metadata["n_src"]
    w, s = m["warmup"], m["measured"]
    lines = [f"GATE_REPLAY_V2_COMPLETE mode={m['mode_id']} n={n} policy={m['policy_id']} seed={m['seed']} "
             f"total_cycles={m['total_cycles']} warmup_cycles={m['warmup_cycles']} "
             f"measured_cycles={m['measured_cycles']} duration_ns={m['duration_ns']}"]
    for name, phase in (("warmup", w), ("measured", s)):
        lines.append(f"phase={name} accepted={sum(phase['accepted_per_source'])} "
                     f"fires={sum(phase['fires_per_source'])}")
    lines.append(f"phase=all accepted={m['all']['accepted']} fires={m['all']['fires']}")
    for h in range(n):
        lines.append(f"source={h} warmup_accepted={w['accepted_per_source'][h]} "
                     f"warmup_fires={w['fires_per_source'][h]} measured_accepted={s['accepted_per_source'][h]} "
                     f"measured_fires={s['fires_per_source'][h]} outstanding_at_cut={m['outstanding_at_cut'][h]} "
                     f"outstanding_at_end={m['outstanding_at_end'][h]}")
    return lines


def check_replay_result(metadata, result, allow_fixture=False):
    """Gate-replay totals only (also used by local Verilator replays that collect no SAIF)."""
    if metadata.get("schema", "cxl-power-replay-v1") == "cxl-power-replay-v1":
        if metadata.get("mode") in TRAINED_MODES or metadata.get("mode_id") in (12, 13):
            raise ValueError("trained mode cannot use the legacy schema")
        _check_result_v1(metadata, result)
        return
    check_mode(metadata, allow_fixture)
    lines, expected = Path(result).read_text().splitlines(), expected_result_v2(metadata)
    if len(lines) != len(expected):
        raise ValueError("gate replay result has missing/extra lines")
    for actual, owed in zip(lines, expected):
        if actual != owed:
            raise ValueError(f"gate replay result differs from model: {actual!r} != {owed!r}")


def check_replay(metadata, result, saif, allow_fixture=False):
    check_replay_result(metadata, result, allow_fixture)
    if metadata.get("schema", "cxl-power-replay-v1") == "cxl-power-replay-v1":
        return _check_saif_v1(metadata, saif)
    activity = Path(saif).read_text()
    timescale = re.search(r"\(TIMESCALE\s+([\d.eE+-]+)\s+(ps|ns|us|ms|s)\s*\)", activity)
    duration = re.search(r"\(DURATION\s+([\d.eE+-]+)\s*\)", activity)
    if not timescale or not duration:
        raise ValueError("SAIF time units or duration missing")
    ns = float(timescale[1]) * float(duration[1]) * {"ps": .001, "ns": 1, "us": 1000,
                                                              "ms": 1e6, "s": 1e9}[timescale[2]]
    if ns != metadata["duration_ns"]:
        raise ValueError("SAIF activity duration differs from the measured window")
    if not re.search(r"\(INSTANCE\s+tb\s+\(INSTANCE\s+dut\b", activity):
        raise ValueError("SAIF does not contain expected tb/dut scope")
    block = re.search(r"\(clk\s+((?:\(\w+\s+\d+\)\s*)+)\)", activity)
    if not block:
        raise ValueError("SAIF dut clock record missing")
    fields = {key: int(value) for key, value in re.findall(r"\((\w+)\s+(\d+)\)", block[1])}
    edges = 2 * metadata["measured_cycles"]
    # Observed VCS endpoints drop one boundary transition (TC 2M-1); the ideal is 2M.
    if (fields.get("TX") != 0 or fields.get("TZ", 0) != 0 or fields.get("T0", -1) + fields.get("T1", -1) != float(duration[1])
            or fields.get("TC") not in (edges - 1, edges)):
        raise ValueError(f"SAIF dut clock record is unknown/incomplete: {fields}")
    return {"status": "REPLAY_TOTALS_AND_SAIF_WINDOW_CHECKED", "schema": metadata["schema"],
            "mode": metadata["mode"], "duration_ns": ns, "clock_fields": fields,
            "saif_sha256": hashlib.sha256(Path(saif).read_bytes()).hexdigest(),
            "annotation_and_clock_pin_semantic_review": "REQUIRED_IN_PT_REPORTS"}


def _check_result_v1(metadata, result):
    text = Path(result).read_text()
    if not text.splitlines():
        raise ValueError("empty gate replay result")
    header = re.fullmatch(r"GATE_REPLAY_COMPLETE cycles=(\d+) n=(\d+) policy=(\d+) seed=(\d+) "
                          r"duration_ns=(\d+) accepted=(\d+) fires=(\d+)", text.splitlines()[0])
    expected = [metadata[k] for k in ("measured_cycles", "n_src", "policy_id", "seed",
                                     "duration_ns", "accepted", "fires")]
    if not header or list(map(int, header.groups())) != expected:
        raise ValueError("gate replay header/totals differ from model metadata")
    lines = text.splitlines()[1:]
    if len(lines) != metadata["n_src"]:
        raise ValueError("wrong number of per-source gate results")
    for h, line in enumerate(lines):
        expected_line = (f"source={h} accepted={metadata['accepted_per_source'][h]} "
                         f"fires={metadata['fires_per_source'][h]} "
                         f"outstanding={metadata['outstanding_at_cut'][h]}")
        if line != expected_line:
            raise ValueError(f"gate source {h} results differ from model")


def _check_saif_v1(metadata, saif):
    activity = Path(saif).read_text()
    timescale = re.search(r"\(TIMESCALE\s+([\d.eE+-]+)\s+(ps|ns|us|ms|s)\s*\)", activity)
    duration = re.search(r"\(DURATION\s+([\d.eE+-]+)\s*\)", activity)
    if not timescale or not duration:
        raise ValueError("SAIF time units or duration missing")
    ns = float(timescale[1]) * float(duration[1]) * {"ps": .001, "ns": 1, "us": 1000,
                                                              "ms": 1e6, "s": 1e9}[timescale[2]]
    if ns != metadata["duration_ns"]:
        raise ValueError("SAIF activity duration differs from measured window")
    if not re.search(r"\(INSTANCE\s+tb\s+\(INSTANCE\s+dut\b", activity):
        raise ValueError("SAIF does not contain expected tb/dut scope")
    clock = re.search(r"\(clk\s+\(T0\s+(\d+)\)\s+\(T1\s+(\d+)\)\s+\(TX\s+(\d+)\)"
                      r"\s+\(TC\s+(\d+)\)", activity)
    # SAIF field order is simulator dependent; preserve this as reviewed raw evidence if absent.
    return {"status": "REPLAY_TOTALS_AND_SAIF_WINDOW_CHECKED", "duration_ns": ns,
            "saif_sha256": hashlib.sha256(Path(saif).read_bytes()).hexdigest(),
            "clock_record_in_common_field_order": clock.group(0) if clock else None,
            "annotation_and_clock_pin_semantic_review": "REQUIRED_IN_PT_REPORTS"}


def check_power_report(text):
    """Classify observed W-2024.09 check_power output without declaring warning cases clean."""
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    detail_pattern = (rf"(ramp|load) ({number}) at pin '([^']+)' of cell '([^']+)' is out of "
                      rf"(ramp|load) range \(({number}), ({number})\) of lib_cell '([^']+)'")
    checks, results, details, warnings = set(), [], [], {}
    succeeded = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        check = re.fullmatch(r"Information: Checking '(out_of_table_range|missing_table|missing_function)'\.", line)
        detail = re.fullmatch(detail_pattern, line)
        warning = re.fullmatch(r"Warning: There are (\d+) out_of_range (ramps|loads)\.", line)
        if check:
            checks.add(check[1])
        elif detail:
            kind, value, pin, cell, range_kind, minimum, maximum, lib_cell = detail.groups()
            if kind != range_kind:
                raise ValueError("inconsistent check_power range diagnostic")
            details.append(dict(kind=kind, value=value, pin=pin, cell=cell,
                                minimum=minimum, maximum=maximum, lib_cell=lib_cell, raw=line))
        elif warning:
            kind = warning[2][:-1]
            if kind in warnings:
                raise ValueError("duplicate check_power warning summary")
            warnings[kind] = int(warning[1])
        elif line == "check_power succeeded.":
            succeeded = True
        elif line in ("0", "1"):
            results.append(int(line))
        else:
            raise ValueError(f"unsupported check_power diagnostic: {line}")
    if len(results) != 1:
        raise ValueError("check_power numeric result missing or ambiguous")
    if checks != {"out_of_table_range", "missing_table", "missing_function"}:
        raise ValueError("check_power did not run all calibrated default checks")
    if results[0] == 1 and succeeded and not details and not warnings:
        return {"tool_result": 1, "quality_status": "NO_CHECK_POWER_ISSUES_REPORTED",
                "range_issue_counts": {"ramp": 0, "load": 0}, "range_issues": []}
    counts = {kind: sum(d["kind"] == kind for d in details) for kind in ("ramp", "load")}
    if (results[0] != 0 or succeeded or not details or not warnings or
            any(warnings.get(kind, 0) != count for kind, count in counts.items())):
        raise ValueError("check_power failed without a complete, consistent table-range-only diagnosis")
    return {"tool_result": 0, "quality_status": "QUALIFIED_TABLE_RANGE_WARNINGS_REVIEW_REQUIRED",
            "range_issue_counts": counts, "range_issues": details,
            "note": "check_power did not succeed; table-domain issues remain in the estimate and require review"}


def check_pt(report_dir):
    reports = Path(report_dir)
    for name in ("design.rpt", "library.rpt", "clocks.rpt", "units.rpt", "saif-read.rpt",
                 "check-power.rpt", "update-power.rpt", "disable-timing.rpt", "switching-coverage.rpt", "not-annotated.rpt",
                 "annotated.rpt", "power.rpt", "power-hierarchy.rpt", "registers-and-clock-pins.rpt",
                 "pilot-status.rpt", "pt.log"):
        path = reports / name
        if not path.is_file() or not path.read_text().strip():
            raise ValueError(f"missing/empty {name}")
        if re.search(r"^\s*(?:Error|Fatal)\s*:|^POWER_PILOT_ERROR:|^.*license.*(?:fail|denied)",
                     path.read_text(), re.MULTILINE | re.IGNORECASE):
            raise ValueError(f"tool error in {name}")
    power_check = check_power_report((reports / "check-power.rpt").read_text())
    saif = (reports / "saif-read.rpt").read_text()
    keys = ("Total number of nets", "Number of annotated nets", "Total number of leaf cells",
            "Number of fully annotated leaf cells")
    counts = {}
    for key in keys:
        match = re.search(re.escape(key) + r"\s*=\s*(\d+)", saif)
        if not match:
            raise ValueError(f"SAIF summary missing {key}")
        counts[key] = int(match[1])
    if not counts[keys[0]] or not counts[keys[1]]:
        raise ValueError("SAIF annotated no design nets")
    power = (reports / "power.rpt").read_text()
    if not re.search(r"Total\s+(?:Power|power)|Total\s*=", power):
        raise ValueError("power report has no total")
    status = ("POWER_PILOT_COMMAND_EVIDENCE_CHECKED_SEMANTIC_REVIEW_REQUIRED" if power_check["tool_result"] == 1
              else "POWER_PILOT_COMMAND_EVIDENCE_CHECKED_WITH_TABLE_RANGE_WARNINGS")
    return {"status": status, "check_power": power_check, "method_acceptance": "NOT_GRANTED_BY_THIS_AUDIT",
            "saif_annotation_counts": counts,
            "note": "switching-coverage is toggled nets; review source tables, all FF clocks, units and warnings"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--saif", type=Path, required=True)
    parser.add_argument("--pt-reports", type=Path)
    args = parser.parse_args()
    summary = check_replay(json.loads(args.metadata.read_text()), args.result, args.saif)
    if args.pt_reports:
        summary["pt"] = check_pt(args.pt_reports)
    print(json.dumps(summary, indent=2, sort_keys=True))
