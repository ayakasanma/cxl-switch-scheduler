"""N4 descriptor follow-up: deterministic traffic and passive pin-history metrics.

Time is trace-relative, beginning at the first non-reset cycle. Cohorts use half-open
generation/acceptance intervals. All generated work is drained, including producer backlog;
this deliberately differs from the old primary boundary-only drain. No model timing is used.
"""
from __future__ import annotations

from collections import deque
from itertools import combinations
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "switch_top_fai"))
from fai_stream import StreamStats, StreamProducers

SCHEMA = "cxl-descriptor-followup-v1"
POLICIES = ("FCFS", "RR", "FAI_MAIN")
LOADS = {"load030": .30, "load090": .90, "load120": 1.20, "ready075": .60}
LOW_SUBSETS = tuple(s for k in (1, 2, 3) for s in combinations(range(4), k))
PHASES = ("warmup", "measurement", "drain")
STAGES = ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire")


def stats(s):
    return {**s.as_dict(), "histogram": dict(sorted(s.hist.items()))}


def check_drain_budget(elapsed, bound):
    assert elapsed < bound, "generated-population drain timeout"


class Traffic:
    """One streaming trace; descriptor tags are serials (no reuse, no completed-tag set).

    Training spreads exact floor(.40W)/k per Low and floor(.05W) per High
    over W-4 cycles, leaving four quiet closing cycles. Legacy k=1 is unchanged.
    """
    def __init__(self, case, seed, warmup, measurement, window=5_000_000, low_sources=(0,)):
        assert case in (*LOADS, "trained", "finite", "placement")
        assert warmup >= 0 and measurement > 0 and window >= 64
        self.low_sources = tuple(low_sources)
        assert all(type(h) is int for h in self.low_sources) and self.low_sources in LOW_SUBSETS, "invalid Low subset"
        assert case == "placement" or self.low_sources == (0,), "legacy Low subset changed"
        if case == "placement":
            assert (seed, window, warmup, measurement) == (509, 256, 512, 240)
            assert warmup + measurement < 3 * window, "measurement reaches next classification"
        if case == "trained":
            assert warmup == 2 * window
        if case == "finite":
            assert warmup == 0 and measurement == 1024
        self.config = dict(generator="descriptor-followup-traffic-v1", case=case, seed=seed,
                           warmup=warmup, measurement=measurement, window=window, n_src=4)
        if case == "placement":
            self.config.update(generator="descriptor-placement-traffic-v1", low_sources=list(self.low_sources),
                               training_counts=self.training_counts(window), quiet_closing_cycles=4,
                               fill_cycles=128, measured_generation_per_source_per_cycle=1, ready=1)
        self.case, self.warmup, self.end, self.window = case, warmup, warmup + measurement, window
        self.rng = random.Random(json.dumps(self.config, sort_keys=True))
        self.serial = 0
        self.next_cycle = 0
        self.sha = hashlib.sha256((json.dumps(self.config, sort_keys=True) + "\n").encode())
        self.generated = [0] * 4
        self.ready_count = 0

    def training_counts(self, window):
        return [2 * window // 5 // len(self.low_sources) if h in self.low_sources else window // 20
                for h in range(4)]

    def ready(self, k):
        return int(k % 4 != 3) if self.case in ("ready075", "finite") else 1

    def step(self, k):
        assert k == self.next_cycle and k < self.end
        self.next_cycle += 1
        if self.case == "finite":
            # 32 bursts, 32 descriptors/source per burst; last release at cycle 1023.
            sources = range(4) if k % 32 == 31 else ()
            sources = [h for h in sources for _ in range(32)]
        elif self.case in ("trained", "placement"):
            if k >= self.warmup:
                sources = range(4)  # persistent demand; finite overload transient
            else:
                pos, span = k % self.window, self.window - 4
                counts = self.training_counts(self.window)
                sources = [h for h, count in enumerate(counts) if pos < span and
                           ((pos + 1) * count // span > pos * count // span)]
        else:
            sources = [h for h in range(4) if self.rng.random() < LOADS[self.case] / 4]
        events = []
        for h in sources:
            assert self.serial < 2**32, "tag space exhausted"
            d = (self.serial << 73) | self.rng.getrandbits(73)
            self.serial += 1
            self.generated[h] += 1
            events.append((h, d))
        ready = self.ready(k)
        self.ready_count += ready
        self.sha.update(f"{k}:{ready}:".encode())
        for h, d in events:
            self.sha.update(bytes([h]) + d.to_bytes(14, "big"))
        self.sha.update(b"\n")
        return events, ready

    @property
    def sha256(self):
        return self.sha.hexdigest()


class Gaps:
    """FIFO-nonempty episodes, measured in wall slots and sink-ready opportunities.

    Initial delay includes the first eligible slot; inter-fire gaps count slots after
    the preceding fire. Phase boundaries right-censor the old segment and left-censor
    the new one. Left-censored completed segments are separate from full gaps.
    """
    def __init__(self):
        self.active = False
        self.left = False
        self.initial = True
        self.wall = self.ready = 0
        self.samples = {}
        self.empty_terminated = 0

    def record(self, kind):
        row = self.samples.setdefault(kind, (StreamStats(), StreamStats()))
        row[0].add(self.wall)
        row[1].add(self.ready)

    def boundary(self, left):
        if self.active:
            self.record("right_censored")
        self.active = False
        self.left = left
        self.wall = self.ready = 0

    def observe(self, nonempty, fire, ready, post_nonempty):
        if nonempty:
            if not self.active:
                self.active = True
                self.initial = True
            self.wall += 1
            self.ready += ready
            if fire:
                kind = "left_censored_completed" if self.left else ("initial" if self.initial else "inter_service")
                self.record(kind)
                self.wall = self.ready = 0
                self.initial = self.left = False
            if not post_nonempty:
                self.record("terminated_by_empty")
                self.empty_terminated += 1
                self.active = False
                self.left = False
        else:
            assert not fire

    def as_dict(self):
        return {"empty_terminated_episodes": self.empty_terminated,
                "samples": {k: {"wall_cycles": stats(a), "eligible_ready_opportunities": stats(b)}
                            for k, (a, b) in self.samples.items()}}


class Metrics:
    def __init__(self, warmup, measurement):
        self.warmup, self.end = warmup, warmup + measurement
        self.fifo = [deque() for _ in range(4)]  # (generation cycle, acceptance cycle, descriptor)
        self.phase_rows = {p: dict(cycles=0, ready=0, fires=0, idle_ready=0,
                                  output_stall_cycles=0, idle_not_ready=0,
                                  eligible_ready=0, avoidable_bubbles=0,
                                  generated=[0]*4, accepted=[0]*4, fired=[0]*4,
                                  occupancy=[StreamStats() for _ in range(4)],
                                  producer_backlog=[StreamStats() for _ in range(4)],
                                  fifo_nonempty=[0]*4, fifo_nonempty_ready=[0]*4,
                                  gaps=[Gaps() for _ in range(4)]) for p in PHASES}
        self.latencies = {axis: {p: [{s: StreamStats() for s in STAGES} for _ in range(4)]
                                for p in PHASES} for axis in ("generation", "acceptance")}
        self.completions = {g: {a: {f: [0]*4 for f in PHASES} for a in PHASES} for g in PHASES}
        self.snapshots = {}
        self.last_phase = None
        self.next_cycle = 0

    def phase(self, k):
        return "warmup" if k < self.warmup else "measurement" if k < self.end else "drain"

    def generate(self, k, events):
        for h, _ in events:
            self.phase_rows[self.phase(k)]["generated"][h] += 1

    def observe(self, k, o, producers):
        assert k == self.next_cycle
        self.next_cycle += 1
        phase = self.phase(k)
        row = self.phase_rows[phase]
        if phase != self.last_phase:
            if self.last_phase is not None:
                for gap in self.phase_rows[self.last_phase]["gaps"]:
                    gap.boundary(False)
            for h, gap in enumerate(row["gaps"]):
                gap.boundary(bool(self.fifo[h]))
            self.last_phase = phase
        occ = [len(q) for q in self.fifo]
        # Every readiness/occupancy datum below is independently reconstructed from pin history.
        assert o.in_ready == sum((c < 16) << h for h, c in enumerate(occ))
        assert o.out_valid == int(any(occ))
        row["cycles"] += 1
        row["ready"] += o.out_ready
        row["fires"] += o.fire
        row["idle_ready"] += int(o.out_ready and not o.fire)
        row["output_stall_cycles"] += int(not o.out_ready and o.out_valid)
        row["idle_not_ready"] += int(not o.out_ready and not o.out_valid)
        row["eligible_ready"] += int(o.out_ready and any(occ))
        bubble = int(o.out_ready and any(occ) and not o.fire)
        row["avoidable_bubbles"] += bubble
        assert not bubble, "avoidable output bubble with eligible FIFO work"
        for h in range(4):
            row["occupancy"][h].add(occ[h])
            row["producer_backlog"][h].add(len(producers.pending[h]))
            row["fifo_nonempty"][h] += int(occ[h] > 0)
            row["fifo_nonempty_ready"][h] += int(occ[h] > 0 and o.out_ready)
        if o.fire:
            h = o.out_source
            g, a, d = self.fifo[h].popleft()
            assert d == o.out_desc and k > a >= g
            row["fired"][h] += 1
            gp, ap = self.phase(g), self.phase(a)
            self.completions[gp][ap][phase][h] += 1
            for axis, cohort in (("generation", gp), ("acceptance", ap)):
                dest = self.latencies[axis][cohort][h]
                dest["acceptance_to_fire"].add(k - a)
                dest["generation_to_fire"].add(k - g)
        for h in range(4):
            if o.push >> h & 1:
                g, d = producers.accept(h, k)
                assert d == o.in_desc[h]
                self.fifo[h].append((g, k, d))
                row["accepted"][h] += 1
                for axis, cohort in (("generation", self.phase(g)), ("acceptance", phase)):
                    self.latencies[axis][cohort][h]["generation_to_acceptance"].add(k - g)
            row["gaps"][h].observe(bool(occ[h]), bool(o.fire and o.out_source == h),
                                     o.out_ready, bool(self.fifo[h]))

    def snapshot(self, name, k, producers):
        # Boundary k is the NEXT cycle: pending ages are right-censored at k, not at k-1.
        pending = []
        for h in range(4):
            generated = {p: StreamStats() for p in PHASES}
            accepted = {p: StreamStats() for p in PHASES}
            accepted_gen = {p: StreamStats() for p in PHASES}
            for g, _ in producers.pending[h]:
                generated[self.phase(g)].add(k-g)
            for g, a, _ in self.fifo[h]:
                accepted[self.phase(a)].add(k-a)
                accepted_gen[self.phase(g)].add(k-g)
            pending.append(dict(producer_pending_by_generation={p: stats(s) for p,s in generated.items()},
                                fifo_pending_by_acceptance={p: stats(s) for p,s in accepted.items()},
                                fifo_pending_generation_age={p: stats(s) for p,s in accepted_gen.items()}))
        self.snapshots[name] = dict(next_trace_cycle=k, per_source=pending,
                                    fifo_occupancy=[len(q) for q in self.fifo],
                                    producer_backlog=[len(q) for q in producers.pending])

    def assert_complete(self, producers, issued, completed):
        generated = sum(sum(r["generated"]) for r in self.phase_rows.values())
        accepted = sum(sum(r["accepted"]) for r in self.phase_rows.values())
        fired = sum(r["fires"] for r in self.phase_rows.values())
        assert not producers.backlog() and not any(self.fifo), "incomplete generated population"
        assert generated == producers.generated == accepted == producers.accepted == fired == issued == completed
        for axis in self.latencies.values():
            for cohort in axis.values():
                for src in cohort:
                    assert len({v.count for v in src.values()}) == 1, "incomplete latency cohort"

    def as_dict(self):
        if self.last_phase is not None:
            for gap in self.phase_rows[self.last_phase]["gaps"]:
                if gap.active:
                    gap.boundary(False)
        phases = {}
        for phase, row in self.phase_rows.items():
            phases[phase] = {k: ([stats(s) for s in v] if k in ("occupancy", "producer_backlog") else
                                 [g.as_dict() for g in v] if k == "gaps" else v) for k,v in row.items()}
            cycles, ready = row["cycles"], row["ready"]
            phases[phase]["successful_slot_utilization"] = row["fires"] / cycles if cycles else None
            phases[phase]["ready_opportunity_utilization"] = row["fires"] / ready if ready else None
        return dict(phases=phases, snapshots=self.snapshots, completion_cohorts=self.completions,
                    latency_by_cohort={axis: {p: [{s: stats(v) for s,v in h.items()} for h in sources]
                                             for p,sources in cohorts.items()}
                                       for axis,cohorts in self.latencies.items()})


def check_result(data, expected, trace_hash):
    """Acceptance gate independent of simulator status; failures are never waived."""
    assert data["schema"] == SCHEMA
    for key, value in expected.items():
        assert data[key] == value, f"{key}: {data.get(key)!r}, expected {value!r}"
    assert data["trace_sha256"] == trace_hash
    assert data["outstanding_after_drain"] == 0 and data["generated_unaccepted_after_drain"] == 0
    m = data["metrics"]
    assert m["phases"]["warmup"]["cycles"] == data["warmup_cycles"]
    assert m["phases"]["measurement"]["cycles"] == data["measurement_cycles"]
    totals = [sum(sum(p[key]) for p in m["phases"].values()) for key in ("generated", "accepted", "fired")]
    assert totals[0] == totals[1] == totals[2] == data["responses"]["issued"] == data["responses"]["completed"]
    assert all(p["avoidable_bubbles"] == 0 for p in m["phases"].values())
    assert all(p["fires"] + p["idle_ready"] + p["output_stall_cycles"] + p["idle_not_ready"] == p["cycles"]
               for p in m["phases"].values())
    if data["case"] == "finite":
        assert totals[0] == 4096
    if data["case"] == "placement":
        low = tuple(data["low_sources"])
        assert low in LOW_SUBSETS, "invalid Low subset"
        assert data["sensitivity_evidence"] is True and data["production_evidence"] is False
        assert data["infrastructure_only"] is False
        assert (data["seed"], data["window"], data["warmup_cycles"], data["measurement_cycles"]) == (509,256,512,240)
        assert data["warmup_cycles"] + data["measurement_cycles"] < 3 * data["window"]
        traffic = Traffic("placement", 509, 512, 240, 256, low)
        assert data["trace_config"] == traffic.config, "wrong subset/config"
        counts = traffic.training_counts(256)
        assert data["trace_generated_per_source"] == [2*b+240 for b in counts]
        assert data["trace_ready_cycles"] == 752
        windows = data["training_windows"]
        assert len(windows) == 2
        for i, w in enumerate(windows):
            assert w["closing_trace_cycle"] == (i+1)*256-1
            assert w["counts"] == counts and w["total"] == sum(counts)
            assert w["evidence"] == ["DOWN" if h in low else "KEEP" for h in range(4)]
            if data["policy_param"] == 2:
                assert w["classes"] == [("B_H" if i == 0 else "L") if h in low else "H" for h in range(4)]
        row = m["phases"]["measurement"]
        assert row["generated"] == [240]*4 and row["fires"] == 239 and row["ready"] == 240
        assert all(n >= 112 for n in row["fifo_nonempty_ready"])
        if data["policy_param"] == 2:
            c = data["contention"]
            assert c["fill_cycles"] == 128
            assert c["post_fill_cycles"] == c["both_classes_eligible_cycles"] == 112
            fired = c["per_source_fires_after_fill"]
            assert sum(fired) == 112
            groups = (low, tuple(h for h in range(4) if h not in low))
            # Two cut visits contribute at most ten fires each; FCFS ties differ by at most one at each cut.
            assert abs(sum(fired[h] for h in groups[0])-sum(fired[h] for h in groups[1])) <= 20
            assert all(max(fired[h] for h in g)-min(fired[h] for h in g) <= 2 for g in groups)
            assert all(c["complete_visits"][cls] > 0 for cls in ("High", "Low"))
    if data["case"] == "trained" and data["policy_param"] == 2:
        assert [r["evidence"] for r in data["training_windows"]] == [["DOWN","KEEP","KEEP","KEEP"]]*2
        assert [r["classes"] for r in data["training_windows"]] == [["B_H","H","H","H"],["L","H","H","H"]]
        if data["production_evidence"]:
            assert data["window"] == 5_000_000 and data["warmup_cycles"] == 10_000_000
            assert data["contention"]["both_classes_eligible_cycles"] == data["contention"]["post_fill_cycles"] > 0
            assert data["contention"]["complete_visits"]["High"] > 0 and data["contention"]["complete_visits"]["Low"] > 0
