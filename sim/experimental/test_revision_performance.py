"""Real RTL edges, independent policy oracle, and separate pin/history checks."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import cocotb
from cocotb.triggers import Timer

from revision_traffic import Metrics, ROOT, StreamProducers, Traffic

sys.path.insert(0, str(ROOT / "refc"))
from cxl_model import FaiAlg2SwitchModel, FaiMainSwitchModel, FcfsSwitchModel, RrSwitchModel

CLASS_CODES = dict(H=0, L=1, B_H=2, B_L=3, STABLE_HIGH=0, STABLE_LOW=1,
                   BUFFER_P_HIGH=2, BUFFER_P_LOW=3)


def model_for(job):
    """Accepted independent models remain the oracles for all default policies."""
    p, n, d = job["policy"], job["n_src"], job["depth"]
    if p == "FCFS":
        return FcfsSwitchModel(n, depth=d)
    if p in ("RR", "RR1", "RR10"):
        return RrSwitchModel(n, depth=d, quantum=job["rr_quantum"])
    if p == "ALG2":
        return FaiAlg2SwitchModel(n, depth=d, window=job["window"])
    if p == "MAIN" and job["high_quota"] == 10:
        return FaiMainSwitchModel(n, depth=d, window=job["window"])
    # Native owns this module. No substitute oracle or model-only RTL result.
    from cxl_model.revision_baselines import BlissSwitchModel, FaiVariantSwitchModel
    if p == "BLISS":
        return BlissSwitchModel(n, depth=d)
    if p in ("MAIN", "MAIN1W"):
        return FaiVariantSwitchModel(n, depth=d, window=job["window"],
                                     high_quota=job["high_quota"], main_1w=p == "MAIN1W")
    raise ValueError(f"unsupported policy {p}")


def peak_rss():
    path = Path("/proc/self/status")
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    return None


@cocotb.test()
async def revision_performance(dut):
    job = json.loads(os.environ["CXL_REVISION_JOB"])
    params = json.loads(os.environ["CXL_REVISION_PARAMS"])
    assert all(int(os.environ[f"CXL_PARAM_{k}"]) == v for k, v in params.items())
    traffic = Traffic(job, cold=json.loads(os.environ["CXL_REVISION_COLD"]))
    metrics, producers, model = Metrics(traffic), StreamProducers(traffic.n), model_for(job)
    windows, counts, n = [], [0]*traffic.n, traffic.n
    cold_pins = hashlib.sha256(b"cxl-revision-training-pins-v1\n")
    t0 = time.monotonic()
    output = Path("revision_performance.json")
    failure_path = Path("revision_failure.json")
    k = -1
    blocked = {}
    input_hold_checks = 0
    fai = None
    if params["POLICY"] in (2, 3):
        variant = params["POLICY"] == 2 and (params["HIGH_QUOTA"] != 10 or params["MAIN_1W"])
        scope = ("gen_policy_fai_variant" if variant else
                 "gen_policy_fai_main" if params["POLICY"] == 2 else "gen_policy_fai_alg2")
        fai = getattr(dut, scope).u_fai_sched

    async def edge(k, events, ready, reset=False):
        nonlocal counts, blocked, input_hold_checks
        producers.generate(k, events)
        offers = producers.offers()
        valid = [h in offers for h in range(n)]
        desc = [offers[h][1] if h in offers else 0 for h in range(n)]
        dut.clk.value = 0
        dut.rst_n.value = int(not reset)
        dut.i_in_valid.value = sum(int(v) << h for h, v in enumerate(valid))
        dut.i_in_desc.value = sum(d << (105*h) for h, d in enumerate(desc))
        dut.i_out_ready.value = ready
        await Timer(4, unit="ns")
        seen_ready = int(dut.o_in_ready.value)
        seen_valid = int(dut.o_out_valid.value)
        source = int(dut.o_out_source.value) if seen_valid else None
        out_desc = int(dut.o_out_desc.value) if seen_valid else None
        oracle = model.view(out_ready=bool(ready), rst_n=not reset)
        assert seen_ready == sum(int(v) << h for h, v in enumerate(oracle.in_ready)), (k, "model readiness")
        assert seen_valid == int(oracle.out_valid), (k, "model valid")
        if seen_valid:
            assert (source, out_desc) == (oracle.out_source, oracle.out_desc), (k, "model selection/105-bit descriptor")
            assert int(dut.grant_ctx.value) == oracle.grant_ctx, (k, "held grant quota context")
        if not reset:
            assert int(dut.grant_held.value) == int(oracle.held), (k, "held controller")
            if fai is not None:
                assert int(fai.cls_q.value) == sum(CLASS_CODES[c] << (2*h) for h, c in enumerate(model.classes())), (
                    k, "actual FAI classes")
                pos, b, total = model.window_state()
                assert list(b) == counts and total == sum(counts), (k, "independent pin fire accounting")
                assert int(fai.idx_q.value) == pos == k % job["window"], (k, "actual window index")
                assert int(fai.b_q.value) == sum(v << (model.count_bits*h) for h, v in enumerate(counts)), (k, "actual B")
                assert int(fai.s_q.value) == sum(counts), (k, "actual S")
                visit = model.visit_state()
                assert int(fai.turn_q.value) == int(visit.cls == "Low"), (k, "actual visit class")
                assert int(fai.used_q.value) == visit.fires, (k, "actual visit quota")
            elif params["POLICY"] == 4:
                bl, last, streak, since = model.bliss_state()
                u = dut.gen_policy_bliss.u_bliss_sched
                assert int(u.bl_q.value) == sum(int(v) << h for h, v in enumerate(bl)), (k, "actual blacklist")
                assert int(u.last_valid_q.value) == int(last is not None), (k, "actual streak valid")
                if last is not None:
                    assert int(u.last_src_q.value) == last, (k, "actual streak source")
                assert int(u.streak_q.value) == streak and int(u.clr_q.value) == since, (k, "actual streak/clear")
        assert int(dut.i_in_valid.value) == sum(int(v) << h for h, v in enumerate(valid))
        assert int(dut.i_in_desc.value) == sum(d << (105*h) for h, d in enumerate(desc))
        if reset:
            blocked = {}
        else:
            for h, d in blocked.items():
                assert valid[h] and desc[h] == d, (k, "producer 105-bit input hold")
                input_hold_checks += 1
            blocked = {h: desc[h] for h in range(n) if valid[h] and not (seen_ready >> h & 1)}
        if not reset:
            metrics.observe(k, events, producers, ready, seen_ready, seen_valid, source, out_desc)
            if k < traffic.training:
                cold_pins.update(seen_ready.to_bytes(2, "big")+bytes([seen_valid, ready]))
                cold_pins.update(sum(int(v) << h for h, v in enumerate(valid)).to_bytes(2, "big"))
                for d in desc:
                    cold_pins.update(d.to_bytes(14, "big"))
                cold_pins.update(bytes([source if seen_valid else 0]))
                cold_pins.update((out_desc or 0).to_bytes(14, "big"))
            if seen_valid and ready:
                counts[source] += 1
        await Timer(1, unit="ns")
        dut.clk.value = 1
        model.commit(out_ready=bool(ready), in_valid=valid, in_desc=desc, rst_n=not reset)
        await Timer(5, unit="ns")
        if not reset and (k+1) % job["window"] == 0:
            total = sum(counts)
            evidence = ["S0" if not total else "UP" if 10*n*b < 3*total else
                        "DOWN" if n*b > total else "KEEP" for b in counts]
            windows.append(dict(closing_cycle=k, counts=counts, total=total, evidence=evidence,
                                classes=list(model.classes()) if hasattr(model, "classes") else None))
            counts = [0]*n
        if not reset and (k+1) % 4096 == 0:
            for name in ("turn_log", "window_log", "visit_log"):
                if hasattr(model, name):
                    getattr(model, name).clear()
        if not reset and (k+1) % 250000 == 0:
            dut._log.info("revision %s cycle=%d backlog=%d peakRSS=%s KiB",
                          job["policy"], k+1, producers.backlog(), peak_rss())

    try:
        await edge(-1, [], 0, reset=True)
        await edge(-1, [], 0, reset=True)
        for k in range(traffic.end):
            events, ready = traffic.step(k)
            await edge(k, events, ready)
            if k+1 in traffic.bounds:
                metrics.guard(k+1, producers)
        pending = producers.backlog()+sum(len(q) for q in metrics.fifo)
        drain_bound = 2*pending+128
        k = traffic.end
        while producers.backlog() or any(metrics.fifo):
            assert k-traffic.end < drain_bound, "complete generated-population drain timeout"
            await edge(k, [], 1)
            k += 1
        await edge(k, [], 1)
        k += 1
        metrics.complete(producers)
        result = dict(schema="cxl-revision-performance-v1", evidence_kind="RTL", status="PASS",
                      job=job, params=params, cold=traffic.cold, cold_cohort=traffic.cold_cohort,
                      production_evidence=job["window"] == 5_000_000,
                      sensitivity_evidence=job["window"] == 256,
                      trace_config=traffic.config, trace_sha256=traffic.sha256,
                      generated_per_source=traffic.generated, ready_cycles=traffic.ready_count,
                      training_cycles=traffic.training, active_cycles=traffic.end,
                      training_pin_sha256=cold_pins.hexdigest(), windows=windows,
                      real_non_reset_cycles=k, drain_cycles=k-traffic.end, drain_bound=drain_bound,
                      outstanding_after_drain=0, producer_backlog_after_drain=0,
                      sparse_guard_complete=True, generated=producers.generated, accepted=producers.accepted,
                      producer_peak_backlog=producers.max_backlog,
                      input_hold_checks=input_hold_checks,
                      fired=sum(sum(r["fired"]) for r in metrics.rows.values()),
                      metrics=metrics.as_dict(), peak_rss_kib=peak_rss(), wall_s=time.monotonic()-t0,
                      method="real RTL edges; independent oracle and pin-history checks every cycle",
                      latency_convention="exact generation cohorts, nearest-rank direct histograms; cycles",
                      limitations="W256 sensitivity is not W5M training; descriptor latency is not slowdown or WCET")
        output.write_text(json.dumps(result, indent=2)+"\n")
        # Include metrics serialization in the process high-water measurement.
        result["peak_rss_kib"] = peak_rss()
        output.write_text(json.dumps(result, indent=2)+"\n")
    except BaseException as exc:
        failure_path.write_text(json.dumps(dict(job=job, cycle=k, error=repr(exc),
                                               trace_sha256=traffic.sha256, peak_rss_kib=peak_rss(),
                                               wall_s=time.monotonic()-t0), indent=2)+"\n")
        raise
