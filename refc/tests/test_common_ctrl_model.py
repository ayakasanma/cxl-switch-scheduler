"""Pure-pytest unit tests for the abstract common-framework model (specs/CXL_SPEC.md v1.0, 4-5).

Every expectation below is written out by hand from the spec contract; nothing is derived from
the model under test or from the RTL.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model import (  # noqa: E402
    NO_CANDIDATE,
    Candidate,
    CommonCtrlModel,
    Grant,
    OutHoldModel,
)

C = Candidate


def push(model, pushes, cand=NO_CANDIDATE, out_ready=False, ts=None):
    """One edge with the given {source: desc} offered on the inputs."""
    valid = [h in pushes for h in range(model.n_src)]
    desc = [pushes.get(h, 0) for h in range(model.n_src)]
    return model.commit(cand, out_ready, valid, desc, ts)


def load(model, contents):
    """Queue ``{source: [descs]}`` one entry per source per edge, with no candidate."""
    longest = max(len(v) for v in contents.values())
    for i in range(longest):
        edge = push(model, {h: v[i] for h, v in contents.items() if i < len(v)})
        assert all(edge.pushed[h] is not None for h, v in contents.items() if i < len(v))


# ----- OutHoldModel alone -------------------------------------------------------------------------


# Covers: SPEC §4 (fire = out_valid && out_ready; selection without acceptance is not service)
def test_hold_offer_truth_table_when_not_held():
    m = OutHoldModel(4, ctx_width=3)
    hv = [True, False, True, False]
    # (cand, out_ready) -> (out_valid, fire, stall, grant)
    rows = [
        (NO_CANDIDATE, False, (False, False, False, None)),
        (NO_CANDIDATE, True, (False, False, False, None)),
        (C(True, 1, 5), False, (False, False, False, Grant(1, 5))),  # empty source
        (C(True, 1, 5), True, (False, False, False, Grant(1, 5))),
        (C(True, 2, 6), False, (True, False, True, Grant(2, 6))),
        (C(True, 2, 6), True, (True, True, False, Grant(2, 6))),
        (C(False, 2, 6), True, (False, False, False, None)),  # invalid candidate on a valid head
    ]
    for cand, ready, (out_valid, fire, stall, grant) in rows:
        o = m.offer(cand, hv, ready)
        assert (o.out_valid, o.fire, o.stall, o.grant, o.held) == (out_valid, fire, stall, grant, False)
        assert o.pop_source == (grant.source if fire else None)
    assert m.held is None  # offer() never changes state


# Covers: SPEC §4 (stalled transfer retained; later candidates cannot preempt it)
def test_hold_latches_stalled_grant_and_ignores_candidate():
    m = OutHoldModel(4, ctx_width=3)
    hv = [True, True, True, True]
    edge = m.commit(C(True, 2, 6), hv, out_ready=False)
    assert edge.latched == Grant(2, 6) and edge.fired is None and not edge.released
    assert m.held == Grant(2, 6)
    for cand in (NO_CANDIDATE, C(True, 0, 1), C(True, 2, 0), C(True, 3, 7)):
        o = m.offer(cand, hv, False)
        assert (o.held, o.grant, o.out_valid, o.fire) == (True, Grant(2, 6), True, False)
        edge = m.commit(cand, hv, out_ready=False)
        assert edge.latched is None and edge.fired is None and not edge.released
        assert m.held == Grant(2, 6)
    # The fire carries the latched source and context, not the candidate of that cycle.
    o = m.offer(C(True, 0, 1), hv, True)
    assert o.fire and o.pop_source == 2
    edge = m.commit(C(True, 0, 1), hv, out_ready=True)
    assert edge.fired == Grant(2, 6) and edge.released
    assert m.held is None


# Covers: SPEC §4 (only fire is service), §5 (retain an offered transfer if stalled)
def test_hold_not_created_without_valid_head_or_candidate():
    m = OutHoldModel(4)
    assert m.commit(C(True, 1, 0), [True, False, True, True], False).latched is None
    assert m.commit(NO_CANDIDATE, [True] * 4, False).latched is None
    assert m.commit(C(True, 1, 1), [True] * 4, True).fired == Grant(1, 1)  # immediate fire: no hold
    assert m.held is None


# Covers: SPEC §5 (reset clears held-grant validity; output inactive during reset)
def test_hold_reset_clears_and_output_inactive_in_reset():
    m = OutHoldModel(8, ctx_width=2)
    hv = [True] * 8
    m.commit(C(True, 5, 3), hv, False)
    o = m.offer(C(True, 1, 0), hv, True, rst_n=False)
    assert (o.held, o.out_valid, o.fire, o.stall) == (True, False, False, False)
    edge = m.commit(C(True, 1, 0), hv, True, rst_n=False)
    assert edge.reset and edge.released and edge.fired is None and edge.latched is None
    assert m.held is None
    # Reset with nothing held, candidate valid and ready: nothing fires, nothing is latched.
    edge = m.commit(C(True, 1, 0), hv, False, rst_n=False)
    assert edge.reset and not edge.released and m.held is None


# Covers: SPEC §4-5 (hold released only by fire or reset) - documented behaviour of the block
# when an environment breaks the selected-head invariant.
def test_hold_survives_invalid_head_until_revalidated():
    m = OutHoldModel(4, ctx_width=4)
    m.commit(C(True, 3, 9), [True] * 4, False)
    gone = [True, True, True, False]
    for ready in (False, True, True):
        o = m.offer(C(True, 0, 2), gone, ready)
        assert (o.held, o.grant, o.out_valid, o.fire) == (True, Grant(3, 9), False, False)
        edge = m.commit(C(True, 0, 2), gone, ready)
        assert edge.fired is None and edge.latched is None and not edge.released
        assert m.held == Grant(3, 9)
    edge = m.commit(C(True, 0, 2), [True] * 4, True)
    assert edge.fired == Grant(3, 9) and edge.released and m.held is None


def test_hold_rejects_out_of_range_candidate():
    m = OutHoldModel(4, ctx_width=2)
    with pytest.raises(ValueError):
        m.offer(C(True, 4, 0), [True] * 4)
    with pytest.raises(ValueError):
        m.offer(C(True, 0, 4), [True] * 4)
    # An invalid candidate's fields are don't-care.
    assert not m.offer(C(False, 99, 99), [True] * 4).out_valid


# ----- CommonCtrlModel: FIFOs + hold ----------------------------------------------------------------


# Covers: SPEC §5 (reset state: empty, nothing held, handshakes inactive in reset)
def test_ctrl_reset_view():
    m = CommonCtrlModel(4, ctx_width=2)
    v = m.view(C(True, 0, 1), out_ready=True, rst_n=False)
    assert v.in_ready == (False,) * 4 and not v.out_valid and not v.fire and v.pop == (False,) * 4
    v = m.view(C(True, 0, 1), out_ready=True)
    assert v.in_ready == (True,) * 4 and v.count == (0,) * 4 and v.head_valid == (False,) * 4
    assert not v.out_valid and not v.held and v.out_source is None and v.out_desc is None


# Covers: SPEC §4 (no empty bypass: eligible no earlier than c+1; and eligible exactly at c+1)
def test_ctrl_push_is_eligible_exactly_next_cycle():
    m = CommonCtrlModel(4)
    cand = C(True, 2, 0)
    v = m.view(cand, out_ready=True)
    assert not v.out_valid and not v.fire
    edge = push(m, {2: 0xABC}, cand, out_ready=True)  # cycle c: accepted, cannot fire
    assert edge.pushed[2].desc == 0xABC and edge.fired is None and edge.latched is None
    v = m.view(cand, out_ready=True)  # cycle c+1
    assert v.out_valid and v.fire and v.out_source == 2 and v.out_desc == 0xABC
    assert v.pop == (False, False, True, False)
    edge = push(m, {}, cand, out_ready=True)
    assert edge.fired.source == 2 and edge.fired.entry.desc == 0xABC
    assert m.occupancy(2) == 0 and m.held is None


# Covers: SPEC §4 (only fire dequeues the selected request)
def test_ctrl_selection_without_ready_never_pops():
    m = CommonCtrlModel(4, ctx_width=2)
    load(m, {0: [10, 11], 1: [20]})
    for i in range(6):
        v = m.view(C(True, i % 2, 1), out_ready=False)
        assert v.out_valid and not v.fire and v.pop == (False,) * 4
        assert v.out_source == 0 and v.out_desc == 10  # first offer (source 0) is retained
        edge = push(m, {}, C(True, i % 2, 1), out_ready=False)
        assert edge.fired is None
        assert (m.occupancy(0), m.occupancy(1)) == (2, 1)
    assert m.delivered == 0


# Covers: SPEC §4 (stall stability; FIFOs keep accepting; later arrivals cannot preempt)
def test_ctrl_stall_is_stable_while_inputs_keep_arriving():
    m = CommonCtrlModel(4, ctx_width=3)
    load(m, {1: [100]})
    push(m, {}, C(True, 1, 5), out_ready=False)  # stalled offer of source 1, ctx 5
    assert m.held == Grant(1, 5)
    for i in range(20):
        cand = [NO_CANDIDATE, C(True, 0, 1), C(True, 3, 2), C(True, 1, 7)][i % 4]
        v = m.view(cand, out_ready=False)
        assert (v.held, v.out_valid, v.out_source, v.out_desc, v.grant_ctx) == (True, True, 1, 100, 5)
        push(m, {h: 1000 * (h + 1) + i for h in range(4)}, cand, out_ready=False)
    # Source 1 held one entry and accepted 15 more before filling; the others accepted 16.
    assert [m.occupancy(h) for h in range(4)] == [16, 16, 16, 16]
    v = m.view(C(True, 0, 1), out_ready=True)
    assert v.in_ready == (False,) * 4
    assert v.fire and v.out_source == 1 and v.out_desc == 100 and v.grant_ctx == 5
    assert v.pop == (False, True, False, False)
    edge = push(m, {1: 9999}, C(True, 0, 1), out_ready=True)
    # Full FIFO refuses the push even though its head fires on this edge (spec section 4).
    assert edge.pushed[1] is None and edge.fired.entry.desc == 100 and edge.fired.ctx == 5
    assert m.occupancy(1) == 15 and m.held is None
    assert m.view(NO_CANDIDATE).in_ready == (False, True, False, False)
    # Per-source order: the next head of source 1 is its first arrival during the stall.
    assert m.view(C(True, 1, 0)).out_desc == 2000


# Covers: SPEC §4 (simultaneous push and pop: occupancy unchanged, order preserved)
def test_ctrl_simultaneous_push_and_pop():
    m = CommonCtrlModel(4)
    load(m, {3: [1, 2, 3]})
    edge = push(m, {3: 4}, C(True, 3, 0), out_ready=True)
    assert edge.fired.entry.desc == 1 and edge.pushed[3].desc == 4
    assert m.occupancy(3) == 3
    got = []
    for _ in range(3):
        got.append(push(m, {}, C(True, 3, 0), out_ready=True).fired.entry.desc)
    assert got == [2, 3, 4] and m.occupancy(3) == 0


# Covers: SPEC §4 (pop only for the selected source), back-to-back throughput of one per cycle
def test_ctrl_back_to_back_fires_switching_source():
    m = CommonCtrlModel(4, ctx_width=2)
    load(m, {h: [10 * h + 1, 10 * h + 2] for h in range(4)})
    order = [3, 0, 2, 1, 1, 3, 0, 2]
    got = []
    for src in order:
        edge = push(m, {}, C(True, src, src), out_ready=True)
        assert edge.fired is not None and edge.fired.source == src and edge.fired.ctx == src
        got.append(edge.fired.entry.desc)
    assert got == [31, 1, 21, 11, 12, 32, 2, 22]
    assert m.delivered == 8 and m.nonempty_sources() == []


# Covers: SPEC §4 (candidate on an empty source / no candidate is not an offer)
def test_ctrl_empty_or_invalid_candidate_creates_no_hold():
    m = CommonCtrlModel(4)
    load(m, {0: [7]})
    for cand in (C(True, 1, 0), C(False, 0, 0), NO_CANDIDATE):
        for ready in (False, True):
            v = m.view(cand, out_ready=ready)
            assert not v.out_valid and not v.fire and not v.held
            edge = push(m, {}, cand, out_ready=ready)
            assert edge.fired is None and edge.latched is None
    # Candidate names source 2 on the very edge source 2 receives its first entry: not an offer.
    edge = push(m, {2: 55}, C(True, 2, 0), out_ready=False)
    assert edge.latched is None and m.held is None
    assert m.occupancy(0) == 1 and m.occupancy(2) == 1


# Covers: SPEC §5 (reset mid-stall clears the hold and the FIFOs; new epoch)
def test_ctrl_reset_during_hold_starts_fresh_epoch():
    m = CommonCtrlModel(4, ctx_width=2)
    load(m, {0: [1, 2], 2: [3]})
    push(m, {}, C(True, 2, 3), out_ready=False)
    assert m.held == Grant(2, 3) and m.epoch == 0
    v = m.view(C(True, 0, 0), out_ready=True, rst_n=False)
    assert v.held and not v.out_valid and v.count == (2, 0, 1, 0)  # nothing cleared before the edge
    edge = m.commit(C(True, 0, 0), True, [True] * 4, [9] * 4, rst_n=False)
    assert edge.reset and edge.released and edge.fired is None and edge.pushed == (None,) * 4
    assert m.epoch == 1 and m.held is None and m.nonempty_sources() == []
    v = m.view(C(True, 0, 0), out_ready=True)
    assert not v.out_valid and not v.held and v.in_ready == (True,) * 4


# Covers: SPEC §4 (pending transfer's context stays stable across later candidate changes)
def test_ctrl_context_latched_with_grant():
    m = CommonCtrlModel(8, ctx_width=4)
    load(m, {6: [0x60, 0x61]})
    push(m, {}, C(True, 6, 0xA), out_ready=False)
    for ctx in (0x0, 0x5, 0xF):
        assert m.view(C(True, 6, ctx)).grant_ctx == 0xA
        push(m, {}, C(True, 6, ctx), out_ready=False)
    edge = push(m, {}, C(True, 6, 0x5), out_ready=True)
    assert (edge.fired.source, edge.fired.ctx, edge.fired.entry.desc) == (6, 0xA, 0x60)
    # Next transfer of the same source is a new, unlocked selection with the current context.
    edge = push(m, {}, C(True, 6, 0x5), out_ready=True)
    assert (edge.fired.source, edge.fired.ctx, edge.fired.entry.desc) == (6, 0x5, 0x61)


# Covers: SPEC §6 (one arrival timestamp for all pushes of a cycle, stored per entry)
def test_ctrl_arrival_timestamp_follows_descriptor():
    m = CommonCtrlModel(4, ts_enabled=True)
    push(m, {0: 1, 3: 2}, ts=0xFFFFFFFF)
    push(m, {0: 3}, ts=0)
    v = m.view(C(True, 3, 0), out_ready=True)
    assert v.head_ts == (0xFFFFFFFF, None, None, 0xFFFFFFFF) and v.out_ts == 0xFFFFFFFF
    push(m, {}, C(True, 0, 0), out_ready=True)
    assert m.view(NO_CANDIDATE).head_ts[0] == 0
    without = CommonCtrlModel(4)
    push(without, {1: 5}, ts=123)
    assert without.view(NO_CANDIDATE).head_ts == (None,) * 4


# Covers: SPEC §4 (conservation and per-source order under arbitrary legal activity)
def test_ctrl_random_conservation_and_invariant():
    import random

    rng = random.Random(20261013)
    n = 8
    m = CommonCtrlModel(n, ctx_width=3)
    accepted = [[] for _ in range(n)]
    delivered = [[] for _ in range(n)]
    serial = 0
    for cycle in range(20000):
        rst_n = rng.random() > 0.002
        cand = C(rng.random() < 0.8, rng.randrange(n), rng.randrange(8))
        ready = rng.random() < 0.4
        valid = [rng.random() < 0.5 for _ in range(n)]
        descs = []
        for _ in range(n):
            serial += 1
            descs.append(serial)
        v = m.view(cand, ready, rst_n)
        if v.held:
            assert v.head_valid[m.held.source] and (v.out_valid or not rst_n)
        assert sum(v.pop) == int(v.fire)
        edge = m.commit(cand, ready, valid, descs, rst_n=rst_n)
        if edge.reset:
            accepted = [[] for _ in range(n)]
            delivered = [[] for _ in range(n)]
            continue
        for h in range(n):
            assert (edge.pushed[h] is not None) == (valid[h] and v.in_ready[h])
            if edge.pushed[h] is not None:
                accepted[h].append(descs[h])
        if edge.fired is not None:
            delivered[edge.fired.source].append(edge.fired.entry.desc)
        for h in range(n):
            assert delivered[h] == accepted[h][: len(delivered[h])]
            assert m.occupancy(h) == len(accepted[h]) - len(delivered[h]) <= 16
    assert sum(len(d) for d in delivered) > 100
