"""Pure-pytest unit tests for the abstract FAI Algorithm-2 (POLICY=3) switch model
(specs/CXL_SPEC.md v1.0 section 8.6 plus shared 4, 5, 6, 8.1, 8.3-8.5; docs/phase-3-uarch/fai_alg2.md).

Every directed expectation is written by hand from spec 8.6: stable High + DOWN -> Buffer(p=Low),
stable Low + UP -> Buffer(p=High), any Buffer + UP -> stable High, any Buffer + DOWN -> stable Low,
KEEP and the zero-service window retain the current state (a Buffer keeps its target). A Buffer is
serviced immediately in its target class. Thresholds/visits/window/hold are the shared contract.
The table below is typed again independently of the model's copy. Nothing is derived from RTL.
"""

import itertools
import random
import sys
from collections import deque
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model import (  # noqa: E402
    ALG2_TRANSITIONS,
    EFFECTIVE_CLASS,
    MAIN_TRANSITIONS,
    FaiAlg2SwitchModel,
    FaiCandidate,
    FaiCtx,
    FaiMainSwitchModel,
    ctx_to_hw,
    pack_desc,
)

HI, LO = "High", "Low"
SH, SL, BPH, BPL = "STABLE_HIGH", "STABLE_LOW", "BUFFER_P_HIGH", "BUFFER_P_LOW"
EFF = {SH: HI, SL: LO, BPH: HI, BPL: LO}

# Spec 8.6, typed again here independently of the model's copy. S0 == the zero-service window.
SPEC_86 = {
    (SH, "UP"): SH, (SH, "DOWN"): BPL, (SH, "KEEP"): SH, (SH, "S0"): SH,
    (SL, "UP"): BPH, (SL, "DOWN"): SL, (SL, "KEEP"): SL, (SL, "S0"): SL,
    (BPH, "UP"): SH, (BPH, "DOWN"): SL, (BPH, "KEEP"): BPH, (BPH, "S0"): BPH,
    (BPL, "UP"): SH, (BPL, "DOWN"): SL, (BPL, "KEEP"): BPL, (BPL, "S0"): BPL,
}  # fmt: skip

_serial = itertools.count()


def d(src):
    i = next(_serial)
    return pack_desc(tag=(src << 24) | (i & 0xFFFFFF), addr=i & 0xFFFFFFFF, opcode=i & 1,
                     length=i & 0xFF, payload=(src * 7919 + i) & 0xFFFFFFFF)  # fmt: skip


def fresh(n=4, w=64, cls=FaiAlg2SwitchModel):
    m = cls(n, w)
    m.commit(rst_n=False)
    return m


def edge(m, push=(), ready=False, rst_n=True):
    push = set(push)
    n = m.n_src
    return m.commit(ready, [h in push for h in range(n)], [d(h) if h in push else 0 for h in range(n)], rst_n)


def stream(m, counts):
    """Push counts[h] descriptors per source with ready=1 until all fired (total+1 edges)."""
    rem = list(counts)
    total = sum(rem)
    fired = []
    while len(fired) < total:
        v = m.view(True)
        push = [h for h in range(m.n_src) if rem[h] and v.in_ready[h]]
        e = edge(m, push, ready=True)
        for h in push:
            rem[h] -= 1
        if e.fired is not None:
            fired.append(e.fired[0])
    return fired


def run_window(m, counts):
    """One complete window from position 0 with empty queues; returns the closing edge."""
    w, n = m.window, m.n_src
    assert m.window_state() == (0, (0,) * n, 0) and m.nonempty_sources() == [] and m.held is None
    stream(m, counts)
    while m.window_state()[0] < w - 1:
        assert not edge(m).closing
    e = edge(m)
    assert e.closing and m.window_state() == (0, (0,) * n, 0)
    return e


def serve(m, k):
    out = []
    for _ in range(k):
        assert m.view(True).out_valid
        e = edge(m, ready=True)
        out.append((e.fired[0], e.charged))
    return out


