"""Cycle-exact cocotb tests of the common framework (milestone M2): N real cxl_desc_fifo + one real
cxl_out_hold inside the sim-only candidate-injection fixture, for N_SRC = 4, 8 and 16.

Run through scripts/run_verify.sh M2 (it builds the design and exports CXL_PARAM_*).

Every cycle of every test goes through sim/common/common_ctrl_tb.CtrlTb, which compares all pins
with the abstract reference model (refc/cxl_model/common_ctrl_model.py), applies model-free
pin-level contract checks (hold provenance, stall stability, selected-head-valid invariant,
one-hot pop) and keeps a pin-level conservation/order scoreboard. On top of that each directed
test asserts literal expectations, so a defect shared by model and RTL would still be caught.

The candidate is always a beginning-of-cycle value: it is chosen before, and never as a function
of, the same cycle's out_ready / fire.

Spec references are to specs/CXL_SPEC.md v1.0.
"""

from __future__ import annotations

import random
import re
from collections import deque

from common_ctrl_tb import DEPTH, DESC_W, CtrlTb, run_seed
from cxl_model import NO_CANDIDATE, Candidate
from hier_util import hierarchy_paths

import cocotb
from cocotb.triggers import ReadOnly, Timer

# Approved slices (spec section 3), written out literally and independently of the model helpers.
TAG_LSB, ADDR_LSB, OPCODE_LSB, LENGTH_LSB, PAYLOAD_LSB = 73, 41, 40, 32, 0

RANDOM_CYCLES = 10000  # per random test and seed


def mk_desc(tag: int, addr: int, opcode: int, length: int, payload: int) -> int:
    assert tag < (1 << 32) and addr < (1 << 32) and opcode < 2 and length < 256 and payload < (1 << 32)
    return (tag << TAG_LSB) | (addr << ADDR_LSB) | (opcode << OPCODE_LSB) | (length << LENGTH_LSB) | payload


def uniq(i: int, salt: int = 0) -> int:
    """A distinct descriptor per (index, salt) with every field populated."""
    assert 0 <= i < 0x10000 and 0 <= salt < 0x100
    return mk_desc(
        tag=(0xA5000000 + salt * 0x10000 + i) & 0xFFFFFFFF,
        addr=(0x10000000 + i * 0x01010101 + salt * 0x00310000) & 0xFFFFFFFF,
        opcode=(i ^ salt) & 1,
        length=(i * 7 + salt * 3 + 3) & 0xFF,
        payload=((i + 1) * 0x9E3779B1 + salt * 0x85EBCA6B) & 0xFFFFFFFF,
    )


def rnd_desc(rng: random.Random, serial: int) -> int:
    """All 105 bits random except Tag[23:0], which carries a unique serial number."""
    assert 0 < serial < (1 << 24)
    return (rng.getrandbits(DESC_W) & ~(0xFFFFFF << TAG_LSB)) | (serial << TAG_LSB)


async def new_tb(dut) -> CtrlTb:
    tb = CtrlTb(dut)
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) N_SRC=%d CTX_W=%d TS_EN=%d DEPTH=%d DESC_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.n, tb.ctx_w, int(tb.ts_en), tb.depth, tb.desc_w,
    )  # fmt: skip
    await tb.start()
    return tb


def per_source(got, n):
    return {h: [d for s, d in got if s == h] for h in range(n)}


# Covers: SPEC §5 (synchronous active-low reset, outputs inactive in reset, new epoch)
@cocotb.test()
async def test_01_reset_inactive_mid_hold_and_fresh_epoch(dut):
    tb = await new_tb(dut)
    n, ALL = tb.n, tb.all_src
    A = tb.ctx_mask
    B = A ^ 1

    o = await tb.cycle(cand=tb.cand(0, A), out_ready=1)
    assert (o.in_ready, o.head_valid, o.out_valid, o.held, o.fire, o.pop) == (ALL, 0, 0, 0, 0, 0)
    assert o.count == [0] * n

    a = {0: [uniq(i, 1) for i in range(3)], 1: [uniq(i, 2) for i in range(2)]}
    await tb.load(a)
    o = await tb.cycle(cand=tb.cand(1, A), out_ready=0)
    assert (o.out_valid, o.held, o.out_source, o.out_desc) == (1, 0, 1, a[1][0])
    o = await tb.cycle(cand=tb.cand(0, B), out_ready=0)
    assert (o.out_valid, o.held, o.out_source, o.grant_ctx, o.out_desc) == (1, 1, 1, A, a[1][0])

    # --- reset in the middle of the held stall, with every request input asserted --------------
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, cand=tb.cand(0, B), out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.pop, o.in_ready, o.push) == (0, 0, 0, 0, 0), f"active in reset: {o}"
    # Synchronous: nothing is cleared before the edge.
    assert o.held == 1 and o.count[:2] == [3, 2] and o.head_valid == 0b11
    assert o.edge.reset and o.edge.released and o.edge.fired is None
    o = await tb.cycle(push=junk, cand=tb.cand(0, B), out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.pop, o.in_ready, o.push) == (0, 0, 0, 0, 0)
    assert o.held == 0 and o.count == [0] * n and o.head_valid == 0, f"reset did not clear: {o}"

    # --- fresh epoch: nothing offered during reset was stored, no old grant or entry resurfaces --
    o = await tb.cycle(cand=tb.cand(1, A), out_ready=1)
    assert (o.in_ready, o.head_valid, o.out_valid, o.held, o.fire) == (ALL, 0, 0, 0, 0)
    fresh = uniq(0, 3)
    o = await tb.cycle(push={1: fresh}, cand=tb.cand(1, B), out_ready=1)
    assert o.out_valid == 0 and o.push == 0b10
    o = await tb.cycle(cand=tb.cand(1, B), out_ready=1)
    assert (o.fire, o.out_desc, o.out_source, o.grant_ctx, o.held) == (1, fresh, 1, B, 0)
    o = await tb.cycle(cand=tb.cand(1, B), out_ready=1)
    assert o.out_valid == 0 and o.count == [0] * n

    # --- reset edge on an unlocked valid+ready offer: no fire, no pop on the reset edge ----------
    await tb.load({2: [uniq(0, 4), uniq(1, 4)]})
    o = await tb.cycle(cand=tb.cand(2, A), out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.pop) == (0, 0, 0) and o.count[2] == 2
    o = await tb.cycle()
    assert o.count == [0] * n and o.held == 0 and o.in_ready == ALL

    # --- reset is synchronous: a low pulse between edges clears neither the hold nor the FIFOs ---
    b = [uniq(0, 5), uniq(1, 5)]
    await tb.load({3: b})
    o = await tb.cycle(cand=tb.cand(3, A), out_ready=0)
    assert o.out_valid == 1 and o.held == 0
    o = await tb.cycle(out_ready=0)
    assert o.held == 1
    await Timer(1, unit="ns")
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    await ReadOnly()
    assert int(dut.o_out_valid.value) == 0, "o_out_valid must be low whenever rst_n is low"
    assert int(dut.o_in_ready.value) == 0, "o_in_ready must be low whenever rst_n is low"
    assert int(dut.o_grant_held.value) == 1 and int(dut.o_head_valid.value) == 0b1000
    await Timer(1, unit="ns")
    dut.rst_n.value = 1
    o = await tb.cycle(cand=tb.cand(0, B), out_ready=1)  # no rising edge saw rst_n low
    assert (o.held, o.fire, o.out_source, o.out_desc, o.grant_ctx) == (1, 1, 3, b[0], A)
    assert o.count[3] == 2
    got = await tb.drain_all()
    assert got == [(3, b[1])]
    assert tb.model.epoch == 1 + 3, "initial reset plus three reset edges"
    assert tb.cov.reset_during_hold == 1 and tb.dropped_by_reset == 5 + 2


