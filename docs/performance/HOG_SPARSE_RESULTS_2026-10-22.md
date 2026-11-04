# Heavy-host/sparse-host RTL experiment — execution record

## Material Passport

- Origin Skill: experiment-agent; execution of the owner-approved saved plan.
- Origin Date:2026-10-22, Asia/Taipei.
- Verification Status: **ACCEPTED:15/15 actual production RTL runs PASS; independent audit PASS**.
- Design: [hog_sparse_plan_v1](HOG_SPARSE_PLAN_2026-10-22.md), commit906ac86.
- Existing evidence is retained, including all losing/negative or incomplete prior attempts.
- Final report remains untouched/unbuilt; no RTL/refc/Spec/PPA changes or SSH.

## Native workflow and authorized fallback

Actual Claude Code2.1.306, enabled RTL Agent Team0.14.6, focused invocation
`/rtl-agent-team:rtl-p5s-func-verify hog-sparse-latency-experiment`, requested
Opus5.5/medium. Sessionba43dac0-d728-4c88-9e91-25be271a795b returned weekly quota429,
child exit1 after248.676s before code changes. Invocation-local model/effort settings were
used; routing/global settings unchanged. No native implementation/PASS is claimed.

Owner-authorized GPT6.1Sol/high fallback /root/sol_hog_sparse was the sole verification-tool
implementation writer and has frozen all five files. Codex owns this record and independent review. Additions are
one strict-runner launcher and four new performance/helper/test/readme files; existing test
code, RTL/models, approved architecture and accepted PPA are protected.

Ignored evidence root `.setup-logs/implementation/hog-sparse-20261022/` preserves prompt,
settings/stream/stderr/numeric exit, plugin/tool versions and source/protection snapshots.
The entry preservation manifest covers348 files, including188 pre-existing dirty Final
manuscript/literature files. Pilot, full runs and independent audit will get separate actual
IDs/exits/results; none are filled in before they execute.

## Planned execution gates

The following paragraphs preserve the pre-execution gates. Actual completed results follow.
Three-policy W256 seed509 pilot first, then review/freeze; only after that the full N4
productionW5M/three policies/five seeds matrix of15 runs. Every formal run performs10M
real training cycles, two measured sparse profiles and background-on completion guards,
then complete producer/FIFO/response drain. Sparse direct generation-to-fire P99 is the
primary endpoint, with per-source tails, heavy service/backlog and total throughput retained.
Main-versus-FCFS and Main-versus-RR10 are distinct comparisons. No favorable performance
threshold is a correctness PASS condition.

## Actual pilot and formal startup

Focused units26PASS; strict pilot `HS-pilot/20261022T034155Z_369` outerexit0, three strict
lint sets,26 units and three actual RTL simulations PASS, scope gate PASS, identical source
hashes before/after. Independent raw audit3/3PASS and13 intentionally corrupted actual-metric
records rejected; parent pooled-tail unit checks3PASS. Pilot actual nonresetcycles629,217:
training1536,measurement607200,guards6144,drain14337; initial9 resetedges excluded. Repeated
pilot attempts are not extra independent performance samples or production evidence.

Retained first attempt `20261022T033946Z_567` has real simulator PASS and independent raw
audit, but outer shell-exit capture is unreliable because Windows/WSL expanded shell variables.
Its blank outer-exit file means NOT_RECORDED, never assumed0. Corrected Python subprocess
capture saved actual numeric exit0 for units02/pilot02; no RTL/stimulus changes were needed.

Full `HS-main/20261022T034507Z_311` launched2026-10-22 UTC03:45:02, **15 declared runs RUNNING**,
not accepted by partial completion. Concurrent jobs6/each build jobs2, a routine resource
adjustment from the plan's initial three-job estimate: WSL16 logical CPUs/~14GiB available,
pilot~50MiB RSS/process. Stimulus, matrix, virtual clocks and verification unchanged.
All three strict lint sets and26 unit checks pass before simulations. Every production run
must perform full10M training with progress/RSS monitoring; no shortened/preloaded substitute.
Full scope/actual outer exit/raw15 metrics will be audited only after actual completion.

