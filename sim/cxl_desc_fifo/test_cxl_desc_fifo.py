"""Cycle-exact cocotb tests for cxl_desc_fifo (milestone M1), run for TS_EN=0 and TS_EN=1.

Run through scripts/run_verify.sh M1 (it builds the design and exports CXL_PARAM_*).

Every test drives the DUT through sim/common/fifo_tb.FifoTb, which on EVERY cycle compares all
outputs with the abstract reference model (refc/cxl_model) and runs a pin-level conservation
scoreboard. On top of that each test asserts explicit literal expectations on the sampled pins, so
a defect shared by the model and the RTL would still be caught by the directed checks.

Spec references are to specs/CXL_SPEC.md v1.0.
"""

from __future__ import annotations

import os
import random
from collections import deque

from fifo_tb import FifoTb
from hier_util import hierarchy_paths

import cocotb
from cocotb.triggers import ReadOnly, Timer

DEPTH = 16
DESC_W = 105
DESC_MASK = (1 << DESC_W) - 1
TS_MASK = 0xFFFFFFFF

# Approved slices (spec section 3), written out literally and independently of the model helpers.
TAG_LSB, ADDR_LSB, OPCODE_LSB, LENGTH_LSB, PAYLOAD_LSB = 73, 41, 40, 32, 0

RANDOM_CYCLES_MIN = 20000


def mk_desc(tag: int, addr: int, opcode: int, length: int, payload: int) -> int:
    assert tag < (1 << 32) and addr < (1 << 32) and opcode < 2 and length < 256 and payload < (1 << 32)
    return (tag << TAG_LSB) | (addr << ADDR_LSB) | (opcode << OPCODE_LSB) | (length << LENGTH_LSB) | payload


def uniq(i: int, salt: int = 0) -> int:
    """A distinct descriptor per index with every field populated."""
    return mk_desc(
        tag=(0xA5000000 + salt * 0x10000 + i) & 0xFFFFFFFF,
        addr=(0x10000000 + i * 0x01010101 + salt) & 0xFFFFFFFF,
        opcode=i & 1,
        length=(i * 7 + 3) & 0xFF,
        payload=((i + 1) * 0x9E3779B1 + salt) & 0xFFFFFFFF,
    )


def run_seed() -> int:
    """Seed given by the runner (COCOTB_RANDOM_SEED). cocotb 2.x derives a different per-test value
    for cocotb.RANDOM_SEED from it; the stimulus below is seeded with the runner's value itself."""
    if "COCOTB_RANDOM_SEED" not in os.environ:
        raise RuntimeError("COCOTB_RANDOM_SEED is not set: run through scripts/run_verify.sh")
    return int(os.environ["COCOTB_RANDOM_SEED"])


async def new_tb(dut) -> FifoTb:
    tb = FifoTb(dut)
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) DEPTH=%d DESC_W=%d TS_EN=%d TS_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.depth, tb.desc_w, int(tb.ts_en), tb.ts_w,
    )  # fmt: skip
    await tb.start()
    return tb


def pins(obs):
    return (obs.in_ready, obs.head_valid, obs.count)


