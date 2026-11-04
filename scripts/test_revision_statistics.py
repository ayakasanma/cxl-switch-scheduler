import unittest

from revision_statistics import histogram_summary, paired_runs


def records(seeds, value):
    return [dict(seed=s, p99=value, count=100, histogram={str(value): 100},
                 trace_sha256=f"trace-{s}", profile="trained-B", policy="fixture",
                 status="PASS", production_evidence=True,
                 configuration=dict(n_src=4, window=5_000_000, training_cycles=10_000_000))
            for s in seeds]


class RevisionStatisticsTest(unittest.TestCase):
    def test_exact_integer_nearest_ranks_and_empty_rejected(self):
        result = histogram_summary({"1": 990, "9": 9, "100": 1})
        self.assertEqual((result["p50"], result["p90"], result["p99"], result["p999"], result["max"]),
                         (1, 1, 1, 9, 100))
        for hist in ({}, {"1": 0}, {"1": -1}, {"1": True}, {"-1": 1}):
            with self.assertRaises(ValueError):
                histogram_summary(hist)

    def test_bootstrap_preserves_pairing_and_is_deterministic(self):
        seeds = range(529, 549)
        a, b = records(seeds, 20), records(seeds, 18)
        result = paired_runs(a, b, confirmation=True)
        self.assertEqual(result["mean_p99_delta_cycles"], -2)
        self.assertEqual(result["paired_bootstrap"]["percentile95"], [-2, -2])
        self.assertEqual(result, paired_runs(a[::-1], b, confirmation=True))
        b[0]["p99"] = 21
        b[0]["histogram"] = {"21": 100}
        self.assertEqual(paired_runs(a, b, confirmation=True)["improved_seeds"], 19)

    def test_reject_pseudoreplication_leakage_and_unpaired_profiles(self):
        a, b = records(range(509, 514), 20), records(range(509, 514), 18)
        result = paired_runs(a, b)
        self.assertNotIn("paired_bootstrap", result)
        with self.assertRaisesRegex(ValueError, "prespecified seed"):
            paired_runs(a, b, confirmation=True)
        with self.assertRaisesRegex(ValueError, "duplicate seed"):
            paired_runs(a + [a[0]], b)
        b[0]["profile"] = "cold-B"
        b[0]["configuration"]["training_cycles"] = 0
        with self.assertRaisesRegex(ValueError, "heterogeneous"):
            paired_runs(a, b)
        b[0]["profile"], b[0]["trace_sha256"] = "trained-B", "different"
        b[0]["configuration"]["training_cycles"] = 10_000_000
        with self.assertRaisesRegex(ValueError, "unpaired intended trace"):
            paired_runs(a, b)

    def test_reject_mixed_scope_failed_rows_and_forged_ranks(self):
        a = records(range(509, 514), 20)
        for field, value, message in (
            ("policy", "different", "heterogeneous"),
            ("status", "FAIL", "passed run"),
            ("production_evidence", False, "production training"),
            ("p99", 1, "histogram"),
            ("count", 1, "histogram"),
            ("configuration", dict(n_src=4, window=256, training_cycles=512), "production training"),
        ):
            b = records(range(509, 514), 18)
            b[0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                paired_runs(a, b)
        b = records(range(509, 514), 18)
        for row in b:
            row["configuration"]["n_src"] = 8
        with self.assertRaisesRegex(ValueError, "experimental boundary"):
            paired_runs(a, b)
        b = records(range(509, 514), 18)
        for row in a + b:
            row["profile"] = "cold-B"
            row["configuration"]["training_cycles"] = 0
        self.assertEqual(paired_runs(a, b)["mean_candidate_p99_cycles"], 18)


if __name__ == "__main__":
    unittest.main()
