# Sealed role-switch adaptation results

Observed2026-10-25; nine sealed RTL runs, with independent literal-state and histogram reanalysis. This report is pending parent adoption; it changes no implementation, experiment, index or manuscript.

## Scope and descriptive unit

Main, Algorithm-2 and Main-1W each use exploration seeds509,510,511, N4/D16, one output, full105 descriptors, W5,000,000, High/Low10/10, and ready always. Heavy generation is Bernoulli0.8; each of the other three sources independently generates with probability1/128. The expected aggregate generation rate0.8234375 is a generator expectation, not a measured output rate. There is no separate training (`training_cycles=0`, `cold=false`); the generic `-trained` filename suffix does not change that contract.

| Generation interval | Role / heavy source | Active window closes |
| --- | --- | --- |
| [0,10000000) | role0 / source0 | 4999999; 9999999 |
| [10000000,20000000) | role3 / source3 | 14999999; 19999999 |
| [20000000,30000000) | role0-return / source0 | 24999999; 29999999 |
| [30000000,30000002) | drain / no new arrivals | none |

RNG, FIFOs, producer queues, timestamps, scheduler visit context and classes continue across both role changes without reset, drain or forced class assignment. Role0-return is history-dependent. The generic `sparse_guard_cycles=1024` and `sparse_guard_complete=true` fields do not insert guards in adaptation: the frozen adaptation guard records a boundary snapshot and returns immediately.

One seed/run is the descriptive unit. Three seeds are reported individually and as arithmetic means of run statistics; no CI, bootstrap, significance test, tuning or extra jobs were used. Sparse histograms pool the three sources that were sparse at **generation**, including any subsequent completion in another role or drain. Requests, sources and repeated roles are not extra independent replicates. A mean of run-P99 values is not a pooled-request P99.

## Literal evidence and state reconstruction

All54 window records and216 source transitions were independently recomputed from raw service counts, starting at reset. For N4 and S=sum(B), the literal labels are S0 if S=0; otherwise UP if40B<3S, DOWN if4B>S, and KEEP otherwise (including equality). Closing-cycle fire is included. Each pair of windows exactly sums to that role phase's per-source fires. These B/S labels measure realized service share, not offered demand.

The independent calculation uses the approved literal Main §8.2 and Algorithm-2 §8.6 tables in `specs/CXL_SPEC.md`, plus the approved Main-1W rule (UP→H, DOWN→L, KEEP/S0 retain effective class); it imports no implementation transition function. Main B_H/B_L preserve previous High/Low; Algorithm-2 BUFFER_P_HIGH/LOW use target High/Low. Neutral/idle cancellation and all Algorithm-2/Main-1W effective-state cases are checked separately, although actual windows in this arm contain UP/DOWN only.

The following actual B vectors are identical across all three policies for each seed; equality was verified, not inferred from heavy IDs. Vector order is source0,1,2,3. All actual windows1,2,5,6 have evidence `[DOWN,UP,UP,UP]`; windows3,4 have `[UP,UP,UP,DOWN]`.

| Seed | Close cycle | Actual B[0..3] | S |
| --- | --- | --- | --- |
| 509 | 4999999 | [4000219,39021,39520,39340] | 4118100 |
| 509 | 9999999 | [4001942,39144,39109,39106] | 4119301 |
| 509 | 14999999 | [39273,38862,39300,4000973] | 4118408 |
| 509 | 19999999 | [38754,39102,39052,4000053] | 4116961 |
| 509 | 24999999 | [4001372,39225,38739,39476] | 4118812 |
| 509 | 29999999 | [4001143,38959,39089,38895] | 4118086 |
| 510 | 4999999 | [3998223,39144,39161,39395] | 4115923 |
| 510 | 9999999 | [3998903,38967,39034,38943] | 4115847 |
| 510 | 14999999 | [39326,39160,39166,3998795] | 4116447 |
| 510 | 19999999 | [39185,39241,38949,4000809] | 4118184 |
| 510 | 24999999 | [3998393,39041,38906,39241] | 4115581 |
| 510 | 29999999 | [4000442,39301,39189,39382] | 4118314 |
| 511 | 4999999 | [4000384,39053,39167,39036] | 4117640 |
| 511 | 9999999 | [4000208,39295,39184,39038] | 4117725 |
| 511 | 14999999 | [38848,39073,39187,4000916] | 4118024 |
| 511 | 19999999 | [38952,39163,39339,3999238] | 4116692 |
| 511 | 24999999 | [3999586,39007,38898,39301] | 4116792 |
| 511 | 29999999 | [4001205,39111,39016,39341] | 4118673 |