# Covers: SPEC §5 (synchronous active-low reset, new epoch), §4 (in_ready low in reset)
@cocotb.test()
async def test_01_synchronous_reset(dut):
    tb = await new_tb(dut)
    a = [uniq(i, 1) for i in range(5)]

    # Behaviour after the initial reset release: empty and ready.
    obs = await tb.cycle()
    assert pins(obs) == (1, 0, 0), f"after reset release: {obs}"

    # --- reset while nonempty: nothing is cleared before the edge, everything after it ---------
    await tb.fill(a)
    obs = await tb.cycle(valid=1, desc=uniq(99, 1), ts=0x1234, pop=1, rst_n=0)
    assert pins(obs) == (0, 1, 5), f"reset cycle before its edge must still show 5 entries: {obs}"
    assert obs.head_desc == a[0], "head changed before the reset edge"
    assert obs.edge.reset and obs.edge.pushed is None and obs.edge.popped is None
    obs = await tb.cycle(valid=1, desc=uniq(98, 1), pop=1, rst_n=0)
    assert pins(obs) == (0, 0, 0), f"second reset cycle must show a cleared FIFO, ready low: {obs}"
    obs = await tb.cycle()
    assert pins(obs) == (1, 0, 0), f"first cycle after release: {obs}"
    assert tb.model.epoch == 2 + 1, "initial reset plus two reset edges"

    # Nothing offered during reset was stored and no old entry resurfaces.
    b = [uniq(i, 2) for i in range(3)]
    await tb.fill(b)
    await tb.drain(b)
    await tb.expect_empty()

    # --- reset is synchronous: a low pulse between edges clears nothing -------------------------
    await tb.fill(a[:3])
    await Timer(1, unit="ns")
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    await ReadOnly()
    assert int(dut.o_in_ready.value) == 0, "o_in_ready must be low whenever rst_n is low"
    assert int(dut.o_count.value) == 3 and int(dut.o_head_valid.value) == 1
    await Timer(1, unit="ns")
    dut.rst_n.value = 1
    obs = await tb.cycle()  # no rising edge saw rst_n low
    assert pins(obs) == (1, 1, 3), f"a reset pulse without a clock edge must not clear: {obs}"
    assert obs.head_desc == a[0]
    await tb.drain(a[:3])
    await tb.expect_empty()

    # --- reset while full ----------------------------------------------------------------------
    full = [uniq(i, 3) for i in range(DEPTH)]
    await tb.fill(full)
    obs = await tb.cycle(valid=1, desc=uniq(97, 3), pop=1, rst_n=0)
    assert pins(obs) == (0, 1, 16), f"reset cycle while full: {obs}"
    assert obs.edge.reset
    obs = await tb.cycle()
    assert pins(obs) == (1, 0, 0), f"after reset from full: {obs}"

    # --- reset while empty, held several cycles ------------------------------------------------
    for _ in range(3):
        obs = await tb.cycle(valid=1, desc=uniq(96, 3), pop=1, rst_n=0)
        assert pins(obs) == (0, 0, 0), f"reset while empty: {obs}"

    # Full capacity and order are available again in the new epoch.
    again = [uniq(i, 4) for i in range(DEPTH)]
    await tb.fill(again)
    obs = await tb.cycle()
    assert pins(obs) == (0, 1, 16)
    await tb.drain(again)
    await tb.expect_empty()
    tb.assert_conserved_and_empty()

    assert tb.cov.reset_nonempty >= 2 and tb.cov.reset_full >= 1
    assert tb.epochs_closed == 6 and tb.dropped_by_reset == 5 + 16


# Covers: SPEC §4 (empty FIFO may push but cannot pop; pop request on empty does nothing)
@cocotb.test()
async def test_02_empty_and_pop_on_empty(dut):
    tb = await new_tb(dut)
    for i in range(4):
        obs = await tb.cycle(pop=1)
        assert pins(obs) == (1, 0, 0), f"pop on empty cycle {i}: {obs}"
        assert obs.edge.popped is None and obs.edge.pushed is None
    await tb.expect_empty()

    # The ignored pops did not move anything: one push/pop pair still works in order.
    d0, d1 = uniq(0, 5), uniq(1, 5)
    await tb.fill([d0, d1])
    await tb.drain([d0, d1])
    for i in range(4):
        obs = await tb.cycle(pop=1)
        assert pins(obs) == (1, 0, 0), f"pop on empty after drain, cycle {i}: {obs}"
    # Still exactly aligned after 8 ignored pops.
    d2 = uniq(2, 5)
    obs = await tb.push(d2)
    assert pins(obs) == (1, 0, 0)
    obs = await tb.pop()
    assert pins(obs) == (1, 1, 1) and obs.head_desc == d2
    await tb.expect_empty()
    tb.assert_conserved_and_empty()
    assert tb.cov.pop_on_empty == 8 and tb.cov.pops == 3 and tb.cov.pushes == 3


