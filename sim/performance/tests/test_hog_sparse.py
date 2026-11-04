"""Hand-derived cohorts and negative controls; no RTL/oracle substitutes."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/"sim"/"performance"),str(ROOT/"sim"/"common"),str(ROOT/"scripts")]
from hog_sparse import (Metrics, PHASES, STAGES, StreamProducers, StreamStats,
                        Timeline, Traffic, check_result, check_stats, stats)
from run_hog_sparse import check_matrix, config


def test_timeline_and_cold_cohort():
    t = Timeline(5_000_000)
    assert t.bounds == (10000000,10100000,10101024,10203424,10204448)
    assert [t.phase(k) for k in (0,9999999,10000000,10099999,10100000,10101024,10203424,10204448)] == ["training","training","A","A","A_guard","B","B_guard","drain"]
    assert [t.cohort(k) for k in (9898975,9898976,9998975,9998976,10000000,10100000,10101024)] == [None,"cold","cold",None,"A",None,"B"]
    assert Timeline(256).cohort(0) is None
    with pytest.raises(AssertionError):
        Timeline(4096)


def test_exact_bursts_and_guard_pressure():
    t = Traffic(509,256)
    counts = {p:[0]*4 for p in PHASES}
    bursts = [[] for _ in range(4)]
    tags = set()
    for k in range(t.end):
        events,ready = t.step(k)
        assert ready == 1 and events[0][0] == 0
        row = counts[t.phase(k)]
        for h,d in events:
            row[h] += 1
            assert 0 <= d < 2**105 and d >> 73 not in tags
            tags.add(d >> 73)
        if t.phase(k) == "B":
            for h in range(1,4):
                n = sum(src == h for src,_ in events)
                assert n in (0,8)
                if n:
                    bursts[h].append(k-t.b_start)
    assert counts["B"] == [102400,800,800,800]
    for p in ("A_guard","B_guard"):
        assert counts[p] == [1024,0,0,0]
    for h in range(1,4):
        assert [k//1024 for k in bursts[h]] == list(range(100))
        assert [k%1024 for k in bursts[h]] == t.offsets[h]
    assert len(tags) == sum(t.generated) and t.ready_count == t.end


def test_rng_independence_and_reproducible_hash():
    a,b,c = (Traffic(509,256) for _ in range(3))
    for k in range(a.end):
        ea,ra = a.step(k)
        eb,rb = b.step(k)
        ec,rc = c.step(k)
        assert ea == eb and ra == rb == rc
        assert [h for h,_ in ea] == [h for h,_ in ec]
        for rng in c.descriptors:
            rng.getrandbits(105)
    assert a.sha256 == b.sha256 and a.sha256 != c.sha256
    assert a.config == b.config and "policy" not in a.config


def test_direct_p99_is_not_sum_of_stage_p99s():
    g2a,a2f,direct = StreamStats(),StreamStats(),StreamStats()
    for a,b in [(0,100),(100,0)]+[(0,0)]*98:
        g2a.add(a)
        a2f.add(b)
        direct.add(a+b)
    assert g2a.p99() == a2f.p99() == 0
    assert direct.p99() == 100
    check_stats(json.loads(json.dumps(stats(direct))))


def test_hand_derived_complete_generation_cohort_and_censor():
    m,p = Metrics(256),StreamProducers(4)
    t = m.time.training
    m.next_cycle = t
    d = 123
    p.generate(t,[(1,d)])
    m.generate(t,[(1,d)])
    def obs(push=0,fire=0):
        return SimpleNamespace(in_ready=15,out_valid=int(any(m.fifo)),out_ready=1,
                               fire=fire,out_source=1,out_desc=d,in_desc=[0,d,0,0],push=push,i_held=0)
    m.observe(t,obs(),p)
    m.snapshot("pending",t+1,p)
    pending = m.snapshots["pending"]["per_source"][1]["sparse_pending_by_generation_cohort"]["A"]
    assert pending["producer_generation_age"]["histogram"] == {1:1}
    m.observe(t+1,obs(push=2),p)
    m.snapshot("accepted",t+2,p)
    ages = m.snapshots["accepted"]["per_source"][1]["sparse_pending_by_generation_cohort"]["A"]
    assert ages["fifo_generation_age"]["histogram"] == {2:1}
    assert ages["fifo_acceptance_age"]["histogram"] == {1:1}
    m.observe(t+2,obs(fire=1),p)
    m.assert_complete(p,1,1)
    row = m.as_dict()["cohorts"]["A"]
    assert row["completed_per_source"] == [0,1,0,0]
    assert [row["pooled_sparse"][s]["p99_nearest_rank"] for s in STAGES] == [1,1,2]


def test_incomplete_guard_and_hold_are_rejected():
    m,p = Metrics(256),StreamProducers(4)
    p.generate(512,[(1,42),(1,43)])
    m.generate(512,[(1,42),(1,43)])
    assert p.offers()[1] == (512,42)
    assert p.offers()[1] == (512,42)
    p.accept(1,513)
    assert p.offers()[1] == (512,43)
    with pytest.raises(AssertionError,match="incomplete A"):
        m.assert_cohort_complete("A")


def fixture_result():
    """Small hand-built production report; rows describe populations, never run RTL."""
    t,m = Timeline(5_000_000),Metrics(5_000_000)
    m.last_phase = "drain"
    lengths = (t.training,100000,1024,102400,1024,1)
    for p,n in zip(PHASES,lengths):
        row = m.phases[p]
        row.update(cycles=n,ready=n,generated=[0 if p == "drain" else n,0,0,0],accepted=[0 if p == "drain" else n,0,0,0],fired=[0 if p == "drain" else n,0,0,0])
        row["fires"] = sum(row["fired"])
        row["idle_ready"] = n-row["fires"]
    for name,k in zip(("training_end","A_end","A_guard_end","B_end","B_guard_end"),t.bounds):
        m.snapshot(name,k,StreamProducers(4))
    for c,count in (("A",1),("B",800)):
        r = m.cohorts[c]
        r["generated_per_source"] = r["completed_per_source"] = [0,count,count,count]
        r["completed_by_phase"][c] = [0,count,count,count]
        for h in range(1,4):
            m.phases[c]["generated"][h] = count
            m.phases[c]["accepted"][h] = count
            m.phases[c]["fired"][0] -= count
            m.phases[c]["fired"][h] = count
            m.phases["drain"]["fired"][0] += count
            m.phases["drain"]["accepted"][0] += 0
            for s in STAGES:
                r["per_source"][h][s].hist = {1:count}
                r["per_source"][h][s].count = r["per_source"][h][s].total = count
                r["pooled_sparse"][s].hist[1] = r["pooled_sparse"][s].hist.get(1,0)+count
                r["pooled_sparse"][s].count += count
                r["pooled_sparse"][s].total += count
    # Drain length covers all displaced heavy work; this fixture is solely a schema control.
    drain = m.phases["drain"]
    drain["cycles"] = drain["ready"] = drain["fires"] = sum(drain["fired"])+1
    drain["idle_ready"] = 1
    drain["fires"] -= 1
    total = sum(sum(r["generated"]) for r in m.phases.values())
    data = dict(schema="cxl-hog-sparse-v1",seed=509,n_src=4,policy="FCFS",policy_param=0,window=t.window,
                params=dict(N_SRC=4,DEPTH=16,DESC_W=105,TS_W=32,RR_QUANTUM=10,FAI_W=t.window,POLICY=0),
                production_evidence=True,sensitivity_evidence=False,infrastructure_only=False,
                training_cycles=t.training,active_cycles=t.end,trace_config=Traffic(509,t.window).config,
                trace_sha256="0"*64,trace_ready_cycles=t.end,cold_pin_cycles=t.training,cold_pin_sha256="1"*64,
                heavy_generation_end=t.end,sparse_guard_complete=True,outstanding_after_drain=0,generated_unaccepted_after_drain=0,
                drain_cycles=drain["cycles"],drain_bound=10000,responses=dict(issued=total,completed=total),
                trace_generated_per_source=[sum(r["generated"][h] for r in m.phases.values()) for h in range(4)],
                metrics=m.as_dict(),real_non_reset_cycles=t.end+drain["cycles"],
                windows=[dict(closing_trace_cycle=(i+1)*t.window-1,counts=[t.window-30,10,10,10],total=t.window,evidence=["DOWN","UP","UP","UP"],classes=None) for i in range(2)])
    return json.loads(json.dumps(data))


def test_gate_accepts_schema_fixture():
    check_result(fixture_result(),{},"0"*64)


@pytest.mark.parametrize("mutation",["trace","policy","params","label","heavy_off","guard","cohort","p99","burst","window","length"])
def test_negative_evidence_controls(mutation):
    d = fixture_result()
    if mutation == "trace": d["trace_sha256"] = "2"*64
    if mutation == "policy": d["policy"] = "RR"
    if mutation == "params": d["params"]["DEPTH"] = 8
    if mutation == "label": d["production_evidence"] = False
    if mutation == "heavy_off": d["metrics"]["phases"]["B_guard"]["generated"][0] -= 1
    if mutation == "guard": d["metrics"]["snapshots"]["A_guard_end"]["fifo_occupancy"][1] = 1
    if mutation == "cohort": d["metrics"]["cohorts"]["A"]["completed_by_phase"]["drain"][1] = 1
    if mutation == "p99": d["metrics"]["cohorts"]["A"]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"] = 99
    if mutation == "burst": d["metrics"]["phases"]["B"]["generated"][1] = 799
    if mutation == "window": d["windows"][0]["total"] -= 1
    if mutation == "length": d["active_cycles"] -= 1
    with pytest.raises(AssertionError):
        check_result(d,{},"0"*64)


def matrix_steps():
    configs = [config(p,True) for p in range(3)]
    steps = [dict(kind="lint",status="PASS",name="lint:"+c["name"]) for c in configs]
    steps += [dict(kind="pytest",status="PASS",name="pytest:hog_sparse",tests=20)]
    steps += [dict(kind="cocotb",name="cocotb:"+c["name"]+"_seed509",seed=509,status="PASS",exit_codes=dict(make=0,simulation=0),tests=1) for c in configs]
    return configs,steps


def test_matrix_gate_accepts_exact_pilot():
    check_matrix(*matrix_steps())


@pytest.mark.parametrize("mutation",["missing","duplicate","failed","exit","skip","lint","config"])
def test_negative_matrix(mutation):
    configs,steps = matrix_steps()
    if mutation == "missing": steps.pop()
    if mutation == "duplicate": steps.append(deepcopy(steps[-1]))
    if mutation == "failed": steps[-1]["status"] = "FAIL"
    if mutation == "exit": steps[-1]["exit_codes"]["simulation"] = 1
    if mutation == "skip": steps[-1]["skipped"] = 1
    if mutation == "lint": steps[0]["status"] = "NOT_RUN"
    if mutation == "config": configs[0]["timeout_s"] = 1
    with pytest.raises(AssertionError):
        check_matrix(configs,steps)
