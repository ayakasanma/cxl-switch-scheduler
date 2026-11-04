"""Cycle-exact cocotb harness for the M2 common-framework fixture (cxl_common_ctrl_fixture):
N real cxl_desc_fifo + one real cxl_out_hold, candidate injected by the test.

Cycle convention (specs/CXL_SPEC.md section 4): cycle c is the interval before its closing rising
edge. ``CtrlTb.cycle`` drives every input shortly after the previous edge (so the candidate is a
beginning-of-cycle value and is fixed before anything about this cycle's handshake is known),
samples every output in the read-only phase at the falling edge, checks, lets the rising edge
happen and commits the same edge in the reference model.

Three independent layers run on EVERY cycle of EVERY test:

1. model comparison: all pins against ``cxl_model.CommonCtrlModel`` (in_ready, head_valid, counts,
   head descriptors/timestamps, held, out_valid, fire, pop, push, and out_desc/out_source/ctx
   whenever the output is valid);
2. pin-level contract checks that do not use the model: handshake identities, one-hot pop for the
   offered source only, hold provenance (held exactly after a stall, released exactly by fire or
   reset), stall stability of all 105 bits/source/context, the selected-head-valid invariant;
3. pin-level conservation scoreboard: per-source order, exactly-once delivery, full 105-bit
   integrity, occupancy == accepted - delivered, and no same-edge bypass.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer

import cocotb

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "refc") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "refc"))

from cxl_model import NO_CANDIDATE, Candidate, CommonCtrlModel, CtrlEdge  # noqa: E402

CLK_PERIOD_NS = 10
DRIVE_DELAY_NS = 1  # inputs change this long after the rising edge, never at an edge

DESC_W = 105
TS_W = 32
CNT_W = 5
DEPTH = 16
DESC_MASK = (1 << DESC_W) - 1


def param_from_env(name: str) -> int:
    """Parameter value the runner built the design with (exported as CXL_PARAM_<NAME>)."""
    key = f"CXL_PARAM_{name}"
    if key not in os.environ:
        raise RuntimeError(f"{key} is not set: run through scripts/run_verify.sh")
    return int(os.environ[key], 0)


def run_seed() -> int:
    """Seed given by the runner (COCOTB_RANDOM_SEED). cocotb 2.x derives a different per-test
    value for cocotb.RANDOM_SEED from it; local stimulus RNGs are seeded from the runner's value."""
    if "COCOTB_RANDOM_SEED" not in os.environ:
        raise RuntimeError("COCOTB_RANDOM_SEED is not set: run through scripts/run_verify.sh")
    return int(os.environ["COCOTB_RANDOM_SEED"])


@dataclass
class Obs:
    """Inputs applied during one cycle, the pre-edge sample of every output, and the edge result."""

    cycle: int
    rst_n: int
    cand: Candidate
    out_ready: int
    in_valid: int  # mask
    in_desc: List[int]
    in_ts: int
    in_ready: int  # mask
    push: int  # mask
    head_valid: int  # mask
    count: List[int]
    head_desc: List[int]
    head_ts: List[int]
    out_valid: int
    out_desc: int
    out_source: int
    grant_ctx: int
    held: int
    fire: int
    pop: int  # mask
    edge: Optional[CtrlEdge] = None


