"""Pure-pytest unit tests for the abstract Main FAI (POLICY=2) switch model (specs/CXL_SPEC.md v1.0
sections 4, 5, 6, 8.1-8.5; docs/phase-3-uarch/fai_main.md sections 2-4).

Every directed expectation is written out by hand from the contract: the literal spec 8.2 table,
UP iff 10*N*B < 3*S, DOWN iff N*B > S, KEEP otherwise, S0 for S == 0, closing-edge fire included,
classes visible from the next cycle, 10/10 visits with post-edge class emptiness under the class map
of the cycle, fires charged to the retained context of the grant that actually fired. Threshold cases
list B/S values and the resulting evidence literally (the arithmetic is worked in the comments).
Nothing is derived from the RTL. The randomized test checks the model against bookkeeping kept by
the test itself (its own window counter, B tally, arrival order and transition table).
"""

import itertools
import random
import sys
from collections import deque
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model import (  # noqa: E402
    ALL_CONTEXTS,
    MAIN_TRANSITIONS,
    FaiCandidate,
    FaiCtx,
    FaiMainSwitchModel,
    check_threshold_operands,
    ctx_from_hw,
    ctx_to_hw,
    pack_desc,
    threshold_evidence,
    window_widths,
)

HI, LO = "High", "Low"
EFF = {"H": HI, "B_H": HI, "L": LO, "B_L": LO}

# Spec 8.2, typed again here independently of the model's copy.
SPEC_TABLE = {
    ("H", "UP"): "H", ("H", "DOWN"): "B_H", ("H", "KEEP"): "H", ("H", "S0"): "H",
    ("B_H", "UP"): "H", ("B_H", "DOWN"): "L", ("B_H", "KEEP"): "H", ("B_H", "S0"): "H",
    ("L", "UP"): "B_L", ("L", "DOWN"): "L", ("L", "KEEP"): "L", ("L", "S0"): "L",
    ("B_L", "UP"): "H", ("B_L", "DOWN"): "L", ("B_L", "KEEP"): "L", ("B_L", "S0"): "L",
}  # fmt: skip

_serial = itertools.count()


def d(src):
    """Distinct descriptor; the tag encodes the source and a global serial number."""
    i = next(_serial)
    return pack_desc(tag=(src << 24) | (i & 0xFFFFFF), addr=i & 0xFFFFFFFF, opcode=i & 1,
                     length=i & 0xFF, payload=(src * 7919 + i) & 0xFFFFFFFF)  # fmt: skip


def fresh(n=4, w=64):
    m = FaiMainSwitchModel(n, w)
    m.commit(rst_n=False)
    return m


def edge(m, push=(), ready=False, rst_n=True):
    push = set(push)
    n = m.n_src
    return m.commit(ready, [h in push for h in range(n)], [d(h) if h in push else 0 for h in range(n)], rst_n)


def stream(m, counts):
    """Push counts[h] descriptors per source (one per cycle while in_ready) with ready=1 every
    cycle until all of them fired. Fires every cycle after the first: total+1 edges."""
    rem = list(counts)
    total = sum(rem)
    fired = []
    edges = 0
    while len(fired) < total:
        v = m.view(True)
        push = [h for h in range(m.n_src) if rem[h] and v.in_ready[h]]
        e = edge(m, push, ready=True)
        for h in push:
            assert e.pushed[h] is not None
            rem[h] -= 1
        if e.fired is not None:
            fired.append(e.fired[0])
        edges += 1
    assert edges == (total + 1 if total else 0)
    return fired


def run_window(m, counts, close_push=(), close_ready=False):
    """One complete window from position 0 with empty queues: stream ``counts``, idle, push
    ``close_push`` on the edge at position W-2, then commit the closing edge (position W-1)."""
    w, n = m.window, m.n_src
    assert m.window_state() == (0, (0,) * n, 0)
    assert m.nonempty_sources() == [] and m.held is None
    total = sum(counts)
    stream(m, counts)
    pos = total + 1 if total else 0
    assert m.window_state() == (pos, tuple(counts), total)
    assert pos <= (w - 2 if close_push else w - 1)
    while pos < w - 1:
        e = edge(m, close_push if pos == w - 2 else (), ready=False)
        assert not e.closing and e.fired is None
        pos += 1
    assert m.window_state()[0] == w - 1
    e = edge(m, ready=close_ready)
    assert e.closing and e.window_pos == w - 1
    assert m.window_state() == (0, (0,) * n, 0)
    return e


def make_low(m, src):
    """Two windows in which only ``src`` fires (4 times): H -DOWN-> B_H -DOWN-> L; other sources
    see UP and stay H. Leaves position 0, empty queues and the visit (Low, 0)."""
    for expect in ("B_H", "L"):
        counts = [0] * m.n_src
        counts[src] = 4
        e = run_window(m, counts)
        assert e.evidence[src] == "DOWN" and m.classes()[src] == expect
    assert m.visit_state() == (LO, 0)


def serve(m, k, push_fn=None):
    """ready=1 for k cycles, each must fire; returns [(source, charged ctx, edge)]."""
    out = []
    for i in range(k):
        assert m.view(True).out_valid, "a fire was expected (work exists, ready=1)"
        e = edge(m, push_fn(i) if push_fn else (), ready=True)
        out.append((e.fired[0], e.charged, e))
    return out


# ===== spec 8.2 table and state machine =============================================================


def test_transition_table_is_spec_8_2_literally():
    assert len(MAIN_TRANSITIONS) == 16
    assert MAIN_TRANSITIONS == SPEC_TABLE


# Realizations of source-0 evidence at N4 (S>0 cases: 4 fires):
#   DOWN [4,0,0,0]: 4*4=16 > 4.       UP [0,4,0,0]: 40*0=0 < 3*4=12.
#   KEEP [1,1,1,1]: 40*1=40 >= 12 and 4*1=4 == 4 (not >).       S0: no fire in the window.
REALIZE_SRC0 = {"DOWN": [4, 0, 0, 0], "UP": [0, 4, 0, 0], "KEEP": [1, 1, 1, 1], "S0": [0, 0, 0, 0]}
PATH_TO = {"H": [], "B_H": ["DOWN"], "L": ["DOWN", "DOWN"], "B_L": ["DOWN", "DOWN", "UP"]}
ALL_16 = [
    ("H", "UP", "H"), ("H", "DOWN", "B_H"), ("H", "KEEP", "H"), ("H", "S0", "H"),
    ("B_H", "UP", "H"), ("B_H", "DOWN", "L"), ("B_H", "KEEP", "H"), ("B_H", "S0", "H"),
    ("L", "UP", "B_L"), ("L", "DOWN", "L"), ("L", "KEEP", "L"), ("L", "S0", "L"),
    ("B_L", "UP", "H"), ("B_L", "DOWN", "L"), ("B_L", "KEEP", "L"), ("B_L", "S0", "L"),
]  # fmt: skip


