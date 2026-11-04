"""Cycle-exact cocotb tests of switch_top with POLICY=0 (FCFS), milestone M3, N_SRC = 4, 8, 16.

Run through scripts/run_verify.sh M3 (it builds the design and exports CXL_PARAM_*).

Every cycle of every test goes through sim/common/switch_fcfs_tb.SwitchFcfsTb, which compares all
pins and the observable internal state with the abstract absolute-time FCFS model
(refc/cxl_model/fcfs_model.py), applies model-free pin rules (in_ready from beginning-of-cycle
occupancy, inactive in reset, work conservation, stall stability of valid/105 bits/source, hold
provenance, FCFS order from the pin history), keeps a pin-level conservation/order scoreboard and
matches TB-only tagged responses exactly once. On top of that each directed test asserts literal
expectations written from the spec, so a defect shared by model and RTL would still be caught.

Spec references are to specs/CXL_SPEC.md v1.0.
"""

from __future__ import annotations

import random
import re

from hier_util import hierarchy_paths
from switch_fcfs_tb import DESC_MASK, DESC_W, SwitchFcfsTb, run_seed, write_json
from traffic_trace import make_trace

import cocotb
from cocotb.triggers import ReadOnly, Timer

TAG_LSB, ADDR_LSB, OPCODE_LSB, LENGTH_LSB = 73, 41, 40, 32
TS_MOD = 1 << 32
SHORT_RANDOM_CYCLES = 12000
DEPTH_D16 = 16  # spec: D16 FIFO per source


def mk_desc(tag: int, addr: int, opcode: int, length: int, payload: int) -> int:
    assert tag < (1 << 32) and addr < (1 << 32) and opcode < 2 and length < 256 and payload < (1 << 32)
    return (tag << TAG_LSB) | (addr << ADDR_LSB) | (opcode << OPCODE_LSB) | (length << LENGTH_LSB) | payload


def uniq(i: int, salt: int = 0) -> int:
    """A distinct descriptor (distinct Tag) per (index, salt) with every field populated."""
    assert 0 <= i < 0x10000 and 0 <= salt < 0x100
    return mk_desc(
        tag=(0xA5000000 + salt * 0x10000 + i) & 0xFFFFFFFF,
        addr=(0x10000000 + i * 0x01010101 + salt * 0x00310000) & 0xFFFFFFFF,
        opcode=(i ^ salt) & 1,
        length=(i * 7 + salt * 3 + 3) & 0xFF,
        payload=((i + 1) * 0x9E3779B1 + salt * 0x85EBCA6B) & 0xFFFFFFFF,
    )


async def new_tb(dut, label: str, **kw) -> SwitchFcfsTb:
    tb = SwitchFcfsTb(dut, label, **kw)
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) N_SRC=%d POLICY=%d DEPTH=%d DESC_W=%d TS_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.n, tb.policy, tb.depth, tb.desc_w, tb.ts_w,
    )  # fmt: skip
    await tb.start()
    return tb


async def load_seq(tb: SwitchFcfsTb, schedule, out_ready: int = 0):
    """schedule: list of {source: desc} per cycle. Every push must be accepted."""
    obs = []
    for pushes in schedule:
        o = await tb.cycle(push=pushes, out_ready=out_ready)
        for h in pushes:
            assert (o.push >> h) & 1, f"cycle {o.cycle}: push into source {h} was not accepted"
        obs.append(o)
    return obs


async def serve(tb: SwitchFcfsTb, count: int):
    """ready=1 for ``count`` cycles, each must fire. Returns [(source, desc)]."""
    got = []
    for _ in range(count):
        o = await tb.cycle(out_ready=1)
        assert o.fire == 1, f"cycle {o.cycle}: expected a fire (work exists, ready=1)"
        got.append((o.out_source, o.out_desc))
    return got


