#!/usr/bin/env python3
"""MODEL_ONLY CGOF/AGE exploration. No RTL, preload, shadow slots or confirmation seeds.

Each lane owns its producer, FIFO, acceptance and service history. Cold A and B
start from reset at their measured phase, receiving exactly the trained lane's
same exogenous events/descriptors. Only pending requests and histograms survive.
"""
import argparse
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "refc"))
sys.path.insert(0, str(ROOT / "sim" / "common"))
sys.path.insert(0, str(ROOT / "sim" / "performance"))
from cxl_model.experimental import ExperimentalSwitchModel, POLICIES
from hog_sparse import Traffic, StreamProducers, StreamStats, stats
from followup import Gaps, STAGES
from cxl_model.fai_main_model import MAIN_TRANSITIONS, threshold_evidence

OUT_ROOT = ROOT / "artifacts" / "implementation" / "insight-screen"
BASELINES = {"FCFS": 0, "RR10": 1, "FAI-inspired": 2}
SEEDS = tuple(range(509, 514))
SCHEMA = "cxl-insight-screen-v1"
FEEDBACK_POLICIES = ("FAI-inspired", "CGOF(2:1)") + tuple(p for p in POLICIES if p.startswith("AGE_T"))


def sha_file(path):
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def source_hashes():
    paths = [Path(__file__).resolve(), ROOT / "scripts" / "test_screen_scheduler_insights.py"]
    # Package __init__ imports these accepted controls, even in candidate runs.
    paths += [ROOT / "refc" / "cxl_model" / name for name in (
        "__init__.py", "common_ctrl_model.py", "experimental.py", "fai_main_model.py",
        "fai_alg2_model.py", "fcfs_model.py", "fifo_model.py", "rr_model.py")]
    paths += [ROOT / "refc" / "tests" / "test_experimental.py"]
    paths += [ROOT / "sim" / "performance" / name for name in ("hog_sparse.py", "followup.py")]
    paths += [ROOT / "sim" / "switch_top_fai" / "fai_stream.py"]
    paths += [ROOT / "sim" / "common" / "traffic_trace.py"]
    return {p.relative_to(ROOT).as_posix(): sha_file(p) for p in paths}


def rss_kib():
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        return None


def archive_sources(out, hashes):
    path = out / "sources.zip"
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, digest in hashes.items():
            content = (ROOT / name).read_bytes()
            assert hashlib.sha256(content).hexdigest() == digest, "source changed while archiving"
            archive.writestr(name, content)
    verify_sources(path, hashes)
    return dict(file=path.name, sha256=sha_file(path), files=hashes)


def verify_sources(path, hashes):
    with zipfile.ZipFile(path) as archive:
        assert set(archive.namelist()) == set(hashes), "source archive dependency mismatch"
        assert len(archive.infolist()) == len(hashes), "duplicate source archive entries"
        assert sum(i.file_size for i in archive.infolist()) < 16_000_000, "oversized source archive"
        for name, digest in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, "archived source mismatch"


def parameters(policy, window):
    m = ExperimentalSwitchModel(policy=policy, window=window)
    return dict(N_SRC=4, DEPTH=16, DESC_W=105, TS_W=32, RR_QUANTUM=10,
                FAI_W=window, gap_max=65535, age_threshold=m.threshold,
                normal_fires_between_rescues=m.budget_limit,
                high_weight=2 if policy == "CGOF(2:1)" else 1, low_weight=1)


def phase_row():
    return dict(cycles=0, ready=0, fires=0, avoidable_bubbles=0, held=0, rescues=0,
                generated=[0]*4, accepted=[0]*4, fired=[0]*4,
                gaps=[Gaps() for _ in range(4)])


class ArchiveAlignment:
    """Stream the actual MSQ B/B_guard pins; never loads the archive in memory."""
    def __init__(self, trace, diag):
        self.trace, self.diag = trace, diag
        self.file = gzip.open(trace, "rt", encoding="utf-8")
        self.sha, self.rows = hashlib.sha256(), 0

    def observe(self, k, view, lane, valid, desc, events):
        line = self.file.readline()
        assert line, "archive trace ended early"
        self.sha.update(line.encode())
        r = json.loads(line)
        mask = lambda xs: sum(int(x) << h for h, x in enumerate(xs))
        expected = dict(k=k, fire=int(view.fire), src=view.out_source if view.fire else None,
                        tag=view.out_desc >> 73 if view.fire else None,
                        in_valid=mask(valid), in_ready=mask(view.in_ready),
                        push=mask([a and b for a, b in zip(valid, view.in_ready)]),
                        occ=list(view.count),
                        heads=[q[0][2] >> 73 if q else None for q in lane.fifo],
                        pending=[len(q) for q in lane.producers.pending],
                        acc=[[h, d >> 73] for h, d in enumerate(desc) if valid[h] and view.in_ready[h]],
                        gen=[[h, d >> 73] for h, d in events if h],
                        heavy_gen=sum(h == 0 for h, _ in events))
        for key, value in expected.items():
            assert r[key] == value, f"archive cycle {k} {key}: {r[key]} != {value}"
        if lane.model.policy == "FAI-inspired":
            assert r["ctx"]["classes"] == lane.model.cls
            assert (r["ctx"]["turn"], r["ctx"]["used"]) == (
                int(lane.model.visit.cls == "Low"), lane.model.visit.fires)
        assert r["ctx"]["held"] == int(view.held)
        self.rows += 1

    def finish(self, trace_hash):
        assert not self.file.readline(), "archive has extra rows"
        self.file.close()
        assert self.diag["trace_sha256"] == trace_hash
        assert self.rows == self.diag["trace"]["rows"]
        assert self.sha.hexdigest() == self.diag["trace"]["sha256_uncompressed"]
        return dict(status="PASS", rows=self.rows, path=str(self.trace),
                    sha256_uncompressed=self.sha.hexdigest(), sha256=sha_file(self.trace))