@pytest.mark.parametrize("state,evidence,expected", ALL_16, ids=[f"{s}-{e}" for s, e, _ in ALL_16])
def test_table_entry_through_window_closings(state, evidence, expected):
    m = fresh(4, 64)
    for ev in PATH_TO[state]:
        e = run_window(m, REALIZE_SRC0[ev])
        assert e.evidence[0] == ev
    assert m.classes()[0] == state
    e = run_window(m, REALIZE_SRC0[evidence])
    assert e.evidence[0] == evidence
    assert e.old_classes[0] == state and e.new_classes[0] == expected
    assert m.classes()[0] == expected and m.effective_classes()[0] == EFF[expected]
    assert m.window_log[-1].new_classes[0] == expected


HYSTERESIS = {
    "H-BH-L": [("DOWN", "B_H"), ("DOWN", "L")],
    "L-BL-H": [("DOWN", "B_H"), ("DOWN", "L"), ("UP", "B_L"), ("UP", "H")],
    "BH-cancel-KEEP": [("DOWN", "B_H"), ("KEEP", "H"), ("DOWN", "B_H"), ("DOWN", "L")],
    "BH-cancel-UP": [("DOWN", "B_H"), ("UP", "H"), ("DOWN", "B_H"), ("DOWN", "L")],
    "BH-cancel-S0": [("DOWN", "B_H"), ("S0", "H"), ("DOWN", "B_H"), ("DOWN", "L")],
    "BL-cancel-KEEP": [("DOWN", "B_H"), ("DOWN", "L"), ("UP", "B_L"), ("KEEP", "L"), ("UP", "B_L"), ("UP", "H")],
    "BL-cancel-DOWN": [("DOWN", "B_H"), ("DOWN", "L"), ("UP", "B_L"), ("DOWN", "L"), ("UP", "B_L"), ("UP", "H")],
    "BL-cancel-S0": [("DOWN", "B_H"), ("DOWN", "L"), ("UP", "B_L"), ("S0", "L"), ("UP", "B_L"), ("UP", "H")],
}  # fmt: skip


@pytest.mark.parametrize("name", list(HYSTERESIS))
def test_two_window_hysteresis_and_cancellation(name):
    """Two consecutive windows of the same evidence switch the effective class; KEEP, opposing
    evidence and an idle window cancel the pending change, which must then build up again."""
    m = fresh(4, 64)
    for ev, state in HYSTERESIS[name]:
        e = run_window(m, REALIZE_SRC0[ev])
        assert e.evidence[0] == ev
        assert m.classes()[0] == state, f"after {ev}"
        assert m.effective_classes()[0] == EFF[state]


def test_pending_buffer_keeps_previous_effective_class():
    m = fresh(4, 64)
    run_window(m, REALIZE_SRC0["DOWN"])
    assert m.classes() == ("B_H", "H", "H", "H") and m.effective_classes() == (HI, HI, HI, HI)
    run_window(m, REALIZE_SRC0["DOWN"])
    assert m.classes() == ("L", "H", "H", "H") and m.effective_classes() == (LO, HI, HI, HI)
    run_window(m, REALIZE_SRC0["UP"])  # [0,4,0,0]: src0 UP, src1 4*4=16 > 4 DOWN
    assert m.classes() == ("B_L", "B_H", "H", "H") and m.effective_classes() == (LO, HI, HI, HI)


# ===== thresholds (spec 8.1) ==========================================================================

# (id, N, W, B per source, expected evidence). S = sum(B). Arithmetic per source in comments.
THRESHOLD_CASES = [
    # N4: UP iff 40B < 3S, DOWN iff 4B > S.
    # S=40: B=3 -> 120 == 120 KEEP (UP equality); B=10 -> 40 == 40 KEEP (DOWN equality);
    #       B=11 -> 44 > 40 DOWN; B=16 -> 64 > 40 DOWN.
    ("N4-S40-eq", 4, 64, [3, 10, 11, 16], ["KEEP", "KEEP", "DOWN", "DOWN"]),
    # S=40: B=2 -> 80 < 120 UP (just below UP eq); B=4 -> 160 >= 120, 16 <= 40 KEEP;
    #       B=9 -> 36 <= 40 KEEP; B=25 -> 100 > 40 DOWN.
    ("N4-S40-below", 4, 64, [2, 4, 9, 25], ["UP", "KEEP", "KEEP", "DOWN"]),
    # S=41: B=3 -> 120 < 123 UP (S just above UP eq); B=10 -> 40 <= 41 KEEP; B=0 UP; B=28 DOWN.
    ("N4-S41", 4, 64, [3, 10, 0, 28], ["UP", "KEEP", "UP", "DOWN"]),
    # S=39: B=3 -> 120 >= 117 KEEP; B=10 -> 40 > 39 DOWN (S just below DOWN eq); B=0 UP; B=26 DOWN.
    ("N4-S39", 4, 64, [3, 10, 0, 26], ["KEEP", "DOWN", "UP", "DOWN"]),
    # N8: UP iff 80B < 3S, DOWN iff 8B > S.
    # S=80: B=3 -> 240 == 240 KEEP; B=10 -> 80 == 80 KEEP; B=11 -> 88 > 80 DOWN; B=2 -> 160 < 240
    #       UP; B=0 UP; B=18 -> 144 > 80 DOWN.
    ("N8-S80-eq", 8, 256, [3, 10, 11, 2, 0, 18, 18, 18], ["KEEP", "KEEP", "DOWN", "UP", "UP", "DOWN", "DOWN", "DOWN"]),
    # S=81: B=3 -> 240 < 243 UP; B=10 -> 80 <= 81 KEEP; B=68 DOWN.
    ("N8-S81", 8, 256, [3, 10, 0, 0, 0, 0, 0, 68], ["UP", "KEEP", "UP", "UP", "UP", "UP", "UP", "DOWN"]),
    # S=79: B=3 -> 240 >= 237 KEEP; B=10 -> 80 > 79 DOWN; B=66 DOWN.
    ("N8-S79", 8, 256, [3, 10, 0, 0, 0, 0, 0, 66], ["KEEP", "DOWN", "UP", "UP", "UP", "UP", "UP", "DOWN"]),
    # N16: UP iff 160B < 3S, DOWN iff 16B > S.
    # S=160: B=3 -> 480 == 480 KEEP; B=10 -> 160 == 160 KEEP; B=11 -> 176 > 160 DOWN; B=2 -> 320 <
    #        480 UP; B=0 UP; B=14 -> 224 > 160 DOWN; B=12 -> 192 > 160 DOWN.
    ("N16-S160-eq", 16, 256, [3, 10, 11, 2, 0, 14] + [12] * 10, ["KEEP", "KEEP", "DOWN", "UP", "UP"] + ["DOWN"] * 11),
    # S=161: B=3 -> 480 < 483 UP; B=10 -> 160 <= 161 KEEP; B=148 DOWN.
    ("N16-S161", 16, 256, [3, 10] + [0] * 13 + [148], ["UP", "KEEP"] + ["UP"] * 13 + ["DOWN"]),
    # S=159: B=3 -> 480 >= 477 KEEP; B=10 -> 160 > 159 DOWN; B=146 DOWN.
    ("N16-S159", 16, 256, [3, 10] + [0] * 13 + [146], ["KEEP", "DOWN"] + ["UP"] * 13 + ["DOWN"]),
]  # fmt: skip
FROM_H = {"UP": "H", "KEEP": "H", "DOWN": "B_H"}


