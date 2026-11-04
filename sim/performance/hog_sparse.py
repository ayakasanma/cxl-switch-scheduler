"""Exogenous heavy/sparse trace and passive, bounded-history multi-phase recorder."""
from collections import Counter, deque
import hashlib
import json
import random

from followup import Gaps, POLICIES, STAGES, StreamProducers, StreamStats, stats

SCHEMA = "cxl-hog-sparse-v1"
PHASES = ("training", "A", "A_guard", "B", "B_guard", "drain")


class Timeline:
    def __init__(self, window):
        assert window in (256, 5_000_000), "unsupported experiment window"
        self.window, self.training = window, 2*window
        self.a_end = self.training+100_000
        self.b_start = self.a_end+1024
        self.b_end = self.b_start+102_400
        self.end = self.b_end+1024
        self.bounds = (self.training, self.a_end, self.b_start, self.b_end, self.end)

    def phase(self, k):
        assert k >= 0
        return PHASES[next((i for i,b in enumerate(self.bounds) if k < b), 5)]

    def cohort(self, k):
        phase = self.phase(k)
        if phase in ("A", "B"):
            return phase
        if self.window == 5_000_000 and self.training-101024 <= k < self.training-1024:
            return "cold"
        return None


class Traffic(Timeline):
    def __init__(self, seed, window):
        super().__init__(window)
        self.config = dict(generator="cxl-hog-sparse-traffic-v1", seed=seed, window=window,
                           n_src=4, depth=16, desc_w=105, heavy_source=0, heavy_per_cycle=1,
                           sparse_probability=[1,128], burst_size=8, burst_block_cycles=1024,
                           burst_blocks=100, burst_offset_inclusive=[0,1023], ready=1,
                           phase_cycles=dict(zip(PHASES[:-1], (self.training,100000,1024,102400,1024))),
                           timing="cycle0 first nonreset; generate before edge; half-open phases",
                           rng="independent arrival/offset/descriptor stream per source")
        self.arrivals = [random.Random(f"hog-sparse-v1:{seed}:arrival:{h}") for h in range(4)]
        self.offsets = []
        for h in range(4):
            rng = random.Random(f"hog-sparse-v1:{seed}:offset:{h}")
            self.offsets.append([rng.randrange(1024) for _ in range(100)])
        self.descriptors = [random.Random(f"hog-sparse-v1:{seed}:descriptor:{h}") for h in range(4)]
        self.serial = self.next_cycle = self.ready_count = 0
        self.generated = [0]*4
        self.sha = hashlib.sha256((json.dumps(self.config,sort_keys=True,separators=(",",":"))+"\n").encode())

    def step(self, k):
        assert k == self.next_cycle and k < self.end
        self.next_cycle += 1
        phase, sources = self.phase(k), [0]
        if phase in ("training", "A"):
            sources += [h for h in range(1,4) if self.arrivals[h].randrange(128) == 0]
        elif phase == "B":
            block, offset = divmod(k-self.b_start,1024)
            sources += [h for h in range(1,4) if self.offsets[h][block] == offset for _ in range(8)]
        events = []
        for h in sources:
            assert self.serial < 2**32, "tag space exhausted"
            d = (self.serial << 73) | self.descriptors[h].getrandbits(73)
            self.serial += 1
            self.generated[h] += 1
            events.append((h,d))
        self.ready_count += 1
        self.sha.update(f"{k}:1:".encode())
        for h,d in events:
            self.sha.update(bytes([h])+d.to_bytes(14,"big"))
        self.sha.update(b"\n")
        return events, 1

    @property
    def sha256(self):
        return self.sha.hexdigest()


class Summary:
    """Constant-memory moments for overload backlog/ages, whose P99 is not an endpoint."""
    def __init__(self):
        self.count = self.total = 0
        self.min = self.max = self.end = None

    def add(self, value):
        self.count += 1
        self.total += value
        self.min = value if self.min is None else min(self.min,value)
        self.max = value if self.max is None else max(self.max,value)
        self.end = value

    def as_dict(self):
        return dict(count=self.count, mean=self.total/self.count if self.count else None,
                    min=self.min,max=self.max,end=self.end)


def stages():
    return {s:StreamStats() for s in STAGES}


