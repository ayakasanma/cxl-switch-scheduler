# Trained N-expansion results: N8 and N16

Observed 2026-10-27 (Asia/Taipei). All60 exact N-expansion rows are sealed and parent-adopted after independent strict-index review. This descriptive report itself remains pending parent and independent narrative review. This analysis did not rerun simulation or remote EDA, or alter source inputs.

## Scope and accounting

The existing fixed matrix is N8/N16 × six policies × five exploration seeds509–513: FCFS, RR1, RR10, Main, Algorithm-2 reconstruction and BLISS-inspired descriptor adaptation. The60 unique runs yield120 A/B endpoints,24 complete five-run cohorts and8 same-N Main-vs-FCFS/RR10 paired comparisons. Inputs are resource1 (N16 FCFS509), sealed N8 ordinal7 thirty rows, N16 non-FCFS ordinal8 twenty-five, and N16 FCFS510–513 ordinal9 four. The resource case is reused once; neither historical failures nor partial raw results add rows. The final accepted matrix is498 PASS, zero RUNNING/NOT_RUN/FAIL/UNRESOLVED (468 unconditional +30 conditional DAC). Matrix completion is not manuscript adoption.

N per-source FIFOs retain depth16, full105-bit descriptors, one equal-cost atomic output, ready always, W5,000,000 and actual training10,000,000 cycles. Main/Algorithm-2 use High/Low10/10; RR1 quantum1 and RR10 quantum10. A generates sparse independent Bernoulli1/128 per nonheavy source for100,000 cycles. B generates100 seeded blocks of8 requests per sparse source over102,400 cycles (800/source). Both measured cohorts retain completions in the1024-cycle background-on guards and final drain. Time units below are scheduler cycles, not nanoseconds or application slowdown. No cold, adaptation or DAC performance rows are mixed in.

## N changes offered load and storage

| N | Sparse sources | Sparse mean generation/cycle | Total mean generation/cycle | Descriptor FIFO slots (D16) |
| ---: | ---: | ---: | ---: | ---: |
| 4 (context only) | 3 | 3/128 =0.0234375 | 131/128 =1.0234375 | 64 |
| 8 | 7 | 7/128 =0.0546875 | 135/128 =1.0546875 | 128 |
| 16 | 15 | 15/128 =0.1171875 | 143/128 =1.1171875 | 256 |

One heavy source generates one request/cycle; the sparse generation rate is per source, not held constant in aggregate. B has the same sparse average8/1024 with burst timing. Increasing N changes aggregate offered load, number of competing sources and total FIFO storage simultaneously. These observations therefore do not isolate a causal fan-in/scaling effect. N4 is boundary context, not an extra paired cohort. No cross-N trace pairing or cross-N confidence interval is performed.

## Latency summaries

A run pools nonheavy sources within its complete generation cohort and uses nearest-rank quantiles. Tables average five run-level statistics; they are not quantiles from merged runs. Requests, sources and A/B are not independent replications. Seeds509–513 are exploratory; no CI, bootstrap, significance claim, tuning or global winner. P99.9 and maximum are descriptive. All three stages (generation→acceptance, acceptance→fire, generation→fire) and per-seed P99 remain in the ignored analysis output; stage quantiles must not be added.

### N8

| Policy | Arm | Mean g→f | Mean P50 | Mean P90 | Mean P99 [run range] | Mean P99.9 | Observed max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FCFS | A | 16.944624 | 17.0 | 18.0 | 20.0 [20–20] | 21.4 | 23 |
| RR1 | A | 1.059362 | 1.0 | 1.0 | 2.0 [2–2] | 3.0 | 4 |
| RR10 | A | 5.799286 | 6.0 | 10.0 | 12.0 [12–12] | 13.0 | 15 |
| MAIN | A | 5.552400 | 6.0 | 10.0 | 10.0 [10–10] | 11.0 | 11 |
| ALG2 | A | 5.499852 | 5.4 | 9.4 | 10.0 [10–10] | 11.0 | 11 |
| BLISS | A | 1.025148 | 1.0 | 1.0 | 2.0 [2–2] | 2.2 | 5 |
| FCFS | B | 23.995107 | 24.0 | 30.0 | 37.6 [37–38] | 42.6 | 46 |
| RR1 | B | 8.387143 | 9.0 | 15.0 | 20.2 [20–21] | 24.2 | 28 |
| RR10 | B | 9.422571 | 9.0 | 14.6 | 21.0 [20–22] | 28.2 | 33 |
| MAIN | B | 9.796857 | 9.2 | 15.2 | 27.6 [27–29] | 36.6 | 43 |
| ALG2 | B | 9.791857 | 9.0 | 15.0 | 28.2 [27–29] | 36.4 | 46 |
| BLISS | B | 22.213393 | 24.0 | 30.0 | 37.0 [36–38] | 41.8 | 46 |

### N16

