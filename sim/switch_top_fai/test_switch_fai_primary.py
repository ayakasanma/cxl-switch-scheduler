"""Primary random regression of switch_top FAI Main (spec 9, 10): one run = one (seed, N) pair.

Run through scripts/run_verify.sh M5-primary (20 seeds 509..528 x N 4/8/16 x 100,000 cycles at the
production window FAI_W = 5,000,000, the RTL default of the primary configuration).

The run replays exactly the policy-independent intended trace that M3 used for FCFS and M4 for RR,
traffic_trace.make_trace(seed, N, cycles, "primary") (same generator, configuration and profile; the
runner compares its SHA-256 with reviews/evidence/M3-primary-v2-trace-hashes.tsv), from the first
cycle after the initial reset (no warmup) for exactly CXL_PRIMARY_CYCLES measured non-reset cycles,
then drains (boundary-held offers only, ready=1) and waits for every TB response (the accepted
switch_fcfs_tb.run_trace, unchanged). Every cycle is checked by every SwitchFaiTb layer (FAI oracle
incl. class/window/visit state, model-free pin/history trackers, scoreboard, observed-pin input
hold, TB tagged responses).

LABEL: no FAI window closes in 100,000 cycles at W = 5,000,000 (closings need 5,000,000 non-reset
edges). Every source therefore stays H, every visit is High, and the selected source sequence is
expected to equal FCFS for the identical acceptance history (docs/phase-3-uarch/fai_main.md 5). This
run checks that expectation on every cycle against an independent FCFS switch model stepped with
the same pins (``SwitchFaiTb.enable_fcfs_mirror``). It is NOT evidence of window classification or
adaptation; that is the separate M5-stress (W64/W256) and M5-production (W = 5,000,000, >= 3 real
windows) evidence. Actual acceptance is recorded separately from the intended generation; the spec
section 10 metrics, measured and drain-only populations, FAI visit statistics, the trace SHA-256 and
the coverage counters go to fai_primary_metrics.json in the run directory.
"""

from __future__ import annotations

import os
import time

from switch_fai_tb import SwitchFaiTb, fai_summary, run_seed, run_trace, write_json
from traffic_trace import make_trace

import cocotb

PROFILE = "primary"
METRICS_FILE = "fai_primary_metrics.json"
SCHEMA = "cxl-m5-fai-primary-v1"
FAI_W_PRODUCTION = 5_000_000


