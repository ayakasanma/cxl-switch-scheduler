"""Hand-derived metric checks and rejected/incomplete evidence controls; no simulator needed."""
import copy
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"common"))
sys.path.insert(0,str(ROOT/"performance"))
sys.path.insert(0,str(ROOT.parent/"scripts"))
from followup import Gaps, LOW_SUBSETS, Metrics, SCHEMA, StreamProducers, StreamStats, Traffic, check_result, check_drain_budget, stats


def drive(m,p,k,events=(),push=(),fire=None,ready=1):
    p.generate(k,events)
    m.generate(k,events)
    offers = p.offers()
    occ = [len(q) for q in m.fifo]
    o = SimpleNamespace(in_ready=sum((c<16)<<h for h,c in enumerate(occ)),
                        out_valid=int(any(occ)),out_ready=ready,fire=int(fire is not None),
                        out_source=fire,out_desc=m.fifo[fire][0][2] if fire is not None else 0,
                        push=sum(1<<h for h in push),in_desc=[offers[h][1] if h in offers else 0 for h in range(4)])
    m.observe(k,o,p)


def hand_result():
    m,p = Metrics(2,3),StreamProducers(4)
    drive(m,p,0,[(0,100)],(0,))
    drive(m,p,1,[(0,101)],(0,),0)
    m.snapshot("measurement_start",2,p)
    drive(m,p,2,ready=0)
    drive(m,p,3,[(0,102)],(0,),0)
    drive(m,p,4,ready=0)
    m.snapshot("measurement_end",5,p)
    drive(m,p,5,fire=0)
    drive(m,p,6)
    m.assert_complete(p,3,3)
    return m,p


def test_hand_cohorts_carryover_and_drain():
    m,p = hand_result()
    d = m.as_dict()
    assert d["phases"]["measurement"]["fired"] == [1,0,0,0]
    assert d["phases"]["drain"]["fired"] == [1,0,0,0]
    assert d["completion_cohorts"]["warmup"]["warmup"]["measurement"] == [1,0,0,0]
    assert d["completion_cohorts"]["measurement"]["measurement"]["drain"] == [1,0,0,0]
    assert d["latency_by_cohort"]["generation"]["warmup"][0]["generation_to_fire"]["mean"] == 1.5
    measured = d["latency_by_cohort"]["acceptance"]["measurement"][0]
    assert measured["acceptance_to_fire"]["histogram"] == {2:1}
    assert measured["generation_to_fire"]["count"] == 1
    snap = d["snapshots"]["measurement_end"]["per_source"][0]
    assert snap["fifo_pending_by_acceptance"]["measurement"]["histogram"] == {2:1}
    assert d["phases"]["measurement"]["successful_slot_utilization"] == 1/3
    assert d["phases"]["measurement"]["ready_opportunity_utilization"] == 1


def test_hand_gaps_ready_stalls_and_boundary_censoring():
    m,_ = hand_result()
    gap = m.as_dict()["phases"]["measurement"]["gaps"][0]["samples"]
    assert gap["left_censored_completed"]["wall_cycles"]["histogram"] == {2:1}
    assert gap["left_censored_completed"]["eligible_ready_opportunities"]["histogram"] == {1:1}
    assert gap["right_censored"]["wall_cycles"]["histogram"] == {1:1}
    assert gap["right_censored"]["eligible_ready_opportunities"]["histogram"] == {0:1}


def test_full_initial_interservice_and_empty_termination():
    g = Gaps()
    g.observe(True,False,0,True)
    g.observe(True,True,1,True)
    g.observe(True,False,0,True)
    g.observe(True,False,1,True)
    g.observe(True,True,1,False)
    d = g.as_dict()
    assert d["empty_terminated_episodes"] == 1
    assert d["samples"]["initial"]["wall_cycles"]["mean"] == 2
    assert d["samples"]["inter_service"]["wall_cycles"]["mean"] == 3
    assert d["samples"]["inter_service"]["eligible_ready_opportunities"]["mean"] == 2
    assert d["samples"]["terminated_by_empty"]["wall_cycles"]["mean"] == 0


