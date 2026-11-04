# Sealed FIFO-depth sensitivity results

Observed2026-10-25. This records45 already completed RTL depth runs; it is a descriptive exploration report, not a parameter decision or manuscript revision.

## Scope and paired unit

FCFS, RR10 and Main each use actual DUT FIFO depths8,16,32, five exploration seeds509-513 per depth. All runs keep N4, one output, full105 descriptors, ready always, W5,000,000, two actual training windows (10,000,000 cycles), and Main High/Low quota10/10 or RR quantum10. Heavy source0 emits one request per cycle. Sparse sources1-3 use profile A independent1/128 arrivals and profile B eight-request bursts per1024 cycles. Generation-cohort measurements retain later completions/drain in the existing harness.

The unit is one seed/run. Each mean below averages five run-level pooled-sparse generation-to-fire statistics. Mean P99 is not a P99 obtained by merging runs. P99.9 and maximum are descriptive; requests, sources and the two profiles are not independent repetitions. Each setting has11,638 sparse A requests and12,000 sparse B requests across its five runs.

Absolute paired P99 delta is candidate depth minus D16 for the same policy/profile/seed, averaged across five pairs. All90 comparisons verify exact intended trace hash/config, cohort generation counts, and frozen source hashes. All DUT parameters except DEPTH match the same-policy D16 baseline. Default rows are retained with zero delta, not extra independent controls.

The shared legacy intended-traffic metadata carries depth16 at all depths; this labels the canonical traffic generator, not the DUT FIFO capacity. Strict frozen configurations/result params explicitly set and verify DUT DEPTH8/16/32. Equal trace hashes are expected because FIFO capacity does not alter intended arrival generation. Accepted inputs and producer backlog may differ as part of the closed-loop capacity intervention.

Only same five exploration seeds are paired; confirmation seeds529-548 are not substituted. No CI, bootstrap, significance claim, parameter tuning or new jobs are part of this depth analysis.

## Per-configuration descriptive means

Units: cycles. Quantiles and latency means are averaged across five runs. Observed max is the largest sparse waiting time in any of the five runs.

| Policy | Depth | Profile | Mean wait | Mean P50 | Mean P90 | Mean P99 | Mean P99.9 | Observed max | Paired delta P99 vs D16 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FCFS | 8 | A | 8.2004 | 8.00 | 9.00 | 10.00 | 10.40 | 12 | -8.20 |
| FCFS | 8 | B | 15.1837 | 16.00 | 22.00 | 23.40 | 28.80 | 33 | -10.40 |
| FCFS | 16 | A | 16.3921 | 16.00 | 17.00 | 18.20 | 19.40 | 22 | +0.00 |
| FCFS | 16 | B | 23.2989 | 24.00 | 30.00 | 33.80 | 38.60 | 45 | +0.00 |
| FCFS | 32 | A | 32.7694 | 33.00 | 34.00 | 35.20 | 36.40 | 38 | +17.00 |
| FCFS | 32 | B | 39.5290 | 40.00 | 46.00 | 51.60 | 54.80 | 62 | +17.80 |
| RR10 | 8 | A | 5.5979 | 5.40 | 10.00 | 11.00 | 11.60 | 13 | +0.00 |
| RR10 | 8 | B | 9.1693 | 9.00 | 14.20 | 17.20 | 23.60 | 32 | +0.00 |
| RR10 | 16 | A | 5.5979 | 5.40 | 10.00 | 11.00 | 11.60 | 13 | +0.00 |
| RR10 | 16 | B | 9.1693 | 9.00 | 14.20 | 17.20 | 23.60 | 32 | +0.00 |
| RR10 | 32 | A | 5.5979 | 5.40 | 10.00 | 11.00 | 11.60 | 13 | +0.00 |
| RR10 | 32 | B | 9.1693 | 9.00 | 14.20 | 17.20 | 23.60 | 32 | +0.00 |
| MAIN | 8 | A | 5.5353 | 5.80 | 9.80 | 10.00 | 10.20 | 11 | +0.00 |
| MAIN | 8 | B | 9.3077 | 9.00 | 14.20 | 20.60 | 30.60 | 38 | -0.20 |
| MAIN | 16 | A | 5.5296 | 5.80 | 9.60 | 10.00 | 10.00 | 11 | +0.00 |
| MAIN | 16 | B | 9.3243 | 9.00 | 14.20 | 20.80 | 30.80 | 38 | +0.00 |
| MAIN | 32 | A | 5.5296 | 5.80 | 9.60 | 10.00 | 10.00 | 11 | +0.00 |
| MAIN | 32 | B | 9.3243 | 9.00 | 14.20 | 20.80 | 30.80 | 38 | +0.00 |

## Exact per-seed P99 and differences

Vector order:509,510,511,512,513. A negative paired difference is lower waiting.

