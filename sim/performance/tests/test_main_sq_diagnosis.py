"""Hand-derived passive-recorder fixtures and negative controls; no RTL substitute."""
from copy import deepcopy
from collections import deque
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/"sim"/"performance"), str(ROOT/"sim"/"common"), str(ROOT/"scripts")]
from hog_sparse import StreamProducers, StreamStats, stats
from main_sq_diagnosis import Recorder, Trace, check_diagnosis, read_trace
import run_hog_sparse as hs
from run_main_sq_diagnosis import config

STAGES3 = ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire")


def d(t):
    return t << 73 | 0x55


class Sim:
    """Tiny pin-level fixture: caller chooses the grant; FIFO/producer updates mirror Metrics."""
    def __init__(self, policy=0, depth=16, end=5, trace=None):
        self.time = SimpleNamespace(window=256, b_start=0, end=end, cohort=lambda k: "B", phase=lambda k: "B")
        self.policy, self.depth = policy, depth
        self.rec = Recorder(self.time, policy, trace, depth=depth)
        self.prod = StreamProducers(4)
        self.fifo = [deque() for _ in range(4)]
        self.k = 0

    def step(self, events=(), grant=None, charged=None, refuse=0):
        k = self.k
        events = [(h, d(t)) for h, t in events]
        self.prod.generate(k, events)
        self.rec.generate(k, events)
        occ = [len(q) for q in self.fifo]
        offers = self.prod.offers()
        in_valid = sum(1 << h for h in offers)
        in_ready = sum((n < self.depth) << h for h, n in enumerate(occ)) & ~refuse
        o = SimpleNamespace(i_count=occ, fire=int(grant is not None), out_source=grant or 0,
                            in_valid=in_valid, in_ready=in_ready, push=in_valid & in_ready,
                            in_desc=[offers[h][1] if h in offers else 0 for h in range(4)],
                            i_held=0, i_cand_valid=0, i_cand_source=0, i_cls=["L", "H", "H", "H"],
                            i_turn=0, i_used=0, offered_ctx=charged, charged=charged, visit_event=None, pos=k)
        self.rec.observe(k, o, self.prod, self.fifo)
        if grant is not None:
            self.fifo[grant].popleft()
        for h in range(4):
            if o.push >> h & 1:
                g, desc = self.prod.accept(h, k)
                self.fifo[h].append((g, k, desc))
        self.rec.after(k, self.fifo)
        self.k += 1

    def metrics(self):
        """Hand-built Metrics cohort from the fixture's own expected joins."""
        per = [{s: StreamStats() for s in STAGES3} for _ in range(4)]
        pooled = {s: StreamStats() for s in STAGES3}
        for r in self.rec.done:
            for s in STAGES3:
                per[r["source"]][s].add(r[s])
                pooled[s].add(r[s])
        gen = [sum(r["source"] == h for r in self.rec.done) for h in range(4)]
        return SimpleNamespace(cohorts={"B": dict(generated_per_source=gen, per_source=per, pooled_sparse=pooled)})

    def result(self, m):
        return dict(seed=509, policy_param=self.policy, window=256, trace_sha256="0"*64,
                    metrics=dict(cohorts=dict(B=dict(generated_per_source=m.cohorts["B"]["generated_per_source"],
                                                     pooled_sparse={s: stats(v) for s, v in m.cohorts["B"]["pooled_sparse"].items()}))))


def fcfs_burst(trace=None):
    s = Sim(depth=2, trace=trace)
    s.step(events=[(0, 0), (1, 10), (1, 11), (1, 12)])  # 10 accepted; 11,12 serialized
    s.step(grant=0)  # heavy fires while 10 is head; 11 accepted
    s.step(grant=1)  # 12 offered to a full FIFO (admission delay); 10 fires
    s.step(grant=1)  # 12 accepted; 11 fires
    s.step(grant=1)  # 12 fires
    return s


def by_tag(s):
    return {r["tag"]: r for r in s.rec.done}


def test_hand_derived_serialization_admission_and_head_waits():
    r = by_tag(fcfs_burst())
    assert set(r) == {10, 11, 12}
    expect = {10: dict(generation=0, acceptance=0, fire=2, producer_predecessors=0, serialization_cycles=0,
                       full_refused_cycles=0, fifo_predecessors=0, nonhead_cycles=0, head_cycles=2,
                       head_fires_heavy=1, head_fires_other_sparse=0, head_fires_same_age=1),
              11: dict(generation=0, acceptance=1, fire=3, producer_predecessors=1, serialization_behind_accepted=1,
                       serialization_behind_refused=0, full_refused_cycles=0, fifo_predecessors=1,
                       nonhead_cycles=1, nonhead_fires_same_source=1, head_cycles=1, head_fires_heavy=0),
              12: dict(generation=0, acceptance=3, fire=4, producer_predecessors=2, serialization_behind_accepted=2,
                       serialization_behind_refused=0, full_refused_cycles=1, fifo_predecessors=0,
                       nonhead_cycles=0, head_cycles=1, generation_to_acceptance=3, generation_to_fire=4)}
    for t, fields in expect.items():
        assert {k: r[t][k] for k in fields} == fields, t
    assert r[12]["grants"] == [[1, 0, 0, None], [2, 1, 10, None], [3, 1, 11, None], [4, 1, 12, None]]
    assert all(r[t]["head_fires_low_class"] == r[t]["head_fires_other_high_class"] == 0 for t in r)