# Covers: SPEC §3 (ports/widths), §5 (synchronous reset, outputs inactive, counter reset), §6
#         (counter starts at 0, +1 every non-reset edge, push stores the pre-edge value), §5/§11
#         (one common FIFO per source, one hold controller, counter + selector only for FCFS)
@cocotb.test()
async def test_01_ports_reset_structure_counter(dut):
    tb = await new_tb(dut, "t01")
    n = tb.n
    names = [p for p, _k in hierarchy_paths(dut)]
    dut._log.info("hierarchy: %d objects", len(names))
    fifo_idx = {int(m.group(1)) for p in names for m in [re.search(r"gen_fifo\[(\d+)\]\.u_fifo$", p)] if m}
    assert fifo_idx == set(range(n)), f"expected {n} cxl_desc_fifo instances, found {sorted(fifo_idx)}"
    assert len([p for p in names if p.endswith(".u_out_hold")]) == 1, "exactly one cxl_out_hold"
    assert len([p for p in names if p.endswith(".desc_mem_q")]) == n
    assert len([p for p in names if p.endswith(".ts_mem_q")]) == n, "FCFS stores a timestamp per entry"
    assert len([p for p in names if p.endswith("gen_arrival_ts.arrival_cnt_q")]) == 1
    assert len([p for p in names if p.endswith("gen_policy_fcfs.u_fcfs_sel")]) == 1
    assert not any(re.search(r"gen_policy_(rr|fai_main|fai_alg2|unknown)|gen_no_arrival_ts|gen_bad_", p) for p in names)
    regs = {p.rsplit(".", 1)[1] for p in names if p.endswith("_q")}
    allowed = {"count_q", "wr_ptr_q", "rd_ptr_q", "desc_mem_q", "ts_mem_q", "held_q", "held_source_q",
               "held_ctx_q", "arrival_cnt_q"}  # fmt: skip
    assert regs <= allowed and "arrival_cnt_q" in regs, f"state in switch_top FCFS: {sorted(regs)}"
    assert not [p for p in names if ".u_fcfs_sel." in p and p.endswith("_q")], "selector must be stateless"
    mem0 = dut.gen_fifo[0].u_fifo.gen_ts.ts_mem_q
    assert len(mem0) == 16 and len(mem0[0]) == 32

    # Counter: 0 in the first cycle after reset, +1 on every non-reset edge, idle or not.
    for k in range(7):
        o = await tb.cycle()
        assert o.i_counter == k and o.out_valid == 0 and o.in_ready == tb.all_src
    d0, d1, d2 = uniq(0, 1), uniq(1, 1), uniq(2, 1)
    o = await tb.cycle(push={n - 1: d0})  # 7 non-reset edges since reset precede this push edge
    assert o.i_counter == 7 and o.out_valid == 0 and o.push == 1 << (n - 1)
    o = await tb.cycle(push={0: d1}, out_ready=0)
    assert o.i_head_ts[n - 1] == 7, f"first stored timestamp {o.i_head_ts[n - 1]}, expected 7"
    assert (o.out_valid, o.out_source, o.out_desc, o.i_counter) == (1, n - 1, d0, 8)
    o = await tb.cycle(out_ready=0)
    assert o.i_head_ts[0] == 8 and o.i_held == 1 and o.i_counter == 9

    # Reset with every request input asserted and ready=1: handshakes/outputs inactive, synchronous.
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and o.i_count[0] == 1 and o.i_count[n - 1] == 1 and o.i_counter == 10, "pre-edge state"
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.in_ready, o.push, o.i_held, o.i_head_valid, o.i_counter) == (0, 0, 0, 0, 0, 0)
    assert o.i_count == [0] * n
    # New epoch: counter 0 again, a push in the first cycle stores 0, nothing old resurfaces.
    o = await tb.cycle(push={1: d2}, out_ready=1)
    assert o.i_counter == 0 and o.out_valid == 0 and o.push == 0b10
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, o.i_head_ts[1], o.i_counter) == (1, 1, d2, 0, 1)
    got = await tb.finish()
    assert got == []
    assert tb.dropped_by_reset == 2 and tb.cov.reset_during_hold == 1


