"""Cycle-exact cocotb tests of switch_top with POLICY=1 (Round Robin), milestone M4.

N_SRC = 4, 8, 16; RR_QUANTUM = 10 (primary; the RTL default, run_verify M4) and 1 (supplementary
D32, run_verify M4-q1, a separate scope). Run through scripts/run_verify.sh (it builds the design
and exports CXL_PARAM_*).

Every cycle of every test goes through sim/common/switch_rr_tb.SwitchRrTb, which compares all pins,
the observable internal state and the RR polling state (ptr_q, used_q) with the independent abstract
turn-record oracle refc/cxl_model/rr_model.RrSwitchModel, applies model-free pin rules (in_ready
from beginning-of-cycle occupancy, inactive in reset, no control-only bubbles, stall stability of
valid/105 bits/source, hold provenance, spec 7 restated over the pin history), keeps a pin-level
conservation/order/integrity/sideband scoreboard, checks the spec 4 producer hold on the observed
input pins and matches TB-only tagged responses exactly once. On top of that each directed test
asserts literal expectations written from the spec for both approved quanta, so a defect shared by
model and RTL would still be caught.

Spec references are to specs/CXL_SPEC.md v1.0 (section 7 = Round Robin) and specs/DECISIONS.md.
"""

from __future__ import annotations

import random
import re

from hier_util import hierarchy_paths
from switch_rr_tb import DESC_MASK, DESC_W, SwitchRrTb, rr_turn_summary, run_seed, write_json
from traffic_trace import make_trace

import cocotb
from cocotb.triggers import ReadOnly, Timer

TAG_LSB, ADDR_LSB, OPCODE_LSB, LENGTH_LSB = 73, 41, 40, 32
SHORT_RANDOM_CYCLES = 12000
DEPTH_D16 = 16  # spec: D16 FIFO per source


def mk_desc(tag: int, addr: int, opcode: int, length: int, payload: int) -> int:
    assert tag < (1 << 32) and addr < (1 << 32) and opcode < 2 and length < 256 and payload < (1 << 32)
    return (tag << TAG_LSB) | (addr << ADDR_LSB) | (opcode << OPCODE_LSB) | (length << LENGTH_LSB) | payload


def uniq(i: int, salt: int = 0) -> int:
    """A distinct descriptor (distinct Tag) per (index, salt) with every field populated."""
    assert 0 <= i < 0x10000 and 0 <= salt < 0x100
    return mk_desc(
        tag=(0xB6000000 + salt * 0x10000 + i) & 0xFFFFFFFF,
        addr=(0x20000000 + i * 0x01010101 + salt * 0x00310000) & 0xFFFFFFFF,
        opcode=(i ^ salt) & 1,
        length=(i * 7 + salt * 3 + 3) & 0xFF,
        payload=((i + 1) * 0x9E3779B1 + salt * 0x85EBCA6B) & 0xFFFFFFFF,
    )


async def new_tb(dut, label: str, **kw) -> SwitchRrTb:
    tb = SwitchRrTb(dut, label, **kw)
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) N_SRC=%d POLICY=%d RR_QUANTUM=%d DEPTH=%d DESC_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.n, tb.policy, tb.q, tb.depth, tb.desc_w,
    )  # fmt: skip
    await tb.start()
    return tb


async def load_seq(tb: SwitchRrTb, schedule, out_ready: int = 0):
    """schedule: list of {source: desc} per cycle. Every push must be accepted."""
    obs = []
    for pushes in schedule:
        o = await tb.cycle(push=pushes, out_ready=out_ready)
        for h in pushes:
            assert (o.push >> h) & 1, f"cycle {o.cycle}: push into source {h} was not accepted"
        obs.append(o)
    return obs


async def serve(tb: SwitchRrTb, count: int):
    """ready=1 for ``count`` cycles, each must fire. Returns [(source, desc)]."""
    got = []
    for _ in range(count):
        o = await tb.cycle(out_ready=1)
        assert o.fire == 1, f"cycle {o.cycle}: expected a fire (work exists, ready=1)"
        got.append((o.out_source, o.out_desc))
    return got


def state(o) -> tuple:
    """RR polling state during the cycle of ``o``: (ptr_q, used_q)."""
    return (o.i_ptr, o.i_used)


def per_q(tb: SwitchRrTb, table: dict):
    """Literal expectation for the quantum under test (10 primary, 1 supplementary)."""
    assert tb.q in table, f"no literal expectation for quantum {tb.q}"
    return table[tb.q]


