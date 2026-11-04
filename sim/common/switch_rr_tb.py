"""Cycle-exact cocotb harness for switch_top with POLICY=1 (Round Robin), milestone M4.

DUT pins (spec 3): clk, rst_n, i_in_valid[N], o_in_ready[N], i_in_desc[N*105], o_out_valid,
i_out_ready, o_out_desc[105], o_out_source[clog2 N]. Internal state is observed READ-ONLY through
VPI (the build uses --public-flat-rw): FIFO head/occupancy vectors of the policy slot, the hold
controller, the RR candidate and the RR state switch_top.gen_policy_rr.u_rr_sched.{ptr_q, used_q}.
Nothing internal is ever written. RR has no arrival metadata, so there is no counter and no
timestamp to observe; ``head_ts`` of the policy slot must read constant 0.

The quantum under test comes from CXL_PARAM_RR_QUANTUM (10 = primary, 1 = supplementary D32).

Cycle convention (spec 4): cycle c is the interval before its closing rising edge. ``cycle()``
drives every input DRIVE_DELAY_NS after the previous edge, samples every output in the read-only
phase at the falling edge, runs the checks, lets the rising edge happen and commits the same edge
in the reference model.

Independent layers on EVERY cycle of EVERY test:

1. model comparison against ``cxl_model.RrSwitchModel`` (abstract turn-record RR oracle, written
   from the contract, not from the RTL): pins (o_in_ready, o_out_valid, and o_out_source and all
   105 bits of o_out_desc when valid) and internal state (FIFO counts, head valid/descriptor, held
   flag, fire, pop, push, RR candidate, and the polling state (ptr_q, used_q) against the model's
   spec-level (polling position, fires charged to the open turn)). After every edge the turn event
   the model derived is compared with the pin-level turn tracker of layer 2;
2. model-free pin rules: in_ready from beginning-of-cycle occupancy as seen on the pins
   (accepted - delivered), outputs/handshakes inactive in reset, work conservation (no control-only
   bubble: offered whenever an accepted descriptor is outstanding, spec 5/7), stall stability of
   valid + all 105 bits + source, hold provenance, and spec 7 restated over the pin history alone
   (turn tracker: an unlocked offer is the open turn's source, otherwise the first nonempty source
   circularly from the polling position; a fire is charged to the source that actually fired;
   a turn ends at the quantum even with a replacement push, or when the post-edge pin occupancy
   is 0; reset polls source 0);
3. pin-level scoreboard (model-free): whole-descriptor and source-sideband integrity (the offered
   descriptor is the oldest accepted descriptor of o_out_source), accepted-request conservation,
   no loss or duplication, per-source order, fire wait >= 1 (no bypass);
4. TB-only tagged responses (``tag_response.TagResponder``): each fire issues one outstanding
   (epoch, tag); responses return after seeded random delays (reordered) and must match exactly one
   outstanding request exactly once. The responder never drives the DUT, so responses can never
   charge quota;
5. spec 4 input (producer) hold from the OBSERVED input pins (``input_hold.InputHoldChecker``),
   unconditional, on every cycle including measurement -> drain entry, drain and drain completion.

The policy-independent methods (input-hold pin read-back, epoch close, conservation, drain, finish,
idle) are the accepted, Codex C1-reviewed implementations of ``switch_fcfs_tb.SwitchFcfsTb``, reused
verbatim; they only use the pin-level scoreboard, the input-hold checker, the responder and
``self.cycle()``. ``run_trace`` (intended-trace replay with measured / drain-only populations) is
likewise reused unchanged from switch_fcfs_tb.
"""

from __future__ import annotations

import random
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "refc") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "refc"))

from cocotb.clock import Clock  # noqa: E402
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer
from switch_fcfs_tb import (  # noqa: F401  (re-exported for the RR tests)
    CLK_PERIOD_NS,
    CNT_W,
    DEPTH,
    DESC_MASK,
    DESC_W,
    DRIVE_DELAY_NS,
    TAG_LSB,
    SbEntry,
    SwitchFcfsTb,
    param_from_env,
    run_seed,
    run_trace,
    write_json,
)

