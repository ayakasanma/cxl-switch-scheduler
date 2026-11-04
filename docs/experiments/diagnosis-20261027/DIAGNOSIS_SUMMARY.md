# Diagnosis Summary

Date: 2026-10-30 Asia/Taipei.

This note separates three evidence tiers. It is the public summary for the
measurement and diagnosis study.

| Tier | What it contains | What it does not contain |
| --- | --- | --- |
| `MODEL_ONLY` | Frozen W5M model runs for fairness, quota/order controls, and finite Heavy work | RTL or application behavior |
| `SCHEDULER_RTL` | Current-source 30-run/60-endpoint performance confirmation, 20-seed held-out single-window finite-Heavy confirmation, single-seed four-window dynamic probe, accepted endpoint analysis, W256 quota checks, and scoped synthesis/STA/equivalence | Completed memory bytes, CXL response latency, or application slowdown |
| `REAL_CXL/APPLICATION` | Not run | All end-to-end claims |

## Frozen evidence

| Evidence | Result | Manifest / source digest / run ID |
| --- | --- | --- |
| Equal-demand confirmation, seeds 6201-6220 | `PASS`, 180/180 jobs, 0 failures, source stable | `dd4ccc8fc7c0861483dacba976b9933c4d7d8634ab28df2f89d8cb7d40509cde` |
| Fixed-class confirmation, seeds 6201-6220 | `PASS`, 100/100 jobs, 0 failures, source stable | `739a6704972d5c2c969157bea27b3360d90a54e0699ffc67738ffb9cbea78bea` |
| Finite-Heavy confirmation, seeds 6201-6220 | `PASS`, 300/300 jobs, 0 failures, source stable | `1f67b0a09ffccd8ccff0f9f1550edb871c8b2f9f040bc72dd1972a803360e84d` |
| Accepted scheduler RTL endpoint analysis | 960 accepted endpoints; scheduler-boundary only | `89170cfbe0bb449c25ebbe782203b1695550b7b6bb9e467bae8d6bb00b483061` |
| Common-demand production RTL, seed 6201, three W5M windows | `PASS`, two quota settings, 0 failures, source stable | `20261027T203657Z_1135` |
| Finite-Heavy production RTL, seed 6201, mixed/isolated x two quota settings | `PASS`, four jobs, two pairs, source stable | `20261027T195414Z_1179` |
| Complete CGOF correctness matrix | `PASS`, 152 steps, 463 tests, zero failures; model unit tests 17/17 | `20261027T222326Z_1164` |
| CGOF (2:1), N4/D16/W5M synthesis/STA and mapped equivalence | DC/PT/Formality exit 0; 9126 equivalent compare points; see scoped results below | `cgof-ppa-dcpt-20261028T0723`, `cgof-ppa-formal-20261028T0727` |
| Current-source model screen | `PASS`; 58 fresh HOG runs plus 8 feedback reports, 275 independent bindings | `e0b4925c1f03b9c05202c8b8c6e2d34359308a48db0711a6236609e341204379` |
| Current-source performance confirmation | `PASS`; 30 W5M runs, 60 cohort endpoints, zero failures; documentation-only `AGENTS.md` source drift accepted | `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097` |
| W256 quota pilot | `PASS`; 5 steps, 43 tests, no failures/errors/skips; 209,699 real non-reset cycles | `pilot-cgof-seed509-w256-current-20261028` |
| Five-seed finite-Heavy RTL diagnosis | `PASS`; 10 mixed/isolated quota pairs, conservation and Heavy completion checked | `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097` |
| 20-seed held-out finite-Heavy RTL confirmation, seeds 529-548 | `PASS`; 80 results, 40 mixed/isolated pairs, stable source, conservation and all scopes checked; 10,000-replicate bootstrap | `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d` |
| Dynamic W256 model screen, seeds 6101-6105 | `MODEL_ONLY PASS`; 90 mixed/isolated pairs; D8/D32 screened before RTL selection | `b89a5b0b6543840b83916550590e446e5cf03a0a5335c3d5f26d7ff6b364b2e3` |
| Dynamic W5M production probe, seed 7291 | `SCHEDULER_RTL PASS (single-seed)`; five cases, 20 results, 10 mixed/isolated pairs; four actual active classifier boundaries in every result; no confidence interval | `e8a398b18348a99a3a20fc89e1d0086b5c75b31db093b9e1e9ebecbd76d649e8` |

