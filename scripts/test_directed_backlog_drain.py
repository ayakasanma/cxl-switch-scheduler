"""Model-only accounting checks and negative controls for the directed backlog drain.

Drives ``DrainAccounting`` from the independent ``ExperimentalSwitchModel`` (no RTL) and shows
that corrupted pin observations fail closed instead of passing.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_directed_backlog_drain as runner  # noqa: E402

_sim = runner.drain_module()
DEFAULT_RATES, run_model_only = _sim.DEFAULT_RATES, _sim.run_model_only


def job(policy="CGOF(2:1)", hw=2, **kw):
    base = dict(policy=policy, high_weight=hw, ordering="oldest-first", n_src=4, depth=16,
                window=5_000_000, seed=7301, gen_cycles=512, rates=list(DEFAULT_RATES))
    base.update(kw)
    return base


@pytest.mark.parametrize("policy,hw", [("CGOF(1:1)", 1), ("CGOF(2:1)", 2), ("FAI-inspired", None)])
def test_model_only_drain_conserves(policy, hw):
    r = run_model_only(job(policy, hw))
    cut, final = r["cutoff"], r["final"]
    assert all(b > 0 for b in cut["producer_backlog"])
    assert cut["fifo_occupancy"] == [16] * 4 and cut["fired_total"] == 0
    assert r["drain"]["cycles"] > 10 and r["drain"]["cycles"] < r["drain"]["limit"]
    assert r["drain"]["limit"] == 2 * cut["pending"] + 128
    assert final["generated"] == final["accepted"] == final["fired"]
    assert final["outstanding_total"] == 0 and r["input_hold_checks"] > 0


def test_runner_jobs_are_the_three_directed_configs():
    rows = runner.configs()
    jobs = [r["env"]["CXL_DRAIN_JOB"] for r in rows]
    assert len(rows) == 3 and len(set(jobs)) == 3
    assert {r["params"].get("HIGH_WEIGHT", "main") for r in rows} == {1, 2, "main"}
    assert all(r["params"]["FAI_W"] == 5_000_000 and r["params"]["DEPTH"] == 16 for r in rows)
    assert all(r["seeds"] == [7301] for r in rows)
    assert not set(runner.SEEDS_FORBIDDEN) & {7301}


def test_negative_corrupted_fire_descriptor_fails():
    def hook(s):
        if s["fire"]:
            s["out_desc"] ^= 1
        return s
    with pytest.raises(AssertionError, match="fired"):
        run_model_only(job(), hook)


def test_negative_lost_fire_fails():
    count = [0]

    def hook(s):
        if s["fire"]:
            count[0] += 1
            if count[0] == 100:  # model pops, accounting never sees the delivery
                s.update(out_valid=0, fire=False, out_source=None, out_desc=None)
        return s
    with pytest.raises(AssertionError, match="occupancy"):
        run_model_only(job(), hook)


def test_negative_fire_while_stalled_fails():
    def hook(s):
        if s["out_valid"] and not s["held"]:
            s["fire"] = True  # claim delivery while the sink is stalled
        return s
    with pytest.raises(AssertionError, match="fire != valid & ready"):
        run_model_only(job(), hook)


def test_verdict_requires_summary_overall_pass():
    good = [dict(status="PASS")] * 3
    assert runner.verdict(0, True, [], good, {"overall": "PASS"}) == "PASS"
    # negative controls: non-PASS / missing summary, legacy "status" key, other gates
    assert runner.verdict(0, True, [], good, {"overall": "FAIL"}) == "FAIL"
    assert runner.verdict(0, True, [], good, {}) == "FAIL"
    assert runner.verdict(0, True, [], good, {"status": "PASS"}) == "FAIL"
    assert runner.verdict(1, True, [], good, {"overall": "PASS"}) == "FAIL"
    assert runner.verdict(0, False, [], good, {"overall": "PASS"}) == "FAIL"
    assert runner.verdict(0, True, ["x"], good, {"overall": "PASS"}) == "FAIL"
    assert runner.verdict(0, True, [], good[:2], {"overall": "PASS"}) == "FAIL"
    assert runner.verdict(0, True, [], good[:2] + [dict(status="FAIL")],
                          {"overall": "PASS"}) == "FAIL"


def test_negative_no_backlog_fails_closed():
    with pytest.raises(AssertionError, match="producer backlog not positive"):
        run_model_only(job(rates=[0.01, 0.01, 0.01, 0.01]))
