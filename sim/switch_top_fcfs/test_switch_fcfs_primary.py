"""Primary random regression of switch_top FCFS (spec 9, 10): one run = one (seed, N) pair.

Run through scripts/run_verify.sh M3-primary (20 seeds 509..528 x N 4/8/16 x 100,000 cycles).

The run replays the policy-independent intended trace traffic_trace.make_trace(seed, N, cycles,
"primary") from the first cycle after the initial reset (no warmup) for exactly CXL_PRIMARY_CYCLES
measured non-reset cycles, with every cycle checked by the same four layers as the directed tests
(model, model-free pin rules, scoreboard, TB tagged responses). It then drains (ready=1, no
pushes) and waits for every response. The spec section 10 metrics, the trace SHA-256 and the
coverage counters are written to fcfs_primary_metrics.json in the run directory; the runner copies
that file into the evidence directory and recomputes the trace hash independently.
"""

from __future__ import annotations

import os
import time

from switch_fcfs_tb import SwitchFcfsTb, run_seed, run_trace, write_json
from traffic_trace import make_trace

import cocotb

PROFILE = "primary"
METRICS_FILE = "fcfs_primary_metrics.json"


# Covers: SPEC §9 (20 reproducible seeds x 100,000 active cycles per primary configuration, no
#         warmup, bounded ready/stall patterns plus directed long stalls, drain phase, scoreboards,
#         TB tagged responses), §10 (accepted-transfer rate, push rate, mean/P99 waits with
#         drain-completed and censored samples labelled, per-source service, generation-to-acceptance)
@cocotb.test()
async def test_primary_random_regression(dut):
    if "CXL_PRIMARY_CYCLES" not in os.environ:
        raise RuntimeError("CXL_PRIMARY_CYCLES is not set: run through scripts/run_verify.sh M3-primary")
    cycles = int(os.environ["CXL_PRIMARY_CYCLES"])
    assert cycles > 0
    seed = run_seed()
    t0 = time.time()
    tb = SwitchFcfsTb(dut, "primary", unique_tags=True)
    trace = make_trace(seed, tb.n, cycles, PROFILE)
    assert sum(trace.reset) == 0, "the primary profile has no resets inside the measurement"
    dut._log.info("primary: seed=%d N=%d cycles=%d trace sha256=%s generated=%d", seed, tb.n, cycles,
                  trace.sha256, trace.generated)  # fmt: skip
    await tb.start()
    metrics = await run_trace(dut, tb, trace, log_every=20000)
    result = {
        "schema": "cxl-m3-fcfs-primary-v1",
        "policy": "FCFS",
        "policy_param": tb.policy,
        "seed": seed,
        "n_src": tb.n,
        "profile": PROFILE,
        "requested_cycles": cycles,
        "measured_cycles": metrics["phases"]["measured_non_reset_cycles"],
        "trace_sha256": trace.sha256,
        "wall_time_s": round(time.time() - t0, 3),
        **metrics,
    }
    write_json(METRICS_FILE, result)
    cov = tb.cov
    dut._log.info(
        "primary done: rate=%.4f pushes=%d fires=%d mean_wait=%s p99_wait=%s unaccepted=%d %s",
        metrics["accepted_transfer_rate"], metrics["input_push_count"], metrics["fires_measurement"],
        metrics["wait_acceptance_to_fire"]["all_completed"]["mean"],
        metrics["wait_acceptance_to_fire"]["all_completed"]["p99_nearest_rank"],
        metrics["generated_but_unaccepted"], cov.summary(),
    )  # fmt: skip
    # Scope and sanity: exact measured length, every source served, stimulus reached its corners.
    assert result["measured_cycles"] == cycles
    assert metrics["fires_measurement"] > 0 and all(c > 0 for c in metrics["per_source_service_measurement"])
    assert cov.full_refused > 0 and cov.ready_after_full_fire == cov.full_refused
    assert cov.max_valid_ready_low_run >= 256 and cov.ties > 0 and cov.b2b_fires > 0
    # No-bypass (wait >= 1) is asserted on every fire by the harness. Whether a wait of exactly 1
    # occurs depends on the trace (the switch must drain and receive a push with ready=1); it is a
    # recorded metric here (coverage min_wait), and a mandatory bin of the M3 directed/short tests.
    assert cov.min_wait is not None and cov.min_wait >= 1
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