The three confirmation manifests were verified independently with
`scripts/run_diagnosis.py --verify-manifest`. The summaries report
`source_stable=true`. Some comparison records are marked `PARTIAL` because a
weighted or quota metric is unavailable in that scenario; the endpoint
measurements themselves are complete.

The current aggregate is
`artifacts/implementation/cgof-rtl-diagnosis/aggregate-current-20261029.json`;
its SHA-256 is
`da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097`.

The held-out finite-Heavy confirmation aggregate is
`artifacts/implementation/cgof-rtl-diagnosis/confirmation-finite-heavy-fixed-20261029/aggregate.json`;
its SHA-256 is
`0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d`.
It binds the 80 confirmation results to one stable source variant and keeps
the earlier five-seed exploration data separate.

## Fairness

### Equal demand, continuous backlog

All non-weighted policies converge to the same equal-share endpoint. WRR and
IWRR deliberately produce a 2:1 allocation, so their raw Jain is not an
unfairness verdict. Their weighted Jain and weighted allocation error are the
appropriate checks.

| Policy | Service shares L/H/H/H | Raw Jain | Demand-share L1 | Weighted Jain | Weighted L1 |
| --- | --- | ---: | ---: | ---: | ---: |
| FAI-inspired | 25.0013 / 25.0013 / 25.0013 / 24.9962 | 0.999999992 | 7.50e-5 | N/A | N/A |
| CGOF (1:1) | 25.0013 / 25.0013 / 25.0013 / 24.9962 | 0.999999992 | 7.50e-5 | N/A | N/A |
| CGOF (2:1) | 25.0013 / 25.0013 / 25.0013 / 24.9962 | 0.999999992 | 7.50e-5 | N/A | N/A |
| WRR 2:1 | 40.0020 / 20.0010 / 20.0010 / 19.9960 | 0.892832 | 0.300040 | 0.999999988 | 8.00e-5 |
| IWRR 2:1 | 39.9970 / 20.0010 / 20.0010 / 20.0010 | 0.892895 | 0.299940 | 0.999999997 | 6.00e-5 |

FAI-inspired, FCFS, RR10, and both CGOF quota settings have the same
equal-demand endpoint. The oldest-first versus eligible-round-robin comparison
is exactly zero under continuous backlog. The 20 seeds are paired runs, but
these endpoints are deterministic; the zero-width intervals are not evidence
of independent external replication.

### Fixed class, equal demand

This scenario verifies the quota interpretation with a fixed Low/High class
map. It is not a substitute for production RTL with the live classifier.

| Policy | Service shares L/H/H/H | Raw Jain | Demand-share L1 |
| --- | --- | ---: | ---: |
| FAI-inspired | 49.9975 / 16.6708 / 16.6658 / 16.6658 | 0.750037 | 0.499950 |
| CGOF (1:1) | 25.0013 / 25.0013 / 25.0013 / 24.9962 | 0.999999992 | 7.50e-5 |
| CGOF (2:1) | 14.2857 / 28.5714 / 28.5714 / 28.5714 | 0.942308 | 0.214286 |

The fixed-class differences are deterministic. CGOF (2:1) versus
FAI-inspired changes Jain by `+0.192270` and demand-share L1 by `-0.285664`.
CGOF (1:1) versus CGOF (2:1) changes Jain by `+0.0576923` and demand-share L1
by `-0.214211`. These are policy-arithmetic checks, not evidence of an
application benefit.

### Production RTL, common demand (three windows)

This run uses the live classifier, N4/D16, seed 6201, and three W5M
classification windows. Both quota settings complete 15,000,000 active cycles
plus 1,086 drain cycles. Total generated, accepted, and fired counts are
15,001,085 each after drain.

| Policy | Measurement fired L/H/H/H | Raw Jain | Demand-share L1 |
| --- | --- | ---: | ---: |
| CGOF (1:1) | 3,750,000 / 3,750,000 / 3,750,000 / 3,749,999 | 0.99999999999999 | 1.33e-7 |
| CGOF (2:1) | 3,750,000 / 3,750,000 / 3,750,000 / 3,749,999 | 0.99999999999999 | 1.33e-7 |

The table counts the measurement phase; the 1,086 drain fires complete the
total.

