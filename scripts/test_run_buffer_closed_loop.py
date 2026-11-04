#!/usr/bin/env python3
"""Contract tests for the MODEL_ONLY closed-loop Buffer screen."""
import hashlib
import inspect
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from refc.cxl_model.experimental import (  # noqa: E402
    CLASSIFIERS, ExperimentalSwitchModel,
)
from refc.cxl_model import experimental  # noqa: E402
from refc.cxl_model.fai_main_model import LOW  # noqa: E402
from refc.cxl_model.revision_baselines import MAIN_1W_TRANSITIONS  # noqa: E402
from scripts import run_buffer_closed_loop as t  # noqa: E402
def first(mapping, *keys):
    for key in keys:
        if key in mapping:
            return mapping[key]
    raise AssertionError(f"missing one of {keys!r}")
def scenario_hash(row):
    return row["scenario_sha256"]
def action_hash(row):
    return row["action_trace_sha256"]
def roles(row):
    return row["roles"]
def events(row):
    return row["events"]
def screen_digest(value):
    payload = dict(value)
    payload.pop("screen_sha256")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
def scenario_for(direction="down", duration=None, phase=0):
    return t.BufferScenario(
        seed=6101, phase=phase, duration=duration,
        direction=direction, window=64,
    )
def six_lanes(scenario):
    return {
        (weight, classifier): t.run_lane(scenario, classifier, weight)
        for weight in (2, 1)
        for classifier in CLASSIFIERS
    }
def push_only_model(classifier):
    model = ExperimentalSwitchModel(
        n_src=4, policy="FCFS", window=64, classifier=classifier
    )
    model.commit(rst_n=False)
    closes = []
    for _ in range(2 * 64):
        edge = model.commit(True, [True, False, False, False], [1, 0, 0, 0])
        if edge.closing is not None:
            closes.append(edge.closing)
    return model, closes
class ScenarioTests(unittest.TestCase):
    def test_public_api_and_screen_schema(self):
        for name in ("BufferScenario", "run_lane", "run_screen", "self_check", "main"):
            self.assertTrue(callable(getattr(t, name)))
        defaults = inspect.signature(t.BufferScenario).parameters
        self.assertEqual((defaults["phase"].default, defaults["duration"].default,
                          defaults["direction"].default, defaults["window"].default),
                         (0, None, "down", 256))
        screen = inspect.signature(t.run_screen).parameters
        self.assertEqual((screen["seeds"].default, screen["window"].default,
                          screen["directions"].default),
                         ((6101,), 256, ("down", "up")))
        self.assertEqual(inspect.signature(t.self_check).parameters["window"].default, 64)
        self.assertEqual(t.SCHEMA, "cxl-buffer-closed-loop-screen-v1")
    def test_horizon_direction_and_immutable_generation_roles(self):
        for direction, initial, switched, returned in (
            ("down", "R0", "R3", "R0_return"),
            ("up", "R3", "R0", "R3_return"),
        ):
            with self.subTest(direction=direction):
                phase, duration = 7, 48
                noise = scenario_for(direction, duration, phase)
                change = 3 * 64 + phase
                self.assertEqual(noise.role_change, change)
                self.assertEqual(noise.role_end, change + duration)
                self.assertEqual(noise.end_exclusive, change + duration + 4 * 64)
                self.assertEqual(noise.generation_role(0, 0), initial)
                self.assertEqual(noise.generation_role(change, 0), switched)
                self.assertEqual(
                    noise.generation_role(noise.role_end, 0), returned
                )
                persistent = scenario_for(direction, None, phase)
                self.assertEqual(persistent.role_change, change)
                self.assertEqual(persistent.role_end, change + 4 * 64)
                self.assertEqual(persistent.end_exclusive, persistent.role_end)
                self.assertEqual(persistent.generation_role(
                    persistent.end_exclusive - 1, 0), switched)
    def test_inputs_are_deterministic_and_hot_source_reverses(self):
        left, right = scenario_for("down", 64), scenario_for("down", 64)
        self.assertEqual(left.input_sha256, right.input_sha256)
        self.assertEqual(left.arrivals, right.arrivals)
        self.assertEqual(left.ready_trace, right.ready_trace)
        with mock.patch.object(t, "_fraction", return_value=0.5):
            down, up = scenario_for("down", 64), scenario_for("up", 64)
        self.assertEqual([s for s, _ in down.arrivals[0]], [0])
        self.assertEqual([s for s, _ in down.arrivals[down.role_change]], [3])
        self.assertEqual([s for s, _ in down.arrivals[down.role_end]], [0])
        self.assertEqual([s for s, _ in up.arrivals[0]], [3])
        self.assertEqual([s for s, _ in up.arrivals[up.role_change]], [0])
        self.assertEqual(set(down.ready_trace), {1})
    def test_invalid_scenario_arguments_are_rejected(self):
        invalid = (
            {"seed": -1}, {"seed": 1.0}, {"seed": True},
            {"window": 0}, {"window": 128}, {"window": True},
            {"phase": -1}, {"window": 64, "phase": 64}, {"phase": 1.0},
            {"duration": 0}, {"duration": -1}, {"duration": 1.5},
            {"direction": "sideways"}, {"direction": "Down"},
            {"direction": None},
        )
        for changes in invalid:
            kwargs = {"seed": 6101}
            kwargs.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                t.BufferScenario(**kwargs)
