#!/usr/bin/env python3
"""Build a one-page visual summary from accepted report evidence."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
OUT = Path(__file__).resolve().parent

POLICIES = ("FCFS", "RR10", "Main")
COLORS = {"FCFS": "#4C78A8", "RR10": "#7A7A7A", "Main": "#D95F02"}

AREA = {
    "FCFS": {4: 103.970, 8: 208.438, 16: 416.886},
    "RR10": {4: 79.047, 8: 158.261, 16: 316.614},
    "Main": {4: 110.090, 8: 219.345, 16: 437.623},
}
SLACK = {
    "FCFS": {4: 13.072, 8: 8.715, 16: 3.892},
    "RR10": {4: 20.519, 8: 19.670, 16: 18.694},
    "Main": {4: 10.496, 8: 5.714, 16: 1.158},
}
POWER = {
    "FCFS": {4: 3.398, 8: 6.727, 16: 13.400},
    "RR10": {4: 2.601, 8: 5.174, 16: 10.300},
    "Main": {4: 3.500, 8: 6.923, 16: 13.800},
}
MEAN = {
    "FCFS": (16.3921, 23.2989),
    "RR10": (5.5979, 9.1693),
    "Main": (5.5296, 9.3243),
}
P99 = {
    "FCFS": (18.2, 33.8),
    "RR10": (11.0, 17.2),
    "Main": (10.0, 20.8),
}
PAIRED = {
    "A/FCFS": 45.0292397661,
    "A/RR10": 9.0909090909,
    "B/FCFS": 38.6401012018,
    "B/RR10": -20.7843137255,
}
PAIRED_SEEDS = (
    (0.88, 44.4444444444), (0.94, 44.4444444444), (1.00, 44.4444444444),
    (1.06, 47.3684210526), (1.12, 44.4444444444),
    (1.88, 9.0909090909), (1.94, 9.0909090909), (2.00, 9.0909090909),
    (2.06, 9.0909090909), (2.12, 9.0909090909),
    (2.88, 29.4117647059), (2.94, 44.1176470588), (3.00, 33.3333333333),
    (3.06, 45.1612903226), (3.12, 41.1764705882),
    (3.88, -41.1764705882), (3.94, -11.7647058824), (4.00, -33.3333333333),
    (4.06, 0.0000000000), (4.12, -17.6470588235),
)
HEAVY = {
    "A": {"FCFS": 97.6728, "RR10": 97.6726, "Main": 97.6724},
    "B": {"FCFS": 97.6576, "RR10": 97.6564, "Main": 97.6564},
}


def read_tex_table(name: str) -> list[list[float]]:
    text = (GENERATED / "hog_sparse_results.tex").read_text(encoding="utf-8")
    found = {}
    lines = text.splitlines()
    cursor = 0
    while cursor < len(lines):
        line = lines[cursor]
        if "pgfplotstableread" not in line:
            cursor += 1
            continue
        if cursor + 1 >= len(lines) or not lines[cursor + 1].startswith("x y lo hi"):
            cursor += 1
            continue
        cursor += 2
        table_lines = []
        while cursor < len(lines) and not lines[cursor].startswith("}"):
            table_lines.append(lines[cursor])
            cursor += 1
        if cursor >= len(lines):
            break
        table_name = lines[cursor].split("}", 1)[1].lstrip("\\")
        if not table_name:
            cursor += 1
            continue
        found[table_name] = "\n".join(table_lines)
        cursor += 1
    if name not in found:
        raise ValueError(f"missing table {name}")
    lines = found[name].splitlines()
    if lines and lines[0].strip() == "x y lo hi":
        lines = lines[1:]
    rows = []
    for line in lines:
        fields = line.replace("\\\\", "").split()
        if fields and fields[0] == "x":
            continue
        if fields:
            rows.append([float(value) for value in fields])
    return rows


def assert_close(actual: float, expected: float, label: str, tol: float = 5e-4) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"{label}: {actual} != {expected}")


def verify_sources() -> None:
    for policy, name in (
        ("FCFS", "HSMeanFCFS"), ("RR10", "HSMeanRR"), ("Main", "HSMeanMain")
    ):
        rows = read_tex_table(name)
        assert_close(rows[0][1], MEAN[policy][0], f"{name} A")
        assert_close(rows[1][1], MEAN[policy][1], f"{name} B")
    for policy, name in (
        ("FCFS", "HSPtailFCFS"), ("RR10", "HSPtailRR"), ("Main", "HSPtailMain")
    ):
        rows = read_tex_table(name)
        assert_close(rows[0][1], P99[policy][0], f"{name} A")
        assert_close(rows[1][1], P99[policy][1], f"{name} B")
    for policy, name in (
        ("FCFS", "HSHeavyFCFS"), ("RR10", "HSHeavyRR"), ("Main", "HSHeavyMain")
    ):
        rows = read_tex_table(name)
        assert_close(rows[0][1] * 100, HEAVY["A"][policy], f"{name} A")
        assert_close(rows[1][1] * 100, HEAVY["B"][policy], f"{name} B")
    paired = read_tex_table("HSPaired")
    for (label, expected), row in zip(PAIRED.items(), paired):
        assert_close(row[1], expected, label)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_text(x: float, y: float, value: str, cls: str = "", anchor: str = "start") -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" class="{cls}" '
        f'text-anchor="{anchor}">{esc(value)}</text>'
    )


def line_chart(
    series: dict[str, dict[int, float]],
    *,
    ymin: float,
    ymax: float,
    yticks: list[float],
    ylabel: str,
    value_fmt: str,
    show_point_labels: bool = False,
) -> str:
    width, height = 520, 248
    left, right, top, bottom = 64, 14, 20, 42
    pw, ph = width - left - right, height - top - bottom
    xs = [4, 8, 16]
    x_pos = {4: left + 30, 8: left + pw / 2, 16: left + pw - 30}

    def sy(v: float) -> float:
        return top + ph * (1 - (v - ymin) / (ymax - ymin))

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for tick in yticks:
        y = sy(tick)
        out.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" class="grid"/>')
        out.append(svg_text(left - 8, y + 4, value_fmt.format(tick), "tick", "end"))
    for x in xs:
        out.append(svg_text(x_pos[x], height - 14, str(x), "tick", "middle"))
    out.append(svg_text(left + pw / 2, height - 1, "Sources N", "axis-label", "middle"))
    out.append(
        f'<text x="13" y="{top + ph/2:.2f}" class="axis-label" text-anchor="middle" '
        f'transform="rotate(-90 13 {top + ph/2:.2f})">{esc(ylabel)}</text>'
    )
    markers = {"FCFS": "square", "RR10": "triangle", "Main": "circle"}
    for policy in POLICIES:
        points = [(x_pos[x], sy(series[policy][x])) for x in xs]
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        dash = ' stroke-dasharray="6 4"' if policy == "RR10" else ""
        out.append(f'<polyline points="{d}" fill="none" stroke="{COLORS[policy]}" stroke-width="2.4"{dash}/>')
        for source, (x, y) in zip(xs, points):
            marker = markers[policy]
            if marker == "square":
                out.append(f'<rect x="{x-4:.2f}" y="{y-4:.2f}" width="8" height="8" fill="{COLORS[policy]}"/>')
            elif marker == "triangle":
                out.append(
                    f'<polygon points="{x:.2f},{y-5:.2f} {x-5:.2f},{y+4:.2f} {x+5:.2f},{y+4:.2f}" '
                    f'fill="white" stroke="{COLORS[policy]}" stroke-width="1.8"/>'
                )
            else:
                out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.3" fill="{COLORS[policy]}"/>')
            if show_point_labels:
                out.append(
                    svg_text(
                        x, y - 9, value_fmt.format(series[policy][source]),
                        f"point {policy}", "middle",
                    )
                )
    out.append("</svg>")
    return "".join(out)


def grouped_bars() -> str:
    width, height = 520, 272
    left, right, top, bottom = 64, 18, 28, 52
    pw, ph = width - left - right, height - top - bottom
    ymax = 36

    def sy(v: float) -> float:
        return top + ph * (1 - v / ymax)

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for tick in (0, 10, 20, 30):
        y = sy(tick)
        out.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" class="grid"/>')
        out.append(svg_text(left - 8, y + 4, str(tick), "tick", "end"))
    centers = [left + pw * .27, left + pw * .73]
    labels = ("A｜單筆", "B｜八筆突發")
    bar_w = 22
    for ci, profile in enumerate(("A", "B")):
        out.append(svg_text(centers[ci], height - 15, labels[ci], "tick strong", "middle"))
        for pi, policy in enumerate(POLICIES):
            value = P99[policy][ci]
            x = centers[ci] + (pi - 1) * (bar_w + 8) - bar_w / 2
            y = sy(value)
            fill = COLORS[policy]
            if policy == "RR10":
                out.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w}" height="{sy(0)-y:.2f}" '
                    f'fill="white" stroke="{fill}" stroke-width="2" stroke-dasharray="5 3"/>'
                )
            else:
                out.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w}" height="{sy(0)-y:.2f}" '
                    f'fill="{fill}" opacity=".88"/>'
                )
            out.append(svg_text(x + bar_w / 2, y - 6, f"{value:.1f}", f"point {policy}", "middle"))
    out.append(svg_text(left + pw / 2, height - 1, "稀疏來源延遲分布", "axis-label", "middle"))
    out.append(
        f'<text x="13" y="{top + ph/2:.2f}" class="axis-label" text-anchor="middle" '
        f'transform="rotate(-90 13 {top + ph/2:.2f})">Generation-to-fire P99（cycles）</text>'
    )
    out.append("</svg>")
    return "".join(out)


def paired_chart() -> str:
    width, height = 520, 300
    left, right, top, bottom = 64, 18, 22, 58
    pw, ph = width - left - right, height - top - bottom
    lo, hi = -55, 60
    labels = ("A / FCFS", "A / RR10", "B / FCFS", "B / RR10")

    def sy(v: float) -> float:
        return top + ph * (1 - (v - lo) / (hi - lo))

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for tick in (-40, -20, 0, 20, 40, 60):
        y = sy(tick)
        cls = "zero" if tick == 0 else "grid"
        out.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" class="{cls}"/>')
        out.append(svg_text(left - 8, y + 4, str(tick), "tick", "end"))
    for x, y in PAIRED_SEEDS:
        cx = left + (x - .5) / 4 * pw
        out.append(f'<circle cx="{cx:.2f}" cy="{sy(y):.2f}" r="3" fill="#8E8E8E" opacity=".6"/>')
    for idx, (label, value) in enumerate(PAIRED.items()):
        cx = left + (idx + .5) / 4 * pw
        color = "#2E8B57" if value >= 0 else "#B33A3A"
        out.append(f'<line x1="{cx:.2f}" y1="{sy(0):.2f}" x2="{cx:.2f}" y2="{sy(value):.2f}" stroke="{color}" stroke-width="3"/>')
        out.append(f'<circle cx="{cx:.2f}" cy="{sy(value):.2f}" r="5" fill="{color}"/>')
        dy = -8 if value >= 0 else 18
        out.append(svg_text(cx, sy(value) + dy, f"{value:+.2f}%", "point", "middle"))
        out.append(svg_text(cx, height - 16, labels[idx], "tick strong", "middle"))
    out.append(svg_text(left + pw / 2, height - 1, "配對百分比變化（正值＝Main 較低 P99）", "axis-label", "middle"))
    out.append(
        f'<text x="13" y="{top + ph/2:.2f}" class="axis-label" text-anchor="middle" '
        f'transform="rotate(-90 13 {top + ph/2:.2f})">P99 reduction（%）</text>'
    )
    out.append("</svg>")
    return "".join(out)


def heavy_chart() -> str:
    width, height = 520, 236
    left, right, top, bottom = 64, 18, 30, 50
    pw, ph = width - left - right, height - top - bottom
    ymin, ymax = 97.0, 97.8

    def sy(v: float) -> float:
        return top + ph * (1 - (v - ymin) / (ymax - ymin))

    out = [f'<svg viewBox="0 0 {width} {height}" class="chart" role="img">']
    for tick in (97.0, 97.2, 97.4, 97.6, 97.8):
        y = sy(tick)
        out.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" class="grid"/>')
        out.append(svg_text(left - 8, y + 4, f"{tick:.1f}%", "tick", "end"))
    centers = [left + pw * .28, left + pw * .72]
    for ci, profile in enumerate(("A", "B")):
        for pi, policy in enumerate(POLICIES):
            value = HEAVY[profile][policy]
            x = centers[ci] + (pi - 1) * 31 - 10
            y = sy(value)
            fill = COLORS[policy]
            if policy == "RR10":
                out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="20" height="{sy(ymin)-y:.2f}" fill="white" stroke="{fill}" stroke-width="1.7" stroke-dasharray="4 2"/>')
            else:
                out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="20" height="{sy(ymin)-y:.2f}" fill="{fill}" opacity=".88"/>')
        out.append(svg_text(centers[ci], height - 18, f"{profile} 組", "tick strong", "middle"))
    out.append(svg_text(left + pw / 2, height - 1, "Heavy host 服務占比（其餘為 sparse）", "axis-label", "middle"))
    out.append(
        f'<text x="13" y="{top + ph/2:.2f}" class="axis-label" text-anchor="middle" '
        f'transform="rotate(-90 13 {top + ph/2:.2f})">Heavy share</text>'
    )
    out.append("</svg>")
    return "".join(out)


def main() -> None:
    verify_sources()
    area_chart = line_chart(
        AREA, ymin=60, ymax=460, yticks=[100, 200, 300, 400],
        ylabel="Complete area（10³ units）", value_fmt="{:.1f}",
        show_point_labels=True,
    )
    slack_chart = line_chart(
        SLACK, ymin=0, ymax=23, yticks=[0, 5, 10, 15, 20],
        ylabel="Setup slack（ns）", value_fmt="{:.2f}",
    )
    power_chart = line_chart(
        POWER, ymin=0, ymax=15, yticks=[0, 5, 10, 15],
        ylabel="Cold power（mW）", value_fmt="{:.2f}",
    )
    p99_chart = grouped_bars()
    pair_chart = paired_chart()
    heavy = heavy_chart()

    source_files = [
        GENERATED / "hog_sparse_results.tex",
        GENERATED / "results.tex",
        ROOT.parent / "performance" / "HOG_SPARSE_RESULTS_2026-10-22.md",
        ROOT.parent / "performance" / "FOLLOWUP_RESULTS_2026-10-22.md",
        ROOT.parent / "performance" / "PLACEMENT_RESULTS_2026-10-22.md",
    ]
    manifest = {
        "generated_by": "make_one_pager.py",
        "source_sha256": {
            str(path.relative_to(ROOT.parents[1])): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_files
        },
        "boundary": (
            "Descriptor-level synthetic RTL evidence; does not establish application IPC, "
            "application slowdown, DRAM behavior, or complete CXL-link bandwidth."
        ),
    }
    (OUT / "one-pager-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    title = "CXL Switch Arbitration：從排程政策到硬體成本"
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<style>
@page {{ size: 13.333in 7.5in; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: 1600px; height: 900px; overflow: hidden; }}
body {{
  font-family: "Microsoft JhengHei", "Noto Sans TC", sans-serif;
  color: #1E2A35; background: #F5F3EE;
}}
.page {{
  width: 1600px; height: 900px; padding: 22px 30px 20px;
  background:
    linear-gradient(135deg, rgba(76,120,168,.08), transparent 34%),
    linear-gradient(315deg, rgba(217,95,2,.06), transparent 30%),
    #F5F3EE;
  display: grid; grid-template-rows: 82px 1fr 34px; gap: 12px;
}}
header {{ display: flex; justify-content: space-between; align-items: flex-start; }}
.eyebrow {{ font-size: 14px; letter-spacing: .14em; color: #65717D; font-weight: 700; }}
h1 {{ margin: 4px 0 0; font-size: 29px; line-height: 1.12; letter-spacing: -.02em; }}
.subtitle {{ margin-top: 5px; font-size: 14px; color: #53606C; }}
.headline {{
  width: 510px; padding: 9px 15px 8px; background: #1E2A35; color: white;
  border-radius: 3px; box-shadow: 6px 6px 0 #D9D2C5;
}}
.headline b {{ display: block; font-size: 19px; line-height: 1.18; color: #FFD59E; }}
.headline span {{ display: block; margin-top: 3px; font-size: 11px; line-height: 1.3; color: #E8EDF1; }}
.grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr);
  gap: 14px; min-height: 0;
}}
.panel {{
  background: rgba(255,255,255,.94); border: 1px solid #D8D2C7;
  box-shadow: 0 2px 0 rgba(30,42,53,.04); padding: 12px 14px 10px;
  display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(200px, .9fr);
  grid-template-rows: auto minmax(0, 1fr);
  gap: 6px 12px; min-height: 0; overflow: hidden;
}}
.panel.wide {{ grid-column: span 2; grid-template-columns: 1.18fr .82fr; }}
.panel-head {{ grid-column: 1 / -1; display: flex; align-items: baseline; gap: 9px; }}
.tag {{
  font: 700 11px/1 "Consolas", monospace; color: white; background: #1E2A35;
  padding: 5px 7px; border-radius: 2px; letter-spacing: .04em;
}}
h2 {{ margin: 0; font-size: 16px; line-height: 1.2; }}
.unit {{ margin-left: auto; color: #7A858F; font-size: 10.5px; }}
.chartwrap {{ min-width: 0; display: flex; align-items: center; overflow: hidden; }}
.chart {{ width: 100%; height: auto; overflow: visible; }}
.grid-line, .grid {{ stroke: #E4E0D8; stroke-width: 1; }}
.zero {{ stroke: #9AA3AA; stroke-width: 1.2; stroke-dasharray: 4 3; }}
.tick {{ font-size: 11.5px; fill: #5C6873; font-family: "Microsoft JhengHei", sans-serif; }}
.tick.strong {{ fill: #25313B; font-weight: 700; }}
.axis-label {{ font-size: 11px; fill: #55616B; font-weight: 600; }}
.point {{ font-size: 10.5px; font-weight: 700; }}
.point.FCFS {{ fill: #315C85; }}
.point.RR10 {{ fill: #5E5E5E; }}
.point.Main {{ fill: #A74701; }}
.note {{
  border-left: 3px solid #D95F02; padding: 0 0 0 11px;
  display: flex; flex-direction: column; justify-content: center; min-width: 0;
  overflow: hidden;
}}
.note strong {{ font-size: 13.5px; line-height: 1.25; margin-bottom: 4px; color: #1E2A35; }}
.note p {{ margin: 0; font-size: 11.5px; line-height: 1.4; color: #4D5964; }}
.note .metric {{ font: 700 17px/1.1 "Consolas", monospace; color: #A74701; margin-bottom: 4px; }}
.legend {{ display: flex; gap: 14px; font-size: 11px; color: #59656F; align-items: center; }}
.legend i {{ display: inline-block; width: 12px; height: 12px; margin-right: 4px; vertical-align: -2px; }}
.legend .sq {{ background: #4C78A8; }}
.legend .tr {{ width: 0; height: 0; background: none; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 11px solid #7A7A7A; }}
.legend .ci {{ background: #D95F02; border-radius: 50%; }}
.footer {{
  display: flex; justify-content: space-between; align-items: flex-end;
  border-top: 1px solid #CFC8BC; padding-top: 9px; font-size: 10.5px; color: #65717D;
}}
.footer b {{ color: #2A3742; }}
.checks {{ display: flex; gap: 12px; }}
.check {{ background: #E8EEE7; color: #355E42; padding: 3px 7px; font-weight: 700; }}
</style>
</head>
<body>
<main class="page">
  <header>
    <div>
      <div class="eyebrow">ECE 509 · ACCEPTED RTL EVIDENCE · 2026-10-22</div>
      <h1>{esc(title)}</h1>
      <div class="subtitle">FCFS × RR10 × Main｜N = 4, 8, 16｜100k-cycle functional, SAED32 PPA, formal equivalence</div>
    </div>
    <div class="headline">
      <b>Main 保護稀疏來源<br>RR10 稱霸突發尾端與面積</b>
      <span>Main 對 FCFS 的 sparse P99 降幅為 45.03%（單筆）／38.64%（突發）；對 RR10 單筆快 1 cycle，但突發慢 3.6 cycles。</span>
    </div>
  </header>

  <section class="grid">
    <article class="panel">
      <div class="panel-head"><span class="tag">01</span><h2>稀疏來源延遲</h2><span class="unit">generation → fire</span></div>
      <div class="chartwrap">{p99_chart}</div>
      <div class="note">
        <div class="metric">−45.03% / −38.64%</div>
        <strong>Main 的主要價值是隔離 heavy host 的干擾</strong>
        <p>單筆 P99 為 10.0 cycles，優於 FCFS 的 18.2；八筆突發為 20.8，仍較 FCFS 的 33.8 低 38.64%。RR10 在突發情境更強。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head"><span class="tag">02</span><h2>配對尾端變化</h2><span class="unit">5 matched seeds</span></div>
      <div class="chartwrap">{pair_chart}</div>
      <div class="note">
        <div class="metric">+9.09% / −20.78%</div>
        <strong>Main 的優勢集中在單筆；突發是結構性弱點</strong>
        <p>Main 對 FCFS 在 A/B 兩組均五個 seed 全勝；對 RR10 則是 A 組全勝、B 組四敗一平。原因是多個 sparse 來源共用一次 High visit。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head"><span class="tag">03</span><h2>輸出容量與 Heavy 服務</h2><span class="unit">30 measured intervals</span></div>
      <div class="chartwrap">{heavy}</div>
      <div class="note">
        <div class="metric">1.000000 transfer/cycle</div>
        <strong>保護 sparse 不等於犧牲總吞吐</strong>
        <p>30 個量測區間全數滿載，沒有 eligible-ready bubble；heavy host 仍取得 97.66–97.67% 服務。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head"><span class="tag">04</span><h2>完整面積</h2><span class="unit">N = 4, 8, 16</span></div>
      <div class="chartwrap">{area_chart}</div>
      <div class="note">
        <div class="metric">+4.97～5.89% vs FCFS</div>
        <strong>Main 的面積代價溫和，但相對 RR10 仍大 38%</strong>
        <p>Main 相對 FCFS 僅增加 4.97–5.89%；RR10 則因省略 arrival metadata、縮小 selector 而勝出。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head"><span class="tag">05</span><h2>Setup Slack</h2><span class="unit">25 ns constraint</span></div>
      <div class="chartwrap">{slack_chart}</div>
      <div class="note">
        <div class="metric">9/9 close timing</div>
        <strong>三者都收斂；Main 在 N=16 只剩 1.158 ns</strong>
        <p>RR10 時序餘裕最大；Main 的 critical path 從 FIFO read pointer 延伸到 class-state update。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head"><span class="tag">06</span><h2>Cold-start 功耗</h2><span class="unit">3 seeds / mapping</span></div>
      <div class="chartwrap">{power_chart}</div>
      <div class="note">
        <div class="metric">RR10 &lt; FCFS &lt; Main</div>
        <strong>功耗排序與面積一致，差距隨 fan-in 放大</strong>
        <p>N=4 時 3.500 對 2.601 mW；N=16 時 13.8 對 10.3 mW。此為獨立 cold activity trace 的敏感度。</p>
      </div>
    </article>

    <article class="panel wide">
      <div class="panel-head"><span class="tag">07</span><h2>硬體成本光譜與研究結論</h2><span class="unit">same RTL boundary · SAED32 RVT · TT / 0.78 V / 25 °C</span></div>
      <div class="chartwrap" style="display:block">
        <div style="display:flex;gap:8px;align-items:center;margin:5px 0 12px">
          <span class="legend"><i class="sq"></i>FCFS</span>
          <span class="legend"><i class="tr"></i>RR10</span>
          <span class="legend"><i class="ci"></i>Main</span>
          <span style="margin-left:auto;font-size:10.5px;color:#65717D">逐項比較；不畫內插曲線</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
          <div style="background:#EAF0F6;padding:12px 14px;border-top:3px solid #4C78A8">
            <div style="font-size:11px;color:#65717D;letter-spacing:.08em">FCFS</div>
            <div style="font-size:22px;font-weight:700;margin:4px 0">公平性基準</div>
            <div style="font-size:12px;line-height:1.45;color:#4D5964">面積小於 Main、邏輯最簡單；但 sparse 必須等待 heavy 的前方隊列，P99 最差。</div>
          </div>
          <div style="background:#EFEFEF;padding:12px 14px;border-top:3px solid #7A7A7A">
            <div style="font-size:11px;color:#65717D;letter-spacing:.08em">RR10</div>
            <div style="font-size:22px;font-weight:700;margin:4px 0">面積與突發尾端贏家</div>
            <div style="font-size:12px;line-height:1.45;color:#4D5964">per-source quantum 避免 aggregation；面積少 38%、burst P99 低 3.6 cycles，是此 boundary 的整體贏家。</div>
          </div>
          <div style="background:#FBEEE4;padding:12px 14px;border-top:3px solid #D95F02">
            <div style="font-size:11px;color:#65717D;letter-spacing:.08em">Main</div>
            <div style="font-size:22px;font-weight:700;margin:4px 0">單筆保護與可解釋性</div>
            <div style="font-size:12px;line-height:1.45;color:#4D5964">以 4.97–5.89% 面積換取 45.03% sparse P99 降幅；Main-SQ 針對 burst aggregation。</div>
          </div>
        </div>
      </div>
      <div class="note" style="border-left-color:#2E8B57">
        <div class="metric" style="color:#2E8B57">14 / 14 PASS</div>
        <strong>結果不是只有平均值：設計也通過實作驗證</strong>
        <p>九個 mapping 全在 25 ns 收斂；14/14 equivalence、180/180 primary、42/42 follow-up、15/15 HOG-SPARSE、42/42 placement 全通過。</p>
      </div>
    </article>

    <article class="panel">
      <div class="panel-head"><span class="tag">08</span><h2>研究判讀</h2><span class="unit">bounded claim</span></div>
      <div style="grid-column:1/-1;display:flex;flex-direction:column;justify-content:center;gap:6px;padding:2px 4px">
        <div style="display:flex;align-items:baseline;gap:10px">
          <span style="font:700 31px/1 Consolas,monospace;color:#D95F02">45%</span>
          <span style="font-size:13px;line-height:1.35"><b>sparse P99 降幅</b><br><span style="color:#65717D">相對 FCFS，單筆；突發為 38.64%</span></span>
        </div>
        <div style="display:flex;align-items:baseline;gap:10px">
          <span style="font:700 31px/1 Consolas,monospace;color:#7A7A7A">−3.6</span>
          <span style="font-size:13px;line-height:1.35"><b>burst P99 差距</b><br><span style="color:#65717D">Main 相對 RR10，單位 cycles</span></span>
        </div>
        <div style="display:flex;align-items:baseline;gap:10px">
          <span style="font:700 31px/1 Consolas,monospace;color:#355E42">1.000000</span>
          <span style="font-size:13px;line-height:1.35"><b>transfer / cycle</b><br><span style="color:#65717D">30/30 measured intervals</span></span>
        </div>
        <p style="margin:1px 0 0;font-size:10.5px;line-height:1.3;color:#65717D">下一步：Main-SQ 切分 per-source sub-quota；Main-PW 加速分類；Main-BQ 保留 unused visit。均為待量測 hypothesis。</p>
      </div>
    </article>
  </section>

  <footer class="footer">
    <div><b>Boundary:</b> descriptor-level synthetic RTL evidence；不主張 application IPC、application slowdown、DRAM 行為或完整 CXL-link bandwidth。</div>
    <div class="checks"><span class="check">180/180 primary</span><span class="check">42/42 follow-up</span><span class="check">15/15 HOG</span><span class="check">42/42 placement</span></div>
  </footer>
</main>
</body>
</html>
"""
    (OUT / "one-pager.html").write_text(page, encoding="utf-8")
    print(OUT / "one-pager.html")


if __name__ == "__main__":
    main()