The live classifier changes three encoded states from H to B_H at cycle
4,999,999; all four sources remain effectively High. The encoded map returns
to H/H/H/H at cycle 9,999,999 and remains there at cycle 14,999,999. Both quota
settings produce the same transition and service trace in this equal-demand
run. The observed nearly equal service shares accompany a transient pending
classification, with no change in effective priority.

The generation-to-fire P99 is 1,086 cycles for every source. The decomposition
is 1,023 cycles generation-to-acceptance plus 63 cycles
acceptance-to-fire. The bounded external-producer backlog dominates this
number; it is not a CXL response latency.

### Accepted scheduler RTL

The accepted endpoint analysis exposes scheduler-boundary service and
arrival demand, not a common-demand application trace. Raw Jain is low when
one Heavy source dominates demand; it must not be read as unfairness by itself.

| Policy | Profile | Seeds | Raw Jain | Sparse-only Jain | Demand-share L1 | Heavy service fraction | Max Heavy wall gap |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FAI-inspired | trained-A | 20 | 0.262086 | 0.999386 | 0.001081 | 0.976578 | 6 |
| CGOF (2:1) | trained-A | 20 | 0.262084 | 0.999388 | 0.001074 | 0.976581 | 5 |
| FAI-inspired | trained-B | 20 | 0.262092 | 0.999999 | 0.001068 | 0.976565 | 11 |
| CGOF (2:1) | trained-B | 20 | 0.262093 | 1.000000 | 0.001070 | 0.976564 | 7 |

RTL sparse-tail evidence is strong in both accepted profiles:

- trained-A: FAI-inspired `10.00` to CGOF (2:1) `1.10` cycles; paired delta
  `-8.90`, 95% interval `[-9.00, -8.75]`; 20/20 seeds improve.
- trained-B: FAI-inspired `21.05` to CGOF (2:1) `12.35` cycles; paired delta
  `-8.70`, 95% interval `[-9.50, -7.90]`; 20/20 seeds improve.

The RTL Heavy evidence is mixed rather than uniformly better. Mean maximum
wall gap improves in these confirmation cohorts, but the trained-B Heavy gap
P99 increases from `1` to `3` cycles. Long-run Heavy service fraction remains
about `0.9766` for both policies.

Direct W256 RTL quota checks also pass:

| Configuration | Rounds | Observed per round |
| --- | ---: | --- |
| CGOF (2:1), low/high | 75 | `[1, 2]` every round |
| CGOF (2:1), high/high | 56 | `[2, 2]` every round |
| CGOF (1:1), both cases | 113 | `[1, 1]` every round |

These checks validate quota arithmetic; they are not a long-run fairness
measurement for CGOF (1:1).

### Current-source CGOF confirmation

The fresh current-source run covers all 20 confirmation seeds and five
robustness seeds. Each run contributes both cohorts, for 60 endpoints. The
source hashes differ from the earlier accepted run only in `AGENTS.md`; the
aggregate records that documentation-only drift explicitly. Raw Jain remains
dominated by the Heavy source and is not an unfairness verdict. Sparse Jain
and demand-share L1 are the relevant common-demand checks.

| Group/profile | Seeds | Raw Jain | Sparse Jain | Demand L1 | Heavy share | Heavy gap P99 / max | Sparse P99 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| confirmation always-A | 20 | 0.262084 | 0.999388 | 0.001074 | 0.976581 | 2 / 4.0 | 1.10 |
| confirmation always-B | 20 | 0.262093 | 1.000000 | 0.001070 | 0.976564 | 3 / 5.1 | 12.35 |
| robustness bernoulli-A | 5 | 0.266153 | 0.999408 | 0.016478 | 0.969015 | 4 / 9.8 | 5.00 |
| robustness bernoulli-B | 5 | 0.266309 | 1.000000 | 0.016744 | 0.968727 | 4 / 11.8 | 20.40 |
| robustness periodic-A | 5 | 0.266178 | 0.999408 | 0.016570 | 0.968969 | 17 / 20.0 | 17.00 |
| robustness periodic-B | 5 | 0.266297 | 1.000000 | 0.016698 | 0.968750 | 17 / 21.0 | 27.00 |

The 20-seed confirmation cells use paired bootstrap intervals; the five-seed
robustness cells are exploration-only and intentionally have no confidence
interval. The current-source RTL run contains CGOF (2:1) only, so the
FAI-inspired versus CGOF comparison above remains a cross-run accepted-endpoint
comparison, not a fresh same-source paired RTL baseline.