@pytest.mark.parametrize("case", THRESHOLD_CASES, ids=[c[0] for c in THRESHOLD_CASES])
def test_threshold_boundaries_in_a_real_window(case):
    _, n, w, counts, expected = case
    assert len(counts) == n and len(expected) == n
    m = fresh(n, w)
    e = run_window(m, counts)
    assert e.b_close == tuple(counts) and e.s_close == sum(counts)
    assert e.evidence == tuple(expected)
    assert e.new_classes == tuple(FROM_H[x] for x in expected)
    assert m.classes() == e.new_classes


@pytest.mark.parametrize(
    "n,counts,expected",
    [
        # N4 S=12, B=6: 4*6=24 > 12 DOWN. Averaging over the 2 active sources only would give 2*6=12 KEEP.
        (4, [6, 6, 0, 0], ["DOWN", "DOWN", "UP", "UP"]),
        # A single active source always exceeds the all-source average: 4*5=20 > 5.
        (4, [5, 0, 0, 0], ["DOWN", "UP", "UP", "UP"]),
        # N8 S=16, B=8: 8*8=64 > 16 DOWN (active-only N=2: 16 == 16 KEEP).
        (8, [8, 8, 0, 0, 0, 0, 0, 0], ["DOWN", "DOWN"] + ["UP"] * 6),
    ],
)
def test_idle_sources_count_in_the_average(n, counts, expected):
    m = fresh(n, 64)
    e = run_window(m, counts)
    assert e.evidence == tuple(expected)


def test_up_and_down_mutually_exclusive_exhaustive():
    for n in (4, 8, 16):
        assert threshold_evidence(n, 0, 0) == "S0"
        for s in range(1, 200):
            for b in range(s + 1):
                up = 10 * n * b < 3 * s
                down = n * b > s
                assert not (up and down)
                assert threshold_evidence(n, b, s) == ("UP" if up else "DOWN" if down else "KEEP")
    with pytest.raises(ValueError):
        threshold_evidence(4, 3, 2)  # B > S is impossible window state


def test_s0_idle_window_and_stalled_backlog_window():
    m = fresh(4, 64)
    run_window(m, [0, 4, 0, 0])  # src1 4*4=16 > 4 DOWN -> B_H; others UP -> H
    assert m.classes() == ("H", "B_H", "H", "H")
    e = run_window(m, [0, 0, 0, 0])
    assert e.s_close == 0 and e.evidence == ("S0",) * 4
    assert m.classes() == ("H", "H", "H", "H"), "S0 cancels the pending B_H"
    run_window(m, [0, 4, 0, 0])
    assert m.classes() == ("H", "B_H", "H", "H")
    # A backlogged but completely stalled window is also a zero-service window.
    edge(m, [1])
    e = edge(m, ready=False)
    assert e.latched == (1, FaiCtx(HI, 0))
    for _ in range(61):
        e = edge(m, ready=False)
        assert not e.closing
    e = edge(m, ready=False)
    assert e.closing and e.s_close == 0 and e.evidence == ("S0",) * 4
    assert m.classes() == ("H", "H", "H", "H") and m.held == 1


# ===== widened arithmetic and representation bounds (spec 8.5) =======================================


def test_n16_w256_products_exceed_counter_width():
    """W=256 has 9-bit B/S counters. 10*N*B = 160*148 = 23680 needs 15 bits; truncated to 9 bits it
    would be 23680 mod 512 = 128 < 3*161 = 483 and wrongly read UP. The exact result is DOWN."""
    m = fresh(16, 256)
    assert (m.idx_bits, m.count_bits) == (8, 9)
    counts = [3, 10] + [0] * 13 + [148]
    assert 160 * 148 == 23680 and 23680 >= 1 << 9 and 23680 % 512 == 128 and 128 < 483
    e = run_window(m, counts)
    assert e.s_close == 161 and e.b_close[15] == 148
    assert e.evidence[15] == "DOWN" and e.new_classes[15] == "B_H"
    # B=10: 16*10 = 160 < 161 and 160*10 = 1600 >= 483 -> KEEP (1600 mod 512 = 64 < 483 would read UP).
    assert 1600 % 512 == 64
    assert e.evidence[1] == "KEEP"


