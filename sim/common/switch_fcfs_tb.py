"""Cycle-exact cocotb harness for switch_top with POLICY=0 (FCFS), milestone M3.

DUT pins (spec 3): clk, rst_n, i_in_valid[N], o_in_ready[N], i_in_desc[N*105], o_out_valid,
i_out_ready, o_out_desc[105], o_out_source[clog2 N]. Internal state is observed READ-ONLY through
VPI (the build uses --public-flat-rw): FIFO head/occupancy/timestamp vectors of the policy slot,
the hold controller, the FCFS selector candidate and the arrival counter. The only write to an
internal signal is the simulation-only deposit of switch_top.gen_arrival_ts.arrival_cnt_q for the
timestamp-wrap test (``cycle(deposit=...)``), mirrored in the model by ``deposit_counter``. No RTL
port or RTL change is involved.

Cycle convention (spec 4): cycle c is the interval before its closing rising edge. ``cycle()``
drives every input DRIVE_DELAY_NS after the previous edge, samples every output in the read-only
phase at the falling edge, runs the checks, lets the rising edge happen and commits the same edge
in the reference model.

Independent layers on EVERY cycle of EVERY test:

1. model comparison against ``cxl_model.FcfsSwitchModel`` (abstract absolute-time FCFS model):
   pins (o_in_ready, o_out_valid, and o_out_source/o_out_desc when valid) and internal state
   (FIFO counts, head valid/descriptor/stored timestamp, held flag, fire, pop, push, FCFS
   candidate, arrival counter value);
2. model-free pin rules: in_ready from beginning-of-cycle occupancy as seen on the pins
   (accepted - delivered), outputs/handshakes inactive in reset, work conservation (FCFS offers
   whenever an accepted descriptor is outstanding), stall stability of valid + all 105 bits +
   source, hold provenance, FCFS order from the pin history (oldest accepting cycle, lowest ID);
3. pin-level scoreboard: whole-descriptor/source integrity, accepted-request conservation, no loss
   or duplication, per-source order, fire wait >= 1 (no bypass);
4. TB-only tagged responses (``tag_response.TagResponder``): each fire issues one outstanding
   (epoch, tag); responses return after seeded random delays (reordered) and must match exactly one
   outstanding request exactly once. The responder never drives the DUT;
5. spec 4 input (producer) hold from the OBSERVED input pins (``input_hold.InputHoldChecker``):
   once in_valid[h]=1 is refused (in_ready[h]=0) in a non-reset cycle, the next cycle must keep
   in_valid[h]=1 and all 105 descriptor bits until push or a reset cycle. Unconditional (no switch),
   on every cycle including measurement -> drain entry, drain and drain completion. ``drain()``
   keeps exactly these already-offered descriptors driven until they are pushed and offers nothing
   new (C1 repair).
"""

from __future__ import annotations

import json
import os
import random
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Deque, Dict, List, NamedTuple, Optional, Tuple

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer

import cocotb

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "refc") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "refc"))

from cxl_model import FcfsSwitchModel  # noqa: E402
from input_hold import InputHoldChecker  # noqa: E402
from tag_response import TagResponder  # noqa: E402
from traffic_trace import Producers, Trace, make_trace, mean, nearest_rank_p99, tag_of  # noqa: E402
from primary_phase_metrics import PrimaryPhaseMetrics  # noqa: E402

CLK_PERIOD_NS = 10
DRIVE_DELAY_NS = 1

DESC_W = 105
TS_W = 32
TS_MASK = (1 << TS_W) - 1
CNT_W = 5
DEPTH = 16
DESC_MASK = (1 << DESC_W) - 1
TAG_LSB = 73


def param_from_env(name: str) -> int:
    key = f"CXL_PARAM_{name}"
    if key not in os.environ:
        raise RuntimeError(f"{key} is not set: run through scripts/run_verify.sh")
    return int(os.environ[key], 0)


def run_seed() -> int:
    if "COCOTB_RANDOM_SEED" not in os.environ:
        raise RuntimeError("COCOTB_RANDOM_SEED is not set: run through scripts/run_verify.sh")
    return int(os.environ["COCOTB_RANDOM_SEED"])


class SbEntry(NamedTuple):
    desc: int
    accept_cycle: int  # TB cycle whose closing edge accepted the descriptor
    meta: Optional[int]  # e.g. the trace generation cycle (None for directed pushes)


@dataclass
class Obs:
    cycle: int
    rst_n: int
    out_ready: int
    in_valid: int
    in_desc: List[int]
    in_ready: int
    out_valid: int
    out_desc: int
    out_source: int
    fire: int  # computed from the pins: out_valid & out_ready
    # internal (VPI, read-only)
    i_head_valid: int
    i_count: List[int]
    i_head_desc: List[int]
    i_head_ts: List[int]
    i_push: int
    i_pop: int
    i_fire: int
    i_held: int
    i_cand_valid: int
    i_cand_source: int
    i_counter: int
    push: int = 0  # pin-level in_valid & in_ready
    fired: Optional[SbEntry] = None
    edge: object = None