## Heavy and sparse diagnosis

The model-only finite-Heavy confirmation uses W5M, N4/D16, and 20 paired
seeds. `Sparse P99` is generation-to-fire in scheduler cycles. Ratios compare
mixed Heavy work with the isolated Heavy baseline.

| Profile | Policy | Sparse P99 | Completion ratio | Throughput ratio | Max Heavy gap |
| --- | --- | ---: | ---: | ---: | ---: |
| under | FAI-inspired | 4.00 | 1.0000006 | 0.9999994 | 5.35 |
| under | CGOF (1:1) | 3.00 | 1.0000012 | 0.9999988 | 5.80 |
| under | CGOF (2:1) | 3.30 | 1.0000006 | 0.9999994 | 6.35 |
| under | WRR 2:1 | 5.00 | 1.0000006 | 0.9999994 | 4.90 |
| under | IWRR 2:1 | 4.40 | 1.0000006 | 0.9999994 | 5.15 |
| near | FAI-inspired | 19.10 | 1.0001380 | 0.9998620 | 6.00 |
| near | CGOF (1:1) | 3.25 | 1.0001540 | 0.9998461 | 6.50 |
| near | CGOF (2:1) | 4.10 | 1.0001520 | 0.9998481 | 7.35 |
| near | WRR 2:1 | 7.85 | 1.0001460 | 0.9998541 | 6.35 |
| near | IWRR 2:1 | 6.70 | 1.0001480 | 0.9998521 | 6.35 |
| over | FAI-inspired | 28.30 | 1.2002146 | 0.8331878 | 7.00 |
| over | CGOF (1:1) | 4.15 | 1.2004486 | 0.8330256 | 7.55 |
| over | CGOF (2:1) | 4.85 | 1.2004373 | 0.8330334 | 9.55 |
| over | WRR 2:1 | 10.00 | 1.2003968 | 0.8330614 | 7.35 |
| over | IWRR 2:1 | 8.70 | 1.2004261 | 0.8330411 | 7.35 |

The confirmation reproduces the exploration direction: CGOF reduces Sparse
tail versus FAI-inspired and versus WRR/IWRR, while its maximum Heavy service
gap is not better than FAI-inspired under overload. CGOF does not improve
long-run Heavy completion or throughput by a meaningful amount.

Official paired comparisons for CGOF (2:1) versus FAI-inspired under
overload:

- Sparse P99: `-23.45` cycles, 95% interval `[-23.80, -23.15]`.
- Maximum Heavy gap: `+2.55` cycles, 95% interval `[2.10, 3.00]`.
- Completion ratio: `+2.227e-4`, 95% interval `[1.688e-4, 2.811e-4]`.
- Throughput ratio: `-1.544e-4`, 95% interval `[-1.947e-4, -1.172e-4]`.

Against WRR/IWRR under overload, CGOF (2:1) lowers Sparse P99 by `5.15` and
`3.85` cycles respectively, but increases maximum Heavy gap by `2.20` cycles
against both. Completion and throughput differences are near zero. These are
model results, not application measurements.

### Production RTL, finite Heavy

The finite-Heavy RTL run uses N4/D16, seed 6201, one W5M classification
window, and a finite Heavy burst of 5,000,000 requests. Each quota setting is
paired with an isolated Heavy-only baseline. All four jobs pass, with
`generated = accepted = fired = 5,375,826` in the mixed lane.

| Policy | Active cycles mixed / isolated | Completion ratio | Heavy max wall gap mixed / isolated | Heavy gap P99 | Sparse P99 |
| --- | --- | ---: | ---: | ---: | ---: |
| CGOF (1:1) | 6,248,272 / 6,248,269 | 1.00000048 | 9 / 7 | 3 | 3 |
| CGOF (2:1) | 6,248,272 / 6,248,269 | 1.00000048 | 10 / 7 | 3 | 4 |

Heavy fired 5,000,000 requests in every mixed and isolated lane. The mixed
service shares are 93.009% Heavy and 2.319% / 2.333% / 2.339% for the three
Sparse sources; the Sparse-only Jain is 0.9999877. Heavy
generation-to-fire P99 is 23 cycles in the mixed lane versus 7 cycles
isolated. The classifier crosses one boundary at cycle 4,999,999, before the
Heavy burst completes at cycle 6,248,271.