All three seeds have the following post-close state trajectory. Effective class is visible from the next cycle; H/L in the effective columns mean High/Low.

| Visible from cycle | Main state | Main effective | Algorithm-2 state | Algorithm-2 / Main-1W effective |
| --- | --- | --- | --- | --- |
| 5000000 | [B_H,H,H,H] | [H,H,H,H] | [BUFFER_P_LOW,STABLE_HIGH,STABLE_HIGH,STABLE_HIGH] | [L,H,H,H] |
| 10000000 | [L,H,H,H] | [L,H,H,H] | [STABLE_LOW,STABLE_HIGH,STABLE_HIGH,STABLE_HIGH] | [L,H,H,H] |
| 15000000 | [B_L,H,H,B_H] | [L,H,H,H] | [BUFFER_P_HIGH,STABLE_HIGH,STABLE_HIGH,BUFFER_P_LOW] | [H,H,H,L] |
| 20000000 | [H,H,H,L] | [H,H,H,L] | [STABLE_HIGH,STABLE_HIGH,STABLE_HIGH,STABLE_LOW] | [H,H,H,L] |
| 25000000 | [B_H,H,H,B_L] | [H,H,H,L] | [BUFFER_P_LOW,STABLE_HIGH,STABLE_HIGH,BUFFER_P_HIGH] | [L,H,H,H] |
| 30000000 | [L,H,H,H] | [L,H,H,H] | [STABLE_LOW,STABLE_HIGH,STABLE_HIGH,STABLE_HIGH] | [L,H,H,H] |

The returned classes are model post-commit state supported by the following cycle's RTL state assertions, including a drain observation after the final active close. They are not separately serialized post-edge RTL register dumps. Main first changes the new heavy/old heavy effective classes after two supporting closes; Algorithm-2/Main-1W change after one. In these phase-aligned traces, switched-role classification therefore changes after5M cycles for Algorithm-2/Main-1W versus10M cycles for Main. This is observed classifier timing, not latency recovery or a general recovery bound.

**Main settles at the role phase end.** Its classes committed at20M apply as the next role begins, and those at30M apply only to drain. The changed-role cohorts therefore contain no long steady interval under Main's newly settled classes. The six-window experiment must not be described as measuring such a settled period.

## Whole-role generated-population latency

All latency units below are cycles. Each cohort includes all requests generated in its10M-cycle role, including carryover completions. No per-window latency histogram or chronological request/visit trace is retained. P99.9 and maximum are descriptive.

| Policy | Seed | Generation role | Sparse N | Mean g→f | P50 | P90 | P99 | P99.9 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAIN | 509 | role0 | 235240 | 1.914521 | 2 | 2 | 3 | 4 | 8 |
| MAIN | 509 | role3 | 234342 | 1.878647 | 1 | 5 | 9 | 10 | 11 |
| MAIN | 509 | role0-return | 234382 | 2.415958 | 2 | 5 | 10 | 10 | 11 |
| MAIN | 510 | role0 | 234644 | 1.913200 | 2 | 2 | 3 | 4 | 6 |
| MAIN | 510 | role3 | 235026 | 1.886127 | 1 | 5 | 9 | 10 | 11 |
| MAIN | 510 | role0-return | 235059 | 2.418201 | 2 | 5 | 10 | 10 | 11 |
| MAIN | 511 | role0 | 234773 | 1.915714 | 2 | 2 | 3 | 4 | 6 |
| MAIN | 511 | role3 | 234562 | 1.883349 | 1 | 5 | 10 | 10 | 11 |
| MAIN | 511 | role0-return | 234674 | 2.426046 | 2 | 5 | 10 | 10 | 11 |
| ALG2 | 509 | role0 | 235240 | 2.645800 | 2 | 6 | 10 | 10 | 11 |
| ALG2 | 509 | role3 | 234342 | 2.623175 | 1 | 7 | 10 | 10 | 11 |
| ALG2 | 509 | role0-return | 234382 | 2.894245 | 2 | 7 | 10 | 10 | 11 |
| ALG2 | 510 | role0 | 234644 | 2.638891 | 2 | 6 | 10 | 10 | 11 |
| ALG2 | 510 | role3 | 235026 | 2.627348 | 1 | 7 | 10 | 10 | 12 |
| ALG2 | 510 | role0-return | 235059 | 2.897239 | 2 | 7 | 10 | 10 | 11 |
| ALG2 | 511 | role0 | 234773 | 2.647293 | 2 | 6 | 10 | 10 | 11 |
| ALG2 | 511 | role3 | 234562 | 2.628218 | 1 | 7 | 10 | 10 | 12 |
| ALG2 | 511 | role0-return | 234674 | 2.905358 | 2 | 7 | 10 | 10 | 12 |
| MAIN1W | 509 | role0 | 235240 | 2.645800 | 2 | 6 | 10 | 10 | 11 |
| MAIN1W | 509 | role3 | 234342 | 2.623175 | 1 | 7 | 10 | 10 | 11 |
| MAIN1W | 509 | role0-return | 234382 | 2.894245 | 2 | 7 | 10 | 10 | 11 |
| MAIN1W | 510 | role0 | 234644 | 2.638891 | 2 | 6 | 10 | 10 | 11 |
| MAIN1W | 510 | role3 | 235026 | 2.627348 | 1 | 7 | 10 | 10 | 12 |
| MAIN1W | 510 | role0-return | 235059 | 2.897239 | 2 | 7 | 10 | 10 | 11 |
| MAIN1W | 511 | role0 | 234773 | 2.647293 | 2 | 6 | 10 | 10 | 11 |
| MAIN1W | 511 | role3 | 234562 | 2.628218 | 1 | 7 | 10 | 10 | 12 |
| MAIN1W | 511 | role0-return | 234674 | 2.905358 | 2 | 7 | 10 | 10 | 12 |

