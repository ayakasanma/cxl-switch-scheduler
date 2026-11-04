"""Cycle-exact cocotb tests of switch_top with POLICY=2 (FAI-inspired Main), milestone M5.

N_SRC = 4, 8, 16; FAI_W = 64 and 256 (stress windows, spec 8.5; passed with -G). Run through
scripts/run_verify.sh M5 (it builds the design and exports CXL_PARAM_*).

Every cycle of every test goes through sim/common/switch_fai_tb.SwitchFaiTb, which compares all
pins, the observable internal state and the Main FAI state (cls_q, idx_q, b_q, s_q, turn_q,
used_q, offered/held context) with the independent oracle refc/cxl_model/fai_main_model.py,
applies model-free pin/history rules (own spec 8.1 evidence + literal spec 8.2 table, window
position from the TB cycle count, B/S from pin fires, visit/quota tracker), keeps a pin-level
conservation/order/integrity/sideband scoreboard, checks the spec 4 producer hold on the observed
input pins and matches TB-only tagged responses exactly once.

On top of that each directed test asserts LITERAL expectations derived by hand from the spec
(specs/CXL_SPEC.md v1.0 sections 4, 5, 6, 8.1-8.4) and docs/phase-3-uarch/fai_main.md; the
derivation of each scenario is written next to it. Every test runs at both stress windows: where
a literal scenario needs a specific W the expectation table has a documented W-specific entry
(nothing is skipped).

Window plans: ``window(tb, plan, close)`` drives one complete window from position 0 with a
single outstanding descriptor at a time, so ``plan[k]`` fires exactly at position k+1 regardless
of the class map, and ``close`` fires exactly at the closing position W-1. That makes B and S of
every window literal. Notation: ctx (class, fires already charged), H(k) = ("High", k).
"""

from __future__ import annotations

import random
import re

from hier_util import hierarchy_paths
from switch_fai_tb import DESC_MASK, DESC_W, SwitchFaiTb, ctx_of_bits, fai_summary, run_seed, run_trace, write_json
from traffic_trace import make_trace

import cocotb
from cocotb.triggers import ReadOnly, Timer

TAG_LSB, ADDR_LSB, OPCODE_LSB, LENGTH_LSB = 73, 41, 40, 32
TS_MOD = 1 << 32
SHORT_RANDOM_CYCLES = 12000
DEPTH_D16 = 16  # spec: D16 FIFO per source


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
        tag=(0xFA000000 + salt * 0x10000 + i) & 0xFFFFFFFF,
        addr=(0x30000000 + i * 0x01010101 + salt * 0x00310000) & 0xFFFFFFFF,
        opcode=(i ^ salt) & 1,
        length=(i * 7 + salt * 3 + 3) & 0xFF,
        payload=((i + 1) * 0x9E3779B1 + salt * 0x85EBCA6B) & 0xFFFFFFFF,
    )


class Descs:
    """Fresh distinct descriptors for one test (salt keeps tests apart)."""

    def __init__(self, salt: int) -> None:
        self.salt = salt
        self.i = 0

    def __call__(self) -> int:
        d = uniq(self.i, self.salt)
        self.i += 1
        return d


async def new_tb(dut, label: str, **kw) -> SwitchFaiTb:
    tb = SwitchFaiTb(dut, label, **kw)
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) N_SRC=%d POLICY=%d FAI_W=%d DEPTH=%d DESC_W=%d TS_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.n, tb.policy, tb.w, tb.depth, tb.desc_w, tb.ts_w,
    )  # fmt: skip
    await tb.start()
    return tb


async def load_seq(tb: SwitchFaiTb, schedule, out_ready: int = 0):
    """schedule: list of {source: desc} per cycle. Every push must be accepted."""
    obs = []
    for pushes in schedule:
        o = await tb.cycle(push=pushes, out_ready=out_ready)
        for h in pushes:
            assert (o.push >> h) & 1, f"cycle {o.cycle}: push into source {h} was not accepted"
        obs.append(o)
    return obs


async def serve(tb: SwitchFaiTb, count: int):
    """ready=1 for ``count`` cycles, each must fire. Returns [(source, desc)]."""
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
    """Idle (ready=0, nothing offered) until the next cycle is window position 0."""
    while tb.pos != 0:
        await tb.cycle()


async def window(tb: SwitchFaiTb, gen: Descs, plan, close=None):
    """One complete window from position 0. ``plan[k]`` fires at position k+1 (pushed at k, the
    only outstanding descriptor); ``close`` fires at the closing position W-1. Returns the W
    observations (positions 0..W-1)."""
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


def per_w(tb: SwitchFaiTb, table: dict):
    """Literal expectation for the window under test (64 / 256)."""
    assert tb.w in table, f"no literal expectation for W={tb.w}"
    return table[tb.w]


def per_nw(tb: SwitchFaiTb, table: dict):
    assert (tb.n, tb.w) in table, f"no literal expectation for N={tb.n}, W={tb.w}"
    return table[(tb.n, tb.w)]


def state(o) -> tuple:
    """(turn_q, used_q) during the cycle of ``o``: turn 0 = High, 1 = Low."""
    return (o.i_turn, o.i_used)


def spread(sources, count: int) -> list:
    """``count`` fires spread round-robin over ``sources``."""
    return [sources[k % len(sources)] for k in range(count)]