# Covers: SPEC §4 (in_ready = occupancy < D from beginning-of-cycle occupancy; +1 per push)
@cocotb.test()
async def test_03_fill_to_full(dut):
    tb = await new_tb(dut)
    d = [uniq(i, 6) for i in range(DEPTH)]
    for i in range(DEPTH):
        obs = await tb.push(d[i])
        assert pins(obs) == (1, int(i > 0), i), f"push {i}: {obs}"
        if i > 0:
            assert obs.head_desc == d[0], f"head must stay the first entry while filling (push {i})"
        assert obs.edge.pushed is not None

    # Ready drops exactly at 16 and stays low; offers while full are refused.
    refused = uniq(77, 6)
    for i in range(4):
        obs = await tb.cycle(valid=1, desc=refused, ts=0xDEAD)
        assert pins(obs) == (0, 1, 16), f"full cycle {i}: {obs}"
        assert obs.head_desc == d[0]
        assert obs.edge.pushed is None
    obs = await tb.cycle()
    assert pins(obs) == (0, 1, 16)

    # Drain: count at every step, ready returns one cycle after the first pop.
    for i in range(DEPTH):
        obs = await tb.pop()
        assert pins(obs) == (int(i > 0), 1, DEPTH - i), f"drain {i}: {obs}"
        assert obs.head_desc == d[i], f"drain {i}: wrong order"
    await tb.expect_empty()
    tb.assert_conserved_and_empty()
    assert tb.cov.full_cycles == 5 + 1 and tb.cov.full_valid_refused == 4
    assert tb.cov.occupancies == set(range(DEPTH + 1))


# Covers: SPEC §4 (a full FIFO refuses push even when its head fires that edge)
@cocotb.test()
async def test_04_full_plus_pop_refuses_push(dut):
    tb = await new_tb(dut)
    for rnd in range(3):  # three rounds so the full boundary is hit at different pointer offsets
        d = [uniq(i, 10 + rnd) for i in range(DEPTH)]
        bad = uniq(200, 10 + rnd)
        new = uniq(201, 10 + rnd)
        await tb.fill(d)

        obs = await tb.cycle(valid=1, desc=bad, ts=0xBAD, pop=1)
        assert pins(obs) == (0, 1, 16), f"round {rnd}: full+pop+valid cycle: {obs}"
        assert obs.head_desc == d[0]
        assert obs.edge.pushed is None and obs.edge.popped is not None

        # Ready returns in the very next cycle; the head left; the refused descriptor is not stored.
        obs = await tb.cycle(valid=1, desc=new, ts=0x600D)
        assert pins(obs) == (1, 1, 15), f"round {rnd}: cycle after full+pop: {obs}"
        assert obs.head_desc == d[1]
        obs = await tb.cycle()
        assert pins(obs) == (0, 1, 16)

        await tb.drain(d[1:] + [new])  # 'bad' appears nowhere
        await tb.expect_empty()
        # Leave the pointers at a new offset for the next round.
        await tb.fill([uniq(300 + rnd, 10)])
        await tb.drain([uniq(300 + rnd, 10)])
    tb.assert_conserved_and_empty()
    assert tb.cov.full_pop_valid == 3


# Covers: SPEC §4 (push and pop on one edge: occupancy unchanged, both advance, order preserved)
@cocotb.test()
async def test_05_simultaneous_push_pop_with_wrap(dut):
    tb = await new_tb(dut)
    streamed = 0
    for occ in (1, 15, 8):
        expect = deque(uniq(i, 20 + occ) for i in range(occ))
        await tb.fill(list(expect))
        for i in range(100):  # far more than 16 transfers: both pointers wrap several times
            nxt = uniq(1000 + i, 20 + occ)
            obs = await tb.cycle(valid=1, desc=nxt, ts=i, pop=1)
            assert pins(obs) == (1, 1, occ), f"occ {occ} transfer {i}: {obs}"
            assert obs.head_desc == expect.popleft(), f"occ {occ} transfer {i}: order broken"
            assert obs.edge.pushed is not None and obs.edge.popped is not None
            expect.append(nxt)
            streamed += 1
        obs = await tb.cycle()
        assert pins(obs) == (1, 1, occ), f"occupancy must still be {occ}: {obs}"
        await tb.drain(list(expect))
        await tb.expect_empty()
    tb.assert_conserved_and_empty()
    assert streamed == 300 and tb.cov.push_pop == 300
    assert {1, 8, 15} <= tb.cov.occupancies


