"""Field-by-field comparison of diagnosis result JSON files (reference vs candidate).

Per top-level field of the union of both files:
  EQUAL           value identical (exact JSON equality, floats included)
  DIFFERENT       value differs (first differing path and both values reported)
  MISSING         present in the reference, absent in the candidate (gate FAIL)
  NOT_AVAILABLE   present only in the candidate (new field; reference cannot verify it)
  EXCLUDED        listed in --exclude with a reason (not compared, not counted as PASS)
Gate PASS iff no DIFFERENT and no MISSING field in any pair.

usage: geq_compare.py --pairs pairs.json --exclude NAME=REASON ... --output out.json
pairs.json: [{"id":..., "reference":path, "candidate":path}, ...]
"""
import argparse
import hashlib
import json
import pathlib


def first_diff(a, b, path=""):
    if type(a) is not type(b):
        return path or "/", a, b
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return f"{path}/{k}", a.get(k, "<absent>"), b.get(k, "<absent>")
            d = first_diff(a[k], b[k], f"{path}/{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}[len]", len(a), len(b)
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else (path or "/", a, b)


def short(v):
    s = json.dumps(v, sort_keys=True)
    return s if len(s) <= 200 else s[:200] + "..."


def compare(ref, cand, exclude):
    rows = {}
    for k in sorted(set(ref) | set(cand)):
        if k in exclude:
            rows[k] = dict(status="EXCLUDED", reason=exclude[k])
        elif k not in cand:
            rows[k] = dict(status="MISSING")
        elif k not in ref:
            rows[k] = dict(status="NOT_AVAILABLE")
        else:
            d = first_diff(ref[k], cand[k], f"/{k}")
            rows[k] = dict(status="EQUAL") if d is None else dict(
                status="DIFFERENT", path=d[0], reference=short(d[1]), candidate=short(d[2]))
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", required=True, type=pathlib.Path)
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--output", required=True, type=pathlib.Path)
    a = p.parse_args()
    exclude = dict(x.split("=", 1) for x in a.exclude)
    pairs = json.loads(a.pairs.read_text(encoding="utf-8"))
    if not pairs:
        p.error("at least one reference/candidate pair is required")
    out, ok = [], True
    for pr in pairs:
        ref_p, cand_p = pathlib.Path(pr["reference"]), pathlib.Path(pr["candidate"])
        ref, cand = json.loads(ref_p.read_text()), json.loads(cand_p.read_text())
        rows = compare(ref, cand, exclude)
        bad = [k for k, r in rows.items() if r["status"] in ("DIFFERENT", "MISSING")]
        ok &= not bad
        out.append(dict(id=pr["id"], reference=pr["reference"], candidate=pr["candidate"],
                        reference_sha256=hashlib.sha256(ref_p.read_bytes()).hexdigest(),
                        candidate_sha256=hashlib.sha256(cand_p.read_bytes()).hexdigest(),
                        status="PASS" if not bad else "FAIL", failing_fields=bad, fields=rows))
    status = {}
    for o in out:
        for k, r in o["fields"].items():
            status.setdefault(k, set()).add(r["status"])
    summary = {k: sorted(v) for k, v in sorted(status.items())}
    data = dict(schema="cxl-geq-compare-v1", overall="PASS" if ok else "FAIL", pairs=len(out),
                pairs_pass=sum(o["status"] == "PASS" for o in out), exclude=exclude,
                field_status_union=summary, results=out)
    with open(a.output, "x", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(dict(overall=data["overall"], pairs=data["pairs"], pairs_pass=data["pairs_pass"],
                          field_status_union=summary)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
