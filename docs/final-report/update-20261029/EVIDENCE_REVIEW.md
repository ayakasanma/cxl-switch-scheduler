# October 29 independent evidence review

## Material Passport

- Status: FINAL / FROZEN for parent integration, 2026-10-29 Asia/Taipei. Early findings are retained as an audit trail; resolution notes below take precedence.
- Role: independent evidence reviewer, GPT-6.1 Sol; read-only experiment audit for the October 29 manuscript update.
- Verification Status: ANALYZED (raw-file/hash/statistic checks; no simulator or EDA rerun).
- Scope: write only this file. Preserve the immutable October 28 planning snapshot and release record.

## Early findings for immediate integration

1. **P1 — Every repaired finite-Heavy job remains effectively High.** All 80 raw results have one classifier record at `closing_cycle=4999999`, `old_classes=[H,H,H,H]`, `classes=[B_H,H,H,H]`; 40 mixed and 40 isolated lanes. B_H retains High. This cohort cannot demonstrate effective demotion, adaptation convergence, or benefit from a learned High/Low distinction. `DIAGNOSIS_SUMMARY.md` also incorrectly describes the earlier common-demand B_H transition as “below-High.”
2. **P1 — Completed confirmation supports a local temporal tradeoff, with 1:1 ahead on both measured tail metrics.** `confirmation-finite-heavy-fixed-20261029/aggregate.json:finite_heavy.groups` agrees with the 80 raw files: Sparse mean run-P99 is 3/4 cycles for 1:1/2:1; mean run-maximum Heavy wall gap is 9.45/10.85 cycles; mean mixed-minus-isolated Heavy completion is 3.05/3.00 cycles. The paired 2:1-minus-1:1 differences are +1 Sparse-P99 cycle, +1.40 maximum-gap cycles, and only -0.05 completion cycle. Do not present this as 2:1 buying a Sparse improvement at Heavy's expense.
3. **P1 — Provenance and failure exclusion.** All 100 bound finite input hashes match, all 20 per-seed runs report PASS with stable sources, and all 80 unique `(seed,weight,lane)` identities are complete and conserve generated/accepted/fired work, including generation-cohort completions. The failed batch `confirmation-finite-heavy-20261029` / run `20261028T202434Z_267411` is excluded. Against the archived exploration source, the repaired source changes only `sim/experimental/cgof_diagnosis_traffic.py` (keep the closing active cycle in the finite-heavy cohort) and its regression test; RTL/model sources are unchanged.
4. **P2 — Launcher status is stale.** The repaired batch's top-level `status.txt` still says `STOPPED_OR_FAILED`, although all 20 completed per-seed scopes and raw result files pass. The final evidence claim should cite the completed scopes/aggregate, disclose interrupted-and-resumed orchestration, and avoid claiming a clean single launcher invocation.
5. **P1 — New performance cohort is CGOF-only.** `aggregate-current-20261029.json:performance` contains 60 endpoints (40 confirmation, 20 exploration robustness), all CGOF (2:1). It reproduces Sparse A/B means 1.10/12.35; comparisons against Main still use the accepted historical cohorts. `source_drift_files=[AGENTS.md]` describes differences within the new performance cohort, not the finite-Heavy repair or a fresh Main RTL comparison.

