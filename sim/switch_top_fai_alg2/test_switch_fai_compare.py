"""Main vs Algorithm-2 behavior-comparison RECORD run (milestone M6-compare), one cocotb test that
runs unchanged under switch_top POLICY=2 (FAI Main) or POLICY=3 (FAI Algorithm-2).

Both builds replay the IDENTICAL intended stimulus: ``fai_stream.make_fai_stress_trace(seed, N,
cycles, W)``, the accepted window-scaled class-dynamics trace (per-window share skew, flips, idle
and whole-window stall phases, random/directed resets), with the same downstream-ready and reset
trace. Its SHA-256 is recorded and must match between the two runs. Generation is intended
traffic: the ACTUAL input acceptance can differ by policy backpressure, and that difference is
recorded rather than hidden.

Every cycle goes through the full SwitchFaiTb layers of the selected interpretation (oracle,
model-free pin/history rules, scoreboard, producer hold, tagged responses), so the recorded traces
are checked behavior, not raw dumps. Recorded per measured cycle: push mask, offered source
(-1 if none), fire flag, charged class of each fire; per closing: cycle, evidence, old/new
effective class map. scripts/compare_fai_interps.py diffs a Main and an Algorithm-2 record. A
difference is an observation; no fairness improvement is claimed from it.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "switch_top_fai"))

from fai_stream import make_fai_stress_trace  # noqa: E402
from switch_fai_tb import SwitchFaiTb, ctx_of_bits, fai_summary, run_seed, run_trace, write_json  # noqa: E402

import cocotb  # noqa: E402

RECORD_FILE = "fai_compare_record.json"
SCHEMA = "cxl-m6-fai-compare-record-v1"


def _digest(values) -> str:
    return hashlib.sha256(",".join(str(v) for v in values).encode()).hexdigest()


# Covers: SPEC §10 (identical intended source-generation / downstream-ready traces across the two
#         interpretations, actual acceptance differences caused by backpressure recorded; accepted-
#         transfer rate, waits, per-source service, generation-to-acceptance), §8.6 vs §8.2
#         (behavior record of the two interpretations under the same W64/W256 class-changing load)
@cocotb.test()
async def test_compare_record(dut):
    if "CXL_COMPARE_CYCLES" not in os.environ:
        raise RuntimeError("CXL_COMPARE_CYCLES is not set: run through scripts/run_verify.sh M6-compare")
    cycles = int(os.environ["CXL_COMPARE_CYCLES"])
    seed = run_seed()
    tb = SwitchFaiTb(dut, "compare", unique_tags=True)
    assert tb.w in (64, 256), f"comparison runs use the stress windows, built with FAI_W={tb.w}"
    trace = make_fai_stress_trace(seed, tb.n, cycles, tb.w)
    await tb.start()
    rec = {"push": [], "offer": [], "fire": [], "charged": [], "rst": []}
    closings = []
    eff = tb.interp.effective
    orig_cycle = tb.cycle
    measuring = {"on": True}

    async def spy(*args, **kw):
        o = await orig_cycle(*args, **kw)
        if measuring["on"]:
            rec["rst"].append(0 if o.rst_n else 1)
            rec["push"].append(o.push)
            rec["offer"].append(o.out_source if o.out_valid else -1)
            rec["fire"].append(o.fire)
            if o.fire:
                rec["charged"].append("L" if ctx_of_bits(o.i_grant_ctx)[0] == "Low" else "H")
            if o.closing:
                closings.append({"k": len(rec["push"]) - 1, "evidence": o.evidence,
                                 "old_eff": ["L" if eff[c] == "Low" else "H" for c in o.old_cls],
                                 "new_eff": ["L" if eff[c] == "Low" else "H" for c in o.new_cls],
                                 "new_state": o.new_cls})  # fmt: skip
        return o

    tb.cycle = spy
    orig_drain = tb.drain

    async def drain(*args, **kw):
        measuring["on"] = False  # first drain call = end of the measured trace (run_trace)
        return await orig_drain(*args, **kw)

    tb.drain = drain
    metrics = await run_trace(dut, tb, trace)
    tb.cycle, tb.drain = orig_cycle, orig_drain
    assert len(rec["push"]) == cycles, f"recorded {len(rec['push'])} measured cycles, expected {cycles}"
    low_cycles = [0] * tb.n  # measured non-reset cycles each source spent effective Low
    cur = ["H"] * tb.n
    by_k = {c["k"]: c for c in closings}
    for k in range(cycles):
        if rec["rst"][k]:
            cur = ["H"] * tb.n
            continue
        for h in range(tb.n):
            low_cycles[h] += cur[h] == "L"
        if k in by_k:
            cur = by_k[k]["new_eff"]
    result = {
        "schema": SCHEMA,
        "policy": tb.interp.name,
        "policy_param": tb.policy,
        "fai_w": tb.w,
        "seed": seed,
        "n_src": tb.n,
        "cycles": cycles,
        "trace_generator": "fai_stream.make_fai_stress_trace",
        "trace_sha256": trace.sha256,
        "label": "behavior record under identical intended generation/ready/reset; differences between "
        "interpretations are observations, not fairness claims",
        "record": rec,
        "record_digests": {k: _digest(v) for k, v in rec.items()},
        "closings": closings,
        "effective_low_cycles_per_source": low_cycles,
        "fai_measurement": fai_summary(metrics["coverage_measurement"], tb.w),
        **metrics,
    }
    write_json(RECORD_FILE, result)
    assert metrics["generated"] == metrics["input_push_count"] + metrics["generated_but_unaccepted"]
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
    assert result["fai_measurement"]["windows_closed"] > 0
