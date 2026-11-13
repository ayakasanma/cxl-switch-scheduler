"""Synthetic evidence corruption and output-boundary tests; no EDA execution."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_fastx_power as audit


class AuditContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()

    def write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def attempt(self, name, seed=7401, count=30, sealed=True):
        directory = self.evidence / "artifacts/implementation/dynamic-role-switch-v2-confirm" / name
        directory.mkdir(parents=True)
        results = []
        for index in range(count):
            path = f"job{index}.json"
            job = dict(status="PASS", job=dict(seed=seed, window=5000000),
                       trace_sha256=str(index), policy="CGOF(1:1)", lane="mixed")
            self.write_json(directory / path, job)
            results.append(dict(path=path, trace_sha256=str(index), policy=job["policy"], lane="mixed"))
        if sealed:
            self.write_json(directory / "manifest.json", dict(seed=seed, jobs=30, failed=[],
                            window=5000000, profile="near", confirmation_seeds=True, results=results))
            source = self.evidence / "source.txt"
            source.write_text("frozen", encoding="utf-8")
            self.write_json(directory / "cohort.json", dict(seeds=[seed], window=5000000,
                            profile="near", failed=[], source_hashes={"source.txt": audit.sha256_file(source)}))
        return directory

    def test_partial_attempts_do_not_stitch_or_hide_duplicates(self):
        self.attempt("first_seed7401", count=15, sealed=False)
        self.attempt("second_seed7401", count=15, sealed=False)
        inventory = audit.confirmation_inventory(self.evidence)
        self.assertIn(7401, inventory["missing_seeds"])
        self.attempt("complete_seed7401")
        self.assertEqual(audit.confirmation_inventory(self.evidence)["complete_directory_count"], 1)
        self.attempt("duplicate_seed7401")
        self.assertEqual(audit.confirmation_inventory(self.evidence)["duplicate_complete_seeds"], [7401])

    def test_manifest_path_and_trace_corruption(self):
        directory = self.attempt("valid_seed7401")
        self.assertEqual(audit.inspect_attempt(directory, self.evidence)["status"], "COMPLETE_FILES_OBSERVED")
        manifest = audit.read_json(directory / "manifest.json")
        original = copy.deepcopy(manifest)
        manifest["results"][0]["path"] = "../escape.json"
        self.write_json(directory / "manifest.json", manifest)
        self.assertEqual(audit.inspect_attempt(directory, self.evidence)["status"], "INCOMPLETE_EXCLUDED_ATTEMPT")
        original["results"][0]["trace_sha256"] = "corrupted"
        self.write_json(directory / "manifest.json", original)
        self.assertIn("mismatch", audit.inspect_attempt(directory, self.evidence)["problems"][0])

    def test_source_drift_is_separate_from_historical_completeness(self):
        directory = self.attempt("valid_seed7401")
        (self.evidence / "source.txt").write_text("changed", encoding="utf-8")
        result = audit.inspect_attempt(directory, self.evidence)
        self.assertEqual(result["status"], "COMPLETE_FILES_OBSERVED")
        self.assertEqual(result["source_drift"], ["source.txt"])

    def test_strict_json(self):
        path = self.root / "invalid.json"
        for payload in ('{', '{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(payload=payload):
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(ValueError):
                    audit.read_json(path)

    def test_output_is_exclusive_and_worktree_scoped(self):
        worktree = self.root / "worktree"
        with patch.object(audit, "ROOT", worktree):
            with self.assertRaises(ValueError):
                audit.write_report(self.evidence, self.evidence / "artifacts/out")
            target = worktree / "artifacts/new"
            audit.write_report(self.evidence, target)
            with self.assertRaises(ValueError):
                audit.write_report(self.evidence, target)
            self.assertEqual(audit.sha256_file(target / "audit.json"),
                             (target / "SHA256SUMS").read_text().split()[0])

    def test_absent_inputs_never_become_power_ready(self):
        result = audit.audit(self.evidence)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertFalse(result["ready_for_saif_power"])
        self.assertEqual(result["power"], "NOT_RUN")
        self.assertEqual(result["cohort"]["seeds"], [509, 510, 511])
        self.assertEqual(result["cohort"]["arms"], ["A", "B"])
        self.assertEqual(result["cohort_status"], "OWNER_FROZEN_509_511_AB_20261107")
        self.assertEqual(result["baseline"]["status"], "INCOMPLETE")
        self.assertTrue(all(row["status"] == "INCOMPLETE" for row in result["cgof"].values()))

    def test_source_path_escape_rejected(self):
        for name in ("../escape", "/absolute", "C:/absolute", "folder\\file"):
            with self.assertRaises(ValueError):
                audit.repo_file(self.root, name)

    def test_netlist_corruption_is_reported(self):
        bundle = "synthetic"
        directory = self.evidence / "artifacts/fastx" / bundle
        manifest = dict(parameters={}, profile_canonical_sha256="fixture", file_sha256={})
        for name in audit.CGOF_SOURCES:
            path = self.evidence / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source", encoding="utf-8")
            manifest["file_sha256"][name] = audit.sha256_file(path)
        self.write_json(directory / "manifest.json", manifest)
        self.write_json(directory / "profile.json", dict(library=dict(sha256="fixture")))
        names = ("run_config.tcl", "parameters.json", "output/cgof_unit_top.syn.v",
                 "output/cgof_unit_top.syn.sdc", "reports/area.rpt",
                 "reports/pt_timing_max.rpt", "reports/pt_timing_min.rpt",
                 "reports/pt_constraints.rpt", "reports/pt_status.rpt")
        for name in names:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        files = {name: audit.sha256_file(directory / name)
                 for name in (*names, "manifest.json", "profile.json")}
        self.write_json(directory / "download-manifest.json", dict(transfer_exit=0, files=files))
        self.assertEqual(audit.inspect_mapping(self.evidence, bundle)["status"], "HASH_BOUND_INPUTS_OBSERVED")
        (directory / "output/cgof_unit_top.syn.v").write_text("changed", encoding="utf-8")
        result = audit.inspect_mapping(self.evidence, bundle)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIn("ARTIFACT_HASH_MISMATCH", result["problems"])


if __name__ == "__main__":
    unittest.main()
