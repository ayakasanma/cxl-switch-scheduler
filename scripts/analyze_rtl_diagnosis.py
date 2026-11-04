#!/usr/bin/env python3
"""Read-only fairness and Heavy diagnostics for the accepted RTL endpoints.

The input is the sealed analysis JSON, not a plan or a model run.  The analyzer
never rewrites evidence and deliberately leaves system-level CXL metrics out:
fires are scheduler events, not completed bytes or memory-response samples.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics


SCHEMA = "cxl-rtl-diagnosis-v1"
STAGES = ("generation_to_acceptance", "acceptance_to_fire", "generation_to_fire")
EXPECTED_ANALYSIS_SHA256 = (
    "89170cfbe0bb449c25ebbe782203b1695550b7b6bb9e467bae8d6bb00b483061"
)
UNAVAILABLE = {
    "joint_backlog_quota_compliance":
        "RTL endpoints expose per-source backlog summaries, not a joint per-cycle "
        "all-source backlog trace.",
    "dynamic_weighted_cgof_entitlement":
        "RTL endpoints do not expose the dynamic per-window class trajectory needed "
        "to reconstruct CGOF (2:1) entitlements.",
    "finite_heavy_completion":
        "RTL endpoints have no finite Heavy workload, burst ID, or burst completion trace.",
    "completed_memory_bandwidth":
        "No calibrated CXL platform or completed-byte measurement is present.",
    "memory_response_latency":
        "Generation-to-fire is scheduler waiting, not an issue-to-response CXL measurement.",
    "application_slowdown":
        "No application or calibrated CXL system harness is present.",
}


def load_json(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def jain_index(values):
    """Jain's index for nonnegative service counts; None when no service exists."""
    values = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Jain inputs must be finite nonnegative values")
    total = sum(values)
    if total <= 0:
        return None
    return total * total / (len(values) * sum(value * value for value in values))


def _shares(counts):
    total = sum(counts)
    return [value / total if total else None for value in counts]


def fairness(counts, demand, heavy_source):
    """Report multiple references instead of treating unequal demand as unfair."""
    if len(counts) != len(demand) or not 0 <= heavy_source < len(counts):
        raise ValueError("invalid source vectors")
    sparse = [source for source in range(len(counts)) if source != heavy_source]
    active = [source for source in range(len(counts)) if demand[source] > 0]
    service_share = _shares(counts)
    demand_share = _shares(demand)
    referenced = None
    if active and service_share and demand_share and sum(counts) > 0:
        referenced = {
            "l1_error": sum(abs(service_share[h] - demand_share[h]) for h in active),
            "max_error": max(abs(service_share[h] - demand_share[h]) for h in active),
        }
    return {
        "service_counts": list(counts),
        "service_share": service_share,
        "generated_demand_counts": list(demand),
        "generated_demand_share": demand_share,
        "raw_jain_all": jain_index(counts),
        "active_service_jain": jain_index([counts[h] for h in active]) if active else None,
        "sparse_service_jain": jain_index([counts[h] for h in sparse]) if sparse else None,
        "generated_share_reference_error": referenced,
        "reference": "measured-phase arrivals; not common-demand fairness",
    }


def _summary(value):
    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in ("count", "mean", "min", "max", "end")}


def heavy_metrics(endpoint):
    """Measured-phase Heavy diagnostics that are actually present in the RTL data."""
    phase = endpoint["phase_metrics"]
    config = endpoint["configuration"]
    heavy = config["heavy_source"]
    fired = phase["fired"]
    total = sum(fired)
    ready = phase["ready"]
    eligible = phase["eligible_ready_opportunities"]
    gaps = phase["gaps"][heavy]["samples"]
    inter = gaps.get("inter_service", {})
    wall = inter.get("wall_cycles", {})
    ready_gap = inter.get("eligible_ready_opportunities", {})
    return {
        "source": heavy,
        "phase_cycles": phase["cycles"],
        "ready_cycles": ready,
        "eligible_ready_opportunities": eligible,
        "fires": fired[heavy],
        "total_fires": total,
        "fire_per_phase_cycle": fired[heavy] / phase["cycles"] if phase["cycles"] else None,
        "fire_per_ready_cycle": fired[heavy] / ready if ready else None,
        "fire_per_eligible_ready_opportunity": (
            fired[heavy] / eligible if eligible else None
        ),
        "service_fraction": fired[heavy] / total if total else None,
        "inter_service_wall_cycles": {
            key: wall.get(key) for key in ("count", "mean", "max", "p99_nearest_rank")
        },
        "inter_service_eligible_ready": {
            key: ready_gap.get(key) for key in ("count", "mean", "max", "p99_nearest_rank")
        },
        "backlog": _summary(phase["backlog"][heavy]),
        "occupancy": _summary(phase["occupancy"][heavy]),
        "avoidable_bubbles": phase["avoidable_bubbles"],
        "eligible_ready_utilization": phase["eligible_ready_utilization"],
    }


