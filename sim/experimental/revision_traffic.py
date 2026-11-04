"""Exogenous revision traffic and passive accepted-pin accounting (no cocotb)."""
from collections import deque
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
for folder in ("sim/common", "sim/performance", "scripts"):
    sys.path.insert(0, str(ROOT / folder))
from hog_sparse import Traffic as LegacyTraffic, Summary
from followup import Gaps, STAGES, StreamProducers, StreamStats
from revision_statistics import histogram_summary


def distribution(s):
    return dict(histogram=dict(sorted(s.hist.items())),
                **(histogram_summary(s.hist) if s.count else
                   dict(count=0, mean=None, max=None, p50=None, p90=None, p99=None, p999=None)))


class Traffic:
    """Default events, descriptor RNG and trace hash exactly match legacy HOG.

    Rate/ready/burst changes apply after training; source permutation starts at reset.
    Cold replay
    consumes the corresponding training RNG stream without driving training edges.
    """
    def __init__(self, job, cold=False):
        self.job = dict(job)
        self.n, self.window, self.seed = (job[k] for k in ("n_src", "window", "seed"))
        assert self.n in (4, 8, 16) and self.window in (256, 5_000_000)
        assert job["depth"] in (8, 16, 32)
        assert 0 <= job["heavy_source"] < self.n
        assert job["ready"] in ("always", "bernoulli-0.75", "periodic-48/64")
        assert job["heavy_rate"] in (1, .5, .8, .9)
        assert (job["burst_size"], job["burst_period"]) in ((8, 1024), (32, 4096))
        self.adaptation = job["group"] == "adaptation"
        assert cold is False or cold in ("A", "B"), "cold replay must select independent A or B"
        assert not (cold and self.adaptation)
        self.training = 0 if cold or self.adaptation else 2*self.window
        self.cold, self.cold_cohort = bool(cold), cold or None
        # Relabel canonical streams together, preserving tags, payloads and event order.
        self.source_permutation = list(range(self.n))
        if not self.adaptation:
            h = job["heavy_source"]
            self.source_permutation[0], self.source_permutation[h] = h, 0
        self.guard_cycles = 1024
        self.a_end = self.training + 100_000
        self.b_start = self.a_end + self.guard_cycles
        self.b_end = self.b_start + 102_400
        self.end = 6*self.window if self.adaptation else self.b_end + self.guard_cycles
        self.shift = 0
        if cold == "A":
            self.shift = 2*self.window
            self.b_end = self.b_start
            self.end = self.b_start
        elif cold == "B":
            self.shift = 2*self.window + 100_000 + self.guard_cycles
            self.a_end = self.b_start = 0
            self.b_end = 102_400
            self.end = self.b_end + self.guard_cycles
        if self.window == 5_000_000 and not cold and not self.adaptation:
            assert self.end < 3*self.window, "measurement must precede third close"
        self.bounds = ((2*self.window, 4*self.window, self.end) if self.adaptation else
                       (self.training, self.a_end, self.b_start, self.b_end, self.end))
        self.phases = (("role0", "role3", "role0-return", "drain") if self.adaptation else
                       ("training", "A", "A_guard", "B", "B_guard", "drain"))
        self.cohorts = ("role0", "role3", "role0-return") if self.adaptation else ("cold", "A", "B")
        self.legacy = LegacyTraffic(self.seed, self.window)
        self.arrivals = [random.Random(f"hog-sparse-v1:{self.seed}:arrival:{h}") for h in range(self.n)]
        self.descriptors = [random.Random(f"hog-sparse-v1:{self.seed}:descriptor:{h}") for h in range(self.n)]
        blocks = (102_400 + job["burst_period"] - 1)//job["burst_period"]
        self.offsets = []
        for h in range(self.n):
            rng = random.Random(f"hog-sparse-v1:{self.seed}:offset:{h}")
            self.offsets.append([rng.randrange(job["burst_period"]) for _ in range(blocks)])
        self.heavy_rng = random.Random(f"revision-v1:{self.seed}:heavy")
        self.ready_rng = random.Random(f"revision-v1:{self.seed}:ready")
        self.serial = self.next_cycle = self.ready_count = 0
        self.generated = [0]*self.n
        self.exact_legacy = (self.n == 4 and not cold and not self.adaptation and
                             job["heavy_source"] == 0 and job["heavy_rate"] == 1 and
                             job["ready"] == "always" and job["burst_size"] == 8)
        self.config = (self.legacy.config if self.exact_legacy else
                       dict(generator="cxl-revision-traffic-v1", seed=self.seed, n_src=self.n,
                            window=self.window, cold=cold, adaptation=self.adaptation,
                            ready=job["ready"], heavy_source=job["heavy_source"],
                            heavy_rate=job["heavy_rate"], burst_size=job["burst_size"],
                            burst_period=job["burst_period"], phase_cycles=list(self.bounds),
                            sparse_guard_cycles=self.guard_cycles,
                            source_permutation=self.source_permutation,
                            perturbation_after_training=(not self.adaptation and
                                (job["ready"] != "always" or job["heavy_rate"] != 1 or
                                 job["burst_size"] != 8))))
        self.sha = hashlib.sha256((json.dumps(self.config, sort_keys=True, separators=(",", ":"))+"\n").encode())
        if cold:
            # Replay RNG/tags exactly; future work is never passed to any scheduler.
            for k in range(self.shift):
                phase = ("training" if k < 2*self.window else
                         "A" if k < 2*self.window+100_000 else "A_guard")
                measured = k >= 2*self.window
                self._events(k, phase, measured)
                if measured and job["ready"] == "bernoulli-0.75":
                    self.ready_rng.random()

    def phase(self, k):
        return self.phases[next((i for i, b in enumerate(self.bounds) if k < b), len(self.bounds))]

    def cohort(self, k):
        p = self.phase(k)
        if p in ("A", "B", "role0", "role3", "role0-return"):
            return p
        if not self.cold and not self.adaptation and self.window == 5_000_000:
            if self.training-101024 <= k < self.training-1024:
                return "cold"
        return None

    def heavy(self, k):
        if self.adaptation:
            return 3 if 2*self.window <= k < 4*self.window else 0
        return self.source_permutation[0]

    def _events(self, k, phase, measured):
        heavy = (3 if 2*self.window <= k < 4*self.window else 0) if self.adaptation else 0
        rate = self.job["heavy_rate"] if measured else 1
        sources = [heavy] if rate == 1 or self.heavy_rng.random() < rate else []
        if phase in ("training", "A", "role0", "role3", "role0-return"):
            sources += [h for h in range(self.n) if h != heavy and self.arrivals[h].randrange(128) == 0]
        elif phase == "B":
            block, offset = divmod(k-(self.b_start+self.shift), self.job["burst_period"])
            sources += [h for h in range(self.n) if h != heavy and self.offsets[h][block] == offset
                        for _ in range(self.job["burst_size"])]
        events = []
        for h in sources:
            assert self.serial < 2**32, "tag space exhausted"
            d = self.serial << 73 | self.descriptors[h].getrandbits(73)
            self.serial += 1
            events.append((self.source_permutation[h], d))
        return events

    def step(self, k):
        assert k == self.next_cycle and k < self.end
        self.next_cycle += 1
        if self.exact_legacy:
            events, ready = self.legacy.step(k)
        else:
            measured = self.adaptation or k >= self.training
            events = self._events(k+self.shift, self.phase(k), measured)
            ready = 1
            if measured and self.job["ready"] == "bernoulli-0.75":
                ready = int(self.ready_rng.random() < .75)
            elif measured and self.job["ready"] == "periodic-48/64":
                pos = k+self.shift-2*self.window if self.cold else k-self.training
                ready = int(pos % 64 < 48)
            self.sha.update(f"{k}:{ready}:".encode())
            for h, d in events:
                self.sha.update(bytes([h])+d.to_bytes(14, "big"))
            self.sha.update(b"\n")
        self.ready_count += ready
        for h, _ in events:
            self.generated[h] += 1
        return events, ready

    @property
    def sha256(self):
        return self.legacy.sha256 if self.exact_legacy else self.sha.hexdigest()