@dataclass
class Coverage:
    cycles: int = 0
    reset_cycles: int = 0
    pushes: int = 0
    fires: int = 0
    fires_direct: int = 0  # fire of an unlocked candidate (no stall first)
    fires_held: int = 0  # fire of a held grant
    stall_cycles: int = 0
    holds: int = 0  # number of distinct held grants
    max_hold_len: int = 0
    hold_cand_invalid: int = 0  # held, candidate not valid
    hold_cand_other_nonempty: int = 0  # held, candidate names another source with a valid head
    hold_cand_empty: int = 0  # held, candidate names an empty source
    hold_cand_same_src_other_ctx: int = 0  # held, candidate = held source with another context
    hold_fire_cand_differs: int = 0  # held grant fires while the candidate names another source
    hold_push_any: int = 0  # push accepted on any source during a hold
    hold_push_held_src: int = 0  # push accepted into the held source during a hold
    hold_held_src_full: int = 0  # held source full during the hold
    hold_all_full: int = 0  # every FIFO full during a hold
    fire_full_push_refused: int = 0  # full FIFO, in_valid, head fires: push refused
    ready_after_full_fire: int = 0  # ... and in_ready is back the following cycle
    fire_with_push_same_src: int = 0  # simultaneous push+pop on one FIFO
    fire_last_entry: int = 0  # fire empties the source
    b2b_fires: int = 0  # fires on consecutive cycles
    b2b_switch: int = 0  # ... from different sources
    unheld_cand_empty: int = 0  # not held, candidate names an empty source (others nonempty)
    unheld_cand_invalid: int = 0  # not held, no candidate while some head is valid
    push_into_empty_with_cand: int = 0  # candidate names the empty source being pushed (no bypass)
    reset_during_hold: int = 0
    reset_nonempty: int = 0
    min_wait: Optional[int] = None  # smallest (fire cycle - push cycle) seen
    fire_sources: set = field(default_factory=set)
    held_sources: set = field(default_factory=set)
    ctx_values: set = field(default_factory=set)
    occupancies: set = field(default_factory=set)

    def summary(self) -> str:
        skip = {"fire_sources", "held_sources", "ctx_values", "occupancies"}
        parts = [f"{k}={v}" for k, v in self.__dict__.items() if k not in skip]
        parts.append(f"fire_sources={sorted(self.fire_sources)}")
        parts.append(f"held_sources={sorted(self.held_sources)}")
        parts.append(f"n_ctx_values={len(self.ctx_values)}")
        parts.append(f"occupancies={sorted(self.occupancies)}")
        return " ".join(parts)