# Covers: SPEC §6 (equal timestamps incl. same-cycle ties -> ascending source ID)
@cocotb.test()
async def test_02_same_cycle_ties_ascending_id(dut):
    tb = await new_tb(dut, "t02")
    n = tb.n
    descs = {h: uniq(h, 1) for h in range(n)}
    o = await tb.cycle(push=descs, out_ready=1)
    assert o.out_valid == 0 and o.push == tb.all_src, "pushes of the cycle are not offered (no bypass)"
    o = await tb.cycle(out_ready=1)
    assert len(set(o.i_head_ts)) == 1, f"one timestamp for all same-cycle pushes: {o.i_head_ts}"
    first = [(o.out_source, o.out_desc)]
    got = first + await serve(tb, n - 1)
    assert got == [(h, descs[h]) for h in range(n)], f"tie order {[s for s, _ in got]}"

    subsets = [[n - 1, 1], [n - 1, n // 2 + 1, 2, 0], list(range(n - 1, -1, -2)), [n - 2, n - 1]]
    for i, subset in enumerate(subsets):
        subset = list(dict.fromkeys(subset))
        pushes = {h: uniq(h, 10 + i) for h in subset}
        await load_seq(tb, [pushes])
        for _ in range(3):  # stalled: the held grant is the lowest ID of the tie
            o = await tb.cycle(out_ready=0)
            assert o.out_source == min(subset)
        got = await serve(tb, len(subset))
        assert got == [(h, pushes[h]) for h in sorted(subset)], f"subset {subset}: {[s for s, _ in got]}"

    # Two entries per source in two consecutive cycles: two ascending rounds.
    r1 = {h: uniq(h, 20) for h in range(n)}
    r2 = {h: uniq(h, 21) for h in range(n)}
    await load_seq(tb, [r1, r2])
    got = await serve(tb, 2 * n)
    assert got == [(h, r1[h]) for h in range(n)] + [(h, r2[h]) for h in range(n)]
    assert tb.cov.ties >= n
    await tb.finish()


# Covers: SPEC §6 (oldest eligible head wins over a lower source ID)
@cocotb.test()
async def test_03_older_head_beats_lower_id(dut):
    tb = await new_tb(dut, "t03")
    n = tb.n
    sched = [{h: uniq(h, 1)} for h in range(n - 1, -1, -1)]  # descending IDs, one per cycle
    await load_seq(tb, sched)
    got = await serve(tb, n)
    assert [s for s, _ in got] == list(range(n - 1, -1, -1)), f"order {[s for s, _ in got]}"

    a, b, c, d = n - 1, 0, n - 2, 1
    sched = [{a: uniq(0, 2)}, {b: uniq(1, 2), c: uniq(2, 2)}, {d: uniq(3, 2)}]
    await load_seq(tb, sched)
    got = await serve(tb, 4)
    assert [s for s, _ in got] == [a, b, c, d]
    assert tb.cov.older_beats_lower >= n - 1
    await tb.finish()


# Covers: SPEC §4 (per-source FIFO order), §6 (cross-source age order)
@cocotb.test()
async def test_04_fifo_order_interleaved_with_age(dut):
    tb = await new_tb(dut, "t04")
    n = tb.n
    A = [uniq(i, 1) for i in range(3)]
    B = [uniq(i, 2) for i in range(2)]
    C = [uniq(i, 3) for i in range(2)]
    await load_seq(tb, [{0: A[0], 2: C[0]}, {0: A[1]}, {2: C[1], 1: B[0]}, {1: B[1], 0: A[2]}])
    got = await serve(tb, 7)
    assert got == [(0, A[0]), (2, C[0]), (0, A[1]), (1, B[0]), (2, C[1]), (0, A[2]), (1, B[1])]

    # Random interleaving with random ready: FCFS delivery order is sorted by (accepting cycle, ID).
    rng = random.Random(f"{run_seed()}:t04:{n}")
    order = []
    tb.on_fire = lambda src, e, cyc: order.append((e.accept_cycle, src))
    serial = 0
    pending = {}
    for _ in range(400):
        for h in range(n):
            if h not in pending and rng.random() < 1.5 / n:
                pending[h] = uniq(serial, 4)
                serial += 1
        o = await tb.cycle(push=dict(pending), out_ready=int(rng.random() < 0.5))
        for h in list(pending):
            if (o.push >> h) & 1:
                del pending[h]
    await tb.finish()
    assert len(order) == tb.total_delivered - 7 and len(order) > 100
    assert order == sorted(order), "FCFS delivery order is not sorted by (accepting cycle, source ID)"


# Covers: SPEC §4 (stall holds valid/data/source; later arrivals cannot preempt), §6 (counter
#         advances on every non-reset edge including stalls; arrivals during the stall get later
#         timestamps; age order resumes after the stall)
@cocotb.test()
async def test_05_counter_runs_through_long_stall(dut):
    tb = await new_tb(dut, "t05")
    n = tb.n
    o = await tb.cycle()
    t0 = o.i_counter
    d1 = uniq(0, 1)
    o = await tb.cycle(push={1: d1})
    assert o.i_counter == t0 + 1
    arrivals = {10: {0: uniq(1, 1), 2: uniq(2, 1)}, 50: {1: uniq(3, 1)}, 120: {n - 1: uniq(4, 1)},
                200: {0: uniq(5, 1)}, 299: {2: uniq(6, 1)}}  # fmt: skip
    pushed_at = {}
    prev_cnt = o.i_counter
    for k in range(300):
        o = await tb.cycle(push=arrivals.get(k), out_ready=0)
        assert o.i_counter == (prev_cnt + 1) % TS_MOD, "counter must advance during the stall"
        prev_cnt = o.i_counter
        assert (o.out_valid, o.out_source, o.out_desc) == (1, 1, d1), f"stall k={k}: offer changed {o}"
        assert o.i_held == int(k > 0) and o.i_cand_source == 1, "held grant / FCFS candidate changed"
        for h in arrivals.get(k, {}):
            pushed_at[(h, k)] = o.i_counter
    assert tb.cov.max_valid_ready_low_run >= 300 and tb.cov.push_during_hold == 5
    o = await tb.cycle(out_ready=0)
    # Stored timestamps are the counter values of the push cycles (later than the held head's).
    assert o.i_head_ts[1] == t0 + 1
    assert o.i_head_ts[0] == pushed_at[(0, 10)] and o.i_head_ts[2] == pushed_at[(2, 10)]
    assert o.i_head_ts[n - 1] == pushed_at[(n - 1, 120)]
    got = await serve(tb, 7)
    exp = [(1, d1), (0, arrivals[10][0]), (2, arrivals[10][2]), (1, arrivals[50][1]),
           (n - 1, arrivals[120][n - 1]), (0, arrivals[200][0]), (2, arrivals[299][2])]  # fmt: skip
    assert got == exp, f"order after the stall {[s for s, _ in got]}"
    await tb.finish()


# Covers: SPEC §4 (no empty-FIFO bypass: push at c with ready=1 -> no offer at c, fire at c+1)
@cocotb.test()
async def test_06_no_bypass_every_source(dut):
    tb = await new_tb(dut, "t06")
    n = tb.n
    for s in range(n):
        d = uniq(s, 1)
        o = await tb.cycle(push={s: d}, out_ready=1)
        assert (o.out_valid, o.fire, o.push) == (0, 0, 1 << s), f"source {s}: offered in its push cycle"
        o = await tb.cycle(out_ready=1)
        assert (o.fire, o.out_source, o.out_desc) == (1, s, d)
        assert o.fired.accept_cycle == o.cycle - 1
    # Push into an empty source while another source is being served: eligible only next cycle.
    other = n - 1
    await load_seq(tb, [{other: uniq(0, 2)}, {other: uniq(1, 2)}])
    o = await tb.cycle(push={0: uniq(2, 2)}, out_ready=1)
    assert (o.fire, o.out_source) == (1, other)
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source) == (1, other), "older head of the other source first"
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc) == (1, 0, uniq(2, 2))
    assert tb.cov.min_wait == 1
    await tb.finish()


