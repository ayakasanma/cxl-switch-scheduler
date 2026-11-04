"""F12 export/replay tests; all executed windows are sensitivity-only, never power."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_revision_power_vectors as revision
from check_power_replay import check_payload_mode, expected_result_v2


class RevisionPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cxl-f12-test-")
        cls.root = Path(cls.temp.name)
        cls.exports = {}
        for policy in revision.POLICIES:
            out = cls.root / policy
            cls.exports[policy] = (out, revision.export_case(policy, 509, "A", out, 256, 64))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_production_plan_exact_separate_cuts_all_seeds(self):
        for seed in range(509, 514):
            for policy in revision.POLICIES:
                a = revision.plan(policy, seed, "A")
                b = revision.plan(policy, seed, "B")
                self.assertEqual((a["training_cycles"], a["warmup_cycles"], a["measured_cycles"]),
                                 (10_000_000, 10_000_000, 100_000))
                self.assertEqual((b["training_cycles"], b["warmup_cycles"], b["measured_cycles"]),
                                 (10_000_000, 10_101_024, 102_400))
                self.assertTrue(a["production_evidence"])
                self.assertEqual(a["planned_power_seed"], seed <= 511)
                self.assertLess(b["total_cycles"], 15_000_000)

    def test_invalid_configuration_rejected_before_creating_output(self):
        out = self.root / "invalid"
        for args in (("fcfs", 529, "A", 256, 1), ("rr", 509, "C", 256, 1),
                     ("fai-main", 509, "A", 5_000_000, 64),
                     ("fcfs", 509, "A", 256, 0), ("fcfs", True, "A", 256, 1)):
            policy, seed, arm, window, count = args
            with self.assertRaises(ValueError):
                revision.export_case(policy, seed, arm, out, window, count)
            self.assertFalse(out.exists())

    def test_actual_exports_reaudited_and_exogenous_hash_matched(self):
        hashes = []
        for out, m in self.exports.values():
            self.assertFalse(m["production_evidence"])
            self.assertTrue(m["sensitivity_only"])
            self.assertEqual(m["dc_pt_power_status"], "NOT_RUN")
            self.assertEqual(m["exit"], 0)
            audit = revision.audit_export(out)
            self.assertEqual(audit["traffic_phase_cycles"], {"training": 512, "A": 64})
            self.assertEqual(audit["rows"], 576)
            self.assertEqual(m["audit_sha256"], revision.legacy.sha(out / "audit.json"))
            hashes.append(m["trace"]["sha256"])
        self.assertEqual(len(set(hashes)), 1)

    def test_main_has_two_real_small_window_training_closes(self):
        _, m = self.exports["fai-main"]
        self.assertEqual([c["cycle"] for c in m["closings"]], [255, 511])
        self.assertEqual(m["state_at_cut"]["window_position"], 0)
        self.assertEqual(m["state_at_cut"]["b"], [0]*4)

    def test_independent_replay_rejects_training_and_window_stat_tampering(self):
        rows, m = self.rows()
        m["closings"][0]["b_close"][0] += 1
        with self.assertRaisesRegex(ValueError, "closing statistics"):
            revision.audit_rows(iter(rows), m)
        for name in ("state_at_cut", "state_at_end"):
            rows, m = self.rows()
            m[name]["s"] += 1
            with self.assertRaisesRegex(ValueError, "window statistics"):
                revision.audit_rows(iter(rows), m)

    def test_existing_production_runner_fails_closed_for_f12(self):
        for _, m in self.exports.values():
            with self.assertRaisesRegex(ValueError, "unsupported supplementary power mode"):
                check_payload_mode(m, 4, m["policy"])

    def rows(self, policy="fai-main"):
        out, m = self.exports[policy]
        with gzip.open(out / "vectors.txt.gz", "rt") as f:
            self.assertEqual(f.readline().strip(), revision.header(m))
            rows = [tuple(int(v, 10 if i == 0 else 16) for i, v in enumerate(line.split())) for line in f]
        return rows, copy.deepcopy(m)

    def test_serialized_pin_mutants_rejected_independently(self):
        for field, value in ((0, 99), (1, 16), (2, 1 << 420), (3, 0),
                             (4, 0), (5, 0), (6, 3), (7, 1 << 105)):
            rows, m = self.rows()
            row = list(rows[1])
            row[field] = value
            rows[1] = tuple(row)
            with self.assertRaises(ValueError, msg=f"field {field}"):
                revision.audit_rows(iter(rows), m)

    def test_truncation_extra_rows_and_counter_tampering_rejected(self):
        rows, m = self.rows()
        for bad in (rows[:-1], rows + [rows[-1]]):
            with self.assertRaises(ValueError):
                revision.audit_rows(iter(bad), m)
        m["measured"]["fires_per_source"][0] += 1
        with self.assertRaisesRegex(ValueError, "counters"):
            revision.audit_rows(iter(rows), m)
        rows, m = self.rows()
        m["all"]["fires"] += 1
        with self.assertRaisesRegex(ValueError, "all-phase"):
            revision.audit_rows(iter(rows), m)

    def test_gate_result_exact_totals_only_never_power_claim(self):
        _, m = self.exports["rr"]
        result = self.root / "synthetic-result.txt"
        lines = expected_result_v2(m)
        result.write_text("\n".join(lines)+"\n")
        self.assertEqual(revision.check_gate_result(m, result)["status"],
                         "F12_GATE_TOTALS_CHECKED_SAIF_PT_NOT_CHECKED")
        result.write_text("\n".join(lines[:-1])+"\n")
        with self.assertRaises(ValueError):
            revision.check_gate_result(m, result)

    def test_synthetic_saif_rejects_warmup_duration_unknown_clock_and_wrong_scope(self):
        _, m = self.exports["rr"]
        result, saif = self.root/"synthetic-gate.txt", self.root/"synthetic.saif"
        result.write_text("\n".join(expected_result_v2(m))+"\n")
        text = ("(TIMESCALE 1 ns) (DURATION 1600) "
                "(INSTANCE tb (INSTANCE dut (NET (clk (T0 800) (T1 800) (TX 0) (TC 128)))))")
        saif.write_text(text)
        self.assertIn("NOT_GRANTED", revision.check_activity(m, result, saif)["method_acceptance"])
        for bad in (text.replace("1600", "14400"), text.replace("(TX 0)", "(TX 1)"),
                    text.replace("(TC 128)", "(TC 1152)"), text.replace("dut", "other")):
            saif.write_text(bad)
            with self.assertRaises(ValueError):
                revision.check_activity(m, result, saif)

    def test_gzip_deterministic_hash_and_fresh_output_only(self):
        out, m = self.exports["fcfs"]
        with self.assertRaises(FileExistsError):
            revision.export_case("fcfs", 509, "A", out, 256, 64)
        second = self.root / "repeat"
        again = revision.export_case("fcfs", 509, "A", second, 256, 64)
        self.assertEqual(m["vectors_gzip_sha256"], again["vectors_gzip_sha256"])
        self.assertEqual(hashlib.sha256(gzip.decompress((out/"vectors.txt.gz").read_bytes())).hexdigest(),
                         m["vectors_text_sha256"])

    def test_corrupt_container_and_source_inventory_fail_closed(self):
        import shutil
        out, _ = self.exports["fcfs"]
        corrupt = self.root / "corrupt"
        shutil.copytree(out, corrupt)
        with (corrupt/"vectors.txt.gz").open("ab") as f:
            f.write(b"corrupt")
        with self.assertRaisesRegex(ValueError, "gzip hash"):
            revision.audit_export(corrupt)
        changed = self.root / "changed"
        shutil.copytree(out, changed)
        m = json.loads((changed/"metadata.json").read_text())
        m["source_sha256"]["scripts/export_revision_power_vectors.py"] = "0"*64
        (changed/"metadata.json").write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "source hashes"):
            revision.audit_export(changed)

    def test_source_archive_exact_bytes_deterministic_and_tamper_rejected(self):
        import shutil
        out, m = self.exports["fcfs"]
        with zipfile.ZipFile(out / "source-freeze.zip") as archive:
            for path, digest in m["source_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.read(path)).hexdigest(), digest)
            for path, digest in m["accepted_case_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.read(f"mapped/{path}")).hexdigest(), digest)
        second = self.root / "archive-repeat"
        second.mkdir()
        revision.archive_inputs(second, "fcfs", m["source_sha256"], m["accepted_case_sha256"])
        self.assertEqual(revision.legacy.sha(second / "source-freeze.zip"), m["source_archive_sha256"])
        with self.assertRaises(FileExistsError):
            revision.archive_inputs(second, "fcfs", m["source_sha256"], m["accepted_case_sha256"])
        corrupt = self.root / "archive-corrupt"
        shutil.copytree(out, corrupt)
        with (corrupt / "source-freeze.zip").open("ab") as f:
            f.write(b"changed")
        with self.assertRaisesRegex(ValueError, "source archive hash"):
            revision.audit_export(corrupt)

    def test_change_during_freeze_retains_failure_without_success(self):
        out = self.root / "freeze-failure"
        before = revision.sources()
        before["sim/experimental/revision_traffic.py"] = "0"*64
        with patch.object(revision, "sources", return_value=before):
            with self.assertRaisesRegex(ValueError, "source changed before archive"):
                revision.export_case("fcfs", 509, "A", out, 256, 64)
        self.assertTrue((out / "failure.json").exists())
        self.assertFalse((out / "metadata.json").exists())
        self.assertFalse((out / "audit.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