# Covers: SPEC §3 (ports/widths), §5 (synchronous reset clears RR state, polling starts at source 0,
#         outputs/handshakes inactive in reset; D25/Q1), §5/§6/§7/§11 (one common FIFO per source and
#         one hold controller; RR has no arrival counter, no timestamp storage, no oldest-head
#         selector; RR state = polling pointer + used quota only)
@cocotb.test()
async def test_01_ports_reset_structure_no_arrival_metadata(dut):
    tb = await new_tb(dut, "t01")
    n, q = tb.n, tb.q
    names = [p for p, _k in hierarchy_paths(dut)]
    dut._log.info("hierarchy: %d objects", len(names))
    fifo_idx = {int(m.group(1)) for p in names for m in [re.search(r"gen_fifo\[(\d+)\]\.u_fifo$", p)] if m}
    assert fifo_idx == set(range(n)), f"expected {n} cxl_desc_fifo instances, found {sorted(fifo_idx)}"
    assert len([p for p in names if p.endswith(".u_out_hold")]) == 1, "exactly one cxl_out_hold"
    assert len([p for p in names if p.endswith(".desc_mem_q")]) == n, "full descriptor storage per source"
    assert not [p for p in names if "ts_mem_q" in p], "RR must not store arrival timestamps"
    assert not [p for p in names if "arrival_cnt_q" in p or "gen_arrival_ts" in p], "RR has no arrival counter"
    assert not [p for p in names if "u_fcfs_sel" in p], "RR has no oldest-head selector"
    assert len([p for p in names if p.endswith("gen_policy_rr.u_rr_sched")]) == 1
    assert not any(re.search(r"gen_policy_(fcfs|fai_main|fai_alg2|unknown)|gen_bad_", p) for p in names)
    regs = {p.rsplit(".", 1)[1] for p in names if p.endswith("_q")}
    allowed = {"count_q", "wr_ptr_q", "rd_ptr_q", "desc_mem_q", "held_q", "held_source_q", "held_ctx_q",
               "ptr_q", "used_q"}  # fmt: skip
    assert regs <= allowed and {"ptr_q", "used_q"} <= regs, f"state in switch_top RR: {sorted(regs)}"
    rr_regs = sorted(p.rsplit(".", 1)[1] for p in names if ".u_rr_sched." in p and p.endswith("_q"))
    assert rr_regs == ["ptr_q", "used_q"], f"RR policy registers {rr_regs}"
    mem0 = dut.gen_fifo[0].u_fifo.desc_mem_q
    assert len(mem0) == 16 and len(mem0[0]) == 105

    o = await tb.cycle()
    assert state(o) == (0, 0) and o.out_valid == 0 and o.in_ready == tb.all_src and o.i_head_ts_any == 0
    # Move the RR state away from its reset value: source 2 holds 3 descriptors, one fires.
    a = [uniq(i, 1) for i in range(3)]
    await load_seq(tb, [{2: d} for d in a])
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc) == (1, 2, a[0]) and state(o) == (0, 0)
    exp = per_q(tb, {10: (2, 1), 1: (3, 0)})  # Q10: turn of source 2 open; Q1: expired, polls source 3
    o = await tb.cycle(out_ready=0)  # stall: the offer becomes held at this edge
    assert state(o) == exp and (o.out_source, o.i_held) == (2, 0)
    o = await tb.cycle(out_ready=0)
    assert state(o) == exp and o.i_held == 1

    # Reset with every request input asserted and ready=1: handshakes/outputs inactive, synchronous.
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and state(o) == exp and o.i_count[2] == 2, "synchronous reset: pre-edge state"
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.i_ptr, o.i_used, o.i_held, o.i_head_valid, o.in_ready) == (0, 0, 0, 0, 0)
    assert o.i_count == [0] * n

    # Polling restarts at source 0: with sources n-1 and 1 nonempty, source 1 is visited first.
    d = {n - 1: uniq(0, 2), 1: uniq(1, 2)}
    o = await tb.cycle(push=d, out_ready=1)
    assert state(o) == (0, 0) and o.out_valid == 0 and o.push == (1 << (n - 1)) | 0b10
    got = await serve(tb, 1)
    assert got == [(1, d[1])]
    o = await tb.cycle(out_ready=0)
    assert state(o) == (2, 0) and o.out_source == n - 1, "source 1 emptied: polling continues at source 2"
    await tb.cycle(rst_n=0)
    o = await tb.cycle(rst_n=0)
    assert state(o) == (0, 0) and o.i_count == [0] * n
    # After reset, with every source nonempty, source 0 is first and the order is ascending.
    allp = {h: uniq(h, 3) for h in range(n)}
    await load_seq(tb, [allp])
    got = await serve(tb, n)
    assert got == [(h, allp[h]) for h in range(n)], f"order after reset {[s for s, _ in got]}"
    await tb.finish()
    assert tb.dropped_by_reset == 3 and tb.cov.reset_during_hold == 2 and tb.cov.resets == 2


# Covers: SPEC §7 (a source turn allows at most RR_QUANTUM successful transfers, then polling
#         advances; Length does not alter cost), §3/D03 (equal-cost atomic service), D32 (Q1)
@cocotb.test()
async def test_02_exact_successful_fire_quota(dut):
    tb = await new_tb(dut, "t02")
    q = tb.q
    # Source 0: maximum Length; source 1: zero Length. Their charge must be identical.
    A = [mk_desc(0xA0000000 + i, 0x1000 + i, i & 1, 0xFF, 0x11110000 + i) for i in range(16)]
    B = [mk_desc(0xB0000000 + i, 0x2000 + i, (i + 1) & 1, 0x00, 0x22220000 + i) for i in range(16)]
    await load_seq(tb, [{0: A[i], 1: B[i]} for i in range(16)])
    exp_src = per_q(tb, {10: [0] * 10 + [1] * 10 + [0] * 6 + [1] * 6, 1: [0, 1] * 16})
    # The state of a turn's first fire is the polling position: after source 1's expired turn the
    # pointer is at 2 and source 0 is reached by wrapping, so that fire shows (2, 0).
    exp_state = per_q(tb, {
        10: [(0, k) for k in range(10)] + [(1, k) for k in range(10)] + [(2, 0)] + [(0, k) for k in range(1, 6)]
        + [(1, k) for k in range(6)],
        1: [(0, 0), (1, 0)] + [(2, 0), (1, 0)] * 15,
    })  # fmt: skip
    srcs, states, descs = [], [], {0: [], 1: []}
    for _ in range(32):
        o = await tb.cycle(out_ready=1)
        assert o.fire == 1, f"cycle {o.cycle}: no fire with work and ready=1"
        srcs.append(o.out_source)
        states.append(state(o))
        descs[o.out_source].append(o.out_desc)
    assert srcs == exp_src, f"quantum {q}: fire order {srcs}"
    assert states == exp_state, f"quantum {q}: (ptr_q, used_q) before each fire {states}"
    assert descs == {0: A, 1: B}, "per-source FIFO order"
    o = await tb.cycle()
    assert state(o) == (2, 0) and o.out_valid == 0, "source 1 emptied last: polling continues at source 2"
    hist = per_q(tb, {10: {10: 2, 6: 2}, 1: {1: 32}})
    assert {k: c for k, c in enumerate(tb.cov.fires_per_turn) if c} == hist, f"fires per turn {tb.cov.fires_per_turn}"
    await tb.finish()