# ARITHMETIC-ONLY (not window evidence): representative W=5,000,000 magnitudes through the pure helper.
PRODUCTION_ARITH = [
    (16, 90_000, 4_800_000, "KEEP"),  # 160*90000 = 14,400,000 == 3*4,800,000
    (16, 89_999, 4_800_000, "UP"),  # 14,399,840 < 14,400,000
    (16, 90_000, 4_800_001, "UP"),  # 14,400,000 < 14,400,003
    (16, 300_000, 4_800_000, "KEEP"),  # 16*300000 = 4,800,000 == S
    (16, 300_001, 4_800_000, "DOWN"),  # 4,800,016 > S
    (16, 300_000, 4_799_999, "DOWN"),  # 4,800,000 > 4,799,999
    (16, 5_000_000, 5_000_000, "DOWN"),  # max product 800,000,000
    (16, 0, 5_000_000, "UP"),
    (8, 187_500, 5_000_000, "KEEP"),  # 80*187500 = 15,000,000 == 3*5,000,000
    (8, 187_499, 5_000_000, "UP"),
    (8, 625_000, 5_000_000, "KEEP"),  # 8*625000 = 5,000,000 == S
    (8, 625_001, 5_000_000, "DOWN"),
    (4, 375_000, 5_000_000, "KEEP"),  # 40*375000 = 15,000,000 == 3*5,000,000
    (4, 374_999, 5_000_000, "UP"),
    (4, 1_250_000, 5_000_000, "KEEP"),  # 4*1,250,000 = 5,000,000 == S
    (4, 1_250_001, 5_000_000, "DOWN"),
]


@pytest.mark.parametrize("n,b,s,expected", PRODUCTION_ARITH)
def test_production_magnitudes_arithmetic_only(n, b, s, expected):
    check_threshold_operands(n, 5_000_000, b, s)  # fits 23-bit counters and 32-bit products
    assert threshold_evidence(n, b, s) == expected


def test_production_widths_and_bounds_literal():
    assert window_widths(64) == (6, 7)
    assert window_widths(256) == (8, 9)
    assert window_widths(5_000_000) == (23, 23)
    assert 10 * 16 * 5_000_000 == 800_000_000 < 1 << 30 < 1 << 32
    # The equality points above need more than the 23-bit counter width: widened arithmetic matters.
    assert 160 * 90_000 == 14_400_000 >= 1 << 23 and 3 * 4_800_000 >= 1 << 23


@pytest.mark.parametrize(
    "n,w,b,s",
    [
        (16, 64, 65, 65),  # S > W
        (16, 5_000_000, 3, 2),  # B > S
        (16, 5_000_000, 5_000_001, 5_000_001),  # S > W (and > 23 bits)
        (1000, 5_000_000, 5_000_000, 5_000_000),  # 10*N*B = 5e10 overflows 32 bits
    ],
)
def test_representation_bound_violations_are_caught(n, w, b, s):
    with pytest.raises(AssertionError):
        check_threshold_operands(n, w, b, s)


def test_model_state_corruption_is_caught_on_next_edge():
    m = fresh(4, 64)
    m.s += 1  # S != sum(B)
    with pytest.raises(AssertionError):
        edge(m)
    m = fresh(4, 64)
    m.b[0], m.s = 65, 65  # B = S > W
    with pytest.raises(AssertionError):
        edge(m)


# ===== window position, closing edge =================================================================


def test_window_index_counts_non_reset_edges_only():
    m = fresh(4, 64)
    for k in range(63):
        e = edge(m)
        assert e.window_pos == k and not e.closing
    e = edge(m)
    assert e.window_pos == 63 and e.closing and m.window_state()[0] == 0
    for _ in range(10):
        edge(m)
    assert m.window_state()[0] == 10
    e = edge(m, rst_n=False)
    assert e.reset and e.window_pos is None and m.window_state()[0] == 0
    for k in range(63):
        assert not edge(m).closing
    e = edge(m)
    assert e.closing, "the 64th non-reset edge after the reset closes the window"
    assert [(r.epoch, r.window) for r in m.window_log] == [(1, 0), (2, 0)]


def test_closing_edge_fire_is_included():
    # Same history, B = [2,10,11,16] (S=39) before the closing edge.
    # Without a closing fire: src0 40*2=80 < 117 UP; src1 4*10=40 > 39 DOWN; 44, 64 > 39 DOWN.
    m = fresh(4, 64)
    e = run_window(m, [2, 10, 11, 16])
    assert e.fired is None and e.b_close == (2, 10, 11, 16) and e.s_close == 39
    assert e.evidence == ("UP", "DOWN", "DOWN", "DOWN")
    assert m.classes() == ("H", "B_H", "B_H", "B_H")
    # With src0 firing on the closing edge: B0=3, S=40: 120 == 120 KEEP; src1 40 == 40 KEEP.
    m = fresh(4, 64)
    e = run_window(m, [2, 10, 11, 16], close_push=[0], close_ready=True)
    assert e.fired[0] == 0 and e.b_close == (3, 10, 11, 16) and e.s_close == 40
    assert e.evidence == ("KEEP", "KEEP", "DOWN", "DOWN")
    assert e.old_classes == ("H",) * 4 and m.classes() == ("H", "H", "B_H", "B_H")
    assert m.window_state() == (0, (0, 0, 0, 0), 0), "counts and position clear after closing"
    # The closing fire is still charged to its context: all-High traffic, Low empty -> (High, 0).
    assert e.charged == FaiCtx(HI, 0) and e.visit_event == "emptied" and m.visit_state() == (LO, 0)
    assert m.service == [3, 10, 11, 16]


def test_window_advances_through_long_stall():
    m = fresh(4, 64)
    edge(m, [1])
    closings = []
    for _ in range(100):
        e = edge(m, ready=False)
        assert e.fired is None and m.held_grant() == (1, FaiCtx(HI, 0))
        if e.closing:
            closings.append(e)
    # pre-edge positions 1..100; the edge at position 63 closes; 101 edges -> position 101-64 = 37
    assert len(closings) == 1 and closings[0].window_pos == 63
    assert closings[0].evidence == ("S0",) * 4
    assert m.window_state() == (37, (0, 0, 0, 0), 0)
    e = edge(m, ready=True)
    assert e.fired[0] == 1 and e.charged == FaiCtx(HI, 0)
    assert m.window_state() == (38, (0, 1, 0, 0), 1)