def test_four_way_cycle_partition_distinguishes_sink_stall():
    m,p = Metrics(0,5),StreamProducers(4)
    drive(m,p,0,ready=0)  # empty, sink not ready
    drive(m,p,1,[(0,99)],(0,))  # empty, sink ready; no bypass
    drive(m,p,2,ready=0)  # eligible, sink stalls
    drive(m,p,3,fire=0)  # fire
    drive(m,p,4)  # empty, ready
    r = m.as_dict()["phases"]["measurement"]
    assert [r[k] for k in ("fires","idle_ready","output_stall_cycles","idle_not_ready")] == [1,2,1,1]
    assert sum(r[k] for k in ("fires","idle_ready","output_stall_cycles","idle_not_ready")) == r["cycles"]


def test_drain_timeout_rejected_at_bound():
    check_drain_budget(9,10)
    with pytest.raises(AssertionError,match="drain timeout"):
        check_drain_budget(10,10)


def test_direct_p99_is_not_sum_of_stage_p99():
    m,p = Metrics(0,13),StreamProducers(4)
    for k in range(13):
        events = [(0,100)] if k == 0 else [(1,101)] if k == 1 else []
        push = (0,) if k == 10 else (1,) if k == 2 else ()
        fire = 0 if k == 11 else 1 if k == 12 else None
        drive(m,p,k,events,push,fire,ready=int(fire is not None))
    m.assert_complete(p,2,2)
    hist = [StreamStats() for _ in range(3)]
    for src in m.latencies["generation"]["measurement"]:
        for i,key in enumerate(("generation_to_acceptance","acceptance_to_fire","generation_to_fire")):
            for value,count in src[key].hist.items():
                for _ in range(count): hist[i].add(value)
    assert [s.p99() for s in hist] == [10,10,11]


@pytest.mark.parametrize("bad",["missing_completion","response_missing","pending_producer"])
def test_missing_population_rejected(bad):
    m,p = Metrics(0,1),StreamProducers(4)
    drive(m,p,0,[(0,123)],() if bad == "pending_producer" else (0,))
    if bad == "response_missing": drive(m,p,1,fire=0)
    with pytest.raises(AssertionError):
        m.assert_complete(p,1,0 if bad == "response_missing" else 1)