class Lane:
    def __init__(self, policy, window, name, bounds):
        self.name, self.bounds = name, bounds
        self.model = ExperimentalSwitchModel(policy=policy, window=window)
        self.model.commit(rst_n=False)
        self.producers = StreamProducers(4)
        self.fifo = [deque() for _ in range(4)]
        self.phases = {}
        self.cohorts = {
            p: dict(generated=[0]*4, completed=[0]*4,
                    per_source=[{s: StreamStats() for s in STAGES} for _ in range(4)],
                    pooled_sparse={s: StreamStats() for s in STAGES})
            for p in ("A", "B")
        }
        self.last_phase, self.held = None, None
        self.windows = deque(maxlen=8)
        self.first_windows = []
        self.accepted = self.fired = self.cycles = 0
        self.pins = hashlib.sha256()
        self.class_maps = {}
        self.measurement_input_sha = {p: hashlib.sha256() for p in ("A", "B")}

    def cohort(self, k):
        for phase, (start, end) in self.bounds.items():
            if start <= k < end:
                return phase
        return None

    def step(self, k, events, ready, phase, alignment=None):
        m, producers = self.model, self.producers
        row = self.phases.setdefault(phase, phase_row()) if phase not in self.phases else self.phases[phase]
        if phase != self.last_phase:
            if self.last_phase is not None:
                for gap in self.phases[self.last_phase]["gaps"]:
                    gap.boundary(False)
            for h, gap in enumerate(row["gaps"]):
                gap.boundary(bool(self.fifo[h]))
            self.last_phase = phase
        producers.generate(k, events)
        cohort = self.cohort(k)
        if cohort:
            sha = self.measurement_input_sha[cohort]
            sha.update(f"{k}:{int(ready)}:".encode())
            for h, d in events:
                sha.update(bytes([h]) + d.to_bytes(14, "big"))
            sha.update(b"\n")
        for h, _ in events:
            row["generated"][h] += 1
            if cohort and h:
                self.cohorts[cohort]["generated"][h] += 1
        offers = producers.offers()
        valid = [h in offers for h in range(4)]
        desc = [offers[h][1] if h in offers else 0 for h in range(4)]
        v = m.view(ready)
        occ = [len(q) for q in self.fifo]
        assert list(v.count) == occ
        assert list(v.in_ready) == [n < 16 for n in occ]
        assert v.out_valid == bool(any(occ))
        if self.held is not None:
            assert (v.out_source, v.out_desc) == self.held, "held offer changed"
        self.held = (v.out_source, v.out_desc) if v.out_valid and not ready else None
        bubble = int(ready and any(occ) and not v.fire)
        row["avoidable_bubbles"] += bubble
        assert not bubble, "avoidable bubble"
        row["cycles"] += 1
        row["ready"] += int(ready)
        row["fires"] += int(v.fire)
        row["held"] += int(v.held)
        if phase in ("A", "B"):
            key = "/".join(m.cls)
            classes = self.class_maps.setdefault(phase, {})
            classes[key] = classes.get(key, 0) + 1
        if alignment:
            alignment.observe(k, v, self, valid, desc, events)
        # Digest actual accepted data and output, rather than storing completed records.
        self.pins.update(f"{k}:{int(ready)}:{v.out_source if v.fire else '-'}:".encode())
        if v.fire:
            self.pins.update(v.out_desc.to_bytes(14, "big"))
        edge = m.commit(ready, valid, desc)
        row["rescues"] += int(edge.rescue)
        if edge.closing is not None:
            closing = dict(edge.closing, trace_cycle=k)
            self.windows.append(closing)
            if len(self.first_windows) < 2:
                self.first_windows.append(closing)
        g = v.out_source if v.fire else None
        if v.fire:
            gen, acc, d = self.fifo[g].popleft()
            assert v.out_desc == d and edge.fired.entry.desc == d and k > acc >= gen
            self.fired += 1
            row["fired"][g] += 1
            c = self.cohort(gen)
            if c and g:
                result = self.cohorts[c]
                result["completed"][g] += 1
                for stage, value in zip(STAGES, (acc-gen, k-acc, k-gen)):
                    result["per_source"][g][stage].add(value)
                    result["pooled_sparse"][stage].add(value)
        for h, entry in enumerate(edge.pushed):
            assert (entry is not None) == (valid[h] and v.in_ready[h])
            if entry is not None:
                gen, d = producers.accept(h, k)
                assert d == entry.desc
                self.fifo[h].append((gen, k, d))
                self.accepted += 1
                row["accepted"][h] += 1
                self.pins.update(bytes([h]) + d.to_bytes(14, "big"))
            row["gaps"][h].observe(bool(occ[h]), h == g, int(ready), bool(self.fifo[h]))
        assert producers.generated == self.accepted + producers.backlog()
        assert self.accepted == self.fired + sum(len(q) for q in self.fifo)
        self.cycles += 1

    def drain(self, start):
        # At most pending+FIFO fires plus one initial admission bubble per source.
        pending = self.producers.backlog() + sum(map(len, self.fifo))
        for i in range(pending * 2 + 100):
            if not self.producers.backlog() and not any(self.fifo):
                return i
            self.step(start + i, (), True, "drain")
        raise AssertionError("drain bound exceeded")

    def result(self):
        assert self.producers.generated == self.accepted == self.fired
        assert not self.producers.backlog() and not any(self.fifo)
        for cohort in self.cohorts.values():
            assert cohort["generated"] == cohort["completed"], "incomplete sparse cohort"
        for gap in self.phases[self.last_phase]["gaps"]:
            gap.boundary(False)
        return dict(
            name=self.name, cycles=self.cycles, generated=self.producers.generated,
            accepted=self.accepted, fired=self.fired, peak_pending=self.producers.max_backlog,
            conservation=True, held_stable=True, avoidable_bubbles=0,
            actual_pin_sha256=self.pins.hexdigest(),
            measurement_input_sha256={p: s.hexdigest() for p, s in self.measurement_input_sha.items()},
            phases={p: {**row, "gaps": [g.as_dict() for g in row["gaps"]]}
                    for p, row in self.phases.items()},
            cohorts={p: {**c, "per_source": [{s: stats(v) for s, v in h.items()}
                                           for h in c["per_source"]],
                         "pooled_sparse": {s: stats(v) for s, v in c["pooled_sparse"].items()}}
                     for p, c in self.cohorts.items()},
            first_windows=self.first_windows, last_windows=list(self.windows),
            windows_closed=self.model.windows_closed, class_maps=self.class_maps,
        )


