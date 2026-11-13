"""Freeze the owner's trained cohort and export CGOF reference pins, never EDA results."""
from __future__ import annotations

import argparse
from collections import deque
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / path) for path in ("scripts", "refc", "sim/experimental")]
import audit_fastx_power as inventory
import export_revision_power_vectors as trained
from check_power_replay import check_mode
from cxl_model.experimental import ExperimentalSwitchModel

SEEDS = (509, 510, 511)
SCHEMA = "cxl-cgof-trained-power-v1"
RECORDED_ROOT = PureWindowsPath("C:/Users/USER/Documents/Coding Space/CXL/cxl-scheduler")
TRAFFIC_SOURCES = ("sim/experimental/revision_traffic.py", "sim/performance/hog_sparse.py",
                   "sim/performance/followup.py", "sim/switch_top_fai/fai_stream.py",
                   "scripts/revision_statistics.py")
MAPPED_FILES = ("manifest.json", "profile.json", "parameters.json", "run_config.tcl",
                "output/cgof_unit_top.syn.v", "output/cgof_unit_top.syn.sdc",
                "download-manifest.json")
MAPPING_PINS = {
    1: ("35f30ca8837ea50c47decc02aca046b264baf6c124eed9f07b7891cf24c4035a",
        "bd77ddccaf1cbc40a80ee8fe3c260c942ede05b84802d09f9448db290c90d4b4"),
    2: ("2e589206b19524938ce4345d8773141c692318a5884cf54092abc8c8047daa76",
        "f7de441d8e9f0611114d70275b7434015ff6b698b2c966041987ce8d357577e5"),
}
DB_SHA = "844d4474c02f771189fef1f57130f1fa9115760b1bb5cd235feedce86f434094"
TRACE_PINS = {
    "509-A": "c49208b8ef08899cbf6557c14ab53c57d4429abf7651456abe07aa5d6851d8f9",
    "509-B": "275ab202d7bd58118b4f6b718f56938a98760b54f697f3c7a6c2ad04b4286747",
    "510-A": "eb70aa077db99ab8435070e812755d50a05cdfc25c19134709408d976281e8dd",
    "510-B": "e15c20d13825726b1e8a805036a3a00d3a8a9830d3b1a2ea9bbd6c844fa94889",
    "511-A": "c29156a2a48e09faf7660c64b2fd2c119af5cfdea96e367f3c068aad206df9d0",
    "511-B": "4fa76013c4c563b02960c36f350d9e69a687dea88b56dfbb7d267041b58ce34d",
}
require = trained.require
sha = inventory.sha256_file
read_json = inventory.read_json


def output_dir(out, evidence_root=None):
    out = Path(out).absolute()
    inventory.no_links(out)
    allowed = (ROOT / "artifacts").resolve()
    require(out.resolve() != allowed and out.resolve().is_relative_to(allowed),
            "output must be a fresh worktree artifacts child")
    if evidence_root is not None:
        require(not out.resolve().is_relative_to((evidence_root / "artifacts").resolve()),
                "output must be outside original evidence artifacts")
    out.mkdir(parents=True, exist_ok=False)
    return out


def historical_path(root, recorded):
    rel = PureWindowsPath(recorded).relative_to(RECORDED_ROOT).as_posix()
    return inventory.repo_file(root, rel)


def bound_json(root, receipt):
    path = historical_path(root, receipt["path"])
    require(sha(path) == receipt["sha256"], f"receipt hash mismatch: {path}")
    return read_json(path)