class Metrics:
    """Independent pin FIFO, full-before-pop/hold checks and exact generation cohorts."""
    def __init__(self, traffic):
        self.t = traffic
        n = traffic.n
        self.fifo = [deque() for _ in range(n)]
        self.rows = {p: dict(cycles=0, ready=0, generated=[0]*n, offered=[0]*n,
                             accepted=[0]*n, fired=[0]*n, eligible_ready_opportunities=0,
                             avoidable_bubbles=0,
                             backlog=[Summary() for _ in range(n)], occupancy=[Summary() for _ in range(n)],
                             gaps=[Gaps() for _ in range(n)]) for p in traffic.phases}
        self.cohorts = {c: dict(generated=[0]*n, completed=[0]*n,
                               completed_by_phase={p: [0]*n for p in traffic.phases},
                               per_source=[{s: StreamStats() for s in STAGES} for _ in range(n)],
                               pooled_sparse={s: StreamStats() for s in STAGES})
                        for c in traffic.cohorts}
        self.held = None
        self.last = None
        self.snapshots = {}

    def observe(self, k, events, producers, ready, in_ready, valid, source, desc):
        p, n = self.t.phase(k), self.t.n
        row = self.rows[p]
        if p != self.last:
            if self.last is not None:
                for g in self.rows[self.last]["gaps"]:
                    g.boundary(False)
            for h, g in enumerate(row["gaps"]):
                g.boundary(bool(self.fifo[h]))
            self.last = p
        for h, _ in events:
            row["generated"][h] += 1
            c = self.t.cohort(k)
            if c:
                self.cohorts[c]["generated"][h] += 1
        offers = producers.offers()
        occ = [len(q) for q in self.fifo]
        assert in_ready == sum(int(v < self.t.job["depth"]) << h for h, v in enumerate(occ)), "full-before-pop"
        fire = bool(valid and ready)
        eligible_ready = bool(ready and any(occ))
        row["eligible_ready_opportunities"] += int(eligible_ready)
        row["avoidable_bubbles"] += int(eligible_ready and not fire)
        assert row["avoidable_bubbles"] == 0, "avoidable eligible-ready bubble"
        assert bool(valid) == any(occ), "no bypass/no control bubble"
        if self.held is not None:
            assert valid and (source, desc) == self.held, "105-bit output hold"
        self.held = (source, desc) if valid and not ready else None
        row["cycles"] += 1
        row["ready"] += ready
        for h in range(n):
            row["offered"][h] += int(h in offers)
            row["backlog"][h].add(len(producers.pending[h]))
            row["occupancy"][h].add(occ[h])
        if fire:
            g, a, d = self.fifo[source].popleft()
            assert d == desc and k > a >= g, "integrity/order/no bypass"
            row["fired"][source] += 1
            c = self.t.cohort(g)
            if c:
                cr = self.cohorts[c]
                cr["completed"][source] += 1
                cr["completed_by_phase"][p][source] += 1
                for s, v in zip(STAGES, (a-g, k-a, k-g)):
                    cr["per_source"][source][s].add(v)
                    if source != self.t.heavy(g):
                        cr["pooled_sparse"][s].add(v)
        for h in range(n):
            if h in offers and in_ready >> h & 1:
                g, d = producers.accept(h, k)
                self.fifo[h].append((g, k, d))
                row["accepted"][h] += 1
            row["gaps"][h].observe(bool(occ[h]), fire and source == h, ready, bool(self.fifo[h]))

    def guard(self, k, producers):
        name = self.t.phase(k-1)
        self.snapshots[name] = dict(next_cycle=k, fifo=[len(q) for q in self.fifo],
                                   producer_backlog=[len(q) for q in producers.pending])
        if self.t.adaptation:
            return
        if name in ("training", "A_guard", "B_guard"):
            c = {"training": "cold", "A_guard": "A", "B_guard": "B"}[name]
            heavy = self.t.heavy(k-1)
            assert all(self.cohorts[c]["generated"][h] == self.cohorts[c]["completed"][h]
                       for h in range(self.t.n) if h != heavy), "incomplete sparse background-on guard"
            # Training keeps generating sparse work after the cold cohort's guard.
            if name != "training":
                assert all(not producers.pending[h] and not self.fifo[h]
                           for h in range(self.t.n) if h != heavy), "sparse pending before heavy-off"

    def complete(self, producers):
        assert not producers.backlog() and not any(self.fifo) and self.held is None
        totals = [sum(sum(row[key]) for row in self.rows.values()) for key in ("generated", "accepted", "fired")]
        assert totals[0] == totals[1] == totals[2] == producers.generated == producers.accepted
        for c in self.cohorts.values():
            assert c["generated"] == c["completed"], "incomplete generation cohort"

    def as_dict(self):
        if self.last:
            for g in self.rows[self.last]["gaps"]:
                g.boundary(False)
        phases = {p: {k: ([v.as_dict() for v in value] if k in ("backlog", "occupancy", "gaps") else value)
                      for k, value in row.items()} for p, row in self.rows.items()}
        for row in phases.values():
            denominator = row["eligible_ready_opportunities"]
            row["eligible_ready_utilization"] = sum(row["fired"])/denominator if denominator else None
        cohorts = {c: {**{k: v for k, v in r.items() if k not in ("per_source", "pooled_sparse")},
                       "per_source": [{s: distribution(v) for s, v in h.items()} for h in r["per_source"]],
                       "pooled_sparse": {s: distribution(v) for s, v in r["pooled_sparse"].items()}}
                   for c, r in self.cohorts.items()}
        return dict(phases=phases, cohorts=cohorts, snapshots=self.snapshots)
