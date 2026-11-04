"""Cycle-exact cocotb tests of the standalone common output hold/stall controller (top =
cxl_out_hold, milestone M2). The FIFO heads are driven by the test.

Run through scripts/run_verify.sh M2 (it builds the design and exports CXL_PARAM_*).

Besides the block-level contract (spec sections 4, 5) this is the place where the selected-head
invariant is violated ON PURPOSE - something the integrated FIFOs can never do - to pin down the
documented behaviour: a held source whose head is invalid gives out_valid=0 and no pop, the grant
stays held (candidate still ignored) and is released only by its fire after the head is valid
again, or by reset.

Every cycle is compared with cxl_model.OutHoldModel and checked by the model-free pin rules of
sim/common/out_hold_tb.HoldTb; the directed tests add literal expectations.
"""

from __future__ import annotations

import random

from common_ctrl_tb import DESC_MASK, DESC_W, run_seed
from cxl_model import NO_CANDIDATE, Candidate
from hier_util import hierarchy_paths
from out_hold_tb import HoldTb

import cocotb
from cocotb.triggers import ReadOnly, Timer

RANDOM_CYCLES = 12000


def head(h: int, salt: int = 0) -> int:
    """A distinct, fully populated 105-bit pattern per (source, salt)."""
    x = (0x1F3D5B79A2C4E6081357 * (h + 1) + 0x0FEDCBA9876543210F1E2D3C4B * (salt + 1)) & DESC_MASK
    return x | (1 << (DESC_W - 1)) | 1


def heads(n: int, salt: int = 0):
    return [head(h, salt) for h in range(n)]


async def new_tb(dut) -> HoldTb:
    tb = HoldTb(dut)
    dut._log.info(
        "run seed=%d (cocotb per-test seed %d) N_SRC=%d CTX_W=%d DESC_W=%d",
        run_seed(), cocotb.RANDOM_SEED, tb.n, tb.ctx_w, tb.desc_w,
    )  # fmt: skip
    await tb.start()
    return tb


# Covers: SPEC §5 (reset clears held-grant validity; output valid inactive during reset)
@cocotb.test()
async def test_01_reset_and_structure(dut):
    tb = await new_tb(dut)
    n, ALL = tb.n, tb.all_src
    A = tb.ctx_mask
    hd = heads(n)

    o = await tb.cycle(head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.out_valid, o.held, o.fire, o.pop) == (0, 0, 0, 0), f"after reset release: {o}"

    # Hold, then reset with candidate, heads and sink all active.
    o = await tb.cycle(cand=tb.cand(1, A), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.out_valid, o.held) == (1, 0)
    o = await tb.cycle(cand=tb.cand(2, 0), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.out_valid, o.held, o.out_source, o.grant_ctx) == (1, 1, 1, A)
    o = await tb.cycle(cand=tb.cand(2, 0), head_valid=ALL, head_desc=hd, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.pop, o.held) == (0, 0, 0, 1), f"reset cycle: {o}"
    o = await tb.cycle(cand=tb.cand(2, 0), head_valid=ALL, head_desc=hd, out_ready=1, rst_n=0)
    assert (o.out_valid, o.fire, o.pop, o.held) == (0, 0, 0, 0), f"hold survived the reset edge: {o}"
    # After release the candidate of that cycle is served; the old grant (source 1) is gone.
    o = await tb.cycle(cand=tb.cand(2, 0), head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.out_valid, o.fire, o.held, o.out_source, o.grant_ctx, o.pop) == (1, 1, 0, 2, 0, 0b100)

    # Reset edge on an unlocked stalled offer: nothing is latched.
    o = await tb.cycle(cand=tb.cand(3, A), head_valid=ALL, head_desc=hd, out_ready=0, rst_n=0)
    assert o.out_valid == 0
    o = await tb.cycle(head_valid=ALL, head_desc=hd)
    assert (o.held, o.out_valid) == (0, 0)

    # Synchronous: a reset pulse between clock edges does not clear a held grant.
    await tb.cycle(cand=tb.cand(3, A), head_valid=ALL, head_desc=hd, out_ready=0)
    o = await tb.cycle(head_valid=ALL, head_desc=hd, out_ready=0)
    assert o.held == 1
    await Timer(1, unit="ns")
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    await ReadOnly()
    assert int(dut.o_out_valid.value) == 0 and int(dut.o_fire.value) == 0
    assert int(dut.o_grant_held.value) == 1
    await Timer(1, unit="ns")
    dut.rst_n.value = 1
    o = await tb.cycle(head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.held, o.fire, o.out_source, o.grant_ctx) == (1, 1, 3, A)

    # The block's only state is the held-grant record: no descriptor copy, no output register.
    names = [p for p, _kind in hierarchy_paths(dut)]
    regs = sorted(p.rsplit(".", 1)[1] for p in names if p.endswith("_q"))
    assert regs == ["held_ctx_q", "held_q", "held_source_q"], f"unexpected state: {regs} in {names}"
    assert len(dut.held_source_q) == tb.src_w and len(dut.held_ctx_q) == tb.ctx_w
    assert tb.cov.reset_during_hold == 1


