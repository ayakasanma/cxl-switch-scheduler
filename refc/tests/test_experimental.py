"""Directed contracts and per-cycle differential checks of exact screen classes."""
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cxl_model.experimental import ExperimentalSwitchModel, POLICIES
from cxl_model.fai_main_model import FaiCtx, FaiMainSwitchModel
from cxl_model.fcfs_model import FcfsSwitchModel
from cxl_model.rr_model import RrSwitchModel


def model(policy, **kwargs):
    m = ExperimentalSwitchModel(policy=policy, window=64, **kwargs)
    m.commit(rst_n=False)
    return m


def push(m, sources, ready=False):
    return m.commit(ready, [h in sources for h in range(m.n_src)], list(range(m.n_src)))


class ExperimentalTests(unittest.TestCase):
    def test_baseline_per_cycle_differential(self):
        for window in (64, 256):
            for n in (4, 8, 16):
                for policy, factory in (
                    ("FAI-inspired", lambda: FaiMainSwitchModel(n, window=window)),
                    ("RR10", lambda: RrSwitchModel(n)),
                    ("FCFS", lambda: FcfsSwitchModel(n)),
                ):
                    with self.subTest(window=window, n=n, policy=policy):
                        rng = random.Random(f"baseline:{window}:{n}:{policy}")
                        a = ExperimentalSwitchModel(n, policy, window)
                        b = factory()
                        for m in (a, b):
                            m.commit(rst_n=False)
                            if policy != "RR10":
                                m.deposit_counter((1 << 32) - 24)
                        pending = [None] * n
                        # Eight actual windows, long boundary stalls, churn and resets.
                        for k in range(8 * window + 19):
                            if k == 4 * window + 7:
                                a.commit(rst_n=False)
                                b.commit(rst_n=False)
                                pending = [None] * n
                            for h in range(n):
                                prob = .9 if h == (k // window) % n else .06
                                if pending[h] is None and rng.random() < prob:
                                    pending[h] = rng.getrandbits(105)
                            ready = rng.random() > .23 and not window-3 <= k % (2*window) < window+9
                            av, bv = a.view(ready), b.view(ready)
                            self.assertEqual(av, bv, (policy, window, n, k))
                            valid = [d is not None for d in pending]
                            desc = [d or 0 for d in pending]
                            ae, be = a.commit(ready, valid, desc), b.commit(ready, valid, desc)
                            self.assertEqual([e.desc if e else None for e in ae.pushed],
                                             [getattr(e, "desc", e) for e in be.pushed])
                            actual = None if ae.fired is None else (ae.fired.source, ae.fired.entry.desc)
                            expected = None if be.fired is None else (be.fired[0], getattr(be.fired[1], "desc", be.fired[1]))
                            self.assertEqual(actual, expected)
                            if policy == "FAI-inspired":
                                self.assertEqual(a.classes(), b.classes())
                                self.assertEqual(a.window_state(), b.window_state())
                                self.assertEqual(a.visit, b.visit)
                                self.assertEqual(a.service, b.service)
                            if policy == "RR10":
                                self.assertEqual((a.poll, a.used), b.polling_state())
                            for h in range(n):
                                if valid[h] and av.in_ready[h]:
                                    pending[h] = None

    def test_cgof_refill_only_on_fire_and_held_snapshot(self):
        m = model("CGOF(2:1)", n_src=2)
        push(m, (0, 1))
        m.cls = ["H", "L"]  # Directed class fixture, not natural training.
        before = m.choice()
        self.assertEqual(before.credits, (2, 1))
        m.commit(False)
        self.assertEqual(m.credits, [0, 0])
        m.cls = ["L", "H"]
        for _ in range(70):
            self.assertEqual(m.choice(), before)
            m.commit(False)
        e = m.commit(True)
        self.assertEqual(e.fired.source, 0)
        self.assertEqual(m.credits, [1, 1])

    def test_cgof_inactive_refill_reentry_and_no_bubble(self):
        m = model("CGOF(2:1)", n_src=2)
        push(m, (0,))
        m.credits = [0, 2]  # Inactive positive credit cannot block refill.
        self.assertTrue(m.view(True).fire)
        m.commit(True)
        self.assertEqual(m.credits, [1, 2])
        push(m, (0,))
        m.commit(True)
        self.assertEqual(m.credits, [0, 2])
        push(m, (0, 1))
        self.assertEqual(m.choice().source, 1)  # No reentry bonus for source 0.
        m.commit(True)
        self.assertEqual(m.credits, [0, 1])
        self.assertEqual(m.choice().source, 0)  # Remaining active source starts next round.
        self.assertEqual(m.choice().credits, (2, 2))

    def test_full_reject_same_cycle_pop_and_nonfull_replace(self):
        for policy in POLICIES:
            m = model(policy, n_src=2, depth=1)
            push(m, (0,))
            e = push(m, (0,), ready=True)
            self.assertIsNotNone(e.fired)
            self.assertIsNone(e.pushed[0])
            self.assertEqual(m.occupancy(0), 0)
            m = model(policy, n_src=2, depth=2)
            push(m, (0,))
            e = push(m, (0,), ready=True)
            self.assertIsNotNone(e.fired)
            self.assertIsNotNone(e.pushed[0])
            self.assertEqual(m.occupancy(0), 1)

    def test_age_gap_ready_only_saturation_and_empty_reset(self):
        m = model("AGE_T16_K8", n_src=2, gap_max=16)
        push(m, (0, 1))
        m.cls = ["H", "L"]
        for _ in range(20):
            m.visit, m.budget = FaiCtx("High", 0), 0
            push(m, (0,), True)
        self.assertEqual(m.gaps[1], 16)
        m.budget = 8
        before = list(m.gaps)
        for _ in range(20):
            m.commit(False)
        self.assertEqual(m.gaps, before)
        # The stalled rescue remains held and fires without preemption.
        self.assertTrue(m.choice().rescue)
        m.commit(True)
        self.assertEqual(m.gaps[1], 0)
        push(m, (1,), False)
        self.assertEqual(m.gaps[1], 0)

    def test_age_same_normal_source_does_not_spend_budget(self):
        m = model("AGE_T16_K8", n_src=2)
        push(m, (0,))
        for _ in range(20):
            m.commit(False)
        m.budget, m.gaps[0] = 8, 20
        self.assertFalse(m.choice().rescue)
        m.commit(True)
        self.assertEqual(m.budget, 8)
        self.assertEqual(m.rescues, 0)

    def test_age_rescue_cap_stall_and_preserved_visit(self):
        m = model("AGE_T16_K8", n_src=2)
        push(m, (0, 1))
        # Build age with a held source, then set an explicit policy-state fixture.
        for _ in range(20):
            push(m, (0,), False)
        m.commit(True)
        m.cls = ["H", "L"]
        m.visit = FaiCtx("High", 3)
        m.budget, m.gaps[1] = 8, 16
        choice = m.choice()
        self.assertTrue(choice.rescue)
        self.assertEqual(choice.source, 1)
        visit = m.visit
        m.commit(False)
        m.cls = ["L", "H"]
        for _ in range(70):
            self.assertEqual(m.choice(), choice)
            m.commit(False)
        e = m.commit(True)
        self.assertTrue(e.rescue)
        self.assertEqual(m.visit, visit)
        self.assertEqual(m.budget, 0)
        self.assertEqual(sum(m.b) + 0, m.s)
        # Across random churn every pair of rescues has >=K normal fires.
        rng, normals, seen = random.Random(521), 0, False
        for _ in range(2000):
            e = push(m, (0, 1), rng.random() > .1)
            if e.fired:
                if e.rescue:
                    if seen:
                        self.assertGreaterEqual(normals, 8)
                    normals, seen = 0, True
                else:
                    normals += 1

    def test_age_heavy_service_prevents_gap_urgency(self):
        m = model("AGE_T16_K8", n_src=2)
        push(m, (0,))
        for _ in range(80):
            push(m, (0,), True)
        self.assertEqual(m.gaps[0], 0)
        self.assertFalse(m.choice().rescue)

    def test_held_half_range_checked_on_view_and_commit(self):
        for policy in POLICIES:
            m = model(policy, n_src=2, ts_width=6)
            push(m, (0,))
            while m.time < 32:
                self.assertTrue(m.view(False).out_valid)
                m.commit(False)
            self.assertIsNotNone(m.ctrl.held)
            for observe in (lambda: m.choice(), lambda: m.view(True), lambda: m.commit(True)):
                with self.assertRaisesRegex(AssertionError, "half-range"):
                    observe()
            m.commit(rst_n=False)
            self.assertIsNone(m.choice())

    def test_age_maxgap_then_oldest_tie_and_age_only(self):
        m = model("AGE_T16_K8", n_src=4)
        push(m, (0, 1, 2, 3))
        # Hold source 0 through aging, then release it before arranging urgency.
        for _ in range(20):
            push(m, (0,), False)
        m.commit(True)
        m.cls = ["H", "L", "L", "L"]
        m.visit, m.budget = FaiCtx("High", 0), 8
        m.gaps = [0, 16, 18, 18]
        self.assertEqual(m.choice().source, 2)
        self.assertTrue(m.choice().rescue)
        m.gaps[1] = 19
        self.assertEqual(m.choice().source, 1)
        # Age alone ignores both the gap and rescue budget, and may equal FCFS.
        m.policy, m.gaps, m.budget = "AGE_ONLY", [0]*4, 0
        self.assertEqual(m.choice().source, 1)
        self.assertTrue(m.choice().rescue)

    def test_closing_fire_included_and_stalled_classification(self):
        for policy in POLICIES:
            m = model(policy, n_src=2)
            for k in range(64):
                edge = push(m, (0,), ready=True)
            self.assertEqual(edge.closing["counts"], (63, 0))
            self.assertEqual(edge.closing["total"], 63)
            self.assertEqual(m.window_state(), (0, (0, 0), 0))
            self.assertEqual(m.cls, ["B_H", "H"])
            for _ in range(64):
                edge = m.commit(False)
            self.assertEqual(edge.closing["total"], 0)
            self.assertEqual(m.cls, ["H", "H"])

    def test_weighted_all_backlogged_objective(self):
        for policy, expected in (("CGOF(2:1)", [200, 100]), ("CGOF(1:1)", [150, 150])):
            m = model(policy, n_src=2)
            for _ in range(16):
                push(m, (0, 1))
            m.commit(True)  # Release the initial all-High held refill context.
            m.credits, m.service = [0, 0], [0, 0]
            # Frozen fixture isolates the weighted objective from classification feedback.
            for _ in range(300):
                m.cls = ["H", "L"]
                push(m, (0, 1), True)
            self.assertEqual(m.service, expected)

    def test_configurations_keep_distinct_allocation(self):
        for weight in (1, 2):
            configured = model(f"CGOF({weight}:1)", n_src=2)
            explicit = model("CGOF", n_src=2, high_weight=weight)
            for m in (configured, explicit):
                push(m, (0, 1))
                m.cls = ["H", "L"]
            self.assertEqual(configured.policy, "CGOF")
            self.assertEqual(configured.choice(), explicit.choice())
            self.assertEqual(configured.choice().credits, (weight, 1))
        for args in (dict(high_weight=0), dict(high_weight=True),
                     dict(high_weight=3), dict(policy="CGOF(1:1)", high_weight=2),
                     dict(ordering="invalid"),
                     dict(policy="FCFS", ordering="eligible-round-robin")):
            with self.assertRaises(ValueError):
                ExperimentalSwitchModel(**args)

    def test_eligible_round_robin_pointer_and_held_refill(self):
        m = model("CGOF", n_src=4, ordering="eligible-round-robin")
        push(m, (0, 1, 2, 3))
        m.poll = 1
        self.assertEqual(m.choice().source, 1)
        offer = m.choice()
        for _ in range(70):
            m.commit(False)
            self.assertEqual(m.choice(), offer)
            self.assertEqual(m.poll, 1)
            self.assertEqual(m.credits, [0]*4)
        m.commit(True)
        self.assertEqual(m.poll, 2)
        self.assertEqual(m.choice().source, 2)
        self.assertEqual(m.credits, [2, 1, 2, 2])
        m.commit(True)
        self.assertEqual(m.poll, 3)
        self.assertEqual(m.choice().source, 3)

    def test_ordering_control_changes_only_eligible_selection(self):
        oldest = model("CGOF", n_src=4)
        rr = model("CGOF", n_src=4, ordering="eligible-round-robin")
        for m in (oldest, rr):
            push(m, (3,))
            push(m, (1, 2), True)
            # Source 1 has the same accepted age as source 2; control starts at 2.
            m.poll = 2
            m.credits = [0, 1, 1, 0]
        self.assertEqual(oldest.choice().source, 1)
        self.assertEqual(rr.choice().source, 2)
        self.assertEqual(oldest.choice().credits, rr.choice().credits)
        self.assertEqual(oldest.window_state(), rr.window_state())
        self.assertEqual(oldest.classes(), rr.classes())

    def test_round_robin_fixed_class_shares(self):
        for weight, expected in ((1, [150, 150]), (2, [200, 100])):
            m = model("CGOF", n_src=2, high_weight=weight,
                      ordering="eligible-round-robin")
            for _ in range(16):
                push(m, (0, 1))
            m.commit(True)
            m.credits, m.service = [0, 0], [0, 0]
            for _ in range(300):
                m.cls = ["H", "L"]
                push(m, (0, 1), True)
            self.assertEqual(m.service, expected)

    def test_reset_wrap_validation_and_random_invariants(self):
        for args in (dict(policy="bad"), dict(window=32), dict(ts_width=1),
                     dict(n_src=1), dict(depth=0), dict(gap_max=8)):
            with self.assertRaises(ValueError):
                ExperimentalSwitchModel(**args)
        for policy in POLICIES:
            m = model(policy, n_src=4)
            m.deposit_counter((1 << 32) - 3)
            push(m, (2, 3))
            m.commit(False)
            push(m, (0, 1))
            self.assertEqual(m.choice().source, 2 if policy != "RR10" else 2)
            rng = random.Random(509)
            held = None
            accepted = fired = 0
            initial = sum(m.occupancy(h) for h in range(4))
            for _ in range(1000):
                ready = rng.random() > .3
                v = m.view(ready)
                if held:
                    self.assertEqual((v.out_source, v.out_desc), held)
                held = (v.out_source, v.out_desc) if v.out_valid and not ready else None
                self.assertEqual(v.out_valid, any(v.count))
                e = push(m, [h for h in range(4) if rng.random() < .3], ready)
                accepted += sum(x is not None for x in e.pushed)
                fired += e.fired is not None
                self.assertEqual(initial + accepted - fired, sum(m.occupancy(h) for h in range(4)))
                self.assertEqual(sum(m.b), m.s)
            m.commit(rst_n=False)
            self.assertEqual(m.service, [0]*4)
            self.assertEqual(m.gaps, [0]*4)
            self.assertEqual(m.credits, [0]*4)
            self.assertIsNone(m.choice())
            self.assertEqual(m.classes(), ("H",)*4)


if __name__ == "__main__":
    unittest.main()
