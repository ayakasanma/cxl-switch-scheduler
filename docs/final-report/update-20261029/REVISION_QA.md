# October 29 report update: acceptance record

Status: **APPLIED_AND_ACCEPTED** — 2026-10-29, Asia/Taipei. Codex completed evidence, editorial and rendered-PDF acceptance for the requested report update. This is manuscript/artifact acceptance, not a conference submission certification or physical-design signoff.

## Deliverables

- [Accepted PDF](../../../output/pdf/cxl-scheduler-revised-20261029.pdf): 13 pages, 9 figures, 7 tables and 19 cited references.
- [Editable driver](../main-v3.tex) and [body](../sections/hotnets-body-v3.tex).
- [New numerical manifest](../generated/update_20261029_manifest.json): 241 bound inputs; 80 finite-Heavy jobs, 40 pairs, 20 seeds; 30 performance runs and 60 A/B endpoints.
- [Two new editable figures and plot data](../generated/figures/update-20261029/) in SVG/PDF/PNG and JSON.
- [Theory synthesis](THEORY_AND_EVIDENCE.md), [hypothesis status](hypothesis-status.json), [separate follow-up experiments](FOLLOWUP_EXPERIMENTS.md) and [release record](revision-release.json).

## Roles and actual execution

| Role | Identity | Completed scope |
| --- | --- | --- |
| Primary author | GPT-6.1 Sol/high, `01a18625-2ccc-7561-a331-7d1e694ba514` | Manuscript/driver update; [handoff](AUTHOR_HANDOFF.md) |
| Figures and numerical products | GPT-6.1 Sol/high, `01a18625-2915-7f12-a7d3-e09d307be97a` | Versioned generator, two vector figures, tables and five tests |
| Independent evidence review | GPT-6.1 Sol/high, `01a18625-2637-7070-98e9-c4805ad5c8e9` | Raw results, cohorts, source repair, statistics and theory audit; [review](EVIDENCE_REVIEW.md) |
| Language review | agy `gemini-3.8-flash-high`, effort `high` | Isolated changed-prose review, exit 0, 290.34 seconds |
| Coordination and acceptance | Codex parent | Evidence adjudication, selective language integration, theory/protocol/status updates, layout, final tests and hashes |

The agy model was confirmed with `agy models` and the actual stream initialization; conversation `b216a9d4-7f89-4e41-808c-4295fadfb971`. Invocation-local settings preserve global configuration. ARS-Codex academic-paper and writing-quality guidance, the Data visualization workflow and the PDF workflow were used. No ARS certification pipeline is claimed.

Gemini proposed six paragraph changes. The parent accepted P8/P10, accepted P4 with a clearer configuration sentence, used one sentence from P2, retained the original P11, and accepted P14 only after clarifying that the replay reproduces CGOF values rather than adding a new Main comparison. Numerical values, intervals, metrics and cohort identities were retained. The acknowledgment records completed assistance. Prompt, stream, stderr, receipt, frozen author draft and exact adjudications are in `.setup-logs/report-update-20261029/`.

## Evidence acceptance and interpretation

The independent review was reconciled with the final manuscript and theory files:

1. Every repaired finite-Heavy job has one boundary at cycle 4,999,999, H/H/H/H → B_H/H/H/H; every source remains effective High. No effective demotion or multi-window adaptation is inferred.
2. The near-load comparison places 1:1 ahead on both measured tail metrics: Sparse mean run-P99 3 versus 4 cycles and mean run-maximum Heavy wall gap 9.45 versus 10.85. The paired maximum-gap increase is 1.40 [1.10, 1.75] cycles. The older overload Main-to-CGOF comparison remains distinct.
3. Mean mixed-minus-isolated completion is 3.05/3.00 cycles; ratios are 1.000000488/1.000000480. These are measured finite-work effects. Relative weights, absolute credits and completion behavior are explained without an equivalence or application-speed claim.
4. Latency uses the generation cohort including drain completions; fairness uses active-phase counts. Near-completion conservation is not interpreted as time-local allocation fairness.
5. The current-source replay contains CGOF (2:1) alone. It reproduces 1.10/12.35 on the same 20 A/B seeds; Main contrasts retain earlier provenance. The finite-work confirmation reuses those seed labels in a different workload, not as extra independent A/B samples.
6. Bernoulli and periodic readiness exploration uses five seeds and the same nominal 75% availability, with slightly different realized rates. The new figure separates exploration from confirmation and does not connect them as paired cohorts.
7. The repaired closing-edge generation cohort is documented. The failed unrepaired batch is excluded. All completed scopes/results pass although the interrupted/resumed launcher's top-level status is stale; no clean-single-launch claim is made.
8. Public-summary errors were corrected: B_H retains High, fixed-class source-3 percentages round to 24.9962, and the current always-ready B Sparse Jain rounds to 1.000000. Raw experiment artifacts remain unchanged.
9. The model candidate screen is recorded in the evidence review as exploration, including non-improving age-rescue settings and one-seed multi-window model exercises. It is not pooled with RTL confirmation. No new hardware measurements were added; the six accepted CGOF area/STA configurations remain the hardware evidence.

