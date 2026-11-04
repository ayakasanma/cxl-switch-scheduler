"""Pure-pytest unit tests for the abstract FIFO model (specs/CXL_SPEC.md v1.0 sections 3-6)."""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cxl_model import (  # noqa: E402
    DESC_FIELDS,
    DESC_WIDTH,
    FIFO_DEPTH,
    Entry,
    FifoModel,
    pack_desc,
    unpack_desc,
)


def fill(model, n, base=0x100):
    for i in range(n):
        assert model.commit(in_valid=True, in_desc=base + i, in_ts=i if model.ts_enabled else None).pushed


# Covers: SPEC §3
def test_descriptor_layout_is_105_bits_msb_first():
    assert DESC_WIDTH == 105 == sum(msb - lsb + 1 for _, msb, lsb in DESC_FIELDS)
    assert DESC_FIELDS == (
        ("tag", 104, 73),
        ("addr", 72, 41),
        ("opcode", 40, 40),
        ("length", 39, 32),
        ("payload", 31, 0),
    )
    desc = pack_desc(tag=0xDEADBEEF, addr=0x12345678, opcode=1, length=0xA5, payload=0xCAFEF00D)
    assert desc == (0xDEADBEEF << 73) | (0x12345678 << 41) | (1 << 40) | (0xA5 << 32) | 0xCAFEF00D
    assert unpack_desc(desc) == {
        "tag": 0xDEADBEEF,
        "addr": 0x12345678,
        "opcode": 1,
        "length": 0xA5,
        "payload": 0xCAFEF00D,
    }
    assert pack_desc(0xFFFFFFFF, 0xFFFFFFFF, 1, 0xFF, 0xFFFFFFFF) == (1 << 105) - 1
    with pytest.raises(ValueError):
        pack_desc(0, 0, 2, 0, 0)
    with pytest.raises(ValueError):
        unpack_desc(1 << 105)


# Covers: SPEC §4
def test_empty_view_and_pop_on_empty_is_a_no_op():
    m = FifoModel()
    assert m.depth == FIFO_DEPTH == 16
    v = m.view()
    assert (v.in_ready, v.head_valid, v.count, v.head_desc, v.head_ts) == (True, False, 0, None, None)
    r = m.commit(pop=True)
    assert r.popped is None and r.pushed is None and not r.reset
    assert m.occupancy == 0 and m.pops == 0


# Covers: SPEC §4
def test_push_is_visible_only_in_the_next_cycle_and_cannot_pop_at_its_edge():
    m = FifoModel()
    before = m.view()
    r = m.commit(in_valid=True, in_desc=0xABC, pop=True)
    assert before.head_valid is False
    assert r.pushed == Entry(0xABC, None) and r.popped is None
    after = m.view()
    assert after.head_valid and after.head_desc == 0xABC and after.count == 1


# Covers: SPEC §4
def test_ready_follows_beginning_of_cycle_occupancy_and_drops_at_depth():
    m = FifoModel()
    for i in range(16):
        assert m.view().in_ready and m.view().count == i
        m.commit(in_valid=True, in_desc=i)
    assert m.full and not m.view().in_ready and m.view().count == 16
    r = m.commit(in_valid=True, in_desc=0x999)
    assert r.pushed is None and m.occupancy == 16
    assert [e.desc for e in m.entries()] == list(range(16))


# Covers: SPEC §4
def test_full_refuses_push_even_when_head_pops_on_the_same_edge():
    m = FifoModel()
    fill(m, 16)
    assert not m.view().in_ready
    r = m.commit(in_valid=True, in_desc=0xBAD, pop=True)
    assert r.pushed is None and r.popped == Entry(0x100, None)
    assert m.occupancy == 15 and m.view().in_ready
    assert 0xBAD not in [e.desc for e in m.entries()]
    assert [e.desc for e in m.entries()] == [0x100 + i for i in range(1, 16)]


# Covers: SPEC §4
@pytest.mark.parametrize("occupancy", [1, 2, 8, 15])
def test_simultaneous_push_pop_keeps_occupancy_and_order(occupancy):
    m = FifoModel()
    fill(m, occupancy)
    expect = [0x100 + i for i in range(occupancy)]
    for i in range(100):
        r = m.commit(in_valid=True, in_desc=0x1000 + i, pop=True)
        expect.append(0x1000 + i)
        assert r.popped.desc == expect.pop(0) and r.pushed.desc == 0x1000 + i
        assert m.occupancy == occupancy
        assert [e.desc for e in m.entries()] == expect