# Source-0 evidence realizations at N4 (4 fires when S > 0):
#   DOWN [4,0,0,0]: 4*4=16 > 4.  UP [0,4,0,0]: 40*0=0 < 12.  KEEP [1,1,1,1]: 40 >= 12, 4 == 4.
REALIZE_SRC0 = {"DOWN": [4, 0, 0, 0], "UP": [0, 4, 0, 0], "KEEP": [1, 1, 1, 1], "S0": [0, 0, 0, 0]}
PATH_TO = {SH: [], BPL: ["DOWN"], SL: ["DOWN", "DOWN"], BPH: ["DOWN", "DOWN", "UP"]}
ALL_16 = sorted(SPEC_86.items())


# ===== spec 8.6 table ==================================================================================


def test_transition_table_is_spec_8_6_literally():
    assert len(ALG2_TRANSITIONS) == 16 and ALG2_TRANSITIONS == SPEC_86
    assert FaiAlg2SwitchModel.EFFECTIVE == EFF and FaiAlg2SwitchModel.RESET_STATE == SH


def test_main_defaults_unchanged_by_the_hook():
    assert FaiMainSwitchModel.TRANSITIONS is MAIN_TRANSITIONS
    assert FaiMainSwitchModel.EFFECTIVE is EFFECTIVE_CLASS and FaiMainSwitchModel.RESET_STATE == "H"
    assert FaiMainSwitchModel.INTERPRETATION == "main" and FaiAlg2SwitchModel.INTERPRETATION == "alg2"
    # Algorithm-2 names never reuse Main's previous-priority buffer names.
    assert not set(EFF) & {"H", "B_H", "L", "B_L"}


@pytest.mark.parametrize("pair,expected", ALL_16, ids=[f"{s}-{e}" for (s, e), _ in ALL_16])
def test_table_entry_through_window_closings(pair, expected):
    state, evidence = pair
    m = fresh(4, 64)
    for ev in PATH_TO[state]:
        assert run_window(m, REALIZE_SRC0[ev]).evidence[0] == ev
    assert m.classes()[0] == state
    e = run_window(m, REALIZE_SRC0[evidence])
    assert e.evidence[0] == evidence
    assert e.old_classes[0] == state and e.new_classes[0] == expected
    assert m.classes()[0] == expected and m.effective_classes()[0] == EFF[expected]


def test_buffer_uses_target_class_immediately_unlike_main():
    """Identical trace: one DOWN window for src0. Main: B_H keeps effective High. Algorithm-2:
    BUFFER_P_LOW is effective Low at once, so the next selection already differs."""
    main, alg2 = fresh(4, 64, FaiMainSwitchModel), fresh(4, 64)
    for m in (main, alg2):
        run_window(m, REALIZE_SRC0["DOWN"])
    assert main.classes()[0] == "B_H" and main.effective_classes()[0] == HI
    assert alg2.classes() == (BPL, SH, SH, SH) and alg2.effective_classes() == (LO, HI, HI, HI)
    # Both visits are (Low, 0) after the High-only window. Push src0 and src1 on the same edge.
    for m in (main, alg2):
        assert m.visit_state() == (LO, 0)
        edge(m, [0, 1])
    # Main: Low turn empty -> High, tie src0 (ascending). Algorithm-2: src0 is Low -> (Low, 0).
    assert main.candidate() == FaiCandidate(True, 0, FaiCtx(HI, 0))
    assert alg2.candidate() == FaiCandidate(True, 0, FaiCtx(LO, 0))
    assert serve(alg2, 2) == [(0, FaiCtx(LO, 0)), (1, FaiCtx(HI, 0))]
    assert serve(main, 2) == [(0, FaiCtx(HI, 0)), (1, FaiCtx(HI, 1))]


@pytest.mark.parametrize("target", [BPL, BPH])
def test_keep_and_multiple_idle_windows_retain_buffer_target(target):
    m = fresh(4, 64)
    for ev in PATH_TO[target]:
        run_window(m, REALIZE_SRC0[ev])
    assert m.classes()[0] == target
    for ev in ("KEEP", "S0", "S0", "S0", "KEEP", "S0"):
        e = run_window(m, REALIZE_SRC0[ev])
        assert e.evidence[0] == ev and m.classes()[0] == target, f"{ev} must not cancel the Buffer"
        assert m.effective_classes()[0] == EFF[target]


