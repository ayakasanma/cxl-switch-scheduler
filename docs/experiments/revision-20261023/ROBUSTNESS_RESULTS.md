# Trained robustness results

Observed 2026-10-26. The sealed 180-run core robustness group and ten DAC2 backpressure runs are accepted inputs. The parent adopted the strict snapshot after independent bundle and arithmetic checks; this report itself awaits independent review. This analysis did not rerun simulation or remote EDA, or alter source inputs.

## Scope and measurement

The fixed matrix is six settings × six policies × five exploration seeds509–513: FCFS, RR1, RR10, Main, Algorithm-2 reconstruction, and BLISS-inspired descriptor baseline. N4, FIFO D16, one equal-cost atomic output, full105 descriptors, W5,000,000, and actual training10,000,000 cycles are fixed. Main/Algorithm-2 use quota10/10; RR1 uses quantum1 and RR10 quantum10. No cold, boundary, adaptation or N8/N16 results are mixed in.

| Setting | Measured perturbation |
| --- | --- |
| ready075 | Independent seeded Bernoulli sink ready0.75 |
| ready48of64 | Sink ready48 cycles per64-cycle period |
| heavy050 / heavy090 | Measured heavy arrival probability0.5 /0.9 |
| burst32 | B sparse bursts32 per4096 instead of8 per1024 |
| heavy-id3 | Whole-trace source0↔3 permutation, including training; not role-change adaptation |

Except heavy-id3, perturbations start after unchanged training and apply through measured phases and guards. A generates for100,000 cycles with independent sparse Bernoulli1/128 arrivals; B generates for102,400 cycles with seeded burst offsets (100 blocks×8, or25×32;800 sparse arrivals/source). Each has a1024-cycle background-on guard. Generation cohorts retain all completions into guards/drain; phase service counts below instead count fires during the named measured phase. All190 runs drain outstanding work and external producer backlog to integer zero.

Latency units are cycles: generation→acceptance (external waiting), acceptance→fire (accepted local waiting), and generation→fire (end-to-end). Nearest-rank quantiles pool nonheavy sources within one run; tables average five run-level endpoints, never merge requests across seeds. A/B stay separate. P999 and maximum are descriptive. No confirmation CI is calculated for509–513. Policies are paired only within the same setting/seed/trace; distinct settings are not paired. The accepted analyzer checks full source closures and exact intended trace/config matches, including the common core closure for the separate DAC53/core39 freezes.

## Core latency summaries

Each entry is mean sparse generation-to-fire P99 [minimum–maximum run-P99], cycles, n=5. The reproducible analysis JSON also retains all72 policy/setting/arm groups with mean/P50/P90/P99/P999 for all three stages, observed maxima, per-seed P99, and exact raw provenance.

### ready075

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 30.6 [30–31] | 46.8 [46–49] |
| RR1 | 5.2 [5–6] | 26.4 [26–28] |
| RR10 | 18.0 [18–18] | 28.0 [27–31] |
| MAIN | 17.2 [17–18] | 32.6 [28–37] |
| ALG2 | 17.2 [17–18] | 31.6 [28–36] |
| BLISS | 5.0 [5–5] | 46.6 [45–49] |

### ready48of64

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 34.0 [34–34] | 47.0 [46–50] |
| RR1 | 17.0 [17–17] | 31.2 [31–32] |
| RR10 | 26.0 [26–26] | 32.2 [31–33] |
| MAIN | 26.0 [26–26] | 34.0 [32–39] |
| ALG2 | 26.0 [26–26] | 33.8 [33–37] |
| BLISS | 17.0 [17–17] | 46.6 [46–49] |

### heavy050

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 18.2 [18–19] | 33.8 [31–36] |
| RR1 | 2.0 [2–2] | 16.4 [15–18] |
| RR10 | 11.0 [11–11] | 17.2 [17–18] |
| MAIN | 10.0 [10–10] | 20.8 [17–24] |
| ALG2 | 10.0 [10–10] | 21.0 [17–24] |
| BLISS | 1.0 [1–1] | 33.0 [31–36] |