class Metrics:
    def __init__(self, window):
        self.time = Timeline(window)
        self.fifo = [deque() for _ in range(4)]
        self.phases = {p:dict(cycles=0,ready=0,fires=0,idle_ready=0,output_stall_cycles=0,
                             idle_not_ready=0,eligible_ready=0,avoidable_bubbles=0,
                             generated=[0]*4,accepted=[0]*4,fired=[0]*4,
                             occupancy=[StreamStats() for _ in range(4)],
                             producer_backlog=[Summary() for _ in range(4)],
                             fifo_nonempty=[0]*4,fifo_nonempty_ready=[0]*4,full=[0]*4,held=0,
                             gaps=[Gaps() for _ in range(4)]) for p in PHASES}
        self.cohorts = {p:dict(generated_per_source=[0]*4,completed_per_source=[0]*4,
                              completed_by_phase={f:[0]*4 for f in PHASES},
                              per_source=[stages() for _ in range(4)],pooled_sparse=stages())
                        for p in ("cold","A","B")}
        self.arrival_contexts = {p:[Counter() for _ in range(4)] for p in self.cohorts}
        self.main_contexts = {p:dict(class_maps=Counter(),visits=Counter(),relinquishments=0,
                                   charged_fires=Counter(),held_cycles=0) for p in PHASES}
        self.snapshots = {}
        self.next_cycle = 0
        self.last_phase = None

    def generate(self,k,events):
        row = self.phases[self.time.phase(k)]
        cohort = self.time.cohort(k)
        for h,_ in events:
            row["generated"][h] += 1
            if h and cohort:
                self.cohorts[cohort]["generated_per_source"][h] += 1

    def observe(self,k,o,producers,events=()):
        assert k == self.next_cycle
        self.next_cycle += 1
        phase = self.time.phase(k)
        row = self.phases[phase]
        if phase != self.last_phase:
            if self.last_phase:
                for gap in self.phases[self.last_phase]["gaps"]:
                    gap.boundary(False)
            for h,gap in enumerate(row["gaps"]):
                gap.boundary(bool(self.fifo[h]))
            self.last_phase = phase
        occ = [len(q) for q in self.fifo]
        assert o.in_ready == sum((n < 16) << h for h,n in enumerate(occ))
        assert o.out_valid == int(any(occ)) and o.out_ready == 1
        row["cycles"] += 1
        row["ready"] += o.out_ready
        row["fires"] += o.fire
        row["idle_ready"] += int(not o.fire)
        row["eligible_ready"] += int(any(occ))
        bubble = int(any(occ) and not o.fire)
        row["avoidable_bubbles"] += bubble
        assert not bubble, "avoidable eligible-ready bubble"
        row["held"] += o.i_held
        for h in range(4):
            row["occupancy"][h].add(occ[h])
            row["producer_backlog"][h].add(len(producers.pending[h]))
            row["fifo_nonempty"][h] += int(bool(occ[h]))
            row["fifo_nonempty_ready"][h] += int(bool(occ[h]) and o.out_ready)
            row["full"][h] += int(occ[h] == 16)
        if hasattr(o,"i_cls"):
            ctx = self.main_contexts[phase]
            ctx["class_maps"]["/".join(o.i_cls)] += 1
            ctx["held_cycles"] += o.i_held
            ctx["relinquishments"] += int(o.relinquished is not None)
            if o.visit_event:
                ctx["visits"][o.visit_event] += 1
            if o.charged:
                ctx["charged_fires"][o.charged[0]] += 1
            cohort = self.time.cohort(k)
            if cohort:
                key = json.dumps(dict(classes=o.i_cls,turn=o.i_turn,used=o.i_used,
                                      remaining=10-o.i_used,held=o.i_held,
                                      offered=o.offered_ctx,held_context=o.i_held_ctx),sort_keys=True)
                for h,_ in events:
                    if h:
                        self.arrival_contexts[cohort][h][key] += 1
        if o.fire:
            h = o.out_source
            g,a,d = self.fifo[h].popleft()
            assert d == o.out_desc and k > a >= g
            row["fired"][h] += 1
            cohort = self.time.cohort(g)
            if h and cohort:
                c = self.cohorts[cohort]
                c["completed_per_source"][h] += 1
                c["completed_by_phase"][phase][h] += 1
                for stage,value in zip(STAGES,(a-g,k-a,k-g)):
                    c["per_source"][h][stage].add(value)
                    c["pooled_sparse"][stage].add(value)
        for h in range(4):
            if o.push >> h & 1:
                g,d = producers.accept(h,k)
                assert d == o.in_desc[h]
                self.fifo[h].append((g,k,d))
                row["accepted"][h] += 1
            row["gaps"][h].observe(bool(occ[h]),bool(o.fire and o.out_source == h),1,bool(self.fifo[h]))

    def snapshot(self,name,k,producers):
        rows = []
        for h in range(4):
            ages = {c:{s:StreamStats() for s in ("producer_generation_age","fifo_generation_age","fifo_acceptance_age")}
                    for c in self.cohorts}
            all_ages = {s:Summary() for s in ("producer_generation_age","fifo_generation_age","fifo_acceptance_age")}
            for g,_ in producers.pending[h]:
                all_ages["producer_generation_age"].add(k-g)
                c = self.time.cohort(g)
                if h and c:
                    ages[c]["producer_generation_age"].add(k-g)
            for g,a,_ in self.fifo[h]:
                for field,value in (("fifo_generation_age",k-g),("fifo_acceptance_age",k-a)):
                    all_ages[field].add(value)
                    c = self.time.cohort(g)
                    if h and c:
                        ages[c][field].add(value)
            rows.append(dict(sparse_pending_by_generation_cohort={c:{s:stats(v) for s,v in a.items()} for c,a in ages.items()},
                             all_pending_ages={s:v.as_dict() for s,v in all_ages.items()}))
        self.snapshots[name] = dict(next_trace_cycle=k,per_source=rows,
                                    fifo_occupancy=[len(q) for q in self.fifo],
                                    producer_backlog=[len(q) for q in producers.pending])

    def assert_cohort_complete(self,cohort):
        c = self.cohorts[cohort]
        assert c["generated_per_source"] == c["completed_per_source"], f"incomplete {cohort} background-on cohort"

    def assert_complete(self,producers,issued,completed):
        assert not producers.backlog() and not any(self.fifo), "incomplete generated population"
        totals = [sum(sum(r[key]) for r in self.phases.values()) for key in ("generated","accepted","fired")]
        assert totals[0] == totals[1] == totals[2] == producers.generated == producers.accepted == issued == completed
        for c in self.cohorts:
            self.assert_cohort_complete(c)

    def as_dict(self):
        for gap in self.phases[self.last_phase]["gaps"]:
            if gap.active:
                gap.boundary(False)
        phases = {}
        for p,row in self.phases.items():
            phases[p] = {k:([stats(s) for s in v] if k == "occupancy" else
                            [s.as_dict() for s in v] if k in ("producer_backlog","gaps") else v) for k,v in row.items()}
            phases[p]["successful_slot_utilization"] = row["fires"]/row["cycles"] if row["cycles"] else None
            phases[p]["ready_opportunity_utilization"] = row["fires"]/row["ready"] if row["ready"] else None
        cohorts = {c:{**{k:v for k,v in row.items() if k not in ("per_source","pooled_sparse")},
                       "per_source":[{s:stats(v) for s,v in h.items()} for h in row["per_source"]],
                       "pooled_sparse":{s:stats(v) for s,v in row["pooled_sparse"].items()}} for c,row in self.cohorts.items()}
        return dict(phases=phases,cohorts=cohorts,snapshots=self.snapshots,
                    arrival_contexts=self.arrival_contexts,main_contexts=self.main_contexts)


