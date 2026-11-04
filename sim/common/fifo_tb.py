"""Cycle-exact cocotb harness for cxl_desc_fifo (driver, monitor, scoreboard, coverage counters).

Cycle convention (specs/CXL_SPEC.md section 4): cycle c is the interval before its closing rising
edge. ``FifoTb.cycle`` drives the inputs shortly after the previous edge, samples every output in
the read-only phase at the falling edge (pre-edge values of the cycle), compares them with the
reference model's beginning-of-cycle view, then lets the rising edge happen and commits the same
edge in the model.

Two independent checks run on every cycle:

* model comparison: ready, head_valid, count, all descriptor bits and the head timestamp;
* conservation scoreboard built only from handshakes observed on the DUT pins: everything accepted
  in an epoch leaves exactly once and in order, nothing else ever appears at the head.
"""

from __future__ import annotations

import os
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

from cxl_model import EdgeResult, FifoModel  # noqa: E402

CLK_PERIOD_NS = 10
DRIVE_DELAY_NS = 1  # inputs change this long after the rising edge, never at an edge


def param_from_env(name: str) -> int:
    """Parameter value the runner built the design with (exported as CXL_PARAM_<NAME>)."""
    key = f"CXL_PARAM_{name}"
    if key not in os.environ:
        raise RuntimeError(f"{key} is not set: run through scripts/run_verify.sh")
    return int(os.environ[key], 0)


@dataclass
class Obs:
    """Pre-edge sample of one cycle plus what the closing edge did."""

    in_ready: int
    head_valid: int
    count: int
    head_desc: Optional[int]
    head_ts: int
    edge: Optional[EdgeResult] = None


@dataclass
class Coverage:
    cycles: int = 0
    reset_cycles: int = 0
    full_cycles: int = 0
    empty_cycles: int = 0
    pushes: int = 0
    pops: int = 0
    push_pop: int = 0  # push and pop on the same edge
    full_pop_valid: int = 0  # full, pop and in_valid together: push refused, head leaves
    full_valid_refused: int = 0  # in_valid refused because full
    pop_on_empty: int = 0  # pop request while empty
    push_empty_with_pop: int = 0  # push into empty with a pop request (no bypass)
    reset_nonempty: int = 0  # reset edge with occupancy > 0
    reset_full: int = 0
    occupancies: set = field(default_factory=set)


