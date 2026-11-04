"""Protect the approved sample allocation and interpretation against silent scope shrinkage."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import revision_matrix as rm


class RevisionMatrixTest(unittest.TestCase):
    def test_complete_matrix_and_seed_separation(self):
        rows = rm.matrix()
        expected = {"n4-confirmation": 120, "n-expansion": 60, "trained-robustness": 180,
                    "rr-quantum": 25, "high-quota": 15, "depth": 45, "adaptation": 9,
                    "one-window-causal": 5, "matched-power": 9,
                    "insight-confirmation": 20, "insight-robustness": 10}
        self.assertEqual(dict(rm.Counter(r["group"] for r in rows)), expected)
        self.assertEqual(len(rows), len({r["id"] for r in rows}))
        self.assertEqual(rows, rm.matrix())
        for row in rows:
            pool = rm.CONFIRMATION if row["seed_role"] == "confirmation" else rm.EXPLORATION
            self.assertIn(row["seed"], pool)
            self.assertEqual(row["execution_status"], "NOT_RUN")
            if row["policy"] == "INSIGHT_WINNER":
                self.assertTrue(row["conditional"])
                self.assertIn("ONE frozen winner", row["prerequisite"])
            if row["group"] != "adaptation":
                self.assertEqual(row["training_cycles"], 2 * row["window"])
        self.assertEqual({r["policy"] for r in rows if r["group"] == "n4-confirmation"}, set(rm.POLICIES))

    def test_window_and_activity_boundaries(self):
        rows = rm.matrix()
        for row in rows:
            if row["group"] == "adaptation":
                self.assertEqual(row["measured_cycles"], 6 * row["window"])
                self.assertEqual(row["role_change_period"], 2 * row["window"])
            if row["group"] == "matched-power":
                self.assertTrue(row["activity_cohorts_separate"])
            if row["group"] == "high-quota":
                self.assertEqual(row["low_quota"], 10)
            if row["group"] == "trained-robustness":
                self.assertEqual(row["perturbation_after_training"],
                                 row["case"] != "heavy-id3")

    def test_asymmetric_area_and_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("docs/ppa/primary-20261021-v2.json", "docs/ppa/formality-20261021.json"):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((rm.ROOT / rel).read_bytes())
            formal = json.loads((root / "docs/ppa/formality-20261021.json").read_text())
            formal["cases"] = []
            (root / "docs/ppa/formality-20261021.json").write_text(json.dumps(formal))
            data = rm.evidence_audit(root)
            self.assertEqual(len(data["missing_in_old_manifest"]), 9)
            n4 = data["arithmetic"][0]
            self.assertAlmostEqual(n4["main_over_rr_percent"], 39.271073, places=5)
            self.assertAlmostEqual(n4["rr_below_main_percent"], 28.197581, places=5)
            self.assertNotEqual(n4["main_over_rr_percent"], n4["rr_below_main_percent"])
            self.assertNotEqual(data["expected_sparse_hog_heavy_residual"],
                                data["normalized_offered_heavy_share"])
            broken = copy.deepcopy(formal)
            broken["cases"] = [dict(policy="fai-main", n_src=4, reference_source_commit=rm.CURRENT,
                                    mapped_source_commit=rm.PRIMARY,
                                    reference_rtl_sha256={"rtl/missing.sv": "0" * 64})]
            (root / "docs/ppa/formality-20261021.json").write_text(json.dumps(broken))
            with self.assertRaisesRegex(ValueError, "reference RTL hash mismatch"):
                rm.evidence_audit(root)


if __name__ == "__main__":
    unittest.main()
