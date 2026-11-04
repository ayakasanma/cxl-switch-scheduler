# Controlled N4 descriptor performance follow-up —2026-10-22

Status: **ACCEPTED:42/42 formal RTL runs PASS**, all three scope exits0 and independent
raw-evidence audit PASS. The owner approved the
review recommendations; [scope and measurement plan](FOLLOWUP_PLAN_2026-10-22.md).
Final report, its existing dirty manuscript/literature edits and PDF remain untouched/unbuilt.

## What these tests add

The previous180 primary cases measure100k cycles, before Main's W5M classifier changes class.
They establish cold all-High behavior and queueing under shared traffic, not adaptive benefits.
The existing Main production tests cover real classification under predictable low offered load.
This follow-up connects the two with actual trained-state competition, controls that separate
offered load from sink readiness, complete generated-request cohorts, and per-source service gaps.
It does not change the architecture or imply application IPC/slowdown, DRAM bandwidth, full CXL
utilization, a general fairness theorem, worst-case execution time or physical PPA results.

## Implementation and independent review

Existing CLI Claude Code2.1.306 / RTL Agent Team0.14.6 were verified and the focused workflow
`/rtl-agent-team:rtl-p5s-func-verify descriptor-performance-controlled-followup` actually invoked,
requested Opus5.5/medium. Sessionb257b3e2-ae45-498c-a0db-d6edee42dba3 retried429 and exited1
after195.141s with weekly quota exhausted (reset15:00 Asia/Taipei). No native code/PASS claim.
Owner-authorized GPT6.1Sol/high fallback wrote five isolated verification files, froze them, and
Codex independently reviewed actual inputs/outputs, instrument logic, raw evidence and schemas.

Frozen implementation files: `scripts/run_descriptor_followup.py`, `sim/performance/followup.py`,
`sim/performance/test_descriptor_followup.py`, `sim/performance/tests/test_followup.py`,
`sim/performance/README.md`. The thin launcher extends the existing strict run_verify engine;
it does not replace the compile/simulation subprocess flow or alter existing milestone entries.
Existing independent policy oracles, model-free pin/history rules, full105 descriptor scoreboards,
input hold, FIFO/response conservation and state accounting remain active on every real RTL edge.
Performance timestamps/counters come from observed pins and reconstructed history, not model exports.

Parent added `scripts/audit_descriptor_followup.py` and hand-derived statistics tests before
formal scope startup. It independently recomputes histogram statistics without importing the new
instrument or its streaming-statistics helper, and checks whole-population/cohort conservation,
direct latency sum identities, completion-phase matrix, snapshots, eligibility and exact matrices.
All source files were frozen before formal execution; report updates do not change the source manifest.

## Pilot and rejection controls actually executed

Final pilot: **DF-pilot/20261022T012452Z_282**, INFRA_SMOKE_PASS, captured outer processexit0;
43 unit tests and21 actual cocotb simulations, nine strict lint parameter sets, no failure/error/skip.
The21 consist of12 short controls,3 finite4096 batches,6 reduced-W64/256 training cases.
Reduced-window cases are infrastructure-only and production_evidence=false; they are not W5M
evidence or independent new seeds in the final matrix. Source hash manifest matches the final pilot.

Parent reran **73 tests and16 subtests PASS** (43 new verification tests,27 prior recorder/audit
tests,3 independent histogram tests); this is not73 RTL simulation runs. Hand and negative cases
exercise phase carryover/censoring, ready versus wall gap, direct P99 versus stage-P99 sum,
missing population/response, drain timeout, wrong policy/hash/length/schema, nonzero exit,
missing/duplicate/empty matrix, failed-run acceptance and pilot/production mislabeling.

All earlier pilot attempts remain archived. First attempt raw simulations/units passed but its
summary incorrectly advertised milestone acceptance; it is excluded and treated as infrastructure
only by this review. Early attempts1/2 wrote empty outer-exit files: numeric launcher exit NOT_RECORDED,
not assumed0. Attempts3/4 capture actual process0 with JSON. No failed simulation is hidden by
these reporting repairs, and duplicate pilots are not additional independent performance samples.

