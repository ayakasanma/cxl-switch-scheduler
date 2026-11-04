# October 29 primary-author handoff

Status: **AUTHOR_SOURCE_FROZEN_FOR_PARENT_INTEGRATION**. Date: 2026-10-29, Asia/Taipei. Role: GPT-6.1 Sol/high, owner-selected primary author. Applied ARS-Codex academic-paper revision workflow and `references/writing_quality_check.md`. This receipt covers author-source work, not final artifact acceptance.

## Exact changed surface

Only these files were written by the author:

1. `docs/final-report/main-v3.tex`: include `generated/update_20261029_results.tex`; update report date, PDF subject and artifact bibliography date to October 29.
2. `docs/final-report/sections/hotnets-body-v3.tex`: targeted changes to abstract; absolute credit-budget explanation in §3.3; cohort table and cohort methods; active-fairness/generation-latency population distinction; current-source replay paragraph and readiness description; two full-width figure/table blocks; replacement of the old seed-6201 finite-RTL result paragraphs; applicability and acknowledgment.
3. `docs/final-report/update-20261029/AUTHOR_HANDOFF.md`: this receipt.

The five section titles and reading order are preserved. Existing historical confirmation, sensitivity, model, allocation and hardware figures remain unchanged. The new finite confirmation replaces use of `\ImprovementProductionRtlTable` with `\UpdateFiniteHeavyTable`; the old macro definition may remain in its historical generator output.

Frozen SHA-256:

| File | SHA-256 |
| --- | --- |
| `main-v3.tex` | `3e5ff313576331f82260410fadb90555de9fd152f67ebe71bf31f74957906366` |
| `sections/hotnets-body-v3.tex` | `bbc27b19483e1bb3e84d7af1e502347a6518d1ac74f7055e9e24c7894b1799aa` |

## Evidence and interpretation accepted into prose

- Repaired finite-Heavy aggregate: `artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/aggregate.json`, SHA-256 `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d`; manifest SHA-256 `2ac939b662c0f3bf970f4861cf01e6dbcb3967b01573c5ac27b8d8371f846407`.
- Current-source CGOF replay: `artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json`, SHA-256 `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097`.
- Read `EVIDENCE_REVIEW.md` findings 1–8 and `THEORY_AND_EVIDENCE.md`; used bound aggregates and raw boundary maps rather than secondary-summary wording. Independently read all forty mixed boundary records: each is `[B_H,H,H,H]`; the reviewer confirms the same for all eighty mixed/isolated jobs. Every source remains effectively High.
- Twenty finite confirmation seeds 529–548 are held out from exploration 509–513 but reuse the original A/B seed identifiers. Eighty executions form forty mixed/isolated pairs. Their scope is near load, N4/D16, five million Heavy requests, one W5M boundary.
- CGOF 1:1/2:1 gives Sparse mean run-P99 3/4, Heavy mean run-max gap 9.45/10.85 and Heavy gap P99 3/3. Paired 2:1-minus-1:1 maximum-gap effect is +1.40 cycles, CI [1.10,1.75]. The text explicitly says 1:1 is ahead on both measured tail metrics; it does not sell this quota contrast as a beneficial Pareto tradeoff.
- Mean mixed/isolated completion ratios 1.000000488/1.000000480 and extra cycles 3.05/3.00 are reported without an equivalence claim. The paired extra-cycle difference is −0.05. Offered rate 0.86 versus ready probability 0.90 is context, with causal saturation/arrival-phase tests still proposed.
- Equal relative source weights are separated from absolute one-/two-credit rounds. The mechanism permits different residual eligibility and refill timing; the text leaves individual gap-event causality to trace decomposition. Conditional share arithmetic remains restricted to fixed classes and sustained backlog.
- Active fairness uses generated/fired counts before drain; Sparse latency includes later completions from the generation cohort. Three mixed jobs retain one Sparse request at cutoff (529 both weights, 542 weight 2). The text states that near-completion conservation limits what demand-share agreement says about short-term allocation.
- Current-source replay is CGOF-only: thirty runs, sixty A/B endpoints. It reproduces 1.10/12.35 on the original twenty seeds, plus descriptive Bernoulli/periodic means 5/20.4 and 17/27 on five exploration seeds. Main comparisons retain earlier provenance. Nominal 75% readiness is distinguished from slightly different realized finite-trace fractions.
- Model Main→CGOF overload findings remain separate from near-load RTL CGOF quota findings. Multi-seed, single-boundary support advances H3 partially; multi-window effective-class adaptation remains proposed.

## Parent integration requirements

The data/figure agent is separately producing:

- `generated/update_20261029_results.tex` with `\UpdateFiniteHeavyTable` and `\UpdatePerformanceTable`.
- `generated/figures/update-20261029/finite-heavy-confirmation.pdf`.
- `generated/figures/update-20261029/readiness-confirmation.pdf`.

Both figure/table blocks are full-width. Parent should verify the final panel content/scales against their captions, generated-table width and float placement. The finite figure caption assumes bootstrap intervals are displayed. No generator, figure, hypothesis or shared-log file was written here.

For an isolated Gemini pass, select only the changed prose surfaces listed above, preserving numbers, cohorts, estimator definitions, hypotheses, TeX paths/macros, labels and citations. Update the acknowledgment only after that pass and final parent acceptance actually finish; it currently records the October 28 review as completed and the October 29 language pass as pending.

Reviewer finding 4 belongs in the parent artifact audit: the launcher was interrupted/resumed and has a stale top-level `STOPPED_OR_FAILED`, while completed per-seed scopes/results pass. The text cites completed evidence and makes no clean-single-launch claim. Exclude the failed unrepaired batch. The manuscript succinctly records the repaired closing-edge generation cohort.

Planning hash audit found 49/52 unchanged files; the changed three are the intended driver/body and the secondary `DIAGNOSIS_SUMMARY.md`. Frozen planning hashes and release records were not updated. The parent owns the new release/QA records.

No simulator, EDA, tests or LaTeX compilation was run by this author, per assignment. Parent still owns generator/test validation, selective language-edit acceptance, compilation, and visual inspection of every final PDF page. No claim of final PDF completion is made in this receipt.