# Covers: SPEC §4 (full FIFO refuses push even when its head fires that edge; ready next cycle)
@cocotb.test()
async def test_07_full_plus_pop_refusal(dut):
    tb = await new_tb(dut, "t07")
    n = tb.n
    for s in range(n):
        content = [uniq(i, s + 1) for i in range(16)]
        await load_seq(tb, [{s: d} for d in content])
        x = uniq(100, s + 1)
        o = await tb.cycle(push={s: x}, out_ready=0)  # full, no fire: refused
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0 and o.i_count[s] == 16
        o = await tb.cycle(push={s: x}, out_ready=1)  # full, head fires: still refused
        assert (o.fire, o.out_source, o.out_desc) == (1, s, content[0])
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0, "full FIFO must refuse a push on its pop edge"
        o = await tb.cycle(push={s: x}, out_ready=0)  # occupancy 15: ready again, accepted
        assert (o.in_ready >> s) & 1 == 1 and o.push == 1 << s and o.i_count[s] == 15
        o = await tb.cycle(out_ready=0)
        assert o.i_count[s] == 16
        got = await tb.drain()
        assert got == [(s, d) for d in content[1:]] + [(s, x)]
    assert tb.cov.full_refused == n and tb.cov.ready_after_full_fire == n
    await tb.finish()


