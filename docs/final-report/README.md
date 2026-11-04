# ECE 509 final report

## Current accepted revision — October 29, 2026

The latest report is *From Service Classes to Hardware Costs: An RTL Study of CXL-Inspired Switch Scheduling*: **13 pages, 9 figures, 7 tables, 19 references**. It preserves the five-step narrative and adds the completed twenty-seed finite-Heavy RTL confirmation (80 jobs, 40 mixed/isolated pairs) and current-source CGOF replay (30 runs, 60 A/B endpoints). Two new figures show paired seed observations, appropriate confidence intervals, and the separate confirmation/exploration cohorts.

- [Latest PDF](../../output/pdf/cxl-scheduler-revised-20261029.pdf)
- [Editable driver](main-v3.tex) and [manuscript body](sections/hotnets-body-v3.tex)
- [Acceptance record](update-20261029/REVISION_QA.md) and [machine-readable release](update-20261029/revision-release.json)
- [New editable figures](generated/figures/update-20261029/) and [source-bound numerical manifest](generated/update_20261029_manifest.json)
- [Theory and evidence](update-20261029/THEORY_AND_EVIDENCE.md), [current hypothesis status](update-20261029/hypothesis-status.json), and [separate follow-up experiments](update-20261029/FOLLOWUP_EXPERIMENTS.md)

In the confirmed near-load workload, CGOF 1:1 has Sparse run-P99 3 cycles and mean run-maximum Heavy gap 9.45, compared with 4 and 10.85 for 2:1. Every run crosses one classification boundary and retains effective High. The absolute-credit and capacity explanations are organized as testable mechanisms; sustained class adaptation remains a follow-up question.

Use **main-v3.tex** for this release. From the repository root, update only the new evidence products and run their focused checks:

```powershell
python -B docs/final-report/generate_update_20261029.py
python -m pytest -q docs/final-report/test_update_20261029.py
```

From `docs/final-report/`, compile twice (the output directory must exist):

```powershell
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error "-output-directory=../../output/pdf" "-jobname=cxl-scheduler-revised-20261029" main-v3.tex
```

The generator recomputes saved statistics from 241 bound inputs and launches no simulations. Earlier generated products remain accepted, hash-checked artifacts. Historical regeneration commands below require their original frozen evidence; do not refresh old pins to accommodate the evolving diagnosis summary. The PDF and temporary build logs are local ignored artifacts. Preserve the full source directory and evidence archive for reproduction.

## Historical accepted revision — October 28, 2026

**October 28:** *From Service Classes to Hardware Costs: An RTL Study of CXL-Inspired Switch Scheduling*.
The 11-page report follows pooling contention → FAI/Buffer → executable RTL → common measurement → results/applicability. It integrates completed evidence through October 28, including allocation and finite-Heavy diagnosis, production-window RTL and six CGOF area/timing configurations.

- [Accepted PDF](../../output/pdf/cxl-scheduler-revised-20261028.pdf)
- [Editable driver](main-v3.tex) and [manuscript body](sections/hotnets-body-v3.tex)
- [Acceptance record](improvement-20261028/REVISION_QA.md) and [machine-readable release](improvement-20261028/revision-release.json)
- [Five new editable vector figures](generated/figures/improvement/) (SVG/PDF/PNG)
- [Separate hypothesis/experiment protocol](improvement-20261028/HYPOTHESES_AND_EXPERIMENTS.md): H1–H5 remain planned

Open **main-v3.tex** explicitly when selecting the current report. The original main.tex and subsequent historical notes below describe earlier releases. The PDF is a local ignored build artifact; retain the complete source directory for regeneration.

From the repository root, regenerate only the added evidence products with:

```powershell
python -B docs/final-report/generate_revision_v3.py --improvement-only
python -B docs/final-report/generate_revision_figures.py --improvement-only
```

From `docs/final-report/`, run the following PDFLaTeX command twice:

```powershell
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error "-output-directory=../../output/pdf" "-jobname=cxl-scheduler-revised-20261028" main-v3.tex
```

