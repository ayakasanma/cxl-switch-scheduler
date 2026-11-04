# One bandwidth-heavy host with sparse hosts: RTL experiment design

## Material Passport

- Origin Skill: ARS experiment-agent; mode: plan.
- Origin Date:2026-10-22, Asia/Taipei.
- Verification Status: **UNVERIFIED / PLANNED; no new RTL run performed**.
- Version Label: hog_sparse_plan_v1.
- Baseline: approved Spec v1.0, existing RTL/model; repository checkpoint a74d29c.
- Authority: owner requests an experiment for the intended Main use case and preservation
  of previous evidence. Final report remains on hold; no manuscript edit/build/render.

## Research question and falsifiable hypotheses

Under one continuously backlogged host and three low-demand hosts, does naturally trained
Main reduce sparse-request latency compared with FCFS and RR10, while retaining useful
whole-switch capacity? This concerns descriptor arbitration, not application slowdown or
physical bandwidth. No assumption that Main must win is built into result acceptance.

H1, primary: Main lowers sparse generation-to-fire P99 relative to FCFS after the heavy
host has naturally moved to Low. H2, separately reported: whether Main improves on RR10.
H3, cost/tradeoff: quantify changes in heavy-host service and producer backlog, alongside
total throughput and sparse demand completion. An H1 result never substitutes for H2.
Mean/tail may disagree; report both and every source. No universal fairness claim follows.

The previous equal-demand trained test demonstrates class allocation, not this use case.
Old primary burst_one changes workload quickly and Main stays all-High for100k cycles.
Existing production has total load0.55 and is a different correctness experiment. None of
these is a trained, persistent heavy-plus-sparse three-policy latency comparison.

## Why an improvement is plausible, without guaranteeing it

The heavy host should get two DOWN windows (H -> B_H -> L); sparse hosts stay effective H.
Main chooses FCFS within the effective class and alternates up-to-ten-fire visits. Sparse
work can be served on a High visit ahead of older Low FIFO entries. Empty High visits
relinquish unused credit; the heavy host can use the remaining capacity. This is not a
permanent50% cap on the heavy host. Existing held transfers cannot be preempted, and a
new sparse request can still wait for the current Low visit.

RR10 already bounds a source visit to ten fires. Main's Low visit also has ten fires;
therefore an advantage over RR10 is not implied. Bursts sharing one High quota may even
favor RR10 in some cases. Finite depth16 also limits the admitted old requests ahead of
a sparse request in FCFS. The experiment must measure, not describe FCFS as unbounded
monopolization or call any capacity loss an intended result.

## Frozen factors and matrices

All cases: common switch_top, N4/D16/M1/full105, FCFS/POLICY0, RR/POLICY1 quantum10,
FAI Main/POLICY2 quota10/10. Same source0 is the heavy host in every formal case;
sources1–3 are sparse. Same clock/reset/interface/FIFO/hold/sink and existing independent
oracles/pin-history rules. No RTL, model, Spec, synthesis or accepted PPA change.

| Stage | Matrix | Timing | Purpose |
| --- | --- | --- | --- |
| Execution pilot |3 policies,seed509,W256|512 training; same two measured profiles and guards below|Check generator, metrics, classes, real RTL, memory and runtime; sensitivity only|
| Formal comparison |3 policies x seeds509–513 =15 runs,W5,000,000|10M real training; two measured profiles per run|Main use-case evidence at production W|

The formal15 runs produce30 policy/seed/profile observations; two profiles within one run
are not independent runs. Five seeds give limited descriptive repeatability, not guaranteed
statistical power or application-population inference. Do not add/drop seeds based on whether
Main wins. N8/16, additional rates, ready-stall sweeps and Algorithm-2 are outside this core
experiment. If the full fixed matrix cannot finish, retain partial results as incomplete.

W4096 is unsupported and must not be used. The W256 pilot may cross many later windows;
allow the classifier to run normally and check actual states. It is not production evidence.
Formal all-host steady demand persists through the first two complete W5M windows; no
preload, time skip, shortened-window substitution or class freeze. Production W remains
unchanged. CLI entry is **NOT_IMPLEMENTED**; extend the existing strict follow-up registry
and passive metrics when implementing, rather than inventing a currently runnable command.

## Self-authored exogenous workloads

The heavy source generates exactly one descriptor per active cycle, independently of ready
or acceptance. Its producer holds the oldest pending request until accepted. This supplies
persistent pressure; it does not force the output to choose that host. Its producer backlog
is expected to grow because combined offered load exceeds capacity. Do not interpret its
finite-window delay as stationary, or confuse unaccepted requests with dropped requests.

Downstream ready is1 throughout the core experiment, including guards and drain. This removes
sink stalls as an explanation for a policy delay difference. Background pressure and sparse
generation continue independently of all DUT pins and policy outcomes.

