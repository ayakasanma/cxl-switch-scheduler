"""Hand-derived generation-boundary attribution and runner configuration checks."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from diagnosis_source_book import SourceBook, population
from cgof_diagnosis_model import job_policy, job_params
import run_rtl_diagnosis as runner


class SourceBookTests(unittest.TestCase):
    def test_pending_crosses_generation_boundary_and_survives_cut(self):
        book = SourceBook(4, 64, 4)
        book.observe(63, [(0, 17)], [], None)
        book.observe(64, [(1, 18)], [(64, 1)], None)
        book.observe(65, [], [(63, 0)], None)
        book.observe(66, [], [], (64, 64, 1))
        book.snapshot_cut()
        book.observe(130, [], [], (63, 65, 0))
        data = book.result()
        self.assertEqual(data["at_cut"]["sources"][0]["pending_fifo"], 1)
        self.assertEqual(data["at_cut"]["epochs"]["epoch_W0"][0]["pending"], 1)
        self.assertEqual(data["final"]["epochs"]["epoch_W0"][0]["fired"], 1)
        self.assertEqual(data["final"]["epochs"]["epoch_W1"][0]["fired"], 0)
        self.assertEqual(data["latency"]["src0"]["generation_to_acceptance"]["histogram"], {2: 1})
        self.assertEqual(data["latency"]["src0"]["acceptance_to_fire"]["histogram"], {65: 1})
        self.assertEqual(data["latency"]["src0"]["generation_to_fire"]["histogram"], {67: 1})
        self.assertEqual(data["latency"]["src2"]["generation_to_fire"]["p99"], None)
        self.assertEqual(data["final_censored"], [0]*4)

    def test_tail_counts_and_incomplete_population(self):
        book = SourceBook(4, 64, 4)
        book.observe(257, [(0, 19)], [], None)
        book.snapshot_cut()
        with self.assertRaisesRegex(AssertionError, "censored"):
            book.result()
        book.observe(258, [], [(257, 0)], None)
        book.observe(259, [], [], (257, 258, 0))
        data = book.result()
        self.assertEqual(data["final"]["epochs"]["epoch_W4-tail"][0]["fired"], 1)
        with self.assertRaises(AssertionError):
            population(dict(generated=0, accepted=1, fired=0))

    def test_main_and_cgof_have_separate_policy_parameters(self):
        args = SimpleNamespace(policy="all", ordering="oldest-first", mode="finite-heavy",
                               seed=7301, window=256, windows=4, heavy_work=896,
                               profile="near", max_active_cycles=2000, depth=16,
                               heavy_sources=[0, 0, 1, 1], ready_pattern="bernoulli", ready_period=100)
        rows = runner.configs(args)
        self.assertEqual(len(rows), 6)
        import json
        jobs = [json.loads(row["env"]["CXL_DIAGNOSIS_JOB"]) for row in rows]
        main = jobs[0]
        self.assertEqual(job_policy(main), "FAI-inspired")
        self.assertIsNone(main["high_weight"])
        self.assertEqual(job_params(main), runner.params(main))
        self.assertEqual(rows[0]["top"], "switch_experiment_top")
        self.assertEqual(rows[2]["top"], "cgof_unit_top")
        self.assertEqual(job_policy(jobs[2]), "CGOF(1:1)")


if __name__ == "__main__":
    unittest.main()