def check_stats(row):
    hist = {int(k):v for k,v in row["histogram"].items()}
    assert all(v > 0 for v in hist.values())
    s = StreamStats()
    s.hist, s.count, s.total = hist, sum(hist.values()), sum(k*v for k,v in hist.items())
    assert {k:v for k,v in row.items() if k != "histogram"} == s.as_dict(), "invalid direct histogram/statistics"


def check_result(data,expected,trace_hash):
    assert data["schema"] == SCHEMA
    for k,v in expected.items():
        assert data[k] == v, f"wrong {k}"
    t = Timeline(data["window"])
    assert data["policy_param"] in (0,1,2) and data["policy"] == POLICIES[data["policy_param"]]
    assert data["seed"] in range(509,514)
    assert data["n_src"] == 4 and data["params"] == dict(N_SRC=4,DEPTH=16,DESC_W=105,TS_W=32,RR_QUANTUM=10,FAI_W=t.window,POLICY=data["policy_param"])
    assert data["production_evidence"] is (t.window == 5_000_000)
    assert data["sensitivity_evidence"] is (t.window == 256) and data["infrastructure_only"] is False
    assert data["training_cycles"] == t.training and data["active_cycles"] == t.end
    assert data["trace_config"] == Traffic(data["seed"],t.window).config
    assert data["trace_sha256"] == trace_hash
    assert data["trace_ready_cycles"] == t.end
    assert data["cold_pin_cycles"] == t.training
    assert len(data["cold_pin_sha256"]) == 64
    assert data["heavy_generation_end"] == t.end and data["sparse_guard_complete"] is True
    assert data["outstanding_after_drain"] == data["generated_unaccepted_after_drain"] == 0
    assert 0 < data["drain_cycles"] <= data["drain_bound"]
    m = data["metrics"]
    assert set(m["phases"]) == set(PHASES)
    lengths = (t.training,100000,1024,102400,1024,data["drain_cycles"])
    for p,n in zip(PHASES,lengths):
        row = m["phases"][p]
        assert row["cycles"] == row["ready"] == n
        assert row["fires"] == sum(row["fired"])
        assert sum(row[k] for k in ("fires","idle_ready","output_stall_cycles","idle_not_ready")) == n
        assert row["avoidable_bubbles"] == 0
        assert row["generated"][0] == (0 if p == "drain" else n), "early heavy stop"
        if p in ("A_guard","B_guard","drain"):
            assert row["generated"][1:] == [0]*3
    assert m["phases"]["B"]["generated"][1:] == [800]*3
    totals = [sum(sum(p[key]) for p in m["phases"].values()) for key in ("generated","accepted","fired")]
    assert totals[0] == totals[1] == totals[2] == data["responses"]["issued"] == data["responses"]["completed"]
    assert data["trace_generated_per_source"] == [sum(p["generated"][h] for p in m["phases"].values()) for h in range(4)]
    for c in ("cold","A","B"):
        row = m["cohorts"][c]
        assert row["generated_per_source"] == row["completed_per_source"]
        assert row["completed_per_source"][0] == 0
        assert row["completed_per_source"] == [sum(p[h] for p in row["completed_by_phase"].values()) for h in range(4)]
        allowed = ("training",) if c == "cold" else (c,c+"_guard")
        assert not any(sum(v) for p,v in row["completed_by_phase"].items() if p not in allowed), "guard contamination"
        if c in ("A","B"):
            assert row["generated_per_source"][1:] == m["phases"][c]["generated"][1:]
        if c == "cold" and t.window == 256:
            assert not sum(row["generated_per_source"])
        for s in STAGES:
            for h in range(4):
                check_stats(row["per_source"][h][s])
                assert row["per_source"][h][s]["count"] == row["completed_per_source"][h]
            pooled = row["pooled_sparse"][s]
            check_stats(pooled)
            combined = Counter()
            for h in range(1,4):
                combined.update({int(k):v for k,v in row["per_source"][h][s]["histogram"].items()})
            assert dict(combined) == {int(k):v for k,v in pooled["histogram"].items()}
    for name,k in zip(("training_end","A_end","A_guard_end","B_end","B_guard_end"),t.bounds):
        snap = m["snapshots"][name]
        assert snap["next_trace_cycle"] == k
        if name in ("training_end","A_guard_end","B_guard_end"):
            cohorts = ("cold",) if name == "training_end" else ("A",) if name == "A_guard_end" else ("B",)
            for h in range(1,4):
                for c in cohorts:
                    assert all(s["count"] == 0 for s in snap["per_source"][h]["sparse_pending_by_generation_cohort"][c].values()), "incomplete guard"
            if name != "training_end":
                assert snap["producer_backlog"][1:] == snap["fifo_occupancy"][1:] == [0]*3
    assert data["real_non_reset_cycles"] == t.end+data["drain_cycles"]
    windows = data["windows"]
    assert len(windows) == data["real_non_reset_cycles"]//t.window
    for i,w in enumerate(windows):
        assert w["closing_trace_cycle"] == (i+1)*t.window-1
        assert w["total"] == sum(w["counts"])
        evidence = ["S0" if not w["total"] else "UP" if 40*b < 3*w["total"] else "DOWN" if 4*b > w["total"] else "KEEP" for b in w["counts"]]
        assert w["evidence"] == evidence
        if i < 2:
            assert evidence[0] == "DOWN" and all(e != "DOWN" for e in evidence[1:])
    if data["policy_param"] == 2:
        assert [w["classes"] for w in windows[:2]] == [["B_H","H","H","H"],["L","H","H","H"]]
        if t.window == 5_000_000:
            for p in ("A","A_guard","B","B_guard"):
                assert m["main_contexts"][p]["class_maps"] == {"L/H/H/H":m["phases"][p]["cycles"]}
        for c in ("cold","A","B"):
            assert [sum(h.values()) for h in m["arrival_contexts"][c]] == m["cohorts"][c]["generated_per_source"]