# Covers: SPEC §3 (ports/widths), §5 (synchronous reset: all sources H, High visit first, used
#         quota / B / S / window index / arrival counter / held grant cleared, handshakes inactive),
#         §6 (FAI stores a 32-bit arrival timestamp per entry, one shared counter and the shared
#         in-class selector), §8.5 / fai_main.md 1 (parameter-derived widths: index ceil(log2 W),
#         B/S ceil(log2(W+1)); 5-bit context {class, used}), D35 (one switch_top / FIFO / hold)
@cocotb.test()
async def test_01_ports_reset_structure_arrival_metadata(dut):
    tb = await new_tb(dut, "t01")
    n, w = tb.n, tb.w
    gen = Descs(1)
    names = [p for p, _k in hierarchy_paths(dut)]
    dut._log.info("hierarchy: %d objects", len(names))
    fifo_idx = {int(m.group(1)) for p in names for m in [re.search(r"gen_fifo\[(\d+)\]\.u_fifo$", p)] if m}
    assert fifo_idx == set(range(n)), f"expected {n} cxl_desc_fifo instances, found {sorted(fifo_idx)}"
    assert len([p for p in names if p.endswith(".u_out_hold")]) == 1, "exactly one cxl_out_hold"
    assert len([p for p in names if p.endswith(".desc_mem_q")]) == n, "full descriptor storage per source"
    assert len([p for p in names if p.endswith(".ts_mem_q")]) == n, "FAI stores an arrival timestamp per entry"
    assert len([p for p in names if p.endswith("gen_arrival_ts.arrival_cnt_q")]) == 1, "one shared counter"
    sel = [p for p in names if p.endswith(".u_fcfs_sel")]
    assert len(sel) == 1 and sel[0].endswith("gen_policy_fai_main.u_fai_sched.u_fcfs_sel"), f"selectors {sel}"
    assert len([p for p in names if p.endswith("gen_policy_fai_main.u_fai_sched")]) == 1
    assert not any(re.search(r"gen_policy_(fcfs|rr|fai_alg2|unknown)|gen_no_arrival_ts|gen_bad_", p) for p in names)
    regs = {p.rsplit(".", 1)[1] for p in names if p.endswith("_q")}
    allowed = {"count_q", "wr_ptr_q", "rd_ptr_q", "desc_mem_q", "ts_mem_q", "held_q", "held_source_q",
               "held_ctx_q", "arrival_cnt_q", "cls_q", "idx_q", "b_q", "s_q", "turn_q", "used_q"}  # fmt: skip
    assert regs == allowed, f"state in switch_top FAI: {sorted(regs)}"
    fai_regs = sorted(p.rsplit(".", 1)[1] for p in names if ".u_fai_sched." in p and p.endswith("_q"))
    assert fai_regs == ["b_q", "cls_q", "idx_q", "s_q", "turn_q", "used_q"], f"FAI policy registers {fai_regs}"
    assert not [p for p in names if ".u_fcfs_sel." in p and p.endswith("_q")], "selector must be stateless"
    mem0 = dut.gen_fifo[0].u_fifo.gen_ts.ts_mem_q
    assert len(mem0) == 16 and len(mem0[0]) == 32
    assert len(dut.u_out_hold.held_ctx_q) == 5, "FAI context {class, used} is 5 bits"
    fai = dut.gen_policy_fai_main.u_fai_sched
    idx_bits, bs_bits = per_w(tb, {64: (6, 7), 256: (8, 9), 5000000: (23, 23)})
    assert (len(fai.idx_q), len(fai.s_q), len(fai.b_q), len(fai.cls_q)) == (idx_bits, bs_bits, n * bs_bits, 2 * n)
    assert (len(fai.turn_q), len(fai.used_q)) == (1, 4)

    # Reset state, then counter and window index advance on every non-reset edge, idle or not.
    for k in range(5):
        o = await tb.cycle(out_ready=k & 1)
        assert o.i_counter == k and o.i_idx == k and o.out_valid == 0 and o.in_ready == tb.all_src
        assert o.i_cls == ["H"] * n and o.i_b == [0] * n and o.i_s == 0 and state(o) == (0, 0)
    await to_window_start(tb)  # window 1 closes idle: S=0 keeps every H
    x = n - 1
    # Window 2: x fires at positions 1 and 2 (High visit: (High,0) continue, (High,1) emptied ->
    # turn Low). Closing: B[x]=2, S=2: N*2 > 2 -> DOWN -> H -> B_H.
    obs = await window(tb, gen, [x, x])
    assert [c for _p, _s, c in fires(obs)] == [H(0), H(1)]
    # Window 3: x pushed at 0, fires at 1 (turn Low, no Low head -> new High visit (High,0)), the
    # replacement keeps the High class live -> (High,1); offered again at 2 and stalled.
    d = [gen() for _ in range(2)]
    o = await tb.cycle(push={x: d[0]})
    assert o.i_cls[x] == "B_H" and o.i_idx == 0 and state(o) == (1, 0)
    o = await tb.cycle(push={x: d[1]}, out_ready=1)
    assert (o.fire, o.out_source, ctx_of_bits(o.i_grant_ctx)) == (1, x, H(0))
    o = await tb.cycle(out_ready=0)
    assert (o.out_source, o.out_desc, o.i_held, ctx_of_bits(o.i_grant_ctx)) == (x, d[1], 0, H(1))
    # Reset with every request input asserted and ready=1: synchronous, the reset cycle still shows
    # the pre-edge state.
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and ctx_of_bits(o.i_held_ctx) == H(1) and o.i_count[x] == 1
    assert o.i_cls[x] == "B_H" and o.i_idx == 3 and o.i_b[x] == 1 and o.i_s == 1 and state(o) == (0, 1)
    assert o.i_counter == 2 * w + 3, "pre-edge counter: non-reset edges since the previous reset"
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.i_held, o.i_head_valid, o.in_ready, o.i_counter, o.i_idx, o.i_s) == (0, 0, 0, 0, 0, 0)
    assert o.i_cls == ["H"] * n and o.i_b == [0] * n and state(o) == (0, 0) and o.i_count == [0] * n
    # New epoch: counter 0 again, a push in the first cycle stores 0, nothing old resurfaces.
    o = await tb.cycle(push={1: d[0]}, out_ready=1)
    assert o.i_counter == 0 and o.out_valid == 0 and o.push == 0b10
    o = await tb.cycle(out_ready=1)
    assert (o.fire, o.out_source, o.out_desc, o.i_head_ts[1], ctx_of_bits(o.i_grant_ctx)) == (1, 1, d[0], 0, H(0))
    got = await tb.finish()
    assert got == []
    assert tb.dropped_by_reset == 1 and tb.cov.reset_during_hold == 1 and tb.cov.reset_non_h == 1


# Covers: SPEC §8.1 (window-local B/S from successful fires, exact thresholds), §8.2 (all sixteen
#         (state, evidence) transitions of the Main table through REAL windows: UP/DOWN/KEEP/S=0 from
#         H, B_H, L, B_L; two consecutive windows switch the effective class; neutral (KEEP),
#         opposing evidence and S=0 cancel a pending change), §8.4 (new class visible in the next
#         cycle, B/S/index cleared), Q3
@cocotb.test()
async def test_02_all_four_state_transitions(dut):
    tb = await new_tb(dut, "t02")
    n, w = tb.n, tb.w
    gen = Descs(2)
    x, p = n - 1, 0
    # Window kinds for source x (single outstanding descriptor, so the plan is exact):
    #   UP   : p fires once           -> x: B=0, S=1      -> UP  (0 < 3);       p: N > 1 -> DOWN
    #   DOWN : x fires once           -> x: B=1, S=1      -> DOWN (N > 1);      p: UP
    #   KEEP : x once + p N-1 times   -> x: B=1, S=N      -> KEEP (N = N, 10N >= 3N); p: N(N-1) > N -> DOWN
    #   S0   : no fire                -> S=0 for every source
    plans = {"UP": [p], "DOWN": [x], "KEEP": [x] + [p] * (n - 1), "S0": []}
    seq = ["UP", "KEEP", "S0", "DOWN", "UP", "DOWN", "KEEP", "DOWN", "S0", "DOWN", "DOWN",
           "DOWN", "KEEP", "S0", "UP", "KEEP", "UP", "DOWN", "UP", "S0", "UP", "UP"]  # fmt: skip
    # Hand-derived class of x and p after each window (spec 8.2 table). Others get UP or S0 only
    # and stay H.
    exp_x = ["H", "H", "H", "B_H", "H", "B_H", "H", "B_H", "H", "B_H", "L",
             "L", "L", "L", "B_L", "L", "B_L", "L", "B_L", "L", "B_L", "H"]  # fmt: skip
    exp_p = ["B_H", "L", "L", "B_L", "L", "B_L", "L", "B_L", "L", "B_L", "H",
             "H", "B_H", "H", "B_H", "L", "L", "B_L", "L", "L", "L", "L"]  # fmt: skip
    prev_x, prev_p = "H", "H"
    for k, kind in enumerate(seq):
        obs = await window(tb, gen, plans[kind])
        first, last = obs[0], obs[-1]
        assert (first.i_idx, first.i_b, first.i_s) == (0, [0] * n, 0), f"window {k}: B/S/index not cleared"
        assert (first.i_cls[x], first.i_cls[p]) == (prev_x, prev_p), f"window {k}: start classes"
        assert last.i_idx == w - 1 and last.i_cls[x] == prev_x, f"window {k}: class changed before the next cycle"
        s_exp = len(plans[kind])
        assert last.i_s == s_exp and last.i_b[x] == plans[kind].count(x), f"window {k}: closing counts"
        assert last.evidence[x] == kind, f"window {k}: evidence of x {last.evidence[x]}, expected {kind}"
        prev_x, prev_p = exp_x[k], exp_p[k]
        assert last.new_cls[x] == prev_x and last.new_cls[p] == prev_p
    o = await tb.cycle()
    assert o.i_cls[x] == "H" and o.i_cls[p] == "L" and all(c == "H" for c in o.i_cls[1:x])
    assert tb.cov.source_transitions(x) == {(s, e) for s in ("H", "B_H", "L", "B_L") for e in ("UP", "DOWN", "KEEP", "S0")}
    assert tb.cov.windows_closed == len(seq) and tb.cov.evidence["S0"] == 4 * n
    await tb.finish()