def test_buffer_settles_on_next_up_or_down_from_either_target():
    m = fresh(4, 64)
    run_window(m, REALIZE_SRC0["DOWN"])  # SH -> BPL
    run_window(m, REALIZE_SRC0["UP"])  # BPL + UP -> SH (no second DOWN needed to leave the Buffer)
    assert m.classes()[0] == SH
    for ev, st in (("DOWN", BPL), ("DOWN", SL), ("UP", BPH), ("DOWN", SL), ("UP", BPH), ("UP", SH)):
        run_window(m, REALIZE_SRC0[ev])
        assert m.classes()[0] == st


def test_other_sources_in_the_same_window():
    # [0,4,0,0]: src0 UP, src1 DOWN, src2/src3 UP - classified in parallel from the closing counts.
    m = fresh(4, 64)
    e = run_window(m, [0, 4, 0, 0])
    assert e.evidence == ("UP", "DOWN", "UP", "UP") and m.classes() == (SH, BPL, SH, SH)


# ===== thresholds and S0 (shared spec 8.1) =============================================================

THRESHOLD_CASES = [
    # N4 S=40: B=3 -> 120 == 120 KEEP; B=10 -> 40 == 40 KEEP; B=11 -> 44 > 40 DOWN; B=16 DOWN.
    ("N4-S40-eq", 4, 64, [3, 10, 11, 16], ["KEEP", "KEEP", "DOWN", "DOWN"]),
    # N4 S=41: B=3 -> 120 < 123 UP; B=10 -> 40 <= 41 KEEP; B=0 UP; B=28 DOWN.
    ("N4-S41", 4, 64, [3, 10, 0, 28], ["UP", "KEEP", "UP", "DOWN"]),
    # N4 S=39: B=3 -> 120 >= 117 KEEP; B=10 -> 40 > 39 DOWN; B=0 UP; B=26 DOWN.
    ("N4-S39", 4, 64, [3, 10, 0, 26], ["KEEP", "DOWN", "UP", "DOWN"]),
    # N4 W256 S=200: B=14 -> 560 < 600 UP; B=15 -> 600 == 600 KEEP; B=50 -> 200 == 200 KEEP;
    #   B=121 -> 484 > 200 DOWN.
    ("N4-W256-S200", 4, 256, [14, 15, 50, 121], ["UP", "KEEP", "KEEP", "DOWN"]),
]  # fmt: skip
FROM_SH = {"UP": SH, "KEEP": SH, "DOWN": BPL}


@pytest.mark.parametrize("case", THRESHOLD_CASES, ids=[c[0] for c in THRESHOLD_CASES])
def test_threshold_boundaries_in_a_real_window(case):
    _, n, w, counts, expected = case
    m = fresh(n, w)
    e = run_window(m, counts)
    assert e.b_close == tuple(counts) and e.s_close == sum(counts)
    assert e.evidence == tuple(expected) and m.classes() == tuple(FROM_SH[x] for x in expected)


def test_closing_edge_fire_is_included():
    # B=[2,10,11,16] S=39 before the closing edge; src0 fires on it: B0=3, S=40 -> KEEP, KEEP, DOWN, DOWN.
    m = fresh(4, 64)
    stream(m, [2, 10, 11, 16])
    while m.window_state()[0] < 62:
        edge(m)
    edge(m, [0])
    e = edge(m, ready=True)
    assert e.closing and e.fired[0] == 0 and e.b_close == (3, 10, 11, 16) and e.s_close == 40
    assert e.evidence == ("KEEP", "KEEP", "DOWN", "DOWN") and m.classes() == (SH, SH, BPL, BPL)
    assert m.window_state() == (0, (0, 0, 0, 0), 0)


def test_stalled_backlog_window_is_zero_service_and_retains_buffer():
    m = fresh(4, 64)
    run_window(m, [0, 4, 0, 0])
    assert m.classes() == (SH, BPL, SH, SH)
    edge(m, [1])
    e = edge(m, ready=False)
    assert e.latched == (1, FaiCtx(LO, 0)), "src1 is offered in its Buffer target class Low"
    while m.window_state()[0] < 63:
        edge(m)
    e = edge(m)
    assert e.closing and e.s_close == 0 and e.evidence == ("S0",) * 4
    assert m.classes() == (SH, BPL, SH, SH) and m.held_grant() == (1, FaiCtx(LO, 0))


# ===== held grants across Buffer target changes (spec 4, 8.3, 8.4) =====================================