# Covers: SPEC §4 (simultaneous push/pop: occupancy unchanged, order preserved, storage wraps)
@cocotb.test()
async def test_08_simultaneous_push_pop(dut):
    tb = await new_tb(dut, "t08")
    n = tb.n
    s = n // 2
    first = [uniq(i, 1) for i in range(3)]
    await load_seq(tb, [{s: d} for d in first])
    stream = [uniq(i, 2) for i in range(40)]
    got = []
    for i, d in enumerate(stream):
        o = await tb.cycle(push={s: d}, out_ready=1)
        assert o.fire == 1 and o.out_source == s and o.push == 1 << s and o.i_count[s] == 3, f"i={i}: {o}"
        got.append(o.out_desc)
    got += [d for _s, d in await tb.drain()]
    assert got == first + stream
    # Push on one source while another one fires.
    await load_seq(tb, [{0: uniq(0, 3)}])
    o = await tb.cycle(push={n - 1: uniq(1, 3)}, out_ready=1)
    assert (o.fire, o.out_source, o.push) == (1, 0, 1 << (n - 1))
    assert tb.cov.fire_with_push_same_src >= 40
    await tb.finish()


# Covers: SPEC §4-5 (at most one fire per cycle; back-to-back fires without bubbles while work exists)
@cocotb.test()
async def test_09_back_to_back_fires(dut):
    tb = await new_tb(dut, "t09")
    n = tb.n
    sched = [{h: uniq(3 * h + r, 1) for h in range(n)} for r in range(3)]
    await load_seq(tb, sched)
    b2b0 = tb.cov.b2b_fires
    got = await serve(tb, 3 * n)
    assert got == [(h, sched[r][h]) for r in range(3) for h in range(n)]
    assert tb.cov.b2b_fires - b2b0 == 3 * n - 1
    # Streaming: every source keeps offering; ready=1 -> a fire in every cycle, no bubble.
    rng = random.Random(f"{run_seed()}:t09:{n}")
    pending, serial = {}, 0
    stream_fires = 0
    for k in range(300):
        for h in range(n):
            if h not in pending and rng.random() < 0.5:
                pending[h] = uniq(serial, 2)
                serial += 1
        work = tb.outstanding() > 0  # accepted before this cycle and not yet delivered (pins)
        o = await tb.cycle(push=dict(pending), out_ready=1)
        assert o.fire == int(work), f"streaming cycle {k}: fire={o.fire} with work={work} (bubble)"
        stream_fires += o.fire
        for h in list(pending):
            if (o.push >> h) & 1:
                del pending[h]
    assert stream_fires >= 250 and tb.cov.b2b_switch > 0
    await tb.finish()


# Covers: SPEC §5 (synchronous reset mid-traffic and mid-hold, outputs inactive, new epoch; TB
#         responses of the old epoch still complete and never affect the DUT)
@cocotb.test()
async def test_10_reset_mid_traffic_and_mid_hold(dut):
    tb = await new_tb(dut, "t10", resp_delay=(4, 48))
    n = tb.n
    await load_seq(tb, [{h: uniq(h, 1) for h in range(n)}, {0: uniq(50, 1), n - 1: uniq(51, 1)}])
    await serve(tb, 3)  # three fires: responses outstanding across the reset
    o = await tb.cycle(out_ready=0)
    o = await tb.cycle(out_ready=0)
    assert o.i_held == 1
    counts_before = list(o.i_count)
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and o.i_count == counts_before, "reset is synchronous: no change before the edge"
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.i_held, o.i_head_valid, o.i_counter) == (0, 0, 0) and o.i_count == [0] * n
    fresh = uniq(0, 2)
    o = await tb.cycle(push={2: fresh}, out_ready=1)
    assert o.i_counter == 0 and o.out_valid == 0
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, o.i_head_ts[2]) == (1, 2, fresh, 0)

    # Reset on an unlocked valid+ready offer: no fire/pop on the reset edge.
    await load_seq(tb, [{1: uniq(1, 3)}], out_ready=0)
    o = await tb.cycle(out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.i_pop, o.i_held) == (0, 0, 0, 0) and o.i_count[1] == 1
    assert o.i_cand_valid == 1 and o.i_cand_source == 1, "an unlocked candidate existed on the reset edge"
    o = await tb.cycle()
    assert o.i_count == [0] * n and o.i_held == 0

    # A low pulse between edges clears nothing (synchronous reset).
    b = [uniq(0, 5), uniq(1, 5)]
    await load_seq(tb, [{3: b[0]}, {3: b[1]}])
    o = await tb.cycle(out_ready=0)
    assert o.i_held == 1
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


