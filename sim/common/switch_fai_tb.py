"""Cycle-exact cocotb harness for switch_top with POLICY=2 (FAI-inspired Main), milestone M5, and,
through the explicit interpretation selector ``FAI_INTERPS`` (M6), POLICY=3 (supplementary FAI
Algorithm-2, spec 8.6). The selector chooses only the oracle class (``FaiMainSwitchModel`` /
``FaiAlg2SwitchModel``), the layer-2 transition table (literal spec 8.2 / spec 8.6, both typed in
this file), the effective-class map, the cls_q decode, the reset state and the switch_top generate
scope (gen_policy_fai_main / gen_policy_fai_alg2). Every other rule below is shared and unchanged.
Where the text below says "spec 8.2", "H" or "Main", read the selected interpretation for POLICY=3.

DUT pins (spec 3): clk, rst_n, i_in_valid[N], o_in_ready[N], i_in_desc[N*105], o_out_valid,
i_out_ready, o_out_desc[105], o_out_source[clog2 N]. Internal state is observed READ-ONLY through
VPI (the build uses --public-flat-rw): FIFO head/occupancy/timestamp vectors of the policy slot, the
hold controller (grant_held, grant_ctx, u_out_hold.held_ctx_q), the policy candidate
(cand_valid/cand_source/cand_ctx), the shared arrival counter gen_arrival_ts.arrival_cnt_q and the
Main FAI state switch_top.gen_policy_fai_main.u_fai_sched.{cls_q, idx_q, b_q, s_q, turn_q, used_q}
plus its closing/evidence/visit-end nets. The only write to an internal signal is the
simulation-only deposit of arrival_cnt_q for the timestamp-wrap test (``cycle(deposit=...)``),
mirrored in the oracle by ``deposit_counter`` exactly as the accepted M3 wrap test. No RTL port
or RTL change is involved.

The window W under test comes from CXL_PARAM_FAI_W (64 / 256 stress, 5,000,000 production).

Cycle convention (spec 4): cycle c is the interval before its closing rising edge. ``cycle()``
drives every input DRIVE_DELAY_NS after the previous edge, samples every output in the read-only
phase at the falling edge, runs the checks, lets the rising edge happen and commits the same edge
in the reference model.

Independent layers on EVERY cycle of EVERY test:

1. model comparison against ``cxl_model.FaiMainSwitchModel`` (abstract oracle written from the
   contract, not from the RTL): pins (o_in_ready, o_out_valid, and o_out_source and all 105 bits
   of o_out_desc when valid) and internal state (FIFO counts, head valid/descriptor/stored
   timestamp, held flag, held and offered context, fire, pop, push, candidate source + context,
   arrival counter, cls_q of every source, idx_q, every b_q, s_q, turn_q, used_q). After every
   edge the model's edge record (window position, closing, closing counts, evidence, old/new
   class map, charged context, visit event, relinquished visit, held/candidate mismatch) is
   compared with the RTL nets of that cycle and with the layer-2 record;
2. MODEL-FREE pin/history rules, written separately from the oracle (own spec 8.1 evidence
   function and own literal spec 8.2 table below; the cls_q code and the 5-bit context layout
   are the only RTL-facing facts): in_ready from pin occupancy (accepted - delivered), inactivity
   in reset, no control-only bubble (offered iff an accepted descriptor is outstanding), stall
   stability of valid + 105 bits + source + context and hold provenance; window position ==
   non-reset edges since reset mod W from the TB's own cycle count; B per source and S
   recomputed from the pin fire history of the current window and compared with b_q / s_q;
   s_q == sum(b_q) every cycle; at each closing edge the TB's own exact-integer evidence
   (closing fire included) and table predict cls_q of the next cycle; a visit/quota tracker over
   pin fires and the (asserted-equal) class map: an unlocked offer is the FCFS-oldest head by pin
   acceptance order (ties: lowest source) within the visit class, or within the other class with
   context (other, 0) when the visit class has no eligible head; <= 10 fires per visit; a fire
   is charged to the context actually offered (the retained context while held); expiry at 10
   fires even with replacement, otherwise emptiness from post-edge pin occupancy of the charged
   class under the class map of the cycle (fai_main.md 4, derived closing convention);
   turn_q / used_q equal the tracker every cycle;
3. pin-level scoreboard (model-free): whole-descriptor and source-sideband integrity,
   accepted-request conservation, no loss or duplication, per-source order, fire wait >= 1;
4. TB-only tagged responses (``tag_response.TagResponder``), never driving the DUT, so responses
   cannot charge quota or B/S;
5. spec 4 input (producer) hold from the OBSERVED input pins (``input_hold.InputHoldChecker``),
   unconditional, on every cycle including measurement -> drain entry, drain and completion.

The policy-independent methods (input-hold pin read-back, epoch close, conservation, drain,
finish, idle) are the accepted, Codex C1-reviewed implementations of
``switch_fcfs_tb.SwitchFcfsTb``, reused verbatim (as the M4 RR harness does); ``run_trace``
(intended-trace replay with measured / drain-only populations) is reused unchanged.

Opt-in extras (off by default, no effect on the layers above): ``enable_fcfs_mirror()`` steps an
independent ``FcfsSwitchModel`` with the same pins and requires FCFS-equal pins every cycle (M5-primary:
no window closes at W=5,000,000 in 100,000 cycles, fai_main.md 5); ``trim_model_logs()`` drops the
oracle's append-only informational visit/window history lists, which the oracle never reads, so
the multi-million-cycle production runs keep bounded memory.
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
from switch_fcfs_tb import (  # noqa: F401  (re-exported for the FAI tests)
    CLK_PERIOD_NS,
    CNT_W,
    DEPTH,
    DESC_MASK,
    DESC_W,
    DRIVE_DELAY_NS,
    TAG_LSB,
    TS_MASK,
    TS_W,
    SbEntry,
    SwitchFcfsTb,
    param_from_env,
    run_seed,
    run_trace,
    write_json,
)

import cocotb
from cxl_model import FaiAlg2SwitchModel, FaiMainSwitchModel, FcfsSwitchModel, ctx_to_hw
from input_hold import InputHoldChecker
from tag_response import TagResponder

POLICY_FAI_MAIN = 2
POLICY_FAI_ALG2 = 3
SUPPORTED_W = (64, 256, 5_000_000)  # spec 8.1/8.5: production + the two stress windows

# ----- layer-2 definitions, written from the spec (NOT imported from refc) -----------------------
HIGH = "High"
LOW = "Low"
QUOTA = 10  # spec 8.3: High/Low quotas 10/10 successful transfers
CTX_W = 5  # {class (0 High, 1 Low), fires already charged 0..9}
# Spec 8.2 Main table, transcribed literally: current state -> evidence -> next state.
SPEC_8_2 = {
    "H": {"UP": "H", "DOWN": "B_H", "KEEP": "H", "S0": "H"},
    "B_H": {"UP": "H", "DOWN": "L", "KEEP": "H", "S0": "H"},
    "L": {"UP": "B_L", "DOWN": "L", "KEEP": "L", "S0": "L"},
    "B_L": {"UP": "H", "DOWN": "L", "KEEP": "L", "S0": "L"},
}
EFFECTIVE = {"H": HIGH, "B_H": HIGH, "L": LOW, "B_L": LOW}  # spec 8.2 first column
# RTL-facing fact: cxl_fai_main_sched cls_q code, bit0 = effective Low, bit1 = pending change.
CLS_CODE = {"H": 0b00, "L": 0b01, "B_H": 0b10, "B_L": 0b11}
CODE_CLS = {v: k for k, v in CLS_CODE.items()}
STATES = ("H", "B_H", "L", "B_L")
EVIDENCE = ("UP", "DOWN", "KEEP", "S0")

# Spec 8.6 Algorithm-2 table (M6), transcribed literally here, NOT imported from refc: stable High /
# stable Low, or Buffer with stored target p serviced immediately in p. "KEEP / zero-service
# window" is one column, so S0 maps like KEEP (no cancellation).
SPEC_8_6 = {
    "STABLE_HIGH": {"UP": "STABLE_HIGH", "DOWN": "BUFFER_P_LOW", "KEEP": "STABLE_HIGH", "S0": "STABLE_HIGH"},
    "STABLE_LOW": {"UP": "BUFFER_P_HIGH", "DOWN": "STABLE_LOW", "KEEP": "STABLE_LOW", "S0": "STABLE_LOW"},
    "BUFFER_P_HIGH": {"UP": "STABLE_HIGH", "DOWN": "STABLE_LOW", "KEEP": "BUFFER_P_HIGH", "S0": "BUFFER_P_HIGH"},
    "BUFFER_P_LOW": {"UP": "STABLE_HIGH", "DOWN": "STABLE_LOW", "KEEP": "BUFFER_P_LOW", "S0": "BUFFER_P_LOW"},
}
ALG2_EFFECTIVE = {"STABLE_HIGH": HIGH, "STABLE_LOW": LOW, "BUFFER_P_HIGH": HIGH, "BUFFER_P_LOW": LOW}
# RTL-facing fact (fai_alg2.md 2): same 2-bit register, bit0 = effective class = target p, bit1 = Buffer.
ALG2_CLS_CODE = {"STABLE_HIGH": 0b00, "STABLE_LOW": 0b01, "BUFFER_P_HIGH": 0b10, "BUFFER_P_LOW": 0b11}
ALG2_STATES = ("STABLE_HIGH", "BUFFER_P_LOW", "STABLE_LOW", "BUFFER_P_HIGH")


@dataclass(frozen=True)
class FaiInterp:
    """Explicit interpretation selector of the harness (POLICY 2 = Main, 3 = Algorithm-2). Everything
    else in the harness (pins, scoreboard, hold, window/B/S/evidence, visit tracker) is shared."""

    policy: int
    name: str
    scope: str  # generate block of switch_top that holds u_fai_sched
    model_cls: type
    table: Dict[str, Dict[str, str]]
    effective: Dict[str, str]
    code_cls: Dict[int, str]
    states: Tuple[str, ...]
    reset_state: str


FAI_INTERPS = {
    POLICY_FAI_MAIN: FaiInterp(POLICY_FAI_MAIN, "FAI_MAIN", "gen_policy_fai_main", FaiMainSwitchModel, SPEC_8_2,
                               EFFECTIVE, CODE_CLS, STATES, "H"),
    POLICY_FAI_ALG2: FaiInterp(POLICY_FAI_ALG2, "FAI_ALG2", "gen_policy_fai_alg2", FaiAlg2SwitchModel, SPEC_8_6,
                               ALG2_EFFECTIVE, {v: k for k, v in ALG2_CLS_CODE.items()}, ALG2_STATES,
                               "STABLE_HIGH"),
}  # fmt: skip


def spec_evidence(n_src: int, b: int, s: int) -> str:
    """Spec 8.1 with exact Python integers: UP iff 10*N*B < 3*S, DOWN iff N*B > S, KEEP
    otherwise (equality included); S == 0 is the explicit no-service column."""
    assert 0 <= b <= s, f"window counts B={b} S={s}"
    if s == 0:
        return "S0"
    up = 10 * n_src * b < 3 * s
    down = n_src * b > s
    assert not (up and down), f"UP and DOWN for N={n_src} B={b} S={s}"
    return "UP" if up else "DOWN" if down else "KEEP"


def other(cls: str) -> str:
    return LOW if cls == HIGH else HIGH


def ctx_bits(ctx: Tuple[str, int]) -> int:
    cls, used = ctx
    assert cls in (HIGH, LOW) and 0 <= used < QUOTA
    return (int(cls == LOW) << 4) | used


def ctx_of_bits(bits: int) -> Tuple[str, int]:
    used = bits & 0xF
    assert 0 <= bits < (1 << CTX_W) and used < QUOTA, f"context bits {bits:#x} are not a valid FAI context"
    return (LOW if (bits >> 4) & 1 else HIGH, used)


@dataclass
class ObsFai:
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
    i_cand_ctx: int
    i_grant_ctx: int
    i_held_ctx: int
    i_counter: int
    i_cls: List[str]
    i_idx: int
    i_b: List[int]
    i_s: int
    i_turn: int
    i_used: int
    i_closing: int
    i_ev_up: int
    i_ev_down: int
    i_ev_s0: int
    i_class_live: int
    i_visit_end: int
    push: int = 0  # pin-level in_valid & in_ready
    fired: Optional[SbEntry] = None
    # layer-2 record of this cycle / edge
    pos: Optional[int] = None  # TB window position (non-reset edges since reset mod W)
    offered_ctx: Optional[Tuple[str, int]] = None
    charged: Optional[Tuple[str, int]] = None
    visit_event: Optional[str] = None  # "continue" | "expired" | "emptied"
    relinquished: Optional[Tuple[str, int]] = None
    visit_after: Optional[Tuple[str, int]] = None
    closing: bool = False
    b_close: Optional[List[int]] = None
    s_close: Optional[int] = None
    evidence: Optional[List[str]] = None
    old_cls: Optional[List[str]] = None
    new_cls: Optional[List[str]] = None
    edge: object = None


def _transitions(states: Tuple[str, ...] = STATES) -> Dict[str, int]:
    return {f"{s}/{e}": 0 for s in states for e in EVIDENCE}


@dataclass
class CoverageFai:
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
    reset_mid_window: int = 0  # reset edge with window position > 0
    reset_mid_visit: int = 0  # reset edge with fires charged to the open visit
    reset_non_h: int = 0  # reset edge while some source is not H
    full_cycles: int = 0
    all_full_cycles: int = 0
    counter_wraps: int = 0  # observed counter step 0xFFFFFFFF -> 0
    wrap_discriminating: int = 0  # unlocked offer whose head ts is numerically above another in-class eligible ts
    responses: int = 0
    min_wait: Optional[int] = None
    max_wait: Optional[int] = None
    idle_cycles: int = 0  # non-reset cycles with every FIFO empty
    idle_visit_open: int = 0  # ... while fires are charged to the retained visit
    idle_turn_low: int = 0  # ... while the retained turn is Low
    # window / classification
    windows_closed: int = 0
    closing_fire: int = 0  # closing edges with a fire (included in the closing counts)
    held_across_closing: int = 0  # offer stalled at a closing edge (held into the next window)
    held_cls_change: int = 0  # ... and the held source's effective class changed at that edge
    held_fire_cls_differs: int = 0  # held grant fired with a retained class != its source's current class
    max_windows_in_hold: int = 0  # closings during one continuous hold
    effective_changes: int = 0
    max_b: int = 0
    max_s: int = 0
    evidence: Dict[str, int] = field(default_factory=lambda: {e: 0 for e in EVIDENCE})
    transitions: Dict[str, int] = field(default_factory=_transitions)
    closing_live_differs: int = 0  # closing-edge fire where the new class map would change class_live
    closing_continue_then_switch: int = 0  # visit continued at a closing, next unlocked offer switches class
    # visits
    unlocked_offers: int = 0
    class_switch_offers: int = 0  # unlocked offer from the other class with context (other, 0)
    switch_relinquish_offers: int = 0  # ... while fires were charged to the open visit
    visits_continue: int = 0
    visits_expired: int = 0
    visits_expired_replaced: int = 0  # expiry with a same-edge replacement push into the fired source
    visits_expired_live: int = 0  # expiry while the charged class stays nonempty
    visits_emptied: int = 0
    visits_relinquished: int = 0
    renew_same_class: int = 0  # new visit of the class whose visit just expired (other class empty)
    fires_per_visit: List[int] = field(default_factory=lambda: [0] * (QUOTA + 1))  # expired/emptied visits
    fires_low: int = 0
    fires_high: int = 0
    ties_in_class: int = 0
    older_beats_lower_in_class: int = 0
    class_over_age: int = 0  # unlocked offer while the other class holds an older head
    fire_sources: set = field(default_factory=set)
    full_sources: set = field(default_factory=set)
    states_seen: set = field(default_factory=set)  # (source, state) in non-reset cycles
    transitions_seen: set = field(default_factory=set)  # (source, state, evidence) at closings

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if not isinstance(v, set)}
        d["fire_sources"] = sorted(self.fire_sources)
        d["full_sources"] = sorted(self.full_sources)
        d["states_seen"] = sorted(f"{h}:{s}" for h, s in self.states_seen)
        d["states_reached"] = sorted({s for _h, s in self.states_seen})
        d["transitions_reached"] = sorted({f"{s}/{e}" for _h, s, e in self.transitions_seen})
        d["evidence"] = dict(self.evidence)
        d["transitions"] = dict(self.transitions)
        d["fires_per_visit"] = list(self.fires_per_visit)
        return d

    def summary(self) -> str:
        d = self.as_dict()
        d.pop("states_seen")
        return " ".join(f"{k}={v}" for k, v in d.items())

    def source_transitions(self, h: int) -> set:
        return {(s, e) for src, s, e in self.transitions_seen if src == h}


class SwitchFaiTb:
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
        self.w = param_from_env("FAI_W")
        self.depth = param_from_env("DEPTH")
        self.desc_w = param_from_env("DESC_W")
        self.ts_w = param_from_env("TS_W")
        if self.policy not in FAI_INTERPS:
            raise RuntimeError(
                f"this harness verifies POLICY=2 (FAI Main) or 3 (FAI Algorithm-2), built with POLICY={self.policy}"
            )
        self.interp = FAI_INTERPS[self.policy]
        if self.w not in SUPPORTED_W:
            raise RuntimeError(f"FAI_W={self.w}: only {SUPPORTED_W} are approved")
        self.src_w = (self.n - 1).bit_length()
        self.all_src = (1 << self.n) - 1
        self.idx_w = (self.w - 1).bit_length()  # ceil(log2 W)
        self.bs_w = self.w.bit_length()  # ceil(log2(W+1))
        self.model = self.interp.model_cls(self.n, self.w, self.depth, self.desc_w, self.ts_w)
        self.cov = self._new_cov()
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
        self.hold_windows = 0
        self.valid_ready_low_run = 0
        self.prev_counter: Optional[int] = None
        self.in_reset_run = False
        self.on_fire: Optional[Callable[[int, SbEntry, int], None]] = None
        self.on_reset_drop: Optional[Callable[[int, SbEntry], None]] = None
        self.in_hold = InputHoldChecker(self.n)  # spec 4 producer hold, always active
        # Optional FCFS-equivalence mirror (M5-primary, fai_main.md 5): an independent FCFS switch
        # model stepped with the same pin inputs; while no window has closed every source is H and
        # the FAI pins must equal FCFS. Enabled with enable_fcfs_mirror() before start().
        self.fcfs_mirror: Optional[FcfsSwitchModel] = None
        self.fcfs_checked = 0
        self._reset_trackers()
        # internal handles (read-only except the counter deposit)
        fai = getattr(dut, self.interp.scope).u_fai_sched
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
        self.h_cand_ctx = dut.cand_ctx
        self.h_grant_ctx = dut.grant_ctx
        self.h_held_ctx = dut.u_out_hold.held_ctx_q
        self.h_cls = fai.cls_q
        self.h_idx = fai.idx_q
        self.h_b = fai.b_q
        self.h_s = fai.s_q
        self.h_turn = fai.turn_q
        self.h_used = fai.used_q
        self.h_closing = fai.closing
        self.h_ev_up = fai.ev_up
        self.h_ev_down = fai.ev_down
        self.h_ev_s0 = fai.ev_s0
        self.h_class_live = fai.class_live
        self.h_visit_end = fai.visit_end

    def _new_cov(self) -> CoverageFai:
        return CoverageFai(transitions=_transitions(self.interp.states))

    def _reset_trackers(self) -> None:
        """Layer-2 policy trackers at their spec 5 / Q1 reset values."""
        self.pin_cls: List[str] = [self.interp.reset_state] * self.n
        self.pin_visit: Tuple[str, int] = (HIGH, 0)
        self.pin_edges = 0  # non-reset edges since the last reset edge (TB cycle count)
        self.pin_b: List[int] = [0] * self.n
        self.pin_s = 0
        self.last_visit_end: Optional[Tuple[str, str]] = None  # (class, reason) of the last ended visit
        self.continued_at_closing = False

    @property
    def pos(self) -> int:
        """Window position of the NEXT cycle (valid if it is a non-reset cycle)."""
        return self.pin_edges % self.w

    def enable_fcfs_mirror(self) -> None:
        """Step an independent ``FcfsSwitchModel`` alongside (call before ``start``). Every cycle
        the FAI pins (in_ready, out_valid, and source + all 105 bits when valid) must equal the FCFS
        model's; meaningful only while no window closes (all sources H), which the caller asserts."""
        assert self.cycle_no == 0 and self.fcfs_mirror is None
        self.fcfs_mirror = FcfsSwitchModel(self.n, self.depth, self.desc_w, self.ts_w)

    def trim_model_logs(self) -> None:
        """Bounded memory for long runs: drop the oracle's informational visit/window history
        lists. They are append-only records that the oracle never reads back (fai_main_model.py
        commit()), so dropping them changes no oracle decision; the harness keeps its own
        streaming per-window record."""
        self.model.visit_log.clear()
        self.model.window_log.clear()

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
        # FAI Main state widths (fai_main.md 1/2): 2-bit class per source, ceil(log2 W) index,
        # ceil(log2(W+1)) B/S, 1-bit turn, 4-bit used, 5-bit context {class, used}.
        assert len(self.h_cls) == 2 * n, f"cls_q width {len(self.h_cls)}"
        assert len(self.h_idx) == self.idx_w, f"idx_q width {len(self.h_idx)} for W={self.w}"
        assert len(self.h_b) == n * self.bs_w, f"b_q width {len(self.h_b)} for W={self.w}"
        assert len(self.h_s) == self.bs_w, f"s_q width {len(self.h_s)} for W={self.w}"
        assert len(self.h_turn) == 1 and len(self.h_used) == 4
        assert len(self.h_held_ctx) == CTX_W and len(self.h_grant_ctx) == CTX_W and len(self.h_cand_ctx) == CTX_W
        assert len(self.h_ev_up) == n and len(self.h_ev_down) == n and len(self.h_ev_s0) == 1

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
        if self.fcfs_mirror is not None:
            self.fcfs_mirror.commit(rst_n=False)
        self.prev = ("reset",)
        self.in_reset_run = True
        for _ in range(reset_cycles - 1):
            await self.cycle(push={h: (h + 1) * 0x1111 for h in range(self.n)}, out_ready=1, rst_n=0)
        self.cov = self._new_cov()  # bring-up reset is not a covered reset event
        self.in_reset_run = False

    # ----- one cycle -----------------------------------------------------------------------------

    async def cycle(
        self,
        push: Optional[Dict[int, int]] = None,
        out_ready: int = 0,
        rst_n: int = 1,
        meta: Optional[Dict[int, int]] = None,
        deposit: Optional[int] = None,
    ) -> ObsFai:
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
            assert self.fcfs_mirror is None, "no counter deposit with the FCFS mirror"
            self.model.deposit_counter(deposit)  # raises unless right after a reset, all empty
            self.h_cnt.value = deposit

        await FallingEdge(dut.clk)
        await ReadOnly()
        o = self._sample(rst_n, out_ready, in_valid, in_desc)
        self._input_hold_check(o)
        self._check_against_model(o)
        if self.fcfs_mirror is not None:
            self._check_fcfs_mirror(o)
        self._pin_checks(o, meta or {})

        await RisingEdge(dut.clk)
        valid_bits = [bool((in_valid >> h) & 1) for h in range(n)]
        o.edge = self.model.commit(bool(out_ready), valid_bits, in_desc, bool(rst_n))
        if self.fcfs_mirror is not None:
            self.fcfs_mirror.commit(bool(out_ready), valid_bits, in_desc, bool(rst_n))
        self._check_edge(o)
        self.cycle_no += 1
        return o

    def _sample(self, rst_n, out_ready, in_valid, in_desc) -> ObsFai:
        dut, n, bs = self.dut, self.n, self.bs_w
        hd = int(self.h_head_desc.value)
        ht = int(self.h_head_ts.value)
        fc = int(self.h_count.value)
        cls = int(self.h_cls.value)
        bq = int(self.h_b.value)
        out_valid = int(dut.o_out_valid.value)
        return ObsFai(
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
            i_cand_ctx=int(self.h_cand_ctx.value),
            i_grant_ctx=int(self.h_grant_ctx.value),
            i_held_ctx=int(self.h_held_ctx.value),
            i_counter=int(self.h_cnt.value),
            i_cls=[self.interp.code_cls[(cls >> (2 * h)) & 3] for h in range(n)],
            i_idx=int(self.h_idx.value),
            i_b=[(bq >> (h * bs)) & ((1 << bs) - 1) for h in range(n)],
            i_s=int(self.h_s.value),
            i_turn=int(self.h_turn.value),
            i_used=int(self.h_used.value),
            i_closing=int(self.h_closing.value),
            i_ev_up=int(self.h_ev_up.value),
            i_ev_down=int(self.h_ev_down.value),
            i_ev_s0=int(self.h_ev_s0.value),
            i_class_live=int(self.h_class_live.value),
            i_visit_end=int(self.h_visit_end.value),
        )

    # ----- layer 1: reference model ----------------------------------------------------------------

    def _check_against_model(self, o: ObsFai) -> None:
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
            assert o.i_grant_ctx == v.grant_ctx, f"{w}: offered context {o.i_grant_ctx:#x}, model {v.grant_ctx:#x}"
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
        if not m.state_known:
            return
        held = m.held_grant()
        if held is not None:
            assert o.i_held_ctx == ctx_to_hw(held[1]), (
                f"{w}: held_ctx_q={o.i_held_ctx:#x}, model held grant {held} -> {ctx_to_hw(held[1]):#x}"
            )
        cand = m.candidate()
        assert o.i_cand_valid == int(cand.valid), f"{w}: FAI cand_valid={o.i_cand_valid}, model {int(cand.valid)}"
        if cand.valid:
            assert (o.i_cand_source, o.i_cand_ctx) == (cand.source, ctx_to_hw(cand.ctx)), (
                f"{w}: FAI candidate (source, ctx)=({o.i_cand_source}, {o.i_cand_ctx:#x}), model {cand} "
                f"classes {m.classes()} visit {m.visit_state()}"
            )
        exp_cnt = m.counter()
        assert o.i_counter == exp_cnt, f"{w}: arrival_cnt_q={o.i_counter:#010x}, model {exp_cnt:#010x}"
        assert o.i_cls == list(m.classes()), f"{w}: cls_q={o.i_cls}, model {list(m.classes())}"
        pos, b, s = m.window_state()
        assert (o.i_idx, o.i_b, o.i_s) == (pos, list(b), s), (
            f"{w}: (idx_q, b_q, s_q)=({o.i_idx}, {o.i_b}, {o.i_s}), model ({pos}, {list(b)}, {s})"
        )
        vis = m.visit_state()
        assert (o.i_turn, o.i_used) == (int(vis.cls == "Low"), vis.fires), (
            f"{w}: (turn_q, used_q)=({o.i_turn}, {o.i_used}), model visit {vis}"
        )

    def _check_fcfs_mirror(self, o: ObsFai) -> None:
        """FCFS-equivalence cross-check (opt-in): the FAI pins equal an independent FCFS model."""
        n = self.n
        v = self.fcfs_mirror.view(bool(o.out_ready), bool(o.rst_n))
        w = f"cycle {o.cycle} [FCFS mirror]"
        ready = sum(1 << h for h in range(n) if v.in_ready[h])
        assert o.in_ready == ready and o.out_valid == int(v.out_valid), (
            f"{w}: FAI (in_ready, out_valid)=({o.in_ready:#x}, {o.out_valid}), FCFS ({ready:#x}, {int(v.out_valid)})"
        )
        if v.out_valid:
            assert (o.out_source, o.out_desc) == (v.out_source, v.out_desc), (
                f"{w}: FAI offered source {o.out_source}, FCFS model {v.out_source} (classes {o.i_cls})"
            )
        if o.rst_n:
            self.fcfs_checked += 1

    def _rtl_evidence(self, o: ObsFai) -> List[str]:
        out = []
        for h in range(self.n):
            up, down = (o.i_ev_up >> h) & 1, (o.i_ev_down >> h) & 1
            assert not (up and down), f"cycle {o.cycle}: RTL ev_up and ev_down both set for source {h}"
            if o.i_ev_s0:
                assert not up and not down, f"cycle {o.cycle}: RTL S=0 with UP/DOWN for source {h}"
                out.append("S0")
            else:
                out.append("UP" if up else "DOWN" if down else "KEEP")
        return out

    def _check_edge(self, o: ObsFai) -> None:
        """After the edge: the model's edge record must agree with the RTL nets of the cycle and
        with the layer-2 (model-free) record."""
        e = o.edge
        w = f"cycle {o.cycle} [model edge vs RTL vs pin tracker]"
        if not o.rst_n:
            assert e.reset
            return
        assert e.window_pos == o.pos == o.i_idx, f"{w}: window position model {e.window_pos} TB {o.pos} RTL {o.i_idx}"
        assert e.closing == o.closing == bool(o.i_closing), (
            f"{w}: closing model {e.closing} TB {o.closing} RTL {o.i_closing}"
        )
        if o.fire:
            assert e.fired is not None and (e.fired[0], e.fired[1].desc) == (o.out_source, o.out_desc), (
                f"{w}: model fired {e.fired}, pins ({o.out_source}, {o.out_desc:#x})"
            )
            charged = (e.charged.cls, e.charged.fires)
            assert charged == o.charged == ctx_of_bits(o.i_grant_ctx), (
                f"{w}: charged context model {charged} TB {o.charged} RTL {ctx_of_bits(o.i_grant_ctx)}"
            )
            n_f = o.charged[1] + 1
            if o.i_visit_end:
                rtl_event = "expired" if n_f == QUOTA else "emptied"
                if rtl_event == "emptied":
                    assert not o.i_class_live, f"{w}: RTL ended the visit with a live class below quota"
            else:
                rtl_event = "continue"
                assert o.i_class_live and n_f < QUOTA, f"{w}: RTL continued a visit (live={o.i_class_live}, n={n_f})"
            assert e.visit_event == o.visit_event == rtl_event, (
                f"{w}: visit event model {e.visit_event} TB {o.visit_event} RTL {rtl_event}"
            )
            assert (e.visit_after.cls, e.visit_after.fires) == o.visit_after, (
                f"{w}: visit after edge model {e.visit_after} TB {o.visit_after}"
            )
            rel = None if e.relinquished is None else (e.relinquished.cls, e.relinquished.fires)
            assert rel == o.relinquished, f"{w}: relinquished visit model {rel} TB {o.relinquished}"
            rtl_mismatch = (not o.i_cand_valid) or (o.i_cand_source, o.i_cand_ctx) != (o.out_source, o.i_grant_ctx)
            assert e.held_mismatch == rtl_mismatch, f"{w}: model held_mismatch {e.held_mismatch}, RTL {rtl_mismatch}"
            assert o.i_held or not rtl_mismatch, f"{w}: unlocked fire differs from this cycle's candidate"
        else:
            assert e.fired is None and e.visit_event is None and o.visit_event is None
        if o.closing:
            assert list(e.b_close) == o.b_close and e.s_close == o.s_close, (
                f"{w}: closing counts model ({list(e.b_close)}, {e.s_close}) TB ({o.b_close}, {o.s_close})"
            )
            rtl_ev = self._rtl_evidence(o)
            assert list(e.evidence) == o.evidence == rtl_ev, (
                f"{w}: evidence model {list(e.evidence)} TB {o.evidence} RTL {rtl_ev}"
            )
            assert list(e.old_classes) == o.old_cls and list(e.new_classes) == o.new_cls, (
                f"{w}: classes model {list(e.old_classes)}->{list(e.new_classes)} TB {o.old_cls}->{o.new_cls}"
            )
        else:
            assert list(e.new_classes) == list(e.old_classes) == o.i_cls

    # ----- layers 2-4: pins, window/class/visit trackers, scoreboard, responses ---------------------

    def _tracker_vs_rtl(self, o: ObsFai) -> None:
        """Beginning-of-cycle policy state vs the model-free trackers (every cycle, reset or not)."""
        w = f"cycle {o.cycle} [pin trackers]"
        assert o.i_s == sum(o.i_b), f"{w}: s_q={o.i_s} != sum(b_q)={sum(o.i_b)} ({o.i_b})"
        assert all(0 <= b <= o.i_s for b in o.i_b) and o.i_s <= self.w, f"{w}: 0 <= B <= S <= W violated"
        assert o.i_cls == self.pin_cls, f"{w}: cls_q={o.i_cls}, TB evidence/table history {self.pin_cls}"
        assert o.i_idx == self.pin_edges % self.w, (
            f"{w}: idx_q={o.i_idx}, {self.pin_edges} non-reset edges since reset mod W={self.w}"
        )
        assert (o.i_b, o.i_s) == (self.pin_b, self.pin_s), (
            f"{w}: (b_q, s_q)=({o.i_b}, {o.i_s}), pin fires of this window ({self.pin_b}, {self.pin_s})"
        )
        assert (o.i_turn, o.i_used) == (int(self.pin_visit[0] == LOW), self.pin_visit[1]), (
            f"{w}: (turn_q, used_q)=({o.i_turn}, {o.i_used}), pin visit tracker {self.pin_visit}"
        )

    def _pin_checks(self, o: ObsFai, meta: Dict[int, int]) -> None:
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

        occ = [len(x) for x in sb]
        prev = self.prev
        assert o.i_held == int(prev[0] == "stall"), f"{w}: grant_held={o.i_held}, previous cycle was {prev[0]}"
        assert o.i_fire == o.fire, f"{w}: internal fire {o.i_fire} != out_valid & out_ready"
        self._tracker_vs_rtl(o)

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
            cov.reset_mid_window += int(self.pin_edges % self.w != 0)
            cov.reset_mid_visit += int(self.pin_visit[1] > 0)
            cov.reset_non_h += int(any(c != self.interp.reset_state for c in self.pin_cls))
            self._close_epoch()
            # Spec 5 / Q1: a reset edge restores every source to H, the High visit with no fires,
            # window index 0 and B = S = 0; reset edges are not window cycles.
            self._reset_trackers()
            self.prev = ("reset",)
            self.hold_len = 0
            self.hold_windows = 0
            self.valid_ready_low_run = 0
            return
        self.in_reset_run = False

        for h in range(n):
            exp_ready = int(occ[h] < self.depth)
            assert (o.in_ready >> h) & 1 == exp_ready, (
                f"{w}: in_ready[{h}]={(o.in_ready >> h) & 1} with pin-level occupancy {occ[h]}"
            )
            assert occ[h] <= self.depth
        # No control-only bubble (spec 5, 8.3: empty classes are skipped, quota renewal costs no
        # cycle): offered iff anything accepted is still outstanding. A same-cycle push never
        # creates an offer (no bypass).
        assert o.out_valid == int(any(occ)), f"{w}: o_out_valid={o.out_valid} with pin occupancy {occ}"

        nonempty = [h for h in range(n) if occ[h]]
        effective = self.interp.effective
        eff = [effective[c] for c in self.pin_cls]  # class map of THIS cycle
        cov.states_seen.update((h, c) for h, c in enumerate(self.pin_cls))
        offered: Optional[Tuple[str, int]] = None
        if prev[0] == "stall":
            _, p_src, p_desc, p_ctx = prev
            assert o.out_valid == 1 and o.out_source == p_src, (
                f"{w}: stalled offer of source {p_src} not retained (valid={o.out_valid}, source={o.out_source})"
            )
            assert o.out_desc == p_desc, f"{w}: descriptor changed during the stall, diff {o.out_desc ^ p_desc:#029x}"
            assert ctx_of_bits(o.i_grant_ctx) == p_ctx and ctx_of_bits(o.i_held_ctx) == p_ctx, (
                f"{w}: held class/quota context changed: offered {ctx_of_bits(o.i_grant_ctx)}, "
                f"held_ctx_q {ctx_of_bits(o.i_held_ctx)}, retained {p_ctx}"
            )
            offered = p_ctx
        elif o.out_valid:
            # Spec 8.3 / Q2 over the pin history: continue the visit class if it has an eligible
            # head, else open a visit of the other class with a fresh quota. Inside the class the
            # FCFS-oldest head by pin acceptance cycle, ties to the lowest source (spec 6).
            cov.unlocked_offers += 1
            vcls, vused = self.pin_visit
            elig = [h for h in nonempty if eff[h] == vcls]
            if elig:
                offered = (vcls, vused)
            else:
                elig = [h for h in nonempty if eff[h] == other(vcls)]
                offered = (other(vcls), 0)
                cov.class_switch_offers += 1
                cov.switch_relinquish_offers += int(vused > 0)
                cov.closing_continue_then_switch += int(self.continued_at_closing)
            if self.last_visit_end is not None and self.last_visit_end[1] == "expired" and offered == (
                self.last_visit_end[0],
                0,
            ):
                cov.renew_same_class += 1
            self.last_visit_end = None
            heads = sorted((sb[h][0].accept_cycle, h) for h in elig)
            exp_src = heads[0][1]
            assert (o.out_source, ctx_of_bits(o.i_grant_ctx)) == (exp_src, offered), (
                f"{w}: offered (source, ctx)=({o.out_source}, {ctx_of_bits(o.i_grant_ctx)}); pin history: "
                f"visit {self.pin_visit}, classes {self.pin_cls}, eligible heads (accept cycle, source) {heads} "
                f"-> ({exp_src}, {offered})"
            )
            oldest = heads[0][0]
            cov.ties_in_class += int(sum(1 for c, _h in heads if c == oldest) > 1)
            cov.older_beats_lower_in_class += int(exp_src > min(elig))
            others = [sb[h][0].accept_cycle for h in nonempty if h not in elig]
            cov.class_over_age += int(bool(others) and min(others) < oldest)
            ts_sel = o.i_head_ts[exp_src]
            cov.wrap_discriminating += int(any(o.i_head_ts[h] < ts_sel for h in elig if h != exp_src))
        else:
            cov.idle_cycles += 1
            cov.idle_visit_open += int(self.pin_visit[1] > 0)
            cov.idle_turn_low += int(self.pin_visit[0] == LOW)
        self.continued_at_closing = False if o.out_valid else self.continued_at_closing
        o.offered_ctx = offered
        if o.out_valid:
            src = o.out_source
            assert occ[src] > 0, f"{w}: offered source {src} has no outstanding accepted descriptor"
            assert o.out_desc == sb[src][0].desc, (
                f"{w}: o_out_desc is not the oldest accepted descriptor of source {src} (sideband/order/integrity), "
                f"diff {o.out_desc ^ sb[src][0].desc:#029x}"
            )

        pos = self.pin_edges % self.w
        o.pos = pos
        closing = pos == self.w - 1
        if o.out_valid and not o.out_ready and closing:
            cov.held_across_closing += 1
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
        post = [len(x) for x in sb]  # pin-level post-edge occupancy (pushes and the pop included)

        # Visit / quota (spec 8.3 Q2, fai_main.md 4): only a fire, charged to the offered context.
        if o.fire:
            g = o.out_source
            vcls, vused = self.pin_visit
            assert offered in ((vcls, vused), (other(vcls), 0)), f"{w}: charged {offered} vs open visit {self.pin_visit}"
            o.charged = offered
            if offered != self.pin_visit and vused > 0:
                o.relinquished = self.pin_visit
                cov.visits_relinquished += 1
            n_f = offered[1] + 1
            assert 1 <= n_f <= QUOTA, f"{w}: {n_f} fires charged to one visit"
            live = any(eff[h] == offered[0] and post[h] > 0 for h in range(n))
            if n_f == QUOTA:
                o.visit_event = "expired"
                cov.visits_expired += 1
                cov.visits_expired_replaced += (o.push >> g) & 1
                cov.visits_expired_live += int(live)
            elif not live:
                o.visit_event = "emptied"
                cov.visits_emptied += 1
            else:
                o.visit_event = "continue"
                cov.visits_continue += 1
            if o.visit_event == "continue":
                self.pin_visit = (offered[0], n_f)
            else:
                cov.fires_per_visit[n_f] += 1
                self.pin_visit = (other(offered[0]), 0)
                self.last_visit_end = (offered[0], o.visit_event)
            o.visit_after = self.pin_visit
            if offered[0] == LOW:
                cov.fires_low += 1
            else:
                cov.fires_high += 1
            cov.held_fire_cls_differs += int(bool(o.i_held) and offered[0] != eff[g])

        # Window accounting (spec 8.1, 8.4, Q3): every non-reset edge is a window cycle.
        if o.fire:
            self.pin_b[o.out_source] += 1
            self.pin_s += 1
        cov.max_b = max(cov.max_b, max(self.pin_b))
        cov.max_s = max(cov.max_s, self.pin_s)
        if closing:
            o.closing = True
            o.b_close = list(self.pin_b)
            o.s_close = self.pin_s
            o.evidence = [spec_evidence(n, b, self.pin_s) for b in self.pin_b]
            o.old_cls = list(self.pin_cls)
            o.new_cls = [self.interp.table[c][ev] for c, ev in zip(self.pin_cls, o.evidence)]
            cov.windows_closed += 1
            cov.closing_fire += o.fire
            for h in range(n):
                key = f"{o.old_cls[h]}/{o.evidence[h]}"
                cov.transitions[key] += 1
                cov.transitions_seen.add((h, o.old_cls[h], o.evidence[h]))
                cov.evidence[o.evidence[h]] += 1
                cov.effective_changes += int(effective[o.old_cls[h]] != effective[o.new_cls[h]])
            if o.out_valid and not o.out_ready:
                src = o.out_source
                cov.held_cls_change += int(effective[o.old_cls[src]] != effective[o.new_cls[src]])
                self.hold_windows += 1
                cov.max_windows_in_hold = max(cov.max_windows_in_hold, self.hold_windows)
            if o.fire:
                # Derived convention (fai_main.md 4): class_live of the closing edge used the
                # class map of the closing cycle; record where the new map would differ.
                new_eff = [effective[c] for c in o.new_cls]
                live_new = any(new_eff[h] == o.charged[0] and post[h] > 0 for h in range(n))
                live_old = any(eff[h] == o.charged[0] and post[h] > 0 for h in range(n))
                cov.closing_live_differs += int(live_new != live_old)
                self.continued_at_closing = o.visit_event == "continue"
            self.pin_cls = o.new_cls
            self.pin_b = [0] * n
            self.pin_s = 0
        self.pin_edges += 1
        if not o.out_valid or o.fire:
            self.hold_windows = 0

        if o.fire:
            src = o.out_source
            refused = src if (occ[src] == self.depth and (o.in_valid >> src) & 1) else None
            self.prev = ("fire", src, refused)
        elif o.out_valid:
            self.prev = ("stall", o.out_source, o.out_desc, offered)
        else:
            self.prev = ("idle",)

    def _coverage(self, o: ObsFai, prev: tuple, occ: List[int], nonempty: List[int]) -> None:
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