def metadata_binding(root, semantic, metadata_sha, identity, depth=0, recovery=None):
    require(depth < 5, "semantic receipt chain exceeds supported depth")
    if "case" in semantic:
        require(semantic["case"] == identity, "semantic case identity mismatch")
    if "case_id" in semantic:
        require(semantic["case_id"] ==
                f"{identity['policy']}-{identity['arm']}-s{identity['seed']}",
                "semantic case_id mismatch")
    if "local_files" in semantic:
        require(semantic["local_files"]["metadata.json"] == metadata_sha, "metadata binding mismatch")
        return
    if "bindings" in semantic:
        require(semantic.get("decision") == "ADOPT_PRE_LAYOUT_TT25NS_MATCHED_POWER"
                and semantic.get("problems") == [], "unaccepted historical semantics")
        require(semantic["bindings"]["metadata"] == metadata_sha, "metadata binding mismatch")
        return
    if semantic.get("status") == "PARENT_ACCEPTED_DETACHED_TRAINED_POWER_CASE":
        require(semantic["actual_EDA_exit"] == 0, "detached EDA exit differs")
        nested = bound_json(root, dict(path=semantic["semantic_receipt"],
                                       sha256=semantic["semantic_sha256"]))
        require(nested["status"] == "REVIEWED_DETACHED_CASE_PARENT_ADOPTION_REQUIRED"
                and nested["case_id"] == semantic["case_id"]
                and nested["blocking_issues"] == []
                and nested["source_before_after_identical"] is True, "detached review differs")
        pins = nested["detached_transport"]["raw_sha256"]
        prepared_paths = [name for name in pins if PureWindowsPath(name).name == "prepared.json"]
        require(len(prepared_paths) == 1, "detached preparation binding is ambiguous")
        name = prepared_paths[0]
        prepared = bound_json(root, dict(path=name, sha256=pins[name]))
        require(prepared["case_id"] == semantic["case_id"]
                and prepared["local_export"]["native_exit"] == 0
                and prepared["local_export"]["files"]["metadata.json"] == metadata_sha
                and prepared["member_sha256"]["metadata.json"] == metadata_sha,
                "detached metadata binding mismatch")
        return
    if semantic.get("status") in {"ADOPTED_QUALIFIED_TABLE_RANGE_PRELAYOUT_CASE",
                                   "ADOPTED_SINGLE_TRAINED_PRELAYOUT_CASE"}:
        require(recovery is not None and semantic.get("blocking_issues") == []
                and semantic.get("source_before_after_identical") is True,
                "incomplete recovered semantic receipt")
        recovery_plan = bound_json(root, recovery["plan"])
        recovery_result = bound_json(root, recovery["result"])
        require(recovery_plan["expected_members"]["metadata.json"] == metadata_sha,
                "recovered metadata binding mismatch")
        require(semantic["recovery_result_sha256"] == recovery["result"]["sha256"]
                and recovery_result["actual_EDA_exit"] == 0
                and recovery_result["payload_and_source_match"] is True,
                "recovered result binding mismatch")
        return
    require(semantic.get("actual_EDA_exit") == 0 and "semantic_receipt" in semantic,
            "missing historical semantic binding")
    nested = bound_json(root, dict(path=semantic["semantic_receipt"],
                                   sha256=semantic["semantic_sha256"]))
    metadata_binding(root, nested, metadata_sha, identity, depth + 1, recovery)


def traffic_binding(current, archived, expected_sha):
    require(hashlib.sha256(archived).hexdigest() == expected_sha,
            "historical traffic bytes differ from pinned archive")
    normalized = lambda data: data.replace(bytes((13, 10)), bytes((10,)))
    require(normalized(current) == normalized(archived), "traffic source content drift")
    return dict(historical_sha256=expected_sha, current_sha256=hashlib.sha256(current).hexdigest(),
                lf_sha256=hashlib.sha256(normalized(current)).hexdigest(),
                comparison="EXACT_BYTES" if current == archived else "CRLF_LF_ONLY")


