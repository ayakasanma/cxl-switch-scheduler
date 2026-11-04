"""Pure-Python stimulus and statistics helpers of the M5 FAI Main stress / production harnesses.

Nothing in this module reads or drives a DUT pin and nothing here imports cocotb, so it is unit
tested by plain pytest (sim/common/tests/test_fai_stream.py).

* ``StreamStats``: bounded-memory sample statistics (count, mean, min, max and the spec 10
  nearest-rank P99 at sorted 1-based rank ceil(0.99*K)) from an integer histogram. It returns
  exactly what ``traffic_trace.mean`` / ``traffic_trace.nearest_rank_p99`` return for the same
  samples (self-tested), without keeping the samples.
* ``StreamProducers``: per-source producer queues (spec 4: the oldest pending generated descriptor
  is presented with valid held and data stable until pushed) that keep only the PENDING records
  and counters, unlike ``traffic_trace.Producers`` which records every acceptance.
* ``ProductionTraffic``: streaming, seeded intended-traffic / ready generator of the W = 5,000,000
  production runs. Per complete window it applies a designed per-source service-share skew
  (``PRODUCTION_KINDS``) at a total offered load below the output capacity, so every accepted
  descriptor is served within the window it arrives in (up to boundary effects of a few hundred
  cycles out of 5,000,000) and each source's closing evidence is predictable from spec 8.1:
  UP-share sources stay far below 0.3/N, KEEP-share sources between 0.3/N and 1/N, DOWN-share
  sources far above 1/N. ``expected_evidence`` / ``expected_classes`` give the hand-derivable
  spec 8.1 / 8.2 expectation the production test asserts at every closing edge. The ready trace
  adds random bounded stalls plus directed stalls at every window boundary: on odd-numbered
  boundaries an offer is held ACROSS the closing edge, on even-numbered boundaries a stall ends just
  before the closing edge so that the closing edge carries a fire (spec 8.4 step 1-2).
* ``make_fai_stress_trace``: list-based window-scaled class-dynamics trace for the W64 / W256
  stress runs, returned as a ``traffic_trace.Trace`` subclass so the accepted ``run_trace`` replays
  it unchanged. Phases are sized in windows: share skew (hot / medium / cold sources), uniform,
  single-source, flip (two source sets alternating hot per window: opposing evidence), idle
  (no generation for several windows: S = 0 windows after the backlog drains), output stall for
  whole windows (S = 0 windows WITH backlog, offers held across several closing edges, FIFOs full)
  and saturation, plus random long stalls and random / directed resets (mid-window, mid-visit,
  mid-hold).
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
import random
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from traffic_trace import TAG_LSB, TAG_MASK, Trace

PRODUCTION_GENERATOR = "cxl-fai-production-traffic-v1"
STRESS_GENERATOR = "cxl-fai-stress-trace-v2"  # v2: flip phases toggle on absolute window multiples
DESC_W = 105

# ----- statistics -----------------------------------------------------------------------------------


class StreamStats:
    """Exact count / mean / min / max / nearest-rank P99 of integer samples, from a histogram."""

    def __init__(self) -> None:
        self.hist: Dict[int, int] = {}
        self.count = 0
        self.total = 0

    def add(self, value: int) -> None:
        self.hist[value] = self.hist.get(value, 0) + 1
        self.count += 1
        self.total += value

    def p99(self) -> Optional[int]:
        if not self.count:
            return None
        rank = -(-99 * self.count // 100)  # ceil(0.99*K) in integers, as traffic_trace
        seen = 0
        for value in sorted(self.hist):
            seen += self.hist[value]
            if seen >= rank:
                return value
        raise AssertionError("histogram bookkeeping")

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "mean": (self.total / self.count) if self.count else None,
            "p99_nearest_rank": self.p99(),
            "min": min(self.hist) if self.hist else None,
            "max": max(self.hist) if self.hist else None,
            "distinct_values": len(self.hist),
        }


class StreamProducers:
    """Per-source producer queues holding only the pending (generated, not yet pushed) records."""

    def __init__(self, n_src: int) -> None:
        self.n_src = n_src
        self.pending: List[Deque[Tuple[int, int]]] = [deque() for _ in range(n_src)]  # (gen_cycle, desc)
        self.generated = 0
        self.accepted = 0
        self.max_backlog = 0

    def generate(self, k: int, events: List[Tuple[int, int]]) -> None:
        for s, d in events:
            self.pending[s].append((k, d))
            self.generated += 1
        if events:
            self.max_backlog = max(self.max_backlog, self.backlog())

    def offers(self) -> Dict[int, Tuple[int, int]]:
        return {h: q[0] for h, q in enumerate(self.pending) if q}

    def accept(self, source: int, push_cycle: int) -> Tuple[int, int]:
        if not self.pending[source]:
            raise AssertionError(f"source {source} accepted but its producer presented nothing")
        gen_cycle, desc = self.pending[source].popleft()
        if push_cycle < gen_cycle:
            raise AssertionError(f"source {source} pushed at {push_cycle} before generation {gen_cycle}")
        self.accepted += 1
        return gen_cycle, desc

    def backlog(self) -> int:
        return sum(len(q) for q in self.pending)


def _tag(serial: int, offset: int) -> int:
    if not 0 <= serial < (1 << 32):
        raise ValueError("tag space exhausted")
    return (serial * 0x9E3779B1 + offset) & TAG_MASK  # odd multiplier: a bijection on 32 bits


# ----- production traffic ---------------------------------------------------------------------------

# Per complete window (cycled every 4 windows) and source group g = h % 4: the intended evidence
# of that window. Sources of group g follow (from H, spec 8.2):
#   g0: DOWN, DOWN, UP,   UP    -> B_H, L,   B_L, H    (High -> Low -> High through both buffers)
#   g1: DOWN, UP,   DOWN, DOWN  -> B_H, H,   B_H, L    (opposing evidence cancels B_H, later Low)
#   g2: UP,   KEEP, DOWN, KEEP  -> H,   H,   B_H, H    (KEEP cancels a pending decrease)
#   g3: DOWN, DOWN, KEEP, UP    -> B_H, L,   L,   B_L
# Every window has at least one DOWN group and one non-DOWN group, so the shares below are
# consistent (sum 1) with a DOWN share strictly above 1/N.
PRODUCTION_KINDS = (
    ("DOWN", "DOWN", "UP", "DOWN"),
    ("DOWN", "UP", "KEEP", "DOWN"),
    ("UP", "DOWN", "DOWN", "KEEP"),
    ("UP", "DOWN", "KEEP", "UP"),
)
SHARE_UP = 0.15  # x 1/N: half of the UP threshold 0.3/N
SHARE_KEEP = 0.65  # x 1/N: inside [0.3/N, 1/N]
PRODUCTION_LOAD = 0.55  # total offered descriptors per cycle (< ready capacity ~0.91)
PRODUCTION_P_READY = 0.92
PRODUCTION_STALL_EVERY = 40000  # mean cycles between random stalls
PRODUCTION_STALL_LEN = (64, 512)
BOUNDARY_STALL = 40  # directed stall half-length around each window boundary
SPEC_8_2 = {
    "H": {"UP": "H", "DOWN": "B_H", "KEEP": "H", "S0": "H"},
    "B_H": {"UP": "H", "DOWN": "L", "KEEP": "H", "S0": "H"},
    "L": {"UP": "B_L", "DOWN": "L", "KEEP": "L", "S0": "L"},
    "B_L": {"UP": "H", "DOWN": "L", "KEEP": "L", "S0": "L"},
}


def production_kinds(n_src: int, window_no: int) -> List[str]:
    """Intended evidence of every source for window ``window_no`` (0-based)."""
    if n_src % 4:
        raise ValueError("production traffic needs N divisible by 4 (groups h % 4)")
    row = PRODUCTION_KINDS[window_no % len(PRODUCTION_KINDS)]
    return [row[h % 4] for h in range(n_src)]


def production_shares(n_src: int, window_no: int) -> List[float]:
    """Designed service share of every source in window ``window_no`` (sums to 1)."""
    kinds = production_kinds(n_src, window_no)
    n_up, n_keep, n_down = kinds.count("UP"), kinds.count("KEEP"), kinds.count("DOWN")
    assert n_down >= 1 and n_up + n_keep >= 1
    down = (1.0 - (n_up * SHARE_UP + n_keep * SHARE_KEEP) / n_src) / n_down
    table = {"UP": SHARE_UP / n_src, "KEEP": SHARE_KEEP / n_src, "DOWN": down}
    return [table[k] for k in kinds]


def expected_classes(n_src: int, windows: int, *, interpretation: str = "main") -> List[List[str]]:
    """Class map after each of ``windows`` closings from the all-H reset state (spec 8.2 table)."""
    if interpretation == "alg2":
        if n_src != 4 or not 0 <= windows <= 4:
            raise ValueError("Algorithm-2 production expectations cover N4 and the first four windows")
        # Spec 8.6 applied by hand to PRODUCTION_KINDS; independent of the oracle/harness tables.
        rows = (
            ("BUFFER_P_LOW", "BUFFER_P_LOW", "STABLE_HIGH", "BUFFER_P_LOW"),
            ("STABLE_LOW", "STABLE_HIGH", "STABLE_HIGH", "STABLE_LOW"),
            ("BUFFER_P_HIGH", "BUFFER_P_LOW", "BUFFER_P_LOW", "STABLE_LOW"),
            ("STABLE_HIGH", "STABLE_LOW", "BUFFER_P_LOW", "BUFFER_P_HIGH"),
        )
        return [list(row) for row in rows[:windows]]
    if interpretation != "main":
        raise ValueError(f"unknown FAI interpretation: {interpretation}")
    cls = ["H"] * n_src
    out = []
    for w in range(windows):
        cls = [SPEC_8_2[c][e] for c, e in zip(cls, production_kinds(n_src, w))]
        out.append(list(cls))
    return out


class ProductionTraffic:
    """Streaming intended trace of one production run; call ``step(k)`` for k = 0, 1, 2, ..."""

    def __init__(self, seed: int, n_src: int, cycles: int, window: int) -> None:
        if n_src % 4 or n_src < 4:
            raise ValueError("N must be 4, 8 or 16")
        if window <= 4 * BOUNDARY_STALL:
            raise ValueError("window too short for the directed boundary stalls")
        self.seed, self.n, self.cycles, self.window = seed, n_src, cycles, window
        self.rng = random.Random(f"{PRODUCTION_GENERATOR}:{seed}:{n_src}:{cycles}:{window}")
        self.serial = 0
        self.k = 0
        self.stall_left = 0
        self.random_stalls = 0
        self.ready_cycles = 0
        self.generated_per_source = [0] * n_src
        self.generated_per_window: List[List[int]] = []
        self._heap: List[Tuple[int, int]] = []
        self._window_no = -1
        self._sha = hashlib.sha256()
        self._sha.update((json.dumps(self.config(), sort_keys=True, separators=(",", ":")) + "\n").encode())

    def config(self) -> dict:
        return {
            "generator": PRODUCTION_GENERATOR,
            "seed": self.seed,
            "n_src": self.n,
            "cycles": self.cycles,
            "window": self.window,
            "kinds": [list(r) for r in PRODUCTION_KINDS],
            "share_up_x_n": SHARE_UP,
            "share_keep_x_n": SHARE_KEEP,
            "load": PRODUCTION_LOAD,
            "p_ready": PRODUCTION_P_READY,
            "stall_every": PRODUCTION_STALL_EVERY,
            "stall_len": list(PRODUCTION_STALL_LEN),
            "boundary_stall": BOUNDARY_STALL,
            "desc_w": DESC_W,
        }

    def _next_gap(self, p: float) -> int:
        u = 1.0 - self.rng.random()  # (0, 1]
        return int(math.log(u) / math.log1p(-p)) + 1 if p < 1.0 else 1

    def _start_window(self, window_no: int, k: int) -> None:
        self._window_no = window_no
        self.generated_per_window.append([0] * self.n)
        self._heap = []
        for h, share in enumerate(production_shares(self.n, window_no)):
            p = PRODUCTION_LOAD * share
            heapq.heappush(self._heap, (k - 1 + self._next_gap(p), h))
        self._p = [PRODUCTION_LOAD * s for s in production_shares(self.n, window_no)]

    def _ready(self, k: int) -> int:
        w, pos = divmod(k, self.window)
        # Directed boundary stalls. Boundary b (b >= 1) is between window b-1's closing edge
        # (position W-1) and window b's position 0. Odd b: ready=0 from W-B .. W-1 and 0 .. B-1
        # (an offer is held across the closing edge). Even b: ready=0 from W-B .. W-3, ready=1 at
        # W-2 and W-1 (the closing edge carries a fire whenever anything is outstanding).
        b = w + 1  # boundary closing this window
        if pos >= self.window - BOUNDARY_STALL:
            if b % 2 == 1:
                return 0
            return 1 if pos >= self.window - 2 else 0
        if pos < BOUNDARY_STALL and w >= 1 and w % 2 == 1:
            return 0  # tail of the held-across stall of odd boundary w
        if self.stall_left:
            self.stall_left -= 1
            return 0
        if self.rng.random() < 1.0 / PRODUCTION_STALL_EVERY:
            self.stall_left = self.rng.randint(*PRODUCTION_STALL_LEN) - 1
            self.random_stalls += 1
            return 0
        return int(self.rng.random() < PRODUCTION_P_READY)

    def step(self, k: int) -> Tuple[List[Tuple[int, int]], int]:
        """(generation events, ready) of trace cycle k (strictly sequential)."""
        assert k == self.k, f"ProductionTraffic.step({k}) out of order (expected {self.k})"
        self.k += 1
        window_no = k // self.window
        if window_no != self._window_no:
            self._start_window(window_no, k)
        events = []
        while self._heap and self._heap[0][0] == k:
            _c, h = heapq.heappop(self._heap)
            desc = (_tag(self.serial, 0x6B6B0000) << TAG_LSB) | self.rng.getrandbits(TAG_LSB)
            self.serial += 1
            events.append((h, desc))
            self.generated_per_source[h] += 1
            self.generated_per_window[-1][h] += 1
            heapq.heappush(self._heap, (k + self._next_gap(self._p[h]), h))
        events.sort()
        ready = self._ready(k)
        self.ready_cycles += ready
        line = ",".join(f"{s}:{d:027x}" for s, d in events)
        self._sha.update(f"{k} r{ready} {line}\n".encode())
        return events, ready

    @property
    def sha256(self) -> str:
        assert self.k == self.cycles, "hash of an incomplete trace"
        return self._sha.hexdigest()

    @property
    def generated(self) -> int:
        return self.serial


# ----- stress trace ---------------------------------------------------------------------------------

STRESS_PHASES = ("skew", "skew", "uniform", "single", "flip", "idle", "stall", "saturate")


class FaiStressTrace(Trace):
    """``traffic_trace.Trace`` with its own generator identity (not a traffic_trace profile)."""

    window: int = 0

    def summary(self) -> dict:
        kinds: Dict[str, int] = {}
        for _s, length, kind in self.phases:
            kinds[kind] = kinds.get(kind, 0) + length
        return {
            "generator": STRESS_GENERATOR,
            "seed": self.seed,
            "n_src": self.n_src,
            "cycles": self.cycles,
            "profile": self.profile,
            "window": self.window,
            "sha256": self.sha256,
            "generated": self.generated,
            "generated_per_source": [sum(1 for g in self.gen for s, _d in g if s == h) for h in range(self.n_src)],
            "ready_cycles": sum(self.ready),
            "reset_cycles": sum(self.reset),
            "phase_count": len(self.phases),
            "phase_cycles_by_kind": dict(sorted(kinds.items())),
            "long_stalls": len(self.long_stalls),
        }


def _stress_sha256(tr: FaiStressTrace) -> str:
    h = hashlib.sha256()
    header = {"generator": STRESS_GENERATOR, "seed": tr.seed, "n_src": tr.n_src, "cycles": tr.cycles,
              "window": tr.window, "phases": list(STRESS_PHASES), "desc_w": DESC_W}  # fmt: skip
    h.update((json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n").encode())
    for k in range(tr.cycles):
        events = ",".join(f"{s}:{d:027x}" for s, d in tr.gen[k])
        h.update(f"{k} r{tr.ready[k]} x{tr.reset[k]} {events}\n".encode())
    return h.hexdigest()


def make_fai_stress_trace(seed: int, n_src: int, cycles: int, window: int) -> FaiStressTrace:
    """Deterministic window-scaled stress trace (independent of the DUT)."""
    if n_src < 4 or cycles < 1 or window < 16:
        raise ValueError("n_src >= 4, cycles >= 1, window >= 16")
    rng = random.Random(f"{STRESS_GENERATOR}:{seed}:{n_src}:{cycles}:{window}")
    tr = FaiStressTrace(seed, n_src, cycles, f"fai-stress-w{window}")
    tr.window = window
    tr.gen = [[] for _ in range(cycles)]
    tr.ready = bytearray(cycles)
    tr.reset = bytearray(cycles)
    directed_reset = int(0.5 * cycles)
    serial = 0
    k = 0
    stall_left = 0
    reset_left = 0
    round_kinds: List[str] = []
    while k < cycles:
        if not round_kinds:
            round_kinds = list(STRESS_PHASES)
            rng.shuffle(round_kinds)
        kind = round_kinds.pop()
        n_win = rng.randint(1, 4)
        length = min(n_win * window + rng.randint(-window // 4, window // 4), cycles - k)
        length = max(length, 1)
        p_ready = rng.choice((1.0, 0.9, 0.75))
        sources = list(range(n_src))
        rng.shuffle(sources)
        flip_sets = None
        if kind == "skew":
            hot = sources[: rng.randint(1, max(1, n_src // 4))]
            cold = sources[len(hot) : len(hot) + rng.randint(1, n_src // 2)]
            weights = [4.0 if h in hot else rng.uniform(0.0, 0.05) if h in cold else 1.0 for h in range(n_src)]
            load = rng.uniform(0.5, 1.3)
        elif kind == "uniform":
            weights = [rng.uniform(0.8, 1.2) for _ in range(n_src)]
            load = rng.uniform(0.3, 1.1)
        elif kind == "single":
            weights = [1.0 if h == sources[0] else 0.0 for h in range(n_src)]
            load = rng.uniform(0.4, 1.0)
        elif kind == "flip":
            # Two disjoint sets alternate hot on ABSOLUTE window multiples (aligned with the FAI
            # windows unless a reset shifted them): DOWN for the hot set, UP for the cold one in
            # consecutive windows, i.e. opposing evidence (B_H/UP, B_L/DOWN, H -> B_H -> H ...).
            cut = rng.randint(1, n_src // 2)
            flip_sets = (sources[:cut], sources[cut : 2 * cut])
            weights = [1.0] * n_src
            load = rng.uniform(0.5, 0.9)
            length = min(rng.randint(3, 7) * window, cycles - k)
        elif kind == "idle":
            weights = [1.0] * n_src
            load = 0.0
            p_ready = 1.0
            length = min((n_win + 1) * window, cycles - k)
        elif kind == "stall":
            weights = [rng.uniform(0.5, 1.5) for _ in range(n_src)]
            load = rng.uniform(0.2, 0.8)
            p_ready = 0.0
            length = min(n_win * window + rng.randint(0, window - 1), cycles - k)
        else:  # saturate
            weights = [rng.uniform(0.5, 1.5) for _ in range(n_src)]
            load = 2.0
            p_ready = rng.choice((0.3, 0.6, 1.0))
        tr.phases.append((k, length, kind))

        def p_gen(kk: int) -> List[float]:
            if flip_sets is not None:
                hot = flip_sets[(kk // window) % 2]
                wts = [4.0 if h in hot else 0.02 for h in range(n_src)]
            else:
                wts = weights
            total = sum(wts) or 1.0
            return [min(1.0, load * w / total) for w in wts]

        probs = p_gen(k)
        for kk in range(k, k + length):
            if flip_sets is not None and kk % window == 0:
                probs = p_gen(kk)
            if reset_left == 0 and rng.random() < 1.0 / (25 * window):
                reset_left = rng.randint(1, 3)
            if reset_left:
                tr.reset[kk] = 1
                reset_left -= 1
            if directed_reset <= kk < directed_reset + 2:
                tr.reset[kk] = 1
            if kind != "stall" and stall_left == 0 and rng.random() < 1.0 / (8 * window):
                stall_left = rng.randint(window // 4, window)
                tr.long_stalls.append((kk, min(stall_left, cycles - kk), "random"))
            if stall_left:
                tr.ready[kk] = 0
                stall_left -= 1
            else:
                tr.ready[kk] = int(rng.random() < p_ready)
            for h in range(n_src):
                if probs[h] and rng.random() < probs[h]:
                    desc = (_tag(serial, 0x3C3C0000) << TAG_LSB) | rng.getrandbits(TAG_LSB)
                    serial += 1
                    tr.gen[kk].append((h, desc))
        if kind == "stall":
            tr.long_stalls.append((k, length, "directed-phase"))
        k += length
    tr.long_stalls.sort()
    tr.sha256 = _stress_sha256(tr)
    return tr
