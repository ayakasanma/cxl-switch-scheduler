"""Pure-pytest tests of the M5 FAI stress / production stimulus and statistics helpers
(sim/switch_top_fai/fai_stream.py).

They check: the bounded-memory statistics equal the list-based spec 10 estimators of
traffic_trace (mean, nearest-rank P99, min, max) exactly; the streaming producers present the oldest
pending descriptor until it is accepted; the production share design is consistent and keeps wide
margins to the spec 8.1 thresholds for N 4/8/16; the hand-derived production class sequence; the
realized per-window generation of the streaming production traffic produces the designed spec 8.1
evidence; determinism, unique tags and the directed boundary ready pattern; determinism and the
phase / stall / reset content of the window-scaled stress trace.
"""

import random
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))  # sim/common
sys.path.insert(0, str(_HERE.parents[2] / "switch_top_fai"))

import traffic_trace as tt  # noqa: E402
from fai_stream import (  # noqa: E402
    BOUNDARY_STALL,
    ProductionTraffic,
    StreamProducers,
    StreamStats,
    expected_classes,
    make_fai_stress_trace,
    production_kinds,
    production_shares,
)


def spec_evidence(n, b, s):
    """Spec 8.1, exact integers (written here independently of the harness)."""
    if s == 0:
        return "S0"
    if 10 * n * b < 3 * s:
        return "UP"
    if n * b > s:
        return "DOWN"
    return "KEEP"


def test_alg2_production_literal_trajectories():
    rows = expected_classes(4, 4, interpretation="alg2")
    assert list(map(list, zip(*rows))) == [
        ["BUFFER_P_LOW", "STABLE_LOW", "BUFFER_P_HIGH", "STABLE_HIGH"],
        ["BUFFER_P_LOW", "STABLE_HIGH", "BUFFER_P_LOW", "STABLE_LOW"],
        ["STABLE_HIGH", "STABLE_HIGH", "BUFFER_P_LOW", "BUFFER_P_LOW"],
        ["BUFFER_P_LOW", "STABLE_LOW", "STABLE_LOW", "BUFFER_P_HIGH"],
    ]
    assert expected_classes(4, 0, interpretation="alg2") == []
    assert expected_classes(4, 3, interpretation="alg2") == rows[:3]


@pytest.mark.parametrize("n,windows,interp", [(8, 4, "alg2"), (4, 5, "alg2"), (4, -1, "alg2"), (4, 4, "unknown")])
def test_production_interpretation_bounds(n, windows, interp):
    with pytest.raises(ValueError):
        expected_classes(n, windows, interpretation=interp)


def test_main_production_default_unchanged():
    assert expected_classes(4, 4) == expected_classes(4, 4, interpretation="main")


@pytest.mark.parametrize("size", [0, 1, 2, 99, 100, 101, 1000, 4321])
def test_stream_stats_equal_reference_estimators(size):
    rng = random.Random(size)
    samples = [rng.choice([1, 1, 2, 3, 7, 50, rng.randint(1, 5000)]) for _ in range(size)]
    st = StreamStats()
    for v in samples:
        st.add(v)
    d = st.as_dict()
    assert d["count"] == size
    assert d["mean"] == tt.mean(samples)
    assert d["p99_nearest_rank"] == tt.nearest_rank_p99(samples)
    assert d["min"] == (min(samples) if samples else None) and d["max"] == (max(samples) if samples else None)


def test_stream_producers_hold_oldest_until_accepted():
    p = StreamProducers(4)
    p.generate(0, [(1, 0xA), (1, 0xB), (3, 0xC)])
    assert p.offers() == {1: (0, 0xA), 3: (0, 0xC)}
    assert p.offers() == {1: (0, 0xA), 3: (0, 0xC)}, "offers are stable until accepted"
    assert p.accept(1, 2) == (0, 0xA)
    assert p.offers() == {1: (0, 0xB), 3: (0, 0xC)} and p.backlog() == 2
    with pytest.raises(AssertionError):
        p.accept(0, 3)
    p.generate(5, [(2, 0xD)])
    with pytest.raises(AssertionError):
        p.accept(2, 4)  # pushed before it was generated
    assert (p.generated, p.accepted, p.max_backlog) == (4, 1, 3)


