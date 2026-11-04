"""Real-edge experiment; existing independent per-policy TBs verify every cycle."""
import hashlib
import os
from pathlib import Path
import time

import cocotb

from hog_sparse import Metrics, POLICIES, SCHEMA, StreamProducers, Traffic, check_result
from switch_fcfs_tb import SwitchFcfsTb, param_from_env, run_seed, write_json
from switch_rr_tb import SwitchRrTb
from switch_fai_tb import SwitchFaiTb


def trim_logs(tb):
    for name in ("turn_log","visit_log","window_log"):
        if hasattr(tb.model,name):
            getattr(tb.model,name).clear()
    assert not tb.resp._seen and not tb.resp.responses


def rss_kib():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])


@cocotb.test()
async def hog_sparse(dut):
    policy, window, seed = param_from_env("POLICY"), param_from_env("FAI_W"), run_seed()
    params = {key:param_from_env(key) for key in ("N_SRC","DEPTH","DESC_W","TS_W","RR_QUANTUM","FAI_W","POLICY")}
    assert params == dict(N_SRC=4,DEPTH=16,DESC_W=105,TS_W=32,RR_QUANTUM=10,FAI_W=window,POLICY=policy)
    assert os.environ["CXL_HOG_SPARSE_SCOPE"] == ("pilot" if window == 256 else "main")
    traffic, metrics, producers = Traffic(seed,window), Metrics(window), StreamProducers(4)
    tb = (SwitchFcfsTb,SwitchRrTb,SwitchFaiTb)[policy](dut,"hog-sparse",unique_tags=False)
    await tb.start()
    assert tb.resp.unique_run is False and tb.resp.keep_log is False
    base = tb.cycle_no
    wall_start = time.monotonic()
    windows, counts = [], [0]*4
    cold = hashlib.sha256(b"cxl-hog-sparse-cold-pins-v1\n")
    cold_cycles = 0
    next_classes = None
    snapshots = dict(zip(traffic.bounds,("training_end","A_end","A_guard_end","B_end","B_guard_end")))

    async def cycle(k,events):
        nonlocal counts, cold_cycles, next_classes
        producers.generate(k,events)
        metrics.generate(k,events)
        offers = producers.offers()
        o = await tb.cycle(push={h:d for h,(_,d) in offers.items()},out_ready=1,
                           meta={h:g for h,(g,_) in offers.items()})
        assert o.cycle-base == k
        if k < traffic.training:
            # Only observed interface values enter this streaming equality control.
            cold.update(bytes([o.in_valid,o.in_ready,o.push,o.out_valid,o.out_ready]))
            for d in o.in_desc:
                cold.update(d.to_bytes(14,"big"))
            cold.update(bytes([o.out_source if o.out_valid else 0]))
            cold.update((o.out_desc if o.out_valid else 0).to_bytes(14,"big"))
            cold_cycles += 1
        if policy == 2:
            if next_classes is not None:
                assert o.i_cls == next_classes, "next-cycle class activation"
                next_classes = None
            if k < traffic.training:
                assert all(c in ("H","B_H") for c in o.i_cls), "cold effective classes diverged"
            elif window == 5_000_000 and k < traffic.end:
                assert o.i_cls == ["L","H","H","H"], "production measured classes changed"
        if o.fire:
            counts[o.out_source] += 1
        if (k+1) % window == 0:
            total = sum(counts)
            evidence = ["S0" if not total else "UP" if 40*b < 3*total else "DOWN" if 4*b > total else "KEEP" for b in counts]
            if k < traffic.training:
                assert evidence[0] == "DOWN" and all(e != "DOWN" for e in evidence[1:])
            row = dict(closing_trace_cycle=k,counts=list(counts),total=total,evidence=evidence,
                       old_classes=o.i_cls if policy == 2 else None,
                       classes=o.new_cls if policy == 2 else None)
            if policy == 2:
                assert o.closing and o.b_close == counts and o.s_close == total and o.evidence == evidence
                next_classes = o.new_cls
                if k < traffic.training:
                    assert o.new_cls == (["B_H","H","H","H"] if k == window-1 else ["L","H","H","H"])
            windows.append(row)
            counts = [0]*4
        metrics.observe(k,o,producers,events)
        if (k+1) % 4096 == 0:
            trim_logs(tb)
        if k+1 in snapshots:
            name = snapshots[k+1]
            metrics.snapshot(name,k+1,producers)
            if name == "training_end":
                metrics.assert_cohort_complete("cold")
            elif name in ("A_guard_end","B_guard_end"):
                metrics.assert_cohort_complete(name[0])
                assert all(not producers.pending[h] and not metrics.fifo[h] for h in range(1,4)), "incomplete background-on guard"
        if (k+1) % 250000 == 0:
            dut._log.info("hog_sparse %s cycle=%d %.0f cycles/s backlog=%d peakRSS=%s KiB",
                          POLICIES[policy],k+1,(k+1)/(time.monotonic()-wall_start),producers.backlog(),rss_kib())

    for k in range(traffic.end):
        events, ready = traffic.step(k)
        assert ready == 1
        await cycle(k,events)
    active_wall = time.monotonic()-wall_start
    remaining = producers.backlog()+sum(len(q) for q in metrics.fifo)
    # Ready1 and no output bubbles: one edge per queued request, plus bounded response slack.
    drain_bound = 2*remaining+128
    k = traffic.end
    while producers.backlog() or any(metrics.fifo) or tb.resp.outstanding:
        assert k-traffic.end < drain_bound, "all-generated drain timeout"
        await cycle(k,[])
        k += 1
    await cycle(k,[])
    k += 1
    trim_logs(tb)
    tb.assert_conserved()
    tb.resp.assert_all_complete()
    metrics.assert_complete(producers,tb.resp.issued,tb.resp.completed)
    assert tb.outstanding() == 0 and not tb.in_hold.pending
    metrics.snapshot("drain_end",k,producers)
    result = dict(schema=SCHEMA,seed=seed,n_src=4,policy=POLICIES[policy],policy_param=policy,
                  params=params,window=window,training_cycles=traffic.training,active_cycles=traffic.end,
                  sensitivity_evidence=window == 256,production_evidence=window == 5_000_000,infrastructure_only=False,
                  trace_config=traffic.config,trace_sha256=traffic.sha256,
                  trace_generated_per_source=traffic.generated,trace_ready_cycles=traffic.ready_count,
                  cold_pin_sha256=cold.hexdigest(),cold_pin_cycles=cold_cycles,
                  windows=windows,metrics=metrics.as_dict(),heavy_generation_end=traffic.end,sparse_guard_complete=True,
                  drain_cycles=k-traffic.end,drain_bound=drain_bound,drain_pending_at_start=remaining,
                  real_non_reset_cycles=k,outstanding_after_drain=tb.outstanding(),
                  generated_unaccepted_after_drain=producers.backlog(),
                  responses=dict(issued=tb.resp.issued,completed=tb.resp.completed),
                  coverage=tb.cov.as_dict(),input_hold_checks=tb.in_hold.checked,
                  active_wall_s=active_wall,total_wall_s=time.monotonic()-wall_start,peak_rss_kib=rss_kib(),
                  method="real RTL edges; independent TB + model-free pin/history checks every cycle; no state deposit/time skip",
                  latency_convention="complete sparse generation cohorts; exact direct G2F and stage histograms; nearest-rank P99",
                  backlog_sampling="pre-edge after current generation; FIFO pre-edge; snapshot ages at next cycle boundary",
                  heavy_latency="omitted: finite overload; all heavy work retained in counters and complete final drain",
                  limitations="W256 sensitivity is not production; descriptor latency is not application slowdown; maxima not WCET")
    check_result(result,{},traffic.sha256)
    write_json("hog_sparse_metrics.json",result)