# Covers: SPEC §4 (no empty-FIFO bypass; accepted at edge c, eligible no earlier than c+1)
@cocotb.test()
async def test_06_no_bypass(dut):
    tb = await new_tb(dut)
    for rnd in range(20):  # more than 16 so every storage slot is used as the single entry
        a = uniq(rnd, 30)
        obs = await tb.cycle(valid=1, desc=a, ts=rnd, pop=1)
        assert pins(obs) == (1, 0, 0), f"round {rnd}: push into empty with pop asserted: {obs}"
        assert obs.edge.pushed is not None, "the push itself must be accepted"
        assert obs.edge.popped is None, "nothing may pop at the accepting edge"

        # The descriptor is the head only in the next cycle, and it is still there (not popped).
        obs = await tb.cycle()
        assert pins(obs) == (1, 1, 1), f"round {rnd}: cycle after the push: {obs}"
        assert obs.head_desc == a
        # It stays the head while unpopped, whatever is offered on the input pins.
        obs = await tb.cycle(valid=0, desc=DESC_MASK ^ a, ts=0xFFFFFFFF)
        assert pins(obs) == (1, 1, 1) and obs.head_desc == a
        obs = await tb.pop()
        assert pins(obs) == (1, 1, 1) and obs.head_desc == a
        await tb.expect_empty()
    tb.assert_conserved_and_empty()
    assert tb.cov.push_empty_with_pop == 20 and tb.cov.pop_on_empty == 20 and tb.cov.pops == 20


def integrity_patterns():
    pats = [0, DESC_MASK]
    pats += [1 << b for b in range(DESC_W)]  # walking one
    pats += [DESC_MASK ^ (1 << b) for b in range(DESC_W)]  # walking zero
    fields = {
        "tag": (0xFFFFFFFF, TAG_LSB),
        "addr": (0xFFFFFFFF, ADDR_LSB),
        "opcode": (0x1, OPCODE_LSB),
        "length": (0xFF, LENGTH_LSB),
        "payload": (0xFFFFFFFF, PAYLOAD_LSB),
    }
    for mask, lsb in fields.values():
        pats.append(mask << lsb)  # one field all ones, the rest zero
        pats.append(DESC_MASK ^ (mask << lsb))  # one field all zeros, the rest ones
    # Both bits on each side of every field boundary: 104|73, 72|41, 40, 39|32, 31|0.
    for hi, lo in ((104, 73), (73, 72), (72, 41), (41, 40), (40, 39), (39, 32), (32, 31), (31, 0)):
        pats.append((1 << hi) | (1 << lo))
        pats.append(DESC_MASK ^ ((1 << hi) | (1 << lo)))
    pats.append(int("A" * 27, 16) & DESC_MASK)
    pats.append(int("5" * 27, 16) & DESC_MASK)
    pats.append(mk_desc(0xDEADBEEF, 0x12345678, 1, 0xA5, 0xCAFEF00D))
    pats.append(mk_desc(0x00000001, 0x80000000, 0, 0x80, 0x00000001))
    pats.append(mk_desc(0x80000000, 0x00000001, 1, 0x01, 0x80000000))
    return pats