# Covers: SPEC §8.3/Q2 (10 successful fires per visit; quota expiry ends the visit even with a
#         same-edge replacement push and a still-nonempty class; windows never reset the visit:
#         a visit spanning a closing edge keeps its fires-already-charged), §8.4 step 1 (the
#         closing-edge fire is charged to its visit)
@cocotb.test()
async def test_03_quota_expiry_replacement_and_visit_across_closing(dut):
    tb = await new_tb(dut, "t03")
    n, w = tb.n, tb.w
    gen = Descs(3)
    x, z = 0, n - 1
    # Z becomes Low: two windows where only z fires once (N*1 > 1 -> DOWN twice: H -> B_H -> L).
    # Visits: window 1 z (High,0) emptied -> turn Low; window 2 z (B_H, High) with no Low head ->
    # (High,0) emptied -> turn Low. Window 3 starts with turn Low, used 0.
    await window(tb, gen, [z])
    await window(tb, gen, [z])
    steps = {}
    xs = [gen() for _ in range(11)]
    z1 = gen()
    steps[w - 6] = ({x: xs[0]}, 0)
    for j in range(10):  # fires at W-5 .. W+4, each with a replacement push into x
        steps[w - 5 + j] = ({x: xs[j + 1], **({z: z1} if j == 1 else {})}, 1)
    steps[w + 5] = (None, 1)
    steps[w + 6] = (None, 1)
    steps[w + 7] = (None, 1)
    obs = await script(tb, [steps.get(k, (None, 0)) for k in range(w + 8)])
    assert obs[0].i_cls[z] == "L" and state(obs[0]) == (1, 0)
    # Expected (hand-derived): at W-5 turn Low has no Low head -> new High visit (High,0); every
    # fire keeps x nonempty (replacement) -> continue; the closing edge (position W-1) fires the
    # 5th transfer (High,4) -> visit (High,5) survives the classification; positions 0..4 of the
    # next window charge (High,5)..(High,9); the 10th fire expires although x is still nonempty and
    # was refilled at that edge; z (Low, its head older than x's) is then served with (Low,0);
    # z empties -> turn High: x's last descriptor (High,0).
    got = fires(obs)
    exp = [((w - 5 + j) % w, x, H(j)) for j in range(10)] + [(5, z, L(0)), (6, x, H(0))]
    assert got == exp, f"fires {got}"
    closing = obs[w - 1]
    assert closing.i_closing == 1 and closing.fire and closing.visit_event == "continue"
    nxt = obs[w]
    assert nxt.i_idx == 0 and state(nxt) == (0, 5), "classification must not reset the visit / quota"
    # Closing counts: B[x]=5, S=5 -> x DOWN: H -> B_H (still High); z UP: L -> B_L (still Low).
    assert nxt.i_cls[x] == "B_H" and nxt.i_cls[z] == "B_L"
    exp_ev = obs[w + 4]
    assert exp_ev.visit_event == "expired" and (exp_ev.push >> x) & 1 and exp_ev.i_count[x] == 1
    assert tb.cov.visits_expired_replaced >= 1 and tb.cov.visits_expired_live >= 1
    assert tb.cov.class_over_age >= 1, "z's older Low head waited behind the High visit"
    await tb.finish()


# Covers: SPEC §8.1 (closing counts include the closing-edge fire), §8.4 steps 2-4 (B_close =
#         B + fire, S_close = S + fire; new class visible only in the following cycle; B, S and
#         the index cleared; idx 0 starts the next window)
@cocotb.test()
async def test_04_closing_edge_fire_inclusion(dut):
    tb = await new_tb(dut, "t04")
    n, w = tb.n, tb.w
    gen = Descs(4)
    x, p = n - 1, 0
    fill = list(range(1, n - 1))  # N-2 sources other than x and p
    # Case A: x's only fire of the window is AT the closing edge. Included: B=1, S=1 -> DOWN ->
    # H -> B_H. (Excluded it would be S=0 -> H.)
    obs = await window(tb, gen, [], close=x)
    last = obs[-1]
    assert last.fire and last.out_source == x and last.i_idx == w - 1
    assert (last.i_b[x], last.i_s, last.i_cls[x]) == (0, 0, "H"), "pre-edge counts exclude the closing fire"
    # Case B: x fires once inside the window, the N-2 fill sources once each, and p at the closing
    # edge. Included: B[x]=1, S=N -> KEEP: B_H -> H. (Excluded: S=N-1 -> DOWN: B_H -> L.)
    obs = await window(tb, gen, [x] + fill, close=p)
    first, last = obs[0], obs[-1]
    assert first.i_cls[x] == "B_H" and first.i_cls[p] == "H", "case A: x DOWN (closing fire counted)"
    assert (first.i_idx, first.i_b, first.i_s) == (0, [0] * n, 0)
    assert last.out_source == p and last.fire and (last.i_b[x], last.i_s) == (1, n - 1)
    assert last.i_cls[x] == "B_H", "the new class is not visible in the closing cycle"
    o = await tb.cycle()
    assert (o.i_idx, o.i_b, o.i_s) == (0, [0] * n, 0)
    # p: B=1, S=N -> KEEP (H); fill: B=1, S=N -> KEEP (H).
    assert o.i_cls == ["H"] * n, f"case B classes {o.i_cls}: x must be H (closing fire counted, KEEP)"
    assert tb.cov.closing_fire == 2
    await tb.finish()


# Covers: SPEC §8.1 threshold equality / just below / just above for the configured N (exact
#         integers): UP iff 10*N*B < 3*S (equality is KEEP), DOWN iff N*B > S (equality is KEEP);
#         UP is observed from L (L -> B_L vs KEEP L), DOWN from H (H -> B_H vs KEEP H)
@cocotb.test()
async def test_05_threshold_equality_boundaries(dut):
    tb = await new_tb(dut, "t05")
    n, w = tb.n, tb.w
    gen = Descs(5)
    x = 1
    others = [h for h in range(n) if h != x]
    # UP side: (B, S, class after the window from L). Equality 10*N*B == 3*S needs 3 | 10*N*B:
    # B=3, S=10N (N4: 40, N8: 80, N16: 160) or N4 B=12, S=160. At W=64 S <= 63, so N8 / N16 use the
    # nearest reachable pair around the threshold with B=1 (no exact equality exists for B=1:
    # 3S = 80 / 160 has no integer solution): N8 S=26 (78 < 80, KEEP) / 27 (81 > 80, UP),
    # N16 S=53 (159 < 160, KEEP) / 54 (162 > 160, UP). N4 at W64: B=3 around S=40.
    up_cases = per_nw(tb, {
        (4, 64): [(3, 39, "L"), (3, 40, "L"), (3, 41, "B_L")],
        (4, 256): [(12, 159, "L"), (12, 160, "L"), (12, 161, "B_L")],
        (8, 64): [(1, 26, "L"), (1, 27, "B_L")],
        (8, 256): [(3, 79, "L"), (3, 80, "L"), (3, 81, "B_L")],
        (16, 64): [(1, 53, "L"), (1, 54, "B_L")],
        (16, 256): [(3, 159, "L"), (3, 160, "L"), (3, 161, "B_L")],
    })  # fmt: skip
    # DOWN side from H: N*B vs S. (1, N-1) DOWN, (1, N) equality KEEP, (1, N+1) KEEP,
    # (2, 2N-1) DOWN, (2, 2N) equality KEEP.
    down_cases = {4: [(1, 3, "B_H"), (1, 4, "H"), (1, 5, "H"), (2, 7, "B_H"), (2, 8, "H")],
                  8: [(1, 7, "B_H"), (1, 8, "H"), (1, 9, "H"), (2, 15, "B_H"), (2, 16, "H")],
                  16: [(1, 15, "B_H"), (1, 16, "H"), (1, 17, "H"), (2, 31, "B_H"), (2, 32, "H")]}[n]  # fmt: skip
    for b, s, exp in up_cases:
        await reset(tb)
        await window(tb, gen, [x])  # DOWN: H -> B_H
        await window(tb, gen, [x])  # DOWN: B_H -> L
        obs = await window(tb, gen, [x] * b + spread(others, s - b))
        assert obs[0].i_cls[x] == "L"
        last = obs[-1]
        assert last.i_s + last.fire == s and last.b_close[x] == b and last.s_close == s
        o = await tb.cycle()
        assert o.i_cls[x] == exp, f"UP threshold N={n} B={b} S={s}: class {o.i_cls[x]}, expected {exp}"
    for b, s, exp in down_cases:
        await reset(tb)
        obs = await window(tb, gen, [x] * b + spread(others, s - b))
        assert obs[-1].s_close == s and obs[-1].b_close[x] == b
        o = await tb.cycle()
        assert o.i_cls[x] == exp, f"DOWN threshold N={n} B={b} S={s}: class {o.i_cls[x]}, expected {exp}"
    await tb.finish()