def archive_path(folder, policy, window, seed, suffix, prefix):
    if folder is None or policy not in BASELINES:
        return None
    return folder / "results" / f"cocotb_{prefix}_p{BASELINES[policy]}_w{window}_seed{seed}__{suffix}"


def compare_archive(run, folder):
    path = archive_path(folder, run["policy"], run["window"], run["seed"],
                        "hog_sparse_metrics.json", "hs")
    if path is None or not path.exists():
        return dict(status="PENDING", reason="matching accepted baseline metrics unavailable")
    old = json.loads(path.read_text())
    assert old["trace_sha256"] == run["trace_sha256"]
    assert old["trace_config"] == run["traffic_config"]
    lane = run["lanes"]["trained"]
    for p in ("A", "A_guard", "B", "B_guard"):
        assert lane["phases"][p]["fired"] == old["metrics"]["phases"][p]["fired"], f"{p} service mismatch"
    for p in ("A", "B"):
        expected = old["metrics"]["cohorts"][p]
        histogram = lambda s: {int(k): v for k, v in s["histogram"].items()}
        for stage in STAGES:
            actual = lane["cohorts"][p]
            assert histogram(actual["pooled_sparse"][stage]) == histogram(expected["pooled_sparse"][stage]), f"{p} histogram mismatch"
            for h in (1, 2, 3):
                assert histogram(actual["per_source"][h][stage]) == histogram(expected["per_source"][h][stage])
    return dict(status="PASS", path=str(path), sha256=sha_file(path),
                checked="A/B all-stage pooled/per-source histograms; A/B/guards per-source service")


def run_one(policy, seed, window, hs_archive=None, msq_archive=None):
    if seed not in SEEDS:
        raise ValueError("exploration seeds 509-513 only; confirmation seeds 529-548 refused")
    start = time.monotonic()
    before = source_hashes()
    traffic = Traffic(seed, window)
    bounds = dict(A=(traffic.training, traffic.a_end), B=(traffic.b_start, traffic.b_end))
    trained = Lane(policy, window, "trained", bounds)
    cold_a, cold_b = Lane(policy, window, "cold_A", bounds), Lane(policy, window, "cold_B", bounds)
    alignment = None
    trace = archive_path(msq_archive, policy, window, seed, "main_sq_trace.jsonl.gz", "msq")
    diag = archive_path(msq_archive, policy, window, seed, "main_sq_diagnosis.json", "msq")
    if trace is not None and trace.exists() and diag.exists():
        alignment = ArchiveAlignment(trace, json.loads(diag.read_text()))
    for k in range(traffic.end):
        events, ready = traffic.step(k)
        phase = traffic.phase(k)
        trained.step(k, events, ready, phase,
                     alignment if traffic.b_start <= k < traffic.end else None)
        if traffic.training <= k < traffic.b_start:
            cold_a.step(k, events, ready, phase)
        if traffic.b_start <= k:
            cold_b.step(k, events, ready, phase)
        if window == 5_000_000 and (k + 1) % 1_000_000 == 0:
            print(f"PROGRESS {policy} seed{seed} cycles={k+1} "
                  f"windows={trained.model.windows_closed} "
                  f"wall={time.monotonic()-start:.3f}s RSS={rss_kib()}KiB", flush=True)
    active_s = time.monotonic() - start
    drains = dict(trained=trained.drain(traffic.end),
                  cold_A=cold_a.drain(traffic.b_start), cold_B=cold_b.drain(traffic.end))
    result = dict(schema=SCHEMA, scope="MODEL_ONLY", status="PASS", exit_code=0,
                  policy=policy, seed=seed, window=window, production=window == 5_000_000,
                  params=parameters(policy, window),
                  actual_training_cycles=traffic.training, traffic_config=traffic.config,
                  trace_sha256=traffic.sha256, generated=traffic.generated,
                  active_cycles=traffic.end, active_wall_s=active_s,
                  drain_cycles=drains,
                  lanes={l.name: l.result() for l in (trained, cold_a, cold_b)},
                  source_hashes=before, peak_rss_kib=rss_kib())
    for p, cold in (("A", "cold_A"), ("B", "cold_B")):
        assert (result["lanes"][cold]["measurement_input_sha256"][p]
                == result["lanes"]["trained"]["measurement_input_sha256"][p])
    result["archive_metrics"] = compare_archive(result, hs_archive)
    result["archive_cycle_alignment"] = (alignment.finish(traffic.sha256) if alignment else
                                         dict(status="PENDING", reason="matching MSQ trace unavailable"))
    assert before == source_hashes(), "screen sources changed during execution"
    result["wall_s"] = time.monotonic() - start
    return result


