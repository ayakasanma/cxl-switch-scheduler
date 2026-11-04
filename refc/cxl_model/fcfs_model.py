"""Abstract cycle-level FCFS model of the complete switch (specs/CXL_SPEC.md v1.0 sections 4-6).

Written from the approved contract, not from the RTL. Ordering is derived from ABSOLUTE time:

* Every rising edge processed by the model has an unbounded Python integer index (``edge_index``,
  counting every committed edge, reset edges included). A push at edge *e* gives the entry the
  absolute arrival time *e*.
* The offered grant of a cycle is the held grant if one is held; otherwise, among the nonempty
  beginning-of-cycle heads, the one with the smallest absolute arrival time, ties (same push edge)
  broken by the lowest source ID.

No modular difference, MSB test or wrap reasoning is used for ordering. The selection is an
explicit ``min`` over (absolute arrival time, source ID) pairs.

Separately, and only to check what the hardware stores, the model also tracks the expected 32-bit
timestamp written with each push: ``(counter_init + non-reset edges since the last reset) mod
2**32``. ``counter_init`` is 0 after every reset and can be set by ``deposit_counter`` to mirror a
simulation-only deposit of the hardware counter (allowed only in the first cycle after a reset,
with every queue empty and no held grant). The stored value never influences the model's order.

The queues and the held-grant record are the reviewed abstract ``CommonCtrlModel`` (per-source
deques + one optional held grant). This module only adds the FCFS candidate and the arrival
bookkeeping; reset clears the queues, the hold, the counter and starts a new epoch.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, NamedTuple, Optional, Sequence, Tuple

from .common_ctrl_model import NO_CANDIDATE, Candidate, CommonCtrlModel, CtrlEdge, CtrlView
from .fifo_model import DESC_WIDTH, FIFO_DEPTH, TS_WIDTH

# Environment assumption of spec section 6: every outstanding request is younger than 2**31 cycles.
MAX_OUTSTANDING_AGE = 1 << 31


class FcfsEntry(NamedTuple):
    """One queued request as the FCFS model sees it."""

    desc: int
    arrival: int  # absolute arrival time: index of the push edge (unbounded)
    ts32: int  # expected stored 32-bit hardware timestamp (checking only, never used to order)


class FcfsEdge(NamedTuple):
    reset: bool
    edge_index: int  # absolute index of this edge
    pushed: Tuple[Optional[FcfsEntry], ...]
    fired: Optional[Tuple[int, FcfsEntry]]  # (source, entry) delivered at this edge
    latched: Optional[int]  # source whose offer became held at this edge
    released: bool


class FcfsSwitchModel:
    """N per-source queues + the common hold record + the FCFS absolute-time candidate."""

    def __init__(
        self,
        n_src: int,
        depth: int = FIFO_DEPTH,
        desc_width: int = DESC_WIDTH,
        ts_width: int = TS_WIDTH,
    ) -> None:
        if n_src < 2:
            raise ValueError("n_src must be at least 2")
        self.n_src = n_src
        self.depth = depth
        self.ts_width = ts_width
        self.ts_mask = (1 << ts_width) - 1
        # ctx_width 1, candidate ctx always 0: FCFS carries no grant context.
        self.ctrl = CommonCtrlModel(n_src, depth, True, 1, desc_width, ts_width)
        self._arrival: List[Deque[int]] = [deque() for _ in range(n_src)]
        self.edge_index = 0  # absolute index of the NEXT edge to be committed
        self.epoch = 0
        self.counter_init = 0
        self.edges_since_reset = 0  # non-reset edges since the last reset edge
        self.counter_known = False  # False until the first reset edge (power-up state unknown)
        self.deposits: List[Tuple[int, int, int]] = []  # (epoch, edge_index, value)

    # ----- beginning-of-cycle observation ------------------------------------------------------

    @property
    def held(self) -> Optional[int]:
        held = self.ctrl.held
        return None if held is None else held.source

    def counter(self) -> Optional[int]:
        """Expected value of the 32-bit arrival counter during the current cycle."""
        if not self.counter_known:
            return None
        return (self.counter_init + self.edges_since_reset) & self.ts_mask

    def heads(self) -> List[Optional[FcfsEntry]]:
        out: List[Optional[FcfsEntry]] = []
        for h in range(self.n_src):
            entries = self.ctrl.fifos[h].entries()
            out.append(FcfsEntry(entries[0].desc, self._arrival[h][0], entries[0].ts) if entries else None)
        return out

    def queue(self, source: int) -> List[FcfsEntry]:
        entries = self.ctrl.fifos[source].entries()
        return [FcfsEntry(e.desc, a, e.ts) for e, a in zip(entries, self._arrival[source])]

    def occupancy(self, source: int) -> int:
        return self.ctrl.occupancy(source)

    def nonempty_sources(self) -> List[int]:
        return self.ctrl.nonempty_sources()

    def oldest_head(self) -> Optional[int]:
        """Source of the oldest nonempty head by absolute arrival time, lowest ID on ties."""
        keyed = [(self._arrival[h][0], h) for h in range(self.n_src) if self._arrival[h]]
        return min(keyed)[1] if keyed else None

    def candidate(self) -> Candidate:
        src = self.oldest_head()
        return NO_CANDIDATE if src is None else Candidate(True, src, 0)

    def view(self, out_ready: bool = False, rst_n: bool = True) -> CtrlView:
        self._check_environment()
        return self.ctrl.view(self.candidate(), out_ready, rst_n)

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
        """Mirror a simulation-only deposit of the hardware counter in the current cycle.

        Allowed only in the first cycle after a reset edge, with every queue empty and no held
        grant, so that the deposited value is the counter value of this whole cycle.
        """
        if not 0 <= value <= self.ts_mask:
            raise ValueError(f"counter value {value:#x} does not fit in {self.ts_width} bits")
        if not self.counter_known or self.edges_since_reset != 0:
            raise ValueError("deposit only in the first cycle after a reset edge")
        if self.ctrl.nonempty_sources() or self.ctrl.held is not None:
            raise ValueError("deposit only with every queue empty and no held grant")
        self.counter_init = value
        self.deposits.append((self.epoch, self.edge_index, value))

    # ----- closing edge --------------------------------------------------------------------------

    def commit(
        self,
        out_ready: bool = False,
        in_valid: Optional[Sequence[bool]] = None,
        in_desc: Optional[Sequence[int]] = None,
        rst_n: bool = True,
    ) -> FcfsEdge:
        n = self.n_src
        this_edge = self.edge_index
        if rst_n:
            # Spec 6 environment assumption, checked at the edge being processed (this_edge) --
            # the same edge view() checks during this cycle -- BEFORE edge_index advances, so a
            # head of age 2**31-1 at this edge is legal in both view() and commit().
            self._check_environment()
        self.edge_index += 1
        if not rst_n:
            ctrl_edge = self.ctrl.commit(NO_CANDIDATE, out_ready, None, None, None, rst_n=False)
            for q in self._arrival:
                q.clear()
            self.epoch += 1
            self.counter_init = 0
            self.edges_since_reset = 0
            self.counter_known = True
            return FcfsEdge(True, this_edge, (None,) * n, None, None, ctrl_edge.released)

        cand = self.candidate()
        ts = self.counter()
        # Before the first reset edge the hardware counter is unknown; nothing may be pushed then.
        ctrl_edge: CtrlEdge = self.ctrl.commit(
            cand, out_ready, in_valid, in_desc, 0 if ts is None else ts, rst_n=True
        )
        if ts is None and any(p is not None for p in ctrl_edge.pushed):
            raise AssertionError("push before the first reset edge: arrival counter is unknown")

        fired = None
        if ctrl_edge.fired is not None:
            src = ctrl_edge.fired.source
            arrival = self._arrival[src].popleft()
            fired = (src, FcfsEntry(ctrl_edge.fired.entry.desc, arrival, ctrl_edge.fired.entry.ts))
        pushed: List[Optional[FcfsEntry]] = []
        for h in range(n):
            e = ctrl_edge.pushed[h]
            if e is None:
                pushed.append(None)
            else:
                self._arrival[h].append(this_edge)
                pushed.append(FcfsEntry(e.desc, this_edge, e.ts))
        for h in range(n):
            assert len(self._arrival[h]) == self.ctrl.occupancy(h)
        if self.counter_known:
            self.edges_since_reset += 1
        latched = None if ctrl_edge.latched is None else ctrl_edge.latched.source
        return FcfsEdge(False, this_edge, tuple(pushed), fired, latched, ctrl_edge.released)