# Covers: SPEC §8.5 (at least 31-bit widened unsigned threshold intermediates, zero-extended operands:
#         10*N*B and 3*S exceed the parameter-derived B/S width (W64: 7 bits, W256: 9 bits); a
#         comparison truncated to that width would classify differently in every case below),
#         §8.1 exact comparisons
@cocotb.test()
async def test_06_widened_threshold_arithmetic(dut):
    tb = await new_tb(dut, "t06")
    n, w = tb.n, tb.w
    gen = Descs(6)
    x = n - 2
    others = [h for h in range(n) if h != x]
    bs_bits = per_w(tb, {64: 7, 256: 9})
    # (B, S, class from L). KEEP rows: 10*N*B > 2^bs - 1 so a bs-bit truncation of 10*N*B would
    # wrap below 3*S and give UP (B_L). UP rows: 3*S > 2^bs - 1 so a truncation of 3*S wraps to 1
    # and would give KEEP (L); N16/W64 has no such S <= 63 (3*S <= 189 never wraps below 160 mod 128),
    # so it exercises the UP side with 10*N*B = 160 > 127.
    cases = per_nw(tb, {
        (4, 64): [(4, 40, "L"), (3, 43, "B_L")],
        (4, 256): [(13, 60, "L"), (12, 171, "B_L")],
        (8, 64): [(2, 40, "L"), (1, 43, "B_L")],
        (8, 256): [(7, 60, "L"), (6, 171, "B_L")],
        (16, 64): [(1, 40, "L"), (1, 54, "B_L")],
        (16, 256): [(4, 100, "L"), (3, 171, "B_L")],
    })  # fmt: skip
    for b, s, exp in cases:
        assert 10 * n * b >= (1 << bs_bits) or 3 * s >= (1 << bs_bits), "case must exceed the B/S width"
        await reset(tb)
        await window(tb, gen, [x])
        await window(tb, gen, [x])
        obs = await window(tb, gen, [x] * b + spread(others, s - b))
        assert obs[0].i_cls[x] == "L" and obs[-1].s_close == s and obs[-1].b_close[x] == b
        o = await tb.cycle()
        assert o.i_cls[x] == exp, f"widened N={n} W={w} B={b} S={s}: class {o.i_cls[x]}, expected {exp}"
    await tb.finish()


# Covers: SPEC §8.1 (the window index advances on every non-reset cycle including downstream
#         stalls), §4 stall clarification (windows close and classifications change during a stall
#         without altering the held output), §8.2 S=0 cancellation, §8.3 (held grant fires with its
#         retained context after several windows)
@cocotb.test()
async def test_07_window_advances_during_long_stall(dut):
    tb = await new_tb(dut, "t07")
    n, w = tb.n, tb.w
    gen = Descs(7)
    x, y = 0, n - 1
    await window(tb, gen, [x])  # x: DOWN -> B_H; visit (High,0) emptied -> turn Low
    x1, x2, y1 = gen(), gen(), gen()
    stall = 3 * w + 5  # stall cycles: positions 1 .. 3W+5 (three closing edges inside)
    steps = [({x: x1}, 0)] + [(({x: x2} if k == 2 else {y: y1} if k == 3 else None), 0) for k in range(stall)]
    steps += [(None, 1)] * 3
    obs = await script(tb, steps)
    held = obs[2:stall + 1]
    for o in held:
        assert (o.out_valid, o.out_source, o.out_desc, o.i_held) == (1, x, x1, 1), f"cycle {o.cycle}: offer changed"
        assert ctx_of_bits(o.i_grant_ctx) == H(0) and o.i_b == [0] * n and o.i_s == 0
    # Offered at position 1: turn Low, no Low head -> (High,0). The window keeps counting: closings
    # at W-1, 2W-1, 3W-1 have S=0: x B_H -> H (S=0 cancels the pending decrease), then H stays.
    assert obs[w - 1].i_cls[x] == "B_H" and obs[w].i_cls[x] == "H" and obs[w].i_idx == 0
    assert [o.pos for o in obs if o.closing] == [w - 1] * 3
    f = obs[stall + 1]
    assert f.fire and f.i_held and f.pos == (1 + stall) % w == 6, f"held fire at position {f.pos}"
    got = fires(obs)
    # The held grant fires with (High,0); x2 (older than y1, both High) continues the visit.
    assert got == [(6, x, H(0)), (7, x, H(1)), (8, y, H(2))], f"fires {got}"
    assert obs[stall + 2].i_b[x] == 1 and obs[stall + 2].i_s == 1, "the held fire counts in the window it fires in"
    assert tb.cov.max_windows_in_hold >= 3 and tb.cov.held_across_closing >= 3 and tb.cov.push_into_held_src >= 1
    await tb.finish()


# Covers: SPEC §8.3 (a held descriptor cannot be preempted by a new class map; its fire is charged to
#         the retained {class, used} context; subsequent unlocked selections use the current
#         effective classes), §8.4 step 5, §4 (held context stable across the classification)
@cocotb.test()
async def test_08_held_grant_across_effective_class_change(dut):
    tb = await new_tb(dut, "t08")
    n, w = tb.n, tb.w
    gen = Descs(8)
    x, y = 1, 2
    await window(tb, gen, [x])  # x: H -> B_H (High); visit -> turn Low, used 0
    x1, x2, x3, y1 = gen(), gen(), gen(), gen()
    steps = {0: ({x: x1}, 0), 1: ({x: x2}, 1), 3: ({x: x3}, 0), 5: ({y: y1}, 0)}
    steps.update({w + 2: (None, 1), w + 3: (None, 1), w + 4: (None, 1), w + 5: (None, 1)})
    obs = await script(tb, [steps.get(k, (None, 0)) for k in range(w + 6)])
    # Position 1: x1 fires (turn Low, no Low head -> (High,0)); x2 replaces it -> (High,1).
    # Position 2: x2 offered with (High,1), stalled through the closing edge. Closing: B[x]=1,
    # S=1 -> x DOWN: B_H -> L (effective Low); y: UP -> H.
    assert obs[w - 1].i_cls[x] == "B_H" and obs[w - 1].i_held and obs[w - 1].out_source == x
    nxt = obs[w]
    assert nxt.i_cls[x] == "L" and nxt.i_cls[y] == "H"
    assert (nxt.i_held, nxt.out_source, nxt.out_desc, ctx_of_bits(nxt.i_grant_ctx)) == (1, x, x2, H(1))
    assert (nxt.i_cand_valid, nxt.i_cand_source, ctx_of_bits(nxt.i_cand_ctx)) == (1, y, H(1)), (
        "the unlocked candidate already uses the new map (y High) while x's grant stays held"
    )
    got = fires(obs)
    # Position 2 of the next window: x2 fires with its retained (High,1) although x is now Low; the
    # High class stays live (y) -> (High,2). Next unlocked selection uses the new classes: y (High)
    # beats x3 (Low, older); y empties the High class -> turn Low: x3 with (Low,0).
    assert got == [(1, x, H(0)), (2, x, H(1)), (3, y, H(2)), (4, x, L(0))], f"fires {got}"
    assert obs[w + 3].i_b[x] == 1 and obs[w + 3].i_s == 1
    assert tb.cov.held_cls_change == 1 and tb.cov.held_fire_cls_differs == 1 and tb.cov.class_over_age >= 1
    await tb.finish()


