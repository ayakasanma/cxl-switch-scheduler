"""Small negative/positive controls for the archive-audit acceptance boundary."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_descriptor_performance as audit


class ArchiveAuditTests(unittest.TestCase):
    def test_constant_twenty_seed_interval(self):
        self.assertEqual(audit.ci([2.0]*20), dict(mean=2.0, sample_sd=0.0, n_runs=20, ci95_low=2.0, ci95_high=2.0))

    def test_mean_is_run_mean_not_request_pool(self):
        stats = audit.ci([0.0]*10+[2.0]*10)
        self.assertEqual(stats["mean"], 1.0)
        self.assertLess(stats["ci95_low"], 1.0)
        self.assertGreater(stats["ci95_high"], 1.0)
        with self.assertRaises(ValueError):
            audit.ci([1.0]*19)

    def run_fixture(self, mutate=None, junit="<testsuite><testcase/></testsuite>"):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            base=root/"artifacts/implementation/pilot/run"
            base.mkdir(parents=True)
            data={"overall":"PASS", "milestone_acceptance_scope":True,
                  "counts":dict(tests=1,fail=0,not_run=0,failures=0,errors=0,skipped=0),
                  "sim_build_relaxations":[],"steps":[dict(kind="cocotb",name="pilot",status="PASS",tests=1,
                    failures=0,errors=0,skipped=0,exit_codes=dict(simulation=0),junit="junit.xml")]}
            if mutate:
                mutate(data)
            (base/"summary.json").write_text(json.dumps(data))
            (base/"junit.xml").write_text(junit)
            with patch.object(audit,"ROOT",root):
                return audit.accepted_run("pilot","run",1)[1]

    def test_valid_raw_evidence(self):
        self.assertEqual(self.run_fixture()["overall"],"PASS")

    def test_summary_pass_cannot_hide_raw_junit_failure(self):
        with self.assertRaises(ValueError):
            self.run_fixture(junit="<testsuite><testcase><failure/></testcase></testsuite>")

    def test_incomplete_relaxed_or_badexit_rejected(self):
        mutations=[lambda d:d.update(overall="RUNNING"),
                   lambda d:d.update(milestone_acceptance_scope=False),
                   lambda d:d["counts"].update(not_run=1),
                   lambda d:d["sim_build_relaxations"].append("-Wno-fatal"),
                   lambda d:d["steps"][0]["exit_codes"].update(simulation=1)]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.run_fixture(mutate=mutation)


if __name__=="__main__":
    unittest.main()
