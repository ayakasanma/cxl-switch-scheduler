# V2 academic draft and language-polish handoff

Date: 2026-10-22 (Asia/Taipei).

## Deliverable

`main-v2-sol.pdf` contains six pages of body, including the abstract and AI
acknowledgment, followed by one separate page of references. The manuscript uses
10pt text, two columns, Letter paper, and the established report preamble.
Its title is unchanged. Twenty-one cited references are retained from the existing
bibliography. The v2 narrative connects service differentiation to its complete
hardware cost, foregrounding the accepted production RTL findings.

New authoring files:

- `main-v2-sol.tex`: entry point, bibliography, and separate reference-page break.
- `sections/hotnets-body-v2-sol.tex`: complete English academic manuscript.
- `generate_hog_sparse_results.py`: standard-library-only deterministic generator.
- `generated/hog_sparse_results.tex`: generated five-seed plot data and text values.
- `generated/hog_sparse_figure.tex`: native four-panel PGFPlots result figure.
- `generated/hardware_cost_v2_sol.tex`: area, timing, and cold-power figure.
- `generated/architecture-v2-sol.tex`: preserved architecture drawing, enlarged
  from the existing 0.62-textwidth placement to 0.96 textwidth.
- `V2_SOL_HANDOFF.md`: this record.

Build and inspection outputs are new files under this same report directory:
`main-v2-sol.pdf`, its `.aux/.log/.out` companions, `build-v2-sol-*.txt`, and
`generated/v2-sol-preview/` (page renders, contact sheet, copyediting diagnostics,
and `build-check.json`). Existing sources and experimental artifacts are read-only.
An entry/final byte comparison confirms all 188 pre-existing report/literature
files retain their original hashes, including the pre-existing dirty files.

## Evidence and interpretation

The manuscript integrates `docs/performance/HOG_SPARSE_RESULTS_2026-10-22.md`,
its audit, CSV records, source/execution record, and linked raw metrics.
The generator checks all 15 raw metric SHA-256 digests against the accepted audit,
the exact production matrix, two real W5M windows per run, complete sparse cohorts,
empty final pending populations, matched external traces, matching FCFS/Main cold
pin digests, all 30 full-capacity intervals, and each paired percentage against its
per-seed P99 endpoints. It cross-checks the CSV means against the accepted JSON
summaries before writing v2 data.

Headline results are 15/15 production RTL PASS with independent audit PASS,
45.03%/38.64% mean paired P99 reductions against FCFS in A/B, 9.09% improvement
and 20.78% regression against RR10, and 1.000000 transfer/cycle throughout measured
intervals. These are five-run descriptive results at N4. The text explains
work conservation, service-domain separation, empty-High quota relinquishment,
and the burst competition introduced by class aggregation. The latter is framed
as a mechanism consistent with the observations, preserving its inference status.

Panels (a,b) use equal-weight run summaries and asymmetric minimum-to-maximum
whiskers. Panel (c) shows individual paired seeds and their mean percentage
reductions. The percentages are averaged per matched seed, not computed as ratios
of mean P99s. Panel (d) shows heavy service against total capacity, with a zero
baseline and no secondary axis. All legends are outside the data areas and above
panel titles. Source-count plots have independent labeled axes and units.

Accepted PPA/equivalence data are reused through the existing read-only
`generated/results.tex`. All six frozen evidence/profile canonical digests in
`generate_results.py` were independently checked without invoking its writer.
The checks confirm nine positive setup/hold closures, 14 scoped equivalence pairs,
and the 92.40--98.63% FIFO-area range. The report preserves the original pre-layout
constraints and cold-power activity assumptions. HOG-SPARSE introduces latency
and service evidence, not a new power measurement.

## Build and checks

From `docs/final-report`:

```powershell
python -B generate_hog_sparse_results.py
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error main-v2-sol.tex
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error main-v2-sol.tex
```

The final two PDFLaTeX passes succeed with package installation disabled.
The PDF is 174,137 bytes; SHA-256:
`b5ceab9c14c0569094c9069edc2145e7a953f09c52de0893568c28efb6efde2d`.
The log contains no LaTeX error, overfull horizontal/vertical box, missing glyph,
undefined reference/citation, duplicate label, or rerun request. Eleven underfull
horizontal-box notices remain, primarily bibliography justification; rendered
pages were reviewed for clipping and overlap. All seven pages were rendered;
the architecture and both result figures were inspected at larger scale.

Repeated generation produces the same v2 TeX. An in-memory mutation setting one
paired reduction to 99% is rejected before any output write. The accepted files
remain unchanged. The AI acknowledgment is 71 words/508 characters versus the
existing 80 words/559 characters.

The ARS acronym checker was run on a derived plain-text body. Its final report is
`generated/v2-sol-preview/acronyms-v2-sol.md`: no findings after explicit allowances
for product names, state labels, and established project names. Coverage remains
partial because the checker declines six definition parses; CXL, RTL, FCFS, FIFO,
HPC, and NoC were manually checked against their expansions in the manuscript.
This advisory report is not a citation or scientific-validity certificate.

## Writing workflow and actual attribution

Guidance read from the installed ARS-Codex academic-paper workflow includes the
draft-writer role, visualization role, writing-quality checklist, and statistical
visualization standards. The PDF skill's render/inspect guidance was also used.
The approved title, scope, evidence, and output configuration supplied by the owner
were carried directly into this drafting task.

This manuscript was written in the current Codex session. The requested `-sol`
filenames are retained as version names; they do not assert an independently
verified runtime model identity. Archived source/execution evidence attributes
the HOG-SPARSE tooling fallback to GPT-6.1 Sol/high. The acknowledgment distinguishes
that contribution, earlier Gemini literature assistance, and the upcoming
Gemini 3.8 Flash language-polish pass. It records no completed polish of this draft.

Owner brief for this version: create new files only; integrate accepted HOG-SPARSE
and existing PPA/equivalence evidence; use achievement-led English academic prose,
six body pages, 10pt and two columns; explain the scheduling mechanism; visualize
mean/P99/paired change/heavy service; preserve the architecture; keep the AI
acknowledgment within its existing length; prepare a compile-ready language-polish
handoff. The chat contains the complete owner prompt and drafting responses.

## Prompt for the subsequent Gemini 3.8 Flash pass

> Polish `main-v2-sol.tex` and `sections/hotnets-body-v2-sol.tex` for precise,
> fluent academic English in an ECE 509 course report. Produce separate new
> `main-v2-flash.tex` and `sections/hotnets-body-v2-flash.tex` files; preserve
> the Sol draft, original report, raw evidence, generators, and numerical figures.
> Keep the fixed title, 10pt two-column format, and six-page body with references
> on separate pages. Lead with achieved results and interpret their mechanisms.
> Preserve all numbers, units, comparison denominators, run/seed counts, scope,
> citation keys, and the distinction between measured findings and mechanistic
> interpretation. In particular, retain the RR10 burst regression and distinguish
> mean paired percentage reduction from a ratio of mean P99s. Preserve cold-power
> assumptions separately from trained-state latency results. Keep acknowledgment
> length at or below 80 words and 559 characters; record your language assistance
> only after it actually occurs. Compile the Flash version twice and inspect
> the seven-page PDF, especially panel titles, legends, axis labels, and the
> final body-page break. Return the polished source/PDF and a brief edit log.
