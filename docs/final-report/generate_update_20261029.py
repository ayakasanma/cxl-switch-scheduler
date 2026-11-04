"""Recompute the Oct29 report figures from sealed RTL results; runs no simulation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "generated" / "figures" / "update-20261029"
sys.path.insert(0, str(ROOT / "scripts"))
import aggregate_cgof_diagnosis as aggregate
from revision_statistics import histogram_summary

BATCH = "artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/"
PINS = {
    BATCH + "aggregate.json": "0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d",
    BATCH + "manifest.json": "2ac939b662c0f3bf970f4861cf01e6dbcb3967b01573c5ac27b8d8371f846407",
    "artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json":
        "da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097",
}
SEEDS = list(range(529, 549))
COLORS = ("#0072B2", "#D55E00")
METRICS = ("sparse_p99", "heavy_wall_gap_max", "heavy_completion_delta_cycles", "completion_ratio")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def check_histogram(stage):
    computed = histogram_summary(stage["histogram"])
    require(computed["count"] == stage["count"] and computed["p99"] == stage["p99"],
            "raw histogram count/P99 disagreement")
    return computed["p99"]


def check_grid(rows):
    keys = [(r["seed"], r["high_weight"]) for r in rows]
    require(len(keys) == 40 and len(set(keys)) == 40
            and set(keys) == {(s, w) for s in SEEDS for w in (1, 2)},
            "finite confirmation requires exactly 40 unique seed/quota pairs")


def collect():
    """Verify input closures, reaggregate per-run values and reproduce saved CIs."""
    inputs = {}

    def bind(path, expected=None):
        path = Path(path)
        if not path.is_absolute():
            path = ROOT / path
        value = sha(path)
        require(expected is None or value == expected, f"input drift: {relative(path)}")
        require(relative(path) not in inputs or inputs[relative(path)] == value,
                f"input changed during analysis: {relative(path)}")
        inputs[relative(path)] = value
        return json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else None

    for path, expected in PINS.items():
        bind(path, expected)
    saved = bind(BATCH + "aggregate.json")
    manifest = bind(BATCH + "manifest.json")
    require(manifest["seeds"] == SEEDS and manifest["expected_jobs"] == 80
            and manifest["expected_pairs"] == 40, "sealed manifest coverage changed")
    require(manifest["baseline_aggregate_sha256"] == inputs[manifest["baseline_aggregate"]],
            "baseline aggregate binding differs")
    finite = saved["finite_heavy"]
    performance = saved["performance"]
    excluded = manifest["prior_failed_batch"]
    require(not finite["partial_runs"] and len(finite["run_directories"]) == 20,
            "finite confirmation must have twenty completed scopes")
    require(len(finite["source_variants"]) == 1 and not finite["source_drift_files"],
            "repaired finite source is not stable")
    source_records = []
    for kind, block in (("finite_heavy", finite), ("performance", performance)):
        for path, expected in block["inputs_sha256"].items():
            bind(path, expected)
        for directory in block["run_directories"]:
            run = Path(directory)
            require(relative(run) != excluded["run"], "failed old batch was included")
            summary = bind(run / "summary.json")
            require(summary["overall"] in {"PASS", "RUNNING"}
                    and summary["steps"] and all(s["status"] == "PASS" for s in summary["steps"]),
                    "input run has non-PASS steps")
            if kind == "finite_heavy":
                scope = bind(run / "diagnosis_scope.json", finite["scopes_sha256"][str(run)])
                require(scope["status"] == "PASS" and scope["source_stable"]
                        and scope["source_hashes"] == scope["source_hashes_after"] == manifest["source_hashes"],
                        "finite scope/source closure differs")
                source = scope["source_hashes"]
                for record in scope["results"]:
                    raw = bind(run / record["path"])
                    require(raw == record["data"], "scope embedded result differs from raw file")
            else:
                source = bind(run / "source_hashes_before.json")
                frozen = bind(run / "frozen-spec.json")
                require(aggregate.canonical_sha(source) == frozen["source_sha256"],
                        "performance frozen source differs")
                if (run / "cgof_performance_scope.json").exists():
                    scope = bind(run / "cgof_performance_scope.json")
                    after = bind(run / "source_hashes_after.json")
                    require(source == after == scope["source_hashes"], "performance source changed during run")
            drift = []
            for path, expected in source.items():
                current = sha(ROOT / path)
                inputs[path] = current
                if current != expected:
                    drift.append(path)
            require(set(drift) <= {"AGENTS.md"}, f"executable source drift: {drift}")
            source_records.append(dict(run=relative(run), kind=kind,
                                       frozen_source_sha256=aggregate.canonical_sha(source),
                                       current_drift=drift))

    # Existing read-only aggregator reproduces every per-seed summary and its keyed bootstrap.
    fresh_finite = aggregate.finite_rows(finite["run_directories"])
    fresh_performance = aggregate.performance_rows(performance["run_directories"])
    for field in ("rows", "groups", "quota_deltas", "coverage", "pair_count"):
        require(fresh_finite[field] == finite[field], f"finite saved {field} differs from raw recomputation")
    for field in ("rows", "cohorts", "coverage", "endpoint_count"):
        require(fresh_performance[field] == performance[field], f"performance saved {field} differs from raw recomputation")
    check_grid(fresh_finite["rows"])
    raw_finite = {}
    for path in finite["inputs_sha256"]:
        if "__cgof_diagnosis_" not in path:
            continue
        raw = bind(path)
        job = raw["job"]
        key = job["seed"], job["high_weight"], job["lane"]
        require(key not in raw_finite, "duplicate raw finite job")
        raw_finite[key] = raw
        require(raw["status"] == "PASS" and job["window"] == job["heavy_work"] == 5_000_000
                and job["n_src"] == 4 and job["depth"] == 16 and job["profile"] == "near"
                and job["windows"] == 1 and len(raw["classifier"]) == 1,
                "finite job is outside the confirmed boundary")
        require(raw["classifier"][0]["classes"] == ["B_H", "H", "H", "H"],
                "unexpected finite class boundary")
        require(raw["active_cycles"] == raw["heavy"]["completion_cycle"] + 1,
                "inclusive completion cycle definition changed")
        cohort = raw["metrics"]["cohorts"]["finite-heavy"]
        require(cohort["generated"] == cohort["completed"] and sum(raw["generated"]) == raw["fired"],
                "repaired finite generation cohort incomplete")
        gap = raw["heavy"]["gaps"]["wall_cycles"]
        gap_stats = histogram_summary(gap["histogram"])
        require(gap_stats["max"] == raw["heavy"]["max_wall_gap"]
                and gap_stats["p99"] == gap["p99_nearest_rank"], "Heavy gap histogram differs")
        if job["lane"] == "mixed":
            check_histogram(cohort["pooled_sparse"]["generation_to_fire"])
    require(len(raw_finite) == 80, "requires all eighty repaired raw results")
    for seed in SEEDS:
        for lane in ("mixed", "isolated"):
            # Sparse generation stops at Heavy completion, so observed trace lengths can differ.
            configs = [raw_finite[(seed, w, lane)]["trace_config"] for w in (1, 2)]
            require(configs[0] == configs[1], "unpaired finite generator across quotas")
    perf_count = 0
    for path in performance["inputs_sha256"]:
        if "__cgof_performance.json" not in path:
            continue
        raw = bind(path)
        require(raw["training_cycles"] == 10_000_000 and raw["job"]["n_src"] == 4
                and raw["job"]["depth"] == 16, "performance training/platform differs")
        for arm in ("A", "B"):
            check_histogram(raw["metrics"]["cohorts"][arm]["pooled_sparse"]["generation_to_fire"])
        perf_count += 1
    require(perf_count == 30 and performance["endpoint_count"] == 60, "performance endpoint coverage differs")
    for script in ("scripts/aggregate_cgof_diagnosis.py", "scripts/analyze_rtl_diagnosis.py",
                   "scripts/revision_statistics.py", "scripts/revision_matrix.py"):
        bind(script)
    require(all(sha(ROOT / path) == expected for path, expected in inputs.items()),
            "input closure changed during analysis")
    return dict(schema="cxl-report-update-20261029/1", inputs=inputs, source_records=source_records,
                finite_rows=fresh_finite["rows"], finite_groups=fresh_finite["groups"],
                quota_deltas=fresh_finite["quota_deltas"], performance_rows=fresh_performance["rows"],
                performance_cohorts=fresh_performance["cohorts"], excluded_batch=excluded,
                coverage=dict(finite_raw_jobs=80, finite_pairs=40, finite_seeds=20,
                              performance_runs=30, performance_endpoints=60),
                pairing="Finite comparisons share seed and generator configuration; Sparse generation stops at Heavy completion, so observed trace hashes can differ with completion time.",
                metric_scope=dict(
                    sparse_p99="Within each run, pooled Sparse generation-to-fire nearest-rank P99, including generation-cohort completions during drain; aggregate is the mean of run P99s.",
                    heavy_wall_gap_max="Within each active phase, maximum FIFO-nonempty inter-service wall-cycle gap; includes sink stalls, excludes initial/empty/censored intervals; aggregate is the mean of run maxima.",
                    heavy_completion_delta_cycles="Heavy last-fire cycle in mixed minus isolated; inclusive active-cycle differences agree. Not memory completion or application slowdown.",
                    fairness="Active phase before drain; three mixed lanes have one Sparse request outstanding at cutoff. Generation-cohort waiting includes later drain completions.",
                    classifier="All eighty lanes cross one boundary to B_H/H/H/H and retain effective High for every source.",
                    readiness="Both exploration schedules have nominal 75% availability; realized Bernoulli rates vary by seed and phase."),
                statistical_method="Seed/run unit; 10,000 keyed percentile-bootstrap resamples; pointwise 95% intervals. No intervals for five-seed exploration.",
                conditions=dict(finite="N4 D16 W5M; 5M Heavy work; Heavy p=.8, each Sparse p=.02, ready p=.9; one class boundary, B_H/H/H/H, all effective High.",
                                performance="N4 D16 W5M; 10M training; CGOF2 only; A independent arrivals, B bursts; always-ready 20 seeds529-548, readiness exploration5 seeds509-513."))


def tex_tables(data):
    def cell(metric):
        mean = f'{metric["mean"]:.2f}'
        ci = metric["percentile95"]
        return mean if ci is None else mean + f' [{ci[0]:.2f}, {ci[1]:.2f}]'

    lines = [r"% Generated by generate_update_20261029.py; all values in cycles.",
             r"\newcommand{\UpdateFiniteHeavyTable}{%", r"\begin{tabular}{lrrr}\toprule",
             r"High:Low & Sparse run-P99 & Heavy run maximum gap & Heavy completion delay \\\midrule"]
    for group in data["finite_groups"]:
        lines.append(f'{group["high_weight"]}:1 & ' + " & ".join(cell(group[m]) for m in METRICS[:3]) + r" \\")
    lines += [r"\bottomrule\end{tabular}}", r"\newcommand{\UpdatePerformanceTable}{%",
              r"\begin{tabular}{llcrr}\toprule",
              r"Stage & Sink readiness & Seeds & A Sparse run-P99 & B Sparse run-P99 \\\midrule"]
    for ready in ("always", "bernoulli-0.75", "periodic-48/64"):
        groups = [next(g for g in data["performance_cohorts"] if g["cohort"] == a and g["ready"] == ready) for a in ("A", "B")]
        lines.append(("Confirmation" if ready == "always" else "Exploration") + " & "
                     + {"always": "Always", "bernoulli-0.75": "Bernoulli 0.75", "periodic-48/64": "Periodic 48/64"}[ready]
                     + f' & {groups[0]["n"]} & ' + " & ".join(cell(g["sparse_p99"]) for g in groups) + r" \\")
    lines += [r"\bottomrule\end{tabular}}", ""]
    return "\n".join(lines)


def figures(data):
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    exports = {}

    def save(fig, name):
        for ext in ("pdf", "svg", "png"):
            path = OUT / f"{name}.{ext}"
            fig.savefig(path, dpi=300, metadata={"Creator": "CXL report Oct29 evidence generator"}
                        if ext == "pdf" else None)
            exports[path.name] = sha(path)
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(7.1, 3.45))
    fig.subplots_adjust(left=.075, right=.985, bottom=.23, top=.66, wspace=.55)
    fig.suptitle("Finite-Heavy RTL confirmation · 20 paired seeds · one boundary", y=.98, fontsize=10)
    fig.text(.5, .895, "N4, D16, W5M · Heavy p=0.8; each Sparse p=0.02; sink-ready p=0.9", ha="center", fontsize=8)
    titles = ("(a) Sparse waiting", "(b) Heavy service gaps", "(c) Mixed − isolated")
    labels = ("Run-P99 (cycles)", "Run maximum (cycles)", "Completion delay (cycles)")
    for ax, metric, title, label in zip(axes, METRICS[:3], titles, labels):
        for i, seed in enumerate(SEEDS):
            rows = [next(r for r in data["finite_rows"] if r["seed"] == seed and r["high_weight"] == w) for w in (1, 2)]
            offset = (i - 9.5) * .009
            ax.plot([offset, 1 + offset], [r[metric] for r in rows], color="#AAAAAA", alpha=.45, linewidth=.6)
            for x, row, color in zip((offset, 1 + offset), rows, COLORS):
                ax.plot(x, row[metric], "o", color=color, markersize=2.6, alpha=.6)
        for x, group, color in zip((0, 1), data["finite_groups"], COLORS):
            stat = group[metric]; mean = stat["mean"]; lo, hi = stat["percentile95"]
            ax.errorbar(x, mean, yerr=[[mean-lo], [hi-mean]], fmt="D", color=color, markersize=5,
                        markeredgecolor="white", markeredgewidth=.5, capsize=4, linewidth=1.6, zorder=5)
            ax.text(x, 1.035, f"{mean:g}\n[{lo:g}, {hi:g}]", transform=ax.get_xaxis_transform(),
                    color=color, ha="center", va="bottom", fontsize=8)
        ax.set_title(title, loc="left", fontsize=9, pad=34)
        ax.set_xticks((0, 1), ("1:1", "2:1")); ax.set_xlim(-.35, 1.35)
        ax.set_xlabel("High:Low quota"); ax.set_ylabel(label, fontsize=8)
        ax.grid(axis="y", alpha=.18); ax.set_axisbelow(True)
    axes[0].set_ylim(0, 5); axes[1].set_ylim(0, 16); axes[2].axhline(0, color="#888888", linewidth=.6)
    axes[2].set_ylim(-1, 21)
    fig.text(.5, .035, "Lines pair the same seed across quotas; diamonds and brackets show means and pointwise 95% CIs.",
             ha="center", fontsize=8)
    save(fig, "finite-heavy-confirmation")

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.15), sharey=True)
    fig.subplots_adjust(left=.08, right=.98, bottom=.23, top=.76, wspace=.16)
    fig.suptitle("CGOF (2:1) RTL · arrival pattern and sink readiness", y=.98, fontsize=10)
    for ax, arm, color in zip(axes, ("A", "B"), COLORS):
        ax.set_title(f"({arm.lower()}) {arm}: " + ("independent arrivals" if arm == "A" else "bursts"), loc="left", fontsize=9, pad=30)
        ax.axvspan(-.4, .4, color="#EAF2F8", zorder=0)
        ax.axvline(.8, color="#AAAAAA", linestyle=":", linewidth=1)
        for xpos, ready in zip((0, 1.5, 2.5), ("always", "bernoulli-0.75", "periodic-48/64")):
            group = next(g for g in data["performance_cohorts"] if g["ready"] == ready and g["cohort"] == arm)
            rows = sorted((r for r in data["performance_rows"] if r["ready"] == ready and r["cohort"] == arm), key=lambda r:r["seed"])
            xs = xpos + np.linspace(-.11, .11, len(rows))
            ax.scatter(xs, [r["sparse_p99"] for r in rows], s=12, color=color, alpha=.5, zorder=3)
            stat=group["sparse_p99"]; mean=stat["mean"]
            if stat["percentile95"] is not None:
                lo, hi=stat["percentile95"]
                ax.errorbar(xpos, mean, yerr=[[mean-lo],[hi-mean]], fmt="D", color=color, markersize=5, capsize=4, zorder=4)
            else:
                ax.plot([xpos-.16,xpos+.16], [mean,mean], color=color, linewidth=2, zorder=4)
            ax.text(xpos, max(r["sparse_p99"] for r in rows)+1.3, f"{mean:g}", ha="center", color=color, fontsize=9)
        ax.text(0, 1.025, "Confirmation\nn=20; mean + 95% CI", transform=ax.get_xaxis_transform(), ha="center", fontsize=8)
        ax.text(2, 1.025, "Exploration\nn=5; mean + observations", transform=ax.get_xaxis_transform(), ha="center", fontsize=8)
        ax.set_xticks((0,1.5,2.5), ("Always\nready", "Bernoulli\n0.75", "Periodic\n48/64"))
        ax.set_xlim(-.45,2.95); ax.set_ylim(0,34)
        ax.grid(axis="y",alpha=.18); ax.set_axisbelow(True)
        ax.set_xlabel("Sink readiness")
    axes[0].set_ylabel("Sparse mean run-P99 (cycles)")
    fig.text(.5,.025,"Exploration compares readiness patterns at the same nominal 75% availability.",ha="center",fontsize=8)
    save(fig,"readiness-confirmation")
    return exports


def main():
    data = collect()
    tex = tex_tables(data)
    path = HERE / "generated" / "update_20261029_results.tex"
    path.write_text(tex, encoding="utf-8")
    exports = figures(data)
    plot_path = OUT / "plot-data.json"
    plot_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    record = dict(schema="cxl-update-20261029-manifest/1", status="RAW_METRICS_AND_SAVED_INTERVALS_RECOMPUTED",
                  generator_sha256=sha(__file__), width_inches=7.1, png_dpi=300,
                  inputs=data["inputs"], source_records=data["source_records"], coverage=data["coverage"],
                  excluded_batch=data["excluded_batch"], statistical_method=data["statistical_method"],
                  pairing=data["pairing"],
                  metric_scope=data["metric_scope"],
                  conditions=data["conditions"], outputs=exports, plot_data_sha256=sha(plot_path),
                  tex_sha256=sha(path), new_simulations=False,
                  historical_policy="Historical generators/pins/products preserved; mutable legacy evidence was not regenerated.")
    (OUT / "figure-manifest.json").write_text(json.dumps(record, indent=2)+"\n",encoding="utf-8")
    (HERE / "generated" / "update_20261029_manifest.json").write_text(json.dumps(record, indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(coverage=data["coverage"], inputs=len(data["inputs"]), exports=list(exports))))


if __name__ == "__main__":
    main()