# Covers: SPEC §4 (only fire dequeues; selection without acceptance is not service)
@cocotb.test()
async def test_02_selection_without_ready_never_pops(dut):
    tb = await new_tb(dut)
    n = tb.n
    a0 = [uniq(i, 1) for i in range(2)]
    a2 = [uniq(0, 2)]
    await tb.load({0: a0, 2: a2})

    o = await tb.cycle(cand=tb.cand(0, 1), out_ready=0)
    assert (o.out_valid, o.fire, o.pop, o.held) == (1, 0, 0, 0)
    pushed1 = 0
    for i in range(60):
        push = {1: uniq(i, 3)} if i % 4 == 0 else None
        # The candidate walks over every source (empty and nonempty) with changing context.
        o = await tb.cycle(push=push, cand=tb.cand(i % n, i), out_ready=0)
        assert (o.out_valid, o.fire, o.pop, o.held) == (1, 0, 0, 1), f"i={i}: {o}"
        assert (o.out_source, o.out_desc, o.grant_ctx) == (0, a0[0], 1 & tb.ctx_mask)
        assert o.count[0] == 2 and o.count[2] == 1 and o.count[1] == pushed1, f"i={i}: {o.count}"
        assert all(o.count[h] == 0 for h in range(3, n))
        pushed1 += int(push is not None)
    assert pushed1 == 15
    assert tb.total_delivered == 0 and tb.cov.fires == 0 and tb.cov.stall_cycles == 61

    # The one acceptance pops exactly one descriptor: the offered one.
    o = await tb.cycle(cand=tb.cand(2, 0), out_ready=1)
    assert (o.fire, o.pop, o.out_source, o.out_desc) == (1, 0b1, 0, a0[0])
    o = await tb.cycle()
    assert o.count[:3] == [1, 15, 1] and o.held == 0
    got = per_source(await tb.drain_all(), n)
    assert got[0] == a0[1:] and got[2] == a2 and got[1] == [uniq(i, 3) for i in range(0, 60, 4)]
    assert tb.total_delivered == 2 + 1 + 15


# Covers: SPEC §4 (pop[h] = fire for the selected source only)
@cocotb.test()
async def test_03_fire_pops_exactly_the_offered_source(dut):
    tb = await new_tb(dut)
    n = tb.n
    content = {h: [uniq(0, h + 1), uniq(1, h + 1)] for h in range(n)}
    await tb.load(content)
    counts = [2] * n

    # Unlocked candidate accepted at once: exactly that source pops, every other count is untouched.
    for s in sorted(range(n), key=lambda h: (h * 5 + 3) % n):
        o = await tb.cycle(cand=tb.cand(s, s), out_ready=1)
        assert (o.fire, o.held, o.pop, o.out_source) == (1, 0, 1 << s, s), f"source {s}: {o}"
        assert o.out_desc == content[s][0] and o.grant_ctx == s & tb.ctx_mask
        assert o.count == counts
        counts[s] -= 1

    # Held grant: the fire pops the held source, never the candidate of the firing cycle.
    for a in range(n):
        b = (a + 1) % n
        o = await tb.cycle(cand=tb.cand(a, a), out_ready=0)
        assert (o.out_valid, o.held, o.out_source) == (1, 0, a)
        o = await tb.cycle(cand=tb.cand(b, ~a), out_ready=1)
        assert (o.held, o.fire, o.pop, o.out_source) == (1, 1, 1 << a, a), f"held {a}, candidate {b}: {o}"
        assert o.out_desc == content[a][1] and o.grant_ctx == a & tb.ctx_mask
        assert o.count == counts, "a source other than the offered one changed"
        counts[a] -= 1
        o = await tb.cycle()
        assert o.count == counts and o.held == 0 and o.pop == 0
    assert counts == [0] * n
    assert tb.cov.hold_fire_cand_differs == n and tb.cov.fire_sources == set(range(n))
    assert tb.cov.fires_direct == n and tb.cov.fires_held == n
    await tb.drain_all()