### heavy090

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 18.2 [18–19] | 33.8 [31–36] |
| RR1 | 2.0 [2–2] | 16.4 [15–18] |
| RR10 | 11.0 [11–11] | 17.2 [17–18] |
| MAIN | 10.0 [10–10] | 20.8 [17–24] |
| ALG2 | 10.0 [10–10] | 21.0 [17–24] |
| BLISS | 1.0 [1–1] | 33.0 [31–36] |

### burst32

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 18.2 [18–19] | 87.0 [78–100] |
| RR1 | 2.0 [2–2] | 70.6 [63–80] |
| RR10 | 11.0 [11–11] | 74.4 [70–87] |
| MAIN | 10.0 [10–10] | 88.8 [70–116] |
| ALG2 | 10.0 [10–10] | 87.6 [69–113] |
| BLISS | 1.0 [1–1] | 86.4 [78–100] |

### heavy-id3

| Policy | A | B |
| --- | ---: | ---: |
| FCFS | 17.2 [17–18] | 32.8 [30–35] |
| RR1 | 2.0 [2–2] | 16.4 [15–18] |
| RR10 | 11.0 [11–11] | 17.2 [17–18] |
| MAIN | 10.0 [10–10] | 20.8 [17–24] |
| ALG2 | 10.0 [10–10] | 20.8 [17–24] |
| BLISS | 1.0 [1–1] | 32.2 [30–35] |

## Prespecified Main comparisons

Delta is Main minus baseline. Negative means lower sparse P99; positive means regression. No global winner or tuning follows from these exploration summaries.

| Setting | Arm | vs FCFS delta / improved seeds | vs RR10 delta / improved seeds |
| --- | --- | ---: | ---: |
| ready075 | A | -13.4 / 5/5 | -0.8 / 4/5 |
| ready075 | B | -14.2 / 5/5 | +4.6 / 0/5 |
| ready48of64 | A | -8.0 / 5/5 | +0.0 / 0/5 |
| ready48of64 | B | -13.0 / 5/5 | +1.8 / 0/5 |
| heavy050 | A | -8.2 / 5/5 | -1.0 / 5/5 |
| heavy050 | B | -13.0 / 5/5 | +3.6 / 0/5 |
| heavy090 | A | -8.2 / 5/5 | -1.0 / 5/5 |
| heavy090 | B | -13.0 / 5/5 | +3.6 / 0/5 |
| burst32 | A | -8.2 / 5/5 | -1.0 / 5/5 |
| burst32 | B | +1.8 / 2/5 | +14.4 / 0/5 |
| heavy-id3 | A | -7.2 / 5/5 | -1.0 / 5/5 |
| heavy-id3 | B | -12.0 / 5/5 | +3.6 / 0/5 |

**Burst32 B retains Main 88.8 versus RR10 74.4 cycles: +14.4 cycles.** A sparse-tail benefit against FCFS does not remove this disadvantage.

## DAC2 matched backpressure results

These ten runs cover only the two readiness settings, not all six robustness perturbations. Each DAC2 run matches the same-seed Main trace and configuration; 20 A/B endpoints are checked against the parent’s independent histogram arithmetic.

| Ready | Arm | Main mean P99 | DAC2 mean P99 | Delta | Improved seeds |
| --- | --- | ---: | ---: | ---: | ---: |
| bernoulli-0.75 | A | 17.2 | 5.0 | -12.2 | 5/5 |
| periodic-48/64 | A | 26.0 | 17.0 | -9.0 | 5/5 |
| bernoulli-0.75 | B | 32.6 | 20.4 | -12.2 | 5/5 |
| periodic-48/64 | B | 34.0 | 27.0 | -7.0 | 5/5 |

### Exact measured-phase service diagnostics

Heavy service fraction = heavy-source fires / total fires in the measured phase. Ready is the number of sink-ready phase cycles; eligible is ready cycles with a nonempty local FIFO. Eligible-ready utilization = total fires / eligible, distinct from total fires / ready and total fires / phase cycles. Each side has zero avoidable bubbles and utilization1.0 in every row below. Exact fired vectors, separate denominator counts, throughput, and per-source local-FIFO occupancy/external-producer backlog summaries are retained in analysis.json.