def freeze(root):
    baseline = inventory.baseline_inventory(root)
    require(baseline["status"] == "PINNED_ACCEPTANCE_INDEX_OBSERVED", str(baseline))
    cases, traces, traffic_bindings = [], {}, []
    for case in read_json(root / inventory.BASELINE)["cases"]:
        identity = {key: case[key] for key in ("policy", "seed", "arm")}
        native = bound_json(root, case["native_exit"])
        require(type(native[case["native_exit_field"]]) is int
                and native[case["native_exit_field"]] == 0, "historical native exit is nonzero")
        semantic = bound_json(root, case["semantic_receipt"])
        directory = historical_path(root, case["export_dir"])
        path = directory / "metadata.json"
        inventory.no_links(path)
        metadata_sha, metadata = sha(path), read_json(path)
        check_mode(metadata)
        require(all(metadata[key] == value for key, value in identity.items()), "baseline identity mismatch")
        require(metadata["profile_canonical_sha256"] == trained.legacy.PROFILE_SHA, "baseline profile differs")
        metadata_binding(root, semantic, metadata_sha, identity, recovery=case.get("recovery"))
        for key, filename in (("audit_sha256", "audit.json"),
                              ("source_archive_sha256", "source-freeze.zip")):
            inventory.no_links(directory / filename)
            require(sha(directory / filename) == metadata[key], f"baseline {filename} changed")
        with zipfile.ZipFile(directory / "source-freeze.zip") as archive:
            for name, digest in metadata["source_sha256"].items():
                require(hashlib.sha256(archive.read(name)).hexdigest() == digest,
                        f"historical archived source differs: {name}")
            comparisons = {name: traffic_binding((ROOT / name).read_bytes(), archive.read(name),
                                                 metadata["source_sha256"][name])
                           for name in TRAFFIC_SOURCES}
        traffic_bindings.append(dict(**identity, sources=comparisons))
        key = f"{case['seed']}-{case['arm']}"
        trace = dict(sha256=metadata["trace"]["sha256"], config=metadata["trace"]["config"])
        require(trace["sha256"] == TRACE_PINS[key], "baseline trace pin differs")
        require(traces.setdefault(key, trace) == trace, "baseline exogenous trace mismatch")
        cases.append(dict(**identity, metadata_sha256=metadata_sha,
                          metadata_path=path.relative_to(root).as_posix(),
                          semantic_receipt=case["semantic_receipt"], native_exit=case["native_exit"],
                          historical_vectors_sha256=metadata["vectors_gzip_sha256"],
                          vector_bytes_rehashed=False,
                          accepted_source_revision=metadata["accepted_source_revision"]))
    mappings = {}
    for weight in (1, 2):
        bundle = inventory.CGOF_BUNDLES[f"cgof{weight}-n4"]
        observed = inventory.inspect_mapping(root, bundle)
        require(observed["status"] == "HASH_BOUND_INPUTS_OBSERVED", str(observed))
        require(observed["profile_canonical_sha256"] == trained.legacy.PROFILE_SHA
                and observed["library_sha256"] == DB_SHA, "CGOF profile/library differs")
        directory = root / "artifacts/fastx" / bundle
        manifest = read_json(directory / "manifest.json")
        profile = read_json(directory / "profile.json")
        canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        require(hashlib.sha256(canonical).hexdigest() == trained.legacy.PROFILE_SHA,
                "CGOF canonical profile content differs")
        params = manifest["parameters"]
        require((params["N_SRC"], params["DEPTH"], params["FAI_W"], params["HIGH_WEIGHT"]) ==
                (4, 16, 5_000_000, weight), "CGOF mapped parameters differ")
        parameters = read_json(directory / "parameters.json")
        require(all(parameters[key] == value for key, value in
                    dict(top_module="cgof_unit_top", policy_name="CGOF", N_SRC=4, DEPTH=16,
                         FAI_W=5_000_000, HIGH_WEIGHT=weight, DESC_W=105, M=1,
                         elab_parameters=f"N_SRC=4,DEPTH=16,FAI_W=5000000,HIGH_WEIGHT={weight}").items()),
                "CGOF parameter receipt differs")
        for name in inventory.CGOF_SOURCES:
            require(sha(ROOT / name) == manifest["file_sha256"][name], f"worktree CGOF drift: {name}")
        files = {name: sha(directory / name) for name in MAPPED_FILES}
        require(tuple(files[name] for name in MAPPED_FILES[4:6]) == MAPPING_PINS[weight],
                "CGOF netlist/SDC pin mismatch")
        mappings[str(weight)] = dict(bundle=bundle, files=files, source=manifest["source"],
                                     parameters=params)
    return dict(schema="cxl-cgof-power-cohort-freeze-v1", decision_date="2026-11-07",
                seeds=list(SEEDS), arms=["A", "B"], baseline_index_sha256=inventory.BASELINE_SHA,
                cases=cases, traces=traces, mappings=mappings,
                historical_traffic_bindings=traffic_bindings,
                traffic_sources={name: sha(ROOT / name) for name in TRAFFIC_SOURCES},
                status="COHORT_INPUT_BINDINGS_CHECKED_NOT_POWER_ACCEPTANCE",
                raw_baseline_vectors="Historical receipt pins retained; vector bytes not rehashed",
                power_status="NOT_RUN", long_backlog_drain="UNVERIFIED")