# Covers: SPEC §4 (stall holds valid/105 bits/source; later arrivals cannot preempt), §7 (stalls
#         retain the turn context and consume no quantum; selection without acceptance is not
#         service; a stall on the turn's last transfer still ends the turn only at its fire)
@cocotb.test()
async def test_03_stalls_hold_offer_and_consume_no_quota(dut):
    tb = await new_tb(dut, "t03")
    n, q = tb.n, tb.q
    S1 = [uniq(i, 1) for i in range(16)]
    S2 = [uniq(i, 2) for i in range(4)]
    await load_seq(tb, [{1: S1[i], **({2: S2[i]} if i < 4 else {})} for i in range(16)])
    k_pre = min(3, q - 1)  # fires of source 1 before the long stall (Q10: 3, Q1: 0)
    got = await serve(tb, k_pre)
    assert got == [(1, d) for d in S1[:k_pre]]
    exp_state = (1, k_pre) if k_pre else (0, 0)
    # Q10: unlocked offer after the fires, held from the next cycle. Q1: the offer has been held
    # since the load cycles (ready=0).
    o = await tb.cycle(out_ready=0)
    assert (o.out_valid, o.out_source, o.out_desc, o.i_held) == (1, 1, S1[k_pre], int(k_pre == 0))
    assert state(o) == exp_state
    late = {5: {0: uniq(0, 3)}, 10: {2: uniq(1, 3)}, 30: {n - 1: uniq(2, 3)}}
    if q > 1:
        late[20] = {1: uniq(3, 3)}  # push into the held source itself (not full for Q10)
    for k in range(60):
        o = await tb.cycle(push=late.get(k), out_ready=0)
        for h in late.get(k, {}):
            assert (o.push >> h) & 1, f"stall k={k}: push into source {h} refused"
        assert (o.out_valid, o.out_source, o.out_desc, o.i_held) == (1, 1, S1[k_pre], 1), f"stall k={k}: offer changed"
        assert state(o) == exp_state, f"stall k={k}: RR state {state(o)} changed during a stall"
    # Resume with an alternating ready pattern; stall again in front of the turn's last fire.
    need = q - k_pre
    fired = []
    for j in range(need):
        if j == need - 1:
            for k in range(20):
                o = await tb.cycle(out_ready=0)
                assert o.out_source == 1 and state(o) == ((1, q - 1) if q > 1 else (0, 0)), "last-fire stall"
        else:
            o = await tb.cycle(out_ready=0)
            assert o.out_source == 1 and o.fire == 0
        o = await tb.cycle(out_ready=1)
        assert o.fire == 1 and o.out_source == 1
        fired.append(o.out_desc)
    assert fired == S1[k_pre:q], "exactly the quantum of successful transfers in the turn"
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc) == (1, 2, S2[0]), "turn expired at the quantum: source 2 is next"
    assert state(o) == (2, 0)
    assert tb.cov.max_valid_ready_low_run >= 60 and tb.cov.push_during_hold >= 3 and tb.cov.fires_held >= 1
    if q > 1:
        assert tb.cov.stall_mid_turn >= 80 and tb.cov.push_into_held_src >= 1
    await tb.finish()


