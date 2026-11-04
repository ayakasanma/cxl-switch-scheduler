"""Local checks for the PPA run preparation flow.

These tests never contact a host or run commercial EDA tools. run.sh is exercised with fake,
test-only dc_shell/pt_shell scripts, and the DC/PT Tcl flow with stub Synopsys commands in a
plain Tcl interpreter; neither validates real Synopsys behavior.
"""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_ppa_run as prep  # noqa: E402

EXPECTED_SOURCES = [
    "rtl/include/cxl_sched_pkg.sv",
    "rtl/common/cxl_desc_fifo.sv",
    "rtl/common/cxl_out_hold.sv",
    "rtl/common/cxl_fcfs_sel.sv",
    "rtl/common/cxl_fai_main_sched.sv",
    "rtl/common/cxl_rr_sched.sv",
    "rtl/top/switch_top.sv",
]
NINE = [(policy, n) for policy in ("fcfs", "rr", "fai-main") for n in (4, 8, 16)]
LIBRARY = "/remote/example/lib/fake_tt.db"


def valid_profile(basename="fake_tt.db", sha="a" * 64):
    """Synthetic numbers for schema tests only; not a reviewed or proposed profile."""
    return {
        "schema": prep.PROFILE_SCHEMA, "profile_id": "unit-test-only", "status": "PILOT",
        "review": {"reviewed_by": "unit test", "reviewed_on": "2026-10-20",
                   "evidence": "synthetic test fixture, not a real profile"},
        "library": {"db_basename": basename, "sha256": sha, "name": "fake_tt", "operating_conditions": "stub_oc"},
        "units": {"time": "1ns", "capacitance": "1ff", "evidence": "synthetic"},
        "clock": {"port": "clk", "name": "core_clk", "period": 7, "setup_uncertainty": 0.25,
                  "hold_uncertainty": 0.125, "transition": 0.5},
        "io": {"input_delay_min": 0, "input_delay_max": 1.5, "output_delay_min": 0,
               "output_delay_max": 1.5, "input_transition": 0.5, "output_load": 3},
        "wire_load": {"method": "fixed_model", "model": "stub_wlm", "mode": "top", "rationale": "synthetic"},
        "compile": {"command": "compile", "map_effort": "tool_default"},
        "power": {"status": "NOT_RUN"},
    }


