#!/usr/bin/env python3
"""MODEL_ONLY replay of CGOF credit size, refill, hold and re-entry.

This is a mechanism trace, not RTL, CXL, memory-bandwidth or application evidence.
It replays identical arrivals and ready cycles with all sources fixed High, changing
only the absolute High credit from 1 to 2.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "refc"))

from cxl_model.experimental import ExperimentalSwitchModel  # noqa: E402


TRACE_FIELDS = ("credits", "eligible", "refill", "held", "reentry", "high_weight")
TRACE_SCHEMA = "cxl-credit-refill-trace-v2"
DEFAULT_STALLS = (5, 11)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def inspect_existing_trace(path):
    """Inspect one record without treating a single-policy trace as paired evidence."""
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    missing = set()
    record_count = 0
    invalid_records = []
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_records.append({"line": line_number, "error": str(exc)})
                continue
            if not isinstance(record, dict):
                invalid_records.append({"line": line_number, "error": "record is not an object"})
                continue
            record_count += 1
            missing.update(field for field in TRACE_FIELDS if field not in record)
    return {
        "schema": TRACE_SCHEMA,
        "path": str(path),
        "record_count": record_count,
        "invalid_records": invalid_records,
        "required_fields": list(TRACE_FIELDS),
        "missing": sorted(missing),
        "sufficient_for_budget_attribution": record_count > 0 and not missing and not invalid_records,
        "note": (
            "Existing trace lacks the paired credit/eligible/refill state; using the "
            "deterministic short replay below."
            if missing or not record_count or invalid_records else
            "Schema is sufficient for state inspection; this tool still uses paired replay "
            "because one trace cannot establish a 1:1 versus 2:1 counterfactual."
        ),
    }


def scenario(sparse_start, horizon=18, stalls=DEFAULT_STALLS):
    """Two-request Sparse burst against continuous background source 1."""
    if sparse_start < 0 or sparse_start + 1 >= horizon:
        raise ValueError("Sparse burst must fit inside the fixed active horizon")
    if any(k < 0 or k >= horizon for k in stalls):
        raise ValueError("stall cycles must lie inside the fixed active horizon")
    events = []
    for k in range(horizon):
        row = [1]  # fixed background pressure makes refill boundaries independent of Sparse
        if k in (sparse_start, sparse_start + 1):
            row.insert(0, 0)
        events.append(tuple(row))
    ready = tuple(0 if k in stalls else 1 for k in range(horizon))
    return tuple(events), ready


def _head_rows(view):
    return [
        {
            "source": source,
            "desc": desc,
            "generation_cycle": desc >> 4,
        }
        for source, desc in enumerate(view.head_desc)
        if desc is not None
    ]


def replay(high_weight, events, ready, max_drain=256):
    model = ExperimentalSwitchModel(
        n_src=4,
        policy="CGOF",
        window=64,
        high_weight=high_weight,
    )
    model.commit(rst_n=False)
    accepted = {}
    fired = {}
    rows = []
    previous_active = []
    drain_cycles = 0
    held_grant = None

    for k in range(len(events) + max_drain):
        draining = k >= len(events)
        if draining and not any(model.occupancy(h) for h in range(4)) and model.ctrl.held is None:
            drain_cycles = k - len(events)
            break
        arrivals = () if draining else events[k]
        out_ready = 1 if draining else ready[k]
        valid = [h in arrivals for h in range(4)]
        desc = [(k << 4) | h if valid[h] else 0 for h in range(4)]

        view = model.view(bool(out_ready))
        choice = model.choice()
        active = [h for h in range(4) if view.head_valid[h]]
        credits_before = list(model.credits)
        candidate_refill = bool(active) and not any(credits_before[h] > 0 for h in active)
        candidate_snapshot = (
            [high_weight if model.classes()[h] in ("H", "B_H") else 1
             for h in range(4)]
            if candidate_refill else list(credits_before)
        )
        reentry = [h for h in active if h not in previous_active]
        held_before = model.ctrl.held
        if held_before is not None and held_grant is None:
            raise AssertionError("held RTL/model grant lacks its diagnostic offer")
        if held_before is None:
            offered = (
                None if choice is None else
                {
                    "source": choice.source,
                    "refill": candidate_refill,
                    "snapshot": list(choice.credits),
                    "origin_cycle": k,
                    "state": "fresh",
                }
            )
        else:
            offered = dict(held_grant)
            offered["state"] = "held"
        eligible = (
            [h for h in active if offered is not None and offered["snapshot"][h] > 0]
            if offered is not None else []
        )
        credits_before_commit = list(model.credits)
        edge = model.commit(bool(out_ready), valid, desc)
        held_after = model.ctrl.held

        accepted_here = []
        for source, entry in enumerate(edge.pushed):
            if entry is not None:
                accepted[entry.desc] = k
                accepted_here.append({"source": source, "desc": entry.desc, "cycle": k})
        fired_here = None
        if edge.fired is not None:
            fired_here = {
                "source": edge.fired.source,
                "desc": edge.fired.entry.desc,
                "cycle": k,
            }
            fired[edge.fired.entry.desc] = k

        committed = None
        if edge.fired is not None:
            if offered is None or offered["source"] != edge.fired.source:
                raise AssertionError("committed fire lacks its offered grant")
            committed = {
                **offered,
                "source": edge.fired.source,
                "credits_after": list(model.credits),
            }
        if list(model.credits) != credits_before_commit and edge.fired is None:
            raise AssertionError("credit state changed without a fire")
        if held_before is None and held_after is not None:
            held_grant = offered
        elif held_before is not None and held_after is None:
            held_grant = None
        elif held_before is None and held_after is None:
            held_grant = None

        row = {
            "schema": TRACE_SCHEMA,
            "cycle": k,
            "phase": "drain" if draining else "active",
            "ready": bool(out_ready),
            "generation": [
                {"source": source, "desc": desc[source]}
                for source in range(4) if valid[source]
            ],
            "accepted": accepted_here,
            "fired": fired_here,
            "selection": None if choice is None else choice.source,
            "oldest_heads": _head_rows(view),
            "active": active,
            "eligible": eligible,
            "credits_before": credits_before,
            "candidate_source": (
                None if choice is None or held_before is not None else choice.source
            ),
            "candidate_refill": candidate_refill,
            "candidate_snapshot": candidate_snapshot,
            "offered_source": None if offered is None else offered["source"],
            "offered_refill": None if offered is None else offered["refill"],
            "offered_snapshot": None if offered is None else offered["snapshot"],
            "offered_origin_cycle": None if offered is None else offered["origin_cycle"],
            "offered_state": None if offered is None else offered["state"],
            "committed": committed,
            "committed_refill": None if committed is None else committed["refill"],
            "committed_snapshot": None if committed is None else committed["snapshot"],
            "credits_snapshot": None if offered is None else offered["snapshot"],
            "credits_after": list(model.credits),
            # Compatibility aliases now describe the offered grant, including a held grant.
            "refill": None if offered is None else offered["refill"],
            "refill_snapshot": (
                offered["snapshot"] if offered is not None and offered["refill"] else None
            ),
            "held_before": (
                None if held_before is None else
                {"source": held_before.source, "ctx": held_before.ctx}
            ),
            "held_view": view.held,
            "latched": (
                {"source": held_after.source, "ctx": held_after.ctx}
                if held_before is None and held_after is not None else None
            ),
            "released": held_before is not None and held_after is None,
            "reentry": reentry,
            "classes": list(model.classes()),
        }
        if any(value != "H" for value in row["classes"]):
            raise AssertionError("fixed all-High control changed class")
        rows.append(row)
        previous_active = active
    else:
        raise AssertionError("replay did not drain")

    generated = sum(len(row) for row in events)
    if generated != len(accepted) or generated != len(fired):
        raise AssertionError("generation/acceptance/fire conservation failed")
    return {
        "high_weight": high_weight,
        "rows": rows,
        "accepted": accepted,
        "fired": fired,
        "drain_cycles": drain_cycles,
        "conservation": {
            "generated": generated,
            "accepted": len(accepted),
            "fired": len(fired),
            "pass": generated == len(accepted) == len(fired),
        },
    }


def _wait_summary(left, right, sources=4):
    rows = {h: [] for h in range(sources)}
    for desc in sorted(left["fired"]):
        if desc not in right["fired"]:
            continue
        source = desc & 0xF
        generation = desc >> 4
        delta = (
            right["fired"][desc] - generation
            - (left["fired"][desc] - generation)
        )
        rows[source].append(delta)
    result = {}
    for source, values in rows.items():
        result[str(source)] = {
            "count": len(values),
            "sum": sum(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": sum(values) / len(values) if values else None,
        }
    return result


def compare(left, right):
    """Attribute the first selection divergence to policy state, not to workload."""
    if left["high_weight"] != 1 or right["high_weight"] != 2:
        raise ValueError("comparison expects 1:1 then 2:1")
    left_rows, right_rows = left["rows"], right["rows"]
    if [row["generation"] for row in left_rows] != [
        row["generation"] for row in right_rows
    ] or [row["ready"] for row in left_rows] != [
        row["ready"] for row in right_rows
    ]:
        raise ValueError("1:1 and 2:1 traces have different generation or ready inputs")
    selection_index = next(
        (index for index, (a, b) in enumerate(zip(left_rows, right_rows))
         if a["selection"] != b["selection"]),
        None,
    )
    fire_index = next(
        (
            index for index, (a, b) in enumerate(zip(left_rows, right_rows))
            if (None if a["fired"] is None else a["fired"]["source"])
            != (None if b["fired"] is None else b["fired"]["source"])
        ),
        None,
    )
    first = None
    if selection_index is not None:
        a, b = left_rows[selection_index], right_rows[selection_index]
        if a["held_before"] != b["held_before"]:
            cause = "held"
        elif a["offered_refill"] != b["offered_refill"]:
            cause = "refill"
        elif a["eligible"] != b["eligible"]:
            cause = "eligibility"
        elif a["offered_snapshot"] != b["offered_snapshot"]:
            cause = "credit_state"
        else:
            cause = "ordering_state"
        first = {
            "cycle": selection_index,
            "cause": cause,
            "selection_1to1": a["selection"],
            "selection_2to1": b["selection"],
            "eligible_1to1": a["eligible"],
            "eligible_2to1": b["eligible"],
            "added_eligible_by_2to1": sorted(set(b["eligible"]) - set(a["eligible"])),
            "candidate_refill_1to1": a["candidate_refill"],
            "candidate_refill_2to1": b["candidate_refill"],
            "offered_snapshot_1to1": a["offered_snapshot"],
            "offered_snapshot_2to1": b["offered_snapshot"],
            "offered_refill_1to1": a["offered_refill"],
            "offered_refill_2to1": b["offered_refill"],
            "offered_origin_cycle_1to1": a["offered_origin_cycle"],
            "offered_origin_cycle_2to1": b["offered_origin_cycle"],
            "committed_1to1": a["committed"],
            "committed_2to1": b["committed"],
            "held_1to1": a["held_before"],
            "held_2to1": b["held_before"],
            "reentry_1to1": a["reentry"],
            "reentry_2to1": b["reentry"],
        }
    return {
        "inputs_match": True,
        "input_cycles_checked": len(left_rows),
        "first_selection_divergence": first,
        "first_fire_divergence_cycle": fire_index,
        "wait_delta_2to1_minus_1to1": _wait_summary(left, right),
        "conservation": {
            "1to1": left["conservation"],
            "2to1": right["conservation"],
            "pass": left["conservation"]["pass"] and right["conservation"]["pass"],
        },
    }


def run_shift(sparse_start, horizon=18, stalls=DEFAULT_STALLS):
    events, ready = scenario(sparse_start, horizon, stalls)
    inputs = {
        "sparse_start": sparse_start,
        "events": events,
        "ready": ready,
        "classes": ["H", "H", "H", "H"],
    }
    left = replay(1, events, ready)
    right = replay(2, events, ready)
    return {
        "scope": "MODEL_ONLY",
        "production_evidence": False,
        "sparse_start": sparse_start,
        "inputs_sha256": digest(inputs),
        "events": [list(row) for row in events],
        "ready": list(ready),
        "1to1": left,
        "2to1": right,
        "comparison": compare(left, right),
    }


def run_sweep(base_start=4, shifts=(-2, -1, 0, 1, 2), horizon=18,
              stalls=DEFAULT_STALLS, existing_trace=None):
    cases = [run_shift(base_start + shift, horizon, stalls) for shift in shifts]
    causes = Counter(
        row["comparison"]["first_selection_divergence"]["cause"]
        for row in cases
        if row["comparison"]["first_selection_divergence"] is not None
    )
    summary = {
        "schema": TRACE_SCHEMA,
        "scope": "MODEL_ONLY",
        "production_evidence": False,
        "decision_trace_source": "deterministic_replay",
        "existing_trace": None if existing_trace is None else inspect_existing_trace(existing_trace),
        "base_sparse_start": base_start,
        "shifts": list(shifts),
        "horizon": horizon,
        "stalls": list(stalls),
        "cases": cases,
        "summary": {
            "shift_count": len(cases),
            "divergent_shifts": [
                row["sparse_start"] for row in cases
                if row["comparison"]["first_selection_divergence"] is not None
            ],
            "first_divergence_cycles": {
                str(row["sparse_start"]): row["comparison"]["first_selection_divergence"]["cycle"]
                for row in cases
                if row["comparison"]["first_selection_divergence"] is not None
            },
            "cause_counts": dict(sorted(causes.items())),
            "conservation_pass": all(
                row["comparison"]["conservation"]["pass"] for row in cases
            ),
        },
        "notes": [
            "MODEL_ONLY mechanism trace",
            "all sources fixed High; only absolute High credit changes",
            "fire and generation-to-fire are scheduler events, not CXL measurements",
        ],
    }
    summary["summary_sha256"] = digest(summary)
    return summary


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--existing-trace", help="optional RTL JSONL/JSONL.gz decision trace")
    result.add_argument("--base-start", type=int, default=4)
    result.add_argument("--shifts", type=int, nargs="+", default=[-2, -1, 0, 1, 2])
    result.add_argument("--horizon", type=int, default=18)
    result.add_argument("--stalls", type=int, nargs="*", default=list(DEFAULT_STALLS))
    result.add_argument("--output", help="optional JSON output path")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    result = run_sweep(
        args.base_start,
        tuple(args.shifts),
        args.horizon,
        tuple(args.stalls),
        args.existing_trace,
    )
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["summary"]["conservation_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
