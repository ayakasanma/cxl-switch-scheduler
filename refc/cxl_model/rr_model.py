"""Abstract cycle-level Round Robin model of the complete switch (specs/CXL_SPEC.md v1.0 sections
4, 5 and 7; specs/DECISIONS.md D07, D25, D26, D32).

Written from the approved contract, not from the RTL. The policy state is an explicit, abstract
*turn* record rather than a pointer/counter register pair:

* ``poll``  - the polling position (a source index). Reset sets it to source 0 (Q1 / D25).
* ``turn``  - ``None`` or ``Turn(source, fires)``: the source that currently owns an unfinished turn
  and the number of SUCCESSFUL transfers (fires) already charged to that turn, 1..quantum-1.

Contract modelled (spec 7 bullets + Q2):

1. Candidate (beginning-of-cycle state only): if a source owns a turn it keeps being offered;
   otherwise the first nonempty source in the circular order poll, poll+1, ... (mod N). Empty
   sources are skipped within the same cycle, so there is never a control-only bubble while any
   source is nonempty. With every source empty there is no candidate and nothing changes.
2. Only a fire (out_valid && out_ready) is service. It is charged to the source that ACTUALLY
   fired - the grant offered by the common hold controller, which can be a held grant latched in
   an earlier cycle even though, because of later arrivals, this cycle's candidate is a different
   source. A fire of a source that does not own a turn opens a new turn for it.
3. After the fire the turn continues or ends according to the post-edge occupancy of the fired
   source, ``beginning count + accepted push - 1`` (the replacement push of the same edge counts):
     - the turn reached ``quantum`` fires -> it ends ("expired"), even if a replacement push keeps
       the source nonempty; polling continues after the fired source;
     - otherwise the source is empty after the edge -> it ends ("emptied") and relinquishes the
       unused quota; polling continues after the fired source;
     - otherwise the turn continues and polling stays at the fired source.
4. Stalls (out_valid && !out_ready), held grants and idle cycles charge nothing and change no turn
   state. Descriptor contents (e.g. Length) never alter the charge: one fire costs exactly one.
5. A reset edge empties every queue, drops any held grant, clears the turn and sets poll = 0.

The queues and the held-grant record are the reviewed abstract ``CommonCtrlModel`` without arrival
metadata (RR keeps no timestamps). This module adds only the RR candidate and turn bookkeeping.

For comparison with the hardware's observable policy state, ``polling_state()`` returns the
spec-level pair (position at which polling resumes, fires charged to the current turn): while a
turn is open that is (turn source, turn fires), otherwise (poll, 0).
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Sequence, Tuple

from .common_ctrl_model import NO_CANDIDATE, Candidate, CommonCtrlModel, CtrlEdge, CtrlView
from .fifo_model import DESC_WIDTH, FIFO_DEPTH

RR_QUANTUM_PRIMARY = 10
RR_QUANTUM_SUPPLEMENTARY = 1


class Turn(NamedTuple):
    source: int
    fires: int  # successful transfers already charged to this unfinished turn


class TurnRecord(NamedTuple):
    """A finished turn."""

    epoch: int
    source: int
    fires: int
    reason: str  # "expired" | "emptied"
    end_edge: int  # absolute index of the edge that ended it
    replaced: bool  # a replacement push arrived on the ending edge (source still nonempty if expired)


class RrEdge(NamedTuple):
    reset: bool
    edge_index: int
    pushed: Tuple[Optional[int], ...]  # descriptor accepted per source, None when no push
    fired: Optional[Tuple[int, int]]  # (source, descriptor) delivered at this edge
    charged_fires: int  # fires of the charged turn after this edge (0 when nothing fired)
    turn_event: Optional[str]  # None | "continue" | "expired" | "emptied"
    post_occupancy: Optional[int]  # post-edge occupancy of the fired source
    candidate: Candidate  # candidate of the cycle this edge closes
    held_mismatch: bool  # the fired grant differs from this cycle's (ignored) candidate
    latched: Optional[int]  # source whose stalled offer became held at this edge
    released: bool


class RrSwitchModel:
    """N per-source queues + the common hold record + the Round Robin turn state."""

    def __init__(
        self,
        n_src: int,
        quantum: int = RR_QUANTUM_PRIMARY,
        depth: int = FIFO_DEPTH,
        desc_width: int = DESC_WIDTH,
    ) -> None:
        if n_src < 2:
            raise ValueError("n_src must be at least 2")
        if quantum < 1:
            raise ValueError("quantum must be at least 1")
        self.n_src = n_src
        self.quantum = quantum
        self.depth = depth
        # No arrival metadata (ts disabled), ctx width 1 with the candidate ctx always 0.
        self.ctrl = CommonCtrlModel(n_src, depth, False, 1, desc_width)
        self.poll = 0
        self.turn: Optional[Turn] = None
        self.state_known = False  # False until the first reset edge (power-up state unknown)
        self.edge_index = 0  # absolute index of the NEXT edge to be committed
        self.epoch = 0
        self.turn_log: List[TurnRecord] = []
        self.service: List[int] = [0] * n_src  # fires per source, current epoch

    # ----- beginning-of-cycle observation ------------------------------------------------------

    @property
    def held(self) -> Optional[int]:
        held = self.ctrl.held
        return None if held is None else held.source

    def occupancy(self, source: int) -> int:
        return self.ctrl.occupancy(source)

    def nonempty_sources(self) -> List[int]:
        return self.ctrl.nonempty_sources()

    def queue(self, source: int) -> List[int]:
        return [e.desc for e in self.ctrl.fifos[source].entries()]

    def polling_state(self) -> Tuple[int, int]:
        """(position from which polling continues, fires charged to the open turn)."""
        if self.turn is not None:
            return self.turn.source, self.turn.fires
        return self.poll, 0

    def candidate(self) -> Candidate:
        nonempty = set(self.ctrl.nonempty_sources())
        if self.turn is not None:
            if self.turn.source not in nonempty:
                raise AssertionError(f"turn {self.turn} is open but its source is empty")
            return Candidate(True, self.turn.source, 0)
        for k in range(self.n_src):
            s = (self.poll + k) % self.n_src
            if s in nonempty:
                return Candidate(True, s, 0)
        return NO_CANDIDATE

    def view(self, out_ready: bool = False, rst_n: bool = True) -> CtrlView:
        return self.ctrl.view(self.candidate(), out_ready, rst_n)

    # ----- closing edge --------------------------------------------------------------------------

    def commit(
        self,
        out_ready: bool = False,
        in_valid: Optional[Sequence[bool]] = None,
        in_desc: Optional[Sequence[int]] = None,
        rst_n: bool = True,
    ) -> RrEdge:
        n = self.n_src
        this_edge = self.edge_index
        self.edge_index += 1
        if not rst_n:
            ctrl_edge = self.ctrl.commit(NO_CANDIDATE, out_ready, None, None, None, rst_n=False)
            self.poll = 0
            self.turn = None
            self.state_known = True
            self.epoch += 1
            self.service = [0] * n
            return RrEdge(True, this_edge, (None,) * n, None, 0, None, None, NO_CANDIDATE, False, None,
                          ctrl_edge.released)  # fmt: skip

        if not self.state_known:
            raise AssertionError("non-reset edge before the first reset edge: RR state is unknown")
        cand = self.candidate()
        begin_occ = [self.ctrl.occupancy(h) for h in range(n)]
        ctrl_edge: CtrlEdge = self.ctrl.commit(cand, out_ready, in_valid, in_desc, None, rst_n=True)
        pushed = tuple(None if e is None else e.desc for e in ctrl_edge.pushed)

        fired = None
        charged = 0
        event = None
        post = None
        mismatch = False
        if ctrl_edge.fired is not None:
            g = ctrl_edge.fired.source
            fired = (g, ctrl_edge.fired.entry.desc)
            mismatch = (not cand.valid) or cand.source != g
            if self.turn is not None and self.turn.source != g:
                # The open turn's source is always the candidate, and a grant only latches as the
                # candidate of its cycle while turn state is frozen until a fire: impossible.
                raise AssertionError(f"source {g} fired while source {self.turn.source} owns the turn")
            charged = (self.turn.fires if self.turn is not None else 0) + 1
            post = begin_occ[g] + int(pushed[g] is not None) - 1
            if post != self.ctrl.occupancy(g):
                raise AssertionError("post-edge occupancy bookkeeping mismatch")
            self.service[g] += 1
            if charged >= self.quantum:
                event = "expired"
            elif post == 0:
                event = "emptied"
            else:
                event = "continue"
            if event == "continue":
                self.turn = Turn(g, charged)
                self.poll = g
            else:
                self.turn = None
                self.poll = (g + 1) % n
                self.turn_log.append(TurnRecord(self.epoch, g, charged, event, this_edge, pushed[g] is not None))
        latched = None if ctrl_edge.latched is None else ctrl_edge.latched.source
        return RrEdge(False, this_edge, pushed, fired, charged, event, post, cand, mismatch, latched,
                      ctrl_edge.released)  # fmt: skip
