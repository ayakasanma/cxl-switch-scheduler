"""Pure adapter checks for the CGOF RTL diagnosis traffic."""
import unittest

from cgof_diagnosis_traffic import DiagnosisTraffic


class DiagnosisTrafficTests(unittest.TestCase):
    def test_common_demand_is_exactly_equal(self):
        traffic = DiagnosisTraffic(
            "common-demand", 6201, n_src=4, window=64, windows=3, depth=16
        )
        for k in range(traffic.measurement_end):
            events, ready = traffic.step(k)
            self.assertEqual(ready, 1)
            self.assertEqual([source for source, _ in events], [0, 1, 2, 3])
            self.assertTrue(all(0 <= desc < 1 << 105 for _, desc in events))
        self.assertEqual(traffic.generated, [192, 192, 192, 192])
        self.assertEqual(traffic.phase(traffic.measurement_end - 1), "measurement")
        self.assertEqual(traffic.phase(traffic.measurement_end), "drain")
        self.assertIsNone(traffic.cohort(traffic.measurement_end))

    def test_finite_heavy_mixed_and_isolated_replay_exogenous_inputs(self):
        mixed = DiagnosisTraffic(
            "finite-heavy", 6201, n_src=4, window=64, windows=1,
            heavy_work=20, profile="near", include_sparse=True,
        )
        isolated = DiagnosisTraffic(
            "finite-heavy", 6201, n_src=4, window=64, windows=1,
            heavy_work=20, profile="near", include_sparse=False,
        )
        for k in range(200):
            mixed_events, mixed_ready = mixed.step(k)
            isolated_events, isolated_ready = isolated.step(k)
            self.assertEqual(
                [event for event in mixed_events if event[0] == 0],
                isolated_events,
            )
            self.assertEqual(mixed_ready, isolated_ready)
        self.assertEqual(mixed.heavy_released, 20)
        self.assertEqual(isolated.heavy_released, 20)
        self.assertEqual(mixed.heavy_ready_prefix_sha256(200),
                         isolated.heavy_ready_prefix_sha256(200))
        self.assertGreater(sum(mixed.generated[1:]), 0)
        self.assertEqual(sum(isolated.generated[1:]), 0)

    def test_finite_completion_switches_to_drain_without_more_work(self):
        traffic = DiagnosisTraffic(
            "finite-heavy", 6201, n_src=4, window=64, windows=1,
            heavy_work=20, profile="near",
        )
        k = 0
        while traffic.heavy_released < traffic.heavy_work:
            traffic.step(k)
            k += 1
        traffic.step(k)
        completed_at = k
        k += 1
        for _ in range(traffic.heavy_work):
            traffic.note_fire(completed_at, 0)
        self.assertTrue(traffic.heavy_complete)
        self.assertEqual(traffic.cut_cycle, completed_at)
        self.assertEqual(traffic.active_cycles, k)
        self.assertEqual(traffic.cohort(completed_at), "finite-heavy")
        self.assertEqual(traffic.phase(k), "drain")
        self.assertIsNone(traffic.cohort(k))
        self.assertEqual(traffic.step(k), ([], 1))

    def test_invalid_arguments_fail_closed(self):
        with self.assertRaises(ValueError):
            DiagnosisTraffic("unknown", 6201)
        with self.assertRaises(ValueError):
            DiagnosisTraffic("common-demand", -1)
        with self.assertRaises(ValueError):
            DiagnosisTraffic("common-demand", 6201, n_src=1)
        with self.assertRaises(ValueError):
            DiagnosisTraffic("finite-heavy", 6201, heavy_work=0)

    def test_switching_pairs_replay_heavy_and_count_old_generation_roles(self):
        lanes = [DiagnosisTraffic(
            "finite-heavy", 6201, window=64, windows=4, heavy_work=256,
            profile="near", include_sparse=sparse, heavy_sources=(0, 0, 1, 1),
            ready_pattern="bursty",
        ) for sparse in (True, False)]
        mixed, isolated = lanes
        for k in range(320):
            events, ready = mixed.step(k)
            heavy, isolated_ready = isolated.step(k)
            self.assertEqual([e for e in events if e[0] == mixed.heavy(k)], heavy)
            self.assertEqual(ready, isolated_ready)
        self.assertEqual(mixed.heavy_ready_prefix_sha256(320),
                         isolated.heavy_ready_prefix_sha256(320))
        mixed.note_fire(200, 0, generation_cycle=127)
        self.assertEqual(mixed.heavy_fired, 1)
        mixed.note_fire(201, 1, generation_cycle=127)
        self.assertEqual(mixed.heavy_fired, 1)
        with self.assertRaises(ValueError):
            mixed.note_fire(202, 1)


if __name__ == "__main__":
    unittest.main()