import cocotb
from cxl_model import RR_QUANTUM_PRIMARY, RR_QUANTUM_SUPPLEMENTARY, RrSwitchModel
from input_hold import InputHoldChecker
from tag_response import TagResponder

POLICY_RR = 1


@dataclass
class ObsRr:
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
    i_head_ts_any: int  # OR of the policy-slot head_ts vector (RR: must be 0)
    i_push: int
    i_pop: int
    i_fire: int
    i_held: int
    i_cand_valid: int
    i_cand_source: int
    i_ptr: int
    i_used: int
    push: int = 0  # pin-level in_valid & in_ready
    fired: Optional[SbEntry] = None
    turn_event: Optional[str] = None  # pin-level turn tracker event of this edge
    charged: int = 0  # pin-level fires of the charged turn after this edge
    edge: object = None


@dataclass
class CoverageRr:
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
    reset_mid_turn: int = 0  # reset edge while a turn is open (fires charged > 0)
    full_cycles: int = 0  # cycles with at least one full FIFO
    all_full_cycles: int = 0
    responses: int = 0
    min_wait: Optional[int] = None
    max_wait: Optional[int] = None
    # Round Robin bins
    turns_expired: int = 0  # turn ended by the quantum
    turns_expired_replaced: int = 0  # ... while a same-edge replacement push kept the source nonempty
    turns_expired_nonempty: int = 0  # ... while the source stays nonempty (with or without replacement)
    turns_emptied: int = 0  # turn ended by post-edge emptiness (unused quota relinquished)
    final_head_replaced_continue: int = 0  # final-head fire + replacement push: turn continued
    turn_continue: int = 0
    turn_opened: int = 0
    renew_same_source: int = 0  # a source opened a new turn right after its own expired turn
    unlocked_offers: int = 0
    skip_offers: int = 0  # unlocked offer of a new turn not at the polling position (empty skipped)
    wrap_offers: int = 0  # ... at a source below the polling position (circular wrap)
    max_skip: int = 0
    held_cand_mismatch: int = 0  # held grant fired while this cycle's candidate is another source
    stall_mid_turn: int = 0  # stall cycles while a turn is open
    idle_cycles: int = 0  # non-reset cycles with every FIFO empty (no candidate)
    idle_nonzero_poll: int = 0  # ... with the polling position away from source 0
    fires_per_turn: List[int] = field(default_factory=list)  # histogram index = fires of an ended turn
    fire_sources: set = field(default_factory=set)
    full_sources: set = field(default_factory=set)
    turn_sources: set = field(default_factory=set)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if not isinstance(v, set)}
        d["fire_sources"] = sorted(self.fire_sources)
        d["full_sources"] = sorted(self.full_sources)
        d["turn_sources"] = sorted(self.turn_sources)
        d["fires_per_turn"] = list(self.fires_per_turn)
        return d

    def summary(self) -> str:
        return " ".join(f"{k}={v}" for k, v in self.as_dict().items())


