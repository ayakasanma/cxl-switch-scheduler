"""Pin-derived primary-trace phase metrics; observation never drives the DUT.

Cycles are trace-relative closing edges. FIFO occupancy is sampled before that
edge; producer backlog is sampled after generation, before acceptance, and after
acceptance. Latency cohorts follow the generation/acceptance phase, not the fire
phase. Measurement counters freeze before the existing boundary-only drain.
"""

from collections import Counter, deque


def histogram_stats(hist):
    """Integer histogram with mergeable counts and exact nearest-rank P99."""
    count = sum(hist.values())
    total = sum(value * frequency for value, frequency in hist.items())
    rank = (99 * count + 99) // 100
    cumulative = 0
    p99 = None
    for value in sorted(hist):
        cumulative += hist[value]
        if cumulative >= rank:
            p99 = value
            break
    return {"count": count, "sum": total, "mean": total / count if count else None,
            "p99_nearest_rank": p99, "min": min(hist) if count else None,
            "max": max(hist) if count else None,
            "histogram": {str(k): hist[k] for k in sorted(hist)}}


class PrimaryPhaseMetrics:
    def __init__(self, phases, n_src, cycles, depth=16):
        assert n_src > 0 and cycles > 0 and depth > 0
        self.n, self.cycles, self.depth = n_src, cycles, depth
        end = 0
        self.segments = []
        for start, length, kind in phases:
            assert start == end and length > 0 and isinstance(kind, str) and kind
            self.segments.append(self._bucket(start=start, length=length, kind=kind))
            end = start + length
        assert end == cycles, "phases must partition the measurement interval"
        self.pending = [deque() for _ in range(n_src)]
        self.accepted = [deque() for _ in range(n_src)]
        self.seen = set()
        self.next_cycle, self.phase = 0, 0
        self.frozen = False

    def _bucket(self, **labels):
        return {**labels, "cycles": 0, "ready_cycles": 0, "stall_cycles": 0,
                "idle_ready_cycles": 0, "idle_not_ready_cycles": 0,
                "generated_per_source": [0] * self.n,
                "accepted_per_source": [0] * self.n,
                "fires_per_source": [0] * self.n,
                **{name: {"sum_per_source": [0] * self.n,
                          "min_per_source": [None] * self.n,
                          "max_per_source": [None] * self.n,
                          "sum_total": 0, "min_total": None, "max_total": None}
                   for name in ("fifo_occupancy_pre_edge", "producer_backlog_after_generation",
                                "producer_backlog_post_edge")},
                **{name: Counter() for name in (
                    "generation_to_acceptance_completed", "acceptance_to_fire_completed",
                    "acceptance_to_fire_drain_completed", "generation_censored_at_phase_end",
                    "acceptance_censored_at_phase_end", "generation_censored_at_measurement_end",
                    "acceptance_censored_at_measurement_end")}}

    @staticmethod
    def _sample(bucket, name, values):
        sample = bucket[name]
        total = sum(values)
        sample["sum_total"] += total
        sample["min_total"] = total if sample["min_total"] is None else min(sample["min_total"], total)
        sample["max_total"] = total if sample["max_total"] is None else max(sample["max_total"], total)
        for h, value in enumerate(values):
            sample["sum_per_source"][h] += value
            low, high = sample["min_per_source"][h], sample["max_per_source"][h]
            sample["min_per_source"][h] = value if low is None else min(low, value)
            sample["max_per_source"][h] = value if high is None else max(high, value)

    def observe(self, cycle, generated, pushes, fire, out_valid, out_ready):
        """Events contain (source, tag), using only generation records and pins."""
        assert not self.frozen and cycle == self.next_cycle < self.cycles
        assert out_valid in (0, 1) and out_ready in (0, 1)
        assert bool(fire is not None) == bool(out_valid and out_ready)
        bucket = self.segments[self.phase]
        bucket["cycles"] += 1
        bucket["ready_cycles"] += out_ready
        bucket["stall_cycles"] += int(out_valid and not out_ready)
        bucket["idle_ready_cycles"] += int(not out_valid and out_ready)
        bucket["idle_not_ready_cycles"] += int(not out_valid and not out_ready)
        occupancy = [len(q) for q in self.accepted]
        self._sample(bucket, "fifo_occupancy_pre_edge", occupancy)
        for src, tag in generated:
            assert 0 <= src < self.n and isinstance(tag, int) and 0 <= tag < 2**32
            assert tag not in self.seen, "duplicate generated tag"
            self.seen.add(tag)
            self.pending[src].append((tag, cycle, self.phase))
            bucket["generated_per_source"][src] += 1
        self._sample(bucket, "producer_backlog_after_generation", [len(q) for q in self.pending])
        if fire is not None:
            src, tag = fire
            self._complete(cycle, src, tag, drain=False)
            bucket["fires_per_source"][src] += 1
        pushed = set()
        for src, tag in pushes:
            assert 0 <= src < self.n and src not in pushed
            pushed.add(src)
            assert occupancy[src] < self.depth, "full FIFO cannot accept a same-edge replacement"
            assert self.pending[src] and self.pending[src][0][0] == tag, "push must match producer head"
            _tag, gen_cycle, gen_phase = self.pending[src].popleft()
            self.segments[gen_phase]["generation_to_acceptance_completed"][cycle - gen_cycle] += 1
            self.accepted[src].append((tag, cycle, self.phase))
            bucket["accepted_per_source"][src] += 1
        self._sample(bucket, "producer_backlog_post_edge", [len(q) for q in self.pending])
        self.next_cycle += 1
        if self.next_cycle == bucket["start"] + bucket["length"]:
            for queues, name in ((self.pending, "generation"), (self.accepted, "acceptance")):
                for queue in queues:
                    for _tag, born, cohort in reversed(queue):
                        if cohort != self.phase:
                            break
                        bucket[name + "_censored_at_phase_end"][self.next_cycle - born] += 1
            self.phase += 1

    def _complete(self, cycle, src, tag, drain):
        assert 0 <= src < self.n and self.accepted[src]
        expected, accept_cycle, cohort = self.accepted[src].popleft()
        assert expected == tag and cycle > accept_cycle, "fire must match a previously accepted FIFO head"
        bucket = self.segments[cohort]
        bucket["acceptance_to_fire_completed"][cycle - accept_cycle] += 1
        if drain:
            bucket["acceptance_to_fire_drain_completed"][cycle - accept_cycle] += 1

    def freeze(self):
        assert not self.frozen and self.next_cycle == self.cycles
        self.frozen = True
        for queues, name in ((self.pending, "generation"), (self.accepted, "acceptance")):
            for queue in queues:
                for _tag, born, cohort in queue:
                    self.segments[cohort][name + "_censored_at_measurement_end"][self.cycles - born] += 1

    def drain_fire(self, cycle, src, tag):
        """Only fires of measured accepts enter here; drain-only accepts stay excluded."""
        assert self.frozen and cycle >= self.cycles
        self._complete(cycle, src, tag, drain=True)

    def result(self, legacy):
        assert self.frozen and not any(self.accepted), "all measured accepts must complete in the drain"
        pooled = {}
        for bucket in self.segments:
            target = pooled.setdefault(bucket["kind"], self._bucket(kind=bucket["kind"]))
            for key, value in bucket.items():
                if isinstance(value, Counter):
                    target[key].update(value)
                elif isinstance(value, list):
                    target[key] = [a + b for a, b in zip(target[key], value)]
                elif isinstance(value, dict):
                    for subkey, numbers in value.items():
                        old = target[key][subkey]
                        def merge(a, b):
                            if a is None:
                                return b
                            if b is None:
                                return a
                            return min(a, b) if subkey.startswith("min") else max(a, b) if subkey.startswith("max") else a + b
                        target[key][subkey] = [merge(a, b) for a, b in zip(old, numbers)] if isinstance(numbers, list) else merge(old, numbers)
                elif key not in ("start", "length", "kind"):
                    target[key] += value
        generated = sum(sum(b["generated_per_source"]) for b in self.segments)
        accepted = sum(sum(b["accepted_per_source"]) for b in self.segments)
        fires = sum(sum(b["fires_per_source"]) for b in self.segments)
        completed = Counter()
        gen_completed = Counter()
        for bucket in self.segments:
            assert sum(bucket["acceptance_to_fire_completed"].values()) == sum(bucket["accepted_per_source"])
            assert sum(bucket["generated_per_source"]) == sum(bucket["generation_to_acceptance_completed"].values()) + sum(bucket["generation_censored_at_measurement_end"].values())
            completed.update(bucket["acceptance_to_fire_completed"])
            gen_completed.update(bucket["generation_to_acceptance_completed"])
        assert generated == legacy["generated"] == accepted + legacy["generated_but_unaccepted"]
        assert accepted == legacy["input_push_count"] and fires == legacy["fires_measurement"]
        for hist, old in ((completed, legacy["wait_acceptance_to_fire"]["all_completed"]),
                          (gen_completed, legacy["generation_to_acceptance"])):
            stats = histogram_stats(hist)
            assert all(stats[key] == old[key] for key in ("count", "mean", "p99_nearest_rank", "min", "max"))
        def export(bucket):
            result = {}
            for key, value in bucket.items():
                if isinstance(value, Counter):
                    result[key] = histogram_stats(value)
                elif isinstance(value, dict):
                    result[key] = {**value, "samples": bucket["cycles"],
                                   "mean_total": value["sum_total"] / bucket["cycles"],
                                   "mean_per_source": [x / bucket["cycles"] for x in value["sum_per_source"]]}
                else:
                    result[key] = value
            result["generated"] = sum(bucket["generated_per_source"])
            result["accepted"] = sum(bucket["accepted_per_source"])
            result["fires"] = sum(bucket["fires_per_source"])
            return result
        return {"schema": "cxl-primary-phase-metrics-v1",
                "conventions": {
                    "cycles": "trace-relative edges; intervals [start,start+length); no warmup/reset",
                    "fifo_occupancy_pre_edge": "pin-history accepted minus fires before same-edge updates; includes carryover",
                    "producer_backlog_after_generation": "all generated pending after current generation, before current acceptance; includes carryover",
                    "producer_backlog_post_edge": "all generated pending after current acceptance; includes carryover",
                    "generation_to_acceptance_completed": "generation-phase cohort; accepted during measurement only; completed subset, not full-population mean",
                    "acceptance_to_fire_completed": "acceptance-phase cohort; includes measured accepts completed in drain; excludes drain-only accepts",
                    "censored": "right-censor age = exclusive boundary cycle minus generation/acceptance edge; frozen snapshots; phase_end is each cohort's own phase end",
                    "by_kind": "pooled histogram samples and cycle sums over all segments of each kind; not average of per-segment percentiles",
                    "stall_cycles": "out_valid && !out_ready; idle_ready_cycles = !out_valid && out_ready",
                }, "segments": [export(b) for b in self.segments],
                "by_kind": {kind: export(b) for kind, b in sorted(pooled.items())}}
