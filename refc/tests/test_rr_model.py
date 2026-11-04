"""Pure-pytest unit tests for the abstract Round Robin switch model (specs/CXL_SPEC.md v1.0
sections 4, 5, 7; DECISIONS D07, D25, D26, D32).

Every directed expectation is written out by hand from the spec contract: polling starts at
source 0 after reset, the first nonempty source circularly from the polling position is offered,
a turn allows at most Q successful fires, the post-edge occupancy (beginning count + accepted push
- pop) decides whether the turn continues, quantum expiry always advances, stalls and idle cycles
charge nothing, a held grant's fire is charged to the source that actually fired. Nothing is
derived from the RTL. The randomized tests compare the model with a separately written
closed-form round enumeration and with model-free bounds.
"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model import RrSwitchModel, pack_desc  # noqa: E402

N = 4


def fresh(n=N, q=10):
    m = RrSwitchModel(n, q)
    m.commit(rst_n=False)
    return m


def d(src, i, length=0):
    """Distinct descriptor: tag encodes (source, index)."""
    return pack_desc(tag=(src << 16) | i, addr=0x1000 + i, opcode=i & 1, length=length, payload=src * 1000 + i)


def edge(m, pushes=None, ready=False, rst_n=True):
    pushes = pushes or {}
    valid = [h in pushes for h in range(m.n_src)]
    desc = [pushes.get(h, 0) for h in range(m.n_src)]
    return m.commit(ready, valid, desc, rst_n)


def load(m, counts, salt=0):
    """Push counts[h] descriptors into each source, one per cycle per source, ready=0."""
    for i in range(max(counts.values())):
        edge(m, {h: d(h, salt + i) for h, c in counts.items() if i < c})


def serve(m, k):
    """ready=1 for k cycles; each must fire. Returns the fired source sequence."""
    out = []
    for _ in range(k):
        v = m.view(True)
        assert v.out_valid, "a fire was expected (work exists, ready=1)"
        e = edge(m, ready=True)
        out.append(e.fired[0])
    return out


# ----- reset / initial state --------------------------------------------------------------------


def test_reset_polls_from_source0_and_offers_nothing_when_empty():
    m = fresh()
    assert m.polling_state() == (0, 0) and m.turn is None
    v = m.view(True)
    assert not v.out_valid and m.candidate().valid is False
    for _ in range(5):  # all-empty cycles keep the polling position, charge nothing
        e = edge(m, ready=True)
        assert e.fired is None and m.polling_state() == (0, 0)


def test_non_reset_edge_before_first_reset_is_rejected():
    m = RrSwitchModel(N)
    with pytest.raises(AssertionError):
        m.commit(True)


@pytest.mark.parametrize("n,q", [(1, 10), (4, 0)])
def test_invalid_parameters(n, q):
    with pytest.raises(ValueError):
        RrSwitchModel(n, q)


def test_same_cycle_arrivals_served_from_source0_in_circular_order():
    m = fresh()
    e = edge(m, {h: d(h, 0) for h in range(N)}, ready=True)
    assert e.fired is None and m.view(True).out_source == 0
    assert serve(m, N) == [0, 1, 2, 3]
    assert m.polling_state() == (0, 0)  # source 3 emptied -> poll wraps to 0


# ----- exact successful-fire quota ----------------------------------------------------------------


def test_quantum10_exact_fires_then_advance():
    m = fresh()
    load(m, {0: 12, 1: 12})
    order = serve(m, 24)
    assert order == [0] * 10 + [1] * 10 + [0] * 2 + [1] * 2
    assert [(r.source, r.fires, r.reason) for r in m.turn_log] == [
        (0, 10, "expired"), (1, 10, "expired"), (0, 2, "emptied"), (1, 2, "emptied")]  # fmt: skip


def test_quota_charged_only_on_fire_not_on_stall_or_idle():
    m = fresh()
    load(m, {0: 12, 2: 3})
    rng = random.Random(7)
    fires = 0
    order = []
    while fires < 15:
        ready = rng.random() < 0.4
        before = m.polling_state()
        e = edge(m, ready=ready)
        if e.fired is None:
            assert m.polling_state() == before, "a non-fire cycle changed the turn state"
        else:
            fires += 1
            order.append(e.fired[0])
    assert order == [0] * 10 + [2] * 3 + [0] * 2


def test_nine_fires_keep_turn_tenth_fire_expires():
    m = fresh()
    load(m, {1: 16, 3: 1})
    for k in range(1, 10):
        e = edge(m, ready=True)
        assert e.fired[0] == 1 and e.turn_event == "continue" and m.polling_state() == (1, k)
    e = edge(m, ready=True)
    assert e.fired[0] == 1 and e.turn_event == "expired" and m.polling_state() == (2, 0)
    assert m.candidate().source == 3  # 2 is empty: skipped, no bubble


def test_length_field_never_changes_the_charge():
    m = fresh()
    for i in range(12):
        edge(m, {0: d(0, i, length=255 if i % 2 else 0), 1: d(1, i, length=1)})
    assert serve(m, 12) == [0] * 10 + [1] * 2


# ----- empty skipping, circular order, no bubbles ------------------------------------------------


def test_empty_sources_skipped_without_bubble():
    m = fresh(8)
    edge(m, {6: d(6, 0)})
    v = m.view(True)
    assert v.out_valid and v.out_source == 6  # first cycle the head is eligible
    e = edge(m, ready=True)
    assert e.fired[0] == 6 and e.turn_event == "emptied" and m.polling_state() == (7, 0)
    load(m, {2: 1, 5: 1})
    assert serve(m, 2) == [2, 5]  # from 7: 7,0,1 empty -> 2, then 3,4 empty -> 5


def test_circular_wrap_from_last_source():
    m = fresh()
    load(m, {3: 11, 0: 1, 2: 1})
    assert serve(m, 13) == [0, 2] + [3] * 10 + [3]
    # after 0 (emptied) poll=1 -> 2; 2 emptied poll=3 -> 3 ten fires expire -> poll 0, only 3 left


def test_turn_order_resumes_after_pointer_not_from_zero():
    m = fresh()
    load(m, {1: 3, 2: 3})
    assert serve(m, 3) == [1, 1, 1] and m.polling_state() == (2, 0)
    edge(m, {0: d(0, 50), 1: d(1, 50)})  # arrivals at 0 and 1 while 2 is next
    assert serve(m, 5) == [2, 2, 2, 0, 1]


# ----- post-edge occupancy: replacement, refusal, expiry ------------------------------------------


def test_final_head_fire_with_replacement_keeps_turn():
    m = fresh()
    load(m, {0: 1, 1: 1})
    e = edge(m, {0: d(0, 9)}, ready=True)  # last head of 0 fires, replacement pushed same edge
    assert e.fired[0] == 0 and e.post_occupancy == 1 and e.turn_event == "continue"
    assert m.polling_state() == (0, 1) and m.candidate().source == 0


def test_final_head_fire_without_replacement_advances():
    m = fresh()
    load(m, {0: 1, 1: 1})
    e = edge(m, ready=True)
    assert e.post_occupancy == 0 and e.turn_event == "emptied" and m.polling_state() == (1, 0)
    assert m.turn_log[-1].reason == "emptied" and m.turn_log[-1].fires == 1


def test_streaming_single_entry_source_keeps_turn_until_expiry_then_advances_with_replacement():
    m = fresh()
    load(m, {0: 1, 1: 1})
    for i in range(10):
        e = edge(m, {0: d(0, 100 + i)}, ready=True)
        assert e.fired[0] == 0 and e.post_occupancy == 1
    assert e.turn_event == "expired" and m.turn_log[-1].replaced
    assert m.polling_state() == (1, 0) and m.occupancy(0) == 1  # expiry advanced despite nonempty
    assert serve(m, 2) == [1, 0]


def test_full_plus_pop_refuses_push_and_turn_continues():
    m = fresh()
    load(m, {0: 16, 1: 1})
    assert not m.view(True).in_ready[0]
    e = edge(m, {0: d(0, 99)}, ready=True)
    assert e.fired[0] == 0 and e.pushed[0] is None, "a full FIFO refuses a push on its pop edge"
    assert e.post_occupancy == 15 and m.polling_state() == (0, 1)
    assert m.view(True).in_ready[0]
    e = edge(m, {0: d(0, 99)}, ready=True)
    assert e.pushed[0] is not None and e.post_occupancy == 15


# ----- held grants and candidate changes -----------------------------------------------------------


def test_held_grant_fire_charged_to_actual_source_when_candidate_changed():
    m = fresh()
    load(m, {2: 3})
    v = m.view(False)
    assert v.out_source == 2 and not v.fire
    edge(m, ready=False)  # stall: grant 2 becomes held
    assert m.held == 2
    edge(m, {0: d(0, 1), 1: d(1, 1)}, ready=False)  # arrivals at sources polled before 2
    # no turn open: the (ignored) candidate is now the first nonempty source from poll 0
    assert m.polling_state() == (0, 0) and m.nonempty_sources() == [0, 1, 2]
    assert m.candidate().source == 0
    v = m.view(True)
    assert v.held and v.out_source == 2, "held grant must not be preempted"
    e = edge(m, ready=True)
    assert e.fired[0] == 2 and e.held_mismatch and e.candidate.source == 0
    assert m.polling_state() == (2, 1), "fire charged to the held source, which keeps its turn"
    assert serve(m, 4) == [2, 2, 0, 1]


def test_held_expiring_fire_with_changed_candidate_advances_after_held_source():
    m = fresh(4, 1)
    load(m, {3: 2})
    edge(m, ready=False)  # grant 3 held
    edge(m, {1: d(1, 1)}, ready=False)
    assert m.candidate().source == 1 and m.held == 3
    e = edge(m, ready=True)
    assert e.fired[0] == 3 and e.turn_event == "expired" and m.polling_state() == (0, 0)
    assert serve(m, 2) == [1, 3]


def test_stall_keeps_turn_context():
    m = fresh()
    load(m, {0: 5, 1: 5})
    serve(m, 3)
    assert m.polling_state() == (0, 3)
    for _ in range(50):
        e = edge(m, {1: d(1, 77)} if m.view().in_ready[1] else None, ready=False)
        assert e.fired is None and m.polling_state() == (0, 3) and m.held == 0
    assert serve(m, 2) == [0, 0]


# ----- one / all / none active, renewal ------------------------------------------------------------


def test_single_source_renews_quota_without_bubble():
    m = fresh()
    load(m, {1: 16})
    out = []
    for i in range(30):
        e = edge(m, {1: d(1, 200 + i)}, ready=True)
        out.append(e.fired[0])
    assert out == [1] * 30
    assert [r.fires for r in m.turn_log] == [10, 10, 10]
    assert all(r.reason == "expired" for r in m.turn_log)


def test_all_sources_active_rotate_in_quanta():
    m = fresh()
    load(m, {h: 16 for h in range(N)})
    assert serve(m, 64) == [0] * 10 + [1] * 10 + [2] * 10 + [3] * 10 + [0] * 6 + [1] * 6 + [2] * 6 + [3] * 6


def test_all_empty_retains_open_position():
    m = fresh()
    load(m, {2: 1})
    serve(m, 1)
    assert m.polling_state() == (3, 0)
    for _ in range(20):
        edge(m, ready=True)
    assert m.polling_state() == (3, 0)
    load(m, {1: 1, 3: 1})
    assert serve(m, 2) == [3, 1]


# ----- quantum 1 (supplementary) -------------------------------------------------------------------


def test_quantum1_every_fire_advances():
    m = fresh(4, 1)
    load(m, {0: 3, 2: 3})
    assert serve(m, 6) == [0, 2, 0, 2, 0, 2]
    assert all(r.fires == 1 for r in m.turn_log)


def test_quantum1_single_source_continuous():
    m = fresh(4, 1)
    load(m, {3: 4})
    assert serve(m, 4) == [3, 3, 3, 3]
    # with Q=1 every turn reaches its quantum at its first fire (expiry, also when it empties)
    assert [r.reason for r in m.turn_log] == ["expired"] * 4


# ----- reset mid-turn / mid-hold --------------------------------------------------------------------


def test_reset_mid_turn_restarts_at_source0():
    m = fresh()
    load(m, {2: 8, 0: 1})
    serve(m, 1)  # source 0 (poll 0)
    serve(m, 4)
    assert m.polling_state() == (2, 4)
    e = edge(m, {h: d(h, 9) for h in range(N)}, ready=True, rst_n=False)
    assert e.reset and e.fired is None and e.pushed == (None,) * N
    assert m.polling_state() == (0, 0) and m.nonempty_sources() == [] and m.held is None
    load(m, {3: 1, 1: 1})
    assert serve(m, 2) == [1, 3]


def test_reset_mid_hold_drops_grant():
    m = fresh()
    load(m, {1: 2})
    edge(m, ready=False)
    assert m.held == 1
    edge(m, rst_n=False)
    assert m.held is None and m.polling_state() == (0, 0)
    assert not m.view(True).out_valid


# ----- no bypass -------------------------------------------------------------------------------------


def test_push_not_offered_in_its_own_cycle():
    m = fresh()
    e = edge(m, {1: d(1, 0)}, ready=True)
    assert e.fired is None
    assert m.view(True).out_source == 1


# ----- randomized: closed-form enumeration and model-free bounds ------------------------------------


def closed_form_order(lengths, q):
    """Fire order for preloaded queues, ready always 1, no further arrivals: visit sources
    circularly from 0, each nonempty one serves min(q, remaining) per visit."""
    rem = list(lengths)
    out = []
    s = 0
    while sum(rem):
        if rem[s]:
            k = min(q, rem[s])
            out += [s] * k
            rem[s] -= k
        s = (s + 1) % len(rem)
    return out


@pytest.mark.parametrize("n,q", [(4, 10), (8, 10), (16, 10), (4, 1), (16, 1), (8, 3)])
def test_preloaded_drain_matches_closed_form(n, q):
    rng = random.Random(f"rr-closed-{n}-{q}")
    for _ in range(25):
        lengths = [rng.choice([0, 0, 1, 2, 5, 9, 10, 11, 16]) for _ in range(n)]
        m = fresh(n, q)
        if any(lengths):
            load(m, {h: c for h, c in enumerate(lengths) if c})
        got = serve(m, sum(lengths))
        assert got == closed_form_order(lengths, q), f"lengths {lengths}"
        assert not m.view(True).out_valid


@pytest.mark.parametrize("n,q", [(4, 10), (8, 10), (16, 10), (4, 1), (8, 1), (4, 3)])
def test_random_traffic_bounds(n, q):
    """Random arrivals/ready/resets. Model-free properties: (a) a source never fires more than q
    times in a row while another source stays nonempty from the first fire of the run onwards,
    (b) a continuously nonempty source waits for at most (n-1)*q fires of other sources,
    (c) no bubble: ready=1 and any nonempty source -> fire, (d) conservation and FIFO order."""
    rng = random.Random(f"rr-random-{n}-{q}")
    m = fresh(n, q)
    serial = 0
    expect = [[] for _ in range(n)]
    run_src, run_len, run_start = None, 0, 0
    nonempty_since = [None] * n
    others_since = [0] * n
    for cyc in range(6000):
        rst = rng.random() < 0.002
        ready = rng.random() < 0.7
        pushes = {}
        for h in range(n):
            if rng.random() < 1.2 / n:
                pushes[h] = d(h % 256, serial & 0xFFFF)
                serial += 1
        v = m.view(ready, not rst)
        occ = [m.occupancy(h) for h in range(n)]
        for h in range(n):
            if occ[h] == 0:
                nonempty_since[h] = None
                others_since[h] = 0
            elif nonempty_since[h] is None:
                nonempty_since[h] = cyc
        if not rst and ready and any(occ):
            assert v.fire, "bubble while work exists"
        if not rst and v.out_valid and not v.held and run_src == v.out_source and run_len >= q:
            others = [t for t in range(n) if t != run_src and nonempty_since[t] is not None
                      and nonempty_since[t] <= run_start]  # fmt: skip
            assert not others, f"source {run_src} offered beyond {q} fires while {others} waited"
        e = m.commit(ready, [h in pushes for h in range(n)], [pushes.get(h, 0) for h in range(n)], not rst)
        if e.reset:
            expect = [[] for _ in range(n)]
            run_src, run_len = None, 0
            nonempty_since = [None] * n
            others_since = [0] * n
            continue
        if e.fired is not None:
            g, desc = e.fired
            assert expect[g].pop(0) == desc, "FIFO order / integrity"
            if g == run_src:
                run_len += 1
            else:
                run_src, run_len, run_start = g, 1, cyc
            others_since[g] = 0
            for t in range(n):
                if t != g and occ[t]:
                    others_since[t] += 1
                    assert others_since[t] <= (n - 1) * q, f"source {t} starved"
        for h, p in enumerate(e.pushed):
            if p is not None:
                expect[h].append(p)
        for h in range(n):
            assert m.occupancy(h) == len(expect[h])
        assert all(r.fires <= q for r in m.turn_log)
    assert len(m.turn_log) > 50