class CtrlTb:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.n = param_from_env("N_SRC")
        self.ctx_w = param_from_env("CTX_W")
        self.ts_en = bool(param_from_env("TS_EN"))
        self.depth = param_from_env("DEPTH")
        self.desc_w = param_from_env("DESC_W")
        self.ts_w = param_from_env("TS_W")
        self.src_w = (self.n - 1).bit_length()
        self.all_src = (1 << self.n) - 1
        self.ctx_mask = (1 << self.ctx_w) - 1
        self.model = CommonCtrlModel(self.n, self.depth, self.ts_en, self.ctx_w, self.desc_w, self.ts_w)
        self.cov = Coverage()
        self.cycle_no = 0
        self.ts_counter = 0xFFFFF000  # free-running test-side arrival counter, wraps during long runs
        # Pin-level scoreboard of the current epoch: per source (desc, ts, accepting cycle).
        self.accepted: List[List[Tuple[int, int, int]]] = [[] for _ in range(self.n)]
        self.delivered_n: List[int] = [0] * self.n
        self.total_accepted = 0
        self.total_delivered = 0
        self.dropped_by_reset = 0
        self.epochs_closed = 0
        # Pin-level memory of the previous cycle: ("stall", desc, source, ctx, ts) / ("fire", src,
        # full_refused_src) / ("idle",) / ("reset",).
        self.prev: tuple = ("reset",)
        self.hold_len = 0

    # ----- bring-up ------------------------------------------------------------------------------

    def check_ports(self) -> None:
        dut, n = self.dut, self.n
        assert n in (4, 8, 16) and self.depth == DEPTH == 16
        assert self.desc_w == DESC_W == 105 and self.ts_w == TS_W == 32
        assert len(dut.i_in_valid) == len(dut.o_in_ready) == n
        assert len(dut.i_in_desc) == n * 105, "input descriptors must be N x 105 bits"
        assert len(dut.o_out_desc) == 105, "output descriptor must be 105 bits"
        assert len(dut.o_out_source) == len(dut.i_cand_source) == self.src_w
        assert len(dut.i_cand_ctx) == len(dut.o_grant_ctx) == self.ctx_w
        assert len(dut.o_pop) == len(dut.o_push) == len(dut.o_head_valid) == n
        assert len(dut.o_head_desc) == n * 105 and len(dut.o_head_ts) == n * 32
        assert len(dut.o_fifo_count) == n * CNT_W and len(dut.i_arrival_ts) == 32

    async def start(self, reset_cycles: int = 3) -> None:
        """Start the clock and apply the initial reset. Returns just after a rising edge."""
        dut = self.dut
        self.check_ports()
        dut.rst_n.value = 0
        dut.i_in_valid.value = 0
        dut.i_in_desc.value = 0
        dut.i_arrival_ts.value = 0
        dut.i_cand_valid.value = 0
        dut.i_cand_source.value = 0
        dut.i_cand_ctx.value = 0
        dut.i_out_ready.value = 0
        cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
        await RisingEdge(dut.clk)
        # Power-up state is undefined, so the first reset cycles are checked for the reset-level
        # rules only (handshakes and output valid inactive), with every request input asserted.
        for _ in range(reset_cycles):
            await Timer(DRIVE_DELAY_NS, unit="ns")
            dut.i_in_valid.value = self.all_src
            dut.i_cand_valid.value = 1
            dut.i_out_ready.value = 1
            await FallingEdge(dut.clk)
            await ReadOnly()
            assert int(dut.o_in_ready.value) == 0, "o_in_ready must be low while rst_n is low"
            assert int(dut.o_out_valid.value) == 0, "o_out_valid must be low while rst_n is low"
            assert int(dut.o_fire.value) == 0 and int(dut.o_pop.value) == 0
            assert int(dut.o_push.value) == 0
            await RisingEdge(dut.clk)
        self.model.commit(NO_CANDIDATE, rst_n=False)
        self.prev = ("reset",)

    # ----- one cycle -----------------------------------------------------------------------------

    async def cycle(
        self,
        push: Optional[Dict[int, int]] = None,
        cand: Candidate = NO_CANDIDATE,
        out_ready: int = 0,
        rst_n: int = 1,
        raw_cand: Optional[Tuple[int, int]] = None,
    ) -> Obs:
        """Run one full cycle. Enter and leave just after a rising edge.

        ``push`` maps source -> descriptor offered on that source's input (in_valid=1).
        ``raw_cand`` gives the (source, ctx) pin values to drive while ``cand.valid`` is 0.
        """
        dut, n = self.dut, self.n
        push = push or {}
        in_valid = 0
        in_desc_vec = 0
        in_desc = [0] * n
        for h, d in push.items():
            assert 0 <= h < n and 0 <= d <= DESC_MASK
            in_valid |= 1 << h
            in_desc[h] = d
            in_desc_vec |= d << (h * DESC_W)
        ts = self.ts_counter
        self.ts_counter = (self.ts_counter + 1) & 0xFFFFFFFF
        if cand.valid:
            pin_src, pin_ctx = cand.source, cand.ctx
        else:
            pin_src, pin_ctx = raw_cand if raw_cand is not None else (cand.source, cand.ctx)

        await Timer(DRIVE_DELAY_NS, unit="ns")
        dut.rst_n.value = rst_n
        dut.i_in_valid.value = in_valid
        dut.i_in_desc.value = in_desc_vec
        dut.i_arrival_ts.value = ts
        dut.i_cand_valid.value = int(cand.valid)
        dut.i_cand_source.value = pin_src
        dut.i_cand_ctx.value = pin_ctx
        dut.i_out_ready.value = out_ready

        await FallingEdge(dut.clk)
        await ReadOnly()
        obs = self._sample(rst_n, cand, out_ready, in_valid, in_desc, ts)
        self._check_against_model(obs)
        self._pin_checks(obs)

        await RisingEdge(dut.clk)
        obs.edge = self.model.commit(
            cand,
            bool(out_ready),
            [bool((in_valid >> h) & 1) for h in range(n)],
            in_desc,
            ts,
            rst_n=bool(rst_n),
        )
        self.cycle_no += 1
        return obs

    def _sample(self, rst_n, cand, out_ready, in_valid, in_desc, ts) -> Obs:
        dut, n = self.dut, self.n
        hd = int(dut.o_head_desc.value)
        ht = int(dut.o_head_ts.value)
        fc = int(dut.o_fifo_count.value)
        return Obs(
            cycle=self.cycle_no,
            rst_n=rst_n,
            cand=cand,
            out_ready=out_ready,
            in_valid=in_valid,
            in_desc=in_desc,
            in_ts=ts,
            in_ready=int(dut.o_in_ready.value),
            push=int(dut.o_push.value),
            head_valid=int(dut.o_head_valid.value),
            count=[(fc >> (h * CNT_W)) & ((1 << CNT_W) - 1) for h in range(n)],
            head_desc=[(hd >> (h * DESC_W)) & DESC_MASK for h in range(n)],
            head_ts=[(ht >> (h * TS_W)) & 0xFFFFFFFF for h in range(n)],
            out_valid=int(dut.o_out_valid.value),
            out_desc=int(dut.o_out_desc.value),
            out_source=int(dut.o_out_source.value),
            grant_ctx=int(dut.o_grant_ctx.value),
            held=int(dut.o_grant_held.value),
            fire=int(dut.o_fire.value),
            pop=int(dut.o_pop.value),
        )

    # ----- layer 1: reference model ----------------------------------------------------------------

    def _check_against_model(self, o: Obs) -> None:
        n = self.n
        v = self.model.view(o.cand, bool(o.out_ready), bool(o.rst_n))
        w = f"cycle {o.cycle} (epoch {self.model.epoch}, rst_n={o.rst_n}, cand={tuple(o.cand)}, ready={o.out_ready})"

        def mask(bits) -> int:
            return sum(1 << h for h in range(n) if bits[h])

        assert o.in_ready == mask(v.in_ready), f"{w}: o_in_ready={o.in_ready:#x}, model {mask(v.in_ready):#x}"
        assert o.head_valid == mask(v.head_valid), (
            f"{w}: head_valid={o.head_valid:#x}, model {mask(v.head_valid):#x}"
        )
        assert o.count == list(v.count), f"{w}: counts={o.count}, model {list(v.count)}"
        for h in range(n):
            if v.head_valid[h]:
                assert o.head_desc[h] == v.head_desc[h], (
                    f"{w}: head_desc[{h}]={o.head_desc[h]:#029x}, model {v.head_desc[h]:#029x}"
                )
                if self.ts_en:
                    assert o.head_ts[h] == v.head_ts[h], (
                        f"{w}: head_ts[{h}]={o.head_ts[h]:#010x}, model {v.head_ts[h]:#010x}"
                    )
            if not self.ts_en:
                assert o.head_ts[h] == 0, f"{w}: head_ts[{h}] must be constant 0 when TS_EN=0"
        exp_push = mask([bool((o.in_valid >> h) & 1) and v.in_ready[h] for h in range(n)])
        assert o.push == exp_push, f"{w}: push={o.push:#x}, model {exp_push:#x}"
        assert o.held == int(v.held), f"{w}: o_grant_held={o.held}, model {int(v.held)}"
        assert o.out_valid == int(v.out_valid), f"{w}: o_out_valid={o.out_valid}, model {int(v.out_valid)}"
        assert o.fire == int(v.fire), f"{w}: o_fire={o.fire}, model {int(v.fire)}"
        assert o.pop == mask(v.pop), f"{w}: o_pop={o.pop:#x}, model {mask(v.pop):#x}"
        if v.out_valid:
            assert o.out_source == v.out_source, f"{w}: o_out_source={o.out_source}, model {v.out_source}"
            assert o.grant_ctx == v.grant_ctx, f"{w}: o_grant_ctx={o.grant_ctx:#x}, model {v.grant_ctx:#x}"
            assert o.out_desc == v.out_desc, (
                f"{w}: o_out_desc={o.out_desc:#029x}, model {v.out_desc:#029x}, "
                f"diff bits {o.out_desc ^ v.out_desc:#029x}"
            )
        if v.held and o.rst_n:
            held = self.model.held
            assert o.out_source == held.source and o.grant_ctx == held.ctx, (
                f"{w}: held grant pins ({o.out_source},{o.grant_ctx:#x}), model {tuple(held)}"
            )

    # ----- layers 2 and 3: DUT pins only -----------------------------------------------------------

    def _pin_checks(self, o: Obs) -> None:
        n, cov = self.n, self.cov
        w = f"cycle {o.cycle} [pins]"
        cov.cycles += 1

        # Handshake identities (spec section 4), valid in every cycle including reset.
        assert o.fire == (o.out_valid & o.out_ready), f"{w}: fire != out_valid && out_ready"
        assert o.pop == ((1 << o.out_source) if o.fire else 0), (
            f"{w}: pop={o.pop:#x} must be one-hot for the offered source {o.out_source} iff fire={o.fire}"
        )
        assert o.push == (o.in_valid & o.in_ready), f"{w}: push != in_valid & in_ready"
        for h in range(n):
            exp_ready = int(bool(o.rst_n) and o.count[h] < self.depth)
            assert (o.in_ready >> h) & 1 == exp_ready, (
                f"{w}: in_ready[{h}]={(o.in_ready >> h) & 1} with occupancy {o.count[h]}, rst_n={o.rst_n}"
            )
            assert (o.head_valid >> h) & 1 == int(o.count[h] > 0), f"{w}: head_valid[{h}] vs count"
            assert o.count[h] <= self.depth
            before = len(self.accepted[h]) - self.delivered_n[h]
            assert o.count[h] == before, f"{w}: count[{h}]={o.count[h]} but pins show {before} outstanding"
            cov.occupancies.add(o.count[h])

        # Hold provenance: held exactly in the cycle(s) after a stalled offer, until fire/reset.
        prev = self.prev
        exp_held = int(prev[0] == "stall")
        assert o.held == exp_held, f"{w}: o_grant_held={o.held}, previous cycle was {prev[0]}"
        if o.held:
            _, p_desc, p_src, p_ctx, p_ts = prev
            # Selected-head-valid invariant and stall stability (also during a reset cycle the
            # state is still the pre-edge state: the head of the held source is untouched).
            assert (o.head_valid >> p_src) & 1, f"{w}: held source {p_src} has no valid head"
            assert o.head_desc[p_src] == p_desc, f"{w}: head of held source {p_src} changed during the hold"
            if o.rst_n:
                assert o.out_source == p_src, f"{w}: out_source {o.out_source} changed from held {p_src}"
                assert o.grant_ctx == p_ctx, f"{w}: grant ctx {o.grant_ctx:#x} changed from held {p_ctx:#x}"
                assert o.out_valid == 1, f"{w}: out_valid dropped while a grant is held"
                assert o.out_desc == p_desc, (
                    f"{w}: out_desc changed during the hold, diff bits {o.out_desc ^ p_desc:#029x}"
                )
                if self.ts_en:
                    assert o.head_ts[p_src] == p_ts, f"{w}: arrival timestamp of the held head changed"
        elif o.rst_n:
            exp_valid = int(o.cand.valid and (o.head_valid >> o.cand.source) & 1)
            assert o.out_valid == exp_valid, (
                f"{w}: out_valid={o.out_valid} with candidate {tuple(o.cand)} and head_valid={o.head_valid:#x}"
            )
            if o.out_valid:
                assert o.out_source == o.cand.source and o.grant_ctx == o.cand.ctx, (
                    f"{w}: unlocked offer ({o.out_source},{o.grant_ctx:#x}) is not the candidate {tuple(o.cand)}"
                )
        if o.out_valid:
            # No output stage: the offered descriptor is the selected FIFO head of this very cycle.
            assert o.out_desc == o.head_desc[o.out_source], f"{w}: out_desc is not the selected head"

        if not o.rst_n:
            assert o.out_valid == 0 and o.fire == 0 and o.pop == 0, f"{w}: output active during reset"
            assert o.in_ready == 0 and o.push == 0, f"{w}: input handshake active during reset"
            cov.reset_cycles += 1
            cov.reset_during_hold += o.held
            cov.reset_nonempty += int(o.head_valid != 0)
            self._close_epoch()
            self.prev = ("reset",)
            self.hold_len = 0
            return

        self._coverage(o, prev)

        # Conservation scoreboard.
        if o.fire:
            src = o.out_source
            idx = self.delivered_n[src]
            assert idx < len(self.accepted[src]), (
                f"{w}: source {src} delivered {o.out_desc:#x} but has no outstanding accepted descriptor"
            )
            a_desc, a_ts, a_cycle = self.accepted[src][idx]
            assert o.out_desc == a_desc, (
                f"{w}: delivery #{idx} of source {src} is {o.out_desc:#029x}, accepted {a_desc:#029x}, "
                f"diff bits {o.out_desc ^ a_desc:#029x} (lost/duplicated/reordered/corrupted)"
            )
            if self.ts_en:
                assert o.head_ts[src] == a_ts, f"{w}: timestamp of delivery #{idx} of source {src}"
            waited = o.cycle - a_cycle
            assert waited >= 1, f"{w}: descriptor fired {waited} cycles after its accepting edge (bypass)"
            cov.min_wait = waited if cov.min_wait is None else min(cov.min_wait, waited)
            self.delivered_n[src] += 1
            self.total_delivered += 1
        for h in range(n):
            if (o.push >> h) & 1:
                self.accepted[h].append((o.in_desc[h], o.in_ts if self.ts_en else 0, o.cycle))
                self.total_accepted += 1

        if o.fire:
            src = o.out_source
            refused = src if (o.count[src] == self.depth and (o.in_valid >> src) & 1) else None
            self.prev = ("fire", src, refused)
        elif o.out_valid:
            self.prev = ("stall", o.out_desc, o.out_source, o.grant_ctx, o.head_ts[o.out_source])
        else:
            self.prev = ("idle",)

    def _coverage(self, o: Obs, prev: tuple) -> None:
        cov, n = self.cov, self.n
        cov.pushes += bin(o.push).count("1")
        if o.held:
            src = o.out_source
            if self.hold_len == 0:
                cov.holds += 1
                cov.held_sources.add(src)
            self.hold_len += 1
            cov.max_hold_len = max(cov.max_hold_len, self.hold_len)
            c = o.cand
            cov.hold_cand_invalid += int(not c.valid)
            if c.valid:
                cand_head = (o.head_valid >> c.source) & 1
                cov.hold_cand_other_nonempty += int(c.source != src and cand_head)
                cov.hold_cand_empty += int(not cand_head)
                cov.hold_cand_same_src_other_ctx += int(c.source == src and c.ctx != o.grant_ctx)
                cov.hold_fire_cand_differs += int(o.fire and c.source != src)
            cov.hold_push_any += int(o.push != 0)
            cov.hold_push_held_src += (o.push >> src) & 1
            cov.hold_held_src_full += int(o.count[src] == self.depth)
            cov.hold_all_full += int(all(c_ == self.depth for c_ in o.count))
        else:
            c = o.cand
            if o.head_valid:
                cov.unheld_cand_invalid += int(not c.valid)
                cov.unheld_cand_empty += int(c.valid and not (o.head_valid >> c.source) & 1)
            if c.valid and not (o.head_valid >> c.source) & 1 and (o.push >> c.source) & 1:
                cov.push_into_empty_with_cand += 1
        if prev[0] == "fire" and prev[2] is not None:
            cov.ready_after_full_fire += (o.in_ready >> prev[2]) & 1
            assert (o.in_ready >> prev[2]) & 1, (
                f"cycle {o.cycle} [pins]: source {prev[2]} fired from full but is not ready the next cycle"
            )
        if o.out_valid and not o.out_ready:
            cov.stall_cycles += 1
        if o.fire:
            src = o.out_source
            cov.fires += 1
            cov.fires_held += o.held
            cov.fires_direct += 1 - o.held
            cov.fire_sources.add(src)
            cov.ctx_values.add(o.grant_ctx)
            cov.fire_full_push_refused += int(o.count[src] == self.depth and (o.in_valid >> src) & 1)
            cov.fire_with_push_same_src += (o.push >> src) & 1
            cov.fire_last_entry += int(o.count[src] == 1 and not (o.push >> src) & 1)
            if prev[0] == "fire":
                cov.b2b_fires += 1
                cov.b2b_switch += int(prev[1] != src)
            self.hold_len = 0

    def _close_epoch(self) -> None:
        """A reset edge ends the epoch: whatever is still queued is discarded by reset."""
        for h in range(self.n):
            assert self.delivered_n[h] <= len(self.accepted[h])
            self.dropped_by_reset += len(self.accepted[h]) - self.delivered_n[h]
        self.accepted = [[] for _ in range(self.n)]
        self.delivered_n = [0] * self.n
        self.epochs_closed += 1

    # ----- end-of-test accounting ------------------------------------------------------------------

    def outstanding(self, source: Optional[int] = None) -> int:
        if source is not None:
            return len(self.accepted[source]) - self.delivered_n[source]
        return sum(len(a) for a in self.accepted) - sum(self.delivered_n)

    def assert_conserved(self) -> None:
        """Pin-level totals: accepted == delivered + dropped by reset + still queued."""
        assert self.total_accepted == self.total_delivered + self.dropped_by_reset + self.outstanding()
        assert self.cov.pushes == self.total_accepted and self.cov.fires == self.total_delivered

    def assert_conserved_and_empty(self) -> None:
        self.assert_conserved()
        assert self.outstanding() == 0, f"{self.outstanding()} accepted descriptors never left"
        assert self.model.nonempty_sources() == [] and self.model.held is None

    # ----- convenience sequences -------------------------------------------------------------------

    def cand(self, source: int, ctx: int = 0) -> Candidate:
        return Candidate(True, source, ctx & self.ctx_mask)

    async def idle(self, n: int = 1) -> Obs:
        obs = None
        for _ in range(n):
            obs = await self.cycle()
        return obs

    async def load(self, contents: Dict[int, List[int]]) -> None:
        """Queue ``{source: [descs]}`` (one per source per cycle) with no candidate: no offer."""
        longest = max((len(v) for v in contents.values()), default=0)
        for i in range(longest):
            pushes = {h: v[i] for h, v in contents.items() if i < len(v)}
            obs = await self.cycle(push=pushes)
            for h in pushes:
                assert (obs.push >> h) & 1, f"load: push {i} into source {h} was not accepted"
            assert obs.out_valid == 0 and obs.fire == 0

    async def fire(self, source: int, ctx: int = 0, push: Optional[Dict[int, int]] = None) -> Obs:
        """One cycle with the candidate on ``source`` and the sink ready; it must fire."""
        obs = await self.cycle(push=push, cand=self.cand(source, ctx), out_ready=1)
        assert obs.fire == 1 and obs.out_valid == 1, f"expected a fire of source {source}: {obs}"
        return obs

    async def drain_all(self) -> List[Tuple[int, int]]:
        """Serve everything left (lowest nonempty source first). Returns [(source, desc)]."""
        got: List[Tuple[int, int]] = []
        guard = self.n * self.depth + 4
        while self.outstanding() and guard:
            guard -= 1
            held = self.model.held
            src = held.source if held is not None else min(self.model.nonempty_sources())
            obs = await self.cycle(cand=self.cand(src, 0), out_ready=1)
            assert obs.fire == 1
            got.append((obs.out_source, obs.out_desc))
        obs = await self.cycle(cand=self.cand(0, 0), out_ready=1)
        assert obs.out_valid == 0 and obs.head_valid == 0 and obs.held == 0
        assert obs.count == [0] * self.n and obs.in_ready == self.all_src
        self.assert_conserved_and_empty()
        return got
