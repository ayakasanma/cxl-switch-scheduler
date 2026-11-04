"""Pure-Python checks of refc/cxl_model/revision_baselines.py (no simulator; not RTL evidence).

* reductions: FaiVariantSwitchModel(high_quota=10, main_1w=False) == accepted FaiMainSwitchModel,
  BlissSwitchModel with an unreachable threshold == accepted FcfsSwitchModel, edge by edge on
  seeded random traffic with stalls and mid-run resets;
* observation: Main-1W at HIGH_QUOTA=10 is pin-identical to the accepted Algorithm-2 model (same
  effective-class rule; only the state encoding differs) - recorded, not hidden;
* literal tables and hand-derived directed scenarios for BLISS streak/blacklist/clear boundaries
  and for High quotas 5/10/20 with Low 10, including retained contexts across stalls.
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "refc"))

from cxl_model import FaiAlg2SwitchModel, FaiMainSwitchModel, FcfsSwitchModel  # noqa: E402
from cxl_model.fai_main_model import EFFECTIVE_CLASS, EVIDENCES, MAIN_TRANSITIONS, FaiCtx  # noqa: E402
from cxl_model.revision_baselines import (  # noqa: E402
    MAIN_1W_TRANSITIONS,
    BlissSwitchModel,
    FaiVariantSwitchModel,
    variant_ctx_bits,
    variant_ctx_from_hw,
    variant_ctx_to_hw,
)

SEEDS = (509, 510, 511)


def pins(view):
    return (view.in_ready, view.out_valid, view.out_source, view.out_desc)


def lockstep(models, n, cycles, seed, push_p=0.35, ready_p=0.6, reset_p=0.002, hog=None,
             compare_ctx=True):
    """Drive identical inputs into every model; views must agree every cycle. Returns fires."""
    rng = random.Random(seed)
    for m in models:
        m.commit(rst_n=False)
    fires = 0
    tag = 0
    for k in range(cycles):
        rst_n = rng.random() >= reset_p
        ready = rng.random() < ready_p
        valid, desc = [], []
        for h in range(n):
            p = 0.9 if hog is not None and h == hog else push_p
            valid.append(rng.random() < p)
            tag += 1
            desc.append((tag << 73) | (rng.getrandbits(32) << 41) | rng.getrandbits(41))
        views = [m.view(ready, rst_n) for m in models]
        ref = views[0]
        for v in views[1:]:
            assert pins(v) == pins(ref), (seed, k, pins(v), pins(ref))
            if compare_ctx:
                assert v.grant_ctx == ref.grant_ctx, (seed, k)
        fires += int(ref.fire)
        for m in models:
            m.commit(ready, valid, desc, rst_n)
    return fires


class Reductions(unittest.TestCase):
    def test_variant_q10_equals_accepted_main(self):
        for n in (4, 8, 16):
            for w in (64, 256):
                for seed in SEEDS:
                    a = FaiMainSwitchModel(n, window=w)
                    b = FaiVariantSwitchModel(n, window=w, high_quota=10, main_1w=False)
                    rng = random.Random(seed)
                    a.commit(rst_n=False)
                    b.commit(rst_n=False)
                    for k in range(6 * w):
                        rst_n = rng.random() >= 0.002
                        ready = rng.random() < 0.6
                        valid = [rng.random() < (0.9 if h == 0 else 0.25) for h in range(n)]
                        desc = [rng.getrandbits(105) for _ in range(n)]
                        va, vb = a.view(ready, rst_n), b.view(ready, rst_n)
                        self.assertEqual(va, vb, (n, w, seed, k))
                        a.commit(ready, valid, desc, rst_n)
                        b.commit(ready, valid, desc, rst_n)
                        self.assertEqual(a.classes(), b.classes())
                        self.assertEqual(a.window_state(), b.window_state())
                        self.assertEqual(a.visit_state(), b.visit_state())

    def test_bliss_without_blacklisting_equals_fcfs(self):
        for n in (4, 8, 16):
            for seed in SEEDS:
                fires = lockstep([FcfsSwitchModel(n), BlissSwitchModel(n, threshold=1 << 30)], n, 4000, seed)
                self.assertGreater(fires, 1000)

    def test_main_1w_q10_is_pin_identical_to_alg2(self):
        # Observation for the experiment plan: Algorithm-2's effective class is UP->High,
        # DOWN->Low, KEEP/S0->unchanged, which is exactly the Main-1W rule.
        for s in ("H", "B_H", "L", "B_L"):
            for e in EVIDENCES:
                want = "High" if e == "UP" else "Low" if e == "DOWN" else EFFECTIVE_CLASS[s]
                self.assertEqual(EFFECTIVE_CLASS[MAIN_1W_TRANSITIONS[s, e]], want)
        for n in (4, 8):
            for seed in SEEDS:
                fires = lockstep([FaiAlg2SwitchModel(n, window=64),
                                  FaiVariantSwitchModel(n, window=64, high_quota=10, main_1w=True)],
                                 n, 3000, seed, hog=0)
                self.assertGreater(fires, 500)

    def test_main_1w_differs_from_main_four_state(self):
        # Hog source 0 at W=64: Main needs two DOWN windows (H->B_H->L), 1W one.
        n, w = 4, 64
        a, b = FaiMainSwitchModel(n, window=w), FaiVariantSwitchModel(n, window=w, main_1w=True)
        for m in (a, b):
            m.commit(rst_n=False)
        for k in range(w):
            valid = [True, False, False, False]
            for m in (a, b):
                m.commit(True, valid, [k, 0, 0, 0])
        self.assertEqual(a.classes()[0], "B_H")
        self.assertEqual(b.classes()[0], "L")
        self.assertEqual(a.window_log[-1].evidence[0], "DOWN")


class Tables(unittest.TestCase):
    def test_main_1w_table_literal(self):
        lit = {("H", "UP"): "H", ("H", "DOWN"): "L", ("H", "KEEP"): "H", ("H", "S0"): "H",
               ("L", "UP"): "H", ("L", "DOWN"): "L", ("L", "KEEP"): "L", ("L", "S0"): "L"}
        for key, val in lit.items():
            self.assertEqual(MAIN_1W_TRANSITIONS[key], val)
        # Accepted Main table is untouched by importing the variant module.
        self.assertEqual(MAIN_TRANSITIONS["H", "DOWN"], "B_H")

    def test_ctx_layout(self):
        self.assertEqual([variant_ctx_bits(q) for q in (5, 10, 20)], [4, 4, 5])
        for q in (5, 10, 20):
            for cls, quota in (("High", q), ("Low", 10)):
                for f in range(quota):
                    c = FaiCtx(cls, f)
                    self.assertEqual(variant_ctx_from_hw(variant_ctx_to_hw(c, q), q), c)
            with self.assertRaises(ValueError):
                variant_ctx_from_hw(q, q)  # High used == quota is not a valid context
        with self.assertRaises(ValueError):
            FaiVariantSwitchModel(4, window=64, high_quota=7)


def bliss_run(m, script):
    """script: list of (push dict, ready). Returns list of (fired source or None) per edge."""
    out = []
    for push, ready in script:
        n = m.n_src
        valid = [h in push for h in range(n)]
        desc = [push.get(h, 0) for h in range(n)]
        m.view(ready)
        out.append(m.commit(ready, valid, desc))
    return out


class BlissDirected(unittest.TestCase):
    def fresh(self, **kw):
        m = BlissSwitchModel(4, **kw)
        m.commit(rst_n=False)
        return m

    def test_sixth_consecutive_fire_blacklists(self):
        m = self.fresh()
        # Preload source 0 with 8 entries (ready low), then serve.
        bliss_run(m, [({0: i}, False) for i in range(8)])
        streaks = []
        for e in bliss_run(m, [({}, True)] * 6):
            streaks.append(e.streak_after)
        self.assertEqual(streaks, [0, 1, 2, 3, 4, 0])
        self.assertEqual(m.bliss_state()[0], (True, False, False, False))
        self.assertEqual(m.blacklist_events, 1)

    def test_change_resets_and_first_service_is_zero(self):
        m = self.fresh()
        bliss_run(m, [({0: 1, 1: 2}, False), ({0: 3}, False)])
        e = bliss_run(m, [({}, True)] * 3)
        self.assertEqual([x.fired for x in e], [0, 1, 0])  # FCFS ages: 0(e1) 1(e1) 0(e2)
        self.assertEqual([x.streak_after for x in e], [0, 0, 0])

    def test_stalls_and_idle_do_not_count(self):
        m = self.fresh()
        bliss_run(m, [({0: i}, False) for i in range(8)])
        bliss_run(m, [({}, True)] * 4)  # streak 3
        bliss_run(m, [({}, False)] * 20)  # stalls hold grant, no streak change
        self.assertEqual(m.bliss_state()[2], 3)
        e = bliss_run(m, [({}, True)] * 2)
        self.assertEqual([x.streak_after for x in e], [4, 0])
        self.assertTrue(m.blacklist[0])

    def test_nonblacklisted_first_then_fcfs_fallback(self):
        m = self.fresh()
        bliss_run(m, [({0: i}, False) for i in range(10)])
        bliss_run(m, [({}, True)] * 6)  # blacklist 0
        bliss_run(m, [({1: 99}, False)])  # stall: grant on 0 latches; younger source 1 lands
        e = bliss_run(m, [({}, True)] * 3)
        self.assertEqual(e[0].fired, 0)  # the held grant is not preempted by the blacklist
        self.assertEqual(e[1].fired, 1)  # non-blacklisted source beats older blacklisted heads
        self.assertEqual(e[2].fired, 0)  # only blacklisted heads left: FCFS fallback

    def test_clear_wins_over_simultaneous_blacklist(self):
        ci = 20
        m = self.fresh(clear_interval=ci)
        # Push at edges 1..12 (ready low), then serve 6 fires so the 6th lands on edge ci.
        bliss_run(m, [({0: i}, False) for i in range(ci - 6)])
        e = bliss_run(m, [({}, True)] * 6)
        self.assertEqual(e[-1].edge_index, ci)  # edge 0 was the reset edge
        self.assertTrue(e[-1].cleared)
        self.assertEqual(e[-1].blacklisted, 0)
        self.assertFalse(e[-1].blacklist_applied)
        self.assertEqual(m.bliss_state(), ((False,) * 4, 0, 0, 0))
        self.assertEqual(m.discarded_blacklists, 1)

    def test_clear_one_edge_later_keeps_nothing_and_earlier_applies(self):
        ci = 20
        m = self.fresh(clear_interval=ci)
        bliss_run(m, [({0: i}, False) for i in range(ci - 7)])
        e = bliss_run(m, [({}, True)] * 6)
        self.assertTrue(e[-1].blacklist_applied)  # edge ci-1
        self.assertTrue(m.blacklist[0])
        e = bliss_run(m, [({}, True)])
        self.assertTrue(e[0].cleared)
        self.assertFalse(m.blacklist[0])

    def test_reset_clears_state(self):
        m = self.fresh()
        bliss_run(m, [({0: i}, False) for i in range(8)])
        bliss_run(m, [({}, True)] * 6)
        m.commit(rst_n=False)
        self.assertEqual(m.bliss_state(), ((False,) * 4, None, 0, 0))
        self.assertEqual(m.nonempty_sources(), [])


class QuotaDirected(unittest.TestCase):
    def test_high_quota_contexts(self):
        for q in (5, 10, 20):
            m = FaiVariantSwitchModel(4, window=256, high_quota=q)
            m.commit(rst_n=False)
            for i in range(16):  # fill source 0 (all High, Low empty)
                m.commit(False, [True, False, False, False], [i, 0, 0, 0])
            for i in range(30):
                m.commit(True, [True, False, False, False], [100 + i, 0, 0, 0])
            # Only High work exists: every expired visit is a High visit of exactly q fires.
            ended = [r for r in m.visit_log if r.reason == "expired"]
            self.assertTrue(ended)
            self.assertTrue(all(r.cls == "High" and r.fires == q for r in ended), (q, ended))

    def test_low_quota_stays_ten_and_context_survives_stall(self):
        for q in (5, 20):
            n, w = 4, 64
            m = FaiVariantSwitchModel(n, window=w, high_quota=q, main_1w=True)
            m.commit(rst_n=False)
            for k in range(w):  # hog source 0 -> DOWN -> L immediately under 1W
                m.commit(True, [True, False, False, False], [k, 0, 0, 0])
            self.assertEqual(m.classes(), ("L", "H", "H", "H"))
            for i in range(16):  # fill source 0 (Low) only; High class empty
                m.commit(False, [True, False, False, False], [500 + i, 0, 0, 0])
            seen = []
            for i in range(40):
                ready = i % 3 != 2  # periodic stalls
                v = m.view(ready)
                if v.out_valid:
                    seen.append((variant_ctx_from_hw(v.grant_ctx, q), v.fire, v.held))
                m.commit(ready, [True, False, False, False], [900 + i, 0, 0, 0])
            fired = [c for c, f, _ in seen if f]
            self.assertTrue(all(c.cls == "Low" for c in fired))
            self.assertEqual(max(c.fires for c in fired), 9)
            # A stalled grant is replayed with the same context on the next (held) cycle.
            for (c0, f0, _), (c1, _, h1) in zip(seen, seen[1:]):
                if not f0:
                    self.assertTrue(h1)
                    self.assertEqual(c0, c1)


if __name__ == "__main__":
    unittest.main()
