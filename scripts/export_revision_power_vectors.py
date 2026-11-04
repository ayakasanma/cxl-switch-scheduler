"""F12 trained HOG pin export and independent local replay; no network or EDA jobs."""
from __future__ import annotations

import argparse
from collections import deque
import datetime as dt
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ("scripts", "refc", "sim/experimental")]
import export_power_vectors as legacy
from check_power_replay import check_pt, expected_result_v2
from cxl_model.experimental import ExperimentalSwitchModel
from revision_traffic import Traffic

SCHEMA = "cxl-revision-trained-power-v1"
POLICIES = {"fcfs": "FCFS", "rr": "RR10", "fai-main": "FAI-inspired"}
SEEDS = tuple(range(509, 514))
POWER_SEEDS = (509, 510, 511)
MODES = {"A": 12, "B": 13}
PRODUCTION_W = 5_000_000
MEASURED = {"A": 100_000, "B": 102_400}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def plan(policy, seed, arm, window=PRODUCTION_W, smoke_cycles=None):
    require(type(seed) is int and type(window) is int, "seed/window must be integers")
    require(policy in POLICIES and seed in SEEDS and arm in MODES, "unsupported policy/seed/arm")
    require(window in (256, PRODUCTION_W), "only W256 sensitivity or production W5M")
    require(smoke_cycles is None or
            (window == 256 and type(smoke_cycles) is int and 0 < smoke_cycles <= MEASURED[arm]),
            "short measurement is sensitivity-only at W256")
    warmup = 2 * window + (101_024 if arm == "B" else 0)
    measured = smoke_cycles or MEASURED[arm]
    return dict(schema=SCHEMA, mode=f"trained-hog-{arm}", mode_id=MODES[arm], arm=arm,
                policy=policy, policy_id=legacy.POLICIES[policy][0], seed=seed, n_src=4,
                depth=16, descriptor_bits=105, rr_quantum=10, fai_window=window,
                training_cycles=2 * window, warmup_cycles=warmup, measured_cycles=measured,
                total_cycles=warmup + measured, period_ps=legacy.PERIOD_PS,
                duration_ns=25 * measured, reset_edges_outside_window=legacy.RESET_EDGES,
                production_evidence=window == PRODUCTION_W, sensitivity_only=window != PRODUCTION_W,
                seed_role="exploration", planned_power_seed=seed in POWER_SEEDS,
                smoke_cycles=smoke_cycles, replaces_primary_dataset=False,
                saif_window=f"{arm} only; replay all preceding edges without annotation")


def traffic_for(m):
    return Traffic(dict(group="matched-power", n_src=4, depth=16, window=m["fai_window"],
                        seed=m["seed"], heavy_source=0, heavy_rate=1, ready="always",
                        burst_size=8, burst_period=1024))


def sources():
    paths = ("scripts/export_revision_power_vectors.py",
             "scripts/test_revision_power_vectors.py",
             "sim/experimental/revision_traffic.py",
             "sim/performance/hog_sparse.py", "sim/performance/followup.py",
             "sim/switch_top_fai/fai_stream.py", "scripts/revision_statistics.py",
             "scripts/revision_matrix.py",
             "rtl/filelist_switch.f", "rtl/top/switch_top.sv",
             "rtl/include/cxl_sched_pkg.sv")
    paths += tuple(p.relative_to(ROOT).as_posix() for p in sorted((ROOT/"rtl/common").glob("*.sv")))
    return legacy._sources(*paths)


def archive_inputs(destination, policy, source_hashes, case_hashes):
    """Freeze exact project sources and mapped inputs, never external library assets."""
    paths = {p: (ROOT / p, digest) for p, digest in source_hashes.items()}
    case = ROOT / f"artifacts/fastx/primary-20261021-v2-{policy}-n4"
    paths.update({f"mapped/{p}": (case / p, digest) for p, digest in case_hashes.items()})
    with zipfile.ZipFile(destination / "source-freeze.zip", "x") as archive:
        for name, (path, digest) in sorted(paths.items()):
            data = path.read_bytes()
            require(hashlib.sha256(data).hexdigest() == digest, f"source changed before archive: {name}")
            entry = zipfile.ZipInfo(name)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)