Across all405 checked per-source/sparse latency distributions, histogram count, weighted mean, nearest-rank P50/P90/P99/P99.9 and maximum match their serialized values. All324 per-source stage distributions have their generation cohort's exact source count; per source, exact weighted totals obey (a−g)+(f−a)=(f−g). Quantiles do not add. All generation→acceptance histograms consist of zero-cycle samples, so generation→fire and acceptance→fire histograms are identical in these runs. This observed zero admission delay is specific to this finite-load arm.

The following means use three paired seeds509..511. Differences are Algorithm-2 or Main-1W minus Main for the same seed/role. Algorithm-2 and Main-1W results are equal in each pair, so their summary is shown once; all nine run identities are retained above.

| Role | Main sparse mean | Alg2/1W sparse mean | Paired Δmean | Main mean run-P99 | Alg2/1W mean run-P99 | Paired ΔP99 | Main heavy mean | Alg2/1W heavy mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| role0 | 1.914479 | 2.643995 | +0.729516 | 3.000000 | 10.000000 | +7.000000 | 1.107315 | 1.085896 |
| role3 | 1.882708 | 2.626247 | +0.743539 | 9.333333 | 10.000000 | +0.666667 | 1.108539 | 1.086732 |
| role0-return | 2.420068 | 2.898947 | +0.478879 | 10.000000 | 10.000000 | +0.000000 | 1.092646 | 1.078598 |

Earlier effective classification does not lower sparse waiting here: Algorithm-2/Main-1W sparse mean wait is higher in all three whole-role comparisons, while heavy mean wait is lower. Sparse mean run-P99 rises for role0 and role3 and is unchanged for role0-return. These are profile-specific service/latency tradeoffs, not an overall policy ranking or an isolated latency-recovery effect.

## Phase accounting, backlog and final drain

For every seed, all policies have identical whole-phase generated, offered, accepted and fired count vectors and boundary snapshots; FIFO occupancy distributions differ. Phase generated equals accepted in each case. Offered counts measure valid-presentation cycles, including repeats in general; in this particular arm they equal unique generated/admitted counts because every request is immediately admitted.

| Seed | Phase | Generated = offered = accepted (sum) | Fired (sum) | Cycles | Observed fires/cycle |
| --- | --- | --- | --- | --- | --- |
| 509 | role0 | 8237402 | 8237401 | 10000000 | 0.8237401 |
| 509 | role3 | 8235369 | 8235369 | 10000000 | 0.8235369 |
| 509 | role0-return | 8236898 | 8236898 | 10000000 | 0.8236898 |
| 509 | drain | 0 | 1 | 2 | 0.5000000 |
| 510 | role0 | 8231771 | 8231770 | 10000000 | 0.8231770 |
| 510 | role3 | 8234631 | 8234631 | 10000000 | 0.8234631 |
| 510 | role0-return | 8233895 | 8233895 | 10000000 | 0.8233895 |
| 510 | drain | 0 | 1 | 2 | 0.5000000 |
| 511 | role0 | 8235365 | 8235365 | 10000000 | 0.8235365 |
| 511 | role3 | 8234716 | 8234716 | 10000000 | 0.8234716 |
| 511 | role0-return | 8235466 | 8235465 | 10000000 | 0.8235465 |
| 511 | drain | 0 | 1 | 2 | 0.5000000 |