Pilot sensitivity A/B sparse direct P99 cycles: FCFS18/34, RR10 11/18, Main10/23.
This preliminary result is recorded without extrapolating to W5M: Main is faster than FCFS,
while its burst P99 exceeds RR10 here. All policies full measured capacity; negative/mixed
findings are retained. Formal comparison remains pending and may differ.

## Accepted formal execution and evidence

The startup RUNNING/pending statements above are historical checkpoints. Full scope
`HS-main/20261022T034507Z_311` actually completed UTC05:45:13, outerexit0, elapsed7210.594s
(about2h00m11s). **15/15 cocotb simulations PASS**, three strict lint parameter sets and26
focused unit cases PASS; actual Verilator/make/simulation exits0, raw JUnit zero failures,
errors or skips. Complete scope gate and Codex independent raw audit PASS, five matched
exogenous trace groups, all30 measured profile records. Five Main/FCFS cold pin digests
over the entire first10M cycles match. No model-only export is counted as RTL evidence.

Total **156,657,531 actual nonreset RTL cycles**:150,000,000 training,3,036,000 measured,
30,720 background-on guard,3,590,811 final drain/response completion;45 initial reset edges
excluded. Every run really executes two W5M windows, no preload/time skip. Each Main closes
B_H/H/H/H thenL/H/H/H from observed successful-transfer evidence; classes remainL/H/H/H
through measured A/B and guards. All generated producer/FIFO/response work completes.
Every sparse cohort completes while heavy generation is still active. Five cold sparse
cohorts complete before classification; no sparse completion is silently dropped or deferred
until heavy stops to make latency look better.

Frozen tooling commit70bc6006eaecaaa93b5c9a56939a9a3e2bcf633b contains the actual new code;
execution started at906ac86 with those same isolated files, reconciled by106 file-byte source
manifest before/after. Later Git commits are documentation checkpoints, no simulation-source
change. Simulation/runner versions/configuration/commands remain in the run artifact root;
Verilator5.052, cocotb2.1.0 and the project Python3.12 environment are preserved. Per-job
reported peakRSS75.19–76.18MiB. No timeout, failed production simulation, skipped seed or
change to the fixed matrix occurred. The only retained execution defect is the pilot01 outer
capture described above. Full15 performance results do not depend on repeated pilot samples.

Durable data: [independent audit](hog-sparse-audit.json),[run index](hog-sparse-runs.csv),
[phase/cohort endpoints](hog-sparse-profiles.csv),[per-source tails](hog-sparse-sources.csv),
[paired P99 deltas](hog-sparse-paired.csv),[run-level summaries](hog-sparse-summary.json),
[source/execution provenance](hog-sparse-source-execution.json). Raw exact histograms,
window records, class/quota-at-arrival contexts, visits, event counters, pending snapshots,
occupancy/backlog/gaps, JUnit and logs remain in each linked metrics artifact. Files in Git
are small summaries/indexes; proprietary EDA assets are not involved.

## Sparse latency: the intended use case has a measured benefit

All values below use **direct generation-to-fire latency in scheduler cycles**. Each mean
column is the arithmetic mean of five per-run sparse means; P99 is the arithmetic mean
of five per-run P99 values, with their min–max range, not a request-pooled P99 or confidence
interval. Each run pools all sparse sources of its complete generation cohort, with every
per-source value retained separately.

| Sparse profile | Policy | Mean latency | Mean runP99 | RunP99 range | Largest observed request latency |
| --- | --- | ---: | ---: | --- | ---: |
|A: single sparse arrivals|FCFS|16.3921|18.2|18–19|22|
|A: single sparse arrivals|RR10|5.5979|11.0|11–11|13|
|A: single sparse arrivals|Main|5.5296|10.0|10–10|11|
|B: eight-request bursts|FCFS|23.2989|33.8|31–36|45|
|B: eight-request bursts|RR10|9.1693|17.2|17–18|32|
|B: eight-request bursts|Main|9.3243|20.8|17–24|38|