Evidence root: ignored `.setup-logs/implementation/descriptor-followup-20261022/` contains native
prompt/settings/stream/stderr/exit, fallback prompt/diff/frozen-source manifest, all attempts,
unit JUnit, process commands/exits, parent audits and before/after protected-file snapshots.
No credentials or proprietary libraries/tools are added to Git.

## Metric and timing boundaries

N4, D16, M1, full105; FCFS/POLICY0, RR/POLICY1 quantum10, Main/POLICY2, real production W5M.
Initial3 reset cycles are excluded. Warmup/measurement/drain use a single trace-relative cycle
axis with half-open boundaries. Simulation clock10ns is separate from the25ns synthesis constraint;
report latency in scheduler cycles without silently substituting either for application time.

Counter phases count **events in the phase**. Generation and acceptance cohorts each hold exact
per-source histograms for generation→acceptance, acceptance→fire and directly generation→fire,
including their later drain completions. The3D completion matrix records generation/acceptance/fire
phase crossings. P99 is exact nearest-rank; stage P99s are never added. Cohort mean sums can be
checked because they refer to the same complete request population.

Unlike the old primary boundary-only drain, these new tests stop generation and keep **all**
producer-pending requests active, continue the specified absolute-cycle ready trace, and complete
all FIFOs/responses under a checked timeout. This removes final generated-population censoring
for these finite runs. The measurement-end pending counts/ages remain frozen cut snapshots;
later completion/drain does not turn the measured interval into a steady-state run. Drain-only
acceptance cohorts and warmup carryover remain separate from measurement acceptance cohorts.

FIFO occupancy is accepted−fired pin history sampled pre-edge. Producer backlog is after current
generation/before current acceptance. Mean/max state and nonempty eligible cycles are recorded
per source. Output cycles partition into fire, idle-ready, valid/not-ready sink stall and idle/not-ready.
An eligible FIFO with ready but no fire is an avoidable bubble and fails the test. Successful
slot utilization=fire/cycle; ready-opportunity utilization=fire/ready, with undefined zero denominator.

Service gaps require continuously nonempty FIFO work, not merely producer backlog. Count both
wall slots and sink-ready opportunities. Initial eligible wait and inter-service intervals are
separate; phase boundaries split left-/right-censored intervals, excluded from full-gap statistics.
An observed largest gap is not a proven starvation bound. Warmup logs are periodically trimmed,
unique descriptors use bounded outstanding-tag checking, and completed warmup requests are not
retained as an ever-growing list/set. Finite overload pending queues/histograms still consume memory.

## Formal run identities (not acceptance by their existence)

| Scope | Run ID | Declared runs | Configuration |
| --- | --- | ---: | --- |
| DF-controls |20261022T012724Z_281|36|four cases×seeds509..511×three policies,10k warmup+100k measurement|
| DF-finite |20261022T012724Z_283|3|seed509,4096 requests total,1024 generation cycles,complete drain|
| DF-trained |20261022T012724Z_287|3|seed509,10M real training+100k contention measurement,complete drain|

The three scopes run concurrently, each `-j3 --make-jobs2`; preserve per-job timing and source hashes.
Partial PASS records are not an accepted aggregate. Full scope requires actual strict compilation,
unit/lint/simulation/JUnit, exact cases/params, regenerated intended trace hashes, whole-population
completion and unchanged source manifests. No failed/skipped/incomplete scope is waived.

The trained performance case has **two** full real W5M windows, just enough for Main's two-window
hysteresis, followed by100k observation; it does not replace the existing M5-production20M/four-window
correctness evidence or claim another full-window response after contention changes. Its quiet
training closings also do not replace earlier closing-fire/held-grant boundary tests.

## Reproduction