| Ready | Seed | Arm (cycles) | Main heavy / fires | DAC2 heavy / fires | Main−DAC2 (pp) | Ready Main / DAC2 | Eligible Main / DAC2 | Bubbles Main / DAC2 | Util Main / DAC2 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bernoulli-0.75 | 509 | A (100000) | 72805/75089 | 72805/75089 | 0.000000000000 | 75089/75089 | 75089/75089 | 0/0 | 1/1 |
| bernoulli-0.75 | 509 | B (102400) | 74270/76665 | 74265/76665 | 0.006521880910 | 76665/76665 | 76665/76665 | 0/0 | 1/1 |
| bernoulli-0.75 | 510 | A (100000) | 72654/75000 | 72654/75000 | 0.000000000000 | 75000/75000 | 75000/75000 | 0/0 | 1/1 |
| bernoulli-0.75 | 510 | B (102400) | 74235/76635 | 74235/76635 | 0.000000000000 | 76635/76635 | 76635/76635 | 0/0 | 1/1 |
| bernoulli-0.75 | 511 | A (100000) | 72709/75114 | 72709/75114 | 0.000000000000 | 75114/75114 | 75114/75114 | 0/0 | 1/1 |
| bernoulli-0.75 | 511 | B (102400) | 74565/76965 | 74565/76965 | 0.000000000000 | 76965/76965 | 76965/76965 | 0/0 | 1/1 |
| bernoulli-0.75 | 512 | A (100000) | 72869/75215 | 72869/75215 | 0.000000000000 | 75215/75215 | 75215/75215 | 0/0 | 1/1 |
| bernoulli-0.75 | 512 | B (102400) | 74197/76597 | 74197/76597 | 0.000000000000 | 76597/76597 | 76597/76597 | 0/0 | 1/1 |
| bernoulli-0.75 | 513 | A (100000) | 72928/75184 | 72927/75184 | 0.001330070228 | 75184/75184 | 75184/75184 | 0/0 | 1/1 |
| bernoulli-0.75 | 513 | B (102400) | 74460/76860 | 74460/76860 | 0.000000000000 | 76860/76860 | 76860/76860 | 0/0 | 1/1 |
| periodic-48/64 | 509 | A (100000) | 72724/75008 | 72724/75008 | 0.000000000000 | 75008/75008 | 75008/75008 | 0/0 | 1/1 |
| periodic-48/64 | 509 | B (102400) | 74400/76800 | 74400/76800 | 0.000000000000 | 76800/76800 | 76800/76800 | 0/0 | 1/1 |
| periodic-48/64 | 510 | A (100000) | 72662/75008 | 72662/75008 | 0.000000000000 | 75008/75008 | 75008/75008 | 0/0 | 1/1 |
| periodic-48/64 | 510 | B (102400) | 74400/76800 | 74400/76800 | 0.000000000000 | 76800/76800 | 76800/76800 | 0/0 | 1/1 |
| periodic-48/64 | 511 | A (100000) | 72603/75008 | 72603/75008 | 0.000000000000 | 75008/75008 | 75008/75008 | 0/0 | 1/1 |
| periodic-48/64 | 511 | B (102400) | 74400/76800 | 74400/76800 | 0.000000000000 | 76800/76800 | 76800/76800 | 0/0 | 1/1 |
| periodic-48/64 | 512 | A (100000) | 72662/75008 | 72662/75008 | 0.000000000000 | 75008/75008 | 75008/75008 | 0/0 | 1/1 |
| periodic-48/64 | 512 | B (102400) | 74400/76800 | 74400/76800 | 0.000000000000 | 76800/76800 | 76800/76800 | 0/0 | 1/1 |
| periodic-48/64 | 513 | A (100000) | 72751/75008 | 72751/75008 | 0.000000000000 | 75008/75008 | 75008/75008 | 0/0 | 1/1 |
| periodic-48/64 | 513 | B (102400) | 74400/76800 | 74400/76800 | 0.000000000000 | 76800/76800 | 76800/76800 | 0/0 | 1/1 |

Maximum measured Main-minus-DAC2 heavy fraction is **0.006521880910455 percentage points**, below the already approved0.01pp guard. Zero bubbles means no missed eligible-ready opportunity; it does not mean the sink was always ready or that the producer had no external backlog. Local FIFO occupancy measures accepted visible work; producer backlog is generated work outside those FIFOs. Heavy work accumulated during training can remain during heavy050/heavy090 measured phases. Fire share therefore is not current offered-demand share, equal-entitlement fairness, or proof that the scheduler observes all producer backlog.