class FeedbackTraffic:
    """Bounded outstanding stress, not exogenous HOG performance evidence."""
    def __init__(self, seed, window):
        if seed not in SEEDS or window not in (256, 5_000_000):
            raise ValueError("unsupported feedback seed/window")
        self.seed, self.window, self.end = seed, window, 4*window
        self.rng = random.Random(f"cxl-feedback-v1:{seed}")
        self.serial = self.next_cycle = 0
        self.config = dict(generator="cxl-feedback-v1", seed=seed, window=window,
                           actual_active_cycles=self.end, producer_limit_per_source=16,
                           heavy0_cycles=2*window, role_switch_cycles=window,
                           allbacklogged_cycles=window//2, churn_cycles=window//2,
                           churn_period=16, ready_stalls=[
                               [window-32, window+64],
                               [3*window+window//4, 3*window+window//4+min(1024, window//8)]],
                           source="closed-loop capped producers; not paired latency evidence")
        self.sha = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode())

    def phase(self, k):
        if k < 2*self.window:
            return "heavy0"
        if k < 3*self.window:
            return "role_switch"
        return "allbacklogged" if k < 7*self.window//2 else "churn"

    def step(self, k, producers):
        assert k == self.next_cycle and k < self.end
        self.next_cycle += 1
        phase = self.phase(k)
        if phase == "allbacklogged":
            sources = range(4)
        else:
            heavy = 0 if phase == "heavy0" else 3 if phase == "role_switch" else (k//16)%4
            sources = [heavy] + [h for h in range(4) if h != heavy and self.rng.randrange(128) == 0]
        events = []
        for h in sources:
            if len(producers.pending[h]) < 16:
                assert self.serial < 1 << 32
                events.append((h, (self.serial << 73) | self.rng.getrandbits(73)))
                self.serial += 1
        ready = not any(a <= k < b for a, b in self.config["ready_stalls"])
        self.sha.update(f"{k}:{int(ready)}:".encode())
        for h, d in events:
            self.sha.update(bytes([h]) + d.to_bytes(14, "big"))
        self.sha.update(b"\n")
        return events, ready


def run_feedback(policy, seed, window):
    start, before = time.monotonic(), source_hashes()
    traffic = FeedbackTraffic(seed, window)
    lane = Lane(policy, window, "feedback", {})
    observations = dict(longstall_cycles=0, held_stall_cycles=0,
                        all_sources_backlogged_cycles=0, max_pending_per_source=0)
    for k in range(traffic.end):
        events, ready = traffic.step(k, lane.producers)
        if not ready:
            observations["longstall_cycles"] += 1
            observations["held_stall_cycles"] += int(lane.model.ctrl.held is not None)
        if traffic.phase(k) == "allbacklogged" and all(lane.fifo):
            observations["all_sources_backlogged_cycles"] += 1
        lane.step(k, events, ready, traffic.phase(k))
        observations["max_pending_per_source"] = max(
            observations["max_pending_per_source"], max(map(len, lane.producers.pending)))
        if window == 5_000_000 and (k+1) % 1_000_000 == 0:
            print(f"FEEDBACK {policy} cycles={k+1} windows={lane.model.windows_closed} "
                  f"wall={time.monotonic()-start:.3f}s RSS={rss_kib()}KiB", flush=True)
    active_s = time.monotonic()-start
    drain = lane.drain(traffic.end)
    result = dict(schema=SCHEMA, kind="feedback", scope="MODEL_ONLY", status="PASS", exit_code=0,
                  policy=policy, seed=seed, window=window, production=window == 5_000_000,
                  params=parameters(policy, window), source_hashes=before,
                  feedback_config=traffic.config, trace_sha256=traffic.sha.hexdigest(),
                  actual_active_cycles=traffic.end, actual_feedback_windows=4,
                  lane=lane.result(), observations=observations, drain_cycles=drain,
                  active_wall_s=active_s, wall_s=time.monotonic()-start, peak_rss_kib=rss_kib())
    assert before == source_hashes(), "feedback sources changed during execution"
    validate_feedback(result, production=window == 5_000_000)
    return result


def validate_feedback(row, production=True):
    assert row["kind"] == "feedback" and row["scope"] == "MODEL_ONLY"
    assert row["status"] == "PASS" and row["exit_code"] == 0
    window, policy, seed = row["window"], row["policy"], row["seed"]
    assert window == (5_000_000 if production else 256), "wrong feedback window"
    assert row["production"] is production and seed in SEEDS and policy in POLICIES
    assert row["source_hashes"] == source_hashes(), "feedback source revision mismatch"
    assert row["params"] == parameters(policy, window), "feedback parameters differ"
    config = FeedbackTraffic(seed, window).config
    assert row["feedback_config"] == config, "feedback scenario configuration differs"
    assert row["actual_active_cycles"] == 4*window and row["actual_feedback_windows"] == 4
    lane = row["lane"]
    assert lane["windows_closed"] == 4, "missing actual window closes"
    assert lane["cycles"] == 4*window + row["drain_cycles"]
    assert 0 <= row["drain_cycles"] < window
    assert lane["generated"] == lane["accepted"] == lane["fired"] > 0
    assert lane["conservation"] and lane["held_stable"] and lane["avoidable_bubbles"] == 0
    assert sum(p["cycles"] for p in lane["phases"].values()) == lane["cycles"]
    assert sum(p["fires"] for p in lane["phases"].values()) == lane["fired"]
    for phase, count in (("heavy0",2*window), ("role_switch",window),
                         ("allbacklogged",window//2), ("churn",window//2)):
        p = lane["phases"][phase]
        assert p["cycles"] == count and p["avoidable_bubbles"] == 0
        assert p["fires"] == sum(p["fired"]) and 0 < p["fires"] <= p["ready"] <= count
        assert len(p["gaps"]) == 4 and sum(p["generated"]) > 0
    obs = row["observations"]
    assert obs["longstall_cycles"] == sum(b-a for a, b in config["ready_stalls"])
    assert 0 < obs["held_stall_cycles"] <= obs["longstall_cycles"]
    assert 0 < obs["all_sources_backlogged_cycles"] <= window//2
    assert 0 < obs["max_pending_per_source"] <= 16
    closes = lane["last_windows"]
    assert len(closes) == 4 and closes[:2] == lane["first_windows"]
    classes = ["H"]*4
    for i, close in enumerate(closes):
        assert close["window"] == i and close["trace_cycle"] == (i+1)*window-1
        counts, total = close["counts"], close["total"]
        assert len(counts) == 4 and all(type(b) is int and 0 <= b <= window for b in counts)
        assert sum(counts) == total <= window
        evidence = [threshold_evidence(4, b, total) for b in counts]
        assert list(close["evidence"]) == evidence and list(close["old_classes"]) == classes
        classes = [MAIN_TRANSITIONS[c, e] for c, e in zip(classes, evidence)]
        assert list(close["classes"]) == classes
    assert len(row["trace_sha256"]) == 64
    return True


def load_evidence(path, kind):
    """Validate a sealed local run, source bytes and report before gate ingestion."""
    path = path.resolve()
    row = json.loads(path.read_text())
    summary = json.loads((path.parent / "summary.json").read_text())
    assert summary["exit_code"] == summary["validation_exit"] == 0
    assert summary["source_hashes"] == row["source_hashes"] == source_hashes()
    assert summary["report_hashes"][path.name] == sha_file(path), "altered evidence report"
    assert summary["kind"] == kind
    archive = summary["source_archive"]
    assert archive["file"] == "sources.zip" and archive["files"] == row["source_hashes"]
    source_zip = path.parent / archive["file"]
    assert sha_file(source_zip) == archive["sha256"], "altered source archive"
    verify_sources(source_zip, row["source_hashes"])
    validation = path.parent / "validation.json"
    assert sha_file(validation) == summary["validation_sha256"], "altered validation evidence"
    checks = json.loads(validation.read_text())
    assert len(checks) == 2 and all(c["exit_code"] == 0 for c in checks)
    binding = row["validation_binding"]
    assert Path(binding["artifact_directory"]).resolve() == path.parent
    assert binding["validation_sha256"] == summary["validation_sha256"]
    assert binding["source_archive_sha256"] == archive["sha256"]
    validate_binding(row)
    if kind == "feedback":
        validate_feedback(row)
    else:
        validate_hog(row)
    return row


def validate_binding(row):
    binding = row["validation_binding"]
    assert binding["exit_code"] == 0
    assert binding["source_hashes"] == row["source_hashes"] == source_hashes()
    directory = Path(binding["artifact_directory"])
    assert directory.is_absolute()
    validation, archive = directory / "validation.json", directory / "sources.zip"
    assert sha_file(validation) == binding["validation_sha256"]
    assert sha_file(archive) == binding["source_archive_sha256"]
    verify_sources(archive, row["source_hashes"])
    checks = json.loads(validation.read_text())
    assert len(checks) == 2 and all(c["exit_code"] == 0 for c in checks)
    expected = ("test_experimental.py", "test_screen_scheduler_insights.py")
    for check, name in zip(checks, expected):
        assert any(Path(arg).name == name for arg in check["command"])


def validate_hog(row):
    """Production is established from clocks, configuration and raw conservation."""
    validate_binding(row)
    assert row["scope"] == "MODEL_ONLY" and row["status"] == "PASS" and row["exit_code"] == 0
    assert row["window"] == 5_000_000 and row["production"] is True
    assert row["seed"] in SEEDS and row["policy"] in POLICIES
    traffic = Traffic(row["seed"], row["window"])
    assert row["actual_training_cycles"] == 2*traffic.window
    assert row["active_cycles"] == traffic.end and row["traffic_config"] == traffic.config
    assert row["params"] == parameters(row["policy"], row["window"])
    assert len(row["trace_sha256"]) == 64
    lengths = dict(training=traffic.training, A=100_000, A_guard=1024, B=102_400, B_guard=1024)
    assert set(row["lanes"]) == {"trained", "cold_A", "cold_B"}
    for name, lane in row["lanes"].items():
        active = lengths if name == "trained" else {p: lengths[p] for p in (
            ("A", "A_guard") if name == "cold_A" else ("B", "B_guard"))}
        drain = row["drain_cycles"][name]
        assert type(drain) is int and 0 <= drain < traffic.window
        assert lane["cycles"] == sum(active.values()) + drain
        assert lane["windows_closed"] == lane["cycles"]//traffic.window
        assert set(lane["phases"]) == set(active) | ({"drain"} if drain else set())
        assert lane["generated"] == lane["accepted"] == lane["fired"]
        assert lane["conservation"] and lane["held_stable"] and lane["avoidable_bubbles"] == 0
        assert sum(p["fires"] for p in lane["phases"].values()) == lane["fired"]
        for p, count in {**active, **({"drain": drain} if drain else {})}.items():
            phase = lane["phases"][p]
            assert phase["cycles"] == phase["ready"] == count
            assert phase["fires"] == sum(phase["fired"]) <= count
            assert phase["avoidable_bubbles"] == 0 and len(phase["gaps"]) == 4
            assert phase["generated"][0] == (0 if p == "drain" else count)
            if p in ("A_guard", "B_guard", "drain"):
                assert phase["generated"][1:] == [0]*3
        for key, total in (("generated", lane["generated"]), ("accepted", lane["accepted"]), ("fired", lane["fired"])):
            assert sum(sum(p[key]) for p in lane["phases"].values()) == total
        for phase in ("A", "B"):
            cohort = lane["cohorts"][phase]
            assert cohort["generated"] == cohort["completed"]
            assert cohort["generated"] == [0] + lane["phases"].get(phase, {"generated":[0]*4})["generated"][1:]
            for stage in STAGES:
                pooled = Counter()
                for h in range(4):
                    sample = cohort["per_source"][h][stage]
                    s = StreamStats()
                    s.hist = {int(k): v for k, v in sample["histogram"].items()}
                    assert all(k >= 0 and type(v) is int and v > 0 for k, v in s.hist.items())
                    s.count, s.total = sum(s.hist.values()), sum(k*v for k, v in s.hist.items())
                    assert s.as_dict() == {k: v for k, v in sample.items() if k != "histogram"}
                    assert s.count == cohort["completed"][h]
                    if h:
                        pooled.update(s.hist)
                target = cohort["pooled_sparse"][stage]
                assert dict(pooled) == {int(k):v for k, v in target["histogram"].items()}
                s = StreamStats()
                s.hist, s.count = dict(pooled), sum(pooled.values())
                s.total = sum(k*v for k, v in pooled.items())
                assert s.as_dict() == {k:v for k, v in target.items() if k != "histogram"}
    trained = row["lanes"]["trained"]
    assert row["generated"] == [sum(p["generated"][h] for p in trained["phases"].values()) for h in range(4)]
    assert len(trained["first_windows"]) == 2
    for i, close in enumerate(trained["first_windows"]):
        assert close["window"] == i and close["trace_cycle"] == (i+1)*traffic.window-1
        assert sum(close["counts"]) == close["total"] <= traffic.window
    for p in ("A", "B"):
        assert (trained["measurement_input_sha256"][p]
                == row["lanes"]["cold_"+p]["measurement_input_sha256"][p])
    return True


def candidate_metrics(rows, policy):
    paired = {}
    for r in rows:
        if r["policy"] in ("FAI-inspired", policy):
            paired[r["seed"], r["policy"]] = r
    values = {}
    for state in ("cold", "trained"):
        for phase in ("A", "B"):
            lane = "trained" if state == "trained" else "cold_" + phase
            deltas, absolute, baseline = [], [], []
            for seed in SEEDS:
                a = paired[seed, policy]["lanes"][lane]["cohorts"][phase]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"]
                b = paired[seed, "FAI-inspired"]["lanes"][lane]["cohorts"][phase]["pooled_sparse"]["generation_to_fire"]["p99_nearest_rank"]
                assert a is not None and b is not None
                deltas.append(a-b)
                absolute.append(a)
                baseline.append(b)
            values[state+"_"+phase] = dict(deltas=deltas, mean_delta=sum(deltas)/5,
                                           mean_candidate_p99=sum(absolute)/5,
                                           mean_baseline_p99=sum(baseline)/5,
                                           improvements=sum(x < 0 for x in deltas))
    heavy_drops = []
    for seed in SEEDS:
        for lane, phases in (("trained", ("A", "B")), ("cold_A", ("A",)), ("cold_B", ("B",))):
            for phase in phases:
                a = paired[seed, policy]["lanes"][lane]["phases"][phase]
                b = paired[seed, "FAI-inspired"]["lanes"][lane]["phases"][phase]
                heavy_drops.append(b["fired"][0]/b["fires"] - a["fired"][0]/a["fires"])
    b_pass = any(values[s+"_B"]["mean_delta"] <= -1 and values[s+"_B"]["improvements"] >= 4
                 for s in ("cold", "trained"))
    a_pass = all(values[s+"_A"]["mean_delta"] <= 1 for s in ("cold", "trained"))
    return dict(paired_p99=values, max_heavy_service_fraction_drop=max(heavy_drops),
                numerical_pass=b_pass and a_pass and max(heavy_drops) <= .0001 + 1e-12,
                worst_mean_B=max(values[s+"_B"]["mean_candidate_p99"] for s in ("cold", "trained")))


def evaluate_gate(rows, validation_exit, feedback_rows=()):
    required = {(s, p) for s in SEEDS for p in POLICIES}
    present = {(r.get("seed"), r.get("policy")) for r in rows if r.get("production")}
    reasons = []
    if present != required or len(rows) != len(required):
        reasons.append("incomplete production matrix: all 12 policies x 5 seeds required")
    if validation_exit != 0:
        reasons.append("directed/differential runner validation missing or failed")
    if any(r.get("exit_code") != 0 or r.get("status") != "PASS" for r in rows):
        reasons.append("failed configuration")
    for row in rows:
        try:
            validate_hog(row)
        except (AssertionError, KeyError, TypeError, ValueError, OSError, zipfile.BadZipFile) as exc:
            reasons.append(f"invalid production HOG evidence: {type(exc).__name__}: {exc}")
    candidates = {}
    if not reasons:
        if len({json.dumps(r["source_hashes"], sort_keys=True) for r in rows}) != 1:
            reasons.append("mixed source revisions")
        for seed in SEEDS:
            group = [r for r in rows if r["seed"] == seed]
            if len({r["trace_sha256"] for r in group}) != 1:
                reasons.append(f"unpaired exogenous trace seed{seed}")
        controls = [r for r in rows if r["policy"] in BASELINES]
        if any(r["archive_metrics"]["status"] != "PASS" for r in controls):
            reasons.append("baseline archive histogram/service validation pending")
        # The representative archive exists for seed509; other seeds need metrics joins.
        if any(r["archive_cycle_alignment"]["status"] != "PASS"
               for r in controls if r["seed"] == 509):
            reasons.append("representative archive cycle alignment pending")
        for r in rows:
            for lane in r["lanes"].values():
                if not (lane["conservation"] and lane["held_stable"] and lane["avoidable_bubbles"] == 0):
                    reasons.append("conservation/held/bubble invariant failed")
        if not reasons:
            candidates = {p: candidate_metrics(rows, p) for p in POLICIES
                          if p not in BASELINES and p not in ("CGOF(1:1)", "AGE_ONLY")}
    passing = [p for p, v in candidates.items() if v["numerical_pass"]]
    numerical_winner = min(passing, key=lambda p: (candidates[p]["worst_mean_B"],
                                                  0 if p.startswith("AGE") else 1, p)) if passing else None
    hog_status = "UNRESOLVED" if reasons else ("PASS" if numerical_winner else "FAIL")
    feedback = {}
    for row in feedback_rows:
        try:
            validate_binding(row)
            validate_feedback(row)
            key = (row["policy"], row["seed"])
            assert key not in feedback, "duplicate feedback"
            feedback[key] = row
        except (AssertionError, KeyError, TypeError, ValueError, OSError, zipfile.BadZipFile) as exc:
            reasons.append(f"invalid feedback evidence: {exc}")
    feedback_complete = all((p, 509) in feedback for p in FEEDBACK_POLICIES)
    if not feedback_complete:
        reasons.append("advancement requires seed509 four-actual-W5M feedback/scenarios for FAI-inspired and all seven candidates")
    status = "UNRESOLVED" if reasons else ("PASS" if numerical_winner else "FAIL")
    return dict(scope="MODEL_ONLY", status=status, numerical_hog_status=hog_status,
                production_gate="NOT_RUN" if present != required else "EVALUATED",
                reasons=reasons, frozen_candidate=numerical_winner if status == "PASS" else None,
                candidates=candidates, endpoint="paired run P99 generation_to_fire; delta=candidate-FAI-inspired",
                long_feedback_4_actual_W5M_windows="PASS" if feedback_complete else "NOT_RUN",
                advancement_scenario_evidence="PASS" if feedback_complete else "NOT_RUN",
                validated_feedback=[dict(policy=p, seed=s, trace_sha256=r["trace_sha256"])
                                    for (p, s), r in sorted(feedback.items())],
                numerical_hog_leader=numerical_winner,
                cgof_all_backlogged="separate directed weighted objective; not sparseHOG benefit",
                age_only="negative control can equal FCFS")


def latest_archive(name):
    folder = ROOT / "artifacts" / "implementation" / name
    latest = folder / "latest.txt"
    return folder / latest.read_text().strip() if latest.exists() else None


def main(argv=None):
    if not __debug__:
        raise RuntimeError("run without -O: evidence and cycle invariant assertions are required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("pilot", "production"), default="pilot")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--feedback", action="store_true", help="four actual windows plus bounded stress scenarios")
    mode.add_argument("--evaluate", type=Path, nargs="+", help="evaluate sealed production HOG reports without rerunning")
    parser.add_argument("--feedback-evidence", type=Path, nargs="*", default=[])
    parser.add_argument("--seeds", type=int, nargs="+", default=[509])
    parser.add_argument("--policies", choices=POLICIES, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--hs-archive", type=Path)
    parser.add_argument("--msq-archive", type=Path)
    args = parser.parse_args(argv)
    args.policies = args.policies or list(FEEDBACK_POLICIES if args.feedback else POLICIES)
    if any(s not in SEEDS for s in args.seeds):
        parser.error("only exploration seeds 509-513; confirmation seeds 529-548 are refused")
    if len(set(args.seeds)) != len(args.seeds) or len(set(args.policies)) != len(args.policies):
        parser.error("duplicate seeds/policies")
    out = args.out.resolve()
    if not out.is_relative_to(OUT_ROOT.resolve()) or out == OUT_ROOT.resolve():
        parser.error(f"--out must be a new child directory of {OUT_ROOT}")
    out.mkdir(parents=True, exist_ok=False)
    initial_hashes = source_hashes()
    source_archive = archive_sources(out, initial_hashes)
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s",
               str(ROOT / "refc" / "tests"), "-p", "test_experimental.py"]
    screen_tests = [sys.executable, "-B", str(ROOT / "scripts" / "test_screen_scheduler_insights.py")]
    checks = []
    for cmd in (command, screen_tests):
        check = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        checks.append(dict(command=cmd, exit_code=check.returncode,
                           stdout=check.stdout, stderr=check.stderr))
    validation_exit = int(any(c["exit_code"] for c in checks))
    (out / "validation.json").write_text(json.dumps(checks, indent=2) + "\n")
    binding = dict(exit_code=validation_exit, source_hashes=initial_hashes,
                   artifact_directory=str(out), validation_sha256=sha_file(out / "validation.json"),
                   source_archive_sha256=source_archive["sha256"])
    rows, failures, feedback_rows, reports, ingested = [], [], [], {}, []
    window = 5_000_000 if args.evaluate else 256 if args.scope == "pilot" else 5_000_000
    hs = args.hs_archive or latest_archive("HS-pilot" if args.scope == "pilot" else "HS-main")
    msq = args.msq_archive or latest_archive("MSQ-pilot" if args.scope == "pilot" else "MSQ-main")
    if not validation_exit:
        try:
            for path in args.feedback_evidence:
                feedback_rows.append(load_evidence(path, "feedback"))
                ingested.append(dict(path=str(path.resolve()), sha256=sha_file(path)))
            if args.evaluate:
                for path in args.evaluate:
                    rows.append(load_evidence(path, "hog"))
                    ingested.append(dict(path=str(path.resolve()), sha256=sha_file(path)))
        except Exception:
            failures.append(dict(status="FAIL", exit_code=1, failure=traceback.format_exc()))
        for seed in (() if args.evaluate or failures else args.seeds):
            for policy in args.policies:
                print(f"START MODEL_ONLY {'feedback' if args.feedback else 'hog'} W{window} seed{seed} {policy}", flush=True)
                try:
                    row = run_feedback(policy, seed, window) if args.feedback else run_one(policy, seed, window, hs, msq)
                    assert initial_hashes == row["source_hashes"], "source revision changed between configurations"
                    row["validation_binding"] = binding
                    validate_binding(row)
                    if window == 5_000_000:
                        validate_feedback(row) if args.feedback else validate_hog(row)
                    rows.append(row)
                    print(f"PASS {policy} wall={row['wall_s']:.3f}s RSS={row['peak_rss_kib']}KiB", flush=True)
                except Exception:
                    row = dict(scope="MODEL_ONLY", status="FAIL", exit_code=1, seed=seed,
                               policy=policy, window=window, production=window == 5_000_000,
                               failure=traceback.format_exc())
                    failures.append(row)
                    print(row["failure"], flush=True)
                file_policy = (f"cgof-hw{ExperimentalSwitchModel(policy=policy).high_weight}"
                               if policy.startswith("CGOF") else policy)
                report = out / f"{file_policy}_seed{seed}.json"
                report.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
                reports[report.name] = sha_file(report)
                if failures:
                    break
            if failures:
                break
    if source_hashes() != initial_hashes:
        failures.append(dict(status="FAIL", exit_code=1, failure="sources changed during execution"))
    exit_code = int(bool(validation_exit or failures))
    if args.feedback:
        feedback_rows += rows if window == 5_000_000 else []
    gate = evaluate_gate([] if args.feedback else rows + failures,
                         validation_exit or exit_code, feedback_rows)
    summary = dict(schema=SCHEMA, scope="MODEL_ONLY", partial=gate["status"] == "UNRESOLVED",
                   kind="feedback" if args.feedback else "evaluate" if args.evaluate else "hog",
                   command=sys.argv, exit_code=exit_code, validation_exit=validation_exit,
                   source_hashes=initial_hashes, gate=gate, completed=len(rows),
                   failures=failures, window=window, seeds=args.seeds, policies=args.policies,
                   source_archive=source_archive, report_hashes=reports,
                   validation_sha256=sha_file(out / "validation.json"), ingested_evidence=ingested)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["gate"], indent=2), flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
