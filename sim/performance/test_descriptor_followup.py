"""Real Verilator follow-up, using the existing strict oracle and pin-rule harnesses."""
import os
from pathlib import Path
import sys
import time

import cocotb

from followup import Metrics, POLICIES, SCHEMA, StreamProducers, Traffic, check_result, check_drain_budget
from switch_fcfs_tb import SwitchFcfsTb, param_from_env, run_seed, write_json
from switch_rr_tb import SwitchRrTb
from switch_fai_tb import SwitchFaiTb


def trim_logs(tb):
    # These append-only oracle diagnostics never participate in scheduling decisions.
    for name in ("turn_log", "visit_log", "window_log"):
        if hasattr(tb.model, name):
            getattr(tb.model, name).clear()
    assert not tb.resp._seen and not tb.resp.responses


def rss_kib():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])


@cocotb.test()
async def descriptor_followup(dut):
    case = os.environ["CXL_FOLLOWUP_CASE"]
    warmup, measured = (int(os.environ[k]) for k in ("CXL_FOLLOWUP_WARMUP", "CXL_FOLLOWUP_MEASURE"))
    infra = os.environ["CXL_FOLLOWUP_INFRA"] == "1"
    low = tuple(map(int, os.environ.get("CXL_FOLLOWUP_LOW_SOURCES", "0").split(",")))
    high = tuple(h for h in range(4) if h not in low)
    trained = case in ("trained", "placement")
    window, policy, seed = param_from_env("FAI_W"), param_from_env("POLICY"), run_seed()
    assert param_from_env("N_SRC") == 4 and policy in (0, 1, 2)
    if case == "placement":
        assert not infra and (seed, window, warmup, measured) == (509,256,512,240)
        assert warmup+measured < 3*window
    elif not infra:
        assert window == 5_000_000
        assert (warmup, measured) == ((10_000_000, 100_000) if case == "trained" else
                                      (0, 1024) if case == "finite" else (10_000, 100_000))
    traffic = Traffic(case, seed, warmup, measured, window, low)
    producers, metrics = StreamProducers(4), Metrics(warmup, measured)
    tb = (SwitchFcfsTb, SwitchRrTb, SwitchFaiTb)[policy](dut, "descriptor-followup", unique_tags=False)
    await tb.start()
    base = tb.cycle_no
    wall_start = time.monotonic()
    training_windows, window_counts = [], [0]*4
    expected_next_classes = None
    contention = dict(fill_cycles=128, post_fill_cycles=0, both_classes_eligible_cycles=0,
                      complete_visits={"High": 0, "Low": 0},
                      partial_visits={"High": [], "Low": []},
                      left_boundary_visit=None, right_boundary_visit=None,
                      per_source_fires_after_fill=[0]*4)
    visit_class, visit_fires = None, 0

    async def cycle(k, events, ready):
        nonlocal expected_next_classes, window_counts, visit_class, visit_fires
        if events:
            producers.generate(k, events)
        metrics.generate(k, events)
        offers = producers.offers()
        before = [len(q) for q in metrics.fifo]
        o = await tb.cycle(push={h:d for h,(_,d) in offers.items()}, out_ready=ready,
                           meta={h:g for h,(g,_) in offers.items()})
        assert o.cycle - base == k
        if expected_next_classes is not None and policy == 2:
            assert o.i_cls == expected_next_classes
            expected_next_classes = None
        if k < warmup and trained:
            if o.fire:
                window_counts[o.out_source] += 1
            if (k+1) % window == 0:
                total = sum(window_counts)
                evidence = ["UP" if 40*b < 3*total else "DOWN" if 4*b > total else "KEEP"
                            for b in window_counts]
                assert evidence == ["DOWN" if h in low else "KEEP" for h in range(4)]
                if case == "placement":
                    assert window_counts == traffic.training_counts(window)
                    assert sum(before) == o.fire and not o.push and not producers.backlog()
                classes = [("B_H" if len(training_windows) == 0 else "L") if h in low else "H" for h in range(4)]
                if policy == 2:
                    assert o.closing and o.b_close == window_counts and o.s_close == total
                    assert o.new_cls == classes
                    expected_next_classes = classes
                training_windows.append(dict(closing_trace_cycle=k, counts=list(window_counts),
                                             total=total, evidence=evidence,
                                             classes=classes if policy == 2 else None))
                window_counts = [0]*4
        if trained and policy == 2 and warmup <= k < warmup+measured:
            rel = k-warmup
            if case == "placement":
                assert not o.closing and o.i_cls == ["L" if h in low else "H" for h in range(4)]
            if rel == 0:
                contention["left_boundary_visit"] = dict(cls="Low" if o.i_turn else "High", used=o.i_used)
            if case == "placement" and rel == contention["fill_cycles"]:
                contention["post_fill_left_boundary_visit"] = dict(cls="Low" if o.i_turn else "High", used=o.i_used)
            if rel >= contention["fill_cycles"]:
                contention["post_fill_cycles"] += 1
                both = any(before[h] for h in low) and any(before[h] for h in high)
                # Reduced-W pilots may reclassify during measurement; production may not.
                if not infra:
                    assert o.i_cls == ["L" if h in low else "H" for h in range(4)] and both
                contention["both_classes_eligible_cycles"] += int(both)
                if o.fire:
                    contention["per_source_fires_after_fill"][o.out_source] += 1
            if o.fire:
                cls, used = o.charged  # independent pin-history context, already checked against nets
                if cls != visit_class:
                    if visit_class is not None and visit_fires:
                        contention["partial_visits"][visit_class].append(visit_fires)
                    visit_class, visit_fires = cls, 0
                visit_fires += 1
                if o.visit_event == "expired":
                    if case == "placement" and rel >= contention["fill_cycles"]:
                        assert visit_fires == 10, "incomplete continuously backlogged class visit"
                    if visit_fires == 10:
                        contention["complete_visits"][cls] += 1
                    else:
                        contention["partial_visits"][cls].append(visit_fires)
                    visit_class, visit_fires = None, 0
                elif o.visit_event == "emptied":
                    if case == "placement":
                        assert rel < contention["fill_cycles"]
                    contention["partial_visits"][cls].append(visit_fires)
                    visit_class, visit_fires = None, 0
            if rel == measured-1:
                contention["right_boundary_visit"] = dict(cls=visit_class, measured_fires=visit_fires)
        metrics.observe(k, o, producers)
        if (k+1) % 4096 == 0:
            trim_logs(tb)
        if (k+1) % 250_000 == 0:
            dut._log.info("followup %s %s cycle=%d %.0f cycles/s pending=%d RSSpeak=%s KiB",
                          case, POLICIES[policy], k+1, (k+1)/(time.monotonic()-wall_start),
                          producers.backlog(), rss_kib())
        return o

    for k in range(traffic.end):
        if k == warmup:
            metrics.snapshot("measurement_start", k, producers)
        events, ready = traffic.step(k)
        await cycle(k, events, ready)
    metrics.snapshot("measurement_end", traffic.end, producers)
    active_wall = time.monotonic()-wall_start
    # Drain continues the same absolute-cycle ready trace, while generation is permanently stopped.
    # Worst ready gap is one cycle; 2 slots/request plus response slack bounds this workload.
    remaining = producers.backlog() + sum(len(q) for q in metrics.fifo)
    drain_bound = 2*remaining + 128
    k = traffic.end
    while producers.backlog() or any(metrics.fifo) or tb.resp.outstanding:
        check_drain_budget(k-traffic.end, drain_bound)
        await cycle(k, [], traffic.ready(k))
        k += 1
    await cycle(k, [], traffic.ready(k))
    k += 1
    trim_logs(tb)
    tb.assert_conserved()
    tb.resp.assert_all_complete()
    metrics.assert_complete(producers, tb.resp.issued, tb.resp.completed)
    assert tb.outstanding() == 0 and not tb.in_hold.pending
    metrics.snapshot("drain_end", k, producers)
    result = dict(schema=SCHEMA, case=case, seed=seed, n_src=4, policy=POLICIES[policy],
                  policy_param=policy, window=window, warmup_cycles=warmup, measurement_cycles=measured,
                  infrastructure_only=infra, production_evidence=(case == "trained" and not infra),
                  trace_config=traffic.config, trace_sha256=traffic.sha256,
                  trace_generated_per_source=traffic.generated, trace_ready_cycles=traffic.ready_count,
                  drain_cycles=k-traffic.end, drain_bound=drain_bound,
                  real_non_reset_cycles=k, training_windows=training_windows, contention=contention,
                  outstanding_after_drain=tb.outstanding(), generated_unaccepted_after_drain=producers.backlog(),
                  responses=dict(issued=tb.resp.issued, completed=tb.resp.completed),
                  metrics=metrics.as_dict(), input_hold_checks=tb.in_hold.checked,
                  coverage=tb.cov.as_dict(), active_wall_s=active_wall,
                  total_wall_s=time.monotonic()-wall_start, peak_rss_kib=rss_kib(),
                  method="real RTL edges; no state deposit/time skip; all performance data from pin history",
                  limitations="finite overload/trained transient; observed maxima are not WCET/starvation guarantees",
                  drain_convention="stop generation, keep every pending producer active; deterministic absolute ready trace; complete all responses",
                  latency_convention="exact per-request stage and direct histograms by generation and acceptance cohorts; never sum P99s",
                  backlog_sampling="pre-edge after current-cycle generation; occupancy before current-edge push/pop",
                  gap_convention="inclusive first eligible slot; inter-service slots exclude preceding fire; phase boundary censors both sides")
    if case == "placement":
        result.update(low_sources=list(low), sensitivity_evidence=True)
        if policy == 2:
            measured_counts = result["metrics"]["phases"]["measurement"]["fired"]
            for label, counts in (("measurement", measured_counts), ("after_fill", contention["per_source_fires_after_fill"])):
                contention["class_fires_"+label] = {name:sum(counts[h] for h in group)
                                                   for name,group in (("Low",low),("High",high))}
                contention["class_share_"+label] = {name:n/sum(counts)
                                                   for name,n in contention["class_fires_"+label].items()}
    check_result(result, {}, traffic.sha256)
    write_json("descriptor_followup_metrics.json", result)