# Covers: SPEC §4 (fire = out_valid && out_ready; pop only for the selected source), opaque ctx
@cocotb.test()
async def test_02_unlocked_candidate_decision_table(dut):
    tb = await new_tb(dut)
    n, mask = tb.n, tb.ctx_mask
    hd = heads(n, 1)
    ctx_vals = sorted({0, 1, mask, max(mask - 1, 0), mask >> 1, min((mask >> 1) + 1, mask)})

    # With the sink ready no grant is ever latched, so every row below is an unlocked decision.
    for s in range(n):
        only = 1 << s
        for ctx in ctx_vals:
            for cand_valid in (0, 1):
                for hv in (only, tb.all_src & ~only, tb.all_src, 0):
                    cand = tb.cand(s, ctx) if cand_valid else NO_CANDIDATE
                    o = await tb.cycle(cand=cand, raw_cand=(s, ctx), head_valid=hv, head_desc=hd, out_ready=1)
                    exp = int(cand_valid and bool(hv & only))
                    assert (o.out_valid, o.fire, o.held) == (exp, exp, 0), f"s={s} ctx={ctx} hv={hv:#x}: {o}"
                    assert o.pop == (only if exp else 0)
                    if exp:
                        assert (o.out_source, o.grant_ctx, o.out_desc) == (s, ctx, hd[s])
    assert tb.cov.holds == 0 and tb.cov.fire_sources == set(range(n)) and tb.cov.ctx_values == set(ctx_vals)

    # Candidate valid without a valid head and sink not ready: no offer, hence no hold.
    for s in range(n):
        o = await tb.cycle(cand=tb.cand(s, mask), head_valid=tb.all_src & ~(1 << s), head_desc=hd, out_ready=0)
        assert (o.out_valid, o.held, o.pop) == (0, 0, 0)
    o = await tb.cycle(head_valid=tb.all_src, head_desc=hd, out_ready=1)
    assert (o.out_valid, o.held) == (0, 0)
    assert tb.cov.holds == 0 and tb.cov.unheld_cand_head_invalid >= n