@pytest.mark.parametrize("n", [4, 8, 16])
def test_production_share_design_margins(n):
    for wn in range(4):
        kinds = production_kinds(n, wn)
        shares = production_shares(n, wn)
        assert abs(sum(shares) - 1.0) < 1e-12
        for k, s in zip(kinds, shares):
            if k == "UP":
                assert s * n <= 0.3 * 0.6, f"UP share {s * n}/N too close to 0.3/N"
            elif k == "KEEP":
                assert 0.3 * 1.5 <= s * n <= 0.8, f"KEEP share {s * n}/N too close to a threshold"
            else:
                assert s * n >= 1.2, f"DOWN share {s * n}/N too close to 1/N"


def test_production_expected_classes_hand_derived():
    # Spec 8.2 by hand for groups g0..g3 (kinds D,D,U,U / D,U,D,D / U,K,D,K / D,D,K,U from H).
    assert expected_classes(4, 4) == [
        ["B_H", "B_H", "H", "B_H"],
        ["L", "H", "H", "L"],
        ["B_L", "B_H", "B_H", "L"],
        ["H", "L", "H", "B_L"],
    ]
    assert expected_classes(8, 4)[3] == ["H", "L", "H", "B_L"] * 2


@pytest.mark.parametrize("n", [4, 16])
def test_production_traffic_realized_evidence_and_ready_pattern(n):
    window = 100_000
    windows = 4
    a = ProductionTraffic(509, n, windows * window, window)
    b = ProductionTraffic(509, n, windows * window, window)
    tags = set()
    ready = bytearray(windows * window)
    for k in range(windows * window):
        ev, r = a.step(k)
        assert (ev, r) == b.step(k)
        ready[k] = r
        for _s, d in ev:
            tag = (d >> tt.TAG_LSB) & tt.TAG_MASK
            assert tag not in tags
            tags.add(tag)
    assert a.sha256 == b.sha256 and len(tags) == a.generated
    assert 0.5 < a.generated / (windows * window) < 0.6
    for wn in range(windows):
        gen = a.generated_per_window[wn]
        s = sum(gen)
        assert [spec_evidence(n, g, s) for g in gen] == production_kinds(n, wn), f"window {wn}: {gen}"
        end = (wn + 1) * window  # boundary wn+1 is just before cycle `end`
        stall = ready[end - BOUNDARY_STALL : end - 2]
        assert not any(stall)
        if (wn + 1) % 2 == 1:
            assert not any(ready[end - 2 : end]), "odd boundary: held across the closing edge"
            assert not any(ready[end : end + BOUNDARY_STALL]) or end == windows * window
        else:
            assert ready[end - 2] == ready[end - 1] == 1, "even boundary: the closing edge is ready"


def test_stress_trace_deterministic_window_scaled_content():
    w = 64
    t1 = make_fai_stress_trace(509, 8, 40_000, w)
    t2 = make_fai_stress_trace(509, 8, 40_000, w)
    assert t1.sha256 == t2.sha256 and t1.gen == t2.gen and t1.ready == t2.ready and t1.reset == t2.reset
    assert make_fai_stress_trace(510, 8, 40_000, w).sha256 != t1.sha256
    kinds = {kind for _s, _l, kind in t1.phases}
    assert {"skew", "uniform", "single", "flip", "idle", "stall", "saturate"} <= kinds
    tags = [(d >> tt.TAG_LSB) & tt.TAG_MASK for g in t1.gen for _s, d in g]
    assert len(tags) == len(set(tags)) == t1.generated > 0
    assert sum(t1.reset) > 0 and t1.reset[20_000] == 1, "random and directed resets"
    run = best = 0
    for r in t1.ready:
        run = run + 1 if not r else 0
        best = max(best, run)
    assert best >= 2 * w, "whole-window output stalls"
    s = t1.summary()
    assert s["sha256"] == t1.sha256 and s["window"] == w and s["generator"] == "cxl-fai-stress-trace-v2"
    # flip phases: the hot set changes exactly on absolute window multiples
    for start, length, kind in t1.phases:
        if kind != "flip" or start + length == t1.cycles:  # skip a phase truncated by the trace end
            continue
        toggles = list(range(((start + w - 1) // w) * w + w, start + length - w + 1, w))
        assert toggles, "flip phases span at least three windows"
        for b in toggles:  # both neighbouring windows lie completely inside the phase
            before = {s_ for kk in range(b - w, b) for s_, _d in t1.gen[kk]}
            after = {s_ for kk in range(b, b + w) for s_, _d in t1.gen[kk]}
            assert before and after and before != after, f"flip phase at {start}: no toggle at {b}"
