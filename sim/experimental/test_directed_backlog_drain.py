"""SCHEDULER_RTL_DIRECTED_BACKLOG_DRAIN: directed long-backlog drain on the unchanged RTL.

Scope label: SCHEDULER_RTL_DIRECTED_BACKLOG_DRAIN (initial reset, all sources High). Production
window parameters (FAI_W=5,000,000) are used, but the run is a short bounded directed sequence: no
window closes, so it is NOT trained-class / long-production evidence, and it makes no latency,
fairness, classification-adaptation or power claim.

Sequence (one job, one configuration):

1. ``generate`` phase, ``gen_cycles`` real edges with ``i_out_ready = 0``: every source draws
   finite Bernoulli traffic (engineering fixture seed, not a power or confirmation seed). Generated
   descriptors wait in per-source producers (``fai_stream.StreamProducers``); the producer head is
   offered every cycle and a refused offer is presented again unchanged (input-hold check). The
   FIFOs fill to DEPTH and the remainder becomes producer backlog. With ready 0 nothing may fire
   (accepted-not-fired state) and, once offered, the first grant must stay held unchanged.
2. explicit cutoff: generation stops; producer backlog per source, FIFO occupancy per source and
   generated/accepted/fired totals are captured. Every source must have positive producer backlog
   and positive FIFO occupancy.
3. ``drain`` phase with ``i_out_ready = 1``, pending producers still offering, bounded by
   ``2 * pending + 128`` real edges (pending = generated - fired at cutoff). The first drain cycle
   must fire exactly the held grant (source, descriptor, context) of the cutoff.
4. two quiescent edges: no output, every input ready.

Throughout, the reused native harness (``test_cgof_sched.Harness`` for CGOF, the accepted
``test_main_diagnosis.MainHarness`` plus an ``ExperimentalSwitchModel`` mirror for Main) runs its
full per-cycle pin/model lockstep, pin scoreboard (per-source FIFO order, exactly-once 105-bit
delivery, readiness = occupancy < DEPTH) and held-grant checks. This module adds the independent
generated/accepted/fired conservation accounting. No preload, state injection, counter deposit or
skipped edge is used: every DUT edge goes through ``Harness.cycle``.

``DrainAccounting`` is free of cocotb/RTL so that ``scripts/test_directed_backlog_drain.py`` can
drive it from the independent model alone and run negative controls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("refc", "sim/common", "sim/switch_top_fai"):
    if str(ROOT / _folder) not in sys.path:
        sys.path.insert(0, str(ROOT / _folder))
from fai_stream import StreamProducers  # noqa: E402

SCOPE = "SCHEDULER_RTL_DIRECTED_BACKLOG_DRAIN"
SCHEMA = "cxl-directed-backlog-drain-v1"
DEFAULT_RATES = (0.75, 0.5, 0.375, 0.25)
QUIESCENT_CYCLES = 2


class DrainAccounting:
    """Directed backlog/cutoff/drain sequence with independent conservation accounting.

    ``cycles()`` yields ``(push, ready)`` per real edge and expects the pre-edge sample dict
    (``in_ready`` mask, ``out_valid``, ``out_source``, ``out_desc``, ``fire``, ``grant_ctx``,
    ``held``) back via ``send()``. ``desc`` is a callable ``source -> descriptor``.
    ``occupancy`` optionally returns the driver's own per-source stored count after each edge
    (the harness pin scoreboard), compared with this accounting every cycle.
    """

    def __init__(self, job: dict, desc, occupancy=None) -> None:
        self.job = dict(job)
        self.n, self.depth = job["n_src"], job["depth"]
        self.gen_cycles = job["gen_cycles"]
        self.rates = list(job["rates"])
        assert len(self.rates) == self.n and all(0 < r <= 1 for r in self.rates)
        assert self.gen_cycles > 0
        self.rng = random.Random(f"directed-backlog-drain-traffic:{job['seed']}")
        self.desc, self.occupancy = desc, occupancy
        self.producers = StreamProducers(self.n)
        n = self.n
        self.generated = [[] for _ in range(n)]
        self.accepted = [[] for _ in range(n)]
        self.fired = [[] for _ in range(n)]
        self.fifo = [0] * n  # accepted - fired per source, from pins
        self.blocked = {}
        self.input_hold_checks = 0
        self.held_continuity_checks = 0
        self.occupancy_checks = 0
        self.held_grant = None  # (source, desc, ctx) offered while ready 0
        self.first_offer_cycle = None
        self.cutoff = None
        self.drain = None
        self.quiescent_cycles = 0
        self.k = 0
        self.phase = "generate"
        self.t0 = time.monotonic()

    # ----- one edge ---------------------------------------------------------------------------

    def edge(self, events, ready):
        for source, _gen, desc in events:
            self.generated[source].append(desc)
        self.producers.generate(self.k, [(s, d) for s, _g, d in events])
        push = {s: rec[1] for s, rec in self.producers.offers().items()}
        sample = yield push, ready
        k, tag = self.k, f"[{self.phase} cycle {self.k}]"
        for source, desc in self.blocked.items():
            assert push.get(source) == desc, f"{tag} producer input hold source {source}"
            self.input_hold_checks += 1
        fire = bool(sample["fire"])
        assert fire == bool(sample["out_valid"] and ready), f"{tag} fire != valid & ready"
        pre = list(self.fifo)  # pre-edge occupancy: readiness has no same-edge pop credit
        if fire:
            src, d = sample["out_source"], sample["out_desc"]
            assert self.fifo[src] > 0, f"{tag} fire from source {src} with nothing accepted"
            expect = self.accepted[src][len(self.fired[src])]
            assert d == expect, f"{tag} source {src} fired {d:#x}, oldest accepted {expect:#x}"
            self.fired[src].append(d)
            self.fifo[src] -= 1
        self.blocked = {}
        for source, desc in push.items():
            if sample["in_ready"] >> source & 1:
                _gen, popped = self.producers.accept(source, k)
                assert popped == desc
                self.accepted[source].append(desc)
                self.fifo[source] += 1
                assert self.fifo[source] <= self.depth, f"{tag} source {source} over DEPTH"
            else:
                assert pre[source] == self.depth, \
                    f"{tag} source {source} refused at pre-edge occupancy {pre[source]}"
                self.blocked[source] = desc
        if self.occupancy is not None:
            assert list(self.occupancy()) == self.fifo, \
                f"{tag} driver occupancy {list(self.occupancy())} != accounting {self.fifo}"
            self.occupancy_checks += 1
        self.k += 1
        return sample

    # ----- sequence ---------------------------------------------------------------------------

    def cycles(self):
        n = self.n
        serial = 0
        # 1. generation with the sink stalled
        self.phase = "generate"
        for _ in range(self.gen_cycles):
            events = []
            for h in range(n):
                if self.rng.random() < self.rates[h]:
                    events.append((h, self.k, self.desc(h)))
                    serial += 1
            stored_before = any(self.fifo)  # pre-edge stored requests
            sample = yield from self.edge(events, 0)
            tag = f"[generate cycle {self.k - 1}]"
            assert not sample["fire"], f"{tag} fired with ready 0"
            if sample["out_valid"]:
                offer = (sample["out_source"], sample["out_desc"], sample["grant_ctx"])
                if self.held_grant is None:
                    self.held_grant, self.first_offer_cycle = offer, self.k - 1
                    assert not sample["held"], f"{tag} first offer already marked held"
                else:
                    assert offer == self.held_grant, f"{tag} stalled grant changed {offer}"
                    assert sample["held"], f"{tag} grant_held low while stalled"
                    self.held_continuity_checks += 1
            else:
                assert self.held_grant is None and not stored_before, \
                    f"{tag} no output with stored requests"
        # 2. explicit cutoff
        backlog = [len(q) for q in self.producers.pending]
        gen = [len(x) for x in self.generated]
        acc = [len(x) for x in self.accepted]
        fired = [len(x) for x in self.fired]
        pending = sum(gen) - sum(fired)
        self.cutoff = dict(
            cycle=self.k,
            producer_backlog=backlog,
            producer_backlog_total=sum(backlog),
            fifo_occupancy=list(self.fifo),
            fifo_occupancy_total=sum(self.fifo),
            generated=gen, accepted=acc, fired=fired,
            generated_total=sum(gen), accepted_total=sum(acc), fired_total=sum(fired),
            pending=pending,
            held_grant=None if self.held_grant is None else dict(
                source=self.held_grant[0], desc=hex(self.held_grant[1]),
                grant_ctx=self.held_grant[2], first_offer_cycle=self.first_offer_cycle,
                stalled_cycles=self.k - self.first_offer_cycle),
        )
        assert sum(fired) == 0, "accepted-not-fired: something fired with ready 0"
        assert acc == self.fifo, "accepted-not-fired: FIFO occupancy != accepted"
        assert all(b > 0 for b in backlog), f"cutoff producer backlog not positive per source {backlog}"
        assert all(f > 0 for f in self.fifo), f"cutoff FIFO occupancy not positive per source {self.fifo}"
        assert self.held_grant is not None, "no held grant at cutoff"
        # 3. drain with ready 1, producers still offering
        self.phase = "drain"
        limit = 2 * pending + 128
        start = self.k
        first = True
        while self.producers.backlog() or any(self.fifo):
            assert self.k - start < limit, f"drain bound {limit} exceeded at cycle {self.k}"
            sample = yield from self.edge([], 1)
            if first:
                got = (sample["out_source"], sample["out_desc"], sample["grant_ctx"])
                assert sample["fire"] and got == self.held_grant, \
                    f"first drain cycle fired {got}, held grant {self.held_grant}"
                assert sample["held"], "released grant not marked held"
                self.held_continuity_checks += 1
                first = False
        drain_cycles = self.k - start
        self.drain = dict(start_cycle=start, end_cycle=self.k, cycles=drain_cycles, limit=limit,
                          released_held_grant_fired_first=not first)
        # 4. quiescence
        self.phase = "quiescent"
        for _ in range(QUIESCENT_CYCLES):
            sample = yield from self.edge([], 1)
            assert not sample["out_valid"], "output valid after full drain"
            assert sample["in_ready"] == (1 << n) - 1, f"in_ready {sample['in_ready']:#x} after drain"
            self.quiescent_cycles += 1
        self.check_conservation()

    def check_conservation(self):
        for h in range(self.n):
            assert self.generated[h] == self.accepted[h] == self.fired[h], f"source {h} conservation"
        every = [d for x in self.fired for d in x]
        assert len(every) == len(set(every)), "duplicate descriptor delivered"
        assert self.producers.backlog() == 0 and not any(self.fifo) and not self.blocked
        assert self.drain["cycles"] > 10, f"drain only {self.drain['cycles']} cycles"

    # ----- results ----------------------------------------------------------------------------

    def totals(self):
        gen = [len(x) for x in self.generated]
        acc = [len(x) for x in self.accepted]
        fired = [len(x) for x in self.fired]
        return dict(generated=gen, accepted=acc, fired=fired, generated_total=sum(gen),
                    accepted_total=sum(acc), fired_total=sum(fired))

    def result(self) -> dict:
        return dict(
            status="PASS", scope=SCOPE, job=self.job, cutoff=self.cutoff, drain=self.drain,
            final=dict(**self.totals(),
                       producer_outstanding=[len(q) for q in self.producers.pending],
                       fifo_outstanding=list(self.fifo),
                       outstanding_total=self.producers.backlog() + sum(self.fifo),
                       quiescent_cycles=self.quiescent_cycles,
                       quiescent=True),
            input_hold_checks=self.input_hold_checks,
            held_continuity_checks=self.held_continuity_checks,
            occupancy_checks=self.occupancy_checks,
            accounted_edges=self.k,
            wall_s=time.monotonic() - self.t0,
        )

    def failure(self, exc: BaseException) -> dict:
        return dict(status="FAIL", scope=SCOPE, job=self.job, phase=self.phase, cycle=self.k,
                    error=repr(exc), cutoff=self.cutoff, drain=self.drain,
                    progress=dict(**self.totals(),
                                  producer_backlog=[len(q) for q in self.producers.pending],
                                  fifo_occupancy=list(self.fifo)),
                    input_hold_checks=self.input_hold_checks,
                    held_continuity_checks=self.held_continuity_checks,
                    wall_s=time.monotonic() - self.t0)


def run_model_only(job: dict, accounting_hook=None) -> dict:
    """Drive ``DrainAccounting`` from the independent ``ExperimentalSwitchModel`` alone.

    Reset sequence matches the harness start (one reset edge, then two busy reset edges).
    ``accounting_hook(sample) -> sample`` lets negative controls corrupt the observed pins.
    """
    from cxl_model.experimental import ExperimentalSwitchModel

    kw = dict(window=job["window"], depth=job["depth"])
    if job["policy"] != "FAI-inspired":
        kw.update(high_weight=job["high_weight"], ordering=job["ordering"])
    model = ExperimentalSwitchModel(job["n_src"], job["policy"], **kw)
    for _ in range(3):
        model.commit(rst_n=False)
    serial = [0]

    def desc(h):
        serial[0] += 1
        return (serial[0] << 8) | h

    acct = DrainAccounting(job, desc, occupancy=lambda: [model.ctrl.fifos[h].occupancy
                                                         for h in range(job["n_src"])])
    steps = acct.cycles()
    try:
        push, ready = next(steps)
        while True:
            view = model.view(bool(ready), True)
            sample = dict(in_ready=sum(int(b) << h for h, b in enumerate(view.in_ready)),
                          out_valid=int(view.out_valid),
                          out_source=view.out_source if view.out_valid else None,
                          out_desc=view.out_desc if view.out_valid else None,
                          fire=bool(view.out_valid and ready), grant_ctx=view.grant_ctx,
                          held=int(view.held))
            valid = [h in push for h in range(job["n_src"])]
            descs = [push.get(h, 0) for h in range(job["n_src"])]
            if accounting_hook is not None:
                sample = accounting_hook(dict(sample))
            model.commit(bool(ready), valid, descs, True)
            push, ready = steps.send(sample)
    except StopIteration:
        pass
    return acct.result()


# ----- cocotb entry --------------------------------------------------------------------------

try:
    import cocotb
except ImportError:  # model-only use outside the simulator environment
    cocotb = None


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if cocotb is not None:

    @cocotb.test()
    async def directed_backlog_drain_rtl(dut):
        job = json.loads(os.environ["CXL_DRAIN_JOB"])
        main = job["policy"] == "FAI-inspired"
        mirror = None
        if main:
            from cxl_model.experimental import ExperimentalSwitchModel
            from test_experiment_top import P
            from test_main_diagnosis import MainHarness
            assert P["POLICY"] == 2 and P["HIGH_QUOTA"] == 10 and P["MAIN_1W"] == 0
            assert (job["n_src"], job["depth"], job["window"]) == (P["N_SRC"], P["DEPTH"], P["FAI_W"])
            harness = MainHarness(dut, "directed-drain-main", job["seed"])
            mirror = ExperimentalSwitchModel(job["n_src"], "FAI-inspired",
                                             window=job["window"], depth=job["depth"])
            harness.mirrors.append(mirror)
        else:
            from test_cgof_sched import Harness, P, POLICY_NAME, ORDERING
            assert (job["n_src"], job["depth"], job["window"]) == (P["N_SRC"], P["DEPTH"], P["FAI_W"])
            assert job["high_weight"] == P["HIGH_WEIGHT"] and job["policy"] == POLICY_NAME
            assert job["ordering"] == ORDERING == "oldest-first" and P["ELIGIBLE_RR"] == 0
            harness = Harness(dut, f"directed-drain-hw{job['high_weight']}", job["seed"])
        account = DrainAccounting(job, harness.desc,
                                  occupancy=lambda: [len(q) for q in harness.sb])
        try:
            await harness.start()
            reset_cycles_at_start = harness.cov["resets"]
            classes_at_start = list(harness.model.classes())
            assert all(c == "H" for c in classes_at_start), f"initial classes {classes_at_start}"
            steps = account.cycles()
            try:
                push, ready = next(steps)
                while True:
                    sample = await harness.cycle(push, ready=ready)
                    if mirror is not None:
                        assert mirror.classes() == harness.model.classes(), "Main mirror classes"
                        assert mirror.window_state() == harness.model.window_state(), "Main mirror window"
                        assert mirror.visit == harness.model.visit_state(), "Main mirror class quota"
                    push, ready = steps.send(sample)
            except StopIteration:
                pass
            assert not any(harness.sb), "harness scoreboard not empty after drain"
            assert harness.cov["fires"] == account.totals()["fired_total"]
            policy_model = mirror if main else harness.model
            assert policy_model.windows_closed == 0, "a window closed: not a no-training sequence"
            result = account.result()
            result.update(
                schema=SCHEMA, evidence_kind="SCHEDULER_RTL",
                params=P, policy=job["policy"],
                initial_state="reset, all sources High (H)", initial_classes=classes_at_start,
                windows_closed=policy_model.windows_closed,
                reset_cycles=harness.cov["resets"], reset_cycles_at_start=reset_cycles_at_start,
                untracked_initial_reset_edges=1,
                nonreset_cycles=harness.cov["cycles"] - harness.cov["resets"],
                harness_cycles=harness.cov["cycles"],
                native_coverage=harness.cov,
                native_policy=(harness.fai_cov if main else harness.cgof),
                limitations=("short bounded directed sequence with production W parameters; "
                             "no window closes, so no trained-class or long-production claim; "
                             "no latency, fairness, classification-adaptation or power claim"),
            )
            assert result["nonreset_cycles"] == account.k, "accounted edges != non-reset harness cycles"
            assert result["final"]["outstanding_total"] == 0
        except BaseException as exc:
            failure = dict(schema=SCHEMA, **account.failure(exc))
            _write(Path(os.environ["CXL_DRAIN_FAILURE"]), failure)
            raise
        _write(Path(os.environ["CXL_DRAIN_OUTPUT"]), result)
