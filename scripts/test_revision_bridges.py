"""Offline corruption controls using retained own-design Formality reports."""

import json
import io
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

import run_revision_bridges as bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        bridge.LOGS.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="offline-test-", dir=bridge.LOGS)
        self.addCleanup(self.temp.cleanup)
        self.reports = Path(self.temp.name) / "reports"
        source = bridge.ROOT / "artifacts/fastx/formality-primary9/reports/fcfs-n4"
        shutil.copytree(source, self.reports)
        post = bridge.ROOT / "artifacts/fastx/formality-postmatch/reports/fcfs-n4/undriven-after-match.rpt"
        shutil.copyfile(post, self.reports / post.name)
        self.expected = {"policy": "fcfs", "n_src": 4, "expected_compare_points": 8967,
                         "expected_registers": 8856, "expected_hashes": {"fixture": "a" * 64}}
        for when in ["before", "after"]:
            bridge.write_json(self.reports / f"source-{when}.json", self.expected["expected_hashes"])

    def test_accepted_report_and_template(self):
        self.assertEqual(bridge.audit_case(self.reports, self.expected)["passing_compare_points"], 8967)
        text = bridge.template()
        self.assertIn("CXL_FM_POLICY", text)
        self.assertIn("undriven-after-match.rpt", text)
        shell = bridge.case_shell("/fixture", "fcfs-n4", "/accepted", 0, 4, "fixture-module")
        self.assertIn("/usr/bin/timeout 15m fm_shell", shell)
        self.assertIn("source-after.json", shell)

    def test_all_six_original_report_schemas(self):
        manifest = json.loads((bridge.ROOT / "docs/ppa/formality-20261021.json").read_text())
        for policy, n in bridge.CASES:
            with self.subTest(policy=policy, n=n):
                label = f"{policy}-n{n}"
                case = next(c for c in manifest["cases"] if c["group"] == "primary9"
                            and c["policy"] == policy and c["n_src"] == n)
                reports = Path(self.temp.name) / label
                shutil.copytree(bridge.ROOT / case["evidence_directory"], reports)
                post = bridge.ROOT / "artifacts/fastx/formality-postmatch/reports" / label
                shutil.copyfile(post / "undriven-after-match.rpt", reports / "undriven-after-match.rpt")
                for when in ["before", "after"]:
                    bridge.write_json(reports / f"source-{when}.json", {"fixture": "a" * 64})
                expected = dict(self.expected, policy=policy, n_src=n,
                                expected_compare_points=case["passing_compare_points"],
                                expected_registers=case["passing_nonconstant_registers"]
                                + case["constant_registers_not_compared"])
                self.assertEqual(bridge.audit_case(reports, expected)["status"], "PASS")

    def test_corruption_rejected(self):
        mutations = [
            ("exits.txt", "fm=124\n"),
            ("source-after.json", "{}\n"),
            ("source-before.json", "{}\n"),
            ("result.txt", "verify_return=0\n"),
            ("undriven-after-match.rpt", "1 Undriven nets:\n"),
            ("dont-verify.rpt", "excluded output\n"),
            ("aborted.rpt", "1 aborted compare point\n"),
            ("unverified.rpt", "1 unverified compare point\n"),
            ("unmatched.rpt", "1 unmatched point\n"),
            ("setup.rpt", 'synopsys_auto_setup = "true"\n'),
            ("constants.rpt", "User Defined Constants: forced_one\n"),
            ("black-boxes.rpt", "1 active black box\n"),
            ("status.rpt", (self.reports / "status.rpt").read_text().replace("8967", "8966")),
            ("status.rpt", (self.reports / "status.rpt").read_text().replace("POLICY0", "POLICY1")),
            ("setup-status.rpt", (self.reports / "setup-status.rpt").read_text()
             .replace("set_constant              :       0    0", "set_constant              :       1    0")),
            ("setup-status.rpt", (self.reports / "setup-status.rpt").read_text()
             .replace("set_cutpoint              :       0    0", "")),
            ("setup-status.rpt", (self.reports / "setup-status.rpt").read_text()
             .replace("Registers:                      8856(8856)", "Registers:                      8855(8855)")),
        ]
        for name, data in mutations:
            with self.subTest(name=name):
                path = self.reports / name
                original = path.read_bytes()
                path.write_text(data)
                with self.assertRaises(ValueError):
                    bridge.audit_case(self.reports, self.expected)
                path.write_bytes(original)

    def test_tool_error_rejected(self):
        path = self.reports / "fm.log"
        path.write_text(path.read_text() + "\nError: deliberate negative control\n")
        with self.assertRaisesRegex(ValueError, "tool error"):
            bridge.audit_case(self.reports, self.expected)

    def test_archive_escape_rejected(self):
        archive = Path(self.temp.name) / "unsafe.tar"
        for name in ["../escape.txt", "/absolute.txt", "reports/library.db"]:
            with self.subTest(name=name):
                with tarfile.open(archive, "w:") as tar:
                    member = tarfile.TarInfo(name)
                    member.size = 1
                    tar.addfile(member, io.BytesIO(b"x"))
                with self.assertRaises(ValueError):
                    bridge.extract_reports(archive, Path(self.temp.name) / "extract")

    def test_all_six_shells_and_connection_failure(self):
        self.assertEqual(len(set(bridge.CASES)), 6)
        for policy, n in bridge.CASES:
            text = bridge.case_shell("/scratch", f"{policy}-n{n}", "/accepted",
                                     0 if policy == "fcfs" else 1, n, "module")
            self.assertIn(f"CXL_FM_N={n}", text)
            self.assertIn("trap ", text)
        folder = Path(self.temp.name)
        (folder / "preflight.stderr.log").write_text("Host key verification failed.\n")
        self.assertEqual(bridge.connection_failure(folder, "preflight"),
                         "strict pinned host-key verification failed")

    def test_only_exact_archived_approved_pin_can_be_restored(self):
        config = json.loads((bridge.HELPERS / "connection.local.json").read_text())
        folder = Path(self.temp.name)
        target = bridge.restore_pin(config, folder)
        self.assertEqual(target.read_text(), (bridge.HELPERS / "known_hosts").read_text())
        config["host_key_observed"] = "SHA256:" + "A" * 43
        with self.assertRaisesRegex(ValueError, "no unique archived approved"):
            bridge.restore_pin(config, folder)
        config["host_key_state"] = "UNCONFIRMED"
        with self.assertRaisesRegex(ValueError, "not pinned"):
            bridge.restore_pin(config, folder)

    def test_pinned_ssh_quotes_spaced_trust_path(self):
        config = json.loads((bridge.HELPERS / "connection.local.json").read_text())
        folder = Path(self.temp.name)
        args = bridge.pinned_ssh(config, folder)
        self.assertIn("StrictHostKeyChecking=yes", args)
        self.assertIn('UserKnownHostsFile="' + bridge.linux(folder / "known_hosts") + '"', args)
        self.assertEqual(sum(x.startswith("UserKnownHostsFile=") for x in args), 1)


if __name__ == "__main__":
    unittest.main()