def test_closing_while_held_retains_context_then_new_classes():
    m = fresh(4, 64)
    run_window(m, [4, 0, 0, 0])
    assert m.classes() == ("B_H", "H", "H", "H") and m.visit_state() == (LO, 0)
    # Window B: 3 fires of src0 (High visit, emptied), then a grant of src0 is held to the closing.
    out = stream(m, [3, 0, 0, 0])
    assert out == [0, 0, 0] and m.visit_state() == (LO, 0)
    assert m.window_state() == (4, (3, 0, 0, 0), 3)
    edge(m, [0])  # position 4: nothing offered yet
    e = edge(m, [0, 1], ready=False)  # position 5: src0 offered (Low empty -> High, 0), stalls
    assert e.latched == (0, FaiCtx(HI, 0)) and m.held_grant() == (0, FaiCtx(HI, 0))
    for pos in range(6, 63):
        e = edge(m, ready=False)
        assert e.window_pos == pos and not e.closing and m.held_grant() == (0, FaiCtx(HI, 0))
        assert m.visit_state() == (LO, 0)
    e = edge(m, ready=False)  # closing edge, no fire: B=[3,0,0,0], S=3 -> src0 12 > 3 DOWN
    assert e.closing and e.fired is None and e.b_close == (3, 0, 0, 0) and e.s_close == 3
    assert e.evidence == ("DOWN", "UP", "UP", "UP") and m.classes() == ("L", "H", "H", "H")
    assert m.held_grant() == (0, FaiCtx(HI, 0)) and m.visit_state() == (LO, 0)
    # The held grant is not preempted and keeps its retained context; the ignored candidate differs.
    v = m.view(True)
    assert v.held and v.out_valid and v.out_source == 0 and v.grant_ctx == 0b00000
    assert m.candidate() == FaiCandidate(True, 0, FaiCtx(LO, 0))
    e = edge(m, ready=True)
    assert e.fired[0] == 0 and e.charged == FaiCtx(HI, 0) and e.held_mismatch and e.released
    # Charged to High: src1 (High under the current map) is nonempty -> the High visit continues.
    assert e.visit_event == "continue" and m.visit_state() == (HI, 1)
    assert m.window_state() == (1, (1, 0, 0, 0), 1)
    # Next unlocked selection uses the new classes: src1 (High) although src0 (now Low) ties older.
    assert m.candidate() == FaiCandidate(True, 1, FaiCtx(HI, 1))
    got = serve(m, 2)
    assert [(s, c) for s, c, _ in got] == [(1, FaiCtx(HI, 1)), (0, FaiCtx(LO, 0))]
    assert [(r.cls, r.fires, r.reason) for r in m.visit_log[-2:]] == [(HI, 2, "emptied"), (LO, 1, "emptied")]


def test_closing_edge_emptiness_uses_closing_cycle_class_map():
    """fai_main.md 4 'Derived convention'. src2 is B_H and is demoted to L by this closing; src1
    fires on the closing edge. Under the closing cycle's map src2 is High and still nonempty, so the
    High visit CONTINUES (High, 1). (Under the new map it would have 'emptied' to (Low, 0).) The next
    cycle relinquishes that visit to Low without a bubble."""
    m = fresh(4, 64)
    run_window(m, [0, 0, 4, 0])
    assert m.classes() == ("H", "H", "B_H", "H")
    stream(m, [0, 0, 4, 0])
    assert m.visit_state() == (LO, 0) and m.window_state()[0] == 5
    for _ in range(5, 62):
        edge(m)
    edge(m, [1, 2])  # position 62
    assert m.window_state()[0] == 63
    # Closing cycle: old map (src2 still effective High). Turn Low has nothing -> High, tie -> src1.
    assert m.effective_classes() == (HI, HI, HI, HI)
    assert m.candidate() == FaiCandidate(True, 1, FaiCtx(HI, 0))
    e = edge(m, ready=True)
    assert e.closing and e.fired[0] == 1 and e.charged == FaiCtx(HI, 0)
    assert e.post_occupancy == (0, 0, 1, 0)
    assert e.visit_event == "continue" and e.visit_after == FaiCtx(HI, 1) and m.visit_state() == (HI, 1)
    # B_close [0,1,4,0], S 5: src0 0 < 15 UP; src1 40 >= 15, 4 <= 5 KEEP; src2 16 > 5 DOWN; src3 UP.
    assert e.b_close == (0, 1, 4, 0) and e.s_close == 5
    assert e.evidence == ("UP", "KEEP", "DOWN", "UP") and e.new_classes == ("H", "H", "L", "H")
    # Next cycle: no High head under the new map -> Low (src2) opens a fresh visit, no bubble.
    assert m.candidate() == FaiCandidate(True, 2, FaiCtx(LO, 0))
    assert m.view(True).fire
    e = edge(m, ready=True)
    assert e.fired[0] == 2 and e.charged == FaiCtx(LO, 0) and e.relinquished == FaiCtx(HI, 1)
    assert e.visit_event == "emptied" and m.visit_state() == (HI, 0)
    assert [(r.cls, r.fires, r.reason) for r in m.visit_log[-2:]] == [(HI, 1, "relinquished"), (LO, 1, "emptied")]


# ===== visits and quotas (spec 8.3, Q2) ===============================================================


def test_alternation_10_10_with_both_classes_backlogged():
    m = fresh(4, 256)
    make_low(m, 0)  # src0 Low, src1/src2 High; visit (Low, 0)
    seq, ctxs, events = [], [], []
    for i in range(41):
        v = m.view(True)
        e = edge(m, [h for h in (0, 1, 2) if v.in_ready[h]], ready=True)
        if i == 0:
            assert e.fired is None
            continue
        seq.append(e.fired[0])
        ctxs.append(e.charged)
        events.append(e.visit_event)
    # High visits are FCFS between src1/src2 (same push edges: ascending ID, then the older head).
    assert seq == [0] * 10 + [1, 2] * 5 + [0] * 10 + [1, 2] * 5
    assert ctxs == ([FaiCtx(LO, k) for k in range(10)] + [FaiCtx(HI, k) for k in range(10)]) * 2
    assert events == (["continue"] * 9 + ["expired"]) * 4
    assert m.visit_state() == (LO, 0)


def test_quota_expiry_with_replacement_push():
    m = fresh(4, 256)
    make_low(m, 0)
    for i in range(12):  # src0 (Low) x12, src1 (High) x1; src0's first offer stalls and is held
        edge(m, [0] + ([1] if i == 0 else []), ready=False)
    assert m.held_grant() == (0, FaiCtx(LO, 0))
    got = serve(m, 10)
    assert [s for s, _, _ in got] == [0] * 10 and got[-1][2].visit_event == "expired"
    assert m.visit_state() == (HI, 0) and m.occupancy(0) == 2
    got = serve(m, 10, push_fn=lambda i: [1])  # every src1 fire gets a same-edge replacement
    assert [s for s, _, _ in got] == [1] * 10
    assert [e.post_occupancy[1] for _, _, e in got] == [1] * 10
    assert [e.visit_event for _, _, e in got] == ["continue"] * 9 + ["expired"]
    assert m.visit_state() == (LO, 0) and m.occupancy(1) == 1
    assert m.candidate() == FaiCandidate(True, 0, FaiCtx(LO, 0))


