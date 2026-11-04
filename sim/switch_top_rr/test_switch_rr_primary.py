"""Primary random regression of switch_top RR (spec 9, 10): one run = one (seed, N) pair.

Run through scripts/run_verify.sh M4-primary (20 seeds 509..528 x N 4/8/16 x 100,000 cycles, RR
quantum 10 = the RTL default of the primary configuration).

The run replays exactly the policy-independent intended trace that M3 used for FCFS,
traffic_trace.make_trace(seed, N, cycles, "primary") (same generator, configuration and profile; the
runner compares its SHA-256 with reviews/evidence/M3-primary-v2-trace-hashes.tsv), from the first
cycle after the initial reset (no warmup) for exactly CXL_PRIMARY_CYCLES measured non-reset cycles.
Every cycle is checked by the same layers as the directed tests (RR oracle incl. polling state,
model-free pin rules incl. the pin-level turn tracker, scoreboard, observed-pin input hold, TB
tagged responses). It then drains (the boundary-held offers only, ready=1) and waits for every
response. Actual input acceptance is recorded separately from the intended generation; the spec
section 10 metrics, measured and drain-only populations, RR turn statistics, the trace SHA-256 and
the coverage counters are written to rr_primary_metrics.json in the run directory.
"""

from __future__ import annotations

import os
import time

from switch_rr_tb import SwitchRrTb, rr_turn_summary, run_seed, run_trace, write_json
from traffic_trace import make_trace

import cocotb

PROFILE = "primary"
METRICS_FILE = "rr_primary_metrics.json"
SCHEMA = "cxl-m4-rr-primary-v1"


# Covers: SPEC §7 (RR quantum 10 under sustained traffic), §9 (20 reproducible seeds x 100,000
#         active cycles per primary configuration, no warmup, identical intended traffic/ready traces
#         as the other policies, bounded ready/stall patterns plus directed long stalls, drain
#         phase, scoreboards, TB tagged responses), §10 (accepted-transfer rate, push rate, mean/P99
#         waits with drain-completed and censored samples labelled, per-source service incl. zero,
#         generation-to-acceptance, generated-but-unaccepted)
@cocotb.test()
async def test_primary_random_regression(dut):
    if "CXL_PRIMARY_CYCLES" not in os.environ:
        raise RuntimeError("CXL_PRIMARY_CYCLES is not set: run through scripts/run_verify.sh M4-primary")
    cycles = int(os.environ["CXL_PRIMARY_CYCLES"])
    assert cycles > 0
    seed = run_seed()
    t0 = time.time()
    tb = SwitchRrTb(dut, "primary", unique_tags=True)
    trace = make_trace(seed, tb.n, cycles, PROFILE)
    assert sum(trace.reset) == 0, "the primary profile has no resets inside the measurement"
    dut._log.info("primary: seed=%d N=%d RR_QUANTUM=%d cycles=%d trace sha256=%s generated=%d", seed, tb.n,
                  tb.q, cycles, trace.sha256, trace.generated)  # fmt: skip
    await tb.start()
    metrics = await run_trace(dut, tb, trace, log_every=20000)
    result = {
        "schema": SCHEMA,
        "policy": "RR",
        "policy_param": tb.policy,
        "rr_quantum": tb.q,
        "seed": seed,
        "n_src": tb.n,
        "profile": PROFILE,
        "requested_cycles": cycles,
        "measured_cycles": metrics["phases"]["measured_non_reset_cycles"],
        "trace_sha256": trace.sha256,
        "intended_generation_vs_actual_acceptance": {
            "note": "generated = intended trace (policy-independent); input_push_count = actual FIFO "
            "acceptance during measurement (policy backpressure dependent)",
            "generated": metrics["generated"],
            "accepted_in_measurement": metrics["input_push_count"],
            "generated_but_unaccepted_at_boundary": metrics["generated_but_unaccepted"],
        },
        "rr_turns_measurement": rr_turn_summary(metrics["coverage_measurement"], tb.q),
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
    assert metrics["generated"] == metrics["input_push_count"] + metrics["generated_but_unaccepted"]
    assert metrics["fires_measurement"] > 0 and all(c > 0 for c in metrics["per_source_service_measurement"])
    assert cov.full_refused > 0 and cov.ready_after_full_fire == cov.full_refused
    assert cov.max_valid_ready_low_run >= 256 and cov.b2b_fires > 0
    assert cov.turns_expired > 0 and cov.turns_emptied > 0 and cov.stall_mid_turn > 0
    # No-bypass (wait >= 1) is asserted on every fire by the harness; an exact 1-cycle minimum is a
    # mandatory bin of the directed/short tests, a recorded metric here.
    assert cov.min_wait is not None and cov.min_wait >= 1
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