```sh
source scripts/wsl_env.sh
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-controls -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-finite -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_descriptor_followup.py DF-trained -j 3 --make-jobs 2
python scripts/audit_descriptor_followup.py --runs CONTROLS_RUN_ID FINITE_RUN_ID TRAINED_RUN_ID --output artifacts/performance/FRESH_FOLLOWUP_AUDIT
```

Keep raw histograms/JUnit/logs/versions/configurations in each artifact run. No old primary run
is overwritten or rerun for this task. No SSH, synthesis/STA/power rerun, external workload,
Algorithm-2 expansion, application/gem5 work or Final-report update is performed.


## Accepted formal outcome

**42/42 actual cocotb runs PASS**, no failures/errors/skips; all strict lint/unit/build/simulation
and exact scope gates pass, all three captured outer exits0. Independent final raw JUnit/metrics
audit accepts36 controls,3 finite and3 trained runs,14 matching intended trace groups.
This is42 formal RTL runs, not a count of repeated unit invocations or reference calculations.

Actual formal nonreset RTL cycles **35,376,594**: warmup30,360,000, measurement3,903,072, drain/response completion1,113,522. Initial126 reset cycles excluded. Selected final infrastructure pilot21 cases adds46,167 nonreset cycles separately; earlier retained pilot repeats are not extra independent samples.


Durable evidence: [independent audit](followup-audit.json),[run/cycle index](followup-runs.csv),
[phase counters](followup-phases.csv),[full per-source/cohort/gap table](followup-per_source.csv),
[pooled per-run latency](followup-run-latencies.csv),[three-seed controls](followup-controls-summary.csv),
[trained mechanism](followup-trained-mechanism.csv),[trained sources](followup-trained-sources.csv),
[source/execution/protection manifest](followup-source-execution.json). Raw exact histograms,
commands, tool versions, parameters, partial checkpoints and JUnit remain in the linked artifact runs.

### Fixed controls: capacity and producer queueing

Below are arithmetic means of three **FCFS run values**, each run pooling requests within its
measurement-generation cohort before computing latency. RR/Main are separately retained in CSV;
similar rounded aggregate values must not erase policy-specific tail/source data. SD/min/max
are in the control summary, no20-seed t interval or application-population inference.
All three latency columns use the same complete generation cohort, including later drain.

| Offered / sink | Fires/cycle | Gen→accept mean | Accept→fire mean | Gen→fire mean | Producer pending at measurement end |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.30 /ready1 | 0.30092 | 0.000 | 1.160 | 1.160 | 0.000 |
| 0.90 /ready1 | 0.89678 | 0.000 | 4.210 | 4.210 | 0.000 |
| 1.20 /ready1 | 1.00000 | 11989.813 | 62.866 | 12052.679 | 21977.000 |
| 0.60 /periodicready0.75 | 0.60134 | 0.000 | 3.465 | 3.465 | 0.000 |

Low offered load limits achieved throughput. In overload, the output reaches1fire/cycle while
producer waiting grows far beyond FIFO waiting. These are finite-window overload/completion
statistics, not stationary response times. No eligible-ready output bubble occurs in any scope.
The periodic-sink control also distinguishes waiting units: for FCFS/seed509/source0, the largest
complete inter-service gap is16 wall cycles versus12 eligible ready opportunities. The two maxima
are statistics over their respective paired sample coordinates; sink stalls are not extra arbitration
opportunities. Full initial/inter-service/left-/right-censored distributions remain in raw evidence.

### Finite batch: same generated work, different recipients of waiting

| Policy | Completed generated requests | Gen→fire mean (cycles) | P99 (cycles) | Observed max (cycles) |
| --- | ---: | ---: | ---: | ---: |
| FCFS | 4096 | 2234.666748 | 4415 | 4469 |
| RR | 4096 | 2234.666748 | 4415 | 4469 |
| FAI_MAIN | 4096 | 2234.666748 | 4415 | 4469 |

