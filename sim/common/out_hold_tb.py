"""Cycle-exact cocotb harness for the standalone cxl_out_hold block (top = cxl_out_hold).

Here the FIFO heads (i_head_valid / i_head_desc) are driven by the test, so the block-level
contract can be checked in isolation, including the documented behaviour when an environment
violates the selected-head invariant (a held source whose head is not valid).

Two layers on every cycle:

1. model comparison against ``cxl_model.OutHoldModel`` (held, out_valid, fire, pop, and the grant
   source/context whenever a grant is offered valid or held);
2. model-free pin checks: handshake identities, one-hot pop, hold provenance from the previous
   cycle's pins (set only by a stalled valid offer, released only by fire or reset), candidate
   ignored while held, out_desc == the head slice of the offered source in the same cycle.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer

import cocotb

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "refc") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "refc"))

from common_ctrl_tb import CLK_PERIOD_NS, DESC_MASK, DESC_W, DRIVE_DELAY_NS, param_from_env  # noqa: E402
from cxl_model import NO_CANDIDATE, Candidate, HoldEdge, OutHoldModel  # noqa: E402


@dataclass
class HoldObs:
    cycle: int
    rst_n: int
    cand: Candidate
    out_ready: int
    head_valid: int  # mask driven by the test
    head_desc: List[int]
    out_valid: int
    out_desc: int
    out_source: int
    grant_ctx: int
    held: int
    fire: int
    pop: int
    edge: Optional[HoldEdge] = None


@dataclass
class HoldCoverage:
    cycles: int = 0
    reset_cycles: int = 0
    fires: int = 0
    fires_held: int = 0
    stalls: int = 0
    holds: int = 0
    max_hold_len: int = 0
    held_head_invalid: int = 0  # invariant deliberately violated: held, head of held source low
    held_head_invalid_ready: int = 0  # ... while the sink is ready (must not fire)
    fire_after_revalidation: int = 0  # held grant fires after its head had been invalid
    hold_cand_valid_other: int = 0  # held, candidate valid on another source with a valid head
    hold_cand_invalid: int = 0
    unheld_cand_head_invalid: int = 0
    reset_during_hold: int = 0
    fire_sources: set = field(default_factory=set)
    held_sources: set = field(default_factory=set)
    ctx_values: set = field(default_factory=set)


class HoldTb:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.n = param_from_env("N_SRC")
        self.ctx_w = param_from_env("CTX_W")
        self.desc_w = param_from_env("DESC_W")
        self.src_w = (self.n - 1).bit_length()
        self.all_src = (1 << self.n) - 1
        self.ctx_mask = (1 << self.ctx_w) - 1
        self.model = OutHoldModel(self.n, self.ctx_w)
        self.cov = HoldCoverage()
        self.cycle_no = 0
        # Pin-level memory: the grant the pins say is held, and whether its head was seen invalid.
        self.pin_held: Optional[Tuple[int, int]] = None
        self.pin_held_was_invalid = False
        self.hold_len = 0

    def check_ports(self) -> None:
        dut, n = self.dut, self.n
        assert self.desc_w == DESC_W == 105
        assert len(dut.i_head_valid) == len(dut.o_pop) == n
        assert len(dut.i_head_desc) == n * 105 and len(dut.o_out_desc) == 105
        assert len(dut.i_cand_source) == len(dut.o_out_source) == self.src_w
        assert len(dut.i_cand_ctx) == len(dut.o_grant_ctx) == self.ctx_w

    async def start(self, reset_cycles: int = 3) -> None:
        dut = self.dut
        self.check_ports()
        dut.rst_n.value = 0
        dut.i_cand_valid.value = 0
        dut.i_cand_source.value = 0
        dut.i_cand_ctx.value = 0
        dut.i_head_valid.value = 0
        dut.i_head_desc.value = 0
        dut.i_out_ready.value = 0
        cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
        await RisingEdge(dut.clk)
        for _ in range(reset_cycles):
            await Timer(DRIVE_DELAY_NS, unit="ns")
            dut.i_cand_valid.value = 1
            dut.i_head_valid.value = self.all_src
            dut.i_out_ready.value = 1
            await FallingEdge(dut.clk)
            await ReadOnly()
            assert int(dut.o_out_valid.value) == 0, "o_out_valid must be low while rst_n is low"
            assert int(dut.o_fire.value) == 0 and int(dut.o_pop.value) == 0
            await RisingEdge(dut.clk)
        self.model.commit(NO_CANDIDATE, [False] * self.n, rst_n=False)
        self.pin_held = None

    def cand(self, source: int, ctx: int = 0) -> Candidate:
        return Candidate(True, source, ctx & self.ctx_mask)

    async def cycle(
        self,
        cand: Candidate = NO_CANDIDATE,
        head_valid: int = 0,
        head_desc: Optional[List[int]] = None,
        out_ready: int = 0,
        rst_n: int = 1,
        raw_cand: Optional[Tuple[int, int]] = None,
    ) -> HoldObs:
        """Run one full cycle. Enter and leave just after a rising edge."""
        dut, n = self.dut, self.n
        head_desc = [0] * n if head_desc is None else list(head_desc)
        assert len(head_desc) == n and all(0 <= d <= DESC_MASK for d in head_desc)
        vec = 0
        for h, d in enumerate(head_desc):
            vec |= d << (h * DESC_W)
        if cand.valid:
            pin_src, pin_ctx = cand.source, cand.ctx
        else:
            pin_src, pin_ctx = raw_cand if raw_cand is not None else (cand.source, cand.ctx)

        await Timer(DRIVE_DELAY_NS, unit="ns")
        dut.rst_n.value = rst_n
        dut.i_cand_valid.value = int(cand.valid)
        dut.i_cand_source.value = pin_src
        dut.i_cand_ctx.value = pin_ctx
        dut.i_head_valid.value = head_valid
        dut.i_head_desc.value = vec
        dut.i_out_ready.value = out_ready

        await FallingEdge(dut.clk)
        await ReadOnly()
        o = HoldObs(
            cycle=self.cycle_no,
            rst_n=rst_n,
            cand=cand,
            out_ready=out_ready,
            head_valid=head_valid,
            head_desc=head_desc,
            out_valid=int(dut.o_out_valid.value),
            out_desc=int(dut.o_out_desc.value),
            out_source=int(dut.o_out_source.value),
            grant_ctx=int(dut.o_grant_ctx.value),
            held=int(dut.o_grant_held.value),
            fire=int(dut.o_fire.value),
            pop=int(dut.o_pop.value),
        )
        self._check_against_model(o)
        self._pin_checks(o)

        await RisingEdge(dut.clk)
        hv = [bool((head_valid >> h) & 1) for h in range(n)]
        o.edge = self.model.commit(cand, hv, bool(out_ready), bool(rst_n))
        self.cycle_no += 1
        return o

    def _check_against_model(self, o: HoldObs) -> None:
        n = self.n
        hv = [bool((o.head_valid >> h) & 1) for h in range(n)]
        m = self.model.offer(o.cand, hv, bool(o.out_ready), bool(o.rst_n))
        w = (
            f"cycle {o.cycle} (rst_n={o.rst_n}, cand={tuple(o.cand)}, head_valid={o.head_valid:#x}, "
            f"ready={o.out_ready})"
        )
        assert o.held == int(m.held), f"{w}: o_grant_held={o.held}, model {int(m.held)}"
        assert o.out_valid == int(m.out_valid), f"{w}: o_out_valid={o.out_valid}, model {int(m.out_valid)}"
        assert o.fire == int(m.fire), f"{w}: o_fire={o.fire}, model {int(m.fire)}"
        exp_pop = (1 << m.grant.source) if m.fire else 0
        assert o.pop == exp_pop, f"{w}: o_pop={o.pop:#x}, model {exp_pop:#x}"
        if o.rst_n and (m.out_valid or m.held):
            assert (o.out_source, o.grant_ctx) == tuple(m.grant), (
                f"{w}: offered grant ({o.out_source},{o.grant_ctx:#x}), model {tuple(m.grant)}"
            )
        if m.out_valid:
            want = o.head_desc[m.grant.source]
            assert o.out_desc == want, f"{w}: o_out_desc diff bits {o.out_desc ^ want:#029x}"

    def _pin_checks(self, o: HoldObs) -> None:
        cov = self.cov
        w = f"cycle {o.cycle} [pins]"
        cov.cycles += 1
        assert o.fire == (o.out_valid & o.out_ready), f"{w}: fire != out_valid && out_ready"
        assert o.pop == ((1 << o.out_source) if o.fire else 0), f"{w}: pop not one-hot for the offered source"
        assert o.held == int(self.pin_held is not None), (
            f"{w}: o_grant_held={o.held} but the pin history says held grant = {self.pin_held}"
        )
        if not o.rst_n:
            assert (o.out_valid, o.fire, o.pop) == (0, 0, 0), f"{w}: output active during reset"
            cov.reset_cycles += 1
            cov.reset_during_hold += o.held
            self.pin_held = None
            self.pin_held_was_invalid = False
            self.hold_len = 0
            return

        if self.pin_held is not None:
            src, ctx = self.pin_held
            head = (o.head_valid >> src) & 1
            # Candidate ignored completely: the offer is the latched grant whatever i_cand_* is.
            assert (o.out_source, o.grant_ctx) == (src, ctx), f"{w}: held grant {self.pin_held} not replayed"
            assert o.out_valid == head, f"{w}: held grant: out_valid={o.out_valid}, head_valid[{src}]={head}"
            self.hold_len += 1
            cov.max_hold_len = max(cov.max_hold_len, self.hold_len)
            cov.held_head_invalid += 1 - head
            cov.held_head_invalid_ready += int(not head and o.out_ready)
            cov.hold_cand_invalid += int(not o.cand.valid)
            cov.hold_cand_valid_other += int(
                o.cand.valid and o.cand.source != src and (o.head_valid >> o.cand.source) & 1
            )
            if not head:
                self.pin_held_was_invalid = True
        else:
            exp = int(o.cand.valid and (o.head_valid >> o.cand.source) & 1)
            assert o.out_valid == exp, f"{w}: unlocked out_valid={o.out_valid}, expected {exp}"
            if o.out_valid:
                assert (o.out_source, o.grant_ctx) == (o.cand.source, o.cand.ctx), f"{w}: offer != candidate"
            cov.unheld_cand_head_invalid += int(o.cand.valid and not exp)
        if o.out_valid:
            # No register stage: the descriptor is the offered source's head slice of this cycle.
            assert o.out_desc == o.head_desc[o.out_source], f"{w}: out_desc is not the selected head slice"

        # Next-state of the pin-level held record: set only by a stall, cleared only by a fire.
        if o.fire:
            cov.fires += 1
            cov.fires_held += o.held
            cov.fire_sources.add(o.out_source)
            cov.ctx_values.add(o.grant_ctx)
            cov.fire_after_revalidation += int(self.pin_held is not None and self.pin_held_was_invalid)
            self.pin_held = None
            self.pin_held_was_invalid = False
            self.hold_len = 0
        elif o.out_valid:
            cov.stalls += 1
            if self.pin_held is None:
                self.pin_held = (o.out_source, o.grant_ctx)
                cov.holds += 1
                cov.held_sources.add(o.out_source)