def _config_identity(config):
    """Canonical intervention identity; the seed is replication, not treatment."""
    without_seed = {key: value for key, value in config.items() if key != "seed"}
    return json.dumps(
        without_seed, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _endpoint_identity(endpoint):
    return (
        endpoint["policy"],
        endpoint["profile"],
        endpoint["seed"],
        _config_identity(endpoint["configuration"]),
    )


def _cohort_identity(endpoint):
    return (
        endpoint["policy"],
        endpoint["profile"],
        _config_identity(endpoint["configuration"]),
    )


def display_policy(policy):
    """Public labels never expose immutable internal evidence identifiers."""
    return {
        "DAC2": "CGOF (2:1)",
        "DAC1": "CGOF (1:1)",
        "MAIN": "FAI-inspired",
        "MAIN1W": "FAI-inspired",
    }.get(policy, policy)


def analyze(path, expected_sha256=None):
    data, digest = load_json(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("analysis SHA-256 does not match the accepted snapshot")
    if data.get("schema") != "cxl-current-result-analysis-v1":
        raise ValueError("accepted current-result analysis schema required")
    endpoints = list(data["endpoints"]) + list(
        data.get("conditional_dac", {}).get("endpoints", [])
    )
    rows = []
    endpoint_identities = set()
    for endpoint in endpoints:
        if endpoint.get("status") != "PASS" or not endpoint.get("production_evidence"):
            raise ValueError("diagnosis requires accepted production endpoints")
        config = endpoint["configuration"]
        phase = endpoint["phase_metrics"]
        fired = phase["fired"]
        generated = phase["generated"]
        if len(fired) != config["n_src"] or len(generated) != config["n_src"]:
            raise ValueError("source population differs from endpoint configuration")
        if endpoint.get("completed_by_phase") is None:
            raise ValueError("cohort completion evidence missing")
        cohort_completion = [
            sum(values[source] for values in endpoint["completed_by_phase"].values())
            for source in range(config["n_src"])
        ]
        latency_counts = [
            row["generation_to_fire"]["count"] for row in endpoint["per_source"]
        ]
        if cohort_completion != latency_counts:
            raise ValueError("generation-cohort completion differs from latency population")
        endpoint_identity = _endpoint_identity(endpoint)
        if endpoint_identity in endpoint_identities:
            raise ValueError("duplicate endpoint identity")
        endpoint_identities.add(endpoint_identity)
        rows.append({
            "identity": endpoint_identity,
            "cohort_identity": _cohort_identity(endpoint),
            "policy": endpoint["policy"],
            "display_policy": display_policy(endpoint["policy"]),
            "profile": endpoint["profile"],
            "seed": endpoint["seed"],
            "group": config.get("group"),
            "ready": config.get("ready"),
            "heavy_source": config["heavy_source"],
            "n_src": config["n_src"],
            "depth": config["depth"],
            "window": config["window"],
            "fairness": fairness(fired, generated, config["heavy_source"]),
            "heavy": heavy_metrics(endpoint),
            "cohort_completion_total": cohort_completion,
            "completed_generation_to_fire_counts": latency_counts,
        })
    by_cohort = defaultdict(list)
    for row in rows:
        by_cohort[row["cohort_identity"]].append(row)
    cohorts = []
    for identity, members in sorted(by_cohort.items(), key=lambda item: str(item[0])):
        seeds = [row["seed"] for row in members]
        if len(seeds) != len(set(seeds)):
            raise ValueError("duplicate seed within cohort")
        cohorts.append({
            "policy": identity[0],
            "display_policy": members[0]["display_policy"],
            "profile": identity[1],
            "group": members[0]["group"],
            "ready": members[0]["ready"],
            "heavy_source": members[0]["heavy_source"],
            "n_src": members[0]["n_src"],
            "depth": members[0]["depth"],
            "window": members[0]["window"],
            "seeds": sorted(seeds),
            "endpoint_count": len(members),
            "mean_raw_jain": statistics.mean(
                row["fairness"]["raw_jain_all"] for row in members
                if row["fairness"]["raw_jain_all"] is not None
            ) if any(row["fairness"]["raw_jain_all"] is not None for row in members) else None,
            "mean_active_jain": statistics.mean(
                row["fairness"]["active_service_jain"] for row in members
                if row["fairness"]["active_service_jain"] is not None
            ) if any(row["fairness"]["active_service_jain"] is not None for row in members) else None,
            "mean_sparse_jain": statistics.mean(
                row["fairness"]["sparse_service_jain"] for row in members
                if row["fairness"]["sparse_service_jain"] is not None
            ) if any(row["fairness"]["sparse_service_jain"] is not None for row in members) else None,
            "mean_heavy_fire_per_ready": statistics.mean(
                row["heavy"]["fire_per_ready_cycle"] for row in members
                if row["heavy"]["fire_per_ready_cycle"] is not None
            ) if any(row["heavy"]["fire_per_ready_cycle"] is not None for row in members) else None,
            "mean_heavy_service_fraction": statistics.mean(
                row["heavy"]["service_fraction"] for row in members
                if row["heavy"]["service_fraction"] is not None
            ) if any(row["heavy"]["service_fraction"] is not None for row in members) else None,
            "max_heavy_wall_gap": max(
                (row["heavy"]["inter_service_wall_cycles"]["max"] for row in members
                 if row["heavy"]["inter_service_wall_cycles"]["max"] is not None),
                default=None,
            ),
            "max_heavy_ready_gap": max(
                (row["heavy"]["inter_service_eligible_ready"]["max"] for row in members
                 if row["heavy"]["inter_service_eligible_ready"]["max"] is not None),
                default=None,
            ),
        })
    return {
        "schema": SCHEMA,
        "scope": "accepted RTL scheduler-boundary evidence only",
        "source_analysis": str(Path(path).resolve()),
        "source_sha256": digest,
        "endpoint_count": len(rows),
        "endpoints": rows,
        "cohorts": cohorts,
        "unavailable": UNAVAILABLE,
        "notes": [
            "Raw Jain is descriptive when source demand is asymmetric.",
            "Sparse-only Jain excludes the configured Heavy source.",
            "Fire/cycle is not measured memory bandwidth.",
            "Service gaps are observed scheduler intervals, not a starvation bound.",
        ],
    }


def markdown(result):
    lines = [
        "# RTL fairness and Heavy diagnosis",
        "",
        f"- Source: `{result['source_analysis']}`",
        f"- SHA-256: `{result['source_sha256']}`",
        f"- Accepted endpoints: {result['endpoint_count']}",
        "- Scope: scheduler-boundary RTL evidence; no CXL application measurement.",
        "",
        "## Cohort summaries",
        "",
        "| Policy | Profile | Group | Ready | N/D/W | Heavy src | Seeds | Raw Jain | Active Jain | Sparse Jain | Heavy fire/ready | Heavy share | Max wall gap |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["cohorts"]:
        def number(value, digits=6):
            return "UNAVAILABLE" if value is None else f"{value:.{digits}f}"
        lines.append(
            f"| {row['display_policy']} | {row['profile']} | {row['group']} | {row['ready']} | "
            f"{row['n_src']}/{row['depth']}/{row['window']} | {row['heavy_source']} | "
            f"{len(row['seeds'])} | {number(row['mean_raw_jain'])} | "
            f"{number(row['mean_active_jain'])} | {number(row['mean_sparse_jain'])} | "
            f"{number(row['mean_heavy_fire_per_ready'])} | "
            f"{number(row['mean_heavy_service_fraction'])} | "
            f"{row['max_heavy_wall_gap'] if row['max_heavy_wall_gap'] is not None else 'UNAVAILABLE'} |"
        )
    lines += [
        "",
        "Raw Jain includes the Heavy source and is expected to be low under asymmetric demand. "
        "It is not by itself a fairness verdict. Sparse Jain excludes the configured Heavy source.",
        "",
        "## Unavailable measurements",
        "",
    ]
    lines += [f"- `{key}`: {value}" for key, value in result["unavailable"].items()]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON path")
    parser.add_argument("--markdown", type=Path, help="new Markdown path")
    args = parser.parse_args(argv)
    if args.out.exists() or (args.markdown and args.markdown.exists()):
        parser.error("outputs must not already exist")
    result = analyze(args.analysis, EXPECTED_ANALYSIS_SHA256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({
        "endpoints": result["endpoint_count"],
        "cohorts": len(result["cohorts"]),
        "source_sha256": result["source_sha256"],
    }))
    return 0


if __name__ == "__main__":
    main()