# Covers: SPEC §7 (circularly choose the first nonempty source from the polling position; skip empty
#         sources), §5 (empty visits cause no control-only bubble when eligible work exists), Q2
#         (all-empty retains the polling position without consuming quota)
@cocotb.test()
async def test_04_circular_skip_without_bubbles(dut):
    tb = await new_tb(dut, "t04")
    n, q = tb.n, tb.q
    S = sorted({1, n // 2 + 1, n - 1})  # gaps of empty sources between them, and before source 1
    k = 2
    sched = [{s: uniq(i * n + s, 1) for s in S} for i in range(k)]
    await load_seq(tb, sched)
    exp = per_q(tb, {10: [s for s in S for _ in range(k)], 1: [s for _ in range(k) for s in S]})
    got = await serve(tb, k * len(S))  # every cycle fires: skipping empty sources costs no cycle
    assert [s for s, _ in got] == exp, f"skip order {[s for s, _ in got]}"
    o = await tb.cycle(out_ready=1)
    assert o.out_valid == 0 and state(o) == (0, 0), "source n-1 emptied: polling wraps to source 0"

    # Polling position n-1, all sources empty: idle cycles keep it and consume no quota.
    await load_seq(tb, [{n - 2: uniq(0, 2)}])
    assert await serve(tb, 1) == [(n - 2, uniq(0, 2))]
    for i in range(12):
        o = await tb.cycle(out_ready=i & 1)
        assert (o.out_valid, o.fire, o.i_cand_valid) == (0, 0, 0) and state(o) == (n - 1, 0), "all-empty retention"
    # Arrivals below the polling position: the search wraps around (no bypass in the push cycle).
    x0, x2 = uniq(1, 2), uniq(2, 2)
    o = await tb.cycle(push={0: x0, 2: x2}, out_ready=1)
    assert o.out_valid == 0 and state(o) == (n - 1, 0)
    got = await serve(tb, 2)
    assert got == [(0, x0), (2, x2)]
    assert tb.cov.skip_offers >= 2 and tb.cov.wrap_offers >= 1 and tb.cov.max_skip >= n - 2

    # Streaming: random sources keep offering, ready=1 -> a fire in every cycle with work.
    rng = random.Random(f"{run_seed()}:t04:{n}:{q}")
    pending, serial = {}, 0
    for i in range(400):
        for h in range(n):
            if h not in pending and rng.random() < 0.6 / n:
                pending[h] = uniq(serial, 3)
                serial += 1
        work = tb.outstanding() > 0
        o = await tb.cycle(push=dict(pending), out_ready=1)
        assert o.fire == int(work), f"streaming cycle {i}: fire={o.fire} with work={work} (bubble)"
        for h in list(pending):
            if (o.push >> h) & 1:
                del pending[h]
    assert tb.cov.skip_offers > 10 and tb.cov.wrap_offers > 0
    await tb.finish()


# Covers: SPEC §7 Q2/D26 (emptiness is evaluated after all same-edge pushes/pops: a final head fire
#         with a replacement push keeps the turn; quantum expiry advances regardless of the
#         replacement; an emptied source relinquishes unused quota and a push one cycle later does
#         not reopen its turn)
@cocotb.test()
async def test_05_replacement_push_versus_quantum_expiry(dut):
    tb = await new_tb(dut, "t05")
    q = tb.q
    # A: source 0 holds one descriptor; every fire of it carries a same-edge replacement push.
    r = [uniq(i, 1) for i in range(q + 1)]
    b = [uniq(i, 2) for i in range(3)]
    await load_seq(tb, [{0: r[0], 1: b[0]}, {1: b[1]}, {1: b[2]}])
    for j in range(q):
        o = await tb.cycle(push={0: r[j + 1]}, out_ready=1)
        assert (o.fire, o.out_source, o.out_desc) == (1, 0, r[j]) and o.push == 1
        assert o.i_count[0] == 1, "final-head fire: the replacement push is the only entry after the edge"
        assert state(o) == (0, j)
        assert o.turn_event == ("expired" if j == q - 1 else "continue"), f"fire {j}: {o.turn_event}"
    o = await tb.cycle(out_ready=1)
    assert o.i_count[0] == 1 and state(o) == (1, 0), "expiry advanced although source 0 is nonempty"
    assert (o.fire, o.out_source, o.out_desc) == (1, 1, b[0])
    got = await serve(tb, 3)
    assert got == per_q(tb, {10: [(1, b[1]), (1, b[2]), (0, r[q])], 1: [(0, r[q]), (1, b[1]), (1, b[2])]})
    assert tb.cov.turns_expired_replaced >= 1 and tb.cov.final_head_replaced_continue == q - 1

    # B: no replacement: a source that empties ends its turn early (unused quota relinquished).
    await tb.cycle(rst_n=0)
    await tb.cycle(rst_n=0)
    c2 = [uniq(i, 3) for i in range(3)]
    c3 = [uniq(i, 4) for i in range(5)]
    await load_seq(tb, [{2: c2[i], 3: c3[i]} if i < 3 else {3: c3[i]} for i in range(5)])
    got = await serve(tb, 8)
    assert [s for s, _ in got] == per_q(tb, {10: [2, 2, 2, 3, 3, 3, 3, 3], 1: [2, 3, 2, 3, 2, 3, 3, 3]})
    # With quantum 1 every fire reaches the quantum, so every turn end is an expiry (same advance).
    assert tb.cov.turns_emptied >= 2 if q > 1 else tb.cov.turns_emptied == 0

    # C: emptied at a fire without replacement; the push arrives one cycle later: no retained turn.
    await tb.cycle(rst_n=0)
    await tb.cycle(rst_n=0)
    z = [uniq(i, 5) for i in range(2)]
    w = [uniq(i, 6) for i in range(q + 1)]
    await load_seq(tb, [{0: z[0], 1: w[0]}] + [{1: d} for d in w[1:]])
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, o.turn_event) == (1, 0, z[0], per_q(tb, {10: "emptied", 1: "expired"}))
    assert o.i_count[0] == 1 and o.push == 0, "single entry, no replacement: empty after the edge"
    o = await tb.cycle(push={0: z[1]}, out_ready=1)
    assert (o.fire, o.out_source) == (1, 1) and state(o) == (1, 0)
    got = [(1, o.out_desc)] + await serve(tb, q + 1)
    assert [s for s, _ in got] == [1] * q + [0] + [1], f"late push order {[s for s, _ in got]}"
    await tb.finish()


# Covers: SPEC §4 (a held offer cannot be preempted by later arrivals), §7 (stalls retain the
#         selection; the eventual fire is charged to the source that actually fired, even though
#         this cycle's RR candidate has moved to another source; post-edge continuation/advance
#         is computed for the fired source)
@cocotb.test()
async def test_06_candidate_change_during_stall_charges_held_source(dut):
    tb = await new_tb(dut, "t06")
    n, q = tb.n, tb.q
    hi = n - 1
    h0, h1, x0, x1 = uniq(0, 1), uniq(1, 1), uniq(2, 1), uniq(3, 1)
    obs = await load_seq(tb, [{hi: h0}, {hi: h1}])
    o = obs[1]  # unlocked offer in the second load cycle: first nonempty from position 0 is n-1
    assert (o.out_valid, o.out_source, o.i_held, o.i_cand_source, state(o)) == (1, hi, 0, hi, (0, 0))
    o = await tb.cycle(push={0: x0, 1: x1}, out_ready=0)  # arrivals between the polling position and n-1
    assert (o.out_source, o.i_held, o.i_cand_source) == (hi, 1, hi)
    for _ in range(4):
        o = await tb.cycle(out_ready=0)
        assert (o.out_source, o.out_desc, o.i_held) == (hi, h0, 1)
        assert o.i_cand_valid == 1 and o.i_cand_source == 0, "the RR candidate moved to source 0"
        assert state(o) == (0, 0), "a stall charges nothing"
    o = await tb.cycle(out_ready=1)  # the held grant fires while the candidate is source 0
    assert (o.fire, o.out_source, o.out_desc, o.i_held, o.i_cand_source) == (1, hi, h0, 1, 0)
    assert o.charged == 1 and o.turn_event == per_q(tb, {10: "continue", 1: "expired"})
    o2 = await tb.cycle(out_ready=1)
    assert state(o2) == per_q(tb, {10: (hi, 1), 1: (0, 0)}), "quota charged to the held source n-1"
    got = [(o2.out_source, o2.out_desc)] + await serve(tb, 2)
    assert got == per_q(tb, {10: [(hi, h1), (0, x0), (1, x1)], 1: [(0, x0), (1, x1), (hi, h1)]})

    # The held grant's fire empties its source: polling continues after it (wraps past n-1).
    await tb.cycle(rst_n=0)
    await tb.cycle(rst_n=0)
    lo, y, y1 = n - 2, uniq(4, 1), uniq(5, 1)
    await load_seq(tb, [{lo: y}])
    o = await tb.cycle(out_ready=0)
    assert o.out_source == lo and o.i_held == 0
    o = await tb.cycle(push={1: y1}, out_ready=0)
    assert o.i_held == 1
    o = await tb.cycle(out_ready=0)
    assert (o.out_source, o.i_cand_source, o.i_held) == (lo, 1, 1)
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, o.turn_event) == (1, lo, y, per_q(tb, {10: "emptied", 1: "expired"}))
    o = await tb.cycle(out_ready=1)
    assert state(o) == (n - 1, 0) and (o.fire, o.out_source, o.out_desc) == (1, 1, y1)
    assert tb.cov.held_cand_mismatch == 2
    await tb.finish()