# Covers: SPEC §8.3/Q2 (skip an empty class without an idle cycle; a sole nonempty class renews its
#         quota without a bubble; both classes empty retains the turn without consuming quota;
#         empty classes relinquish unused quota, no credit banking: the next visit gets exactly 10),
#         §5 (no control-only bubbles)
@cocotb.test()
async def test_09_class_switching_renewal_retention_no_banking(dut):
    tb = await new_tb(dut, "t09")
    n, w = tb.n, tb.w
    gen = Descs(9)
    a, z = 0, n - 1
    await window(tb, gen, [z])
    await window(tb, gen, [z])  # z: L; turn Low, used 0 (see test_03)
    pa = [gen() for _ in range(17)]
    pz = [gen() for _ in range(30)]
    ia, iz = iter(pa), iter(pz)
    steps = {0: ({a: next(ia)}, 0), 1: (None, 1), 2: (None, 1), 3: (None, 0), 4: (None, 1),
             5: ({a: next(ia), z: next(iz)}, 0), 6: (None, 1), 7: (None, 1)}  # fmt: skip
    for k in range(8, 20):
        steps[k] = ({z: next(iz)}, 1)
    steps[20] = (None, 1)
    for k in range(21, 38):
        push = {}
        if k <= 23 or 26 <= k <= 37:
            push[a] = next(ia)
        if k <= 36:
            push[z] = next(iz)
        steps[k] = (push, 1)
    for k in range(38, 54):
        steps[k] = (None, 1)
    obs = await script(tb, [steps[k] for k in range(54)])
    assert obs[0].i_cls[z] == "L" and obs[0].i_cls[a] == "H" and state(obs[0]) == (1, 0)
    assert obs[0].pos == 0 and obs[53].pos == 53, "the whole scenario lies inside one window"
    exp = [(1, a, H(0))]  # turn Low, Low empty -> High visit without an idle cycle; a empties
    exp += [(6, z, L(0)), (7, a, H(0))]  # idle 2..5 retained turn Low: z first, then a
    exp += [(9 + k, z, L(k)) for k in range(10)]  # sole Low class: 10 fires, expired with replacement
    exp += [(19, z, L(0)), (20, z, L(1))]  # High empty -> Low renewed with no bubble; z empties
    exp += [(22, a, H(0)), (23, a, H(1)), (24, a, H(2))]  # High visit emptied after 3 (7 unused)
    exp += [(25 + k, z, L(k)) for k in range(10)]  # Low visit expires at 10 (z still nonempty)
    exp += [(35 + k, a, H(k)) for k in range(10)]  # next High visit: exactly 10, no banked credit
    exp += [(45 + k, z, L(k)) for k in range(6)]  # z empties after 6
    exp += [(51, a, H(0)), (52, a, H(1))]
    got = fires(obs)
    assert got == exp, f"fires {got}"
    for k in (2, 3, 4, 5):
        assert obs[k].out_valid == 0 and state(obs[k]) == (1, 0), f"position {k}: both-empty retention"
    assert obs[8].out_valid == 0 and state(obs[8]) == (1, 0)
    work = [k for k in range(54) if obs[k].i_head_valid]
    assert all(obs[k].fire for k in work), "an eligible head with ready=1 must fire (no bubble)"
    assert obs[34].visit_event == "expired" and obs[44].visit_event == "expired" and obs[18].visit_event == "expired"
    assert obs[24].visit_event == "emptied" and obs[24].i_used == 2
    assert tb.cov.renew_same_class >= 1 and tb.cov.idle_turn_low >= 4 and tb.cov.class_switch_offers >= 3
    assert tb.cov.fires_per_visit[10] == 3
    await tb.finish()


# Covers: fai_main.md 4 "Derived convention" (at a closing edge class_live uses the class map in
#         force during the closing cycle; a visit continuing into a class the new map leaves
#         empty is relinquished by rule 3.2 in the next cycle without a bubble), SPEC §8.4 step 1
#         before step 3, Q2 (empty class relinquishes quota)
@cocotb.test()
async def test_10_closing_edge_class_live_derived_convention(dut):
    tb = await new_tb(dut, "t10")
    n, w = tb.n, tb.w
    gen = Descs(10)
    # Variant 1: x (B_H, High) fires at the closing edge with a second entry left. Old map: High
    # class live -> visit continues (High,1). New map: x DOWN -> L. Next cycle the High class is
    # empty: x is served at once with (Low,0), the (High,1) visit is relinquished.
    x = 1
    await window(tb, gen, [x])  # x: B_H; turn Low
    x1, x2 = gen(), gen()
    steps = {w - 3: ({x: x1}, 0), w - 2: ({x: x2}, 0), w - 1: (None, 1), w: (None, 1), w + 1: (None, 1)}
    obs = await script(tb, [steps.get(k, (None, 0)) for k in range(w + 2)])
    c = obs[w - 1]
    assert c.closing and c.fire and c.i_held and (c.out_source, ctx_of_bits(c.i_grant_ctx)) == (x, H(0))
    assert c.visit_event == "continue" and c.new_cls[x] == "L"
    nx = obs[w]
    assert state(nx) == (0, 1), "derived convention: the closing edge continued the High visit"
    assert nx.i_cls[x] == "L" and (nx.i_cand_valid, nx.i_cand_source, ctx_of_bits(nx.i_cand_ctx)) == (1, x, L(0))
    assert nx.fire and nx.out_desc == x2 and nx.relinquished == H(1), "no bubble, (High,1) relinquished"
    assert state(obs[w + 1]) == (0, 0)

    # Variant 2: old map says the High class empties (x was its only member), the new map would
    # make y High and nonempty. Derived: "emptied" -> turn Low -> z (Low) first, then y.
    await reset(tb)
    x, y, z = 0, 1, 2
    await window(tb, gen, [y, z])  # y, z: N*1 > 2 -> DOWN -> B_H
    await window(tb, gen, [y, z])  # y, z: B_H -> L
    obs3 = await window(tb, gen, [z])  # y: UP -> B_L; z: DOWN -> L
    assert (obs3[0].i_cls[y], obs3[0].i_cls[z]) == ("L", "L")
    xa, ya, za = gen(), gen(), gen()
    steps = {w - 2: ({x: xa}, 0), w - 1: ({y: ya, z: za}, 1), w: (None, 1), w + 1: (None, 1), w + 2: (None, 1)}
    obs = await script(tb, [steps.get(k, (None, 0)) for k in range(w + 3)])
    assert (obs[0].i_cls[x], obs[0].i_cls[y], obs[0].i_cls[z]) == ("H", "B_L", "L") and state(obs[0]) == (0, 0)
    c = obs[w - 1]
    assert c.closing and c.fire and (c.out_source, ctx_of_bits(c.i_grant_ctx)) == (x, H(0))
    assert c.visit_event == "emptied" and c.new_cls[:3] == ["B_H", "H", "B_L"]
    nx = obs[w]
    assert state(nx) == (1, 0) and nx.i_cls[:3] == ["B_H", "H", "B_L"]
    assert fires(obs[w:]) == [(0, z, L(0)), (1, y, H(0))], f"fires {fires(obs[w:])}"
    assert tb.cov.closing_live_differs == 2
    await tb.finish()