def test_empty_class_relinquishes_quota_no_banking():
    m = fresh(4, 256)
    make_low(m, 0)
    for i in range(16):  # src1 (High) x16, src0 (Low) x4
        edge(m, [1] + ([0] if i < 4 else []), ready=False)
    got = serve(m, 32, push_fn=lambda i: [0] if 4 <= i < 16 else [])
    # Low 4 (emptied, 6 unused are lost), High 10, Low gets a FRESH 10 (not 16) out of 12 queued,
    # High 6 (emptied), Low the remaining 2.
    assert [s for s, _, _ in got] == [0] * 4 + [1] * 10 + [0] * 10 + [1] * 6 + [0] * 2
    assert [(r.cls, r.fires, r.reason) for r in m.visit_log[-5:]] == [
        (LO, 4, "emptied"), (HI, 10, "expired"), (LO, 10, "expired"), (HI, 6, "emptied"), (LO, 2, "emptied")]  # fmt: skip
    assert m.nonempty_sources() == [] and m.visit_state() == (HI, 0)


def test_sole_nonempty_class_renews_without_bubble():
    m = fresh(4, 256)  # all High, Low class empty
    got = []
    for i in range(31):
        if i:
            assert m.view(True).fire, "no bubble when only High has work"
        e = edge(m, [1], ready=True)
        if i:
            got.append(e.charged)
    assert got == [FaiCtx(HI, k) for k in range(10)] * 3
    assert [(r.cls, r.fires, r.reason) for r in m.visit_log] == [(HI, 10, "expired")] * 3
    assert m.visit_state() == (LO, 0)
    # Low-only variant.
    m = fresh(4, 256)
    make_low(m, 0)
    base = len(m.visit_log)
    got = [c for _, c, _ in serve_after_push(m, 0, 25)]
    assert got == [FaiCtx(LO, k) for k in range(10)] * 2 + [FaiCtx(LO, k) for k in range(5)]
    assert [(r.cls, r.fires, r.reason) for r in m.visit_log[base:]] == [(LO, 10, "expired")] * 2
    assert m.visit_state() == (LO, 5)


def serve_after_push(m, src, k):
    edge(m, [src])
    return serve(m, k, push_fn=lambda i: [src])


def test_both_empty_retains_the_turn_without_consumption():
    m = fresh(4, 64)
    make_low(m, 0)
    edge(m, [0])
    e = edge(m, ready=True)
    assert e.charged == FaiCtx(LO, 0) and e.visit_event == "emptied" and m.visit_state() == (HI, 0)
    closings = []
    for _ in range(70):
        e = edge(m, ready=True)
        assert e.fired is None and m.visit_state() == (HI, 0)
        if e.closing:
            closings.append(e)
    # The window [B0=1, S=1]: src0 4 > 1 DOWN (stays L), others UP. The visit is untouched.
    assert len(closings) == 1 and closings[0].evidence == ("DOWN", "UP", "UP", "UP")
    assert m.classes() == ("L", "H", "H", "H")
    edge(m, [0, 1])  # same push edge: plain FCFS would pick src0, but the retained turn is High
    assert m.candidate() == FaiCandidate(True, 1, FaiCtx(HI, 0))
    assert [(s, c) for s, c, _ in serve(m, 2)] == [(1, FaiCtx(HI, 0)), (0, FaiCtx(LO, 0))]


def test_window_closing_never_resets_visit_or_fires():
    m = fresh(4, 64)
    edge(m, [1], ready=True)
    for k in range(3):
        e = edge(m, [1], ready=True)
        assert e.charged == FaiCtx(HI, k) and e.visit_event == "continue"
    e = edge(m, [1], ready=False)  # position 4
    assert e.latched == (1, FaiCtx(HI, 3)) and m.visit_state() == (HI, 3)
    for _ in range(5, 63):
        edge(m, ready=False)
    e = edge(m, ready=False)
    assert e.closing and e.b_close == (0, 3, 0, 0) and e.s_close == 3
    assert e.evidence == ("UP", "DOWN", "UP", "UP") and m.classes() == ("H", "B_H", "H", "H")
    assert m.visit_state() == (HI, 3), "a closing does not reset the open visit"
    got = serve(m, 2)
    assert [c for _, c, _ in got] == [FaiCtx(HI, 3), FaiCtx(HI, 4)]
    assert [e.visit_event for _, _, e in got] == ["continue", "emptied"]


def test_held_context_differs_from_changed_candidate_without_reclassification():
    m = fresh(4, 64)
    make_low(m, 0)  # visit (Low, 0)
    edge(m, [1])
    e = edge(m, [1], ready=False)  # turn Low is empty -> High src1 (High, 0) offered and stalls
    assert e.latched == (1, FaiCtx(HI, 0))
    edge(m, [0], ready=False)  # a Low arrival: the turn class now has work
    assert m.candidate() == FaiCandidate(True, 0, FaiCtx(LO, 0))
    v = m.view(True)
    assert v.held and v.out_source == 1 and v.grant_ctx == ctx_to_hw(FaiCtx(HI, 0)) == 0
    e = edge(m, ready=True)
    assert e.fired[0] == 1 and e.charged == FaiCtx(HI, 0) and e.held_mismatch
    assert e.candidate == FaiCandidate(True, 0, FaiCtx(LO, 0))
    assert e.visit_event == "continue" and m.visit_state() == (HI, 1)
    assert [(s, c) for s, c, _ in serve(m, 2)] == [(1, FaiCtx(HI, 1)), (0, FaiCtx(LO, 0))]


# ===== FCFS inside a class (spec 6) ===================================================================


def test_fcfs_tie_ascending_source_and_older_head_wins():
    m = fresh(4, 64)
    edge(m, [3, 1, 2])
    assert [s for s, _, _ in serve(m, 3)] == [1, 2, 3]
    edge(m, [3])
    edge(m, [0], ready=False)  # src3 offered and held; src0 arrives one edge later
    assert m.held == 3
    assert m.candidate().source == 3, "the older head (src3) wins over the lower ID"
    assert [s for s, _, _ in serve(m, 2)] == [3, 0]


