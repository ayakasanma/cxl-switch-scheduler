"""Passive Main-SQ baseline diagnosis of the N4 heavy/sparse B profile.

Observation only. diagnostic_metrics() subclasses the existing hog_sparse Metrics; the existing
test_hog_sparse coroutine, Traffic schedule, descriptor packing, TBs, reference models and
pin-history checks run unchanged. Nothing here drives a pin, alters stimulus or policy.

Per B sparse request (generated in phase B by sources1-3), cycles are trace-relative and
pre-edge (sampled in the read-only phase, before the closing edge commits):

  generation_to_acceptance = serialization_behind_accepted + serialization_behind_refused
                             + full_refused_cycles
    serialization: the request is pending but not its producer's offered head
                   (split by whether the offered head was accepted or refused that cycle);
    full_refused:  the request is the offered head, in_valid=1, refused because its FIFO
                   held DEPTH entries at the beginning of the cycle (admission delay).
  acceptance_to_fire = nonhead_cycles + head_cycles
    nonhead: same-source FIFO predecessors ahead (each fires during these cycles);
    head:    the request is its FIFO head, i.e. an eligible candidate; includes its fire.
  head_fires_* count the other grants issued while the request was head ("head eligible"):
    by role (heavy source0 / other sparse), by Main charged class (Low / High of another
    source), and by acceptance age of the granted head relative to this request.

Per-cycle rows (phases B and B_guard) are streamed to a deterministic gzip JSONL file.
"""
from collections import Counter, deque
import gzip
import hashlib
import io
import json

from hog_sparse import POLICIES, StreamStats, stats

SCHEMA = "cxl-main-sq-diagnosis-v1"
TRACE_FILE = "main_sq_trace.jsonl.gz"
DIAG_FILE = "main_sq_diagnosis.json"
VOLATILE = ("active_wall_s", "total_wall_s", "peak_rss_kib")
EFFECTIVE = {"H": "High", "B_H": "High", "L": "Low", "B_L": "Low"}
TAG_LSB = 73
GRANT_HISTORY = 4096
HEAD_KEYS = ("heavy", "other_sparse", "low_class", "other_high_class", "older", "same_age", "younger")
NONHEAD_KEYS = ("same_source", "heavy", "other_sparse")
COMPONENTS = ("generation_to_acceptance", "serialization_behind_accepted", "serialization_behind_refused",
              "serialization_cycles", "full_refused_cycles", "producer_predecessors",
              "acceptance_to_fire", "fifo_predecessors", "nonhead_cycles", "head_cycles",
              *("head_fires_"+k for k in HEAD_KEYS), *("nonhead_fires_"+k for k in NONHEAD_KEYS),
              "generation_to_fire")


def tag(d):
    return d >> TAG_LSB


def context(policy, o):
    """Policy scheduling context exactly as observed/derived by the existing TB this cycle."""
    if policy == 0:
        return dict(held=o.i_held, cand=o.i_cand_source if o.i_cand_valid else None)
    if policy == 1:
        return dict(held=o.i_held, ptr=o.i_ptr, used=o.i_used, turn_event=o.turn_event,
                    charged=o.charged if o.fire else None)
    return dict(held=o.i_held, classes=list(o.i_cls), turn=o.i_turn, used=o.i_used,
                offered=list(o.offered_ctx) if o.offered_ctx else None,
                charged=list(o.charged) if o.charged else None, visit_event=o.visit_event, pos=o.pos)


class Trace:
    """Deterministic (mtime0) gzip JSONL stream; hash covers the uncompressed lines."""
    def __init__(self, path=None):
        self.sha = hashlib.sha256()
        self.rows = 0
        self.closed = False
        self.raw = open(path, "wb") if path else None
        self.text = (io.TextIOWrapper(gzip.GzipFile(filename="", mode="wb", fileobj=self.raw, mtime=0),
                                      encoding="utf-8", newline="\n") if path else None)

    def write(self, row):
        assert not self.closed
        line = json.dumps(row, sort_keys=True, separators=(",", ":"))+"\n"
        self.sha.update(line.encode())
        self.rows += 1
        if self.text:
            self.text.write(line)

    def close(self):
        if not self.closed and self.text:
            self.text.close()
            self.raw.close()
        self.closed = True

    def as_dict(self, name):
        return dict(file=name, rows=self.rows, sha256_uncompressed=self.sha.hexdigest())


