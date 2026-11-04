#!/usr/bin/env python3
"""Compare FAI Main and FAI Algorithm-2 behavior records (M6-compare).

Input: the ``fai_compare_record.json`` files written by
sim/switch_top_fai_alg2/test_switch_fai_compare.py, found under one or two runner evidence
directories (artifacts/implementation/M6-compare/<run-id>/results/...). Records are paired by
(N, W, seed); each pair must have identical intended traces (same generator, same SHA-256, same
measured length) or the script fails.

Output (JSON, plus a short Markdown table on stdout): per pair and aggregated per W, the ACTUAL
differences of the two interpretations under the same intended stimulus:
  * acceptance: total / per-source pushes, generated-but-unaccepted, first measured cycle whose
    push mask differs, number of cycles with a different push mask;
  * selection: first cycle whose offered source differs, cycles with a different offer / fire;
  * service: per-source fires, fires charged to High / Low visits, accepted-transfer rate;
  * waiting: mean / P99 acceptance-to-fire (all completed), generation-to-acceptance;
  * classes: windows closed, effective-class changes, cycles each source spent effective Low,
    first closing whose effective class map differs.
Differences are observations. The script states no fairness conclusion.

Usage: python scripts/compare_fai_interps.py --out <file.json> <evidence dir or record file> [...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RECORD_NAME = "fai_compare_record.json"
SCHEMA = "cxl-m6-fai-compare-record-v1"
OUT_SCHEMA = "cxl-m6-fai-compare-v1"


def find_records(paths: List[Path]) -> List[Path]:
    found: List[Path] = []
    for p in paths:
        if p.is_file():
            found.append(p)
        elif p.is_dir():
            # The runner copies run-directory artifacts as results/<job>__<file>.
            found.extend(sorted(set(p.rglob(RECORD_NAME)) | set(p.rglob(f"*__{RECORD_NAME}"))))
        else:
            raise SystemExit(f"compare_fai_interps: {p} does not exist")
    return found


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise SystemExit(f"compare_fai_interps: {path} has schema {data.get('schema')!r}, expected {SCHEMA}")
    data["_path"] = str(path)
    return data


def _first_diff(a: List, b: List) -> Optional[int]:
    for k, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return k
    return None if len(a) == len(b) else min(len(a), len(b))


def _count_diff(a: List, b: List) -> int:
    return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))


def _side(r: dict) -> dict:
    w = r["wait_acceptance_to_fire"]["all_completed"]
    g = r["generation_to_acceptance"]
    fm = r["fai_measurement"]
    return {
        "input_push_count": r["input_push_count"],
        "per_source_pushes": r["per_source_pushes"],
        "generated": r["generated"],
        "generated_but_unaccepted": r["generated_but_unaccepted"],
        "fires_measurement": r["fires_measurement"],
        "accepted_transfer_rate": r["accepted_transfer_rate"],
        "per_source_service_measurement": r["per_source_service_measurement"],
        "fires_high": fm["fires_high"],
        "fires_low": fm["fires_low"],
        "wait_mean": w.get("mean"),
        "wait_p99": w.get("p99_nearest_rank"),
        "gen_to_accept_mean": g.get("mean"),
        "gen_to_accept_p99": g.get("p99_nearest_rank"),
        "windows_closed": fm["windows_closed"],
        "effective_class_changes": fm["effective_class_changes"],
        "states_reached": fm["states_reached"],
        "effective_low_cycles_per_source": r["effective_low_cycles_per_source"],
        "evidence": fm["evidence"],
    }


def compare_pair(main: dict, alg2: dict) -> dict:
    key = (main["n_src"], main["fai_w"], main["seed"])
    if (alg2["n_src"], alg2["fai_w"], alg2["seed"]) != key:
        raise SystemExit(f"compare_fai_interps: unpaired records {main['_path']} / {alg2['_path']}")
    if main["policy"] != "FAI_MAIN" or alg2["policy"] != "FAI_ALG2":
        raise SystemExit(f"compare_fai_interps: policies {main['policy']} / {alg2['policy']}")
    for f in ("trace_generator", "trace_sha256", "cycles"):
        if main[f] != alg2[f]:
            raise SystemExit(f"compare_fai_interps: {key}: intended stimulus differs in {f}: {main[f]} / {alg2[f]}")
    ra, rb = main["record"], alg2["record"]
    if ra["rst"] != rb["rst"]:
        raise SystemExit(f"compare_fai_interps: {key}: reset traces differ")
    cl_a = [c["new_eff"] for c in main["closings"]]
    cl_b = [c["new_eff"] for c in alg2["closings"]]
    fire_src_a = [s if f else -1 for s, f in zip(ra["offer"], ra["fire"])]
    fire_src_b = [s if f else -1 for s, f in zip(rb["offer"], rb["fire"])]
    sa, sb = _side(main), _side(alg2)
    delta = {
        "input_push_count": sb["input_push_count"] - sa["input_push_count"],
        "generated_but_unaccepted": sb["generated_but_unaccepted"] - sa["generated_but_unaccepted"],
        "fires_measurement": sb["fires_measurement"] - sa["fires_measurement"],
        "per_source_service": [b - a for a, b in zip(sa["per_source_service_measurement"], sb["per_source_service_measurement"])],
        "per_source_pushes": [b - a for a, b in zip(sa["per_source_pushes"], sb["per_source_pushes"])],
        "fires_low": sb["fires_low"] - sa["fires_low"],
        "effective_low_cycles_per_source": [
            b - a for a, b in zip(sa["effective_low_cycles_per_source"], sb["effective_low_cycles_per_source"])
        ],
    }
    return {
        "n_src": key[0],
        "fai_w": key[1],
        "seed": key[2],
        "cycles": main["cycles"],
        "trace_sha256": main["trace_sha256"],
        "records": {"main": main["_path"], "alg2": alg2["_path"]},
        "identical_record_streams": {k: main["record_digests"][k] == alg2["record_digests"][k] for k in ra},
        "acceptance": {
            "first_cycle_push_mask_differs": _first_diff(ra["push"], rb["push"]),
            "cycles_push_mask_differs": _count_diff(ra["push"], rb["push"]),
        },
        "selection": {
            "first_cycle_offer_differs": _first_diff(ra["offer"], rb["offer"]),
            "cycles_offer_differs": _count_diff(ra["offer"], rb["offer"]),
            "cycles_fire_source_differs": _count_diff(fire_src_a, fire_src_b),
        },
        "classes": {
            "closings": [len(cl_a), len(cl_b)],
            "first_closing_effective_map_differs": _first_diff(cl_a, cl_b),
            "closings_effective_map_differs": _count_diff(cl_a, cl_b),
        },
        "main": sa,
        "alg2": sb,
        "delta_alg2_minus_main": delta,
    }


def aggregate(pairs: List[dict]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for w in sorted({p["fai_w"] for p in pairs}):
        sel = [p for p in pairs if p["fai_w"] == w]
        out[f"W{w}"] = {
            "pairs": len(sel),
            "seeds": [p["seed"] for p in sel],
            "pairs_with_any_offer_difference": sum(1 for p in sel if p["selection"]["cycles_offer_differs"]),
            "pairs_with_any_push_difference": sum(1 for p in sel if p["acceptance"]["cycles_push_mask_differs"]),
            "sum_cycles_offer_differs": sum(p["selection"]["cycles_offer_differs"] for p in sel),
            "sum_cycles_push_mask_differs": sum(p["acceptance"]["cycles_push_mask_differs"] for p in sel),
            "sum_closings_effective_map_differs": sum(p["classes"]["closings_effective_map_differs"] for p in sel),
            "sum_delta_fires_measurement": sum(p["delta_alg2_minus_main"]["fires_measurement"] for p in sel),
            "sum_delta_input_push_count": sum(p["delta_alg2_minus_main"]["input_push_count"] for p in sel),
            "sum_delta_fires_low": sum(p["delta_alg2_minus_main"]["fires_low"] for p in sel),
        }
    return out


def compare(records: List[dict]) -> dict:
    if not records:
        raise SystemExit("compare_fai_interps: no records")
    by_key: Dict[Tuple[int, int, int], Dict[str, dict]] = {}
    for r in records:
        rec = r.get("record", {})
        digests = r.get("record_digests", {})
        fields = {"push", "offer", "fire", "charged", "rst"}
        if (type(r.get("cycles")) is not int or r["cycles"] <= 0
                or set(rec) != fields or set(digests) != fields
                or any(not isinstance(rec[k], list) for k in fields)):
            raise SystemExit("compare_fai_interps: malformed cycle record")
        if (any(type(v) is not int or v not in (0, 1) for k in ("fire", "rst") for v in rec[k])
                or any(v not in ("H", "L") for v in rec["charged"])):
            raise SystemExit("compare_fai_interps: malformed fire/reset/charged stream")
        for k in fields:
            expected = sum(rec["fire"]) if k == "charged" else r["cycles"]
            digest = hashlib.sha256(",".join(str(v) for v in rec[k]).encode()).hexdigest()
            if len(rec[k]) != expected or digests[k] != digest:
                raise SystemExit(f"compare_fai_interps: {r.get('_path', '<record>')}: invalid {k} length or digest")
        if any(len(r[k]) != r["n_src"] for k in ("per_source_pushes", "per_source_service_measurement", "effective_low_cycles_per_source")):
            raise SystemExit("compare_fai_interps: invalid per-source array length")
        slot = by_key.setdefault((r["n_src"], r["fai_w"], r["seed"]), {})
        if r["policy"] in slot:
            raise SystemExit(f"compare_fai_interps: duplicate {r['policy']} record for {(r['n_src'], r['fai_w'], r['seed'])}")
        slot[r["policy"]] = r
    pairs = []
    for key in sorted(by_key):
        slot = by_key[key]
        if set(slot) != {"FAI_MAIN", "FAI_ALG2"}:
            raise SystemExit(f"compare_fai_interps: {key} has only {sorted(slot)}")
        pairs.append(compare_pair(slot["FAI_MAIN"], slot["FAI_ALG2"]))
    return {
        "schema": OUT_SCHEMA,
        "label": "observed behavior differences under identical intended stimulus; NOT a fairness "
        "or performance claim, stress windows only, N4 supplementary scope",
        "pairs": pairs,
        "full_matrix": set(by_key) == {(4, w, seed) for w in (64, 256) for seed in range(509, 514)},
        "aggregate": aggregate(pairs),
    }


def markdown(result: dict) -> str:
    lines = [
        "| N | W | seed | offer diff cycles | push diff cycles | fires M/A | pushes M/A | Low fires M/A | "
        "wait mean M/A | wait P99 M/A | map-diff closings |",
        "| ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |",
    ]
    for p in result["pairs"]:
        m, a = p["main"], p["alg2"]

        def f(x):
            return "N/A" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))

        lines.append(
            f"| {p['n_src']} | {p['fai_w']} | {p['seed']} | {p['selection']['cycles_offer_differs']} | "
            f"{p['acceptance']['cycles_push_mask_differs']} | {m['fires_measurement']}/{a['fires_measurement']} | "
            f"{m['input_push_count']}/{a['input_push_count']} | {m['fires_low']}/{a['fires_low']} | "
            f"{f(m['wait_mean'])}/{f(a['wait_mean'])} | {f(m['wait_p99'])}/{f(a['wait_p99'])} | "
            f"{p['classes']['closings_effective_map_differs']} |"
        )
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path, help="output JSON file")
    ap.add_argument("inputs", nargs="+", type=Path, help="evidence directories or record files")
    args = ap.parse_args(argv)
    paths = find_records(args.inputs)
    if not paths:
        raise SystemExit("compare_fai_interps: no fai_compare_record.json found")
    result = compare([load(p) for p in paths])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