# Covers: SPEC §5 (synchronous reset mid-window, mid-visit and mid-hold: classes H, High visit with
#         no fires, B/S and index 0, held grant / occupancy / counter cleared, no fire/pop on a reset
#         edge, outputs inactive; reset edges are not window cycles: the first window after reset
#         closes at the W-th non-reset edge; a pulse between edges clears nothing), D25/D28
@cocotb.test()
async def test_11_reset_mid_window_mid_visit_mid_hold(dut):
    tb = await new_tb(dut, "t11", resp_delay=(4, 48))
    n, w = tb.n, tb.w
    gen = Descs(11)
    x, z = 1, n - 1
    await window(tb, gen, [z])
    await window(tb, gen, [z])  # z: L; turn Low
    z1, z2, x1 = gen(), gen(), gen()
    obs = await script(tb, [({z: z1}, 0), ({z: z2}, 1), ({x: x1}, 0), (None, 0), (None, 0)])
    assert fires(obs) == [(1, z, L(0))] and obs[2].out_source == z and ctx_of_bits(obs[2].i_grant_ctx) == L(1)
    junk = {h: uniq(h, 9) for h in range(n)}
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)  # position 5 of the window
    assert (o.out_valid, o.fire, o.in_ready, o.push, o.i_pop) == (0, 0, 0, 0, 0)
    assert o.i_held == 1 and ctx_of_bits(o.i_held_ctx) == L(1) and o.i_cls[z] == "L"
    assert (o.i_idx, o.i_b[z], o.i_s, state(o), o.i_count[z], o.i_count[x]) == (5, 1, 1, (1, 1), 1, 1)
    o = await tb.cycle(push=junk, out_ready=1, rst_n=0)
    assert (o.i_held, o.i_head_valid, o.i_idx, o.i_s, o.i_counter) == (0, 0, 0, 0, 0)
    assert o.i_cls == ["H"] * n and o.i_b == [0] * n and state(o) == (0, 0) and o.i_count == [0] * n
    # First window after the reset: x fires once; the W-th non-reset edge closes it (x DOWN).
    start = tb.cycle_no
    obs = await window(tb, gen, [x])
    assert obs[-1].cycle - start == w - 1 and obs[-1].closing and obs[-1].i_cls[x] == "H"
    o = await tb.cycle()
    assert o.cycle - start == w and o.i_cls[x] == "B_H" and o.i_idx == 0
    assert tb.cov.reset_mid_window == 1 and tb.cov.reset_mid_visit == 1 and tb.cov.reset_non_h == 1

    # Reset on an unlocked valid+ready offer: no fire/pop on the reset edge.
    await load_seq(tb, [{2: gen()}], out_ready=0)
    o = await tb.cycle(out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.i_pop, o.i_held) == (0, 0, 0, 0) and o.i_count[2] == 1
    assert o.i_cand_valid == 1 and o.i_cand_source == 2, "an unlocked candidate existed on the reset edge"
    o = await tb.cycle()
    assert o.i_count == [0] * n and o.i_held == 0 and state(o) == (0, 0) and o.i_cls == ["H"] * n

    # A low pulse between edges clears nothing (synchronous reset).
    b = [gen(), gen()]
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
    assert tb.cov.reset_during_hold == 1 and tb.cov.resets == 2
    assert tb.resp.cross_epoch_completions > 0, "old-epoch responses must complete after the reset"


# Covers: SPEC §6/§8.3 (inside the chosen effective class: shared FCFS head selection, older head
#         beats a lower source ID, equal timestamps (same-cycle ties) go to the lower ID; the
#         visit class is chosen before age: an older head of the other class waits)
@cocotb.test()
async def test_12_fcfs_ties_and_age_within_class(dut):
    tb = await new_tb(dut, "t12")
    n, w = tb.n, tb.w
    gen = Descs(12)
    # High class (all H after reset, turn High): 2 is offered at position 1 and held while n-1,
    # then 0 and 1 (same cycle) arrive. After the held fire: n-1 (older) beats the lower IDs, then
    # the 0 / 1 tie goes to 0. One High visit: (High,0..3).
    d = [gen() for _ in range(4)]
    steps = [({2: d[0]}, 0), ({n - 1: d[1]}, 0), ({0: d[2], 1: d[3]}, 0)] + [(None, 1)] * 5
    obs = await script(tb, steps)
    got = [(s, c) for _p, s, c in fires(obs)]
    assert got == [(2, H(0)), (n - 1, H(1)), (0, H(2)), (1, H(3))], f"High order {got}"
    assert [o.out_desc for o in obs if o.fire] == [d[0], d[1], d[2], d[3]]
    # Low class: sources 1 and 3 become L (two windows where each fires once: N*1 > 2 -> DOWN);
    # the visit then rests at turn Low, used 0 (both windows end with an emptied High visit).
    await reset(tb)
    await window(tb, gen, [1, 3])
    await window(tb, gen, [1, 3])
    l = [gen() for _ in range(5)]
    h0, h2 = gen(), gen()
    steps = [({3: l[0]}, 0), ({1: l[1]}, 0), ({1: l[2], 3: l[3]}, 0), (None, 1), (None, 1), (None, 1),
             (None, 1), ({2: h2}, 0), ({3: l[4]}, 0), ({0: h0}, 0), (None, 1), (None, 1), (None, 1),
             (None, 1)]  # fmt: skip
    obs = await script(tb, steps)
    assert obs[0].i_cls[:4] == ["H", "L", "H", "L"] and state(obs[0]) == (1, 0)
    got = [(s, c) for _p, s, c in fires(obs)]
    # Positions 1-2: 3's l0 offered (Low,0) and held; 3: it fires; then 1's l1 (older than 3's l3),
    # then the tie l2 / l3 (same cycle) -> source 1 first; 3 empties the Low class -> turn High.
    # Position 8: 2's h2 offered (High,0) and held while 3 (Low, l4) and 0 (High, h0) arrive;
    # after the held fire the High visit continues with 0 although 3's head is older; then 3.
    assert got == [(3, L(0)), (1, L(1)), (1, L(2)), (3, L(3)), (2, H(0)), (0, H(1)), (3, L(0))], f"fires {got}"
    assert [o.out_desc for o in obs if o.fire][:4] == [l[0], l[1], l[2], l[3]]
    assert tb.cov.ties_in_class >= 2 and tb.cov.older_beats_lower_in_class >= 1 and tb.cov.class_over_age >= 1
    assert obs[-1].pos < w, "scenario inside one window"
    await tb.finish()