Global values happen to match here; per-source latencies differ (see raw/source tables). For
fixed completed work, mean generation→fire equals(sum fire times−sum generation times)/count.
Identical aggregate dispatch times and generated timestamps therefore fix that mean even when
the policy changes which request fires. This identity is not a proof that P99/per-source results
must match in arbitrary workloads. Observed maxima are not WCET.

### Trained contention: class allocation versus per-source equality

Main actually closes two W5M windows with source0 DOWN and others KEEP, producing B_H/H/H/H
then L/H/H/H; next-cycle class pins are checked. Training counts/S and exact closing cycles are
in raw records. No preload, time skip or reduced production W is used. Measurement generates
100k descriptors **per source**, ready1. Every source is FIFO-nonempty/ready on99,999 of100k
cycles; Main also verifies both classes eligible on every post-fill cycle and complete10-fire visits.

| Policy | Fires/cycle | Source0 service share | Jain of equal-demand service | Largest complete eligible-ready gap |
| --- | ---: | ---: | ---: | ---: |
| FCFS | 0.99999 | 25.000% | 1.000000 | 4 |
| RR | 0.99999 | 24.999% | 1.000000 | 31 |
| FAI_MAIN | 0.99999 | 50.001% | 0.749992 | 13 |

Jain=(sum service counts)^2/(4 sum squared counts) is computed **only for this equal-demand,
jointly eligible source comparison**, not for unequal training demand or old primary phases.
It describes source service equality; it is not application slowdown fairness or the owner's
universal desired objective. No uncertainty interval is claimed for one trained seed.

| Policy / source | Effective class | Service share | Complete generation-cohort mean wait to fire | P99 | Observed max | Complete ready gap max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| FCFS /0 | not_applicable | 25.000% | 149999.500 | 296998 | 299998 | 4 |
| FCFS /1 | not_applicable | 25.000% | 150000.500 | 296999 | 299999 | 4 |
| FCFS /2 | not_applicable | 25.000% | 150001.500 | 297000 | 300000 | 4 |
| FCFS /3 | not_applicable | 24.999% | 150002.500 | 297001 | 300001 | 4 |
| RR /0 | not_applicable | 24.999% | 150016.000 | 297001 | 300001 | 31 |
| RR /1 | not_applicable | 25.000% | 149986.000 | 296971 | 299971 | 31 |
| RR /2 | not_applicable | 25.000% | 149996.000 | 296981 | 299981 | 31 |
| RR /3 | not_applicable | 25.000% | 150006.000 | 296991 | 299991 | 31 |
| FAI_MAIN /0 | Low | 50.001% | 49996.000 | 98991 | 99991 | 11 |
| FAI_MAIN /1 | High | 16.667% | 183334.667 | 297999 | 299999 | 13 |
| FAI_MAIN /2 | High | 16.666% | 183336.000 | 298000 | 300000 | 13 |
| FAI_MAIN /3 | High | 16.666% | 183337.333 | 298001 | 300001 | 13 |

The approved10/10 single-output reconstruction apportions visits **per class**. With one source
in Low and three in High, similar class totals need not give equal source shares. This mechanism
can redistribute waiting without improving total throughput; no fairness benefit is assumed or
fabricated. Any changed quota/priority rule would be a new architectural decision, not a test fix.
Full/censored service gaps stay distinct in CSV; largest complete observed gap is no starvation proof.

The measurement is a deliberately changed-load finite transient, shorter than another W5M window.
It establishes trained-state behavior, not later reclassification/recovery, stable long-term fairness,
source-placement invariance or multi-seed application performance. Further N8/16/adaptation sweeps
and trained activity power are deferred. Existing approved architecture and accepted PPA remain intact.

Final protection:188 existing dirty manuscript/literature files,52 protected files and97 frozen
runtime-source files unchanged. No active scope/writer remains for this task. Final report is
not edited/built/rendered; no SSH, new PPA, external workload, gem5 or Algorithm-2 expansion.