# Covers: SPEC §4
def test_update_table_rows():
    m = FifoModel()
    fill(m, 4)
    m.commit()
    assert m.occupancy == 4
    m.commit(in_valid=True, in_desc=1)
    assert m.occupancy == 5
    m.commit(pop=True)
    assert m.occupancy == 4
    m.commit(in_valid=True, in_desc=2, pop=True)
    assert m.occupancy == 4


# Covers: SPEC §5
def test_reset_edge_clears_and_refuses_handshakes_and_starts_new_epoch():
    m = FifoModel()
    fill(m, 16)
    v = m.view(rst_n=False)
    assert not v.in_ready and v.count == 16 and v.head_valid  # nothing cleared before the edge
    r = m.commit(rst_n=False, in_valid=True, in_desc=0x55, pop=True)
    assert r.reset and r.pushed is None and r.popped is None
    assert m.occupancy == 0 and m.epoch == 1 and m.pushes == 0 and m.pops == 0
    assert m.view(rst_n=False).in_ready is False
    assert m.view().in_ready is True
    m.commit(in_valid=True, in_desc=0x77)
    assert m.view().head_desc == 0x77 and m.view().count == 1

    partial = FifoModel()
    fill(partial, 5)
    partial.commit(rst_n=False)
    assert partial.occupancy == 0 and not partial.view().head_valid


# Covers: SPEC §6
def test_timestamp_metadata_travels_with_its_entry():
    m = FifoModel(ts_enabled=True)
    stamps = [0xFFFFFFFE, 0xFFFFFFFF, 0, 1, 0x80000000]
    for i, ts in enumerate(stamps):
        m.commit(in_valid=True, in_desc=i, in_ts=ts)
    for i, ts in enumerate(stamps):
        v = m.view()
        assert (v.head_desc, v.head_ts) == (i, ts)
        assert m.commit(pop=True).popped == Entry(i, ts)
    with pytest.raises(ValueError):
        m.commit(in_valid=True, in_desc=0)  # timestamp required
    with pytest.raises(ValueError):
        m.commit(in_valid=True, in_desc=0, in_ts=1 << 32)


# Covers: SPEC §6
def test_no_timestamp_is_kept_when_metadata_is_disabled():
    m = FifoModel(ts_enabled=False)
    m.commit(in_valid=True, in_desc=5, in_ts=0x1234)
    assert m.head() == Entry(5, None) and m.view().head_ts is None


# Covers: SPEC §4
def test_refused_push_with_bad_value_is_not_validated_or_stored():
    m = FifoModel()
    fill(m, 16)
    assert m.commit(in_valid=True, in_desc=1 << 200).pushed is None
    empty = FifoModel()
    with pytest.raises(ValueError):
        empty.commit(in_valid=True, in_desc=1 << 105)
    with pytest.raises(ValueError):
        FifoModel(depth=0)


# Covers: SPEC §4, §9
@pytest.mark.parametrize("seed", [509, 510, 511])
@pytest.mark.parametrize("ts_enabled", [False, True])
def test_random_conservation_and_order(seed, ts_enabled):
    """Cross-check against a deliberately different formulation: global sequence numbers."""
    rng = random.Random(seed)
    m = FifoModel(ts_enabled=ts_enabled)
    accepted, delivered = [], []
    seen_full = seen_empty = seen_full_pop = seen_push_pop = False
    for cycle in range(20000):
        phase = (cycle // 2000) % 4
        p_push, p_pop = [(0.9, 0.2), (0.2, 0.9), (0.6, 0.6), (0.95, 0.95)][phase]
        in_valid, pop = rng.random() < p_push, rng.random() < p_pop
        desc, ts = rng.getrandbits(105), cycle & 0xFFFFFFFF
        occ = m.occupancy
        v = m.view()
        assert v.count == occ == len(accepted) - len(delivered)
        assert v.in_ready == (occ < 16) and v.head_valid == (occ > 0)
        r = m.commit(in_valid=in_valid, in_desc=desc, in_ts=ts, pop=pop)
        if r.pushed:
            accepted.append((desc, ts if ts_enabled else None))
        if r.popped:
            delivered.append(tuple(r.popped))
        assert bool(r.pushed) == (in_valid and occ < 16)
        assert bool(r.popped) == (pop and occ > 0)
        seen_full |= occ == 16
        seen_empty |= occ == 0
        seen_full_pop |= occ == 16 and pop and in_valid
        seen_push_pop |= bool(r.pushed) and bool(r.popped)
    assert seen_full and seen_empty and seen_full_pop and seen_push_pop
    assert delivered == accepted[: len(delivered)]
    assert [tuple(e) for e in m.entries()] == accepted[len(delivered) :]