The existing output folder must be present. This release additionally uses the already-installed LaTeX `balance` package. Table/report and figure tests pass 10/10 and 5/5. Compilation and reporting commands do not launch scheduler or EDA experiments. The planning handoff is immutable; current status and output hashes live in the release record.

## Historical report and release notes

English academic LaTeX report, using the supplied first progress report's Letter-sized,
two-column Times layout, numbered sections, booktabs-style tables, and numeric references.
The author line (Jay Chiang; Daniel Chou) follows that PDF. The final title is *From Scheduling
Policies to Hardware Costs: A Comparative RTL Study of CXL Switch Arbitration*. This is a course
report, not a claim of IEEE/ACM publication-template compliance or submission acceptance.

Evidence cutoff: **2026-10-21 Asia/Taipei**. Accepted starting snapshot:
`9141dfe3303d60b2f00747811eee80cb16db7269`.

## Files and editing

- [main.tex](main.tex): editable report driver with the preamble, title, generated numerical data,
  and references.
- [sections/hotnets-body.tex](sections/hotnets-body.tex): six-section course-report body
  (Introduction, Related Work, Design, Implementation, Evaluation, AI Use Acknowledgment).
- [generate_results.py](generate_results.py): standard-library-only data checks and generation of
  numerical tables/PGFPlots coordinates from the six accepted JSON/profile inputs.
- [generated/results.tex](generated/results.tex): generated presentation data, checked into Git
  so the LaTeX editor can compile immediately. Do not hand-edit numerical rows.
- [generated/evidence_manifest.json](generated/evidence_manifest.json): full input file digests,
  evidence snapshot, asserted matrix sizes and energy formula.
- [Final PDF](../../output/pdf/cxl-scheduler-final-report.pdf): local rendered deliverable, ignored
  with build products. Regenerate from source after checkout. PDF generation is separate from
  synthesis or verification; it does not launch SSH, Claude, or RTL tests.

## Literature review artifacts

This is a report-level rapid/narrative review, not a systematic review or a PRISMA submission.
The final matrix covers all 23 external papers cited in the report: 21 were read from PDF full
text and 2 from ACM HTML full text. The two HTML sources use section/figure locators rather than
invented PDF page numbers.

- [lit-review/evidence_matrix_v2.md](lit-review/evidence_matrix_v2.md): canonical evidence matrix,
  exact locators, metrics, platform, limitations and verification notes.
- [lit-review/reading/](lit-review/reading/): four parallel full-text reading records and the
  independent [Gemini 4 Argon critique](lit-review/reading/argon_critique.md).
- [lit-review/search_gap_report.md](lit-review/search_gap_report.md): search and gap synthesis
  supporting the Related Work revision.

Open this directory or `main.tex` in the Codex LaTeX editor to edit and preview. Preserve
the project folder: `main.tex` includes `generated/results.tex` and
`sections/hotnets-body.tex`, so it is not a standalone file.

## Rebuild

From `docs/final-report/` with Python 3 and PDFLaTeX already installed:

```sh
python generate_results.py
mkdir -p ../../output/pdf
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../../output/pdf -jobname=cxl-scheduler-final-report main.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../../output/pdf -jobname=cxl-scheduler-final-report main.tex
```

PowerShell: replace `mkdir -p` with
`New-Item -ItemType Directory -Force ../../output/pdf | Out-Null`.
For MiKTeX, add `--disable-installer` to avoid installing missing packages automatically.
The actual build used this flag. No TeX distribution/package was installed by this report task.
An initially missing local `fancyhdr` dependency was removed by using the standard LaTeX
page-style mechanism; the desktop editor's compiler also compiled the project successfully.
The final course-report layout uses the article class with a 7 in by 9.25 in text block,
10 pt body text, 12 pt leading, and two columns, matching the numerical HotNets 2019 limits.
The obsolete `hotnets19.cls` was not adopted because its copyright and blind-review furniture
do not fit this non-anonymous course report.