def git_out(*args):
    return subprocess.run(["git", "-C", str(prep.ROOT), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def prepare(tmp, mode, policy, n, profile=None, library=LIBRARY, name=None):
    profile_path = None
    if profile is not None:
        profile_path = Path(tmp) / f"profile-{policy}-{n}-{mode}.json"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
    output = Path(tmp) / (name or f"{mode}-{policy}-n{n}")
    summary = prep.prepare(mode, policy, n, library, profile_path, output)
    return summary, output / "payload" / summary["run_name"]


def extract(output_dir, destination):
    with tarfile.open(Path(output_dir) / "payload.tar") as archive:
        archive.extractall(destination, filter="data")


class NineConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cxl-ppa-prep-")
        cls.head = git_out("rev-parse", "HEAD")
        cls.runs = {}
        for policy, n in NINE:
            for mode in ("probe", "syn"):
                profile = valid_profile() if mode == "syn" else None
                cls.runs[(mode, policy, n)] = prepare(cls.tmp, mode, policy, n, profile)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_exact_nine_parameters_and_expectations(self):
        for (mode, policy, n), (summary, payload) in self.runs.items():
            with self.subTest(mode=mode, policy=policy, n=n):
                code = {"fcfs": 0, "rr": 1, "fai-main": 2}[policy]
                elab = f"N_SRC={n},POLICY={code},RR_QUANTUM=10,FAI_W=5000000"
                self.assertEqual(summary["elab_parameters"], elab)
                config = (payload / "run_config.tcl").read_text(encoding="ascii")
                self.assertIn(f"set ELAB_PARAMETERS {{{elab}}}\n", config)
                self.assertIn("set TOP_MODULE {switch_top}\n", config)
                params = json.loads((payload / "parameters.json").read_text(encoding="ascii"))
                self.assertEqual((params["N_SRC"], params["POLICY"], params["RR_QUANTUM"], params["FAI_W"],
                                  params["D"], params["M"], params["DESC_W"]), (n, code, 10, 5_000_000, 16, 1, 105))
                exp = params["expected"]
                desc, ts = n * 16 * 105, n * 16 * 32
                self.assertEqual(exp["port_bits"]["i_in_desc"], n * 105)
                self.assertEqual(exp["port_bits"]["o_out_source"], {4: 2, 8: 3, 16: 4}[n])
                self.assertEqual(exp["timed_input_bits"], n + n * 105 + 2)
                if policy == "rr":
                    self.assertFalse(params["arrival_metadata"])
                    self.assertEqual((exp["min_register_bits"], exp["max_register_bits_exclusive"]), (desc, desc + ts))
                    self.assertIn("set FORBIDDEN_POLICY_MODULES [list {cxl_fcfs_sel} {cxl_fai_main_sched}]", config)
                else:
                    self.assertTrue(params["arrival_metadata"])
                    self.assertEqual((exp["min_register_bits"], exp["max_register_bits_exclusive"]), (desc + ts, None))
                self.assertEqual((payload / "expected" / "dc_status.rpt").read_text(encoding="ascii"),
                                 f"DC_STATUS: COMMANDS_COMPLETED\nMODE: {mode}\nRUN: cxl-ppa-{mode}-{policy}-n{n}\n"
                                 f"TOP: switch_top\nELAB_PARAMETERS: {elab}\n")

    def test_filelist_order_and_source_hash_attribution(self):
        self.assertEqual(prep.parse_filelist(prep.ROOT), EXPECTED_SOURCES)
        for key, (summary, payload) in self.runs.items():
            with self.subTest(run=key):
                manifest = json.loads((payload / "manifest.json").read_text(encoding="ascii"))
                self.assertEqual(manifest["source"]["head"], self.head)
                self.assertEqual(manifest["source"]["filelist_order"], EXPECTED_SOURCES)
                config = (payload / "run_config.tcl").read_text(encoding="ascii")
                self.assertIn("set RTL_FILES [list " + " ".join("{%s}" % s for s in EXPECTED_SOURCES) + "]", config)
                records = {r["path"]: r for r in manifest["source"]["exported_files"]}
                for name in EXPECTED_SOURCES + [prep.FILELIST, prep.APPROVAL]:
                    data = (payload / name).read_bytes()
                    self.assertEqual(data, (prep.ROOT / name).read_bytes())
                    self.assertEqual(records[name]["sha256"], hashlib.sha256(data).hexdigest())
                    self.assertEqual(records[name]["git_blob"], git_out("rev-parse", f"HEAD:{name}"))
                    self.assertTrue(records[name]["matches_head"])
                for name, digest in manifest["file_sha256"].items():
                    self.assertEqual(hashlib.sha256((payload / name).read_bytes()).hexdigest(), digest)
                sums = (payload / "SHA256SUMS").read_text(encoding="ascii").splitlines()
                listed = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in sums}
                files = {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
                self.assertEqual(set(listed), files - {"SHA256SUMS"})

    def test_profile_hash_and_library_pin_identical_for_all_nine(self):
        hashes = set()
        for (mode, policy, n), (summary, payload) in self.runs.items():
            if mode != "syn":
                continue
            hashes.add(summary["profile_canonical_sha256"])
            run_sh = (payload / "run.sh").read_text(encoding="ascii")
            self.assertIn(f"readonly EXPECTED_LIBRARY_SHA256='{'a' * 64}'", run_sh)
            self.assertTrue((payload / "sta" / "ppa_pt.tcl").is_file())
            self.assertTrue((payload / "expected" / "pt_status.rpt").is_file())
        self.assertEqual(len(hashes), 1)
        probe_payload = self.runs[("probe", "fcfs", 4)][1]
        self.assertFalse((probe_payload / "sta").exists())
        self.assertFalse((probe_payload / "profile.json").exists())
        self.assertIn("readonly EXPECTED_LIBRARY_SHA256=''", (probe_payload / "run.sh").read_text(encoding="ascii"))

    def test_tar_is_safe_complete_and_run_sh_executable_lf(self):
        for key, (summary, payload) in self.runs.items():
            with self.subTest(run=key):
                output = payload.parent.parent
                tar_bytes = (output / "payload.tar").read_bytes()
                self.assertEqual((output / "payload.tar.sha256").read_text(encoding="ascii"),
                                 f"{hashlib.sha256(tar_bytes).hexdigest()}  payload.tar\n")
                with tarfile.open(output / "payload.tar") as archive:
                    members = archive.getmembers()
                regular = {}
                for member in members:
                    name = PurePosixPath(member.name)
                    self.assertFalse(name.is_absolute())
                    self.assertNotIn("..", name.parts)
                    self.assertEqual(name.parts[0], summary["run_name"])
                    self.assertTrue(member.isfile() or member.isdir())
                    self.assertEqual((member.uid, member.gid), (0, 0))
                    if member.isfile():
                        regular["/".join(name.parts[1:])] = member
                files = {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
                self.assertEqual(set(regular), files)
                self.assertEqual(regular["run.sh"].mode, 0o755)
                self.assertTrue(all(m.mode == 0o644 for n_, m in regular.items() if n_ != "run.sh"))
                run_sh = (payload / "run.sh").read_bytes()
                self.assertTrue(run_sh.startswith(b"#!/usr/bin/env bash\n"))
                self.assertNotIn(b"\r", run_sh)
                for name in files:
                    self.assertNotIn(".git", PurePosixPath(name).parts)
                    self.assertFalse(PurePosixPath(name).suffix in prep.FORBIDDEN_SUFFIXES)
                manifest = json.loads((payload / "manifest.json").read_text(encoding="ascii"))
                self.assertFalse(manifest["target_library"]["content_bundled"])
                self.assertEqual(manifest["power"], "NOT_RUN")


class SupplementaryAlgorithm2Tests(unittest.TestCase):
    def test_explicit_opt_in_and_n4_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            for policy, n, opt_in in [("fai-alg2", 4, False), ("fai-alg2", 8, True),
                                       ("fai-alg2", 16, True), ("fai-main", 4, True), ("rr", 4, True), ("fcfs", 4, True)]:
                with self.subTest(policy=policy, n=n, opt_in=opt_in), self.assertRaises(ValueError):
                    prep.prepare("probe", policy, n, LIBRARY, None, Path(tmp) / "rejected",
                                 supplementary_alg2=opt_in)
            self.assertFalse((Path(tmp) / "rejected").exists())
        self.assertEqual(len(prep.POLICIES) * len(prep.N_VALUES), 9)
        self.assertEqual(set(prep.POLICIES), {"fcfs", "rr", "fai-main"})

    def test_supplementary_payload_storage_module_and_manifest(self):
        profile_path = prep.ROOT / "syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json"
        profile = json.loads(profile_path.read_text())
        library = "/remote/example/" + profile["library"]["db_basename"]
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ("probe", "syn"):
                with self.subTest(mode=mode):
                    output = Path(tmp) / mode
                    summary = prep.prepare(mode, "fai-alg2", 4, library,
                                           profile_path if mode == "syn" else None, output,
                                           supplementary_alg2=True)
                    payload = output / "payload" / summary["run_name"]
                    manifest = json.loads((payload / "manifest.json").read_text())
                    params = json.loads((payload / "parameters.json").read_text())
                    self.assertTrue(params["supplementary"])
                    self.assertEqual(manifest["parameters"], params)
                    self.assertEqual(params["POLICY"], 3)
                    self.assertEqual(params["elab_parameters"], "N_SRC=4,POLICY=3,RR_QUANTUM=10,FAI_W=5000000")
                    self.assertTrue(params["arrival_metadata"])
                    self.assertEqual(params["expected"], prep.parameters("fai-main", 4)["expected"])
                    self.assertEqual(params["expected"]["descriptor_storage_bits"], 4 * 16 * 105)
                    self.assertEqual(params["expected"]["timestamp_storage_bits"], 4 * 16 * 32)
                    self.assertEqual(params["expected"]["policy_module"], "cxl_fai_main_sched")
                    config = (payload / "run_config.tcl").read_text()
                    self.assertIn("set EXPECT_POLICY_MODULE {cxl_fai_main_sched}", config)
                    top = (payload / prep.TOP_SOURCE).read_text()
                    self.assertIn("gen_policy_fai_alg2", top)
                    self.assertIn("arrival_cnt_q", top)
                    self.assertIn("FAI_CTX_W", top)
                    self.assertEqual(summary["profile_canonical_sha256"], prep.ALG2_PROFILE_SHA256 if mode == "syn" else None)
                    for rel, digest in manifest["file_sha256"].items():
                        self.assertEqual(hashlib.sha256((payload / rel).read_bytes()).hexdigest(), digest)
                    with tarfile.open(output / "payload.tar") as archive:
                        self.assertFalse(any(set(Path(m.name).suffixes) & prep.FORBIDDEN_SUFFIXES for m in archive.getmembers()))
                    self.assertFalse(manifest["target_library"]["content_bundled"])

    def test_supplementary_rejects_other_synthesis_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "profile.json"
            profile.write_text(json.dumps(valid_profile()))
            with self.assertRaisesRegex(ValueError, "frozen"):
                prep.prepare("syn", "fai-alg2", 4, LIBRARY, profile, Path(tmp) / "out", supplementary_alg2=True)

    def test_cli_opt_in_cannot_apply_to_template(self):
        with self.assertRaises(SystemExit) as error:
            prep.main(["--print-profile-template", "--supplementary-alg2"])
        self.assertEqual(error.exception.code, 2)


class ProfileValidationTests(unittest.TestCase):
    def assert_rejected(self, profile, pattern=None, library=LIBRARY):
        with self.assertRaisesRegex(ValueError, pattern or "."):
            prep.validate_profile(profile, library)

    def mutated(self, path, value=None, delete=False):
        profile = valid_profile()
        node = profile
        for key in path[:-1]:
            node = node[key]
        if delete:
            del node[path[-1]]
        else:
            node[path[-1]] = value
        return profile

    def test_valid_profile_accepted(self):
        prep.validate_profile(valid_profile(), LIBRARY)
        zero = self.mutated(("wire_load",), {"method": "zero_wireload", "rationale": "reviewed reason"})
        prep.validate_profile(zero, LIBRARY)

    def test_template_is_rejected_until_filled(self):
        self.assert_rejected(prep.profile_template())

    def test_cap_scale_schema_and_default_config(self):
        profile = valid_profile()
        before = prep.canonical_json(profile)
        params = prep.parameters("fcfs", 4)
        config = prep.run_config("syn", "unit", params, LIBRARY, EXPECTED_SOURCES, profile, "a" * 64)
        self.assertNotIn(b"MAX_CAPACITANCE_SCALE", config)
        self.assertEqual(prep.canonical_json(profile), before)
        for value in (1, 0.75, 0.01):
            profile["optimization"] = {"max_capacitance_scale": value}
            prep.validate_profile(profile, LIBRARY)
            config = prep.run_config("syn", "unit", params, LIBRARY, EXPECTED_SOURCES, profile, "a" * 64)
            self.assertIn(f"set MAX_CAPACITANCE_SCALE {prep.tcl_number(value)}\n".encode(), config)
        for value in (0, -1, 1.01, True, False, "0.75", None, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                profile["optimization"] = {"max_capacitance_scale": value}
                self.assert_rejected(profile)
        for opt in ({}, {"max_capacitance_scale": 0.75, "extra": 1}, None, []):
            profile["optimization"] = opt
            self.assert_rejected(profile)

    def test_cap_scale_payload_requires_restoration_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = valid_profile()
            profile["optimization"] = {"max_capacitance_scale": 0.75}
            _, payload = prepare(tmp, "syn", "fcfs", 4, profile)
            manifest = json.loads((payload / "manifest.json").read_text())
            self.assertIn("reports/dc_cap_optimization.rpt", manifest["required_outputs"]["dc"])
            self.assertIn("reports/dc_cap_optimization.rpt\n", (payload / "expected/dc_required.txt").read_text())

    def test_missing_and_unknown_keys_rejected(self):
        for key in prep.PROFILE_KEYS:
            with self.subTest(top=key):
                self.assert_rejected(self.mutated((key,), delete=True), "missing")
        for section, keys in list(prep.PROFILE_SECTIONS.items()):
            for key in keys:
                with self.subTest(section=section, key=key):
                    self.assert_rejected(self.mutated((section, key), delete=True), "missing")
        extra = valid_profile()
        extra["clock"]["multicycle"] = 2
        self.assert_rejected(extra, "unexpected")
        extra = valid_profile()
        extra["false_paths"] = []
        self.assert_rejected(extra, "unexpected")

    def test_bad_numeric_values_rejected(self):
        numeric = [("clock", k) for k in ("period", "setup_uncertainty", "hold_uncertainty", "transition")]
        numeric += [("io", k) for k in prep.PROFILE_SECTIONS["io"]]
        for path in numeric:
            for bad in (None, "1.0", True, float("nan"), float("inf"), -float("inf"), -0.5, 10 ** 400, [1]):
                with self.subTest(path=path, bad=bad):
                    self.assert_rejected(self.mutated(path, bad))
        self.assert_rejected(self.mutated(("clock", "period"), 0), "positive")

    def test_nonfinite_json_literals_and_duplicates_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            base = json.dumps(valid_profile())
            for literal in ("NaN", "Infinity", "-Infinity", "1e999"):
                with self.subTest(literal=literal):
                    path.write_text(base.replace('"period": 7', f'"period": {literal}'), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        prep.load_profile(path, LIBRARY)
            path.write_text(base.replace('"period": 7', '"period": 7, "period": 5'), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                prep.load_profile(path, LIBRARY)
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                prep.load_profile(path, LIBRARY)
            path.write_bytes(b"\xef\xbb\xbf" + base.encode("utf-8"))
            prep.load_profile(path, LIBRARY)

    def test_contradictory_values_rejected(self):
        cases = [
            (("io", "input_delay_min"), 2.0, "exceeds"),
            (("io", "output_delay_min"), 2.0, "exceeds"),
            (("io", "input_delay_max"), 7, "smaller than clock.period"),
            (("io", "output_delay_max"), 8, "smaller than clock.period"),
            (("clock", "setup_uncertainty"), 7, "smaller than clock.period"),
            (("clock", "port"), "core_clk", "must be clk"),
            (("library", "db_basename"), "other.db", "contradicts"),
            (("wire_load", "mode"), "enclosed", "must be top"),
            (("wire_load", "method"), "auto", "fixed_model or zero_wireload"),
            (("compile", "command"), "compile_ultra", "must be compile"),
            (("compile", "map_effort"), "low", "map_effort"),
            (("power", "status"), "MEASURED", "NOT_RUN"),
            (("schema",), "v0", "schema"),
            (("status",), "DRAFT", "PILOT or FROZEN"),
            (("review", "reviewed_on"), "2026-13-40", "date"),
            (("library", "sha256"), "ABC", "unsupported"),
            (("units", "time"), "1s", "unsupported"),
            (("units", "capacitance"), "1nF", "unsupported"),
            (("library", "operating_conditions"), "tt; exit", "unsupported"),
            (("wire_load", "model"), "a b", "unsupported"),
            (("wire_load", "rationale"), "", "nonempty"),
        ]
        for path, value, pattern in cases:
            with self.subTest(path=path, value=value):
                self.assert_rejected(self.mutated(path, value), pattern)
        zero_with_model = self.mutated(("wire_load",), {"method": "zero_wireload", "rationale": "r", "model": "x"})
        self.assert_rejected(zero_with_model, "unexpected")

    def test_mode_profile_combinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "p.json"
            profile.write_text(json.dumps(valid_profile()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "probe mode applies no profile"):
                prep.prepare("probe", "fcfs", 4, LIBRARY, profile, Path(tmp) / "a")
            with self.assertRaisesRegex(ValueError, "requires --profile"):
                prep.prepare("syn", "fcfs", 4, LIBRARY, None, Path(tmp) / "b")
            for policy, n in (("fai-alg2", 4), ("fcfs", 2), ("rr", 32)):
                with self.assertRaisesRegex(ValueError, "supplementary-alg2 opt-in" if policy == "fai-alg2" else "primary nine"):
                    prep.prepare("probe", policy, n, LIBRARY, None, Path(tmp) / "c")
            self.assertEqual(sorted(os.listdir(tmp)), ["p.json"])


class PathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cxl-ppa-paths-"))
        self.root = self.tmp / "repo"
        for name in EXPECTED_SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// fixture\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_filelist(self, lines):
        path = self.root / "rtl" / "filelist_switch.f"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_fixture_filelist_parses(self):
        self.write_filelist(["// header", ""] + [f"{s}  // c" for s in EXPECTED_SOURCES])
        self.assertEqual(prep.parse_filelist(self.root), EXPECTED_SOURCES)

    def test_unsafe_filelist_entries_rejected(self):
        outside = self.tmp / "outside.sv"
        outside.write_text("// outside\n", encoding="utf-8")
        (self.root / "rtl" / "lib.db").write_bytes(b"not a library")
        bad_entries = {
            "absolute": str(outside).replace("\\", "/"),
            "traversal": "rtl/../../outside.sv",
            "backslash": "rtl\\top\\switch_top.sv",
            "option": "-f other.f",
            "incdir": "+incdir+rtl/include",
            "missing": "rtl/common/missing.sv",
            "proprietary": "rtl/lib.db",
            "two_paths": "rtl/common/cxl_rr_sched.sv rtl/common/cxl_fcfs_sel.sv",
            "duplicate": "rtl/common/cxl_rr_sched.sv",
        }
        for label, entry in bad_entries.items():
            with self.subTest(label=label):
                self.write_filelist(EXPECTED_SOURCES[:-1] + [entry, EXPECTED_SOURCES[-1]])
                with self.assertRaises(ValueError):
                    prep.parse_filelist(self.root)
        self.write_filelist(EXPECTED_SOURCES[1:2] + EXPECTED_SOURCES[:1] + EXPECTED_SOURCES[2:])
        with self.assertRaisesRegex(ValueError, "package"):
            prep.parse_filelist(self.root)
        self.write_filelist(EXPECTED_SOURCES[:-1])
        with self.assertRaisesRegex(ValueError, "last"):
            prep.parse_filelist(self.root)
        self.write_filelist(["/* block */"] + EXPECTED_SOURCES)
        with self.assertRaisesRegex(ValueError, "block comments"):
            prep.parse_filelist(self.root)

    def test_symlinked_sources_rejected(self):
        outside_dir = self.tmp / "elsewhere"
        outside_dir.mkdir()
        (outside_dir / "cxl_rr_sched.sv").write_text("// outside\n", encoding="utf-8")
        target = self.root / "rtl" / "common" / "cxl_rr_sched.sv"
        target.unlink()
        try:
            os.symlink(outside_dir / "cxl_rr_sched.sv", target)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlinks unavailable here: {error}")
        self.write_filelist(EXPECTED_SOURCES)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            prep.parse_filelist(self.root)
        target.unlink()
        shutil.rmtree(self.root / "rtl" / "top")
        os.symlink(outside_dir, self.root / "rtl" / "top", target_is_directory=True)
        (outside_dir / "switch_top.sv").write_text("// outside\n", encoding="utf-8")
        target.write_text("// fixture\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            prep.parse_filelist(self.root)

    def test_payload_rejects_proprietary_hidden_and_git_members(self):
        for name in ("lib/saed32rvt_tt0p78v25c.db", "x.lib", "x.lib.gz", "tools/dc_shell.so", ".git/config",
                     "rtl/.hidden.sv", "license.lic", "work/a.exe", "a/../b.sv", "/abs.sv"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    prep.check_payload({name: b"x"})
        prep.check_payload({"rtl/top/switch_top.sv": b"x", "SHA256SUMS": b"x", "run.sh": b"x"})

    def test_library_path_validation(self):
        for bad in ("relative/lib.db", "C:\\lib\\x.db", "/a/../b.db", "/a/./b.db", "//a/b.db", "/a b/c.db",
                    "/a/b.db;rm", "/a/$(id).db", "/a/`id`.db", "/a/b.lib", "/a/b.db\n", "/a/{b}.db"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    prep.validate_library(bad)
        self.assertEqual(prep.validate_library(LIBRARY), LIBRARY)

    def test_output_refusals_create_nothing(self):
        existing = self.tmp / "exists"
        existing.mkdir()
        (self.tmp / "file").write_text("x", encoding="utf-8")
        for path, pattern in ((existing, "overwrite"), (self.tmp / "file", "overwrite"),
                              (self.tmp / "missing" / "out", "parent"),
                              (prep.ROOT / "rtl" / "ppa-test-should-not-exist", "artifacts")):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, pattern):
                    prep.prepare("probe", "fcfs", 4, LIBRARY, None, path)
        self.assertFalse((prep.ROOT / "rtl" / "ppa-test-should-not-exist").exists())
        self.assertEqual(sorted(os.listdir(existing)), [])

    def test_modified_accepted_source_rejected_but_flow_change_recorded(self):
        state = prep.source_state(prep.ROOT)
        with patch.object(prep, "head_blob", return_value="0" * 40):
            with self.assertRaisesRegex(ValueError, "differs from HEAD"):
                prep.export_file(prep.ROOT, state["head"], EXPECTED_SOURCES[-1], "rtl")
            with self.assertRaisesRegex(ValueError, "differs from HEAD"):
                prep.export_file(prep.ROOT, state["head"], prep.APPROVAL, "approval")
            _, record = prep.export_file(prep.ROOT, state["head"], prep.DC_SCRIPT, "flow")
            self.assertFalse(record["matches_head"])
        with patch.object(prep, "head_blob", return_value=None):
            with self.assertRaisesRegex(ValueError, "untracked"):
                prep.export_file(prep.ROOT, state["head"], prep.FILELIST, "filelist")


# ------------------------------------------------------------------ run.sh with fake tools

FAKE_TOOL = r"""#!/usr/bin/env bash
# Test-only stand-in for a Synopsys shell. It never runs EDA; it only writes files run.sh checks.
# Its -version banners imitate the identity/release lines of the observed W-2024.09 banners only.
tool="__TOOL__"
scenario="${__VAR__:-ok}"
version_case="${__VAR___VERSION:-__VERSION_DEFAULT__}"
banner() {
  echo "FAKE-TEST-ONLY $tool version output"
  if [[ ${1:-$tool} == dc ]]; then
    printf '                 Design Compiler Graphical\n                 Version W-2024.09 for linux64 - Aug 27, 2024\n'
  else
    printf '                 PrimeTime (R)\n                 Version W-2024.09 for linux64 - Aug 31, 2024\n'
  fi
}
if [[ "${1:-}" == "-version" ]]; then
  case $version_case in
    banner_rc0) banner; exit 0 ;;
    banner_rc1) banner; exit 1 ;;
    banner_stderr_rc1) banner >&2; exit 1 ;;
    silent_rc1) exit 1 ;;
    noise_rc0) echo "starting wrapper"; exit 0 ;;
    error_banner_rc1) banner; echo "Error: Unable to checkout license (SEC-50)"; exit 1 ;;
    wrong_tool_rc0) if [[ $tool == dc ]]; then banner pt; else banner dc; fi; exit 0 ;;
    no_release_rc0) banner | grep -v Version; exit 0 ;;
  esac
  exit 2
fi
[[ "${1:-}" == "-f" ]] || exit 64
while IFS= read -r path; do
  [[ -n $path ]] || continue
  mkdir -p "$(dirname "$path")"
  printf 'fake report for test\n' > "$path"
done < "expected/${tool}_required.txt"
cp "expected/${tool}_status.rpt" "reports/${tool}_status.rpt"
if [[ $tool == dc ]] && grep -qx 'output/switch_top.syn.v' expected/dc_required.txt; then
  printf 'module switch_top (clk, rst_n);\nendmodule\n' > output/switch_top.syn.v
  printf 'create_clock -name core_clk -period 7 [get_ports clk]\n' > output/switch_top.syn.sdc
fi
[[ -f reports/${tool}_constraints.rpt ]] && \
  printf '   n47   0.107692   0.109245   -0.001553 (VIOLATED)\n' >> "reports/${tool}_constraints.rpt"
[[ $tool == pt ]] && printf 'ANALYSIS_COVERAGE = UNTESTED_CHECKS_PRESENT_REVIEW_REQUIRED\n' >> reports/pt_coverage_summary.rpt
echo "Information: fake test tool run (TEST-1)"
echo "Diagnostics summary: 0 errors, 4 warnings, 11 informationals"
case $scenario in
  ok) ;;
  diag_error_exit0) echo "Diagnostics summary: 1 error, 4 warnings, 11 informationals" ;;
  error_exit0) echo "Error: Cannot find the design 'switch_top' in the library 'WORK'. (LBR-0)" ;;
  fatal_exit0) echo "Fatal: Internal system error, cannot recover." ;;
  eda_failure_exit0) echo "EDA_FAILURE: link raised" ;;
  unresolved_exit0) echo "Warning: Unable to resolve reference 'cxl_desc_fifo' in 'switch_top'. (LINK-5)" ;;
  no_marker) rm -f "reports/${tool}_status.rpt" ;;
  bad_marker) echo "STATUS: SUCCESS" > "reports/${tool}_status.rpt" ;;
  missing_report) rm -f "$(grep -m1 '_structure.rpt' "expected/${tool}_required.txt")" ;;
  empty_report) : > "$(grep -m1 '_structure.rpt' "expected/${tool}_required.txt")" ;;
  report_error) echo "Error: report failed (RPT-1)" >> "$(grep -m1 '_structure.rpt' "expected/${tool}_required.txt")" ;;
  missing_netlist) rm -f output/switch_top.syn.v ;;
  sdc_exception) echo 'set_false_path -from [get_ports rst_n]' >> output/switch_top.syn.sdc ;;
  modify_netlist) echo '// changed' >> output/switch_top.syn.v ;;
  exit1) exit 1 ;;
esac
exit 0
"""


@unittest.skipIf(os.name == "nt" or not shutil.which("bash") or not shutil.which("sha256sum"),
                 "run.sh checks need a POSIX bash with GNU coreutils (run under WSL/Linux)")
class RunScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="cxl_ppa_runsh_"))
        cls.library = cls.tmp / "remote_lib" / "fake_tt.db"
        cls.library.parent.mkdir()
        cls.library.write_bytes(b"synthetic bytes, not a library\n")
        sha = hashlib.sha256(cls.library.read_bytes()).hexdigest()
        cls.syn_out = prepare(cls.tmp, "syn", "rr", 8, valid_profile(sha=sha), library=str(cls.library))[1].parent.parent
        cls.probe_out = prepare(cls.tmp, "probe", "fai-main", 16, library=str(cls.library))[1].parent.parent
        cls.bin = cls.tmp / "fakebin"
        cls.bin.mkdir()
        # Default version behavior mirrors the observed host: dc_shell -version exits 1, pt_shell 0.
        for tool, var, default in (("dc", "FAKE_DC", "banner_rc1"), ("pt", "FAKE_PT", "banner_rc0")):
            path = cls.bin / f"{tool}_shell"
            script = FAKE_TOOL.replace("__TOOL__", tool).replace("__VAR__", var).replace("__VERSION_DEFAULT__", default)
            path.write_text(script, encoding="ascii")
            path.chmod(0o755)
        cls.counter = 0

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_case(self, output, dc="ok", pt="ok", with_pt=True, tamper=None, versions=None):
        type(self).counter += 1
        root = self.tmp / f"case{self.counter}"
        root.mkdir()
        extract(output, root)
        run_dir = next(root.iterdir())
        if tamper:
            tamper(run_dir)
        bin_dir = self.bin
        if not with_pt:
            bin_dir = root / "bin_without_pt"
            bin_dir.mkdir()
            shutil.copy2(self.bin / "dc_shell", bin_dir / "dc_shell")
        env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(root), "LANG": "C",
               "FAKE_DC": dc, "FAKE_PT": pt, **(versions or {})}
        done = subprocess.run(["bash", "./run.sh"], cwd=run_dir, env=env, capture_output=True, text=True, check=False)
        status = (run_dir / "execution-status.txt").read_text() if (run_dir / "execution-status.txt").exists() else ""
        return done, status, run_dir

    def assert_failed(self, result, stage):
        done, status, _ = result
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(status.startswith("FAILED\n"), status)
        self.assertIn(f"STAGE: {stage}\n", status)
        self.assertNotIn("COMMANDS_COMPLETED_REVIEW_REQUIRED", status)

    def test_completed_runs_report_review_required_not_pass(self):
        for output in (self.probe_out, self.syn_out):
            with self.subTest(output=output.name):
                done, status, run_dir = self.run_case(output)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                lines = status.splitlines()
                self.assertEqual(lines[0], "COMMANDS_COMPLETED_REVIEW_REQUIRED")
                self.assertFalse([line for line in lines if line == "PASS" or line.endswith(": PASS")])
                self.assertIn("not PASS, timing closure or accepted PPA", status)
                self.assertIn("POWER_STATUS: NOT_RUN", (run_dir / "reports" / "power_status.rpt").read_text())
                self.assertTrue((run_dir / "RESULT_SHA256SUMS").is_file())
                self.assertIn("sha256=", (run_dir / "logs" / "library.log").read_text())
                environment = (run_dir / "logs" / "environment.log").read_text()
                # Observed host behavior: dc_shell -version exits 1 with a valid banner.
                self.assertIn("dc_shell_version_query_exit=1\n", environment)
                self.assertIn("dc_shell_release=W-2024.09\n", environment)
                self.assertIn("Design Compiler", (run_dir / "logs" / "dc_shell-version.stdout").read_text())
                self.assertTrue((run_dir / "logs" / "dc_shell-version.stderr").is_file())
                self.assertEqual((run_dir / "logs" / "tool-exit.txt").read_text().splitlines()[0], "dc_exit=0")
                if output == self.syn_out:
                    self.assertIn("pt_shell_version_query_exit=0\n", environment)
                    # Violations and untested checks are review facts, not automatic failure or waiver.
                    self.assertIn("dc_constraints_violated_lines: 1\n", status)
                    self.assertIn("pt_constraints_violated_lines: 1\n", status)
                    self.assertIn("pt_analysis_coverage: UNTESTED_CHECKS_PRESENT_REVIEW_REQUIRED\n", status)
                else:
                    self.assertNotIn("violated_lines", status)

    def test_version_query_banner_identity(self):
        accepted = self.run_case(self.syn_out, versions={"FAKE_DC_VERSION": "banner_stderr_rc1",
                                                         "FAKE_PT_VERSION": "banner_rc1"})
        self.assertEqual(accepted[0].returncode, 0, accepted[0].stdout + accepted[0].stderr)
        self.assertIn("pt_shell_version_query_exit=1\n", (accepted[2] / "logs" / "environment.log").read_text())
        self.assertIn("PrimeTime", (accepted[2] / "logs" / "pt_shell-version.stdout").read_text())
        for case in ("silent_rc1", "noise_rc0", "error_banner_rc1", "wrong_tool_rc0", "no_release_rc0"):
            for variable in ("FAKE_DC_VERSION", "FAKE_PT_VERSION"):
                with self.subTest(case=case, tool=variable):
                    self.assert_failed(self.run_case(self.syn_out, versions={variable: case}), "tools")

    def test_tool_error_messages_with_exit_zero_fail(self):
        for scenario in ("error_exit0", "fatal_exit0", "eda_failure_exit0", "unresolved_exit0", "diag_error_exit0",
                         "no_marker", "bad_marker", "missing_report", "empty_report", "report_error", "exit1"):
            with self.subTest(dc=scenario):
                self.assert_failed(self.run_case(self.probe_out, dc=scenario), "dc")

    def test_dc_handoff_failures(self):
        self.assert_failed(self.run_case(self.syn_out, dc="missing_netlist"), "dc")
        self.assert_failed(self.run_case(self.syn_out, dc="sdc_exception"), "dc-handoff")

    def test_pt_failures(self):
        for scenario in ("error_exit0", "unresolved_exit0", "diag_error_exit0", "no_marker", "bad_marker",
                         "missing_report", "empty_report", "report_error", "exit1"):
            with self.subTest(pt=scenario):
                self.assert_failed(self.run_case(self.syn_out, pt=scenario), "pt")
        self.assert_failed(self.run_case(self.syn_out, pt="modify_netlist"), "pt")
        self.assert_failed(self.run_case(self.syn_out, with_pt=False), "tools")

    def test_library_and_payload_guards(self):
        original = self.library.read_bytes()
        try:
            self.library.write_bytes(b"different library bytes\n")
            self.assert_failed(self.run_case(self.syn_out), "library")
            self.library.unlink()
            self.assert_failed(self.run_case(self.probe_out), "library")
        finally:
            self.library.write_bytes(original)
        tamper = lambda run_dir: (run_dir / "rtl" / "top" / "switch_top.sv").write_text("// tampered\n")
        self.assert_failed(self.run_case(self.probe_out, tamper=tamper), "payload")

    def test_rerun_refused_without_touching_status(self):
        done, status, run_dir = self.run_case(self.probe_out)
        self.assertEqual(done.returncode, 0)
        again = subprocess.run(["bash", "./run.sh"], cwd=run_dir, capture_output=True, text=True, check=False,
                               env={"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(run_dir), "LANG": "C"})
        self.assertEqual(again.returncode, 91)
        self.assertEqual((run_dir / "execution-status.txt").read_text(), status)


# ------------------------------------------------------------------ Tcl flow with stub commands

STUBS = r"""
set ::STUB_EXIT ""
set ::STUB_STDOUT ""
set ::STUB_CALLS {}
rename puts ::stub_real_puts
proc puts {args} {
    if {[llength $args] == 1} {append ::STUB_STDOUT "[lindex $args 0]\n"; return}
    if {[llength $args] == 2 && [lindex $args 0] eq "-nonewline" && [lindex $args 1] ni {stdout stderr}} {
        return [::stub_real_puts {*}$args]
    }
    if {[llength $args] == 2 && [lindex $args 0] in {stdout stderr}} {append ::STUB_STDOUT "[lindex $args 1]\n"; return}
    return [::stub_real_puts {*}$args]
}
proc exit {{code 0}} {set ::STUB_EXIT $code; return -code error STUB_EXIT_CALLED}
# Like dc_shell/pt_shell -f: evaluate each top-level command and keep its return value (they echo it).
proc stub_echo_source {path} {
    set handle [open $path]; set text [read $handle]; close $handle
    info script $path
    set ::STUB_ECHO {}
    set command ""
    foreach line [split $text "\n"] {
        append command $line "\n"
        if {![info complete $command]} {continue}
        set code [catch {uplevel #0 $command} result]
        lappend ::STUB_ECHO $result
        set command ""
        if {$code} {return -code error $result}
    }
}
proc stub_call {name args} {lappend ::STUB_CALLS [list $name {*}$args]}
proc stub_ok {args} {stub_call {*}$args; return 1}
foreach name {set_host_options define_design_lib read_db analyze link set_operating_conditions set_wire_load_mode
              set_wire_load_model create_clock set_clock_uncertainty set_clock_transition set_input_delay
              set_output_delay set_input_transition set_load compile change_names read_verilog read_sdc
              update_timing set_zero_interconnect_delay_mode} {
    proc $name {args} "stub_call $name {*}\$args; return \[stub_result $name\]"
}
proc stub_result {name} {
    if {[info exists ::STUB(result,$name)]} {return $::STUB(result,$name)}
    return 1
}
proc compile {args} {
    stub_call compile {*}$args
    if {[info exists ::STUB(expect_cap_scale)]} {
        foreach pin {fake_tt/BUF/Y fake_tt/DFF/Q} {
            if {$::STUB(cap,$pin) != $::STUB(original,$pin) * $::STUB(expect_cap_scale)} {
                error "stub compile saw incorrect cap scale"
            }
        }
    }
    set ::STUB(compiled) 1
    if {[info exists ::STUB(throw_compile)]} {error "stub compile raised"}
    return [stub_result compile]
}
proc stub_original_caps {} {
    if {[info exists ::STUB(compiled)]} {
        foreach pin {fake_tt/BUF/Y fake_tt/DFF/Q} {
            if {$::STUB(cap,$pin) != $::STUB(original,$pin)} {error "stub final output saw tightened cap"}
        }
    }
}
set ::search_path {.}
set ::sh_product_version STUB-NOT-SYNOPSYS
proc set_app_var {name value} {stub_call set_app_var $name $value; set ::$name $value; return $value}
proc redirect {flag var script} {
    set out [uplevel #0 $script]
    uplevel #0 [list set $var $out]
    return ""
}
proc stub_text {name} {
    stub_original_caps
    if {[info exists ::STUB(text,$name)]} {return $::STUB(text,$name)}
    return "stub $name output"
}
foreach name {report_design report_hierarchy report_port report_reference report_qor report_timing
              report_constraint report_clock report_units report_analysis_coverage report_global_timing
              report_exceptions report_area report_disable_timing} {
    proc $name {args} "stub_call $name {*}\$args; return \[stub_text $name\]"
}
proc check_design {args} {return ""}
proc check_timing {args} {return ""}
# Observed on W-2024.09: redirected list_libs/report_lib text may be empty; report_lib has no stub.
proc list_libs {} {return ""}
proc get_attribute {args} {
    set object [lindex $args end-1]; set name [lindex $args end]
    stub_call get_attribute $object $name
    if {[string match LIBPIN:* $object]} {
        set pin [string range $object 7 end]
        if {$name eq "direction"} {return $::STUB(direction,$pin)}
        if {$name eq "max_capacitance"} {
            set value $::STUB(cap,$pin)
            if {[info exists ::STUB(bad_cap_readback)] && $value != $::STUB(original,$pin)} {
                return [expr {$value + 1}]
            }
            return $value
        }
    }
    return $::STUB(attr,$name)
}
proc get_lib_pins {args} {
    stub_call get_lib_pins {*}$args
    set result {}
    foreach pin $::STUB(libpins) {
        if {[string match [lindex $args end] $pin]} {lappend result LIBPIN:$pin}
    }
    return $result
}
proc foreach_in_collection {var collection body} {uplevel 1 [list foreach $var $collection $body]}
proc set_attribute {object name value} {
    stub_call set_attribute $object $name $value
    set pin [string range $object 7 end]
    if {$value == $::STUB(original,$pin) && [info exists ::STUB(false_cap_restore)]} {return 0}
    if {$value == $::STUB(original,$pin) && [info exists ::STUB(throw_cap_restore)]} {error "stub restore rejected"}
    if {$value == $::STUB(original,$pin) && [info exists ::STUB(no_op_cap_restore)]} {return $object}
    if {[info exists ::STUB(native_cap_storage)]} {
        binary scan [binary format f $value] f rounded
        set ::STUB(cap,$pin) [format %.6f $rounded]
    } else {
        set ::STUB(cap,$pin) $value
    }
    return $object
}
proc elaborate {args} {
    stub_call elaborate {*}$args
    set ::STUB(current) "switch_top_N_SRC$::PARAM_N_SRC\_POLICY$::PARAM_POLICY"
    return [stub_result elaborate]
}
proc current_design {args} {
    if {[llength $args]} {stub_call current_design {*}$args; set ::STUB(current) [lindex $args 0]}
    return "DESIGN:$::STUB(current)"
}
proc link_design {name} {stub_call link_design $name; set ::STUB(current) $name; return [stub_result link_design]}
proc rename_design {old new} {stub_call rename_design $old $new; return 1}
proc get_object_name {object} {
    if {$object eq "LIBS"} {return [list $::STUB(lib) gtech standard.sldb]}
    return [string range $object [expr {[string first : $object] + 1}] end]
}
proc get_designs {args} {return {}}
proc get_libs {args} {
    set name [lindex $args end]
    if {$name eq "*"} {return LIBS}
    if {$name in [list $::STUB(lib) gtech standard.sldb]} {return "LIB:$name"}
    return {}
}
proc get_clocks {args} {return CLOCK}
proc all_outputs {} {return OUTPUTS}
proc all_inputs {} {return INPUTS}
proc get_ports {args} {
    set pattern [lindex $args end]
    if {[string index $pattern end] eq "*"} {return "PORTS:[string range $pattern 0 end-1]"}
    return "PORT:$pattern"
}
proc remove_from_collection {a b} {
    if {$a eq "INPUTS" && $b eq "PORT:clk"} {return TIMED}
    if {$a eq "PORT:rst_n" && $b eq "TIMED"} {return EMPTY}
    return "UNKNOWN"
}
proc get_cells {args} {
    regexp {ref_name=~(\S+)} [lindex $args end] -> pattern
    return "CELLS:$pattern"
}
proc all_registers {args} {
    if {"-level_sensitive" in $args} {return REGS:latch}
    if {"-edge_triggered" in $args} {return REGS:edge}
    return REGS:all
}
proc sizeof_collection {collection} {
    switch -glob -- $collection {
        PORTS:* {set key [string range $collection 6 end]; return [expr {[info exists ::STUB(port,$key)] ? $::STUB(port,$key) : 0}]}
        PORT:* {return 1}
        TIMED {return $::STUB(timed)}
        EMPTY {return 0}
        LIB:* {return 1}
        CELLS:* {set key [string range $collection 6 end]; return [expr {[info exists ::STUB(cells,$key)] ? $::STUB(cells,$key) : 0}]}
        REGS:all {return $::STUB(regs)}
        REGS:edge {return $::STUB(regs)}
        REGS:latch {return $::STUB(latches)}
        default {return [llength $collection]}
    }
}
proc write {args} {
    stub_original_caps
    stub_call write {*}$args
    set handle [open [lindex $args end] w]; ::stub_real_puts $handle "module switch_top (clk);"; close $handle
    return 1
}
proc write_sdc {args} {
    stub_original_caps
    stub_call write_sdc {*}$args
    set handle [open [lindex $args end] w]; ::stub_real_puts $handle "create_clock"; close $handle
    return 1
}
"""

AREA_TEXT = """Number of ports:                          430
Number of nets:                          9000
Number of cells:                            7
Number of combinational cells:           5000
Number of sequential cells:              8900
Number of macros/black boxes:               0
Number of buf/inv:                        900
Number of references:                       7

Combinational area:              1000.500000
Buf/Inv area:                     100.250000
Noncombinational area:           2000.250000
Macro/Black Box area:               0.000000
Net Interconnect area:      undefined  (Wire load has zero net area)

Total cell area:                 3000.750000
Total area:                 undefined
"""

# Excerpts copied from the Codex-run FastX W-2024.09 pilot reports (pilot-fcfs-n4-pt-20261020a);
# PilotEvidenceTests confirms them against the local copies when those ignored files are present.
PILOT_DIR = prep.ROOT / "artifacts" / "fastx" / "pilot-fcfs-n4-pt-20261020a" / "reports"
DC_UNITS_OBSERVED = """Units
------------------------------------
Time_unit            : 1.0e-09 Second(ns)
Capacitive_load_unit : 1.0e-15 Farad(fF)
Resistance_unit      : 1.0e+6 Ohm(MOhm)
Voltage_unit         : 1 Volt
Power_unit           : N/A
Current_unit         : 1.0e-06 Amp(uA)
"""
PT_UNITS_OBSERVED = """Units
---------------------------------------------
Capacitive_load_unit        : 1e-15 Farad
Current_unit                : 1e-06 Amp
Resistance_unit             : 1e+06 Ohm
Time_unit                   : 1e-09 Second
Voltage_unit                : 1 Volt
"""
PT_COVERAGE_OBSERVED = """Type of Check         Total              Met         Violated         Untested
--------------------------------------------------------------------------------
setup                  8920      8888 (100%)         0 (  0%)        32 (  0%)
hold                   8920      8888 (100%)         0 (  0%)        32 (  0%)
min_pulse_width       17712     17712 (100%)         0 (  0%)         0 (  0%)
out_setup               112       112 (100%)         0 (  0%)         0 (  0%)
out_hold                112       112 (100%)         0 (  0%)         0 (  0%)
--------------------------------------------------------------------------------
All Checks            35776     35712 (100%)         0 (  0%)        64 (  0%)
"""

# Synthetic path record shape (Startpoint ... slack (MET)); the real PT text is confirmed on the host.
TIMING_PATH_TEXT = """  Startpoint: stub_start_reg
  Endpoint: stub_end_reg
  data arrival time                    1.000000
  slack (MET)                          8.765432
"""
# Observed in the real PT pilot (native-syn-fcfs-n4-direct-a) without -slack_lesser_than 1e9.
NO_PATHS_OBSERVED = "No paths with slack less than 0.000000.\n"


def run_sh_patterns():
    """Failure patterns exactly as generated into run.sh, converted from POSIX ERE to Python."""
    patterns = {}
    for name in ("MESSAGE_RE", "UNRESOLVED_RE", "DIAGNOSTICS_RE", "EXCEPTION_RE"):
        value = re.search(rf"^readonly {name}='([^']*)'$", prep.RUN_SH, re.M).group(1)
        flags = re.I if name == "UNRESOLVED_RE" else 0
        patterns[name] = re.compile(value.replace("[[:space:]]", r"\s"), flags)
    return patterns


class EchoAndPilotEvidenceTests(unittest.TestCase):
    """dc_shell/pt_shell -f echo script lines into their logs (seen in the pilot logs)."""

    def test_echoed_flow_lines_cannot_trigger_failure_patterns(self):
        patterns = run_sh_patterns()
        with tempfile.TemporaryDirectory() as tmp:
            texts = {name: (prep.ROOT / name).read_text(encoding="ascii") for name in (prep.DC_SCRIPT, prep.PT_SCRIPT)}
            for mode, profile in (("probe", None), ("syn", valid_profile())):
                payload = prepare(tmp, mode, "fai-main", 16, profile)[1]
                texts[f"{mode} run_config.tcl"] = (payload / "run_config.tcl").read_text(encoding="ascii")
            for source, text in texts.items():
                for number, line in enumerate(text.splitlines(), 1):
                    for name in ("MESSAGE_RE", "UNRESOLVED_RE", "DIAGNOSTICS_RE"):
                        with self.subTest(source=source, line=number, pattern=name):
                            self.assertIsNone(patterns[name].search(line), line)

    @unittest.skipUnless(PILOT_DIR.is_dir(), "local copy of the FastX pilot reports is absent")
    def test_patterns_against_real_pilot_logs(self):
        patterns = run_sh_patterns()
        dc_log = (PILOT_DIR / "dc.log").read_text(encoding="utf-8", errors="replace")
        pt_log = (PILOT_DIR / "pt.log").read_text(encoding="utf-8", errors="replace")
        for name in ("MESSAGE_RE", "UNRESOLVED_RE", "DIAGNOSTICS_RE"):
            self.assertIsNone(patterns[name].search(dc_log), name)
        # The pilot's redirected SEL-005 error is invisible in pt.log except in its diagnostics summary.
        self.assertIsNone(patterns["MESSAGE_RE"].search(pt_log))
        self.assertIsNotNone(patterns["DIAGNOSTICS_RE"].search(pt_log))
        self.assertIsNotNone(patterns["MESSAGE_RE"].search((PILOT_DIR / "pt_slew_driver.rpt").read_text()))

    @unittest.skipUnless(PILOT_DIR.is_dir(), "local copy of the FastX pilot reports is absent")
    def test_embedded_excerpts_match_pilot_reports(self):
        for excerpt, name in ((DC_UNITS_OBSERVED, "units.rpt"), (PT_UNITS_OBSERVED, "pt_units.rpt"),
                              (PT_COVERAGE_OBSERVED, "pt_coverage.rpt")):
            self.assertIn(excerpt, (PILOT_DIR / name).read_text(encoding="utf-8"), name)


def tcl_interpreter():
    try:
        import tkinter
        return tkinter.Tcl()
    except Exception:  # tkinter or its Tcl runtime may be absent (e.g. a minimal Linux venv)
        return None


@unittest.skipIf(tcl_interpreter() is None, "Tcl via tkinter is unavailable in this Python")
class TclStubFlowTests(unittest.TestCase):
    """Executes ppa_dc.tcl/ppa_pt.tcl control flow against stub commands; not a Synopsys check."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="cxl-ppa-tcl-"))
        cls.outputs = {}
        for policy, n in (("fcfs", 4), ("rr", 8), ("fai-main", 16)):
            for mode in ("probe", "syn"):
                profile = valid_profile() if mode == "syn" else None
                cls.outputs[(mode, policy, n)] = prepare(cls.tmp, mode, policy, n, profile)
        other = valid_profile()
        other["library"]["name"] = "other_name"
        cls.outputs["profile-name-mismatch"] = prepare(cls.tmp, "syn", "fcfs", 4, other, name="syn-other-name")
        scaled = valid_profile()
        scaled["optimization"] = {"max_capacitance_scale": 0.75}
        cls.outputs["cap-scaled"] = prepare(cls.tmp, "syn", "fcfs", 4, scaled, name="syn-cap-scaled")
        scaled["optimization"]["max_capacitance_scale"] = 1
        cls.outputs["cap-unit"] = prepare(cls.tmp, "syn", "fcfs", 4, scaled, name="syn-cap-unit")
        cls.counter = 0

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def stub_state(self, params, **overrides):
        exp = params["expected"]
        state = {"lib": "fake_tt", "timed": exp["timed_input_bits"],
                 "regs": exp["min_register_bits"] + 200, "latches": 0,
                 "attr,time_unit_name": "1ns", "attr,capacitive_load_units": "1.000000ff",
                 "text,report_units": DC_UNITS_OBSERVED, "text,report_analysis_coverage": PT_COVERAGE_OBSERVED,
                 "text,report_timing": TIMING_PATH_TEXT,
                 "text,report_area": AREA_TEXT}
        state["libpins"] = "fake_tt/BUF/Y fake_tt/DFF/Q fake_tt/UNDEFINED/Y fake_tt/BUF/A"
        for pin, cap in (("fake_tt/BUF/Y", 16), ("fake_tt/DFF/Q", 8)):
            state[f"cap,{pin}"] = cap
            state[f"original,{pin}"] = cap
        for pin in ("fake_tt/BUF/Y", "fake_tt/DFF/Q", "fake_tt/UNDEFINED/Y"):
            state[f"direction,{pin}"] = "out"
        state["direction,fake_tt/BUF/A"] = "in"
        for port, bits in exp["port_bits"].items():
            state[f"port,{port}"] = bits
        state["cells,cxl_desc_fifo*"] = exp["fifo_instances"]
        state["cells,cxl_out_hold*"] = 1
        state[f"cells,{exp['policy_module']}*"] = 1
        state.update(overrides)
        return state

    def run_tcl(self, key, script, overrides=None, prepared_run_dir=None, echo=False):
        summary, payload = self.outputs[key]
        type(self).counter += 1
        if prepared_run_dir is None:
            root = self.tmp / f"tcl{self.counter}"
            root.mkdir()
            extract(payload.parent.parent, root)
            run_dir = root / summary["run_name"]
            (run_dir / "reports").mkdir()
            (run_dir / "output").mkdir()
        else:
            run_dir = prepared_run_dir
        params = json.loads((payload / "parameters.json").read_text(encoding="ascii"))
        tcl = tcl_interpreter()
        tcl.eval(STUBS)
        tcl.eval("array set ::STUB {}")
        tcl.eval("set ::STUB(current) none")
        for name, value in self.stub_state(params, **(overrides or {})).items():
            tcl.call("set", f"::STUB({name})", str(value))
        cwd = os.getcwd()
        try:
            try:
                tcl.call("stub_echo_source" if echo else "source", str(run_dir / script))
            except Exception as error:  # the stub exit raises to stop the sourced script
                if "STUB_EXIT_CALLED" not in str(error):
                    raise
        finally:
            os.chdir(cwd)
        count = int(tcl.eval("llength $::STUB_CALLS"))
        calls = [tcl.eval(f"lindex [lindex $::STUB_CALLS {i}] 0") for i in range(count)]
        self.full_calls = [tcl.eval(f"lindex $::STUB_CALLS {i}") for i in range(count)]
        return tcl.eval("set ::STUB_EXIT"), tcl.eval("set ::STUB_STDOUT"), run_dir, calls, tcl

    def calls_named(self, name):
        return [call for call in self.full_calls if call.split()[0] == name]

    def test_cap_scale_applied_during_compile_and_restored_before_outputs(self):
        code, stdout, run_dir, calls, tcl = self.run_tcl("cap-scaled", "syn/ppa_dc.tcl", {"expect_cap_scale": "0.75"})
        self.assertEqual(code, "0", stdout)
        for pin, original in (("BUF/Y", "16"), ("DFF/Q", "8")):
            self.assertEqual(float(tcl.eval(f"set ::STUB(cap,fake_tt/{pin})")), float(original))
        edits = self.calls_named("set_attribute")
        self.assertEqual(len(edits), 4)
        self.assertIn("max_capacitance 12.0", edits[0])
        self.assertIn("max_capacitance 6.0", edits[1])
        self.assertEqual(calls[:calls.index("compile")].count("set_attribute"), 2)
        self.assertEqual(calls[calls.index("compile") + 1:calls.index("write")].count("set_attribute"), 2)
        report = (run_dir / "reports/dc_cap_optimization.rpt").read_text()
        for fact in ("max_capacitance_scale = 0.75", "applied_count = 2", "restored_count = 2",
                     "undefined_output_limit_count = 1", "original_limit_bin = 8 count=1",
                     "original_limit_bin = 16 count=1", "final_library_limits = ORIGINAL"):
            self.assertIn(fact, report)
        self.assertNotIn("fake_tt/BUF", report)  # Aggregate evidence, not a library dump.

    def test_cap_scale_absent_or_one_leaves_library_and_reporting_unchanged(self):
        for key in (("syn", "fcfs", 4), "cap-unit"):
            with self.subTest(key=key):
                code, stdout, run_dir, calls, _ = self.run_tcl(key, "syn/ppa_dc.tcl", {"expect_cap_scale": "1"})
                self.assertEqual(code, "0", stdout)
                self.assertNotIn("set_attribute", calls)
                self.assertNotIn("get_lib_pins", calls)
                self.assertFalse((run_dir / "reports/dc_cap_optimization.rpt").exists())

    def test_cap_scale_restores_on_compile_false_or_exception(self):
        for failure in ({"result,compile": "0"}, {"throw_compile": "1"}):
            with self.subTest(failure=failure):
                code, stdout, run_dir, calls, tcl = self.run_tcl(
                    "cap-scaled", "syn/ppa_dc.tcl", {"expect_cap_scale": "0.75", **failure})
                self.assertEqual(code, "1", stdout)
                self.assertFalse((run_dir / "reports/dc_status.rpt").exists())
                self.assertNotIn("write", calls)
                self.assertEqual(float(tcl.eval("set ::STUB(cap,fake_tt/BUF/Y)")), 16)
                self.assertEqual(float(tcl.eval("set ::STUB(cap,fake_tt/DFF/Q)")), 8)
                report = (run_dir / "reports/dc_cap_optimization.rpt").read_text()
                self.assertIn("compile_status = FAILED_OR_NOT_RUN", report)
                self.assertIn("restored_count = 2", report)
                self.assertIn("final_library_limits = ORIGINAL", report)

    def test_cap_scale_bad_apply_readback_restores_attempted_edit(self):
        code, stdout, run_dir, calls, tcl = self.run_tcl("cap-scaled", "syn/ppa_dc.tcl", {"bad_cap_readback": "1"})
        self.assertEqual(code, "1", stdout)
        self.assertIn("readback", stdout)
        self.assertNotIn("compile", calls)
        self.assertEqual(float(tcl.eval("set ::STUB(cap,fake_tt/BUF/Y)")), 16)
        self.assertFalse((run_dir / "reports/dc_status.rpt").exists())

    def test_cap_scale_native_float32_six_decimal_readback(self):
        overrides = {
            "libpins": "fake_tt/TNBUFF/Y", "direction,fake_tt/TNBUFF/Y": "out",
            "cap,fake_tt/TNBUFF/Y": "67.686699", "original,fake_tt/TNBUFF/Y": "67.686699",
            "native_cap_storage": "1",
        }
        code, stdout, run_dir, calls, tcl = self.run_tcl("cap-scaled", "syn/ppa_dc.tcl", overrides)
        self.assertEqual(code, "0", stdout)
        self.assertIn("50.76502425", self.calls_named("set_attribute")[0])
        self.assertEqual(tcl.eval("set ::STUB(cap,fake_tt/TNBUFF/Y)"), "67.686699")
        # Observed native calibration fixtures, not implementation-mirroring approximate bounds.
        for requested, expected in (("50.76502425", "50.765026"), ("50.765024", "50.765022"),
                                    ("50.765020", "50.765018"), ("50.765000", "50.764999"),
                                    ("12", "12.000000"), ("6", "6.000000")):
            tcl.call("ppa_cap_write", "LIBPIN:fake_tt/TNBUFF/Y", requested, "67.686699")
            self.assertEqual(tcl.eval("set ::STUB(cap,fake_tt/TNBUFF/Y)"), expected)
        # Rounding that erases the intended tightening is not allowed, even at a near-one scale.
        with self.assertRaisesRegex(Exception, "not strictly below"):
            tcl.call("ppa_cap_write", "LIBPIN:fake_tt/TNBUFF/Y", "67.6866989999", "67.686699")
        tcl.call("ppa_cap_write", "LIBPIN:fake_tt/TNBUFF/Y", "67.686699")
        self.assertEqual(tcl.eval("set ::STUB(cap,fake_tt/TNBUFF/Y)"), "67.686699")

    def test_cap_scale_false_or_throwing_restore_blocks_handoff_and_tries_every_pin(self):
        for failure in ({"false_cap_restore": "1"}, {"throw_cap_restore": "1"}, {"no_op_cap_restore": "1"}):
            with self.subTest(failure=failure):
                code, stdout, run_dir, calls, _ = self.run_tcl("cap-scaled", "syn/ppa_dc.tcl", failure)
                self.assertEqual(code, "1", stdout)
                self.assertIn("restoration failed", stdout)
                self.assertEqual(len(self.calls_named("set_attribute")), 4)
                self.assertNotIn("write", calls)
                self.assertNotIn("write_sdc", calls)
                self.assertFalse((run_dir / "reports/dc_status.rpt").exists())
                self.assertIn("final_library_limits = RESTORE_FAILED", (run_dir / "reports/dc_cap_optimization.rpt").read_text())

    def test_dc_probe_and_syn_complete_with_required_outputs(self):
        for key, (summary, payload) in self.outputs.items():
            if not isinstance(key, tuple):
                continue
            mode, policy, n = key
            with self.subTest(mode=mode, policy=policy, n=n):
                code, stdout, run_dir, calls, tcl = self.run_tcl((mode, policy, n), "syn/ppa_dc.tcl")
                self.assertEqual(code, "0", stdout)
                self.assertNotIn("EDA_FAILURE", stdout)
                required = (payload / "expected" / "dc_required.txt").read_text(encoding="ascii").split()
                for name in required:
                    self.assertTrue((run_dir / name).is_file() and (run_dir / name).stat().st_size, name)
                self.assertEqual((run_dir / "reports" / "dc_status.rpt").read_bytes(),
                                 (payload / "expected" / "dc_status.rpt").read_bytes())
                elab_args = tcl.eval("lsearch -inline -index 0 $::STUB_CALLS elaborate")
                self.assertIn(f"-parameters {summary['elab_parameters']}", elab_args)
                self.assertIn("rename_design", calls)
                metadata = (run_dir / "reports" / "lib_metadata.rpt").read_text()
                self.assertIn("library_name = fake_tt\n", metadata)
                self.assertIn("attribute time_unit_name = 1ns (CONSISTENT_WITH_REPORT_UNITS)", metadata)
                self.assertIn("attribute capacitive_load_units = 1.000000ff (CONSISTENT_WITH_REPORT_UNITS)", metadata)
                self.assertIn("report_units time_unit_seconds = 1.0e-09", metadata)
                self.assertIn("report_lib = NOT_USED", metadata)
                self.assertNotIn("report_lib", calls)
                # Units are read after the elaborated design is linked.
                self.assertLess(calls.index("link"), calls.index("report_units"))
                self.assertNotIn("set_false_path", calls)
                for call in self.calls_named("report_timing") + self.calls_named("report_constraint"):
                    self.assertIn("-significant_digits 6", call)
                    self.assertNotIn("-nosplit", call)
                self.assertEqual([c for c in self.full_calls if "-nosplit" in c.split()], [])
                if mode == "probe":
                    for forbidden in ("compile", "create_clock", "set_load", "write", "write_sdc"):
                        self.assertNotIn(forbidden, calls)
                else:
                    self.assertEqual(calls.count("compile"), 1)
                    self.assertIn("AREA_RECONCILIATION = RECONCILED",
                                  (run_dir / "reports" / "area_summary.rpt").read_text())
                    applied = (run_dir / "reports" / "profile_applied.rpt").read_text()
                    self.assertIn("including rst_n", applied)
                    self.assertIn("CLOCK_PERIOD = 7 (1ns)", applied)

    def test_pt_completes_after_dc(self):
        key = ("syn", "rr", 8)
        code, stdout, run_dir, _, _ = self.run_tcl(key, "syn/ppa_dc.tcl")
        self.assertEqual(code, "0", stdout)
        code, stdout, run_dir, calls, _ = self.run_tcl(key, "sta/ppa_pt.tcl", {"text,report_units": PT_UNITS_OBSERVED},
                                                       prepared_run_dir=run_dir)
        self.assertEqual(code, "0", stdout)
        payload = self.outputs[key][1]
        for name in (payload / "expected" / "pt_required.txt").read_text(encoding="ascii").split():
            self.assertTrue((run_dir / name).is_file() and (run_dir / name).stat().st_size, name)
        self.assertEqual((run_dir / "reports" / "pt_status.rpt").read_bytes(),
                         (payload / "expected" / "pt_status.rpt").read_bytes())
        self.assertLess(calls.index("link_design"), calls.index("read_sdc"))
        self.assertLess(calls.index("read_sdc"), calls.index("update_timing"))
        self.assertLess(calls.index("link_design"), calls.index("report_units"))
        for call in self.calls_named("report_timing") + self.calls_named("report_constraint"):
            self.assertIn("-significant_digits 6", call)
            self.assertIn("-nosplit", call)
        timing_calls = self.calls_named("report_timing")
        self.assertEqual(len(timing_calls), 2)
        for call in timing_calls:
            self.assertIn("-max_paths 20 -slack_lesser_than 1e9", call)
        coverage_calls = self.calls_named("report_analysis_coverage")
        self.assertEqual(coverage_calls, ["report_analysis_coverage",
                                          "report_analysis_coverage -status_details untested"])
        self.assertIn("report_disable_timing", calls)
        summary = (run_dir / "reports" / "pt_coverage_summary.rpt").read_text()
        for line in ("all_checks_total = 35776", "met = 35712", "violated = 0", "untested = 64",
                     "ANALYSIS_COVERAGE = UNTESTED_CHECKS_PRESENT_REVIEW_REQUIRED"):
            self.assertIn(line + "\n", summary)

    def test_pt_coverage_summary_states(self):
        key = ("syn", "fcfs", 4)
        code, stdout, dc_run, _, _ = self.run_tcl(key, "syn/ppa_dc.tcl")
        self.assertEqual(code, "0", stdout)
        complete = PT_COVERAGE_OBSERVED.replace("35712 (100%)         0 (  0%)        64 (  0%)",
                                                "35776 (100%)         0 (  0%)         0 (  0%)")
        violated = PT_COVERAGE_OBSERVED.replace("35712 (100%)         0 (  0%)",
                                                "35711 (100%)         1 (  0%)")
        for text, status in ((complete, "ALL_CHECKS_TESTED_AND_MET"),
                             (violated, "VIOLATED_CHECKS_PRESENT_REVIEW_REQUIRED"),
                             ("Type of Check Total\n", "NOT_PARSED_REVIEW_REQUIRED")):
            with self.subTest(status=status):
                self.assertNotEqual(text, PT_COVERAGE_OBSERVED)
                for report in ("pt_status.rpt", "pt_coverage_summary.rpt"):
                    (dc_run / "reports" / report).unlink(missing_ok=True)
                code, stdout, run_dir, _, _ = self.run_tcl(
                    key, "sta/ppa_pt.tcl", {"text,report_units": PT_UNITS_OBSERVED,
                                            "text,report_analysis_coverage": text}, prepared_run_dir=dc_run)
                self.assertEqual(code, "0", stdout)
                self.assertIn(f"ANALYSIS_COVERAGE = {status}\n",
                              (run_dir / "reports" / "pt_coverage_summary.rpt").read_text())

    def assert_dc_fails(self, key, overrides, message):
        code, stdout, run_dir, _, _ = self.run_tcl(key, "syn/ppa_dc.tcl", overrides)
        self.assertEqual(code, "1")
        self.assertIn("EDA_FAILURE", stdout)
        self.assertIn(message, stdout)
        self.assertFalse((run_dir / "reports" / "dc_status.rpt").exists())

    def test_dc_failures_never_write_marker(self):
        probe_rr, syn_fcfs = ("probe", "rr", 8), ("syn", "fcfs", 4)
        rr_bound = 8 * 16 * (105 + 32)
        self.assert_dc_fails(probe_rr, {"result,elaborate": "0"}, "elaborate returned 0")
        self.assert_dc_fails(probe_rr, {"result,link": "0"}, "link returned 0")
        self.assert_dc_fails(probe_rr, {"text,report_design": "Error: stub design failure (X-1)"}, "reported")
        self.assert_dc_fails(probe_rr, {"port,i_in_desc": 420}, "port i_in_desc")
        self.assert_dc_fails(probe_rr, {"regs": rr_bound}, "timestamp-bank bound")
        self.assert_dc_fails(probe_rr, {"cells,cxl_fcfs_sel*": 1}, "forbidden policy module cxl_fcfs_sel")
        self.assert_dc_fails(probe_rr, {"latches": 3}, "latches")
        self.assert_dc_fails(("probe", "fcfs", 4), {"regs": 4 * 16 * 137 - 1}, "below required storage")
        self.assert_dc_fails(("probe", "fai-main", 16), {"cells,cxl_fai_main_sched*": 0}, "missing")
        # Library identity and unit facts (report_lib is not used; report_units after link is).
        self.assert_dc_fails(probe_rr, {"lib": "other_lib"}, "no loaded library is named fake_tt")
        self.assert_dc_fails("profile-name-mismatch", {}, "profile library name other_name differs from loaded library fake_tt")
        self.assert_dc_fails(probe_rr, {"attr,capacitive_load_units": ""}, "capacitive_load_units is empty")
        self.assert_dc_fails(probe_rr, {"attr,time_unit_name": "1ps"}, "time_unit_name = 1ps contradicts report_units")
        self.assert_dc_fails(probe_rr, {"attr,time_unit_name": "Error: no such attribute (UID-341)"}, "reported")
        self.assert_dc_fails(probe_rr, {"text,report_units": ""}, "dc_units.rpt produced no output")
        self.assert_dc_fails(probe_rr, {"text,report_units": "Units\nTime_unit : 1.0e-09 Second(ns)\n"},
                             "no parsable cap unit")
        self.assert_dc_fails(syn_fcfs, {"text,report_units": DC_UNITS_OBSERVED.replace("1.0e-09", "1.0e-12"),
                                        "attr,time_unit_name": "1ps"},
                             "profile declares time unit 1ns but report_units shows 1.0e-12")
        self.assert_dc_fails(syn_fcfs, {"text,report_units": DC_UNITS_OBSERVED.replace("1.0e-15", "1.0e-12"),
                                        "attr,capacitive_load_units": "1pf"},
                             "profile declares cap unit 1ff but report_units shows 1.0e-12")
        self.assert_dc_fails(syn_fcfs, {"timed": 10}, "timed input bits")
        self.assert_dc_fails(syn_fcfs, {"result,compile": "0"}, "compile returned 0")
        black_box = re.sub(r"(Macro/Black Box area:\s+)0\.000000", r"\g<1>12.000000", AREA_TEXT)
        self.assertNotEqual(black_box, AREA_TEXT)
        self.assert_dc_fails(syn_fcfs, {"text,report_area": black_box}, "macro_black_box_area")

    def test_pt_link_failure_never_writes_marker(self):
        key = ("syn", "fai-main", 16)
        code, stdout, run_dir, _, _ = self.run_tcl(key, "syn/ppa_dc.tcl")
        self.assertEqual(code, "0", stdout)
        code, stdout, run_dir, _, _ = self.run_tcl(key, "sta/ppa_pt.tcl", {"result,link_design": "0"},
                                                   prepared_run_dir=run_dir)
        self.assertEqual(code, "1")
        self.assertIn("link_design returned 0", stdout)
        self.assertFalse((run_dir / "reports" / "pt_status.rpt").exists())
        for overrides, message in (
                ({"text,report_units": PT_UNITS_OBSERVED.replace("1e-09", "1e-12")},
                 "profile declares time unit 1ns but report_units shows 1e-12"),
                ({"text,report_units": DC_UNITS_OBSERVED, "text,report_constraint": "Error: bad option (CMD-010)"},
                 "pt_constraints.rpt reported")):
            with self.subTest(message=message):
                code, stdout, run_dir, _, _ = self.run_tcl(key, "sta/ppa_pt.tcl", overrides, prepared_run_dir=run_dir)
                self.assertEqual(code, "1")
                self.assertIn(message, stdout)
                self.assertFalse((run_dir / "reports" / "pt_status.rpt").exists())

    def test_pt_timing_reports_require_path_records(self):
        key = ("syn", "rr", 8)
        code, stdout, dc_run, _, _ = self.run_tcl(key, "syn/ppa_dc.tcl")
        self.assertEqual(code, "0", stdout)
        for text in (NO_PATHS_OBSERVED, "  Startpoint: a\n  Endpoint: b\n", "  slack (MET)  1.0\n"):
            with self.subTest(text=text):
                code, stdout, run_dir, _, _ = self.run_tcl(
                    key, "sta/ppa_pt.tcl", {"text,report_units": PT_UNITS_OBSERVED, "text,report_timing": text},
                    prepared_run_dir=dc_run)
                self.assertEqual(code, "1")
                self.assertIn("pt_timing_max.rpt contains no timing path records", stdout)
                self.assertFalse((run_dir / "reports" / "pt_status.rpt").exists())

    def test_echoed_top_level_return_values_cannot_trigger_failure_patterns(self):
        patterns = run_sh_patterns()
        # Control: the revision-2 initialization result is exactly what the real DC log flagged.
        control = tcl_interpreter().eval('set PPA_FAIL_TAG "EDA_[string toupper failure]"')
        self.assertIsNotNone(patterns["MESSAGE_RE"].search(control))
        runs = [((mode, policy, n), "syn/ppa_dc.tcl") for mode in ("probe", "syn")
                for policy, n in (("fcfs", 4), ("rr", 8), ("fai-main", 16))]
        for key, script in runs:
            with self.subTest(run=key):
                code, stdout, run_dir, _, tcl = self.run_tcl(key, script, echo=True)
                self.assertEqual(code, "0", stdout)
                echoed = [tcl.eval(f"lindex $::STUB_ECHO {i}") for i in range(int(tcl.eval("llength $::STUB_ECHO")))]
                self.assertGreater(len(echoed), 10)
                if key[0] == "syn":
                    code, stdout, _, _, tcl = self.run_tcl(key, "sta/ppa_pt.tcl", {"text,report_units": PT_UNITS_OBSERVED},
                                                           prepared_run_dir=run_dir, echo=True)
                    self.assertEqual(code, "0", stdout)
                    echoed += [tcl.eval(f"lindex $::STUB_ECHO {i}") for i in range(int(tcl.eval("llength $::STUB_ECHO")))]
                for result in echoed:
                    for line in result.splitlines():
                        for name in ("MESSAGE_RE", "UNRESOLVED_RE", "DIAGNOSTICS_RE"):
                            self.assertIsNone(patterns[name].search(line), f"{name}: {line}")
        # A real failure still prints the tag at top level.
        code, stdout, _, _, _ = self.run_tcl(("probe", "rr", 8), "syn/ppa_dc.tcl", {"result,link": "0"}, echo=True)
        self.assertEqual(code, "1")
        self.assertIsNotNone(patterns["MESSAGE_RE"].search(stdout))

    def test_unit_attribute_text_not_understood_is_recorded_not_guessed(self):
        code, stdout, run_dir, _, _ = self.run_tcl(("probe", "fcfs", 4), "syn/ppa_dc.tcl",
                                                   {"attr,time_unit_name": "nanosecond_scale"})
        self.assertEqual(code, "0", stdout)
        self.assertIn("attribute time_unit_name = nanosecond_scale (NOT_PARSED_RECORDED_ONLY)",
                      (run_dir / "reports" / "lib_metadata.rpt").read_text())


if __name__ == "__main__":
    unittest.main()