6. **P1 — Fairness and latency use different temporal populations.** `test_cgof_diagnosis.py:143–150` computes fairness from active-phase generated/fired counts, before drain. Sparse latency is the pooled generation cohort, including requests completed during drain. At active cutoff only three mixed jobs retain one Sparse request: seed 529 at both weights and seed 542 at weight 2. Thus nearly zero active demand-L1 largely reflects completion conservation; it does not establish short-term fairness or entitlement compliance.
7. **P2 — Readiness is nominally matched, not numerically identical in every run.** The theory note's “same average readiness” should mean the same nominal 75% level. In the actual A measurement, periodic ready is 0.75008 and Bernoulli ranges 0.75000–0.75215; in B periodic is 0.75000 and Bernoulli ranges 0.748018–0.751611. Their temporal patterns and measured tails differ, but this is not an exact finite-trace capacity-matched causal isolation.
8. **P2 — Public-summary transcription error.** `DIAGNOSIS_SUMMARY.md` current-source always-B Sparse Jain `0.999720` is wrong; raw/recomputed `aggregate-current-20261029.json:performance.cohorts[always,B].sparse_jain.mean` is `0.9999997212955298`. The fixed-class source3 share also rounds to 24.9962%, not 24.9963%. Use bound aggregates/raw counts rather than relabeled summary tables.

Parent additions reviewed read-only: `THEORY_AND_EVIDENCE.md` and `hypothesis-status.json` correctly preserve the quota direction, the reused seed identifiers, near-profile scope, and partial H3 status. Add the explicit all-80 effective-High boundary fact, distinguish active fairness from generation-cohort latency, and phrase the readiness comparison as nominal 75%. Detailed final audit follows.

## Final disposition and source bindings

The parent corrected findings 1, 6, 7 and 8 in the mutable synthesis/theory documents during this review. The final read confirms explicit all-80 effective-High traces, active fairness versus generation-cohort latency, nominal readiness, corrected source3 rounding and always-B Sparse Jain. The finite-Heavy quota direction is now correct. `THEORY_AND_EVIDENCE.md` and `hypothesis-status.json` are factually suitable for integration within their stated scope. Findings 2–5 remain conditions on the manuscript narrative/provenance, not failed numerical checks.

Repository-relative abbreviations used below:

- `B = artifacts/implementation/cgof-rtl-diagnosis/`.
- `C = B/confirmation-finite-heavy-fixed-20261029/`.
- `P = B/aggregate-current-20261029.json`.
- `S = artifacts/implementation/insight-screen/current-production-20261028/`.
- Raw confirmation files are located through `C/aggregate.json:finite_heavy.inputs_sha256` and their `(job.seed, job.high_weight, job.lane)` identity; this is an exact locator without copying 80 filenames.

| Reviewed file | SHA-256 |
| --- | --- |
| P | `da0a2fd16a40f2eea871be967a6f7e93fa454544bdd19f015856199508904097` |
| C/aggregate.json | `0f39a3c5e8342c44d6d05bcfd46cfd249f69f1e7ef5ef15615b63a95aa98226d` |
| C/manifest.json | `2ac939b662c0f3bf970f4861cf01e6dbcb3967b01573c5ac27b8d8371f846407` |
| update-20261029/THEORY_AND_EVIDENCE.md | `e25243f42194f7de8d8d758f7e1348594d7dc37ac3ed967c8ab082ec0ac203f9` |
| update-20261029/hypothesis-status.json | `02ccb0eb92e5b75dbb10aa850e1212599a39803568e33b4a8ed77261096a6f16` |
| docs/experiments/diagnosis-20261027/DIAGNOSIS_SUMMARY.md, after parent's corrections | `95bebbe4cbd9bce3599ed4fbeb64167196e30405d7b2c36bb45868244400e451` |

The last three hashes are review snapshots, not generator pins to refresh automatically. The October 28 plan/release describe a historical snapshot; the public synthesis has intentionally evolved, while the two raw aggregate hashes above remain unchanged.

## Completeness, exclusions and exact source drift

