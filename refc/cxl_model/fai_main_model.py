"""Abstract cycle-level model of the complete switch under the FAI-inspired Main policy (POLICY=2).

Authority: specs/CXL_SPEC.md v1.0 sections 4, 5, 6 and 8.1-8.5, and the implementation derivation
docs/phase-3-uarch/fai_main.md sections 2-4. Algorithm-2 (spec 8.6) is NOT modelled here; it is
the separate ``fai_alg2_model``, which reuses these mechanics through the three-attribute
interpretation hook of ``FaiMainSwitchModel`` (Main values are the defaults).

Independence: this module was written from the spec contract and fai_main.md only. The FAI RTL
(rtl/common/cxl_fai_main_sched.sv and the FAI branch of rtl/top/switch_top.sv) was NOT read. The
single RTL-facing fact used is the 5-bit layout of the grant context, isolated in ``ctx_to_hw``.

State is deliberately abstract (no registers, no bit widths in the policy):

* queues + held grant: the reviewed ``CommonCtrlModel`` with arrival metadata enabled;
* arrival order: each entry's unbounded absolute push-edge index (``edge_index`` of the push edge,
  counting every committed edge) - the per-class oldest head is ``min((arrival, source))``. The
  32-bit stored timestamp is tracked only as an observation and never orders anything;
* per-source class: one of the names ``'H' 'B_H' 'L' 'B_L'``; effective class ``'High'``/``'Low'``;
* window: position, ``B`` per source and ``S`` as unbounded Python ints;
* the open visit: ``FaiCtx(cls, fires)`` = class of the current visit and fires already charged.

Cycle convention as in the other models: ``view()`` describes cycle *c* from beginning-of-cycle state,
``commit()`` applies its closing edge; effects become visible in cycle *c+1*.

Contract modelled (fai_main.md 2-4, spec 8.1-8.4):

1. Reset edge: queues empty, held grant dropped, arrival counter 0, every source 'H', visit
   ('High', 0), window position 0, B = 0, S = 0. Before the first reset edge the state is unknown:
   there is no candidate and a non-reset edge is rejected.
2. Candidate (beginning-of-cycle state only): if the visit class has a nonempty head, the
   FCFS-oldest head of that class with context (visit class, visit fires); otherwise, if the other
   class has a nonempty head, the FCFS-oldest head of the other class with context (other, 0) - a
   new visit with a fresh quota; otherwise none. Never depends on ready/fire/pop of the cycle.
3. Only a fire is service, charged to the ACTUAL fired grant's retained context (a held grant keeps
   the context it was latched with). With n = fires + 1 and ``class_live`` = some source whose
   effective class in THIS cycle's class map equals the charged class has post-edge occupancy > 0:
   n == 10 -> 'expired'; else not class_live -> 'emptied'; both switch the visit to (other, 0);
   otherwise 'continue' with (class, n). Without a fire the visit is unchanged.
4. Window: every non-reset edge (stalls, idle and held cycles included) is a window cycle. A fire
   adds 1 to B[fired source] and S. On the closing edge (pre-edge position W-1) the closing fire is
   included, every source is classified in parallel from (B_close, S_close) and its current state
   via the literal spec 8.2 table, then B, S and the position clear. The new classes are visible
   from the next cycle; the visit/held grant are not touched by a closing. ``class_live`` of the
   closing edge uses the closing cycle's class map (fai_main.md 4 "Derived convention").
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, NamedTuple, Optional, Sequence, Tuple

from .common_ctrl_model import NO_CANDIDATE, Candidate, CommonCtrlModel, CtrlEdge, CtrlView
from .fcfs_model import MAX_OUTSTANDING_AGE, FcfsEntry
from .fifo_model import DESC_WIDTH, FIFO_DEPTH, TS_WIDTH

HIGH = "High"
LOW = "Low"
CLASS_STATES = ("H", "B_H", "L", "B_L")
EFFECTIVE_CLASS: Dict[str, str] = {"H": HIGH, "B_H": HIGH, "L": LOW, "B_L": LOW}
EVIDENCES = ("UP", "DOWN", "KEEP", "S0")

# Spec 8.2 table, copied literally: (current state, evidence) -> next state. "S0" = S == 0 column.
MAIN_TRANSITIONS: Dict[Tuple[str, str], str] = {
    ("H", "UP"): "H",    ("H", "DOWN"): "B_H",   ("H", "KEEP"): "H",   ("H", "S0"): "H",
    ("B_H", "UP"): "H",  ("B_H", "DOWN"): "L",   ("B_H", "KEEP"): "H", ("B_H", "S0"): "H",
    ("L", "UP"): "B_L",  ("L", "DOWN"): "L",     ("L", "KEEP"): "L",   ("L", "S0"): "L",
    ("B_L", "UP"): "H",  ("B_L", "DOWN"): "L",   ("B_L", "KEEP"): "L", ("B_L", "S0"): "L",
}  # fmt: skip

FAI_QUOTA = 10  # successful fires per visit, High and Low alike (spec 8.3)
FAI_W_PRODUCTION = 5_000_000
FAI_W_STRESS = (64, 256)
FAI_SUPPORTED_WINDOWS = (64, 256, FAI_W_PRODUCTION)
THRESHOLD_BITS = 32  # common unsigned representation of the threshold intermediates (spec 8.5)


def other_class(cls: str) -> str:
    if cls == HIGH:
        return LOW
    if cls == LOW:
        return HIGH
    raise ValueError(f"unknown effective class {cls!r}")


class FaiCtx(NamedTuple):
    """Abstract class/quota context: visit class and fires already charged to it (0..9)."""

    cls: str
    fires: int


def check_ctx(ctx: FaiCtx) -> None:
    if ctx.cls not in (HIGH, LOW):
        raise ValueError(f"context class {ctx.cls!r} is not 'High'/'Low'")
    if not (isinstance(ctx.fires, int) and 0 <= ctx.fires < FAI_QUOTA):
        raise ValueError(f"context fires {ctx.fires!r} outside 0..{FAI_QUOTA - 1}")


ALL_CONTEXTS: Tuple[FaiCtx, ...] = tuple(FaiCtx(c, f) for c in (HIGH, LOW) for f in range(FAI_QUOTA))

# ===================================================================================================
# RTL-FACING FACT (the only one this model uses): the 5-bit hardware grant context is
#   bit [4]   = class (0 = High, 1 = Low)
#   bits[3:0] = fires already charged to the visit (0..9)
# Everything else in this module is abstract. ``ctx_from_hw`` is defined as the exact inverse of
# this one function over the 20 valid contexts, so the layout lives in exactly one place.
HW_CTX_WIDTH = 5


def ctx_to_hw(ctx: FaiCtx) -> int:
    """Map an abstract context to the 5-bit hardware context {class bit, fires[3:0]}."""
    check_ctx(ctx)
    return ((0 if ctx.cls == HIGH else 1) << 4) | ctx.fires


# ===================================================================================================

_HW_TO_CTX: Dict[int, FaiCtx] = {ctx_to_hw(c): c for c in ALL_CONTEXTS}


def ctx_from_hw(bits: int) -> FaiCtx:
    """Inverse of ``ctx_to_hw``; rejects encodings that no valid context produces."""
    if bits not in _HW_TO_CTX:
        raise ValueError(f"hardware context {bits!r} is not the encoding of a valid FAI context")
    return _HW_TO_CTX[bits]


# ----- window arithmetic (pure functions) -----------------------------------------------------------


def window_widths(window: int) -> Tuple[int, int]:
    """(index bits, B/S bits) = (ceil(log2 W), ceil(log2(W+1))) for a supported window."""
    if window not in FAI_SUPPORTED_WINDOWS:
        raise ValueError(f"window {window} not supported (allowed: {FAI_SUPPORTED_WINDOWS})")
    return (window - 1).bit_length(), window.bit_length()


def threshold_evidence(n_src: int, b: int, s: int) -> str:
    """Spec 8.1 evidence from closing counts, exact unbounded integer arithmetic.

    UP iff 10*N*B < 3*S; DOWN iff N*B > S; KEEP otherwise (equality included). S == 0 is the
    explicit no-service column 'S0' (then B == 0 and it coincides with KEEP).
    """
    if not (isinstance(n_src, int) and isinstance(b, int) and isinstance(s, int)):
        raise TypeError("threshold operands must be integers")
    if n_src < 1 or b < 0 or s < b:
        raise ValueError(f"invalid threshold operands N={n_src} B={b} S={s} (need 0 <= B <= S)")
    if s == 0:
        return "S0"
    up = (10 * n_src) * b < 3 * s
    down = n_src * b > s
    if up and down:
        raise AssertionError(f"UP and DOWN both hold for N={n_src} B={b} S={s}")
    return "UP" if up else "DOWN" if down else "KEEP"


def check_threshold_operands(n_src: int, window: int, b: int, s: int) -> None:
    """Assert the production/stress representation bounds of one classification (spec 8.5).

    0 <= B <= S <= W; B and S fit the parameter-derived counter width (23 bits at W=5,000,000);
    10*N*B and 3*S fit the 32-bit unsigned threshold representation. Raises AssertionError.
    """
    _, cnt_bits = window_widths(window)
    if not 0 <= b <= s <= window:
        raise AssertionError(f"count bound violated: need 0 <= B={b} <= S={s} <= W={window}")
    if b >= (1 << cnt_bits) or s >= (1 << cnt_bits):
        raise AssertionError(f"B={b}/S={s} do not fit the {cnt_bits}-bit counters of W={window}")
    if (10 * n_src) * b >= (1 << THRESHOLD_BITS) or 3 * s >= (1 << THRESHOLD_BITS):
        raise AssertionError(f"threshold product overflows {THRESHOLD_BITS} bits (N={n_src} B={b} S={s})")


# ----- records ---------------------------------------------------------------------------------------


class FaiCandidate(NamedTuple):
    """Policy candidate of one cycle; ``source``/``ctx`` are None when ``valid`` is false."""

    valid: bool
    source: Optional[int]
    ctx: Optional[FaiCtx]


NO_FAI_CANDIDATE = FaiCandidate(False, None, None)


class FaiVisitRecord(NamedTuple):
    """A finished visit (only visits with at least one fire are recorded)."""

    epoch: int
    cls: str
    fires: int
    reason: str  # "expired" | "emptied" | "relinquished" (left open, other class opened a new visit)
    end_edge: int  # edge that ended it (for "relinquished": the fire of the next visit)


class FaiWindowClose(NamedTuple):
    epoch: int
    edge_index: int
    window: int  # window number within the epoch, 0-based
    b_close: Tuple[int, ...]
    s_close: int
    evidence: Tuple[str, ...]
    old_classes: Tuple[str, ...]
    new_classes: Tuple[str, ...]


class FaiEdge(NamedTuple):
    reset: bool
    edge_index: int
    window_pos: Optional[int]  # pre-edge window position (None on reset edges)
    pushed: Tuple[Optional[FcfsEntry], ...]
    fired: Optional[Tuple[int, FcfsEntry]]  # (source, entry) delivered at this edge
    charged: Optional[FaiCtx]  # retained context the fire was charged to
    visit_event: Optional[str]  # None | "continue" | "expired" | "emptied"
    visit_after: Optional[FaiCtx]  # visit state after the edge
    relinquished: Optional[FaiCtx]  # open visit abandoned by this edge's fire (rule 3.2)
    post_occupancy: Optional[Tuple[int, ...]]  # post-edge occupancies (None on reset edges)
    closing: bool
    b_close: Optional[Tuple[int, ...]]
    s_close: Optional[int]
    evidence: Optional[Tuple[str, ...]]
    old_classes: Optional[Tuple[str, ...]]  # class map of the cycle this edge closes
    new_classes: Optional[Tuple[str, ...]]  # class map of the next cycle
    candidate: FaiCandidate  # candidate of the cycle this edge closes
    held_mismatch: bool  # fired (source, ctx) differs from this cycle's (ignored) candidate
    latched: Optional[Tuple[int, FaiCtx]]  # grant that became held at this edge
    released: bool


# ----- the switch model ------------------------------------------------------------------------------


class FaiMainSwitchModel:
    """N per-source queues + common hold record + arrival metadata + Main FAI policy state.

    Interpretation hook (class attributes): the per-source state table, the effective-class map and
    the reset state. Main uses the spec 8.2 values below; the separate Algorithm-2 model
    (``fai_alg2_model``) overrides only these three. All FIFO/hold/FCFS/visit/window mechanics are
    shared.
    """

    INTERPRETATION = "main"
    TRANSITIONS: Dict[Tuple[str, str], str] = MAIN_TRANSITIONS
    EFFECTIVE: Dict[str, str] = EFFECTIVE_CLASS
    RESET_STATE = "H"

    def __init__(
        self,
        n_src: int,
        window: int = FAI_W_PRODUCTION,
        depth: int = FIFO_DEPTH,
        desc_width: int = DESC_WIDTH,
        ts_width: int = TS_WIDTH,
    ) -> None:
        if n_src < 2:
            raise ValueError("n_src must be at least 2")
        self.idx_bits, self.count_bits = window_widths(window)  # rejects unsupported windows
        self.n_src = n_src
        self.window = window
        self.depth = depth
        self.ts_width = ts_width
        self.ts_mask = (1 << ts_width) - 1
        self.ctrl = CommonCtrlModel(n_src, depth, True, HW_CTX_WIDTH, desc_width, ts_width)
        self._arrival: List[Deque[int]] = [deque() for _ in range(n_src)]
        self.edge_index = 0  # absolute index of the NEXT edge to be committed
        self.epoch = 0
        self.state_known = False  # False until the first reset edge (power-up state unknown)
        self.counter_init = 0
        self.edges_since_reset = 0  # non-reset edges since the last reset edge
        self.deposits: List[Tuple[int, int, int]] = []  # (epoch, edge_index, value)
        self.visit_log: List[FaiVisitRecord] = []
        self.window_log: List[FaiWindowClose] = []
        self._reset_policy()

    def _reset_policy(self) -> None:
        n = self.n_src
        self.cls: List[str] = [self.RESET_STATE] * n
        self.visit = FaiCtx(HIGH, 0)
        self.win_pos = 0
        self.b: List[int] = [0] * n
        self.s = 0
        self.windows_closed = 0  # in the current epoch
        self.service: List[int] = [0] * n  # fires per source, current epoch

    # ----- beginning-of-cycle observation ------------------------------------------------------

    def classes(self) -> Optional[Tuple[str, ...]]:
        return tuple(self.cls) if self.state_known else None

    def effective_classes(self) -> Optional[Tuple[str, ...]]:
        return tuple(self.EFFECTIVE[c] for c in self.cls) if self.state_known else None

    def window_state(self) -> Optional[Tuple[int, Tuple[int, ...], int]]:
        """(window position, B per source, S)."""
        return (self.win_pos, tuple(self.b), self.s) if self.state_known else None

    def visit_state(self) -> Optional[FaiCtx]:
        """(class of the open visit, fires already charged to it)."""
        return self.visit if self.state_known else None

    @property
    def held(self) -> Optional[int]:
        held = self.ctrl.held
        return None if held is None else held.source

    def held_grant(self) -> Optional[Tuple[int, FaiCtx]]:
        held = self.ctrl.held
        return None if held is None else (held.source, ctx_from_hw(held.ctx))

    def counter(self) -> Optional[int]:
        """Expected value of the 32-bit arrival counter during the current cycle."""
        if not self.state_known:
            return None
        return (self.counter_init + self.edges_since_reset) & self.ts_mask

    def occupancy(self, source: int) -> int:
        return self.ctrl.occupancy(source)

    def nonempty_sources(self) -> List[int]:
        return self.ctrl.nonempty_sources()

    def queue(self, source: int) -> List[FcfsEntry]:
        entries = self.ctrl.fifos[source].entries()
        return [FcfsEntry(e.desc, a, e.ts) for e, a in zip(entries, self._arrival[source])]

    def oldest_in(self, cls: str) -> Optional[int]:
        """FCFS-oldest nonempty head among sources whose effective class is ``cls``."""
        keyed = [(self._arrival[h][0], h) for h in range(self.n_src)
                 if self._arrival[h] and self.EFFECTIVE[self.cls[h]] == cls]  # fmt: skip
        return min(keyed)[1] if keyed else None

    def candidate(self) -> FaiCandidate:
        if not self.state_known:
            return NO_FAI_CANDIDATE
        turn, used = self.visit
        src = self.oldest_in(turn)
        if src is not None:
            return FaiCandidate(True, src, FaiCtx(turn, used))
        other = other_class(turn)
        src = self.oldest_in(other)
        if src is not None:
            return FaiCandidate(True, src, FaiCtx(other, 0))
        return NO_FAI_CANDIDATE

    def ctrl_candidate(self) -> Candidate:
        """The candidate in the common-framework form (context encoded for the hold controller)."""
        cand = self.candidate()
        return Candidate(True, cand.source, ctx_to_hw(cand.ctx)) if cand.valid else NO_CANDIDATE

    def offered(self) -> Optional[Tuple[int, FaiCtx]]:
        """Grant offered this cycle (held grant, else candidate), abstract context."""
        held = self.held_grant()
        if held is not None:
            return held
        cand = self.candidate()
        return (cand.source, cand.ctx) if cand.valid else None

    def view(self, out_ready: bool = False, rst_n: bool = True) -> CtrlView:
        """Common-framework view; ``grant_ctx`` is the 5-bit hardware encoding (``ctx_to_hw``)."""
        self._check_environment()
        return self.ctrl.view(self.ctrl_candidate(), out_ready, rst_n)

    def _check_environment(self) -> None:
        for h in range(self.n_src):
            if self._arrival[h]:
                age = self.edge_index - self._arrival[h][0]
                if age >= MAX_OUTSTANDING_AGE:
                    raise AssertionError(
                        f"environment assumption violated: source {h} head is {age} cycles old (spec 6)"
                    )

    # ----- simulation-only counter deposit -------------------------------------------------------

    def deposit_counter(self, value: int) -> None:
        """Mirror a simulation-only deposit of the hardware arrival counter in the current cycle.

        Allowed only in the first cycle after a reset edge, with every queue empty and no held
        grant (same restriction as the FCFS model). Ordering is unaffected: it uses absolute time.
        """
        if not 0 <= value <= self.ts_mask:
            raise ValueError(f"counter value {value:#x} does not fit in {self.ts_width} bits")
        if not self.state_known or self.edges_since_reset != 0:
            raise ValueError("deposit only in the first cycle after a reset edge")
        if self.ctrl.nonempty_sources() or self.ctrl.held is not None:
            raise ValueError("deposit only with every queue empty and no held grant")
        self.counter_init = value
        self.deposits.append((self.epoch, self.edge_index, value))

    # ----- invariants ----------------------------------------------------------------------------

    def _check_window_invariants(self) -> None:
        if self.s != sum(self.b):
            raise AssertionError(f"S={self.s} != sum(B)={sum(self.b)}")
        if not 0 <= self.win_pos < self.window or self.win_pos >= (1 << self.idx_bits):
            raise AssertionError(f"window position {self.win_pos} outside 0..{self.window - 1}")
        for b in self.b:
            check_threshold_operands(self.n_src, self.window, b, self.s)

    # ----- closing edge --------------------------------------------------------------------------

    def commit(
        self,
        out_ready: bool = False,
        in_valid: Optional[Sequence[bool]] = None,
        in_desc: Optional[Sequence[int]] = None,
        rst_n: bool = True,
    ) -> FaiEdge:
        n = self.n_src
        this_edge = self.edge_index
        if rst_n:
            if not self.state_known:
                raise AssertionError("non-reset edge before the first reset edge: FAI state is unknown")
            # Checked at the edge being processed, before edge_index advances (as in the FCFS model).
            self._check_environment()
        self.edge_index += 1

        if not rst_n:
            ctrl_edge = self.ctrl.commit(NO_CANDIDATE, out_ready, None, None, None, rst_n=False)
            for q in self._arrival:
                q.clear()
            self.epoch += 1
            self.counter_init = 0
            self.edges_since_reset = 0
            self.state_known = True
            self._reset_policy()
            return FaiEdge(True, this_edge, None, (None,) * n, None, None, None, None, None, None,
                           False, None, None, None, None, None, NO_FAI_CANDIDATE, False, None,
                           ctrl_edge.released)  # fmt: skip

        # Everything below is decided from beginning-of-cycle state.
        cand = self.candidate()
        held_before = self.held_grant()
        old_classes = tuple(self.cls)
        eff = tuple(self.EFFECTIVE[c] for c in old_classes)  # class map of this cycle
        pos = self.win_pos
        begin_occ = [self.ctrl.occupancy(h) for h in range(n)]
        ts = self.counter()

        ctrl_edge: CtrlEdge = self.ctrl.commit(
            self.ctrl_candidate(), out_ready, in_valid, in_desc, ts, rst_n=True
        )

        # Arrival bookkeeping: pop first (only the fired source), then append this edge's pushes.
        fired = None
        g: Optional[int] = None
        charged: Optional[FaiCtx] = None
        if ctrl_edge.fired is not None:
            g = ctrl_edge.fired.source
            charged = ctx_from_hw(ctrl_edge.fired.ctx)
            arrival = self._arrival[g].popleft()
            fired = (g, FcfsEntry(ctrl_edge.fired.entry.desc, arrival, ctrl_edge.fired.entry.ts))
            expected = held_before if held_before is not None else (cand.source, cand.ctx)
            if (g, charged) != expected:
                raise AssertionError(f"fired grant {(g, charged)} is neither the held grant nor the candidate")
        pushed: List[Optional[FcfsEntry]] = []
        for h in range(n):
            e = ctrl_edge.pushed[h]
            if e is None:
                pushed.append(None)
            else:
                self._arrival[h].append(this_edge)
                pushed.append(FcfsEntry(e.desc, this_edge, e.ts))
        post = tuple(begin_occ[h] + int(pushed[h] is not None) - int(h == g) for h in range(n))
        for h in range(n):
            if post[h] != self.ctrl.occupancy(h) or len(self._arrival[h]) != post[h]:
                raise AssertionError("post-edge occupancy bookkeeping mismatch")

        # Quota / visit: only a fire, charged to the fired grant's retained context.
        event = None
        relinquished = None
        mismatch = False
        if charged is not None:
            mismatch = (not cand.valid) or (cand.source, cand.ctx) != (g, charged)
            # The retained context continues the open visit or opens a new one in the other class
            # (the visit cannot change while a grant waits, because only a fire changes it).
            if charged != self.visit and charged != FaiCtx(other_class(self.visit.cls), 0):
                raise AssertionError(f"charged context {charged} inconsistent with open visit {self.visit}")
            if charged != self.visit and self.visit.fires > 0:
                relinquished = self.visit
                self.visit_log.append(
                    FaiVisitRecord(self.epoch, self.visit.cls, self.visit.fires, "relinquished", this_edge)
                )
            self.service[g] += 1
            n_fires = charged.fires + 1
            class_live = any(eff[h] == charged.cls and post[h] > 0 for h in range(n))
            if n_fires == FAI_QUOTA:
                event = "expired"
            elif not class_live:
                event = "emptied"
            else:
                event = "continue"
            if event == "continue":
                self.visit = FaiCtx(charged.cls, n_fires)
            else:
                self.visit = FaiCtx(other_class(charged.cls), 0)
                self.visit_log.append(FaiVisitRecord(self.epoch, charged.cls, n_fires, event, this_edge))

        # Window accounting: every non-reset edge is a window cycle.
        if g is not None:
            self.b[g] += 1
            self.s += 1
        closing = pos == self.window - 1
        b_close = s_close = evidence = new_classes = None
        if closing:
            b_close = tuple(self.b)
            s_close = self.s
            if s_close != sum(b_close):
                raise AssertionError("S_close != sum(B_close)")
            for b in b_close:
                check_threshold_operands(n, self.window, b, s_close)
            evidence = tuple(threshold_evidence(n, b, s_close) for b in b_close)
            new_classes = tuple(self.TRANSITIONS[(old_classes[h], evidence[h])] for h in range(n))
            self.window_log.append(FaiWindowClose(self.epoch, this_edge, self.windows_closed, b_close,
                                                  s_close, evidence, old_classes, new_classes))  # fmt: skip
            self.windows_closed += 1
            self.cls = list(new_classes)
            self.b = [0] * n
            self.s = 0
            self.win_pos = 0
        else:
            self.win_pos += 1
        self._check_window_invariants()
        self.edges_since_reset += 1

        latched = None
        if ctrl_edge.latched is not None:
            latched = (ctrl_edge.latched.source, ctx_from_hw(ctrl_edge.latched.ctx))
        return FaiEdge(
            reset=False,
            edge_index=this_edge,
            window_pos=pos,
            pushed=tuple(pushed),
            fired=fired,
            charged=charged,
            visit_event=event,
            visit_after=self.visit,
            relinquished=relinquished,
            post_occupancy=post,
            closing=closing,
            b_close=b_close,
            s_close=s_close,
            evidence=evidence,
            old_classes=old_classes,
            new_classes=new_classes if closing else old_classes,
            candidate=cand,
            held_mismatch=mismatch,
            latched=latched,
            released=ctrl_edge.released,
        )
