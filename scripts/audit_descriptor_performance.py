"""Audit/reuse archived RTL evidence; emit per-run tables without running a simulator.

The selected accepted runs are explicit. Failed/partial siblings are inventoried, not deleted.
Run from any directory: python scripts/audit_descriptor_performance.py --output DIR
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim/common"))
from traffic_trace import make_trace  # noqa: E402

PRIMARY = {
    "FCFS": ("M3-primary", "20261020T165716Z_534", 0, "fcfs_primary_metrics.json"),
    "RR10": ("M4-primary", "20261020T170247Z_5075", 1, "rr_primary_metrics.json"),
    "Main": ("M5-primary", "20261020T172737Z_382", 2, "fai_primary_metrics.json"),
}
LONG = {
    "M5-stress": ("20261020T170825Z_8460", 30),
    "M5-production": ("20261020T173518Z_3766", 3),
    "M6-stress": ("20261021T011237Z_23789", 10),
    "M6-production": ("20261021T011237Z_23785", 1),
}
SOURCE = "759f86b24f13ed5984c19034eeeea2ca43b0e971"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def csv_write(path, rows):
    check(bool(rows), f"empty table: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def accepted_run(scope, run_id, expected):
    base = ROOT / "artifacts/implementation" / scope / run_id
    summary = read(base / "summary.json")
    check(summary["overall"] == "PASS" and summary["milestone_acceptance_scope"], str(base))
    counts = summary["counts"]
    check(counts["tests"] == expected and not any(counts[k] for k in ["fail", "not_run", "failures", "errors", "skipped"]), f"bad counts: {base}")
    check(summary["sim_build_relaxations"] == [], f"relaxed simulation: {base}")
    jobs = [s for s in summary["steps"] if s["kind"] == "cocotb"]
    check(len(jobs) == expected, f"wrong job matrix: {base}")
    for step in jobs:
        check(step["status"] == "PASS" and step["tests"] == 1, f"bad step: {step['name']}")
        check(not any(step[k] for k in ["failures", "errors", "skipped"]), step["name"])
        check(all(v == 0 for v in step["exit_codes"].values()), step["name"])
        xml = ET.parse(base / step["junit"]).getroot()
        check(len(list(xml.iter("testcase"))) == 1, f"JUnit count: {step['name']}")
        check(not any(list(xml.iter(k)) for k in ["failure", "error", "skipped"]), f"JUnit failure: {step['name']}")
    return base, summary, jobs


def ci(values):
    # Fixed twenty-seed descriptive interval under an independent-run sampling assumption.
    check(len(values) == 20, "twenty run values required, never pool requests as replications")
    m = statistics.mean(values)
    sd = statistics.stdev(values)
    half = 2.093024054408263 * sd / math.sqrt(20)  # t(0.975,19)
    return {"mean": m, "sample_sd": sd, "n_runs": 20, "ci95_low": m-half, "ci95_high": m+half}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    output = args.output.resolve()
    check(not output.exists() or not any(output.iterdir()), "use a fresh output directory; preserve prior audit")
    output.mkdir(parents=True, exist_ok=True)
    records, source_rows, inputs, traces = [], [], {}, {}
    old_hash_file = ROOT / ".setup-logs/implementation/comparator-20261021/regression/functional-sha256.txt"
    manifest = dict((line.split(maxsplit=1)[1].strip(), line.split()[0]) for line in old_hash_file.read_text().splitlines())
    needed = [n for n in manifest if n.startswith("rtl/") or n.endswith("traffic_trace.py") or n.endswith("test_switch_fcfs_primary.py") or n.endswith("test_switch_rr_primary.py") or n.endswith("test_switch_fai_primary.py") or n.endswith("switch_fcfs_tb.py")]
    for name in needed:
        blob = subprocess.check_output(["git", "show", f"{SOURCE}:{name}"], cwd=ROOT)
        check(hashlib.sha256(blob).hexdigest() == manifest[name], f"archived source mismatch: {name}")
    generator = "sim/common/traffic_trace.py"
    check(sha(ROOT/generator) == manifest[generator], "generator changed since archived primary")
    inputs[str(old_hash_file.relative_to(ROOT))] = sha(old_hash_file)
    provenance = {"accepted_source_revision": SOURCE,
                  "archived_manifest_checked_files": needed,
                  "note": "Runs were launched at dirty b54aa64; the archived source hashes reconcile selected RTL/harness/trace files to later clean759f86b, not launchHEAD alone."}
    for policy, (scope, run_id, param, suffix) in PRIMARY.items():
        base, summary, jobs = accepted_run(scope, run_id, 60)
        check(read(base/"primary_summary.json")["full_scope"] is True, f"incomplete gate: {base}")
        inputs[str((base/"summary.json").relative_to(ROOT))] = sha(base/"summary.json")
        keys = set()
        for step in jobs:
            n, seed = step["params"]["N_SRC"], step["seed"]
            check((n,seed) not in keys, "duplicate run")
            keys.add((n,seed))
            f = base / "results" / f"cocotb_{step['name'].split(':',1)[1]}__{suffix}"
            d = read(f)
            if (n,seed) not in traces:
                traces[n,seed] = make_trace(seed,n,100000,"primary").summary()
            check(d["trace"] == traces[n,seed], f"trace/config/hash mismatch: {f}")
            check(d["trace_sha256"] == traces[n,seed]["sha256"], str(f))
            check(d["n_src"] == n and d["seed"] == seed and d["policy_param"] == param, str(f))
            check(step["params"]["POLICY"] == param, str(f))
            check(d["profile"] == "primary" and d["measured_cycles"] == d["requested_cycles"] == 100000, str(f))
            check(d["phases"]["warmup_cycles"] == d["phases"]["measurement_reset_cycles"] == 0, str(f))
            if policy == "RR10":
                check(d["rr_quantum"] == 10 and step["params"].get("RR_QUANTUM", 10) == 10, str(f))
            if policy == "Main":
                check(d["fai_w"] == 5000000 and d["windows_closed_measurement"] == 0, str(f))
                check(d["fcfs_equivalence_checked_cycles"] == 100000, str(f))
            f_m, p_m, backlog = d["fires_measurement"], d["input_push_count"], d["generated_but_unaccepted"]
            waits = d["wait_acceptance_to_fire"]
            check(d["generated"] == p_m + backlog, f"producer conservation: {f}")
            check(p_m == f_m + d["fires_drain"] == waits["all_completed"]["count"], f"accept conservation: {f}")
            check(waits["outstanding_after_drain"] == waits["dropped_by_reset"] == 0, f"censored accept: {f}")
            check(waits["censored_at_measurement_end"] == d["fires_drain"], str(f))
            check(d["responses"]["completed"] == d["responses"]["issued"] == p_m+d["drain_only"]["pushes"], str(f))
            check(d["generation_to_acceptance"]["count"] == p_m, str(f))
            check(d["accepted_transfer_rate"] == f_m/100000 and d["input_push_rate"] == p_m/100000, str(f))
            check(sum(d["per_source_service_measurement"]) == f_m and sum(d["per_source_pushes"]) == p_m, str(f))
            cov = d["coverage_measurement"]
            row = {"policy":policy,"N":n,"seed":seed,"cycles":100000,"trace_sha256":d["trace_sha256"],
                   "generated":d["generated"],"accepted":p_m,"fires":f_m,"transfer_rate":f_m/100000,
                   "acceptance_rate":p_m/100000,"wait_mean":waits["all_completed"]["mean"],
                   "wait_p99":waits["all_completed"]["p99_nearest_rank"],
                   "gen_accept_mean_accepted_subset":d["generation_to_acceptance"]["mean"],
                   "gen_accept_p99_accepted_subset":d["generation_to_acceptance"]["p99_nearest_rank"],
                   "generated_unaccepted_at_cut":backlog,"accepted_unfired_at_cut":d["fires_drain"],
                   "stall_cycles":cov["stall_cycles"],"full_fifo_cycles":cov["full_cycles"],
                   "all_fifo_full_cycles":cov["all_full_cycles"],"drain_only_accepts":d["drain_only"]["pushes"],
                   "drain_cycles":d["phases"]["drain_cycles_total"],"sim_wall_s":step["sim_wall_time_s"],
                   "raw_metrics":str(f.relative_to(ROOT)),"raw_sha256":sha(f),"job_junit":str((base/step["junit"]).relative_to(ROOT))}
            records.append(row)
            for h in range(n):
                source_rows.append({"policy":policy,"N":n,"seed":seed,"source":h,
                    "generated":d["trace"]["generated_per_source"][h],"accepted":d["per_source_pushes"][h],
                    "fires":d["per_source_service_measurement"][h],
                    "offered_share":d["trace"]["generated_per_source"][h]/d["generated"],
                    "service_share":d["per_source_service_measurement"][h]/f_m})
        check(keys == {(n,s) for n in [4,8,16] for s in range(509,529)}, f"matrix mismatch: {scope}")
    pairs = {(r["policy"],r["N"],r["seed"]):r for r in records}
    for n in [4,8,16]:
        for seed in range(509,529):
            a,b=pairs["FCFS",n,seed],pairs["Main",n,seed]
            # Cold all-H equality is a measured outcome; don't invent an adaptive benefit.
            for k in ["fires","accepted","wait_mean","wait_p99","generated_unaccepted_at_cut"]:
                check(a[k]==b[k],f"FCFS/Main cold mismatch {n}/{seed}/{k}")
    stats=[]
    metric_names=["transfer_rate","acceptance_rate","wait_mean","wait_p99","gen_accept_mean_accepted_subset","gen_accept_p99_accepted_subset","generated_unaccepted_at_cut","stall_cycles"]
    for n in [4,8,16]:
        for policy in PRIMARY:
            for metric in metric_names:
                stats.append({"N":n,"policy":policy,"metric":metric,**ci([pairs[policy,n,s][metric] for s in range(509,529)])})
    deltas=[]
    for n in [4,8,16]:
        for policy in ["RR10","Main"]:
            for metric in metric_names:
                deltas.append({"N":n,"contrast":policy+" minus FCFS","metric":metric,
                               **ci([pairs[policy,n,s][metric]-pairs["FCFS",n,s][metric] for s in range(509,529)])})
    long_records=[]
    for scope,(run_id,expected) in LONG.items():
        base,summary,jobs=accepted_run(scope,run_id,expected)
        inputs[str((base/"summary.json").relative_to(ROOT))]=sha(base/"summary.json")
        for step in jobs:
            files=[base/a for a in step["artifacts"] if a.endswith("metrics.json")]
            check(len(files)==1,step["name"])
            d=read(files[0]);cov=d["coverage_measurement"]
            check(d["wait_acceptance_to_fire"]["outstanding_after_drain"]==0,str(files[0]))
            if "production" in scope:
                check(d["seed"]==509 and d["fai_w"]==5000000 and d["measured_cycles"]==20000000 and len(d["windows"])==4,str(files[0]))
                check(d["production_evidence"] is True,str(files[0]))
                check(all(sum(w["b_close"])==w["s_close"] for w in d["windows"]),str(files[0]))
            long_records.append({"scope":scope,"N":d["n_src"],"seed":d["seed"],"W":d["fai_w"],
                "measured_cycles":d["measured_cycles"],"reset_cycles":cov["reset_cycles"],"windows":cov["windows_closed"],
                "transition_bins":len(cov["transitions_reached"]),"transitions":cov["transitions_reached"],
                "held_class_changes":cov["held_cls_change"],"max_observed_wait":cov["max_wait"],
                "raw":str(files[0].relative_to(ROOT)),"sha256":sha(files[0])})
    history=[]
    for scope in [v[0] for v in PRIMARY.values()]+list(LONG):
        for f in sorted((ROOT/"artifacts/implementation"/scope).glob("*/summary.json")):
            d=read(f)
            history.append({"scope":scope,"run_id":f.parent.name,"recorded_status":d["overall"],
                "accepted_scope":d["milestone_acceptance_scope"],"tests":d["counts"]["tests"],
                "reason":"selected accepted evidence" if any(f.parent.name==v[1] for v in PRIMARY.values()) or (scope in LONG and f.parent.name==LONG[scope][0]) else "retained historical / not selected; RUNNING may be a stale interrupted checkpoint",
                "summary_sha256":sha(f)})
    records.sort(key=lambda r:(r["N"],r["seed"],r["policy"]))
    csv_write(output/"primary_runs.csv",records)
    csv_write(output/"per_source.csv",source_rows)
    csv_write(output/"seed_summary.csv",stats)
    csv_write(output/"paired_differences.csv",deltas)
    csv_write(output/"run_history.csv",history)
    audit={"status":"ACCEPTED_ARCHIVED_PRIMARY_REUSE","actual_primary_runs":len(records),"trace_groups":len(traces),
           "primary_cycles":18000000,"source":provenance,"inputs":inputs,"long_runs":long_records,
           "statistics":"20 seeds perN/policy; mean, sampleSD, t19 95%interval on mean; mean runP99 is NOT pooledrequestP99; paired differences sameN/seed",
           "missing_old_primary_fields":["per-phase measured counters/cohort latency","time-mean/max producer backlog","FIFO occupancy time series/mean/max","source backlog-conditioned service gaps"],
           "bias":"generation latency is measuredaccepted subset; unaccepted producer backlog remains censored. Accepted cohort includes drains but drain ready is1, not counterfactual continued workload.",
           "all_main_primary_equal_fcfs":True,"new_simulation_executed_by_this_script":False}
    (output/"audit.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print(f"PASS archived180runs,60regeneratedtracegroups,{len(long_records)}longruns; outputs {output}")


if __name__=="__main__":
    main()
