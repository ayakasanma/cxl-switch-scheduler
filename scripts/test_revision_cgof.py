import itertools
import re
import unittest

from run_revision_cgof import (
    BASE_TESTS, FILELIST, REJECTS, ROOT, RUNNER_TESTS, SMALL_W_TESTS, SUBSETS, TEST_MODULE, W5M,
    W5M_TESTS, configurations, identities, identity, lint_configurations, reject_configurations,
    row, runner_test_count, source_paths, subset_cases,
)

IDENTITIES = {"CGOF(2:1)/oldest-first", "CGOF(2:1)/eligible-round-robin",
              "CGOF(1:1)/oldest-first", "CGOF(1:1)/eligible-round-robin"}


class CgofConfigurationTests(unittest.TestCase):
    def test_simulation_matrix_dimensions(self):
        configs = configurations()
        self.assertEqual(len({c["name"] for c in configs}), len(configs))
        rows = [c["params"] for c in configs]
        self.assertEqual({r["N_SRC"] for r in rows}, {4, 8, 16})
        self.assertEqual({r["DEPTH"] for r in rows}, {8, 16, 32})
        self.assertEqual({r["FAI_W"] for r in rows}, {64, 256, W5M})
        self.assertEqual({identity(r) for r in rows}, IDENTITIES)
        for (hw, rr), n, w in itertools.product(identities(), (4, 8, 16), (64, W5M)):
            self.assertIn(row(n, 16, w, hw, rr), rows)
        # every identity covers identical structural configurations
        strip = lambda ident: sorted(  # noqa: E731
            tuple(sorted({**r, "HIGH_WEIGHT": 0, "ELIGIBLE_RR": 0}.items()))
            for r in rows if (r["HIGH_WEIGHT"], r["ELIGIBLE_RR"]) == ident)
        shapes = [strip(i) for i in identities()]
        self.assertTrue(all(s == shapes[0] for s in shapes))

    def test_identity_names(self):
        self.assertEqual({identity(row(hw=hw, rr=rr)) for hw, rr in identities()}, IDENTITIES)
        self.assertEqual(len(identities()), 4)

    def test_exact_applicable_tests_exist(self):
        source = (ROOT / f"sim/experimental/{TEST_MODULE}.py").read_text()
        defined = set(re.findall(r"^\s*async def (test_\w+)\(dut\)", source, re.M))
        self.assertEqual(defined, set(BASE_TESTS + SMALL_W_TESTS + W5M_TESTS))
        for c in configurations():
            expr = c["env"]["COCOTB_TEST_FILTER"]
            names = expr[1:-2].split("|")
            small = c["params"]["FAI_W"] <= 256
            self.assertEqual(names, list(BASE_TESTS + (SMALL_W_TESTS if small else W5M_TESTS)))
            self.assertEqual(c["expect_tests"], len(names))
            self.assertEqual(c["seeds"], [509])
            self.assertEqual(c["artifacts"], [{"file": "cgof_checks.json", "required": True}])

    def test_lint_and_rejection_scope(self):
        lints = lint_configurations()
        self.assertEqual(len(lints), 108)
        self.assertEqual(len({tuple(sorted(c["params"].items())) for c in lints}), 108)
        self.assertEqual({identity(c["params"]) for c in lints}, IDENTITIES)
        self.assertTrue(any(c["params"]["FAI_W"] == W5M and c["params"]["N_SRC"] == 16 for c in lints))
        rejects = reject_configurations()
        self.assertEqual(len(rejects), len(REJECTS))
        self.assertEqual({next(iter(c["params"])) for c in rejects},
                         {"N_SRC", "DEPTH", "FAI_W", "HIGH_WEIGHT", "ELIGIBLE_RR"})
        for c in rejects:
            (k, v), = c["params"].items()
            self.assertIn(f"{k if k != 'FAI_W' else 'W'}={v} is not supported", c["expect_message"])
            self.assertEqual((c["expect_undriven"], c["expect_unused"]), ([], []))

    def test_subsets_are_labeled_and_bounded(self):
        configs = configurations()
        for label in SUBSETS:
            cases = subset_cases(label)
            self.assertTrue(cases, label)
            self.assertLess(len(cases), len(configs), label)
            params = [configs[i]["params"] for i in cases]
            self.assertEqual({identity(p) for p in params}, IDENTITIES, label)
            self.assertTrue(all(p["FAI_W"] == 64 for p in params), label)
        self.assertEqual(len(subset_cases("w64-n4-d16-all-identities")), 4)

    def test_runner_test_count_matches_file(self):
        self.assertEqual(runner_test_count(), 7)
        self.assertEqual(RUNNER_TESTS, "scripts/test_revision_cgof.py")

    def test_source_archive_is_transitive(self):
        paths = set(source_paths())
        for line in (ROOT / FILELIST).read_text().splitlines():
            if line.strip().endswith(".sv"):
                self.assertIn(line.strip(), paths)
        for need in ("sim/common/hier_util.py", "sim/experimental/test_cgof_sched.py",
                     "rtl/experimental/cxl_cgof_sched.sv", "rtl/experimental/cgof_unit_top.sv",
                     "refc/cxl_model/experimental.py", "refc/cxl_model/common_ctrl_model.py",
                     "refc/cxl_model/fai_main_model.py", "scripts/run_verify.py", "scripts/wsl_env.sh"):
            self.assertIn(need, paths)
        self.assertTrue(all((ROOT / p).is_file() for p in paths))


if __name__ == "__main__":
    unittest.main()