def plan(weight, seed, arm, window=5_000_000, smoke_cycles=None):
    require(type(weight) is int and weight in (1, 2) and type(seed) is int and seed in SEEDS,
            "unsupported CGOF weight/seed")
    base = trained.plan("fcfs", seed, arm, window, smoke_cycles)
    base.pop("rr_quantum")
    base.update(schema=SCHEMA, policy=f"cgof{weight}", policy_id=weight + 2,
                top_module="cgof_unit_top", high_weight=weight, ordering="oldest-first",
                eligible_rr=0, mode_id=base["mode_id"] if window == 5_000_000 else 9)
    return base


def check_contract(metadata):
    expected = plan(metadata["high_weight"], metadata["seed"], metadata["arm"], metadata["fai_window"], metadata["smoke_cycles"])
    require(all(type(metadata.get(key)) is type(value) and metadata.get(key) == value
                for key, value in expected.items()), "metadata differs from frozen CGOF contract")


def sources():
    names = (*TRAFFIC_SOURCES, *inventory.CGOF_SOURCES,
             "scripts/export_cgof_power_vectors.py", "scripts/audit_fastx_power.py",
             "scripts/index_revision_evidence.py", "scripts/export_revision_power_vectors.py",
             "scripts/revision_matrix.py",
             "scripts/export_power_vectors.py", "scripts/check_power_replay.py",
             "sim/common/traffic_trace.py", "sim/common/input_hold.py",
             "sim/power/tb_power.sv", "sta/power_pt.tcl",
             "scripts/check_cgof_power_replay.py", "scripts/run_cgof_power_pilot.sh",
             "scripts/test_cgof_power_vectors.py", "scripts/test_cgof_power_tcl.py",
             "scripts/test_cgof_power_checker.py", "scripts/test_cgof_power_tb.py")
    names += tuple(path.relative_to(ROOT).as_posix() for path in sorted((ROOT / "refc/cxl_model").glob("*.py")))
    return {name: sha(ROOT / name) for name in sorted(set(names))}


def snapshot(model):
    position, counts, total = model.window_state()
    return dict(classes=list(model.classes()), credits=list(model.credits),
                window_position=position, b=list(counts), s=total,
                occupancy=[model.occupancy(source_index) for source_index in range(4)], held=bool(model.ctrl.held))