def header(m):
    return (f"{legacy.V2_MAGIC} {m['mode_id']} 4 {m['total_cycles']} {m['warmup_cycles']} "
            f"{m['measured_cycles']} {m['seed']} {m['policy_id']} 25000 3")


def check_contract(m):
    expected = plan(m["policy"], m["seed"], m["arm"], m["fai_window"], m["smoke_cycles"])
    require(all(m.get(k) == v and type(m.get(k)) is type(v) for k, v in expected.items()),
            "metadata differs from fixed F12 contract")


def audit_rows(rows, m):
    """Recheck serialized pins with a separate policy implementation and passive FIFO ledger."""
    check_contract(m)
    traffic = traffic_for(m)
    model = ExperimentalSwitchModel(4, POLICIES[m["policy"]], m["fai_window"], 16)
    for _ in range(3):
        model.commit(rst_n=False)
    producer = legacy.StreamProducers(4)
    hold = legacy.InputHoldChecker(4)
    fifo = [deque() for _ in range(4)]
    counters = {p: dict(cycles=0, accepted_per_source=[0]*4, fires_per_source=[0]*4)
                for p in ("warmup", "measured")}
    phase_hashes, phase_counts, phase_totals = {}, {}, {}
    cut, nrows, closings = None, 0, []
    for k, row in enumerate(rows):
        require(k < m["total_cycles"] and len(row) == 8 and row[0] == k, "row index/count/shape")
        _, valid, packed, ready, in_ready, out_valid, source, desc = row
        require(0 <= valid < 16 and 0 <= packed < 1 << 420 and ready in (0, 1)
                and 0 <= in_ready < 16 and out_valid in (0, 1) and 0 <= source < 4
                and 0 <= desc < 1 << 105, f"cycle {k}: pin width/range")
        events, expected_ready = traffic.step(k)
        producer.generate(k, events)
        offers = producer.offers()
        inputs = [offers[h][1] if h in offers else 0 for h in range(4)]
        require((valid, packed, ready) == (sum(1 << h for h in offers),
                sum(d << (105*h) for h, d in enumerate(inputs)), expected_ready),
                f"cycle {k}: serialized inputs differ from exogenous HOG/producer")
        hold.step(k, 1, valid, in_ready, inputs)
        view = model.view(out_ready=bool(ready))
        require(in_ready == sum(int(len(q) < 16) << h for h, q in enumerate(fifo)),
                f"cycle {k}: independent full-before-pop readiness")
        require(out_valid == int(any(fifo)) == int(view.out_valid) and
                in_ready == sum(int(v) << h for h, v in enumerate(view.in_ready)),
                f"cycle {k}: independent model readiness/valid")
        if out_valid:
            require((source, desc) == (view.out_source, view.out_desc),
                    f"cycle {k}: independent policy replay differs")
            require(bool(fifo[source]) and fifo[source][0] == desc, f"cycle {k}: FIFO integrity")
        if k == m["warmup_cycles"]:
            cut = dict(occupancy=[len(q) for q in fifo], classes=list(model.classes()),
                       window_state=list(model.window_state()))
        name = "warmup" if k < m["warmup_cycles"] else "measured"
        c = counters[name]
        c["cycles"] += 1
        phase = traffic.phase(k)
        phase_hashes.setdefault(phase, hashlib.sha256()).update((legacy._row_text(row)+"\n").encode("ascii"))
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        pc = phase_totals.setdefault(phase, dict(accepted_per_source=[0]*4, fires_per_source=[0]*4))
        if out_valid and ready:
            fifo[source].popleft()
            c["fires_per_source"][source] += 1
            pc["fires_per_source"][source] += 1
        for h in range(4):
            if valid & in_ready & (1 << h):
                require(producer.accept(h, k)[1] == inputs[h], "producer descriptor changed")
                fifo[h].append(inputs[h])
                c["accepted_per_source"][h] += 1
                pc["accepted_per_source"][h] += 1
        edge = model.commit(out_ready=bool(ready), in_valid=[bool(valid >> h & 1) for h in range(4)],
                            in_desc=inputs)
        if m["policy"] == "fai-main" and edge.closing:
            closing = edge.closing
            closings.append(dict(cycle=k, b_close=list(closing["counts"]), s_close=closing["total"],
                                 evidence=list(closing["evidence"]),
                                 old_classes=list(closing["old_classes"]),
                                 next_cycle_classes=list(closing["classes"])))
        require(all(len(fifo[h]) == model.occupancy(h) for h in range(4)), "model occupancy mismatch")
        nrows += 1
    require(nrows == m["total_cycles"], "missing vector rows")
    for p, c in counters.items():
        require(all(c[k] == m[p][k] for k in c), f"{p} counters differ from export")
    end = [len(q) for q in fifo]
    require(cut["occupancy"] == m["outstanding_at_cut"] and end == m["outstanding_at_end"],
            "phase cut/end occupancy differs")
    accepted = [sum(c["accepted_per_source"][h] for c in counters.values()) for h in range(4)]
    fired = [sum(c["fires_per_source"][h] for c in counters.values()) for h in range(4)]
    require([a-f for a, f in zip(accepted, fired)] == end, "per-source conservation")
    require(producer.generated == sum(accepted) + producer.backlog() == m["generated"]
            and producer.backlog() == m["generated_but_unaccepted"], "generated conservation")
    require(m["all"] == dict(cycles=nrows, generated=producer.generated,
                            accepted=sum(accepted), fires=sum(fired)), "all-phase totals differ")
    require(traffic.sha256 == m["trace"]["sha256"], "exogenous trace hash differs")
    if m["policy"] == "fai-main":
        require(cut["classes"] == m["state_at_cut"]["classes"], "trained classes differ")
        require(closings == [{key: c[key] for key in closings[0]} for c in m["closings"]],
                "training/measurement closing statistics differ")
        for state, actual in ((m["state_at_cut"], cut["window_state"]),
                              (m["state_at_end"], model.window_state())):
            require((state["window_position"], tuple(state["b"]), state["s"]) ==
                    (actual[0], tuple(actual[1]), actual[2]), "cut/end window statistics differ")
    return dict(status="INDEPENDENT_MODEL_AND_PIN_FIFO_CHECKED", rows=nrows,
                warmup=counters["warmup"], measured=counters["measured"], state_at_cut=cut,
                outstanding_at_end=end, generated=producer.generated,
                generated_but_unaccepted=producer.backlog(), input_hold_checks=hold.checked,
                traffic_phase_cycles=phase_counts,
                main_closings=closings,
                traffic_phase_totals=phase_totals,
                traffic_phase_pin_sha256={p: d.hexdigest() for p, d in phase_hashes.items()})


