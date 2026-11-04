"""Screen protocol checks, including finite adverse closed-loop workloads."""
from collections import Counter
from contextlib import redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screen_scheduler_insights as screen


def fake_rows():
    rows = []
    for seed in screen.SEEDS:
        for policy in screen.POLICIES:
            lanes = {}
            for name in ("trained", "cold_A", "cold_B"):
                cohorts = {}
                for phase in ("A", "B"):
                    value = 19 if policy.startswith("AGE_T") else 20
                    cohorts[phase] = dict(pooled_sparse=dict(generation_to_fire=dict(p99_nearest_rank=value)))
                lanes[name] = dict(conservation=True, held_stable=True, avoidable_bubbles=0,
                                   cohorts=cohorts, phases={p: dict(fires=10000, fired=[9700,100,100,100])
                                                          for p in ("A", "B")})
            rows.append(dict(seed=seed, policy=policy, production=True, exit_code=0, status="PASS",
                             source_hashes={"source": "fixture"}, trace_sha256=str(seed), lanes=lanes,
                             archive_metrics=dict(status="PASS"),
                             archive_cycle_alignment=dict(status="PASS")))
    return rows


class ScreenTests(unittest.TestCase):
    @patch.object(screen, "validate_hog", return_value=True)
    def test_gate_incomplete_and_validation_fail_closed(self, _validation):
        for rows in ([], fake_rows()[:-1], fake_rows() + [fake_rows()[0]]):
            result = screen.evaluate_gate(rows, 0)
            self.assertEqual(result["status"], "UNRESOLVED")
            self.assertIsNone(result["frozen_candidate"])
        self.assertEqual(screen.evaluate_gate(fake_rows(), 1)["status"], "UNRESOLVED")
        rows = fake_rows()
        rows[0]["archive_cycle_alignment"]["status"] = "PENDING"
        self.assertEqual(screen.evaluate_gate(rows, 0)["status"], "UNRESOLVED")

    @patch.object(screen, "validate_hog", return_value=True)
    def test_gate_paired_numeric_thresholds_and_failclosed_advancement(self, _validation):
        rows = fake_rows()
        result = screen.evaluate_gate(rows, 0)
        self.assertEqual(result["numerical_hog_status"], "PASS")
        self.assertTrue(result["numerical_hog_leader"].startswith("AGE_T"))
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertIsNone(result["frozen_candidate"])
        self.assertEqual(result["long_feedback_4_actual_W5M_windows"], "NOT_RUN")
        self.assertEqual(result["advancement_scenario_evidence"], "NOT_RUN")
        # A regression over one cycle blocks that candidate.
        for r in rows:
            if r["policy"] == "AGE_T16_K8":
                r["lanes"]["cold_A"]["cohorts"]["A"]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"] = 22
        result = screen.evaluate_gate(rows, 0)
        self.assertFalse(result["candidates"]["AGE_T16_K8"]["numerical_pass"])
        # Heavy share loss over .01 percentage point blocks a candidate.
        for r in rows:
            if r["policy"] == "AGE_T16_K16":
                r["lanes"]["trained"]["phases"]["A"]["fired"][0] = 9698
        result = screen.evaluate_gate(rows, 0)
        self.assertFalse(result["candidates"]["AGE_T16_K16"]["numerical_pass"])
        # Four individual improvements required even when mean is sufficient.
        for r in rows:
            if r["policy"] == "CGOF(2:1)":
                value = 15 if r["seed"] in (509, 510, 511) else 20
                for lane in r["lanes"].values():
                    lane["cohorts"]["B"]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"] = value
        self.assertFalse(screen.evaluate_gate(rows, 0)["candidates"]["CGOF(2:1)"]["numerical_pass"])

    @patch.object(screen, "validate_hog", return_value=True)
    def test_gate_rejects_unpaired_or_changed_sources(self, _validation):
        for field in ("trace_sha256", "source_hashes"):
            rows = fake_rows()
            rows[0][field] = {} if field == "source_hashes" else "different"
            self.assertEqual(screen.evaluate_gate(rows, 0)["status"], "UNRESOLVED")

    def test_confirmation_seeds_refused_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "must_not_exist"
            for seed in (508, 514, 529, 548):
                with redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as exc:
                        screen.main(["--out", str(p), "--seeds", str(seed)])
                self.assertEqual(exc.exception.code, 2)
                self.assertFalse(p.exists())
            with self.assertRaises(ValueError):
                screen.run_one("FAI-inspired", 529, 256)

    def test_finite_churn_allbacklogged_longstalls_role_switch(self):
        coverage = Counter()
        for policy in screen.POLICIES:
            for scenario in ("churn", "allbacklogged", "longstalls", "role_switch"):
                lane = screen.Lane(policy, 256, scenario, dict(A=(0,512), B=(512,1024)))
                rng = random.Random(509)
                serial = 0
                for k in range(1024):
                    if scenario == "allbacklogged":
                        sources = list(range(4))
                    elif scenario == "churn":
                        sources = [h for h in range(4) if h == (k//19)%4 and rng.random() < .7]
                    elif scenario == "role_switch":
                        heavy = 0 if k < 512 else 3
                        sources = [heavy] + [h for h in range(4) if h != heavy and rng.random() < .04]
                    else:
                        sources = [h for h in range(4) if rng.random() < .2]
                    ready = not (scenario == "longstalls" and 200 <= k < 780)
                    events = []
                    for h in sources:
                        events.append((h, (serial << 73) | rng.getrandbits(73)))
                        serial += 1
                    lane.step(k, events, ready, "A" if k < 512 else "B")
                lane.drain(1024)
                r = lane.result()
                self.assertEqual(r["generated"], r["fired"])
                self.assertEqual(r["avoidable_bubbles"], 0)
                self.assertGreaterEqual(r["windows_closed"], 4)
                coverage[scenario] += 1
        self.assertEqual(dict(coverage), dict.fromkeys(
            ("churn", "allbacklogged", "longstalls", "role_switch"), len(screen.POLICIES)))

    def test_cold_pair_input_and_independent_reset_histories(self):
        bounds = dict(A=(20, 60), B=(80, 120))
        trained = screen.Lane("FAI-inspired", 256, "trained", bounds)
        cold = screen.Lane("FAI-inspired", 256, "cold_A", bounds)
        for k in range(80):
            events = [(0, k << 73)] + ([(1, (1000+k) << 73)] if k % 8 == 0 else [])
            trained.step(k, events, True, "training" if k < 20 else "A")
            if k >= 20:
                cold.step(k, events, True, "A")
        trained.drain(80)
        cold.drain(80)
        a, b = trained.result(), cold.result()
        self.assertEqual(a["measurement_input_sha256"]["A"], b["measurement_input_sha256"]["A"])
        self.assertNotEqual(a["actual_pin_sha256"], b["actual_pin_sha256"])
        self.assertEqual(trained.model.time - cold.model.time, a["cycles"]-b["cycles"])

    def test_archive_missing_pending(self):
        self.assertEqual(screen.compare_archive(dict(policy="CGOF(2:1)", window=256, seed=509), None)["status"],
                         "PENDING")

    @patch.object(screen, "validate_hog", return_value=True)
    def test_absolute_candidate_tiebreak_differs_from_delta_ranking(self, _validation):
        rows = fake_rows()
        for row in rows:
            for name, lane in row["lanes"].items():
                value = {"FAI-inspired": (100, 10), "CGOF(2:1)": (90, 9),
                         "AGE_T16_K8": (98, 6)}.get(row["policy"], (100, 10))
                lane["cohorts"]["B"]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"] = value[name == "trained"]
        result = screen.evaluate_gate(rows, 0)
        self.assertEqual(result["numerical_hog_leader"], "CGOF(2:1)")
        self.assertEqual(result["candidates"]["CGOF(2:1)"]["worst_mean_B"], 90)
        self.assertEqual(result["candidates"]["AGE_T16_K8"]["worst_mean_B"], 98)
        self.assertLess(result["candidates"]["AGE_T16_K8"]["paired_p99"]["trained_B"]["mean_delta"],
                        result["candidates"]["CGOF(2:1)"]["paired_p99"]["trained_B"]["mean_delta"])

    def seal(self, directory, row, kind):
        directory = Path(directory)
        hashes = screen.source_hashes()
        archive = screen.archive_sources(directory, hashes)
        checks = [dict(exit_code=0, command=["python", name]) for name in
                  ("test_experimental.py", "test_screen_scheduler_insights.py")]
        validation = directory / "validation.json"
        validation.write_text(json.dumps(checks))
        row["source_hashes"] = hashes
        row["validation_binding"] = dict(
            exit_code=0, source_hashes=hashes, artifact_directory=str(directory),
            validation_sha256=screen.sha_file(validation), source_archive_sha256=archive["sha256"])
        report = directory / "row.json"
        report.write_text(json.dumps(row))
        summary = dict(exit_code=0, validation_exit=0, kind=kind, source_hashes=hashes,
                       source_archive=archive, validation_sha256=screen.sha_file(validation),
                       report_hashes={report.name: screen.sha_file(report)})
        (directory / "summary.json").write_text(json.dumps(summary))
        return report

    def test_feedback_four_actual_short_windows_and_forged_production(self):
        for policy in screen.FEEDBACK_POLICIES:
            row = screen.run_feedback(policy, 509, 256)
            self.assertTrue(screen.validate_feedback(row, production=False))
            self.assertEqual(row["lane"]["windows_closed"], 4)
            self.assertLessEqual(row["observations"]["max_pending_per_source"], 16)
            with self.assertRaises(AssertionError):
                screen.validate_feedback(row)
            forged = deepcopy(row)
            forged["production"], forged["window"] = True, 5_000_000
            with self.assertRaises(AssertionError):
                screen.validate_feedback(forged)
            for key in ("actual_active_cycles", "params", "source_hashes", "observations"):
                broken = deepcopy(row)
                broken[key] = None
                with self.assertRaises((AssertionError, TypeError)):
                    screen.validate_feedback(broken, production=False)

    def test_sealed_evidence_detects_report_archive_and_validation_tampering(self):
        row = screen.run_feedback("FAI-inspired", 509, 256)
        for target in ("row.json", "validation.json", "sources.zip"):
            with tempfile.TemporaryDirectory() as directory:
                report = self.seal(directory, deepcopy(row), "feedback")
                # Verify the entire sealed path; the only bypass is production W5M
                # eligibility, since this fixture actually ran four W256 windows.
                with patch.object(screen, "validate_feedback",
                                  side_effect=lambda r: screen_validate_short(r)):
                    self.assertEqual(screen.load_evidence(report, "feedback")["policy"], "FAI-inspired")
                    path = Path(directory) / target
                    path.write_bytes(path.read_bytes() + b"altered")
                    with self.assertRaises((AssertionError, ValueError)):
                        screen.load_evidence(report, "feedback")
        with tempfile.TemporaryDirectory() as directory:
            self.seal(directory, deepcopy(row), "feedback")
            with self.assertRaises(FileExistsError):
                screen.archive_sources(Path(directory), screen.source_hashes())
            self.assertNotIn("refc/cxl_model/revision_baselines.py", screen.source_hashes())

    def test_production_bool_is_insufficient_and_gate_malformed_fails_closed(self):
        rows = fake_rows()
        for row in rows:
            row.update(window=5_000_000, actual_training_cycles=10_000_000,
                       active_cycles=10_204_448)
        result = screen.evaluate_gate(rows, 0)
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertIsNone(result["frozen_candidate"])
        self.assertEqual(result["candidates"], {})
        self.assertTrue(any("invalid production HOG evidence" in r for r in result["reasons"]))
        # Failed rows remain unresolved without indexing missing successful-row keys.
        result = screen.evaluate_gate([dict(status="FAIL", exit_code=1)], 0)
        self.assertEqual(result["status"], "UNRESOLVED")

    def test_production_clocks_accounting_and_binding_validation(self):
        traffic = screen.Traffic(509, 5_000_000)
        row = dict(scope="MODEL_ONLY", status="PASS", exit_code=0, production=True,
                   seed=509, policy="FAI-inspired", window=traffic.window, source_hashes=screen.source_hashes(),
                   params=screen.parameters("FAI-inspired", traffic.window), traffic_config=traffic.config,
                   active_cycles=traffic.end, actual_training_cycles=traffic.training,
                   trace_sha256="a"*64, lanes={}, drain_cycles={})
        lengths = dict(training=traffic.training, A=100_000, A_guard=1024, B=102_400, B_guard=1024)
        # Structural fixture only: no experiment or numerical benefit is claimed.
        for name, phases in (("trained", tuple(lengths)), ("cold_A", ("A","A_guard")),
                             ("cold_B", ("B","B_guard"))):
            active = sum(lengths[p] for p in phases)
            phase_rows = {}
            for i, p in enumerate(phases):
                n = lengths[p]
                fired = n - int(i == 0)
                phase_rows[p] = dict(cycles=n, ready=n, fires=fired, fired=[fired,0,0,0],
                                     generated=[n,0,0,0], accepted=[n,0,0,0],
                                     avoidable_bubbles=0, gaps=[{}]*4)
            phase_rows["drain"] = dict(cycles=1, ready=1, fires=1, fired=[1,0,0,0],
                                       generated=[0]*4, accepted=[0]*4,
                                       avoidable_bubbles=0, gaps=[{}]*4)
            empty = {s: screen.stats(screen.StreamStats()) for s in screen.STAGES}
            cohorts = {p: dict(generated=[0]*4, completed=[0]*4,
                               per_source=[deepcopy(empty) for _ in range(4)],
                               pooled_sparse=deepcopy(empty)) for p in ("A","B")}
            row["lanes"][name] = dict(cycles=active+1, windows_closed=(active+1)//traffic.window,
                generated=active, accepted=active, fired=active, conservation=True,
                held_stable=True, avoidable_bubbles=0, phases=phase_rows, cohorts=cohorts,
                measurement_input_sha256=dict(A="b"*64, B="c"*64))
            row["drain_cycles"][name] = 1
        row["generated"] = [traffic.end,0,0,0]
        row["lanes"]["trained"]["first_windows"] = [
            dict(window=i, trace_cycle=(i+1)*traffic.window-1,
                 counts=[traffic.window-int(i == 0),0,0,0], total=traffic.window-int(i == 0))
            for i in range(2)]
        with tempfile.TemporaryDirectory() as directory:
            self.seal(directory, row, "hog")
            self.assertTrue(screen.validate_hog(row))
            for key, value in (("window", 256), ("actual_training_cycles", 512),
                               ("active_cycles", traffic.end-1), ("production", False),
                               ("params", {}), ("traffic_config", {})):
                bad = deepcopy(row)
                bad[key] = value
                with self.subTest(key=key), self.assertRaises(AssertionError):
                    screen.validate_hog(bad)
            for key in ("cycles", "windows_closed", "fired", "conservation"):
                bad = deepcopy(row)
                bad["lanes"]["trained"][key] = -1 if key != "conservation" else False
                with self.subTest(key=key), self.assertRaises(AssertionError):
                    screen.validate_hog(bad)
            bad = deepcopy(row)
            bad["validation_binding"]["validation_sha256"] = "0"*64
            with self.assertRaises(AssertionError):
                screen.validate_hog(bad)

    @patch.object(screen, "validate_hog", return_value=True)
    @patch.object(screen, "validate_binding", return_value=None)
    @patch.object(screen, "validate_feedback", return_value=True)
    def test_advancement_requires_all_feedback_configs(self, *_validation):
        feedback = [dict(policy=p, seed=509, trace_sha256="fixture") for p in screen.FEEDBACK_POLICIES]
        self.assertEqual(screen.evaluate_gate(fake_rows(), 0, feedback)["status"], "PASS")
        for partial in (feedback[:-1], feedback + [feedback[0]]):
            result = screen.evaluate_gate(fake_rows(), 0, partial)
            self.assertEqual(result["status"], "UNRESOLVED")
            self.assertIsNone(result["frozen_candidate"])


screen_validate_short = lambda row: screen_validate_feedback(row, production=False)
screen_validate_feedback = screen.validate_feedback


if __name__ == "__main__":
    unittest.main()
