"""Deterministic exogenous traffic for the CGOF measurement/diagnosis runs.

This adapter only supplies events and ready cycles.  It does not observe RTL pins;
``Metrics`` in ``revision_traffic`` remains the independent pin-history checker.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
for folder in ("refc",):
    path = str(ROOT / folder)
    if path not in sys.path:
        sys.path.insert(0, path)

from cxl_model.diagnosis import DiagnosisScenario  # noqa: E402


class DiagnosisTraffic:
    """One common-demand or finite-Heavy lane with a fixed exogenous trace.

    Common demand releases one request from every source per cycle for
    ``windows * window`` cycles.  Finite Heavy releases source 0 until
    ``heavy_work`` requests have been generated; Sparse sources continue until
    the caller marks the finite Heavy burst complete.  Both modes drain all
    generated work with ready asserted.
    """

    MODES = ("common-demand", "finite-heavy")
    LANES = ("mixed", "isolated")

    def __init__(
        self,
        mode: str,
        seed: int,
        *,
        n_src: int = 4,
        window: int = 5_000_000,
        depth: int = 16,
        windows: int = 3,
        heavy_work: Optional[int] = None,
        profile: Optional[str] = None,
        include_sparse: bool = True,
        heavy_sources: Optional[Sequence[int]] = None,
        ready_pattern: str = "bernoulli",
        ready_period: int = 100,
    ) -> None:
        if mode not in self.MODES:
            raise ValueError(f"mode must be one of {self.MODES}")
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if type(n_src) is not int or n_src < 2:
            raise ValueError("n_src must be at least 2")
        if type(window) is not int or window < 1:
            raise ValueError("window must be a positive integer")
        if type(depth) is not int or depth < 1:
            raise ValueError("depth must be a positive integer")
        if type(windows) is not int or windows < 1:
            raise ValueError("windows must be a positive integer")

        self.mode, self.seed, self.n_src = mode, seed, n_src
        self.n = n_src
        self.window, self.depth, self.windows = window, depth, windows
        # A saturated common-demand source self-throttles instead of retaining an
        # unbounded generated-not-accepted population across a production window.
        self.producer_backlog_limit = max(4 * depth, 256) if mode == "common-demand" else None
        self.outstanding = [0] * n_src
        self.include_sparse = bool(include_sparse)
        self.job = dict(n_src=n_src, window=window, depth=depth, seed=seed,
                        mode=mode, include_sparse=self.include_sparse)
        self.phases = (("measurement", "drain") if mode == "common-demand"
                       else ("active", "drain"))
        self.cohorts = (("common-demand",) if mode == "common-demand"
                        else ("finite-heavy",))

        if mode == "common-demand":
            self.measurement_end = windows * window
            self.scenario = DiagnosisScenario(
                seed=seed,
                n_src=n_src,
                window=window,
                windows=windows,
                heavy_work=self.measurement_end,
                heavy_p=1.0,
                sparse_p=1.0,
                ready_p=1.0,
            )
            self.scenario.load_profile_name = "equal"
            self.heavy_work = self.measurement_end
            self._max_active_cycles = self.measurement_end
        else:
            self.measurement_end = None
            self.heavy_work = heavy_work if heavy_work is not None else windows * window
            if profile is not None:
                self.scenario = DiagnosisScenario.load_profile(
                    seed,
                    profile,
                    n_src=n_src,
                    window=window,
                    windows=windows,
                    heavy_work=self.heavy_work,
                    heavy_sources=heavy_sources, ready_pattern=ready_pattern,
                    ready_period=ready_period,
                )
            else:
                self.scenario = DiagnosisScenario(
                    seed=seed,
                    n_src=n_src,
                    window=window,
                    windows=windows,
                    heavy_work=self.heavy_work,
                    heavy_sources=heavy_sources, ready_pattern=ready_pattern,
                    ready_period=ready_period,
                )
            self._max_active_cycles = None

        self.generated = [0] * n_src
        self.ready_count = 0
        self.next_cycle = 0
        self.heavy_released = 0
        self.heavy_fired = 0
        self.first_heavy_release_cycle: Optional[int] = None
        self.last_heavy_release_cycle: Optional[int] = None
        self.cut_cycle: Optional[int] = None
        self.drain_started = False
        self._sha = hashlib.sha256(
            (json.dumps(self.config(), sort_keys=True, separators=(",", ":")) + "\n").encode()
        )

    def config(self) -> dict:
        result = dict(generator="cxl-cgof-diagnosis-traffic-v1",
                      mode=self.mode,
                      seed=self.seed,
                      n_src=self.n_src,
                      window=self.window,
                      windows=self.windows,
                      depth=self.depth,
                      include_sparse=self.include_sparse,
                      measurement_end=self.measurement_end,
                      heavy_work=self.heavy_work,
                      producer_backlog_limit=self.producer_backlog_limit,
                      scenario=self.scenario.config())
        return result

    def phase(self, k: int) -> str:
        if self.mode == "common-demand":
            return "measurement" if k < self.measurement_end else "drain"
        return "drain" if self.drain_started else "active"

    def cohort(self, k: int) -> Optional[str]:
        if self.mode == "common-demand":
            return "common-demand" if k < self.measurement_end else None
        return "finite-heavy" if self.cut_cycle is None or k <= self.cut_cycle else None

    def heavy(self, k: int) -> int:
        return self.scenario.heavy_source(k)

    def step(self, k: int) -> Tuple[List[Tuple[int, int]], int]:
        if k != self.next_cycle:
            raise AssertionError(f"step({k}) out of order (expected {self.next_cycle})")
        self.next_cycle += 1
        if self.mode == "common-demand" and k >= self.measurement_end:
            return [], 1
        if self.mode == "finite-heavy" and self.drain_started:
            return [], 1

        heavy = self.scenario.heavy_events(k, self.heavy_released)
        sparse = self.scenario.sparse_events(k) if self.include_sparse else []
        events = []
        for source, desc in heavy + sparse:
            limit = self.producer_backlog_limit
            if limit is not None and self.outstanding[source] >= limit:
                continue
            events.append((source, desc))
            self.outstanding[source] += 1
        emitted_heavy = [source for source, _ in events if source == self.heavy(k)]
        if emitted_heavy:
            if self.first_heavy_release_cycle is None:
                self.first_heavy_release_cycle = k
            self.last_heavy_release_cycle = k
        self.heavy_released += len(emitted_heavy)
        ready = self.scenario.ready(k)
        for source, _desc in events:
            self.generated[source] += 1
        self.ready_count += ready
        self._sha.update(f"{k}:{ready}:{events!r}\n".encode())
        return events, ready

    def note_accept(self, source: int) -> None:
        """Account for one producer record accepted by the RTL input."""
        if not 0 <= source < self.n_src:
            raise ValueError("source out of range")
        if self.outstanding[source] <= 0:
            raise AssertionError(f"source {source} accepted with no outstanding record")
        self.outstanding[source] -= 1

    def note_fire(self, k: int, source: Optional[int],
                  generation_cycle: Optional[int] = None) -> None:
        """Keep pending old-role requests attached to their generation role."""
        if generation_cycle is None:
            if len(set(self.scenario.heavy_sources)) > 1 and source is not None:
                raise ValueError("role switching requires a fired generation cycle")
            generation_cycle = k
        if self.mode != "finite-heavy" or source != self.heavy(generation_cycle):
            return
        self.heavy_fired += 1
        if self.heavy_fired == self.heavy_work:
            self.cut_cycle = k
            self.drain_started = True

    @property
    def heavy_complete(self) -> bool:
        return self.mode == "finite-heavy" and self.heavy_fired == self.heavy_work

    @property
    def active_cycles(self) -> Optional[int]:
        if self.mode == "common-demand":
            return self.measurement_end
        return None if self.cut_cycle is None else self.cut_cycle + 1

    def heavy_ready_prefix_sha256(self, cycles: int) -> str:
        return self.scenario.input_prefix_sha256(cycles, include_sparse=False)

    @property
    def sha256(self) -> str:
        return self._sha.hexdigest()