# Covers: SPEC §4 (stalled offer retained: source and context stable, candidate ignored)
@cocotb.test()
async def test_03_stall_latches_source_and_context(dut):
    tb = await new_tb(dut)
    n, ALL, mask = tb.n, tb.all_src, tb.ctx_mask
    rng = random.Random(f"{run_seed()}:hold_latch:{n}")
    hd = heads(n, 2)

    for s in range(n):
        ctx = (0x15 + 3 * s) & mask
        o = await tb.cycle(cand=tb.cand(s, ctx), head_valid=ALL, head_desc=hd, out_ready=0)
        assert (o.out_valid, o.held, o.out_source, o.grant_ctx, o.pop) == (1, 0, s, ctx, 0)
        for i in range(40):
            k = i % 4
            raw = None
            if k == 0:
                cand, raw = NO_CANDIDATE, (rng.randrange(n), rng.getrandbits(tb.ctx_w))
            elif k == 1:
                cand = tb.cand((s + 1 + i) % n, rng.getrandbits(tb.ctx_w))
            elif k == 2:
                cand = tb.cand(s, ctx ^ 1)  # same source, other context
            else:
                cand = tb.cand(rng.randrange(n), ~ctx)
            o = await tb.cycle(cand=cand, raw_cand=raw, head_valid=ALL, head_desc=hd, out_ready=0)
            assert (o.out_valid, o.held, o.fire, o.pop) == (1, 1, 0, 0), f"s={s} i={i}: {o}"
            assert (o.out_source, o.grant_ctx, o.out_desc) == (s, ctx, hd[s]), f"s={s} i={i}: grant changed"
        other = (s + 1) % n
        o = await tb.cycle(cand=tb.cand(other, ~ctx), head_valid=ALL, head_desc=hd, out_ready=1)
        assert (o.held, o.fire, o.pop, o.out_source, o.grant_ctx) == (1, 1, 1 << s, s, ctx), f"s={s}: {o}"
        # Released by the fire: the same candidate is now an unlocked offer of the other source.
        o = await tb.cycle(cand=tb.cand(other, ~ctx), head_valid=ALL, head_desc=hd, out_ready=1)
        assert (o.held, o.fire, o.pop, o.out_source, o.grant_ctx) == (0, 1, 1 << other, other, ~ctx & mask)
    assert tb.cov.holds == n and tb.cov.held_sources == set(range(n)) and tb.cov.max_hold_len == 41
    assert tb.cov.held_head_invalid == 0


# Covers: documented block behaviour when the selected-head invariant is violated by the
#         environment (cxl_out_hold.sv header): never silently dropped or re-selected.
@cocotb.test()
async def test_04_invariant_violation_keeps_grant_held(dut):
    tb = await new_tb(dut)
    n, ALL, mask = tb.n, tb.all_src, tb.ctx_mask
    hd = heads(n, 3)
    s, other = n - 1, 0
    ctx = mask
    gone = ALL & ~(1 << s)

    o = await tb.cycle(cand=tb.cand(s, ctx), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.out_valid, o.held) == (1, 0)
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.out_valid, o.held, o.out_source) == (1, 1, s)

    # The held source's head disappears. The candidate names a source with a valid head and the
    # sink is ready: nothing may be offered, fired or popped, and the grant must stay held.
    for i in range(30):
        ready = int(i % 3 != 0)
        cand = tb.cand(other, i) if i % 5 else NO_CANDIDATE
        o = await tb.cycle(cand=cand, head_valid=gone, head_desc=hd, out_ready=ready)
        assert (o.out_valid, o.fire, o.pop) == (0, 0, 0), f"i={i}: output active without a held head: {o}"
        assert o.held == 1, f"i={i}: grant dropped because its head looked invalid"
        assert (o.out_source, o.grant_ctx) == (s, ctx), f"i={i}: grant re-selected to the candidate"
    assert tb.cov.held_head_invalid == 30 and tb.cov.held_head_invalid_ready == 20

    # Head valid again but sink not ready: offered again, still the same grant.
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.out_valid, o.held, o.fire, o.out_source, o.grant_ctx, o.out_desc) == (1, 1, 0, s, ctx, hd[s])
    # Invalid once more, then the fire after revalidation releases the grant.
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=gone, head_desc=hd, out_ready=1)
    assert (o.out_valid, o.held, o.fire) == (0, 1, 0)
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.out_valid, o.held, o.fire, o.pop, o.out_source, o.grant_ctx) == (1, 1, 1, 1 << s, s, ctx)
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.held, o.fire, o.out_source, o.grant_ctx) == (0, 1, other, 0)
    assert tb.cov.fire_after_revalidation == 1

    # Violated invariant ended by reset instead of a fire.
    await tb.cycle(cand=tb.cand(s, ctx), head_valid=ALL, head_desc=hd, out_ready=0)
    for _ in range(4):
        o = await tb.cycle(cand=tb.cand(other, 0), head_valid=gone, head_desc=hd, out_ready=1)
        assert (o.held, o.out_valid, o.fire) == (1, 0, 0)
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=gone, head_desc=hd, out_ready=1, rst_n=0)
    assert (o.held, o.out_valid) == (1, 0)
    o = await tb.cycle(cand=tb.cand(other, 0), head_valid=gone, head_desc=hd, out_ready=1)
    assert (o.held, o.out_valid, o.fire, o.out_source) == (0, 1, 1, other)

    # All heads invalid while held.
    await tb.cycle(cand=tb.cand(1, 1), head_valid=ALL, head_desc=hd, out_ready=0)
    for _ in range(3):
        o = await tb.cycle(cand=tb.cand(2, 0), head_valid=0, head_desc=hd, out_ready=1)
        assert (o.held, o.out_valid, o.pop) == (1, 0, 0)
    o = await tb.cycle(cand=tb.cand(2, 0), head_valid=0b10, head_desc=hd, out_ready=1)
    assert (o.held, o.fire, o.out_source, o.grant_ctx) == (1, 1, 1, 1 & mask)