All27 active phases have zero avoidable bubbles and eligible-ready utilization1.0; this denominator includes only ready cycles with a beginning-of-cycle FIFO head. It does not mean100% utilization of all clock cycles. Total delivered counts and completion cycles are equal across policies; there is no observed total-throughput or drain advantage in this arm.

Producer pending/backlog is sampled after generation but before same-cycle acceptance; its per-source maximum is1 in every active phase and its aggregate run peak is4. Those counts include newly generated requests and do not imply requests waiting across cycles. Boundary producer backlog is zero for all sources. FIFO occupancy is sampled before pop/push; its per-source maxima are below D16:

| Policy | Seed | Role | FIFO max[0..3] | FIFO mean[0..3] |
| --- | --- | --- | --- | --- |
| MAIN | 509 | role0 | [6,2,3,3] | [0.8860771,0.0149162,0.0150521,0.0150689] |
| MAIN | 509 | role3 | [4,2,2,7] | [0.0269020,0.0085233,0.0085994,0.8867567] |
| MAIN | 509 | role0-return | [6,2,3,3] | [0.8743443,0.0148173,0.0147767,0.0270318] |
| MAIN | 510 | role0 | [6,3,2,2] | [0.8851059,0.0148892,0.0149629,0.0150400] |
| MAIN | 510 | role3 | [3,2,2,7] | [0.0271554,0.0085733,0.0086003,0.8865170] |
| MAIN | 510 | role0-return | [7,2,3,3] | [0.8735282,0.0148240,0.0148114,0.0272067] |
| MAIN | 511 | role0 | [6,2,3,2] | [0.8863594,0.0149653,0.0150091,0.0150014] |
| MAIN | 511 | role3 | [3,2,2,7] | [0.0269381,0.0085792,0.0086589,0.8873073] |
| MAIN | 511 | role0-return | [8,2,2,4] | [0.8747131,0.0148150,0.0148393,0.0272787] |
| ALG2 | 509 | role0 | [6,3,3,3] | [0.8688745,0.0206770,0.0207978,0.0207650] |
| ALG2 | 509 | role3 | [4,3,3,7] | [0.0265564,0.0174107,0.0175050,0.8693093] |
| ALG2 | 509 | role0-return | [6,3,4,3] | [0.8631341,0.0206024,0.0204733,0.0267603] |
| ALG2 | 510 | role0 | [6,3,3,3] | [0.8680780,0.0205181,0.0207295,0.0206724] |
| ALG2 | 510 | role3 | [3,3,3,7] | [0.0268198,0.0174771,0.0174527,0.8690964] |
| ALG2 | 510 | role0-return | [7,3,3,3] | [0.8622680,0.0205711,0.0206231,0.0269081] |
| ALG2 | 511 | role0 | [6,3,4,3] | [0.8691839,0.0207036,0.0207053,0.0207424] |
| ALG2 | 511 | role3 | [3,4,3,7] | [0.0265690,0.0175324,0.0175466,0.8698355] |
| ALG2 | 511 | role0-return | [8,3,3,4] | [0.8634649,0.0206025,0.0205984,0.0269803] |

Main-1W has exactly the same occupancy/backlog/gap summaries as Algorithm-2 for each seed, not just the same maxima. Boundary snapshots and full cohort×completion-phase matrices are independently reconciled per source in the audit. Actual nonzero carryover, identical across policies, is:

| Seed | Generation cohort | Later completion phase | Requests[0..3] |
| --- | --- | --- | --- |
| 509 | role0 | role3 | [1,0,0,0] |
| 509 | role3 | role0-return | [0,0,0,1] |
| 509 | role0-return | drain | [1,0,0,0] |
| 510 | role0 | role3 | [1,0,0,0] |
| 510 | role3 | role0-return | [0,0,0,1] |
| 510 | role0-return | drain | [1,0,0,0] |
| 511 | role0-return | drain | [1,0,0,0] |