The seed-6201 run confirms the single-window mechanics. A separate five-seed
exploration sweep now checks the same mixed/isolated grid for seeds 509-513,
using two quota settings per seed. All ten pairs pass conservation and Heavy
completion checks.

| Policy | Seeds | Sparse P99 mean | Completion ratio mean | Heavy gap P99 mean | Heavy gap max mean | Heavy share mean | Sparse Jain mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CGOF (1:1) | 5 | 3.00 | 1.000000512 | 3.00 | 9.00 | 0.930301 | 0.999994 |
| CGOF (2:1) | 5 | 4.00 | 1.000000512 | 3.00 | 9.80 | 0.930301 | 0.999994 |

The descriptive quota delta for `CGOF (2:1) minus CGOF (1:1)` is `+1.0`
Sparse-P99 cycle and `+0.8` maximum-Heavy-gap cycle; completion ratio does not
change. These five seeds are exploration evidence and have no confidence
intervals.

The repaired 20-seed held-out confirmation covers seeds 529-548 with one W5M
classification window, N4/D16, both quota settings, and mixed/isolated lanes.
All 80 results pass, all 40 pairs complete conservation and Heavy completion,
and the confirmation binds to one stable source variant.

| Policy | Seeds | Sparse P99 (95% CI) | Mixed/isolated completion ratio (95% CI) | Heavy gap P99 (95% CI) | Heavy gap max (95% CI) |
| --- | ---: | ---: | ---: | ---: | ---: |
| CGOF (1:1) | 20 | 3.00 (3.00-3.00) | 1.000000488 (1.000000224-1.000000808) | 3.00 (3.00-3.00) | 9.45 (9.15-9.75) |
| CGOF (2:1) | 20 | 4.00 (4.00-4.00) | 1.000000480 (1.000000224-1.000000800) | 3.00 (3.00-3.00) | 10.85 (10.45-11.35) |

| Fairness metric | CGOF (1:1) | CGOF (2:1) |
| --- | ---: | ---: |
| Raw Jain (95% CI) | 0.288367 (0.288341-0.288393) | 0.288367 (0.288341-0.288393) |
| Sparse-only Jain (95% CI) | 0.999993735 (0.999990826-0.999996078) | 0.999993735 (0.999990781-0.999996030) |
| Demand-share L1 (95% CI) | 1.82e-8 (0-5.45e-8) | 3.63e-8 (0-9.09e-8) |
| Heavy service share (95% CI) | 0.930230 (0.930186-0.930274) | 0.930230 (0.930187-0.930275) |

Raw Jain is dominated by the intentional Heavy service share and is not an
unfairness verdict. The paired `CGOF (2:1) minus CGOF (1:1)` deltas are `+1`
Sparse-P99 cycle (95% CI `[1, 1]`), `+1.40` maximum-Heavy-gap cycles (95% CI
`[1.10, 1.75]`), and effectively zero completion-ratio change (95% CI
`[-2.40e-8, 0]`). The Heavy gap P99 delta is zero. Thus the held-out RTL result
shows a temporal allocation difference: CGOF (1:1) has lower Sparse P99 and
smaller maximum Heavy gaps than CGOF (2:1) in this near-load profile. Mean
mixed-minus-isolated completion delays are 3.05 and 3.00 cycles. All 80 lanes
cross one boundary to B_H/H/H/H while remaining effectively High; the
comparison exercises one-credit versus two-credit rounds under intermittent
activity, rather than a learned High/Low allocation. Fairness uses active
counts, while Sparse latency follows the active generation cohort through
drain. Three mixed lanes have one Sparse request outstanding at active cutoff.

This confirmation remains a single-window cohort. The separate dynamic probe
below adds multi-window finite-Heavy, role switching and a minimal backpressure
comparison at one seed; it does not extend the twenty-seed confirmation.
Real CXL/application measurements remain `NOT_RUN`.

## Dynamic finite-Heavy diagnostic - 2026-10-30

A separate dynamic cohort now tests four classifier windows, physical
role switching and two ready-stall arrangements. The model screen used W256,
four nominal windows, Heavy work `3.5W`, seeds `6101-6105`, both CGOF quota
settings and paired mixed/isolated lanes. All 90 model pairs passed, every
case crossed four active classifier boundaries, and source hashes remained
stable.

Mean model Sparse generation-to-fire P99 (cycles):