| Paired comparison | Seeds Main lower/tied/higher P99 | Mean reduction in P99 cycles | Mean paired percentage reduction |
| --- | --- | ---: | ---: |
|A, Main vs FCFS|5/0/0|8.2|45.03%|
|A, Main vs RR10|5/0/0|1.0|9.09%|
|B, Main vs FCFS|5/0/0|13.0|38.64%|
|B, Main vs RR10|0/1/4|−3.6|−20.78%|

Percentage reductions are calculated per matched seed then averaged; negative means Main's
P99 is higher. The mean of percentages differs from a ratio of mean P99s. SampleSD/min/max
and each seed value are in JSON/CSV. No p-value, population-wide interval or guaranteed
minimum benefit is inferred from five synthetic seeds.

All15 source/seed A pairs have lower Main P99 than FCFS; versus RR10,14 are lower and one
ties. In B all15 source/seed pairs improve over FCFS, while against RR10 one improves,
four tie and ten worsen. These source/seed counts describe exceptions; the three sources
within one run are not independent statistical replications. Pooled results therefore do
not hide an individual sparse-source regression versus FCFS in this experiment.

Cold diagnostic: Main and FCFS both have mean sparse latency16.3842 and P9918 across the
five runs, with exact matching per-seed histograms; RR10 is already near its trained A
result (mean5.6117/P9911). This supports the classifier/service mechanism interpretation,
and also records that Main's protection is delayed until its two-window hysteresis completes.
The cold and trained cohorts contain different time segments/arrivals, so the controlled
cross-policy comparisons at each phase remain the primary evidence, not a same-request
pre/post latency estimate.

Generation-to-acceptance mean is0 in A under all policies: sparse descriptors enter their
own FIFOs immediately. A's advantage comes from arbitration after acceptance. In B the
producer-side mean is3.5cycles for all three (eight descriptors must enter one/source/cycle),
so direct latency includes this shared injection cost. Main's mean acceptance-to-fire is
5.8243 versus FCFS19.7989 and RR10 5.6693. Exact direct P99 is measured per request; no
stage P99s are added. The observed maxima are not WCET/starvation guarantees.

## Throughput and heavy-host tradeoff

Every one of the30 measured policy/seed/profile intervals has **1.000000 transfer/cycle**,
zero avoidable eligible-ready bubbles. Total capacity is unchanged in these ready1 cases.

| Profile | Policy | Heavy transfers/cycle, five-run mean | Heavy share of measured transfers |
| --- | --- | ---: | ---: |
|A|FCFS|0.976728|97.6728%|
|A|RR10|0.976726|97.6726%|
|A|Main|0.976724|97.6724%|
|B|FCFS|0.97657617|97.6576%|
|B|RR10|0.97656445|97.6564%|
|B|Main|0.97656445|97.6564%|

The small per-interval differences include sparse completion crossing phase boundaries;
identical external arrivals do not force identical accepted/fired order. A's Main–FCFS
heavy-rate difference is−0.000004 transfer/cycle on average, not a50% heavy-host cap.
Main's empty High visits relinquish unused credit, so the heavy Low source still uses
about97.7% of output while sparse requests receive shorter waits. Per-phase relinquishment,
charged-class counts and source counts are retained to distinguish allocation from naming.

Heavy pending backlog at A-end averages236931.2 for FCFS and236931.8 for RR/Main; at B-end
239330.4/239331.6/239331.6 respectively. Full raw histories/snapshots retain population counts
and moments. This is expected finite overload from the heavy host offering1/cycle plus sparse
work. It is not stationary heavy delay or unlimited admitted FIFO occupancy; each FIFO is
still depth16. Heavy latency was explicitly not an endpoint, and complete final drain still
accounts for every heavy generated request. Sparse cohort completion is100% before heavy-off.