- Checked every one of 80 repaired raw results: exactly seeds 529–548 × weights 1/2 × mixed/isolated; all `status=PASS`, `evidence_kind=SCHEDULER_RTL`; Heavy work and fired count both 5,000,000; `heavy.completed=true`; final `sum(generated)=accepted=fired`. Every generation cohort has `generated=completed`, and its phase completion vectors sum to its cohort totals. There are no missing or duplicate identities.
- All 20 listed run directories have `summary.overall=PASS`, seven PASS steps, eight tests, zero failures/errors/skips/not-run, and `diagnosis_scope.status=PASS`, `source_stable=true`. Their four results each form a complete two-weight/two-lane grid. Verified all 100 `finite_heavy.inputs_sha256` entries plus all 20 `scopes_sha256` bindings. For each run, all 31 source members in `sources.zip` match the scope's before/after hashes. The repaired source variant is `cd18f19782370166f2d1c7ba56f255bf94b3eba7e9a94322e2fd2836b5488f49`, with no internal source drift or partial runs.
- `C/manifest.json:prior_failed_batch` identifies `B/confirmation-finite-heavy-20261029` and run `B/20261028T202434Z_267411`. The latter has `summary.overall=FAIL`, two failed mixed jobs at seed529, and `AssertionError: incomplete generation cohort` in both mixed logs. Its result set is two isolated successes plus two mixed failure records. None is an input to the repaired aggregate. The failed run has no completed source archive/scope; its manifest records the old source hashes.
- Independently compared the failed manifest and an archived exploration source with repaired sources. Exactly two of 31 files changed: `sim/experimental/cgof_diagnosis_traffic.py`, `2b67019f21ab3da588d3a27702f9fcef6e165d794c493a231d34b2f5c62ece9b` → `de773579475a0e3b15ed488045801d16a6b16849d9b38c9bdab4e2a3ffe29498`; and its regression test, `997b08f0aaec7d8421fcbd395b35065c4ca67db9a5efb6217e688bfb58d1dfe5` → `8cee3feddf69a426425b3cc69123c58dc6346a30e29205e4353aea8459700bee`. The production change is only `DiagnosisTraffic.cohort`: replace `not drain_started` with `cut_cycle is None or k <= cut_cycle`; the test now asserts that the closing active cycle belongs to `finite-heavy`. RTL, reference-policy logic and the measurement implementation did not change. Do not silently combine the old and repaired cohorts as one source variant.
- C's `status.txt` remains `STOPPED_OR_FAILED`. This is a stale batch-launcher status after interrupted/resumed execution, not a verdict on the complete per-seed grid. C's `completed-runs.txt` lists all 20 accepted directories. Accepting the complete result grid is justified; claiming every orchestration attempt passed is not.
- P's performance population is 30 raw jobs / 60 A/B endpoints: 40 always-ready confirmation endpoints (20 seeds) plus 20 robustness endpoints (five seeds × two readiness patterns × two arms). All 48 bound input hashes match; the aggregator checks complete per-cell seed coverage and unique endpoint identities. Six split directories retain RUNNING summaries with only completed PASS steps, while two resumed directories have final PASS scopes. This is assembled complete endpoint coverage, not eight fully finalized runs. Sampled the completed performance source archive; all 54 members match its before hashes. Across variants, only AGENTS.md changes (`b03c95b8c03b0dde87574def2cd3d4aa0899219c649fefce9d237bff4cbfde94` → `c5637c360bdd8c8a15afc49e2fbde078b73f1241840b93c5680ffbff908a0d82`), also the only difference from `revision-cgof-performance/confirmation-cgof-20261028/source_hashes_before.json`.

## Estimators and independently reproduced numbers

Read `scripts/aggregate_cgof_diagnosis.py` (especially `bootstrap_mean`, `performance_rows`, `finite_rows`), `sim/experimental/test_cgof_diagnosis.py:edge` and result construction, `DiagnosisTraffic.cohort/phase/note_fire/active_cycles`, `sim/performance/followup.py:Gaps`, and `refc/cxl_model/diagnosis.py:fairness_summary`; sampled their archived definitions. Recomputed **both complete aggregate sections** using their read-only analysis functions; performance and finite-Heavy outputs each match the stored section exactly. Separately recomputed all repaired latency and Heavy-gap histogram P99s and all pair completion fields: zero discrepancies. This is post-processing reproduction, not a simulator rerun.