def audit_export(destination):
    destination = Path(destination)
    m = json.loads((destination / "metadata.json").read_text())
    check_contract(m)
    require(legacy.sha(destination / "vectors.txt.gz") == m["vectors_gzip_sha256"], "gzip hash mismatch")
    require(sources() == m["source_sha256"], "source hashes changed since export")
    archive = destination / "source-freeze.zip"
    require(legacy.sha(archive) == m["source_archive_sha256"], "source archive hash mismatch")
    inventory = {**m["source_sha256"],
                 **{f"mapped/{p}": digest for p, digest in m["accepted_case_sha256"].items()}}
    with zipfile.ZipFile(archive) as frozen:
        require(sorted(frozen.namelist()) == sorted(inventory), "source archive inventory differs")
        require(all(hashlib.sha256(frozen.read(p)).hexdigest() == digest
                    for p, digest in inventory.items()), "source archive contents differ")
    revision, hashes = legacy._accepted_case(m["policy"], 4)
    require((revision, hashes) == (m["accepted_source_revision"], m["accepted_case_sha256"]),
            "mapped case hashes changed since export")
    digest = hashlib.sha256()

    def rows():
        with gzip.open(destination / "vectors.txt.gz", "rb") as f:
            line = f.readline()
            require(line == (header(m)+"\n").encode("ascii"), "v2 header differs")
            digest.update(line)
            for line in f:
                digest.update(line)
                fields = line.decode("ascii").split()
                require(len(fields) == 8, "vector field count")
                yield tuple(int(v, 10 if i == 0 else 16) for i, v in enumerate(fields))
    report = audit_rows(rows(), m)
    require(digest.hexdigest() == m["vectors_text_sha256"], "text hash mismatch")
    require(m["vectors_rows"] == report["rows"], "declared row count differs")
    require(sources() == m["source_sha256"], "source changed during independent replay")
    require(legacy._accepted_case(m["policy"], 4) ==
            (m["accepted_source_revision"], m["accepted_case_sha256"]),
            "mapped case changed during independent replay")
    return report