class LaneTests(unittest.TestCase):
    def test_six_lanes_share_inputs_and_fixed_contract(self):
        scenario = scenario_for()
        lanes = six_lanes(scenario)
        self.assertEqual(len(lanes), 6)
        self.assertEqual(
            {scenario_hash(row) for row in lanes.values()},
            {scenario.input_sha256},
        )
        for (weight, classifier), row in lanes.items():
            with self.subTest(weight=weight, classifier=classifier):
                self.assertEqual(
                    row["latency_recovery"], "NOT_DEFINED_THIS_ROUND"
                )
                self.assertEqual(
                    (row["window"], row["high_weight"], row["classifier"]),
                    (64, weight, classifier),
                )
                self.assertEqual(row["cycles"], scenario.end_exclusive)
                self.assertEqual(len(events(row)), 1)
                expected = "R3" if scenario.direction == "down" else "R0"
                self.assertEqual(
                    first(events(row)[0], "role_id", "role"), expected
                )
                self.assertGreaterEqual(len(action_hash(row)), 32)
    def test_generation_cohorts_are_immutable_and_split_hot_sparse(self):
        for direction, expected in (
            ("down", {"R0", "R3", "R0_return"}),
            ("up", {"R3", "R0", "R3_return"}),
        ):
            scenario = scenario_for(direction, duration=64)
            expected_counts = {role: 0 for role in expected}
            for cycle, arrivals in enumerate(scenario.arrivals):
                for source, _ in arrivals:
                    role = scenario.generation_role(cycle, source)
                    expected_counts[role] += 1
            for row in six_lanes(scenario).values():
                with self.subTest(direction=direction,
                                  classifier=row["classifier"]):
                    observed = roles(row)
                    self.assertEqual(
                        {role: observed[role]["generated"] for role in expected},
                        expected_counts,
                    )
                    self.assertTrue(all(
                        "hot" in observed[role] and "sparse" in observed[role]
                        for role in expected
                    ))
    def test_event_completion_needs_real_pre_end_suffix(self):
        scenario = scenario_for("down", duration=64)
        for row in six_lanes(scenario).values():
            for event in events(row):
                with self.subTest(classifier=row["classifier"]):
                    end = first(
                        event, "end_exclusive", "role_end_exclusive"
                    )
                    suffix = first(
                        event, "stable_suffix_start",
                        "target_stable_visible_cycle",
                    )
                    post = first(
                        event, "post_settle_cycles",
                        "post_target_stable_observation_cycles",
                    )
                    if event["status"] == "COMPLETE":
                        self.assertIsNotNone(suffix)
                        self.assertGreaterEqual(end - suffix, 64)
                        self.assertGreaterEqual(post, 64)
                    else:
                        self.assertEqual(event["status"], "INCOMPLETE")
                        self.assertTrue(event.get("reason"))
                    if post == 0:
                        self.assertEqual(suffix, end)
                        self.assertNotEqual(event["status"], "COMPLETE")
    def test_bounded_drain_is_incomplete_not_fatal(self):
        scenario = scenario_for("down", duration=64)
        scenario.ready_trace[:] = [0] * len(scenario.ready_trace)
        row = t.run_lane(scenario, "live", 2)
        self.assertEqual(row["latency_recovery"], "NOT_DEFINED_THIS_ROUND")
        self.assertEqual(row["requests_censored"], row["requests_generated"])
        self.assertEqual(row["population"]["generation_to_fire"]["count"], 0)
        self.assertIsNone(row["population"]["generation_to_fire"]["p99"])
        self.assertEqual(row["drain_cycles"], 4 * scenario.window)
        self.assertEqual(row["drain_status"], "INCOMPLETE")
        self.assertEqual(row["drain_reason"], "RIGHT_CENSORED_AT_DRAIN_BUDGET")
        self.assertTrue(all(e["status"] == "INCOMPLETE" for e in events(row)))
    def test_empty_statistics_are_null_and_invalid_lane_args_fail(self):
        empty = t.stats([])
        self.assertEqual(empty["count"], 0)
        for key in ("mean", "p50", "p95", "p99", "max"):
            self.assertIsNone(empty[key])
        scenario = scenario_for()
        for classifier in ("bad", None, ""):
            with self.subTest(classifier=classifier), self.assertRaises(ValueError):
                t.run_lane(scenario, classifier, 1)
        for weight in (0, 3, True, 1.0, None):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                t.run_lane(scenario, "live", weight)

    def test_terminal_close_and_last_stable_suffix_have_no_extra_window(self):
        scenario = scenario_for()
        stop = scenario.end_exclusive
        event = {
            "start": 0, "stop": stop, "target_effective": LOW,
            "hot_source": 3, "role_id": "R3", "name": "terminal",
        }
        high = ("H",) * 4
        low3 = ("H", "H", "H", "L")
        timing = t._event_timing(
            scenario, event, 1, [(0, high), (stop, low3)], [],
        )
        self.assertEqual(timing["first_effective_visible"], stop)
        self.assertEqual(timing["stable_suffix_start"], stop)
        self.assertEqual(timing["post_settle_cycles"], 0)
        self.assertFalse(timing["target_stable_observed"])
        self.assertEqual(timing["reason"], "POST_SETTLE_LT_W")
        timeline = [(0, high), (64, low3), (128, high), (256, low3), (stop, high)]
        timing = t._event_timing(scenario, event, 1, timeline, [])
        self.assertEqual(timing["first_effective_visible"], 64)
        self.assertEqual(timing["first_stable_visible"], 256)
        self.assertEqual(timing["stable_suffix_start"], 256)
        self.assertEqual(timing["post_settle_cycles"], stop - 256)
        self.assertEqual(timing["status"], "COMPLETE")

    def test_generation_role_survives_switch_and_empty_sources_keep_null_latency(self):
        scenario = scenario_for()
        row = t.run_lane(scenario, "live", 2)
        self.assertGreater(row["roles"]["R0"]["completed_after_role_end"], 0)
        self.assertEqual(
            sum(role["generated"] for role in row["roles"].values()),
            row["requests_generated"],
        )
        request = t.Request(0, 0, "R0", 7, 0, True)
        request.accepted_cycle = 3
        request.fired_cycle = scenario.role_change + 5
        block = t._latency_block([request], scenario.end_exclusive, scenario.role_change)
        self.assertEqual(request.generation_role, "R0")
        self.assertEqual(block["completed_after_role_end"], 1)
        self.assertEqual(block["generation_to_acceptance"]["mean"], 3)
        self.assertEqual(block["generation_to_fire"]["mean"], request.fired_cycle)
        for source in block["by_source"][1:]:
            self.assertEqual(source["generated"], 0)
            for stage in t.STAGES:
                self.assertEqual(source[stage], t.stats([]))
        self.assertEqual(block["sparse"]["generation_to_fire"], t.stats([]))

    def test_already_target_zero_flips_is_class_observation_only(self):
        scenario = scenario_for()
        event = {
            "start": 0, "stop": 64, "target_effective": LOW,
            "hot_source": 3, "role_id": "R3", "name": "already",
        }
        timing = t._event_timing(
            scenario, event, 1, [(0, ("H", "H", "H", "L"))], [],
        )
        self.assertTrue(timing["already_target"])
        self.assertEqual(timing["effective_change_count"], 0)
        self.assertEqual(timing["stable_suffix_start"], 0)
        self.assertEqual(timing["status"], "COMPLETE")
        lane = t.run_lane(scenario, "frozen", 1)
        self.assertEqual(lane["latency_recovery"], "NOT_DEFINED_THIS_ROUND")
        self.assertEqual(lane["effective_change_count"], 0)
        self.assertTrue(all(event["status"] == "INCOMPLETE" for event in lane["events"]))

    def test_nearest_rank_is_not_interpolation(self):
        result = t.stats(range(1, 21))
        self.assertEqual((result["p50"], result["p95"], result["p99"]), (10, 19, 20))