@dataclass
class Coverage:
    cycles: int = 0
    reset_cycles: int = 0
    resets: int = 0  # reset events (runs of reset cycles)
    pushes: int = 0
    fires: int = 0
    fires_held: int = 0
    stall_cycles: int = 0
    holds: int = 0
    max_hold_len: int = 0
    max_valid_ready_low_run: int = 0  # consecutive cycles out_valid=1, out_ready=0
    ties: int = 0  # unlocked offer while another nonempty head has the same accepting cycle
    older_beats_lower: int = 0  # unlocked offer of a source above the lowest nonempty source
    full_refused: int = 0  # full source, in_valid, its head fires: push refused
    ready_after_full_fire: int = 0
    full_fire_then_reset: int = 0  # full fire whose next cycle is a reset cycle (ready low by reset)
    fire_with_push_same_src: int = 0
    b2b_fires: int = 0
    b2b_switch: int = 0
    push_during_hold: int = 0
    push_into_held_src: int = 0
    hold_with_other_nonempty: int = 0
    reset_during_hold: int = 0
    reset_nonempty: int = 0
    full_cycles: int = 0  # cycles with at least one full FIFO
    all_full_cycles: int = 0
    counter_wraps: int = 0  # observed counter step 0xFFFFFFFF -> 0
    wrap_discriminating: int = 0  # unlocked offer whose head ts is numerically above another eligible head ts
    responses: int = 0
    min_wait: Optional[int] = None
    max_wait: Optional[int] = None
    fire_sources: set = field(default_factory=set)
    full_sources: set = field(default_factory=set)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if not isinstance(v, set)}
        d["fire_sources"] = sorted(self.fire_sources)
        d["full_sources"] = sorted(self.full_sources)
        return d

    def summary(self) -> str:
        return " ".join(f"{k}={v}" for k, v in self.as_dict().items())


