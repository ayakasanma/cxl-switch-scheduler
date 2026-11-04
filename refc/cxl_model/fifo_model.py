"""Abstract cycle-level model of one per-source descriptor FIFO (specs/CXL_SPEC.md v1.0, section 4).

The model is a plain queue of entries. It has no pointers, no storage array and no occupancy
counter; occupancy is simply the queue length. Time advances in two explicit steps per cycle:

1. ``view(rst_n)`` returns what is observable during cycle *c*, i.e. before the closing rising
   edge. It depends only on the beginning-of-cycle queue contents (and on reset).
2. ``commit(...)`` applies the closing rising edge of cycle *c* using the inputs presented during
   that cycle. Its effects are visible from cycle *c+1* on.

Contract implemented (spec sections 3-6):

* ``in_ready`` is ``occupancy < depth`` when not in reset. It never anticipates a same-edge pop, so
  a full queue refuses a push even when its head leaves on that edge.
* ``push = in_valid and in_ready``. The pushed entry joins the tail and is not observable (and
  cannot be popped) before the next cycle: there is no empty bypass.
* A pop request removes the head only when the queue was nonempty at the beginning of the cycle.
  A pop request on an empty queue does nothing.
* Simultaneous push and pop leaves occupancy unchanged and preserves order.
* A rising edge with ``rst_n`` low empties the queue and starts a new epoch; nothing is pushed or
  popped on that edge. ``in_ready`` is low while ``rst_n`` is low.
* With arrival metadata enabled every entry carries the timestamp presented at its push edge.
  Without it no timestamp is kept at all.

The FIFO itself does not suppress ``head_valid`` during reset: it reports beginning-of-cycle
occupancy. Suppressing the output handshake in reset is the job of the common output controller.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Iterable, NamedTuple, Optional, Tuple

FIFO_DEPTH = 16
TS_WIDTH = 32

# Approved packed slices, most to least significant: (name, msb, lsb). Spec section 3.
DESC_FIELDS: Tuple[Tuple[str, int, int], ...] = (
    ("tag", 104, 73),
    ("addr", 72, 41),
    ("opcode", 40, 40),
    ("length", 39, 32),
    ("payload", 31, 0),
)
DESC_WIDTH = 105


def pack_desc(tag: int, addr: int, opcode: int, length: int, payload: int) -> int:
    """Pack descriptor fields into the approved 105-bit layout."""
    values = {"tag": tag, "addr": addr, "opcode": opcode, "length": length, "payload": payload}
    desc = 0
    for name, msb, lsb in DESC_FIELDS:
        width = msb - lsb + 1
        value = values[name]
        if not 0 <= value < (1 << width):
            raise ValueError(f"{name}={value:#x} does not fit in {width} bits")
        desc |= value << lsb
    return desc


def unpack_desc(desc: int) -> dict:
    """Split a 105-bit descriptor into its approved fields."""
    if not 0 <= desc < (1 << DESC_WIDTH):
        raise ValueError(f"descriptor {desc:#x} does not fit in {DESC_WIDTH} bits")
    return {name: (desc >> lsb) & ((1 << (msb - lsb + 1)) - 1) for name, msb, lsb in DESC_FIELDS}


class Entry(NamedTuple):
    """One queued request. ``ts`` is None when arrival metadata is disabled."""

    desc: int
    ts: Optional[int]


class FifoView(NamedTuple):
    """Observable state during a cycle (before its closing edge)."""

    in_ready: bool
    head_valid: bool
    count: int
    head_desc: Optional[int]  # None while empty (not meaningful)
    head_ts: Optional[int]  # None while empty or when arrival metadata is disabled


class EdgeResult(NamedTuple):
    """What one rising edge did."""

    reset: bool
    pushed: Optional[Entry]
    popped: Optional[Entry]


class FifoModel:
    """Abstract per-source queue with beginning-of-cycle readiness and next-cycle visibility."""

    def __init__(
        self,
        depth: int = FIFO_DEPTH,
        ts_enabled: bool = False,
        desc_width: int = DESC_WIDTH,
        ts_width: int = TS_WIDTH,
    ) -> None:
        if depth < 1:
            raise ValueError("depth must be at least 1")
        self.depth = depth
        self.ts_enabled = bool(ts_enabled)
        self.desc_width = desc_width
        self.ts_width = ts_width
        self._queue: Deque[Entry] = deque()
        self.epoch = 0  # incremented by every reset edge
        self.pushes = 0  # accepted pushes in the current epoch
        self.pops = 0  # completed pops in the current epoch

    # ----- beginning-of-cycle observation ------------------------------------------------------

    @property
    def occupancy(self) -> int:
        return len(self._queue)

    @property
    def empty(self) -> bool:
        return not self._queue

    @property
    def full(self) -> bool:
        return len(self._queue) >= self.depth

    def head(self) -> Optional[Entry]:
        """Head entry eligible during the current cycle, or None when empty."""
        return self._queue[0] if self._queue else None

    def entries(self) -> Tuple[Entry, ...]:
        """Queue contents, head first."""
        return tuple(self._queue)

    def view(self, rst_n: bool = True) -> FifoView:
        """Observable values for the current cycle given the reset level during it."""
        head = self.head()
        return FifoView(
            in_ready=bool(rst_n) and not self.full,
            head_valid=head is not None,
            count=len(self._queue),
            head_desc=None if head is None else head.desc,
            head_ts=None if head is None else head.ts,
        )

    # ----- closing edge --------------------------------------------------------------------------

    def commit(
        self,
        rst_n: bool = True,
        in_valid: bool = False,
        in_desc: int = 0,
        in_ts: Optional[int] = None,
        pop: bool = False,
    ) -> EdgeResult:
        """Apply one rising edge with the inputs held during the closing cycle."""
        if not rst_n:
            self._queue.clear()
            self.epoch += 1
            self.pushes = 0
            self.pops = 0
            return EdgeResult(reset=True, pushed=None, popped=None)

        # Both decisions use the queue as it stood at the beginning of the cycle.
        do_push = bool(in_valid) and not self.full
        do_pop = bool(pop) and not self.empty

        popped = self._queue.popleft() if do_pop else None
        pushed = None
        if do_push:
            pushed = self._make_entry(in_desc, in_ts)
            self._queue.append(pushed)

        self.pushes += int(do_push)
        self.pops += int(do_pop)
        assert len(self._queue) <= self.depth
        return EdgeResult(reset=False, pushed=pushed, popped=popped)

    def _make_entry(self, in_desc: int, in_ts: Optional[int]) -> Entry:
        if not 0 <= in_desc < (1 << self.desc_width):
            raise ValueError(f"descriptor {in_desc:#x} does not fit in {self.desc_width} bits")
        if not self.ts_enabled:
            return Entry(in_desc, None)
        if in_ts is None:
            raise ValueError("arrival metadata is enabled: a timestamp is required on push")
        if not 0 <= in_ts < (1 << self.ts_width):
            raise ValueError(f"timestamp {in_ts:#x} does not fit in {self.ts_width} bits")
        return Entry(in_desc, in_ts)

    def __len__(self) -> int:
        return len(self._queue)

    def __iter__(self) -> Iterable[Entry]:
        return iter(tuple(self._queue))
