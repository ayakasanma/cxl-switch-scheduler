"""Abstract cycle-level model of the common output hold/stall controller and of the common
framework (N per-source FIFOs + that controller). specs/CXL_SPEC.md v1.0 sections 4 and 5.

Written from the spec contract, not from the RTL. State is deliberately abstract:

* each source is a queue (``FifoModel``, a deque of entries);
* the output controller owns exactly one optional record, the *held grant* ``(source, ctx)``.

There is no policy here. The candidate ``(valid, source, ctx)`` is an INPUT of every cycle, exactly
like the DUT's policy interface. ``ctx`` is opaque: it is stored and replayed, never interpreted.

Cycle convention (spec section 4): cycle *c* is the interval before its closing rising edge.
``offer``/``view`` describe what is observable during the cycle from beginning-of-cycle state;
``commit`` applies the closing edge and its effects are visible from cycle *c+1*.

Contract modelled:

* The grant offered in a cycle is the held grant if one exists, otherwise the candidate if it is
  valid, otherwise nothing. While a grant is held the candidate is ignored completely.
* ``out_valid`` = not in reset, a grant is offered, and the head of the offered source is valid.
* ``fire`` = ``out_valid and out_ready``. Only fire dequeues, and only from the offered source.
* An offer that is valid but not accepted (stall) is held from the next cycle on. A held grant is
  released only by its fire or by a reset edge - never because the candidate changed or vanished
  and never because the head of the held source appears invalid.
* A reset edge drops the held grant and empties every queue; nothing is pushed or popped on it.

Selected-head invariant of the integrated framework: a queue is popped only by the fire of the
offered grant, and a grant can only become held while its head is valid, so the head of a held
source stays valid and unchanged until that grant fires. ``CommonCtrlModel`` asserts this.
``OutHoldModel`` alone takes head validity as an input and therefore also defines what happens if
an environment violates the invariant: no output, no pop, and the grant stays held.
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence, Tuple

from .fifo_model import DESC_WIDTH, FIFO_DEPTH, TS_WIDTH, Entry, FifoModel


class Candidate(NamedTuple):
    """Policy candidate of one cycle. ``source``/``ctx`` are ignored when ``valid`` is false."""

    valid: bool
    source: int = 0
    ctx: int = 0


NO_CANDIDATE = Candidate(False, 0, 0)


class Grant(NamedTuple):
    source: int
    ctx: int


class Offer(NamedTuple):
    """Output-side view of one cycle."""

    held: bool  # the offered grant is a latched, previously stalled grant
    grant: Optional[Grant]  # grant being offered (held or candidate), None when there is none
    out_valid: bool
    fire: bool
    stall: bool  # out_valid and not out_ready

    @property
    def pop_source(self) -> Optional[int]:
        return self.grant.source if self.fire else None


class HoldEdge(NamedTuple):
    reset: bool
    fired: Optional[Grant]  # grant whose transfer completed at this edge
    latched: Optional[Grant]  # grant that became held at this edge
    released: bool  # a held grant was released (by fire or by reset)


class OutHoldModel:
    """The hold/stall controller alone: one optional held-grant record."""

    def __init__(self, n_src: int, ctx_width: int = 1) -> None:
        if n_src < 2:
            raise ValueError("n_src must be at least 2")
        if ctx_width < 1:
            raise ValueError("ctx_width must be at least 1")
        self.n_src = n_src
        self.ctx_width = ctx_width
        self.held: Optional[Grant] = None

    def _check_candidate(self, cand: Candidate) -> None:
        if cand.valid:
            if not 0 <= cand.source < self.n_src:
                raise ValueError(f"candidate source {cand.source} outside 0..{self.n_src - 1}")
            if not 0 <= cand.ctx < (1 << self.ctx_width):
                raise ValueError(f"candidate ctx {cand.ctx:#x} does not fit in {self.ctx_width} bits")

    def offer(
        self, cand: Candidate, head_valid: Sequence[bool], out_ready: bool = False, rst_n: bool = True
    ) -> Offer:
        """What the controller presents during the current cycle."""
        self._check_candidate(cand)
        if len(head_valid) != self.n_src:
            raise ValueError("head_valid must have one element per source")
        if self.held is not None:
            grant: Optional[Grant] = self.held  # the candidate is not looked at
        elif cand.valid:
            grant = Grant(cand.source, cand.ctx)
        else:
            grant = None
        out_valid = bool(rst_n) and grant is not None and bool(head_valid[grant.source])
        fire = out_valid and bool(out_ready)
        return Offer(
            held=self.held is not None,
            grant=grant,
            out_valid=out_valid,
            fire=fire,
            stall=out_valid and not fire,
        )

    def commit(
        self, cand: Candidate, head_valid: Sequence[bool], out_ready: bool = False, rst_n: bool = True
    ) -> HoldEdge:
        """Apply the closing edge of the cycle."""
        if not rst_n:
            released = self.held is not None
            self.held = None
            return HoldEdge(reset=True, fired=None, latched=None, released=released)
        offer = self.offer(cand, head_valid, out_ready, True)
        if offer.fire:
            released = self.held is not None
            self.held = None
            return HoldEdge(reset=False, fired=offer.grant, latched=None, released=released)
        if offer.stall and self.held is None:
            self.held = offer.grant
            return HoldEdge(reset=False, fired=None, latched=offer.grant, released=False)
        # Nothing offered, or an already held grant still waiting: no change.
        return HoldEdge(reset=False, fired=None, latched=None, released=False)


class CtrlView(NamedTuple):
    """Everything observable on the common framework during one cycle."""

    in_ready: Tuple[bool, ...]
    head_valid: Tuple[bool, ...]
    count: Tuple[int, ...]
    head_desc: Tuple[Optional[int], ...]  # None for an empty source
    head_ts: Tuple[Optional[int], ...]  # None for an empty source or without arrival metadata
    held: bool
    out_valid: bool
    fire: bool
    pop: Tuple[bool, ...]  # one-hot or all false
    out_source: Optional[int]  # None when out_valid is false (not meaningful)
    out_desc: Optional[int]
    out_ts: Optional[int]
    grant_ctx: Optional[int]


class Delivery(NamedTuple):
    source: int
    ctx: int
    entry: Entry


class CtrlEdge(NamedTuple):
    reset: bool
    pushed: Tuple[Optional[Entry], ...]
    fired: Optional[Delivery]
    latched: Optional[Grant]
    released: bool


class CommonCtrlModel:
    """N per-source queues feeding one hold controller (the policy-independent framework)."""

    def __init__(
        self,
        n_src: int,
        depth: int = FIFO_DEPTH,
        ts_enabled: bool = False,
        ctx_width: int = 1,
        desc_width: int = DESC_WIDTH,
        ts_width: int = TS_WIDTH,
    ) -> None:
        self.n_src = n_src
        self.depth = depth
        self.ts_enabled = bool(ts_enabled)
        self.fifos: List[FifoModel] = [
            FifoModel(depth, ts_enabled, desc_width, ts_width) for _ in range(n_src)
        ]
        self.hold = OutHoldModel(n_src, ctx_width)
        self.epoch = 0
        self.delivered = 0  # completed output transfers in the current epoch

    # ----- beginning-of-cycle observation ------------------------------------------------------

    @property
    def held(self) -> Optional[Grant]:
        return self.hold.held

    def occupancy(self, source: int) -> int:
        return self.fifos[source].occupancy

    def nonempty_sources(self) -> List[int]:
        return [h for h, f in enumerate(self.fifos) if not f.empty]

    def empty_sources(self) -> List[int]:
        return [h for h, f in enumerate(self.fifos) if f.empty]

    def _head_valid(self) -> Tuple[bool, ...]:
        return tuple(not f.empty for f in self.fifos)

    def _check_invariant(self) -> None:
        held = self.hold.held
        if held is not None and self.fifos[held.source].empty:
            raise AssertionError(
                f"selected-head invariant broken: grant {held} is held but its source is empty"
            )

    def view(self, cand: Candidate, out_ready: bool = False, rst_n: bool = True) -> CtrlView:
        self._check_invariant()
        fviews = [f.view(rst_n) for f in self.fifos]
        offer = self.hold.offer(cand, self._head_valid(), out_ready, rst_n)
        if offer.out_valid:
            source: Optional[int] = offer.grant.source
            head = self.fifos[source].head()
            out_desc, out_ts, ctx = head.desc, head.ts, offer.grant.ctx
        else:
            source = out_desc = out_ts = ctx = None
        return CtrlView(
            in_ready=tuple(v.in_ready for v in fviews),
            head_valid=tuple(v.head_valid for v in fviews),
            count=tuple(v.count for v in fviews),
            head_desc=tuple(v.head_desc for v in fviews),
            head_ts=tuple(v.head_ts for v in fviews),
            held=offer.held,
            out_valid=offer.out_valid,
            fire=offer.fire,
            pop=tuple(offer.fire and h == source for h in range(self.n_src)),
            out_source=source,
            out_desc=out_desc,
            out_ts=out_ts,
            grant_ctx=ctx,
        )

    # ----- closing edge --------------------------------------------------------------------------

    def commit(
        self,
        cand: Candidate,
        out_ready: bool = False,
        in_valid: Optional[Sequence[bool]] = None,
        in_desc: Optional[Sequence[int]] = None,
        in_ts: Optional[int] = None,
        rst_n: bool = True,
    ) -> CtrlEdge:
        """Apply one rising edge. ``in_ts`` is the single arrival timestamp of this cycle."""
        n = self.n_src
        in_valid = [False] * n if in_valid is None else list(in_valid)
        in_desc = [0] * n if in_desc is None else list(in_desc)
        if len(in_valid) != n or len(in_desc) != n:
            raise ValueError("in_valid/in_desc must have one element per source")
        self._check_invariant()

        if not rst_n:
            hold_edge = self.hold.commit(cand, self._head_valid(), out_ready, False)
            for f in self.fifos:
                f.commit(rst_n=False)
            self.epoch += 1
            self.delivered = 0
            return CtrlEdge(True, (None,) * n, None, None, hold_edge.released)

        # The output decision uses the queues as they stand at the beginning of the cycle.
        hold_edge = self.hold.commit(cand, self._head_valid(), out_ready, True)
        pop_source = hold_edge.fired.source if hold_edge.fired is not None else None

        pushed: List[Optional[Entry]] = []
        fired: Optional[Delivery] = None
        for h, f in enumerate(self.fifos):
            res = f.commit(
                rst_n=True,
                in_valid=in_valid[h],
                in_desc=in_desc[h],
                in_ts=in_ts if self.ts_enabled else None,
                pop=(h == pop_source),
            )
            pushed.append(res.pushed)
            if h == pop_source:
                assert res.popped is not None, "fire without a valid head"
                fired = Delivery(h, hold_edge.fired.ctx, res.popped)
        self.delivered += int(fired is not None)
        self._check_invariant()
        return CtrlEdge(False, tuple(pushed), fired, hold_edge.latched, hold_edge.released)
