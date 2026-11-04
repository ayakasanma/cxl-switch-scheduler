"""Directed checks for the read-only accepted-RTL diagnosis."""
import json
from pathlib import Path
import tempfile
import unittest

import analyze_rtl_diagnosis as diagnosis


def endpoint(policy="CGOF (2:1)", profile="trained-A", seed=1, heavy=0, n=4,
             generated=None, fired=None, completed=None):
    generated = generated or [100, 10, 20, 30]
    fired = fired or [80, 8, 16, 24]
    completed = completed or [100, 10, 20, 30]
    return {
        "policy": policy,
        "profile": profile,
        "seed": seed,
        "status": "PASS",
        "production_evidence": True,
        "configuration": {
            "group": "test", "ready": "always", "heavy_source": heavy,
            "n_src": n, "depth": 16, "window": 5_000_000,
        },
        "phase_metrics": {
            "cycles": 100, "ready": 90, "generated": generated, "fired": fired,
            "eligible_ready_opportunities": 90, "avoidable_bubbles": 0,
            "eligible_ready_utilization": sum(fired) / 90,
            "backlog": [{"count": 100, "mean": 1, "min": 0, "max": 2, "end": 1}
                        for _ in range(n)],
            "occupancy": [{"count": 100, "mean": 1, "min": 0, "max": 2, "end": 1}
                          for _ in range(n)],
            "gaps": [{"samples": {"inter_service": {
                "wall_cycles": {"count": 3, "mean": 2, "max": 5, "p99_nearest_rank": 5},
                "eligible_ready_opportunities": {
                    "count": 3, "mean": 1, "max": 3, "p99_nearest_rank": 3,
                },
            }}} for _ in range(n)],
        },
        "completed_by_phase": {
            "A": [0, 10, 20, 30], "drain": [100, 0, 0, 0],
        },
        "per_source": [
            {"generation_to_fire": {"count": completed[source]}}
            for source in range(n)
        ],
    }


def document(*endpoints):
    return {
        "schema": "cxl-current-result-analysis-v1",
        "endpoints": list(endpoints),
        "conditional_dac": {"endpoints": []},
    }


class DiagnosisTests(unittest.TestCase):
    def write(self, value):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "analysis.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_fairness_keeps_raw_active_and_sparse_views_separate(self):
        row = endpoint(fired=[80, 0, 10, 10])["phase_metrics"]
        result = diagnosis.fairness(row["fired"], row["generated"], 0)
        self.assertAlmostEqual(result["raw_jain_all"], 10000 / 26400)
        self.assertAlmostEqual(result["active_service_jain"], 10000 / 26400)
        self.assertAlmostEqual(result["sparse_service_jain"], 400 / 600)
        self.assertEqual(result["reference"], "measured-phase arrivals; not common-demand fairness")

    def test_heavy_source_zero_and_three_use_physical_index(self):
        for source in (0, 3):
            value = endpoint(heavy=source, generated=[10] * 4, fired=[2, 3, 4, 5])
            result = diagnosis.analyze(self.write(document(value)))
            heavy = result["endpoints"][0]["heavy"]
            self.assertEqual(heavy["source"], source)
            self.assertEqual(heavy["fires"], 2 if source == 0 else 5)

    def test_phase_fire_is_not_cohort_completion(self):
        value = endpoint(fired=[72805, 788, 745, 751])
        result = diagnosis.analyze(self.write(document(value)))
        row = result["endpoints"][0]
        self.assertEqual(row["fairness"]["service_counts"], [72805, 788, 745, 751])
        self.assertEqual(row["cohort_completion_total"], [100, 10, 20, 30])

    def test_cohort_completion_must_match_latency_population(self):
        value = endpoint()
        value["completed_by_phase"]["drain"][0] = 99
        with self.assertRaisesRegex(ValueError, "cohort completion"):
            diagnosis.analyze(self.write(document(value)))

    def test_seeds_aggregate_into_one_intervention_cohort(self):
        value = document(endpoint(seed=1), endpoint(seed=2))
        result = diagnosis.analyze(self.write(value))
        self.assertEqual(len(result["cohorts"]), 1)
        self.assertEqual(result["cohorts"][0]["seeds"], [1, 2])
        self.assertEqual(result["cohorts"][0]["endpoint_count"], 2)

    def test_unavailable_metrics_are_explicit(self):
        result = diagnosis.analyze(self.write(document(endpoint())))
        self.assertIn("joint_backlog_quota_compliance", result["unavailable"])
        self.assertIn("memory_response_latency", result["unavailable"])
        self.assertIn("application_slowdown", result["unavailable"])
        self.assertIn("finite_heavy_completion", result["unavailable"])

    def test_rejects_nonaccepted_endpoint(self):
        value = endpoint()
        value["status"] = "FAIL"
        with self.assertRaisesRegex(ValueError, "accepted production"):
            diagnosis.analyze(self.write(document(value)))


if __name__ == "__main__":
    unittest.main()
