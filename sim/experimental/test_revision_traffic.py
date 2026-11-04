"""Pure tests; no simulator or model result is represented as RTL evidence."""
import json
import unittest

from revision_traffic import LegacyTraffic, Metrics, StreamProducers, StreamStats, Traffic, distribution


def job(**changes):
    row = dict(group="n4-confirmation", n_src=4, window=256, seed=529, depth=16,
               heavy_source=0, heavy_rate=1, ready="always", burst_size=8, burst_period=1024)
    row.update(changes)
    return row


class TrafficTests(unittest.TestCase):
    def test_exact_legacy_descriptors_rng_and_hash(self):
        primary_hashes = {
            509: "cfffb58a5233aaa4b018d95e6a2a7606edc92d0daae784189c1b214e7219b984",
            529: "bc01f0a168c8519ba35260335160ddf73ee1ade904915368e9a596069d969620",
        }
        for seed in (509, 529):
            a, b = Traffic(job(seed=seed)), LegacyTraffic(seed, 256)
            for k in range(a.end):
                self.assertEqual(a.step(k), b.step(k))
            self.assertEqual(a.config, b.config)
            self.assertEqual(a.sha256, b.sha256)
            self.assertEqual(a.sha256, primary_hashes[seed])
            self.assertEqual(a.generated, b.generated)

    def test_robustness_only_changes_measurement(self):
        for changes in (dict(ready="bernoulli-0.75"), dict(ready="periodic-48/64"),
                        dict(heavy_rate=.5), dict(heavy_rate=.9),
                        dict(burst_size=32, burst_period=4096)):
            a, b = Traffic(job(**changes)), LegacyTraffic(529, 256)
            for k in range(a.training):
                self.assertEqual(a.step(k), b.step(k))
            for k in range(a.training, a.training+128):
                events, ready = a.step(k)
                if changes.get("ready") == "periodic-48/64":
                    self.assertEqual(ready, int((k-a.training) % 64 < 48))

    def test_static_source_permutation_exact_canonical_trace(self):
        for n in (4, 16):
            canonical, permuted = Traffic(job(n_src=n)), Traffic(job(n_src=n, heavy_source=3))
            permutation = [3, 1, 2, 0] + list(range(4, n))
            self.assertEqual(permuted.config["source_permutation"], permutation)
            self.assertFalse(permuted.config["perturbation_after_training"])
            self.assertEqual(permuted.bounds, canonical.bounds)
            phases = set()
            for k in range(canonical.end):
                events, ready = canonical.step(k)
                self.assertEqual(permuted.step(k), ([(permutation[h], d) for h, d in events], ready))
                self.assertEqual(permuted.heavy(k), 3)
                phases.add(permuted.phase(k))
            self.assertTrue({"training", "A", "A_guard", "B", "B_guard"} <= phases)
            self.assertEqual(permuted.generated, [canonical.generated[h] for h in permutation])

    def test_cold_replays_corresponding_measurement(self):
        for changes in ({}, dict(n_src=8), dict(heavy_source=3, ready="bernoulli-0.75")):
            trained, cold = Traffic(job(**changes)), Traffic(job(**changes), cold="A")
            for k in range(trained.training):
                trained.step(k)
            for k in range(2048):
                self.assertEqual(trained.step(k+trained.training), cold.step(k))

    def test_cold_b_independent_exact_arrivals_tags_ready(self):
        for changes in ({}, dict(ready="bernoulli-0.75"), dict(ready="periodic-48/64"),
                        dict(heavy_source=3, heavy_rate=.5)):
            trained, cold = Traffic(job(**changes)), Traffic(job(**changes), cold="B")
            self.assertEqual(cold.training, 0)
            self.assertEqual(cold.phase(0), "B")
            for k in range(trained.b_start):
                trained.step(k)
            for k in range(2048):
                self.assertEqual(trained.step(k+trained.b_start), cold.step(k))
            self.assertEqual(cold.cold_cohort, "B")

    def test_static_permutation_cold_lanes_through_final_guard(self):
        for cohort in ("A", "B"):
            canonical = Traffic(job(ready="bernoulli-0.75"), cold=cohort)
            permuted = Traffic(job(heavy_source=3, ready="bernoulli-0.75"), cold=cohort)
            self.assertEqual(permuted.training, 0)
            self.assertEqual(permuted.generated, [0]*4)
            permutation = [3, 1, 2, 0]
            for k in range(canonical.end):
                events, ready = canonical.step(k)
                self.assertEqual(permuted.step(k), ([(permutation[h], d) for h, d in events], ready))
            self.assertEqual(permuted.phase(permuted.end-1), cohort+"_guard")

    def test_static_permutation_default_guards_before_third_close(self):
        t = Traffic(job(window=5_000_000, heavy_source=3))
        self.assertEqual(t.guard_cycles, 1024)
        self.assertEqual(t.heavy(0), 3)
        self.assertLess(t.end, 3*t.window)

    def test_generalized_n_and_bursts(self):
        for n in (8, 16):
            t = Traffic(job(n_src=n, heavy_source=n-1, burst_size=32, burst_period=4096))
            seen = [0]*n
            for k in range(t.end):
                events, _ = t.step(k)
                if t.phase(k) == "B":
                    for h, d in events:
                        self.assertLess(d, 1 << 105)
                        seen[h] += 1
            self.assertEqual([v for h, v in enumerate(seen) if h != n-1], [800]*(n-1))
            self.assertEqual(json.loads(json.dumps(t.config)), t.config)

    def test_adaptation_roles_and_six_windows(self):
        t = Traffic(job(group="adaptation", heavy_rate=.8))
        self.assertEqual(t.end, 1536)
        self.assertEqual([t.heavy(k) for k in (0, 511, 512, 1023, 1024, 1535)], [0, 0, 3, 3, 0, 0])
        for k in range(t.end):
            t.step(k)
        self.assertEqual(t.next_cycle, t.end)

    def test_production_before_third_close(self):
        t = Traffic(job(window=5_000_000))
        self.assertEqual(t.training, 10_000_000)
        self.assertLess(t.end, 3*t.window)

    def test_histogram_ranks(self):
        s = StreamStats()
        for k in range(1, 1001):
            s.add(k)
        self.assertEqual({k: distribution(s)[k] for k in ("count", "p50", "p90", "p99", "p999", "max")},
                         dict(count=1000, p50=500, p90=900, p99=990, p999=999, max=1000))
        self.assertEqual(distribution(StreamStats())["count"], 0)

    def test_pin_fifo_full_before_pop_and_integrity(self):
        t, p = Traffic(job(depth=8)), StreamProducers(4)
        m = Metrics(t)
        for k in range(8):
            e = [(0, k)]
            p.generate(k, e)
            m.observe(k, e, p, 0, 15, int(k > 0), 0, 0)
        p.generate(8, [(0, 99)])
        with self.assertRaisesRegex(AssertionError, "full-before-pop"):
            m.observe(8, [(0, 99)], p, 1, 15, 1, 0, 0)
        m.observe(8, [(0, 99)], p, 1, 14, 1, 0, 0)
        self.assertEqual(p.offers()[0], (8, 99))
        self.assertEqual(len(m.fifo[0]), 7)

    def test_guard_failure_retained(self):
        t, p = Traffic(job()), StreamProducers(4)
        m = Metrics(t)
        m.fifo[1].append((t.a_end-1, t.a_end-1, 5))
        with self.assertRaisesRegex(AssertionError, "sparse pending"):
            m.guard(t.b_start, p)

    def test_training_boundary_retains_late_sparse_work_but_requires_cold_completion(self):
        for window in (256, 5_000_000):
            t, p = Traffic(job(window=window, n_src=16)), StreamProducers(16)
            m = Metrics(t)
            p.generate(t.training-1, [(1, 7)])
            m.fifo[2].append((t.training-2, t.training-2, 9))
            m.guard(t.training, p)
            self.assertEqual(p.offers()[1], (t.training-1, 7))
            self.assertEqual(len(m.fifo[2]), 1)
            m.cohorts["cold"]["generated"][1] = 1
            with self.assertRaisesRegex(AssertionError, "incomplete sparse background-on guard"):
                m.guard(t.training, p)

    def test_closed_producer_hold_stages_and_conservation(self):
        t, p = Traffic(job(), cold="A"), StreamProducers(4)
        m = Metrics(t)
        schedule = [([(1, (1 << 104)+7)], 1, 0, None, None),
                    ([(0, 11)], 0, 1, 1, (1 << 104)+7),
                    ([], 0, 1, 1, (1 << 104)+7),
                    ([], 1, 1, 1, (1 << 104)+7),
                    ([], 1, 1, 0, 11)]
        for k, (events, ready, valid, source, desc) in enumerate(schedule):
            p.generate(k, events)
            m.observe(k, events, p, ready, 15, valid, source, desc)
        m.complete(p)
        result = m.as_dict()
        self.assertEqual(result["cohorts"]["A"]["pooled_sparse"]["generation_to_fire"]["histogram"], {3: 1})
        self.assertEqual(result["cohorts"]["A"]["per_source"][1]["generation_to_acceptance"]["p99"], 0)
        self.assertEqual(result["phases"]["A"]["accepted"], [1, 1, 0, 0])
        self.assertEqual(result["phases"]["A"]["offered"], [1, 1, 0, 0])
        self.assertEqual(result["phases"]["A"]["fired"], [1, 1, 0, 0])

    def test_offered_cycles_and_backlog_keep_blocked_work(self):
        t, p = Traffic(job(depth=8)), StreamProducers(4)
        m = Metrics(t)
        events = [(0, d) for d in range(10)]
        for k in range(10):
            p.generate(k, events if k == 0 else [])
            m.observe(k, events if k == 0 else [], p, 0, 15 if k < 8 else 14,
                      int(k > 0), 0 if k else None, 0 if k else None)
        row = m.as_dict()["phases"]["training"]
        self.assertEqual(row["generated"], [10, 0, 0, 0])
        self.assertEqual(row["offered"], [10, 0, 0, 0])
        self.assertEqual(row["accepted"], [8, 0, 0, 0])
        self.assertEqual(row["fired"], [0]*4)
        self.assertEqual(row["backlog"][0]["end"], 2)
        self.assertEqual(row["occupancy"][0]["end"], 8)
        self.assertEqual(p.offers()[0], (0, 8))

    def test_output_hold_corruption_fails(self):
        t, p = Traffic(job(), cold="A"), StreamProducers(4)
        m = Metrics(t)
        p.generate(0, [(1, 7)])
        m.observe(0, [(1, 7)], p, 0, 15, 0, None, None)
        m.observe(1, [], p, 0, 15, 1, 1, 7)
        with self.assertRaisesRegex(AssertionError, "105-bit output hold"):
            m.observe(2, [], p, 1, 15, 1, 1, 1 << 104)

    def test_joint_eligible_ready_excludes_idle_and_stalled_cycles(self):
        t, p = Traffic(job()), StreamProducers(4)
        m = Metrics(t)
        schedule = [([], 1, 0), ([(1, 7)], 1, 0), ([], 0, 1), ([], 1, 1), ([], 1, 0)]
        for k, (events, ready, valid) in enumerate(schedule):
            p.generate(k, events)
            m.observe(k, events, p, ready, 15, valid, 1 if valid else None, 7 if valid else None)
        m.complete(p)
        phases = m.as_dict()["phases"]
        row = phases["training"]
        self.assertEqual(row["ready"], 4)
        self.assertEqual(sum(row["fired"]), 1)
        self.assertEqual(row["eligible_ready_opportunities"], 1)
        self.assertEqual(row["eligible_ready_utilization"], 1.0)
        self.assertEqual(row["avoidable_bubbles"], 0)
        self.assertEqual(phases["A"]["eligible_ready_opportunities"], 0)
        self.assertIsNone(phases["A"]["eligible_ready_utilization"])

    def test_eligible_ready_bubble_is_counted_and_fails(self):
        t, p = Traffic(job()), StreamProducers(4)
        m = Metrics(t)
        p.generate(0, [(1, 7)])
        m.observe(0, [(1, 7)], p, 1, 15, 0, None, None)
        with self.assertRaisesRegex(AssertionError, "eligible-ready bubble"):
            m.observe(1, [], p, 1, 15, 0, None, None)
        self.assertEqual(m.rows["training"]["eligible_ready_opportunities"], 1)
        self.assertEqual(m.rows["training"]["avoidable_bubbles"], 1)


if __name__ == "__main__":
    unittest.main()
