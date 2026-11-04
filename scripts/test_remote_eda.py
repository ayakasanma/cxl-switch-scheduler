"""Local orchestration checks. These tests never contact SSH or run EDA tools."""

import contextlib
import io
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import remote_eda as runner


def archive_bytes(name, data=b"report", kind=tarfile.REGTYPE):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.size = len(data) if kind == tarfile.REGTYPE else 0
        member.linkname = "/outside" if kind == tarfile.SYMTYPE else ""
        archive.addfile(member, io.BytesIO(data) if member.size else None)
    return stream.getvalue()


class RunnerTests(unittest.TestCase):
    def test_example_requires_real_connection_configuration(self):
        with self.assertRaisesRegex(ValueError, "Fill host"):
            runner.load_config(runner.ROOT / "scripts" / "fastx.config.example.json", "preflight")

    def test_default_preflight_is_offline(self):
        config = {"host": "example.invalid", "user": "test_user", "target_library": "/not-real/saed32rvt_tt0p78v25c.db",
                  "module_name": "Synopsys_x86-64/2024", "module_init": "", "identity_file": "", "port": 22}
        with tempfile.TemporaryDirectory(prefix="cxl runner test ") as temporary:
            config_path = Path(temporary) / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with patch.object(runner, "run_ssh", side_effect=AssertionError("Unexpected SSH call")) as ssh:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(runner.main(["preflight", "--config", str(config_path)]), 0)
                ssh.assert_not_called()
                self.assertIn("DRY RUN", output.getvalue())

    def test_missing_and_pending_approval_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="cxl approval test ") as temporary:
            root = Path(temporary)
            (root / "specs").mkdir()
            with patch.object(runner, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "not a regular file"):
                    runner.approved_architecture()
                (root / "specs" / "APPROVAL.md").write_text("Architecture status: PENDING\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Architecture status: APPROVED"):
                    runner.approved_architecture()
                header = "Architecture status: APPROVED\nApproved by: Test fixture only\nApproved on: 2026-10-13\n"
                for specification in ("", "Specification: TBD\n", "Specification: <approved revision or commit>\n"):
                    (root / "specs" / "APPROVAL.md").write_text(header + specification, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "non-placeholder.*Specification"):
                        runner.approved_architecture()
                (root / "specs" / "APPROVAL.md").write_text(header + "Specification: test-fixture revision 0.1\n", encoding="utf-8")
                self.assertEqual(runner.approved_architecture()[0], "specs/APPROVAL.md")

    def test_shell_environment_preserves_literals(self):
        config = {"module_name": "module; touch /wrong", "module_init": "/path with spaces/'literal'",
                  "target_library": '/library/$HOME/$(command)/[cells].db'}
        for line in runner.shell_environment(config).splitlines():
            words = shlex.split(line)
            self.assertEqual(len(words), 2)
        self.assertIn(config["module_name"], shlex.split(runner.shell_environment(config).splitlines()[0])[1])

    def test_download_rejects_paths_and_proprietary_files(self):
        for name in ("../outside.rpt", "output/library.db", "reports/license.lic", "reports\\escape.rpt", "reports/C:bad.rpt",
                     "output/NUL.syn.v", "output/CON.syn.v", "reports/COM1.rpt", "reports/LPT².rpt", "reports/bad\x01.rpt"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaisesRegex(ValueError, "unexpected remote output"):
                    runner.save_download(archive_bytes(name), Path(temporary))
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "unexpected remote output"):
                runner.save_download(archive_bytes("reports/link.rpt", kind=tarfile.SYMTYPE), Path(temporary))

    def test_portable_filenames(self):
        for name in ("CON", "nul", "COM1", "LPT².rpt", "trailing.", "trailing ", "bad\x01.rpt", 'bad".rpt'):
            self.assertFalse(runner.portable_component(name), name)
        for name in ("cxl_switch_scheduler", "approved_top", "path with spaces.sv", "timing_max.rpt"):
            self.assertTrue(runner.portable_component(name), name)

    def test_download_accepts_only_new_regular_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(runner.save_download(archive_bytes("reports/timing.rpt"), root), ["reports/timing.rpt"])
            self.assertEqual((root / "reports" / "timing.rpt").read_bytes(), b"report")
            with self.assertRaises(FileExistsError):
                runner.save_download(archive_bytes("reports/timing.rpt"), root)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl interpreter is optional for local template tests")
    def test_tcl_value_escaping(self):
        value = '/path with spaces/[cells]/$name/"quote";\\slash.db'
        script = f"set value {runner.tcl_string(value)}\nputs [binary encode hex [encoding convertto utf-8 $value]]\n"
        result = subprocess.run([shutil.which("tclsh")], input=script, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(bytes.fromhex(result.stdout.strip()).decode("utf-8"), value)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl interpreter is optional for local template tests")
    def test_templates_require_completion_and_propagate_errors(self):
        for mode, script_name, failing_command in (("syn", "dc.tcl", "compile"), ("sta", "pt.tcl", "update_timing")):
            for fail_tool in (False, True):
                with self.subTest(mode=mode, fail_tool=fail_tool), tempfile.TemporaryDirectory(prefix="cxl tcl test ") as temporary:
                    root = Path(temporary)
                    (root / mode).mkdir()
                    (root / "reports").mkdir()
                    (root / "output").mkdir()
                    script = root / mode / script_name
                    script.write_bytes((runner.ROOT / mode / script_name).read_bytes())
                    (root / "run_config.tcl").write_bytes(runner.tcl_config({"top_module": "approved_top", "target_library": "/external/library.db"}))
                    mocks = ["set search_path {}", "proc set_app_var {args} {}", "proc define_design_lib {args} {}",
                             "proc redirect {path script} {uplevel 1 $script}"]
                    commands = ("analyze", "elaborate", "current_design", "link", "check_design", "check_timing",
                                "compile", "report_area", "report_timing", "report_qor", "write", "write_sdc",
                                "read_verilog", "link_design", "read_sdc", "update_timing", "report_constraint", "report_analysis_coverage")
                    for command in commands:
                        body = 'error "intentional mock failure"' if fail_tool and command == failing_command else "return 1"
                        mocks.append(f"proc {command} {{args}} {{{body}}}")
                    wrapper = root / "mock.tcl"
                    wrapper.write_text("\n".join(mocks) + f"\nsource {runner.tcl_string(script.as_posix())}\n", encoding="utf-8")
                    result = subprocess.run([shutil.which("tclsh"), str(wrapper)], capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 1 if fail_tool else 0, result.stderr)
                    marker = root / "reports" / "run_status.rpt"
                    self.assertEqual(marker.exists(), not fail_tool)
                    if fail_tool:
                        self.assertIn("EDA_FAILURE", result.stderr)
                    else:
                        self.assertEqual(marker.read_text(), f"STATUS: SUCCESS\nOPERATION: {mode}\n")


if __name__ == "__main__":
    unittest.main()
