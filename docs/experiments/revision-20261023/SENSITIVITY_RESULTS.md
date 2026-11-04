# Sealed RTL sensitivity results

Observed2026-10-25. Read-only analysis of the already sealed High-quota15, RR quantum25 and Main-1W5 runs. These45 RTL runs are exploration evidence; no new experiment, parameter choice or manuscript revision is made.

## Measurement and pairing

All configurations use N4, FIFO D16, one output, full105 descriptors, downstream always ready, W5,000,000 and two actual training windows (10,000,000 cycles). Heavy source0 generates one request per cycle. Sparse sources1-3 use profile A with independent1/128 arrivals, and profile B with eight-request bursts per1024 cycles. Profiles are generation cohorts, with completion/drain retained by the existing harness.

Each table value is the arithmetic mean of five per-run pooled-sparse generation-to-fire nearest-rank quantiles, seeds509-513. It is not the quantile of merged runs. Requests, sources, and A/B are not independent repetitions. A has11,638 sparse samples across these five runs and B has12,000, for every listed configuration. P99.9 and observed maximum are descriptive.

Delta P99 = candidate run-P99 minus same-seed default run-P99, averaged over the five pairs, in absolute cycles. Negative means less waiting. RR is paired with Q10 in the same sweep; High-quota is paired with High10/Low10; Main-1W is paired with the High10/Low10 Main runs using the same five seeds. Every pair passes exact intended-trace SHA/config, generation-cohort counts and common-source checks; the RTL parameters differ only in the declared intervention (RR_QUANTUM, HIGH_QUOTA or MAIN_1W). There is no comparison against different confirmation seeds.

This is exploration-only descriptive analysis: no CI, bootstrap, significance claim, parameter tuning or overall ranking. Defaults remain unchanged.

## Exact five-run means

| Group | Setting | Profile | Mean P50 | Mean P90 | Mean P99 | Mean P99.9 | Observed max | Paired delta P99 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RR quantum | 1 | A | 1.00 | 1.00 | 2.00 | 2.00 | 3 | -9.00 |
| RR quantum | 1 | B | 9.00 | 15.00 | 16.40 | 22.20 | 26 | -0.80 |
| RR quantum | 4 | A | 2.80 | 4.00 | 5.00 | 5.20 | 6 | -6.00 |
| RR quantum | 4 | B | 9.00 | 13.40 | 16.40 | 20.40 | 26 | -0.80 |
| RR quantum | 8 | A | 4.80 | 8.00 | 9.00 | 9.60 | 10 | -2.00 |
| RR quantum | 8 | B | 8.00 | 12.80 | 15.80 | 19.60 | 22 | -1.40 |
| RR quantum | 10 | A | 5.40 | 10.00 | 11.00 | 11.60 | 13 | +0.00 |
| RR quantum | 10 | B | 9.00 | 14.20 | 17.20 | 23.60 | 32 | +0.00 |
| RR quantum | 16 | A | 8.80 | 15.00 | 17.00 | 18.00 | 19 | +6.00 |
| RR quantum | 16 | B | 11.80 | 19.00 | 23.80 | 29.60 | 38 | +6.60 |
| Main High quota | 5 | A | 5.80 | 9.60 | 10.00 | 10.00 | 11 | +0.00 |
| Main High quota | 5 | B | 11.00 | 24.40 | 32.20 | 47.20 | 58 | +11.40 |
| Main High quota | 10 | A | 5.80 | 9.60 | 10.00 | 10.00 | 11 | +0.00 |
| Main High quota | 10 | B | 9.00 | 14.20 | 20.80 | 30.80 | 38 | +0.00 |
| Main High quota | 20 | A | 5.80 | 9.60 | 10.00 | 10.00 | 11 | +0.00 |
| Main High quota | 20 | B | 9.00 | 14.00 | 17.00 | 20.80 | 28 | -3.80 |
| Main-1W | one-window effective class | A | 5.00 | 9.20 | 10.00 | 10.60 | 11 | +0.00 |
| Main-1W | one-window effective class | B | 9.00 | 14.00 | 21.00 | 29.80 | 35 | +0.20 |

Low quota remains10 throughout the High-quota sweep. Default rows are retained with zero delta as a provenance check; they are not extra independent baseline replications. Main-1W keeps W5,000,000, rather than shortening the window to one cycle.

## Per-seed P99 and absolute paired differences

Vector order is509,510,511,512,513. Units are cycles. Full per-source/stage histograms remain in the sealed raw results.