# Covers: SPEC §6 (TRUE timestamp wraparound under FAI: simulation-only deposit of the internal
#         counter gen_arrival_ts.arrival_cnt_q near 2^32 in the first cycle after reset (mirrored by
#         the oracle's deposit_counter, exactly as the accepted M3 wrap test); stored values straddle
#         the wrap and pre-wrap arrivals win inside the class over numerically smaller post-wrap
#         timestamps; counter returns to 0 on reset). LABEL: simulation-only state deposit.
@cocotb.test()
async def test_13_true_timestamp_wrap(dut):
    tb = await new_tb(dut, "t13")
    n = tb.n
    gen = Descs(13)
    hi = list(range(n // 2, n))
    lo = list(range(0, n // 2))
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
    for s in sorted({s for s, _d in pre}):
        assert o.i_head_ts[s] >= 0xFFFFFFFA, f"pre-wrap head of source {s}: {o.i_head_ts[s]:#x}"
    for s in sorted({s for s, _d in post}):
        assert o.i_head_ts[s] <= 5, f"post-wrap head of source {s}: {o.i_head_ts[s]:#x}"
    assert o.i_cls == ["H"] * n and tb.cov.counter_wraps == 1
    wd0 = tb.cov.wrap_discriminating
    got = await serve(tb, 12)
    assert got == pre + post, f"wrap order {[s for s, _ in got]}"
    assert tb.cov.wrap_discriminating - wd0 >= 5, "pre-wrap heads must have won against smaller post-wrap values"
    assert o.pos + 12 < tb.w, "the literal wrap part stays inside the first window (all High)"

    # Random traffic across a second wrap with windows closing, every cycle checked against the
    # oracle (absolute-time order) and the pin trackers.
    await reset(tb)
    rng = random.Random(f"{run_seed()}:t13:{n}:{tb.w}")
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
    assert tb.cov.wrap_discriminating - wd1 > 0, "no selection straddled the wrap in the random segment"
    await tb.drain()
    await tb.cycle(rst_n=0)
    o = await tb.cycle()
    assert o.i_counter == 0
    await tb.finish()


# Covers: SPEC §4 (a full FIFO refuses a push even when its head fires that edge; in_ready from
#         beginning-of-cycle occupancy; ready again next cycle; the refused replacement does not
#         count as post-edge occupancy)
@cocotb.test()
async def test_14_full_plus_pop_refusal(dut):
    tb = await new_tb(dut, "t14")
    n = tb.n
    gen = Descs(14)
    for s in range(n):
        content = [gen() for _ in range(16)]
        await load_seq(tb, [{s: d} for d in content])
        x = gen()
        o = await tb.cycle(push={s: x}, out_ready=0)  # full, no fire: refused
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0 and o.i_count[s] == 16
        o = await tb.cycle(push={s: x}, out_ready=1)  # full, head fires: still refused
        assert (o.fire, o.out_source, o.out_desc) == (1, s, content[0])
        assert (o.in_ready >> s) & 1 == 0 and o.push == 0, "full FIFO must refuse a push on its pop edge"
        assert o.visit_event == "continue", "15 entries remain: the class stays live"
        o = await tb.cycle(push={s: x}, out_ready=0)  # occupancy 15: ready again, accepted
        assert (o.in_ready >> s) & 1 == 1 and o.push == 1 << s and o.i_count[s] == 15
        o = await tb.cycle(out_ready=0)
        assert o.i_count[s] == 16
        got = await tb.drain()
        assert got == [(s, d) for d in content[1:]] + [(s, x)]
    assert tb.cov.full_refused == n and tb.cov.ready_after_full_fire == n
    await tb.finish()


# Covers: SPEC §4 (no empty-FIFO bypass: a push at c is eligible no earlier than c+1, also while
#         another source is served; FCFS inside the class keeps the older heads first)
@cocotb.test()
async def test_15_no_bypass_next_cycle_eligibility(dut):
    tb = await new_tb(dut, "t15")
    n = tb.n
    gen = Descs(15)
    for s in range(n):
        d = gen()
        o = await tb.cycle(push={s: d}, out_ready=1)
        assert (o.out_valid, o.fire, o.push, o.i_cand_valid) == (0, 0, 1 << s, 0), f"source {s}: offered in its push cycle"
        o = await tb.cycle(out_ready=1)
        assert (o.fire, o.out_source, o.out_desc) == (1, s, d) and o.fired.accept_cycle == o.cycle - 1
    other_src = n - 1
    v = [gen() for _ in range(3)]
    await reset(tb)
    await load_seq(tb, [{other_src: d} for d in v])
    w0 = gen()
    o = await tb.cycle(push={0: w0}, out_ready=1)  # source 0 empty at the beginning of this cycle
    assert (o.fire, o.out_source, o.out_desc) == (1, other_src, v[0])
    got = [(o.out_source, o.out_desc)] + await serve(tb, 3)
    assert got == [(other_src, v[0]), (other_src, v[1]), (other_src, v[2]), (0, w0)]
    assert tb.cov.min_wait == 1
    await tb.finish()


# Covers: SPEC §3 (all 105 descriptor bits transported intact, per source; source sideband)
@cocotb.test()
async def test_16_walking_ones_and_zeros_all_bits(dut):
    tb = await new_tb(dut, "t16", resp_delay=(1, 1))
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


# Covers: SPEC §4, §5, §6, §8.1-8.4, §9 (whole Main FAI contract under the policy-independent
#         intended trace used for FCFS/RR with the stress window: windows, evidence, classes,
#         visits/quota, stalls, directed long stalls, overload/full refusal, back-to-back, resets,
#         TB tagged responses)
@cocotb.test()
async def test_17_short_random_trace(dut):
    seed = run_seed()
    tb = await new_tb(dut, "t17", unique_tags=True)
    trace = make_trace(seed, tb.n, SHORT_RANDOM_CYCLES, "short")
    dut._log.info("short trace sha256=%s generated=%d resets=%d", trace.sha256, trace.generated, sum(trace.reset))
    metrics = await run_trace(dut, tb, trace)
    cov = tb.cov
    write_json("fai_short_random.json", {"schema": "cxl-m5-fai-short-random-v1", "policy": "FAI_MAIN",
                                         "policy_param": 2, "fai_w": tb.w, "seed": seed, "n_src": tb.n,
                                         "trace_sha256": trace.sha256,
                                         "fai_measurement": fai_summary(metrics["coverage_measurement"], tb.w),
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
    # Resets restart the window, so only half the nominal window count is required.
    assert cov.windows_closed >= (SHORT_RANDOM_CYCLES // tb.w) // 2, "windows must keep closing"
    assert cov.evidence["DOWN"] > 0 and cov.closing_fire > 0, "evidence bins"
    assert cov.visits_expired > 0 and cov.visits_emptied > 0 and cov.visits_continue > 0, "visit bins"
    # UP evidence, held-across-closing, class changes of held grants, Low-class service and the
    # four states depend on the seed under this policy-independent trace (designed for FCFS/RR):
    # e.g. UP needs a source below 0.3/N of a window's service, which at N4/W256 (~45 windows) the
    # saturation-heavy "short" profile does not guarantee (seed 510: UP=0, preserved as initial
    # failure 02 with diagnosis). They are mandatory deterministic bins of test_02 (all 16
    # transitions) / test_05 / test_06 / test_07 / test_08 / test_10, mandatory per run in
    # M5-stress (all 16 transitions), and recorded here in fai_measurement.
    assert tb.resp.issued == tb.total_delivered > 0 and tb.resp.completed == tb.resp.issued
    assert tb.resp.reordered > 0 and tb.resp.cross_epoch_completions > 0, "response reorder/epoch bins"
    assert metrics["generation_to_acceptance"]["max"] > 0, "backpressure must delay some acceptance"
    assert metrics["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0


# Covers: SPEC §4 (producer retains its valid descriptor until push: an offer refused by a full D16
#         FIFO in the last measured cycle stays valid with identical bits across measurement -> drain
#         until pushed; full-plus-pop refusal on the drain edge), §8.3 (drain order: all sources H,
#         FCFS inside the High class), §9/§10 (measurement snapshots frozen at the boundary,
#         drain-only accepts counted separately, every tag answered exactly once). FAI counterpart
#         of the FCFS C1 regression (reviews/phase-4-rtl/codex-fcfs-review.md).
@cocotb.test()
async def test_18_measurement_boundary_input_hold(dut):
    from traffic_trace import Trace, trace_sha256

    tb = await new_tb(dut, "t18", unique_tags=True)
    n = tb.n
    a, z, mid = 0, n - 1, 1  # two sources fill their FIFOs; one source has unoffered backlog
    cycles = 20
    serial = iter(range(1000))

    def tdesc() -> int:
        i = next(serial)
        return mk_desc(tag=0xC5000000 + i, addr=0x60000000 + i, opcode=i & 1, length=i & 0xFF, payload=0xFA170000 + i)

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
    # ... and kept valid with identical bits in the drain until pushed. All sources are H (no
    # window closed: 20 measured cycles < W) and a / z were filled in the same cycles, so inside
    # the High class the oldest heads alternate a, z (same-cycle tie -> lower ID first): a fires
    # at the first drain edge (full + pop: refused) and is pushed at the second; z fires at the
    # second (refused while full) and is pushed at the third. The 10-fire High visit quota renews
    # with (High,0) because the Low class is empty, so it does not change the order.
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
    assert tb.cov.visits_expired >= 3 and tb.cov.renew_same_class >= 3, "High quota renewed while Low is empty"
    assert not tb.in_hold.pending and tb.outstanding() == 0


# Covers: SPEC §4 (full-plus-pop: a full D16 FIFO refuses the push on the edge its head fires and is
#         ready again in the next cycle; the producer keeps the refused descriptor valid with
#         identical bits until it is pushed, across measurement -> drain), §9/§10 (measured vs
#         drain-only populations: the next-cycle follow-up of a full-plus-pop fire in the LAST
#         measured cycle is observed in the first drain cycle, outside the frozen measurement
#         snapshot). Directed reproducer of the M5-stress boundary relation (test_switch_fai_stress.py).
@cocotb.test()
async def test_19_full_fire_last_measured_cycle(dut):
    from test_switch_fai_stress import check_full_followups, observe_measurement_boundary
    from traffic_trace import Trace, trace_sha256

    tb = await new_tb(dut, "t19", unique_tags=True)
    n = tb.n
    s = n - 1  # the only source; it generates one descriptor every measured cycle
    cycles = 24  # < 64: no window closes inside the measurement at W64 / W256; no resets
    assert cycles < tb.w
    serial = iter(range(1000))

    def tdesc() -> int:
        i = next(serial)
        return mk_desc(tag=0xC6000000 + i, addr=0x61000000 + i, opcode=i & 1, length=(i * 5 + 1) & 0xFF, payload=0xFA190000 + i)

    # Cycles 0..15 push 16 descriptors (empty FIFO, ready=0 downstream: D16 full after cycle 15).
    # Cycles 16..22: the 17th descriptor is offered and refused (full, no fire), held by its producer.
    # Cycle 23 (last measured): ready=1, the held head fires from full with in_valid=1 (full + pop:
    # refused). The follow-up (ready again) is cycle 24 = the first drain cycle, which pushes it.
    tr = Trace(run_seed(), n, cycles, "primary")
    tr.gen = [[(s, tdesc())] for _ in range(cycles)]
    tr.ready = bytearray(cycles)
    tr.ready[cycles - 1] = 1
    tr.reset = bytearray(cycles)
    tr.phases = [(0, cycles, "directed-full-fire-boundary")]
    tr.sha256 = trace_sha256(tr)
    descs = [g[0][1] for g in tr.gen]
    held = descs[DEPTH_D16]  # 17th descriptor

    seen = []  # every TB cycle observation from trace cycle 0 through the end of finish()
    orig_cycle = tb.cycle

    async def spy(*args, **kw):
        o = await orig_cycle(*args, **kw)
        seen.append(o)
        return o

    tb.cycle = spy
    base = tb.cycle_no
    meas_end = base + cycles
    boundary = observe_measurement_boundary(tb)
    m = await run_trace(dut, tb, tr)
    tb.cycle = orig_cycle
    cm, ct = m["coverage_measurement"], m["coverage_total"]
    at = {o.cycle: o for o in seen}

    # No cycle escaped the per-cycle checks: start() runs 1 power-up reset cycle outside cycle()
    # plus 2 reset cycles through cycle() and then clears the coverage, so the trace starts at TB
    # cycle 2 and every later TB cycle is one observed cycle() with one _pin_checks pass.
    assert base == 2 and tb.in_hold.cycles == tb.cycle_no
    assert [o.cycle for o in seen] == list(range(base, tb.cycle_no)), "observed TB cycles not contiguous"
    assert ct["cycles"] == tb.cov.cycles == len(seen) == tb.cycle_no - base and cm["cycles"] == cycles
    assert m["phases"]["drain_cycles_total"] == tb.cycle_no - meas_end

    # Measurement: 16 pushes, the 17th held (valid, identical bits, refused) from cycle 16 on.
    for c in range(base, meas_end):
        o = at[c]
        k = c - base
        assert (o.in_valid >> s) & 1 and o.in_valid == 1 << s, f"cycle {c}: in_valid={o.in_valid:#x}"
        if k < DEPTH_D16:
            assert o.push == 1 << s and o.in_desc[s] == descs[k] and o.fire == 0
        else:
            assert o.in_desc[s] == held and not (o.in_ready >> s) & 1 and o.push == 0, f"cycle {c}: 17th not held/refused"
            assert o.i_count[s] == DEPTH_D16
    last = at[meas_end - 1]
    assert (last.fire, last.out_source, last.out_desc, last.i_held) == (1, s, descs[0], 1), "fire from full at the last measured cycle"
    assert [o.cycle for o in seen if o.fire and o.cycle < meas_end] == [meas_end - 1]

    # Frozen measurement snapshot: the refusal is counted, its follow-up is not (it is a drain cycle).
    assert (cm["full_refused"], cm["ready_after_full_fire"], cm["full_fire_then_reset"]) == (1, 0, 0), _fu(cm)
    assert m["fires_measurement"] == cm["fires"] == 1 and m["input_push_count"] == cm["pushes"] == DEPTH_D16
    assert cm["windows_closed"] == 0 and cm["resets"] == 0 and cm["reset_cycles"] == 0
    # FAILING BEFORE the repair: the original test_switch_fai_stress.py:121 relation on the measurement.
    original_121 = cm["ready_after_full_fire"] + cm["full_fire_then_reset"] == cm["full_refused"]
    assert not original_121, "original stress.py:121 relation must be False for a full fire in the last measured cycle"

    # FIXED AFTER: one follow-up owed to the drain, observed at the exact freeze instant.
    det = check_full_followups(cm, ct, boundary, m["drain_only"], meas_end=meas_end)
    assert (boundary["owed"], boundary["owed_src"], det["owed_followups"]) == (1, s, 1)
    assert boundary["prev"] == ["fire", s, s] and boundary["hold_obligations"] == [s]
    assert boundary["owed_src_held_desc"] == held
    f = boundary["first_drain"]
    assert f["cycle"] == meas_end and (f["in_ready"] >> s) & 1 and f["push"] == 1 << s and f["owed_src_desc"] == held
    first = at[meas_end]
    assert (first.push, first.in_desc[s], first.i_count[s], first.fire, first.out_desc) == (1 << s, held, DEPTH_D16 - 1, 1, descs[1])
    for o in seen:
        if o.cycle > meas_end:
            assert o.in_valid == 0, f"cycle {o.cycle}: unoffered backlog released in the drain"

    # Whole run: exactly one full-plus-pop refusal with exactly one follow-up; drain order and no bubble.
    assert (ct["full_refused"], ct["ready_after_full_fire"], ct["full_fire_then_reset"]) == (1, 1, 0), _fu(ct)
    fired = [(o.cycle, o.out_source, o.out_desc) for o in seen if o.fire]
    assert fired == [(meas_end - 1 + i, s, descs[i]) for i in range(DEPTH_D16 + 1)], "drain order / bubble"
    d = m["drain_only"]
    assert d["boundary_held_sources"] == [s] and d["boundary_held_offers"] == 1
    assert d["pushes"] == d["fires"] == 1 and d["per_source_pushes"][s] == d["per_source_fires"][s] == 1
    assert d["unoffered_backlog_at_boundary"] == d["generated_never_accepted"] == cycles - DEPTH_D16 - 1
    assert m["fires_drain"] == DEPTH_D16 - 1 and m["wait_acceptance_to_fire"]["outstanding_after_drain"] == 0
    h = m["input_hold"]
    assert h["obligation_checks_measurement"] == cycles - DEPTH_D16 - 1 > 0 and h["obligation_checks_drain"] == 1
    r = m["responses"]
    assert r["issued"] == r["completed"] == DEPTH_D16 + 1 and r["issued_for_drain_only_accepts"] == 1
    assert not tb.in_hold.pending and tb.outstanding() == 0 and not tb.resp.outstanding


def _fu(cov: dict) -> dict:
    return {k: cov[k] for k in ("full_refused", "ready_after_full_fire", "full_fire_then_reset")}
