"""Pure pytest of scripts/compare_fai_interps.py on hand-written synthetic records (no DUT)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_fai_interps as cmp  # noqa: E402


def _rec(policy, offer, fire, push, closings, seed=509, w=64, sha="abc", **over):
    rec = {"push": push, "offer": offer, "fire": fire, "charged": ["H"] * sum(fire), "rst": [0] * len(push)}
    d = {
        "schema": cmp.SCHEMA, "policy": policy, "policy_param": 2 if policy == "FAI_MAIN" else 3,
        "fai_w": w, "seed": seed, "n_src": 4, "cycles": len(push),
        "trace_generator": "fai_stream.make_fai_stress_trace", "trace_sha256": sha,
        "record": rec, "record_digests": {k: cmp_digest(v) for k, v in rec.items()},
        "closings": closings, "effective_low_cycles_per_source": [0, 0, 0, 0],
        "fai_measurement": {"fires_high": sum(fire), "fires_low": 0, "windows_closed": len(closings),
                            "effective_class_changes": 0, "states_reached": [], "evidence": {}},
        "wait_acceptance_to_fire": {"all_completed": {"mean": 1.0, "p99_nearest_rank": 1}},
        "generation_to_acceptance": {"mean": 0.0, "p99_nearest_rank": 0},
        "input_push_count": sum(bin(p).count("1") for p in push), "per_source_pushes": [1, 0, 0, 0],
        "generated": 2, "generated_but_unaccepted": 0, "fires_measurement": sum(fire),
        "accepted_transfer_rate": sum(fire) / len(push), "per_source_service_measurement": [sum(fire), 0, 0, 0],
    }  # fmt: skip
    d.update(over)
    return d


def cmp_digest(v):
    import hashlib

    return hashlib.sha256(",".join(str(x) for x in v).encode()).hexdigest()


def _write(tmp_path, name, data):
    p = tmp_path / name / cmp.RECORD_NAME
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(data))
    return p


def test_identical_records_have_no_difference(tmp_path):
    a = _rec("FAI_MAIN", [-1, 0, 1], [0, 1, 1], [1, 2, 0], [{"new_eff": ["H"] * 4}])
    b = _rec("FAI_ALG2", [-1, 0, 1], [0, 1, 1], [1, 2, 0], [{"new_eff": ["H"] * 4}])
    out = tmp_path / "o.json"
    assert cmp.main(["--out", str(out), str(_write(tmp_path, "a", a)), str(_write(tmp_path, "b", b))]) == 0
    r = json.loads(out.read_text())
    p = r["pairs"][0]
    assert p["selection"] == {"first_cycle_offer_differs": None, "cycles_offer_differs": 0, "cycles_fire_source_differs": 0}
    assert p["acceptance"]["cycles_push_mask_differs"] == 0 and all(p["identical_record_streams"].values())
    assert r["aggregate"]["W64"]["pairs_with_any_offer_difference"] == 0


def test_runner_artifact_names_are_found(tmp_path):
    (tmp_path / "results").mkdir()
    for policy in ("FAI_MAIN", "FAI_ALG2"):
        (tmp_path / "results" / (f"cocotb_x_{policy}_seed509__" + cmp.RECORD_NAME)).write_text(
            json.dumps(_rec(policy, [-1], [0], [0], [])))
    (tmp_path / "results" / "other.json").write_text("{}")
    assert len(cmp.find_records([tmp_path])) == 2
    assert cmp.main(["--out", str(tmp_path / "comparison.json"), str(tmp_path)]) == 0


def test_differences_are_counted_exactly():
    a = _rec("FAI_MAIN", [-1, 0, 0, 2], [0, 1, 0, 1], [1, 0, 4, 0], [{"new_eff": ["H", "H", "H", "H"]}])
    b = _rec("FAI_ALG2", [-1, 1, 0, 2], [0, 1, 1, 1], [1, 2, 4, 0], [{"new_eff": ["L", "H", "H", "H"]}])
    r = cmp.compare([dict(a, _path="a"), dict(b, _path="b")])
    p = r["pairs"][0]
    assert p["selection"]["first_cycle_offer_differs"] == 1 and p["selection"]["cycles_offer_differs"] == 1
    # fire sources: [-1, 0, -1, 2] vs [-1, 1, 0, 2] -> 2 cycles differ
    assert p["selection"]["cycles_fire_source_differs"] == 2
    assert p["acceptance"] == {"first_cycle_push_mask_differs": 1, "cycles_push_mask_differs": 1}
    assert p["classes"]["first_closing_effective_map_differs"] == 0
    assert p["delta_alg2_minus_main"]["fires_measurement"] == 1


@pytest.mark.parametrize("field,value", [("trace_sha256", "zzz"), ("cycles", 99)])
def test_non_identical_stimulus_is_rejected(field, value):
    a = _rec("FAI_MAIN", [-1], [0], [0], [])
    b = _rec("FAI_ALG2", [-1], [0], [0], [], **{field: value})
    with pytest.raises(SystemExit):
        cmp.compare([dict(a, _path="a"), dict(b, _path="b")])


def test_unpaired_and_duplicate_records_are_rejected():
    a = _rec("FAI_MAIN", [-1], [0], [0], [])
    with pytest.raises(SystemExit):
        cmp.compare([dict(a, _path="a")])
    with pytest.raises(SystemExit):
        cmp.compare([dict(a, _path="a"), dict(a, _path="a2")])
    b = _rec("FAI_ALG2", [-1], [0], [0], [])
    b["record"]["rst"] = [1]
    with pytest.raises(SystemExit):
        cmp.compare([dict(a, _path="a"), dict(b, _path="b")])


@pytest.mark.parametrize("field", ["push", "offer", "fire", "rst", "charged"])
@pytest.mark.parametrize("damage", ["truncate", "digest"])
def test_corrupt_record_arrays_are_rejected(field, damage):
    a = _rec("FAI_MAIN", [0], [1], [1], [])
    b = _rec("FAI_ALG2", [0], [1], [1], [])
    if damage == "truncate":
        b["record"][field].pop()
        b["record_digests"][field] = cmp_digest(b["record"][field])
    else:
        b["record_digests"][field] = "0" * 64
    with pytest.raises(SystemExit):
        cmp.compare([a, b])


def test_empty_and_partial_matrix():
    with pytest.raises(SystemExit):
        cmp.compare([])
    a = _rec("FAI_MAIN", [-1], [0], [0], [])
    b = _rec("FAI_ALG2", [-1], [0], [0], [])
    assert cmp.compare([dict(a, _path="a"), dict(b, _path="b")])["full_matrix"] is False


def test_required_full_matrix_pairs():
    records = [dict(_rec(policy, [-1], [0], [0], [], seed=seed, w=w), _path=policy)
               for policy in ("FAI_MAIN", "FAI_ALG2") for w in (64, 256) for seed in range(509, 514)]
    assert cmp.compare(records)["full_matrix"] is True
    with pytest.raises(SystemExit):
        cmp.compare(records[:-1])
