# Final report delivery checks

Date: 2026-10-22 Asia/Taipei; evidence cutoff: 2026-10-21.
Evidence base: `9141dfe3303d60b2f00747811eee80cb16db7269`.
This is report preparation, not a new RTL/EDA acceptance run or submission approval.

## Delivered rendering

- PDF: `output/pdf/cxl-scheduler-final-report.pdf` (repository-relative; ignored build artifact).
- 6 Letter-size pages, 171,142 bytes; body ends on page 5 and the AI acknowledgment begins on page 6,
  followed by References.
  The former reproduction appendix is no longer part of the PDF.
- SHA-256: `37869D388412FD48BD93FDBE5DAACA7FED9B9AD22400F7929D8D3244BE904AD9`.
- Course layout: 10 pt body, 12 pt leading, two columns, 7 in by 9.25 in text block
  (505.89 pt by 668.50 pt), with 24 pt column separation.
- Standalone MiKTeX PDFLaTeX 25.12: final two passes exit 0 with package installer disabled.
- Final log: no LaTeX/package error, undefined citation/reference, required rerun, missing glyph,
  underfull vertical box, table/figure overflow, or `Overfull \hbox`. Sixteen underfull
  horizontal-box notices remain; their paragraphs were visually reviewed, with no
  clipping/overlap. No warning suppression was added to pass a check.
  MiKTeX's update reminder is an environment notice; no update was run.
- Nine font subsets: all embedded Type 1; no bitmap or Type 3 font in the delivered PDF.
- Final PDF rendered with Poppler at 300 dpi for the figure pages and inspected in color and
  grayscale. Figure 1 is a full-width editable TikZ block diagram with an explicit synthesized
  boundary, descriptor layout, fire feedback path and separate testbench-only region; it is
  scaled to 62% to preserve the six-page limit without clipping or label collisions. Figure 2
  has three side-by-side PGFPlots panels with independent `Sources N` axes, a horizontal legend
  above the panels, and one y-axis title; Figure 3 has two side-by-side power panels with their
  legends in plot whitespace and no shared-axis title. Marker and line styles remain
  distinguishable in grayscale. No unreadable glyphs, clipped objects, overlapped text, or
  orphaned near-empty page remains.

The literature pass used `agy` Gemini 3.8 Flash for four parallel full-text reading groups and
Gemini 4 Argon for a separate gap/claim audit. A DeepSeek attempt failed with a 502 provider error
because tool definitions were unsupported; no DeepSeek output was used.

The first locally exported pass stopped on a missing `fancyhdr.sty` with auto-install disabled.
Standard LaTeX page styles replaced that dependency. The first draft had stretched table text
and awkward float/page breaks; ragged table cells, widow controls and the appendix split fixed
them. These were document-build/layout issues, not scheduler failures. Ignored build logs are
under `output/pdf/`; the final inspected PDF is identified by the digest above.

## Content and data checks

`generate_results.py` passes on the frozen accepted inputs. It verifies canonical JSON digests
(including the common frozen profile), complete primary/power matrices, positive timing margins,
equivalence/negative-control outcomes, intended-traffic hashes and relevant counts before writing.
Full byte and canonical digests are in [evidence_manifest.json](generated/evidence_manifest.json).
Regeneration is deterministic: `results.tex` is unchanged on a repeated execution.

An in-memory negative control changed the first primary area by one library unit. Generation
raised `Frozen evidence changed` **before overwriting output**. The accepted JSONs and rendered
table remained untouched. This checks reporting integrity, not additional scheduler correctness.

The report distinguishes:

- Primary v2's nine complete-switch area/STA cases from prior failing pilots and the separate N4
  supplementary synthesis pair; area library units from physical area/NAND2, and slack from Fmax.
- Primary 180 runs, actual production/stress cycles, repeated unit-model collections, model
  exports, file comparisons, gate replay, and 14 specific equivalence pairs.
- Main's frozen previous-effective-class semantics from Algorithm-2's target-buffer semantics;
  paper state operations from the project-defined one-output 10/10 reconstruction.
- Original cold seed509, new cold seed510/511, and the three truly warmed boundary cases.
  All 27 cold results and all three boundary results are sourced from their own accepted JSONs.
- 32,098,500 supplementary gate-checked cycles from 2,100,000 measured activity cycles;
  warmup is checked but not miscounted as measured activity.
- Whole-switch derived energy/transfer (including leakage) from incremental scheduler energy;
  printed N16 power precision from unrounded values; paired behavior from generalized fairness.
- File annotation from state coverage/knownness, model class labels from direct gate probes,
  formal RTL/netlist equivalence from proof against the English Spec, and comparative
  pre-layout timing from physical/multicorner signoff.

The 140 constant-disabled timing checks, FCFS/RR power table-range warnings, cold transient X,
50x event-enriched boundary sample, lack of naturally weighted long-average power, and deferred
Algorithm-2/trained N8/16 power are explicit. No Fmax, full-CXL, application IPC/fairness,
APR/SDF-glitch/CTS/multicorner, numerical coverage-closure or universal PPA claim is introduced.

Source PDF metadata/inspection scope is recorded in [README.md](README.md). All five progress
pages were reviewed; FAI Algorithm 2 page 5 was read and visually inspected. Historical approved
Spec provenance remains unchanged. No copyrighted source PDF, university DB, license, model,
executable, credential or private connection configuration was added.

Final source/link/whitespace/scope checks cover the report project and its documentation links.
Changes are restricted to report source/data-generation files, ignore rules and additive report
links/entries in STATUS, PROGRESS_TRACKER and DEVELOPMENT_REPORT. Existing RTL, Python oracles,
testbenches, frozen Spec, profile and accepted result datasets are unchanged. No SSH, Claude
invocation, new synthesis, or functional regression was necessary for this reporting task.

## Remaining author review

The body and AI section end on page 5, References occupy the rest of page 5 and page 6, and the
delivered PDF has six pages total. Human contribution assignments are not invented. The author
line follows the supplied progress report. New substantive edits require regeneration, two-pass
compilation and another visual check; this PDF hash identifies only the delivered version. A
fresh checkout can rebuild it but does not include ignored raw commercial evidence or
proprietary prerequisites.

## 2026-10-27 approved v3 revision scope

The owner approved `main-v3.tex` and its included v3 body for the498-row evidence
revision. The preceding historical QA entries retain their original scope. Current
v3 build/render/re-review results are recorded separately in `V3_REVISION_QA.md`;
this note alone does not mark the new PDF checked. The original `main.tex` and body
are preserved. No new RTL simulation or remote EDA is launched for manuscript QA.