def test_fcfs_wrap_via_counter_deposit():
    m = fresh(4, 64)
    m.deposit_counter(0xFFFFFFFE)
    edge(m, [3])  # stored 0xFFFFFFFE
    edge(m, [2])  # 0xFFFFFFFF (src3 now offered and held)
    edge(m, [1])  # 0x00000000
    edge(m, [0])  # 0x00000001
    assert [m.queue(h)[0].ts32 for h in range(4)] == [1, 0, 0xFFFFFFFF, 0xFFFFFFFE]
    assert m.view(True).out_ts == 0xFFFFFFFE
    assert [s for s, _, _ in serve(m, 4)] == [3, 2, 1, 0]


def test_deposit_restrictions():
    m = fresh()
    edge(m, [0])
    with pytest.raises(ValueError):
        m.deposit_counter(5)
    with pytest.raises(ValueError):
        FaiMainSwitchModel(4, 64).deposit_counter(5)
    with pytest.raises(ValueError):
        fresh().deposit_counter(1 << 32)


def test_class_precedence_over_age_and_id():
    m = fresh(4, 64)
    make_low(m, 0)
    edge(m, [0])
    e = edge(m, ready=True)
    assert e.charged == FaiCtx(LO, 0) and m.visit_state() == (HI, 0)
    edge(m, [0, 3])  # edge A: Low src0 and High src3 tie
    assert m.candidate() == FaiCandidate(True, 3, FaiCtx(HI, 0)), "visit class beats a lower ID"
    e = edge(m, [2], ready=True)  # edge B: src3 fires; src2's same-edge push keeps High live
    assert e.fired[0] == 3 and e.post_occupancy == (1, 0, 1, 0) and e.visit_event == "continue"
    assert m.candidate() == FaiCandidate(True, 2, FaiCtx(HI, 1)), "visit class beats an older head"
    assert [s for s, _, _ in serve(m, 2)] == [2, 0]


def test_environment_age_assumption_checked():
    m = fresh()
    edge(m, [0])
    m.edge_index += 1 << 31
    with pytest.raises(AssertionError):
        m.view(True)
    with pytest.raises(AssertionError):
        edge(m, ready=True)


# ===== reset (spec 5) =================================================================================


def test_reset_mid_window_mid_visit_mid_hold_clears_everything():
    m = fresh(4, 64)
    make_low(m, 0)
    edge(m, [0, 1])
    e = edge(m, [0], ready=True)
    assert e.charged == FaiCtx(LO, 0) and m.visit_state() == (LO, 1)
    e = edge(m, [2], ready=False)
    assert e.latched == (0, FaiCtx(LO, 1))
    assert m.classes() == ("L", "H", "H", "H") and m.window_state() == (3, (1, 0, 0, 0), 1)
    epoch = m.epoch
    e = edge(m, [0, 1, 2, 3], ready=True, rst_n=False)
    assert e.reset and e.released and e.fired is None and e.pushed == (None,) * 4
    assert m.classes() == ("H",) * 4 and m.effective_classes() == (HI,) * 4
    assert m.visit_state() == (HI, 0) and m.window_state() == (0, (0, 0, 0, 0), 0)
    assert m.held is None and m.nonempty_sources() == [] and m.counter() == 0
    assert m.service == [0, 0, 0, 0] and m.epoch == epoch + 1
    assert not m.view(True).out_valid
    e = run_window(m, [0, 0, 0, 0])
    assert e.evidence == ("S0",) * 4 and m.classes() == ("H",) * 4


def test_reset_on_the_closing_cycle_suppresses_classification():
    m = fresh(4, 64)
    stream(m, [4, 0, 0, 0])
    for _ in range(5, 63):
        edge(m)
    assert m.window_state() == (63, (4, 0, 0, 0), 4)
    e = edge(m, rst_n=False)
    assert e.reset and not e.closing and m.window_log == []
    assert m.classes() == ("H",) * 4 and m.window_state() == (0, (0, 0, 0, 0), 0)


def test_state_unknown_before_first_reset():
    m = FaiMainSwitchModel(4, 64)
    assert m.classes() is None and m.window_state() is None and m.visit_state() is None
    assert m.candidate() == FaiCandidate(False, None, None) and m.counter() is None
    with pytest.raises(AssertionError):
        m.commit(True)
    m.commit(rst_n=False)
    assert m.classes() == ("H",) * 4 and m.visit_state() == (HI, 0)
    assert m.window_state() == (0, (0, 0, 0, 0), 0) and m.counter() == 0


@pytest.mark.parametrize("w", [0, 1, 63, 65, 128, 255, 257, 4_999_999, 5_000_001])
def test_unsupported_windows_rejected(w):
    with pytest.raises(ValueError):
        FaiMainSwitchModel(4, w)


def test_supported_windows_and_minimum_sources():
    assert (FaiMainSwitchModel(4, 64).idx_bits, FaiMainSwitchModel(4, 64).count_bits) == (6, 7)
    assert (FaiMainSwitchModel(8, 256).idx_bits, FaiMainSwitchModel(8, 256).count_bits) == (8, 9)
    m = FaiMainSwitchModel(16, 5_000_000)
    assert (m.idx_bits, m.count_bits) == (23, 23)
    with pytest.raises(ValueError):
        FaiMainSwitchModel(1, 64)


def test_production_window_short_run_behaves_as_fcfs_all_high():
    """fai_main.md 5: before any W=5,000,000 closing every source is H and every visit High."""
    m = fresh(16, 5_000_000)
    rng = random.Random("fai-prod-short")
    order = []
    for _ in range(300):
        push = [h for h in range(16) if rng.random() < 0.08]
        e = edge(m, push, ready=rng.random() < 0.8)
        if e.fired is not None:
            order.append(e.fired[1].arrival)
            assert e.charged.cls == HI
    assert not m.window_log and m.window_state()[0] == 300 and m.classes() == ("H",) * 16
    assert m.window_state()[2] == len(order) > 0
    assert order == sorted(order), "all-High service is plain FCFS (non-decreasing arrival)"
    assert all(r.cls == HI for r in m.visit_log)


# ===== RTL-facing context encoding ====================================================================