# Covers: SPEC §3 (all 105 descriptor bits transported intact, per source)
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


# Covers: SPEC §6 (TRUE timestamp wraparound: simulation-only deposit of the internal counter near
#         2^32, stored values straddle the wrap, pre-wrap arrivals win over numerically smaller
#         post-wrap timestamps, order = absolute arrival order of the model; counter resets to 0)
@cocotb.test()
async def test_12_true_timestamp_wrap(dut):
    tb = await new_tb(dut, "t12")
    n = tb.n
    hi = list(range(n // 2, n))
    lo = list(range(0, n // 2))
    v0 = TS_MOD - 6
    pre = [(hi[j % len(hi)], uniq(j, 1)) for j in range(6)]
    post = [(lo[j % len(lo)], uniq(j, 2)) for j in range(6)]
    seen_ts = []
    for j, (s, d) in enumerate(pre + post):
        o = await tb.cycle(push={s: d}, out_ready=0, deposit=v0 if j == 0 else None)
        assert o.i_counter == (v0 + j) % TS_MOD
        assert o.push == 1 << s
        seen_ts.append(o.i_counter)
    assert seen_ts == [0xFFFFFFFA, 0xFFFFFFFB, 0xFFFFFFFC, 0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFF, 0, 1, 2, 3, 4, 5]
    o = await tb.cycle(out_ready=0)
    pre_srcs = sorted({s for s, _d in pre})
    post_srcs = sorted({s for s, _d in post})
    assert o.i_head_valid == sum(1 << s for s in pre_srcs + post_srcs)
    for s in pre_srcs:
        assert o.i_head_ts[s] >= 0xFFFFFFFA, f"pre-wrap head of source {s}: {o.i_head_ts[s]:#x}"
    for s in post_srcs:
        assert o.i_head_ts[s] <= 5, f"post-wrap head of source {s}: {o.i_head_ts[s]:#x}"
    assert tb.cov.counter_wraps == 1
    wd0 = tb.cov.wrap_discriminating
    got = await serve(tb, 12)
    assert got == pre + post, f"wrap order {[s for s, _ in got]}"
    assert tb.cov.wrap_discriminating - wd0 >= 5, "pre-wrap heads must have won against smaller post-wrap values"

    # Random traffic across a second wrap, every cycle checked against the absolute-time model.
    await tb.cycle(rst_n=0)
    await tb.cycle(rst_n=0)
    rng = random.Random(f"{run_seed()}:t12:{n}")
    v1 = TS_MOD - 400
    pending, serial = {}, 0
    wd1 = tb.cov.wrap_discriminating
    for k in range(1500):
        for h in range(n):
            if h not in pending and rng.random() < 1.3 / n:
                pending[h] = uniq(serial, 3)
                serial += 1
        o = await tb.cycle(push=dict(pending), out_ready=int(rng.random() < 0.6), deposit=v1 if k == 0 else None)
        assert o.i_counter == (v1 + k) % TS_MOD
        for h in list(pending):
            if (o.push >> h) & 1:
                del pending[h]
    assert tb.cov.counter_wraps == 2
    assert tb.cov.wrap_discriminating - wd1 > 0, "no selection straddled the wrap in the random segment"
    await tb.drain()
    # Reset returns the counter to 0.
    await tb.cycle(rst_n=0)
    o = await tb.cycle()
    assert o.i_counter == 0
    await tb.finish()


# Covers: SPEC §4-6, §9 (whole contract under the policy-independent intended trace: ties, stalls,
#         directed long stalls, overload/full refusal, back-to-back, resets, TB tagged responses)
@cocotb.test()
async def test_13_short_random_trace(dut):
    from switch_fcfs_tb import run_trace

    seed = run_seed()
    tb = await new_tb(dut, "t13", unique_tags=True)
    trace = make_trace(seed, tb.n, SHORT_RANDOM_CYCLES, "short")
    dut._log.info("short trace sha256=%s generated=%d resets=%d", trace.sha256, trace.generated, sum(trace.reset))
    metrics = await run_trace(dut, tb, trace)
    write_json("fcfs_short_random.json", {"schema": "cxl-m3-fcfs-short-random-v1", "policy": "FCFS",
                                          "seed": seed, "n_src": tb.n, "trace_sha256": trace.sha256,
                                          **metrics})  # fmt: skip
    cov = tb.cov
    dut._log.info("short random coverage: %s", cov.summary())
    every = set(range(tb.n))
    assert cov.ties > 0 and cov.older_beats_lower > 0, "tie / age-over-ID bins"
    assert cov.stall_cycles > 0 and cov.max_valid_ready_low_run >= 100 and cov.holds > 0, "stall bins"
    assert cov.push_during_hold > 0 and cov.push_into_held_src > 0 and cov.hold_with_other_nonempty > 0
    assert cov.full_refused > 0, "full-plus-pop bin"
    assert cov.ready_after_full_fire + cov.full_fire_then_reset == cov.full_refused, "ready after full fire"
    assert cov.full_sources and cov.full_cycles > 0
    assert cov.b2b_fires > 0 and cov.b2b_switch > 0 and cov.fire_with_push_same_src > 0
    assert cov.resets >= 1 and cov.reset_nonempty >= 1 and tb.dropped_by_reset > 0, "reset bins"
    assert cov.min_wait == 1 and cov.fire_sources == every
    assert tb.resp.issued == tb.total_delivered > 0 and tb.resp.completed == tb.resp.issued
    assert tb.resp.reordered > 0 and tb.resp.cross_epoch_completions > 0, "response reorder/epoch bins"
    assert metrics["generation_to_acceptance"]["max"] > 0, "backpressure must delay some acceptance"
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0


# Covers: SPEC §4 (producer retains its valid descriptor until push: an offer refused by a full D16
#         FIFO in the last measured cycle stays valid with identical bits across measurement -> drain
#         until pushed; full-plus-pop refusal on the drain edge), §9/§10 (measurement snapshots frozen
#         at the boundary, drain-only accepts counted separately, every tag answered exactly once).
#         Deterministic regression of Codex finding C1 (reviews/phase-4-rtl/codex-fcfs-review.md).
@cocotb.test()
async def test_14_measurement_boundary_input_hold(dut):
    from switch_fcfs_tb import run_trace
    from traffic_trace import Trace, trace_sha256

    tb = await new_tb(dut, "t14", unique_tags=True)
    n = tb.n
    a, z, mid = 0, n - 1, 1  # two sources fill their FIFOs; one source has unoffered backlog
    cycles = 20
    serial = iter(range(1000))

    def tdesc() -> int:
        i = next(serial)
        return mk_desc(tag=0xC1000000 + i, addr=0x40000000 + i, opcode=i & 1, length=i & 0xFF, payload=0xDEAD0000 + i)

    tr = Trace(run_seed(), n, cycles, "primary")
    tr.gen = [[(a, tdesc()), (z, tdesc())] for _ in range(cycles)]
    tr.gen[cycles - 1] += [(mid, tdesc()), (mid, tdesc())]  # first accepted at the last edge, second never offered
    tr.ready = bytearray(cycles)  # downstream stalled for the whole measurement
    tr.reset = bytearray(cycles)
    tr.phases = [(0, cycles, "directed-boundary")]
    tr.sha256 = trace_sha256(tr)
    held = {a: tr.gen[16][0][1], z: tr.gen[16][1][1]}  # 17th descriptor: refused from cycle 16 on

    seen = []  # (TB cycle, in_valid, in_ready, desc[a], desc[z]) from the last measured cycle on
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
    # ... and kept valid with identical bits in the drain until pushed: a at the first drain edge
    # is refused (full + pop), pushed at the second; z (served second) is pushed at the third.
    drain = [s for s in seen if s[0] >= meas_end]
    push_at = {h: next(s[0] for s in drain if (s[5] >> h) & 1) for h in (a, z)}
    assert push_at == {a: meas_end + 1, z: meas_end + 2}, f"boundary pushes at {push_at}"
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
