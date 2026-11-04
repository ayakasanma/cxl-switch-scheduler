"""PRODUCTION-window regression of switch_top FAI Main: W = 5,000,000 over real complete windows.

Run through scripts/run_verify.sh M5-production: N 4/8/16, seed 509, FAI_W = the RTL default
5,000,000 (NOT passed with -G; the 23-bit index / B / S widths are checked on the DUT),
CXL_PRODUCTION_CYCLES = 20,000,000 real non-reset cycles = 4 complete windows (spec 9 requires >= 3).

What this run is (spec 8.1, 8.4, 9): every one of those cycles is a real simulated clock edge of
the Verilated RTL. There is NO time skip, NO deposit / preload of the window index, B, S, class or
any other internal state, and NO smaller window relabelled as production. Closings happen at the
5,000,000-th, 10,000,000-th, ... non-reset edge after reset exactly as in the production
configuration.

Checks (bounded memory, streaming): every cycle goes through every SwitchFaiTb layer - the
independent oracle (pins, FIFO state, cls_q / idx_q / b_q / s_q / turn_q / used_q, offered / held
context, edge records vs the RTL nets), the model-free pin/history trackers (own spec 8.1 evidence +
literal spec 8.2 table, window position from the TB cycle count, B/S recomputed from pin fires,
visit/quota tracker, FCFS-in-class order), the pin-level conservation / order / 105-bit / source
scoreboard, the observed-pin input hold and the TB-only tagged responses. Only outstanding /
in-flight records and aggregate counters are kept: the scoreboard holds at most D=16 entries per
source, the producers only pending descriptors, the responder only outstanding tags, waits and
generation-to-acceptance delays go into exact integer histograms (``fai_stream.StreamStats``), and
the oracle's append-only informational visit/window history lists are dropped periodically
(``SwitchFaiTb.trim_model_logs``; the oracle never reads them). One summary per closed window is
kept (closing counts, evidence, transitions per source).

Traffic (``fai_stream.ProductionTraffic``, streaming, SHA-256 recorded): per complete window a
designed per-source service-share skew at total load 0.55 < output capacity, so the closing evidence
of every source is predictable from spec 8.1 and the class sequence from spec 8.2 (hand-derivable,
asserted at every closing edge): groups g = h % 4 follow
    g0: DOWN, DOWN, UP, UP    -> B_H, L, B_L, H   (High -> Low -> High through both buffers)
    g1: DOWN, UP, DOWN, DOWN  -> B_H, H, B_H, L   (opposing evidence cancels, later Low)
    g2: UP, KEEP, DOWN, KEEP  -> H, H, B_H, H     (KEEP cancels a pending decrease)
    g3: DOWN, DOWN, KEEP, UP  -> B_H, L, L, B_L
plus random bounded ready stalls and directed stalls at each window boundary: boundaries 1 and 3
hold an offer ACROSS the closing edge, boundaries 2 and 4 end the stall just before the closing edge
so the closing edge carries a fire (spec 8.4 steps 1-2: included in the closing counts).

A run with CXL_INFRA_SMOKE=1 (runner --infra-smoke) may be shorter than one window; it is labelled
"infra_smoke" and "production_evidence": false and is NEVER production evidence.
"""

from __future__ import annotations

import os
import time

from fai_stream import (
    ProductionTraffic,
    StreamProducers,
    StreamStats,
    expected_classes,
    production_kinds,
    production_shares,
)
from switch_fai_tb import SwitchFaiTb, fai_summary, run_seed, write_json

import cocotb

METRICS_FILE = "fai_production_metrics.json"
SCHEMA = "cxl-m5-fai-production-v1"
W_PRODUCTION = 5_000_000
MIN_WINDOWS = 3
TRIM_EVERY = 1 << 16
LOG_EVERY = 500_000