# Covers: SPEC §8.3 (High visits of at most 10 fires renewed without a bubble while the Low class is
#         empty), §8.1 (window index advances every non-reset cycle; no closing within 100,000),
#         §9 (20 reproducible seeds x 100,000 active cycles per primary configuration, no warmup,
#         identical intended traffic/ready traces as FCFS/RR, bounded ready/stall patterns plus
#         directed long stalls, drain phase, scoreboards, TB tagged responses), §10 (accepted-transfer
#         rate, push rate, mean/P99 waits with drain-completed and censored samples labelled,
#         per-source service incl. zero, generation-to-acceptance, generated-but-unaccepted),
#         fai_main.md 5 (FCFS equivalence while no window has closed)
@cocotb.test()
async def test_primary_random_regression(dut):
    if "CXL_PRIMARY_CYCLES" not in os.environ:
        raise RuntimeError("CXL_PRIMARY_CYCLES is not set: run through scripts/run_verify.sh M5-primary")
    cycles = int(os.environ["CXL_PRIMARY_CYCLES"])
    smoke = os.environ.get("CXL_INFRA_SMOKE") == "1"
    assert cycles > 0
    seed = run_seed()
    t0 = time.time()
    tb = SwitchFaiTb(dut, "primary", unique_tags=True)
    assert tb.w == FAI_W_PRODUCTION, f"M5-primary runs the production window, built with FAI_W={tb.w}"
    assert cycles < tb.w, "the primary length must stay inside the first window (no closing)"
    tb.enable_fcfs_mirror()
    trace = make_trace(seed, tb.n, cycles, PROFILE)
    assert sum(trace.reset) == 0, "the primary profile has no resets inside the measurement"
    dut._log.info("primary: seed=%d N=%d FAI_W=%d cycles=%d trace sha256=%s generated=%d%s", seed, tb.n,
                  tb.w, cycles, trace.sha256, trace.generated, " [INFRA SMOKE]" if smoke else "")  # fmt: skip
    await tb.start()
    assert len(dut.gen_policy_fai_main.u_fai_sched.idx_q) == 23, "production window index is 23 bits"
    first_cycle = tb.cycle_no
    checked_at_start = tb.fcfs_checked
    metrics = await run_trace(dut, tb, trace, log_every=20000)
    # The mirror checked every cycle after bring-up (no resets in the primary profile): the
    # ``cycles`` measured cycles plus the drain / response-wait cycles.
    assert tb.fcfs_checked - checked_at_start == tb.cycle_no - first_cycle, "a cycle escaped the FCFS mirror"
    cov_m = metrics["coverage_measurement"]
    fai = fai_summary(cov_m, tb.w)
    result = {
        "schema": SCHEMA,
        "policy": "FAI_MAIN",
        "policy_param": tb.policy,
        "fai_w": tb.w,
        "seed": seed,
        "n_src": tb.n,
        "profile": PROFILE,
        "requested_cycles": cycles,
        "measured_cycles": metrics["phases"]["measured_non_reset_cycles"],
        "trace_sha256": trace.sha256,
        "infra_smoke": smoke,
        "label": "NO window closes in the primary length at W=5,000,000: all sources stay H and the "
        "selection equals FCFS (checked every cycle against an independent FCFS model); NOT evidence "
        "of window classification/adaptation",
        "windows_closed_measurement": cov_m["windows_closed"],
        "fcfs_equivalence_checked_cycles": cycles,  # every measured cycle (asserted above)
        "fcfs_equivalence_checked_cycles_total": tb.fcfs_checked - checked_at_start,
        "intended_generation_vs_actual_acceptance": {
            "note": "generated = intended trace (policy-independent); input_push_count = actual FIFO "
            "acceptance during measurement (policy backpressure dependent)",
            "generated": metrics["generated"],
            "accepted_in_measurement": metrics["input_push_count"],
            "generated_but_unaccepted_at_boundary": metrics["generated_but_unaccepted"],
        },
        "fai_measurement": fai,
        "wall_time_s": None,
        **metrics,
    }
    result["wall_time_s"] = round(time.time() - t0, 3)
    write_json(METRICS_FILE, result)
    cov = tb.cov
    dut._log.info(
        "primary done: rate=%.4f pushes=%d fires=%d mean_wait=%s p99_wait=%s unaccepted=%d fcfs_checked=%d %s",
        metrics["accepted_transfer_rate"], metrics["input_push_count"], metrics["fires_measurement"],
        metrics["wait_acceptance_to_fire"]["all_completed"]["mean"],
        metrics["wait_acceptance_to_fire"]["all_completed"]["p99_nearest_rank"],
        metrics["generated_but_unaccepted"], tb.fcfs_checked, cov.summary(),
    )  # fmt: skip
    # Scope and sanity: exact measured length, no closing, all-H, every source served.
    assert result["measured_cycles"] == cycles
    assert cov_m["windows_closed"] == 0 and cov.windows_closed == 0, "no window may close in the primary run"
    assert cov.states_seen == {(h, "H") for h in range(tb.n)}, f"classes other than H seen: {cov.states_seen}"
    assert cov.fires_low == 0 and cov.fires_high == cov.fires, "every fire is charged to a High visit"
    assert metrics["generated"] == metrics["input_push_count"] + metrics["generated_but_unaccepted"]
    assert metrics["fires_measurement"] > 0 and all(c > 0 for c in metrics["per_source_service_measurement"])
    if not smoke:
        assert cov.full_refused > 0 and cov.ready_after_full_fire == cov.full_refused
        assert cov.max_valid_ready_low_run >= 256 and cov.b2b_fires > 0
        assert cov.visits_expired > 0 and cov.renew_same_class > 0, "High quota expiry renewed without a bubble"
    # No-bypass (wait >= 1) is asserted on every fire by the harness; an exact 1-cycle minimum is a
    # mandatory bin of the directed/short tests, a recorded metric here.
    assert cov.min_wait is not None and cov.min_wait >= 1
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