def read_trace(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            yield line, json.loads(line)


class Recorder:
    def __init__(self, time, policy, trace=None, n_src=4, depth=16):
        self.time, self.policy, self.n, self.depth = time, policy, n_src, depth
        self.trace = trace or Trace()
        self.pending, self.queued, self.done = {}, {}, []
        self.grants = deque(maxlen=GRANT_HISTORY)
        self.new_events = []
        self.class_maps = Counter()
        self.next_cycle = 0
        self.finalized = False

    def window(self, k):
        return self.time.b_start <= k < self.time.end

    def generate(self, k, events):
        self.new_events = list(events)
        if self.time.cohort(k) != "B":
            return
        for h, d in events:
            if h:
                t = tag(d)
                assert t not in self.pending and t not in self.queued, "duplicate tracked tag"
                self.pending[t] = dict(source=h, tag=t, generation=k, producer_predecessors=None,
                                       acceptance=None, fire=None, serialization_behind_accepted=0,
                                       serialization_behind_refused=0, full_refused_cycles=0,
                                       fifo_predecessors=None, nonhead_cycles=0, head_cycles=0,
                                       head_start=None, head=Counter(), nonhead=Counter(),
                                       head_charged=Counter(), ctx_generation=None, ctx_head=None,
                                       ctx_acceptance=None, ctx_fire=None)

    def observe(self, k, o, producers, fifo):
        """Pre-edge: fifo/producers are the beginning-of-cycle state, before Metrics updates."""
        assert k == self.next_cycle, "recorder cycle order"
        self.next_cycle += 1
        events, self.new_events = self.new_events, []
        if not (self.pending or self.queued or self.window(k)):
            return
        occ = [len(q) for q in fifo]
        assert list(o.i_count) == occ, "internal occupancy differs from pin-level FIFO history"
        ctx = context(self.policy, o)
        src = o.out_source if o.fire else None
        entry = fifo[src][0] if o.fire else None
        fcls = o.charged[0] if self.policy == 2 and o.fire else None
        if o.fire:
            self.grants.append((k, src, tag(entry[2]), fcls))
        seen, expected = 0, len(self.queued)
        for h in range(1, self.n):
            for i, (g, a, d) in enumerate(fifo[h]):
                r = self.queued.get(tag(d))
                if r is None:
                    continue
                seen += 1
                if i:
                    r["nonhead_cycles"] += 1
                    if o.fire:
                        r["nonhead"]["same_source" if src == h else "heavy" if src == 0 else "other_sparse"] += 1
                    continue
                r["head_cycles"] += 1
                if r["head_start"] is None:
                    r["head_start"], r["ctx_head"] = k, ctx
                if src == h:
                    self.fire(r, k, ctx)
                    continue
                assert o.fire, "tracked eligible head without a grant"
                c = r["head"]
                c["heavy" if src == 0 else "other_sparse"] += 1
                c["older" if entry[1] < a else "same_age" if entry[1] == a else "younger"] += 1
                if fcls:
                    c["low_class" if fcls == "Low" else "other_high_class"] += 1
                    r["head_charged"][f"{o.charged[0]}:{o.charged[1]}"] += 1
        assert seen == expected, "tracked FIFO request missing from pin-level history"
        seen = 0
        for h in range(1, self.n):
            pushed = o.push >> h & 1
            for i, (g, d) in enumerate(producers.pending[h]):
                r = self.pending.get(tag(d))
                if r is None:
                    continue
                seen += 1
                if r["producer_predecessors"] is None:
                    assert g == k == r["generation"], "first observation is not the generation cycle"
                    r["producer_predecessors"], r["ctx_generation"] = i, ctx
                if i:
                    r["serialization_behind_accepted" if pushed else "serialization_behind_refused"] += 1
                    continue
                assert o.in_valid >> h & 1 and o.in_desc[h] == d, "offered head not on input pins"
                if pushed:
                    r["acceptance"], r["ctx_acceptance"] = k, ctx
                    r["fifo_predecessors"] = occ[h]-int(src == h)
                else:
                    assert not o.in_ready >> h & 1 and occ[h] == self.depth, "refusal without full FIFO"
                    r["full_refused_cycles"] += 1
        assert seen == len(self.pending), "tracked producer request missing"
        for t in [t for t, r in self.pending.items() if r["acceptance"] == k]:
            self.queued[t] = self.pending.pop(t)
        if self.policy == 2 and self.window(k):
            self.class_maps["/".join(o.i_cls)] += 1
        if self.window(k):
            self.trace.write(dict(
                k=k, phase=self.time.phase(k), fire=o.fire, src=src, tag=tag(entry[2]) if o.fire else None,
                in_valid=o.in_valid, in_ready=o.in_ready, push=o.push, occ=occ,
                heads=[tag(q[0][2]) if q else None for q in fifo],
                acc=[[h, tag(producers.pending[h][0][1])] for h in range(self.n) if o.push >> h & 1],
                gen=[[h, tag(d)] for h, d in events if h], heavy_gen=sum(h == 0 for h, _ in events),
                pending=[len(q) for q in producers.pending], ctx=ctx))

    def fire(self, r, k, ctx):
        g, a = r["generation"], r["acceptance"]
        r.update(fire=k, ctx_fire=ctx, generation_to_acceptance=a-g, acceptance_to_fire=k-a,
                 generation_to_fire=k-g,
                 serialization_cycles=r["serialization_behind_accepted"]+r["serialization_behind_refused"])
        for key in HEAD_KEYS:
            r["head_fires_"+key] = r["head"][key]
        for key in NONHEAD_KEYS:
            r["nonhead_fires_"+key] = r["nonhead"][key]
        check_request(r, self.policy)
        r["grants_truncated"] = bool(self.grants) and len(self.grants) == GRANT_HISTORY and self.grants[0][0] > g
        r["grants"] = [list(x) for x in self.grants if x[0] >= g]
        r["head"], r["nonhead"], r["head_charged"] = dict(r["head"]), dict(r["nonhead"]), dict(r["head_charged"])
        self.done.append(r)
        del self.queued[r["tag"]]

    def after(self, k, fifo):
        for r in self.queued.values():
            if r["acceptance"] == k:
                g, a, d = fifo[r["source"]][-1]
                assert (tag(d), g, a) == (r["tag"], r["generation"], k), "acceptance differs from Metrics"

    def finalize(self, metrics, result=None):
        assert not self.finalized and not self.pending and not self.queued, "unfinished tracked requests"
        self.finalized = True
        self.trace.close()
        done = sorted(self.done, key=lambda r: (r["generation"], r["source"], r["tag"]))
        cohort = metrics.cohorts["B"]
        assert [sum(r["source"] == h for r in done) for h in range(self.n)] == cohort["generated_per_source"]
        pooled = {c: StreamStats() for c in COMPONENTS}
        per = [{c: StreamStats() for c in COMPONENTS} for _ in range(self.n)]
        for r in done:
            for c in COMPONENTS:
                pooled[c].add(r[c])
                per[r["source"]][c].add(r[c])
        for s in ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire"):
            assert pooled[s].hist == cohort["pooled_sparse"][s].hist, f"recorder {s} differs from Metrics"
            for h in range(1, self.n):
                assert per[h][s].hist == cohort["per_source"][h][s].hist, f"recorder {s} source{h} differs"
        p99 = pooled["generation_to_fire"].p99()
        tail = [r for r in done if r["generation_to_fire"] >= p99]
        for r in done:
            if r["generation_to_fire"] < p99:
                r.pop("grants")
        totals = {c: sum(r[c] for r in done) for c in COMPONENTS}
        out = dict(schema=SCHEMA, policy=POLICIES[self.policy], policy_param=self.policy,
                   window=self.time.window, depth=self.depth, b_start=self.time.b_start, trace_end=self.time.end,
                   requests=len(done), direct_g2f_p99_nearest_rank=p99, tail_threshold=p99,
                   tail_requests=len(tail), totals=totals,
                   pooled={c: stats(v) for c, v in pooled.items()},
                   per_source=[{c: stats(v) for c, v in row.items()} for row in per],
                   tail_totals={c: sum(r[c] for r in tail) for c in COMPONENTS},
                   head_charged_contexts=dict(sum((Counter(r["head_charged"]) for r in done), Counter())),
                   b_window_class_maps=dict(self.class_maps),
                   trace=self.trace.as_dict(TRACE_FILE), per_request=done,
                   method="passive pre-edge observation of the unchanged hog_sparse run; tail = direct G2F >= nearest-rank P99",
                   limitations="diagnostic decomposition only; no causal or scheduler claim")
        if result is not None:
            out.update(seed=result["seed"], trace_sha256=result["trace_sha256"],
                       metrics_p99=result["metrics"]["cohorts"]["B"]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"])
            assert out["metrics_p99"] == p99
        return out


def check_request(r, policy):
    g, a, f = r["generation"], r["acceptance"], r["fire"]
    assert g <= a < f and r["head_start"] is not None and a < r["head_start"] <= f
    assert a-g == r["serialization_cycles"]+r["full_refused_cycles"], "G2A decomposition"
    assert f-a == r["nonhead_cycles"]+r["head_cycles"] and r["head_start"] == f-r["head_cycles"]+1, "A2F decomposition"
    assert r["nonhead_fires_same_source"] == r["fifo_predecessors"], "same-source predecessors"
    assert r["nonhead_cycles"] == sum(r["nonhead_fires_"+k] for k in NONHEAD_KEYS), "nonhead bubble"
    waits = r["head_cycles"]-1
    assert waits == r["head_fires_heavy"]+r["head_fires_other_sparse"], "head bubble"
    assert waits == r["head_fires_older"]+r["head_fires_same_age"]+r["head_fires_younger"]
    if policy == 2:
        assert waits == r["head_fires_low_class"]+r["head_fires_other_high_class"], "class split"
    else:
        assert r["head_fires_low_class"] == r["head_fires_other_high_class"] == 0


def diagnostic_metrics(base, policy, trace):
    """Subclass of the given (existing hog_sparse) Metrics that also feeds a Recorder."""
    class _DiagnosticMetrics(base):
        def __init__(self, window):
            super().__init__(window)
            self.recorder = Recorder(self.time, policy, trace)

        def generate(self, k, events):
            super().generate(k, events)
            self.recorder.generate(k, events)

        def observe(self, k, o, producers, events=()):
            self.recorder.observe(k, o, producers, self.fifo)
            super().observe(k, o, producers, events)
            self.recorder.after(k, self.fifo)
    return _DiagnosticMetrics


def replay(rows, policy, n_src=4, depth=16):
    """Second, independent reconstruction of the sparse joins from the trace rows only."""
    fifo = [deque() for _ in range(n_src)]
    prod = [deque() for _ in range(n_src)]
    rec = {}
    first = True
    for row in rows:
        k = row["k"]
        if first:
            gen = [sum(h == x for x, _ in row["gen"]) for h in range(n_src)]
            assert row["occ"][1:] == [0]*(n_src-1) and row["pending"][1:] == gen[1:], "sparse state not empty at B start"
            first = False
        for h, t in row["gen"]:
            prod[h].append(t)
            rec[t] = Counter(source=h, generation=k)
        for h in range(1, n_src):
            assert len(fifo[h]) == row["occ"][h] and (fifo[h][0] if fifo[h] else None) == row["heads"][h]
            assert len(prod[h]) == row["pending"][h]
        src, charged = row["src"], (row["ctx"].get("charged") if policy == 2 else None)
        for h in range(1, n_src):
            for i, t in enumerate(fifo[h]):
                r = rec[t]
                assert row["fire"], "bubble while sparse work queued"
                if i:
                    r["nonhead_cycles"] += 1
                    r["nonhead_fires_"+("same_source" if src == h else "heavy" if src == 0 else "other_sparse")] += 1
                    continue
                r["head_cycles"] += 1
                if src != h:
                    r["head_fires_"+("heavy" if src == 0 else "other_sparse")] += 1
                    if charged:
                        r["head_fires_"+("low_class" if charged[0] == "Low" else "other_high_class")] += 1
            pushed = row["push"] >> h & 1
            for i, t in enumerate(prod[h]):
                if i:
                    rec[t]["serialization_behind_"+("accepted" if pushed else "refused")] += 1
                elif not pushed:
                    assert not row["in_ready"] >> h & 1 and row["occ"][h] == depth
                    rec[t]["full_refused_cycles"] += 1
        if row["fire"] and src:  # src0 heavy history before B is not reconstructed
            t = fifo[src].popleft()
            assert t == row["tag"]
            rec[t]["fire"] = k
        for h, t in row["acc"]:
            if h:
                assert prod[h].popleft() == t
                fifo[h].append(t)
                rec[t]["acceptance"] = k
                rec[t]["fifo_predecessors"] = len(fifo[h])-1
    assert not any(fifo[1:]) and not any(prod[1:]), "sparse work left at trace end"
    return rec


REPLAY_KEYS = ("source", "generation", "acceptance", "fire", "fifo_predecessors", "nonhead_cycles", "head_cycles",
               "serialization_behind_accepted", "serialization_behind_refused", "full_refused_cycles",
               *("head_fires_"+k for k in ("heavy", "other_sparse", "low_class", "other_high_class")),
               *("nonhead_fires_"+k for k in NONHEAD_KEYS))


def check_diagnosis(diag, result, trace_path=None):
    """Runner-side gate: exact cross-checks against the accepted-format metrics and the trace file."""
    assert diag["schema"] == SCHEMA and diag["policy_param"] == result["policy_param"]
    assert diag["seed"] == result["seed"] and diag["trace_sha256"] == result["trace_sha256"]
    assert diag["window"] == result["window"]
    cohort = result["metrics"]["cohorts"]["B"]
    assert diag["requests"] == sum(cohort["generated_per_source"]) == len(diag["per_request"])
    p = diag["policy_param"]
    for s in ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire"):
        assert {int(k): v for k, v in diag["pooled"][s]["histogram"].items()} == \
               {int(k): v for k, v in cohort["pooled_sparse"][s]["histogram"].items()}, f"{s} histogram"
    p99 = cohort["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"]
    assert diag["direct_g2f_p99_nearest_rank"] == diag["metrics_p99"] == p99
    for r in diag["per_request"]:
        check_request(r, p)
        assert ("grants" in r) == (r["generation_to_fire"] >= p99)
    assert diag["tail_requests"] == sum(r["generation_to_fire"] >= p99 for r in diag["per_request"])
    if trace_path is None:
        return
    sha, rows = hashlib.sha256(), []
    for line, row in read_trace(trace_path):
        sha.update(line.encode())
        rows.append(row)
    t = diag["trace"]
    assert t["rows"] == len(rows) == diag["trace_end"]-diag["b_start"] and t["sha256_uncompressed"] == sha.hexdigest()
    assert [r["k"] for r in rows] == list(range(diag["b_start"], diag["trace_end"]))
    rec = replay(rows, p, depth=diag["depth"])
    tracked = {r["tag"]: r for r in diag["per_request"]}
    assert set(rec) == set(tracked), "trace-generated sparse population differs"
    for t, r in tracked.items():
        for key in REPLAY_KEYS:
            assert rec[t][key] == r[key], f"replay {key} tag{t}"