class SwitchRrTb:
    # Policy-independent harness methods, reused verbatim from the accepted FCFS harness.
    _input_hold_check = SwitchFcfsTb._input_hold_check
    _close_epoch = SwitchFcfsTb._close_epoch
    outstanding = SwitchFcfsTb.outstanding
    assert_conserved = SwitchFcfsTb.assert_conserved
    drain = SwitchFcfsTb.drain
    finish = SwitchFcfsTb.finish
    idle = SwitchFcfsTb.idle

    def __init__(self, dut, label: str, resp_delay: Tuple[int, int] = (1, 48), unique_tags: bool = False) -> None:
        self.dut = dut
        self.n = param_from_env("N_SRC")
        self.policy = param_from_env("POLICY")
        self.q = param_from_env("RR_QUANTUM")
        self.depth = param_from_env("DEPTH")
        self.desc_w = param_from_env("DESC_W")
        self.ts_w = param_from_env("TS_W")
        if self.policy != POLICY_RR:
            raise RuntimeError(f"this harness verifies POLICY=1 (RR), built with POLICY={self.policy}")
        if self.q not in (RR_QUANTUM_PRIMARY, RR_QUANTUM_SUPPLEMENTARY):
            raise RuntimeError(f"RR_QUANTUM={self.q}: only 10 (primary) and 1 (supplementary) are approved")
        self.src_w = (self.n - 1).bit_length()
        self.all_src = (1 << self.n) - 1
        self.model = RrSwitchModel(self.n, self.q, self.depth, self.desc_w)
        self.cov = CoverageRr(fires_per_turn=[0] * (self.q + 1))
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
        self.in_reset_run = False
        self.on_fire: Optional[Callable[[int, SbEntry, int], None]] = None
        self.on_reset_drop: Optional[Callable[[int, SbEntry], None]] = None
        self.in_hold = InputHoldChecker(self.n)  # spec 4 producer hold, always active
        # Pin-level spec 7 turn tracker (layer 2): polling position and open turn (source, fires).
        self.pin_poll = 0
        self.pin_turn: Optional[Tuple[int, int]] = None
        self.last_ended: Optional[Tuple[int, str]] = None  # (source, reason) of the last ended turn
        # internal handles (read-only)
        rr = dut.gen_policy_rr.u_rr_sched
        self.h_ptr = rr.ptr_q
        self.h_used = rr.used_q
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
        assert self.depth == DEPTH and self.desc_w == DESC_W and self.ts_w == 32
        assert len(dut.i_in_valid) == n and len(dut.o_in_ready) == n
        assert len(dut.i_in_desc) == n * 105, "input descriptors must be N x 105 bits"
        assert len(dut.o_out_desc) == 105, "output descriptor must be 105 bits"
        assert len(dut.o_out_source) == self.src_w, "o_out_source must be ceil(log2 N) bits"
        assert len(dut.o_out_valid) == 1 and len(dut.i_out_ready) == 1
        assert len(dut.clk) == 1 and len(dut.rst_n) == 1
        assert len(self.h_ptr) == self.src_w, "RR polling pointer must be ceil(log2 N) bits"
        # used_q holds 0..QUANTUM-1 in $clog2(QUANTUM+1) bits (= bit_length(QUANTUM)): 4 for Q10, 1 for Q1
        assert len(self.h_used) == self.q.bit_length(), f"used_q width {len(self.h_used)} for quantum {self.q}"
        assert len(self.h_head_desc) == n * 105 and len(self.h_count) == n * CNT_W

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
        self.cov = CoverageRr(fires_per_turn=[0] * (self.q + 1))  # bring-up reset is not a covered reset event
        self.in_reset_run = False

    # ----- one cycle -----------------------------------------------------------------------------

    async def cycle(
        self,
        push: Optional[Dict[int, int]] = None,
        out_ready: int = 0,
        rst_n: int = 1,
        meta: Optional[Dict[int, int]] = None,
    ) -> ObsRr:
        """One full cycle. Enter and leave just after a rising edge. ``push`` maps source ->
        descriptor offered with in_valid=1."""
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
        self._check_edge(o)
        self.cycle_no += 1
        return o

    def _sample(self, rst_n, out_ready, in_valid, in_desc) -> ObsRr:
        dut, n = self.dut, self.n
        hd = int(self.h_head_desc.value)
        fc = int(self.h_count.value)
        out_valid = int(dut.o_out_valid.value)
        return ObsRr(
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
            i_head_ts_any=int(self.h_head_ts.value),
            i_push=int(self.h_push.value),
            i_pop=int(self.h_pop.value),
            i_fire=int(self.h_fire.value),
            i_held=int(self.h_held.value),
            i_cand_valid=int(self.h_cand_valid.value),
            i_cand_source=int(self.h_cand_source.value),
            i_ptr=int(self.h_ptr.value),
            i_used=int(self.h_used.value),
        )

    # ----- layer 1: reference model ----------------------------------------------------------------

    def _check_against_model(self, o: ObsRr) -> None:
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
        assert o.i_head_ts_any == 0, f"{w}: RR policy slot head_ts must be constant 0 (no arrival metadata)"
        assert o.i_held == int(v.held), f"{w}: grant_held={o.i_held}, model {int(v.held)}"
        assert o.i_fire == int(v.fire), f"{w}: internal fire={o.i_fire}, model {int(v.fire)}"
        assert o.i_pop == mask(v.pop), f"{w}: pop={o.i_pop:#x}, model {mask(v.pop):#x}"
        exp_push = mask([bool((o.in_valid >> h) & 1) and v.in_ready[h] for h in range(n)])
        assert o.i_push == exp_push, f"{w}: push={o.i_push:#x}, model {exp_push:#x}"
        if not m.state_known:
            return
        cand = m.candidate()
        assert o.i_cand_valid == int(cand.valid), f"{w}: RR cand_valid={o.i_cand_valid}, model {int(cand.valid)}"
        if cand.valid:
            assert o.i_cand_source == cand.source, (
                f"{w}: RR candidate source {o.i_cand_source}, model {cand.source} "
                f"(polling {m.polling_state()}, nonempty {m.nonempty_sources()})"
            )
        exp_state = m.polling_state()
        assert (o.i_ptr, o.i_used) == exp_state, (
            f"{w}: RR state (ptr_q, used_q)=({o.i_ptr}, {o.i_used}), model (polling position, turn fires)={exp_state}"
        )

    def _check_edge(self, o: ObsRr) -> None:
        """After the edge: the model's turn bookkeeping must agree with the pin-level tracker."""
        e = o.edge
        w = f"cycle {o.cycle} [model edge vs pin turn tracker]"
        if not o.rst_n:
            assert e.reset
            return
        if o.fire:
            assert e.fired == (o.out_source, o.out_desc), f"{w}: model fired {e.fired}, pins ({o.out_source}, ...)"
            assert e.turn_event == o.turn_event and e.charged_fires == o.charged, (
                f"{w}: model event {e.turn_event}/{e.charged_fires}, pins {o.turn_event}/{o.charged}"
            )
            # A fire whose RTL candidate differs from the offered grant must be a held grant, and
            # the model must classify it the same way (charged to the grant, not the candidate).
            rtl_mismatch = o.i_cand_source != o.out_source
            assert e.held_mismatch == rtl_mismatch, f"{w}: model held_mismatch {e.held_mismatch}, RTL {rtl_mismatch}"
            assert o.i_held or not rtl_mismatch, f"{w}: unlocked fire of source {o.out_source} != candidate"
            self.cov.held_cand_mismatch += int(rtl_mismatch)
        else:
            assert e.fired is None and e.turn_event is None and o.turn_event is None

    # ----- layers 2-4: pins, RR turn tracker, scoreboard, responses ----------------------------------

    def _pin_checks(self, o: ObsRr, meta: Dict[int, int]) -> None:
        n, cov, sb, q = self.n, self.cov, self.sb, self.q
        w = f"cycle {o.cycle} [pins]"
        cov.cycles += 1
        o.push = o.in_valid & o.in_ready

        # Responses due this cycle (the memory model runs in every cycle, reset or not).
        cov.responses += len(self.resp.step(o.cycle, self.epoch))

        occ = [len(x) for x in sb]
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
            cov.reset_mid_turn += int(self.pin_turn is not None)
            self._close_epoch()
            # Spec 5 / Q1: a reset edge restarts polling at source 0 with no open turn.
            self.pin_poll = 0
            self.pin_turn = None
            self.last_ended = None
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
        # Work conservation (spec 5/7: empty visits and quota renewal never cause a control-only
        # bubble): offered iff anything accepted is still outstanding. A same-cycle push never
        # creates an offer (no bypass).
        assert o.out_valid == int(any(occ)), f"{w}: o_out_valid={o.out_valid} with pin occupancy {occ}"

        nonempty = [h for h in range(n) if occ[h]]
        if prev[0] == "stall":
            _, p_src, p_desc = prev
            assert o.out_valid == 1 and o.out_source == p_src, (
                f"{w}: stalled offer of source {p_src} not retained (valid={o.out_valid}, source={o.out_source})"
            )
            assert o.out_desc == p_desc, f"{w}: descriptor changed during the stall, diff {o.out_desc ^ p_desc:#029x}"
        elif o.out_valid:
            # Spec 7 over the pin history: the open turn keeps the output, otherwise the first
            # nonempty source circularly from the polling position.
            cov.unlocked_offers += 1
            if self.pin_turn is not None:
                exp_src = self.pin_turn[0]
                assert occ[exp_src] > 0, f"{w}: open turn of source {exp_src} with empty pin queue"
            else:
                dist = next(k for k in range(n) if occ[(self.pin_poll + k) % n])
                exp_src = (self.pin_poll + dist) % n
                cov.skip_offers += int(dist > 0)
                cov.wrap_offers += int(exp_src < self.pin_poll)
                cov.max_skip = max(cov.max_skip, dist)
            assert o.out_source == exp_src, (
                f"{w}: RR offered source {o.out_source}; pin history: polling position {self.pin_poll}, "
                f"open turn {self.pin_turn}, nonempty {nonempty} -> source {exp_src}"
            )
        else:
            cov.idle_cycles += 1
            cov.idle_nonzero_poll += int(self.pin_poll != 0)
        if o.out_valid:
            src = o.out_source
            assert occ[src] > 0, f"{w}: offered source {src} has no outstanding accepted descriptor"
            assert o.out_desc == sb[src][0].desc, (
                f"{w}: o_out_desc is not the oldest accepted descriptor of source {src} (sideband/order/integrity), "
                f"diff {o.out_desc ^ sb[src][0].desc:#029x}"
            )
        if o.out_valid and not o.out_ready and self.pin_turn is not None:
            cov.stall_mid_turn += 1

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

        # Turn bookkeeping of this edge from the pins: charge the source that actually fired.
        if o.fire:
            g = o.out_source
            if self.pin_turn is not None:
                assert self.pin_turn[0] == g, f"{w}: source {g} fired while source {self.pin_turn[0]} owns the turn"
                charged = self.pin_turn[1] + 1
            else:
                charged = 1
                cov.turn_opened += 1
                cov.turn_sources.add(g)
                if self.last_ended == (g, "expired"):
                    cov.renew_same_source += 1
            assert 1 <= charged <= q, f"{w}: {charged} fires charged to one turn, quantum {q}"
            post = len(sb[g])  # pin-level post-edge occupancy: beginning + replacement push - fire
            replaced = bool((o.push >> g) & 1)
            if charged == q:
                o.turn_event = "expired"
                cov.turns_expired += 1
                cov.turns_expired_replaced += int(replaced)
                cov.turns_expired_nonempty += int(post > 0)
            elif post == 0:
                o.turn_event = "emptied"
                cov.turns_emptied += 1
            else:
                o.turn_event = "continue"
                cov.turn_continue += 1
                cov.final_head_replaced_continue += int(occ[g] == 1 and replaced)
            o.charged = charged
            if o.turn_event == "continue":
                self.pin_turn = (g, charged)
                self.pin_poll = g
            else:
                cov.fires_per_turn[charged] += 1
                self.pin_turn = None
                self.pin_poll = (g + 1) % n
                self.last_ended = (g, o.turn_event)

        if o.fire:
            src = o.out_source
            refused = src if (occ[src] == self.depth and (o.in_valid >> src) & 1) else None
            self.prev = ("fire", src, refused)
        elif o.out_valid:
            self.prev = ("stall", o.out_source, o.out_desc)
        else:
            self.prev = ("idle",)

    def _coverage(self, o: ObsRr, prev: tuple, occ: List[int], nonempty: List[int]) -> None:
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


def rr_turn_summary(cov: dict, q: int) -> dict:
    """RR turn statistics of a coverage snapshot (JSON-ready)."""
    return {
        "quantum": q,
        "turns_ended": cov["turns_expired"] + cov["turns_emptied"],
        "turns_expired": cov["turns_expired"],
        "turns_expired_with_replacement_push": cov["turns_expired_replaced"],
        "turns_expired_source_still_nonempty": cov["turns_expired_nonempty"],
        "turns_emptied": cov["turns_emptied"],
        "fires_per_ended_turn_histogram": cov["fires_per_turn"],
        "final_head_fire_replacement_continue": cov["final_head_replaced_continue"],
        "renew_same_source_after_expiry": cov["renew_same_source"],
        "skip_offers": cov["skip_offers"],
        "wrap_offers": cov["wrap_offers"],
        "max_skip": cov["max_skip"],
        "held_grant_candidate_mismatch_fires": cov["held_cand_mismatch"],
        "stall_cycles_mid_turn": cov["stall_mid_turn"],
    }