class SwitchFcfsTb:
    def __init__(self, dut, label: str, resp_delay: Tuple[int, int] = (1, 48), unique_tags: bool = False) -> None:
        self.dut = dut
        self.n = param_from_env("N_SRC")
        self.policy = param_from_env("POLICY")
        self.depth = param_from_env("DEPTH")
        self.desc_w = param_from_env("DESC_W")
        self.ts_w = param_from_env("TS_W")
        if self.policy != 0:
            raise RuntimeError(f"this harness verifies POLICY=0 (FCFS), built with POLICY={self.policy}")
        self.src_w = (self.n - 1).bit_length()
        self.all_src = (1 << self.n) - 1
        self.model = FcfsSwitchModel(self.n, self.depth, self.desc_w, self.ts_w)
        self.cov = Coverage()
        self.cycle_no = 0
        self.epoch = 0  # pin-level TB epoch, +1 per reset edge
        self.sb: List[Deque[SbEntry]] = [deque() for _ in range(self.n)]
        self.total_accepted = 0
        self.total_delivered = 0
        self.dropped_by_reset = 0
        self.dropped_entries: List[Tuple[int, SbEntry]] = []
        self.resp = TagResponder(random.Random(f"{run_seed()}:resp:{label}:{self.n}"), resp_delay, unique_tags)
        self.prev: tuple = ("reset",)
        self.hold_len = 0
        self.valid_ready_low_run = 0
        self.prev_counter: Optional[int] = None
        self.in_reset_run = False
        self.on_fire: Optional[Callable[[int, SbEntry, int], None]] = None
        self.on_reset_drop: Optional[Callable[[int, SbEntry], None]] = None
        self.in_hold = InputHoldChecker(self.n)  # spec 4 producer hold, always active
        # internal handles (read-only except the counter deposit)
        self.h_cnt = dut.gen_arrival_ts.arrival_cnt_q
        self.h_head_valid = dut.head_valid
        self.h_head_desc = dut.head_desc
        self.h_head_ts = dut.head_ts
        self.h_count = dut.fifo_count
        self.h_push = dut.push
        self.h_pop = dut.pop
        self.h_fire = dut.fire
        self.h_held = dut.grant_held
        self.h_cand_valid = dut.cand_valid
        self.h_cand_source = dut.cand_source

    # ----- bring-up ------------------------------------------------------------------------------

    def check_ports(self) -> None:
        dut, n = self.dut, self.n
        assert n in (4, 8, 16), f"N_SRC={n}"
        assert self.depth == DEPTH and self.desc_w == DESC_W and self.ts_w == TS_W
        assert len(dut.i_in_valid) == n and len(dut.o_in_ready) == n
        assert len(dut.i_in_desc) == n * 105, "input descriptors must be N x 105 bits"
        assert len(dut.o_out_desc) == 105, "output descriptor must be 105 bits"
        assert len(dut.o_out_source) == self.src_w, "o_out_source must be ceil(log2 N) bits"
        assert len(dut.o_out_valid) == 1 and len(dut.i_out_ready) == 1
        assert len(dut.clk) == 1 and len(dut.rst_n) == 1
        assert len(self.h_cnt) == 32, "arrival counter must be 32 bits"
        assert len(self.h_head_ts) == n * 32 and len(self.h_head_desc) == n * 105
        assert len(self.h_count) == n * CNT_W

    async def start(self, reset_cycles: int = 3) -> None:
        """Start the clock and apply the initial reset. Returns just after a rising edge."""
        dut = self.dut
        self.check_ports()
        dut.rst_n.value = 0
        dut.i_in_valid.value = 0
        dut.i_in_desc.value = 0
        dut.i_out_ready.value = 0
        cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
        await RisingEdge(dut.clk)
        # Power-up state is unknown: the first reset cycle checks only the reset-level pin rules,
        # with every request input asserted.
        await Timer(DRIVE_DELAY_NS, unit="ns")
        dut.i_in_valid.value = self.all_src
        dut.i_out_ready.value = 1
        await FallingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.o_in_ready.value) == 0, "o_in_ready must be low while rst_n is low"
        assert int(dut.o_out_valid.value) == 0, "o_out_valid must be low while rst_n is low"
        await RisingEdge(dut.clk)
        self.model.commit(rst_n=False)
        self.prev = ("reset",)
        self.in_reset_run = True
        for _ in range(reset_cycles - 1):
            await self.cycle(push={h: (h + 1) * 0x1111 for h in range(self.n)}, out_ready=1, rst_n=0)
        self.cov = Coverage()  # bring-up reset does not count as a covered reset event
        self.in_reset_run = False

    # ----- one cycle -----------------------------------------------------------------------------

    async def cycle(
        self,
        push: Optional[Dict[int, int]] = None,
        out_ready: int = 0,
        rst_n: int = 1,
        meta: Optional[Dict[int, int]] = None,
        deposit: Optional[int] = None,
    ) -> Obs:
        """One full cycle. Enter and leave just after a rising edge. ``push`` maps source ->
        descriptor offered with in_valid=1. ``deposit`` writes the arrival counter (sim-only)."""
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

        await Timer(DRIVE_DELAY_NS, unit="ns")
        dut.rst_n.value = rst_n
        dut.i_in_valid.value = in_valid
        dut.i_in_desc.value = in_desc_vec
        dut.i_out_ready.value = out_ready
        if deposit is not None:
            assert rst_n, "deposit is meaningful only in a non-reset cycle"
            self.model.deposit_counter(deposit)  # raises unless right after a reset, all empty
            self.h_cnt.value = deposit

        await FallingEdge(dut.clk)
        await ReadOnly()
        o = self._sample(rst_n, out_ready, in_valid, in_desc)
        self._input_hold_check(o)
        self._check_against_model(o)
        self._pin_checks(o, meta or {})

        await RisingEdge(dut.clk)
        o.edge = self.model.commit(
            bool(out_ready), [bool((in_valid >> h) & 1) for h in range(n)], in_desc, bool(rst_n)
        )
        self.cycle_no += 1
        return o

    def _sample(self, rst_n, out_ready, in_valid, in_desc) -> Obs:
        dut, n = self.dut, self.n
        hd = int(self.h_head_desc.value)
        ht = int(self.h_head_ts.value)
        fc = int(self.h_count.value)
        out_valid = int(dut.o_out_valid.value)
        return Obs(
            cycle=self.cycle_no,
            rst_n=rst_n,
            out_ready=out_ready,
            in_valid=in_valid,
            in_desc=in_desc,
            in_ready=int(dut.o_in_ready.value),
            out_valid=out_valid,
            out_desc=int(dut.o_out_desc.value),
            out_source=int(dut.o_out_source.value),
            fire=out_valid & out_ready,
            i_head_valid=int(self.h_head_valid.value),
            i_count=[(fc >> (h * CNT_W)) & 0x1F for h in range(n)],
            i_head_desc=[(hd >> (h * DESC_W)) & DESC_MASK for h in range(n)],
            i_head_ts=[(ht >> (h * TS_W)) & TS_MASK for h in range(n)],
            i_push=int(self.h_push.value),
            i_pop=int(self.h_pop.value),
            i_fire=int(self.h_fire.value),
            i_held=int(self.h_held.value),
            i_cand_valid=int(self.h_cand_valid.value),
            i_cand_source=int(self.h_cand_source.value),
            i_counter=int(self.h_cnt.value),
        )

    # ----- layer 5: spec 4 input hold from the observed pins -----------------------------------------

    def _input_hold_check(self, o: Obs) -> None:
        """Read rst_n / i_in_valid / i_in_desc back from the DUT pins (not the requested values) and
        step the unconditional producer-hold checker with them."""
        dut, n = self.dut, self.n
        pin_rst_n = int(dut.rst_n.value)
        pin_valid = int(dut.i_in_valid.value)
        pin_vec = int(dut.i_in_desc.value)
        pin_desc = [(pin_vec >> (h * DESC_W)) & DESC_MASK for h in range(n)]
        w = f"cycle {o.cycle} [input pins]"
        assert pin_rst_n == o.rst_n, f"{w}: rst_n pin {pin_rst_n}, driven {o.rst_n}"
        assert pin_valid == o.in_valid, f"{w}: i_in_valid pin {pin_valid:#x}, driven {o.in_valid:#x}"
        assert pin_desc == o.in_desc, f"{w}: i_in_desc pins differ from the driven descriptors"
        self.in_hold.step(o.cycle, pin_rst_n, pin_valid, o.in_ready, pin_desc)

    # ----- layer 1: reference model ----------------------------------------------------------------

    def _check_against_model(self, o: Obs) -> None:
        n, m = self.n, self.model
        v = m.view(bool(o.out_ready), bool(o.rst_n))
        w = f"cycle {o.cycle} (epoch {m.epoch}, rst_n={o.rst_n}, ready={o.out_ready}) [model]"

        def mask(bits) -> int:
            return sum(1 << h for h in range(n) if bits[h])

        assert o.in_ready == mask(v.in_ready), f"{w}: o_in_ready={o.in_ready:#x}, model {mask(v.in_ready):#x}"
        assert o.out_valid == int(v.out_valid), f"{w}: o_out_valid={o.out_valid}, model {int(v.out_valid)}"
        if v.out_valid:
            assert o.out_source == v.out_source, f"{w}: o_out_source={o.out_source}, model {v.out_source}"
            assert o.out_desc == v.out_desc, (
                f"{w}: o_out_desc={o.out_desc:#029x}, model {v.out_desc:#029x}, diff {o.out_desc ^ v.out_desc:#029x}"
            )
        # internal state
        assert o.i_head_valid == mask(v.head_valid), f"{w}: head_valid={o.i_head_valid:#x}, model {mask(v.head_valid):#x}"
        assert o.i_count == list(v.count), f"{w}: fifo_count={o.i_count}, model {list(v.count)}"
        for h in range(n):
            if v.head_valid[h]:
                assert o.i_head_desc[h] == v.head_desc[h], (
                    f"{w}: head_desc[{h}]={o.i_head_desc[h]:#029x}, model {v.head_desc[h]:#029x}"
                )
                assert o.i_head_ts[h] == v.head_ts[h], (
                    f"{w}: stored head_ts[{h}]={o.i_head_ts[h]:#010x}, model {v.head_ts[h]:#010x}"
                )
        assert o.i_held == int(v.held), f"{w}: grant_held={o.i_held}, model {int(v.held)}"
        assert o.i_fire == int(v.fire), f"{w}: internal fire={o.i_fire}, model {int(v.fire)}"
        assert o.i_pop == mask(v.pop), f"{w}: pop={o.i_pop:#x}, model {mask(v.pop):#x}"
        exp_push = mask([bool((o.in_valid >> h) & 1) and v.in_ready[h] for h in range(n)])
        assert o.i_push == exp_push, f"{w}: push={o.i_push:#x}, model {exp_push:#x}"
        cand = m.candidate()
        assert o.i_cand_valid == int(cand.valid), f"{w}: FCFS cand_valid={o.i_cand_valid}, model {int(cand.valid)}"
        if cand.valid:
            assert o.i_cand_source == cand.source, (
                f"{w}: FCFS candidate source {o.i_cand_source}, model (oldest absolute arrival, lowest ID) "
                f"{cand.source}; heads ts={[hex(t) for t in o.i_head_ts]}"
            )
        exp_cnt = m.counter()
        assert exp_cnt is not None, "arrival counter unknown after reset"
        assert o.i_counter == exp_cnt, f"{w}: arrival_cnt_q={o.i_counter:#010x}, model {exp_cnt:#010x}"

    # ----- layers 2-4: pins, scoreboard, responses -------------------------------------------------

    def _pin_checks(self, o: Obs, meta: Dict[int, int]) -> None:
        n, cov, sb = self.n, self.cov, self.sb
        w = f"cycle {o.cycle} [pins]"
        cov.cycles += 1
        o.push = o.in_valid & o.in_ready

        # Responses due this cycle (the memory model runs in every cycle, reset or not).
        cov.responses += len(self.resp.step(o.cycle, self.epoch))

        # Counter wrap observation (internal, informative bin).
        if self.prev_counter is not None and self.prev_counter == TS_MASK and o.i_counter == 0 and o.rst_n:
            cov.counter_wraps += 1
        self.prev_counter = o.i_counter

        occ = [len(q) for q in sb]
        prev = self.prev
        assert o.i_held == int(prev[0] == "stall"), f"{w}: grant_held={o.i_held}, previous cycle was {prev[0]}"
        assert o.i_fire == o.fire, f"{w}: internal fire {o.i_fire} != out_valid & out_ready"

        if not o.rst_n:
            assert o.out_valid == 0, f"{w}: o_out_valid active during reset"
            assert o.in_ready == 0, f"{w}: o_in_ready active during reset"
            assert o.i_push == 0 and o.i_pop == 0 and o.i_fire == 0
            cov.reset_cycles += 1
            if prev[0] == "fire" and prev[2] is not None:
                cov.full_fire_then_reset += 1
            if not self.in_reset_run:
                cov.resets += 1
            self.in_reset_run = True
            cov.reset_during_hold += o.i_held
            cov.reset_nonempty += int(any(occ))
            self._close_epoch()
            self.prev = ("reset",)
            self.hold_len = 0
            self.valid_ready_low_run = 0
            return
        self.in_reset_run = False

        for h in range(n):
            exp_ready = int(occ[h] < self.depth)
            assert (o.in_ready >> h) & 1 == exp_ready, (
                f"{w}: in_ready[{h}]={(o.in_ready >> h) & 1} with pin-level occupancy {occ[h]}"
            )
            assert occ[h] <= self.depth
        # Work conservation (FCFS selects whenever an eligible head exists): offered iff anything
        # accepted is still outstanding. A same-cycle push never creates an offer (no bypass).
        assert o.out_valid == int(any(occ)), f"{w}: o_out_valid={o.out_valid} with pin occupancy {occ}"

        nonempty = [h for h in range(n) if occ[h]]
        if prev[0] == "stall":
            _, p_src, p_desc = prev
            assert o.out_valid == 1 and o.out_source == p_src, (
                f"{w}: stalled offer of source {p_src} not retained (valid={o.out_valid}, source={o.out_source})"
            )
            assert o.out_desc == p_desc, f"{w}: descriptor changed during the stall, diff {o.out_desc ^ p_desc:#029x}"
        elif o.out_valid:
            heads = [(sb[h][0].accept_cycle, h) for h in nonempty]
            exp_src = min(heads)[1]
            assert o.out_source == exp_src, (
                f"{w}: FCFS offered source {o.out_source}, pin history says oldest head is source {exp_src} "
                f"(accepting cycles {dict((h, c) for c, h in heads)})"
            )
            oldest = sb[exp_src][0].accept_cycle
            cov.ties += int(sum(1 for c, _h in heads if c == oldest) > 1)
            cov.older_beats_lower += int(exp_src > nonempty[0])
            ts_sel = o.i_head_ts[exp_src]
            cov.wrap_discriminating += int(any(o.i_head_ts[h] < ts_sel for h in nonempty if h != exp_src))
        if o.out_valid:
            src = o.out_source
            assert o.out_desc == sb[src][0].desc, (
                f"{w}: o_out_desc is not the oldest accepted descriptor of source {src}, "
                f"diff {o.out_desc ^ sb[src][0].desc:#029x}"
            )

        self._coverage(o, prev, occ, nonempty)

        # Scoreboard: fire first (beginning-of-cycle queue), then this edge's pushes.
        if o.fire:
            src = o.out_source
            e = sb[src].popleft()
            waited = o.cycle - e.accept_cycle
            assert waited >= 1, f"{w}: descriptor fired {waited} cycles after its accepting edge (bypass)"
            cov.min_wait = waited if cov.min_wait is None else min(cov.min_wait, waited)
            cov.max_wait = waited if cov.max_wait is None else max(cov.max_wait, waited)
            self.total_delivered += 1
            o.fired = e
            self.resp.issue(self.epoch, (o.out_desc >> TAG_LSB) & 0xFFFFFFFF, o.cycle, src, o.out_desc)
            if self.on_fire is not None:
                self.on_fire(src, e, o.cycle)
        for h in range(n):
            if (o.push >> h) & 1:
                sb[h].append(SbEntry(o.in_desc[h], o.cycle, meta.get(h)))
                self.total_accepted += 1

        if o.fire:
            src = o.out_source
            refused = src if (occ[src] == self.depth and (o.in_valid >> src) & 1) else None
            self.prev = ("fire", src, refused)
        elif o.out_valid:
            self.prev = ("stall", o.out_source, o.out_desc)
        else:
            self.prev = ("idle",)

    def _coverage(self, o: Obs, prev: tuple, occ: List[int], nonempty: List[int]) -> None:
        cov, n = self.cov, self.n
        cov.pushes += bin(o.push).count("1")
        if o.out_valid and not o.out_ready:
            cov.stall_cycles += 1
            self.valid_ready_low_run += 1
            cov.max_valid_ready_low_run = max(cov.max_valid_ready_low_run, self.valid_ready_low_run)
        else:
            self.valid_ready_low_run = 0
        if any(c == self.depth for c in occ):
            cov.full_cycles += 1
            cov.full_sources.update(h for h in range(n) if occ[h] == self.depth)
        cov.all_full_cycles += int(all(c == self.depth for c in occ))
        if o.i_held:
            src = o.out_source
            if self.hold_len == 0:
                cov.holds += 1
            self.hold_len += 1
            cov.max_hold_len = max(cov.max_hold_len, self.hold_len)
            cov.push_during_hold += int(o.push != 0)
            cov.push_into_held_src += (o.push >> src) & 1
            cov.hold_with_other_nonempty += int(any(h != src for h in nonempty))
        if prev[0] == "fire" and prev[2] is not None:
            cov.ready_after_full_fire += (o.in_ready >> prev[2]) & 1
            assert (o.in_ready >> prev[2]) & 1, (
                f"cycle {o.cycle} [pins]: source {prev[2]} fired from full but is not ready the next cycle"
            )
        if o.fire:
            src = o.out_source
            cov.fires += 1
            cov.fires_held += o.i_held
            cov.fire_sources.add(src)
            if occ[src] == self.depth and (o.in_valid >> src) & 1:
                cov.full_refused += 1
                assert not (o.push >> src) & 1, f"cycle {o.cycle} [pins]: full source {src} accepted a push"
            cov.fire_with_push_same_src += (o.push >> src) & 1
            if prev[0] == "fire":
                cov.b2b_fires += 1
                cov.b2b_switch += int(prev[1] != src)
            self.hold_len = 0

    def _close_epoch(self) -> None:
        """A reset edge ends the epoch: whatever is still queued is discarded by reset."""
        for h in range(self.n):
            for e in self.sb[h]:
                self.dropped_by_reset += 1
                if self.on_reset_drop is not None:
                    self.on_reset_drop(h, e)
            self.sb[h].clear()
        self.epoch += 1

    # ----- accounting ------------------------------------------------------------------------------

    def outstanding(self) -> int:
        return sum(len(q) for q in self.sb)

    def assert_conserved(self) -> None:
        assert self.total_accepted == self.total_delivered + self.dropped_by_reset + self.outstanding()
        assert self.cov.pushes == self.total_accepted and self.cov.fires == self.total_delivered
        assert self.resp.issued == self.total_delivered

    async def drain(
        self, guard_extra: int = 8, on_cycle: Optional[Callable[[Obs], None]] = None
    ) -> List[Tuple[int, int]]:
        """ready=1 until every FIFO is empty. Returns [(source, desc)] in fire order.

        Inputs (spec 4 producer hold, C1 repair): a descriptor that was offered and refused in the
        cycle before the drain (and each drain cycle) is kept driven, valid with identical bits,
        until it is pushed; nothing else is ever offered. Each source owes at most one such push,
        so the drain is bounded by n * (depth + 1) fire cycles. ``on_cycle`` sees every drain cycle's
        observation (used by run_trace to account drain-only pushes)."""
        got: List[Tuple[int, int]] = []
        guard = self.n * (self.depth + 1) + guard_extra
        while self.outstanding() or self.in_hold.pending:
            assert guard > 0, "drain did not complete"
            guard -= 1
            work = self.outstanding()
            # A refused offer outside reset means a full FIFO, so there is always work here.
            assert work > 0, f"cycle {self.cycle_no}: input hold obligation {self.in_hold.pending} with empty FIFOs"
            o = await self.cycle(push=self.in_hold.obligations(), out_ready=1)
            if on_cycle is not None:
                on_cycle(o)
            assert o.fire == 1, f"cycle {o.cycle}: drain cycle without fire (bubble) while work exists"
            got.append((o.out_source, o.out_desc))
        assert not self.in_hold.pending
        o = await self.cycle(out_ready=1)
        assert o.out_valid == 0 and o.i_head_valid == 0 and o.i_held == 0
        assert o.i_count == [0] * self.n and o.in_ready == self.all_src
        return got

    async def finish(self) -> List[Tuple[int, int]]:
        """Drain the switch, then idle until every TB response has returned."""
        got = await self.drain()
        guard = self.resp.delay[1] + 4
        while self.resp.outstanding:
            assert guard > 0, "responses did not complete"
            guard -= 1
            await self.cycle()
        self.resp.assert_all_complete()
        self.assert_conserved()
        assert self.outstanding() == 0 and self.model.nonempty_sources() == [] and self.model.held is None
        return got

    async def idle(self, k: int = 1, out_ready: int = 0) -> Obs:
        o = None
        for _ in range(k):
            o = await self.cycle(out_ready=out_ready)
        return o