**Profile A: isolated sparse requests.** For each sparse host and each cycle, generate one
descriptor with probability1/128, independently. Expected aggregate sparse load is3/128
(0.0234375/cycle), expected total offered load1.0234375. Bernoulli arrivals can coincide;
do not discard coincidences or unusually long waits. Apply this from reset release through
training and the first measured profile. Use separate deterministic RNG streams for each
source's arrival decisions and descriptor contents, so descriptor generation cannot perturb
future arrival/ready times.

**Profile B: short sparse bursts.** Each sparse host generates one eight-descriptor burst
per1024-cycle block, at a uniformly seeded offset0..1023, independently by host/block.
All eight enter the producer queue in that cycle; the interface still accepts at most
one descriptor per source per edge. A102,400-cycle phase contains100 blocks: exactly800
generated requests per sparse host,2400 total, average demand1/128 per host as in A.
This comparison is paired by policy within profile; do not claim that the two profiles
have identical event counts or isolate arrival shape with exactly equal finite A populations.

Use unique full105 descriptors with a32-bit serial tag, no outstanding-tag reuse. Versioned
trace headers include all rates, phase lengths, seed, N/D, heavy ID, W, burst rule and timing.
Hash canonical generated events/ready for the complete active trace. Each seed/profile must
match across policies; generation must never wait for DUT completion or be rescheduled to
favorable class phases. Record the actual remaining class/source quota at sparse arrivals
passively, to explain waiting and check phase diversity without steering those arrivals.

## Timeline, warmup and completion cohorts

Let T=2W. Cycle0 is the first non-reset trace cycle; exclude the initial reset edges.

1. **Training [0,T):** heavy1/cycle plus profile A. Main's first two actual closing cycles
   are W-1 and2W-1, with closing fire included, S=sum(B), next-cycle class activation.
   Assert observed heavy DOWN twice and sparse effective H; retain actual B/S/evidence.
   No window emptiness/generation-count assumption replaces observed fire accounting.
2. **Cold diagnostic:** for production only, also record sparse generation cohorts in
   [T-101024,T-1024). The offered process continues unchanged afterward. Check these
   requests complete before T while background pressure is active; otherwise flag boundary
   contamination explicitly. Main and FCFS must match pins cycle-by-cycle before T because
   every source remains effective High. This is a control, not another independent seed.
3. **Trained A [T,T+100000):** unchanged offered process and heavy pressure. Record each
   sparse generation cohort, all acceptance/fire events, snapshots and class/visit context.
4. **A completion guard,1024 cycles:** stop new sparse generation, keep every pending producer
   active and continue generating heavy requests. All A sparse cohorts must complete here
   at the latest. The guard is outside measured throughput and inside A latency completion.
5. **Trained B,102400 cycles:** heavy pressure plus profile B, starting with no sparse pending
   work after the checked guard. Record the B generation cohort and actual service.
6. **B completion guard,1024 cycles:** same background-on completion rule. Do not improve
   sparse latency artificially by switching off the heavy host before sparse completion.
7. **Final drain:** stop all generation only after both guards. Complete every remaining
   generated/accepted request and response, including heavy producer backlog, using a checked
   request-count-derived timeout. Retain its counters separately; final drain is not measured
   useful throughput or fixed-class latency evidence.

Formal active generation/guard timeline ends at T+204448=10,204,448, before the third
classification at14,999,999. Classes must stay L/H/H/H during measured A/B and guards;
afterward final drain can reclassify normally. This establishes fixed trained-class behavior
under continued heavy pressure, not long-term adaptation beyond another full W5M window.
Cold diagnostic and trained A sample different time segments: cross-policy pairing is primary;
do not treat their raw difference as a matched identical-arrival causal estimate.

The pilot uses T512 and omits the nonexistent production cold-diagnostic interval. During
its longer measured phases, verify actual classification on every closing rather than
silently forbidding later windows. Metric labels must distinguish this from formal timing.

## Metrics and estimands

**Primary endpoint:** each run/profile's nearest-rank P99 of direct generation-to-fire
latency, pooling sources1–3 of that phase's complete generation cohort. Profile A vs FCFS
is the prespecified primary comparison. Separately retain per-source P99 so pooling cannot
hide a disadvantaged sparse host. Do not add generation-to-acceptance and acceptance-to-fire P99.

Secondary endpoints, each in cycles unless otherwise specified:

- Sparse direct mean/P99/observed max and generation-to-acceptance / acceptance-to-fire
  mean/P99; request counts and guard completions. Right-censored ages at phase end remain
  recorded even though eventual completion is required. All sparse generated requests count.
- The same paired endpoints vs RR10 and the burst-profile endpoints; report them independently.
- Heavy and total completed transfers per measured cycle, actual input acceptance, per-source
  generated/accepted/fired counts, and expected/actual offered demand. No byte-bandwidth label.
- Producer backlog and FIFO occupancy mean/max/end; FIFO-nonempty ready opportunities,
  full/held cycles, observed service gaps with wall/ready units and censored intervals.
- Main actual class map, visits, empty-class relinquishment, quota at sparse arrival and
  any held transfer. Explain why the heavy host can get much more than50% under sparse demand.