# Covers: SPEC §4-5 (held-grant validity is set by a stalled valid offer only and cleared by its
#         fire or by reset only)
@cocotb.test()
async def test_05_hold_set_and_release_conditions(dut):
    tb = await new_tb(dut)
    n, ALL, mask = tb.n, tb.all_src, tb.ctx_mask
    hd = heads(n, 4)

    # Not set by: no candidate / candidate without head / immediate fire.
    for cand, hv, ready in (
        (NO_CANDIDATE, ALL, 0),
        (tb.cand(0, mask), ALL & ~1, 0),
        (tb.cand(0, mask), ALL, 1),
    ):
        await tb.cycle(cand=cand, head_valid=hv, head_desc=hd, out_ready=ready)
        o = await tb.cycle(head_valid=ALL, head_desc=hd, out_ready=1)
        assert o.held == 0, f"hold created by cand={tuple(cand)} hv={hv:#x} ready={ready}"

    # Set by a single stalled cycle; then not released by any candidate/head activity of others.
    await tb.cycle(cand=tb.cand(2, 1), head_valid=ALL, head_desc=hd, out_ready=0)
    for i in range(20):
        cand = [NO_CANDIDATE, tb.cand(3, 0), tb.cand(2, 0), tb.cand(0, mask)][i % 4]
        hv = ALL if i % 2 else 0b100  # other heads come and go; the held head stays valid
        o = await tb.cycle(cand=cand, head_valid=hv, head_desc=hd, out_ready=0)
        assert (o.held, o.out_valid, o.out_source, o.grant_ctx) == (1, 1, 2, 1 & mask), f"i={i}: {o}"
    o = await tb.cycle(head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.held, o.fire, o.pop) == (1, 1, 0b100)
    o = await tb.cycle(head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.held, o.out_valid) == (0, 0)

    # A stall immediately after a fire of a held grant latches the NEW candidate, not the old one.
    await tb.cycle(cand=tb.cand(1, mask), head_valid=ALL, head_desc=hd, out_ready=0)
    o = await tb.cycle(cand=tb.cand(3, 0), head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.held, o.fire, o.out_source) == (1, 1, 1)
    o = await tb.cycle(cand=tb.cand(3, 0), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.held, o.out_valid, o.out_source, o.grant_ctx) == (0, 1, 3, 0)
    o = await tb.cycle(cand=tb.cand(0, mask), head_valid=ALL, head_desc=hd, out_ready=0)
    assert (o.held, o.out_valid, o.out_source, o.grant_ctx) == (1, 1, 3, 0)
    o = await tb.cycle(cand=tb.cand(0, mask), head_valid=ALL, head_desc=hd, out_ready=1)
    assert (o.held, o.fire, o.pop) == (1, 1, 0b1000)
    assert tb.cov.holds == 3 and tb.cov.fires_held == 3


