"""Export model-checked gate pin replay; no simulator, RTL or profile changes."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "refc"), str(ROOT / "sim/common"), str(ROOT / "sim/switch_top_fai")]
from cxl_model.fcfs_model import FcfsSwitchModel
from cxl_model.rr_model import RrSwitchModel
from cxl_model.fai_main_model import FaiMainSwitchModel
from input_hold import InputHoldChecker
from traffic_trace import GENERATOR_VERSION, Producers, make_trace
from fai_stream import PRODUCTION_GENERATOR, ProductionTraffic, StreamProducers
from check_power_replay import FIXTURE_MODE_ID, SUPPLEMENTARY_MODES

POLICIES = {"fcfs": (0, FcfsSwitchModel), "rr": (1, RrSwitchModel),
            "fai-main": (2, FaiMainSwitchModel)}
CYCLES, SEED, PERIOD_PS, RESET_EDGES = 100_000, 509, 25_000, 3
PROFILE_SHA = "6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d"
V2_MAGIC, BOUNDARY_W = "43585032", 5_000_000
# Boundary pilot: pre-edge global indices of the first two production closings. The measured
# window (9,999,500..10,099,499) holds a fixed 499-cycle tail, the second closing and 99,500 cycles.
BOUNDARY_CLOSINGS = (BOUNDARY_W - 1, 2 * BOUNDARY_W - 1)
# Hand-derived from frozen Spec 8.2 and fai_stream.PRODUCTION_KINDS rows 0/1 (groups h%4 = 0..3)
# starting all-H: DOWN,DOWN,UP,DOWN -> B_H,B_H,H,B_H; then DOWN,UP,KEEP,DOWN -> L,H,H,L. Literal
# on purpose: never computed from the oracle being checked.
MAIN_BOUNDARY_CLASSES = (("B_H", "B_H", "H", "B_H"), ("L", "H", "H", "L"))
MAIN_BOUNDARY_EVIDENCE = (("DOWN", "DOWN", "UP", "DOWN"), ("DOWN", "UP", "KEEP", "DOWN"))
# Odd boundary 1 holds an offer across the closing edge; even boundary 2 ends with a ready fire.
BOUNDARY_CARRY = ("held", "fire")
TRIM_EVERY = 1 << 16  # append-only model visit/window/turn logs are never read back by the models


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def replay(trace, policy, stats):
    """Yield pre-edge pins, checking producer hold and independent queue conservation."""
    if policy not in POLICIES or trace.n_src not in (4, 8, 16):
        raise ValueError("only the primary nine configurations are supported")
    if trace.profile != "primary" or any(trace.reset):
        raise ValueError("power measurement requires the reset-free primary trace")
    n = trace.n_src
    model = POLICIES[policy][1](n)
    for _ in range(RESET_EDGES):
        model.commit(rst_n=False)
    producer, hold = Producers(n), InputHoldChecker(n)
    accepted, fired = [0] * n, [0] * n
    full_refused = stalls = 0
    for k in range(trace.cycles):
        producer.generate(k, trace.gen[k])
        offers = producer.offers()
        valid = sum(1 << h for h in offers)
        desc = [offers[h][1] if h in offers else 0 for h in range(n)]
        ready = int(trace.ready[k])
        view = model.view(out_ready=bool(ready))
        in_ready = sum(int(v) << h for h, v in enumerate(view.in_ready))
        hold.step(k, 1, valid, in_ready, desc)
        packed = sum(d << (105 * h) for h, d in enumerate(desc))
        yield (k, valid, packed, ready, in_ready, int(view.out_valid),
               view.out_source or 0, view.out_desc or 0)
        edge = model.commit(out_ready=bool(ready),
                            in_valid=[bool(valid & (1 << h)) for h in range(n)], in_desc=desc)
        for h in range(n):
            pushed = bool(valid & in_ready & (1 << h))
            assert (edge.pushed[h] is not None) == pushed
            if pushed:
                record = producer.accept(h, k)
                assert record.desc == desc[h]
                accepted[h] += 1
            full_refused += int(bool(valid & (1 << h)) and view.count[h] == 16)
        assert (edge.fired is not None) == view.fire
        if view.fire:
            fired[view.out_source] += 1
        stalls += int(view.out_valid and not ready)
        assert all(accepted[h] - fired[h] == model.occupancy(h) for h in range(n))
    stats.update(accepted_per_source=accepted, fires_per_source=fired,
                 accepted=sum(accepted), fires=sum(fired),
                 outstanding_at_cut=[model.occupancy(h) for h in range(n)],
                 generated_but_unaccepted=producer.backlog(),
                 input_hold_checks=hold.checked, full_refused_source_cycles=full_refused,
                 stalled_output_cycles=stalls, drain_cycles=0)
    assert producer.generated == sum(accepted) + producer.backlog()
    if policy == "fai-main":
        assert not model.window_log and set(model.classes()) == {"H"}
        stats["fai_state_scope"] = "untrained all-H; zero W=5000000 classification boundaries"


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _model_logs(model):
    return [getattr(model, name) for name in ("visit_log", "window_log", "turn_log") if hasattr(model, name)]


def _snapshot(model, producer, hold, n, fai):
    """Beginning-of-cycle state handed across a phase cut; nothing is reset or deposited there."""
    snap = {"occupancy": [model.occupancy(h) for h in range(n)], "held_source": model.held,
            "producer_backlog": producer.backlog(), "input_hold_obligation_sources": sorted(hold.obligations())}
    if fai:
        pos, b, s = model.window_state()
        held = model.held_grant()
        snap.update(window_position=pos, b=list(b), s=s, classes=list(model.classes()),
                    visit=list(model.visit_state()), held_grant_ctx=list(held[1]) if held else None)
    return snap


def _closing(k, phase, pre, offered, view, ready, edge, model, n):
    """Spec 8.4 closing-edge evidence: fire included, B/S/index cleared, classes visible next cycle."""
    pos, b, s = pre
    src = edge.fired[0] if edge.fired is not None else None
    _require(pos == model.window - 1 and edge.window_pos == pos, f"cycle {k}: closing at position {pos}")
    _require(list(edge.b_close) == [b[h] + int(h == src) for h in range(n)] and
             edge.s_close == s + int(src is not None) == sum(edge.b_close),
             f"cycle {k}: closing-edge fire not included exactly once in B_close/S_close")
    _require(model.window_state() == (0, (0,) * n, 0), f"cycle {k}: B/S/index not cleared after closing")
    _require(model.classes() == edge.new_classes, f"cycle {k}: new classes not exposed next cycle")
    # Python integers retain the full widened comparison, independent of model threshold helpers.
    evidence = tuple("S0" if edge.s_close == 0 else
                     "UP" if 10 * n * b < 3 * edge.s_close else
                     "DOWN" if n * b > edge.s_close else "KEEP" for b in edge.b_close)
    _require(evidence == edge.evidence, f"cycle {k}: closing evidence differs from exact integer inequalities")
    held_across = bool(view.out_valid and not ready)
    if held_across:
        _require(model.held_grant() == offered, f"cycle {k}: held grant context changed across the boundary")
    return {"cycle": k, "phase": phase, "window_position": pos, "pre_edge_b": list(b), "pre_edge_s": s,
            "closing_fire_source": src, "closing_fire_ctx": list(edge.charged) if edge.charged else None,
            "b_close": list(edge.b_close), "s_close": edge.s_close, "evidence": list(edge.evidence),
            "old_classes": list(edge.old_classes), "next_cycle_classes": list(edge.new_classes),
            "held_across_closing": held_across, "held_grant": [offered[0], list(offered[1])] if held_across else None,
            "b_s_index_cleared_after": True}


def replay_phases(policy, n, steps, total, warmup, stats, *, window=BOUNDARY_W, expect=None):
    """Yield pre-edge pins of every non-reset cycle; warmup and measured cycles get identical checks.

    ``steps`` yields (generation events, ready) per cycle. Counts are kept per phase; ``expect``
    (Main only) lists independently derived closing cycles/classes/evidence/carry to enforce.
    """
    if policy not in POLICIES or n not in (4, 8, 16):
        raise ValueError("only the primary nine configurations are supported")
    if not 0 <= warmup < total:
        raise ValueError("warmup must leave at least one measured cycle")
    fai = policy == "fai-main"
    model = FaiMainSwitchModel(n, window) if fai else POLICIES[policy][1](n)
    for _ in range(RESET_EDGES):
        model.commit(rst_n=False)
    producer, hold = StreamProducers(n), InputHoldChecker(n)
    phases = {name: dict(generated_per_source=[0] * n, accepted_per_source=[0] * n, fires_per_source=[0] * n,
                         ready_cycles=0, stalled_output_cycles=0, full_refused_source_cycles=0, cycles=0)
              for name in ("warmup", "measured")}
    if fai:
        for phase in phases.values():
            phase.update(high_class_fires=0, low_class_fires=0)
    accepted, fired, closings, max_log, k = [0] * n, [0] * n, [], 0, -1
    for k, (events, ready) in enumerate(steps):
        _require(k < total, "trace longer than the declared run")
        name = "measured" if k >= warmup else "warmup"
        if k == warmup:
            stats["state_at_cut"] = _snapshot(model, producer, hold, n, fai)
        phase = phases[name]
        phase["cycles"] += 1
        for h, _ in events:
            phase["generated_per_source"][h] += 1
        producer.generate(k, events)
        offers = producer.offers()
        valid = sum(1 << h for h in offers)
        desc = [offers[h][1] if h in offers else 0 for h in range(n)]
        ready = int(ready)
        _require(ready in (0, 1), f"cycle {k}: invalid ready")
        phase["ready_cycles"] += ready
        view = model.view(out_ready=bool(ready))
        in_ready = sum(int(v) << h for h, v in enumerate(view.in_ready))
        hold.step(k, 1, valid, in_ready, desc)
        pre, offered = (model.window_state(), model.offered()) if fai else (None, None)
        packed = sum(d << (105 * h) for h, d in enumerate(desc))
        yield (k, valid, packed, ready, in_ready, int(view.out_valid),
               view.out_source or 0, view.out_desc or 0)
        edge = model.commit(out_ready=bool(ready),
                            in_valid=[bool(valid & (1 << h)) for h in range(n)], in_desc=desc)
        for h in range(n):
            pushed = bool(valid & in_ready & (1 << h))
            _require((edge.pushed[h] is not None) == pushed, f"cycle {k}: source {h} push mismatch")
            if pushed:
                _require(producer.accept(h, k)[1] == desc[h], f"cycle {k}: source {h} full105 changed")
                accepted[h] += 1
                phase["accepted_per_source"][h] += 1
            phase["full_refused_source_cycles"] += int(bool(valid & (1 << h)) and view.count[h] == 16)
        _require((edge.fired is not None) == view.fire, f"cycle {k}: fire mismatch")
        if view.fire:
            fired[view.out_source] += 1
            phase["fires_per_source"][view.out_source] += 1
            if fai:
                _require(edge.charged.cls in ("High", "Low"), f"cycle {k}: unknown charged class")
                phase["high_class_fires" if edge.charged.cls == "High" else "low_class_fires"] += 1
        phase["stalled_output_cycles"] += int(view.out_valid and not ready)
        _require(all(accepted[h] - fired[h] == model.occupancy(h) for h in range(n)),
                 f"cycle {k}: accepted-request conservation broken")
        if fai and edge.closing:
            record = _closing(k, name, pre, offered, view, ready, edge, model, n)
            if expect is not None:
                i = len(closings)
                _require(i < len(expect), f"cycle {k}: unexpected extra closing")
                cycle, classes, evidence, carry = expect[i]
                _require((k, tuple(edge.new_classes), tuple(edge.evidence)) == (cycle, tuple(classes), tuple(evidence)),
                         f"closing {i}: got cycle {k} {edge.evidence} -> {edge.new_classes}, "
                         f"expected cycle {cycle} {evidence} -> {classes}")
                _require(record["held_across_closing"] if carry == "held" else edge.fired is not None,
                         f"closing {i}: expected boundary carry {carry!r}")
            closings.append(record)
        max_log = max(max_log, sum(len(log) for log in _model_logs(model)))
        if (k + 1) % TRIM_EVERY == 0:
            for log in _model_logs(model):
                log.clear()
    _require(k == total - 1, "trace shorter than the declared run")
    _require(expect is None or len(closings) == len(expect), f"{len(closings)} closings, expected {len(expect or ())}")
    _require(producer.generated == sum(accepted) + producer.backlog(), "generated-request conservation broken")
    stats.update(warmup=phases["warmup"], measured=phases["measured"],
                 all={"cycles": total, "generated": producer.generated, "accepted": sum(accepted), "fires": sum(fired)},
                 outstanding_at_cut=stats["state_at_cut"]["occupancy"],
                 outstanding_at_end=[model.occupancy(h) for h in range(n)],
                 state_at_end=_snapshot(model, producer, hold, n, fai),
                 generated=producer.generated, generated_but_unaccepted=producer.backlog(),
                 max_producer_backlog=producer.max_backlog, input_hold_checks=hold.checked,
                 drain_cycles=0, model_log_trim_every=TRIM_EVERY, max_retained_model_log_entries=max_log)
    if fai:
        stats["closings"] = closings


def boundary_expectation():
    """Independent Main N4 expectation for the two production closings (never the oracle)."""
    return list(zip(BOUNDARY_CLOSINGS, MAIN_BOUNDARY_CLASSES, MAIN_BOUNDARY_EVIDENCE, BOUNDARY_CARRY))


def _row_text(row):
    k, valid, packed, ready, in_ready, out_valid, source, out_desc = row
    return f"{k} {valid:x} {packed:x} {ready:x} {in_ready:x} {out_valid:x} {source:x} {out_desc:027x}"


def _write_vectors(destination, header, rows):
    """Stream a deterministic gzip (fixed mtime, empty filename); returns text SHA-256 and row count."""
    digest, count = hashlib.sha256(), 0
    with (destination / "vectors.txt.gz").open("xb") as raw, \
            gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
        data = (header + "\n").encode("ascii")
        digest.update(data)
        zipped.write(data)
        for row in rows:
            data = (_row_text(row) + "\n").encode("ascii")
            digest.update(data)
            zipped.write(data)
            count += 1
    return digest.hexdigest(), count


def _accepted_case(policy, n):
    accepted_case = ROOT / f"artifacts/fastx/primary-20261021-v2-{policy}-n{n}"
    accepted_manifest = json.loads((accepted_case / "manifest.json").read_text())
    if (accepted_manifest["source"]["head"] != "759f86b24f13ed5984c19034eeeea2ca43b0e971" or
            not accepted_manifest["source"]["worktree_clean"]):
        raise ValueError("accepted case must be the clean primary-v2 source revision")
    return accepted_manifest["source"]["head"], {
        p: sha(accepted_case / p) for p in
        ("run_config.tcl", "output/switch_top.syn.v", "output/switch_top.syn.sdc", "manifest.json")}


def _sources(*extra):
    sources = ["scripts/export_power_vectors.py", "scripts/check_power_replay.py", "scripts/run_power_pilot.sh",
               "sim/power/tb_power.sv", "sta/power_pt.tcl",
               "sim/common/traffic_trace.py", "sim/common/input_hold.py", *extra]
    sources += [str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted((ROOT / "refc/cxl_model").glob("*.py"))]
    return {p: sha(ROOT / p) for p in sources}


def _supplementary_rows(mode, policy, n, seed, total, warmup, window, stats, expect):
    """Return (row iterator, trace-info callable) for one supplementary or fixture run."""
    if mode == "cold-seed":
        trace = make_trace(seed, n, total, "primary")
        if any(trace.reset):
            raise ValueError("power measurement requires the reset-free primary trace")
        steps = ((trace.gen[k], trace.ready[k]) for k in range(total))
        return (replay_phases(policy, n, steps, total, warmup, stats, window=window, expect=expect),
                lambda: {"generator": GENERATOR_VERSION, "summary": trace.summary(), "sha256": trace.sha256})
    traffic = ProductionTraffic(seed, n, total, window)
    steps = (traffic.step(k) for k in range(total))
    return (replay_phases(policy, n, steps, total, warmup, stats, window=window, expect=expect),
            lambda: {"generator": PRODUCTION_GENERATOR, "config": traffic.config(), "sha256": traffic.sha256,
                     "generated": traffic.generated, "generated_per_source": traffic.generated_per_source,
                     "generated_per_window": traffic.generated_per_window, "ready_cycles": traffic.ready_cycles,
                     "random_stalls": traffic.random_stalls})


def _v2_metadata(schema, mode, mode_id, policy, n, seed, total, warmup, window, trace, digest, rows, vector, stats):
    measured = total - warmup
    return {"schema": schema, "mode": mode, "mode_id": mode_id, "policy": policy,
            "policy_id": POLICIES[policy][0], "n_src": n, "depth": 16, "descriptor_bits": 105,
            "rr_quantum": 10, "fai_window": window, "seed": seed, "total_cycles": total,
            "warmup_cycles": warmup, "measured_cycles": measured, "period_ps": PERIOD_PS,
            "duration_ns": measured * PERIOD_PS // 1000, "reset_edges_outside_window": RESET_EDGES,
            "saif_window": "measured cycles only; warmup cycles are replayed and checked but not annotated",
            "trace": trace, "vectors_text_sha256": digest, "vectors_rows": rows,
            "vectors_gzip_sha256": sha(vector), "vectors_gzip_bytes": vector.stat().st_size,
            "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "python": sys.version, "platform": platform.platform(), **stats}


def export_supplementary(mode, policy, n, seed, destination):
    """Export one fixed supplementary mode; the accepted primary seed-509 dataset is never replaced."""
    spec = SUPPLEMENTARY_MODES.get(mode)
    if spec is None or policy not in POLICIES or n not in spec["n_src"] or seed not in spec["seeds"]:
        raise ValueError(f"unsupported supplementary configuration {mode}/{policy}/N{n}/seed{seed}")
    warmup, total = spec["warmup"], spec["warmup"] + spec["measured"]
    accepted_revision, accepted_hashes = _accepted_case(policy, n)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    stats = {}
    expect = boundary_expectation() if mode == "boundary-n4" and policy == "fai-main" else None
    rows, trace = _supplementary_rows(mode, policy, n, seed, total, warmup, BOUNDARY_W, stats, expect)
    header = f"{V2_MAGIC} {spec['mode_id']} {n} {total} {warmup} {spec['measured']} {seed} " \
             f"{POLICIES[policy][0]} {PERIOD_PS} {RESET_EDGES}"
    digest, count = _write_vectors(destination, header, rows)
    vector = destination / "vectors.txt.gz"
    metadata = _v2_metadata("cxl-power-replay-v2", mode, spec["mode_id"], policy, n, seed, total, warmup,
                            BOUNDARY_W, trace(), digest, count, vector, stats)
    metadata.update(status="MODEL_CHECKED_GATE_NOT_RUN", supplementary=True, replaces_primary_dataset=False,
                    profile_canonical_sha256=PROFILE_SHA, accepted_source_revision=accepted_revision,
                    accepted_case_sha256=accepted_hashes, source_sha256=_sources("sim/switch_top_fai/fai_stream.py"))
    if policy == "fai-main" and mode == "cold-seed":
        _require(not stats["closings"] and stats["state_at_end"]["classes"] == ["H"] * n, "cold Main left all-H")
        metadata["fai_state_scope"] = "untrained all-H; zero W=5000000 classification boundaries"
    elif policy == "fai-main":
        metadata["fai_state_scope"] = ("two production closings: first in warmup, second inside the measured "
                                       "SAIF window; expectation hand-derived from Spec 8.2/PRODUCTION_KINDS")
        metadata["boundary_expectation"] = [dict(cycle=e[0], next_cycle_classes=list(e[1]),
                                                evidence=list(e[2]), carry=e[3]) for e in expect]
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def write_fixture(policy, n, destination, *, warmup, measured, window=256, seed=SEED, expect=None):
    """Small-window replay FIXTURE for local parser/phase tests only; never exported as evidence."""
    if policy not in POLICIES or n not in (4, 8, 16) or window != 256 or warmup < 0 or not 0 < measured <= 100_000 or warmup > 100_000:
        raise ValueError("fixtures use a stress window and at most 100,000 cycles per phase")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    stats, total = {}, warmup + measured
    rows, trace = _supplementary_rows("fixture", policy, n, seed, total, warmup, window, stats, expect)
    header = f"{V2_MAGIC} {FIXTURE_MODE_ID} {n} {total} {warmup} {measured} {seed} {POLICIES[policy][0]} " \
             f"{PERIOD_PS} {RESET_EDGES}"
    digest, count = _write_vectors(destination, header, rows)
    metadata = _v2_metadata("cxl-power-replay-v2-fixture", "fixture", FIXTURE_MODE_ID, policy, n, seed, total,
                            warmup, window, trace(), digest, count, destination / "vectors.txt.gz", stats)
    metadata.update(status="FIXTURE_ONLY_NOT_PRODUCTION_EVIDENCE", production_evidence=False)
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def export(policy, n, destination):
    if policy not in POLICIES or n not in (4, 8, 16):
        raise ValueError("only the primary nine configurations are supported")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    trace = make_trace(SEED, n, CYCLES, "primary")
    stats = {}
    # Gzip mtime and filename are fixed so compressed bytes are reproducible too.
    vector = destination / "vectors.txt.gz"
    digest = hashlib.sha256()
    with vector.open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
        def line(text):
            data = (text + "\n").encode("ascii")
            digest.update(data)
            zipped.write(data)
        line(f"43585031 {n} {CYCLES} {SEED} {POLICIES[policy][0]} {PERIOD_PS} {RESET_EDGES}")
        for row in replay(trace, policy, stats):
            k, valid, packed, ready, in_ready, out_valid, source, out_desc = row
            line(f"{k} {valid:x} {packed:x} {ready:x} {in_ready:x} {out_valid:x} {source:x} {out_desc:027x}")
    sources = ["scripts/export_power_vectors.py", "scripts/check_power_replay.py", "scripts/run_power_pilot.sh",
               "sim/power/tb_power.sv", "sta/power_pt.tcl",
               "sim/common/traffic_trace.py", "sim/common/input_hold.py"]
    sources += [str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted((ROOT / "refc/cxl_model").glob("*.py"))]
    metadata = {"schema": "cxl-power-replay-v1", "status": "MODEL_CHECKED_GATE_NOT_RUN",
                "policy": policy, "policy_id": POLICIES[policy][0], "n_src": n,
                "depth": 16, "descriptor_bits": 105, "rr_quantum": 10, "fai_window": 5_000_000,
                "measured_cycles": CYCLES, "period_ps": PERIOD_PS,
                "duration_ns": CYCLES * PERIOD_PS // 1000, "reset_edges_outside_window": RESET_EDGES,
                "generator": GENERATOR_VERSION, "seed": SEED, "trace": trace.summary(),
                "trace_sha256": trace.sha256, "vectors_text_sha256": digest.hexdigest(),
                "vectors_gzip_sha256": sha(vector), "profile_canonical_sha256": PROFILE_SHA,
                "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "python": sys.version, "platform": platform.platform(),
                "source_sha256": {p: sha(ROOT / p) for p in sources}, **stats}
    accepted_case = ROOT / f"artifacts/fastx/primary-20261021-v2-{policy}-n{n}"
    accepted_manifest = json.loads((accepted_case / "manifest.json").read_text())
    if (accepted_manifest["source"]["head"] != "759f86b24f13ed5984c19034eeeea2ca43b0e971" or
            not accepted_manifest["source"]["worktree_clean"]):
        raise ValueError("accepted case must be the clean primary-v2 source revision")
    metadata["accepted_source_revision"] = accepted_manifest["source"]["head"]
    metadata["accepted_case_sha256"] = {
        p: sha(accepted_case / p) for p in
        ("run_config.tcl", "output/switch_top.syn.v", "output/switch_top.syn.sdc", "manifest.json")}
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, choices=POLICIES)
    parser.add_argument("--n", type=int, required=True, choices=(4, 8, 16))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("primary", *SUPPLEMENTARY_MODES), default="primary")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.mode == "primary":
        if args.seed != SEED:
            parser.error("primary v1 seed is fixed at 509; use --mode cold-seed for 510/511")
        result = export(args.policy, args.n, args.out)
    else:
        result = export_supplementary(args.mode, args.policy, args.n, args.seed, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
