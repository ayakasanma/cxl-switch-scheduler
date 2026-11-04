"""Policy-independent intended-traffic and downstream-ready trace generator (spec 9, 10).

The trace is a pure function of (seed, n_src, cycles, profile). It never looks at the DUT, so the
same intended trace can be replayed for FCFS (M3), RR (M4) and FAI, and differences in actual
input acceptance are attributable to the policy alone. Nothing in this module reads a DUT pin.

Contents, indexed by trace cycle k = 0 .. cycles-1 (cycle 0 is the first cycle after the initial
reset):

* generation events gen[k] = [(source, descriptor)]. The descriptor is a full 105-bit value whose
  32-bit Tag [104:73] is globally unique within the trace (a bijection of a per-trace serial
  number, so never reused within a run / epoch); the other 73 bits are random. A descriptor
  generated in cycle k joins the source's producer queue at the beginning of cycle k.
* ready[k]: downstream out_ready during cycle k. Bounded random per-phase ready patterns, random
  long stalls, and DIRECTED long stalls at fixed fractions of the trace (always present).
* reset[k]: rst_n held low during cycle k (only profiles that declare resets; directed resets at
  fixed fractions plus random ones).

Load phases are visited in rounds; every round visits every phase kind of the profile once in a
seeded shuffled order, so overload phases (offered load > 1 descriptor/cycle in total, and a
one-hot burst source) are guaranteed in every trace longer than one round.

Producers: each source has an unbounded producer queue. Its oldest pending generated descriptor
is presented with valid held and data stable until it is pushed (spec 4). The actual push cycle
is recorded separately (``AcceptRecord``); what is still pending is "generated but unaccepted".

``trace_sha256`` hashes a canonical text serialisation (header with the generator version and the
full profile configuration as canonical JSON, then one line per cycle with ready, reset and the
generation events). The same (seed, n_src, cycles, profile) always gives the same hash, so a later
RR/FAI run can prove it replayed the identical intended trace.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, NamedTuple, Optional, Tuple

GENERATOR_VERSION = "cxl-traffic-trace-v2"
DESC_W = 105
TAG_LSB = 73
TAG_MASK = (1 << 32) - 1
# Tag permutation: serial -> (serial * odd + offset) mod 2^32 is a bijection on 32-bit values.
_TAG_MULT = 0x9E3779B1
_TAG_OFFSET = 0x5A5A0000

# Phase kinds: (total offered load per cycle as a multiple of 1 fire/cycle, ready probabilities).
# The load is split over the sources by a per-phase weight vector.
PHASES = {
    "idle": (0.0, (1.0,)),
    "light": (0.3, (1.0, 0.9)),
    "balanced": (0.9, (1.0, 0.95, 0.8)),
    "overload": (1.6, (1.0, 0.9, 0.6)),
    "burst_one": (1.2, (1.0, 0.7)),  # most load on one source: its FIFO fills
    "saturate": (2.0, (0.5, 0.2, 0.05)),  # every FIFO fills, downstream slow
}
OVERLOAD_KINDS = ("overload", "burst_one", "saturate")

PROFILES = {
    # 100,000-cycle primary measurement profile: no resets.
    "primary": {
        "phases": ["light", "balanced", "overload", "burst_one", "saturate", "idle"],
        "phase_len": [300, 2500],
        "long_stall_every": 4000,  # mean cycles between random long stalls
        "long_stall_len": [64, 400],
        "directed_stalls": [[0.25, 256], [0.5, 1024], [0.75, 512]],  # (fraction, length)
        "reset_every": None,
        "directed_resets": [],
    },
    # Short random profile for the per-seed M3 random test: resets included.
    "short": {
        "phases": ["light", "balanced", "overload", "burst_one", "saturate", "idle"],
        "phase_len": [100, 600],
        "long_stall_every": 1200,
        "long_stall_len": [40, 200],
        "directed_stalls": [[0.3, 300], [0.7, 150]],
        "reset_every": 2500,
        "reset_len": [1, 3],
        "directed_resets": [[0.5, 2]],
    },
}


@dataclass
class Trace:
    seed: int
    n_src: int
    cycles: int
    profile: str
    gen: List[List[Tuple[int, int]]] = field(default_factory=list)  # gen[k] = [(source, desc)]
    ready: bytearray = field(default_factory=bytearray)
    reset: bytearray = field(default_factory=bytearray)
    phases: List[Tuple[int, int, str]] = field(default_factory=list)  # (start, length, kind)
    long_stalls: List[Tuple[int, int, str]] = field(default_factory=list)  # (start, len, "random"|"directed")
    sha256: str = ""

    @property
    def generated(self) -> int:
        return sum(len(g) for g in self.gen)

    def summary(self) -> dict:
        kinds: Dict[str, int] = {}
        for _s, length, kind in self.phases:
            kinds[kind] = kinds.get(kind, 0) + length
        return {
            "generator": GENERATOR_VERSION,
            "seed": self.seed,
            "n_src": self.n_src,
            "cycles": self.cycles,
            "profile": self.profile,
            "profile_cfg": PROFILES[self.profile],
            "sha256": self.sha256,
            "generated": self.generated,
            "generated_per_source": [
                sum(1 for g in self.gen for s, _d in g if s == h) for h in range(self.n_src)
            ],
            "ready_cycles": sum(self.ready),
            "reset_cycles": sum(self.reset),
            "phase_count": len(self.phases),
            "phase_cycles_by_kind": dict(sorted(kinds.items())),
            "long_stalls": [list(x) for x in self.long_stalls],
        }


def _tag(serial: int) -> int:
    if not 0 <= serial < (1 << 32):
        raise ValueError("tag space exhausted")
    return (serial * _TAG_MULT + _TAG_OFFSET) & TAG_MASK


def tag_of(desc: int) -> int:
    return (desc >> TAG_LSB) & TAG_MASK


def _directed_windows(spec: List[List[float]], cycles: int) -> List[Tuple[int, int]]:
    out = []
    for frac, length in spec:
        start = int(frac * cycles)
        length = min(int(length), cycles - start)
        if length > 0:
            out.append((start, length))
    return out


def make_trace(seed: int, n_src: int, cycles: int, profile: str) -> Trace:
    """The intended trace for (seed, n_src, cycles, profile). Deterministic, DUT-independent."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}")
    if n_src < 2 or cycles < 1:
        raise ValueError("n_src >= 2 and cycles >= 1 required")
    cfg = PROFILES[profile]
    rng = random.Random(f"{GENERATOR_VERSION}:{seed}:{n_src}:{cycles}:{profile}")
    tr = Trace(seed, n_src, cycles, profile)
    tr.gen = [[] for _ in range(cycles)]
    tr.ready = bytearray(cycles)
    tr.reset = bytearray(cycles)

    directed_stall = bytearray(cycles)
    for start, length in _directed_windows(cfg["directed_stalls"], cycles):
        directed_stall[start : start + length] = b"\x01" * length
        tr.long_stalls.append((start, length, "directed"))
    directed_reset = bytearray(cycles)
    for start, length in _directed_windows(cfg["directed_resets"], cycles):
        directed_reset[start : start + length] = b"\x01" * length

    serial = 0
    k = 0
    stall_left = 0
    reset_left = 0
    round_kinds: List[str] = []
    while k < cycles:
        if not round_kinds:
            round_kinds = list(cfg["phases"])
            rng.shuffle(round_kinds)
        kind = round_kinds.pop()
        length = min(rng.randint(*cfg["phase_len"]), cycles - k)
        load, ready_choices = PHASES[kind]
        p_ready = rng.choice(ready_choices)
        if kind == "burst_one":
            hot = rng.randrange(n_src)
            weights = [0.7 if h == hot else 0.3 / (n_src - 1) for h in range(n_src)]
        else:
            raw = [rng.uniform(0.5, 1.5) for _ in range(n_src)]
            total = sum(raw)
            weights = [w / total for w in raw]
        p_gen = [min(1.0, load * w) for w in weights]
        tr.phases.append((k, length, kind))
        for kk in range(k, k + length):
            # Reset (random part; directed resets are OR-ed in).
            if cfg["reset_every"] and reset_left == 0 and rng.random() < 1.0 / cfg["reset_every"]:
                reset_left = rng.randint(*cfg["reset_len"])
            if reset_left:
                tr.reset[kk] = 1
                reset_left -= 1
            if directed_reset[kk]:
                tr.reset[kk] = 1
            # Ready (random long stalls, per-phase random pattern; directed stalls override).
            if stall_left == 0 and rng.random() < 1.0 / cfg["long_stall_every"]:
                stall_left = rng.randint(*cfg["long_stall_len"])
                tr.long_stalls.append((kk, min(stall_left, cycles - kk), "random"))
            if stall_left:
                tr.ready[kk] = 0
                stall_left -= 1
            else:
                tr.ready[kk] = int(rng.random() < p_ready)
            if directed_stall[kk]:
                tr.ready[kk] = 0
            # Generation.
            for h in range(n_src):
                if rng.random() < p_gen[h]:
                    desc = (_tag(serial) << TAG_LSB) | rng.getrandbits(TAG_LSB)
                    serial += 1
                    tr.gen[kk].append((h, desc))
        k += length
    tr.long_stalls.sort()
    tr.sha256 = trace_sha256(tr)
    return tr


