"""Supplementary power tooling tests; small-W fixtures are never production evidence."""
import gzip
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_power_vectors as vectors
import check_power_replay as checker
import export_revision_power_vectors as trained


def fixture(policy="fai-main", warmup=495, measured=273):
    stats = {}
    rows, info = vectors._supplementary_rows("fixture", policy, 4, 509, warmup + measured,
                                            warmup, 256, stats, None)
    rows = list(rows)
    return rows, stats, info()


def trained_metadata(policy="fai-main", seed=509, arm="A"):
    """Synthetic completed metadata for checker tests; never serialized production evidence."""
    m = trained.plan(policy, seed, arm)
    m.update(status="MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN", exit=0,
             vectors_rows=m["total_cycles"], audit_sha256="a"*64, source_archive_sha256="b"*64,
             vectors_text_sha256="c"*64, vectors_gzip_sha256="d"*64)
    for name in ("warmup", "measured"):
        m[name] = dict(cycles=m[f"{name}_cycles"], accepted_per_source=[0]*4, fires_per_source=[0]*4)
    m.update(all=dict(cycles=m["total_cycles"], accepted=0, fires=0),
             outstanding_at_cut=[0]*4, outstanding_at_end=[0]*4)
    if policy == "fai-main":
        m["closings"] = []
        old = ["H"]*4
        for cycle, classes in ((4_999_999, ["B_H", "H", "H", "H"]), (9_999_999, ["L", "H", "H", "H"])):
            m["closings"].append(dict(cycle=cycle, phase="warmup", window_position=4_999_999,
                old_classes=old, next_cycle_classes=classes, b_s_index_cleared_after=True,
                b_close=[4_999_999, 0, 0, 0], pre_edge_b=[4_999_998, 0, 0, 0],
                s_close=4_999_999, pre_edge_s=4_999_998, closing_fire_source=0,
                evidence=["DOWN", "UP", "UP", "UP"]))
            old = classes
        m["warmup"].update(accepted_per_source=[9_999_998, 0, 0, 0], fires_per_source=[9_999_998, 0, 0, 0])
        m["all"].update(accepted=9_999_998, fires=9_999_998)
    return m


