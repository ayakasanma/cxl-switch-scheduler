"""Independent cycle-level models of the revision-study baselines (2026-10-23).

Authority: specs/CXL_SPEC.md v1.0 sections 4, 5, 6, 8.1-8.5 (shared FIFO/hold/FCFS/window
contract) and docs/experiments/revision-20261023/{METHOD_DIFFERENCES,BASELINES}.md (adaptation
rules). These models are experiment oracles for rtl/experimental/switch_experiment_top.sv; they do
not replace or modify the accepted models, which remain the oracles for POLICY 0-3 at their
accepted parameters.

Reused unchanged: ``CommonCtrlModel`` (queues + held grant), FCFS absolute-time ordering
convention, the Main spec 8.1 evidence (``threshold_evidence``), the literal spec 8.2 table
(``MAIN_TRANSITIONS``), window widths and the 32-bit operand checks of ``fai_main_model``.

Two models, same ``view(out_ready, rst_n)`` / ``commit(out_ready, in_valid, in_desc, rst_n)``
convention as the accepted switch models (view = cycle c from beginning-of-cycle state, commit =
its closing edge, visible from c+1; a reset edge clears everything; before the first reset edge the
state is unknown and a non-reset edge is rejected):

``BlissSwitchModel`` - BLISS-inspired descriptor scheduler (POLICY=4)
  * candidate: among nonempty heads, the non-blacklisted ones if any exist, else all of them;
    within that group the oldest absolute arrival edge, lowest source ID on ties;
  * streak, only on a fire of source g: no previous source or g != last -> count = 0;
    g == last -> count + 1; if the new count exceeds THRESHOLD (4) g is blacklisted and the count
    becomes 0; last = g. Idle, stall and held cycles change nothing;
  * clear: the CLEAR_INTERVAL-th (10000-th) non-reset edge after the last clear/reset empties the
    blacklist. A clear wins over a same-edge new blacklisting; last/count are still updated;
  * the blacklist read by the candidate is the beginning-of-cycle one; a held grant is replayed by
    the common controller and never altered by a blacklist set or clear.

``FaiVariantSwitchModel`` - FAI-inspired Main with experimental variants (POLICY=2)
  * HIGH quota 5 / 10 / 20 fires per High visit, Low quota fixed at 10;
  * ``main_1w``: closing-edge classification UP -> 'H', DOWN -> 'L', KEEP/S0 -> stable state of the
    current effective class (no pending Buffer state); otherwise the literal spec 8.2 table;
  * everything else (candidate, fire-only charging to the retained context of the grant actually
    fired, class_live from post-edge occupancy and this cycle's class map, window/B/S/closing fire
    inclusion) as the accepted Main contract. ``high_quota=10, main_1w=False`` is the accepted Main
    policy; test_baseline_models.py checks that it equals ``FaiMainSwitchModel`` edge by edge.

The ONLY RTL-facing facts are isolated in ``variant_ctx_bits``/``variant_ctx_to_hw``
(context layout {class, used}) and documented in sim/experimental/test_experiment_top.py (state
register encodings). Nothing here was derived from RTL control code.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, NamedTuple, Optional, Sequence, Tuple

from .common_ctrl_model import NO_CANDIDATE, Candidate, CommonCtrlModel, CtrlEdge, CtrlView
from .fai_main_model import (
    EFFECTIVE_CLASS,
    EVIDENCES,
    FAI_W_PRODUCTION,
    HIGH,
    LOW,
    MAIN_TRANSITIONS,
    FaiCtx,
    FaiVisitRecord,
    FaiWindowClose,
    check_threshold_operands,
    other_class,
    threshold_evidence,
    window_widths,
)
from .fcfs_model import MAX_OUTSTANDING_AGE, FcfsEntry
from .fifo_model import DESC_WIDTH, FIFO_DEPTH, TS_WIDTH

BLISS_THRESHOLD = 4
BLISS_CLEAR_INTERVAL = 10_000

LOW_QUOTA = 10
HIGH_QUOTAS = (5, 10, 20)

# Main-1W: UP/DOWN settle immediately; KEEP and the zero-service window retain the effective class
# as a stable state. Defined for all four Main states so that it is total.
MAIN_1W_TRANSITIONS: Dict[Tuple[str, str], str] = {
    (s, e): ("H" if e == "UP" else "L" if e == "DOWN" else ("H" if EFFECTIVE_CLASS[s] == HIGH else "L"))
    for s in ("H", "B_H", "L", "B_L")
    for e in EVIDENCES
}


class _ArrivalSwitch:
    """Queues + held grant + absolute arrival bookkeeping + 32-bit stored-timestamp tracking."""

    def __init__(self, n_src: int, depth: int, ctx_width: int, desc_width: int, ts_width: int) -> None:
        if n_src < 2:
            raise ValueError("n_src must be at least 2")
        self.n_src = n_src
        self.depth = depth
        self.ts_width = ts_width
        self.ts_mask = (1 << ts_width) - 1
        self.ctrl = CommonCtrlModel(n_src, depth, True, ctx_width, desc_width, ts_width)
        self._arrival: List[Deque[int]] = [deque() for _ in range(n_src)]
        self.edge_index = 0  # absolute index of the NEXT edge to be committed
        self.epoch = 0
        self.state_known = False
        self.counter_init = 0
        self.edges_since_reset = 0

    @property
    def held(self) -> Optional[int]:
        held = self.ctrl.held
        return None if held is None else held.source

    def occupancy(self, source: int) -> int:
        return self.ctrl.occupancy(source)

    def nonempty_sources(self) -> List[int]:
        return self.ctrl.nonempty_sources()

    def counter(self) -> Optional[int]:
        if not self.state_known:
            return None
        return (self.counter_init + self.edges_since_reset) & self.ts_mask

    def queue(self, source: int) -> List[FcfsEntry]:
        entries = self.ctrl.fifos[source].entries()
        return [FcfsEntry(e.desc, a, e.ts) for e, a in zip(entries, self._arrival[source])]

    def _oldest(self, sources) -> Optional[int]:
        keyed = [(self._arrival[h][0], h) for h in sources]
        return min(keyed)[1] if keyed else None

    def deposit_counter(self, value: int) -> None:
        """Mirror a simulation-only deposit of the arrival counter (first post-reset cycle only,
        every queue empty, no held grant). Ordering is unaffected: it uses absolute time."""
        if not 0 <= value <= self.ts_mask:
            raise ValueError(f"counter value {value:#x} does not fit in {self.ts_width} bits")
        if not self.state_known or self.edges_since_reset != 0:
            raise ValueError("deposit only in the first cycle after a reset edge")
        if self.ctrl.nonempty_sources() or self.ctrl.held is not None:
            raise ValueError("deposit only with every queue empty and no held grant")
        self.counter_init = value

    def _check_environment(self) -> None:
        for h in range(self.n_src):
            if self._arrival[h] and self.edge_index - self._arrival[h][0] >= MAX_OUTSTANDING_AGE:
                raise AssertionError(f"environment assumption violated: source {h} head too old (spec 6)")

    def _reset_edge(self, out_ready: bool) -> CtrlEdge:
        edge = self.ctrl.commit(NO_CANDIDATE, out_ready, None, None, None, rst_n=False)
        for q in self._arrival:
            q.clear()
        self.epoch += 1
        self.counter_init = 0
        self.edges_since_reset = 0
        self.state_known = True
        return edge

    def _data_edge(self, cand: Candidate, out_ready, in_valid, in_desc, this_edge: int):
        """Commit queues/hold for a non-reset edge; returns (ctrl_edge, fired source, begin occ)."""
        begin_occ = [self.ctrl.occupancy(h) for h in range(self.n_src)]
        edge = self.ctrl.commit(cand, out_ready, in_valid, in_desc, self.counter(), rst_n=True)
        g = None
        if edge.fired is not None:
            g = edge.fired.source
            self._arrival[g].popleft()
        for h, e in enumerate(edge.pushed):
            if e is not None:
                self._arrival[h].append(this_edge)
            if len(self._arrival[h]) != self.ctrl.occupancy(h):
                raise AssertionError("arrival bookkeeping mismatch")
        self.edges_since_reset += 1
        return edge, g, begin_occ


# ===================================================================================================
# BLISS-inspired descriptor scheduler
# ===================================================================================================


class BlissEdge(NamedTuple):
    reset: bool
    edge_index: int
    fired: Optional[int]  # source that fired at this edge
    streak_after: int
    blacklisted: Optional[int]  # source whose streak exceeded the threshold at this edge
    blacklist_applied: bool  # False when a same-edge clear discarded it
    cleared: bool  # this edge was a clearing edge
    candidate: Candidate
    latched: Optional[int]
    released: bool


class BlissSwitchModel(_ArrivalSwitch):
    def __init__(
        self,
        n_src: int,
        depth: int = FIFO_DEPTH,
        threshold: int = BLISS_THRESHOLD,
        clear_interval: int = BLISS_CLEAR_INTERVAL,
        desc_width: int = DESC_WIDTH,
        ts_width: int = TS_WIDTH,
    ) -> None:
        if threshold < 1 or clear_interval < 2:
            raise ValueError("threshold >= 1 and clear_interval >= 2 required")
        super().__init__(n_src, depth, 1, desc_width, ts_width)
        self.threshold = threshold
        self.clear_interval = clear_interval
        self.blacklist_events = 0  # streak overflows (applied or discarded), current epoch
        self.discarded_blacklists = 0  # overflows on a clearing edge
        self.clears = 0
        self.service: List[int] = [0] * n_src
        self._reset_policy()

    def _reset_policy(self) -> None:
        self.blacklist: List[bool] = [False] * self.n_src
        self.last: Optional[int] = None
        self.streak = 0
        self.since_clear = 0  # non-reset edges since the last clear or reset
        self.blacklist_events = self.discarded_blacklists = self.clears = 0
        self.service = [0] * self.n_src

    # ----- observation ---------------------------------------------------------------------------

    def bliss_state(self) -> Optional[Tuple[Tuple[bool, ...], Optional[int], int, int]]:
        """(blacklist per source, last serviced source or None, streak, edges since last clear)."""
        if not self.state_known:
            return None
        return tuple(self.blacklist), self.last, self.streak, self.since_clear

    def candidate(self) -> Candidate:
        if not self.state_known:
            return NO_CANDIDATE
        active = self.ctrl.nonempty_sources()
        preferred = [h for h in active if not self.blacklist[h]]
        src = self._oldest(preferred or active)
        return NO_CANDIDATE if src is None else Candidate(True, src, 0)

    def view(self, out_ready: bool = False, rst_n: bool = True) -> CtrlView:
        self._check_environment()
        return self.ctrl.view(self.candidate(), out_ready, rst_n)

    # ----- closing edge ----------------------------------------------------------------------------

    def commit(
        self,
        out_ready: bool = False,
        in_valid: Optional[Sequence[bool]] = None,
        in_desc: Optional[Sequence[int]] = None,
        rst_n: bool = True,
    ) -> BlissEdge:
        this_edge = self.edge_index
        if not rst_n:
            self.edge_index += 1
            edge = self._reset_edge(out_ready)
            self._reset_policy()
            return BlissEdge(True, this_edge, None, 0, None, False, False, NO_CANDIDATE, None, edge.released)
        if not self.state_known:
            raise AssertionError("non-reset edge before the first reset edge: BLISS state is unknown")
        self._check_environment()
        self.edge_index += 1
        cand = self.candidate()
        held_before = self.held
        edge, g, _ = self._data_edge(cand, out_ready, in_valid, in_desc, this_edge)

        new_bl = None
        if g is not None:
            expected = held_before if held_before is not None else cand.source
            if g != expected:
                raise AssertionError(f"source {g} fired but the offered grant was {expected}")
            self.service[g] += 1
            self.streak = self.streak + 1 if self.last is not None and g == self.last else 0
            self.last = g
            if self.streak > self.threshold:
                new_bl = g
                self.streak = 0
                self.blacklist_events += 1

        self.since_clear += 1
        cleared = self.since_clear == self.clear_interval
        if cleared:
            self.blacklist = [False] * self.n_src
            self.since_clear = 0
            self.clears += 1
            if new_bl is not None:
                self.discarded_blacklists += 1
        elif new_bl is not None:
            self.blacklist[new_bl] = True
        latched = None if edge.latched is None else edge.latched.source
        return BlissEdge(False, this_edge, g, self.streak, new_bl, new_bl is not None and not cleared,
                         cleared, cand, latched, edge.released)  # fmt: skip


# ===================================================================================================
# FAI-inspired Main variants (High quota sweep, Main-1W)
# ===================================================================================================


def variant_ctx_bits(high_quota: int) -> int:
    """Width of the 'used' field: enough for 0..max(High, Low quota)-1."""
    return (max(high_quota, LOW_QUOTA) - 1).bit_length()


# RTL-FACING FACT: variant grant context = {class bit (0 High, 1 Low), used[USED_W-1:0]}.
def variant_ctx_to_hw(ctx: FaiCtx, high_quota: int) -> int:
    used_w = variant_ctx_bits(high_quota)
    return ((0 if ctx.cls == HIGH else 1) << used_w) | ctx.fires


def variant_ctx_from_hw(bits: int, high_quota: int) -> FaiCtx:
    used_w = variant_ctx_bits(high_quota)
    if not 0 <= bits < (1 << (used_w + 1)):
        raise ValueError(f"context {bits:#x} wider than {used_w + 1} bits")
    ctx = FaiCtx(LOW if bits >> used_w else HIGH, bits & ((1 << used_w) - 1))
    quota = high_quota if ctx.cls == HIGH else LOW_QUOTA
    if ctx.fires >= quota:
        raise ValueError(f"context {ctx} has used >= quota {quota}")
    return ctx


class FaiVariantSwitchModel(_ArrivalSwitch):
    def __init__(
        self,
        n_src: int,
        window: int = FAI_W_PRODUCTION,
        depth: int = FIFO_DEPTH,
        high_quota: int = 10,
        main_1w: bool = False,
        desc_width: int = DESC_WIDTH,
        ts_width: int = TS_WIDTH,
    ) -> None:
        if high_quota not in HIGH_QUOTAS:
            raise ValueError(f"high_quota {high_quota} not in {HIGH_QUOTAS}")
        self.idx_bits, self.count_bits = window_widths(window)
        self.high_quota = high_quota
        self.main_1w = bool(main_1w)
        self.transitions = MAIN_1W_TRANSITIONS if self.main_1w else MAIN_TRANSITIONS
        self.ctx_width = variant_ctx_bits(high_quota) + 1
        super().__init__(n_src, depth, self.ctx_width, desc_width, ts_width)
        self.window = window
        self.visit_log: List[FaiVisitRecord] = []
        self.window_log: List[FaiWindowClose] = []
        self._reset_policy()

    def quota(self, cls: str) -> int:
        return self.high_quota if cls == HIGH else LOW_QUOTA

    def _reset_policy(self) -> None:
        n = self.n_src
        self.cls: List[str] = ["H"] * n
        self.visit = FaiCtx(HIGH, 0)
        self.win_pos = 0
        self.b: List[int] = [0] * n
        self.s = 0
        self.windows_closed = 0
        self.service: List[int] = [0] * n

    # ----- observation ---------------------------------------------------------------------------

    def classes(self) -> Optional[Tuple[str, ...]]:
        return tuple(self.cls) if self.state_known else None

    def effective_classes(self) -> Optional[Tuple[str, ...]]:
        return tuple(EFFECTIVE_CLASS[c] for c in self.cls) if self.state_known else None

    def window_state(self) -> Optional[Tuple[int, Tuple[int, ...], int]]:
        return (self.win_pos, tuple(self.b), self.s) if self.state_known else None

    def visit_state(self) -> Optional[FaiCtx]:
        return self.visit if self.state_known else None

    def held_grant(self) -> Optional[Tuple[int, FaiCtx]]:
        held = self.ctrl.held
        return None if held is None else (held.source, variant_ctx_from_hw(held.ctx, self.high_quota))

    def _oldest_in(self, cls: str) -> Optional[int]:
        return self._oldest(h for h in range(self.n_src) if self._arrival[h] and EFFECTIVE_CLASS[self.cls[h]] == cls)

    def fai_candidate(self) -> Optional[Tuple[int, FaiCtx]]:
        if not self.state_known:
            return None
        src = self._oldest_in(self.visit.cls)
        if src is not None:
            return src, self.visit
        other = other_class(self.visit.cls)
        src = self._oldest_in(other)
        return None if src is None else (src, FaiCtx(other, 0))

    def candidate(self) -> Candidate:
        c = self.fai_candidate()
        return NO_CANDIDATE if c is None else Candidate(True, c[0], variant_ctx_to_hw(c[1], self.high_quota))

    def view(self, out_ready: bool = False, rst_n: bool = True) -> CtrlView:
        self._check_environment()
        return self.ctrl.view(self.candidate(), out_ready, rst_n)

    # ----- closing edge ----------------------------------------------------------------------------

    def commit(
        self,
        out_ready: bool = False,
        in_valid: Optional[Sequence[bool]] = None,
        in_desc: Optional[Sequence[int]] = None,
        rst_n: bool = True,
    ) -> dict:
        n = self.n_src
        this_edge = self.edge_index
        if not rst_n:
            self.edge_index += 1
            edge = self._reset_edge(out_ready)
            self._reset_policy()
            return dict(reset=True, edge_index=this_edge, released=edge.released)
        if not self.state_known:
            raise AssertionError("non-reset edge before the first reset edge: FAI state is unknown")
        self._check_environment()
        self.edge_index += 1

        cand = self.fai_candidate()
        held_before = self.held_grant()
        eff = [EFFECTIVE_CLASS[c] for c in self.cls]  # class map of this cycle
        pos = self.win_pos
        edge, g, begin_occ = self._data_edge(self.candidate(), out_ready, in_valid, in_desc, this_edge)

        charged = event = None
        if g is not None:
            charged = variant_ctx_from_hw(edge.fired.ctx, self.high_quota)
            expected = held_before if held_before is not None else cand
            if (g, charged) != expected:
                raise AssertionError(f"fired grant {(g, charged)} is neither the held grant nor the candidate")
            if charged != self.visit and charged != FaiCtx(other_class(self.visit.cls), 0):
                raise AssertionError(f"charged context {charged} inconsistent with open visit {self.visit}")
            if charged != self.visit and self.visit.fires > 0:
                self.visit_log.append(FaiVisitRecord(self.epoch, self.visit.cls, self.visit.fires,
                                                     "relinquished", this_edge))  # fmt: skip
            self.service[g] += 1
            post = [begin_occ[h] + int(edge.pushed[h] is not None) - int(h == g) for h in range(n)]
            n_fires = charged.fires + 1
            class_live = any(eff[h] == charged.cls and post[h] > 0 for h in range(n))
            event = "expired" if n_fires == self.quota(charged.cls) else "continue" if class_live else "emptied"
            if event == "continue":
                self.visit = FaiCtx(charged.cls, n_fires)
            else:
                self.visit = FaiCtx(other_class(charged.cls), 0)
                self.visit_log.append(FaiVisitRecord(self.epoch, charged.cls, n_fires, event, this_edge))
            self.b[g] += 1
            self.s += 1

        closing = pos == self.window - 1
        if closing:
            for b in self.b:
                check_threshold_operands(n, self.window, b, self.s)
            evidence = tuple(threshold_evidence(n, b, self.s) for b in self.b)
            old = tuple(self.cls)
            self.cls = [self.transitions[(old[h], evidence[h])] for h in range(n)]
            self.window_log.append(FaiWindowClose(self.epoch, this_edge, self.windows_closed, tuple(self.b),
                                                  self.s, evidence, old, tuple(self.cls)))  # fmt: skip
            self.windows_closed += 1
            self.b = [0] * n
            self.s = 0
            self.win_pos = 0
        else:
            self.win_pos += 1
        if self.s != sum(self.b):
            raise AssertionError("S != sum(B)")
        latched = None
        if edge.latched is not None:
            latched = (edge.latched.source, variant_ctx_from_hw(edge.latched.ctx, self.high_quota))
        return dict(reset=False, edge_index=this_edge, window_pos=pos, fired=g, charged=charged,
                    visit_event=event, visit_after=self.visit, closing=closing, latched=latched,
                    released=edge.released)  # fmt: skip