def test_hw_context_mapping():
    assert ctx_to_hw(FaiCtx(HI, 0)) == 0b00000
    assert ctx_to_hw(FaiCtx(HI, 1)) == 0b00001
    assert ctx_to_hw(FaiCtx(HI, 9)) == 0b01001
    assert ctx_to_hw(FaiCtx(LO, 0)) == 0b10000
    assert ctx_to_hw(FaiCtx(LO, 5)) == 0b10101
    assert ctx_to_hw(FaiCtx(LO, 9)) == 0b11001
    assert len(ALL_CONTEXTS) == 20
    for c in ALL_CONTEXTS:
        assert ctx_from_hw(ctx_to_hw(c)) == c
    for bad in list(range(10, 16)) + list(range(26, 32)) + [32, -1]:
        with pytest.raises(ValueError):
            ctx_from_hw(bad)
    for bad in (FaiCtx(HI, 10), FaiCtx(LO, -1), FaiCtx("Mid", 0)):
        with pytest.raises(ValueError):
            ctx_to_hw(bad)


# ===== common-framework sanity ========================================================================


def test_full_plus_pop_refusal_and_no_bypass():
    m = fresh(4, 64)
    e = edge(m, [1], ready=True)
    assert e.fired is None, "no bypass: a push is not offered in its own cycle"
    v = m.view(True)
    assert v.out_valid and v.out_source == 1
    serve(m, 1)
    for _ in range(16):
        edge(m, [0], ready=False)
    assert m.occupancy(0) == 16 and not m.view(True).in_ready[0]
    e = edge(m, [0], ready=True)
    assert e.fired[0] == 0 and e.pushed[0] is None, "a full FIFO refuses a push on its pop edge"
    assert m.occupancy(0) == 15 and m.view(True).in_ready[0]


# ===== randomized long run ============================================================================


@pytest.mark.parametrize(
    "n,w,windows", [(4, 64, 400), (8, 64, 400), (16, 64, 400), (4, 256, 120), (8, 256, 120), (16, 256, 120)]
)
def test_randomized_long_run_self_consistency(n, w, windows):
    """Random arrivals/ready/resets against bookkeeping kept by the test: its own window counter,
    B tally, evidence, literal transition table, arrival order, per-source FIFO order and the
    class/visit choice. Fails unless every class state and all 16 (state, evidence) transitions
    and every visit event were exercised."""
    rng = random.Random(f"fai-main-random-{n}-{w}")
    m = fresh(n, w)
    abs_edge = 1  # the fresh() reset was edge 0
    expect = [deque() for _ in range(n)]  # (desc, arrival)
    cls = ["H"] * n
    tally = [0] * n
    since_close = 0
    rates = [0.0] * n
    ready_p = 1.0
    pairs, events = set(), set()
    rate_choices = [0.0, 0.0, 0.01, 0.03, 0.08, 0.2, 0.5, 0.9]
    for _ in range(windows * w):
        if since_close == 0:  # new window: re-draw some sources' offered load and the ready level
            if rng.random() < 0.2:
                # Focus phase: one or two active sources (sole-source classes, class flips under load).
                focus = rng.sample(range(n), rng.choice([1, 2]))
                rates = [rng.choice([0.3, 0.6, 0.9]) if h in focus else 0.0 for h in range(n)]
            else:
                for h in range(n):
                    if rng.random() < 0.4:
                        rates[h] = rng.choice(rate_choices) * 4 / n
            ready_p = rng.choice([0.0, 0.3, 0.7, 1.0, 1.0])
        rst = rng.random() < 0.0002
        ready = rng.random() < ready_p
        v = m.view(ready, not rst)
        eff = [EFF[c] for c in cls]
        assert m.effective_classes() == tuple(eff)
        heads = {h: expect[h][0][1] for h in range(n) if expect[h]}
        visit = m.visit_state()
        held_before = m.held_grant()
        if not rst and ready and heads:
            assert v.fire, "bubble while work exists"
        push = [h for h in range(n) if rng.random() < rates[h]]
        e = edge(m, push, ready, not rst)
        this_edge = abs_edge
        abs_edge += 1
        assert e.edge_index == this_edge
        if e.reset:
            expect = [deque() for _ in range(n)]
            cls, tally, since_close = ["H"] * n, [0] * n, 0
            continue
        if e.fired is not None:
            g, ent = e.fired
            desc, arr = expect[g].popleft()
            assert ent.desc == desc and ent.arrival == arr, "FIFO order / integrity"
            c = e.charged
            assert 0 <= c.fires <= 9
            if held_before is None:
                # Unlocked: visit class if it has a head (context = open visit), else the other
                # class with a fresh quota; FCFS-oldest (arrival, source) inside that class.
                own = [h for h in heads if eff[h] == visit.cls]
                if own:
                    assert c == visit
                else:
                    assert c == FaiCtx(LO if visit.cls == HI else HI, 0)
                in_cls = [(heads[h], h) for h in heads if eff[h] == c.cls]
                assert min(in_cls)[1] == g
            else:
                assert (g, c) == held_before
            tally[g] += 1
            events.add(e.visit_event)
            if e.relinquished is not None:
                events.add("relinquished")
        else:
            assert e.visit_after == visit, "no fire -> visit unchanged"
        for h, p in enumerate(e.pushed):
            if p is not None:
                assert p.arrival == this_edge
                expect[h].append((p.desc, p.arrival))
        since_close += 1
        assert e.closing == (since_close == w)
        if e.closing:
            s = sum(tally)
            ev = ["S0" if s == 0 else "UP" if 10 * n * b < 3 * s else "DOWN" if n * b > s else "KEEP"
                  for b in tally]  # fmt: skip
            assert e.b_close == tuple(tally) and e.s_close == s and e.evidence == tuple(ev)
            new = [SPEC_TABLE[(cls[h], ev[h])] for h in range(n)]
            assert e.old_classes == tuple(cls) and e.new_classes == tuple(new)
            pairs |= {(cls[h], ev[h]) for h in range(n)}
            cls, tally, since_close = new, [0] * n, 0
        assert m.window_state() == (since_close, tuple(tally), sum(tally))
        for h in range(n):
            assert m.occupancy(h) == len(expect[h])
    missing = set(SPEC_TABLE) - pairs
    assert not missing, f"transitions never exercised: {sorted(missing)}"
    assert {"continue", "expired", "emptied", "relinquished"} <= events
