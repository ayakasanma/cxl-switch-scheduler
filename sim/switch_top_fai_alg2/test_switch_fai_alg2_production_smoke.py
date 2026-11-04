"""Production-parameter SMOKE of switch_top POLICY=3 (FAI Algorithm-2) at the RTL default
FAI_W = 5,000,000 (not passed with -G), N4, milestone M6.

This is NOT the production-window test: no 5,000,000-cycle window closes in its length, so it
cannot show window classification (spec 9). It proves on the DUT that the production
configuration elaborates and runs with the production widths: 23-bit index/B/S, 2-bit state
per source, 5-bit context, shared 32-bit counter. Under the M3 "primary" intended trace every
source stays STABLE_HIGH, every visit is High and the selection must equal an independent FCFS
model every cycle (fai_alg2.md 5), with all harness layers active. The full >= 3-window
production run for Algorithm-2 is separate later work and is not claimed here.
"""

from __future__ import annotations

import os

from switch_fai_tb import SwitchFaiTb, fai_summary, run_seed, run_trace, write_json
from traffic_trace import make_trace

import cocotb

SMOKE_CYCLES = 20000
FAI_W_PRODUCTION = 5_000_000


# Covers: SPEC §8.5 (production 23-bit B/S/index, 32-bit thresholds; unchanged production widths for
#         the supplement), §8.6 (separate selection in the shared switch at the production window),
#         §5 (reset: all STABLE_HIGH, High first), fai_alg2.md 5 (no closing -> FCFS-equal selection)
@cocotb.test()
async def test_production_param_smoke(dut):
    cycles = int(os.environ.get("CXL_SMOKE_CYCLES", SMOKE_CYCLES))
    seed = run_seed()
    tb = SwitchFaiTb(dut, "alg2-prod-smoke", unique_tags=True)
    assert tb.policy == 3 and tb.w == FAI_W_PRODUCTION, f"built with POLICY={tb.policy} FAI_W={tb.w}"
    assert cycles < tb.w
    tb.enable_fcfs_mirror()
    trace = make_trace(seed, tb.n, cycles, "primary")
    await tb.start()
    fai = dut.gen_policy_fai_alg2.u_fai_sched
    assert (len(fai.idx_q), len(fai.s_q), len(fai.b_q), len(fai.cls_q)) == (23, 23, 23 * tb.n, 2 * tb.n)
    assert len(dut.u_out_hold.held_ctx_q) == 5 and len(dut.gen_arrival_ts.arrival_cnt_q) == 32
    first = tb.cycle_no
    checked0 = tb.fcfs_checked
    metrics = await run_trace(dut, tb, trace, log_every=10000)
    assert tb.fcfs_checked - checked0 == tb.cycle_no - first, "a cycle escaped the FCFS mirror"
    cov = tb.cov
    write_json("fai_alg2_production_smoke.json", {
        "schema": "cxl-m6-fai-alg2-production-smoke-v1", "policy": "FAI_ALG2", "policy_param": 3,
        "fai_w": tb.w, "seed": seed, "n_src": tb.n, "cycles": cycles, "trace_sha256": trace.sha256,
        "label": "SMOKE: no production window closes; widths + FCFS-equal selection only",
        "fai_measurement": fai_summary(metrics["coverage_measurement"], tb.w), **metrics,
    })  # fmt: skip
    assert cov.windows_closed == 0 and cov.states_seen == {(h, "STABLE_HIGH") for h in range(tb.n)}
    assert cov.fires_low == 0 and cov.fires_high == cov.fires > 0
    assert metrics["phases"]["measured_non_reset_cycles"] == cycles
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