def replay(metadata, stats, rows=None):
    check_contract(metadata)
    traffic, producer = trained.traffic_for(metadata), trained.legacy.StreamProducers(4)
    hold = trained.legacy.InputHoldChecker(4)
    model = ExperimentalSwitchModel(4, f"CGOF({metadata['high_weight']}:1)", metadata["fai_window"], 16)
    for _ in range(3):
        model.commit(rst_n=False)
    fifo, credits, classes, counts = [deque() for _ in range(4)], [0]*4, ["H"]*4, [0]*4
    phases = {name: dict(cycles=0, accepted_per_source=[0]*4, fires_per_source=[0]*4)
              for name in ("warmup", "measured")}
    closings, total, cut, refills = [], 0, None, dict(warmup=0, measured=0)
    supplied = iter(rows) if rows is not None else None
    for cycle in range(metadata["total_cycles"]):
        if cycle == metadata["warmup_cycles"]:
            cut = snapshot(model)
        producer.generate(cycle, traffic.step(cycle)[0])
        offers = producer.offers()
        inputs = [offers[source_index][1] if source_index in offers else 0 for source_index in range(4)]
        valid = sum(1 << source_index for source_index in offers)
        active = [source_index for source_index in range(4) if fifo[source_index]]
        eligible = [source_index for source_index in active if credits[source_index] > 0]
        next_credits = credits[:]
        if active and not eligible:
            refills["warmup" if cycle < metadata["warmup_cycles"] else "measured"] += 1
            next_credits = [metadata["high_weight"] if cls in ("H", "B_H") else 1 for cls in classes]
            eligible = active
        selected = min(eligible, key=lambda source_index: (fifo[source_index][0][0], source_index)) if eligible else 0
        ready = sum(int(len(queue) < 16) << source_index for source_index, queue in enumerate(fifo))
        desc = fifo[selected][0][1] if active else 0
        row = (cycle, valid, sum(value << (105*source_index) for source_index, value in enumerate(inputs)),
               1, ready, int(bool(active)), selected, desc)
        view = model.view(out_ready=True)
        require((ready, row[5]) == (sum(int(value) << source_index for source_index, value in enumerate(view.in_ready)),
                                  int(view.out_valid)), f"cycle {cycle}: ledger ready/valid differs")
        if active:
            require((selected, desc) == (view.out_source, view.out_desc),
                    f"cycle {cycle}: independent credit/oldest/full105 ledger differs")
        if supplied is not None:
            require(next(supplied, None) == row, f"cycle {cycle}: serialized pin mismatch")
        hold.step(cycle, 1, valid, ready, inputs)
        phase = phases["warmup" if cycle < metadata["warmup_cycles"] else "measured"]
        phase["cycles"] += 1
        closing_edge = (cycle + 1) % metadata["fai_window"] == 0
        pre_counts, pre_total = (counts[:], total) if closing_edge else (None, None)
        if active:
            fifo[selected].popleft()
            credits = next_credits
            credits[selected] -= 1
            counts[selected] += 1
            total += 1
            phase["fires_per_source"][selected] += 1
        for source in offers:
            if ready & (1 << source):
                producer.accept(source, cycle)
                fifo[source].append((cycle, inputs[source]))
                phase["accepted_per_source"][source] += 1
        edge = model.commit(True, [bool(valid & (1 << source_index)) for source_index in range(4)], inputs)
        if closing_edge:
            evidence = ["S0" if total == 0 else "UP" if 40*value < 3*total else
                        "DOWN" if 4*value > total else "KEEP" for value in counts]
            old = classes[:]
            transitions = {"H": ("H", "B_H", "H"), "B_H": ("H", "L", "H"),
                           "L": ("B_L", "L", "L"), "B_L": ("H", "L", "L")}
            classes = [transitions[cls][0 if ev == "UP" else 1 if ev == "DOWN" else 2]
                       for cls, ev in zip(classes, evidence)]
            closing = dict(cycle=cycle, b_close=counts[:], s_close=total, evidence=evidence,
                           old_classes=old, next_cycle_classes=classes[:],
                           pre_edge_b=pre_counts, pre_edge_s=pre_total,
                           closing_fire_source=selected if active else None,
                           phase="warmup" if cycle < metadata["warmup_cycles"] else "measured",
                           window_position=metadata["fai_window"] - 1,
                           b_s_index_cleared_after=True)
            require(edge.closing is not None and list(edge.closing["counts"]) == counts
                    and edge.closing["total"] == total, "closing fire inclusion differs")
            closings.append(closing)
            counts, total = [0]*4, 0
        require(model.credits == credits and list(model.classes()) == classes
                and model.window_state() == ((cycle + 1) % metadata["fai_window"], tuple(counts), total)
                and [model.occupancy(source_index) for source_index in range(4)] == [len(queue) for queue in fifo],
                f"cycle {cycle}: independent CGOF state differs")
        yield row
    require(supplied is None or next(supplied, None) is None, "extra serialized vector rows")
    if metadata["production_evidence"]:
        require([closing["next_cycle_classes"] for closing in closings] ==
                [["B_H", "H", "H", "H"], ["L", "H", "H", "H"]],
                "unexpected actual training trajectory")
    end = snapshot(model)
    accepted = sum(sum(path["accepted_per_source"]) for path in phases.values())
    fired = sum(sum(path["fires_per_source"]) for path in phases.values())
    require(producer.generated == accepted + producer.backlog() and
            accepted - fired == sum(end["occupancy"]), "request conservation differs")
    for source in range(4):
        require(sum(phase["accepted_per_source"][source] - phase["fires_per_source"][source]
                    for phase in phases.values()) == end["occupancy"][source],
                "per-source conservation differs")
    stats.update(**phases, state_at_cut=cut, state_at_end=end, closings=closings,
                         outstanding_at_cut=cut["occupancy"], outstanding_at_end=end["occupancy"],
                         all=dict(cycles=metadata["total_cycles"], generated=producer.generated,
                                  accepted=accepted, fires=fired),
                         generated_but_unaccepted=producer.backlog(), input_hold_checks=hold.checked,
                         drain_cycles=0, credit_refills=refills,
                         trace=dict(sha256=traffic.sha256, config=traffic.config))