class FifoTb:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.depth = param_from_env("DEPTH")
        self.desc_w = param_from_env("DESC_W")
        self.ts_en = bool(param_from_env("TS_EN"))
        self.ts_w = param_from_env("TS_W")
        self.model = FifoModel(self.depth, self.ts_en, self.desc_w, self.ts_w)
        self.cov = Coverage()
        # Conservation scoreboard for the current epoch, from DUT-pin handshakes only.
        self.accepted: List[Tuple[int, int]] = []
        self.delivered: List[Tuple[int, int]] = []
        self.epochs_closed = 0
        self.dropped_by_reset = 0
        self.total_delivered = 0

    # ----- bring-up ------------------------------------------------------------------------------

    async def start(self, reset_cycles: int = 3) -> None:
        """Start the clock and apply the initial reset. Returns just after a rising edge."""
        dut = self.dut
        assert len(dut.i_in_desc) == self.desc_w == 105, "descriptor port must be 105 bits"
        assert len(dut.o_head_desc) == self.desc_w
        assert len(dut.i_in_ts) == len(dut.o_head_ts) == self.ts_w == 32
        assert len(dut.o_count) == (self.depth).bit_length() == 5
        assert self.depth == 16
        dut.rst_n.value = 0
        dut.i_in_valid.value = 0
        dut.i_in_desc.value = 0
        dut.i_in_ts.value = 0
        dut.i_pop.value = 0
        cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
        await RisingEdge(dut.clk)
        # Power-up state is undefined, so the first reset cycle is not compared with the model.
        for _ in range(reset_cycles):
            await Timer(DRIVE_DELAY_NS, unit="ns")
            await FallingEdge(dut.clk)
            await ReadOnly()
            assert int(dut.o_in_ready.value) == 0, "o_in_ready must be low while rst_n is low"
            await RisingEdge(dut.clk)
        self.model.commit(rst_n=False)
        self.accepted.clear()
        self.delivered.clear()

    # ----- one cycle -----------------------------------------------------------------------------

    def sample(self) -> Obs:
        """Read every output. Must be called in the read-only phase."""
        dut = self.dut
        head_valid = int(dut.o_head_valid.value)
        return Obs(
            in_ready=int(dut.o_in_ready.value),
            head_valid=head_valid,
            count=int(dut.o_count.value),
            head_desc=int(dut.o_head_desc.value) if head_valid else None,
            head_ts=int(dut.o_head_ts.value) if (head_valid or not self.ts_en) else 0,
        )

    def check_against_model(self, obs: Obs, rst_n: int, where: str = "") -> None:
        view = self.model.view(rst_n=bool(rst_n))
        ctx = f"cycle {self.cov.cycles}{' ' + where if where else ''} (epoch {self.model.epoch})"
        assert obs.in_ready == int(view.in_ready), f"{ctx}: o_in_ready={obs.in_ready}, model {view.in_ready}"
        assert obs.head_valid == int(view.head_valid), (
            f"{ctx}: o_head_valid={obs.head_valid}, model {view.head_valid}"
        )
        assert obs.count == view.count, f"{ctx}: o_count={obs.count}, model {view.count}"
        if view.head_valid:
            assert obs.head_desc == view.head_desc, (
                f"{ctx}: o_head_desc={obs.head_desc:#029x}, model {view.head_desc:#029x}, "
                f"diff bits {obs.head_desc ^ view.head_desc:#029x}"
            )
            if self.ts_en:
                assert obs.head_ts == view.head_ts, (
                    f"{ctx}: o_head_ts={obs.head_ts:#010x}, model {view.head_ts:#010x}"
                )
        if not self.ts_en:
            assert int(self.dut.o_head_ts.value) == 0, f"{ctx}: o_head_ts must be constant 0 when TS_EN=0"

    async def cycle(
        self,
        valid: int = 0,
        desc: int = 0,
        ts: int = 0,
        pop: int = 0,
        rst_n: int = 1,
    ) -> Obs:
        """Run one full cycle. Enter and leave just after a rising edge."""
        dut = self.dut
        await Timer(DRIVE_DELAY_NS, unit="ns")
        dut.rst_n.value = rst_n
        dut.i_in_valid.value = valid
        dut.i_in_desc.value = desc
        dut.i_in_ts.value = ts
        dut.i_pop.value = pop

        await FallingEdge(dut.clk)
        await ReadOnly()
        obs = self.sample()
        self.check_against_model(obs, rst_n)
        self._scoreboard(obs, valid, desc, ts, pop, rst_n)

        await RisingEdge(dut.clk)
        obs.edge = self.model.commit(
            rst_n=bool(rst_n),
            in_valid=bool(valid),
            in_desc=desc,
            in_ts=ts if self.ts_en else None,
            pop=bool(pop),
        )
        return obs

    # ----- scoreboard and coverage (DUT pins only) -----------------------------------------------

    def _scoreboard(self, obs: Obs, valid: int, desc: int, ts: int, pop: int, rst_n: int) -> None:
        cov = self.cov
        cov.cycles += 1
        cov.occupancies.add(obs.count)
        if not rst_n:
            cov.reset_cycles += 1
            cov.reset_nonempty += int(obs.count > 0)
            cov.reset_full += int(obs.count == self.depth)
            # The reset edge ends the epoch: whatever is still queued is discarded by reset.
            self._check_order()
            self.dropped_by_reset += len(self.accepted) - len(self.delivered)
            self.epochs_closed += 1
            self.accepted = []
            self.delivered = []
            return

        push = bool(valid and obs.in_ready)
        popped = bool(pop and obs.head_valid)
        full = obs.count == self.depth
        empty = obs.count == 0
        cov.full_cycles += int(full)
        cov.empty_cycles += int(empty)
        cov.pushes += int(push)
        cov.pops += int(popped)
        cov.push_pop += int(push and popped)
        cov.full_pop_valid += int(full and bool(pop) and bool(valid))
        cov.full_valid_refused += int(full and bool(valid))
        cov.pop_on_empty += int(empty and bool(pop))
        cov.push_empty_with_pop += int(empty and bool(pop) and push)

        stamp = ts if self.ts_en else 0
        if popped:
            self.delivered.append((obs.head_desc, obs.head_ts if self.ts_en else 0))
            self.total_delivered += 1
            idx = len(self.delivered) - 1
            assert idx < len(self.accepted), (
                f"cycle {cov.cycles}: descriptor {obs.head_desc:#x} left the FIFO but was never accepted"
            )
            assert self.delivered[idx] == self.accepted[idx], (
                f"cycle {cov.cycles}: out-of-order/corrupt delivery #{idx}: "
                f"got {self.delivered[idx]}, accepted {self.accepted[idx]}"
            )
        if push:
            self.accepted.append((desc, stamp))
        # Occupancy seen on the pins must equal accepted minus delivered before this edge.
        before = len(self.accepted) - int(push) - (len(self.delivered) - int(popped))
        assert obs.count == before, (
            f"cycle {cov.cycles}: o_count={obs.count} but pins show {before} outstanding"
        )

    def _check_order(self) -> None:
        n = len(self.delivered)
        assert n <= len(self.accepted), "more descriptors delivered than accepted"
        assert self.delivered == self.accepted[:n], "delivered sequence is not the accepted prefix"

    def outstanding(self) -> int:
        return len(self.accepted) - len(self.delivered)

    def assert_conserved_and_empty(self) -> None:
        """Every descriptor accepted in the current epoch has left exactly once, in order."""
        self._check_order()
        assert self.delivered == self.accepted, (
            f"{len(self.accepted) - len(self.delivered)} accepted descriptors never left the FIFO"
        )
        assert self.model.occupancy == 0

    # ----- convenience sequences -----------------------------------------------------------------

    async def push(self, desc: int, ts: int = 0, pop: int = 0) -> Obs:
        obs = await self.cycle(valid=1, desc=desc, ts=ts, pop=pop)
        return obs

    async def pop(self) -> Obs:
        return await self.cycle(pop=1)

    async def idle(self, n: int = 1) -> None:
        for _ in range(n):
            await self.cycle()

    async def fill(self, descs, ts_of=lambda i: i) -> None:
        """Push each descriptor; every one must be accepted."""
        for i, d in enumerate(descs):
            obs = await self.push(d, ts=ts_of(i))
            assert obs.in_ready == 1 and obs.edge.pushed is not None, f"push {i} was not accepted"

    async def drain(self, expect_descs, expect_ts=None) -> None:
        """Pop one per cycle and compare each head explicitly with the expected list."""
        for i, d in enumerate(expect_descs):
            obs = await self.pop()
            assert obs.head_valid == 1, f"drain {i}: head not valid"
            assert obs.head_desc == d, f"drain {i}: got {obs.head_desc:#x}, expected {d:#x}"
            if expect_ts is not None and self.ts_en:
                assert obs.head_ts == expect_ts[i], (
                    f"drain {i}: timestamp {obs.head_ts:#x}, expected {expect_ts[i]:#x}"
                )

    async def expect_empty(self) -> Obs:
        obs = await self.cycle()
        assert (obs.head_valid, obs.count, obs.in_ready) == (0, 0, 1), f"FIFO not empty: {obs}"
        return obs