def export_case(policy, seed, arm, destination, window=PRODUCTION_W, smoke_cycles=None):
    m = plan(policy, seed, arm, window, smoke_cycles)
    revision, hashes = legacy._accepted_case(policy, 4)
    before = sources()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        archive_inputs(destination, policy, before, hashes)
        traffic, stats = traffic_for(m), {}
        steps = (traffic.step(k) for k in range(m["total_cycles"]))
        rows = legacy.replay_phases(policy, 4, steps, m["total_cycles"], m["warmup_cycles"],
                                    stats, window=window)
        phase_times = {}

        def timed_rows():
            last, tick = None, time.monotonic()
            for row in rows:
                phase = traffic.phase(row[0])
                if phase != last:
                    now = time.monotonic()
                    if last is not None:
                        phase_times[last] = now - tick
                    tick, last = now, phase
                yield row
            if last is not None:
                phase_times[last] = time.monotonic() - tick
        digest, count = legacy._write_vectors(destination, header(m), timed_rows())
        if policy == "fai-main" and window == PRODUCTION_W:
            training = [c for c in stats["closings"] if c["cycle"] < 2*window]
            require([c["cycle"] for c in training] == [window-1, 2*window-1] and
                    [c["next_cycle_classes"] for c in training] ==
                    [["B_H", "H", "H", "H"], ["L", "H", "H", "H"]],
                    "two real HOG training closes must yield literal expected Main classes")
        m.update(stats)
        m.update(status="EXPORTED_INDEPENDENT_AUDIT_PENDING_GATE_NOT_RUN",
                 vectors_rows=count, vectors_text_sha256=digest,
                 vectors_gzip_sha256=legacy.sha(destination / "vectors.txt.gz"),
                 trace=dict(config=traffic.config, sha256=traffic.sha256, generated=traffic.generated),
                 source_sha256=before, accepted_source_revision=revision, accepted_case_sha256=hashes,
                 source_archive_sha256=legacy.sha(destination / "source-freeze.zip"),
                 profile_canonical_sha256=legacy.PROFILE_SHA,
                 source_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                 command=[sys.executable, *sys.argv], python=sys.version, platform=platform.platform(),
                 started_utc=started, export_phase_seconds=phase_times,
                 gate_replay_status="NOT_RUN", dc_pt_power_status="NOT_RUN",
                 integration_status="BLOCKED_EXISTING_NATIVE_MODE_ALLOWLIST")
        require(sources() == before, "source changed during export")
        meta = destination / "metadata.json"
        meta.write_text(json.dumps(m, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        audit_start = time.monotonic()
        audit = audit_export(destination)
        require(sources() == before, "source changed during independent audit")
        audit.update(exit=0, audit_seconds=time.monotonic()-audit_start)
        (destination / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True)+"\n")
        m.update(status="MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN", exit=0,
                 audit_sha256=legacy.sha(destination / "audit.json"),
                 elapsed_seconds=time.monotonic()-start,
                 finished_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        meta.write_text(json.dumps(m, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        return m
    except Exception as exc:
        (destination / "failure.json").write_text(json.dumps(dict(exit=1, error=repr(exc),
            started_utc=started, elapsed_seconds=time.monotonic()-start,
            source_sha256_before=before, source_sha256_after=sources(),
            command=[sys.executable, *sys.argv]), indent=2)+"\n")
        raise


def check_gate_result(m, result):
    """F12 result contract, ready for the native mode extension; never invent gate output."""
    check_contract(m)
    require(Path(result).read_text().splitlines() == expected_result_v2(m),
            "gate replay missing/extra/different phase or source totals")
    return dict(status="F12_GATE_TOTALS_CHECKED_SAIF_PT_NOT_CHECKED",
                result_sha256=legacy.sha(result))


def check_activity(m, result, saif):
    """Same duration/scope/clock contract as the existing supplementary replay checker."""
    totals = check_gate_result(m, result)
    text = Path(saif).read_text()
    scale = re.search(r"\(TIMESCALE\s+([\d.eE+-]+)\s+(ps|ns|us|ms|s)\s*\)", text)
    duration = re.search(r"\(DURATION\s+([\d.eE+-]+)\s*\)", text)
    require(scale is not None and duration is not None, "SAIF units/duration missing")
    ns = Decimal(scale[1]) * Decimal(duration[1]) * {
        "ps": Decimal(".001"), "ns": Decimal(1), "us": Decimal(1000),
        "ms": Decimal(1_000_000), "s": Decimal(1_000_000_000)}[scale[2]]
    require(ns == m["duration_ns"], "SAIF must cover measured phase only")
    require(re.search(r"\(INSTANCE\s+tb\s+\(INSTANCE\s+dut\b", text), "SAIF tb/dut scope missing")
    clock = re.search(r"\(clk\s+((?:\(\w+\s+\d+\)\s*)+)\)", text)
    require(clock is not None, "SAIF dut clock record missing")
    fields = {k: int(v) for k, v in re.findall(r"\((\w+)\s+(\d+)\)", clock[1])}
    require(fields.get("TX") == 0 and fields.get("TZ", 0) == 0 and
            fields.get("T0", -1) + fields.get("T1", -1) == Decimal(duration[1]) and
            fields.get("TC") in (2*m["measured_cycles"]-1, 2*m["measured_cycles"]),
            "SAIF clock unknown/incomplete or includes warmup")
    return dict(status="F12_REPLAY_TOTALS_AND_SAIF_WINDOW_CHECKED", totals=totals,
                saif_sha256=legacy.sha(saif), clock_fields=fields,
                method_acceptance="NOT_GRANTED; annotation and FF clock semantics require review")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--policy", choices=POLICIES)
    p.add_argument("--seed", type=int, choices=SEEDS, default=509)
    p.add_argument("--arm", choices=MODES)
    p.add_argument("--window", type=int, choices=(256, PRODUCTION_W), default=PRODUCTION_W)
    p.add_argument("--smoke-cycles", type=int)
    p.add_argument("--out", type=Path)
    p.add_argument("--audit", type=Path, help="independently replay an existing export")
    p.add_argument("--gate-result", type=Path, help="check actual future gate totals with --audit")
    p.add_argument("--saif", type=Path, help="check actual measured-only SAIF with --gate-result")
    p.add_argument("--pt-reports", type=Path, help="audit actual PT reports with --saif")
    p.add_argument("--plan", action="store_true", help="print fixed phase contract without running")
    a = p.parse_args()
    if (a.saif and not a.gate_result) or (a.pt_reports and not a.saif):
        p.error("--saif requires --gate-result; --pt-reports requires --saif")
    if a.audit:
        result = audit_export(a.audit)
        if a.gate_result:
            m = json.loads((a.audit/"metadata.json").read_text())
            result["gate"] = (check_activity(m, a.gate_result, a.saif) if a.saif else
                              check_gate_result(m, a.gate_result))
        if a.pt_reports:
            result["pt"] = check_pt(a.pt_reports)
        result.update(exit=0, command=[sys.executable, *sys.argv])
    else:
        if not a.policy or not a.arm or (not a.plan and not a.out) or a.gate_result:
            p.error("--policy/--arm and --out (unless --plan) required; --gate-result needs --audit")
        result = (plan(a.policy, a.seed, a.arm, a.window, a.smoke_cycles) if a.plan else
                  export_case(a.policy, a.seed, a.arm, a.out, a.window, a.smoke_cycles))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
