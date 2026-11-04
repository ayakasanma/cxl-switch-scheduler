"""Vector result figures from the same validated evidence as the v3 tables."""
import json
import argparse
from pathlib import Path
import hashlib
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import generate_revision_v3 as g
from matplotlib.patches import Rectangle, FancyArrowPatch

OUT = Path(__file__).parent / "generated" / "figures"
COLORS = ["#666666", "#56B4E9", "#0072B2", "#D55E00", "#CC79A7", "#A78500", "#009E73"]
LABELS = ["FCFS", "RR1", "RR10", "FAI-\ninspired", "Alg.-2", "BLISS\ninsp.", "CGOF\n(2:1)"]


def data():
    _, manifest = g.render()
    analysis = json.loads((g.ROOT / (g.FINAL + "snapshot/analysis/analysis.json")).read_text())
    endpoints = analysis["endpoints"] + analysis["conditional_dac"]["endpoints"]
    def p99(policy, arm, group, n=4, ready=None):
        rows = [r for r in endpoints if r["policy"] == policy and r["profile"] == "trained-" + arm
                and r["configuration"]["group"] == group and r["configuration"]["n_src"] == n
                and (ready is None or r["configuration"]["ready"] == ready)]
        return g.cohort(rows, range(529, 549) if "confirmation" in group else range(509, 514))["p99"]
    confirmation = {a: [p99(p, a, "insight-confirmation" if p == "DAC2" else "n4-confirmation")
                        for p in g.POLICIES] for a in ("A", "B")}
    pairs = [p for p in analysis["comparisons"] + analysis["conditional_dac"]["comparisons"]
             if p.get("confirmation") and p["candidate_configuration"]["group"] in ("n4-confirmation", "insight-confirmation")]
    contrasts = []
    for candidate, baseline in (("MAIN", "FCFS"), ("MAIN", "RR10"), ("DAC2", "MAIN")):
        for arm in ("A", "B"):
            p = next(p for p in pairs if (p["candidate"], p["baseline"], p["profile"]) ==
                     (candidate, baseline, "trained-" + arm))
            lo, hi = p["paired_bootstrap"]["percentile95"]
            value = p["mean_p99_delta_cycles"]
            g.require(lo <= value <= hi, "CI must bracket the plotted estimate")
            contrasts.append(dict(candidate=candidate, baseline=baseline, arm=arm, value=value, low=lo, high=hi))
    ns = {a: {str(n): [p99(p, a, "n-expansion", n) for p in g.POLICIES[:-1]]
              for n in (8, 16)} for a in ("A", "B")}
    # Read perturbation identities from the accepted endpoints, not manuscript cells.
    robust = [r for r in endpoints if r["configuration"]["group"] == "trained-robustness"]
    configs = {}
    for r in robust:
        c = r["configuration"]
        key = json.dumps(c, sort_keys=True)
        configs[key] = c
    # The complete configuration includes policy; group by workload fields below.
    keys = ("ready", "heavy_rate", "heavy_source", "burst_size", "burst_period")
    workloads = {}
    for c in configs.values():
        workloads[tuple(str(c[k]) for k in keys)] = {k: c[k] for k in keys}
    robustness = []
    for _, c in sorted(workloads.items()):
        values = {}
        for p in g.POLICIES[:-1]:
            chosen = [r for r in robust if r["policy"] == p and r["profile"] == "trained-B"
                      and all(r["configuration"][k] == c[k] for k in keys)]
            values[p] = g.cohort(chosen, range(509, 514))["p99"]
        robustness.append(dict(configuration=c, values=values))
    dac = []
    for ready in ("bernoulli-0.75", "periodic-48/64"):
        for a in ("A", "B"):
            dac.append(dict(ready=ready, arm=a,
                           main=p99("MAIN", a, "trained-robustness", ready=ready),
                           dac=p99("DAC2", a, "insight-robustness", ready=ready)))
    power = json.loads((g.ROOT / g.POWER).read_text())["cases"]
    totals = {a: [float(sum(g.Decimal(c["printed_W"]["total"]) for c in power
                           if c["policy"] == p and c["arm"] == a) / 3 * 1000)
                  for p in ("fcfs", "rr", "fai-main")] for a in ("A", "B")}
    area = manifest["existing_record_supplement"]["primary_disjoint_area"]["n4_subset"]
    dac_area = float(re.search(r"^total_cell_area\s*=\s*([\d.]+)",
                     (g.ROOT / (g.PPA + "reports/area_summary.rpt")).read_text(),
                     re.M)[1])
    sensitivity = {}
    for group, field in (("rr-quantum","rr_quantum"),("high-quota","high_quota"),("depth","depth")):
        selected = [r for r in endpoints if r["configuration"]["group"] == group]
        series = []
        for policy in sorted({r["policy"] for r in selected}):
            for arm in ("A","B"):
                points = []
                for value in sorted({r["configuration"][field] for r in selected}):
                    chosen = [r for r in selected if r["policy"] == policy and r["profile"] == "trained-"+arm
                              and r["configuration"][field] == value]
                    points.append([value,g.cohort(chosen,range(509,514))["p99"]])
                series.append(dict(policy=policy,arm=arm,points=points))
        sensitivity[group] = series
    return dict(confirmation=confirmation, contrasts=contrasts, n_expansion=ns,
                robustness=robustness, dac_backpressure=dac, power_mW=totals,
                primary_area=area, dac_area=dac_area, sensitivity=sensitivity,
                inputs=manifest["inputs"], table_tex_sha256=manifest["output_tex_sha256"],
                scope="Confirmation: 20 seeds, paired pointwise 95% CIs only. Exploration: 5 seeds, power: 3 seeds, no CIs. N8/16 and power exclude CGOF.")