## Candidate gate and limitations

DAC2 is the previously frozen MODEL_ONLY screen selection; this analysis neither reranks candidates nor retunes parameters. The original gate requires B improvement≥1 cycle in cold OR trained with≥4/5 improved seeds, A regression≤1 cycle in cold AND trained, and maximum heavy-service fraction loss≤0.0001 (=0.01pp), with the existing validation/feedback prerequisites. The trained robustness readiness comparisons show A/B improvement in5/5 seeds per group and satisfy that phase heavy-share guard; they do not independently re-establish the full cold+trained model-selection gate or cover DAC2 on the other four settings.

The separate accepted confirmation cohort529–548 reports Main→DAC2 A10.00→1.10 (−8.90 cycles), B21.05→12.35 (−8.70),20/20 improved each. Its existing paired95% intervals are [−9.00,−8.75] and [−9.50,−7.90]; these are cited, not recomputed or transferred to509–513. The confirmation heavy guard already passes at maximum0.001953125pp, with zero avoidable bubbles. See [CONFIRMATION_RESULTS.md](CONFIRMATION_RESULTS.md) and [MODEL_SCREEN.md](MODEL_SCREEN.md) for their distinct accepted boundaries.

DAC2 uses active-source2:1 weights, changing the allocation target. Synthetic sparse latency and phase service diagnostics do not establish global superiority, causal application performance/CXL benefit, equal-share fairness, physical signoff, or real-workload generalization. Algorithm-2 and BLISS are qualified project reconstructions. All gap metrics remain episode/censoring-dependent; no uncensored starvation bound is inferred.

## Evidence and reproduction

All paths below are repository-relative. The accepted strict snapshot records439 PASS,30 RUNNING,29 NOT_RUN (zero FAIL/UNRESOLVED) at its own checkpoint; this report does not adopt unsealed later queue outputs. Core robustness has364 PASS steps,226 tests, zero failures/errors/skips, actual ordinal6 exit0. The364 includes one derived scope step and363 retained numeric-exit tool steps.

- Strict release: `.setup-logs/implementation/revision-20261024/power-index/robustness-sealed-20261026t1518/release.json`, SHA256 `1fea76a9c574f2b47a3c6b94299f62748db0ad3d19cf80d341af13f082397af2`.
- Parent adoption: `.setup-logs/implementation/revision-20261024/parent-continuation-20261026T1518/robustness-index-adoption.json`.
- Independent strict snapshot: `.setup-logs/implementation/revision-20261024/robustness-independent-20261026/snapshot-review.json` (PASS).
- Parent ten-pair arithmetic/service anchor: `parent-continuation-20261026T1518/paired-dac-robustness-check.json` under the same revision root.
- Core source ZIP SHA256 `a411f6141dc1013d7b129d836460e8902ef234356fedab5b9a9353078dd26dac`; evidence ZIP SHA256 `0c132690084b1750296168fb3392582c20f61781ae772e059b31af1782b7b1d9`.
- Core raw bundle: `queue-recovery/prepared-20261024T0108Z/runs/core/06-trained-robustness/attempt000`; DAC: `runs/dac/00-insight-robustness/attempt000` under the same recovery root.
- Reproducible outputs and complete input/result/source hashes: `.setup-logs/implementation/revision-20261024/robustness-results-20261026/output/analysis.json`.
- Analysis provenance: actual `gpt-6.1-sol`, effort `high`; selected runtime fields saved in `model-provenance.json`. No Opus invocation.

The parent documented an initial ad hoc Python type error (`any(integer_backlog)`), corrected to exact integer-zero comparison before its successful check. This was analysis tooling, not an RTL finding; its original evidence remains preserved.

From the repository root (fresh output/report paths are required; existing files are never overwritten):

```powershell
$scope = ".setup-logs/implementation/revision-20261024/robustness-results-20261026"
python "$scope/analyze.py" --selfcheck
python "$scope/analyze.py" --output "$scope/repeat-output" --report "$scope/repeat-ROBUSTNESS_RESULTS.md"
```