def audit_export(directory):
    directory = Path(directory)
    inventory.no_links(directory)
    for filename in ("metadata.json", "vectors.txt.gz", "source-freeze.zip"):
        inventory.no_links(directory / filename)
    metadata = read_json(directory / "metadata.json")
    check_contract(metadata)
    require(metadata["vectors_rows"] == metadata["total_cycles"], "vector row count differs")
    require(metadata["profile_canonical_sha256"] == trained.legacy.PROFILE_SHA
            and metadata["library_sha256"] == DB_SHA
            and metadata["baseline_index_sha256"] == inventory.BASELINE_SHA, "profile/library/index differs")
    mapped_files = metadata["mapping"]["files"]
    require(set(mapped_files) == set(MAPPED_FILES) and
            tuple(mapped_files[name] for name in MAPPED_FILES[4:6]) == MAPPING_PINS[metadata["high_weight"]],
            "mapped CGOF input pins differ")
    expected_archive = dict(metadata["source_sha256"])
    expected_archive.update({f"mapped/{name}": digest for name, digest in mapped_files.items()})
    expected_archive["baseline-acceptance.json"] = inventory.BASELINE_SHA
    require(metadata["archive_files"] == expected_archive, "archive/source bindings differ")
    require(sources() == metadata["source_sha256"], "export source drift")
    require(sha(directory / "vectors.txt.gz") == metadata["vectors_gzip_sha256"], "gzip hash mismatch")
    require(sha(directory / "source-freeze.zip") == metadata["source_archive_sha256"], "archive hash mismatch")
    with zipfile.ZipFile(directory / "source-freeze.zip") as archive:
        require(len(archive.namelist()) == len(expected_archive)
                and set(archive.namelist()) == set(expected_archive), "archive entries differ")
        for name, digest in metadata["archive_files"].items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == digest, f"archive entry differs: {name}")
    digest = hashlib.sha256()
    with gzip.open(directory / "vectors.txt.gz", "rb") as stream:
        header = stream.readline()
        require(header == (trained.header(metadata) + "\n").encode("ascii"), "header differs")
        digest.update(header)

        def rows():
            for line in stream:
                digest.update(line)
                fields = line.decode("ascii").split()
                require(len(fields) == 8, "invalid vector row shape")
                yield tuple(int(value, 10 if index == 0 else 16) for index, value in enumerate(fields))
        stats = {}
        for _ in replay(metadata, stats, rows()):
            pass
    require(digest.hexdigest() == metadata["vectors_text_sha256"], "vector text hash differs")
    require(all(metadata.get(key) == value for key, value in stats.items()), "replay statistics differ")
    if metadata["production_evidence"]:
        require(metadata["trace"]["sha256"] == TRACE_PINS[f"{metadata['seed']}-{metadata['arm']}"],
                "matched production trace pin differs")
    require(sources() == metadata["source_sha256"], "source changed during serialized audit")
    return dict(status="MODEL_AND_INDEPENDENT_CREDIT_LEDGER_CHECKED_NOT_RTL_OR_POWER",
                rows=metadata["total_cycles"], power_status="NOT_RUN")