| Policy | Depth | Profile | Five run-P99 values | Five paired differences vs D16 |
| --- | ---: | --- | --- | --- |
| FCFS | 8 | A | [10, 10, 10, 10, 10] | [-8, -8, -8, -9, -8] |
| FCFS | 8 | B | [24, 23, 25, 22, 23] | [-10, -11, -11, -9, -11] |
| FCFS | 16 | A | [18, 18, 18, 19, 18] | [0, 0, 0, 0, 0] |
| FCFS | 16 | B | [34, 34, 36, 31, 34] | [0, 0, 0, 0, 0] |
| FCFS | 32 | A | [35, 35, 35, 36, 35] | [17, 17, 17, 17, 17] |
| FCFS | 32 | B | [52, 52, 52, 50, 52] | [18, 18, 16, 19, 18] |
| RR10 | 8 | A | [11, 11, 11, 11, 11] | [0, 0, 0, 0, 0] |
| RR10 | 8 | B | [17, 17, 18, 17, 17] | [0, 0, 0, 0, 0] |
| RR10 | 16 | A | [11, 11, 11, 11, 11] | [0, 0, 0, 0, 0] |
| RR10 | 16 | B | [17, 17, 18, 17, 17] | [0, 0, 0, 0, 0] |
| RR10 | 32 | A | [11, 11, 11, 11, 11] | [0, 0, 0, 0, 0] |
| RR10 | 32 | B | [17, 17, 18, 17, 17] | [0, 0, 0, 0, 0] |
| MAIN | 8 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| MAIN | 8 | B | [23, 19, 24, 17, 20] | [-1, 0, 0, 0, 0] |
| MAIN | 16 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| MAIN | 16 | B | [24, 19, 24, 17, 20] | [0, 0, 0, 0, 0] |
| MAIN | 32 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| MAIN | 32 | B | [24, 19, 24, 17, 20] | [0, 0, 0, 0, 0] |

## Stage decomposition

These are averages of each run's pooled-sparse mean latency, not quantiles. Generation-to-acceptance includes producer waiting before FIFO admission; acceptance-to-fire includes accepted FIFO/arbitration waiting. Their means add to the mean generation-to-fire wait up to floating representation.

| Policy | Depth | Profile | Mean generation-to-acceptance | Mean acceptance-to-fire |
| --- | ---: | --- | ---: | ---: |
| FCFS | 8 | A | 0.0000 | 8.2004 |
| FCFS | 8 | B | 3.5000 | 11.6837 |
| FCFS | 16 | A | 0.0000 | 16.3921 |
| FCFS | 16 | B | 3.5000 | 19.7989 |
| FCFS | 32 | A | 0.0000 | 32.7694 |
| FCFS | 32 | B | 3.5000 | 36.0290 |
| RR10 | 8 | A | 0.0000 | 5.5979 |
| RR10 | 8 | B | 3.5000 | 5.6693 |
| RR10 | 16 | A | 0.0000 | 5.5979 |
| RR10 | 16 | B | 3.5000 | 5.6693 |
| RR10 | 32 | A | 0.0000 | 5.5979 |
| RR10 | 32 | B | 3.5000 | 5.6693 |
| MAIN | 8 | A | 0.0000 | 5.5353 |
| MAIN | 8 | B | 3.5000 | 5.8077 |
| MAIN | 16 | A | 0.0000 | 5.5296 |
| MAIN | 16 | B | 3.5000 | 5.8243 |
| MAIN | 32 | A | 0.0000 | 5.5296 |
| MAIN | 32 | B | 3.5000 | 5.8243 |

In these exact sparse cohorts, mean pre-admission waiting is0 in A and3.5 cycles in B for every policy/depth. The FCFS depth effect therefore appears in the accepted-to-fire part of this measured cohort; these observations do not imply the heavy producer has no backlog or that all offered demand is admitted.

## Offered counts, admission history and conservation

The additional retained-count audit checks all45 runs and270 phase boundaries. Per source, generated = accepted + change in producer backlog, and accepted = fired + change in FIFO occupancy. Phase-end values match the recorded FIFO/producer snapshots; after drain, generated = accepted = fired and both FIFO occupancy and producer backlog are zero. Every measured generation cohort completes all generated requests.

`offered` counts per-cycle producer-valid observations, including repeat observations while an offer is held. It is not a count of distinct requests or an independent demand estimate. The audit verifies accepted <= offered <= phase cycles per source and total phase fires <= downstream-ready cycles. All recorded phases have zero avoidable bubbles and100% eligible-ready utilization when opportunities exist. Exact generated/offered/accepted/fired vectors and boundary backlogs are retained in `conservation.json`.

Intended arrivals match; accepted timelines are explicitly **not** assumed equal. For example, relative to D16, training accepted-count changes for the heavy source across the depth intervention include-9,-8 and+16 requests, with the corresponding backlog/FIFO boundary changes. Within each matched policy/seed, final total requests and real non-reset completion cycles are identical at D8/D16/D32 (all45 depth-minus-D16 completion-cycle deltas are0). Thus these observations show no end-to-end throughput benefit from the smaller local FIFO; the FCFS sparse latency change must not be relabeled as increased output throughput. This check includes drain and does not assert identical admission or service schedules within a phase.