def trace_sha256(tr: Trace) -> str:
    """SHA-256 over the canonical text form: header line(s), then one line per cycle."""
    h = hashlib.sha256()
    header = {
        "generator": GENERATOR_VERSION,
        "seed": tr.seed,
        "n_src": tr.n_src,
        "cycles": tr.cycles,
        "profile": tr.profile,
        "profile_cfg": PROFILES[tr.profile],
        "desc_w": DESC_W,
    }
    h.update((json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n").encode())
    for k in range(tr.cycles):
        events = ",".join(f"{s}:{d:027x}" for s, d in tr.gen[k])
        h.update(f"{k} r{tr.ready[k]} x{tr.reset[k]} {events}\n".encode())
    return h.hexdigest()


class AcceptRecord(NamedTuple):
    source: int
    gen_cycle: int  # trace cycle the descriptor was generated in
    push_cycle: int  # trace cycle whose closing edge accepted it (actual DUT acceptance)
    desc: int


class Producers:
    """Per-source producer queues: the oldest pending generated descriptor of each source is
    presented with valid held and data stable until it is pushed (spec 4).

    Generation (``generate``) comes only from the trace; acceptance (``accept``) is reported by the
    environment from the observed DUT handshake and is recorded separately. The two never mix:
    acceptance cannot create, drop or reorder a generated descriptor."""

    def __init__(self, n_src: int) -> None:
        self.n_src = n_src
        self.pending: List[Deque[Tuple[int, int]]] = [deque() for _ in range(n_src)]  # (gen_cycle, desc)
        self.generated = 0
        self.accepted: List[AcceptRecord] = []

    def generate(self, k: int, events: List[Tuple[int, int]]) -> None:
        for s, d in events:
            self.pending[s].append((k, d))
            self.generated += 1

    def offers(self) -> Dict[int, Tuple[int, int]]:
        """source -> (gen_cycle, desc) currently presented (valid=1)."""
        return {h: q[0] for h, q in enumerate(self.pending) if q}

    def accept(self, source: int, push_cycle: int) -> AcceptRecord:
        """The presented descriptor of ``source`` was pushed at the closing edge of push_cycle."""
        if not self.pending[source]:
            raise AssertionError(f"source {source} accepted but its producer presented nothing")
        gen_cycle, desc = self.pending[source].popleft()
        if push_cycle < gen_cycle:
            raise AssertionError(f"source {source} pushed at {push_cycle} before generation {gen_cycle}")
        rec = AcceptRecord(source, gen_cycle, push_cycle, desc)
        self.accepted.append(rec)
        return rec

    def backlog(self) -> int:
        return sum(len(q) for q in self.pending)

    def all_pending(self) -> List[Tuple[int, int, int]]:
        return [(h, g, d) for h, q in enumerate(self.pending) for g, d in q]


def nearest_rank_p99(samples: List[int]) -> Optional[int]:
    """Nearest-rank P99: sorted 1-based rank ceil(0.99*K); None (N/A) for no samples."""
    if not samples:
        return None
    s = sorted(samples)
    k = len(s)
    rank = -(-99 * k // 100)  # ceil(0.99*K) exactly in integers
    return s[rank - 1]


def mean(samples: List[int]) -> Optional[float]:
    """Arithmetic mean; None (N/A) for no samples."""
    return (sum(samples) / len(samples)) if samples else None