class ClassifierTests(unittest.TestCase):
    def test_frozen_and_transition_tables_are_distinct(self):
        frozen, frozen_closes = push_only_model("frozen")
        live, live_closes = push_only_model("live")
        one, one_closes = push_only_model("1w")
        self.assertEqual(frozen.classes(), ("H", "H", "H", "H"))
        self.assertTrue(all(set(c["classes"]) == {"H"} for c in frozen_closes))
        self.assertEqual(
            (live_closes[0]["classes"][0], live_closes[1]["classes"][0]),
            ("B_H", "L"),
        )
        self.assertEqual(
            (one_closes[0]["classes"][0], one_closes[1]["classes"][0]),
            ("L", "L"),
        )
        self.assertEqual(live.classes()[0], one.classes()[0])
        self.assertEqual(live.windows_closed, one.windows_closed)

    def test_one_window_uses_all_sixteen_accepted_table_entries(self):
        for (state, evidence), expected in MAIN_1W_TRANSITIONS.items():
            with self.subTest(state=state, evidence=evidence):
                model = ExperimentalSwitchModel(
                    policy="CGOF(2:1)", window=64, classifier="1w",
                )
                model.commit(rst_n=False)
                model.cls = [state] * 4
                model.win_pos = 63
                with mock.patch.object(experimental, "threshold_evidence", return_value=evidence):
                    edge = model.commit()
                self.assertEqual(edge.closing["old_classes"], (state,) * 4)
                self.assertEqual(model.classes(), (expected,) * 4)

    def test_frozen_is_high_on_every_cycle_including_stalls_and_closes(self):
        model = ExperimentalSwitchModel(window=64, classifier="frozen")
        model.commit(rst_n=False)
        for cycle in range(3 * 64):
            self.assertEqual(model.classes(), ("H",) * 4)
            model.commit(cycle % 4 != 0, [True, False, False, False], [1, 0, 0, 0])
            self.assertEqual(model.classes(), ("H",) * 4)

class ScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen = t.run_screen(
            seeds=(6101,), window=64, phases=(0,),
            durations=(None,), directions=("down", "up"),
        )
    def test_screen_schema_hash_and_self_check(self):
        screen = self.screen
        self.assertEqual(
            (screen["schema"], screen["scope"], screen["contract_version"]),
            ("cxl-buffer-closed-loop-screen-v1", "MODEL_ONLY",
             "cxl-buffer-closed-loop-v1"),
        )
        self.assertEqual(
            screen["latency_recovery"], "NOT_DEFINED_THIS_ROUND"
        )
        self.assertEqual(
            (screen["window"], screen["identity"]["seed"],
             screen["identity"]["window"]),
            (64, 6101, 64),
        )
        self.assertEqual(len(screen["variants"]), 12)
        self.assertEqual(screen["screen_sha256"], screen_digest(screen))
        checked = t.self_check(64)
        self.assertEqual(
            (checked["schema"], checked["window"]),
            ("cxl-buffer-closed-loop-screen-v1", 64),
        )
        self.assertTrue(all(row["window"] == 64
                            for row in checked["variants"]))
        self.assertEqual(checked["screen_sha256"], screen_digest(checked))
    def test_cgof1_control_and_cgof2_descriptive_difference(self):
        positive_differences = 0
        for direction in ("down", "up"):
            lanes = six_lanes(scenario_for(direction))
            for weight in (1, 2):
                group = [row for (w, _), row in lanes.items() if w == weight]
                self.assertEqual(
                    len({scenario_hash(row) for row in group}), 1
                )
                if weight == 1:
                    self.assertEqual(
                        len({action_hash(row) for row in group}), 1
                    )
                    for key in ("population", "roles", "queue_metrics", "snapshots"):
                        self.assertEqual(group[0][key], group[1][key])
                        self.assertEqual(group[0][key], group[2][key])
                elif len({action_hash(row) for row in group}) > 1:
                    positive_differences += 1
        self.assertGreater(positive_differences, 0)
        pairing = self.screen["pairing"]
        self.assertTrue(pairing["input_equal"])
        self.assertTrue(pairing["cgof1_control_equal"])
        self.assertTrue(pairing["cgof2_descriptive_only"])

    def test_pairing_rejects_descriptor_ready_and_horizon_mismatch(self):
        original = t.run_lane
        for changed in ("descriptor", "ready", "horizon"):
            calls = 0

            def mismatched(scenario, classifier, weight):
                nonlocal calls
                result = original(scenario, classifier, weight)
                calls += 1
                if calls == 1:
                    if changed == "descriptor":
                        source, description = scenario.arrivals[0][0]
                        scenario.arrivals[0][0] = (source, description ^ 1)
                    elif changed == "ready":
                        scenario.ready_trace[0] ^= 1
                    else:
                        scenario.end_exclusive += 1
                return result

            with self.subTest(changed=changed), mock.patch.object(t, "run_lane", mismatched):
                with self.assertRaises((AssertionError, ValueError)):
                    t.run_screen((6101,), 64, (0,), (None,), ("down",))

    def test_classifier_leakage_fails_cgof1_control(self):
        def leaking_model(**kwargs):
            model = ExperimentalSwitchModel(**kwargs)
            if kwargs["policy"] == "CGOF(1:1)" and kwargs["classifier"] == "1w":
                model.high_weight = 2
            return model

        with mock.patch.object(t, "ExperimentalSwitchModel", leaking_model):
            result = t.run_screen((6101,), 64, (0,), (None,), ("down",))
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["pairing"]["cgof1_control_equal"])

    def test_source_changes_during_screen_are_rejected(self):
        before = t._source_hashes()
        after = {**before, "scripts/run_buffer_closed_loop.py": "changed"}
        with mock.patch.object(t, "_source_hashes", side_effect=[before, after]):
            with self.assertRaisesRegex(RuntimeError, "source changed"):
                t.run_screen((6101,), 64, (0,), (None,), ("down",))
    def test_cli_seed_forms_and_exclusive_output(self):
        parser = t.parser()
        self.assertEqual(
            parser.parse_args(
                ["--seeds", "6101-6103", "--window", "64"]
            ).seeds,
            (6101, 6102, 6103),
        )
        self.assertEqual(
            parser.parse_args(
                ["--seeds", "6101,6103", "--window", "256"]
            ).seeds,
            (6101, 6103),
        )
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["--seeds", "6103-6101"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            t.main(["--window", "128"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "self-check.json"
            with redirect_stdout(io.StringIO()):
                status = t.main([
                    "--self-check", "--window", "64", "--output", str(output)
                ])
            self.assertEqual(status, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                (payload["schema"], payload["window"]),
                ("cxl-buffer-closed-loop-screen-v1", 64),
            )
            self.assertEqual(payload["screen_sha256"],
                             screen_digest(payload))
            original = output.read_bytes()
            with self.assertRaises(OSError):
                t.main([
                    "--self-check", "--window", "64", "--output", str(output)
                ])
            self.assertEqual(output.read_bytes(), original)
    def test_invalid_screen_arguments_are_rejected(self):
        cases = (
            {"window": 0}, {"window": 128}, {"seeds": (-1,)},
            {"phases": (-1,)}, {"phases": (64,)}, {"durations": (0,)},
            {"durations": (1.5,)}, {"directions": ("sideways",)},
        )
        for changes in cases:
            args = {
                "seeds": (6101,), "window": 64, "phases": (0,),
                "durations": (None,), "directions": ("down",),
            }
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                t.run_screen(**args)
        for window in (0, 128, True):
            with self.subTest(window=window), self.assertRaises(ValueError):
                t.self_check(window)
if __name__ == "__main__":
    unittest.main()