# Covers: SPEC §4 (during output stalls valid, all 105 bits, source and context remain stable;
#         later arrivals / candidate changes cannot preempt), §4 stall clarification
@cocotb.test()
async def test_04_long_stall_with_adversarial_candidate(dut):
    tb = await new_tb(dut)
    n, w, mask = tb.n, tb.ctx_w, tb.ctx_mask
    rng = random.Random(f"{run_seed()}:long_stall:{n}")
    H, E = n - 1, 2  # held source, a source kept empty
    q = {h: deque(uniq(i, h + 1) for i in range(3)) for h in range(n) if h != E}
    q[E] = deque()
    await tb.load({h: list(v) for h, v in q.items() if v})
    others = [h for h in range(n) if h not in (H, E)]
    X = mask
    held_desc = q[H][0]

    o = await tb.cycle(cand=tb.cand(H, X), out_ready=0)
    assert (o.out_valid, o.held, o.out_source, o.grant_ctx, o.out_desc) == (1, 0, H, X, held_desc)

    STALL = 400
    for i in range(STALL):
        k = i % 4
        raw = None
        if k == 0:  # no candidate at all (pins still wiggle)
            cand, raw = NO_CANDIDATE, (rng.randrange(n), rng.getrandbits(w))
        elif k == 1:  # another source with a valid head
            cand = tb.cand(others[(i // 4) % len(others)], rng.getrandbits(w))
        elif k == 2:  # an empty source
            cand = tb.cand(E, rng.getrandbits(w))
        else:  # the held source itself with a different context
            cand = tb.cand(H, X ^ 1 ^ (rng.getrandbits(w) & ~1))
        o = await tb.cycle(cand=cand, raw_cand=raw, out_ready=0)
        assert (o.out_valid, o.held, o.fire, o.pop) == (1, 1, 0, 0), f"stall cycle {i}: {o}"
        assert o.out_desc == held_desc, f"stall cycle {i}: descriptor bits changed {o.out_desc ^ held_desc:#x}"
        assert (o.out_source, o.grant_ctx) == (H, X), f"stall cycle {i}: grant changed"
    cov = tb.cov
    assert cov.max_hold_len == STALL and cov.holds == 1
    assert cov.hold_cand_invalid == 100 and cov.hold_cand_other_nonempty == 100
    assert cov.hold_cand_empty == 100 and cov.hold_cand_same_src_other_ctx == 100

    # The eventual fire carries the held source/context although the candidate names another one.
    other = others[0]
    o = await tb.cycle(cand=tb.cand(other, X ^ 1), out_ready=1)
    assert (o.fire, o.held, o.out_source, o.grant_ctx, o.out_desc, o.pop) == (1, 1, H, X, held_desc, 1 << H)
    q[H].popleft()
    # ... and the very next cycle is an unlocked selection again.
    o = await tb.cycle(cand=tb.cand(other, X ^ 1), out_ready=1)
    assert (o.fire, o.held, o.out_source, o.grant_ctx, o.out_desc) == (1, 0, other, X ^ 1, q[other][0])
    q[other].popleft()

    # --- a randomized set of stall lengths, with arrivals and a fully random candidate ----------
    lengths = [1, 2, 3] + [rng.randint(4, 80) for _ in range(12)]
    rng.shuffle(lengths)
    serial = 0
    for length in lengths:
        nonempty = [h for h in range(n) if q[h]]
        if not nonempty:
            serial += 1
            q[0].append(uniq(serial, 200))
            await tb.load({0: [q[0][-1]]})
            nonempty = [0]
        src, ctx = rng.choice(nonempty), rng.getrandbits(w)
        want = q[src][0]
        for j in range(length + 1):  # `length` stalled cycles, then the accepting cycle
            if j == 0:
                cand, raw = tb.cand(src, ctx), None
            elif rng.random() < 0.25:
                cand, raw = NO_CANDIDATE, (rng.randrange(n), rng.getrandbits(w))
            else:
                cand, raw = tb.cand(rng.randrange(n), rng.getrandbits(w)), None
            push = {}
            if rng.random() < 0.3:
                h = rng.randrange(n)
                serial += 1
                push[h] = uniq(serial, 201)
            o = await tb.cycle(push=push, cand=cand, raw_cand=raw, out_ready=int(j == length))
            for h, d in push.items():
                accepted = len(q[h]) < DEPTH
                assert (o.push >> h) & 1 == int(accepted)
                if accepted:
                    q[h].append(d)
            assert (o.out_valid, o.held, o.fire) == (1, int(j > 0), int(j == length)), f"len {length} j {j}: {o}"
            assert (o.out_source, o.grant_ctx, o.out_desc) == (src, ctx, want), f"len {length} j {j}: {o}"
        q[src].popleft()
    assert cov.holds == 1 + len(lengths)
    got = per_source(await tb.drain_all(), n)
    assert got == {h: list(q[h]) for h in range(n)}


# Covers: SPEC §4 (FIFOs keep accepting input during a downstream stall; later arrivals cannot
#         preempt the pending transfer; per-source order; full refuses push even when head fires)
@cocotb.test()
async def test_05_pushes_during_stall_fill_to_full(dut):
    tb = await new_tb(dut)
    n, ALL = tb.n, tb.all_src
    A = tb.ctx_mask
    B = A ^ 1
    H = 1
    first = uniq(0, 50)
    await tb.load({H: [first]})
    exp = {h: [] for h in range(n)}
    exp[H].append(first)

    o = await tb.cycle(cand=tb.cand(H, A), out_ready=0)
    assert o.out_valid == 1 and o.held == 0
    for i in range(20):
        pushes = {h: uniq(i, h + 1) for h in range(n)}
        latest = (H + 1 + i) % n
        latest = latest if latest != H else (H + 1) % n
        o = await tb.cycle(push=pushes, cand=tb.cand(latest, B), out_ready=0)
        assert (o.out_valid, o.held, o.fire, o.pop) == (1, 1, 0, 0), f"i={i}: {o}"
        assert (o.out_desc, o.out_source, o.grant_ctx) == (first, H, A), f"i={i}: pending transfer changed"
        for h in range(n):
            room = len(exp[h]) < DEPTH
            assert o.count[h] == len(exp[h])
            assert (o.in_ready >> h) & 1 == int(room) and (o.push >> h) & 1 == int(room), f"i={i} h={h}"
            if room:
                exp[h].append(pushes[h])
    assert all(len(exp[h]) == DEPTH for h in range(n))
    o = await tb.cycle(cand=tb.cand(0, B), out_ready=0)
    assert o.in_ready == 0 and o.count == [DEPTH] * n and o.held == 1 and o.out_desc == first
    assert tb.cov.hold_push_held_src == 15 and tb.cov.hold_all_full >= 1 and tb.cov.hold_held_src_full >= 1

    # Fire with every producer still valid: the held (oldest) entry leaves, no full FIFO accepts.
    late = {h: uniq(99, h + 1) for h in range(n)}
    o = await tb.cycle(push=late, cand=tb.cand(0, B), out_ready=1)
    assert (o.fire, o.out_desc, o.out_source, o.grant_ctx, o.pop) == (1, first, H, A, 1 << H)
    assert o.push == 0 and o.in_ready == 0, "a full FIFO accepted on the edge its head fired"
    o = await tb.cycle(push=late)
    assert o.in_ready == 1 << H and o.push == 1 << H and o.count[H] == DEPTH - 1 and o.held == 0
    exp[H] = exp[H][1:] + [late[H]]
    o = await tb.cycle()
    assert o.in_ready == 0 and o.count == [DEPTH] * n
    assert tb.cov.fire_full_push_refused == 1 and tb.cov.ready_after_full_fire == 1

    got = per_source(await tb.drain_all(), n)
    assert got == exp, "per-source FIFO order was not preserved across the stall"
    assert tb.total_delivered == n * DEPTH + 1


# Covers: SPEC §4 (no empty bypass: eligible no earlier than c+1), §5 (no extra mandatory output
#         stage: eligible exactly at c+1)
@cocotb.test()
async def test_06_next_cycle_eligibility_no_extra_stage(dut):
    tb = await new_tb(dut)
    n, ALL = tb.n, tb.all_src

    for s in range(n):
        d = uniq(s, 1)
        # Cycle c: accepted, but neither offered nor fired although candidate and sink want it.
        o = await tb.cycle(push={s: d}, cand=tb.cand(s, s), out_ready=1)
        assert (o.push, o.out_valid, o.fire, o.pop, o.head_valid) == (1 << s, 0, 0, 0, 0), f"s={s}: {o}"
        # Cycle c+1: offered and fired - exactly one cycle of latency, no extra stage, no hold.
        o = await tb.cycle(cand=tb.cand(s, s), out_ready=1)
        assert (o.held, o.out_valid, o.fire, o.pop) == (0, 1, 1, 1 << s), f"s={s}: not eligible at c+1: {o}"
        assert (o.out_desc, o.out_source, o.count[s]) == (d, s, 1)
        o = await tb.cycle(cand=tb.cand(s, s), out_ready=1)
        assert o.out_valid == 0 and o.count == [0] * n
    assert tb.cov.min_wait == 1 and tb.cov.push_into_empty_with_cand == n and tb.cov.holds == 0

    # Offered at c+1 without acceptance, fired at c+2 from the hold.
    d = uniq(0, 2)
    o = await tb.cycle(push={3: d}, cand=tb.cand(3, 1), out_ready=0)
    assert o.out_valid == 0
    o = await tb.cycle(cand=tb.cand(3, 1), out_ready=0)
    assert (o.out_valid, o.held, o.out_desc) == (1, 0, d)
    o = await tb.cycle(out_ready=1)
    assert (o.held, o.fire, o.out_desc, o.out_source) == (1, 1, d, 3)

    # Nonempty FIFO: the head fires while a new entry arrives; that entry fires the next cycle.
    d0, d1 = uniq(1, 2), uniq(2, 2)
    await tb.cycle(push={0: d0})
    o = await tb.cycle(push={0: d1}, cand=tb.cand(0, 0), out_ready=1)
    assert (o.fire, o.out_desc, o.push) == (1, d0, 1)
    o = await tb.cycle(cand=tb.cand(0, 0), out_ready=1)
    assert (o.fire, o.out_desc, o.count[0]) == (1, d1, 1)
    o = await tb.cycle(cand=tb.cand(0, 0), out_ready=1)
    assert o.out_valid == 0

    # Every source pushed on one edge: none is offered that cycle, all are eligible the next.
    pushes = {h: uniq(h, 3) for h in range(n)}
    o = await tb.cycle(push=pushes, cand=tb.cand(n - 1, 0), out_ready=1)
    assert o.out_valid == 0 and o.push == ALL
    for h in reversed(range(n)):
        o = await tb.fire(h)
        assert (o.out_desc, o.out_source) == (pushes[h], h)
        if h == n - 1:
            assert o.head_valid == ALL and o.count == [1] * n
    await tb.drain_all()


# Covers: SPEC §4 (at most one fire per edge, one per cycle achievable), §5 (no control bubbles
#         from the common output path)
@cocotb.test()
async def test_07_back_to_back_fires_and_streaming(dut):
    tb = await new_tb(dut)
    n = tb.n
    content = {h: [uniq(i, h + 1) for i in range(4)] for h in range(n)}
    await tb.load(content)

    # A different source on every consecutive cycle, each visited twice.
    for i in range(2 * n):
        s = (i * 3) % n
        o = await tb.cycle(cand=tb.cand(s, i), out_ready=1)
        assert (o.fire, o.held, o.out_source, o.pop) == (1, 0, s, 1 << s), f"i={i}: {o}"
        assert o.out_desc == content[s][i // n] and o.grant_ctx == i & tb.ctx_mask
    # The same source on consecutive cycles.
    for s in range(n):
        for k in (2, 3):
            o = await tb.cycle(cand=tb.cand(s, k), out_ready=1)
            assert (o.fire, o.out_source, o.out_desc) == (1, s, content[s][k])
    assert tb.cov.fires == 4 * n and tb.cov.b2b_fires == 4 * n - 1, "a bubble appeared between fires"
    assert tb.cov.b2b_switch >= 2 * n - 1 and tb.cov.stall_cycles == 0 and tb.cov.holds == 0
    o = await tb.cycle(cand=tb.cand(0, 0), out_ready=1)
    assert o.out_valid == 0 and o.count == [0] * n

    # Streaming through one FIFO: push and fire on every edge, occupancy stays 1, latency 1.
    s = n - 1
    stream = [uniq(i, 40) for i in range(48)]
    o = await tb.cycle(push={s: stream[0]}, cand=tb.cand(s, 0), out_ready=1)
    assert o.out_valid == 0
    for i in range(1, len(stream)):
        o = await tb.cycle(push={s: stream[i]}, cand=tb.cand(s, i), out_ready=1)
        assert (o.fire, o.out_desc, o.count[s], o.push) == (1, stream[i - 1], 1, 1 << s), f"i={i}: {o}"
    o = await tb.cycle(cand=tb.cand(s, 0), out_ready=1)
    assert (o.fire, o.out_desc) == (1, stream[-1])
    assert tb.cov.fire_with_push_same_src == len(stream) - 1 and tb.cov.min_wait == 1
    await tb.drain_all()


# Covers: SPEC §4 (in_ready from beginning-of-cycle occupancy only; full refuses push even when
#         its head fires; simultaneous push+pop table)
@cocotb.test()
async def test_08_full_plus_pop_readiness_and_push_pop(dut):
    tb = await new_tb(dut)
    n, ALL = tb.n, tb.all_src
    S = 1
    bit = 1 << S
    full = [uniq(i, 1) for i in range(DEPTH)]
    await tb.load({S: full})
    o = await tb.cycle()
    assert o.in_ready == ALL & ~bit and o.count[S] == DEPTH

    # Unlocked offer accepted while full and in_valid: head leaves, push refused, ready next cycle.
    x0, x1 = uniq(0, 2), uniq(1, 2)
    o = await tb.cycle(push={S: x0}, cand=tb.cand(S, 0), out_ready=1)
    assert (o.fire, o.out_desc, o.pop) == (1, full[0], bit)
    assert o.in_ready & bit == 0 and o.push == 0 and o.count[S] == DEPTH, f"full+pop accepted a push: {o}"
    o = await tb.cycle(push={S: x0})
    assert o.in_ready & bit and o.push == bit and o.count[S] == DEPTH - 1
    o = await tb.cycle()
    assert o.in_ready & bit == 0 and o.count[S] == DEPTH

    # The same through a held grant.
    o = await tb.cycle(push={S: x1}, cand=tb.cand(S, 1), out_ready=0)
    assert (o.out_valid, o.held, o.push) == (1, 0, 0)
    o = await tb.cycle(push={S: x1}, out_ready=0)
    assert (o.held, o.push, o.in_ready & bit) == (1, 0, 0)
    o = await tb.cycle(push={S: x1}, out_ready=1)
    assert (o.held, o.fire, o.out_desc, o.push, o.in_ready & bit) == (1, 1, full[1], 0, 0)
    o = await tb.cycle(push={S: x1})
    assert o.push == bit and o.count[S] == DEPTH - 1 and o.held == 0
    exp = full[2:] + [x0, x1]
    assert tb.cov.fire_full_push_refused == 2 and tb.cov.ready_after_full_fire == 2

    # Simultaneous push+pop on a nonempty, nonfull FIFO: occupancy and order unchanged.
    for _ in range(2):
        o = await tb.fire(S)
        assert o.out_desc == exp.pop(0)
    for i in range(40):  # 40 > DEPTH: the storage wraps more than twice
        y = uniq(i, 3)
        o = await tb.cycle(push={S: y}, cand=tb.cand(S, i), out_ready=1)
        assert (o.fire, o.push, o.count[S], o.in_ready & bit) == (1, bit, DEPTH - 2, bit), f"i={i}: {o}"
        assert o.out_desc == exp.pop(0)
        exp.append(y)
    assert tb.cov.fire_with_push_same_src == 40
    o = await tb.cycle()
    assert o.count[S] == DEPTH - 2
    got = await tb.drain_all()
    assert got == [(S, d) for d in exp]


# Covers: SPEC §4 (out_valid needs a selected valid head; no service, no hold without an offer)
@cocotb.test()
async def test_09_empty_or_invalid_candidate_makes_no_offer(dut):
    tb = await new_tb(dut)
    n = tb.n
    A = tb.ctx_mask
    B = A ^ 1
    d0 = uniq(0, 1)
    await tb.load({0: [d0]})

    # Candidate names an empty source while another source has a valid head.
    for ready in (0, 1):
        for _ in range(5):
            o = await tb.cycle(cand=tb.cand(1, A), out_ready=ready)
            assert (o.out_valid, o.fire, o.pop, o.held) == (0, 0, 0, 0), f"ready={ready}: {o}"
            assert o.count[0] == 1
    # cand_valid=0 while the source/context pins point at every source, including the nonempty one.
    for ready in (0, 1):
        for src in range(n):
            o = await tb.cycle(cand=NO_CANDIDATE, raw_cand=(src, A), out_ready=ready)
            assert (o.out_valid, o.fire, o.pop, o.held) == (0, 0, 0, 0), f"src={src} ready={ready}: {o}"
            assert o.count[0] == 1

    # Candidate names an empty source on the very edge that source gets its first entry: the
    # un-offered selection must not turn into a hold.
    d2 = uniq(0, 2)
    o = await tb.cycle(push={2: d2}, cand=tb.cand(2, A), out_ready=0)
    assert o.out_valid == 0 and o.push == 0b100
    o = await tb.cycle(out_ready=0)
    assert (o.held, o.out_valid, o.count[2]) == (0, 0, 1)
    o = await tb.cycle(out_ready=1)
    assert (o.held, o.out_valid, o.fire) == (0, 0, 0)
    cov = tb.cov
    assert cov.holds == 0 and cov.stall_cycles == 0 and cov.fires == 0
    assert cov.unheld_cand_empty == 10 + 1 and cov.unheld_cand_invalid >= 2 * n

    o = await tb.fire(0, B)
    assert (o.out_desc, o.held, o.grant_ctx) == (d0, 0, B)
    o = await tb.fire(2, B)
    assert o.out_desc == d2
    await tb.drain_all()


# Covers: SPEC §4-5 (an offered transfer is retained if stalled; held-grant validity is cleared
#         only by its fire or by reset). The selected-head-valid invariant is checked by the
#         harness on every held cycle of every test.
@cocotb.test()
async def test_10_hold_released_only_by_fire_or_reset(dut):
    tb = await new_tb(dut)
    n = tb.n
    A = tb.ctx_mask
    B = A ^ 1
    content = {0: [uniq(i, 1) for i in range(3)], 1: [uniq(i, 2) for i in range(2)], 3: [uniq(0, 4)]}
    await tb.load(content)

    # 1) The candidate disappears, then names another nonempty source: the grant stays held.
    o = await tb.cycle(cand=tb.cand(0, A), out_ready=0)
    assert o.out_valid == 1 and o.held == 0
    for i in range(12):
        cand = NO_CANDIDATE if i < 6 else tb.cand(1, B)
        o = await tb.cycle(cand=cand, out_ready=0)
        assert (o.held, o.out_valid, o.out_source, o.grant_ctx, o.out_desc) == (1, 1, 0, A, content[0][0])

    # 2) Released by its fire; the next cycle honours the new candidate at once.
    o = await tb.cycle(out_ready=1)
    assert (o.held, o.fire, o.out_source, o.out_desc) == (1, 1, 0, content[0][0])
    o = await tb.cycle(cand=tb.cand(1, B), out_ready=0)
    assert (o.held, o.out_valid, o.out_source, o.grant_ctx, o.out_desc) == (0, 1, 1, B, content[1][0])
    o = await tb.cycle(cand=tb.cand(0, A), out_ready=0)
    assert (o.held, o.out_source, o.grant_ctx) == (1, 1, B)

    # 3) Released by reset.
    o = await tb.cycle(cand=tb.cand(0, A), out_ready=0, rst_n=0)
    assert o.held == 1 and o.out_valid == 0
    o = await tb.cycle(cand=tb.cand(0, A), out_ready=0)
    assert (o.held, o.out_valid, o.head_valid) == (0, 0, 0) and o.count == [0] * n

    # 4) Held grant on a single-entry source: the fire empties the source and releases the hold.
    d = uniq(0, 5)
    await tb.load({3: [d]})
    o = await tb.cycle(cand=tb.cand(3, A), out_ready=0)
    o = await tb.cycle(cand=tb.cand(3, A), out_ready=0)
    assert (o.held, o.out_valid, o.count[3]) == (1, 1, 1)
    o = await tb.cycle(cand=tb.cand(3, A), out_ready=1)
    assert (o.held, o.fire, o.out_desc) == (1, 1, d)
    for ready in (1, 0, 0):
        o = await tb.cycle(cand=tb.cand(3, A), out_ready=ready)
        assert (o.held, o.out_valid, o.head_valid) == (0, 0, 0), f"hold outlived its fire: {o}"

    # 5) Holds of every length 1..8 ending in a one-cycle ready pulse; never held after the fire.
    seq = [uniq(i, 6) for i in range(8)]
    await tb.load({2: seq})
    holds_before = tb.cov.holds
    for k in range(8):
        o = await tb.cycle(cand=tb.cand(2, k), out_ready=0)
        assert (o.held, o.out_valid) == (0, 1)
        for _ in range(k):
            o = await tb.cycle(out_ready=0)
            assert (o.held, o.out_valid, o.out_desc) == (1, 1, seq[k])
        o = await tb.cycle(out_ready=1)
        assert (o.held, o.fire, o.out_desc, o.grant_ctx) == (1, 1, seq[k], k & tb.ctx_mask)
        o = await tb.cycle()
        assert (o.held, o.out_valid) == (0, 0)
    assert tb.cov.holds - holds_before == 8 and tb.cov.fire_last_entry >= 2
    await tb.drain_all()


# Covers: SPEC §4 (pending transfer's class/quota context remains stable during a stall) and the
#         stall clarification (classifications may change at a window edge; those updates cannot
#         alter the held output)
@cocotb.test()
async def test_11_context_change_for_same_source_during_stall(dut):
    tb = await new_tb(dut)
    w, mask = tb.ctx_w, tb.ctx_mask
    S = tb.n - 2
    A = mask
    B = A ^ 1
    descs = [uniq(i, 1) for i in range(4)]
    await tb.load({S: descs})
    q = deque(descs)

    # The stalled grant was offered with context A; from then on the candidate for the SAME source
    # carries other contexts (a later classification), while new requests keep arriving.
    o = await tb.cycle(cand=tb.cand(S, A), out_ready=0)
    assert (o.out_valid, o.held, o.grant_ctx) == (1, 0, A)
    other_ctx = [c for c in range(1 << w) if c != A]
    for i in range(64):
        push = None
        if i < 5:
            push = {S: uniq(i, 2)}
            q.append(push[S])
        o = await tb.cycle(push=push, cand=tb.cand(S, other_ctx[i % len(other_ctx)]), out_ready=0)
        assert (o.held, o.out_valid, o.out_source, o.grant_ctx, o.out_desc) == (1, 1, S, A, descs[0]), (
            f"i={i}: context/descriptor of the pending transfer changed: {o}"
        )
    assert tb.cov.hold_cand_same_src_other_ctx == 64
    # The fire carries the originally latched context ...
    o = await tb.cycle(cand=tb.cand(S, B), out_ready=1)
    assert (o.held, o.fire, o.grant_ctx, o.out_desc) == (1, 1, A, q.popleft())
    assert o.edge.fired.ctx == A
    # ... and the next transfer of the same source uses the then-current context.
    o = await tb.cycle(cand=tb.cand(S, B), out_ready=1)
    assert (o.held, o.fire, o.grant_ctx, o.out_desc) == (0, 1, B, q.popleft())

    # Context boundary values, as an immediate transfer and as a held transfer whose candidate
    # context is inverted before the fire.
    vals = sorted({0, 1, mask, max(mask - 1, 0), mask >> 1, min((mask >> 1) + 1, mask)})
    serial = 0
    for v in vals:
        o = await tb.cycle(cand=tb.cand(S, v), out_ready=1)
        assert (o.fire, o.held, o.grant_ctx, o.out_desc) == (1, 0, v, q.popleft())
        o = await tb.cycle(cand=tb.cand(S, v), out_ready=0)
        assert (o.out_valid, o.grant_ctx) == (1, v)
        o = await tb.cycle(cand=tb.cand(S, v ^ mask), out_ready=0)
        assert (o.held, o.grant_ctx) == (1, v)
        o = await tb.cycle(cand=tb.cand(S, v ^ mask), out_ready=1)
        assert (o.fire, o.held, o.grant_ctx, o.out_desc) == (1, 1, v, q.popleft())
        new = [uniq(serial, 3), uniq(serial + 1, 3)]
        serial += 2
        await tb.load({S: new})
        q.extend(new)
    assert tb.cov.ctx_values >= set(vals)
    got = await tb.drain_all()
    assert got == [(S, d) for d in q]


# Covers: SPEC §5 (one common FIFO implementation and one common output/stall controller, no
#         extra output stage) - the fixture really contains the common blocks and nothing else.
@cocotb.test()
async def test_12_fixture_structure_real_common_blocks(dut):
    tb = await new_tb(dut)
    n = tb.n
    paths = hierarchy_paths(dut)
    names = [p for p, _kind in paths]
    dut._log.info("hierarchy: %d objects, e.g. %s", len(names), names[:12])

    fifo_idx = set()
    for p in names:
        m = re.search(r"gen_fifo\[(\d+)\]\.u_fifo$", p)
        if m:
            fifo_idx.add(int(m.group(1)))
    assert fifo_idx == set(range(n)), f"expected {n} cxl_desc_fifo instances, found indices {sorted(fifo_idx)}"
    holds = [p for p in names if p.endswith(".u_out_hold")]
    assert len(holds) == 1, f"expected exactly one cxl_out_hold instance: {holds}"
    assert not any("gen_bad_n_src" in p for p in names)

    desc_mems = [p for p in names if p.endswith(".desc_mem_q")]
    ts_mems = [p for p in names if p.endswith(".ts_mem_q")]
    assert len(desc_mems) == n, f"one descriptor store per source expected: {desc_mems}"
    assert len(ts_mems) == (n if tb.ts_en else 0), f"TS_EN={int(tb.ts_en)}: timestamp stores {ts_mems}"
    mem0 = dut.gen_fifo[0].u_fifo.desc_mem_q
    assert len(mem0) == DEPTH and len(mem0[0]) == DESC_W

    # State of the hold controller: the held-grant record only. No descriptor copy and no output
    # register stage exist anywhere between the FIFO heads and the output pins.
    hold_regs = sorted(p.rsplit(".", 1)[1] for p in names if ".u_out_hold." in p and p.endswith("_q"))
    assert hold_regs == ["held_ctx_q", "held_q", "held_source_q"], f"hold controller state: {hold_regs}"
    assert len(dut.u_out_hold.held_source_q) == tb.src_w and len(dut.u_out_hold.held_ctx_q) == tb.ctx_w
    # Registers anywhere in the design: FIFO control/storage and the held-grant record, nothing else.
    allowed = {"count_q", "wr_ptr_q", "rd_ptr_q", "desc_mem_q", "ts_mem_q"} | set(hold_regs)
    regs = {p.rsplit(".", 1)[1] for p in names if p.endswith("_q")}
    assert regs <= allowed, f"unexpected state in the fixture: {sorted(regs - allowed)}"
    top_level_state = [p for p in names if p.endswith("_q") and ".u_out_hold." not in p and ".u_fifo." not in p]
    assert not top_level_state, f"the fixture itself must hold no state: {top_level_state}"

    # Smoke through every source so that the structural test also moves data.
    for s in range(n):
        d = uniq(s, 7)
        await tb.cycle(push={s: d})
        o = await tb.fire(s, s)
        assert (o.out_desc, o.out_source) == (d, s)
    await tb.drain_all()


# ----- constrained-random traffic ---------------------------------------------------------------

# Per-source push probability per traffic phase, as a function of N (service is 1 per cycle).
PUSH_PROFILES = {
    "idle": lambda rng, n: [0.0] * n,
    "light": lambda rng, n: [0.5 / n] * n,
    "balanced": lambda rng, n: [0.95 / n] * n,
    "heavy": lambda rng, n: [2.0 / n] * n,
    "saturating": lambda rng, n: [1.0] * n,
    "skewed": lambda rng, n: [1.0 if h == rng.randrange(n) else 0.3 / n for h in range(n)],
    "half_sources": lambda rng, n: [0.8 if h % 2 else 0.0 for h in range(n)],
}
# Candidate mix: (p no candidate, p any source, p an empty source, p the held source); the rest
# of the probability mass picks a uniformly random nonempty source.
CAND_MIXES = [
    (0.10, 0.10, 0.10, 0.10),
    (0.30, 0.20, 0.20, 0.10),
    (0.02, 0.03, 0.00, 0.05),  # nearly work-conserving: long back-to-back runs
    (0.15, 0.30, 0.10, 0.30),
]


def gen_candidate(rng: random.Random, tb: CtrlTb, mix):
    """Adversarial candidate from beginning-of-cycle state only (the model has been committed up
    to the previous edge). It is drawn BEFORE this cycle's out_ready is decided."""
    n, m = tb.n, tb.model
    p_none, p_any, p_empty, p_held = mix
    ctx = rng.getrandbits(tb.ctx_w)
    r = rng.random()
    if r < p_none:
        return NO_CANDIDATE, (rng.randrange(n), ctx)
    r -= p_none
    if r < p_any:
        return Candidate(True, rng.randrange(n), ctx), None
    r -= p_any
    empty = m.empty_sources()
    if r < p_empty and empty:
        return Candidate(True, rng.choice(empty), ctx), None
    r -= p_empty
    if r < p_held and m.held is not None:
        return Candidate(True, m.held.source, ctx), None
    nonempty = m.nonempty_sources()
    if nonempty:
        return Candidate(True, rng.choice(nonempty), ctx), None
    return Candidate(True, rng.randrange(n), ctx), None


async def run_random(dut, label, profiles, ready_probs, p_reset, p_long_stall, cycles=RANDOM_CYCLES) -> CtrlTb:
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:{label}:{n}:{tb.ctx_w}")
    pending = [None] * n  # descriptor each producer holds valid until it is pushed (spec 4)
    serial = 0
    reset_left = stall_left = phase_left = 0
    resets = long_stalls = 0
    p_push, p_ready, mix = [0.0] * n, 1.0, CAND_MIXES[0]

    for _ in range(cycles):
        if phase_left == 0:
            p_push = PUSH_PROFILES[rng.choice(profiles)](rng, n)
            p_ready = rng.choice(ready_probs)
            mix = rng.choice(CAND_MIXES)
            phase_left = rng.randint(100, 500)
        phase_left -= 1

        if reset_left == 0 and rng.random() < p_reset:
            reset_left = rng.randint(1, 3)
            resets += 1
        rst_n = 0 if reset_left else 1
        reset_left = max(0, reset_left - 1)

        for h in range(n):
            if pending[h] is None and rng.random() < p_push[h]:
                serial += 1
                pending[h] = rnd_desc(rng, serial)
        pushes = {h: d for h, d in enumerate(pending) if d is not None}

        cand, raw = gen_candidate(rng, tb, mix)  # before, and independent of, out_ready

        if stall_left:
            stall_left -= 1
            ready = 0
        elif rng.random() < p_long_stall:
            stall_left = rng.randint(100, 400)
            long_stalls += 1
            ready = 0
        else:
            ready = int(rng.random() < p_ready)

        o = await tb.cycle(push=pushes, cand=cand, raw_cand=raw, out_ready=ready, rst_n=rst_n)
        for h in range(n):
            if (o.push >> h) & 1:
                pending[h] = None

    await tb.drain_all()
    cov = tb.cov
    dut._log.info(
        "random[%s]: resets=%d long_stalls=%d generated=%d dropped_by_reset=%d epochs=%d %s",
        label, resets, long_stalls, serial, tb.dropped_by_reset, tb.epochs_closed, cov.summary(),
    )  # fmt: skip
    assert cov.cycles >= cycles
    tb.assert_conserved_and_empty()
    return tb


ALL_PROFILES = list(PUSH_PROFILES)


# Covers: SPEC §4-5 (whole common contract under mixed random traffic and candidates)
@cocotb.test()
async def test_13_random_mixed_traffic(dut):
    tb = await run_random(
        dut, "mixed", ALL_PROFILES, [1.0, 0.9, 0.5, 0.2, 0.05], p_reset=1 / 1500, p_long_stall=1 / 800
    )
    cov, every = tb.cov, set(range(tb.n))
    assert cov.fires > 500 and cov.pushes > 500 and cov.holds > 50
    assert cov.fires_direct > 0 and cov.fires_held > 0
    assert cov.hold_cand_invalid > 0 and cov.hold_cand_other_nonempty > 0 and cov.hold_cand_empty > 0
    assert cov.hold_cand_same_src_other_ctx > 0 and cov.hold_fire_cand_differs > 0
    assert cov.hold_push_any > 0 and cov.hold_push_held_src > 0
    assert cov.b2b_fires > 0 and cov.b2b_switch > 0 and cov.fire_with_push_same_src > 0
    assert cov.unheld_cand_empty > 0 and cov.unheld_cand_invalid > 0 and cov.fire_last_entry > 0
    assert cov.min_wait == 1, "coverage: the 1-cycle minimum latency never occurred"
    assert cov.fire_sources == every and cov.held_sources == every
    assert len(cov.ctx_values) >= 2


# Covers: SPEC §4 (long stalls with saturating producers: FIFOs fill, full+fire refuses push)
@cocotb.test()
async def test_14_random_saturating_long_stalls(dut):
    tb = await run_random(
        dut, "saturating", ["saturating", "heavy", "skewed"], [1.0, 0.6, 0.1], p_reset=0.0, p_long_stall=1 / 300
    )
    cov = tb.cov
    assert cov.max_hold_len >= 100 and cov.holds > 20 and cov.fires > 500
    assert cov.hold_all_full > 0 and cov.hold_held_src_full > 0
    assert cov.fire_full_push_refused > 0 and cov.ready_after_full_fire == cov.fire_full_push_refused
    assert cov.hold_push_held_src > 0 and cov.hold_cand_other_nonempty > 0
    assert DEPTH in cov.occupancies and cov.b2b_fires > 0
    assert cov.reset_cycles == 0 and tb.dropped_by_reset == 0
    assert tb.total_accepted == tb.total_delivered, "without resets everything accepted must be delivered"


# Covers: SPEC §5 (reset at arbitrary points incl. mid-hold; every epoch is fresh)
@cocotb.test()
async def test_15_random_with_frequent_resets(dut):
    tb = await run_random(
        dut, "resets", ALL_PROFILES, [1.0, 0.7, 0.3, 0.05], p_reset=1 / 150, p_long_stall=1 / 600
    )
    cov = tb.cov
    assert cov.reset_cycles >= 15 and tb.epochs_closed >= 15
    assert cov.reset_during_hold > 0 and cov.reset_nonempty > 0 and tb.dropped_by_reset > 0
    assert cov.fires > 200 and cov.holds > 20 and cov.fires_held > 0
    assert tb.total_accepted == tb.total_delivered + tb.dropped_by_reset
