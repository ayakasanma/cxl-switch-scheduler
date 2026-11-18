"""Generate standalone v6 figures from verified Nov 2, Nov 6, and Nov 7 records.

Reads only pinned manifests/acceptances via generate_update_20261102 and the accepted
Nov 6/7 JSON records without altering any prior version scripts or figure files.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT_DIR = HERE / "generated" / "figures" / "v6"
sys.path.insert(0, str(HERE))

import generate_update_20261102 as nov02  # noqa: E402


def configure_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(
            out,
            dpi=300,
            bbox_inches="tight",
            metadata={"Creator": "CXL report v6 figure generator"} if ext == "pdf" else None,
        )
    plt.close(fig)


def make_ordering_figure(nov_data: dict) -> None:
    w5m_seeds = nov_data["w5m_ordering"]["seeds"]
    s_vals = [
        w5m_seeds[0]["S_Q1_OF"],
        w5m_seeds[0]["S_Q1_RR"],
        w5m_seeds[0]["S_Q2_OF"],
        w5m_seeds[0]["S_Q2_RR"],
    ]
    w256 = nov_data["w256_ordering"]
    assert w256["primary"]["d2"]["negative"] == 7 and w256["primary"]["d2"]["count"] == 20
    assert w256["verdict"] == "NOT_CONFIRMED"

    fig, ax = plt.subplots(figsize=(3.45, 2.50), constrained_layout=True)
    x = np.arange(4)
    colors = ["#0072B2", "#56B4E9", "#D55E00", "#E69F00"]
    bars = ax.bar(x, s_vals, width=0.50, color=colors, edgecolor="#222222", linewidth=0.5)
    ax.bar_label(bars, labels=[f"{int(v)}" for v in s_vals], padding=2, fontsize=8.0, weight="bold")
    ax.set_xticks(x, ["1:1\nOF", "1:1\nRR", "2:1\nOF", "2:1\nRR"], fontsize=8.0)
    ax.set_ylim(0, 20.5)
    ax.set_ylabel("Sparse G→F P99 (cycles)", fontsize=8.0)
    ax.set_title("W5M quota × ordering RTL (6601–6605)", loc="left", fontsize=8.3, weight="bold", pad=6)
    ax.grid(axis="y", alpha=0.20)
    ax.set_axisbelow(True)
    ax.text(
        0.50,
        0.96,
        "W5M (5/5): I = −1c; Q1 gap +1.6c, Q2 −0.2c\n"
        "W256 (n=20): d₂ = −1 in 7/20 (NOT_CONFIRMED)",
        transform=ax.transAxes,
        fontsize=6.4,
        va="top",
        ha="center",
        bbox=dict(facecolor="#F8F9FA", edgecolor="#CCCCCC", boxstyle="round,pad=0.25"),
    )
    save_figure(fig, "v6-ordering-panel")


def make_capacity_figure(nov_data: dict, cap_data: dict) -> None:
    p0 = {(r["profile"], r["policy"]): r for r in nov_data["arrival_p0_w256"]}
    profiles = ["under", "near", "over"]
    max_lags = [p0[(p, "CGOF (2:1)")]["max_lag_mean"] for p in profiles]
    term_deltas = [p0[(p, "CGOF (2:1)")]["delta_mean"] for p in profiles]

    over_pols = cap_data["summary"]["over"]["policies"]
    under_pols = cap_data["summary"]["under"]["policies"]
    pol_names = ["FAI-inspired", "CGOF(1:1)", "CGOF(2:1)"]
    pol_labels = ["Main", "CGOF (1:1)", "CGOF (2:1)"]

    sp_over = [over_pols[p]["mixed_sparse_gf_p99"][0] for p in pol_names]
    sp_under = [under_pols[p]["mixed_sparse_gf_p99"][0] for p in pol_names]
    for p in pol_names:
        assert len(set(over_pols[p]["mixed_sparse_gf_p99"])) == 1
        assert len(set(under_pols[p]["mixed_sparse_gf_p99"])) == 1

    fig, (ax0, ax1) = plt.subplots(
        1, 2, figsize=(7.05, 2.75), constrained_layout=True
    )
    fig.get_layout_engine().set(w_pad=0.06, wspace=0.08)

    # Panel (a): W256 P0 lag vs terminal Delta C + W5M 20-seed annotation
    xb = np.arange(3)
    b1 = ax0.bar(xb - 0.17, max_lags, width=0.33, color="#0072B2", label="W256 P0 max lag (desc.)")
    b2 = ax0.bar(xb + 0.17, term_deltas, width=0.33, color="#D55E00", label="W256 terminal ΔC (cycles)")
    ax0.bar_label(b1, labels=[f"{v:.2f}" for v in max_lags], padding=2, fontsize=7.4)
    ax0.bar_label(b2, labels=[f"{v:.2f}" for v in term_deltas], padding=2, fontsize=7.4)
    ax0.set_xticks(xb, ["Under\n(offer=0.31)", "Near\n(offer=0.86)", "Over\n(offer=1.15)"], fontsize=7.6)
    ax0.set_ylim(0, 128)
    ax0.set_ylabel("Descriptors / cycles", fontsize=8.0)
    ax0.set_title("(a) CGOF (2:1) lag & absorption (MODEL)", loc="left", fontsize=8.1, weight="bold", pad=6)
    ax0.legend(fontsize=6.6, loc="upper left", frameon=False)
    ax0.grid(axis="y", alpha=0.20)
    ax0.set_axisbelow(True)
    ax0.text(
        0.02,
        0.77,
        "W5M confirm (6201–6220):\n"
        "Under ΔC = 0.00 [0, 0]\n"
        "Over ΔC = +834.25 [820.4, 849.3]\n"
        "Near P0: 1:1 lag 5.00; 20/20 recov.",
        transform=ax0.transAxes,
        fontsize=6.2,
        va="top",
        bbox=dict(facecolor="#F8F9FA", edgecolor="#CCCCCC", boxstyle="round,pad=0.24"),
    )

    # Panel (b): Long W5M 4-window overload & conservation (seeds 8101–8105)
    xp = np.arange(3)
    bu = ax1.bar(xp - 0.18, sp_under, width=0.34, color="#56B4E9", label="Under (4M Heavy, ratio 1.000000)")
    bo = ax1.bar(xp + 0.18, sp_over, width=0.34, color="#E69F00", label="Over (17.5M Heavy, ratio 1.200002)")
    ax1.bar_label(bu, labels=[f"{int(v)}" for v in sp_under], padding=2, fontsize=7.8)
    ax1.bar_label(bo, labels=[f"{int(v)}" for v in sp_over], padding=2, fontsize=7.8, weight="bold")
    ax1.set_xticks(xp, pol_labels, fontsize=8.0)
    ax1.set_ylim(0, 35)
    ax1.set_ylabel("Mixed Sparse G→F P99 (cycles)", fontsize=8.0)
    ax1.set_title("(b) Long W5M conservation (8101–8105)", loc="left", fontsize=8.3, weight="bold", pad=6)
    ax1.legend(fontsize=6.6, loc="upper right", frameon=False)
    ax1.grid(axis="y", alpha=0.20)
    ax1.set_axisbelow(True)
    ax1.text(
        0.98,
        0.74,
        "Over Heavy max wall gap:\n"
        "Main 18–19c | 1:1 11c | 2:1 13–14c\n"
        "Extra Heavy cycles vs Main:\n"
        "mean +0.4c (0–1c) over 3.89M ΔC",
        transform=ax1.transAxes,
        fontsize=6.4,
        va="top",
        ha="right",
        bbox=dict(facecolor="#F8F9FA", edgecolor="#CCCCCC", boxstyle="round,pad=0.24"),
    )

    save_figure(fig, "v6-capacity-slack-panel")


def make_dynamic_figure(nov_data: dict, dyn_data: dict) -> None:
    dyn = {(r["case"], r["policy"]): r for r in nov_data["dynamic_rtl_probe"]}
    labels_c = ["Multi\nD16", "Spread\nD16", "Bursty\nD16", "Bursty\nD8", "Role-sw\nD16"]
    cases_c = ["multi-window", "ready-spread", "ready-bursty", "depth8-bursty", "role-switch"]
    sp_p99 = [dyn[(c, "CGOF (2:1)")]["sparse_gf_p99"] for c in cases_c]
    hv_ga = [dyn[(c, "CGOF (2:1)")]["heavy_ga_p99"] for c in cases_c]
    hv_af = [dyn[(c, "CGOF (2:1)")]["heavy_af_p99"] for c in cases_c]
    hv_gf = [dyn[(c, "CGOF (2:1)")]["heavy_gf_p99"] for c in cases_c]

    contrasts = {c["id"]: c for c in dyn_data["contrasts"]}
    p_ids = ["P1", "P2", "P3"]
    p_labels = [
        "P1: Role-switch\nMain − CGOF(2:1)",
        "P2: Role-switch\n2:1 − 1:1",
        "P3: Multi-window\nMain − CGOF(2:1)",
    ]
    means = [contrasts[pid]["mean_delta"] for pid in p_ids]
    lows = [contrasts[pid]["mean_delta"] - contrasts[pid]["bootstrap"]["low"] for pid in p_ids]
    highs = [contrasts[pid]["bootstrap"]["high"] - contrasts[pid]["mean_delta"] for pid in p_ids]

    fig, (ax0, ax1) = plt.subplots(
        1, 2, figsize=(7.05, 2.75), constrained_layout=True
    )
    fig.get_layout_engine().set(w_pad=0.06, wspace=0.08)

    # Panel (a): seed 7291 RTL probe (all 5 cases, CGOF 2:1)
    xc = np.arange(5) * 1.24
    w = 0.19
    bs = ax0.bar(xc - 1.90 * w, sp_p99, width=w, color="#009E73", label="Sparse G→F P99")
    ba = ax0.bar(xc - 0.63 * w, hv_ga, width=w, color="#E69F00", label="Heavy G→A P99")
    bf = ax0.bar(xc + 0.63 * w, hv_af, width=w, color="#56B4E9", label="Heavy A→F P99")
    bg = ax0.bar(xc + 1.90 * w, hv_gf, width=w, color="#4D4D4D", label="Heavy G→F P99")
    for bars in (bs, ba, bf, bg):
        ax0.bar_label(bars, labels=[f"{int(v)}" for v in bars.datavalues], padding=2, fontsize=5.0)
    ax0.set_xlim(-0.56, xc[-1] + 0.56)
    ax0.set_xticks(xc, labels_c, fontsize=7.3)
    ax0.set_ylim(0, 31)
    ax0.set_ylabel("Per-run nearest-rank P99 (cycles)", fontsize=7.9)
    ax0.set_title("(a) CGOF (2:1) 4-win probe (RTL 7291)", loc="left", fontsize=8.0, weight="bold", pad=6)
    ax0.legend(fontsize=6.4, loc="upper left", ncol=2, frameon=False, columnspacing=0.8)
    ax0.grid(axis="y", alpha=0.20)
    ax0.set_axisbelow(True)

    # Panel (b): 20-seed held-out MODEL_ONLY confirmation (7401–7420)
    xd = np.arange(3)
    bar_colors = ["#0072B2", "#CC79A7", "#0072B2"]
    bd = ax1.bar(xd, means, width=0.44, color=bar_colors, edgecolor="#222222", linewidth=0.5)
    ax1.errorbar(xd, means, yerr=[lows, highs], fmt="none", ecolor="#111111", elinewidth=1.1, capsize=3)
    ax1.axhline(1.0, color="#666666", linestyle="--", linewidth=0.9, label="Pre-registered gate (Δ ≥ 1c)")
    ax1.bar_label(
        bd,
        labels=[f"{m:.1f}c" if m != int(m) else f"{int(m)}c" for m in means],
        padding=4,
        fontsize=8.0,
        weight="bold",
    )
    ax1.set_xticks(xd, p_labels, fontsize=7.3)
    ax1.set_ylim(0, 23.5)
    ax1.set_ylabel("Sparse G→F P99 Δ (cycles)", fontsize=7.9)
    ax1.set_title("(b) Dynamic confirm (MODEL, 7401–7420)", loc="left", fontsize=8.2, weight="bold", pad=6)
    ax1.legend(fontsize=6.5, loc="lower center", bbox_to_anchor=(0.50, 0.14), frameon=False)
    ax1.grid(axis="y", alpha=0.20)
    ax1.set_axisbelow(True)
    ax1.text(
        0.50,
        0.97,
        "20/20 pass P1–P3 (sign p = 9.54e−7, Holm α = 0.05)\n"
        "Main RTL G-EQ anchors: seed 7301 (4/4) & 7401 (2/2)",
        transform=ax1.transAxes,
        fontsize=6.3,
        va="top",
        ha="center",
        bbox=dict(facecolor="#F8F9FA", edgecolor="#CCCCCC", boxstyle="round,pad=0.24"),
    )

    save_figure(fig, "v6-dynamic-probe-panel")


def main() -> None:
    configure_style()
    nov_data = nov02.collect()
    cap_data = json.loads((ROOT / "docs/reviews/capacity-absorption-acceptance-20261107.json").read_text(encoding="utf-8"))
    dyn_data = json.loads((ROOT / "docs/reviews/dynamic-role-switch-v2-confirmation-analysis-20261106.json").read_text(encoding="utf-8"))
    make_ordering_figure(nov_data)
    make_capacity_figure(nov_data, cap_data)
    make_dynamic_figure(nov_data, dyn_data)
    print("Generated v6 figures in", OUT_DIR)


if __name__ == "__main__":
    main()
