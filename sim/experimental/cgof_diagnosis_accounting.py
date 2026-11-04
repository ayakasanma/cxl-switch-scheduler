"""Per-cycle diagnosis accounting shared by the cocotb RTL test and the model-only runner.

One fixed exogenous lane (``DiagnosisTraffic``) is driven cycle by cycle; the scheduler
under test is opaque. ``DiagnosisAccounting.cycles()`` is a generator that yields one
``(push, ready)`` request per clock edge and expects the cycle's pre-edge sample back via
``send()``: the cocotb test answers with ``Harness.cycle()``, the model runner with
``model.view()`` + ``model.commit()``. Both therefore run this exact bookkeeping, active
loop and cut-time ``ready=1`` cleanup drain.

The sample is the dict returned by ``Harness.sample()`` restricted to the keys used here:
``in_ready`` (bit mask), ``out_valid``, ``out_source``/``out_desc`` (None when not valid)
and ``fire``.
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

from cgof_diagnosis_traffic import DiagnosisTraffic
from revision_traffic import Metrics, StreamProducers
from diagnosis_source_book import SourceBook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "refc"))
from cxl_model.diagnosis import RoleBook, fairness_summary  # noqa: E402


class DiagnosisAccounting:
    """Traffic, producers, Metrics, RoleBook and classifier records of one diagnosis job.

    ``model`` is a zero-argument callable returning the scheduler reference model whose
    ``windows_closed``/``classes()``/``credits`` describe the classifier state.
    """

    def __init__(self, job: dict, model) -> None:
        mode, lane = job["mode"], job.get("lane", "mixed")
        assert mode in DiagnosisTraffic.MODES and lane in DiagnosisTraffic.LANES
        self.job, self.mode, self.lane = job, mode, lane
        self.model = model
        self.traffic = DiagnosisTraffic(
            mode,
            job["seed"],
            n_src=job["n_src"],
            window=job["window"],
            depth=job["depth"],
            windows=job.get("windows", 3),
            heavy_work=job.get("heavy_work"),
            profile=job.get("profile"),
            include_sparse=lane == "mixed",
            heavy_sources=job.get("heavy_sources"),
            ready_pattern=job.get("ready_pattern", "bernoulli"),
            ready_period=job.get("ready_period", 100),
        )
        traffic = self.traffic
        self.metrics, self.producers = Metrics(traffic), StreamProducers(traffic.n)
        self.roles = RoleBook(traffic.scenario)
        self.sources = SourceBook(traffic.n, traffic.window, job.get("windows", 3))
        self.blocked = {}
        self.window_generated = [0] * traffic.n
        self.window_accepted = [0] * traffic.n
        self.window_fired = [0] * traffic.n
        self.classifier = []
        self.input_hold_checks = 0
        self.active_end = None
        self.drain_start = None
        self.k = -1
        self.t0 = time.monotonic()

    def edge(self, cycle: int, events, ready):
        """One clock edge; yields the scheduler request and returns its sample."""
        traffic, metrics, producers, roles = self.traffic, self.metrics, self.producers, self.roles
        producers.generate(cycle, events)
        push = {source: value[1] for source, value in producers.offers().items()}
        model = self.model()
        before_windows = model.windows_closed
        before_classes = model.classes()
        sample = yield push, ready
        model = self.model()
        fired_record = None
        if sample["fire"]:
            generation, acceptance, _ = metrics.fifo[sample["out_source"]][0]
            fired_record = (generation, acceptance, sample["out_source"])
        accepted_records = [(producers.pending[source][0][0], source) for source in push
                            if sample["in_ready"] >> source & 1]
        roles.observe(cycle, events, accepted_records, fired_record, ready,
                      traffic.phase(cycle) != "drain")
        self.sources.observe(cycle, events, accepted_records, fired_record)
        metrics.observe(
            cycle, events, producers, ready,
            sample["in_ready"], sample["out_valid"],
            sample["out_source"], sample["out_desc"],
        )
        for source, desc in self.blocked.items():
            assert push.get(source) == desc, (cycle, "producer input hold")
            self.input_hold_checks += 1
        self.blocked = {
            source: desc for source, desc in push.items()
            if not (sample["in_ready"] >> source & 1)
        }
        for source, _desc in events:
            self.window_generated[source] += 1
        for source in push:
            if sample["in_ready"] >> source & 1:
                self.window_accepted[source] += 1
                traffic.note_accept(source)
        if sample["fire"]:
            self.window_fired[sample["out_source"]] += 1
        if model.windows_closed != before_windows:
            self.classifier.append({
                "window": before_windows,
                "closing_cycle": cycle,
                "phase": traffic.phase(cycle),
                "heavy_source_at_close": traffic.heavy(cycle),
                "next_heavy_source": traffic.heavy(cycle + 1),
                "generated": list(self.window_generated),
                "accepted": list(self.window_accepted),
                "fired": list(self.window_fired),
                "old_classes": list(before_classes or []),
                "classes": list(model.classes() or []),
                "credits": (None if self.job.get("policy") == "FAI-inspired"
                            else list(model.credits)),
                "generation_role_counts": {
                    role: {key: list(value) for key, value in counts.items()}
                    for role, counts in roles.counts.items()
                },
                "producer_backlog": [len(q) for q in producers.pending],
                "fifo_occupancy": [len(q) for q in metrics.fifo],
            })
            self.window_generated = [0] * traffic.n
            self.window_accepted = [0] * traffic.n
            self.window_fired = [0] * traffic.n
        traffic.note_fire(cycle, sample["out_source"] if sample["fire"] else None,
                          fired_record[0] if fired_record is not None else None)
        return sample

    def cycles(self):
        """Active loop, then the cut-time ready=1 cleanup drain (bound 2*(backlog+fifo)+128)."""
        traffic, metrics, producers, roles = self.traffic, self.metrics, self.producers, self.roles
        if self.mode == "common-demand":
            for self.k in range(traffic.measurement_end):
                events, ready = traffic.step(self.k)
                yield from self.edge(self.k, events, ready)
            self.active_end = traffic.measurement_end
        else:
            max_active = self.job.get("max_active_cycles", traffic.heavy_work + 4 * traffic.window)
            for self.k in range(max_active):
                events, ready = traffic.step(self.k)
                yield from self.edge(self.k, events, ready)
                if traffic.heavy_complete:
                    break
            assert traffic.heavy_complete, "finite Heavy burst did not complete"
            self.active_end = traffic.active_cycles

        roles.snapshot_cut()
        self.sources.snapshot_cut()
        self.drain_start = self.active_end
        self.k = self.active_end
        drain_bound = 2 * (producers.backlog() + sum(len(q) for q in metrics.fifo)) + 128
        while producers.backlog() or any(metrics.fifo) or metrics.held is not None:
            assert self.k - self.drain_start < drain_bound, "generated-population drain timeout"
            yield from self.edge(self.k, [], 1)
            self.k += 1
        metrics.complete(producers)
        for counts in roles.counts.values():
            assert counts["generated"] == counts["accepted"] == counts["fired"], "role conservation"
        assert not self.blocked

    def result(self) -> dict:
        """Scheduler-independent result fields; callers add schema/evidence/params/policy."""
        traffic, metrics, roles = self.traffic, self.metrics, self.roles
        metrics_data = metrics.as_dict()
        active_name = "measurement" if self.mode == "common-demand" else "active"
        active = metrics_data["phases"][active_name]
        fairness = fairness_summary(active["fired"], active["generated"])
        active_total = sum(active["fired"])
        role_data = roles.as_dict()
        role_gaps = role_data["heavy_gaps"]["samples"].get("inter_service", {})
        heavy_gaps = {
            "wall_cycles": role_gaps.get("wall_cycles", {}),
            "eligible_ready": role_gaps.get("eligible_ready_opportunities", {}),
        }
        shares = {
            str(source): (active["fired"][source] / active_total if active_total else None)
            for source in range(traffic.n)
        }
        return {
            "status": "PASS",
            "mode": self.mode,
            "lane": self.lane,
            "job": self.job,
            "trace_config": traffic.config(),
            "trace_sha256": traffic.sha256,
            "active_cycles": self.active_end,
            "drain_cycles": self.k - self.drain_start,
            "generated": traffic.generated,
            "ready_cycles": traffic.ready_count,
            "accepted": sum(sum(row["accepted"]) for row in metrics.rows.values()),
            "fired": sum(sum(row["fired"]) for row in metrics.rows.values()),
            "fairness": fairness,
            "service_shares": shares,
            "classifier": self.classifier,
            "heavy": {
                "burst_id": 0,
                "work": traffic.heavy_work,
                "generated": traffic.heavy_released,
                "fired": traffic.heavy_fired,
                "completed": traffic.heavy_complete if self.mode == "finite-heavy" else None,
                "completion_cycle": traffic.cut_cycle,
                "first_release_to_last_fire": (
                    traffic.cut_cycle - traffic.first_heavy_release_cycle
                    if traffic.cut_cycle is not None
                    and traffic.first_heavy_release_cycle is not None
                    else None
                ),
                "first_release_cycle": traffic.first_heavy_release_cycle,
                "last_release_cycle": traffic.last_heavy_release_cycle,
                "max_wall_gap": heavy_gaps["wall_cycles"].get("max"),
                "gaps": heavy_gaps,
            },
            "generation_roles": role_data,
            "physical_sources": self.sources.result(),
            "metrics": metrics_data,
            "wall_s": time.monotonic() - self.t0,
        }

    def failure(self, exc: BaseException) -> dict:
        return dict(status="FAIL", mode=self.mode, lane=self.lane, job=self.job, cycle=self.k,
                    error=repr(exc), trace_sha256=self.traffic.sha256,
                    wall_s=time.monotonic() - self.t0)