# Covers: SPEC §4 (a full FIFO refuses a push even when its head fires that edge; in_ready from
#         beginning-of-cycle occupancy; ready again next cycle), §7 (the refused replacement does not
#         change the turn bookkeeping)
@cocotb.test()
async def test_07_full_plus_pop_refusal(dut):
    tb = await new_tb(dut, "t07")
    n, q = tb.n, tb.q
    for s in range(n):
        content = [uniq(i, s + 1) for i in range(16)]
        await load_seq(tb, [{s: d} for d in content])
        x = uniq(100, s + 1)
        o = await tb.cycle(push={s: x}, out_ready=0)  # full, no fire: refused
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0 and o.i_count[s] == 16
        o = await tb.cycle(push={s: x}, out_ready=1)  # full, head fires: still refused
        assert (o.fire, o.out_source, o.out_desc) == (1, s, content[0])
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0, "full FIFO must refuse a push on its pop edge"
        assert o.turn_event == per_q(tb, {10: "continue", 1: "expired"})
        o = await tb.cycle(push={s: x}, out_ready=0)  # occupancy 15: ready again, accepted
        assert (o.in_ready >> s) & 1 == 1 and o.push == 1 << s and o.i_count[s] == 15
        assert state(o) == per_q(tb, {10: (s, 1), 1: ((s + 1) % n, 0)})
        o = await tb.cycle(out_ready=0)
        assert o.i_count[s] == 16
        got = await tb.drain()
        assert got == [(s, d) for d in content[1:]] + [(s, x)]
    assert tb.cov.full_refused == n and tb.cov.ready_after_full_fire == n
    await tb.finish()


# Covers: SPEC §4 (no empty-FIFO bypass: a push at c is eligible no earlier than c+1, also into the
#         source at the polling position and while another source is served)
@cocotb.test()
async def test_08_no_bypass_next_cycle_eligibility(dut):
    tb = await new_tb(dut, "t08")
    n, q = tb.n, tb.q
    for s in range(n):
        d = uniq(s, 1)
        o = await tb.cycle(push={s: d}, out_ready=1)
        assert (o.out_valid, o.fire, o.push) == (0, 0, 1 << s), f"source {s}: offered in its push cycle"
        assert state(o) == (s, 0), "the pushed (empty) source is the polling position itself"
        o = await tb.cycle(out_ready=1)
        assert (o.fire, o.out_source, o.out_desc) == (1, s, d) and o.fired.accept_cycle == o.cycle - 1
    other = n - 1
    v = [uniq(i, 2) for i in range(3)]
    await tb.cycle(rst_n=0)
    await tb.cycle(rst_n=0)
    await load_seq(tb, [{other: d} for d in v])
    w0 = uniq(9, 2)
    o = await tb.cycle(push={0: w0}, out_ready=1)  # source 0 empty at the beginning of this cycle
    assert (o.fire, o.out_source, o.out_desc) == (1, other, v[0])
    got = [(o.out_source, o.out_desc)] + await serve(tb, 3)
    assert got == per_q(tb, {10: [(other, v[0]), (other, v[1]), (other, v[2]), (0, w0)],
                             1: [(other, v[0]), (0, w0), (other, v[1]), (other, v[2])]})  # fmt: skip
    assert tb.cov.min_wait == 1
    await tb.finish()


