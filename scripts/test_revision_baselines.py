import unittest

from run_revision_baselines import BASE_TESTS, configurations, source_paths


class BaselineConfigurationTests(unittest.TestCase):
    def test_source_archive_covers_hierarchy_helper(self):
        self.assertIn("sim/common/hier_util.py", source_paths())

    def test_exact_applicable_tests_and_dimensions(self):
        configs = configurations()
        self.assertEqual(len({c["name"] for c in configs}), len(configs))
        self.assertEqual({c["params"]["N_SRC"] for c in configs}, {4, 8, 16})
        self.assertEqual({c["params"]["DEPTH"] for c in configs}, {8, 16, 32})
        self.assertEqual({c["params"]["RR_QUANTUM"] for c in configs}, {1, 4, 8, 10, 16})
        for c in configs:
            row, expr = c["params"], c["env"]["COCOTB_TEST_FILTER"]
            self.assertTrue(all(t in expr for t in BASE_TESTS))
            self.assertEqual("test_bliss_clear_boundaries" in expr, row["POLICY"] == 4)
            self.assertEqual("test_quota_high_only" in expr, row["POLICY"] == 2)
            self.assertEqual("test_main_1w_classification" in expr,
                             row["POLICY"] == 2 and row["FAI_W"] <= 256)
            self.assertEqual(c["expect_tests"], expr.count("|") + 1)


if __name__ == "__main__":
    unittest.main()