- Sparse P99: pool the three Sparse sources' completed generation-to-fire samples within each run; nearest-rank P99; arithmetic mean of 20 run-P99s. It includes cleanup completions from the active-generated cohort; it is neither the average of source P99s nor a P99 pooled across seeds.
- Heavy gaps: active-phase `gaps[0].samples.inter_service` while the FIFO remains nonempty. Consecutive fires have wall gap1; sink stalls count toward wall cycles. Initial, empty-terminated and censored intervals are separate populations. `heavy_wall_gap_max` is a per-run maximum; the reported aggregate is the mean of 20 such maxima. The observed whole-cohort maximum is 11 for 1:1 and 14 for 2:1, not 9.45/10.85. These are observed uncensored gaps, not a universal starvation bound.
- Completion: `active_cycles=heavy.completion_cycle+1` includes the closing edge and excludes drain. Ratio is mixed/isolated inclusive durations; delay is their completion-cycle difference. Throughput ratio is the reciprocal **within each pair**, using identical Heavy work; its aggregate is a mean of reciprocals, not the reciprocal of the mean completion ratio. It measures Heavy scheduler completion, not total memory throughput or application slowdown.
- Intervals: `bootstrap_mean` uses 10,000 seed-level resamples of size20, Python RNG seeded by the first16 hex digits of the canonical SHA-256 of the statistic key; sorted samples at zero-based indices249/9749 give the percentile limits. Quota contrasts bootstrap the 20 within-seed differences (`2:1 − 1:1`). These are marginal descriptive intervals, with no simultaneous-coverage/multiplicity guarantee. Degenerate [3,3], [4,4], [1,1] reflect identical observed run-P99 values, not zero uncertainty about untested workloads.

| Finite near-profile statistic | 1:1 mean [95% interval] | 2:1 mean [95% interval] |
| --- | --- | --- |
| Sparse run-P99, cycles | 3 [3,3] | 4 [4,4] |
| Run-maximum Heavy wall gap, cycles | 9.45 [9.15,9.75] | 10.85 [10.45,11.35] |
| Heavy wall-gap run-P99, cycles | 3 [3,3] | 3 [3,3] |
| Mixed-minus-isolated completion, cycles | 3.05 [1.45,5.05] | 3.00 [1.40,5.00] |
| Mixed/isolated completion ratio | 1.00000048799413 [1.000000224015324,1.0000008079500087] | 1.0000004799951348 [1.0000002240008359,1.0000007999618958] |

Paired 2:1-minus-1:1 fields in `finite_heavy.quota_deltas`: Sparse P99 +1 [1,1]; mean run-maximum gap +1.40 [1.10,1.75]; wall-gap P99 0 [0,0]; completion ratio −7.9989953e−9 [−2.3996986e−8,0]. The completion contrast is one fewer cycle in seed542 and zero in the other19 seeds; its mean delay contrast is −0.05 cycle. No equivalence margin/test was predeclared.

## All-seed behavior and temporal fairness boundary

All 80 raw `classifier` arrays have length1, `window=0`, `closing_cycle=4999999`, and the same H→B_H transition for source0. All Sparse sources stay H even in isolated runs because the reset/UP rule preserves H. There is **no effective-class change** in any mixed or isolated lane. The aggregate's `classifier_transitions.mean=1` counts an encoded-state change, not an effective-priority transition.

