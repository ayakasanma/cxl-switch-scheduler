"""TB-only abstract tagged-completion memory model (spec 2, 9 retained defaults).

Every completed output transfer (fire) creates one outstanding request keyed by (epoch, tag); a
response returns after a seeded random delay, so responses are reordered relative to the fires.
Each response must match exactly one outstanding request, exactly once. Outstanding tags are
never reused before their response (checked at issue time).

This object never drives a DUT pin: it only consumes observed fires. Response delay and order
therefore cannot influence acceptance, selection, fire or any scheduler state (spec 9: response
delay/reordering never charges quota or B/S). A reset starts a new TB epoch; requests of an older
epoch that already fired still complete in the memory model and are matched within their own
epoch's table.
"""

from __future__ import annotations

import heapq
import random
from typing import Dict, List, NamedTuple, Optional, Tuple


class Outstanding(NamedTuple):
    seq: int  # issue order
    fire_cycle: int
    source: int
    desc: int


class Response(NamedTuple):
    epoch: int
    tag: int
    seq: int
    fire_cycle: int
    resp_cycle: int
    source: int
    desc: int


class TagResponder:
    def __init__(self, rng: random.Random, delay: Tuple[int, int] = (1, 48), unique_run: bool = False) -> None:
        if delay[0] < 1 or delay[1] < delay[0]:
            raise ValueError("response delay range must satisfy 1 <= lo <= hi")
        self.rng = rng
        self.delay = delay
        # unique_run: additionally require every tag to be unique for the whole run (trace-driven
        # traffic has globally unique tags by construction).
        self.unique_run = unique_run
        self.outstanding: Dict[Tuple[int, int], Outstanding] = {}
        self._heap: List[Tuple[int, int, int, int]] = []  # (due_cycle, seq, epoch, tag)
        self._seen: set = set()
        self.issued = 0
        self.completed = 0
        self.reordered = 0  # responses that overtook an earlier-issued, still outstanding request
        self.max_outstanding = 0
        self.cross_epoch_completions = 0  # responses completed after a later epoch started
        self.responses: List[Response] = []
        self.keep_log = False

    def issue(self, epoch: int, tag: int, cycle: int, source: int, desc: int) -> None:
        key = (epoch, tag)
        if key in self.outstanding:
            raise AssertionError(
                f"cycle {cycle}: tag {tag:#010x} fired by source {source} while still outstanding "
                f"(issued cycle {self.outstanding[key].fire_cycle}): outstanding tag reuse"
            )
        if self.unique_run:
            if tag in self._seen:
                raise AssertionError(f"cycle {cycle}: tag {tag:#010x} delivered twice in one run")
            self._seen.add(tag)
        seq = self.issued
        self.issued += 1
        self.outstanding[key] = Outstanding(seq, cycle, source, desc)
        self.max_outstanding = max(self.max_outstanding, len(self.outstanding))
        heapq.heappush(self._heap, (cycle + self.rng.randint(*self.delay), seq, epoch, tag))

    def step(self, cycle: int, current_epoch: int) -> List[Response]:
        """Return every response due at or before ``cycle``, each matched exactly once."""
        out: List[Response] = []
        while self._heap and self._heap[0][0] <= cycle:
            _due, seq, epoch, tag = heapq.heappop(self._heap)
            key = (epoch, tag)
            req = self.outstanding.pop(key, None)
            if req is None:
                raise AssertionError(f"cycle {cycle}: response for tag {tag:#010x} matches no outstanding request")
            if req.seq != seq:
                raise AssertionError(f"cycle {cycle}: response for tag {tag:#010x} matched the wrong request")
            if any(o.seq < seq for o in self.outstanding.values()):
                self.reordered += 1
            if epoch != current_epoch:
                self.cross_epoch_completions += 1
            self.completed += 1
            r = Response(epoch, tag, seq, req.fire_cycle, cycle, req.source, req.desc)
            if self.keep_log:
                self.responses.append(r)
            out.append(r)
        return out

    def next_due(self) -> Optional[int]:
        return self._heap[0][0] if self._heap else None

    def assert_all_complete(self) -> None:
        assert not self.outstanding and not self._heap, f"{len(self.outstanding)} responses never returned"
        assert self.completed == self.issued, f"issued {self.issued}, completed {self.completed}"