| Case | FAI-inspired | CGOF (1:1) | CGOF (2:1) |
| --- | ---: | ---: | ---: |
| Multi-window | 12.6 | 4.0 | 4.2 |
| Role switch | 14.8 | 5.4 | 6.6 |
| Ready spread | 11.8 | 2.6 | 3.2 |
| Ready bursty | 18.0 | 11.2 | 11.0 |

Mean model maximum Heavy service gaps (cycles):

| Case | FAI-inspired | CGOF (1:1) | CGOF (2:1) |
| --- | ---: | ---: | ---: |
| Multi-window | 6.2 | 4.2 | 5.2 |
| Role switch | 6.6 | 4.2 | 5.6 |
| Ready spread | 5.2 | 3.6 | 4.0 |
| Ready bursty | 11.6 | 11.2 | 11.4 |

The D8/D32 screen did not meet the primary performance-selection rule: under
bursty readiness, neither depth changed total Sparse P99 or maximum Heavy gap
by at least one cycle in three of five paired seeds. D8 did expose a
measurement-boundary effect: admission wait moved out of the FIFO while total
latency stayed unchanged. D8 therefore received one production RTL case to
validate that observability finding; D32 received no production run.

The single-seed production probe completed at N4/W5M with seed `7291`,
four nominal windows and `17.5M` finite Heavy requests. It covers
multi-window, role switching, ready spread, ready bursty and D8 bursty, with
both quota settings and mixed/isolated lanes: 20 simulations and 10 pairs.
The frozen manifest SHA-256 is
`527a9206c16e0198f6ae6067f37b6652d72009eb956acfbdffa9cb85a529a03a`.
All lint, traffic-test and RTL gates passed, with one stable source variant.
All `17.5M` Heavy requests completed in every lane; generation-role and
physical-source conservation passed. Every result crossed four actual active
classifier boundaries; no Sparse generation-cohort request was censored at
cutoff. This is `SCHEDULER_RTL PASS (single-seed)`.

The aggregate is
`artifacts/implementation/cgof-dynamic-20261030/aggregate.json`, SHA-256
`e8a398b18348a99a3a20fc89e1d0086b5c75b31db093b9e1e9ebecbd76d649e8`.
All 30 result/scope/summary bindings, archived source hashes and protected
document hashes were independently checked. The analyzer self-check and
targeted diagnosis suites passed (40 tests and 18 subtests). The separate
W256 smoke comparison also matched an independent model execution.

The following are per-run observations, with gaps in wall cycles or eligible
ready opportunities. Completion ratio is mixed/isolated active cycles; values
above one mean longer Heavy completion with Sparse interference.

| Case | Policy | Sparse generation-to-fire P99 | Heavy wall gap P99 / max | Heavy ready-opportunity gap P99 / max | Completion ratio |
| --- | --- | ---: | ---: | ---: | ---: |
| Multi-window, D16 | CGOF (1:1) | 3 | 3 / 10 | 2 / 4 | 1.0000002286 |
| Multi-window, D16 | CGOF (2:1) | 4 | 3 / 11 | 2 / 7 | 1.0000002286 |
| Role switch, D16 | CGOF (1:1) | 3 | 3 / 9 | 2 / 4 | 1.0000002743 |
| Role switch, D16 | CGOF (2:1) | 4 | 3 / 11 | 2 / 7 | 1.0000002743 |
| Ready spread, D16 | CGOF (1:1) | 3 | 3 / 5 | 2 / 4 | 1.0000001828 |
| Ready spread, D16 | CGOF (2:1) | 3 | 3 / 8 | 2 / 7 | 1.0000001828 |
| Ready bursty, D16 | CGOF (1:1) | 11 | 11 / 14 | 2 / 4 | 1.0000002286 |
| Ready bursty, D16 | CGOF (2:1) | 11 | 11 / 17 | 2 / 7 | 1.0000002286 |
| Ready bursty, D8 | CGOF (1:1) | 11 | 11 / 14 | 2 / 4 | 1.0000002286 |
| Ready bursty, D8 | CGOF (2:1) | 11 | 11 / 17 | 2 / 7 | 1.0000002286 |

Mixed completion takes four extra cycles for spread readiness, five for
multi-window/bursty/D8 and six for role switching. No equivalence margin was
predeclared, so the small observed differences do not establish equivalence.
Spread and bursty readiness have realized ready fractions
`0.8999999863` and `0.9000001143`, respectively. The burst arrangement raises
Sparse P99 from 3 to 11 cycles for both quotas at nearly equal availability.
Heavy wall-gap P99 changes from 3 to 11, while ready-opportunity gap P99
remains 2. Both clock boundaries are therefore needed to describe the
backpressure result.