| Seed | FIFO at10M | FIFO at20M | FIFO at30M | Total generated = accepted = fired | Final drain cycles | Final outstanding / producer backlog |
| --- | --- | --- | --- | --- | --- | --- |
| 509 | [1,0,0,0] | [0,0,0,1] | [1,0,0,0] | 24709669 | 2 | 0 / 0 |
| 510 | [1,0,0,0] | [0,0,0,1] | [1,0,0,0] | 24700297 | 2 | 0 / 0 |
| 511 | [0,0,0,0] | [0,0,0,0] | [1,0,0,0] | 24705547 | 2 | 0 / 0 |

| Seed | Total generated = accepted = fired per source[0..3] |
| --- | --- |
| 509 | [16082704,234313,234809,8157843] |
| 510 | [16074473,234854,234405,8156565] |
| 511 | [16079184,234702,234791,8156870] |

The total per-source populations and full phase/source count vectors are retained in `audit.json`. Across all nine runs, every generated cohort completes and per-source cumulative generated−accepted equals producer backlog; accepted−fired equals FIFO occupancy at each snapshot. The final active close is followed by two drain cycles; no extra classification close occurs in drain.

## Algorithm-2 / Main-1W overlap and limits

For all three same-seed pairs, the independently checked effective classes, window counts/evidence, complete `metrics` dictionaries (all cohort histograms/completion matrices, phase counters, occupancy/backlog/gaps and snapshots), generated/admitted/fired totals, real cycles and drain are exactly equal. Raw class-state names/encodings, policy identity and runtime measurements are intentionally not required to match. The literal tables also agree in effective class for all Algorithm-2 states and UP/DOWN/KEEP/S0 inputs, not only the labels observed here.

This supports observed overlap under the matched10/10 configuration; the two rows are not independent mechanisms or extra repetitions. Each RTL run passed its own per-cycle oracle assertions, but no complete adaptation output-pin hash was serialized. The untouched `training_pin_sha256` is the hash of the empty training-prefix stream because training is zero. Aggregate equality plus oracle checks is not an independently recorded cross-RTL cycle-by-cycle equivalence proof.

Retained evidence does not support per-window P99, chronological latency recovery curves, a source starvation/recovery bound, complete visit maxima, full CXL response latency or application slowdown. Classification timing and whole-role generated-population latency must remain separate conclusions.

## Evidence and independent audit

Sealed bundle: `.setup-logs/implementation/revision-20261024/queue-recovery/prepared-20261024T0108Z/runs/core/05-adaptation/attempt000/`. Existing strict acceptance was reused with recomputed current raw/bundle hashes; every archive member was compared with its actual returned file. All39 archived source members match before/after manifests and current pinned sources. The22 steps comprise21 tool steps with numeric exit0 and one derived scope PASS; the scope step has no process exit code. There are55 actual JUnit testcases (46 Python,9 cocotb), with no failure/error/skip. Each simulation duration equals10ns×(real non-reset cycles+2 reset edges).

| Binding | SHA256 |
| --- | --- |
| Canonical core39 source | 800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86 |
| sources.zip | e38f5bc37897bad7adb19cd5a00e596c2e64aca0bbd6ded9fc860a090c2560e6 |
| evidence.zip | e8682b09dce23c4d93cb40a60e5e4de44afaf94f93ec4de7ccd1bdea5b64501c |

Audit scope: `.setup-logs/implementation/revision-20261024/power-index/adaptation-results-20261025T1555/`. `audit.py` independently checks54 windows,216 source transitions,405 latency histograms, completion matrices, phase/snapshot conservation and three observable-overlap pairs. `audit.json` binds every raw result, the independent checklist and prior strict inspection by SHA256, and retains exact per-source/phase results. `guards-before.json`/`guards-after.json` show core39, DAC53, power33 and protected539 unchanged, as well as the frozen indexer/test/doc hashes.

Reproduce from repository root (read-only inputs; writes only this assigned report and its ignored audit scope):

```powershell
C:\ProgramData\anaconda3\python.exe -B .setup-logs/implementation/revision-20261024/power-index/adaptation-results-20261025T1555/audit.py
C:\ProgramData\anaconda3\python.exe -B .setup-logs/implementation/revision-20261024/power-index/adaptation-results-20261025T1555/report.py
```

No simulations, source/index changes, CI, manuscript edits, remote work or other matrix promotions were performed. Independent parent review remains the adoption step.