Dependencies: article, geometry, fontenc, mathptmx, amsmath, booktabs, graphicx, array,
PGFPlots/TikZ, caption and hyperref. Figures are native editable vector LaTeX/TikZ/PGFPlots,
not screenshots or a draw.io import. The architecture figure is full-width and scaled to 62%
to keep labels inside the six-page layout without collisions; Figure 2 uses three side-by-side
panels, each with its own source-count axis, and Figure 3 uses side-by-side cold-power and N=4
boundary-decomposition panels with external legends.
The original-size architecture floats to a seventh page; the 62% scale is the smallest layout
change that preserves all content and the course page limit.
Tables preserve the printed power precision; derived N16 cold energy uses integer pJ because
the printed total has only three significant figures. Energy includes leakage and is specific
to the measured traffic window. It is not marginal scheduler energy.

The generator's assertions check the complete 9-case matrix, common profile, positive timing
margins, 140 explicit constant-disabled checks, 14 clean equivalence outcomes and negative
control status, complete 27-case cold/3-case boundary power matrices, shared intended-traffic
hashes, ordering and measured fire counts. Pinned canonical JSON digests reject changed evidence
before any generated file is overwritten, independently of whitespace/line endings. Updating
those pins requires a deliberate manuscript/evidence review. These checks do not rerun EDA.

## Source PDF inspection and provenance

The following files are supplied outside the repository in its parent directory. They were
available and inspected during report preparation on 2026-10-21; none is copied into Git.
Historical frozen-spec statements about then-unavailable PDFs are left intact.

| Supplied source | Inspection used | SHA-256 |
| --- | --- | --- |
| `ECE509.pdf` | All five pages rendered/read; format, title, author line, original scope and proposed evaluation | `7703ac42b732f4f1e21aac4536a048a8a97424b400bc45ef070a57345968913a` |
| `FAI-CXL_An_Efficient_Hardware-Accelerated_Fairness-Aware_CXL_Memory_Pool_Management_with_Fine-Grained_Cacheline-Level_Interleaving.pdf` | Title/author/abstract metadata; complete Algorithm 2 page 5 text and rendered page | `817105335c362b8a95b934e852efd8764ef97c19fd88f8b8a760d1cee4c84366` |
| `BLISS.pdf` | Title/authors/report identifier/abstract for related-work framing; no reused numerical baseline | `8b4e74c8d9eba0a0f2973a54deb69b67a8087beede8d1a19ab01bf99db6f6f0c` |

The FAI paper's stored-target assignments and KEEP behavior agree with the approved
supplementary interpretation. Its dispatch statements do not uniquely specify the project's
one-output 10/10 schedule. The final report clearly labels that reconstruction, retains Main
as the primary baseline, and does not silently revise Spec v1.0.

## Evidence boundaries

Use the latest accepted outcomes in [DEVELOPMENT_REPORT](../DEVELOPMENT_REPORT.md),
[STATUS](../STATUS.md), the per-milestone verification reports, and the five PPA/equivalence
JSON datasets. Older dated NOT_RUN/RUNNING statements remain historical checkpoints; they
are not current missing experiments and are not rewritten to invent past completion.

Accepted area/STA is the **entire v2 matrix**, not a mixture of v1/pilots and v2. Supplemental
Main/Algorithm-2 source, original cold-power tooling, and newer supplementary tooling have
distinct recorded revisions. Formality bridges relate current Main RTL to accepted netlists.
Do not add repeated model collections or vector-file comparisons as new RTL coverage.

All power is qualified zero-delay/pre-layout estimation. The N4 boundary sample has 50 times
the natural classification-event density. Cold transient X and FCFS/RR table-range warnings
remain explicit. No Fmax, full-CXL, generalized fairness, physical/multicorner signoff,
Algorithm-2 power or trained N8/16 power result is claimed. Raw commercial artifacts are
ignored, locally retained evidence; copying tracked summaries alone does not archive them.