The five-step narrative is retained: pooling/contention → FAI/Buffer → executable RTL and paper differences → common measurement/hardware cost → results/applicability. New mechanism experiments specify falsifiable predictions and required evidence in a separate file. H3 is now partial multi-seed, single-boundary support; H1/H2 retain conditional supported statements, and H4/H5 remain open.

## Version and source boundaries

All 30 outputs in the October 28 release matched at intake. At final acceptance, 28 remain byte-identical; only the shared current driver and body have advanced. All 19 historical generated products in that release remain unchanged. The frozen planning handoff and experiment protocol are preserved. Its pre-revision manuscript hashes and PLAN_COMPLETE_NOT_APPLIED status still describe the planning snapshot.

The old generator rejects the evolved pinned public summary as designed. Its guards were not weakened. The separate October 29 generator recomputes archived statistics, validates unique coverage and raw histograms, and records current-source drift. The final documentation-only AGENTS navigation edit is recorded as allowed non-executable drift; all executable source checks pass. After that edit, new products were regenerated and focused tests rerun.

## Verification and PDF acceptance

- `python -m pytest -q docs/final-report/test_update_20261029.py`: **5/5 PASS** (final pytest time 4.09 seconds). Tests cover raw numerical reconstruction, paired confidence intervals, missing/duplicate pairs, corrupted histogram rejection, exploration scope and editable export hashes.
- All 241 bound input hashes and all six new PDF/SVG/PNG export hashes match. The generator reproduces saved keyed 10,000-resample bootstrap results exactly.
- Two final PDFLaTeX passes exited 0. No undefined citations/references, duplicate labels, missing figures or horizontal overfull boxes remain. All 19 citation keys resolve.
- Rendered all 13 pages at 120 dpi and visually inspected them; enlarged inspection covered the new readiness and finite-work figures, hardware table and final balanced columns. Labels, intervals, units, tables and captions are readable; no clipping, overlap or blank pages was found. Full-width floats were reordered near their relevant result sections.
- One 1.7849 pt vertical-box diagnostic from balancing page 12 remains. That page is visually clear with substantial bottom margin and no clipped content; this is a documented typesetting diagnostic, not a suppressed warning. Normal underfull-box diagnostics remain in justified text and references.
- The ARS acronym checker ran as an advisory on extracted PDF text. Its findings were manually reviewed: core abbreviations are expanded in the manuscript; line wraps/math extraction, state labels, model/product names and bibliography titles account for the reported false or context-specific flags. The check is partial and is not represented as a clean automated acronym certification.

PDF SHA-256: `3cf656cedf4a245b8f48c3198cb3106636ae6bb116c1323d2cd46156e2e07782`.

Local reproducibility records: `.setup-logs/report-update-20261029/` contains tests, build passes, PDF/text checks, author/Gemini comparison, intake hashes and render receipts. Final page renders are in `tmp/pdfs/report-update-20261029-final/`.

## Work not run and remaining scope

This task ran no new scheduler/model simulation, RTL regression, synthesis, STA, power or application experiment. It reused completed source-bound evidence. CGOF power, finite-Heavy adaptation across multiple effective-class changes, calibrated CXL response/byte measurements, application outcomes and physical signoff remain outside the completed evidence. The report does not convert their experiment plans into results.