def test_main_class_and_age_split_while_head():
    s = Sim(policy=2, end=4)
    s.step(events=[(3, 30), (0, 1)])
    s.step(events=[(2, 20)], grant=0, charged=("Low", 0))   # Low fire while 30 is head
    s.step(grant=3, charged=("High", 0))                     # older other-High fire while 20 is head
    s.step(grant=2, charged=("High", 1))
    r = by_tag(s)
    assert {k: r[30][k] for k in ("head_cycles", "head_fires_heavy", "head_fires_low_class",
                                  "head_fires_other_high_class", "head_fires_same_age")} == \
        dict(head_cycles=2, head_fires_heavy=1, head_fires_low_class=1, head_fires_other_high_class=0, head_fires_same_age=1)
    assert r[30]["head_charged"] == {"Low:0": 1}
    assert {k: r[20][k] for k in ("generation", "acceptance", "fire", "head_fires_other_sparse",
                                  "head_fires_other_high_class", "head_fires_older", "head_fires_low_class")} == \
        dict(generation=1, acceptance=1, fire=3, head_fires_other_sparse=1, head_fires_other_high_class=1,
             head_fires_older=1, head_fires_low_class=0)
    assert r[20]["ctx_fire"]["charged"] == ["High", 1] and r[20]["ctx_head"]["classes"] == ["L", "H", "H", "H"]


def test_finalize_trace_replay_and_tamper_controls(tmp_path):
    paths = []
    for i in range(2):
        path = tmp_path/f"t{i}.jsonl.gz"
        s = fcfs_burst(Trace(path))
        m = s.metrics()
        diag = json.loads(json.dumps(s.rec.finalize(m, s.result(m))))
        paths.append(path)
    assert paths[0].read_bytes() == paths[1].read_bytes(), "trace is not deterministic"
    result = s.result(m)
    assert diag["direct_g2f_p99_nearest_rank"] == 4 and diag["tail_requests"] == 1
    assert diag["totals"]["full_refused_cycles"] == 1 and diag["totals"]["serialization_cycles"] == 3
    assert diag["trace"]["rows"] == 5
    check_diagnosis(diag, result, paths[1])
    bad = deepcopy(diag)
    bad["per_request"][2]["full_refused_cycles"] = 0
    bad["per_request"][2]["serialization_behind_refused"] = 1
    bad["per_request"][2]["serialization_cycles"] = 3
    with pytest.raises(AssertionError):
        check_diagnosis(bad, result, paths[1])  # passes local identities, fails trace replay
    bad = deepcopy(diag)
    bad["pooled"]["generation_to_fire"]["histogram"] = {"2": 1, "3": 1, "5": 1}
    with pytest.raises(AssertionError):
        check_diagnosis(bad, result)
    rows = [line for line, _ in read_trace(paths[1])]
    short = tmp_path/"short.jsonl.gz"
    w = Trace(short)
    for line in rows[:-1]:
        w.write(json.loads(line))
    w.close()
    with pytest.raises(AssertionError):
        check_diagnosis(diag, result, short)


def test_recorder_rejects_inconsistent_observations():
    s = Sim(depth=4)
    with pytest.raises(AssertionError, match="refusal without full FIFO"):
        s.step(events=[(1, 10)], refuse=0b10)
    s = Sim()
    s.step(events=[(1, 10)])
    with pytest.raises(AssertionError, match="without a grant"):
        s.step()
    s = Sim()
    s.step(events=[(1, 10)])
    with pytest.raises(AssertionError, match="recorder cycle order"):
        s.rec.observe(5, None, s.prod, s.fifo)
    s = fcfs_burst()
    with pytest.raises(AssertionError):
        s.rec.finalize(SimpleNamespace(cohorts={"B": dict(generated_per_source=[0, 2, 0, 0])}))


def test_runner_jobs_equal_accepted_hog_sparse_jobs():
    for pilot in (True, False):
        for p in range(3):
            new, old = config(p, pilot), hs.config(p, pilot)
            changed = {"name", "test_module", "seeds", "env", "artifacts"}
            assert {k: v for k, v in new.items() if k not in changed} == {k: v for k, v in old.items() if k not in changed}
            assert new["seeds"] == [509] and old["seeds"][0] == 509 and new["test_module"] == "test_main_sq_diagnosis"
            assert new["env"] == dict(old["env"], CXL_MAIN_SQ_SCOPE="pilot" if pilot else "main")
            assert [a["file"] for a in new["artifacts"]][0] == old["artifacts"][0]["file"]


def test_cocotb_module_exposes_only_wrapper_and_restores_globals():
    pytest.importorskip("cocotb")
    spec = importlib.util.spec_from_file_location("msq_cocotb_fixture", ROOT/"sim"/"performance"/"test_main_sq_diagnosis.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from cocotb.regression import TestGenerator
    assert [k for k, v in vars(mod).items() if isinstance(v, TestGenerator)] == ["main_sq_diagnosis"]
    import hog_sparse
    assert mod.base.Metrics is hog_sparse.Metrics