# ----- trace-driven random traffic (short random test and primary regression) -----------------------


def _stats(samples: List[int]) -> dict:
    return {
        "count": len(samples),
        "mean": mean(samples),
        "p99_nearest_rank": nearest_rank_p99(samples),
        "min": min(samples) if samples else None,
        "max": max(samples) if samples else None,
    }


async def run_trace(dut, tb: SwitchFcfsTb, trace: Trace, log_every: int = 0) -> dict:
    """Replay ``trace`` (intended generation + ready + reset) on the DUT, then drain.

    Measurement interval = trace cycles 0..cycles-1 (no warmup). Producers present their oldest
    pending generated descriptor with valid held until push. Every measurement metric (push/fire
    counts and rates over the measured cycles, generation-to-acceptance, generated-but-unaccepted,
    coverage snapshot) is taken at the measurement boundary and is not changed by the drain.

    Drain phase (C1 repair, spec 4 producer hold; chosen design = "hold the boundary offers, release
    nothing else"): ready=1. A request that was presented and refused in the last measured cycle
    (observed pins: in_valid=1, in_ready=0, rst_n=1) stays driven with identical bits until it is
    pushed; no further producer backlog is ever presented. Those boundary pushes and their fires
    are accounted separately as drain-only accepts (``drain_only``) and are excluded from every
    measurement population (rates, measured-accept waits, generation-to-acceptance). Then idle
    until every TB response has returned (each fired tag, including drain-only ones, exactly once).
    Returns the spec 10 metrics (JSON-ready dict)."""
    n = tb.n
    prod = Producers(n)
    base = tb.cycle_no  # TB cycle of trace cycle 0
    meas_end = base + trace.cycles  # first drain cycle
    phase_metrics = None
    if trace.profile == "primary":
        assert not any(trace.reset), "primary phase metrics require the reset-free primary profile"
        phase_metrics = PrimaryPhaseMetrics(trace.phases, n, trace.cycles, tb.depth)
    waits_meas: List[int] = []  # accepted in measurement, fired in measurement
    waits_drain: List[int] = []  # accepted in measurement, fired in drain (drain-completed)
    waits_drain_only: List[int] = []  # accepted in drain (boundary hold), fired in drain
    fires_meas = [0] * n
    fires_drain = [0] * n  # fires in drain of requests accepted during measurement
    fires_drain_only = [0] * n  # fires of requests accepted only in drain
    pushes_src = [0] * n
    drain_pushes_src = [0] * n
    gen_to_accept: List[int] = []
    gen_to_accept_drain: List[int] = []
    dropped_meas = 0

    def on_fire(src: int, e: SbEntry, cycle: int) -> None:
        w = cycle - e.accept_cycle
        if phase_metrics is not None and cycle >= meas_end and e.accept_cycle < meas_end:
            phase_metrics.drain_fire(cycle - base, src, tag_of(e.desc))
        if cycle < meas_end:
            fires_meas[src] += 1
            waits_meas.append(w)
        elif e.accept_cycle < meas_end:
            fires_drain[src] += 1
            waits_drain.append(w)
        else:
            fires_drain_only[src] += 1
            waits_drain_only.append(w)

    def on_drop(_src: int, _e: SbEntry) -> None:
        nonlocal dropped_meas
        dropped_meas += 1

    tb.on_fire = on_fire
    tb.on_reset_drop = on_drop
    resp_at_meas_end = None
    for k in range(trace.cycles):
        if trace.gen[k]:
            prod.generate(k, trace.gen[k])
        offers = prod.offers()
        o = await tb.cycle(
            push={h: d for h, (_g, d) in offers.items()},
            out_ready=trace.ready[k],
            rst_n=0 if trace.reset[k] else 1,
            meta={h: g for h, (g, _d) in offers.items()},
        )
        if phase_metrics is not None:
            phase_metrics.observe(
                k, [(h, tag_of(d)) for h, d in trace.gen[k]],
                [(h, tag_of(o.in_desc[h])) for h in range(n) if (o.push >> h) & 1],
                (o.out_source, tag_of(o.out_desc)) if o.fire else None, o.out_valid, o.out_ready,
            )
        for h in range(n):
            if (o.push >> h) & 1:
                rec = prod.accept(h, k)
                assert rec.desc == o.in_desc[h]
                pushes_src[h] += 1
                gen_to_accept.append(rec.push_cycle - rec.gen_cycle)
        if log_every and (k + 1) % log_every == 0:
            dut._log.info("trace cycle %d/%d: fires=%d pushes=%d backlog=%d", k + 1, trace.cycles,
                          tb.cov.fires, tb.cov.pushes, prod.backlog())  # fmt: skip
    assert tb.cycle_no == meas_end
    if phase_metrics is not None:
        phase_metrics.freeze()
    outstanding_at_meas_end = tb.outstanding()
    resp_at_meas_end = len(tb.resp.outstanding)
    backlog = prod.backlog()
    cov_meas = tb.cov.as_dict()
    # Already-offered, refused requests at the boundary, from the observed pins of the last
    # measured cycle. They must be the producers' current offers (oldest pending per source).
    boundary = tb.in_hold.obligations()
    offers_now = prod.offers()
    boundary_offers: Dict[int, Tuple[int, int]] = {}
    for h, d in boundary.items():
        assert h in offers_now and offers_now[h][1] == d, f"boundary offer of source {h} is not its producer head"
        boundary_offers[h] = offers_now[h]
    unoffered_at_boundary = backlog - len(boundary_offers)
    hold_checked_at_meas_end = tb.in_hold.checked

    def on_drain_cycle(o: Obs) -> None:
        assert o.cycle >= meas_end
        for h in range(n):
            if not (o.in_valid >> h) & 1:
                continue
            assert h in boundary_offers and drain_pushes_src[h] == 0, (
                f"cycle {o.cycle}: drain offered source {h}, which owed no boundary hold"
            )
            if (o.push >> h) & 1:
                rec = prod.accept(h, o.cycle - base)
                assert (rec.gen_cycle, rec.desc) == boundary_offers[h] and rec.desc == o.in_desc[h]
                drain_pushes_src[h] += 1
                gen_to_accept_drain.append(rec.push_cycle - rec.gen_cycle)

    drain_start = tb.cycle_no
    await tb.drain(on_cycle=on_drain_cycle)
    drain_fire_cycles = tb.cycle_no - drain_start
    resp_wait_start = tb.cycle_no
    await tb.finish()
    drain_cycles = tb.cycle_no - drain_start

    measured_cycles = trace.cycles - sum(trace.reset)
    fires_m = sum(fires_meas)
    pushes_m = sum(pushes_src)
    pushes_d = sum(drain_pushes_src)
    assert pushes_m + pushes_d == len(prod.accepted)
    assert prod.generated == trace.generated == pushes_m + backlog, "generation/acceptance bookkeeping"
    assert fires_m + sum(fires_drain) + dropped_meas == pushes_m
    assert len(waits_drain) == outstanding_at_meas_end
    # Every boundary-held offer was pushed exactly once in the drain, then fired exactly once.
    assert [h for h in range(n) if drain_pushes_src[h]] == sorted(boundary_offers), "boundary offer not pushed"
    assert fires_drain_only == drain_pushes_src and len(waits_drain_only) == pushes_d == len(boundary_offers)
    assert prod.backlog() == backlog - pushes_d == unoffered_at_boundary
    assert tb.resp.issued == tb.resp.completed == fires_m + sum(fires_drain) + pushes_d
    completed = waits_meas + waits_drain  # measured-accept population only (no drain-only accepts)
    result = {
        "trace": trace.summary(),
        "phases": {
            "initial_reset_cycles_not_measured": 3,
            "measurement_cycles": trace.cycles,
            "measurement_reset_cycles": sum(trace.reset),
            "measured_non_reset_cycles": measured_cycles,
            "warmup_cycles": 0,
            "drain_cycles_total": drain_cycles,
            "drain_fire_phase_cycles": drain_fire_cycles,
            "drain_response_wait_cycles": tb.cycle_no - resp_wait_start,
            "drain_policy": "ready=1; spec 4 hold: each request presented and refused in the last "
            "measured cycle stays driven (identical bits) until pushed (drain-only accept); no "
            "further producer backlog is presented",
        },
        "accepted_transfer_rate": fires_m / measured_cycles if measured_cycles else None,
        "fires_measurement": fires_m,
        "fires_drain": sum(fires_drain),
        "input_push_count": pushes_m,
        "input_push_rate": pushes_m / measured_cycles if measured_cycles else None,
        "per_source_service_measurement": fires_meas,
        "per_source_service_drain": fires_drain,
        "per_source_pushes": pushes_src,
        "wait_acceptance_to_fire": {
            "definition": "fire-edge cycle minus push-edge cycle; requests accepted during measurement",
            "all_completed": _stats(completed),
            "fired_in_measurement": _stats(waits_meas),
            "drain_completed": _stats(waits_drain),
            "censored_at_measurement_end": outstanding_at_meas_end,
            "censored_note": "accepted in measurement but not yet fired at its end; their waits "
            "are completed in the drain phase and included in all_completed",
            "outstanding_after_drain": tb.outstanding(),
            "dropped_by_reset": dropped_meas,
        },
        "generation_to_acceptance": {
            "definition": "push-edge cycle minus TB generation cycle",
            **_stats(gen_to_accept),
        },
        "generated": prod.generated,
        "generated_but_unaccepted": backlog,
        "generated_but_unaccepted_note": "snapshot at the measurement boundary; includes the "
        "boundary-held offers that are pushed only in the drain (see drain_only)",
        "drain_only": {
            "definition": "requests presented and refused in the last measured cycle, kept driven "
            "(spec 4 hold) and accepted only in the drain; excluded from every measurement metric",
            "boundary_held_offers": len(boundary_offers),
            "boundary_held_sources": sorted(boundary_offers),
            "unoffered_backlog_at_boundary": unoffered_at_boundary,
            "pushes": pushes_d,
            "per_source_pushes": drain_pushes_src,
            "fires": sum(fires_drain_only),
            "per_source_fires": fires_drain_only,
            "wait_acceptance_to_fire": _stats(waits_drain_only),
            "generation_to_acceptance": _stats(gen_to_accept_drain),
            "generated_never_accepted": prod.backlog(),
        },
        "input_hold": {
            "rule": "spec 4: in_valid=1 refused in a non-reset cycle must keep valid and all 105 bits "
            "until push or reset (observed pins, every cycle, unconditional)",
            "obligation_checks_total": tb.in_hold.checked,
            "obligation_checks_measurement": hold_checked_at_meas_end,
            "obligation_checks_drain": tb.in_hold.checked - hold_checked_at_meas_end,
        },
        "responses": {
            "issued": tb.resp.issued,
            "issued_for_drain_only_accepts": sum(fires_drain_only),
            "completed": tb.resp.completed,
            "outstanding_at_measurement_end": resp_at_meas_end,
            "reordered": tb.resp.reordered,
            "max_outstanding": tb.resp.max_outstanding,
            "cross_epoch_completions": tb.resp.cross_epoch_completions,
            "delay_range": list(tb.resp.delay),
        },
        "coverage_measurement": cov_meas,
        "coverage_total": tb.cov.as_dict(),
    }
    if phase_metrics is not None:
        result["primary_phase_metrics"] = phase_metrics.result(result)
    return result


def write_json(name: str, data: dict) -> Path:
    """Write a JSON result into the cocotb run directory (the runner copies it as evidence)."""
    path = Path.cwd() / name
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
