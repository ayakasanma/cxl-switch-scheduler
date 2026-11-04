"""Contract regressions for the MODEL_ONLY Buffer transition screen."""

import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_buffer_transition_screen as t  # noqa: E402

VARIANTS = ("Main", "Main-1W", "Algorithm-2")
HEAVY = [208, 16, 16, 16]
SPARSE = [16, 208, 16, 16]
KEEP = [64, 64, 64, 64]
IDLE = [0, 0, 0, 0]


def case(counts, events=None, **changes):
    value = {
        "name": "directed", "window": 256, "phase": 0, "direction": "down",
        "duration_cycles": None,
        "role_events": ([{"cycle": 0, "target_effective": "Low"}]
                        if events is None else events),
        "counts": counts,
    }
    value.update(changes)
    return value


def result_name(result):
    value = result.get("case_name", result.get("case"))
    return value["name"] if isinstance(value, dict) else value


def result_digest(result):
    payload = dict(result)
    payload.pop("screen_sha256")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class BufferTransitionTests(unittest.TestCase):
    def check_case(self, value):
        self.assertEqual(set(value), {"name", "window", "phase", "direction",
                                     "duration_cycles", "role_events", "counts"})
        self.assertTrue(value["name"] and value["counts"])
        self.assertEqual([e["cycle"] for e in value["role_events"]],
                         sorted(e["cycle"] for e in value["role_events"]))
        for counts in value["counts"]:
            self.assertEqual(len(counts), 4)
            self.assertTrue(all(type(v) is int for v in counts))
            self.assertTrue(all(0 <= v <= value["window"] for v in counts))
            self.assertLessEqual(sum(counts), value["window"])

    def test_make_case_covers_phase_duration_direction_matrix(self):
        default = t.make_case()
        self.assertEqual((default["window"], default["phase"], default["direction"],
                          default["counts"][0][0], default["counts"][3][0]),
                         (256, 0, "down", 16, 208))
        for window in (64, 256):
            for phase in (0, window // 4, window - 1):
                for duration in (None, window // 2, window, 3 * window // 2):
                    for direction in ("down", "up"):
                        with self.subTest(window=window, phase=phase,
                                          duration=duration, direction=direction):
                            value = t.make_case(window, phase, duration, direction)
                            self.check_case(value)
                            start = 3 * window + phase
                            target = "Low" if direction == "down" else "High"
                            baseline = "High" if direction == "down" else "Low"
                            self.assertTrue(all(
                                sum(c) == window for c in value["counts"]))
                            self.assertIn(
                                {"cycle": start, "target_effective": target},
                                value["role_events"])
                            if duration is None:
                                self.assertEqual(value["role_events"][-1]
                                                 ["target_effective"], target)
                                self.assertGreaterEqual(
                                    len(value["counts"]) * window - start, 4 * window)
                            else:
                                self.assertIn(
                                    {"cycle": start + duration,
                                     "target_effective": baseline},
                                    value["role_events"])

    def test_make_case_up_warmup_measures_low_to_high(self):
        value = t.make_case(256, 0, None, "up")
        self.assertEqual((value["counts"][0][0], value["counts"][3][0]), (208, 16))
        result = t.run_case("Main", value)
        event = next(e for e in result["events"]
                     if e["role_change_cycle"] == 768)
        before = [r for r in result["rows"]
                  if r["effective_visible_cycle"] <= 768][-1]
        self.assertEqual(before["effective_after"][0], "Low")
        self.assertEqual(event["target_effective_visible_cycle"], 1280)
        self.assertEqual(event["target_stable_visible_cycle"], 1280)
        self.assertEqual(event["status"], "COMPLETE")

    def test_invalid_make_case_arguments_are_rejected(self):
        for args in ({"window": 0}, {"window": 128}, {"window": True},
                     {"phase": -1}, {"phase": 256}, {"duration": 0},
                     {"duration": -1}, {"duration": 1.5}, {"duration": True},
                     {"direction": "sideways"}, {"direction": "Down"},
                     {"direction": None}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                t.make_case(**args)

    def test_invalid_counts_are_rejected(self):
        for counts in ([], [[-1, 1, 1, 1]], [[1.0, 1, 1, 1]],
                       [[True, 1, 1, 1]], [[1, 1, 1]], [[1, 1, 1, 1, 1]],
                       [[256, 1, 0, 0]]):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                t.run_case("Main", case(counts, [] if not counts else None))

    def test_invalid_role_events_are_rejected(self):
        for events in ([], [{"cycle": 256, "target_effective": "High"},
                            {"cycle": 0, "target_effective": "Low"}],
                       [{"cycle": 1024, "target_effective": "Low"}],
                       [{"cycle": -1, "target_effective": "Low"}],
                       [{"cycle": 0, "target_effective": "Middle"}],
                       [{"cycle": 0}]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                t.run_case("Main", case([HEAVY] * 4, events))

    def test_run_case_rejects_invalid_case_metadata(self):
        for change in ({"window": 128}, {"phase": -1}, {"phase": 256},
                       {"duration_cycles": 0}, {"duration_cycles": 1.5},
                       {"direction": "sideways"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                t.run_case("Main", case([HEAVY] * 4, **change))
        for run in (t.run_screen, t.self_check):
            with self.subTest(entry_point=run.__name__), self.assertRaises(ValueError):
                run(128)

    def test_rows_use_closing_counts_and_half_open_visibility(self):
        rows = t.run_case("Main", case([HEAVY] * 4))["rows"]
        first, second = rows[:2]
        self.assertEqual(list(first["b_close"]), HEAVY)
        self.assertEqual((first["s_close"], first["evidence_close_cycle"],
                          first["effective_visible_cycle"]), (256, 255, 256))
        self.assertEqual(first["evidence"], ["DOWN", "UP", "UP", "UP"])
        self.assertEqual(first["effective_before"], ["High"] * 4)
        self.assertEqual(first["effective_after"], ["High"] * 4)
        self.assertEqual(second["effective_after"], ["Low", "High", "High", "High"])
        self.assertEqual((len(first["states_before"]), len(first["states_after"])),
                         (4, 4))

    def test_single_down_keep_and_idle_variant_controls(self):
        for followup, evidence in ((KEEP, "KEEP"), (IDLE, "S0")):
            with self.subTest(evidence=evidence):
                value = case([HEAVY, followup, followup, followup])
                main, one, alg2 = (t.run_case(v, value) for v in VARIANTS)
                self.assertEqual((main["effective_change_count"],
                                  main["events"][0]["target_effective_visible_cycle"]),
                                 (0, None))
                self.assertEqual((one["effective_change_count"],
                                  one["events"][0]["target_effective_visible_cycle"],
                                  one["events"][0]["status"]), (1, 256, "COMPLETE"))
                self.assertEqual((alg2["effective_change_count"],
                                  alg2["events"][0]["target_stable_visible_cycle"],
                                  alg2["events"][0]["target_stable_observed"],
                                  alg2["events"][0]["status"]),
                                 (1, None, False, "INCOMPLETE"))

    def test_persistent_transition_timing_matches_each_variant(self):
        value = case([HEAVY] * 4)
        expected = {"Main": (512, 512, 512), "Main-1W": (256, 256, 768),
                    "Algorithm-2": (256, 512, 512)}
        hashes = set()
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                result = t.run_case(variant, value)
                event = result["events"][0]
                hashes.add(result["counts_sha256"])
                self.assertEqual((event["role_end_exclusive"],
                                  event["first_supporting_evidence_close_cycle"],
                                  event["already_target"],
                                  event["target_effective_observed"],
                                  event["target_stable_observed"]),
                                 (1024, 255, False, True, True))
                self.assertEqual((event["target_effective_visible_cycle"],
                                  event["target_stable_visible_cycle"],
                                  event["post_target_stable_observation_cycles"]),
                                 expected[variant])
                self.assertEqual((event["status"], result["effective_change_count"],
                                  result["status"], result["latency_recovery"]),
                                 ("COMPLETE", 1, "COMPLETE", "NOT_MEASURED"))
        self.assertEqual(len(hashes), 1)
        self.assertEqual(len(next(iter(hashes))), 64)

    def test_last_close_timing_is_visible_but_not_observed(self):
        two = t.run_case("Main", case([HEAVY] * 2))
        event = two["events"][0]
        self.assertEqual(two["rows"][-1]["effective_visible_cycle"], 512)
        self.assertEqual((event["target_effective_visible_cycle"],
                          event["target_effective_observed"],
                          event["target_stable_visible_cycle"],
                          event["target_stable_observed"],
                          event["post_target_stable_observation_cycles"],
                          event["status"], two["status"]),
                         (512, False, 512, False, 0, "INCOMPLETE", "INCOMPLETE"))
        three = t.run_case("Main", case([HEAVY] * 3))["events"][0]
        self.assertTrue(three["target_effective_observed"])
        self.assertTrue(three["target_stable_observed"])
        self.assertEqual(three["post_target_stable_observation_cycles"], 256)
        self.assertEqual(three["status"], "COMPLETE")

    def test_phase_255_realizes_boundary_evidence_then_settles(self):
        value = t.make_case(256, 255, None, "down")
        rows = t.run_case("Main", value)["rows"]
        boundary = next(row for row in rows if row["evidence_close_cycle"] == 1023)
        self.assertEqual(boundary["b_close"], [16, 80, 80, 80])
        self.assertEqual(boundary["evidence"], ["UP", "DOWN", "DOWN", "DOWN"])
        expected = {"Main": 1536, "Main-1W": 1280, "Algorithm-2": 1280}
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                event = t.run_case(variant, value)["events"][0]
                self.assertEqual(event["role_change_cycle"], 1023)
                self.assertEqual(event["first_supporting_evidence_close_cycle"], 1279)
                self.assertEqual(event["target_effective_visible_cycle"], expected[variant])
                self.assertTrue(event["target_effective_observed"])

    def test_already_high_is_immediately_visible(self):
        value = case([KEEP] * 3, [{"cycle": 0, "target_effective": "High"}])
        event = t.run_case("Main", value)["events"][0]
        self.assertEqual((event["already_target"],
                          event["target_effective_visible_cycle"],
                          event["target_effective_observed"],
                          event["target_stable_visible_cycle"],
                          event["target_stable_observed"],
                          event["post_target_stable_observation_cycles"],
                          event["status"]),
                         (True, 0, True, 0, True, 768, "COMPLETE"))

    def test_early_stable_that_leaves_is_not_final_settle(self):
        value = case([HEAVY] * 3 + [SPARSE] * 2)
        event = t.run_case("Main", value)["events"][0]
        self.assertEqual((event["target_effective_visible_cycle"],
                          event["target_effective_observed"],
                          event["target_stable_visible_cycle"],
                          event["target_stable_observed"],
                          event["post_target_stable_observation_cycles"],
                          event["status"]),
                         (512, True, None, False, None, "INCOMPLETE"))

    def test_terminal_snapshot_does_not_erase_observed_stable_suffix(self):
        result = t.run_case("Main", case([HEAVY] * 3 + [SPARSE]))
        event, terminal = result["events"][0], result["rows"][-1]
        self.assertEqual((terminal["effective_visible_cycle"],
                          terminal["states_after"][0],
                          terminal["effective_after"][0]), (1024, "B_L", "Low"))
        self.assertEqual((event["target_effective_visible_cycle"],
                          event["target_stable_visible_cycle"],
                          event["target_stable_observed"],
                          event["post_target_stable_observation_cycles"],
                          event["status"]), (512, 512, True, 512, "COMPLETE"))

    def test_events_are_half_open_and_do_not_borrow_next_role(self):
        value = case([HEAVY, HEAVY, SPARSE, SPARSE], [
            {"cycle": 0, "target_effective": "Low"},
            {"cycle": 512, "target_effective": "High"}])
        result = t.run_case("Main", value)
        first, second = result["events"]
        self.assertEqual((first["role_end_exclusive"], second["role_end_exclusive"]),
                         (512, 1024))
        self.assertEqual((result["rows"][1]["effective_visible_cycle"],
                          result["rows"][1]["effective_after"][0]), (512, "Low"))
        self.assertEqual((first["target_effective_visible_cycle"],
                          first["target_effective_observed"],
                          first["target_stable_visible_cycle"],
                          first["target_stable_observed"],
                          first["post_target_stable_observation_cycles"],
                          first["status"]), (None, False, None, False, None,
                                             "INCOMPLETE"))
        self.assertEqual(second["first_supporting_evidence_close_cycle"], 767)
        self.assertEqual((second["target_effective_visible_cycle"],
                          second["target_effective_observed"],
                          second["target_stable_visible_cycle"],
                          second["target_stable_observed"],
                          second["post_target_stable_observation_cycles"],
                          second["status"]), (1024, False, 1024, False, 0,
                                              "INCOMPLETE"))
        self.assertEqual(result["effective_change_count"], 1)

    def test_screen_has_78_replays_all_cases_and_recomputable_hash(self):
        expected = {t.make_case(64, p, d, direction)["name"] for p in (0, 16, 63)
                    for d in (None, 32, 64, 96)
                    for direction in ("down", "up")}
        expected |= {"down_then_keep", "down_then_idle"}
        self.assertEqual(len(expected), 26)
        screen = t.run_screen(64)
        self.assertEqual((screen["schema"], screen["window"], screen["scope"]),
                         ("cxl-buffer-transition-screen-v2", 64, "MODEL_ONLY"))
        self.assertEqual((len(screen["results"]),
                          screen["summary"]["case_count"]), (78, 78))
        grouped = {}
        for row in screen["results"]:
            grouped.setdefault(result_name(row), []).append(row)
        self.assertEqual(set(grouped), expected)
        for name, group in grouped.items():
            with self.subTest(case=name):
                self.assertEqual({row["variant"] for row in group}, set(VARIANTS))
                self.assertEqual(len({row["counts_sha256"] for row in group}), 1)
        self.assertTrue(all(row["latency_recovery"] == "NOT_MEASURED"
                            for row in screen["results"]))
        self.assertEqual(screen["screen_sha256"], result_digest(screen))

    def test_self_check_cli_and_exclusive_output_honor_window_64(self):
        direct = t.self_check(64)
        self.assertEqual(direct["window"], 64)
        self.assertTrue(all(row["window"] == 64 for row in direct["results"]))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "screen.json"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(t.main(["--window", "64",
                                         "--output", str(output)]), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual((payload["window"], payload["schema"]),
                             (64, "cxl-buffer-transition-screen-v2"))
            self.assertEqual(payload["screen_sha256"], result_digest(payload))
            original = output.read_bytes()
            with self.assertRaises(OSError):
                t.main(["--window", "64", "--output", str(output)])
            self.assertEqual(output.read_bytes(), original)
            checked = Path(directory) / "self-check.json"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(t.main(["--self-check", "--window", "64",
                                         "--output", str(checked)]), 0)
            self.assertEqual(json.loads(checked.read_text())["window"], 64)


if __name__ == "__main__":
    unittest.main()