| Seed | Mixed−isolated completion 1:1 / 2:1 | Heavy maximum gap 1:1 / 2:1 / isolated |
| --- | --- | --- |
| 529 | 0 / 0 | 9 / 10 / 9 |
| 530 | 1 / 1 | 11 / 14 / 8 |
| 531 | 1 / 1 | 10 / 11 / 7 |
| 532 | 11 / 11 | 9 / 11 / 8 |
| 533 | 2 / 2 | 8 / 10 / 7 |
| 534 | 0 / 0 | 9 / 11 / 8 |
| 535 | 3 / 3 | 10 / 12 / 9 |
| 536 | 0 / 0 | 10 / 10 / 7 |
| 537 | 4 / 4 | 9 / 11 / 8 |
| 538 | 8 / 8 | 9 / 10 / 7 |
| 539 | 2 / 2 | 9 / 12 / 7 |
| 540 | 0 / 0 | 9 / 10 / 7 |
| 541 | 4 / 4 | 9 / 10 / 7 |
| 542 | 4 / 3 | 10 / 11 / 8 |
| 543 | 4 / 4 | 10 / 11 / 7 |
| 544 | 0 / 0 | 9 / 10 / 7 |
| 545 | 1 / 1 | 9 / 10 / 8 |
| 546 | 0 / 0 | 10 / 11 / 8 |
| 547 | 16 / 16 | 9 / 10 / 7 |
| 548 | 0 / 0 | 11 / 12 / 7 |

Sparse P99 is3/4 in every seed; Heavy wall-gap P99 is3 in every mixed and isolated run. Ready-opportunity gap P99 is2 mixed versus1 isolated for all seeds. Mixed eligible-ready maximum is4 for 1:1 and6–7 for 2:1. Isolated maxima are7–9 wall cycles (mean7.55). Thus larger mixed wall gaps cannot be interpreted solely through average completion. The newer 20-seed Heavy generation-to-fire run-P99 is21 in one seed,22 in14 and23 in5; do not carry over the old single-seed value23 as a cohort-wide constant.

At active cutoff, only seed529 at both weights and seed542 at2:1 need one drain cycle (one source3 Sparse completion). Their active demand-L1 is about3.63e−7; every other mixed job's active L1 is zero. Hence the aggregate L1 means 1.82e−8/3.63e−8 reflect almost-complete finite inputs. Raw Jain≈.288367 and Sparse Jain≈.999993735 are descriptive shares under unequal demand; none proves equitable time-local allocation. The reported fairness uses active snapshots, whereas final generated/accepted/fired conservation includes drain.

Thirty-nine of40 same-lane, same-seed cross-weight `trace_sha256` values match. The exception is mixed seed542, where completion stops generation one cycle earlier at2:1. Mixed/isolated trace configurations match after removing `include_sparse`, and Heavy/sink generation uses common deterministic seed-based functions; complete trace digests differ with included Sparse events and completion-driven stopping. Describe this as common exogenous generation rules and paired seeds, not 80 identical full input traces or a fixed identical realized Sparse population in every contrast.

## Mechanism interpretation and new model-screen context

`rtl/experimental/cxl_cgof_sched.sv` explicitly gates eligibility by FIFO head validity and remaining credit, refills when no active source is eligible, overwrites unused credit on refill, charges only actual fires, and retains held offer context. All-High refill vectors are (1,1,1,1) versus (2,2,2,2). Their normalized entitlements agree under sustained backlog; with intermittent active sets, credit budgets/refill timing can differ. This code-level explanation is consistent with native coverage: mixed confirmation sums `credit_blocked_older=7,096,790/6,209,950`, `reentry_fires=649,122/6,279,842`, and `refill_fires=100,000,009/50,000,003` for1:1/2:1. These counters substantiate exercised credit/refill behavior; they do not isolate every causal contribution or prove a general waiting-time theorem.

Near profile uses Heavy p=.8, three Sparse sources p=.02 each and ready p=.9. The nominal offered rate .86 is below .9, giving context for completion differences of0–16 cycles over roughly6.25M cycles. A spare-capacity explanation is plausible, but needs matched load/phase controls for a stronger causal claim. Overload-model completion/throughput contrasts are small but nonzero and directionally adverse to CGOF versus Main; “flat throughput” must mean practically small in the stated cohort, not exact equality, proven equivalence, or higher completed CXL bandwidth.

