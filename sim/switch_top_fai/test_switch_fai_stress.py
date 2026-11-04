"""Long random STRESS regression of switch_top FAI Main at the stress windows (spec 8.5, 9).

Run through scripts/run_verify.sh M5-stress: N 4/8/16 x FAI_W 64 / 256 (passed with -G) x seeds
509..513, CXL_STRESS_CYCLES trace cycles per run (W64: 400,000, W256: 800,000 = 6,250 / 3,125
nominal windows; resets restart the window, so the closed-window count is somewhat lower; >= 80 %
of the nominal count is required).

Stimulus: ``fai_stream.make_fai_stress_trace`` (pure function of seed, N, cycles, W; SHA-256
recorded), a window-scaled class-dynamics trace: per-window share skew (hot / medium / cold
sources), uniform, single-source, flip (two source sets alternating hot every window: opposing
evidence), idle for several windows (S = 0 windows after the backlog drains), whole-window output
stalls (S = 0 windows with backlog, offers held across several closing edges, full FIFOs), and
saturation; plus random long stalls and random + directed resets (mid-window / mid-visit / mid-hold).
It is replayed by the accepted ``switch_fcfs_tb.run_trace`` (producer hold, measured vs drain-only
populations, drain, TB responses) unchanged.

Every cycle of the run goes through every SwitchFaiTb layer: the independent oracle (pins, FIFO
state, cls_q / idx_q / b_q / s_q / turn_q / used_q, offered / held context, edge records incl.
closing counts / evidence / class maps vs the RTL nets), the model-free pin/history trackers (own
spec 8.1 evidence + literal spec 8.2 table, window position from the TB cycle count, B/S from pin
fires, visit/quota tracker, FCFS-in-class order), the scoreboard, the observed-pin input hold and the
TB-only tagged responses. Mandatory per run: all 16 (state x evidence) Main transitions, all four
states, effective class changes, every visit outcome, held grants across closing edges whose class
changes, closing-edge fires, Low service, full-plus-pop refusals and resets in the middle of
windows / visits / holds. Results: fai_stress_metrics.json in the run directory.

Full-plus-pop follow-ups across the measurement boundary: ``full_refused`` is counted in the fire
cycle t, its follow-up (``ready_after_full_fire`` or ``full_fire_then_reset``) only in cycle t+1.
A full-plus-pop fire in the LAST measured cycle therefore has its follow-up in the first drain
cycle, outside the frozen ``coverage_measurement`` snapshot. ``observe_measurement_boundary``
records the harness state at the exact freeze instant (one fire per cycle: 0 or 1 owed follow-up)
and ``check_full_followups`` requires the exact relation in both populations.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from fai_stream import make_fai_stress_trace
from switch_fai_tb import SwitchFaiTb, fai_summary, run_seed, run_trace, write_json

import cocotb

METRICS_FILE = "fai_stress_metrics.json"
SCHEMA = "cxl-m5-fai-stress-v1"
ALL16 = sorted(f"{s}/{e}" for s in ("H", "B_H", "L", "B_L") for e in ("UP", "DOWN", "KEEP", "S0"))


def observe_measurement_boundary(tb: SwitchFaiTb) -> dict:
    """Observe the measurement boundary of ``run_trace`` without changing stimulus, timing or checks.

    Installs a test-local instance-attribute wrapper around ``tb.drain``. The FIRST call is
    run_trace's drain, entered right after ``coverage_measurement`` was frozen: it records the TB
    cycle (the first drain cycle), the pin-history ``prev`` record, the coverage at that instant,
    the owed full-plus-pop follow-up (``prev`` is a fire from a full source with in_valid=1: its
    next-cycle observation is the first drain cycle) and the spec 4 boundary hold obligations, and
    captures the first drain cycle's observation before forwarding it to run_trace's ``on_cycle``.
    Later calls (``finish()``) pass through; every call records ``prev`` on return."""
    rec: dict = {"drain_calls": 0, "first_drain": None}
    orig_drain = tb.drain

    async def drain(guard_extra: int = 8, on_cycle=None):
        rec["drain_calls"] += 1
        if rec["drain_calls"] > 1:
            got = await orig_drain(guard_extra=guard_extra, on_cycle=on_cycle)
            rec["prev_after_drain"] = list(tb.prev)
            return got
        prev = tb.prev
        owed = 1 if prev[0] == "fire" and prev[2] is not None else 0
        src = prev[2] if owed else None
        hold = tb.in_hold.obligations()
        rec.update(
            cycle_no=tb.cycle_no,
            prev=list(prev),
            cov_at_entry=tb.cov.as_dict(),
            owed=owed,
            owed_src=src,
            hold_obligations=sorted(hold),
            owed_src_held_desc=hold.get(src) if owed else None,
        )

        def observe(o) -> None:
            if rec["first_drain"] is None:
                rec["first_drain"] = {
                    "cycle": o.cycle,
                    "in_valid": o.in_valid,
                    "in_ready": o.in_ready,
                    "push": o.push,
                    "fire": o.fire,
                    "owed_src_desc": o.in_desc[src] if owed else None,
                }
            if on_cycle is not None:
                on_cycle(o)

        got = await orig_drain(guard_extra=guard_extra, on_cycle=observe)
        rec["prev_after_drain"] = list(tb.prev)
        return got

    tb.drain = drain
    return rec


def _followups(cov: dict) -> dict:
    return {k: cov[k] for k in ("full_refused", "ready_after_full_fire", "full_fire_then_reset")}


def full_followup_details(cov_meas: dict, cov_total: dict, boundary: dict, drain_only: dict) -> dict:
    """JSON-ready record of the full-plus-pop follow-up accounting (no assertion)."""
    return {
        "rule": "full_refused counted at fire cycle t, its follow-up (ready_after_full_fire or "
        "full_fire_then_reset) at t+1; a full fire in the last measured cycle owes its follow-up to "
        "the first drain cycle. Measurement: ready_after_full_fire + full_fire_then_reset + owed == "
        "full_refused; whole run: ready_after_full_fire + full_fire_then_reset == full_refused",
        "boundary_cycle": boundary.get("cycle_no"),
        "prev_at_boundary": boundary.get("prev"),
        "cov_at_entry_equals_coverage_measurement": boundary.get("cov_at_entry") == cov_meas,
        "owed_followups": boundary.get("owed"),
        "owed_source": boundary.get("owed_src"),
        "owed_source_held_desc": boundary.get("owed_src_held_desc"),
        "hold_obligations_at_boundary": boundary.get("hold_obligations"),
        "boundary_held_sources": drain_only["boundary_held_sources"],
        "first_drain_cycle": boundary.get("first_drain"),
        "measurement": _followups(cov_meas),
        "total": _followups(cov_total),
        "drain_calls": boundary.get("drain_calls"),
        "prev_after_final_drain": boundary.get("prev_after_drain"),
    }


def check_full_followups(
    cov_meas: dict, cov_total: dict, boundary: dict, drain_only: dict, meas_end: Optional[int] = None
) -> dict:
    """Exact full-plus-pop follow-up relations in the measured and whole-run populations (asserts).

    ``boundary`` comes from ``observe_measurement_boundary``; the owed count (0 or 1) is derived
    from the observed boundary state, never a tolerance. Returns ``full_followup_details``."""
    d = full_followup_details(cov_meas, cov_total, boundary, drain_only)
    assert boundary["drain_calls"] == 2, f"expected run_trace drain + finish drain, saw {boundary['drain_calls']}"
    if meas_end is not None:
        assert boundary["cycle_no"] == meas_end, f"boundary observed at cycle {boundary['cycle_no']}, not {meas_end}"
    # a. the observation is the exact freeze instant (no cycle between the snapshot and the drain)
    assert d["cov_at_entry_equals_coverage_measurement"], "coverage changed between the measurement snapshot and the drain"
    owed, src = boundary["owed"], boundary["owed_src"]
    assert owed in (0, 1)
    m, t = d["measurement"], d["total"]
    # b. measured population: every follow-up seen inside the measurement, plus the owed one
    assert m["ready_after_full_fire"] + m["full_fire_then_reset"] + owed == m["full_refused"], (
        f"measured full-plus-pop follow-ups {m} with {owed} owed to the drain"
    )
    # c. whole run: every full-plus-pop fire has exactly one follow-up
    assert t["ready_after_full_fire"] + t["full_fire_then_reset"] == t["full_refused"], f"whole-run follow-ups {t}"
    # d. the owed follow-up is the first drain cycle: ready again, the identical held offer pushed
    if owed:
        f = boundary["first_drain"]
        assert f is not None and f["cycle"] == boundary["cycle_no"], f"first drain observation {f}"
        assert (f["in_ready"] >> src) & 1 and (f["push"] >> src) & 1, (
            f"cycle {f['cycle']}: source {src} fired from full at the boundary but in_ready/push = "
            f"{(f['in_ready'] >> src) & 1}/{(f['push'] >> src) & 1} in the first drain cycle"
        )
        assert f["owed_src_desc"] == boundary["owed_src_held_desc"], "held boundary offer changed bits"
        assert src in drain_only["boundary_held_sources"], f"source {src} not in {drain_only['boundary_held_sources']}"
        assert t["ready_after_full_fire"] - m["ready_after_full_fire"] >= 1
    # e. nothing pending after the drain of finish()
    p = boundary["prev_after_drain"]
    assert not (p[0] == "fire" and p[2] is not None), f"full-plus-pop follow-up pending after finish: {p}"
    return d


# Covers: SPEC §8.1-8.4 under sustained random traffic at W64 / W256 (window-local B/S, closing-edge
#         inclusion, exact thresholds, all sixteen (state x evidence) Main transitions, S=0 and
#         opposing / neutral cancellation, two-window effective change), §8.3 (10/10 visits,
#         relinquish, renewal, held grant context across classifications), §4 (stalls, full-plus-pop,
#         no bypass, producer hold), §5 (resets mid-window / mid-visit / mid-hold), §9 (FAI stress
#         tests W=64 and W=256, scoreboards, TB tagged responses)
@cocotb.test()
async def test_stress_random_regression(dut):
    if "CXL_STRESS_CYCLES" not in os.environ:
        raise RuntimeError("CXL_STRESS_CYCLES is not set: run through scripts/run_verify.sh M5-stress")
    cycles = int(os.environ["CXL_STRESS_CYCLES"])
    smoke = os.environ.get("CXL_INFRA_SMOKE") == "1"
    assert cycles > 0
    seed = run_seed()
    t0 = time.time()
    tb = SwitchFaiTb(dut, "stress", unique_tags=True)
    alg2 = tb.policy == 3
    assert tb.w in (64, 256), f"M5-stress runs the stress windows, built with FAI_W={tb.w}"
    trace = make_fai_stress_trace(seed, tb.n, cycles, tb.w)
    dut._log.info("stress: seed=%d N=%d FAI_W=%d cycles=%d trace sha256=%s generated=%d resets=%d%s", seed,
                  tb.n, tb.w, cycles, trace.sha256, trace.generated, sum(trace.reset),
                  " [INFRA SMOKE]" if smoke else "")  # fmt: skip
    await tb.start()
    meas_end = tb.cycle_no + cycles
    boundary = observe_measurement_boundary(tb)
    sim_t0 = time.time()
    metrics = await run_trace(dut, tb, trace, log_every=50000)
    sim_s = time.time() - sim_t0
    cov_m = metrics["coverage_measurement"]
    fai = fai_summary(cov_m, tb.w)
    followups = full_followup_details(cov_m, metrics["coverage_total"], boundary, metrics["drain_only"])
    result = {
        "schema": "cxl-m6-fai-alg2-stress-v1" if alg2 else SCHEMA,
        "policy": tb.interp.name,
        "policy_param": tb.policy,
        "fai_w": tb.w,
        "seed": seed,
        "n_src": tb.n,
        "profile": trace.profile,
        "requested_cycles": cycles,
        "measured_cycles": metrics["phases"]["measurement_cycles"],
        "measured_cycles_note": "trace (measurement) cycles, all simulated; reset cycles inside are "
        "listed in phases.measurement_reset_cycles and restart the window",
        "trace_sha256": trace.sha256,
        "infra_smoke": smoke,
        "windows_closed_measurement": cov_m["windows_closed"],
        "transitions_reached": cov_m["transitions_reached"],
        "states_reached": cov_m["states_reached"],
        "outstanding_after_drain": metrics["wait_acceptance_to_fire"]["outstanding_after_drain"],
        "fai_measurement": fai,
        "measurement_boundary": followups,
        "throughput": {
            "simulated_cycles_total": tb.cycle_no,
            "trace_and_drain_wall_s": round(sim_s, 3),
            "cycles_per_s": round((tb.cycle_no) / sim_s, 1) if sim_s > 0 else None,
            "peak_rss_kib": _peak_rss_kib(),
        },
        "wall_time_s": round(time.time() - t0, 3),
        **metrics,
    }
    write_json("fai_alg2_stress_metrics.json" if alg2 else METRICS_FILE, result)
    cov = tb.cov
    dut._log.info("stress done: windows=%d transitions=%d/16 rate=%.4f fires=%d %.1f cycles/s rss=%s KiB %s",
                  cov_m["windows_closed"], len(cov_m["transitions_reached"]), metrics["accepted_transfer_rate"],
                  metrics["fires_measurement"], result["throughput"]["cycles_per_s"], _peak_rss_kib(),
                  cov.summary())  # fmt: skip
    assert result["measured_cycles"] == cycles
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
    if smoke:
        return  # infrastructure smoke: every per-cycle check ran; coverage bins are not required
    c = cov_m
    all16 = {f"{s}/{e}" for s in tb.interp.states for e in ("UP", "DOWN", "KEEP", "S0")}
    missing = sorted(all16 - set(c["transitions_reached"]))
    assert not missing, f"{tb.interp.name} transitions not reached in this run: {missing}"
    assert c["states_reached"] == sorted(tb.interp.states) and c["effective_changes"] > 0
    assert c["windows_closed"] >= (cycles // tb.w) * 8 // 10, f"only {c['windows_closed']} windows closed"
    assert all(c["evidence"][e] > 0 for e in ("UP", "DOWN", "KEEP", "S0")), f"evidence {c['evidence']}"
    assert c["closing_fire"] > 0 and c["held_across_closing"] > 0 and c["max_windows_in_hold"] >= 2
    assert c["held_cls_change"] > 0 and c["held_fire_cls_differs"] > 0, "held grant across a class change"
    assert c["visits_continue"] > 0 and c["visits_expired"] > 0 and c["visits_emptied"] > 0
    assert c["visits_relinquished"] > 0 and c["visits_expired_replaced"] > 0 and c["renew_same_class"] > 0
    assert c["class_switch_offers"] > 0 and c["fires_low"] > 0 and c["fires_high"] > 0
    assert c["class_over_age"] > 0 and c["ties_in_class"] > 0
    assert c["full_refused"] > 0, "full-plus-pop refusal bin"
    check_full_followups(cov_m, metrics["coverage_total"], boundary, metrics["drain_only"], meas_end=meas_end)
    assert c["resets"] >= 1 and c["reset_mid_window"] > 0 and c["reset_mid_visit"] > 0 and c["reset_non_h"] > 0
    assert c["reset_during_hold"] > 0 and c["reset_nonempty"] > 0
    assert c["idle_cycles"] > 0 and c["max_valid_ready_low_run"] >= tb.w
    assert c["fire_sources"] == list(range(tb.n)) and c["min_wait"] == 1
    assert tb.resp.reordered > 0 and tb.resp.cross_epoch_completions > 0


def _peak_rss_kib():
    """Peak resident set size (VmHWM) of this simulator process, KiB (Linux)."""
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None