def _status_kib(key: str):
    """VmRSS / VmHWM of this simulator process in KiB (Linux /proc)."""
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith(key + ":"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


# Covers: SPEC §8.1 (production W=5,000,000; window index on every non-reset cycle; window-local B/S;
#         exact thresholds with all N sources in the average), §8.2 (Main table through REAL
#         5,000,000-cycle windows: H->B_H->L->B_L->H, opposing and KEEP cancellation, two-window
#         effective changes), §8.4 (closing-edge fire included, held offer across closing edges,
#         new class visible next cycle, clear), §8.5 (23-bit production B/S/index widths), §9 (at
#         least one W=5,000,000 test over >= 3 complete windows per FAI N value, every-cycle checking,
#         scoreboards, TB tagged responses), §4 (stalls, producer hold, conservation, full105)
@cocotb.test()
async def test_production_windows(dut):
    if "CXL_PRODUCTION_CYCLES" not in os.environ:
        raise RuntimeError("CXL_PRODUCTION_CYCLES is not set: run through scripts/run_verify.sh M5-production")
    cycles = int(os.environ["CXL_PRODUCTION_CYCLES"])
    smoke = os.environ.get("CXL_INFRA_SMOKE") == "1"
    seed = run_seed()
    t0 = time.time()
    tb = SwitchFaiTb(dut, "production", unique_tags=False)  # tags unique by construction (bijection)
    alg2 = tb.policy == 3
    metrics_file = "fai_alg2_production_metrics.json" if alg2 else METRICS_FILE
    n, w = tb.n, tb.w
    assert w == W_PRODUCTION, f"M5-production runs the production window, built with FAI_W={w}"
    assert cycles > 0
    if not smoke:
        assert cycles % w == 0 and cycles // w >= MIN_WINDOWS, (
            f"production needs a whole number >= {MIN_WINDOWS} of windows, got {cycles} cycles"
        )
    windows = cycles // w
    exp_cls = expected_classes(n, windows, interpretation="alg2" if alg2 else "main")
    traffic = ProductionTraffic(seed, n, cycles, w)
    prod = StreamProducers(n)
    dut._log.info("production: seed=%d N=%d FAI_W=%d cycles=%d windows=%d%s", seed, n, w, cycles, windows,
                  " [INFRA SMOKE - NOT production evidence]" if smoke else "")  # fmt: skip
    await tb.start()
    fai = getattr(dut, tb.interp.scope).u_fai_sched
    assert (len(fai.idx_q), len(fai.s_q), len(fai.b_q)) == (23, 23, 23 * n), "production widths (spec 8.5)"

    base = tb.cycle_no  # TB cycle of trace cycle 0
    meas_end = base + cycles
    waits_meas, waits_drain, waits_drain_only = StreamStats(), StreamStats(), StreamStats()
    gen_to_accept, gen_to_accept_drain = StreamStats(), StreamStats()
    fires_meas, fires_drain, fires_drain_only = [0] * n, [0] * n, [0] * n
    pushes_src, drain_pushes_src = [0] * n, [0] * n

    def on_fire(src: int, e, cycle: int) -> None:
        wt = cycle - e.accept_cycle
        if cycle < meas_end:
            fires_meas[src] += 1
            waits_meas.add(wt)
        elif e.accept_cycle < meas_end:
            fires_drain[src] += 1
            waits_drain.add(wt)
        else:
            fires_drain_only[src] += 1
            waits_drain_only.add(wt)

    def on_drop(_src: int, _e) -> None:
        raise AssertionError("the production trace has no reset after bring-up")

    tb.on_fire = on_fire
    tb.on_reset_drop = on_drop
    window_records = []
    t_meas = time.time()
    t_last, k_last = t_meas, 0
    for k in range(cycles):
        events, ready = traffic.step(k)
        if events:
            prod.generate(k, events)
        offers = prod.offers()
        o = await tb.cycle(
            push={h: d for h, (_g, d) in offers.items()},
            out_ready=ready,
            meta={h: g for h, (g, _d) in offers.items()},
        )
        if o.push:
            for h in range(n):
                if (o.push >> h) & 1:
                    g, d = prod.accept(h, k)
                    assert d == o.in_desc[h]
                    pushes_src[h] += 1
                    gen_to_accept.add(k - g)
        if o.closing:
            wn = len(window_records)
            assert k == (wn + 1) * w - 1 and o.pos == w - 1 and o.i_idx == w - 1, f"closing at trace cycle {k}"
            kinds = production_kinds(n, wn)
            shares = production_shares(n, wn)
            assert o.evidence == kinds, (
                f"window {wn}: evidence {o.evidence}, designed {kinds} (B_close {o.b_close}, S_close {o.s_close})"
            )
            assert o.new_cls == exp_cls[wn], f"window {wn}: classes {o.old_cls} -> {o.new_cls}, expected {exp_cls[wn]}"
            boundary = wn + 1
            if boundary % 2 == 1:
                assert o.out_valid and not o.out_ready, f"boundary {boundary}: an offer must be held across the closing edge"
            else:
                assert o.fire, f"boundary {boundary}: the closing edge must carry a fire"
            rec = {
                "window": wn,
                "closing_trace_cycle": k,
                "closing_non_reset_edge": k + 1,
                "s_close": o.s_close,
                "b_close": list(o.b_close),
                "realized_share": [round(b / o.s_close, 6) if o.s_close else None for b in o.b_close],
                "designed_share": [round(s, 6) for s in shares],
                "thresholds_share": {"up_below": round(0.3 / n, 6), "down_above": round(1.0 / n, 6)},
                "evidence": list(o.evidence),
                "old_classes": list(o.old_cls),
                "new_classes": list(o.new_cls),
                "transitions": [f"{a}/{e}->{b}" for a, e, b in zip(o.old_cls, o.evidence, o.new_cls)],
                "effective_changes": [h for h in range(n) if tb.interp.effective[o.old_cls[h]] != tb.interp.effective[o.new_cls[h]]],
                "closing_fire": bool(o.fire),
                "closing_fire_source": o.out_source if o.fire else None,
                "closing_fire_ctx": list(o.charged) if o.fire else None,
                "held_across_closing": bool(o.out_valid and not o.out_ready),
                "held_source": o.out_source if (o.out_valid and not o.out_ready) else None,
                "generated_per_source": list(traffic.generated_per_window[wn]),
                "wall_s_since_start": round(time.time() - t_meas, 1),
            }
            window_records.append(rec)
            dut._log.info("window %d closed at edge %d: S_close=%d evidence=%s classes %s -> %s", wn, k + 1,
                          o.s_close, o.evidence, o.old_cls, o.new_cls)  # fmt: skip
        if (k + 1) % TRIM_EVERY == 0:
            tb.trim_model_logs()
        if (k + 1) % LOG_EVERY == 0:
            now = time.time()
            dut._log.info("production cycle %d/%d: %.0f cycles/s (avg %.0f) rss=%s KiB fires=%d backlog=%d",
                          k + 1, cycles, (k + 1 - k_last) / (now - t_last), (k + 1) / (now - t_meas),
                          _status_kib("VmRSS"), tb.cov.fires, prod.backlog())  # fmt: skip
            t_last, k_last = now, k + 1
    meas_wall = time.time() - t_meas
    assert tb.cycle_no == meas_end
    assert len(window_records) == windows, f"{len(window_records)} windows closed, {windows} expected"
    if windows:
        assert tb.pin_cls == exp_cls[-1]
    tb.trim_model_logs()

    # Measurement snapshot (frozen at the boundary).
    cov_meas = tb.cov.as_dict()
    outstanding_at_meas_end = tb.outstanding()
    backlog = prod.backlog()
    boundary = tb.in_hold.obligations()
    offers_now = prod.offers()
    boundary_offers = {}
    for h, d in boundary.items():
        assert h in offers_now and offers_now[h][1] == d, f"boundary offer of source {h} is not its producer head"
        boundary_offers[h] = offers_now[h]

    def on_drain_cycle(o) -> None:
        for h in range(n):
            if not (o.in_valid >> h) & 1:
                continue
            assert h in boundary_offers and drain_pushes_src[h] == 0, f"drain offered source {h} without obligation"
            if (o.push >> h) & 1:
                g, d = prod.accept(h, o.cycle - base)
                assert (g, d) == boundary_offers[h] and d == o.in_desc[h]
                drain_pushes_src[h] += 1
                gen_to_accept_drain.add(o.cycle - base - g)

    drain_start = tb.cycle_no
    await tb.drain(on_cycle=on_drain_cycle)
    await tb.finish()
    drain_cycles = tb.cycle_no - drain_start

    fires_m, pushes_m, pushes_d = sum(fires_meas), sum(pushes_src), sum(drain_pushes_src)
    assert prod.generated == traffic.generated == pushes_m + backlog
    assert fires_m + sum(fires_drain) == pushes_m and waits_drain.count == outstanding_at_meas_end
    assert sum(fires_drain_only) == pushes_d == len(boundary_offers) and fires_drain_only == drain_pushes_src
    assert tb.resp.issued == tb.resp.completed == fires_m + sum(fires_drain) + pushes_d
    assert tb.outstanding() == 0 and tb.dropped_by_reset == 0
    completed = StreamStats()
    for st in (waits_meas, waits_drain):
        for v, c in st.hist.items():
            completed.hist[v] = completed.hist.get(v, 0) + c
            completed.count += c
            completed.total += v * c
    wall = time.time() - t0
    result = {
        "schema": "cxl-m6-fai-alg2-production-v1" if alg2 else SCHEMA,
        "policy": tb.interp.name,
        "policy_param": tb.policy,
        "fai_w": w,
        "fai_w_source": "RTL default (not passed with -G); 23-bit idx/B/S checked on the DUT",
        "seed": seed,
        "n_src": n,
        "requested_cycles": cycles,
        "measured_cycles": cycles,
        "real_non_reset_cycles_simulated": tb.cycle_no - base,
        "infra_smoke": smoke,
        "production_evidence": (not smoke) and windows >= MIN_WINDOWS,
        "method": "real simulated edges of the Verilated RTL; no time skip, no internal state deposit or "
        "preload, no smaller window; every cycle checked by oracle + independent pin/history layers",
        "trace": {**traffic.config(), "sha256": traffic.sha256, "generated": traffic.generated,
                  "generated_per_source": traffic.generated_per_source, "ready_cycles": traffic.ready_cycles,
                  "random_stalls": traffic.random_stalls},  # fmt: skip
        "windows_closed_measurement": cov_meas["windows_closed"],
        "windows": window_records,
        "expected_class_sequence": exp_cls,
        "transitions_reached": cov_meas["transitions_reached"],
        "states_reached": cov_meas["states_reached"],
        "fai_measurement": fai_summary(cov_meas, w),
        "accepted_transfer_rate": fires_m / cycles,
        "fires_measurement": fires_m,
        "fires_drain": sum(fires_drain),
        "input_push_count": pushes_m,
        "input_push_rate": pushes_m / cycles,
        "per_source_service_measurement": fires_meas,
        "per_source_pushes": pushes_src,
        "wait_acceptance_to_fire": {
            "all_completed": completed.as_dict(),
            "fired_in_measurement": waits_meas.as_dict(),
            "drain_completed": waits_drain.as_dict(),
            "censored_at_measurement_end": outstanding_at_meas_end,
            "outstanding_after_drain": tb.outstanding(),
        },
        "generation_to_acceptance": gen_to_accept.as_dict(),
        "generated": prod.generated,
        "generated_but_unaccepted": backlog,
        "max_producer_backlog": prod.max_backlog,
        "drain_only": {
            "boundary_held_offers": len(boundary_offers),
            "pushes": pushes_d,
            "per_source_pushes": drain_pushes_src,
            "fires": sum(fires_drain_only),
            "wait_acceptance_to_fire": waits_drain_only.as_dict(),
            "generation_to_acceptance": gen_to_accept_drain.as_dict(),
        },
        "input_hold_checks": tb.in_hold.checked,
        "responses": {"issued": tb.resp.issued, "completed": tb.resp.completed, "reordered": tb.resp.reordered,
                      "max_outstanding": tb.resp.max_outstanding},  # fmt: skip
        "outstanding_after_drain": tb.outstanding(),
        "phases": {"initial_reset_cycles_not_measured": 3, "measured_non_reset_cycles": cycles,
                   "drain_cycles_total": drain_cycles},  # fmt: skip
        "throughput": {
            "measurement_wall_s": round(meas_wall, 3),
            "cycles_per_s": round(cycles / meas_wall, 1) if meas_wall > 0 else None,
            "peak_rss_kib": _status_kib("VmHWM"),
        },
        "coverage_measurement": cov_meas,
        "coverage_total": tb.cov.as_dict(),
        "wall_time_s": round(wall, 3),
    }
    write_json(metrics_file, result)
    dut._log.info("production done: %d windows, %.0f cycles/s, peak RSS %s KiB, transitions %s", windows,
                  cycles / meas_wall, _status_kib("VmHWM"), cov_meas["transitions_reached"])  # fmt: skip
    assert result["outstanding_after_drain"] == 0
    if windows:
        assert cov_meas["effective_changes"] > 0 and cov_meas["closing_fire"] > 0 and cov_meas["held_across_closing"] > 0
