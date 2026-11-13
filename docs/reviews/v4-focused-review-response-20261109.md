# Response to the v4 focused review (2026-11-09)

Source: `cxl-v4-focused-review.zip`
(SHA-256 `324131a638917672bebc208a6aafb62d015cfc83b4de2a9ad309d9e0fdaac21e`),
review `CXL_V4_SCOPE_FOCUSED_REVIEW_ZH.md`.

## Verdict

The review's direction is correct: the remaining work is text/evidence alignment,
not a new round of RTL, EDA, or a 600-job campaign. The review independently
recomputed the P1--P3 values, the capacity pairs and the power reports, and its
two mandatory findings (P2 direction and the stale power-open sentence) check out
against the stored JSON and PDF.

## Adopted changes

| Review item | Decision | Change |
|---|---|---|
| R1 P2 direction | Accepted | `hotnets-body-v5.tex` now says CGOF (2:1) trails CGOF (1:1) by one cycle; `README_REVIEWERS.txt` now reports `CGOF(2:1) - CGOF(1:1) = +1`. |
| R2 power-open sentence | Accepted | Removed "CGOF's area and timing measurements leave its power comparison open." The power paragraph and Table 7 caption now identify the representative seed 509/A pair. |
| R3(a) ordering tradeoff | Accepted | Ordering is described as quota-dependent: Q2 gains one Sparse cycle without an observed Q2 maximum-gap increase; Q1 has no Sparse gain and a +1.6-cycle maximum-gap increase. |
| R3(b) primary lever | Accepted | Replaced with the narrower statement that the tested quota and ordering controls do not establish a universal ordering advantage. |
| R3(c) overload cost | Accepted | The 1--2.55-cycle gap cost is explicitly limited to the short finite-work overload model; the boundary count is corrected from three to four. |
| R3 seed invariance | Accepted | Replaced the mechanism claim with an observed-endpoint statement; zero-width intervals no longer imply seed independence. |
| R4 scope | Accepted | The conclusions concern scheduler-side dispatch delay and implementation cost; DRAM service time, end-to-end memory latency and application performance are outside the study. |
| Capacity result | Accepted in compact form | Added one sentence: a five-seed long overload gives Sparse P99 27/4/4 at ratio 1.200002. A separate float was not added, to retain the 15-page limit. |

## Not adopted

- No Ramulator/DRAM timing, application slowdown, or CXL protocol-conformance
  experiment. The review agrees these are outside the dispatch-latency scope.
- No new 600-job RTL campaign, extra under/over RTL sweep, extra power corners,
  or APR/SPEF/glitch/silicon measurement.
- No formal starvation bound or full quota-round theorem. The tested controls
  support the conditional claims already in the paper.
- No separate capacity table float. The result is present as a compact sentence
  to keep the accepted 15-page layout; the raw 30-pair manifest and acceptance
  record remain in the review package.

## Verification

- P2 checked against `docs/reviews/dynamic-role-switch-v2-confirmation-analysis-20261106.json`:
  `left=CGOF(2:1)`, `right=CGOF(1:1)`, all 20 deltas `+1`.
- Power values checked against the 12 PrimeTime reports and `matched-comparison.json`.
- Capacity values checked against `docs/reviews/capacity-absorption-acceptance-20261107.json`:
  over-load ratios 1.20000215/1.20000217/1.20000217 and Sparse P99 27/4/4.
- `main-v5.pdf`: 15 pages, 0 undefined references, 0 overfull hbox, one disclosed
  `4.48248pt` overfull vbox unchanged from the prior build.
- Page-level visual check: page 9 (capacity sentence), page 13 (P2 direction),
  page 14 (power/scope/applicability).

## Files changed

- `docs/final-report/sections/hotnets-body-v5.tex`
- `docs/final-report/main-v5.pdf`
- `docs/reviews/report-v5-acceptance-20261108.json`
- `README_REVIEWERS.txt` (review package)
- `V5_CHANGES.md` (review package)