# Covers: SPEC §3 (all 105 bits transported intact), §5 (no extra output stage: the offered
#         descriptor is the selected head of the same cycle, for the candidate and for a held grant)
@cocotb.test()
async def test_06_descriptor_mux_all_bits_all_sources(dut):
    tb = await new_tb(dut)
    n, ALL = tb.n, tb.all_src
    rng = random.Random(f"{run_seed()}:hold_mux:{n}")

    patterns = [0, DESC_MASK, int("5" * 27, 16) & DESC_MASK, int("A" * 27, 16) & DESC_MASK]
    patterns += [1 << b for b in range(DESC_W)] + [DESC_MASK ^ (1 << b) for b in (0, 31, 32, 39, 40, 41, 72, 73, 104)]
    for i, pat in enumerate(patterns):
        s = i % n
        # Selected slice carries the pattern, every other slice carries its complement.
        hd = [pat if h == s else pat ^ DESC_MASK for h in range(n)]
        o = await tb.cycle(cand=tb.cand(s, i), head_valid=ALL, head_desc=hd, out_ready=1)
        assert o.fire == 1 and o.out_desc == pat, f"pattern {pat:#x} via source {s}: got {o.out_desc:#x}"

    # Held grant: the descriptor is still read from the held source's head in the same cycle
    # (no copy, no stage) - the other slices change every cycle and never leak through.
    for s in range(n):
        keep = rng.getrandbits(DESC_W)
        hd = [keep if h == s else rng.getrandbits(DESC_W) for h in range(n)]
        o = await tb.cycle(cand=tb.cand(s, s), head_valid=ALL, head_desc=hd, out_ready=0)
        assert o.out_desc == keep
        for _ in range(8):
            hd = [keep if h == s else rng.getrandbits(DESC_W) for h in range(n)]
            o = await tb.cycle(cand=tb.cand((s + 1) % n, 0), head_valid=ALL, head_desc=hd, out_ready=0)
            assert (o.held, o.out_valid, o.out_source, o.out_desc) == (1, 1, s, keep)
        o = await tb.cycle(cand=tb.cand((s + 1) % n, 0), head_valid=ALL, head_desc=hd, out_ready=1)
        assert (o.held, o.fire, o.out_desc) == (1, 1, keep)


# Covers: SPEC §4-5 block contract under random candidates, heads (invariant violated at random),
#         sink readiness and resets
@cocotb.test()
async def test_07_random_vs_model(dut):
    tb = await new_tb(dut)
    n = tb.n
    rng = random.Random(f"{run_seed()}:hold_random:{n}:{tb.ctx_w}")
    phase_left = reset_left = 0
    resets = 0
    p_head = p_ready = p_cand = 1.0
    sticky = False
    hv = 0

    for _ in range(RANDOM_CYCLES):
        if phase_left == 0:
            p_head = rng.choice([1.0, 0.95, 0.6, 0.2])
            p_ready = rng.choice([1.0, 0.7, 0.3, 0.05])
            p_cand = rng.choice([1.0, 0.8, 0.4])
            sticky = rng.random() < 0.5  # heads change slowly (FIFO-like) or every cycle
            phase_left = rng.randint(100, 400)
        phase_left -= 1
        if reset_left == 0 and rng.random() < 1 / 400:
            reset_left = rng.randint(1, 3)
            resets += 1
        rst_n = 0 if reset_left else 1
        reset_left = max(0, reset_left - 1)

        if sticky:
            for h in range(n):
                if rng.random() < 0.1:
                    hv = (hv & ~(1 << h)) | (int(rng.random() < p_head) << h)
        else:
            hv = sum(int(rng.random() < p_head) << h for h in range(n))
        hd = [rng.getrandbits(DESC_W) for _ in range(n)]
        src, ctx = rng.randrange(n), rng.getrandbits(tb.ctx_w)
        cand = Candidate(True, src, ctx) if rng.random() < p_cand else NO_CANDIDATE
        ready = int(rng.random() < p_ready)
        await tb.cycle(cand=cand, raw_cand=(src, ctx), head_valid=hv, head_desc=hd, out_ready=ready, rst_n=rst_n)

    cov = tb.cov
    dut._log.info("random: resets=%d %s", resets, cov)
    assert cov.cycles >= RANDOM_CYCLES and cov.fires > 500 and cov.holds > 100 and cov.fires_held > 50
    assert cov.held_head_invalid > 0 and cov.held_head_invalid_ready > 0 and cov.fire_after_revalidation > 0
    assert cov.hold_cand_valid_other > 0 and cov.hold_cand_invalid > 0 and cov.unheld_cand_head_invalid > 0
    assert cov.reset_cycles >= 5 and cov.reset_during_hold > 0
    assert cov.fire_sources == set(range(n)) and cov.held_sources == set(range(n))
    assert len(cov.ctx_values) >= 2