@pytest.mark.parametrize("window",[64,256,5_000_000])
def test_training_integer_design_counts_and_evidence(window):
    span = window-4
    counts = [2*window//5,window//20,window//20,window//20]
    assert all(3*sum(counts) <= 40*b <= 10*sum(counts) for b in counts[1:])
    assert 4*counts[0] > sum(counts)
    if window < 1000:
        t = Traffic("trained",509,2*window,16,window)
        generated = [[0]*4 for _ in range(2)]
        for k in range(2*window):
            events,ready = t.step(k)
            assert ready == 1
            for h,_ in events: generated[k//window][h] += 1
            if k%window >= span: assert not events
        assert generated == [counts,counts]


def test_finite_same_unique_generated_population_and_ready():
    t = Traffic("finite",509,0,1024)
    tags = set()
    for k in range(1024):
        events,ready = t.step(k)
        assert ready == int(k%4 != 3)
        for _,d in events:
            assert d>>73 not in tags
            tags.add(d>>73)
    assert t.generated == [1024]*4 and len(tags) == 4096


@pytest.mark.parametrize("case",["load030","load090","load120","ready075","trained"])
def test_stream_reproducibility_and_hash(case):
    warmup,w = (128,64) if case == "trained" else (32,5_000_000)
    a,b = [Traffic(case,509,warmup,32,w) for _ in range(2)]
    for k in range(a.end): assert a.step(k) == b.step(k)
    assert a.sha256 == b.sha256 and len(a.sha256) == 64
    c = Traffic(case,510,warmup,32,w)
    for k in range(c.end): c.step(k)
    assert c.sha256 != a.sha256


def result_fixture():
    m,_ = hand_result()
    return dict(schema=SCHEMA,case="load030",policy="FCFS",policy_param=0,seed=509,
                trace_sha256="a"*64,outstanding_after_drain=0,generated_unaccepted_after_drain=0,
                warmup_cycles=2,measurement_cycles=3,responses=dict(issued=3,completed=3),metrics=m.as_dict())


@pytest.mark.parametrize("bad",[None,"policy","hash","short","outstanding","population","response","bubble","schema"])
def test_evidence_rejection_controls(bad):
    d = result_fixture()
    if bad == "policy": d["policy"] = "RR"
    if bad == "hash": d["trace_sha256"] = "b"*64
    if bad == "short": d["measurement_cycles"] = 2
    if bad == "outstanding": d["outstanding_after_drain"] = 1
    if bad == "population": d["metrics"]["phases"]["warmup"]["generated"][0] += 1
    if bad == "response": d["responses"]["completed"] -= 1
    if bad == "bubble": d["metrics"]["phases"]["measurement"]["avoidable_bubbles"] = 1
    if bad == "schema": d["schema"] = "wrong"
    if bad:
        with pytest.raises(AssertionError): check_result(d,{"policy":"FCFS"},"a"*64)
    else:
        check_result(d,{"policy":"FCFS"},"a"*64)


def test_registry_exact_matrix_and_unmodified_engine():
    sys.path.insert(0,str(ROOT.parent/"scripts"))
    import run_descriptor_followup as launcher
    launcher.register()
    assert [sum(len(c["seeds"]) for c in launcher.rv.MILESTONES[s]["cocotb"])
            for s in ("DF-pilot","DF-controls","DF-finite","DF-trained")] == [21,36,3,3]
    for c in launcher.rv.MILESTONES["DF-trained"]["cocotb"]:
        assert c["default_params"]["FAI_W"] == 5_000_000 and "FAI_W" not in c["params"]
        assert c["env"]["CXL_FOLLOWUP_WARMUP"] == 10_000_000
        assert c["env"]["CXL_FOLLOWUP_MEASURE"] == 100_000
        assert c["env"]["CXL_FOLLOWUP_INFRA"] == 0


@pytest.mark.parametrize("bad",[None,"missing","duplicate","wrong_seed","failed","nonzero_exit","empty"])
def test_exact_job_matrix_rejection(bad):
    sys.path.insert(0,str(ROOT.parent/"scripts"))
    from run_descriptor_followup import check_job_matrix
    configs = [dict(name="finite",seeds=[509])]
    steps = [dict(kind="cocotb",name="cocotb:finite_seed509",seed=509,status="PASS",
                  exit_codes=dict(verilator=0,make=0,sim=0))]
    if bad == "missing": steps = []
    if bad == "duplicate": steps += copy.deepcopy(steps)
    if bad == "wrong_seed": steps[0]["seed"] = 510
    if bad == "failed": steps[0]["status"] = "FAIL"
    if bad == "nonzero_exit": steps[0]["exit_codes"]["make"] = 1
    if bad == "empty": configs,steps = [],[]
    if bad:
        with pytest.raises(AssertionError): check_job_matrix(configs,steps)
    else:
        check_job_matrix(configs,steps)


@pytest.mark.parametrize("milestone",["DF-pilot","DF-trained","DF-placement","DF-placement-pilot"])
@pytest.mark.parametrize("gate",[False,True])
@pytest.mark.parametrize("failed",[False,True])
def test_summary_never_adopts_pilot_as_production(tmp_path,milestone,gate,failed):
    sys.path.insert(0,str(ROOT.parent/"scripts"))
    from run_descriptor_followup import FollowupRun, register
    import run_verify
    register()
    run = object.__new__(FollowupRun)
    run.out,run.milestone,run.run_id,run.t0 = tmp_path,milestone,"unit",time.time()
    run.args = SimpleNamespace(lint_only=False)
    run.smoke,run.n_filter,run.seeds_override = False,None,None
    run.entry = run_verify.MILESTONES[milestone]
    run.steps = [dict(kind="lint",status="FAIL" if failed else "PASS",order=1)]
    if gate: run.steps.append(dict(kind="scope",status="PASS",order=2))
    result = run.write_summary(final=True)
    import json
    summary = json.loads((tmp_path/"summary.json").read_text())
    assert summary["production_evidence"] == (gate and milestone == "DF-trained" and not failed)
    assert summary["milestone_acceptance_scope"] == (gate and milestone not in ("DF-pilot","DF-placement-pilot") and not failed)
    if milestone.startswith("DF-placement"):
        assert summary["sensitivity_evidence"] == (gate and not failed)
        assert summary["infrastructure_only"] is False
    assert result == ("INFRA_SMOKE_" if milestone == "DF-pilot" else "") + ("FAIL" if failed else "PASS")


# Captured from the accepted pre-placement generator before changing any source.
@pytest.mark.parametrize("args,steps,digest", [(['load030', 509, 128, 1024, 5000000], 1152, '93faf1aa2ee44f4aacbcabfd6174eb4c8fa5a4f67edb68c5faae0de3bd4f1584'), (['load090', 509, 128, 1024, 5000000], 1152, '3bdebd62f74486939ec98c2281fb153fe7e4c16c39b025321f2ccecf5ed4df5e'), (['load120', 509, 128, 1024, 5000000], 1152, '3a15f73b8f115f145c12f09d058eddfbec8f29f882b93b570e021bb1ab8309cb'), (['ready075', 509, 128, 1024, 5000000], 1152, 'bfffd828429659245193c8da25dec2ff6114d0539cd2fa5ff152596102b8128b'), (['finite', 509, 0, 1024, 5000000], 1024, '6e5e4ba8b445efef90f9eed455383c9671cd7088a1bf5546449b6f1ec51604ba'), (['trained', 509, 128, 512, 64], 640, '39cc084fb98df06e7b0feb913e9a60edd06be503d7aac237dd3eb11e4caeb200'), (['trained', 509, 512, 512, 256], 1024, 'b2a0cfce16af34d0f6ff795100193aec0ee13e66676a05728640a0c8f6e3d3f5'), (['trained', 509, 10000000, 100000, 5000000], 2048, '8f04fbbc2e7099464f17d4a144a2de0fc60b65c9d959583e8cb7310a26590dda')])
def test_legacy_generator_byte_identity(args,steps,digest):
    t = Traffic(*args)
    assert t.config == dict(generator="descriptor-followup-traffic-v1",case=args[0],seed=args[1],
                            warmup=args[2],measurement=args[3],window=args[4],n_src=4)
    for k in range(steps): t.step(k)
    assert t.sha256 == digest


@pytest.mark.parametrize("low", LOW_SUBSETS)
def test_placement_trace_counts_thresholds_and_policy_identity(low):
    from run_descriptor_followup import config
    traces = []
    for policy in range(3):
        cfg = config("placement",policy,low_sources=low)
        assert cfg["env"]["CXL_FOLLOWUP_INFRA"] == 0
        t = Traffic("placement",509,512,240,256,low)
        counts = [[0]*4 for _ in range(2)]
        for k in range(t.end):
            events,ready = t.step(k)
            assert ready == 1
            if k < 512:
                for h,_ in events: counts[k//256][h] += 1
                if k%256 >= 252: assert not events
            else:
                assert [h for h,_ in events] == list(range(4))
        expected = [102//len(low) if h in low else 12 for h in range(4)]
        assert counts == [expected]*2
        assert ["UP" if 40*b < 3*sum(expected) else "DOWN" if 4*b > sum(expected) else "KEEP"
                for b in expected] == ["DOWN" if h in low else "KEEP" for h in range(4)]
        assert t.config["low_sources"] == list(low) and t.config["training_counts"] == expected
        assert t.generated == [2*b+240 for b in expected]
        traces.append(t.sha256)
    assert len(set(traces)) == 1


@pytest.mark.parametrize("low", [(),(0,1,2,3),(0,0),(4,),(-1,),(1,0),(True,)])
def test_invalid_placement_subset(low):
    with pytest.raises(AssertionError): Traffic("placement",509,512,240,256,low)


@pytest.mark.parametrize("args", [(509,512,256,256),(509,511,240,256),
                                  (509,512,240,5000000),(510,512,240,256)])
def test_placement_timing_parameters_rejected(args):
    with pytest.raises(AssertionError): Traffic("placement",*args)


def test_placement_subset_hash_and_legacy_config_isolation():
    hashes = []
    for low in LOW_SUBSETS:
        t = Traffic("placement",509,512,240,256,low)
        hashes.append(t.sha256)
    assert len(set(hashes)) == 14
    with pytest.raises(AssertionError): Traffic("trained",509,128,32,64,(1,))


def placement_result_fixture():
    d = result_fixture()
    counts = [102,12,12,12]
    traffic = Traffic("placement",509,512,240,256)
    d.update(case="placement",policy="FAI_MAIN",policy_param=2,low_sources=[0],window=256,
             warmup_cycles=512,measurement_cycles=240,infrastructure_only=False,
             production_evidence=False,sensitivity_evidence=True,trace_config=traffic.config,
             trace_generated_per_source=[2*b+240 for b in counts],trace_ready_cycles=752,
             training_windows=[dict(closing_trace_cycle=(i+1)*256-1,counts=counts,total=sum(counts),
                                    evidence=["DOWN","KEEP","KEEP","KEEP"],
                                    classes=["B_H" if i == 0 else "L","H","H","H"]) for i in range(2)],
             contention=dict(fill_cycles=128,post_fill_cycles=112,both_classes_eligible_cycles=112,
                             per_source_fires_after_fill=[60,18,17,17],complete_visits=dict(High=100,Low=100)))
    rows = d["metrics"]["phases"]
    warm,measured,drain = (rows[p] for p in ("warmup","measurement","drain"))
    warm.update(cycles=512,generated=[2*b for b in counts],accepted=[2*b for b in counts],fired=[2*b for b in counts])
    measured.update(cycles=240,ready=240,generated=[240]*4,accepted=[60]*4,fired=[119,40,40,40],
                    fifo_nonempty_ready=[127]*4)
    drain.update(cycles=721,generated=[0]*4,accepted=[180]*4,fired=[121,200,200,200])
    for r in rows.values():
        r.update(fires=sum(r["fired"]),idle_ready=r["cycles"]-sum(r["fired"]),output_stall_cycles=0,idle_not_ready=0)
    d["responses"] = dict(issued=sum(d["trace_generated_per_source"]),completed=sum(d["trace_generated_per_source"]))
    return d


@pytest.mark.parametrize("bad", [None,"production","sensitivity","infra","subset","training","closing",
                                 "classes","next_window","eligibility","class_skew","source_skew"])
def test_placement_evidence_rejections(bad):
    d = placement_result_fixture()
    if bad == "production": d["production_evidence"] = True
    if bad == "sensitivity": d["sensitivity_evidence"] = False
    if bad == "infra": d["infrastructure_only"] = True
    if bad == "subset": d["low_sources"] = [1]
    if bad == "training": d["training_windows"][0]["counts"] = [1637,12,12,12]
    if bad == "closing": d["training_windows"][0]["closing_trace_cycle"] -= 1
    if bad == "classes": d["training_windows"][1]["classes"] = ["H"]*4
    if bad == "next_window": d["measurement_cycles"] = 256
    if bad == "eligibility": d["contention"]["both_classes_eligible_cycles"] -= 1
    if bad == "class_skew": d["contention"]["per_source_fires_after_fill"] = [67,15,15,15]
    if bad == "source_skew": d["contention"]["per_source_fires_after_fill"] = [60,20,16,16]
    if bad:
        with pytest.raises(AssertionError): check_result(d,{},"a"*64)
    else:
        check_result(d,{},"a"*64)


def test_placement_exact_matrix_and_incomplete_rejection():
    from run_descriptor_followup import register, rv, check_job_matrix
    register()
    cfgs = rv.MILESTONES["DF-placement"]["cocotb"]
    assert len(cfgs) == 42
    observed = {(tuple(map(int,c["env"]["CXL_FOLLOWUP_LOW_SOURCES"].split(","))),c["params"]["POLICY"]) for c in cfgs}
    assert observed == {(low,p) for low in LOW_SUBSETS for p in range(3)}
    assert len(rv.MILESTONES["DF-placement-pilot"]["cocotb"]) == 9
    steps = [dict(kind="cocotb",name="cocotb:"+c["name"]+"_seed509",seed=509,status="PASS",exit_codes=dict(sim=0)) for c in cfgs]
    check_job_matrix(cfgs,steps)
    with pytest.raises(AssertionError): check_job_matrix(cfgs,steps[:-1])
