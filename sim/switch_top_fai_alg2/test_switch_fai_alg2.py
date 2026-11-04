"""Cycle-exact cocotb tests of switch_top with POLICY=3 (supplementary FAI Algorithm-2, spec 8.6),
milestone M6.

N_SRC = 4 (initial supplementary scope, spec 8.5/8.6); FAI_W = 64 and 256 (stress windows, passed
with -G). Run through scripts/run_verify.sh M6 (it builds the design and exports CXL_PARAM_*).

Every cycle of every test goes through sim/common/switch_fai_tb.SwitchFaiTb with its explicit
interpretation selector at POLICY=3. That compares all pins, the observable internal state and
the FAI state (cls_q, idx_q, b_q, s_q, turn_q, used_q, offered/held context) with the independent
oracle refc/cxl_model/fai_alg2_model.py. It also applies the model-free pin/history rules: its own
spec 8.1 evidence, its own literal spec 8.6 table typed in the harness, window position from the
TB cycle count, B/S from pin fires and a visit/quota tracker. On top of that it keeps the pin-level
conservation/order/integrity/sideband scoreboard, the spec 4 producer hold and TB-only tagged
responses.

Each directed test additionally asserts LITERAL expectations derived by hand from spec 8.6 (and
the shared 4, 5, 6, 8.1, 8.3, 8.4) and docs/phase-3-uarch/fai_alg2.md; the derivation is written
next to it, and where Algorithm-2 differs observably from Main the Main outcome is noted.
Algorithm-2 state names: SH = stable High, SL = stable Low, BPH = Buffer p=High, BPL = Buffer p=Low.

Window plans: ``window(tb, gen, plan, close)`` drives one complete window from position 0 with a
single outstanding descriptor at a time, so ``plan[k]`` fires exactly at position k+1 and ``close``
fires at the closing position W-1 (same convention as sim/switch_top_fai/test_switch_fai.py).
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

# The pure-Python, DUT-independent stimulus helpers of the accepted M5 harness (fai_stream: the
# window-scaled class-dynamics trace) are reused unchanged from sim/switch_top_fai.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "switch_top_fai"))

from hier_util import hierarchy_paths  # noqa: E402
from switch_fai_tb import DESC_MASK, DESC_W, SwitchFaiTb, ctx_of_bits, fai_summary, run_seed, run_trace, write_json  # noqa: E402
from traffic_trace import make_trace  # noqa: E402

import cocotb  # noqa: E402

TAG_LSB, ADDR_LSB, OPCODE_LSB, LENGTH_LSB = 73, 41, 40, 32
TS_MOD = 1 << 32
SHORT_RANDOM_CYCLES = 12000
POLICY_FAI_ALG2 = 3
SH, SL, BPH, BPL = "STABLE_HIGH", "STABLE_LOW", "BUFFER_P_HIGH", "BUFFER_P_LOW"
ALL16 = {(s, e) for s in (SH, SL, BPH, BPL) for e in ("UP", "DOWN", "KEEP", "S0")}


def H(k: int) -> tuple:
    return ("High", k)


def L(k: int) -> tuple:
    return ("Low", k)


def mk_desc(tag: int, addr: int, opcode: int, length: int, payload: int) -> int:
    assert tag < (1 << 32) and addr < (1 << 32) and opcode < 2 and length < 256 and payload < (1 << 32)
    return (tag << TAG_LSB) | (addr << ADDR_LSB) | (opcode << OPCODE_LSB) | (length << LENGTH_LSB) | payload


def uniq(i: int, salt: int = 0) -> int:
    """A distinct descriptor (distinct Tag) per (index, salt) with every field populated."""
    assert 0 <= i < 0x10000 and 0 <= salt < 0x100
    return mk_desc(
        tag=(0xA2000000 + salt * 0x10000 + i) & 0xFFFFFFFF,
        addr=(0x32000000 + i * 0x01010101 + salt * 0x00310000) & 0xFFFFFFFF,
        opcode=(i ^ salt) & 1,
        length=(i * 7 + salt * 3 + 5) & 0xFF,
        payload=((i + 3) * 0x9E3779B1 + salt * 0x85EBCA6B) & 0xFFFFFFFF,
    )


class Descs:
    def __init__(self, salt: int) -> None:
        self.salt = salt
        self.i = 0

    def __call__(self) -> int:
        d = uniq(self.i, self.salt)
        self.i += 1
        return d


async def new_tb(dut, label: str, **kw) -> SwitchFaiTb:
    tb = SwitchFaiTb(dut, label, **kw)
    assert tb.policy == POLICY_FAI_ALG2 and tb.interp.name == "FAI_ALG2", f"built with POLICY={tb.policy}"
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) N_SRC=%d POLICY=%d FAI_W=%d DEPTH=%d DESC_W=%d TS_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.n, tb.policy, tb.w, tb.depth, tb.desc_w, tb.ts_w,
    )  # fmt: skip
    await tb.start()
    return tb


async def load_seq(tb: SwitchFaiTb, schedule, out_ready: int = 0):
    obs = []
    for pushes in schedule:
        o = await tb.cycle(push=pushes, out_ready=out_ready)
        for h in pushes:
            assert (o.push >> h) & 1, f"cycle {o.cycle}: push into source {h} was not accepted"
        obs.append(o)
    return obs


async def serve(tb: SwitchFaiTb, count: int):
    got = []
    for _ in range(count):
        o = await tb.cycle(out_ready=1)
        assert o.fire == 1, f"cycle {o.cycle}: expected a fire (work exists, ready=1)"
        got.append((o.out_source, o.out_desc))
    return got


async def script(tb: SwitchFaiTb, steps):
    """steps: list of (push dict or None, ready). Every push must be accepted."""
    obs = []
    for push, ready in steps:
        o = await tb.cycle(push=push, out_ready=ready)
        for h in push or {}:
            assert (o.push >> h) & 1, f"cycle {o.cycle}: push into source {h} was not accepted"
        obs.append(o)
    return obs


def fires(obs) -> list:
    """[(position, source, ctx)] of the fire cycles in ``obs``."""
    return [(o.pos, o.out_source, ctx_of_bits(o.i_grant_ctx)) for o in obs if o.fire]


async def reset(tb: SwitchFaiTb, k: int = 2) -> None:
    for _ in range(k):
        await tb.cycle(rst_n=0)
    assert tb.pos == 0


async def to_window_start(tb: SwitchFaiTb) -> None:
    while tb.pos != 0:
        await tb.cycle()


async def window(tb: SwitchFaiTb, gen: Descs, plan, close=None):
    """One complete window from position 0 (see module docstring). Returns the W observations."""
    w = tb.w
    assert tb.pos == 0, f"window must start at position 0 (next position {tb.pos})"
    assert tb.outstanding() == 0 and not tb.in_hold.pending
    at = {k + 1: s for k, s in enumerate(plan)}
    if close is not None:
        assert w - 1 not in at
        at[w - 1] = close
    assert all(1 <= p <= w - 1 for p in at), f"plan of {len(plan)} fires does not fit W={w}"
    obs = []
    for p in range(w):
        nxt = at.get(p + 1)
        push = {nxt: gen()} if nxt is not None else None
        o = await tb.cycle(push=push, out_ready=int(p in at))
        assert o.pos == p and o.i_idx == p
        if push:
            assert (o.push >> nxt) & 1, f"cycle {o.cycle}: plan push into source {nxt} refused"
        if p in at:
            assert (o.fire, o.out_source) == (1, at[p]), f"position {p}: expected source {at[p]} to fire"
        else:
            assert o.out_valid == 0
        obs.append(o)
    assert tb.pos == 0 and tb.outstanding() == 0
    return obs


def per_nw(tb: SwitchFaiTb, table: dict):
    assert (tb.n, tb.w) in table, f"no literal expectation for N={tb.n}, W={tb.w} (M6 runs N4 only)"
    return table[(tb.n, tb.w)]


def state(o) -> tuple:
    """(turn_q, used_q) during the cycle of ``o``: turn 0 = High, 1 = Low."""
    return (o.i_turn, o.i_used)


def spread(sources, count: int) -> list:
    return [sources[k % len(sources)] for k in range(count)]


# Covers: SPEC §3 (ports/widths), §5 (synchronous reset: every source STABLE_HIGH with no pending
#         Buffer, High visit first, quota / B / S / index / counter / held grant cleared, handshakes
#         inactive), §6 (arrival metadata kept for FAI), §8.5/§8.6 (same widths, same 5-bit context,
#         separate parameter selection in the shared switch: gen_policy_fai_alg2 with the shared
#         FIFOs / hold / counter / selector, no Main branch), §8.6 (one DOWN window gives
#         BUFFER_P_LOW, serviced at once in Low: Main would keep B_H in High)
@cocotb.test()
async def test_01_ports_reset_structure_shared_framework(dut):
    tb = await new_tb(dut, "a01")
    n, w = tb.n, tb.w
    gen = Descs(1)
    names = [p for p, _k in hierarchy_paths(dut)]
    fifo_idx = {int(m.group(1)) for p in names for m in [re.search(r"gen_fifo\[(\d+)\]\.u_fifo$", p)] if m}
    assert fifo_idx == set(range(n)), f"expected {n} cxl_desc_fifo instances, found {sorted(fifo_idx)}"
    assert len([p for p in names if p.endswith(".u_out_hold")]) == 1, "exactly one cxl_out_hold"
    assert len([p for p in names if p.endswith(".desc_mem_q")]) == n, "full descriptor storage per source"
    assert len([p for p in names if p.endswith(".ts_mem_q")]) == n, "FAI stores an arrival timestamp per entry"
    assert len([p for p in names if p.endswith("gen_arrival_ts.arrival_cnt_q")]) == 1, "one shared counter"
    sel = [p for p in names if p.endswith(".u_fcfs_sel")]
    assert len(sel) == 1 and sel[0].endswith("gen_policy_fai_alg2.u_fai_sched.u_fcfs_sel"), f"selectors {sel}"
    assert len([p for p in names if p.endswith("gen_policy_fai_alg2.u_fai_sched")]) == 1
    assert not any(re.search(r"gen_policy_(fcfs|rr|fai_main|unknown)|gen_no_arrival_ts|gen_bad_", p) for p in names)
    regs = {p.rsplit(".", 1)[1] for p in names if p.endswith("_q")}
    allowed = {"count_q", "wr_ptr_q", "rd_ptr_q", "desc_mem_q", "ts_mem_q", "held_q", "held_source_q",
               "held_ctx_q", "arrival_cnt_q", "cls_q", "idx_q", "b_q", "s_q", "turn_q", "used_q"}  # fmt: skip
    assert regs == allowed, f"state in switch_top FAI_ALG2: {sorted(regs)}"
    fai_regs = sorted(p.rsplit(".", 1)[1] for p in names if ".u_fai_sched." in p and p.endswith("_q"))
    assert fai_regs == ["b_q", "cls_q", "idx_q", "s_q", "turn_q", "used_q"], f"FAI policy registers {fai_regs}"
    assert len(dut.u_out_hold.held_ctx_q) == 5, "FAI context {class, used} is 5 bits"
    fai = dut.gen_policy_fai_alg2.u_fai_sched
    idx_bits, bs_bits = {64: (6, 7), 256: (8, 9)}[w]
    assert (len(fai.idx_q), len(fai.s_q), len(fai.b_q), len(fai.cls_q)) == (idx_bits, bs_bits, n * bs_bits, 2 * n)
    assert (len(fai.turn_q), len(fai.used_q)) == (1, 4)

    for k in range(5):
        o = await tb.cycle(out_ready=k & 1)
        assert o.i_counter == k and o.i_idx == k and o.out_valid == 0 and o.in_ready == tb.all_src
        assert o.i_cls == [SH] * n and o.i_b == [0] * n and o.i_s == 0 and state(o) == (0, 0)
    await to_window_start(tb)  # window 1 closes idle: zero service keeps every SH
    x = n - 1
    # Window 2: x fires at 1 (High,0; replacement pushed -> continue) and 2 (High,1; emptied -> turn
    # Low). Closing: B[x]=2, S=2: N*2 > 2 -> DOWN -> SH -> BPL (effective Low immediately).
    obs = await window(tb, gen, [x, x])
    assert [c for _p, _s, c in fires(obs)] == [H(0), H(1)]
    d = [gen() for _ in range(2)]
    o = await tb.cycle(push={x: d[0]})
    assert o.i_cls[x] == BPL and o.i_idx == 0 and state(o) == (1, 0)
    # Turn Low and x is Low (Buffer target): (Low,0). Main would offer (High,0) here (B_H is High).
    o = await tb.cycle(push={x: d[1]}, out_ready=1)
    assert (o.fire, o.out_source, ctx_of_bits(o.i_grant_ctx)) == (1, x, L(0))
    o = await tb.cycle(out_ready=0)
    assert (o.out_source, o.out_desc, o.i_held, ctx_of_bits(o.i_grant_ctx)) == (x, d[1], 0, L(1))
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and ctx_of_bits(o.i_held_ctx) == L(1) and o.i_count[x] == 1
    assert o.i_cls[x] == BPL and o.i_idx == 3 and o.i_b[x] == 1 and o.i_s == 1 and state(o) == (1, 1)
    assert o.i_counter == 2 * w + 3
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.i_held, o.i_head_valid, o.in_ready, o.i_counter, o.i_idx, o.i_s) == (0, 0, 0, 0, 0, 0)
    assert o.i_cls == [SH] * n and o.i_b == [0] * n and state(o) == (0, 0) and o.i_count == [0] * n
    o = await tb.cycle(push={1: d[0]}, out_ready=1)
    assert o.i_counter == 0 and o.out_valid == 0 and o.push == 0b10
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, o.i_head_ts[1], ctx_of_bits(o.i_grant_ctx)) == (1, 1, d[0], 0, H(0))
    assert await tb.finish() == []
    assert tb.dropped_by_reset == 1 and tb.cov.reset_during_hold == 1 and tb.cov.reset_non_h == 1


# Covers: SPEC §8.6 (exhaustive 4 x {UP, DOWN, KEEP, zero-service} table through REAL windows for one
#         source, and a second source following its own path in the same windows; Buffer settles on
#         the next UP/DOWN; KEEP and idle windows retain the Buffer and its target), §8.1 (exact
#         evidence), §8.4 (new state visible in the next cycle, B/S/index cleared)
@cocotb.test()
async def test_02_exhaustive_alg2_table(dut):
    tb = await new_tb(dut, "a02")
    n, w = tb.n, tb.w
    gen = Descs(2)
    x, p = n - 1, 0
    # Window kinds for x (single outstanding descriptor):
    #   UP  : p once            -> x B=0,S=1 UP;      p B=1,S=1 DOWN
    #   DOWN: x once            -> x DOWN;            p UP
    #   KEEP: x once, p N-1     -> x B=1,S=N KEEP;    p N(N-1) > N DOWN
    #   S0  : no fire           -> every source zero-service
    plans = {"UP": [p], "DOWN": [x], "KEEP": [x] + [p] * (n - 1), "S0": []}
    seq = ["UP", "KEEP", "S0", "DOWN", "KEEP", "S0", "UP", "DOWN", "DOWN",
           "KEEP", "S0", "DOWN", "UP", "KEEP", "S0", "DOWN", "UP", "UP"]  # fmt: skip
    # Hand-derived from the spec 8.6 table.
    exp_x = [SH, SH, SH, BPL, BPL, BPL, SH, BPL, SL, SL, SL, SL, BPH, BPH, BPH, SL, BPH, SH]
    # p sees DOWN, DOWN, S0, UP, DOWN, S0, DOWN, UP, UP, DOWN, S0, UP, DOWN, DOWN, S0, UP, DOWN, DOWN.
    exp_p = [BPL, SL, SL, BPH, SL, SL, SL, BPH, SH, BPL, BPL, SH, BPL, SL, SL, BPH, SL, SL]
    prev_x, prev_p = SH, SH
    for k, kind in enumerate(seq):
        obs = await window(tb, gen, plans[kind])
        first, last = obs[0], obs[-1]
        assert (first.i_idx, first.i_b, first.i_s) == (0, [0] * n, 0), f"window {k}: B/S/index not cleared"
        assert (first.i_cls[x], first.i_cls[p]) == (prev_x, prev_p), f"window {k}: start states"
        assert last.i_idx == w - 1 and last.i_cls[x] == prev_x, f"window {k}: state changed before the next cycle"
        assert last.evidence[x] == kind, f"window {k}: evidence of x {last.evidence[x]}, expected {kind}"
        prev_x, prev_p = exp_x[k], exp_p[k]
        assert last.new_cls[x] == prev_x and last.new_cls[p] == prev_p, f"window {k}: {last.new_cls}"
    o = await tb.cycle()
    assert o.i_cls[x] == SH and o.i_cls[p] == SL and all(c == SH for c in o.i_cls[1:x])
    assert tb.cov.source_transitions(x) == ALL16, f"missing {ALL16 - tb.cov.source_transitions(x)}"
    assert tb.cov.windows_closed == len(seq) and tb.cov.evidence["S0"] == 4 * n
    await tb.finish()


# Covers: SPEC §8.6 ("A Buffer request is immediately serviced in stored target class p. Unlike Main,
#         Buffer does not retain the previous effective class"), both targets, observed in the
#         selection order of same-cycle arrivals; §8.3 (10/10 visit continuation / class switch)
@cocotb.test()
async def test_03_buffer_target_serviced_immediately(dut):
    tb = await new_tb(dut, "a03")
    n = tb.n
    gen = Descs(3)
    x, p = n - 1, 0
    # Scenario A (target Low): one DOWN window [x] -> x BPL; the visit ends (High,0) emptied ->
    # turn Low. 0 and x arrive together: turn Low, x Low -> x (Low,0), emptied -> 0 (High,0).
    # Main would have x in B_H (High): turn Low empty -> High, same timestamps -> 0 first.
    await window(tb, gen, [x])
    a0, x0 = gen(), gen()
    obs = await script(tb, [({p: a0, x: x0}, 0), (None, 1), (None, 1)])
    assert obs[0].i_cls[x] == BPL and obs[0].i_cls[p] == SH and state(obs[0]) == (1, 0)
    assert fires(obs) == [(1, x, L(0)), (2, p, H(0))], f"fires {fires(obs)}"
    assert [o.out_desc for o in obs if o.fire] == [x0, a0]
    # Scenario B (target High): two DOWN windows -> x SL (visits: (Low,0) after each). An UP window
    # for x (p fires once: p DOWN) -> x BPH (High), p BPL (Low); p's fire was (High,0) emptied ->
    # turn Low. p and x arrive together: p (Low,0) first, then x (High,0). Main would have x B_L
    # (Low) and p B_H (High): x (Low,0) first.
    await to_window_start(tb)
    await reset(tb)
    await window(tb, gen, [x])
    await window(tb, gen, [x])
    obs = await window(tb, gen, [p])
    assert obs[0].i_cls[x] == SL and fires(obs) == [(1, p, H(0))]
    a1, x1 = gen(), gen()
    obs = await script(tb, [({p: a1, x: x1}, 0), (None, 1), (None, 1)])
    assert obs[0].i_cls[x] == BPH and obs[0].i_cls[p] == BPL and state(obs[0]) == (1, 0)
    assert fires(obs) == [(1, p, L(0)), (2, x, H(0))], f"fires {fires(obs)}"
    await tb.finish()


# Covers: SPEC §4 stall clarification / §8.3 / §8.4 step 5 (a held grant keeps source, class and
#         quota context through a Buffer TARGET change at a closing edge and through several further
#         idle windows; its fire is charged to the retained context; later unlocked selections use
#         the current map), §8.6 (idle zero-service windows retain BUFFER_P_LOW without cancellation;
#         Main would cancel a pending B_H back to H on S=0)
@cocotb.test()
async def test_04_held_grant_across_target_change_and_idle_windows(dut):
    tb = await new_tb(dut, "a04")
    n, w = tb.n, tb.w
    gen = Descs(4)
    x, p, y = 1, 2, 0
    await window(tb, gen, [x])  # x: SH -> BPL; visit (High,0) emptied -> turn Low
    p0, x0, y0 = gen(), gen(), gen()
    # Window B positions: 0 push p; 1 p fires (turn Low, Low class empty -> High (High,0); emptied ->
    # turn Low), x pushed; 2 x offered (Low,0) (x Low) and stalled; held through the closing edge.
    # Closing: B[p]=1, S=1 -> p DOWN: SH -> BPL; x B=0 -> UP: BPL -> SH (target flips to High).
    # Two more complete idle windows (zero service) keep x SH and p BPL. y arrives during the stall.
    steps = [({p: p0}, 0), ({x: x0}, 1)] + [(({y: y0} if k == 5 else None), 0) for k in range(2, 3 * w)]
    steps += [(None, 1), (None, 1), (None, 1)]
    obs = await script(tb, steps)
    for o in obs[3:3 * w]:
        assert (o.out_valid, o.out_source, o.out_desc, o.i_held) == (1, x, x0, 1), f"cycle {o.cycle}: offer changed"
        assert ctx_of_bits(o.i_grant_ctx) == L(0) and ctx_of_bits(o.i_held_ctx) == L(0)
    assert obs[w - 1].closing and obs[w - 1].evidence[:3] == ["UP", "UP", "DOWN"]
    assert (obs[w].i_cls[x], obs[w].i_cls[p], obs[w].i_cls[y]) == (SH, BPL, SH)
    for k in (2 * w - 1, 3 * w - 1):
        assert obs[k].closing and obs[k].evidence == ["S0"] * n, f"idle closing at {k}: {obs[k].evidence}"
        assert obs[k + 1].i_cls[p] == BPL and obs[k + 1].i_cls[x] == SH, "idle window must retain the Buffer"
    # x fires with its retained (Low,0) at position 0 of the fourth window although x is now High.
    # The Low class (p BPL, empty) is not live -> emptied -> turn High: y (High,0), emptied -> Low.
    got = fires(obs)
    assert got == [(1, p, H(0)), (0, x, L(0)), (1, y, H(0))], f"fires {got}"
    # The ignored unlocked candidate of that cycle already uses the current map: turn Low has no
    # eligible head (p empty), so High: x's own head (now High, older than y) with (High,0).
    hf = obs[3 * w]
    assert hf.i_held and (hf.i_cand_valid, hf.i_cand_source, ctx_of_bits(hf.i_cand_ctx)) == (1, x, H(0))
    assert hf.edge.held_mismatch, "held fire is charged to the retained (Low,0), not the candidate"
    assert tb.cov.held_cls_change == 1 and tb.cov.held_fire_cls_differs == 1 and tb.cov.max_windows_in_hold >= 3
    await tb.finish()


# Covers: SPEC §8.1 threshold equality / just below / just above at N4 with exact integers;
#         UP observed from SL (SL -> BPH vs KEEP SL), DOWN from SH (SH -> BPL vs KEEP SH)
@cocotb.test()
async def test_05_threshold_equality_boundaries(dut):
    tb = await new_tb(dut, "a05")
    n = tb.n
    gen = Descs(5)
    x = 1
    others = [h for h in range(n) if h != x]
    # UP iff 40B < 3S at N4: B=3 around S=40 (W64), B=12 around S=160 (W256); equality is KEEP.
    up_cases = per_nw(tb, {
        (4, 64): [(3, 39, SL), (3, 40, SL), (3, 41, BPH)],
        (4, 256): [(12, 159, SL), (12, 160, SL), (12, 161, BPH)],
    })  # fmt: skip
    # DOWN iff 4B > S: (1,3) DOWN, (1,4) equality KEEP, (1,5) KEEP, (2,7) DOWN, (2,8) equality KEEP.
    down_cases = [(1, 3, BPL), (1, 4, SH), (1, 5, SH), (2, 7, BPL), (2, 8, SH)]
    for b, s, exp in up_cases:
        await reset(tb)
        await window(tb, gen, [x])  # DOWN: SH -> BPL
        await window(tb, gen, [x])  # DOWN: BPL -> SL
        obs = await window(tb, gen, [x] * b + spread(others, s - b))
        assert obs[0].i_cls[x] == SL and obs[-1].b_close[x] == b and obs[-1].s_close == s
        o = await tb.cycle()
        assert o.i_cls[x] == exp, f"UP threshold B={b} S={s}: {o.i_cls[x]}, expected {exp}"
    for b, s, exp in down_cases:
        await reset(tb)
        obs = await window(tb, gen, [x] * b + spread(others, s - b))
        assert obs[-1].s_close == s and obs[-1].b_close[x] == b
        o = await tb.cycle()
        assert o.i_cls[x] == exp, f"DOWN threshold B={b} S={s}: {o.i_cls[x]}, expected {exp}"
    await tb.finish()


# Covers: SPEC §8.5 (at least 31-bit widened unsigned threshold intermediates with zero-extended
#         operands: 10*N*B or 3*S exceed the parameter-derived B/S width (W64: 7 bits, W256: 9 bits);
#         a comparison truncated to that width would classify differently in every case)
@cocotb.test()
async def test_06_widened_threshold_arithmetic(dut):
    tb = await new_tb(dut, "a06")
    n, w = tb.n, tb.w
    gen = Descs(6)
    x = n - 2
    others = [h for h in range(n) if h != x]
    bs_bits = {64: 7, 256: 9}[w]
    # From SL. W64: (4,40): 160 >= 120, 16 <= 40 KEEP (160 mod 128 = 32 < 120 would be UP);
    #               (3,43): 120 < 129 UP (129 mod 128 = 1 would be KEEP).
    #         W256: (13,60): 520 >= 180, 52 <= 60 KEEP (520 mod 512 = 8 < 180 would be UP);
    #               (12,171): 480 < 513 UP (513 mod 512 = 1 would be KEEP).
    cases = per_nw(tb, {(4, 64): [(4, 40, SL), (3, 43, BPH)], (4, 256): [(13, 60, SL), (12, 171, BPH)]})
    for b, s, exp in cases:
        assert 10 * n * b >= (1 << bs_bits) or 3 * s >= (1 << bs_bits)
        await reset(tb)
        await window(tb, gen, [x])
        await window(tb, gen, [x])
        obs = await window(tb, gen, [x] * b + spread(others, s - b))
        assert obs[0].i_cls[x] == SL and obs[-1].s_close == s and obs[-1].b_close[x] == b
        o = await tb.cycle()
        assert o.i_cls[x] == exp, f"widened W={w} B={b} S={s}: {o.i_cls[x]}, expected {exp}"
    await tb.finish()


# Covers: SPEC §8.1/§8.4 steps 1-4 (closing counts include the closing-edge fire; the new state is
#         visible only in the next cycle; B, S and index cleared), §8.6 (KEEP retains a Buffer:
#         Main would cancel B_H to H in case B)
@cocotb.test()
async def test_07_closing_edge_fire_inclusion(dut):
    tb = await new_tb(dut, "a07")
    n, w = tb.n, tb.w
    gen = Descs(7)
    x, p = n - 1, 0
    fill = list(range(1, n - 1))
    # Case A: x's only fire is AT the closing edge. Included: B=1, S=1 -> DOWN: SH -> BPL.
    # (Excluded it would be a zero-service window: SH.)
    obs = await window(tb, gen, [], close=x)
    last = obs[-1]
    assert last.fire and last.out_source == x and (last.i_b[x], last.i_s, last.i_cls[x]) == (0, 0, SH)
    # Case B: x once, fill once each, p at the closing edge. Included: B[x]=1, S=N -> KEEP: BPL
    # retained. (Excluded: S=N-1 -> 4 > 3 DOWN: BPL -> SL.)
    obs = await window(tb, gen, [x] + fill, close=p)
    first, last = obs[0], obs[-1]
    assert first.i_cls[x] == BPL and first.i_cls[p] == SH
    assert last.out_source == p and last.fire and (last.i_b[x], last.i_s) == (1, n - 1) and last.i_cls[x] == BPL
    o = await tb.cycle()
    assert (o.i_idx, o.i_b, o.i_s) == (0, [0] * n, 0)
    assert o.i_cls == [SH] * (n - 1) + [BPL], f"case B states {o.i_cls}: x keeps BPL (closing fire counted, KEEP)"
    assert tb.cov.closing_fire == 2
    await tb.finish()


# Covers: SPEC §8.3/Q2 with a Buffer class (10/10 visits: Low = BPL source, High = SH source; expiry
#         at 10 fires even with a same-edge replacement and a live class; an emptied class
#         relinquishes its quota; renewed quota on a new visit, no banking; held first offer)
@cocotb.test()
async def test_08_quota_alternation_with_buffer_class(dut):
    tb = await new_tb(dut, "a08")
    gen = Descs(8)
    x, y = tb.n - 1, 0
    await window(tb, gen, [x])  # x BPL (Low); visit (Low,0)
    xs = [gen() for _ in range(12)]
    ys = [gen() for _ in range(13)]
    # Positions 0..11: push x and y each cycle, ready=0. x is offered at 1 with (Low,0) and held.
    steps = [({x: xs[k], y: ys[k]}, 0) for k in range(12)]
    # Then ready=1: x L0..L9 (expired), y H0..H9 (the 10th with a replacement push: still expired),
    # x L0, L1 (emptied), y H0, H1, H2 (12 - 10 + 1 left; emptied).
    serve_steps = [(None, 1)] * 25
    serve_steps[19] = ({y: ys[12]}, 1)  # the 20th fire is y's 10th
    obs = await script(tb, steps + serve_steps)
    got = [(s, c) for _p, s, c in fires(obs)]
    exp = ([(x, L(k)) for k in range(10)] + [(y, H(k)) for k in range(10)] + [(x, L(0)), (x, L(1))]
           + [(y, H(k)) for k in range(3)])  # fmt: skip
    assert got == exp, f"fires {got}"
    assert [o.out_desc for o in obs if o.fire and o.out_source == x] == xs
    assert [o.out_desc for o in obs if o.fire and o.out_source == y] == ys
    ev = [o.visit_event for o in obs if o.fire]
    assert ev[9] == "expired" and ev[19] == "expired" and ev[21] == "emptied" and ev[24] == "emptied"
    assert tb.cov.visits_expired_replaced >= 1 and tb.cov.visits_expired_live >= 1
    assert obs[-1].pos < tb.w - 1, "scenario inside one window"
    await tb.finish()


# Covers: SPEC §6/§8.3 inside a Buffer target class (shared FCFS head selection: older head beats a
#         lower ID; same-cycle ties go to the lower ID; the visit class is chosen before age: an older
#         head of the other class waits). One DOWN window suffices for BPL (Main needs two for L).
@cocotb.test()
async def test_09_fcfs_ties_and_age_within_buffer_class(dut):
    tb = await new_tb(dut, "a09")
    gen = Descs(9)
    await window(tb, gen, [1, 3])  # B=1, S=2 each: 4 > 2 DOWN -> 1, 3 BPL; visit -> turn Low
    l = [gen() for _ in range(5)]
    h0, h2 = gen(), gen()
    steps = [({3: l[0]}, 0), ({3: l[1]}, 0), ({1: l[2], 3: l[3]}, 0), (None, 1), (None, 1), (None, 1),
             (None, 1), ({2: h2}, 0), ({3: l[4]}, 0), ({0: h0}, 0), (None, 1), (None, 1), (None, 1),
             (None, 1)]  # fmt: skip
    obs = await script(tb, steps)
    assert obs[0].i_cls == [SH, BPL, SH, BPL] and state(obs[0]) == (1, 0)
    got = [(s, c) for _p, s, c in fires(obs)]
    # 3's l0 offered (Low,0), held, fires; then 3's l1 (pushed at 1) is older than 1's l2 (pushed at
    # 2): the older head beats the lower ID; then l2 / l3 (same cycle) tie -> source 1 first; 3
    # empties Low -> High: 2's h2 offered and held while 3 (Low, l4) and 0 (High) arrive; the High
    # visit continues with 0 although l4 is older; then 3 (Low,0).
    assert got == [(3, L(0)), (3, L(1)), (1, L(2)), (3, L(3)), (2, H(0)), (0, H(1)), (3, L(0))], f"fires {got}"
    assert [o.out_desc for o in obs if o.fire][:4] == [l[0], l[1], l[2], l[3]]
    # Exactly one unlocked same-timestamp tie (l2 / l3) and one older-higher-ID win (l1 over l2). The
    # first M6 run asserted ties >= 2, copied from the Main test_12 whose High-class first half adds
    # a second tie this scenario does not contain (test derivation error, corrected with the
    # scenario; see docs/phase-5-verification/M6-results.md).
    assert tb.cov.ties_in_class == 1 and tb.cov.older_beats_lower_in_class == 1 and tb.cov.class_over_age >= 1
    await tb.finish()


# Covers: SPEC §6 (true timestamp wraparound under Algorithm-2: simulation-only deposit of
#         gen_arrival_ts.arrival_cnt_q in the first cycle after reset, mirrored by the oracle;
#         pre-wrap arrivals win over numerically smaller post-wrap timestamps; random segment with
#         closing windows across a second wrap). LABEL: simulation-only state deposit.
@cocotb.test()
async def test_10_true_timestamp_wrap(dut):
    tb = await new_tb(dut, "a10")
    n = tb.n
    gen = Descs(10)
    hi, lo = list(range(n // 2, n)), list(range(0, n // 2))
    v0 = TS_MOD - 6
    pre = [(hi[j % len(hi)], gen()) for j in range(6)]
    post = [(lo[j % len(lo)], gen()) for j in range(6)]
    seen_ts = []
    for j, (s, d) in enumerate(pre + post):
        o = await tb.cycle(push={s: d}, out_ready=0, deposit=v0 if j == 0 else None)
        assert o.i_counter == (v0 + j) % TS_MOD and o.push == 1 << s
        seen_ts.append(o.i_counter)
    assert seen_ts == [0xFFFFFFFA, 0xFFFFFFFB, 0xFFFFFFFC, 0xFFFFFFFD, 0xFFFFFFFE, 0xFFFFFFFF, 0, 1, 2, 3, 4, 5]
    o = await tb.cycle(out_ready=0)
    assert o.i_cls == [SH] * n and tb.cov.counter_wraps == 1
    wd0 = tb.cov.wrap_discriminating
    got = await serve(tb, 12)
    assert got == pre + post, f"wrap order {[s for s, _ in got]}"
    assert tb.cov.wrap_discriminating - wd0 >= 5
    await reset(tb)
    rng = random.Random(f"{run_seed()}:a10:{n}:{tb.w}")
    v1 = TS_MOD - 400
    pending = {}
    wd1 = tb.cov.wrap_discriminating
    for k in range(1500):
        for h in range(n):
            if h not in pending and rng.random() < 1.3 / n:
                pending[h] = gen()
        o = await tb.cycle(push=dict(pending), out_ready=int(rng.random() < 0.6), deposit=v1 if k == 0 else None)
        assert o.i_counter == (v1 + k) % TS_MOD
        for h in list(pending):
            if (o.push >> h) & 1:
                del pending[h]
    assert tb.cov.counter_wraps == 2 and tb.cov.windows_closed >= 1500 // tb.w
    assert tb.cov.wrap_discriminating - wd1 > 0
    await tb.drain()
    await tb.cycle(rst_n=0)
    o = await tb.cycle()
    assert o.i_counter == 0
    await tb.finish()


# Covers: SPEC §5 (reset in the middle of a window, a visit and a hold, with a pending Buffer: every
#         source back to STABLE_HIGH, nothing old resurfaces; the next idle window keeps SH), §9
#         (TB-only tagged responses of the old epoch still complete)
@cocotb.test()
async def test_11_reset_mid_window_visit_hold_buffer(dut):
    tb = await new_tb(dut, "a11")
    n, w = tb.n, tb.w
    gen = Descs(11)
    x = 2
    await window(tb, gen, [x, x])  # x BPL
    a = [gen() for _ in range(3)]
    obs = await script(tb, [({x: a[0], 0: a[1]}, 0), (None, 1), (None, 0), (None, 0)])
    # Turn Low: x (Low,0) fires at 1 (Low emptied -> High); 0 offered (High,0) at 2 and held.
    assert fires(obs) == [(1, x, L(0))] and obs[3].i_held and obs[3].out_source == 0
    assert obs[3].i_cls[x] == BPL and obs[3].i_idx == 3
    await reset(tb)
    o = await tb.cycle()
    assert o.i_cls == [SH] * n and o.i_b == [0] * n and state(o) == (0, 0) and o.i_count == [0] * n
    assert o.i_held == 0 and o.i_idx == 0
    await to_window_start(tb)  # the rest of the first post-reset window closes idle: SH kept
    o = await tb.cycle(push={3: a[2]}, out_ready=0)
    assert o.i_cls == [SH] * n and o.i_idx == 0 and tb.cov.windows_closed >= 1
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, ctx_of_bits(o.i_grant_ctx)) == (1, 3, a[2], H(0))
    assert await tb.finish() == []
    assert tb.dropped_by_reset == 1 and tb.cov.reset_non_h >= 1 and tb.cov.reset_during_hold == 1
    assert w in (64, 256)


# Covers: SPEC §4 (a full FIFO refuses a push even when its head fires that edge; ready again next
#         cycle; the refused replacement does not count as post-edge occupancy)
@cocotb.test()
async def test_12_full_plus_pop_refusal(dut):
    tb = await new_tb(dut, "a12")
    n = tb.n
    gen = Descs(12)
    for s in range(n):
        content = [gen() for _ in range(16)]
        await load_seq(tb, [{s: d} for d in content])
        x = gen()
        o = await tb.cycle(push={s: x}, out_ready=0)
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0 and o.i_count[s] == 16
        o = await tb.cycle(push={s: x}, out_ready=1)
        assert (o.fire, o.out_source, o.out_desc) == (1, s, content[0])
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0, "full FIFO must refuse a push on its pop edge"
        assert o.visit_event == "continue"
        o = await tb.cycle(push={s: x}, out_ready=0)
        assert (o.in_ready >> s) & 1 == 1 and o.push == 1 << s and o.i_count[s] == 15
        await tb.cycle(out_ready=0)
        got = await tb.drain()
        assert got == [(s, d) for d in content[1:]] + [(s, x)]
    assert tb.cov.full_refused == n and tb.cov.ready_after_full_fire == n
    await tb.finish()


# Covers: SPEC §4 (no empty-FIFO bypass: a push at c is eligible no earlier than c+1)
@cocotb.test()
async def test_13_no_bypass_next_cycle_eligibility(dut):
    tb = await new_tb(dut, "a13")
    n = tb.n
    gen = Descs(13)
    for s in range(n):
        d = gen()
        o = await tb.cycle(push={s: d}, out_ready=1)
        assert (o.out_valid, o.fire, o.push, o.i_cand_valid) == (0, 0, 1 << s, 0)
        o = await tb.cycle(out_ready=1)
        assert (o.fire, o.out_source, o.out_desc) == (1, s, d) and o.fired.accept_cycle == o.cycle - 1
    assert tb.cov.min_wait == 1
    await tb.finish()


# Covers: SPEC §3 (all 105 descriptor bits transported intact per source; source sideband)
@cocotb.test()
async def test_14_walking_ones_and_zeros_all_bits(dut):
    tb = await new_tb(dut, "a14", resp_delay=(1, 1))
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


# Covers: SPEC §4, §5, §6, §8.1, §8.3-8.6, §9 (whole Algorithm-2 contract under the policy-independent
#         intended trace used for FCFS/RR/Main: windows, evidence, Buffer states, visits/quota,
#         stalls, overload/full refusal, resets, TB tagged responses)
@cocotb.test()
async def test_15_short_random_trace(dut):
    seed = run_seed()
    tb = await new_tb(dut, "a15", unique_tags=True)
    trace = make_trace(seed, tb.n, SHORT_RANDOM_CYCLES, "short")
    metrics = await run_trace(dut, tb, trace)
    cov = tb.cov
    write_json("fai_alg2_short_random.json", {"schema": "cxl-m6-fai-alg2-short-random-v1", "policy": "FAI_ALG2",
                                              "policy_param": 3, "fai_w": tb.w, "seed": seed, "n_src": tb.n,
                                              "trace_sha256": trace.sha256,
                                              "fai_measurement": fai_summary(metrics["coverage_measurement"], tb.w),
                                              **metrics})  # fmt: skip
    dut._log.info("short random coverage: %s", cov.summary())
    assert cov.stall_cycles > 0 and cov.holds > 0 and cov.push_during_hold > 0 and cov.full_refused > 0
    assert cov.ready_after_full_fire + cov.full_fire_then_reset == cov.full_refused
    assert cov.b2b_fires > 0 and cov.fire_with_push_same_src > 0
    assert cov.resets >= 1 and cov.reset_nonempty >= 1 and tb.dropped_by_reset > 0
    assert cov.min_wait == 1 and cov.fire_sources == set(range(tb.n))
    assert cov.windows_closed >= (SHORT_RANDOM_CYCLES // tb.w) // 2
    assert cov.evidence["DOWN"] > 0 and cov.closing_fire > 0
    assert cov.visits_expired > 0 and cov.visits_emptied > 0 and cov.visits_continue > 0
    assert tb.resp.issued == tb.total_delivered > 0 and tb.resp.completed == tb.resp.issued
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0


# Covers: SPEC §8.6 under the window-scaled class-dynamics stress trace (shares skewed per window,
#         flips, idle and whole-window stall phases, resets): Buffer states with both targets are
#         entered and left, Buffer service in the target class happens, idle/KEEP retention of a
#         Buffer occurs, held grants span closings; every cycle checked by all harness layers
@cocotb.test()
async def test_16_class_dynamics_trace(dut):
    from fai_stream import make_fai_stress_trace

    seed = run_seed()
    tb = await new_tb(dut, "a16", unique_tags=True)
    # 12,800 (W64, 200 nominal windows) / 25,600 (W256, 100 nominal windows). The first M6 run used
    # 96 / 48 windows and W256 seed 509 did not reach BUFFER_P_LOW/UP; the stimulus was lengthened,
    # the requirement kept.
    cycles = {64: 200, 256: 100}[tb.w] * tb.w
    trace = make_fai_stress_trace(seed, tb.n, cycles, tb.w)
    metrics = await run_trace(dut, tb, trace)
    cov = tb.cov
    fai = fai_summary(metrics["coverage_measurement"], tb.w)
    write_json("fai_alg2_class_dynamics.json", {"schema": "cxl-m6-fai-alg2-class-dynamics-v1", "policy": "FAI_ALG2",
                                                "policy_param": 3, "fai_w": tb.w, "seed": seed, "n_src": tb.n,
                                                "cycles": cycles, "trace_sha256": trace.sha256,
                                                "fai_measurement": fai, **metrics})  # fmt: skip
    dut._log.info("class dynamics: %s transitions=%s", fai["evidence"], fai["transitions_reached"])
    states = {s for _h, s in cov.states_seen}
    assert {SH, SL, BPH, BPL} <= states, f"states reached {sorted(states)}"
    reached = {tuple(t.split("/")) for t in fai["transitions_reached"]}
    for need in ((SH, "DOWN"), (SL, "UP"), (BPL, "UP"), (BPL, "DOWN"), (BPH, "UP"), (BPH, "DOWN")):
        assert need in reached, f"transition {need} not reached; reached {sorted(reached)}"
    assert (BPL, "S0") in reached or (BPL, "KEEP") in reached or (BPH, "S0") in reached or (BPH, "KEEP") in reached
    assert cov.effective_changes > 0 and cov.fires_low > 0 and cov.fires_high > 0
    assert cov.held_across_closing > 0
    assert tb.resp.completed == tb.resp.issued == tb.total_delivered
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