For `S/evaluation/summary.json`, verified all68 ingested hashes (60 HOG model jobs and8 feedback jobs), the validation-file hash and source-archive hash/content. The 60-job HOG screen spans12 policies × seeds509–513. `gate.candidates` records six age-rescue threshold/quota settings with zero paired P99 improvement in all four cold/trained A/B endpoints. CGOF2:1 has five-of-five improvements in each endpoint; model mean differences versus Main are −16.2/−17.8 cycles cold A/B and−9.0/−8.8 trained A/B. This is a candidate-screen result using exploration seeds, not new held-out confirmation or an age-policy impossibility result. There is no need to crowd the main report with all rejected settings; it can explain the design search in the supplement.

Eight feedback jobs use one seed509 and four actual W5M model windows (20M active cycles), with capped closed-loop producers, deliberate stalls, churn and role switching. The sampled CGOF job has `feedback_config.source="closed-loop capped producers; not paired latency evidence"`. The evaluation's `scope=MODEL_ONLY` overrides its potentially misleading `production=true` flag. These jobs establish exercised model mechanics/advancement-gate checks; they do not complete multi-seed, multi-window finite-Heavy RTL H3. Existing accepted report/model evidence already motivates allocation over simple age rescue, so this screen is useful context rather than an additional independent confirmation population.

## Safe narrative and hypothesis disposition

Suggested report statements:

> In twenty paired-seed finite-work RTL trials, both settings complete five million Heavy requests. With all sources effectively High throughout, one-credit and two-credit rounds have identical relative source weights but different temporal service behavior: Sparse run-P99 is3 versus4 cycles, and mean run-maximum Heavy wall gap is9.45 versus10.85 cycles. Mean mixed Heavy completion exceeds isolated completion by3.05 and3.00 cycles, respectively.

> The current-source CGOF replay reproduces the previously reported1.10/12.35-cycle A/B means. Separate five-seed robustness runs yield5.00/20.40 under Bernoulli readiness and17.00/27.00 under periodic readiness, both at nominal75%. Their differing temporal patterns and slightly differing realized ready fractions motivate measuring tail delay alongside average service availability.

Avoid carrying forward “below-High,” classifier “convergence” from a short initial-map control, universal Sparse “protection,” proof of no starvation, or exact/long-term throughput equivalence. Continuous-backlog oldest-first/eligible-RR equality is restricted to that tested endpoint; intermittent-ordering controls remain open. Reusing seeds529–548 in a different workload does not create another20 independent seeds for the original A/B estimate.

Final read-only critique of the parent's two new files: accepted after the all-80/temporal-population/readiness edits. Their conditional sustained-backlog share derivation is sound at the service-opportunity boundary. H1/H2 `report_integration_ready=true` applies to their explicitly supported conditional statements, not closure of the full hypotheses. H3 `PARTIAL_SUPPORT_SINGLE_WINDOW` correctly describes20-seed completion replication, while at least three finite-work boundaries, under/near/over loads, role switching, finite-harness readiness sensitivity and same-harness Main/WRR/IWRR contrasts remain unrun. H4/H5 remain unverified. No further factual blocker is present in those reviewed versions.

ARS statistical-fallacy scan:11/11 categories considered. Specific risks are ecological overreach (scheduler→application), survivorship/selection (failed and interrupted batches must be disclosed), look-elsewhere/forking paths (candidate screen and many marginal intervals), and unsupported causal/equivalence language. No observed Simpson reversal appears in the complete per-seed quota contrast. Base-rate/diagnostic-screen and clinical selection patterns are inapplicable; no pre/post regression-to-mean or reverse-causality inference is made. The controlled RTL quota comparison supports local intervention effects; it does not remove workload-selection limits.

Final receipt: only this evidence-review Markdown was written. No manuscript, generator, theory/status file, raw artifact, RTL, simulation, EDA or application measurement was modified or launched. Evidence is accepted for the bounded numerical/manuscript update; compiled report language/layout acceptance remains with the parent.