## Findings and qualifications

FCFS is sensitive to this depth intervention: A mean run-P99 is10.0/18.2/35.2 at D8/16/32; B is23.4/33.8/51.6. Relative to D16, D8 reduces A by8.2 and B by10.4 cycles, while D32 increases A by17 and B by17.8 cycles. All five same-seed FCFS comparisons move in those directions. A smaller local queue changes admission history and timestamp-ordered contention as well as storage. These runs do not isolate a pure storage-capacity mechanism or justify a general D8 recommendation.

RR10 reports the same sparse quantiles and mean waits across these three depths: A mean run-P99=11, B=17.2. This describes the listed sparse cohorts only; it is not pin-equivalence, absence of heavy backlog, or a bound under other traffic/backpressure.

Main A mean run-P99 remains10; B is20.6/20.8/20.8 at D8/16/32. The D8 B mean paired change is-0.2 cycles, from one seed improving by1 and four ties. Smaller changes in mean/P90/P99.9 do exist even when P99 ties. D32 does not improve the reported Main sparse waiting over D16 in these five runs. No overall policy/depth winner is declared.

The default D16 latency comparison is not merged with confirmation runs or the earlier quantum/quota exploration. Hardware area, timing and power at D8/D32 were not measured here. The result cannot establish an area/latency optimum, fairness target, starvation bound, full CXL-system effect or physical signoff.

## Strict acceptance and reproduction

Depth bundle: `.setup-logs/implementation/revision-20261024/queue-recovery/prepared-20261024T0108Z/runs/core/04-depth/attempt000/`. Strict index accepts45 declared rows, scope/source-before/source-after and both archives. Actual runner counts:45 lint steps,19 traffic unit tests,12 runner unit tests,15 baseline-model unit tests,45 cocotb tests and1 final scope step (94 steps,91 tests). Every reported build/sim/test exit is0; failures/errors/skips/not-run are0. Raw JUnit and matching frozen config/seed/results are checked by the released inspector, not inferred from summary PASS alone.

Common39 source canonical SHA256:

`800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86`.

Source ZIP SHA256:

`46fb690fa2f45d857ec768d0306c54ab2276806803e662b591c2957b15342662`.

Evidence ZIP SHA256:

`d2760702d94a574aa877528e1f8b0ced5241a2b380190b40ccbfa096bf94864d`.

New receipts: `.setup-logs/implementation/revision-20261024/power-index/depth-completion-20261025t1022/`. Reproduce only the local evidence audit/analysis:

```text
python -B .setup-logs/implementation/revision-20261024/power-index/depth-completion-20261025t1022/audit_depth.py
```

The script uses the existing strict index and analysis CLIs, plus the unchanged strict normalizer for per-source/cohort histogram consistency. An independent nearest-rank check and exact Fraction arithmetic verify45 runs,90 profile endpoints,18 complete tables and90 same-seed D16 pairs. `statistics.json` includes exact per-seed P99 deltas, means, sample counts, raw result hashes and paired intended trace hashes. `depth-inspection.json`, `test-exit-summary.json`, `endpoints.json`, source guards and logs preserve detailed checks. The script runs no scheduler simulation, export or remote command. Existing implementation test suites were not rerun because no implementation changes were made.

Fresh combined snapshot: `snapshot-20261025T022343Z/` under this receipt scope. Both strict CLI commands exited0, with exact interpreter/arguments/timestamps in `commands.json` and the snapshot `exits.json`. Inputs explicitly include the accepted cumulative10-case power manifest and the active adaptation bundle, plus every latest existing core/DAC recovery bundle and the accepted N16 resource row. Old interrupted/superseded attempts are retained in `history.json`.

**246 PASS /9 RUNNING /243 NOT_RUN /0 FAIL or UNRESOLVED**, total498. All45 depth rows are newly accepted. Adaptation9 remains RUNNING and is not promoted from raw steps. Accepted power is5/9 paired rows; conditional contribution30; W256 contribution0. RUNNING counts declared jobs, not worker processes.

Index SHA256 `8e5d436695ab9e461ee4adbff304cca3ae9f90577d4ec8e4f6e7f85e77368a31`.

Frozen index/test/EVIDENCE_INDEX and source39/53/33/protected539 match before/after. Only this new depth report is a tracked write. No manuscript, frozen source, accepted receipt, older report, parameter or running job is changed. Pending adaptation/robustness/N expansion/power work remains outside these conclusions.

The separate `check_conservation.py` local receipt checker rehashes the already inspected45 raw results and verifies the count/boundary equations above without another index run, traffic replay or simulation. Both local scripts and their exit0 logs are retained for parent review.
