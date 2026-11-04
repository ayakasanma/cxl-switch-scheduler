"""Passive performance collection around native CGOF cycle/pin/oracle checks."""
import hashlib
import json
import os
from pathlib import Path
import time

import cocotb

from revision_traffic import Metrics, StreamProducers, Traffic
from test_cgof_sched import Harness, P, POLICY_NAME


def peak_rss():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    raise RuntimeError("simulator high-water RSS unavailable")


async def sampled_cycle(harness, metrics, producers, k, events, ready):
    """Feed passive metrics the native return sample, never post-edge RTL pins."""
    producers.generate(k, events)
    push = {h: value[1] for h, value in producers.offers().items()}
    sample = await harness.cycle(push, ready=ready)
    metrics.observe(k, events, producers, ready, sample["in_ready"], sample["out_valid"],
                    sample["out_source"], sample["out_desc"])
    return sample, push


@cocotb.test()
async def cgof_performance(dut):
    job = json.loads(os.environ["CXL_REVISION_JOB"])
    policy = os.environ["CXL_CGOF_SELECTED_POLICY"]
    params = json.loads(os.environ["CXL_CGOF_PARAMS"])
    assert params == P and policy == POLICY_NAME
    assert all(int(os.environ[f"CXL_PARAM_{k}"]) == v for k, v in params.items())
    assert job["policy"] == "INSIGHT_WINNER"
    traffic = Traffic(job)
    metrics, producers = Metrics(traffic), StreamProducers(traffic.n)
    harness = Harness(dut, "cgof-performance", job["seed"])
    windows, counts, blocked = [], [0]*traffic.n, {}
    training_pins = hashlib.sha256(b"cxl-revision-training-pins-v1\n")
    input_hold_checks, k = 0, -1
    t0 = time.monotonic()

    async def edge(k, events, ready):
        nonlocal blocked, input_hold_checks, counts
        # Native owns both the RTL/oracle comparison and all rising-edge updates.
        o, push = await sampled_cycle(harness, metrics, producers, k, events, ready)
        for h, desc in blocked.items():
            assert push.get(h) == desc, (k, "producer input hold")
            input_hold_checks += 1
        blocked = {h: desc for h, desc in push.items() if not (o["in_ready"] >> h & 1)}
        if k < traffic.training:
            training_pins.update(o["in_ready"].to_bytes(2, "big")+bytes([o["out_valid"], ready]))
            training_pins.update(sum(1 << h for h in push).to_bytes(2, "big"))
            for h in range(traffic.n):
                training_pins.update(push.get(h, 0).to_bytes(14, "big"))
            training_pins.update(bytes([o["out_source"] if o["out_valid"] else 0]))
            training_pins.update((o["out_desc"] or 0).to_bytes(14, "big"))
        if o["fire"]:
            counts[o["out_source"]] += 1
        if (k+1) % job["window"] == 0:
            total, n = sum(counts), traffic.n
            evidence = ["S0" if not total else "UP" if 10*n*b < 3*total else
                        "DOWN" if n*b > total else "KEEP" for b in counts]
            windows.append(dict(closing_cycle=k, counts=counts, total=total, evidence=evidence,
                                classes=list(harness.model.classes())))
            counts = [0]*traffic.n
        if (k+1) % 4096 == 0:
            for name in ("window_log", "turn_log", "visit_log"):
                if hasattr(harness.model, name):
                    getattr(harness.model, name).clear()
        if (k+1) % 250000 == 0:
            dut._log.info("revision %s cycle=%d backlog=%d peakRSS=%d KiB wall_s=%.6f",
                          policy, k+1, producers.backlog(), peak_rss(), time.monotonic()-t0)

    try:
        await harness.start()
        for k in range(traffic.end):
            events, ready = traffic.step(k)
            await edge(k, events, ready)
            if k+1 in traffic.bounds:
                metrics.guard(k+1, producers)
        pending = producers.backlog()+sum(len(q) for q in metrics.fifo)
        drain_bound, k = 2*pending+128, traffic.end
        while producers.backlog() or any(metrics.fifo):
            assert k-traffic.end < drain_bound, "generated-population drain timeout"
            await edge(k, [], 1)
            k += 1
        await edge(k, [], 1)
        k += 1
        metrics.complete(producers)
        assert not any(harness.sb) and not blocked
        result = dict(schema="cxl-revision-cgof-performance-v1", evidence_kind="RTL", status="PASS",
                      job=job, selected_policy=policy, params=params, cold=False, cold_cohort=None,
                      matrix_contribution=int(policy == "CGOF(2:1)" and job["group"] in (
                          "insight-confirmation", "insight-robustness")),
                      production_evidence=job["window"] == 5_000_000,
                      sensitivity_evidence=job["window"] == 256,
                      trace_config=traffic.config, trace_sha256=traffic.sha256,
                      generated_per_source=traffic.generated, ready_cycles=traffic.ready_count,
                      training_cycles=traffic.training, active_cycles=traffic.end,
                      training_pin_sha256=training_pins.hexdigest(), windows=windows,
                      real_non_reset_cycles=k, drain_cycles=k-traffic.end, drain_bound=drain_bound,
                      outstanding_after_drain=0, producer_backlog_after_drain=0,
                      sparse_guard_complete=True, generated=producers.generated, accepted=producers.accepted,
                      producer_peak_backlog=producers.max_backlog, input_hold_checks=input_hold_checks,
                      fired=sum(sum(r["fired"]) for r in metrics.rows.values()), metrics=metrics.as_dict(),
                      native_coverage=harness.cov, native_cgof=harness.cgof,
                      wall_s=time.monotonic()-t0, peak_rss_kib=peak_rss(),
                      method="native Harness.cycle pre-edge pins; passive Traffic/Metrics/StreamProducers",
                      limitations="descriptor slice only; W256 sensitivity is not W5M training; no application slowdown")
        output = Path("cgof_performance.json")
        output.write_text(json.dumps(result, indent=2)+"\n")
        result["peak_rss_kib"] = peak_rss()
        output.write_text(json.dumps(result, indent=2)+"\n")
    except BaseException as exc:
        Path("cgof_performance_failure.json").write_text(json.dumps(dict(
            job=job, selected_policy=policy, cycle=k, error=repr(exc),
            trace_sha256=traffic.sha256, wall_s=time.monotonic()-t0,
            peak_rss_kib=peak_rss()), indent=2)+"\n")
        raise