# Covers: SPEC §7 Q2 (all sources empty: polling position retained, no quota consumed), §5/§7 (one
#         active source: quota renewal on a new turn without bubbles), §7 (all sources active:
#         strict circular turns of exactly RR_QUANTUM fires, then residual turns)
@cocotb.test()
async def test_09_one_active_all_active_all_empty(dut):
    tb = await new_tb(dut, "t09")
    n, q = tb.n, tb.q
    await load_seq(tb, [{1: uniq(0, 1)}])
    await serve(tb, 1)
    for i in range(20):  # all empty
        o = await tb.cycle(out_ready=(i >> 1) & 1)
        assert (o.out_valid, o.fire, o.i_cand_valid) == (0, 0, 0) and state(o) == (2, 0)
    assert tb.cov.idle_nonzero_poll >= 20

    # One active source behind the polling position, refilled at every fire: a fire every cycle.
    s = 1
    serial = iter(range(1, 1000))
    o = await tb.cycle(push={s: uniq(next(serial), 2)}, out_ready=1)
    assert o.out_valid == 0
    total = 3 * q + 5
    for k in range(total):
        o = await tb.cycle(push={s: uniq(next(serial), 2)} if k < total - 1 else None, out_ready=1)
        assert (o.fire, o.out_source) == (1, s), f"single-source cycle {k}: bubble or wrong source"
        exp = (s + 1, 0) if k % q == 0 else (s, k % q)
        assert state(o) == exp, f"single-source cycle {k}: state {state(o)}, expected {exp}"
    o = await tb.cycle(out_ready=1)
    assert o.out_valid == 0
    assert tb.cov.renew_same_source >= 3 and tb.cov.turns_expired >= 3

    # All sources active from polling position 0 (after a reset).
    await tb.cycle(rst_n=0)
    await tb.cycle(rst_n=0)
    depth = q + 2
    await load_seq(tb, [{h: uniq(r * n + h, 3) for h in range(n)} for r in range(depth)])
    got = await serve(tb, n * depth)
    exp_src = per_q(tb, {10: [h for h in range(n) for _ in range(10)] + [h for h in range(n) for _ in range(2)],
                         1: list(range(n)) * 3})  # fmt: skip
    assert [x for x, _ in got] == exp_src, f"all-active order {[x for x, _ in got]}"
    o = await tb.cycle(out_ready=1)
    assert o.out_valid == 0 and state(o) == (0, 0)
    await tb.finish()


# Covers: SPEC §5 (synchronous reset mid-turn and mid-hold: pointer to source 0, used quota and held
#         grant cleared, no fire/pop on a reset edge, outputs inactive; a pulse between edges clears
#         nothing; TB responses of the old epoch still complete and never affect the DUT), D25/D28
@cocotb.test()
async def test_10_reset_mid_turn_and_mid_hold(dut):
    tb = await new_tb(dut, "t10", resp_delay=(4, 48))
    n, q = tb.n, tb.q
    a = [uniq(i, 1) for i in range(5)]
    c = [uniq(i, 2) for i in range(2)]
    await load_seq(tb, [{1: a[i], **({3: c[i]} if i < 2 else {})} for i in range(5)])
    assert await serve(tb, 1) == [(1, a[0])]
    mid = per_q(tb, {10: (1, 1), 1: (2, 0)})
    o = await tb.cycle(out_ready=0)
    o = await tb.cycle(out_ready=0)
    assert o.i_held == 1 and state(o) == mid
    counts_before = list(o.i_count)
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and o.i_count == counts_before and state(o) == mid, "no change before the edge"
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.i_held, o.i_head_valid) == (0, 0) and state(o) == (0, 0) and o.i_count == [0] * n
    f0, f3 = uniq(0, 3), uniq(3, 3)
    o = await tb.cycle(push={3: f3, 0: f0}, out_ready=1)
    assert o.out_valid == 0
    assert await serve(tb, 2) == [(0, f0), (3, f3)], "polling restarted at source 0"
    if q > 1:
        assert tb.cov.reset_mid_turn >= 1

    # Reset on an unlocked valid+ready offer: no fire/pop on the reset edge.
    await load_seq(tb, [{2: uniq(1, 4)}], out_ready=0)
    o = await tb.cycle(out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.i_pop, o.i_held) == (0, 0, 0, 0) and o.i_count[2] == 1
    assert o.i_cand_valid == 1 and o.i_cand_source == 2, "an unlocked candidate existed on the reset edge"
    o = await tb.cycle()
    assert o.i_count == [0] * n and o.i_held == 0 and state(o) == (0, 0)

    # A low pulse between edges clears nothing (synchronous reset).
    b = [uniq(0, 5), uniq(1, 5)]
    await load_seq(tb, [{3: b[0]}, {3: b[1]}])
    o = await tb.cycle(out_ready=0)
    assert o.i_held == 1 and o.out_source == 3
    await Timer(1, unit="ns")
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    await ReadOnly()
    assert int(dut.o_out_valid.value) == 0 and int(dut.o_in_ready.value) == 0, "inactive while rst_n low"
    assert int(dut.grant_held.value) == 1 and int(dut.head_valid.value) == 0b1000
    await Timer(1, unit="ns")
    dut.rst_n.value = 1
    o = await tb.cycle(out_ready=1)
    assert (o.i_held, o.fire, o.out_source, o.out_desc) == (1, 1, 3, b[0])
    got = await tb.finish()
    assert got == [(3, b[1])]
    assert tb.cov.reset_during_hold == 1 and tb.cov.resets == 2 and tb.cov.reset_nonempty == 2
    assert tb.resp.cross_epoch_completions > 0, "old-epoch responses must complete after the reset"


