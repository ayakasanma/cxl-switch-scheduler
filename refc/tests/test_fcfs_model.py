"""Pure-pytest unit tests for the abstract FCFS switch model (specs/CXL_SPEC.md v1.0 sections 4-6).

Every expectation is written out by hand from the spec contract (absolute arrival order, lowest
source ID on ties, held grant not preempted, stored 32-bit timestamp = counter value at the push
edge). Nothing is derived from the RTL.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model import FcfsSwitchModel  # noqa: E402

N = 4


def fresh(n=N):
    m = FcfsSwitchModel(n)
    m.commit(rst_n=False)
    return m


def edge(m, pushes=None, ready=False, rst_n=True):
    pushes = pushes or {}
    valid = [h in pushes for h in range(m.n_src)]
    desc = [pushes.get(h, 0) for h in range(m.n_src)]
    return m.commit(ready, valid, desc, rst_n)


def serve_all(m):
    """Fire with ready=1 until empty; returns the delivered (source, desc) order."""
    got = []
    for _ in range(m.n_src * m.depth + 2):
        v = m.view(True)
        if not v.out_valid:
            break
        e = edge(m, ready=True)
        got.append((e.fired[0], e.fired[1].desc))
    assert m.view(True).out_valid is False
    return got


# Covers: SPEC §5 (reset clears queues/hold/counter; counter starts at 0)
def test_reset_clears_and_counter_starts_at_zero():
    m = FcfsSwitchModel(N)
    assert m.counter() is None
    m.commit(rst_n=False)
    assert m.counter() == 0 and m.epoch == 1
    edge(m)
    edge(m)
    assert m.counter() == 2
    edge(m, {1: 0x11})
    assert m.queue(1)[0].ts32 == 2
    edge(m, rst_n=False)
    assert m.counter() == 0 and m.nonempty_sources() == [] and m.held is None and m.epoch == 2


# Covers: SPEC §6 (same-cycle ties -> ascending source ID)
def test_same_cycle_tie_ascending_id():
    m = fresh()
    edge(m, {3: 0x3, 1: 0x1, 2: 0x2})
    v = m.view(True)
    assert v.out_valid and v.out_source == 1
    assert serve_all(m) == [(1, 0x1), (2, 0x2), (3, 0x3)]


# Covers: SPEC §6 (older head wins over lower ID)
def test_older_head_beats_lower_id():
    m = fresh()
    edge(m, {3: 0x30})
    edge(m, {0: 0x00})
    assert m.view(True).out_source == 3
    assert serve_all(m) == [(3, 0x30), (0, 0x00)]


# Covers: SPEC §4, §6 (per-source FIFO order interleaved with cross-source age order)
def test_fifo_order_and_cross_source_age():
    m = fresh()
    edge(m, {0: 0xA0, 2: 0xC0})  # edge t
    edge(m, {0: 0xA1})  # t+1
    edge(m, {2: 0xC1, 1: 0xB0})  # t+2
    assert serve_all(m) == [(0, 0xA0), (2, 0xC0), (0, 0xA1), (1, 0xB0), (2, 0xC1)]


# Covers: SPEC §4 (no bypass: pushed at edge c, offered at c+1)
def test_no_bypass():
    m = fresh()
    assert m.view(True).out_valid is False
    e = edge(m, {2: 0x7}, ready=True)
    assert e.fired is None
    v = m.view(True)
    assert v.out_valid and v.out_source == 2 and v.out_desc == 0x7


# Covers: SPEC §4, §6 (held grant not preempted by older arrivals... counter advances in stall)
def test_held_grant_not_preempted_and_counter_runs_in_stall():
    m = fresh()
    edge(m, {2: 0x20})  # ts 0
    v = m.view(False)
    assert v.out_valid and v.out_source == 2 and not v.held
    e = edge(m, {0: 0x00}, ready=False)  # stall latches source 2; source 0 pushed with ts 1
    assert e.latched == 2
    for _ in range(5):
        edge(m, {1: 0x10} if m.occupancy(1) == 0 else None, ready=False)
    assert m.held == 2 and m.counter() == 7
    assert m.queue(0)[0].ts32 == 1 and m.queue(1)[0].ts32 == 2
    assert serve_all(m) == [(2, 0x20), (0, 0x00), (1, 0x10)]


# Covers: SPEC §4 (full refuses push even when its head fires; ready next cycle)
def test_full_plus_pop_refusal():
    m = fresh(4)
    for i in range(16):
        edge(m, {0: i})
    v = m.view(True)
    assert v.in_ready[0] is False
    e = edge(m, {0: 0x99}, ready=True)
    assert e.fired[1].desc == 0 and e.pushed[0] is None
    assert m.view(True).in_ready[0] is True and m.occupancy(0) == 15


# Covers: SPEC §6 (wrap: ordering by absolute time across the 2^32 boundary)
def test_wrap_ordering_uses_absolute_time():
    m = fresh()
    m.deposit_counter(0xFFFFFFFE)
    edge(m, {3: 0x3})  # stored 0xFFFFFFFE
    edge(m, {2: 0x2})  # stored 0xFFFFFFFF
    edge(m, {1: 0x1})  # stored 0x00000000
    edge(m, {0: 0x0})  # stored 0x00000001
    assert [m.queue(h)[0].ts32 for h in range(4)] == [1, 0, 0xFFFFFFFF, 0xFFFFFFFE]
    assert serve_all(m) == [(3, 0x3), (2, 0x2), (1, 0x1), (0, 0x0)]


# Covers: SPEC §6 (deposit only right after reset with empty queues)
def test_deposit_restrictions():
    m = fresh()
    edge(m, {0: 1})
    with pytest.raises(ValueError):
        m.deposit_counter(5)
    m2 = FcfsSwitchModel(N)
    with pytest.raises(ValueError):
        m2.deposit_counter(5)
    m3 = fresh()
    with pytest.raises(ValueError):
        m3.deposit_counter(1 << 32)


# Covers: SPEC §5 (reset mid-hold drops everything; new epoch)
def test_reset_mid_hold_new_epoch():
    m = fresh()
    edge(m, {1: 0x1})
    edge(m, ready=False)
    assert m.held == 1
    e = edge(m, {0: 0x5}, ready=True, rst_n=False)
    assert e.reset and e.released and e.fired is None
    assert m.held is None and m.nonempty_sources() == [] and m.counter() == 0


# Covers: SPEC §6 (environment assumption check: outstanding < 2^31 cycles)
def test_environment_age_assumption_checked():
    m = fresh()
    edge(m, {0: 1})
    m.edge_index += 1 << 31  # simulate an absurdly old head
    with pytest.raises(AssertionError):
        m.view(True)


MAX_LEGAL_AGE = (1 << 31) - 1


def _aged_single_entry(age, src=2, desc=0x5A):
    """Reset, push one entry on `src`, then move the current edge so its head is `age` old."""
    m = fresh()
    e = edge(m, {src: desc})
    entry = e.pushed[src]
    assert entry is not None and m.edge_index == entry.arrival + 1
    m.edge_index = entry.arrival + age
    return m, entry


# Covers: SPEC §6 (allowed boundary: a head aged exactly 2^31-1 at the current edge is legal in
# both view() and commit(); regression for Codex age-boundary reproducer)
def test_age_boundary_max_legal_fires():
    m, entry = _aged_single_entry(MAX_LEGAL_AGE)
    v = m.view(True)
    assert v.out_valid and v.out_source == 2 and v.out_desc == 0x5A
    e = edge(m, ready=True)
    assert e.fired is not None
    assert e.fired[0] == 2 and e.fired[1].desc == 0x5A and e.fired[1].arrival == entry.arrival
    assert e.edge_index == entry.arrival + MAX_LEGAL_AGE
    assert m.nonempty_sources() == [] and m.view(True).out_valid is False


# Covers: SPEC §6 (non-firing commit at the maximum legal age also succeeds; the request is held)
def test_age_boundary_max_legal_non_firing_commit():
    m, entry = _aged_single_entry(MAX_LEGAL_AGE)
    assert m.view(False).out_valid
    e = edge(m, ready=False)
    assert e.fired is None and e.latched == 2 and m.held == 2
    # One edge later the same head is 2^31 old: the environment assumption is now violated.
    with pytest.raises(AssertionError):
        m.view(True)
    with pytest.raises(AssertionError):
        edge(m, ready=True)


# Covers: SPEC §6 (invalid ages 2^31 and larger: both view() and commit() raise, no state change)
@pytest.mark.parametrize("age", [1 << 31, (1 << 31) + 1, 1 << 40])
def test_age_boundary_invalid_raises(age):
    m, _ = _aged_single_entry(age)
    with pytest.raises(AssertionError):
        m.view(True)
    before = m.edge_index
    with pytest.raises(AssertionError):
        edge(m, ready=True)
    assert m.edge_index == before and m.occupancy(2) == 1
    with pytest.raises(AssertionError):
        edge(m, ready=False)


# Covers: SPEC §5, §6 (a reset edge is always legal and clears the over-age head)
def test_age_boundary_reset_clears_over_age_head():
    m, _ = _aged_single_entry(1 << 31)
    e = edge(m, rst_n=False)
    assert e.reset and m.nonempty_sources() == []
    assert m.view(True).out_valid is False
