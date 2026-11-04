"""Small contracts for the MODEL_ONLY credit/refill trace."""
import unittest

import run_credit_refill_trace as trace


class CreditRefillTraceTests(unittest.TestCase):
    def test_fixed_high_credit_changes_trace_and_conserves(self):
        result = trace.run_shift(4)
        divergence = result["comparison"]["first_selection_divergence"]
        self.assertIsNotNone(divergence)
        self.assertIn(divergence["cause"], ("eligibility", "refill", "held"))
        self.assertTrue(result["comparison"]["conservation"]["pass"])
        self.assertTrue(all("credits_after" in row for row in result["1to1"]["rows"]))
        self.assertTrue(all(row["refill_snapshot"] is not None
                            for row in result["1to1"]["rows"] if row["refill"]))
        self.assertTrue(any(row["latched"] for row in result["1to1"]["rows"]))

    def test_arrival_phase_moves_divergence(self):
        result = trace.run_sweep(4, (-2, -1, 0, 1, 2))
        self.assertTrue(result["summary"]["conservation_pass"])
        self.assertTrue(result["summary"]["divergent_shifts"])
        self.assertGreaterEqual(len(result["summary"]["first_divergence_cycles"]), 2)
        self.assertNotEqual(
            set(result["summary"]["first_divergence_cycles"].values()),
            {4},
        )

    def test_existing_trace_schema_is_insufficient(self):
        existing = (
            trace.ROOT / "artifacts/implementation/MSQ-main/20261023T083405Z_1850/"
            "results/cocotb_msq_p0_w5000000_seed509__main_sq_trace.jsonl.gz"
        )
        self.assertTrue(existing.exists())
        inspected = trace.inspect_existing_trace(existing)
        self.assertFalse(inspected["sufficient_for_budget_attribution"])
        self.assertIn("credits", inspected["missing"])
        self.assertIn("refill", inspected["missing"])

    def test_held_refill_is_committed_from_the_original_offer(self):
        result = trace.run_shift(5)
        rows = {row["cycle"]: row for row in result["2to1"]["rows"]}
        latched = rows[5]
        committed = rows[6]
        self.assertTrue(latched["candidate_refill"])
        self.assertEqual(latched["offered_refill"], True)
        self.assertEqual(latched["offered_snapshot"], [2, 2, 2, 2])
        self.assertIsNone(latched["committed"])
        self.assertEqual(committed["offered_origin_cycle"], 5)
        self.assertEqual(committed["offered_state"], "held")
        self.assertEqual(committed["candidate_refill"], False)
        self.assertEqual(committed["committed_refill"], True)
        self.assertEqual(committed["committed_snapshot"], [2, 2, 2, 2])
        self.assertEqual(committed["committed"]["source"], 1)
        self.assertEqual(committed["credits_after"], [2, 1, 2, 2])

    def test_trace_records_live_candidate_and_committed_state_separately(self):
        result = trace.run_shift(4)
        rows = result["1to1"]["rows"]
        self.assertTrue(all(row["schema"] == trace.TRACE_SCHEMA for row in rows))
        self.assertTrue(any(row["committed"] is not None for row in rows))
        for row in rows:
            if row["committed"] is None:
                self.assertEqual(row["credits_before"], row["credits_after"])
            else:
                self.assertTrue(row["committed_refill"] in (True, False))
                source = row["committed"]["source"]
                expected = list(row["committed_snapshot"])
                expected[source] -= 1
                self.assertEqual(row["credits_after"], expected)

    def test_compare_rejects_full_input_mismatch(self):
        result = trace.run_shift(4)
        left = result["1to1"]
        right = result["2to1"]
        wrong = {**right, "rows": [dict(row) for row in right["rows"]]}
        wrong["rows"][0]["ready"] = not wrong["rows"][0]["ready"]
        with self.assertRaisesRegex(ValueError, "different generation or ready"):
            trace.compare(left, wrong)


if __name__ == "__main__":
    unittest.main()
