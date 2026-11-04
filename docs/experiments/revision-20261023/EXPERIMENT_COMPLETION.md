# Declared experiment matrix completion

## Material Passport

- Observed and parent-accepted2026-10-27, after independent evidence review.
- Scope: the owner-approved498-row experiment matrix, not manuscript acceptance.
- Repository HEAD: `99400ded42cc63c3b206bd5d13f51d36344b2689`.
- Manuscript remains unchanged by this execution; separate revision approval is pending.

## Exact coverage

| Group | Accepted rows |
| --- | ---: |
| N4 six-policy confirmation | 120 |
| N8/16 expansion | 60 |
| Trained core robustness | 180 |
| RR quantum | 25 |
| High quota | 15 |
| FIFO depth | 45 |
| Role-switch adaptation | 9 |
| Main-1W causal control | 5 |
| Matched trained power | 9 |
| Selected DAC2 confirmation / robustness | 20 / 10 |
| Total | 498 |

All498 unique planned IDs are PASS. RUNNING, NOT_RUN, FAIL and UNRESOLVED
are zero. The468 unconditional rows and30 conditional DAC rows are complete;
W256 pilots contribute zero matrix rows. The earlier FCFS/N16/seed509 resource
run is included once among the60 expansion rows. Nine power rows comprise18
accepted A/B captures. Historical failures, interrupted transport and recovered
results remain inspectable rather than overwritten.

## Evidence chain

Paths below are relative to the repository. Ignored raw artifacts must be
preserved with the repository; this document alone is not their archive.

- Final index and analysis:
  `.setup-logs/implementation/revision-20261024/power-index/final498-20261027/snapshot/`.
- Index SHA256:
  `1defb1bbebe31948b5a2834e3510bfcda660190a8630732593bb2169c462f668`.
- Writer release SHA256:
  `75399940a90fa0973552e78ee1c64341b47b6b0873fa96dc3e29ac4bfa113771`.
- Independent release:
  `.setup-logs/implementation/revision-20261024/final498-independent-20261027/RELEASE.json`,
  SHA256 `d2f0b08e211a2b9822709641aa8499d2c3aa6918a516ac79f27a59b8600bf2cc`.
- Parent adoption:
  `.setup-logs/implementation/revision-20261024/parent-continuation-20261027T0325/final498-adoption.json`,
  SHA256 `16445cbcbcc10be603e619405fd7c170605c3c0694398a88bb30b2b387f430c4`.

Parent separately inspected the final four-run bundle, recomputed all eight
sparse P99 endpoints, checked zero drain outstanding/backlog and zero avoidable
bubbles, and verified that prior494 accepted rows,485 prior performance records
and the complete power block were unchanged. Independent review found no
concrete findings within this acceptance scope. Source guards cover core39,
DAC53, power33 and539 protected RTL/specification/manuscript files.

## Interpretation and remaining release work

The confirmation, sensitivity, depth, adaptation, robustness, trained-power
and DAC PPA reports retain their own evidence scopes. Full60 N-expansion
numeric analysis and N_EXPANSION_RESULTS.md are independently reviewed and
parent-accepted. The report covers120 endpoints,24 cohorts and8 same-N pairs.
Parent receipt: the same parent-continuation scope, n60-report-adoption.json,
SHA256 `54ab9d38df70a6efdb22cccfc5c14781c8e4751f46109af31130e40e1d05a33f`.

DAC2 improved the prespecified N4 trained sparse-tail confirmation comparison
against Main. This does not establish full producer-demand estimation,
equal-entitlement fairness, an overall policy winner, or DAC benefit at N8/16.
Main's burst-tail regressions against RR10 remain in the accepted results.
Five-seed exploration comparisons have no confirmation confidence intervals.

The proposal in `MANUSCRIPT_REVISION_PACKET.md` is approval material only.
The existing `main.tex` includes the original body, whose area denominator is
already correct. `main-v3.tex` is a separate proposed revision target and is
not silently substituted for that entry point.

After manuscript approval, remaining work is to apply scoped corrections,
bind updated tables/figures and manifest to accepted evidence, compile and
inspect the final PDF, and conduct independent Devil's Advocate, Methodology
and Domain re-review. Matrix completion does not close those paper issues.
PPA and power remain bounded pre-layout TT/25ns evidence, with recorded
disabled checks and qualified static-pin table warnings; no physical signoff
is claimed.