class TrainedContracts(unittest.TestCase):
    def test_all_policies_seeds_and_arms_match_exporter_plan(self):
        for policy in trained.POLICIES:
            for seed in range(509, 514):
                for arm in ("A", "B"):
                    with self.subTest(policy=policy, seed=seed, arm=arm):
                        m = trained_metadata(policy, seed, arm)
                        expected = trained.plan(policy, seed, arm)
                        self.assertEqual({k: m[k] for k in expected}, expected)
                        checker.check_payload_mode(m, 4, policy)
                        self.assertEqual(m["smoke_cycles"], None)
                        with self.assertRaises(ValueError):
                            checker.check_payload_mode(expected, 4, policy)

    def test_exact_fields_types_and_incomplete_export_rejected(self):
        for arm in ("A", "B"):
            m = trained_metadata(arm=arm)
            mutations = [(k, m[k]+delta) for k in (
                "mode_id", "training_cycles", "warmup_cycles", "measured_cycles", "total_cycles",
                "duration_ns", "period_ps", "reset_edges_outside_window", "n_src", "depth",
                "descriptor_bits", "rr_quantum", "vectors_rows") for delta in (-1, 1)]
            mutations += [(k, float(m[k])) for k in (
                "seed", "policy_id", "training_cycles", "fai_window", "vectors_rows", "exit")]
            mutations += [("seed", True), ("seed", 508), ("seed", 514), ("schema", "cxl-power-replay-v1"),
                ("schema", "cxl-power-replay-v2"), ("schema", "unknown"), ("mode", "cold-seed"),
                ("arm", "B" if arm == "A" else "A"), ("policy", "rr"), ("production_evidence", 1),
                ("sensitivity_only", 0), ("planned_power_seed", 1), ("smoke_cycles", 64),
                ("seed_role", "confirmation"), ("replaces_primary_dataset", True), ("exit", False),
                ("status", "EXPORTED_INDEPENDENT_AUDIT_PENDING_GATE_NOT_RUN"),
                ("audit_sha256", "bad"), ("source_archive_sha256", ""),
                ("vectors_text_sha256", None), ("vectors_gzip_sha256", 1)]
            for key, value in mutations:
                with self.subTest(arm=arm, key=key, value=value), self.assertRaises(ValueError):
                    checker.check_payload_mode(dict(m, **{key: value}), 4, "fai-main")
            for key in ("smoke_cycles", "status", "exit", "audit_sha256", "vectors_rows", "warmup", "closings"):
                bad = copy.deepcopy(m)
                del bad[key]
                with self.subTest(missing=key), self.assertRaises(ValueError):
                    checker.check_mode(bad)
            for key, value in (("fai_window", 256), ("training_cycles", 512)):
                with self.assertRaises(ValueError):
                    checker.check_mode(dict(m, **{key: value}))
        for policy in trained.POLICIES:
            with self.assertRaisesRegex(ValueError, "unsupported supplementary power mode"):
                checker.check_mode(trained.plan(policy, 509, "A", 256, 64))

    def test_statistics_and_actual_main_closings_reject_mutations(self):
        m = trained_metadata()
        for index in (0, 1):
            bad = copy.deepcopy(m)
            bad["closings"][index].update(b_close=[0]*4, pre_edge_b=[0]*4, s_close=0,
                                          pre_edge_s=0, closing_fire_source=None, evidence=["S0"]*4)
            with self.subTest(zero_service_closing=index), self.assertRaises(ValueError):
                checker.check_mode(bad)
        for phase, key, value in (("warmup", "cycles", 512), ("measured", "fires_per_source", [True, 0, 0, 0]),
                ("all", "accepted", 0), ("warmup", "accepted_per_source", [0]*4)):
            bad = copy.deepcopy(m)
            bad[phase][key] = value
            with self.subTest(phase=phase, key=key), self.assertRaises(ValueError):
                checker.check_mode(bad)
        for key, value in (("cycle", 4_999_998), ("window_position", 255), ("phase", "measured"),
                ("b_s_index_cleared_after", 1), ("old_classes", ["L"]*4), ("next_cycle_classes", ["H"]*4),
                ("pre_edge_s", 0), ("s_close", 0), ("closing_fire_source", True), ("b_close", [0]*4),
                ("pre_edge_b", [0]*4), ("evidence", ["UP"]*4)):
            bad = copy.deepcopy(m)
            bad["closings"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                checker.check_mode(bad)
        for closings in (m["closings"][:1], m["closings"]+[m["closings"][0]], m["closings"][::-1]):
            with self.assertRaises(ValueError):
                checker.check_mode(dict(m, closings=closings))

    def test_trained_synthetic_results_and_measured_only_saif(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, saif = Path(tmp)/"result", Path(tmp)/"activity.saif"
            for arm in ("A", "B"):
                m = trained_metadata(arm=arm)
                lines = checker.expected_result_v2(m)
                result.write_text("\n".join(lines)+"\n")
                duration, edges = m["duration_ns"], 2*m["measured_cycles"]
                activity = f"(SAIFILE (TIMESCALE 1 ns) (DURATION {duration}) (INSTANCE tb (INSTANCE dut (NET (clk (T0 {duration//2}) (T1 {duration//2}) (TX 0) (TC {edges}))))))"
                for tc in (edges, edges-1):
                    saif.write_text(activity.replace(f"TC {edges}", f"TC {tc}"))
                    checker.check_replay(m, result, saif)
                for bad in (activity.replace("TX 0", "TX 1"), activity.replace("INSTANCE dut", "INSTANCE wrong"),
                        activity.replace(f"TC {edges}", f"TC {edges+1}"),
                        activity.replace(f"TC {edges}", f"TC {edges-2}"),
                        activity.replace(f"DURATION {duration}", f"DURATION {25*m['total_cycles']}"),
                        activity.replace(f"DURATION {duration}", f"DURATION {25*m['warmup_cycles']}")):
                    saif.write_text(bad)
                    with self.assertRaises(ValueError):
                        checker.check_replay(m, result, saif)
                for bad in (lines[:-1], lines+["extra"], [lines[0], lines[2], lines[1], *lines[3:]],
                            [lines[0].replace(f"mode={m['mode_id']}", f"mode={25-m['mode_id']}"), *lines[1:]]):
                    result.write_text("\n".join(bad)+"\n")
                    with self.assertRaises(ValueError):
                        checker.check_replay_result(m, result)

    def test_legacy_table_and_exporter_do_not_gain_trained_modes(self):
        self.assertEqual(checker.SUPPLEMENTARY_MODES, {
            "cold-seed": dict(mode_id=1, seeds=(510, 511), n_src=(4, 8, 16), warmup=0, measured=100_000),
            "boundary-n4": dict(mode_id=2, seeds=(509,), n_src=(4,), warmup=9_999_500, measured=100_000)})
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)/"refused"
            for mode in checker.TRAINED_MODES:
                with self.assertRaises(ValueError):
                    vectors.export_supplementary(mode, "fcfs", 4, 509, dest)
                self.assertFalse(dest.exists())


class ExtensionContracts(unittest.TestCase):
    def test_v1_known_vector_bytes_remain_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = vectors.export("rr", 4, Path(tmp) / "legacy")
            self.assertEqual(m["vectors_gzip_sha256"], "3b5c7c95767b4d1fa544b09d93b71e2adc6fd1641831d3718a6d8b7c02925014")
            self.assertEqual(m["vectors_text_sha256"], "0997f5f7b5c8c0c2eac0735723fc2ae9824b3f07a55c5318c82510c5e134df0b")
            checker.check_payload_mode(m, 4, "rr")
            for key, value in (("seed", 510), ("measured_cycles", 99999), ("fai_window", 256)):
                bad = dict(m, **{key: value})
                with self.assertRaises(ValueError):
                    checker.check_payload_mode(bad, 4, "rr")

    def test_seed_pairs_all_n_reproducible_and_policy_independent(self):
        for n in (4, 8, 16):
            hashes = []
            for seed in (510, 511):
                trace = vectors.make_trace(seed, n, 1000, "primary")
                self.assertEqual(trace.sha256, vectors.make_trace(seed, n, 1000, "primary").sha256)
                hashes.append(trace.sha256)
                for policy in vectors.POLICIES:
                    stats = {}
                    rows = list(vectors.replay_phases(policy, n,
                                ((trace.gen[k], trace.ready[k]) for k in range(1000)), 1000, 0, stats))
                    self.assertEqual([r[3] for r in rows], list(trace.ready))
                    self.assertEqual(stats["warmup"]["cycles"], 0)
                    self.assertEqual(stats["measured"]["cycles"], 1000)
                    self.assertEqual(sum(stats["measured"]["accepted_per_source"]), stats["all"]["accepted"])
            self.assertNotEqual(*hashes)

    def test_cold_supplement_export_and_reject_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for seed in (510, 511):
                dest = root / str(seed)
                m = vectors.export_supplementary("cold-seed", "rr", 4, seed, dest)
                checker.check_mode(m)
                checker.check_payload_mode(m, 4, "rr")
                self.assertEqual((m["total_cycles"], m["warmup_cycles"], m["measured_cycles"]), (100000, 0, 100000))
                with gzip.open(dest / "vectors.txt.gz", "rt") as handle:
                    self.assertEqual(handle.readline().strip(), f"43585032 1 4 100000 0 100000 {seed} 1 25000 3")
                with self.assertRaises(FileExistsError):
                    vectors.export_supplementary("cold-seed", "rr", 4, seed, dest)
            for mode, n, seed, policy in (("cold-seed", 4, 509, "rr"), ("boundary-n4", 8, 509, "rr"),
                    ("boundary-n4", 4, 510, "fai-main"), ("primary", 4, 510, "fcfs"),
                    ("boundary-n4", 4, 509, "alg2")):
                dest = root / "rejected"
                with self.assertRaises(ValueError):
                    vectors.export_supplementary(mode, policy, n, seed, dest)
                self.assertFalse(dest.exists())

    def test_fixed_production_contract_and_literal_boundary_trajectory(self):
        spec = checker.SUPPLEMENTARY_MODES["boundary-n4"]
        self.assertEqual((spec["warmup"], spec["measured"]), (9999500, 100000))
        self.assertEqual(vectors.boundary_expectation(), [
            (4999999, ("B_H", "B_H", "H", "B_H"), ("DOWN", "DOWN", "UP", "DOWN"), "held"),
            (9999999, ("L", "H", "H", "L"), ("DOWN", "UP", "KEEP", "DOWN"), "fire")])
        self.assertEqual(9999999 - spec["warmup"], 499)
        self.assertEqual(spec["warmup"] + spec["measured"] - 1, 10099499)
        # Exercise boundary export configuration without constructing or skipping a 10M trace.
        with tempfile.TemporaryDirectory() as tmp, patch.object(vectors, "_supplementary_rows", side_effect=RuntimeError("test stops before generation")) as steps:
            with self.assertRaisesRegex(RuntimeError, "stops before generation"):
                vectors.export_supplementary("boundary-n4", "fai-main", 4, 509, Path(tmp) / "unrun")
            args = steps.call_args.args
            self.assertEqual(args[4:7], (10099500, 9999500, 5000000))

    def test_production_mode_metadata_guards(self):
        m = dict(schema="cxl-power-replay-v2", mode="boundary-n4", mode_id=2, policy="fai-main",
                 policy_id=2, period_ps=25000, reset_edges_outside_window=3, depth=16, descriptor_bits=105,
                 rr_quantum=10, total_cycles=10099500, warmup_cycles=9999500, measured_cycles=100000,
                 duration_ns=2500000, seed=509, n_src=4, fai_window=5000000, replaces_primary_dataset=False)
        checker.check_mode(m)
        checker.check_payload_mode(m, 4, "fai-main")
        for key, value in (("schema", "unknown"), ("mode_id", 1), ("seed", 510), ("n_src", 8),
                ("warmup_cycles", 9999501), ("measured_cycles", 99999), ("total_cycles", 10099501),
                ("fai_window", 256), ("policy_id", 1), ("replaces_primary_dataset", True), ("seed", 509.0)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                checker.check_mode(dict(m, **{key: value}))
        with self.assertRaises(ValueError):
            checker.check_payload_mode(m, 4, "rr")

    def test_phase_cut_preserves_every_pin_and_held_context_with_bounded_history(self):
        for policy in vectors.POLICIES:
            with patch.object(vectors, "TRIM_EVERY", 8):
                rows, stats, info = fixture(policy)
            flat_rows, flat, flat_info = fixture(policy, warmup=0, measured=768)
            self.assertEqual(rows, flat_rows)
            self.assertEqual(info["sha256"], flat_info["sha256"])
            self.assertEqual(stats["all"], flat["all"])
            self.assertEqual(stats["warmup"]["cycles"], 495)
            self.assertEqual(stats["measured"]["cycles"], 273)
            self.assertLessEqual(stats["max_retained_model_log_entries"], 16)
            self.assertIsNotNone(stats["state_at_cut"]["held_source"])
            self.assertEqual(stats["all"]["accepted"] - stats["all"]["fires"], sum(stats["outstanding_at_end"]))
            if policy == "fai-main":
                self.assertEqual(stats["state_at_cut"]["held_grant_ctx"], ["High", 0])
                self.assertGreater(stats["measured"]["high_class_fires"], 0)
                self.assertGreater(stats["measured"]["low_class_fires"], 0)
                close = stats["closings"][1]
                self.assertEqual((close["cycle"], close["phase"]), (511, "measured"))
                self.assertEqual(close["s_close"], close["pre_edge_s"] + 1)
                self.assertTrue(close["b_s_index_cleared_after"])
                self.assertEqual(close["next_cycle_classes"], ["L", "H", "H", "L"])

    def test_full_refused_producers_hold_through_phase_cut(self):
        steps = [([(h, k * 4 + h + 1) for h in range(4)], int(k >= 80)) for k in range(100)]
        for policy in vectors.POLICIES:
            stats, flat = {}, {}
            split_rows = list(vectors.replay_phases(policy, 4, iter(steps), 100, 40, stats, window=256))
            flat_rows = list(vectors.replay_phases(policy, 4, iter(steps), 100, 0, flat, window=256))
            self.assertEqual(split_rows, flat_rows)
            self.assertEqual(stats["state_at_cut"]["input_hold_obligation_sources"], [0, 1, 2, 3])
            self.assertEqual(stats["outstanding_at_cut"], [16] * 4)
            self.assertGreater(stats["input_hold_checks"], 0)

    def test_closing_mutations_and_widened_comparisons_rejected(self):
        n = 4
        model = vectors.FaiMainSwitchModel(n, 256)
        for _ in range(3):
            model.commit(rst_n=False)
        for k in range(255):
            model.commit(out_ready=True)
        pre, offered, view = model.window_state(), model.offered(), model.view(out_ready=True)
        edge = model.commit(out_ready=True)
        args = (255, "measured", pre, offered, view, True, edge, model, n)
        vectors._closing(*args)
        for bad in (edge._replace(s_close=1), edge._replace(b_close=(1, 0, 0, 0)),
                    edge._replace(evidence=("UP",) * 4), edge._replace(new_classes=("L",) * 4)):
            with self.assertRaises(AssertionError):
                vectors._closing(*args[:6], bad, *args[7:])
        # Full production-scale count: 10*N*B exceeds 24 bits; no truncated comparison allowed.
        large_pre = (255, (3000000, 1000000, 500000, 500000), 5000000)
        large = edge._replace(b_close=large_pre[1], s_close=5000000,
                             evidence=("DOWN", "KEEP", "KEEP", "KEEP"))
        vectors._closing(255, "measured", large_pre, offered, view, True, large, model, n)
        with self.assertRaises(AssertionError):
            vectors._closing(255, "measured", large_pre, offered, view, True,
                             large._replace(evidence=("UP", "KEEP", "KEEP", "KEEP")), model, n)

    def test_fixture_guards_result_and_saif_phase_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            m = vectors.write_fixture("fai-main", 4, root / "fixture", warmup=495, measured=273)
            checker.check_mode(m, allow_fixture=True)
            with self.assertRaises(ValueError):
                checker.check_payload_mode(m, 4, "fai-main")
            result, saif = root / "result", root / "activity.saif"
            text = "\n".join(checker.expected_result_v2(m)) + "\n"
            result.write_text(text)
            duration = m["duration_ns"]
            activity = f"(SAIFILE (TIMESCALE 1 ns) (DURATION {duration}) (INSTANCE tb (INSTANCE dut (NET (clk (T0 3400) (T1 3425) (TX 0) (TC 545))))))"
            saif.write_text(activity)
            checker.check_replay(m, result, saif, allow_fixture=True)
            for mutation in (text.replace("warmup_cycles=495", "warmup_cycles=0"), text + "extra\n", "\n".join(text.splitlines()[:-1])):
                result.write_text(mutation)
                with self.assertRaises(ValueError):
                    checker.check_replay_result(m, result, allow_fixture=True)
            result.write_text(text)
            for mutation in (activity.replace("TX 0", "TX 1"), activity.replace("TC 545", "TC 544"),
                             activity.replace("INSTANCE dut", "INSTANCE wrong"), activity.replace("DURATION 6825", "DURATION 19200"),
                             activity.replace("TX 0", "TX 0) (TZ 1")):
                saif.write_text(mutation)
                with self.assertRaises(ValueError):
                    checker.check_replay(m, result, saif, allow_fixture=True)
            for key, value in (("depth", 8), ("n_src", 2), ("warmup_cycles", -1), ("period_ps", 20000)):
                bad = dict(m, **{key: value})
                with self.assertRaises(ValueError):
                    checker.check_mode(bad, allow_fixture=True)
            with self.assertRaises(ValueError):
                vectors.write_fixture("fai-main", 4, root / "wrongwindow", warmup=10, measured=10, window=64)


@unittest.skipUnless(sys.platform == "linux" and shutil.which("verilator"), "WSL Verilator required")
class RealTestbenchReplay(unittest.TestCase):
    """Compile the actual common TB against actual RTL; no SAIF/power claim from these fixtures."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cxl-power-tb-")
        cls.root = Path(cls.tmp.name)
        cls.log_root = Path(os.environ.get("CXL_POWER_TEST_LOG_DIR", cls.root / "logs"))
        cls.log_root.mkdir(parents=True, exist_ok=True)
        cls.binaries = {}
        for policy, (number, _) in vectors.POLICIES.items():
            build = cls.root / policy
            command = ["verilator", "--binary", "--timing", "--timescale", "1ns/1ps", "--top-module", "tb",
                "--Mdir", str(build), "-j", "2", "+define+POWER_NO_SAIF", "+define+POWER_RTL_FIXTURE",
                f"+define+POWER_FIXTURE_POLICY={number}", "-f", "rtl/filelist_switch.f", "sim/power/tb_power.sv"]
            result = subprocess.run(command, cwd=vectors.ROOT, capture_output=True, text=True)
            (cls.log_root / f"build-{policy}.txt").write_text(" ".join(command) + "\n" + result.stdout + result.stderr)
            if result.returncode:
                raise AssertionError(f"strict Verilator build failed for {policy}: {result.stderr}")
            cls.binaries[policy] = build / "Vtb"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, policy, name, content, expected=None, error=None):
        folder = self.root / name
        folder.mkdir()
        (folder / "vectors.txt").write_text(content)
        command = [str(self.binaries[policy]), f"+vectors={folder}/vectors.txt", f"+result={folder}/result.txt", f"+saif={folder}/unused.saif"]
        result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=30)
        (self.log_root / f"run-{name}.txt").write_text(" ".join(command) + "\n" + result.stdout + result.stderr)
        if error:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(error, result.stdout + result.stderr)
            self.assertFalse((folder / "result.txt").exists())
        else:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            checker.check_replay_result(expected, folder / "result.txt", allow_fixture=True)
        return result.stdout + result.stderr

    def test_all_policy_warmup_and_measured_replay(self):
        for policy in vectors.POLICIES:
            path = self.root / f"export-{policy}"
            m = vectors.write_fixture(policy, 4, path, warmup=495, measured=273)
            content = gzip.decompress((path / "vectors.txt.gz").read_bytes()).decode()
            output = self.run_case(policy, f"good-{policy}", content, m)
            self.assertEqual([l for l in output.splitlines() if l.startswith("POWER_LOCAL_TOGGLE_")], [
                "POWER_LOCAL_TOGGLE_START checked_cycles=495",
                "POWER_LOCAL_TOGGLE_STOP checked_cycles=768 measured_cycles=273"])

    def test_trained_exact_headers_reach_missing_row_without_training(self):
        for policy in vectors.POLICIES:
            for seed in range(509, 514):
                for arm in ("A", "B"):
                    self.run_case(policy, f"trained-header-{policy}-{seed}-{arm}",
                                  trained.header(trained.plan(policy, seed, arm))+"\n",
                                  error="missing vector row 0")
        for mode, header in ((1, "43585032 1 4 100000 0 100000 510 1 25000 3"),
                             (2, "43585032 2 4 10099500 9999500 100000 509 1 25000 3")):
            self.run_case("rr", f"legacy-header-{mode}", header+"\n", error="missing vector row 0")

    def test_trained_header_mutations_fail_before_rows(self):
        for arm in ("A", "B"):
            header = trained.header(trained.plan("rr", 509, arm)).split()
            cases = [("short", header[:-1], "invalid supplementary power header"),
                     ("extra", header+["extra"], "extra supplementary header fields"),
                     ("unknown", [header[0], "14", *header[2:]], "unsupported power mode")]
            for field in range(2, 10):
                for delta in (-1, 1):
                    # Seed510 and policies0/2 are legal; test out-of-range values instead.
                    if field in (6, 7):
                        continue
                    bad = header.copy()
                    bad[field] = str(int(bad[field])+delta)
                    error = ("invalid supplementary power header" if field in (3, 4, 5) else
                             f"invalid trained {arm} header" if field == 2 else "invalid power configuration")
                    cases.append((f"field{field}-{delta}", bad, error))
            for label, field, value, error in (("seed-low", 6, "508", f"invalid trained {arm} header"),
                    ("seed-high", 6, "514", f"invalid trained {arm} header"),
                    ("policy-bad", 7, "3", "invalid power configuration"),
                    ("float-seed", 6, "509.0", "invalid supplementary power header")):
                bad = header.copy()
                bad[field] = value
                cases.append((label, bad, error))
            short = trained.header(trained.plan("rr", 509, arm, 256, 64)).split()
            cases.append(("sensitivity", short, f"invalid trained {arm} header"))
            for field in range(1, 10):
                bad = header.copy()
                bad[field] = str(int(bad[field]) + 2**32)
                cases.append((f"overflow-{field}", bad, "noncanonical trained power header"))
            cases.append(("overflow-magic", ["143585032", *header[1:]], "noncanonical trained power header"))
            for name, fields, error in cases:
                self.run_case("rr", f"trained-bad-{arm}-{name}", " ".join(fields)+"\n", error=error)

    def test_production_runner_refuses_trained_sensitivity_before_tools(self):
        path = self.root / "trained-refused-payload"
        path.mkdir()
        (path / "metadata.json").write_text(json.dumps(trained.plan("rr", 509, "A", 256, 64)))
        (path / "vectors.txt.gz").write_bytes(b"")
        (path / "scripts").mkdir()
        shutil.copyfile(vectors.ROOT / "scripts/check_power_replay.py", path / "scripts/check_power_replay.py")
        command = ["bash", str(vectors.ROOT / "scripts/run_power_pilot.sh"), "/nonexistent/case", "4", "rr",
                   "/nonexistent/model", "/nonexistent/db"]
        result = subprocess.run(command, cwd=path, capture_output=True, text=True, timeout=10)
        (self.log_root / "run-production-runner-trained-guard.txt").write_text(
            " ".join(command)+"\n"+result.stdout+result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported supplementary power mode", result.stdout+result.stderr)
        self.assertFalse((path / "execution/reports/compile.log").exists())

    def test_v1_100k_compatibility_with_actual_common_tb(self):
        path = self.root / "export-v1"
        m = vectors.export("rr", 4, path)
        content = gzip.decompress((path / "vectors.txt.gz").read_bytes()).decode()
        self.run_case("rr", "good-v1-100k", content, m)

    def test_production_runner_refuses_fixture_before_tools(self):
        path = self.root / "refused-payload"
        vectors.write_fixture("rr", 4, path, warmup=495, measured=273)
        (path / "scripts").mkdir()
        for name in ("check_power_replay.py", "run_power_pilot.sh"):
            shutil.copyfile(vectors.ROOT / "scripts" / name, path / "scripts" / name)
        command = ["bash", str(vectors.ROOT / "scripts/run_power_pilot.sh"), "/nonexistent/case", "4", "rr", "/nonexistent/model", "/nonexistent/db"]
        result = subprocess.run(command, cwd=path, capture_output=True, text=True)
        (self.log_root / "run-production-runner-fixture-guard.txt").write_text(result.stdout + result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture vectors are local test fixtures", result.stdout + result.stderr)
        self.assertFalse((path / "execution/reports/compile.log").exists())

    def test_parser_and_pin_mutations_fail(self):
        path = self.root / "export-mutations"
        vectors.write_fixture("rr", 4, path, warmup=495, measured=273)
        content = gzip.decompress((path / "vectors.txt.gz").read_bytes()).decode()
        lines = content.splitlines()
        cases = {"badheader": (content.replace("43585032", "43585033", 1), "invalid power magic"),
                 "short": ("\n".join(lines[:-1]) + "\n", "missing vector row"),
                 "extra": (content + lines[-1] + "\n", "extra vector rows/content"),
                 "headerextra": (lines[0] + " extra\n" + "\n".join(lines[1:]) + "\n", "extra supplementary header fields"),
                 "rowextra": (lines[0] + "\n" + lines[1] + " extra\n" + "\n".join(lines[2:]) + "\n", "extra fields in vector row"),
                 "badrow": (lines[0] + "\n0 0\n" + "\n".join(lines[2:]) + "\n", "bad vector row")}
        for name, header, error in (
                ("coldseed", "43585032 1 4 100000 0 100000 509 1 25000 3", "invalid cold-seed header"),
                ("boundarycut", "43585032 2 4 10099500 9999501 99999 509 1 25000 3", "invalid boundary header"),
                ("period", "43585032 9 4 768 495 273 509 1 20000 3", "invalid power configuration"),
                ("policy", "43585032 9 4 768 495 273 509 3 25000 3", "invalid power configuration")):
            cases[name] = (header + "\n" + "\n".join(lines[1:]) + "\n", error)
        for field, label in ((4, "ready"), (5, "valid"), (6, "source"), (7, "desc")):
            mutated = lines.copy()
            row = next(i for i in range(1, len(lines)) if lines[i].split()[5] == "1")
            parts = mutated[row].split()
            parts[field] = f"{int(parts[field], 16) ^ 1:x}"
            mutated[row] = " ".join(parts)
            cases[label] = ("\n".join(mutated) + "\n", "mismatch")
        for name, (mutation, error) in cases.items():
            self.run_case("rr", f"bad-{name}", mutation, error=error)


IVL_ROOT = Path.home() / ".local/opt/cxl-scheduler/iverilog-12.0/usr"


@unittest.skipUnless(sys.platform == "linux" and (IVL_ROOT / "bin/iverilog").is_file(), "user-local WSL Icarus required for true four-state checks")
class FourStateTestbenchRejection(unittest.TestCase):
    def test_actual_common_tb_rejects_x_on_every_relevant_output(self):
        # This fixed-pin fixture implements no scheduler; only the common TB's X rejection is tested.
        with tempfile.TemporaryDirectory(prefix="cxl-power-x-") as tmp:
            root = Path(tmp)
            stub = root / "fixed_pins.sv"
            stub.write_text('''`timescale 1ns/1ps
module switch_top #(parameter N_SRC=4, POLICY=1, FAI_W=256)(
  input clk, rst_n, input [N_SRC-1:0] i_in_valid, input [N_SRC*105-1:0] i_in_desc,
  input i_out_ready, output [N_SRC-1:0] o_in_ready, output o_out_valid,
  output [104:0] o_out_desc, output [$clog2(N_SRC)-1:0] o_out_source);
  integer kind;
  initial if (!$value$plusargs("xkind=%d", kind)) $fatal(1, "xkind missing");
  initial begin
    #1;
    if (kind==5) begin
      @(posedge rst_n);
      force tb.clk = 1'bx;
    end
  end
  assign o_in_ready = !rst_n ? '0 : kind==0 ? 'x : '1;
  assign o_out_valid = !rst_n ? 1'b0 : kind==1 ? 1'bx : 1'b1;
  assign o_out_source = kind==2 ? 'x : '0;
  assign o_out_desc = kind==3 ? 'x : '0;
endmodule
''')
            command = [str(IVL_ROOT / "bin/iverilog"), "-B", str(IVL_ROOT / "lib/x86_64-linux-gnu/ivl"),
                "-g2012", "-s", "tb", "-DPOWER_NO_SAIF", "-DPOWER_RTL_FIXTURE", "-DPOWER_FIXTURE_POLICY=1",
                "-o", str(root / "sim.vvp"), str(vectors.ROOT / "sim/power/tb_power.sv"), str(stub)]
            compile_result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            (root / "vectors.txt").write_text("43585032 9 4 2 1 1 509 1 25000 3\n0 0 0 1 f 1 0 0\n1 0 0 1 f 1 0 0\n")
            logs = Path(os.environ.get("CXL_POWER_TEST_LOG_DIR", root / "logs"))
            logs.mkdir(parents=True, exist_ok=True)
            (logs / "build-four-state.txt").write_text(" ".join(command) + "\n" + compile_result.stdout + compile_result.stderr)
            for kind in range(6):
                result = subprocess.run([str(IVL_ROOT / "bin/vvp"), "-M", str(IVL_ROOT / "lib/x86_64-linux-gnu/ivl"),
                    str(root / "sim.vvp"), f"+xkind={kind}", f"+vectors={root}/vectors.txt",
                    f"+result={root}/result-{kind}.txt", f"+saif={root}/none.saif"], capture_output=True, text=True, timeout=10)
                (logs / f"run-four-state-{kind}.txt").write_text(result.stdout + result.stderr)
                if kind < 4 or kind == 5:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("mismatch" if kind < 4 else "invalid replay clock", result.stdout + result.stderr)
                    self.assertFalse((root / f"result-{kind}.txt").exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue((root / "result-4.txt").is_file())
            # Production compile has no fixture-enable define: reject mode9 even with a valid header.
            production = command.copy()
            production.remove("-DPOWER_RTL_FIXTURE")
            production[production.index("-o") + 1] = str(root / "production.vvp")
            result = subprocess.run(production, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(IVL_ROOT / "bin/vvp"), "-M", str(IVL_ROOT / "lib/x86_64-linux-gnu/ivl"),
                str(root / "production.vvp"), "+xkind=4", f"+vectors={root}/vectors.txt",
                f"+result={root}/production.txt", f"+saif={root}/none.saif"], capture_output=True, text=True)
            (logs / "run-four-state-production-fixture-guard.txt").write_text(result.stdout + result.stderr)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fixture refused by production", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