def test_held_grant_survives_buffer_target_changes_and_idle_windows():
    """src0 is BUFFER_P_LOW (effective Low). Its offer (Low, 0) stalls through three closings. Each
    stalled window has zero service (S0), which retains the Buffer; the held source/class/quota
    never changes and the eventual fire is charged to it."""
    m = fresh(4, 64)
    run_window(m, REALIZE_SRC0["DOWN"])  # src0 BPL
    assert m.visit_state() == (LO, 0)
    edge(m, [0])
    e = edge(m, ready=False)
    held = (0, FaiCtx(LO, 0))
    assert e.latched == held
    closings = []
    for _ in range(3 * 64):
        e = edge(m)
        assert m.held_grant() == held and e.fired is None
        if e.closing:
            closings.append(e)
            assert e.evidence == ("S0",) * 4 and m.classes()[0] == BPL
    assert len(closings) == 3
    e = edge(m, ready=True)
    assert e.fired[0] == 0 and e.charged == FaiCtx(LO, 0) and e.released
    assert m.service[0] == 5


def test_held_grant_charged_to_retained_class_after_target_flip():
    """Held (Low, 0) of src0 (BUFFER_P_LOW). The closing reclassifies src0 by UP to STABLE_HIGH.
    The held descriptor still fires with its retained Low context; later selections use High."""
    m = fresh(4, 64)
    run_window(m, REALIZE_SRC0["DOWN"])  # src0 BPL, visit (Low, 0)
    stream(m, [0, 4, 0, 0])  # src1 (High) 4 fires: positions 0..4
    assert m.window_state()[:2] == (5, (0, 4, 0, 0))
    edge(m, [0])
    e = edge(m, ready=False)
    assert e.latched == (0, FaiCtx(LO, 0))
    while m.window_state()[0] < 63:
        edge(m)
    e = edge(m)
    # B=[0,4,0,0]: src0 UP -> STABLE_HIGH; src1 DOWN -> BPL.
    assert e.closing and e.evidence == ("UP", "DOWN", "UP", "UP") and m.classes() == (SH, BPL, SH, SH)
    v = m.view(True)
    assert v.held and v.out_source == 0 and v.grant_ctx == ctx_to_hw(FaiCtx(LO, 0))
    # This cycle's (ignored) candidate: Low turn has no head (src1 BPL is empty) -> src0 (High, 0).
    assert m.candidate() == FaiCandidate(True, 0, FaiCtx(HI, 0))
    e = edge(m, [0], ready=True)
    assert e.fired[0] == 0 and e.charged == FaiCtx(LO, 0) and e.held_mismatch and e.released
    # Low class (src1 BPL) is empty post-edge; src0's replacement push is High -> Low visit empties.
    assert e.visit_event == "emptied" and m.visit_state() == (HI, 0)
    assert m.candidate() == FaiCandidate(True, 0, FaiCtx(HI, 0))


# ===== reset and validation (spec 5, 8.5) ==============================================================


def test_reset_initializes_all_stable_high_with_high_first():
    m = FaiAlg2SwitchModel(4, 64)
    assert m.classes() is None and m.candidate() == FaiCandidate(False, None, None)
    with pytest.raises(AssertionError):
        m.commit(True)
    m.commit(rst_n=False)
    assert m.classes() == (SH,) * 4 and m.visit_state() == (HI, 0) and m.window_state() == (0, (0,) * 4, 0)


def test_reset_mid_buffer_clears_pending_buffer():
    m = fresh(4, 64)
    run_window(m, REALIZE_SRC0["DOWN"])
    edge(m, [0, 1])
    edge(m, ready=False)
    assert m.classes()[0] == BPL and m.held is not None
    e = edge(m, [0, 1, 2, 3], ready=True, rst_n=False)
    assert e.reset and e.released and m.held is None and m.nonempty_sources() == []
    assert m.classes() == (SH,) * 4 and m.visit_state() == (HI, 0) and m.window_state() == (0, (0,) * 4, 0)


@pytest.mark.parametrize("w", [0, 1, 63, 65, 255, 257, 4_999_999, 5_000_001])
def test_unsupported_windows_rejected(w):
    with pytest.raises(ValueError):
        FaiAlg2SwitchModel(4, w)