## Interpretation and boundaries

This directly answers the owner's target scenario: **after natural training, Main protects
low-demand hosts from a sustained high-demand host relative to FCFS**, in both the isolated
and short-burst profiles tested. Aggregate throughput need not increase to obtain that
latency benefit. The earlier equal-demand tests remain valid; they measured a different
question and cannot be used to deny this result or erased because this result is favorable.

The stronger claim "Main is always better than RR10" is unsupported. In A the P99 advantage
is one cycle while mean delays are close. In B, several sparse sources can overlap and
share a single10-fire High visit, while RR10 grants per source; Main's burst tail is often
worse. That is a plausible explanation consistent with the specified visit structure and
recorded behavior, not a separate causal ablation or a reason to alter the approved design.
No change to quotas/FIFO/pipeline/hold or selective seed/profile removal was made.

Two W5M windows create a long response lag for newly appearing interference; this experiment
does not show protection before classification. Measured A/B ends before a third production
window, so this is a finite trained-state study under sustained pressure, not many-window
recovery/steady-state proof. N4 only, five fixed seeds, ready1, self-authored descriptors,
single output/equal atomic service and the project-defined10/10 reconstruction. It does not
establish application IPC/slowdown, byte bandwidth/complete CXL utilization, DRAM-controller
behavior, universal fairness, original-paper cycle reproduction or new PPA/power values.
Existing accepted PPA is reused only with its own constraints/activity assumptions.

## Independent validation and preservation

Codex independently recomputes every histogram's count/moments/extrema/nearest-rank P99,
source-pooling/direct-stage sum identity, phase event and pending snapshot conservation,
all-source final completion, guards, training thresholds/class sets, actual cold pin matching,
raw JUnit/exits, exact matrix/evidence labels, and before/after source hashes. Parent3 pooled
tail unit cases PASS;13 intentional mutations of real pilot and formal results are rejected.
The strict runner separately regenerates each complete external trace before acceptance.
Neither trace regeneration nor read-only audit adds RTL cycles.

Methodological review covers11/11 ARS fallacy categories: profile/source stratification guards
against aggregate reversal; no individual/application extrapolation; no selecting only accepted
or fast-completed requests; no conditioning arrivals on policy outcomes; offered counts/base
rates shown; controlled paired seeds rather than selected extremes/pre-post alone; all trials
and exceptions retained; prespecified primary/profile comparisons avoid winner selection;
all execution repairs/provenance retained; causal language limited to this controlled RTL
boundary; generation precedes observed handshakes, with no response-driven traffic feedback.
No human-study statistical assumptions or significance labels are imported into this experiment.

The348 protected files, including188 pre-existing dirty Final/literature files, remain byte-
identical. Previous264 raw metrics were rehashed against the preservation manifest after
completion and match. Existing positive/negative results, failed pilots and incomplete historical
attempts stay in place. No Final manuscript edit/build/render, SSH, proprietary asset, new
dependency, RTL/model/Spec/PPA change or Algorithm-2/gem5 expansion. Full simulation process
has ended; no active test writer remains.

Reproduce in WSL from the sole existing repository:

```sh
source scripts/wsl_env.sh
PYTHONDONTWRITEBYTECODE=1 python scripts/run_hog_sparse.py HS-pilot -j 3 --make-jobs 2
PYTHONDONTWRITEBYTECODE=1 python scripts/run_hog_sparse.py HS-main -j 6 --make-jobs 2
python scripts/audit_hog_sparse.py --run RUN_ID --output FRESH_AUDIT_DIRECTORY
```

Use a fresh run/audit directory and retain prior attempts. Source, tool versions, raw reports,
all five paired seeds and effect directions are part of the result; a favorable P99 is not
the verification acceptance gate.
