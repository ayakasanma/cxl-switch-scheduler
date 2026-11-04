"""MODEL_ONLY measurement and diagnosis harness for the CXL scheduler study.

The harness deliberately keeps the accepted queue/hold controller as the only queueing
implementation.  ``WrrSwitchModel`` and ``IwrrSwitchModel`` are model baselines for this
study; they are not RTL policies and their semantics are stated below.  The mixed lane
contains finite Heavy work and deterministic Sparse background traffic.  Its paired
isolated lane replays the same Heavy events and ready schedule without Sparse traffic.

All output is model evidence.  A fire is one model service event, never a measured memory
transaction or a memory-bandwidth result.
"""
from __future__ import annotations

from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys
from typing import Any, Deque, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
for _folder in (
    ROOT / "sim" / "performance",
    ROOT / "sim" / "switch_top_fai",
    ROOT / "sim" / "common",
):
    _path = str(_folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from followup import Gaps, STAGES  # noqa: E402
from fai_stream import StreamProducers, StreamStats  # noqa: E402

from .common_ctrl_model import Candidate, CommonCtrlModel, NO_CANDIDATE  # noqa: E402
from .experimental import ExperimentalSwitchModel  # noqa: E402
from .fai_main_model import EFFECTIVE_CLASS, HIGH, window_widths  # noqa: E402

MODEL_SCOPE = "MODEL_ONLY"
SCHEMA = "cxl-model-diagnosis-v1"
ARRIVAL_COMMON_GENERATION_CONTRACT = "cxl-arrival-common-generation-v1"
QUOTA_BACKLOG_HISTORY_CONTRACT = "cxl-quota-predecision-backlog-v1"
DEFAULT_N_SRC = 4
DEFAULT_DEPTH = 16
DEFAULT_WINDOW = 5_000_000
DEFAULT_WINDOWS = 3
DEFAULT_SPARSE_P = 0.05
DEFAULT_READY_P = 0.90
DEFAULT_HEAVY_P = 1.0
LOAD_PROFILES = {
    # Offered Heavy descriptors/cycle versus one model fire per ready cycle.
    "under": {"heavy_p": 0.25, "sparse_p": 0.02, "ready_p": 0.90},
    "near": {"heavy_p": 0.80, "sparse_p": 0.02, "ready_p": 0.90},
    "over": {"heavy_p": 1.00, "sparse_p": 0.05, "ready_p": 0.90},
    # Saturated common demand: every source offers one request per ready cycle.
    "equal": {"heavy_p": 1.00, "sparse_p": 1.00, "ready_p": 1.00},
}
EXPLORATION_SEEDS = tuple(range(6101, 6106))
CONFIRMATION_SEEDS = tuple(range(6201, 6221))
MIN_LONG_RUN_WINDOWS = 3

WRR_SEMANTICS = (
    "chosen benchmark variant: contiguous weighted quota in source-index order; active "
    "set is snapshotted at round start; empty sources are skipped; unused quota is "
    "discarded and not banked"
)
IWRR_SEMANTICS = (
    "chosen benchmark variant: interleaved weighted subrounds in source-index order "
    "(2:1:1 -> 0,1,2,0); active set is snapshotted at round start; empty sources are "
    "skipped without restarting a round; unused slots are discarded and not banked"
)


def _stats(value: StreamStats) -> Dict[str, Any]:
    return {
        **value.as_dict(),
        "histogram": {str(k): v for k, v in sorted(value.hist.items())},
    }


def jsonable(value: Any) -> Any:
    """Convert the small set of harness records to JSON-safe values."""
    if isinstance(value, StreamStats):
        return _stats(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(jsonable(value), sort_keys=True, separators=(",", ":"))


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_seed_groups() -> None:
    """Fail closed if the declared independent cohorts overlap or change."""
    if tuple(EXPLORATION_SEEDS) != tuple(range(6101, 6106)):
        raise AssertionError("exploration seeds must be exactly 6101..6105")
    if tuple(CONFIRMATION_SEEDS) != tuple(range(6201, 6221)):
        raise AssertionError("confirmation seeds must be exactly 6201..6220")
    if set(EXPLORATION_SEEDS) & set(CONFIRMATION_SEEDS):
        raise AssertionError("exploration and confirmation seeds overlap")


def seed_role_for(seeds: Sequence[int]) -> str:
    """Return the declared cohort containing exactly ``seeds``."""
    validate_seed_groups()
    actual = tuple(sorted(seeds))
    if actual == EXPLORATION_SEEDS:
        return "exploration"
    if actual == CONFIRMATION_SEEDS:
        return "confirmation"
    raise ValueError("seeds must be exactly the declared exploration or confirmation cohort")


def policy_configs() -> List[Dict[str, Any]]:
    """The small, prespecified model matrix used by the runner and plots."""
    return [
        {"family": "FAI-inspired", "policy": "FAI-inspired"},
        {"family": "FCFS", "policy": "FCFS"},
        {"family": "RR10", "policy": "RR10"},
        {"family": "CGOF", "policy": "CGOF", "high_weight": 1, "ordering": "oldest-first"},
        {"family": "CGOF", "policy": "CGOF", "high_weight": 2, "ordering": "oldest-first"},
        {"family": "CGOF", "policy": "CGOF", "high_weight": 1, "ordering": "eligible-round-robin"},
        {"family": "CGOF", "policy": "CGOF", "high_weight": 2, "ordering": "eligible-round-robin"},
        {"family": "WRR", "weights": (2, 1, 1, 1), "model_only": True},
        {"family": "IWRR", "weights": (2, 1, 1, 1), "model_only": True},
    ]


def config_identity(config: Dict[str, Any]) -> str:
    family = config["family"]
    if family == "CGOF":
        return f"CGOF_w{config['high_weight']}_{config['ordering']}"
    if family in ("WRR", "IWRR"):
        return f"{family}_weights{'-'.join(str(x) for x in config['weights'])}"
    return str(family)


def model_config(config: Dict[str, Any], n_src: int, window: int, depth: int) -> Dict[str, Any]:
    result = {
        "family": config["family"],
        "n_src": n_src,
        "window": window,
        "depth": depth,
        "scope": MODEL_SCOPE,
    }
    if config["family"] == "CGOF":
        result.update(high_weight=config["high_weight"], ordering=config["ordering"],
                      policy="CGOF", refill="only when no active source has positive credit",
                      held="snapshot retained until fire or reset")
    elif config["family"] in ("WRR", "IWRR"):
        result.update(weights=list(config["weights"]),
                      semantics=WRR_SEMANTICS if config["family"] == "WRR" else IWRR_SEMANTICS,
                      controller="accepted CommonCtrlModel", model_only=True)
    else:
        result["policy"] = config["policy"]
    return result


def make_model(config: Dict[str, Any], n_src: int, window: int, depth: int):
    family = config["family"]
    if family == "CGOF":
        return ExperimentalSwitchModel(
            n_src=n_src, policy="CGOF", window=window, depth=depth,
            high_weight=config["high_weight"], ordering=config["ordering"],
        )
    if family in ("FAI-inspired", "FCFS", "RR10"):
        return ExperimentalSwitchModel(n_src=n_src, policy=family, window=window, depth=depth)
    if family == "WRR":
        return WrrSwitchModel(n_src=n_src, weights=config["weights"], window=window, depth=depth)
    if family == "IWRR":
        return IwrrSwitchModel(n_src=n_src, weights=config["weights"], window=window, depth=depth)
    raise ValueError(f"unknown model family {family!r}")


def _cycle_fraction(seed: int, stream: str, k: int, source: int = 0) -> float:
    """A pure deterministic [0,1) value, so paired lanes replay identical inputs."""
    raw = hashlib.sha256(
        f"cxl-model-diagnosis-v1:{seed}:{stream}:{k}:{source}".encode("ascii")
    ).digest()
    return int.from_bytes(raw[:8], "big") / float(1 << 64)


def _descriptor(seed: int, stream: str, k: int, source: int) -> int:
    raw = hashlib.sha256(
        f"cxl-model-diagnosis-desc-v1:{seed}:{stream}:{k}:{source}".encode("ascii")
    ).digest()
    serial = int.from_bytes(raw[:8], "big")
    # 105-bit descriptor: stream tag, release cycle, source, and a deterministic suffix.
    return ((1 if stream == "heavy" else 2) << 100) | ((k & 0xFFFFFFFF) << 32) | (
        (source & 0xF) << 24
    ) | (serial & 0xFFFFFF)


class DiagnosisScenario:
    """Finite Heavy release plus deterministic Sparse background until Heavy completes.

    ``heavy_work`` is the finite number of Heavy requests released.  A release opportunity
    occurs on each cycle with ``heavy_p`` until that count is reached.  Sparse sources
    ``1..N-1`` independently generate with ``sparse_p`` on every active cycle.  The
    heavy-only lane replays exactly the same Heavy events and ready schedule.  Methods
    are pure, so the mixed and isolated lanes receive identical exogenous inputs.
    """

    def __init__(
        self,
        seed: int,
        n_src: int = DEFAULT_N_SRC,
        window: int = DEFAULT_WINDOW,
        windows: int = DEFAULT_WINDOWS,
        heavy_work: Optional[int] = None,
        heavy_p: float = DEFAULT_HEAVY_P,
        sparse_p: float = DEFAULT_SPARSE_P,
        ready_p: float = DEFAULT_READY_P,
        subwindow: Optional[int] = None,
        heavy_sources: Optional[Sequence[int]] = None,
        ready_pattern: str = "bernoulli",
        ready_period: int = 100,
    ) -> None:
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if type(n_src) is not int or n_src < 2:
            raise ValueError("n_src must be at least 2")
        if type(windows) is not int or windows < 1:
            raise ValueError("windows must be a positive integer")
        window_widths(window)
        if heavy_work is None:
            heavy_work = windows * window
        if type(heavy_work) is not int or heavy_work < 1:
            raise ValueError("heavy_work must be a positive integer")
        if not 0.0 <= heavy_p <= 1.0 or not 0.0 <= sparse_p <= 1.0 or not 0.0 <= ready_p <= 1.0:
            raise ValueError("heavy_p, sparse_p and ready_p must be in [0, 1]")
        if heavy_p == 0.0:
            raise ValueError("heavy_p must be positive for finite Heavy work")
        if subwindow is None:
            subwindow = max(1, window // 4)
        if type(subwindow) is not int or subwindow < 1:
            raise ValueError("subwindow must be a positive integer")
        heavy_sources = tuple(heavy_sources) if heavy_sources is not None else (0,)
        if not heavy_sources or any(type(h) is not int or not 0 <= h < n_src
                                    for h in heavy_sources):
            raise ValueError("heavy_sources must contain valid source indices")
        if ready_pattern not in ("bernoulli", "spread", "bursty"):
            raise ValueError("ready_pattern must be bernoulli, spread or bursty")
        if type(ready_period) is not int or ready_period < 1:
            raise ValueError("ready_period must be a positive integer")
        if ready_pattern != "bernoulli" and not math.isclose(
            ready_p * ready_period, round(ready_p * ready_period), abs_tol=1e-9
        ):
            raise ValueError("periodic ready_p * ready_period must be an integer")
        self.seed, self.n_src, self.window, self.windows = seed, n_src, window, windows
        self.heavy_work, self.heavy_p = heavy_work, float(heavy_p)
        self.sparse_p, self.ready_p = float(sparse_p), float(ready_p)
        self.subwindow = subwindow
        self.heavy_sources = heavy_sources
        self.ready_pattern, self.ready_period = ready_pattern, ready_period
        self.load_profile_name = "custom"

    @classmethod
    def load_profile(
        cls,
        seed: int,
        profile: str,
        **kwargs: Any,
    ) -> "DiagnosisScenario":
        """Construct an offered-load case without implying measured memory capacity."""
        if profile not in LOAD_PROFILES:
            raise ValueError(f"load profile must be one of {sorted(LOAD_PROFILES)}")
        values = dict(LOAD_PROFILES[profile])
        # ``None`` means "use the profile value", not "replace it with a default".
        values.update({key: value for key, value in kwargs.items() if value is not None})
        scenario = cls(seed=seed, **values)
        scenario.load_profile_name = profile
        return scenario

    def config(self) -> Dict[str, Any]:
        result = {
            "generator": "cxl-model-diagnosis-scenario-v1",
            "seed": self.seed,
            "n_src": self.n_src,
            "window": self.window,
            "windows": self.windows,
            "heavy_source": 0,
            "heavy_work": self.heavy_work,
            "heavy_release": "one request per heavy_p opportunity until heavy_work releases",
            "heavy_p": self.heavy_p,
            "load_profile": self.load_profile_name,
            "sparse_sources": list(range(1, self.n_src)),
            "sparse_p": self.sparse_p,
            "sparse_stop": "when finite Heavy work completes",
            "ready_p": self.ready_p,
            "subwindow": self.subwindow,
            "timing": "events generated before the closing edge; model-only cycle index",
        }
        if self.heavy_sources != (0,):
            result.update(heavy_source=None, sparse_sources=None,
                          heavy_sources_by_window=list(self.heavy_sources),
                          role_schedule="one source per generation window; last entry repeats")
        if self.ready_pattern != "bernoulli":
            result.update(ready_pattern=self.ready_pattern, ready_period=self.ready_period,
                          ready_slots_per_period=round(self.ready_p * self.ready_period))
        return result

    def heavy_source(self, k: int) -> int:
        return self.heavy_sources[min(max(0, k) // self.window, len(self.heavy_sources) - 1)]

    def heavy_opportunity(self, k: int) -> bool:
        return k >= 0 and _cycle_fraction(self.seed, "heavy", k, 0) < self.heavy_p

    def heavy_events(self, k: int, ordinal: Optional[int] = None) -> List[Tuple[int, int]]:
        """Heavy event at release opportunity ``k``, capped at ``heavy_work`` releases.

        Lanes pass their local release ordinal so the same scenario object can feed both
        paired lanes without mutable generator state.  Without an ordinal, this helper
        counts prior opportunities; that convenience is intended for small tests only.
        """
        if not self.heavy_opportunity(k):
            return []
        if ordinal is None:
            ordinal = sum(self.heavy_opportunity(j) for j in range(k))
        if ordinal >= self.heavy_work:
            return []
        source = self.heavy_source(k)
        return [(source, _descriptor(self.seed, "heavy", k, source))]

    def sparse_events(self, k: int) -> List[Tuple[int, int]]:
        if k < 0:
            return []
        return [
            (h, _descriptor(self.seed, "sparse", k, h))
            for h in range(self.n_src)
            if h != self.heavy_source(k)
            and _cycle_fraction(self.seed, "sparse", k, h) < self.sparse_p
        ]

    def heavy_release_end_exclusive(self) -> int:
        """First cycle after the last declared finite-Heavy release."""
        released = 0
        for k in range(sys.maxsize):
            if self.heavy_opportunity(k):
                released += 1
                if released == self.heavy_work:
                    return k + 1
        raise AssertionError("finite Heavy release did not terminate")

    def declared_heavy_arrivals(self, cycles: int) -> List[List[int]]:
        if type(cycles) is not int or cycles < 1:
            raise ValueError("cycles must be a positive integer")
        arrivals: List[List[int]] = []
        released = 0
        for k in range(cycles):
            events = self.heavy_events(k, released)
            released += len(events)
            for source, desc in events:
                arrivals.append([k, source, desc])
        return arrivals

    def declared_sparse_work_multiset(self, cycles: int) -> List[List[int]]:
        if type(cycles) is not int or cycles < 1:
            raise ValueError("cycles must be a positive integer")
        events = [
            [source, desc]
            for k in range(cycles)
            for source, desc in self.sparse_events(k)
        ]
        return sorted(events)

    def declared_ready_schedule(self, cycles: int) -> List[List[int]]:
        if type(cycles) is not int or cycles < 1:
            raise ValueError("cycles must be a positive integer")
        return [[k, self.ready(k)] for k in range(cycles)]

    def ready(self, k: int) -> int:
        if self.ready_pattern != "bernoulli":
            position, slots = k % self.ready_period, round(self.ready_p * self.ready_period)
            if self.ready_pattern == "bursty":
                return int(position < slots)
            return int((position + 1) * slots // self.ready_period
                       > position * slots // self.ready_period)
        return int(_cycle_fraction(self.seed, "ready", k) < self.ready_p)

    def input_prefix_sha256(self, cycles: int, include_sparse: bool = True) -> str:
        h = hashlib.sha256()
        released = 0
        for k in range(cycles):
            heavy = self.heavy_events(k, released)
            released += len(heavy)
            sparse = self.sparse_events(k) if include_sparse else []
            h.update(
                f"{k}:{self.ready(k)}:{heavy!r}:{sparse!r}\n".encode("utf-8")
            )
        return h.hexdigest()


class RoleBook:
    """Attribute completions to generation roles, including work pending at a switch."""

    def __init__(self, scenario: DiagnosisScenario) -> None:
        self.scenario = scenario
        self.counts = {r: {s: [0] * scenario.n_src for s in
                          ("generated", "accepted", "fired", "active_fired")}
                       for r in ("heavy", "sparse")}
        self.latency = {r: {s: StreamStats() for s in STAGES} for r in self.counts}
        self.bursts = {}
        self.gaps = [Gaps() for _ in range(scenario.n_src)]
        self.cut = None

    def role(self, generation: int, source: int) -> str:
        return "heavy" if source == self.scenario.heavy_source(generation) else "sparse"

    def observe(self, k, events, accepts, fired, ready, active=True) -> None:
        heavy = self.counts["heavy"]
        before = [a - f for a, f in zip(heavy["accepted"], heavy["fired"])]
        for source, _ in events:
            role = self.role(k, source)
            self.counts[role]["generated"][source] += 1
            if role == "heavy":
                burst = self.bursts.setdefault(k // self.scenario.window, dict(
                    source=source, generated=0, completed=0, completed_in_drain=0,
                    first_release=k, last_release=k, last_fire=None))
                burst["generated"] += 1
                burst["last_release"] = k
        for generation, source in accepts:
            self.counts[self.role(generation, source)]["accepted"][source] += 1
        heavy_fire = None
        if fired is not None:
            generation, acceptance, source = fired
            role = self.role(generation, source)
            self.counts[role]["fired"][source] += 1
            self.counts[role]["active_fired"][source] += int(active)
            for stage, value in zip(STAGES, (acceptance-generation, k-acceptance, k-generation)):
                self.latency[role][stage].add(value)
            if role == "heavy":
                heavy_fire = source
                burst = self.bursts[generation // self.scenario.window]
                burst["completed"] += 1
                burst["completed_in_drain"] += int(not active)
                burst["last_fire"] = k
        if active:
            for source, gap in enumerate(self.gaps):
                after = heavy["accepted"][source] - heavy["fired"][source]
                gap.observe(before[source] > 0, heavy_fire == source, ready, after > 0)

    def snapshot_cut(self) -> None:
        for gap in self.gaps:
            gap.boundary(False)
        self.cut = {role: {key: list(value) for key, value in counts.items()}
                    for role, counts in self.counts.items()}

    def as_dict(self) -> dict:
        pooled = {}
        for gap in self.gaps:
            for kind, values in gap.samples.items():
                target = pooled.setdefault(kind, [StreamStats(), StreamStats()])
                for dest, value in zip(target, values):
                    for sample, count in value.hist.items():
                        dest.hist[sample] = dest.hist.get(sample, 0) + count
                    dest.count += value.count
                    dest.total += value.total
        gap_data = {"samples": {kind: {
            "wall_cycles": _stats(values[0]),
            "eligible_ready_opportunities": _stats(values[1]),
        } for kind, values in pooled.items()}}
        cut = self.cut or self.counts
        sparse = cut["sparse"]
        return dict(
            attribution="source role at generation; cohorts survive role switches and drain",
            counts=self.counts, at_cut=cut,
            latency={r: {s: _stats(v) for s, v in stages.items()}
                     for r, stages in self.latency.items()},
            sparse_fairness=fairness_summary(sparse["active_fired"], sparse["generated"]),
            heavy_gaps=gap_data,
            heavy_gaps_per_source=[gap.as_dict() for gap in self.gaps],
            bursts=[dict(burst_id=key, **value,
                         first_release_to_last_fire=(
                             value["last_fire"] - value["first_release"]
                             if value["last_fire"] is not None else None))
                    for key, value in sorted(self.bursts.items())],
        )


def jain_index(values: Sequence[float]) -> Optional[float]:
    """Jain index, or ``None`` when no positive service/demand exists."""
    clean = [float(v) for v in values]
    if any(not math.isfinite(v) or v < 0 for v in clean):
        raise ValueError("Jain inputs must be finite nonnegative numbers")
    total = sum(clean)
    if total <= 0:
        return None
    return total * total / (len(clean) * sum(v * v for v in clean))


def fairness_summary(
    service: Sequence[int],
    demand: Sequence[int],
    weights: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    """Demand-referenced fairness with zero-demand sources excluded.

    Raw Jain over all sources is retained for transparency, but the primary demand
    reference uses only sources that generated work.  A source with zero demand can
    therefore never force a divide-by-zero or an artificial fairness target.  The
    normalized error compares achieved service shares with demand shares, not with
    delivered service itself; ``active_service_jain`` is explicitly the raw Jain of
    that delivered subset.
    """
    if len(service) != len(demand):
        raise ValueError("service and demand must have equal length")
    if any(type(v) is not int or v < 0 for v in service + demand):
        raise ValueError("service and demand must be nonnegative integers")
    if weights is not None:
        if len(weights) != len(service):
            raise ValueError("weights must match service length")
        weights = [float(w) for w in weights]
        if any(not math.isfinite(w) or w < 0 for w in weights):
            raise ValueError("weights must be finite nonnegative numbers")
    active = [h for h, d in enumerate(demand) if d > 0]
    raw = jain_index(service)
    if not active:
        return {
            "raw_jain_all": raw,
            "active_service_jain": None,
            "demand_share_l1_error": None,
            "demand_share_max_error": None,
            "weighted_jain_active": None,
            "weighted_service_share": {},
            "weighted_share_l1_error": None,
            "weighted_share_max_error": None,
            "active_sources": [],
            "idle_sources": list(range(len(demand))),
            "demand_reference_share": {},
            "weighted_reference_share": {},
        }
    demand_total = sum(demand[h] for h in active)
    demand_share = {h: demand[h] / demand_total for h in active}
    service_active = [service[h] for h in active]
    result: Dict[str, Any] = {
        "raw_jain_all": raw,
        "active_service_jain": jain_index(service_active),
        "demand_share_l1_error": None,
        "demand_share_max_error": None,
        "weighted_jain_active": None,
        "weighted_service_share": {},
        "weighted_share_l1_error": None,
        "weighted_share_max_error": None,
        "active_sources": active,
        "idle_sources": [h for h in range(len(demand)) if h not in active],
        "demand_reference_share": demand_share,
        "weighted_reference_share": {},
    }
    service_share: Dict[int, float] = {}
    if service_active and sum(service_active) > 0:
        service_total = sum(service_active)
        service_share = {h: service[h] / service_total for h in active}
        errors = [abs(service_share[h] - demand_share[h]) for h in active]
        result["demand_share_l1_error"] = sum(errors)
        result["demand_share_max_error"] = max(errors)
    if weights is not None:
        positive = [h for h in active if weights[h] > 0]
        weight_total = sum(weights[h] for h in positive)
        if positive and weight_total > 0:
            weighted_reference = {
                h: (weights[h] / weight_total if weights[h] > 0 else 0.0)
                for h in active
            }
            result["weighted_reference_share"] = weighted_reference
            result["weighted_jain_active"] = jain_index(
                [service[h] / weights[h] for h in positive]
            )
            if service_share:
                result["weighted_service_share"] = {
                    h: service_share.get(h, 0.0) for h in active
                }
                weighted_errors = [
                    abs(result["weighted_service_share"][h] - weighted_reference[h])
                    for h in active
                ]
                result["weighted_share_l1_error"] = sum(weighted_errors)
                result["weighted_share_max_error"] = max(weighted_errors)
    return result


def pooled_stage_summary(
    result: Dict[str, Any],
    stage: str,
    sources: Sequence[int],
) -> Dict[str, Any]:
    """Pool completed latency samples across sources without counting censored work as zero."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    if not sources:
        raise ValueError("at least one source is required")
    counts: Counter = Counter()
    for row in result["cohorts"].values():
        for source in sources:
            per_source = row.get("stages_by_source")
            if per_source is None or source >= len(per_source):
                raise ValueError("cohort output lacks per-source latency histograms")
            counts.update({
                int(k): v for k, v in per_source[source][stage]["histogram"].items()
            })
    total = sum(counts.values())
    sample_total = sum(value * count for value, count in counts.items())
    rank = (99 * total + 99) // 100 if total else 0
    seen = 0
    p99 = None
    for value in sorted(counts):
        seen += counts[value]
        if seen >= rank:
            p99 = value
            break
    return {
        "stage": stage,
        "sources": list(sources),
        "count": total,
        "mean": sample_total / total if total else None,
        "max": max(counts) if counts else None,
        "p99_nearest_rank": p99,
    }


def quota_summary(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Observed CGOF service against class quota in fully backlogged active windows.

    Eligibility is established from every beginning-of-cycle local FIFO observation,
    not from the closing snapshot.  The closing snapshot remains diagnostic evidence.
    """
    model = result["model_config"]
    if model["family"] != "CGOF":
        return None
    n_src = result.get("n_src", model.get("n_src"))
    if type(n_src) is not int or n_src < 1:
        raise ValueError("quota summary requires a positive n_src")
    window = result.get("window", model.get("window"))
    if type(window) is not int or window < 1:
        raise ValueError("quota summary requires a positive configured window")
    if model.get("window", window) != window:
        raise ValueError("configured window and model window disagree")

    def count(history: Dict[str, Any], key: str) -> int:
        value = history.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"quota history {key} must be a nonnegative integer")
        return value

    rows = []
    weighted_error = 0.0
    total_fired = 0
    for row in result["classifier_trajectory"]:
        if not isinstance(row, dict):
            raise ValueError("classifier rows must be objects")
        counts = row.get("counts")
        classes = row.get("old_classes")
        if not isinstance(counts, (list, tuple)) or not isinstance(classes, (list, tuple)):
            raise ValueError("classifier row lacks counter or class arrays")
        if len(counts) != len(classes) or len(counts) != n_src:
            raise ValueError("classifier row has inconsistent source dimensions")
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError("classifier row counts must be nonnegative integers")
        fired = sum(counts)
        if row.get("total") is not None and row["total"] != fired:
            raise ValueError("classifier closing total disagrees with counts")
        producer_backlog = row.get("producer_backlog")
        fifo_occupancy = row.get("fifo_occupancy")
        for label, values in (
            ("producer backlog", producer_backlog),
            ("FIFO occupancy", fifo_occupancy),
        ):
            if not isinstance(values, (list, tuple)) or len(values) != n_src:
                raise ValueError(f"closing {label} has inconsistent source dimensions")
            if any(type(value) is not int or value < 0 for value in values):
                raise ValueError(f"closing {label} must contain nonnegative integers")
        weights = [
            model["high_weight"] if EFFECTIVE_CLASS[value] == HIGH else 1
            for value in classes
        ]
        weight_total = sum(weights)
        observed = [value / fired for value in counts] if fired else None
        target = [value / weight_total for value in weights]
        errors = (
            [abs(a - b) for a, b in zip(observed, target)]
            if observed is not None else None
        )
        l1_error = sum(errors) if errors is not None else None
        max_error = max(errors) if errors is not None else None
        closing_backlogged = all(
            producer_backlog[source] + fifo_occupancy[source] > 0
            for source in range(n_src)
        )
        history = row.get("quota_backlog_history")
        eligibility = "UNAVAILABLE"
        ineligible_reason = "missing_predecision_history"
        backlog_eligible = False
        if history is not None:
            if not isinstance(history, dict):
                raise ValueError("quota backlog history must be an object")
            if history.get("contract_version") != QUOTA_BACKLOG_HISTORY_CONTRACT:
                raise ValueError("unsupported quota backlog history contract")
            expected_cycles = count(history, "expected_cycles")
            observed_cycles = count(history, "observed_cycles")
            active_cycles = count(history, "active_cycles")
            drain_cycles = count(history, "drain_cycles")
            ready_cycles = count(history, "ready_cycles")
            held_cycles = count(history, "held_cycles")
            idle_cycles = count(history, "idle_cycles")
            output_stall_cycles = count(history, "output_stall_cycles")
            all_nonempty_cycles = count(history, "all_source_fifo_nonempty_cycles")
            source_nonempty = history.get("source_fifo_nonempty_cycles")
            if expected_cycles != window:
                raise ValueError("quota history window differs from configured window")
            if observed_cycles != active_cycles + drain_cycles:
                raise ValueError("quota history active/drain cycles do not sum to observed")
            for label, value in (
                ("ready", ready_cycles),
                ("held", held_cycles),
                ("idle", idle_cycles),
                ("output stall", output_stall_cycles),
                ("all-nonempty", all_nonempty_cycles),
            ):
                if value > observed_cycles:
                    raise ValueError(f"quota history {label} cycles exceed observed")
            if not isinstance(source_nonempty, (list, tuple)) or len(source_nonempty) != n_src:
                raise ValueError("quota history source dimensions are inconsistent")
            if any(
                type(value) is not int or value < 0 or value > observed_cycles
                for value in source_nonempty
            ):
                raise ValueError("quota history source counters are malformed")
            if idle_cycles == observed_cycles and (
                all_nonempty_cycles or any(source_nonempty)
            ):
                raise ValueError("quota history idle and nonempty counters contradict")
            if any(value > observed_cycles - idle_cycles for value in source_nonempty):
                raise ValueError("quota history source counters exceed non-idle cycles")
            if all_nonempty_cycles > observed_cycles - idle_cycles:
                raise ValueError("quota history all-nonempty cycles exceed non-idle cycles")
            if all_nonempty_cycles == observed_cycles and any(
                value != observed_cycles for value in source_nonempty
            ):
                raise ValueError("quota history all-nonempty and source counters contradict")
            if all_nonempty_cycles > min(source_nonempty, default=0):
                raise ValueError("quota history all-nonempty cycles exceed a source counter")
            if observed_cycles < expected_cycles:
                eligibility = "PARTIAL_WINDOW"
                ineligible_reason = "partial_window"
            elif observed_cycles > expected_cycles:
                raise ValueError("quota history exceeds the configured window")
            elif drain_cycles or active_cycles != expected_cycles or row.get("phase") != "active":
                eligibility = "MIXED_ACTIVE_DRAIN"
                ineligible_reason = "not_an_all_active_window"
            elif all_nonempty_cycles != expected_cycles:
                eligibility = "NOT_ALL_SOURCES_BACKLOGGED"
                ineligible_reason = "source_local_fifo_empty_during_window"
            else:
                eligibility = "ELIGIBLE"
                ineligible_reason = None
                backlog_eligible = True
        included = bool(backlog_eligible and fired)
        rows.append({
            "window": row["window"],
            "closing_cycle": row.get("closing_cycle"),
            "phase": row.get("phase"),
            "classes": list(classes),
            "weights": weights,
            "target_share": target,
            "observed_share": observed,
            "service_share_l1_error": l1_error,
            "service_share_max_error": max_error,
            "closing_snapshot": {
                "producer_backlog": list(producer_backlog),
                "fifo_occupancy": list(fifo_occupancy),
                "all_sources_backlogged": closing_backlogged,
            },
            "closing_snapshot_all_sources_backlogged": closing_backlogged,
            "quota_backlog_history": history,
            "eligibility_status": eligibility,
            "ineligible_reason": ineligible_reason,
            "backlog_eligible": backlog_eligible,
            "included_in_aggregate": included,
        })
        if included:
            weighted_error += l1_error * fired
            total_fired += fired
    return {
        "applicable": True,
        "availability": "AVAILABLE" if total_fired else "UNAVAILABLE",
        "history_contract": QUOTA_BACKLOG_HISTORY_CONTRACT,
        "closing_snapshot_role": "diagnostic_only",
        "interpretation": (
            "policy quota service-share deviation over complete active windows whose "
            "source-local FIFOs were nonempty at every predecision cycle; not full "
            "refill-round compliance, general fairness, RTL evidence, or a common-demand "
            "fairness verdict"
        ),
        "windows": rows,
        "window_count": len(rows),
        "eligible_window_count": sum(row["included_in_aggregate"] for row in rows),
        "backlog_eligible_window_count": sum(row["backlog_eligible"] for row in rows),
        "observed_share_l1_error": weighted_error / total_fired if total_fired else None,
        "observed_share_max_error": (
            max(
                row["service_share_max_error"]
                for row in rows if row["included_in_aggregate"]
            )
            if total_fired else None
        ),
    }


ENDPOINT_METRIC_KEYS = (
    "sparse_completed_generation_to_fire_p99",
    "sparse_completed_count",
    "sparse_censored_at_cut",
    "active_service_jain",
    "active_demand_share_l1_error",
    "quota_share_l1_error",
    "heavy_completion_time_ratio_mixed_over_isolated",
    "heavy_completion_ratio_mixed_over_isolated",
    "heavy_first_release_to_last_fire",
    "heavy_span_ratio_mixed_over_isolated",
    "heavy_active_fire_rate",
    "heavy_throughput_ratio_mixed_over_isolated",
    "heavy_max_service_gap",
    "heavy_inter_service_gap_count",
)


def endpoint_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Scalar model endpoints for paired seed/run comparisons."""
    if result.get("status") != "PASS":
        return {
            "scope": MODEL_SCOPE,
            **{key: None for key in ENDPOINT_METRIC_KEYS},
            "incomplete_endpoints": True,
        }
    mixed = result["mixed"]
    isolated = result["isolated"]
    n_src = result["model_config"]["n_src"]
    sparse = (mixed["generation_roles"]["latency"]["sparse"]["generation_to_fire"]
              if "generation_roles" in mixed else pooled_stage_summary(
                  mixed, "generation_to_fire", tuple(range(1, n_src))))
    demand = mixed["active_demand_fairness"]
    quota = quota_summary(mixed)
    heavy_gap = mixed["heavy"]["gaps"] or {}
    inter_service = heavy_gap.get("samples", {}).get("inter_service", {}).get(
        "wall_cycles", {}
    )
    mixed_heavy_rate = (
        mixed["heavy"]["fired"] / mixed["active_cycles"]
        if mixed["active_cycles"] else None
    )
    isolated_heavy_rate = (
        isolated["heavy"]["fired"] / isolated["active_cycles"]
        if isolated["active_cycles"] else None
    )
    mixed_completion = mixed["heavy"].get("actual_completion_cycle")
    isolated_completion = isolated["heavy"].get("actual_completion_cycle")
    if mixed_completion is None:
        mixed_completion = mixed["cut_cycle"]
    if isolated_completion is None:
        isolated_completion = isolated["cut_cycle"]
    sparse_censored = sum(
        sum(row["unaccepted_at_cut"][1:]) + sum(row["accepted_unfired_at_cut"][1:])
        for row in mixed["cohorts"].values()
    )
    if "generation_roles" in mixed:
        counts = mixed["generation_roles"]["at_cut"]["sparse"]
        sparse_censored = sum(counts["generated"]) - sum(counts["fired"])
    return {
        "scope": MODEL_SCOPE,
        "sparse_completed_generation_to_fire_p99": sparse["p99_nearest_rank"],
        "sparse_completed_count": sparse["count"],
        "sparse_censored_at_cut": sparse_censored,
        "active_service_jain": demand["active_service_jain"],
        "active_demand_share_l1_error": demand["demand_share_l1_error"],
        "quota_share_l1_error": (
            quota["observed_share_l1_error"] if quota is not None else None
        ),
        "heavy_completion_time_ratio_mixed_over_isolated": (
            (mixed_completion + 1) / (isolated_completion + 1)
            if mixed["heavy"]["completed"] and isolated["heavy"]["completed"]
            and mixed_completion is not None and isolated_completion is not None
            else None
        ),
        "heavy_completion_ratio_mixed_over_isolated": (
            (mixed_completion + 1) / (isolated_completion + 1)
            if mixed["heavy"]["completed"] and isolated["heavy"]["completed"]
            and mixed_completion is not None and isolated_completion is not None
            else None
        ),
        "heavy_first_release_to_last_fire": mixed["heavy"]["first_release_to_last_fire"],
        "heavy_span_ratio_mixed_over_isolated": (
            mixed["heavy"]["first_release_to_last_fire"]
            / isolated["heavy"]["first_release_to_last_fire"]
            if mixed["heavy"]["completed"] and isolated["heavy"]["completed"]
            and mixed["heavy"]["first_release_to_last_fire"] is not None
            and isolated["heavy"]["first_release_to_last_fire"] not in (None, 0) else None
        ),
        "heavy_active_fire_rate": mixed_heavy_rate,
        "heavy_throughput_ratio_mixed_over_isolated": (
            mixed_heavy_rate / isolated_heavy_rate
            if mixed_heavy_rate is not None
            and isolated_heavy_rate not in (None, 0) else None
        ),
        "heavy_max_service_gap": inter_service.get("max"),
        "heavy_inter_service_gap_count": inter_service.get("count"),
        "incomplete_endpoints": False,
    }


def heavy_fire_lag_summary(
    mixed_change_points: Sequence[Dict[str, int]],
    isolated_change_points: Sequence[Dict[str, int]],
    *,
    observation_end_exclusive: int,
    mixed_complete: bool,
    isolated_complete: bool,
) -> Dict[str, Any]:
    """Compute post-edge Heavy lag without resampling or truncating to a prefix."""
    if type(observation_end_exclusive) is not int or observation_end_exclusive < 1:
        raise ValueError("observation_end_exclusive must be a positive integer")

    def checked(points: Sequence[Dict[str, int]]) -> List[Tuple[int, int]]:
        result: List[Tuple[int, int]] = []
        previous_cycle, previous_count = -1, 0
        for point in points:
            if not isinstance(point, dict) or set(point) != {
                "cycle", "cumulative_heavy_fires"
            }:
                raise ValueError("lag change points have malformed fields")
            cycle = point["cycle"]
            count = point["cumulative_heavy_fires"]
            if type(cycle) is not int or type(count) is not int:
                raise ValueError("lag change point values must be integers")
            if cycle <= previous_cycle or cycle >= observation_end_exclusive:
                raise ValueError("lag change point cycles must be ordered within observation")
            if count < previous_count:
                raise ValueError("cumulative Heavy fires must be monotonic")
            result.append((cycle, count))
            previous_cycle, previous_count = cycle, count
        return result

    mixed = checked(mixed_change_points)
    isolated = checked(isolated_change_points)
    if mixed_complete and isolated_complete:
        mixed_total = mixed[-1][1] if mixed else 0
        isolated_total = isolated[-1][1] if isolated else 0
        if mixed_total != isolated_total:
            raise ValueError("complete paired lanes have different Heavy totals")

    endpoint_cycle = observation_end_exclusive - 1
    cycles = sorted(
        {0, endpoint_cycle}
        | {cycle for cycle, _count in mixed}
        | {cycle for cycle, _count in isolated}
    )
    rows = []
    mixed_index = isolated_index = 0
    mixed_count = isolated_count = 0
    for cycle in cycles:
        while mixed_index < len(mixed) and mixed[mixed_index][0] <= cycle:
            mixed_count = mixed[mixed_index][1]
            mixed_index += 1
        while (
            isolated_index < len(isolated)
            and isolated[isolated_index][0] <= cycle
        ):
            isolated_count = isolated[isolated_index][1]
            isolated_index += 1
        rows.append({
            "cycle": cycle,
            "mixed_cumulative_heavy_fires": mixed_count,
            "isolated_cumulative_heavy_fires": isolated_count,
            "lag": isolated_count - mixed_count,
        })
    change_cycles = {
        cycle for cycle, _count in mixed
    } | {
        cycle for cycle, _count in isolated
    }
    change_points = [
        row for row in rows if row["cycle"] in change_cycles
    ]
    max_lag = max(row["lag"] for row in rows)
    max_lag_cycle = next(
        row["cycle"] for row in rows if row["lag"] == max_lag
    )
    positive = [row for row in rows if row["lag"] > 0]
    last_positive = positive[-1] if positive else None
    recovery_cycle = None
    recovery_reason = None
    if last_positive is None:
        recovery_reason = "never_positive_lag"
    else:
        recovery_cycle = next(
            (row["cycle"] for row in rows if row["cycle"] > last_positive["cycle"]
             and row["lag"] <= 0),
            None,
        )
        if recovery_cycle is None:
            recovery_reason = (
                "observation_truncated_before_recovery"
                if not mixed_complete or not isolated_complete
                else "observation_ended_before_nonpositive_lag"
            )
    return {
        "lag_convention": "isolated Heavy cumulative fires minus mixed",
        "initial_cumulative_heavy_fires": {"mixed": 0, "isolated": 0},
        "post_edge_change_points": change_points,
        "observation_end_cycle": endpoint_cycle,
        "max_lag": max_lag,
        "max_lag_cycle": max_lag_cycle,
        "endpoint_lag": rows[-1]["lag"],
        "last_positive_lag": (
            None if last_positive is None else last_positive["lag"]
        ),
        "last_positive_lag_cycle": (
            None if last_positive is None else last_positive["cycle"]
        ),
        "recovery_cycle": recovery_cycle,
        "recovered": recovery_cycle is not None,
        "right_censored": last_positive is not None and recovery_cycle is None,
        "recovery_null_reason": recovery_reason,
        "observation_complete": mixed_complete and isolated_complete,
    }


def comparison_specs() -> List[Dict[str, Any]]:
    """Prespecified diagnostic contrasts; candidates and baselines never mix quotas."""
    common = (
        "sparse_completed_generation_to_fire_p99",
        "sparse_censored_at_cut",
        "active_service_jain",
        "active_demand_share_l1_error",
        "heavy_completion_time_ratio_mixed_over_isolated",
        "heavy_span_ratio_mixed_over_isolated",
        "heavy_active_fire_rate",
        "heavy_throughput_ratio_mixed_over_isolated",
        "heavy_max_service_gap",
    )
    cgof = common + ("quota_share_l1_error",)
    return [
        {
            "id": "allocation-1-1-vs-2-1",
            "candidate": "CGOF_w1_oldest-first",
            "baseline": "CGOF_w2_oldest-first",
            "metrics": list(cgof),
        },
        {
            "id": "ordering-1-1",
            "candidate": "CGOF_w1_oldest-first",
            "baseline": "CGOF_w1_eligible-round-robin",
            "metrics": list(cgof),
        },
        {
            "id": "ordering-2-1",
            "candidate": "CGOF_w2_oldest-first",
            "baseline": "CGOF_w2_eligible-round-robin",
            "metrics": list(cgof),
        },
        {
            "id": "wrr-2-1-control",
            "candidate": "CGOF_w2_oldest-first",
            "baseline": "WRR_weights2-1-1-1",
            "metrics": list(common),
        },
        {
            "id": "iwrr-2-1-control",
            "candidate": "CGOF_w2_oldest-first",
            "baseline": "IWRR_weights2-1-1-1",
            "metrics": list(common),
        },
        {
            "id": "fai-inspired-control",
            "candidate": "CGOF_w2_oldest-first",
            "baseline": "FAI-inspired",
            "metrics": list(common),
        },
    ]


def _new_phase_metrics(n_src: int) -> Dict[str, Any]:
    return {
        "cycles": 0,
        "ready_cycles": 0,
        "generated": [0] * n_src,
        "accepted": [0] * n_src,
        "fired": [0] * n_src,
        "output_transfers": 0,
        "eligible_ready_cycles": 0,
        "avoidable_bubbles": 0,
        "output_stall_cycles": 0,
        "idle_ready_cycles": 0,
        "idle_not_ready_cycles": 0,
    }


class WeightedEdge(NamedTuple):
    reset: bool
    pushed: tuple
    fired: object
    closing: object
    choice_source: Optional[int]
    quota_state: Dict[str, Any]


class _WeightedBase:
    """MODEL_ONLY weighted benchmark base using the accepted common controller.

    A round's active set is snapshotted only when that round is planned.  Empty sources
    and zero quotas are skipped without inventing work.  Policy state changes only when
    an offer actually fires; a held offer retains the complete selected plan.
    """

    family = ""
    semantics = ""

    def __init__(self, n_src: int, weights: Sequence[int], window: int = DEFAULT_WINDOW,
                 depth: int = DEFAULT_DEPTH, desc_width: int = 105, ts_width: int = 32) -> None:
        if n_src < 2:
            raise ValueError("n_src must be at least 2")
        if len(weights) != n_src or any(type(w) is not int or w < 1 for w in weights):
            raise ValueError("weights must contain one positive integer per source")
        window_widths(window)
        self.n_src, self.weights, self.window, self.depth = n_src, tuple(weights), window, depth
        self.ctrl = CommonCtrlModel(n_src, depth, False, 1, desc_width, ts_width)
        self.state_known = False
        self.time = 0
        self._reset_policy()

    def _reset_policy(self) -> None:
        self.service = [0] * self.n_src
        self.b = [0] * self.n_src
        self.s = 0
        self.win_pos = 0
        self.windows_closed = 0
        self.round_index = 0
        self.round_active: Tuple[int, ...] = ()
        self.round_remaining: Dict[int, int] = {}
        self.slot_sources: Tuple[int, ...] = ()
        self.slot_pos = 0
        self._held_plan: Optional[Dict[str, Any]] = None

    def occupancy(self, source: int) -> int:
        return self.ctrl.occupancy(source)

    def classes(self):
        return None

    def _active(self) -> Tuple[int, ...]:
        return tuple(h for h in range(self.n_src) if self.ctrl.occupancy(h) > 0)

    def _fresh_plan(self, active: Tuple[int, ...]) -> Dict[str, Any]:
        raise NotImplementedError

    def _choose_plan(self, active: Tuple[int, ...]) -> Dict[str, Any]:
        raise NotImplementedError

    def _commit_plan(self, plan: Dict[str, Any]) -> None:
        raise NotImplementedError

    def choice(self) -> Optional[int]:
        if not self.state_known:
            return None
        active = self._active()
        return None if not active else int(self._choose_plan(active)["selected"])

    def held_choice(self) -> Optional[int]:
        """Selected source retained across a stall, or ``None`` without a held grant."""
        return None if self._held_plan is None else int(self._held_plan["selected"])

    def _candidate(self) -> Candidate:
        source = self.choice()
        return NO_CANDIDATE if source is None else Candidate(True, source, 0)

    def view(self, out_ready: bool = False, rst_n: bool = True):
        return self.ctrl.view(self._candidate(), out_ready, rst_n)

    def quota_state(self) -> Dict[str, Any]:
        return {
            "round": self.round_index,
            "round_active": list(self.round_active),
            "remaining": dict(sorted(self.round_remaining.items())),
            "slot_sources": list(self.slot_sources),
            "slot_pos": self.slot_pos,
        }

    def commit(self, out_ready: bool = False, in_valid=None, in_desc=None, rst_n: bool = True):
        if not rst_n:
            edge = self.ctrl.commit(NO_CANDIDATE, out_ready, None, None, None, rst_n=False)
            self._reset_policy()
            self.state_known = True
            return WeightedEdge(True, edge.pushed, None, None, None, self.quota_state())
        if not self.state_known:
            raise AssertionError("reset required before use")
        if self.ctrl.held is not None and self._held_plan is None:
            raise AssertionError("held weighted grant has no retained plan")
        # Plan from beginning-of-cycle state.  In particular, do not consult occupancy
        # after this edge's pop/accept when a source singleton drains.
        active = self._active()
        plan = self._choose_plan(active) if active else None
        if plan is None:
            # With no beginning-of-cycle work there is no round to retain.  Unused
            # quota is discarded rather than banked for a future re-entry.
            self._clear_round()
        choice = None if plan is None else int(plan["selected"])
        candidate = NO_CANDIDATE if choice is None else Candidate(True, choice, 0)
        held_before = self.ctrl.held
        edge = self.ctrl.commit(candidate, out_ready, in_valid, in_desc, None, rst_n=True)
        fired = edge.fired
        source = fired.source if fired is not None else None
        if source is not None:
            if plan is None or choice != source:
                raise AssertionError("weighted fire lacks its selected pre-edge plan")
            self.service[source] += 1
            self.b[source] += 1
            self.s += 1
            if held_before is not None:
                assert source == held_before.source and plan is self._held_plan
            self._commit_plan(plan)
        if edge.latched is not None:
            self._held_plan = plan
        elif self.ctrl.held is None:
            self._held_plan = None
        closing = None
        self.win_pos += 1
        if self.win_pos == self.window:
            closing = {
                "window": self.windows_closed,
                "counts": tuple(self.b),
                "total": self.s,
                "evidence": None,
                "old_classes": None,
                "classes": None,
                "credits": None,
                "quota_state": self.quota_state(),
            }
            self.windows_closed += 1
            self.win_pos = 0
            self.b = [0] * self.n_src
            self.s = 0
        self.time += 1
        return WeightedEdge(False, edge.pushed, fired, closing, choice, self.quota_state())

    def _clear_round(self) -> None:
        self.round_active = ()
        self.round_remaining = {}
        self.slot_sources = ()
        self.slot_pos = 0

    def _decrement(self, plan: Dict[str, Any]) -> None:
        selected = int(plan["selected"])
        if self.round_remaining.get(selected, 0) <= 0:
            raise AssertionError("selected weighted source has no remaining quota")
        self.round_remaining[selected] -= 1


class WrrSwitchModel(_WeightedBase):
    """MODEL_ONLY benchmark variant: contiguous per-source quota per round.

    This is the chosen source-index benchmark, not a claim that every standard WRR
    definition snapshots its active set at the same instant.
    """

    family = "WRR"
    semantics = WRR_SEMANTICS

    def _fresh_plan(self, active: Tuple[int, ...]) -> Dict[str, Any]:
        if not active:
            return {
                "round": self.round_index,
                "active": (),
                "remaining": {},
                "selected": None,
                "slots": (),
                "slot": 0,
            }
        return {
            "round": self.round_index + 1,
            "active": active,
            "remaining": {h: self.weights[h] for h in active},
            "selected": active[0],
            "slots": (),
            "slot": 0,
        }

    def _choose_plan(self, active: Tuple[int, ...]) -> Dict[str, Any]:
        if self.ctrl.held is not None:
            if self._held_plan is None:
                raise AssertionError("held weighted grant has no retained WRR plan")
            plan = self._held_plan
            if plan["selected"] not in active:
                raise AssertionError("held WRR source is absent from pre-edge occupancy")
            return plan
        if self.round_index == 0:
            return self._fresh_plan(active)
        if self.round_active:
            selected = next(
                (h for h in self.round_active
                 if h in active and self.round_remaining.get(h, 0) > 0),
                None,
            )
            if selected is not None:
                return {
                    "round": self.round_index,
                    "active": self.round_active,
                    "remaining": dict(self.round_remaining),
                    "selected": selected,
                    "slots": (),
                    "slot": 0,
                }
        # The snapshotted round is exhausted; start one from the current active set.
        return self._fresh_plan(active)

    def _commit_plan(self, plan: Dict[str, Any]) -> None:
        selected = int(plan["selected"])
        if plan["remaining"].get(selected, 0) <= 0:
            raise AssertionError("selected weighted source has no remaining quota")
        self.round_index = plan["round"]
        self.round_active = plan["active"]
        self.round_remaining = dict(plan["remaining"])
        self.round_remaining[selected] -= 1
        self.slot_sources, self.slot_pos = (), 0


class IwrrSwitchModel(_WeightedBase):
    """MODEL_ONLY benchmark variant: interleaved weighted subrounds.

    ``weights=(2,1,1)`` produces ``0,1,2,0``.  This is contiguous weighted-slot
    interleaving, not the WRR contiguous-quota sequence ``0,0,1,2``.
    """

    family = "IWRR"
    semantics = IWRR_SEMANTICS

    @staticmethod
    def _slots(active: Tuple[int, ...], weights: Sequence[int]) -> Tuple[int, ...]:
        return tuple(
            h for subround in range(max((weights[h] for h in active), default=0))
            for h in active if weights[h] > subround
        )

    def _fresh_plan(self, active: Tuple[int, ...]) -> Dict[str, Any]:
        if not active:
            return {
                "round": self.round_index,
                "active": (),
                "remaining": {},
                "selected": None,
                "slots": (),
                "slot": 0,
            }
        slots = self._slots(active, self.weights)
        return {
            "round": self.round_index + 1,
            "active": active,
            "remaining": {h: self.weights[h] for h in active},
            "selected": slots[0],
            "slots": slots,
            "slot": 0,
        }

    def _choose_plan(self, active: Tuple[int, ...]) -> Dict[str, Any]:
        if self.ctrl.held is not None:
            if self._held_plan is None:
                raise AssertionError("held weighted grant has no retained IWRR plan")
            plan = self._held_plan
            if plan["selected"] not in active:
                raise AssertionError("held IWRR source is absent from pre-edge occupancy")
            return plan
        if self.round_index == 0:
            return self._fresh_plan(active)
        if self.slot_sources:
            for index in range(self.slot_pos, len(self.slot_sources)):
                source = self.slot_sources[index]
                if source in active and self.round_remaining.get(source, 0) > 0:
                    return {
                        "round": self.round_index,
                        "active": self.round_active,
                        "remaining": dict(self.round_remaining),
                        "selected": source,
                        "slots": self.slot_sources,
                        "slot": index,
                    }
        return self._fresh_plan(active)

    def _commit_plan(self, plan: Dict[str, Any]) -> None:
        self.round_index = plan["round"]
        self.round_active = plan["active"]
        self.round_remaining = dict(plan["remaining"])
        self.slot_sources = plan["slots"]
        self.slot_pos = int(plan["slot"]) + 1
        selected = int(plan["selected"])
        if self.round_remaining.get(selected, 0) <= 0:
            raise AssertionError("selected weighted source has no remaining quota")
        self.round_remaining[selected] -= 1
        # Quota exhaustion is not the end of the slot sequence: source 0 can exhaust
        # its two slots before the remaining source-index slots of the round.
        while self.slot_pos < len(self.slot_sources):
            source = self.slot_sources[self.slot_pos]
            if self.round_remaining.get(source, 0) > 0:
                break
            self.slot_pos += 1


class CohortBook:
    """Generation-window cohorts retained through acceptance, fire and drain."""

    def __init__(self, n_src: int, window: int) -> None:
        self.n_src, self.window = n_src, window
        self.rows: Dict[int, Dict[str, Any]] = {}

    def _row(self, generation_cycle: int) -> Dict[str, Any]:
        cohort = generation_cycle // self.window
        if cohort not in self.rows:
            self.rows[cohort] = {
                "generation_window": cohort,
                "generated": [0] * self.n_src,
                "accepted": [0] * self.n_src,
                "fired": [0] * self.n_src,
                "unaccepted_at_cut": [0] * self.n_src,
                "accepted_unfired_at_cut": [0] * self.n_src,
                "fired_at_cut": [0] * self.n_src,
                "completed_after_cut": [0] * self.n_src,
                "stages": {stage: StreamStats() for stage in STAGES},
                "stages_by_source": [
                    {stage: StreamStats() for stage in STAGES}
                    for _ in range(self.n_src)
                ],
            }
        return self.rows[cohort]

    def generate(self, generation_cycle: int, events: Iterable[Tuple[int, int]]) -> None:
        for source, _desc in events:
            self._row(generation_cycle)["generated"][source] += 1

    def accept(self, generation_cycle: int, acceptance_cycle: int, source: int) -> None:
        row = self._row(generation_cycle)
        row["accepted"][source] += 1
        row["stages"]["generation_to_acceptance"].add(acceptance_cycle - generation_cycle)
        row["stages_by_source"][source]["generation_to_acceptance"].add(
            acceptance_cycle - generation_cycle
        )

    def fire(self, generation_cycle: int, acceptance_cycle: int, fire_cycle: int,
             source: int, phase: str) -> None:
        row = self._row(generation_cycle)
        row["fired"][source] += 1
        row["stages"]["acceptance_to_fire"].add(fire_cycle - acceptance_cycle)
        row["stages"]["generation_to_fire"].add(fire_cycle - generation_cycle)
        source_stages = row["stages_by_source"][source]
        source_stages["acceptance_to_fire"].add(fire_cycle - acceptance_cycle)
        source_stages["generation_to_fire"].add(fire_cycle - generation_cycle)
        if phase == "drain":
            row["completed_after_cut"][source] += 1

    def snapshot_cut(self, producers: StreamProducers, fifo: Sequence[Deque[tuple]]) -> None:
        for row in self.rows.values():
            row["unaccepted_at_cut"] = [0] * self.n_src
            row["accepted_unfired_at_cut"] = [0] * self.n_src
            row["fired_at_cut"] = list(row["fired"])
        for source, pending in enumerate(producers.pending):
            for generation_cycle, _desc in pending:
                self._row(generation_cycle)["unaccepted_at_cut"][source] += 1
        for source, queue in enumerate(fifo):
            for generation_cycle, _acceptance_cycle, _desc, _source in queue:
                self._row(generation_cycle)["accepted_unfired_at_cut"][source] += 1

    def as_dict(self) -> Dict[str, Any]:
        result = {}
        for cohort, row in sorted(self.rows.items()):
            for stage, aggregate in row["stages"].items():
                per_source_count = sum(
                    source[stage].count for source in row["stages_by_source"]
                )
                if aggregate.count != per_source_count:
                    raise AssertionError("aggregate and per-source cohort counts diverged")
            value = {
                key: (list(item) if isinstance(item, list) else item)
                for key, item in row.items()
                if key not in ("stages", "stages_by_source")
            }
            value["stages"] = {stage: _stats(stat) for stage, stat in row["stages"].items()}
            value["stages_by_source"] = [
                {stage: _stats(stat) for stage, stat in per_source.items()}
                for per_source in row["stages_by_source"]
            ]
            value["censored_at_cut"] = sum(row["unaccepted_at_cut"]) + sum(
                row["accepted_unfired_at_cut"]
            )
            value["generated_total"] = sum(row["generated"])
            value["accepted_total"] = sum(row["accepted"])
            value["fired_total"] = sum(row["fired"])
            value["completed_after_cut_total"] = sum(row["completed_after_cut"])
            result[str(cohort)] = jsonable(value)
        return result


def _edge_source(edge: Any) -> Optional[int]:
    fired = getattr(edge, "fired", None)
    if fired is None:
        return None
    return fired.source if hasattr(fired, "source") else int(fired)


def _model_classes(model: Any) -> Optional[Tuple[str, ...]]:
    classes = model.classes()
    return None if classes is None else tuple(classes)


def _classifier_row(
    model: Any,
    closing: Dict[str, Any],
    k: int,
    phase: str,
    generated: Sequence[int],
    accepted: Sequence[int],
    fired: Sequence[int],
    producer_backlog: Sequence[int],
    fifo_occupancy: Sequence[int],
    quota_backlog_history: Dict[str, Any],
) -> Dict[str, Any]:
    fired_total = sum(fired)
    return {
        "closing_cycle": k,
        "window": closing.get("window"),
        "phase": phase,
        "counts": list(closing.get("counts", ())),
        "total": closing.get("total"),
        "evidence": list(closing.get("evidence") or []),
        "old_classes": list(closing.get("old_classes") or []),
        "classes": list(closing.get("classes") or []),
        "credits": list(getattr(model, "credits", ())),
        "high_weight": getattr(model, "high_weight", None),
        "ordering": getattr(model, "ordering", None),
        "generated": list(generated),
        "accepted": list(accepted),
        "fired": list(fired),
        "producer_backlog": list(producer_backlog),
        "fifo_occupancy": list(fifo_occupancy),
        "quota_backlog_history": quota_backlog_history,
        "delivered_service_share": {
            str(source): (fired[source] / fired_total if fired_total else None)
            for source in range(len(fired))
        },
        "delivered_service_total": fired_total,
    }


class DiagnosisLane:
    """One mixed or Heavy-only lane, using the accepted common controller."""

    def __init__(self, config: Dict[str, Any], scenario: DiagnosisScenario,
                 include_sparse: bool, max_active_cycles: int,
                 max_drain_cycles: int, fixed_horizon: bool = False,
                 initial_classes: Optional[Sequence[str]] = None,
                 common_generation_horizon: Optional[int] = None) -> None:
        self.config, self.scenario = config, scenario
        self.include_sparse = bool(include_sparse)
        self.n_src, self.window, self.depth = scenario.n_src, scenario.window, config.get("depth", DEFAULT_DEPTH)
        self.model = make_model(config, self.n_src, self.window, self.depth)
        self.model.commit(rst_n=False)
        if initial_classes is not None:
            if len(initial_classes) != self.n_src or any(
                value not in ("L", "H") for value in initial_classes
            ):
                raise ValueError("initial_classes must contain one L/H value per source")
            if not hasattr(self.model, "cls"):
                raise ValueError("initial_classes require a class-aware model")
            self.model.cls = list(initial_classes)
        self.producers = StreamProducers(self.n_src)
        self.fifo: List[Deque[tuple]] = [deque() for _ in range(self.n_src)]
        self.cohorts = CohortBook(self.n_src, self.window)
        self.roles = RoleBook(scenario)
        self.last_fire_was_heavy = False
        self.gaps_fifo = [Gaps() for _ in range(self.n_src)]
        self.gaps_backlog = [Gaps() for _ in range(self.n_src)]
        self.generated = [0] * self.n_src
        self.accepted = [0] * self.n_src
        self.fired = [0] * self.n_src
        self.accepted_total = 0
        self.fired_total = 0
        self.last_fire_cycle: Optional[int] = None
        self.heavy_generated = 0
        self.first_heavy_release_cycle: Optional[int] = None
        self.last_heavy_release_cycle: Optional[int] = None
        self.last_heavy_fire_cycle: Optional[int] = None
        self.heavy_fired = 0
        self.cut_cycle: Optional[int] = None
        self.timeout_cycle: Optional[int] = None
        self.generation_observed_cycles = 0
        self.drain_start_cycle: Optional[int] = None
        self.drain_cycles = 0
        self.status = "RUNNING"
        self.classifier: List[Dict[str, Any]] = []
        self.class_changes: List[Dict[str, Any]] = []
        self.last_heavy_backlog: Optional[int] = None
        self.last_heavy_occupancy: Optional[int] = None
        self.cut_heavy_backlog: Optional[int] = None
        self.cut_heavy_occupancy: Optional[int] = None
        self.previous_classes = _model_classes(self.model)
        self.held_offer: Optional[Tuple[Optional[int], Optional[int]]] = None
        self.heavy_backlog = StreamStats()
        self.heavy_occupancy = StreamStats()
        self.heavy_progress = {
            b: {"start": None, "end": None, "cycles": 0, "fires": 0,
                "backlog": StreamStats()} for b in range(4)
        }
        self.heavy_time = {}
        self.cut_snapshot: Dict[str, Any] = {}
        self.cut_gaps: Dict[str, Any] = {}
        self.cut_censoring: Optional[Dict[str, Any]] = None
        self.generation_snapshot: Dict[str, Any] = {}
        self.max_active_cycles = max_active_cycles
        self.max_drain_cycles = max_drain_cycles
        self.fixed_horizon = bool(fixed_horizon)
        if common_generation_horizon is not None:
            if type(common_generation_horizon) is not int or common_generation_horizon < 1:
                raise ValueError("common_generation_horizon must be a positive integer")
            if self.fixed_horizon:
                raise ValueError(
                    "common_generation_horizon and fixed_horizon are incompatible"
                )
        self.common_generation_horizon = common_generation_horizon
        self.initial_classes = (
            None if initial_classes is None else list(initial_classes)
        )
        self.observed_heavy_arrivals: List[List[int]] = []
        self.observed_sparse_work: List[List[int]] = []
        self.observed_active_ready: List[List[int]] = []
        self.observed_drain_ready: List[List[int]] = []
        self.heavy_fire_change_points: List[Dict[str, int]] = []
        self.phase_metrics = {
            phase: _new_phase_metrics(self.n_src) for phase in ("active", "drain")
        }
        self.window_generated = [0] * self.n_src
        self.window_accepted = [0] * self.n_src
        self.window_fired = [0] * self.n_src
        self._reset_quota_window_history()
        if self.previous_classes is not None:
            self.class_changes.append({"cycle": 0, "classes": list(self.previous_classes)})

    def _reset_quota_window_history(self) -> None:
        self.quota_window_history = {
            "observed_cycles": 0,
            "active_cycles": 0,
            "drain_cycles": 0,
            "ready_cycles": 0,
            "held_cycles": 0,
            "idle_cycles": 0,
            "output_stall_cycles": 0,
            "all_source_fifo_nonempty_cycles": 0,
            "source_fifo_nonempty_cycles": [0] * self.n_src,
        }

    def _observe_quota_cycle(
        self, begin_occ: Sequence[int], ready: int, phase: str, held: bool, out_valid: bool
    ) -> None:
        history = self.quota_window_history
        history["observed_cycles"] += 1
        history["active_cycles"] += int(phase == "active")
        history["drain_cycles"] += int(phase == "drain")
        history["ready_cycles"] += int(bool(ready))
        history["held_cycles"] += int(bool(held))
        history["idle_cycles"] += int(not any(begin_occ))
        history["output_stall_cycles"] += int(bool(out_valid) and not ready)
        history["all_source_fifo_nonempty_cycles"] += int(all(begin_occ))
        for source, occupancy in enumerate(begin_occ):
            history["source_fifo_nonempty_cycles"][source] += int(occupancy > 0)

    def _quota_window_history_record(self) -> Dict[str, Any]:
        return {
            "contract_version": QUOTA_BACKLOG_HISTORY_CONTRACT,
            "expected_cycles": self.window,
            **self.quota_window_history,
            "source_fifo_nonempty_cycles": list(
                self.quota_window_history["source_fifo_nonempty_cycles"]
            ),
        }

    def _observe_edge(self, k: int, ready: int, events: List[Tuple[int, int]],
                      phase: str) -> Any:
        begin_occ = [len(q) for q in self.fifo]
        if self.common_generation_horizon is not None:
            heavy_source = self.scenario.heavy_source(k)
            for source, descriptor in events:
                if source == heavy_source:
                    self.observed_heavy_arrivals.append([k, source, descriptor])
                else:
                    self.observed_sparse_work.append([source, descriptor])
        self.last_heavy_backlog = self.heavy_generated - self.heavy_fired
        counts = self.roles.counts["heavy"]
        self.last_heavy_occupancy = sum(counts["accepted"]) - sum(counts["fired"])
        offers = self.producers.offers()
        valid = [h in offers for h in range(self.n_src)]
        desc = [offers[h][1] if h in offers else 0 for h in range(self.n_src)]
        view = self.model.view(ready)
        if list(view.count) != begin_occ:
            raise AssertionError("model FIFO occupancy and diagnostic metadata diverged")
        if view.out_valid != bool(any(begin_occ)):
            raise AssertionError("common controller emitted an invalid output view")
        self._observe_quota_cycle(begin_occ, ready, phase, view.held, view.out_valid)
        if self.held_offer is not None:
            if (view.out_source, view.out_desc) != self.held_offer:
                raise AssertionError("held output changed across a stall")
        self.held_offer = (
            (view.out_source, view.out_desc) if view.out_valid and not ready else None
        )
        edge = self.model.commit(ready, valid, desc)
        source = _edge_source(edge)
        fired_record, accepted_records = None, []
        self.last_fire_was_heavy = False
        if bool(view.fire) != (source is not None):
            raise AssertionError("view fire and committed fire disagree")
        if source is not None:
            if source != view.out_source:
                raise AssertionError("committed source differs from the offered grant")
            generation_cycle, acceptance_cycle, descriptor, metadata_source = self.fifo[source].popleft()
            if descriptor != view.out_desc or metadata_source != source:
                raise AssertionError("fired metadata does not match the offered descriptor")
            self.fired[source] += 1
            self.fired_total += 1
            self.last_fire_cycle = k
            self.cohorts.fire(generation_cycle, acceptance_cycle, k, source, phase)
            fired_record = (generation_cycle, acceptance_cycle, source)
            if source == self.scenario.heavy_source(generation_cycle):
                self.heavy_fired += 1
                self.last_heavy_fire_cycle = k
                self.last_fire_was_heavy = True
                if self.common_generation_horizon is not None:
                    self.heavy_fire_change_points.append({
                        "cycle": k,
                        "cumulative_heavy_fires": self.heavy_fired,
                    })
        for h, entry in enumerate(edge.pushed):
            if entry is None:
                continue
            if not valid[h] or not view.in_ready[h]:
                raise AssertionError("model accepted an input that was not offered/ready")
            generation_cycle, accepted_desc = self.producers.accept(h, k)
            if accepted_desc != entry.desc:
                raise AssertionError("accepted descriptor differs from producer record")
            self.fifo[h].append((generation_cycle, k, accepted_desc, h))
            self.accepted[h] += 1
            self.accepted_total += 1
            self.cohorts.accept(generation_cycle, k, h)
            accepted_records.append((generation_cycle, h))
        self.roles.observe(k, events, accepted_records, fired_record, ready, phase == "active")
        post_occ = [len(q) for q in self.fifo]
        for h in range(self.n_src):
            self.gaps_fifo[h].observe(
                begin_occ[h] > 0, source == h, ready, post_occ[h] > 0
            )
            backlog_before = bool(self.producers.pending[h]) or begin_occ[h] > 0
            backlog_after = bool(self.producers.pending[h]) or post_occ[h] > 0
            self.gaps_backlog[h].observe(backlog_before, source == h, ready, backlog_after)
        if self.producers.generated != self.accepted_total + self.producers.backlog():
            raise AssertionError("generated != accepted + producer backlog")
        if self.accepted_total != self.fired_total + sum(len(q) for q in self.fifo):
            raise AssertionError("accepted != fired + FIFO occupancy")
        phase_row = self.phase_metrics[phase]
        phase_row["cycles"] += 1
        phase_row["ready_cycles"] += ready
        for h, _desc in events:
            phase_row["generated"][h] += 1
            self.window_generated[h] += 1
        if source is not None:
            phase_row["fired"][source] += 1
            phase_row["output_transfers"] += 1
            self.window_fired[source] += 1
        for h, entry in enumerate(edge.pushed):
            if entry is not None:
                phase_row["accepted"][h] += 1
                self.window_accepted[h] += 1
        had_work = any(begin_occ)
        phase_row["eligible_ready_cycles"] += int(bool(ready) and had_work)
        phase_row["avoidable_bubbles"] += int(bool(ready) and had_work and source is None)
        phase_row["output_stall_cycles"] += int(not ready and had_work)
        phase_row["idle_ready_cycles"] += int(bool(ready) and not had_work)
        phase_row["idle_not_ready_cycles"] += int(not ready and not had_work)
        if ready and had_work and source is None:
            raise AssertionError("avoidable output bubble with eligible FIFO work")
        closing = getattr(edge, "closing", None)
        if closing is not None and self.config["family"] in (
            "FAI-inspired", "CGOF"
        ):
            self.classifier.append(
                _classifier_row(
                    self.model,
                    closing,
                    k,
                    phase,
                    self.window_generated,
                    self.window_accepted,
                    self.window_fired,
                    [len(q) for q in self.producers.pending],
                    post_occ,
                    self._quota_window_history_record(),
                )
            )
            self.classifier[-1].update(
                heavy_source_at_close=self.scenario.heavy_source(k),
                next_heavy_source=self.scenario.heavy_source(k + 1),
                generation_role_counts={
                    role: {key: list(value) for key, value in counts.items()}
                    for role, counts in self.roles.counts.items()
                },
            )
            self.window_generated = [0] * self.n_src
            self.window_accepted = [0] * self.n_src
            self.window_fired = [0] * self.n_src
            self._reset_quota_window_history()
        classes = _model_classes(self.model)
        if classes is not None and classes != self.previous_classes:
            self.class_changes.append({"cycle": k, "classes": list(classes)})
            self.previous_classes = classes
        return edge

    def _record_heavy(self, k: int, heavy_before: int, source: Optional[int]) -> None:
        self.heavy_backlog.add(heavy_before)
        counts = self.roles.counts["heavy"]
        self.heavy_occupancy.add(sum(counts["accepted"]) - sum(counts["fired"]))
        bucket = min(3, (self.heavy_fired * 4) // max(1, self.scenario.heavy_work))
        row = self.heavy_progress[bucket]
        if row["start"] is None:
            row["start"] = k
        row["end"] = k
        row["cycles"] += 1
        row["backlog"].add(heavy_before)
        if self.last_fire_was_heavy:
            row["fires"] += 1
        sub = k // self.scenario.subwindow
        time_row = self.heavy_time.setdefault(
            sub, {"start": k, "end": k, "cycles": 0, "fires": 0, "backlog": StreamStats()}
        )
        time_row["end"] = k
        time_row["cycles"] += 1
        time_row["backlog"].add(heavy_before)
        if self.last_fire_was_heavy:
            time_row["fires"] += 1

    def _boundary_gaps(self) -> None:
        for gap in self.gaps_fifo + self.gaps_backlog:
            gap.boundary(False)

    def run(self) -> Dict[str, Any]:
        try:
            if self.common_generation_horizon is not None:
                return self._run_common_generation()
            for k in range(self.max_active_cycles):
                if self.heavy_fired >= self.scenario.heavy_work:
                    self.cut_cycle = k - 1
                    break
                events = self.scenario.heavy_events(k, self.heavy_generated)
                if events:
                    self.heavy_generated += len(events)
                    if self.first_heavy_release_cycle is None:
                        self.first_heavy_release_cycle = k
                    self.last_heavy_release_cycle = k
                if self.include_sparse:
                    # Sparse is background until the finite Heavy population completes.
                    # It is intentionally not part of the Heavy-only paired input hash.
                    events = events + self.scenario.sparse_events(k)
                self.producers.generate(k, events)
                self.cohorts.generate(k, events)
                for source, _desc in events:
                    self.generated[source] += 1
                ready = self.scenario.ready(k)
                edge = self._observe_edge(k, ready, events, phase="active")
                self._record_heavy(k, self.last_heavy_backlog, _edge_source(edge))
                if self.heavy_fired >= self.scenario.heavy_work:
                    self.cut_cycle = k
                    break
            if self.cut_cycle is None:
                if not self.fixed_horizon:
                    self.status = "TIMEOUT"
                    self.timeout_cycle = self.max_active_cycles
                    self.cut_cycle = self.max_active_cycles - 1
                    self.cut_snapshot = self._snapshot(self.cut_cycle + 1)
                    self.cut_heavy_backlog = self.last_heavy_backlog
                    self.cut_heavy_occupancy = self.last_heavy_occupancy
                    self.cut_censoring = self._snapshot_cut()
                    self._boundary_gaps()
                    self.cut_gaps = self._gaps_dict()
                    return self.result()
                self.cut_cycle = self.max_active_cycles - 1
            self.cut_snapshot = self._snapshot(self.cut_cycle + 1)
            self.cut_heavy_backlog = self.last_heavy_backlog
            self.cut_heavy_occupancy = self.last_heavy_occupancy
            self.cut_censoring = self._snapshot_cut()
            self._boundary_gaps()
            self.cut_gaps = self._gaps_dict()
            start = self.cut_cycle + 1
            self.drain_cycles = 0
            for offset in range(self.max_drain_cycles):
                if not self.producers.backlog() and not any(self.fifo) and self.model.ctrl.held is None:
                    self.drain_cycles = offset
                    break
                k = start + offset
                self._observe_edge(k, 1, [], phase="drain")
                self.drain_cycles = offset + 1
            else:
                self.drain_cycles = self.max_drain_cycles
                self.status = "TIMEOUT"
                self.timeout_cycle = start + self.max_drain_cycles
                self._boundary_gaps()
                return self.result()
            self._boundary_gaps()
            if self.producers.generated != self.accepted_total or self.accepted_total != self.fired_total:
                raise AssertionError("final conservation failed")
            for counts in self.roles.counts.values():
                if not counts["generated"] == counts["accepted"] == counts["fired"]:
                    raise AssertionError("generation-role conservation failed")
            self.status = "PASS"
            return self.result()
        except Exception as exc:
            self.status = "FAIL"
            return {**self.result(), "failure": f"{type(exc).__name__}: {exc}"}

    def _run_common_generation(self) -> Dict[str, Any]:
        horizon = self.common_generation_horizon
        if horizon is None:
            raise AssertionError("common-generation dispatch lost its horizon")
        active_limit = min(horizon, self.max_active_cycles)
        for k in range(active_limit):
            events = self.scenario.heavy_events(k, self.heavy_generated)
            if events:
                self.heavy_generated += len(events)
                if self.first_heavy_release_cycle is None:
                    self.first_heavy_release_cycle = k
                self.last_heavy_release_cycle = k
            if self.include_sparse:
                events = events + self.scenario.sparse_events(k)
            self.producers.generate(k, events)
            self.cohorts.generate(k, events)
            for source, _desc in events:
                self.generated[source] += 1
            ready = self.scenario.ready(k)
            self.observed_active_ready.append([k, ready])
            edge = self._observe_edge(k, ready, events, phase="active")
            self._record_heavy(k, self.last_heavy_backlog, _edge_source(edge))
            self.generation_observed_cycles = k + 1
            self._capture_common_cut(k)

        self.generation_snapshot = self._snapshot(self.generation_observed_cycles)
        if not self.cut_snapshot:
            self.cut_cycle = self.last_heavy_fire_cycle
            self.cut_snapshot = self.generation_snapshot
            self.cut_heavy_backlog = self.last_heavy_backlog
            self.cut_heavy_occupancy = self.last_heavy_occupancy
        self._boundary_gaps()
        self.cut_gaps = self._gaps_dict()

        if self.generation_observed_cycles != horizon:
            self.status = "TIMEOUT"
            self.timeout_cycle = self.generation_observed_cycles
            return self.result()
        if self.heavy_generated != self.scenario.heavy_work:
            raise AssertionError("common horizon did not emit all Heavy work")

        self.drain_start_cycle = horizon
        for offset in range(self.max_drain_cycles):
            if (
                not self.producers.backlog()
                and not any(self.fifo)
                and self.model.ctrl.held is None
            ):
                self.drain_cycles = offset
                break
            k = horizon + offset
            ready = self.scenario.ready(k)
            self.observed_drain_ready.append([k, ready])
            edge = self._observe_edge(k, ready, [], phase="drain")
            self._record_heavy(k, self.last_heavy_backlog, _edge_source(edge))
            self.drain_cycles = offset + 1
            self._capture_common_cut(k)
        else:
            self.drain_cycles = self.max_drain_cycles
            self.status = "TIMEOUT"
            self.timeout_cycle = horizon + self.max_drain_cycles
            self.cut_cycle = self.last_heavy_fire_cycle
            return self.result()

        if self.producers.generated != self.accepted_total:
            raise AssertionError("common-generation drain left producer backlog")
        if self.accepted_total != self.fired_total:
            raise AssertionError("common-generation drain left FIFO backlog")
        for counts in self.roles.counts.values():
            if not counts["generated"] == counts["accepted"] == counts["fired"]:
                raise AssertionError("generation-role conservation failed")
        self.cut_cycle = self.last_heavy_fire_cycle
        self.status = "PASS"
        return self.result()

    def _capture_common_cut(self, cycle: int) -> None:
        if self.cut_snapshot or self.heavy_fired != self.scenario.heavy_work:
            return
        self.cut_cycle = cycle
        self.cut_snapshot = self._snapshot(cycle + 1)
        self.cut_heavy_backlog = self.last_heavy_backlog
        self.cut_heavy_occupancy = self.last_heavy_occupancy
        self.cut_censoring = self._snapshot_cut()

    def _snapshot(self, next_cycle: int) -> Dict[str, Any]:
        return {
            "next_cycle": next_cycle,
            "producer_backlog": [len(q) for q in self.producers.pending],
            "fifo_occupancy": [len(q) for q in self.fifo],
            "heavy_generated": self.heavy_generated,
            "heavy_fired": self.heavy_fired,
            "unaccepted": self.producers.backlog(),
            "accepted_unfired": sum(len(q) for q in self.fifo),
        }

    def _snapshot_cut(self) -> Dict[str, Any]:
        self.roles.snapshot_cut()
        self.cohorts.snapshot_cut(self.producers, self.fifo)
        rows = self.cohorts.as_dict()
        return {
            "cohorts": rows,
            "unaccepted_total": sum(
                sum(row["unaccepted_at_cut"]) for row in rows.values()
            ),
            "accepted_unfired_total": sum(
                sum(row["accepted_unfired_at_cut"]) for row in rows.values()
            ),
        }

    def _gaps_dict(self) -> Dict[str, Any]:
        return {
            "fifo": [gap.as_dict() for gap in self.gaps_fifo],
            "producer_plus_fifo": [gap.as_dict() for gap in self.gaps_backlog],
        }

    def result(self) -> Dict[str, Any]:
        progress = {}
        for bucket, row in self.heavy_progress.items():
            progress[str(bucket)] = {
                "start": row["start"], "end": row["end"], "cycles": row["cycles"],
                "fires": row["fires"],
                "fire_rate": row["fires"] / row["cycles"] if row["cycles"] else None,
                "backlog": _stats(row["backlog"]),
            }
        time_rows = {}
        for sub, row in sorted(self.heavy_time.items()):
            time_rows[str(sub)] = {
                "start": row["start"], "end": row["end"], "cycles": row["cycles"],
                "fires": row["fires"],
                "fire_rate": row["fires"] / row["cycles"] if row["cycles"] else None,
                "backlog": _stats(row["backlog"]),
            }
        weights = self.config.get("weights") if self.config["family"] in ("WRR", "IWRR") else None
        all_fired = sum(self.fired)
        active_fired = self.phase_metrics["active"]["fired"]
        drain_fired = self.phase_metrics["drain"]["fired"]
        active_total = sum(active_fired)
        drain_total = sum(drain_fired)
        first_release = self.first_heavy_release_cycle
        last_release = self.last_heavy_release_cycle
        last_fire = self.last_heavy_fire_cycle
        roles = self.roles.as_dict()
        common_generation = self.common_generation_horizon is not None
        common_record = (
            {
                "contract_version": ARRIVAL_COMMON_GENERATION_CONTRACT,
                "generation_end_exclusive": self.common_generation_horizon,
                "generation_observed_cycles": self.generation_observed_cycles,
                "emitted_heavy_arrivals": self.observed_heavy_arrivals,
                "emitted_sparse_work_multiset": sorted(self.observed_sparse_work),
                "active_ready_schedule": self.observed_active_ready,
                "drain_ready_schedule": self.observed_drain_ready,
                "post_edge_heavy_fire_change_points": self.heavy_fire_change_points,
            }
            if common_generation else None
        )
        return {
            "scope": MODEL_SCOPE,
            "status": self.status,
            "include_sparse": self.include_sparse,
            "config_id": config_identity(self.config),
            "model_config": model_config(self.config, self.n_src, self.window, self.depth),
            "scenario_sha256": digest_json(self.scenario.config()),
            "load_profile": self.scenario.load_profile_name,
            "n_src": self.n_src,
            "depth": self.depth,
            "window": self.window,
            "heavy_work": self.scenario.heavy_work,
            "measurement_mode": (
                "common_generation"
                if common_generation
                else ("fixed_horizon" if self.fixed_horizon else "finite_heavy")
            ),
            "arrival_contract": (
                ARRIVAL_COMMON_GENERATION_CONTRACT
                if common_generation else "legacy-finite-heavy-v1"
            ),
            "initial_classes": self.initial_classes,
            "active_cycles": (
                self.generation_observed_cycles
                if common_generation
                else ((self.cut_cycle + 1) if self.cut_cycle is not None else 0)
            ),
            "generation_end_exclusive": (
                self.common_generation_horizon if common_generation else None
            ),
            "generation_observed_cycles": self.generation_observed_cycles,
            "cut_cycle": self.cut_cycle,
            "full_cohort_last_fire_cycle": self.last_fire_cycle,
            "drain_start_cycle": self.drain_start_cycle,
            "drain_cycles": self.drain_cycles,
            "timeout_cycle": self.timeout_cycle,
            "generated": list(self.generated),
            "accepted": list(self.accepted),
            "fired": list(self.fired),
            "generated_total": self.producers.generated,
            "accepted_total": self.accepted_total,
            "fired_total": self.fired_total,
            "conservation": {
                "generated_eq_accepted_plus_producer": (
                    self.producers.generated == self.accepted_total + self.producers.backlog()
                ),
                "accepted_eq_fired_plus_fifo": (
                    self.accepted_total == self.fired_total + sum(len(q) for q in self.fifo)
                ),
                "final_generated_eq_accepted_eq_fired": (
                    self.producers.generated == self.accepted_total == self.fired_total
                ),
                "final_producer_backlog": self.producers.backlog(),
                "final_fifo_occupancy": [len(q) for q in self.fifo],
            },
            "cut_snapshot": self.cut_snapshot,
            "cut_censoring": self.cut_censoring,
            "cut_gaps": self.cut_gaps,
            "generation_snapshot": self.generation_snapshot,
            "common_generation": common_record,
            "cohorts": self.cohorts.as_dict(),
            "classifier_trajectory": self.classifier,
            "class_changes": self.class_changes,
            "phase_metrics": {
                "active": self.phase_metrics["active"],
                "drain": self.phase_metrics["drain"],
                "labels": {
                    "active": "research evidence; finite Heavy workload until completion",
                    "drain": "cleanup and conservation evidence only",
                },
            },
            "heavy": {
                "burst_id": 0,
                "generated": self.heavy_generated,
                "fired": self.heavy_fired,
                "first_release_cycle": first_release,
                "last_release_cycle": last_release,
                "last_fire_cycle": last_fire,
                "first_release_to_last_fire": (
                    last_fire - first_release
                    if first_release is not None and last_fire is not None else None
                ),
                "last_release_to_last_fire": (
                    last_fire - last_release
                    if last_release is not None and last_fire is not None else None
                ),
                "completion_cycle": last_fire if common_generation else self.cut_cycle,
                "actual_completion_cycle": last_fire if common_generation else None,
                "completed": self.heavy_fired == self.scenario.heavy_work,
                "at_cut_backlog": self.cut_heavy_backlog,
                "at_cut_occupancy": self.cut_heavy_occupancy,
                "progress_subwindows": progress,
                "time_subwindows": time_rows,
                "backlog": _stats(self.heavy_backlog),
                "occupancy": _stats(self.heavy_occupancy),
                "gaps": roles["heavy_gaps"],
            },
            "drain": {
                "phase": (
                    "scenario-ready bounded drain"
                    if common_generation else "forced-ready drain"
                ),
                "ready": "scenario.ready(k)" if common_generation else 1,
                "bounded": common_generation,
                "max_cycles": self.max_drain_cycles if common_generation else None,
                "cycles": self.drain_cycles,
                "status": self.status if self.status == "TIMEOUT" else "COMPLETE",
                "uncompleted": (
                    {
                        "producer_pending": self.producers.backlog(),
                        "fifo_backlog": sum(len(q) for q in self.fifo),
                        "held_grant": self.model.ctrl.held is not None,
                    }
                    if common_generation and self.status == "TIMEOUT" else None
                ),
                "stability_evidence": False,
                "note": "drain completion is not long-run stability evidence",
            },
            "gaps": self._gaps_dict(),
            "service_shares": {
                str(h): (self.fired[h] / all_fired if all_fired else None)
                for h in range(self.n_src)
            },
            "active_service_shares": {
                str(h): (active_fired[h] / active_total if active_total else None)
                for h in range(self.n_src)
            },
            "drain_service_shares": {
                str(h): (drain_fired[h] / drain_total if drain_total else None)
                for h in range(self.n_src)
            },
            "demand_fairness": fairness_summary(self.fired, self.generated, weights=weights),
            "active_demand_fairness": fairness_summary(
                active_fired, self.phase_metrics["active"]["generated"], weights=weights
            ),
            "generation_roles": roles,
            "notes": [
                "MODEL_ONLY",
                "fire is a scheduler service event, not measured memory bandwidth",
                (
                    "all declared generation ends at the policy-independent horizon; "
                    "drain uses the original scenario.ready schedule"
                    if common_generation
                    else "Sparse generation stops at finite Heavy completion; "
                         "forced-ready drain accepts pending work"
                ),
            ],
        }


def run_lane(config: Dict[str, Any], scenario: DiagnosisScenario, include_sparse: bool,
             max_active_cycles: Optional[int] = None,
             max_drain_cycles: Optional[int] = None,
             fixed_horizon: bool = False,
             initial_classes: Optional[Sequence[str]] = None,
             common_generation_horizon: Optional[int] = None) -> Dict[str, Any]:
    if max_active_cycles is None:
        max_active_cycles = scenario.heavy_work + 4 * scenario.window
    if max_drain_cycles is None:
        max_drain_cycles = 4 * (scenario.heavy_work + scenario.n_src * scenario.window) + 1024
    lane = DiagnosisLane(
        config, scenario, include_sparse, max_active_cycles, max_drain_cycles,
        fixed_horizon=fixed_horizon, initial_classes=initial_classes,
        common_generation_horizon=common_generation_horizon,
    )
    return lane.run()


def run_job(
    config: Dict[str, Any],
    seed: int,
    role: str,
    *,
    n_src: int = DEFAULT_N_SRC,
    depth: int = DEFAULT_DEPTH,
    window: int = DEFAULT_WINDOW,
    windows: int = DEFAULT_WINDOWS,
    heavy_work: Optional[int] = None,
    heavy_p: Optional[float] = None,
    sparse_p: Optional[float] = None,
    ready_p: Optional[float] = None,
    subwindow: Optional[int] = None,
    profile: Optional[str] = None,
    max_active_cycles: Optional[int] = None,
    max_drain_cycles: Optional[int] = None,
    fixed_horizon: bool = False,
    initial_classes: Optional[Sequence[str]] = None,
    heavy_sources: Optional[Sequence[int]] = None,
    ready_pattern: str = "bernoulli",
    ready_period: int = 100,
) -> Dict[str, Any]:
    """Run the mixed and paired Heavy-only lanes for one configuration/seed."""
    if profile is not None:
        scenario = DiagnosisScenario.load_profile(
            seed,
            profile,
            n_src=n_src,
            window=window,
            windows=windows,
            heavy_work=heavy_work,
            heavy_p=heavy_p,
            sparse_p=sparse_p,
            ready_p=ready_p,
            subwindow=subwindow,
            heavy_sources=heavy_sources, ready_pattern=ready_pattern, ready_period=ready_period,
        )
    else:
        scenario = DiagnosisScenario(
            seed=seed, n_src=n_src, window=window, windows=windows,
            heavy_work=heavy_work,
            heavy_p=DEFAULT_HEAVY_P if heavy_p is None else heavy_p,
            sparse_p=DEFAULT_SPARSE_P if sparse_p is None else sparse_p,
            ready_p=DEFAULT_READY_P if ready_p is None else ready_p,
            subwindow=subwindow,
            heavy_sources=heavy_sources, ready_pattern=ready_pattern, ready_period=ready_period,
        )
    effective_config = {**config, "depth": depth}
    mixed = run_lane(
        effective_config, scenario, True, max_active_cycles, max_drain_cycles,
        fixed_horizon=fixed_horizon, initial_classes=initial_classes,
    )
    isolated = run_lane(
        effective_config, scenario, False, max_active_cycles, max_drain_cycles,
        fixed_horizon=fixed_horizon, initial_classes=initial_classes,
    )
    statuses = (mixed["status"], isolated["status"])
    status = "PASS" if statuses == ("PASS", "PASS") else (
        "TIMEOUT" if "TIMEOUT" in statuses else "FAIL"
    )
    prefix = min(mixed["active_cycles"], isolated["active_cycles"])
    heavy_prefix_sha256 = scenario.input_prefix_sha256(prefix, False)
    return {
        "schema": SCHEMA,
        "scope": MODEL_SCOPE,
        "status": status,
        "role": role,
        "seed": seed,
        "config_id": config_identity(config),
        "config": jsonable(effective_config),
        "model_config": model_config(effective_config, n_src, window, depth),
        "scenario": scenario.config(),
        "scenario_sha256": digest_json(scenario.config()),
        "production_evidence": False,
        "long_run": bool(window == DEFAULT_WINDOW
                         and min(mixed["active_cycles"], isolated["active_cycles"])
                         // window >= MIN_LONG_RUN_WINDOWS),
        "smoke_stress": bool(window == 256),
        "measurement_mode": "fixed_horizon" if fixed_horizon else "finite_heavy",
        "initial_classes": None if initial_classes is None else list(initial_classes),
        "pairing": {
            "same_seed": True,
            "same_scenario": mixed["scenario_sha256"] == isolated["scenario_sha256"],
            "same_heavy_ready_prefix_cycles": prefix,
            "same_heavy_ready_prefix_sha256": heavy_prefix_sha256,
            "mixed_input_prefix_sha256": scenario.input_prefix_sha256(prefix, True),
            "isolated_input_prefix_sha256": heavy_prefix_sha256,
            "mixed_completion_cycle": mixed["cut_cycle"],
            "isolated_completion_cycle": isolated["cut_cycle"],
            "mixed_heavy_burst": mixed["heavy"],
            "isolated_heavy_burst": isolated["heavy"],
            "heavy_completion_cycle_delta_mixed_minus_isolated": (
                mixed["cut_cycle"] - isolated["cut_cycle"]
                if mixed["cut_cycle"] is not None and isolated["cut_cycle"] is not None else None
            ),
            "heavy_first_release_to_last_fire_ratio": (
                mixed["heavy"]["first_release_to_last_fire"]
                / isolated["heavy"]["first_release_to_last_fire"]
                if mixed["heavy"]["first_release_to_last_fire"] is not None
                and isolated["heavy"]["first_release_to_last_fire"] not in (None, 0) else None
            ),
            "completion_ratio_mixed_over_isolated": (
                (mixed["cut_cycle"] + 1) / (isolated["cut_cycle"] + 1)
                if mixed["cut_cycle"] is not None and isolated["cut_cycle"] is not None else None
            ),
        },
        "mixed": mixed,
        "isolated": isolated,
        "notes": [
            "MODEL_ONLY",
            "paired isolated baseline replays Heavy events and ready schedule",
            "no actual memory-bandwidth claim",
            "finite Heavy work; Sparse continues until Heavy completion",
        ],
    }


def paired_bootstrap(
    candidate: Sequence[float],
    baseline: Sequence[float],
    seeds: Sequence[int],
    *,
    replicates: int = 10_000,
    rng_seed: int = 20261027,
) -> Dict[str, Any]:
    """Paired-seed bootstrap over exactly one declared seed cohort.

    Deltas are candidate minus baseline.  Exploration intervals are descriptive only;
    this function never labels them confirmatory.
    """
    role = seed_role_for(seeds)
    if len(candidate) != len(baseline) or len(candidate) != len(seeds):
        raise ValueError("candidate, baseline and seeds must have equal lengths")
    if type(replicates) is not int or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    ordered = sorted(range(len(seeds)), key=lambda i: seeds[i])
    deltas = []
    for i in ordered:
        x, y = float(baseline[i]), float(candidate[i])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("bootstrap inputs must be finite")
        deltas.append(y - x)
    rng = random.Random(rng_seed)
    n = len(deltas)
    samples = sorted(
        sum(deltas[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(replicates)
    )
    return {
        "unit": "paired seed/run",
        "seed_role": role,
        "seeds": list(sorted(seeds)),
        "n": n,
        "replicates": replicates,
        "rng_seed": rng_seed,
        "delta_convention": "candidate minus baseline",
        "paired_deltas": deltas,
        "mean_paired_delta": statistics.mean(deltas),
        "percentile95": [samples[249], samples[9749]] if replicates == 10_000 else [
            samples[int(0.025 * (replicates - 1))],
            samples[int(0.975 * (replicates - 1))],
        ],
        "descriptive_only": role == "exploration",
        "inference": "MODEL_ONLY synthetic scenario; not production confirmation",
    }