| Policy | Arm | Mean g→f | Mean P50 | Mean P90 | Mean P99 [run range] | Mean P99.9 | Observed max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FCFS | A | 18.174151 | 18.0 | 20.0 | 22.0 [22–22] | 24.0 | 26 |
| RR1 | A | 1.133978 | 1.0 | 2.0 | 3.0 [3–3] | 4.0 | 7 |
| RR10 | A | 6.174387 | 6.0 | 11.0 | 13.0 [13–13] | 15.0 | 19 |
| MAIN | A | 5.561769 | 6.0 | 10.0 | 10.0 [10–10] | 11.0 | 14 |
| ALG2 | A | 5.565086 | 5.8 | 10.0 | 10.0 [10–10] | 11.0 | 13 |
| BLISS | A | 1.062790 | 1.0 | 1.0 | 2.0 [2–2] | 3.0 | 6 |
| FCFS | B | 25.437083 | 25.8 | 33.6 | 41.8 [40–43] | 49.2 | 59 |
| RR1 | B | 8.956267 | 9.0 | 15.0 | 23.4 [22–25] | 30.0 | 38 |
| RR10 | B | 10.054667 | 10.0 | 16.0 | 24.4 [23–26] | 31.8 | 46 |
| MAIN | B | 11.094333 | 10.0 | 19.6 | 34.8 [32–37] | 47.4 | 61 |
| ALG2 | B | 11.204667 | 10.0 | 19.6 | 35.2 [33–39] | 48.8 | 63 |
| BLISS | B | 23.506083 | 24.0 | 32.6 | 41.6 [40–43] | 48.8 | 59 |

## Same-N paired comparisons

Delta is Main minus baseline in cycles; negative means lower sparse run-P99. Existing normalizer/statistics helpers verify exact trace, source, profile and configuration boundaries within N, retaining distinct policy settings. All six policies have matching intended trace and trace_config for each seed within N.

| N | Arm | Baseline | Baseline mean P99 | Main mean P99 | Paired mean delta | Improved seeds |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 8 | A | FCFS | 20.0 | 10.0 | -10.0 | 5/5 |
| 8 | A | RR10 | 12.0 | 10.0 | -2.0 | 5/5 |
| 8 | B | FCFS | 37.6 | 27.6 | -10.0 | 5/5 |
| 8 | B | RR10 | 21.0 | 27.6 | +6.6 | 0/5 |
| 16 | A | FCFS | 22.0 | 10.0 | -12.0 | 5/5 |
| 16 | A | RR10 | 13.0 | 10.0 | -3.0 | 5/5 |
| 16 | B | FCFS | 41.8 | 34.8 | -7.0 | 5/5 |
| 16 | B | RR10 | 24.4 | 34.8 | +10.4 | 0/5 |

**Main B remains unfavorable versus RR10: N8 27.6 vs21.0 (+6.6 cycles); N16 34.8 vs24.4 (+10.4), with0/5 improved seeds at each N.** Main improves over FCFS in all five seeds per N/arm, while its A advantage over RR10 is2 cycles at N8 and3 at N16. This is a conditional tradeoff, not an overall ranking. No DAC2 N8/N16 RTL performance evidence is included or implied by the accepted N4 candidate results.

## Measured-phase service and producer accounting

| N | Arm | Phases | Cycles per phase | Ready cycles | Eligible-ready opportunities | Total fires | Eligible-ready utilization | Avoidable bubbles |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | A | 30 | 100000 | 100000 | 100000 | 100000 | 1.0 | 0 |
| 8 | B | 30 | 102400 | 102400 | 102400 | 102400 | 1.0 | 0 |
| 16 | A | 30 | 100000 | 100000 | 100000 | 100000 | 1.0 | 0 |
| 16 | B | 30 | 102400 | 102400 | 102400 | 102400 | 1.0 | 0 |

Heavy service fraction is heavy-source fires / total measured-phase fires, not offered or generated heavy demand. Eligible-ready utilization divides fires by ready cycles with a beginning-of-cycle nonempty FIFO. Fires/ready and fires/phase-cycles have separate denominators; all equal1 only in these saturated ready-always measured phases. They do not describe all training/guard/drain clocks, link bandwidth or general backpressure behavior.