The static-role cases record `[B_H,H,H,H]` at the first closing window and
`[L,H,H,H]` at the next three, one effective-class transition. With Heavy
source schedule `[0,0,1,1]`, the role-switch case records
`[B_H,H,H,H] -> [L,H,H,H] -> [B_L,B_H,H,H] -> [H,L,H,H]`, three effective
source-class transitions. Buffer states retain their previous effective
class. This demonstrates actual adaptation in the recorded run, rather than
merely a configured multi-window horizon.

Demand-share L1 is zero in all ten mixed rows, and Sparse
demand-normalized Jain is 1. Static-role Sparse raw Jain is approximately
`0.999997`; role-switch Sparse raw Jain is `0.898643`, with all-source raw
Jain `0.545057`. Unequal time in each role explains the latter raw-share
comparison; it is not an unfairness verdict. These are aggregate active-count
measures with all Sparse work completed at cutoff, not evidence of
time-local quota compliance or a latency bound.

Sparse generation-to-acceptance P99 is zero in every case, and its
acceptance-to-fire P99 equals the total values in the table. D8 exposes a
different boundary for Heavy waiting under bursty readiness:

| Depth | Quotas | Heavy generation-to-acceptance P99 | Heavy acceptance-to-fire P99 | Heavy generation-to-fire P99 |
| --- | --- | ---: | ---: | ---: |
| D16 | CGOF (1:1), CGOF (2:1) | 2 | 18 | 20 |
| D8 | CGOF (1:1), CGOF (2:1) | 11 | 16 | 20 |

The component percentiles describe different requests and must not be added.
Reducing FIFO depth shifts waiting before admission while leaving the
observed total Heavy P99 and Sparse P99 unchanged.

This is a descriptive single-seed probe (`confidence_intervals: null`),
separate from the older twenty-seed single-window confirmation. The dynamic
RTL batch contains CGOF only; the FAI-inspired contrasts above remain W256
model exploration. D32 RTL, multi-seed dynamic confirmation and a broad
backpressure/load sweep remain `NOT_RUN`.

## End-to-end measurements

| Metric | Status | Reason |
| --- | --- | --- |
| Completed memory bandwidth | `NOT_RUN` | No calibrated CXL platform or completed-byte trace |
| Memory issue-to-response latency | `NOT_RUN` | Generation-to-fire is scheduler waiting, not a CXL response |
| Application slowdown | `NOT_RUN` | No application or calibrated system harness |
| Maximum application slowdown | `NOT_RUN` | Same boundary |
| Common-demand CGOF production RTL with live classifier | `SCHEDULER_RTL PASS` | Three W5M windows, one seed; no application trace |
| Finite-Heavy burst completion in RTL | `SCHEDULER_RTL PASS` | 20 held-out seeds plus five-seed exploration; mixed/isolated x two quota settings; single window only |
| Multi-window finite-Heavy stress | `SCHEDULER_RTL PASS (single-seed)` | Four actual W5M boundaries; no held-out dynamic seed interval |
| Role switching | `MODEL_ONLY PASS; SCHEDULER_RTL PASS (single-seed)` | Generation-time roles preserved; three effective source-class transitions |
| Ready spread versus bursty | `MODEL_ONLY PASS; SCHEDULER_RTL PASS (single-seed)` | Nearly equal realized 90% readiness; wall and ready-opportunity gaps separated |
| D8/D32 depth sensitivity | `MODEL_ONLY PASS; D8 SCHEDULER_RTL PASS (single-seed)` | D8 confirms wait-boundary shift; D32 not selected for RTL |

Scheduler `fire/cycle` must not be called memory bandwidth. A
generation-to-fire distribution must not be called memory response latency.

## Implementation feasibility

The complete CGOF correctness matrix passed before the matched synthesis/STA
matrix. CGOF (2:1), N4/D16/W5M, has total cell area `109794.784709` in library
area units and 9014 sequential cells. Under the frozen TT 25 ns cap075-v2
profile, worst reported setup/hold slack is `+10.398800 / +0.038578 ns`, with
zero reported constraint violations. There are 68 disclosed constant-disabled
timing checks; tested coverage is not 100%.