| Group | Setting | Profile | Five run-P99s | Five deltas vs matched default |
| --- | --- | --- | --- | --- |
| rr-quantum | 1 | A | [2, 2, 2, 2, 2] | [-9, -9, -9, -9, -9] |
| rr-quantum | 1 | B | [17, 16, 18, 15, 16] | [0, -1, 0, -2, -1] |
| rr-quantum | 4 | A | [5, 5, 5, 5, 5] | [-6, -6, -6, -6, -6] |
| rr-quantum | 4 | B | [16, 16, 18, 15, 17] | [-1, -1, 0, -2, 0] |
| rr-quantum | 8 | A | [9, 9, 9, 9, 9] | [-2, -2, -2, -2, -2] |
| rr-quantum | 8 | B | [17, 15, 17, 15, 15] | [0, -2, -1, -2, -2] |
| rr-quantum | 10 | A | [11, 11, 11, 11, 11] | [0, 0, 0, 0, 0] |
| rr-quantum | 10 | B | [17, 17, 18, 17, 17] | [0, 0, 0, 0, 0] |
| rr-quantum | 16 | A | [17, 17, 17, 17, 17] | [6, 6, 6, 6, 6] |
| rr-quantum | 16 | B | [24, 23, 26, 23, 23] | [7, 6, 8, 6, 6] |
| high-quota | 5 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| high-quota | 5 | B | [35, 31, 36, 27, 32] | [11, 12, 12, 10, 12] |
| high-quota | 10 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| high-quota | 10 | B | [24, 19, 24, 17, 20] | [0, 0, 0, 0, 0] |
| high-quota | 20 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| high-quota | 20 | B | [17, 17, 17, 17, 17] | [-7, -2, -7, 0, -3] |
| one-window-causal | 1 | A | [10, 10, 10, 10, 10] | [0, 0, 0, 0, 0] |
| one-window-causal | 1 | B | [24, 18, 24, 17, 22] | [0, -1, 0, 0, 2] |

## Interpretation and limits

RR quantum is profile sensitive. Q1 lowers A mean run-P99 from11 to2 cycles (delta-9); Q8 lowers A to9 (delta-2). In B, Q1 andQ4 both average16.4 (delta-0.8), while Q8 averages15.8 (delta-1.4). Q16 worsens both A and B by6 and6.6 cycles. Thus the setting with the lowest A waiting is not the setting with the lowest B waiting in these five seeds. These observations do not select a replacement quantum.

Reducing Main High quota to5 leaves A P99 unchanged at10 but raises B from20.8 to32.2 cycles (delta+11.4, all five seeds worse). Increasing it to20 leaves A P99 at10 and reduces B to17 (delta-3.8; four improve, one tie). This intervention changes class-service budgets with Low fixed10, including intervening Low visits and the closed-loop service/classification history. Latency alone does not establish free improvement, equal fairness, preserved saturated shares or a classifier-independent cause.

Main-1W leaves A P99 at10 and changes B from20.8 to21 (delta+0.2). Its B paired differences are[0,-1,0,0,+2]: one seed improves and one worsens. P90/P99.9/max do not move uniformly with P99. This trained steady-profile evidence does not establish faster cold reaction or role-switch adaptation; training trajectory and visit alignment are part of the intervention.

Main-1W at quota10/10 has the same effective transition rule and external model-pin behavior from reset as the approved Algorithm-2 target-Buffer reconstruction, despite distinct state encoding. See [method differences](METHOD_DIFFERENCES.md) and [baseline verification](BASELINES.md). It is a causal/diagnostic row, not an independently novel mechanism. The Algorithm-2 confirmation cohort uses529-548; no direct same-seed Main-1W/Algorithm-2 equivalence or superiority is inferred from those different cohorts here.

No overall winner is declared. These synthetic single-output descriptor experiments do not establish full CXL-system behavior, upstream demand estimation, generalized starvation bounds or physical signoff.

## Reproduction and exact evidence

Receipts and reproducible local analysis script: `.setup-logs/implementation/revision-20261024/power-index/sensitivity-20261025/`. Run:

```text
python -B .setup-logs/implementation/revision-20261024/power-index/sensitivity-20261025/analyze_sensitivity.py
```

The script reuses the released strict bundle inspector and histogram normalizer, independently checks nearest-rank P99, and asserts45 accepted runs,90 profile endpoints,18 complete five-seed tables and90 exact same-seed default matches. No policy simulator or traffic generator is executed. Fractions check that each reported mean paired difference equals the difference of paired run-P99 means. Existing unit suites are not rerun because no implementation is changed.

`statistics.json` binds every paired job/result/trace digest and stores all per-seed deltas; `endpoints.json` retains normalized per-source/stage evidence; `sealed-inspections.json` records scope/archive/JUnit/source checks. `guard-before.json` and `guard-after.json` confirm frozen indexer/test/doc and39/53/33 source closures unchanged. The sole new tracked file is this report. Common39 source canonical SHA256:

`800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86`.

| Sealed bundle under recovery prepared-20261024T0108Z | Source ZIP SHA256 | Evidence ZIP SHA256 |
| --- | --- | --- |
| runs/core/02-high-quota/attempt000 | `13ca9112a45dd3ad5817ca78e90e08a7c0fce43c39d68cdbc710f8f7902f342e` | `5d8cc1f5871dafc2eac968669ad75b8a4db47d81cf3d08a63d475bc01117113e` |
| runs/core/03-rr-quantum/attempt000 | `b518eecd675c3eed2277aae26f4ab4ce51b9111c9cb6e01765a9c09c74e2c5ee` | `6c0284c123220275059381a1a7e7206187f61341b22bcaa1047c43320fa51d92` |
| runs/core/01-one-window-causal/attempt000 | `89031921f8ad6e28455323642d1113e963b9d1e5ff54c91e4acd37c68870e780` | `86607efa33b21481cb2c8a14c5b0cd20d618e802dcc5fc729eceaefe2fd7da61` |

All data are observed local RTL results. No bootstrap, new simulation, remote EDA, export, accepted-source modification, index refresh, manuscript edit or research-parameter adjustment is part of this analysis.