| N | Policy | A mean heavy fraction % [range] | B mean heavy fraction % [range] |
| ---: | --- | ---: | ---: |
| 8 | FCFS | 94.565000 [94.439000–94.688000] | 94.532617 [94.531250–94.538086] |
| 8 | RR1 | 94.563800 [94.438000–94.687000] | 94.531250 [94.531250–94.531250] |
| 8 | RR10 | 94.564200 [94.439000–94.687000] | 94.531250 [94.531250–94.531250] |
| 8 | MAIN | 94.564000 [94.439000–94.687000] | 94.531250 [94.531250–94.531250] |
| 8 | ALG2 | 94.564000 [94.438000–94.687000] | 94.531250 [94.531250–94.531250] |
| 8 | BLISS | 94.563800 [94.438000–94.687000] | 94.532617 [94.531250–94.538086] |
| 16 | FCFS | 88.307000 [88.217000–88.412000] | 88.282617 [88.281250–88.288086] |
| 16 | RR1 | 88.304200 [88.215000–88.408000] | 88.281250 [88.281250–88.281250] |
| 16 | RR10 | 88.304600 [88.215000–88.408000] | 88.281250 [88.281250–88.281250] |
| 16 | MAIN | 88.304400 [88.216000–88.408000] | 88.281250 [88.281250–88.281250] |
| 16 | ALG2 | 88.304800 [88.216000–88.408000] | 88.281250 [88.281250–88.281250] |
| 16 | BLISS | 88.304200 [88.215000–88.408000] | 88.282617 [88.281250–88.288086] |

These are five-run arithmetic means and observed ranges, not service guarantees. Raw phase accounting preserves generated/offered/accepted/fired vectors, ready/eligible counts, local FIFO occupancy, external producer backlog and cohort completion-by-phase. Offered counts are valid-presentation cycles (possibly repeated), not automatically unique arrivals. Local FIFO state sees admitted work; external backlog is distinct. Sparse counts are verified against complete generation cohorts by the existing normalizer. No upstream-demand estimator or equal-entitlement fairness is established.

| N | Observed producer peak backlog range | Final drain cycle range | Final outstanding / producer backlog |
| ---: | ---: | ---: | ---: |
| 8 | 556587–558859 | 556602–558874 | 0 /0 |
| 16 | 1192524–1197154 | 1192539–1197169 | 0 /0 |

Heavy generation already saturates the output before sparse work; training backlog survives into measurement and later drains. Do not interpret these overloaded finite traces as stationary heavy-latency distributions, unsaturated workload evidence or application-level performance. No storage-only cost conclusion follows from the across-N table, and no new area/timing/power experiment is run. Algorithm-2 and BLISS remain the project adaptations described in [METHOD_DIFFERENCES.md](METHOD_DIFFERENCES.md). There is no full CXL protocol, causal system benefit, starvation bound, hardware-efficiency or physical-signoff claim.

## Accepted inputs and reproduction

The frozen caller `E/n-expansion-analysis-20261027/analyze.py` was executed only after the explicit parent adoption binding; E means `.setup-logs/implementation/revision-20261024/`. It reuses the existing histogram normalizer and same-N paired statistics. Raw hashes, source maps and archive hashes are checked locally; no full10M replay or new strict-index run is performed. The earlier N8 preparation and expected blocked full60 attempt remain immutable historical outputs.

- Adopted index: `E/power-index/final498-20261027/snapshot/index/matrix-coverage.json`, SHA256 `1defb1bbebe31948b5a2834e3510bfcda660190a8630732593bb2169c462f668`.
- Parent adoption: `E/parent-continuation-20261027T0325/final498-adoption.json`, SHA256 `16445cbcbcc10be603e619405fd7c170605c3c0694398a88bb30b2b387f430c4`.
- Independent final review is bound by that adoption; narrative adoption of this report remains separate.
- Complete60 output, source/result/trace/archive identities and all24 cohorts/8 pairs: `E/n-expansion-analysis-20261027/full60-output/analysis.json`.
- Actual full60/selfcheck logs, command bindings and frozen-source hashes: the same scope, `full60-release.json`.
- Actual prior N8 numeric anchor: `E/parent-continuation-20261027T0202/n8-arithmetic-check.json`; caller verifies it while separately computing raw service denominators.
- Continuing owner-requested gpt-6.1-sol/high scope, no Opus invocation. Historical selected runtime evidence remains qualified in `prior-runtime-provenance.json`; no new runtime introspection is claimed.

Reproduce from the repository root with fresh output names (never overwrite accepted output):

```powershell
$scope = ".setup-logs/implementation/revision-20261024/n-expansion-analysis-20261027"
python -B "$scope/analyze.py" --selfcheck
python -B "$scope/analyze.py" --index ".setup-logs/implementation/revision-20261024/power-index/final498-20261027/snapshot/index/matrix-coverage.json" --index-sha 1defb1bbebe31948b5a2834e3510bfcda660190a8630732593bb2169c462f668 --adoption ".setup-logs/implementation/revision-20261024/parent-continuation-20261027T0325/final498-adoption.json" --adoption-sha 16445cbcbcc10be603e619405fd7c170605c3c0694398a88bb30b2b387f430c4 --out "$scope/full60-repeat"
python -B "$scope/report.py" --input "$scope/full60-repeat/analysis.json" --report "$scope/N_EXPANSION_RESULTS-repeat.md"
```

The manuscript revision packet revision2 retains its historical494/56-of60 checkpoint unchanged. This report updates neither that packet nor final-report/DEVELOPMENT_REPORT/ISSUE_LEDGER. Accepted498 execution does not authorize manuscript revision or constitute final paper QA.