def fai_summary(cov: dict, window: int) -> dict:
    """FAI window/class/visit statistics of a coverage snapshot (JSON-ready)."""
    return {
        "window": window,
        "windows_closed": cov["windows_closed"],
        "closing_edges_with_fire": cov["closing_fire"],
        "evidence": cov["evidence"],
        "transitions": cov["transitions"],
        "transitions_reached": cov["transitions_reached"],
        "states_reached": cov["states_reached"],
        "effective_class_changes": cov["effective_changes"],
        "held_across_closing": cov["held_across_closing"],
        "held_class_change_at_closing": cov["held_cls_change"],
        "held_fire_retained_class_differs": cov["held_fire_cls_differs"],
        "max_windows_in_one_hold": cov["max_windows_in_hold"],
        "closing_live_convention_differs": cov["closing_live_differs"],
        "visits": {
            "continue": cov["visits_continue"],
            "expired": cov["visits_expired"],
            "expired_with_replacement_push": cov["visits_expired_replaced"],
            "expired_class_still_live": cov["visits_expired_live"],
            "emptied": cov["visits_emptied"],
            "relinquished": cov["visits_relinquished"],
            "renew_same_class": cov["renew_same_class"],
            "class_switch_offers": cov["class_switch_offers"],
            "fires_per_ended_visit_histogram": cov["fires_per_visit"],
        },
        "fires_high": cov["fires_high"],
        "fires_low": cov["fires_low"],
        "max_b": cov["max_b"],
        "max_s": cov["max_s"],
        "ties_in_class": cov["ties_in_class"],
        "class_over_age": cov["class_over_age"],
    }