- Useful output-slot and ready-opportunity utilization, avoidable bubbles and request/response
  conservation. Ready1 makes their numerical denominators equal here; do not generalize that
  equality to previous ready-stall experiments.

Sparse completion ratio must reach1 with the heavy host still active. Service equality/Jain
is not the primary fairness criterion for this asymmetric demand. Report sparse waiting
against the offered sparse load; do not call the heavy host's larger service share unfair
when it supplies nearly all work. Application slowdown and application speedup remain unmeasured.

## Analysis and claim rules, fixed before execution

For each seed/profile/baseline, compute Delta=P99_baseline-P99_Main and percentage reduction
100*Delta/P99_baseline. Positive favors Main. Show all five paired seed values, arithmetic
mean, sampleSD and min/max of run-level metrics/differences; do not treat request samples,
sources or two profiles as independent seeds. A mean of run P99s is not a pooled-request P99.
No formal p-value or population-wide confidence claim is planned from five seeds; plot
seed points or explicitly labelled min–max ranges rather than unsupported95% intervals.

- Consistently positive paired deltas support a benefit in the tested scenario; state exact
  magnitude and source-level exceptions. Mixed signs are a mixed result; zero/negative values
  are no demonstrated benefit/regression. Scientific non-improvement is not a test failure.
- Main vs FCFS and Main vs RR10 are separate claims. Better than FCFS but tied with RR10
  is a valid outcome. Mean improvement does not establish P99 improvement or vice versa.
- Show absolute total/heavy throughput changes beside sparse latency. Diagnose any active
  eligible-ready bubble; a correctness failure cannot be traded for a favorable latency value.
- Profile B is a robustness check, not permission to discard A or choose the winning profile.
  Cold Main=FCFS plus subsequent divergence helps explain the class mechanism, not a claim
  that classification costs or application effects have been isolated experimentally.
- Do not impose a favorable minimum speedup as simulator PASS. Acceptance requires valid
  execution/conservation/labels; benefit is an independently evaluated result.

If no Main advantage vs RR10 appears, retain it and relate it to the common ten-fire quantum.
Do not change quotas, FIFO depth, hold/preemption, pipeline, traffic seeds or output timing
to obtain a win. Any new architecture is separate owner-approved work.

## Implementation, validation and execution gates

No implementation or command execution is claimed by this plan. Reuse the existing WSL
Verilator5.052/cocotb2.1.0/Python3.12 strict runner, Metrics, independent per-policy TBs/oracles,
and tag-response scoreboard. New generator is self-authored/project-owned; no external trace,
SPEC, SSH, gem5, Algorithm-2 or new dependency is needed. Native Claude RTL Agent Team
Opus5.5/medium implements verification when execution begins; actual quota exhaustion permits
the existing Sol/high fallback. Codex reviews independently; one implementation writer.

Before full execution: validate hand-derived latency/cohort/guard examples, independence of
arrival RNG and descriptor RNG, exact burst counts, no hidden sparse exclusions, full-hold
semantics, trace identity across policies and source/version/evidence labels. Negative controls
must reject changed input trace, missing sparse completion, early heavy stop, wrong class,
shortened-production mislabel, bad P99 and missing/failed/skipped matrix jobs.

Run the three-policy W256 pilot before the15 production cases. Use measured pilot throughput,
actual prior10M-run costs and observed backlog/histogram memory to record a conservative cost
estimate. The previous three-policy10M follow-up took about41minutes concurrently;15 long
runs may require several hours. The short pilot alone cannot predict full memory/runtime.
Plan concurrency at three jobs/two build jobs each only if memory permits. Log every250k
real cycles, process status, peakRSS, subprocess/JUnit results, and a24-hour hard timeout per
long simulator. Retain failures/timeouts/partial runs as such, never silently relabel them.

Preserve prompts/agent model/effort, exact commands/tool versions, source Git revision plus
dirty-source manifest, parameters, phase definitions, complete trace hash, raw histograms,
snapshots/JUnit/logs and numeric exits in fresh artifacts. Source freeze before formal runs;
independent audit must check exact15 matrix/5 paired trace groups, all30 profile records,
correctness, cold control and guard completion. Keep raw data, summaries and provenance
separate. No numerical results are filled into this plan in advance.

Expected report output is one sparse-P99 comparison figure with two labelled profile panels,
seed points/range definition and external legend, plus a small total/heavy throughput table.
Figures are deferred with the Final report; no new manuscript rendering now.

## Existing evidence preservation

Existing accepted primary180, controlled follow-up42 and placement42 remain unchanged, with
their positive and negative outcomes. Their source records are fe728d0,949470f and a74d29c
respectively. See [preservation manifest](EVIDENCE_PRESERVATION_2026-10-22.json) for current
tracked performance-file hashes and264 verified raw metric hashes. The latter are read-only
checks, not new RTL cycles or an independent re-run. Failed/incomplete historical attempts
and the W4096 pilot failure stay in the existing records. No baseline data is overwritten.