## Delivery checks

Build/render results, final PDF hash/page count, final-log diagnostics and source/data checks
are recorded in [QA.md](QA.md), including the `agy` Gemini 3.8 Flash / Gemini 4 Argon tool
provenance and the failed DeepSeek attempt. The source and local PDF are both reviewable; further
author editing changes the PDF hash and requires a fresh compile/render check.

The delivered six-page PDF ends the body and AI section on page 5; references fill the rest of
page 5 and page 6. The reproduction/provenance appendix was moved out of the PDF, with its
source paths, commits, evidence locations and rebuild commands retained in this README and
[QA.md](QA.md).

## Approved v3 revision (2026-10-27)

The owner approved `main-v3.tex` and `sections/hotnets-body-v3.tex` as the revision
entry point. This is separate from the historical `main.tex` flow above. The revision
uses the complete498-row accepted matrix, including the full60-run N expansion,
twenty-seed N4 confirmation and nine matched trained-power A/B pairs. It retains
negative Main-versus-RR10 results and the descriptor-slice/pre-layout limitations.

`generate_revision_v3.py` reads hash-pinned accepted local evidence and emits only
`generated/revision_v3_results.tex` and `generated/revision_v3_evidence_manifest.json`.
It preserves the historical generators and outputs. The latter manifest also binds
the six historical source anchors used by `generated/results.tex`. The final PDF
release receipt binds these data to the actual v3 source and rendered PDF.

From this directory:

```powershell
python -B generate_revision_v3.py
python -B -m unittest test_generate_revision_v3
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error -recorder "-output-directory=../../output/pdf" "-jobname=cxl-scheduler-v3-revised-20261027" main-v3.tex
pdflatex --disable-installer -interaction=nonstopmode -halt-on-error -file-line-error -recorder "-output-directory=../../output/pdf" "-jobname=cxl-scheduler-v3-revised-20261027" main-v3.tex
```

See `V3_REVISION_QA.md` for the actual build, visual checks and review disposition;
the historical QA above does not certify this revised PDF. `PAPER_REREVIEW.md` in
`../experiments/revision-20261023/` records the three advisory review roles and
issue dispositions. Their separation is not a claim of external peer review or
independent model-error processes.

Raw archives under ignored `.setup-logs/` and `artifacts/` are required to regenerate
the v3 data; preserve them with this workspace. A clone containing only tracked files
is not the complete experimental archive. Do not infer physical signoff, full CXL
protocol behavior, or DAC performance beyond the measured N4 configurations.
# 2026-10-27 圖形版入口

最新圖形版：`output/pdf/cxl-scheduler-v3-graphical-20261027.pdf`（12 頁、六張結果圖）。
先執行 `python -B docs/final-report/generate_revision_figures.py`，再依既有 v3
指令編譯 `main-v3.tex`，jobname 使用 `cxl-scheduler-v3-graphical-20261027`。
向量 PDF、可編輯 SVG 與逐圖數據位於 `docs/final-report/generated/figures/`；
詳見 [GRAPHICAL_EDITION_QA.md](GRAPHICAL_EDITION_QA.md)。
原九頁交付與 ZIP 保留為歷史版本。

## Report improvement handoff (2026-10-28)

For the next report revision, start with
[the improvement plan](improvement-20261028/IMPROVEMENT_PLAN.md) and load
[agent-handoff.json](improvement-20261028/agent-handoff.json). The plan follows
the owner's five-step narrative and incorporates the October 28 model,
production RTL, and six-configuration CGOF area/STA results. It is a planning
artifact; the current v3 manuscript and PDF have not been rewritten by this task.

[Hypotheses and required experiments](improvement-20261028/HYPOTHESES_AND_EXPERIMENTS.md)
records predictions, controls, supporting and refuting outcomes, and report
integration conditions. Future writing agents should load both documents,
check the handoff's source hashes, and use completed outcomes in their actual
direction. Proposed experiments remain planned until execution evidence exists.