# Covers: SPEC §3 (all 105 descriptor bits transported intact, per source; source sideband)
@cocotb.test()
async def test_11_walking_ones_and_zeros_all_bits(dut):
    tb = await new_tb(dut, "t11", resp_delay=(1, 1))
    n = tb.n
    pats = [1 << b for b in range(DESC_W)] + [DESC_MASK ^ (1 << b) for b in range(DESC_W)]
    for s in range(n):
        got = []
        for d in pats:
            o = await tb.cycle(push={s: d}, out_ready=1)
            if o.fire:
                got.append((o.out_source, o.out_desc))
        got += await tb.drain()
        assert got == [(s, d) for d in pats], f"source {s}: walking pattern corrupted"
    await tb.finish()


# Covers: SPEC §4, §5, §7, §9 (whole contract under the policy-independent intended trace used for
#         FCFS: turns, quantum expiry, emptying, skips/wraps, stalls, directed long stalls,
#         overload/full refusal, back-to-back, resets, TB tagged responses)
@cocotb.test()
async def test_12_short_random_trace(dut):
    from switch_rr_tb import run_trace

    seed = run_seed()
    tb = await new_tb(dut, "t12", unique_tags=True)
    trace = make_trace(seed, tb.n, SHORT_RANDOM_CYCLES, "short")
    dut._log.info("short trace sha256=%s generated=%d resets=%d", trace.sha256, trace.generated, sum(trace.reset))
    metrics = await run_trace(dut, tb, trace)
    cov = tb.cov
    write_json("rr_short_random.json", {"schema": "cxl-m4-rr-short-random-v1", "policy": "RR",
                                        "rr_quantum": tb.q, "seed": seed, "n_src": tb.n,
                                        "trace_sha256": trace.sha256,
                                        "rr_turns_measurement": rr_turn_summary(metrics["coverage_measurement"], tb.q),
                                        **metrics})  # fmt: skip
    dut._log.info("short random coverage: %s", cov.summary())
    every = set(range(tb.n))
    assert cov.stall_cycles > 0 and cov.max_valid_ready_low_run >= 100 and cov.holds > 0, "stall bins"
    assert cov.push_during_hold > 0 and cov.push_into_held_src > 0 and cov.hold_with_other_nonempty > 0
    assert cov.full_refused > 0, "full-plus-pop bin"
    assert cov.ready_after_full_fire + cov.full_fire_then_reset == cov.full_refused, "ready after full fire"
    assert cov.full_sources and cov.full_cycles > 0
    assert cov.b2b_fires > 0 and cov.b2b_switch > 0 and cov.fire_with_push_same_src > 0
    assert cov.resets >= 1 and cov.reset_nonempty >= 1 and tb.dropped_by_reset > 0, "reset bins"
    assert cov.min_wait == 1 and cov.fire_sources == every
    assert cov.turns_expired > 0 and cov.turns_expired_nonempty > 0, "turn-end bins"
    # Quantum 1: every turn end is an expiry (an emptying fire also reaches the quantum).
    assert cov.turns_emptied > 0 if tb.q > 1 else cov.turns_emptied == 0, "emptied-turn bin"
    # Wrap offers (a new turn below the polling position), held-grant/candidate mismatches and
    # same-source quota renewal depend on the seed under this saturated trace (e.g. N4 seed 511
    # has skips but no wrap); they are mandatory deterministic bins of test_04 / test_06 / test_09
    # and are recorded here in rr_turns_measurement.
    assert cov.skip_offers > 0 and cov.idle_cycles > 0, "skip/idle bins"
    if tb.q > 1:
        assert cov.turn_continue > 0 and cov.stall_mid_turn > 0, "open-turn bins"
    assert tb.resp.issued == tb.total_delivered > 0 and tb.resp.completed == tb.resp.issued
    assert tb.resp.reordered > 0 and tb.resp.cross_epoch_completions > 0, "response reorder/epoch bins"
    assert metrics["generation_to_acceptance"]["max"] > 0, "backpressure must delay some acceptance"
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0


