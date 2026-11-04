"""Hand-derived statistics, Holm ordering and seed-audit checks."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_dynamic_role_switch as a


def rows(values, seeds=a.EXPECTED_SEEDS, offsets=None):
    offsets = offsets or {"FAI-inspired": 0, "CGOF(1:1)": -2, "CGOF(2:1)": -1}
    table = {}
    for index, seed in enumerate(seeds):
        for case in ("role-switch", "multi-window"):
            for policy in ("FAI-inspired", "CGOF(1:1)", "CGOF(2:1)"):
                offset = offsets[policy] * values[index]
                table[(seed, case, policy)] = dict(endpoint=10 + offset, path="", lane="mixed")
    return table


class StatisticsTests(unittest.TestCase):
    def test_exact_tail_matches_frozen_thresholds(self):
        self.assertAlmostEqual(a.sign_p_value(16, 20), 0.005908966)
        self.assertAlmostEqual(a.sign_p_value(15, 20), 0.020694732)
        self.assertAlmostEqual(a.sign_p_value(14, 20), 0.057659149)
        self.assertAlmostEqual(a.sign_p_value(20, 20), 9.5367431640625e-07)

    def test_holm_requires_sixteen_for_the_first_step_only(self):
        contrasts = [dict(exact_p=a.sign_p_value(15, 20)),
                     dict(exact_p=a.sign_p_value(15, 20)),
                     dict(exact_p=a.sign_p_value(15, 20))]
        a.holm(contrasts)
        self.assertEqual(sorted(c["holm_threshold"] for c in contrasts),
                         sorted([0.05/3, 0.05/2, 0.05]))
        self.assertTrue(all(not c["holm_rejected"] for c in contrasts))
        contrasts = [dict(exact_p=a.sign_p_value(16, 20)),
                     dict(exact_p=a.sign_p_value(15, 20)),
                     dict(exact_p=a.sign_p_value(4, 20))]
        a.holm(contrasts)
        self.assertEqual([c["holm_rejected"] for c in contrasts], [True, True, False])
        stopped = [dict(exact_p=a.sign_p_value(16, 20)),
                   dict(exact_p=a.sign_p_value(14, 20)),
                   dict(exact_p=a.sign_p_value(4, 20))]
        a.holm(stopped)
        self.assertEqual([c["holm_rejected"] for c in stopped], [True, False, False])

    def test_margin_and_verdict(self):
        table = rows([1]*20, offsets={"FAI-inspired": 0, "CGOF(1:1)": -5, "CGOF(2:1)": -3})
        report = a.analyze(table)
        self.assertEqual({c["verdict"] for c in report["contrasts"]}, {"SUPPORTED_WITHIN_PROTOCOL"})
        table = rows([0]*19 + [5])
        report = a.analyze(table)
        self.assertEqual(report["contrasts"][0]["successes"], 1)
        self.assertEqual(report["contrasts"][0]["verdict"], "NOT_CONFIRMED")

    def test_seed_audit_rejects_excluded_missing_and_duplicate(self):
        table = rows([1]*20)
        table[(7291, "role-switch", "CGOF(1:1)")] = dict(endpoint=1, path="", lane="mixed")
        with self.assertRaisesRegex(ValueError, "excluded seed"):
            a.analyze(table)
        table = rows([1]*19, a.EXPECTED_SEEDS[:19])
        with self.assertRaisesRegex(ValueError, "cohort mismatch"):
            a.analyze(table, a.EXPECTED_SEEDS)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            a.audit(rows([1]*2, (7401, 7401)), (7401, 7401))

    def test_endpoint_rejects_non_frozen_evidence(self):
        good = dict(status="PASS", evidence_kind="MODEL_ONLY", lane="mixed", drain_cycles=0,
                    job=dict(seed=7401, window=5_000_000, windows=4, depth=16,
                             heavy_sources=[0], ready_pattern="bernoulli"),
                    policy="CGOF(1:1)",
                    generation_roles={"latency": {"sparse": {"generation_to_fire":
                        dict(count=10, p99_nearest_rank=3)}}})
        self.assertEqual(a.endpoint(good), 3)
        for change in (dict(evidence_kind="SCHEDULER_RTL"), dict(lane="isolated"),
                       dict(job=dict(good["job"], windows=3))):
            with self.assertRaises(ValueError):
                a.endpoint(dict(good, **change))
        self.assertEqual(a.endpoint(dict(good, drain_cycles=2)), 3)


if __name__ == "__main__":
    unittest.main()