def main():
    d = data()
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    outputs = {}
    def save(fig, name):
        for ext in ("pdf", "svg", "png"):
            p = OUT / (name + "." + ext)
            fig.savefig(p, bbox_inches="tight", dpi=180)
            outputs[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        plt.close(fig)
    def bars(ax, values, labels, colors=COLORS):
        x = np.arange(len(values))
        b = ax.bar(x, values, color=colors[:len(values)], width=.67)
        ax.bar_label(b, labels=[f"{v:g}" for v in values], padding=3, fontsize=8)
        ax.set_xticks(x, labels)
        ax.set_ylim(0, max(values) * 1.23)
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=.18)
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.65), layout="constrained", sharey=True)
    for ax, a in zip(axes, ("A", "B")):
        bars(ax, d["confirmation"][a], LABELS)
        ax.set_title(f"({a.lower()}) Arm {a}: " + ("independent arrivals" if a == "A" else "bursts"))
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel("Mean run-P99 (cycles; lower is better)")
    save(fig, "confirmation")
    fig, ax = plt.subplots(figsize=(7.1, 2.75), layout="constrained")
    for y, p in enumerate(d["contrasts"]):
        ax.errorbar(p["value"], y, xerr=[[p["value"]-p["low"]], [p["high"]-p["value"]]],
                    fmt="o", capsize=4, color="#0072B2" if p["arm"] == "A" else "#D55E00")
        ax.annotate(f'{p["value"]:g} [{p["low"]:g}, {p["high"]:g}]', (p["high"], y),
                    xytext=(9, 0), textcoords="offset points", va="center", fontsize=8)
    ax.set_yticks(range(6), [f'{g.LABELS.get(p["candidate"],p["candidate"])} minus {g.LABELS.get(p["baseline"],p["baseline"])} / {p["arm"]}' for p in d["contrasts"]])
    ax.invert_yaxis(); ax.axvline(0, color="#555555", lw=1)
    ax.set_xlim(-15, 10); ax.grid(axis="x", alpha=.18)
    ax.set_xlabel("Paired mean P99 difference (cycles); negative favors the candidate")
    save(fig, "paired-contrasts")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.8), layout="constrained", sharey=True)
    for ax, a in zip(axes, ("A", "B")):
        for i, p in enumerate(g.POLICIES[:-1]):
            ax.plot([8, 16], [d["n_expansion"][a][str(n)][i] for n in (8,16)],
                    marker=["o","s","^","D","v","X"][i], color=COLORS[i], label=LABELS[i].replace("\n"," "))
        ax.set_xticks([8,16]); ax.set_xlabel("Sources N"); ax.set_title(f"Arm {a} (5 exploration seeds)")
        ax.set_ylim(0,57); ax.grid(alpha=.18)
    axes[0].set_ylabel("Mean run-P99 (cycles)")
    axes[1].legend(fontsize=7, loc="upper left", ncol=2)
    save(fig, "n-expansion")
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.1), layout="constrained", gridspec_kw={"width_ratios":[1.35,1]})
    def workload_label(c):
        if c["ready"] != "always": return c["ready"].replace("bernoulli-","Ready ").replace("periodic-","Ready ")
        if c["burst_size"] == 32: return "Burst 32"
        if c["heavy_source"] == 3: return "Heavy ID3"
        return f'Heavy rate {c["heavy_rate"]}'
    matrix = [[r["values"][p] for p in g.POLICIES[:-1]] for r in d["robustness"]]
    axes[0].imshow(matrix, cmap="YlOrRd", vmin=0, vmax=90, aspect="auto")
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            axes[0].text(x,y,f"{v:g}",ha="center",va="center",fontsize=7,color="white" if v>60 else "#222222")
    axes[0].set_xticks(range(6), LABELS[:6], fontsize=7)
    axes[0].set_yticks(range(6), [workload_label(r["configuration"]) for r in d["robustness"]], fontsize=7)
    axes[0].set_title("(a) Burst-arm B mean run-P99")
    x=np.arange(4)
    for offset, field, color, label in ((-.18,"main",COLORS[3],"FAI-inspired"),(.18,"dac",COLORS[6],"CGOF (2:1)")):
        b=axes[1].bar(x+offset,[r[field] for r in d["dac_backpressure"]],.36,color=color,label=label)
        axes[1].bar_label(b,fmt="%g",fontsize=7,padding=2)
    axes[1].set_xticks(x,["0.75\nA","0.75\nB","48/64\nA","48/64\nB"],fontsize=8)
    axes[1].set_ylim(0,44);axes[1].legend(fontsize=7); axes[1].set_title("(b) Paired backpressure cohorts")
    axes[1].set_ylabel("Mean run-P99 (cycles)"); axes[1].grid(axis="y",alpha=.18);axes[1].set_axisbelow(True)
    save(fig, "robustness")
    fig,axes=plt.subplots(1,3,figsize=(7.1,2.7),layout="constrained")
    for ax,group,title,xlabel in zip(axes,("rr-quantum","high-quota","depth"),
            ("(a) RR quantum","(b) FAI-inspired class quota","(c) FIFO depth"),
            ("RR quantum","High quota (Low = 10)","FIFO depth")):
        for s in d["sensitivity"][group]:
            color=COLORS[2 if s["policy"]=="RR" else g.POLICIES.index(s["policy"])]
            x,y=zip(*s["points"])
            ax.plot(x,y,marker="o" if s["arm"]=="A" else "s",ls="--" if s["arm"]=="A" else "-",
                    color=color,markersize=3,label=g.LABELS.get(s["policy"],s["policy"])+" "+s["arm"])
        ax.set_title(title,fontsize=9);ax.set_xlabel(xlabel,fontsize=8)
        ax.set_ylim(bottom=0);ax.grid(alpha=.18);ax.legend(fontsize=6,ncol=2,loc="upper left")
    axes[0].set_ylabel("Mean run-P99 (cycles)")
    # Leave space above the largest point so legends never cover measured values.
    for ax in axes: ax.set_ylim(0,ax.get_ylim()[1]*1.45)
    save(fig,"sensitivity")
    fig, axes = plt.subplots(1,2,figsize=(7.1,3.0),layout="constrained")
    bottom=np.zeros(3)
    for key,label,color in (("descriptor_storage","Descriptors","#56B4E9"),("timestamp_storage","Timestamps","#E69F00"),("policy","Policy logic","#D55E00"),("common","Common","#777777")):
        values=np.array([float(c["categories"][key])/1000 for c in d["primary_area"]])
        axes[0].bar(range(3),values,bottom=bottom,color=color,label=label,width=.65);bottom+=values
    axes[0].bar(3,d["dac_area"]/1000,color="white",edgecolor=COLORS[6],hatch="///",label="CGOF (2:1) total only",width=.65)
    for i,v in enumerate(list(bottom)+[d["dac_area"]/1000]): axes[0].text(i,v+1.5,f"{v:.2f}",ha="center",fontsize=8)
    axes[0].set_xticks(range(4),["FCFS","RR10",LABELS[3],LABELS[6]],fontsize=8)
    axes[0].set_ylim(0,146);axes[0].legend(fontsize=6.5,ncol=2,loc="upper left")
    axes[0].set_ylabel(r"Cell area ($10^3$ $\mu$m$^2$)"); axes[0].set_title("(a) N4 complete mapped area")
    x=np.arange(3)
    for a,offset,color in (("A",-.18,"#0072B2"),("B",.18,"#D55E00")):
        axes[1].bar(x+offset,d["power_mW"][a],.36,label="Arm "+a,color=color)
    for i in range(3):
        axes[1].text(i,max(d["power_mW"][a][i] for a in ("A","B"))+.07,
                     f'{d["power_mW"]["A"][i]:.3f} / {d["power_mW"]["B"][i]:.3f}',ha="center",fontsize=7)
    axes[1].set_xticks(x,["FCFS","RR10",LABELS[3]]);axes[1].set_ylim(0,4.3)
    axes[1].set_ylabel("Mean total power (mW)");axes[1].legend(fontsize=7)
    axes[1].set_title("(b) Trained activity; 3 seeds")
    for ax in axes: ax.set_axisbelow(True); ax.grid(axis="y",alpha=.18)
    save(fig,"hardware")
    (OUT/"plot-data.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    outputs["plot-data.json"]=hashlib.sha256((OUT/"plot-data.json").read_bytes()).hexdigest()
    (OUT/"figure-manifest.json").write_text(json.dumps(dict(generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        matplotlib=matplotlib.__version__,outputs=outputs),indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(figures=6,formats=["pdf","svg","png"],output=str(OUT))))


def improvement_data():
    """Use the generated table evidence, rechecking all bound bytes without reanalysis."""
    p = OUT.parent / "improvement_evidence_manifest.json"
    d = json.loads(p.read_bytes())
    g.require(d["generator"]["sha256"] == g.digest(Path(g.__file__).read_bytes()), "regenerate improvement tables first")
    g.require(d["output_tex_sha256"] == g.digest((OUT.parent / "improvement_results.tex").read_bytes()), "improvement table binding")
    for name, expected in d["inputs"].items():
        with (g.ROOT / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        g.require(actual == expected, "improvement figure input hash mismatch: " + name)
    d["table_manifest_sha256"] = g.digest(p.read_bytes())
    return d


def improvement_figures(d, out=OUT / "improvement"):
    """Five full-width, editable vector figures; source semantics stay in the evidence manifest."""
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
        "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 9, "legend.fontsize": 8,
        "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
        "svg.fonttype": "none", "svg.hashsalt": "cxl-improvement-20261028"})
    blue, orange, ink, pale = "#0077BB", "#AA5500", "#252525", "#EDF4F8"
    outputs = {}
    def save(fig, name):
        for ext in ("pdf", "svg", "png"):
            path = out / (name + "." + ext)
            metadata = {"CreationDate": None, "ModDate": None} if ext == "pdf" else ({"Date": None} if ext == "svg" else {})
            fig.savefig(path, dpi=300, facecolor="white", metadata=metadata)
            outputs[path.name] = g.digest(path.read_bytes())
        plt.close(fig)
    def box(ax, x, y, w, h, text, color=pale, edge=ink, size=9):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor=edge, lw=.9))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=size, color=ink)
    def arrow(ax, start, end, back=False):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11,
            color=orange if back else blue, lw=1.2, linestyle="--" if back else "-"))
    def diagram(height):
        fig, ax = plt.subplots(figsize=(7.1, height))
        fig.subplots_adjust(left=.015, right=.985, bottom=.02, top=.98)
        ax.set(xlim=(0, 10), ylim=(0, height * 1.4)); ax.axis("off")
        return fig, ax

    fig, ax = diagram(4.0)
    ax.text(.15, 5.3, "(a) Shared CXL memory-access path", weight="bold", fontsize=10)
    for y, label in ((4.55, "Host 0"), (3.88, "Host 1"), (3.21, "Host N−1")):
        box(ax, .15, y, 1.45, .48, label)
        arrow(ax, (1.6, y+.24), (3.05, 4.12))
    box(ax, 3.05, 3.65, 1.85, .94, "CXL switch\nshared egress")
    box(ax, 7.4, 3.65, 2.1, .94, "Pooled memory\nshared capacity")
    arrow(ax, (4.9, 4.32), (7.4, 4.32)); ax.text(6.15, 4.55, "Requests", ha="center", color=blue)
    arrow(ax, (7.4, 3.9), (4.9, 3.9), back=True); ax.text(6.15, 3.55, "Backpressure", ha="center", color=orange)
    ax.text(6.4, 3.14, "Concurrent hosts contend for the shared path", ha="center", fontsize=8)
    ax.plot([.15, 9.75], [2.95, 2.95], color="#B0B0B0", lw=.7)
    ax.text(.15, 2.65, "(b) Executable single-output descriptor slice", weight="bold", fontsize=10)
    box(ax, .15, 1.15, 1.5, .9, "N request\nsources")
    box(ax, 2.45, 1.15, 1.5, .9, "N FIFOs\ndepth D")
    box(ax, 4.75, 1.15, 1.75, .9, "Policy\narbitration")
    box(ax, 7.15, 1.15, 1.35, .9, "Held grant\n+ output")
    box(ax, 9.05, 1.15, .8, .9, "Sink", color="white")
    for x1, x2 in ((1.65, 2.45), (3.95, 4.75), (6.5, 7.15), (8.5, 9.05)):
        arrow(ax, (x1, 1.8), (x2, 1.8))
    arrow(ax, (2.45, 1.38), (1.65, 1.38), back=True)
    arrow(ax, (9.05, 1.38), (8.5, 1.38), back=True)
    ax.text(2.05, .99, "in_ready", ha="center", fontsize=8, color=orange)
    ax.text(8.78, .99, "out_ready", ha="center", fontsize=8, color=orange)
    ax.text(5.0, 2.2, "105-bit descriptors flow forward; arbitration selects an eligible head", ha="center", fontsize=8)
    ax.text(5.0, .77, "fire = valid ∧ ready: dequeue + consume service quota", ha="center", weight="bold")
    ax.text(5.0, .36, "FIFO admission uses beginning occupancy.  Output stall holds descriptor + grant context.", ha="center", fontsize=8)
    save(fig, "pooling-path")

    fig, ax = diagram(3.55)
    ax.text(.15, 4.68, "Main FAI-inspired: window evidence and effective service class", weight="bold", fontsize=10)
    x = [2.6, 5.25, 7.9]
    for i, label in enumerate(("Initial state", "After window k", "After window k+1")):
        ax.text(x[i]+.75, 4.25, label, ha="center", fontsize=8)
    examples = [(3.23, "Persistent DOWN", ["H", r"$B_H$", "L"], ["High", "High", "Low"], ["DOWN", "DOWN"]),
                (2.05, "Persistent UP", ["L", r"$B_L$", "H"], ["Low", "Low", "High"], ["UP", "UP"]),
                (.87, "Cancelled change", ["H", r"$B_H$", "H"], ["High"]*3, ["DOWN", "KEEP / UP / idle"])]
    for y, title, states, effective, evidence in examples:
        ax.text(.15, y+.29, title, va="center", weight="bold", fontsize=9)
        for i, (state, eff) in enumerate(zip(states, effective)):
            box(ax, x[i], y, 1.5, .63, state, color=pale if eff == "High" else "#FFF1DF", size=12)
            ax.text(x[i]+.75, y-.2, "effective " + eff, ha="center", fontsize=8)
        for i in range(2):
            arrow(ax, (x[i]+1.5, y+.3), (x[i+1], y+.3))
            ax.text((x[i]+1.5+x[i+1])/2, y+.73, evidence[i], ha="center", fontsize=8)
    ax.text(5, .15, "Buffer is a classification state.  B_H retains High; B_L retains Low until confirmation.", ha="center", fontsize=8)
    save(fig, "buffer-transition")

    fig, ax = plt.subplots(figsize=(7.1, 3.25))
    fig.subplots_adjust(left=.19, right=.97, top=.74, bottom=.26)
    rows = d["fixed_class"]
    left = np.zeros(len(rows))
    fills = ["#FFF1DF", "#D2E5F0", "#A8CEE4", "#75AECE"]
    for i, (label, hatch) in enumerate(zip(("Source 0 · Low", "Source 1 · High", "Source 2 · High", "Source 3 · High"), ("", "", "//", ".."))):
        vals = np.array([100*r["shares"][i] for r in rows])
        ax.barh(range(3), vals, left=left, height=.58, color=fills[i], edgecolor=ink, lw=.65, hatch=hatch, label=label)
        for j, v in enumerate(vals):
            ax.text(left[j]+v/2, j, f"{v:.2f}%", ha="center", va="center", fontsize=9,
                    bbox=dict(facecolor=fills[i], edgecolor="none", pad=1.5))
        left += vals
    ax.set_yticks(range(3), [r["policy"] for r in rows]); ax.invert_yaxis()
    ax.set(xlim=(0, 100), xlabel="Measurement-phase service share (%)", xticks=[0, 25, 50, 75, 100])
    ax.legend(loc="lower left", bbox_to_anchor=(-.01, 1.02), ncol=2, frameon=False)
    fig.text(.02, .95, "Fixed-class allocation: one Low source and three High sources", weight="bold", fontsize=10)
    fig.text(.02, .07, "MODEL_ONLY · N4/D16 · 20,000 cycles · initialized L/H/H/H · drain excluded", fontsize=8)
    fig.text(.02, .025, "W = 5M configured; no classification boundary. Seeds 6201–6220 give identical shares.", fontsize=8)
    save(fig, "allocation-shares")

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.85), sharey=True)
    fig.subplots_adjust(left=.19, right=.96, top=.78, bottom=.32, wspace=.24)
    rows = d["finite_heavy"]
    palette = ["#666666", blue, orange, "#666666", "#666666"]
    for ax, key, title, limit in zip(axes, ("sparse_p99", "heavy_max_gap"),
            ("(a) Sparse mean run-P99", "(b) Mean per-run Heavy max gap"), (35, 12)):
        values = [r[key] for r in rows]
        bars = ax.barh(range(5), values, height=.59, color=palette)
        for i in (2, 4): bars[i].set_hatch("///"); bars[i].set_edgecolor("white")
        ax.bar_label(bars, labels=[f"{v:.2f}" for v in values], padding=4, fontsize=9)
        ax.set_title(title, fontsize=9); ax.set(xlim=(0, limit), xlabel="Cycles")
        ax.set_axisbelow(True); ax.grid(axis="x", color="#DDDDDD", lw=.5)
    axes[0].set_yticks(range(5), [r["policy"] for r in rows]); axes[0].invert_yaxis()
    fig.text(.02, .95, "Sparse waiting and Heavy service gaps under overload", weight="bold", fontsize=10)
    fig.text(.02, .89, "MODEL_ONLY · N4/D16 · 20 seeds (6201–6220) · Heavy work = 20,000", fontsize=8)
    fig.text(.02, .84, "W = 5M configured; no classification boundary. Class-aware policies remain initially all High.", fontsize=8)
    contrast = next(c for c in d["model_cohorts"]["finite-heavy"]["overload_paired_contrasts"] if c["id"] == "fai-inspired-control")
    g.require(contrast["candidate"] == "CGOF_w2_oldest-first" and contrast["baseline"] == "FAI-inspired", "tradeoff contrast direction")
    pieces = []
    for key, label in (("sparse_completed_generation_to_fire_p99", "Sparse P99"), ("heavy_max_service_gap", "Heavy max gap")):
        m = contrast["metrics"][key]
        pieces.append(f"{label}: {m['mean_paired_delta']:+.2f} [{m['percentile95'][0]:+.2f}, {m['percentile95'][1]:+.2f}]")
    fig.text(.02, .16, "CGOF (2:1) − FAI-inspired: paired mean differences, 95% bootstrap CIs (cycles)", fontsize=8)
    fig.text(.02, .105, "    ".join(pieces), fontsize=8)
    fig.text(.02, .04, "Sparse generation-to-fire includes completed drain requests; Heavy gaps use active service.", fontsize=8)
    save(fig, "heavy-sparse-tradeoff")

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.75), sharey=True)
    fig.subplots_adjust(left=.18, right=.96, top=.77, bottom=.24, wspace=.25)
    rows = sorted(d["hardware"], key=lambda r: (r["n"], r["policy"]))
    for ax, key, scale, title, limit, fmt in zip(axes, ("area", "setup_slack_ns"), (1000, 1),
            ("(a) Complete mapped cell area", "(b) Worst reported setup slack"), (550, 16), (".2f", ".3f")):
        values = [float(r[key])/scale for r in rows]
        bars = ax.barh(range(6), values, height=.62, color=[blue, orange]*3)
        for i in (1, 3, 5): bars[i].set_hatch("///"); bars[i].set_edgecolor("white")
        ax.bar_label(bars, labels=[format(v, fmt) for v in values], padding=4, fontsize=8)
        ax.set_title(title, fontsize=9); ax.set_xlim(0, limit)
        ax.set_xlabel("Library cell-area units (×1,000)" if key == "area" else "Setup slack (ns); clock period 25 ns", fontsize=8)
        ax.set_axisbelow(True); ax.grid(axis="x", color="#DDDDDD", lw=.5)
    axes[0].set_yticks(range(6), [f"N{r['n']} · {r['policy'].replace('CGOF ', '')}" for r in rows]); axes[0].invert_yaxis()
    fig.text(.02, .95, "CGOF hardware cost and timing across six configurations", weight="bold", fontsize=10)
    fig.text(.02, .88, "PRE-LAYOUT · SAED32 RVT TT 0.78 V / 25 °C · D16/W5M · High:Low = 1:1 or 2:1", fontsize=8)
    fig.text(.02, .075, "Zero reported timing violations; untested timing checks remain. CGOF power is unmeasured.", fontsize=8)
    fig.text(.02, .025, "Area includes shared FIFOs, timestamps, policy logic and interface; exact values are in the table.", fontsize=8)
    save(fig, "cgof-hardware")
    plot_data = {k:d[k] for k in ("fixed_class", "finite_heavy", "production_rtl", "common_demand_rtl", "hardware", "model_cohorts")}
    p = out / "plot-data.json"
    p.write_text(json.dumps(plot_data, indent=2, sort_keys=True)+"\n", encoding="utf-8", newline="\n")
    outputs[p.name] = g.digest(p.read_bytes())
    manifest = dict(schema="cxl-improvement-figures-v1", generator_sha256=g.digest(Path(__file__).read_bytes()),
        table_manifest_sha256=d["table_manifest_sha256"], outputs=outputs, matplotlib=matplotlib.__version__,
        width_inches=7.1, placement="full-width figure*; preserve at least 8pt annotation text", png_dpi=300,
        figure_table_trace=[dict(artifact_id=name, source_data=dict(file="../../improvement_evidence_manifest.json", dataset_id=key),
            transformation=dict(script="docs/final-report/generate_revision_figures.py", hash=g.digest(Path(__file__).read_bytes())),
            caption_claim=claim, supported_manuscript_claims=[], limitations=limits)
            for name, key, claim, limits in (
                ("pooling-path", "inputs/specs/CXL_SPEC.md", "Multiple hosts contend on a shared path; the modeled slice transports atomic descriptors.", ["Conceptual system path; descriptor RTL boundary only."]),
                ("buffer-transition", "inputs/specs/CXL_SPEC.md", "Main Buffer preserves the previous effective class pending a second supporting window.", ["Illustrative rule examples; not latency measurements or H1 evidence."]),
                ("allocation-shares", "fixed_class", "Class quotas and per-source credits yield different fixed-class shares.", ["MODEL_ONLY continuous backlog, 20,000-cycle horizon; drain excluded; initial L/H/H/H; no W5M boundary."]),
                ("heavy-sparse-tradeoff", "finite_heavy", "Lower Sparse mean run-P99 coexists with higher mean maximum Heavy gaps for CGOF.", ["MODEL_ONLY overload, 20 seeds; class-aware policies initially all High; no W5M boundary; distinct from one-seed near-profile RTL."]),
                ("cgof-hardware", "hardware", "Six CGOF configurations have positive reported setup slack at 25ns.", ["Pre-layout STA; untested checks; no CGOF power result."]))])
    (out / "figure-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(dict(figures=5, formats=["pdf", "svg", "png"], output=str(out))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--improvement-only", action="store_true")
    args = parser.parse_args()
    if args.improvement_only:
        improvement_figures(improvement_data())
    else:
        main()