# Covers: SPEC §4 (producer retains its valid descriptor until push: an offer refused by a full D16
#         FIFO in the last measured cycle stays valid with identical bits across measurement -> drain
#         until pushed; full-plus-pop refusal on the drain edge), §7 (drain order follows RR turns),
#         §9/§10 (measurement snapshots frozen at the boundary, drain-only accepts counted separately,
#         every tag answered exactly once). RR counterpart of the FCFS C1 regression.
@cocotb.test()
async def test_13_measurement_boundary_input_hold(dut):
    from switch_rr_tb import run_trace
    from traffic_trace import Trace, trace_sha256

    tb = await new_tb(dut, "t13", unique_tags=True)
    n, q = tb.n, tb.q
    a, z, mid = 0, n - 1, 1  # two sources fill their FIFOs; one source has unoffered backlog
    cycles = 20
    serial = iter(range(1000))

    def tdesc() -> int:
        i = next(serial)
        return mk_desc(tag=0xC4000000 + i, addr=0x50000000 + i, opcode=i & 1, length=i & 0xFF, payload=0xBEEF0000 + i)

    tr = Trace(run_seed(), n, cycles, "primary")
    tr.gen = [[(a, tdesc()), (z, tdesc())] for _ in range(cycles)]
    tr.gen[cycles - 1] += [(mid, tdesc()), (mid, tdesc())]  # first accepted at the last edge, second never offered
    tr.ready = bytearray(cycles)  # downstream stalled for the whole measurement
    tr.reset = bytearray(cycles)
    tr.phases = [(0, cycles, "directed-boundary")]
    tr.sha256 = trace_sha256(tr)
    held = {a: tr.gen[16][0][1], z: tr.gen[16][1][1]}  # 17th descriptor: refused from cycle 16 on

    seen = []  # (TB cycle, in_valid, in_ready, desc[a], desc[z], push) from the boundary on
    orig_cycle = tb.cycle

    async def spy(*args, **kw):
        o = await orig_cycle(*args, **kw)
        seen.append((o.cycle, o.in_valid, o.in_ready, o.in_desc[a], o.in_desc[z], o.push))
        return o

    tb.cycle = spy
    base = tb.cycle_no
    m = await run_trace(dut, tb, tr)
    tb.cycle = orig_cycle

    # Measurement snapshot (frozen at the boundary).
    assert m["phases"]["measured_non_reset_cycles"] == cycles
    assert m["input_push_count"] == 2 * DEPTH_D16 + 1 and m["fires_measurement"] == 0
    assert m["accepted_transfer_rate"] == 0 and m["input_push_rate"] == (2 * DEPTH_D16 + 1) / cycles
    assert m["per_source_pushes"][a] == m["per_source_pushes"][z] == DEPTH_D16 and m["per_source_pushes"][mid] == 1
    assert m["generated"] == 2 * cycles + 2 and m["generated_but_unaccepted"] == 2 * (cycles - DEPTH_D16) + 1
    assert m["generation_to_acceptance"]["count"] == 2 * DEPTH_D16 + 1
    assert m["coverage_measurement"]["pushes"] == 2 * DEPTH_D16 + 1 and m["coverage_measurement"]["fires"] == 0
    w = m["wait_acceptance_to_fire"]
    assert w["censored_at_measurement_end"] == 2 * DEPTH_D16 + 1 and w["fired_in_measurement"]["count"] == 0
    assert w["drain_completed"]["count"] == w["all_completed"]["count"] == 2 * DEPTH_D16 + 1, "drain-only accepts excluded"
    assert m["fires_drain"] == 2 * DEPTH_D16 + 1 and w["outstanding_after_drain"] == 0

    # Boundary: both full sources were offering and refused in the last measured cycle ...
    meas_end = base + cycles
    last = [s for s in seen if s[0] == meas_end - 1][0]
    for h in (a, z):
        assert (last[1] >> h) & 1 and not (last[2] >> h) & 1
    assert (last[3], last[4]) == (held[a], held[z])
    # ... and kept valid with identical bits in the drain until pushed. RR drain from polling
    # position 0: source a fires at the first drain edge (full + pop: refused) and is pushed at the
    # second; a's turn runs its quantum, then mid's single entry, then z fires (refused while
    # full) at drain cycle q+1 and z is pushed at drain cycle q+2 (Q10: 12, Q1: 3).
    drain = [s for s in seen if s[0] >= meas_end]
    push_at = {h: next(s[0] for s in drain if (s[5] >> h) & 1) for h in (a, z)}
    assert push_at == {a: meas_end + 1, z: meas_end + per_q(tb, {10: 12, 1: 3})}, f"boundary pushes at {push_at}"
    for cyc, valid, _rdy, da, dz, _push in drain:
        for h, d in ((a, da), (z, dz)):
            owed = cyc <= push_at[h]
            assert ((valid >> h) & 1) == int(owed), f"cycle {cyc}: source {h} valid={(valid >> h) & 1}, owed={owed}"
            if owed:
                assert d == held[h], f"cycle {cyc}: source {h} descriptor changed while held"
        assert not (valid >> mid) & 1, "unoffered backlog must not be released in the drain"

    d = m["drain_only"]
    assert d["boundary_held_sources"] == sorted({a, z}) and d["boundary_held_offers"] == 2
    assert d["pushes"] == d["fires"] == 2 and d["per_source_pushes"] == d["per_source_fires"]
    assert d["generation_to_acceptance"]["count"] == 2 and d["generation_to_acceptance"]["min"] == cycles + 1 - 16
    assert d["wait_acceptance_to_fire"]["count"] == 2 and d["wait_acceptance_to_fire"]["min"] >= 1
    assert d["unoffered_backlog_at_boundary"] == d["generated_never_accepted"] == 2 * (cycles - DEPTH_D16 - 1) + 1
    assert m["input_hold"]["obligation_checks_drain"] >= 3 and m["input_hold"]["obligation_checks_measurement"] >= 6
    r = m["responses"]
    assert r["issued"] == r["completed"] == 2 * DEPTH_D16 + 1 + 2 and r["issued_for_drain_only_accepts"] == 2
    assert tb.cov.full_refused >= 2 and tb.cov.ready_after_full_fire == tb.cov.full_refused
    assert not tb.in_hold.pending and tb.outstanding() == 0
