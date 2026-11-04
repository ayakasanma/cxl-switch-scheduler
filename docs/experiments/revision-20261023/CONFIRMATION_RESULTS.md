# N4 trained confirmation checkpoint

Observed2026-10-25. This is an experiment record, not a manuscript revision.
All values below are actual RTL simulation results, distinct from the earlier
MODEL_ONLY screening. The full498-row experiment matrix is now accepted; manuscript revision remains pending.

## Boundary and statistical unit

N4, D16, single output, ready always, full105 descriptors, W5,000,000,
two actual training windows, frozen parameters, confirmation seeds529-548.
Each seed/run contributes one pooled sparse generation-to-fire P99 for each
profile. A and B remain separate; sources and requests are not independent
replicates. Values are means of20 run-P99s in cycles, not P99s of merged runs.

| Policy | Trained A | Trained B |
| --- | ---: | ---: |
| FCFS | 18.10 | 33.45 |
| RR1 | 2.00 | 16.65 |
| RR10 | 11.00 | 17.70 |
| Main | 10.00 | 21.05 |
| Algorithm-2 reconstruction | 10.00 | 21.35 |
| BLISS-inspired descriptor baseline | 1.15 | 33.00 |
| Main-DAC2 | 1.10 | 12.35 |

Core120 runs, Main-1W five exploration runs, DAC20 confirmation runs and
DAC10 robustness runs have completed scope validation. Main-1W exploration
seeds are not pooled with Algorithm-2 confirmation seeds to infer equivalence.
Its declared quota10/10 model pin-equivalence remains a separate finding.

## Prespecified paired comparisons

Delta is candidate minus baseline; negative means lower waiting. Intervals
use10,000 paired seed bootstrap resamples, RNG20261023, the fixed percentile
convention, and complete20-seed cohorts only. They describe this synthetic
generator and configuration.

| Baseline | Candidate | Profile | Mean delta | 95% interval | Improved seeds |
| --- | --- | --- | ---: | --- | ---: |
| FCFS | Main | A | -8.10 | [-8.25, -8.00] | 20/20 |
| FCFS | Main | B | -12.40 | [-13.25, -11.55] | 20/20 |
| RR10 | Main | A | -1.00 | [-1.00, -1.00] | 20/20 |
| RR10 | Main | B | +3.35 | [+2.25, +4.45] | 1/20 |
| Main | Main-DAC2 | A | -8.90 | [-9.00, -8.75] | 20/20 |
| Main | Main-DAC2 | B | -8.70 | [-9.50, -7.90] | 20/20 |

The new seeds retain Main's trained-B disadvantage relative to RR10.
Main-DAC2's sparse-tail improvement survives this confirmation cohort.
Neither observation establishes an overall winner, system-level CXL benefit,
or equal-entitlement fairness. DAC uses active-source2:1 weights and changes
the allocation target; it does not estimate all producer demand.

Parent's additional confirmation-phase fire-count check finds a maximum
Main-minus-DAC2 heavy-service fraction of0.001953125 percentage points across
the40 seed/profile pairs, below the declared0.01 percentage-point guard.
Both policies report zero avoidable bubbles in these phases. This check
describes phase service counts, not full producer demand or saturated
weighted-share compliance. Receipt:
`.setup-logs/implementation/revision-20261024/parent-continuation-20261025T0410/heavy-share-check.json`.

## Evidence and independent arithmetic

Repository-relative evidence:

- Core: `.setup-logs/implementation/revision-20261024/queue-recovery/prepared-20261024T0108Z/runs/core/00-n4-confirmation/attempt001/`
- DAC: the same recovery root, `runs/dac/01-insight-confirmation/attempt001/`
- Strict source/archive/result inspection and analysis:
  `.setup-logs/implementation/revision-20261024/power-index/continuation-20261025/sealed-snapshot-20261024T163321Z/`
- Parent independently recomputed nearest-rank P99 from all120 core result
  histograms and all20 DAC histograms, checked exact Main/DAC intended trace
  pairing, and reproduced all six intervals:
  `.setup-logs/implementation/revision-20261024/parent-continuation-20261025T0028/core-independent-arithmetic.json`
  and `dac-independent-arithmetic.json`.

The first sealed index had a reporting defect: its aggregate
`matrix_contribution_from_insight` is hardcoded0 although its individual
conditional groups correctly accept30 rows and the total158 is correct.
That snapshot is preserved. The minimal reporting correction now counts
accepted conditional rows, with37 index tests and20 analysis tests PASS;
parent independently repeated37 index tests. Corrected snapshot:
the same index root,
`conditional-count-fix/snapshot-20261024T163817Z/`.
It accepts173/498 rows, including the newly sealed15 High-quota runs,
and correctly reports30 insight rows. This correction does not alter
simulation sources, histograms or paired results.

## Remaining closure work (updated2026-10-27)

The10 DAC backpressure runs and the matching180 core robustness runs are now
sealed and strictly accepted. Paired backpressure comparisons use exact
seed/configuration/arrival traces; the five exploration seeds are descriptive,
without confidence intervals. High-quota,
RR quantum, depth and adaptation groups are now strictly accepted and reported
separately. N expansion has all60 exact rows sealed and parent-accepted; N_EXPANSION_RESULTS.md and its full60 descriptive analysis are independently reviewed and parent-accepted. The final FCFS/N16 group has four PASS runs,12 PASS steps and50 tests, zero failures/errors/skips. The independently reviewed robustness report is
ROBUSTNESS_RESULTS.md; parent adoption is recorded in
parent-continuation-20261026T1600/robustness-report-adoption.json.

Matched trained power now has18 strictly accepted captures/nine complete A/B
rows, separate from the historical cold and boundary-focused activity.
Final index: power-index/index-detached-final4-20261026t0912/snapshot/index,
under ignored revision-20261024 evidence. Parent acceptance:
parent-continuation-20261026T0906/index-final18-adoption.json.
Original transport failures and recovered actual EDA exits remain distinct.
Qualified static-pin table-domain warnings are retained. The full study matrix
is498PASS/0RUNNING/0NOT_RUN/0FAIL/0UNRESOLVED.
The final snapshot is power-index/final498-20261027/snapshot; parent adoption
after independent review is parent-continuation-20261027T0325/final498-adoption.json.
Physical signoff, approved manuscript edits, final PDF QA and independent
post-revision review have not been performed.