def test_supported_windows_and_production_widths():
    assert (FaiAlg2SwitchModel(4, 64).idx_bits, FaiAlg2SwitchModel(4, 64).count_bits) == (6, 7)
    assert (FaiAlg2SwitchModel(4, 256).idx_bits, FaiAlg2SwitchModel(4, 256).count_bits) == (8, 9)
    m = FaiAlg2SwitchModel(4, 5_000_000)
    assert (m.idx_bits, m.count_bits) == (23, 23)
    with pytest.raises(ValueError):
        FaiAlg2SwitchModel(1, 64)


def test_production_window_short_run_is_fcfs_all_stable_high():
    m = fresh(4, 5_000_000)
    rng = random.Random("alg2-prod-short")
    order = []
    for _ in range(300):
        e = edge(m, [h for h in range(4) if rng.random() < 0.2], ready=rng.random() < 0.8)
        if e.fired is not None:
            order.append(e.fired[1].arrival)
            assert e.charged.cls == HI
    assert not m.window_log and m.classes() == (SH,) * 4 and order == sorted(order) and order


# ===== randomized self-consistency ======================================================================


@pytest.mark.parametrize("n,w,windows", [(4, 64, 500), (4, 256, 150)])
def test_randomized_long_run_self_consistency(n, w, windows):
    """Random arrivals/ready/resets against the test's own bookkeeping (window counter, B tally,
    evidence, independently typed spec 8.6 table, arrival order, class/visit choice). Requires all
    16 (state, evidence) pairs and every visit event."""
    rng = random.Random(f"fai-alg2-random-{n}-{w}")
    m = fresh(n, w)
    abs_edge = 1
    expect = [deque() for _ in range(n)]
    cls = [SH] * n
    tally = [0] * n
    since_close = 0
    rates = [0.0] * n
    ready_p = 1.0
    pairs, events = set(), set()
    for _ in range(windows * w):
        if since_close == 0:
            if rng.random() < 0.25:
                focus = rng.sample(range(n), rng.choice([1, 2]))
                rates = [rng.choice([0.3, 0.6, 0.9]) if h in focus else 0.0 for h in range(n)]
            else:
                for h in range(n):
                    if rng.random() < 0.4:
                        rates[h] = rng.choice([0.0, 0.0, 0.01, 0.03, 0.08, 0.2, 0.5, 0.9])
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
        e = edge(m, [h for h in range(n) if rng.random() < rates[h]], ready, not rst)
        this_edge = abs_edge
        abs_edge += 1
        if e.reset:
            expect = [deque() for _ in range(n)]
            cls, tally, since_close = [SH] * n, [0] * n, 0
            continue
        if e.fired is not None:
            g, ent = e.fired
            desc, arr = expect[g].popleft()
            assert ent.desc == desc and ent.arrival == arr
            c = e.charged
            if held_before is None:
                own = [h for h in heads if eff[h] == visit.cls]
                assert c == (visit if own else FaiCtx(LO if visit.cls == HI else HI, 0))
                assert min((heads[h], h) for h in heads if eff[h] == c.cls)[1] == g
            else:
                assert (g, c) == held_before
            tally[g] += 1
            events.add(e.visit_event)
            if e.relinquished is not None:
                events.add("relinquished")
        for h, p in enumerate(e.pushed):
            if p is not None:
                expect[h].append((p.desc, this_edge))
        since_close += 1
        assert e.closing == (since_close == w)
        if e.closing:
            s = sum(tally)
            ev = ["S0" if s == 0 else "UP" if 10 * n * b < 3 * s else "DOWN" if n * b > s else "KEEP"
                  for b in tally]  # fmt: skip
            assert e.evidence == tuple(ev)
            new = [SPEC_86[(cls[h], ev[h])] for h in range(n)]
            assert e.old_classes == tuple(cls) and e.new_classes == tuple(new)
            pairs |= {(cls[h], ev[h]) for h in range(n)}
            cls, tally, since_close = new, [0] * n, 0
        assert m.window_state() == (since_close, tuple(tally), sum(tally))
    missing = set(SPEC_86) - pairs
    assert not missing, f"transitions never exercised: {sorted(missing)}"
    assert {"continue", "expired", "emptied", "relinquished"} <= events
