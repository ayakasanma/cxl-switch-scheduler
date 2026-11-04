"""Depth and scenario propagation through the native diagnosis runner."""
from argparse import Namespace
import json
import unittest

import run_rtl_diagnosis as runner


class RunnerTests(unittest.TestCase):
    def test_depth_and_role_ready_settings_reach_native_job(self):
        for depth in (8, 16, 32):
            job = runner.make_job(
                "finite-heavy", "mixed", 6201, 256, 2, 4, 1024, "near", 3000,
                depth=depth, heavy_sources=[0, 0, 1, 1], ready_pattern="bursty",
            )
            config = runner.config(job)
            self.assertEqual(config["params"]["DEPTH"], depth)
            self.assertEqual(json.loads(config["env"]["CXL_DIAGNOSIS_JOB"]), job)
            self.assertIn(f"-d{depth}-", runner.job_id(job))

    def test_pairs_do_not_merge_depth_or_ready_pattern(self):
        results = []
        for depth in (8, 32):
            for pattern in ("spread", "bursty"):
                for lane in ("mixed", "isolated"):
                    job = runner.make_job("finite-heavy", lane, 6201, 256, 2, 4,
                                          1024, "near", 3000, depth=depth,
                                          ready_pattern=pattern)
                    results.append(dict(job=job, data=dict(
                        active_cycles=2000, heavy=dict(fired=1024))))
        self.assertEqual(len(runner.paired_results(results)), 4)

    def test_ordering_reaches_build_job_and_result_identity(self):
        jobs = [
            runner.make_job(
                "finite-heavy", latency_lane, 6201, 256, 2, 4, 1024, "near", 3000,
                depth=16, ordering=ordering,
            )
            for ordering in ("oldest-first", "eligible-round-robin")
            for latency_lane in ("mixed",)
        ]
        self.assertEqual(
            [runner.config(job)["params"]["ELIGIBLE_RR"] for job in jobs],
            [0, 1],
        )
        self.assertEqual(len({runner.output_name(job) for job in jobs}), 2)
        self.assertEqual(
            [json.loads(runner.config(job)["env"]["CXL_DIAGNOSIS_JOB"])["ordering"]
             for job in jobs],
            ["oldest-first", "eligible-round-robin"],
        )

    def test_both_orderings_build_disjoint_pairs(self):
        args = Namespace(
            policy="2:1",
            mode="finite-heavy",
            ordering="both",
            seed=6201,
            window=256,
            windows=1,
            heavy_work=1024,
            profile="near",
            max_active_cycles=3000,
            depth=16,
            heavy_sources=None,
            ready_pattern="bernoulli",
            ready_period=100,
        )
        configs = runner.configs(args)
        self.assertEqual(len(configs), 4)
        self.assertEqual(len({row["name"] for row in configs}), 4)
        results = []
        for config in configs:
            job = json.loads(config["env"]["CXL_DIAGNOSIS_JOB"])
            results.append(dict(job=job, data=dict(
                active_cycles=2000, heavy=dict(fired=1024)
            )))
        pairs = runner.paired_results(results)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(
            {pair["ordering"] for pair in pairs},
            {"oldest-first", "eligible-round-robin"},
        )

    def test_missing_lane_and_duplicate_lane_fail_closed(self):
        mixed = runner.make_job(
            "finite-heavy", "mixed", 6201, 256, 2, 4, 1024, "near", 3000,
        )
        item = dict(job=mixed, data=dict(active_cycles=2000, heavy=dict(fired=1024)))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runner.paired_results([item])
        isolated = runner.make_job(
            "finite-heavy", "isolated", 6201, 256, 2, 4, 1024, "near", 3000,
        )
        duplicate = dict(job=dict(mixed), data=item["data"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            runner.paired_results([
                item,
                dict(job=isolated, data=item["data"]),
                duplicate,
            ])


if __name__ == "__main__":
    unittest.main()