# Covers: SPEC §3 (all 105 bits stored intact; Tag[104:73] Address[72:41] Opcode[40] Length[39:32] Payload[31:0])
@cocotb.test()
async def test_07_descriptor_integrity_105_bits(dut):
    tb = await new_tb(dut)
    pats = integrity_patterns()
    assert len(pats) == 2 + 105 + 105 + 10 + 16 + 5
    assert all(0 <= p <= DESC_MASK for p in pats)

    # Batches of 16 through a full FIFO: every storage slot holds every kind of pattern over time.
    seen = 0
    for start in range(0, len(pats), DEPTH):
        batch = pats[start : start + DEPTH]
        stamps = [(~p) & TS_MASK for p in batch]
        await tb.fill(batch, ts_of=lambda i, s=stamps: s[i])
        for i, p in enumerate(batch):
            obs = await tb.pop()
            assert obs.head_valid == 1
            got = obs.head_desc
            assert got == p, f"pattern {start + i}: got {got:#029x}, sent {p:#029x}, diff {got ^ p:#029x}"
            # Field-by-field on the approved slices.
            assert (got >> TAG_LSB) & 0xFFFFFFFF == (p >> 73) & 0xFFFFFFFF, "Tag[104:73]"
            assert (got >> ADDR_LSB) & 0xFFFFFFFF == (p >> 41) & 0xFFFFFFFF, "Address[72:41]"
            assert (got >> OPCODE_LSB) & 0x1 == (p >> 40) & 0x1, "Opcode[40]"
            assert (got >> LENGTH_LSB) & 0xFF == (p >> 32) & 0xFF, "Length[39:32]"
            assert got & 0xFFFFFFFF == p & 0xFFFFFFFF, "Payload[31:0]"
            assert obs.head_ts == (stamps[i] if tb.ts_en else 0)
            seen += 1
        await tb.expect_empty()

    # Same patterns streamed through a one-entry queue (push and pop on the same edge).
    first = pats[0]
    await tb.fill([first])
    prev = first
    for p in pats[1:]:
        obs = await tb.cycle(valid=1, desc=p, ts=p & TS_MASK, pop=1)
        assert pins(obs) == (1, 1, 1) and obs.head_desc == prev
        prev = p
    await tb.drain([prev])
    await tb.expect_empty()
    tb.assert_conserved_and_empty()
    assert seen == len(pats) == 243

    # A known field pattern, checked against literal field values on the DUT pins.
    await tb.push(mk_desc(0xDEADBEEF, 0x12345678, 1, 0xA5, 0xCAFEF00D))
    obs = await tb.pop()
    h = obs.head_desc
    assert h >> 73 == 0xDEADBEEF and (h >> 41) & 0xFFFFFFFF == 0x12345678
    assert (h >> 40) & 1 == 1 and (h >> 32) & 0xFF == 0xA5 and h & 0xFFFFFFFF == 0xCAFEF00D
    await tb.expect_empty()


TS_VALUES = [
    0xFFFFFFFE,
    0xFFFFFFFF,
    0x00000000,
    0x00000001,
    0x7FFFFFFF,
    0x80000000,
    0x80000001,
    0xAAAAAAAA,
    0x55555555,
    0x00000000,  # repeated and non-monotonic values: metadata is opaque to the FIFO
    0xFFFFFFFF,
    0x80000000,
    0x12345678,
    0x12345678,
    0x00000002,
    0xFFFFFFFD,
]