def export_case(root, weight, seed, arm, out, window=5_000_000, smoke_cycles=None):
    metadata = plan(weight, seed, arm, window, smoke_cycles)
    frozen = freeze(root)
    before = sources()
    directory = output_dir(out, root)
    try:
        bundle = frozen["mappings"][str(weight)]
        entries = {name: (ROOT / name, digest) for name, digest in before.items()}
        entries.update({f"mapped/{name}": (root / "artifacts/fastx" / bundle["bundle"] / name, digest)
                        for name, digest in bundle["files"].items()})
        entries["baseline-acceptance.json"] = (root / inventory.BASELINE, inventory.BASELINE_SHA)
        with zipfile.ZipFile(directory / "source-freeze.zip", "x") as archive:
            for name, (path, digest) in sorted(entries.items()):
                data = path.read_bytes()
                require(hashlib.sha256(data).hexdigest() == digest, f"source changed before archive: {name}")
                entry = zipfile.ZipInfo(name)
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, data)
        stats = {}
        digest, count = trained.legacy._write_vectors(directory, trained.header(metadata), replay(metadata, stats))
        metadata.update(stats)
        if metadata["production_evidence"]:
            require(metadata["trace"] == frozen["traces"][f"{seed}-{arm}"], "matched baseline trace differs")
        metadata.update(source_sha256=before, archive_files={name: item[1] for name, item in entries.items()},
                 vectors_text_sha256=digest, vectors_rows=count,
                 vectors_gzip_sha256=sha(directory / "vectors.txt.gz"),
                 source_archive_sha256=sha(directory / "source-freeze.zip"),
                 profile_canonical_sha256=trained.legacy.PROFILE_SHA, mapping=bundle,
                 library_sha256=DB_SHA,
                 baseline_index_sha256=inventory.BASELINE_SHA,
                 source_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                 command=[sys.executable, *sys.argv], observed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                 status="EXPORTED_SERIALIZED_AUDIT_PENDING_GATE_NOT_RUN",
                 gate_replay_status="NOT_RUN", power_status="NOT_RUN")
        write_json(directory / "metadata.json", metadata)
        report = audit_export(directory)
        write_json(directory / "audit.json", report)
        metadata.update(status="MODEL_AND_SERIALIZED_PINS_CHECKED_GATE_NOT_RUN",
                 audit_sha256=sha(directory / "audit.json"), exit=0)
        write_json(directory / "metadata.json", metadata)
        return metadata
    except Exception as exc:
        write_json(directory / "failure.json", dict(status="INCOMPLETE", exit=1, error=str(exc),
                                                      command=[sys.executable, *sys.argv]))
        raise


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--weight", type=int, choices=(1, 2))
    parser.add_argument("--seed", type=int, choices=SEEDS, default=509)
    parser.add_argument("--arm", choices=("A", "B"))
    parser.add_argument("--window", type=int, choices=(256, 5_000_000), default=5_000_000)
    parser.add_argument("--smoke-cycles", type=int)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    if args.audit:
        result = audit_export(args.audit)
    elif args.plan:
        result = plan(args.weight, args.seed, args.arm, args.window, args.smoke_cycles)
    else:
        if not args.evidence_root or not args.out:
            parser.error("--evidence-root and --out required")
        root = args.evidence_root.resolve()
        if args.freeze:
            result = freeze(root)
            directory = output_dir(args.out, root)
            write_json(directory / "cohort.json", result)
            (directory / "SHA256SUMS").write_text(sha(directory / "cohort.json") + "  cohort.json\n")
        else:
            result = export_case(root, args.weight, args.seed, args.arm, args.out, args.window, args.smoke_cycles)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