Five additional pre-layout configurations complete the N4/N8/N16 quota
matrix:

| Policy | N | Total cell area | Seq. cells | PT worst setup (ns) | PT worst hold (ns) | Coverage met/total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CGOF (1:1) | 4 | 106163.066946 | 8998 | +12.683299 | +0.034898 | 36284/36352 |
| CGOF (1:1) | 8 | 212027.006396 | 17915 | +8.135937 | +0.054674 | 71958/72022 |
| CGOF (1:1) | 16 | 423513.448454 | 35748 | +3.158005 | +0.078278 | 143244/143244 |
| CGOF (2:1) | 8 | 218863.734160 | 17947 | +5.675092 | +0.103860 | 72026/72030 |
| CGOF (2:1) | 16 | 436771.124393 | 35812 | +1.248813 | +0.084335 | 143500/143500 |

All five report zero timing violations. Formality proves every matched compare
point with no user constants or exclusions. The CGOF (1:1) runs retain
`23 * (N_SRC + 2)` unread classifier-accounting DFFs (138/230/414 for
N4/N8/N16), so the claim is observable-boundary equivalence with disclosed
dead state, not full all-register equivalence. Both CGOF (2:1) runs have no
unread compare points.

The independent area/STA audit accepts this scoped comparison with caveats.
The matched FAI-inspired N4 cell area is `110089.845892`, so the observed
CGOF area difference is `-0.268019%`, with three more registers and
`0.097609 ns` less setup slack. Different top-level glue contributes a small
part of the area difference; this is not an isolated policy-efficiency claim.

For N4 CGOF (2:1), Formality proves all 9126 compare points, including 112
output bits and 9014 registers, with zero failing, aborted, unverified or
unmatched points. All matrix results are pre-layout implementation results;
power, physical signoff and all real-CXL/application metrics remain
unmeasured. See
[CGOF correctness and N4 synthesis/STA](CGOF_RTL_PPA.md) for bindings, reports
and diagnostic caveats.

## Interpretation

The defensible contribution is a measurement and diagnosis result:

1. Quota and ordering are separated. Under continuous backlog, oldest-first
   and eligible round-robin are identical; the quota/credit intervention is
   the active lever.
2. Raw Jain alone misclassifies intentional weighted allocation. Demand-share
   error and weighted Jain are required alongside raw Jain.
3. CGOF has a reproducible Sparse-tail benefit, but it can pay a Heavy
   maximum-gap cost. The long-run Heavy throughput result is essentially flat.
4. The current-source performance confirmation and 20-seed held-out
   finite-Heavy RTL confirmation support the scheduler-boundary direction and
   quota arithmetic, but they do not yet support an end-to-end CXL or
   application claim.
5. The single-seed dynamic probe records effective-class adaptation and shows
   why readiness arrangement and FIFO admission boundaries matter. Its
   observed fairness and small completion differences do not establish
   multi-seed robustness, time-local fairness or completion equivalence.

The current evidence is credible for a rigorous workshop or moderate-venue
measurement paper. It is not yet top-tier evidence because the live-classifier
RTL evidence remains scheduler-boundary only, the calibrated CXL platform is
absent, and application slowdown is not measured.

## Next-stage gate

Do not expand the implementation until the following are complete:

1. Keep the completed 20-seed common-demand performance confirmation and
   20-seed single-window finite-Heavy confirmation separate from the completed
   single-seed multi-window/role-switch probe. Held-out dynamic replication
   remains a future gate.
2. Preserve paired seeds, burst IDs, generated/accepted/fired conservation,
   and the external-producer versus FIFO versus delivered-service boundary.
3. Keep CGOF (1:1), CGOF (2:1), WRR/IWRR, and FAI-inspired as separate
   configurations in the same manifest.
4. Preserve the completed model D8/D32 screen, selected D8 RTL and minimal
   readiness/role-switch comparisons. N8/N16 behavior and any broader
   sensitivity matrix need a separate justified selection; use W256 only for
   plumbing and fast screening.
5. If the result survives matched-quota and WRR/IWRR controls, calibrate a
   real CXL system or a validated cycle-accurate system model.
6. Measure completed bytes/s, issue-to-response latency, application slowdown,
   maximum slowdown, and tail behavior on representative applications.

If the system measurements show no application-level translation, retain the
diagnostic paper and drop any algorithm-novelty claim.