# Covers: SPEC §6 (per-entry 32-bit arrival timestamp for FCFS/FAI; RR has no timestamp storage),
#         common_framework.md item 3 (elaboration-time option, no dummy timestamp bank)
@cocotb.test()
async def test_08_timestamp_metadata(dut):
    tb = await new_tb(dut)
    descs = [uniq(i, 40) for i in range(len(TS_VALUES))]
    assert len(TS_VALUES) == DEPTH

    # Full batch: each timestamp comes out with the descriptor it was pushed with.
    await tb.fill(descs, ts_of=lambda i: TS_VALUES[i])
    for i, d in enumerate(descs):
        # Hold the head one cycle while a different value sits on i_in_ts: the head is unaffected.
        obs = await tb.cycle(valid=0, ts=(~TS_VALUES[i]) & TS_MASK)
        assert obs.head_desc == d
        assert obs.head_ts == (TS_VALUES[i] if tb.ts_en else 0), f"held entry {i}: ts {obs.head_ts:#x}"
        obs = await tb.pop()
        assert obs.head_desc == d
        assert obs.head_ts == (TS_VALUES[i] if tb.ts_en else 0), f"entry {i}: ts {obs.head_ts:#x}"
    await tb.expect_empty()

    # Streaming across pointer wrap at occupancy 3: timestamps stay attached to their entries.
    queue = deque()
    for i in range(3):
        ts = TS_VALUES[i]
        await tb.push(uniq(100 + i, 41), ts=ts)
        queue.append((uniq(100 + i, 41), ts))
    for i in range(64):
        ts = (0xFFFFFFE0 + i) & TS_MASK  # crosses 0xFFFFFFFF -> 0
        d = uniq(200 + i, 41)
        obs = await tb.cycle(valid=1, desc=d, ts=ts, pop=1)
        exp_d, exp_ts = queue.popleft()
        assert obs.head_desc == exp_d
        assert obs.head_ts == (exp_ts if tb.ts_en else 0), f"stream {i}: ts {obs.head_ts:#x}"
        queue.append((d, ts))
    while queue:
        exp_d, exp_ts = queue.popleft()
        obs = await tb.pop()
        assert obs.head_desc == exp_d and obs.head_ts == (exp_ts if tb.ts_en else 0)
    obs = await tb.expect_empty()
    assert obs.head_ts == 0 or tb.ts_en  # TS_EN=0: constant 0 even while empty
    tb.assert_conserved_and_empty()

    # Structural check through the simulator's own view of the elaborated hierarchy.
    paths = hierarchy_paths(dut)
    names = [p for p, _kind in paths]
    for p, kind in paths:
        dut._log.info("hierarchy: %s (%s)", p, kind)
    assert any(p.endswith("desc_mem_q") for p in names), (
        "hierarchy inspection is not usable in this simulator: desc_mem_q is not visible, so "
        "absence of a timestamp memory could not be concluded from it"
    )
    has_ts_mem = any("ts_mem_q" in p for p in names)
    has_gen_ts = any("gen_ts" in p for p in names)
    has_gen_no_ts = any("gen_no_ts" in p for p in names)
    if tb.ts_en:
        assert has_ts_mem and has_gen_ts, f"TS_EN=1 must elaborate gen_ts.ts_mem_q: {names}"
        assert not has_gen_no_ts
        ts_mem = dut.gen_ts.ts_mem_q
        assert len(ts_mem) == DEPTH and len(ts_mem[0]) == 32
    else:
        assert not has_ts_mem, f"TS_EN=0 must not elaborate any timestamp memory: {names}"
        assert not has_gen_ts, f"TS_EN=0 must not elaborate gen_ts: {names}"
        assert has_gen_no_ts, f"TS_EN=0 must elaborate gen_no_ts: {names}"
        # No other memory may stand in for a timestamp bank: desc_mem_q is the only array.
        arrays = [p for p, kind in paths if kind == "ArrayObject"]
        assert len(arrays) == 1 and arrays[0].endswith("desc_mem_q"), f"unexpected arrays: {arrays}"
    desc_mem = dut.desc_mem_q
    assert len(desc_mem) == DEPTH and len(desc_mem[0]) == DESC_W


# (push probability, pop probability) per traffic phase
PHASES = [
    (0.90, 0.15),  # filling: reaches and sits at full
    (0.15, 0.90),  # draining: reaches and sits at empty, pops on empty
    (0.60, 0.60),  # balanced
    (0.97, 0.97),  # saturated: simultaneous push/pop almost every cycle
    (0.10, 0.10),  # sparse
    (1.00, 0.30),  # producer always valid: full + pop + valid
    (0.30, 1.00),  # consumer always popping: push into empty with pop asserted
    (0.50, 0.45),
]


# Covers: SPEC §4, §5, §6, §9 (random vs independent model; conservation, order, reset epochs)
@cocotb.test()
async def test_09_random_vs_model(dut):
    tb = await new_tb(dut)
    cycles = int(os.environ.get("CXL_FIFO_RANDOM_CYCLES", RANDOM_CYCLES_MIN))
    assert cycles >= RANDOM_CYCLES_MIN, "the random test may be lengthened, never shortened"
    rng = random.Random(run_seed())

    serial = 0
    pending = None  # descriptor the producer is holding until it is pushed (spec section 4)
    push_cycle = deque()  # accepting-edge cycle index of every outstanding entry, from the pins
    min_wait = None
    resets = 0
    reset_left = 0
    phase = PHASES[0]
    phase_left = 0
    total_pushed = 0

    for n in range(cycles):
        if phase_left == 0:
            phase = PHASES[rng.randrange(len(PHASES))]
            phase_left = rng.randint(150, 700)
        phase_left -= 1
        p_push, p_pop = phase

        if reset_left == 0 and rng.random() < 1.0 / 600.0:
            reset_left = rng.randint(1, 3)
            resets += 1
        rst_n = 0 if reset_left else 1
        reset_left = max(0, reset_left - 1)

        if pending is None and rng.random() < p_push:
            serial += 1
            # All 105 bits random, except Tag[23:0] which carries a unique serial number so that
            # no two generated requests are equal (loss/duplication/reordering stay observable).
            assert serial < (1 << 24)
            pending = (rng.getrandbits(DESC_W) & ~(0xFFFFFF << TAG_LSB)) | (serial << TAG_LSB)
        pop = int(rng.random() < p_pop)
        ts = (0xFFFFC000 + n) & TS_MASK  # free-running, wraps through 0 during the run

        obs = await tb.cycle(
            valid=int(pending is not None), desc=pending or 0, ts=ts, pop=pop, rst_n=rst_n
        )

        if not rst_n:
            assert obs.in_ready == 0
            push_cycle.clear()
            continue
        if pop and obs.head_valid:
            waited = n - push_cycle.popleft()
            assert waited >= 1, f"cycle {n}: entry left {waited} cycles after its push (bypass)"
            min_wait = waited if min_wait is None else min(min_wait, waited)
        if pending is not None and obs.in_ready:
            push_cycle.append(n)
            total_pushed += 1
            pending = None
        assert len(push_cycle) == tb.outstanding(), "pin-level bookkeeping disagrees with scoreboard"

    # Drain what is left; nothing new is offered.
    for _ in range(DEPTH + 1):
        if tb.outstanding() == 0:
            break
        await tb.pop()
    await tb.expect_empty()
    tb.assert_conserved_and_empty()

    cov = tb.cov
    dut._log.info(
        "random: cycles=%d resets=%d reset_cycles=%d pushes=%d pops=%d push_pop=%d full=%d "
        "empty=%d full_pop_valid=%d full_valid_refused=%d pop_on_empty=%d push_empty_with_pop=%d "
        "reset_nonempty=%d reset_full=%d dropped_by_reset=%d min_wait=%s occupancies=%s",
        cov.cycles, resets, cov.reset_cycles, cov.pushes, cov.pops, cov.push_pop, cov.full_cycles,
        cov.empty_cycles, cov.full_pop_valid, cov.full_valid_refused, cov.pop_on_empty,
        cov.push_empty_with_pop, cov.reset_nonempty, cov.reset_full, tb.dropped_by_reset, min_wait,
        sorted(cov.occupancies),
    )  # fmt: skip

    # Conservation over the whole run, from pin-level counters only.
    assert cov.pushes == total_pushed
    assert cov.pushes == tb.total_delivered + tb.dropped_by_reset, "accepted != delivered + reset-dropped"
    assert cov.pops == tb.total_delivered
    assert cov.cycles >= cycles

    # Mandatory event coverage: the run is not a pass unless every one of these happened.
    assert cov.full_cycles > 0, "coverage: never full"
    assert cov.empty_cycles > 0, "coverage: never empty"
    assert cov.push_pop > 0, "coverage: no simultaneous push+pop"
    assert cov.full_pop_valid > 0, "coverage: no full+pop+valid"
    assert cov.full_valid_refused > 0, "coverage: no refused push"
    assert cov.pop_on_empty > 0, "coverage: no pop on empty"
    assert cov.push_empty_with_pop > 0, "coverage: no push into empty with pop asserted"
    assert cov.reset_nonempty > 0, "coverage: no reset while nonempty"
    assert resets >= 2 and tb.epochs_closed >= 2, "coverage: fewer than two reset epochs"
    assert cov.occupancies >= set(range(DEPTH + 1)), (
        f"coverage: occupancies never seen: {sorted(set(range(DEPTH + 1)) - cov.occupancies)}"
    )
    assert min_wait == 1, "coverage: the minimum 1-cycle wait (next-cycle eligibility) never occurred"
    assert cov.pushes > 1000 and cov.pops > 1000
