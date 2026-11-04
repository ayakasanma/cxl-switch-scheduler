# DAC/AGE Python model screen

Scope: MODEL_ONLY, exploration seeds 509-513. This code does not implement RTL,
change accepted models, or establish hardware cost or a production winner.
Confirmation seeds 529-548 are rejected before creating output files.

The implementation follows the owner's saved
`.setup-logs/implementation/revision-20261023/prompt.txt`. The earlier native
Opus attempt returned its internal safeguard before writes, exit 0, without
quota exhaustion. This is the separately authorized Python implementation;
it is not fallback RTL. No further delegation was used. The installed
`rtl-agent-team/0.14.6/agents/testbench-dev.md` supplied the directed/random,
per-transaction scoreboard and reproducible evidence workflow. RTL/cocotb and
coverage claims from that agent template do not apply to these Python tests.

## Model API and semantics

`refc/cxl_model/experimental.py` exports `ExperimentalSwitchModel` and `POLICIES`.
Construction accepts `n_src=4, policy="Main", window=5_000_000, depth=16,
desc_width=105, ts_width=32, gap_max=65535`. Supported windows are the accepted
64, 256 and 5,000,000. The production runner fixes N4/D16/105-bit descriptors
and 32-bit timestamps.

- `commit(rst_n=False)` synchronously resets queues, hold, policy and counters.
- `view(out_ready=False, rst_n=True)` returns the accepted `CtrlView`.
- `commit(out_ready=False, in_valid=None, in_desc=None, rst_n=True)` returns
  `ExperimentalEdge(reset, pushed, fired, rescue, closing)`. `pushed` entries
  and the `fired` delivery use the accepted common controller records.
- `choice()` returns the immutable source/context offer, including the DAC
  credit snapshot or AGE rescue designation. It preserves a held offer.
- `classes()`, `window_state()`, `occupancy(source)`, and the `visit`,
  `credits`, `gaps`, `budget`, `service`, `time`, `windows_closed` attributes
  support independent review. `deposit_counter` exists only for wrap tests;
  the runner never uses it.

The model reuses accepted FIFO, hold, readiness and classification functions.
Main 10/10 visit accounting uses the fired offer's context and post-edge
occupancy. Classification includes every closing-edge fire. RR10 and FCFS are
independently expressed policy controls, compared against their accepted
classes on every tested cycle. No accepted source is patched.

DAC2 snapshots High=2/Low=1 credits whenever no beginning-cycle active head
has positive credit; DAC1 uses 1/1. Refill replaces all credits in the same
opportunity, without a bubble or banking. Oldest eligible acceptance time,
then source ID, selects service. Only a fire charges credit. A stalled refill
offer retains the complete credit snapshot through classification changes.
Inactive sources cannot prevent refill, and reentry within a round adds no
credit.

AGE_T16/32/64_K8/16 require both acceptance head age and consecutive eligible
ready-opportunity gap to reach T. Gap saturates at 65535 and clears on own
fire or empty. Budget starts at zero, increases on every normal fire up to K,
and clears on a rescue. Rescue picks largest gap, then oldest acceptance time
and source. A choice equal to the normal source counts as normal service.
Rescue fires contribute to B/S, preserve the open normal visit and spend no
normal quota. The next normal choice rechecks eligibility. Held normal and
rescue offers cannot be preempted. AGE_ONLY removes gap/budget protection and
selects oldest age-urgent heads; persistent urgency can make it equal FCFS.

Absolute local acceptance edges order heads under the timestamp half-range
assumption. Neither selection nor classification reads producer backlog,
generation times, future arrivals, or the passive measurement queues.

## Executable protocol

`scripts/screen_scheduler_insights.py` uses the exact original `hog_sparse.Traffic`
including descriptors and trace hashing. A production run executes two actual
W5M windows before A, with no source loading or class deposit. Each policy has
its own closed-loop producer admission and FIFO/service history.

For each policy/seed, three independent lanes run:

1. Trained starts at reset and consumes the complete original trace.
2. Cold A starts at reset at A's first measured arrival, consuming exactly the
   trained A/A_guard arrivals and descriptors.
3. Cold B independently starts at reset at B's first measured arrival, consuming
   exactly the trained B/B_guard arrivals and descriptors.

The cold lanes have independent classes, windows and visits. Their measured
input hashes must equal their trained counterpart. Every generated request,
including heavy pending work, drains. Statistics retain sparse raw integer
histograms and per-source wall/ready service gaps, with phase boundary
censoring. Completed heavy requests are not retained. Pending producer queues
remain necessary for the overloaded original workload; memory therefore scales
with outstanding work, not completed work. Window histories retain first two
and last eight closes only.

Baseline A/B all-stage pooled and per-source histograms and A/B/guard service
vectors are compared against matching accepted HS seed files. If available,
the actual MSQ B/B_guard archive is streamed and every cycle's occupancy,
heads, producer backlog, handshakes, output source/tag and accepted tags are
compared, plus Main classes and visit state. Its uncompressed hash/row count
must match the diagnosis manifest. Missing archive evidence stays PENDING.

Every configuration records source hashes, exact parameters, seed, raw
histograms, service counters/gaps, timings, RSS on Linux, drain counts, trace
hashes and numeric exit. The run directory also contains validation command
arguments, stdout/stderr, numeric exits and a gate summary. No output directory
is reused. New runs archive exact transitive model, traffic, runner and test
bytes in immutable `sources.zip`, checked against hashes before and after the
run. The dependency list is explicit; unrelated `revision_baselines.py` is
excluded. Validation records and source ZIP digests are bound into each report;
summary records bind report digests. Ingestion rechecks all these artifacts
and the current source revision. Output is restricted to a new child of
`artifacts/implementation/insight-screen/`.

The gate requires all 12 policies x 5 exploration seeds at W5M, passing
directed/differential checks, consistent source/trace hashes, accepted baseline
histogram/service joins, representative seed509 cycle alignment, conservation,
held stability and zero avoidable bubbles. Paired per-run P99 uses
generation-to-fire. A candidate must improve cold B OR trained B mean by at
least one cycle with at least four individual improvements; cold A AND trained
A means may regress by at most one cycle. Maximum original sparseHOG heavy
service fraction loss is 0.0001. The lower worst ABSOLUTE candidate mean P99
across cold/trained B breaks ties (not the mean delta);
AGE wins equal ties in the numerical HOG ranking. DAC1 and AGE_ONLY remain
controls. Missing/incomplete/unvalidated evidence yields UNRESOLVED.

Numerical HOG qualification is explicitly separate from advancement:
`numerical_hog_status` and `numerical_hog_leader` may report a completed HOG
screen, but `frozen_candidate` stays null and overall status UNRESOLVED while
required four-window production feedback and scenario evidence remain NOT_RUN.
The finite W256 unit scenarios cannot satisfy that advancement requirement.
`--feedback --scope production` executes four actual W5M windows for each
requested policy. The scenario has heavy source0 for two full windows, a finite
switch to heavy source3 for one window, all sources backlogged for half a window,
and source churn every16 cycles for the last half. Two directed sink stalls
exercise held grants, including a window boundary. Producers cap pending work
at16 per source, in addition to the model FIFO16. This bounded, closed-loop
stress trace intentionally differs from the original exogenous HOG workload;
its latency is not paired HOG benefit evidence. The model never reads these
producer caps or pending queues for selection.

Feedback validation checks actual phase durations, all four window closes and
Main hysteresis transitions, conservation, held stability, bubble counts,
observed stalls/backlog, parameters and source revision. The advancement gate
requires sealed production feedback for Main, DAC2 and all six AGE candidates
at seed509, with no duplicates. `--feedback-evidence` ingests those reports;
`--evaluate` ingests completed HOG reports without rerunning simulations.
Only complete validated evidence can populate `frozen_candidate`. Invalid or
missing report/source/validation artifacts fail closed.

The HOG production flag alone is insufficient: validation independently checks
W5M, two real training-window durations, the original Traffic configuration,
all requested phase and lane clocks, close counts, complete drain accounting,
raw histogram statistics and cold/trained input pairing. Assertions must be
enabled; the runner refuses optimized Python. DAC all-backlogged weighting
remains a separate directed objective, not a sparseHOG benefit claim.

## Verification record

Initial native unit checks observed 10 model tests and 7 runner tests passing.
The first model-test invocation found three fixture failures: normal service
had already cleared urgency in two fixtures, and the weighted fixture had
retained an earlier all-High refill snapshot. Fixtures were repaired to state
their intended beginning state. The first runner-test invocation exposed a
missing import path for the existing `sim/common/traffic_trace.py`; the new
runner now supplies that path. No accepted file was changed for these repairs.

The model differential covers N4/N8/N16, W64/W256, eight windows with a midpoint
reset, skew/churn, random backpressure, boundary stalls and 32-bit wrap. Directed
tests cover refill/charge/reentry, held classification, full rejection and
replacement, gap reset/saturation, rescue budget/visit preservation and weighted
all-backlogged behavior. The runner tests additionally execute all 12 policies
through finite churn, all-backlogged, long-stall and role-switch scenarios.

Parent review found that a held choice bypassed timestamp half-range
validation. Validation now precedes that return; a 6-bit timestamp test stalls
a held offer to the boundary and verifies that choice, view and commit all
reject it while reset still recovers. This affects assumption enforcement,
not normal production traffic. Parent also identified the missing advancement
gate; tests now require null freeze/UNRESOLVED even for a complete synthetic
HOG matrix with a qualifying numerical leader. Added tie-order, age-only and
closing-fire tests bring the WSL model suite to 13 passing tests; all seven
runner tests also pass in that historical revision.

The initial W256 seed509 pilot completed all 12 policies, process exit 0,
under `artifacts/implementation/insight-screen/pilot-seed509/`. Times per policy
were 14.49-19.37 seconds; peak Linux RSS was 37,448 KiB. Baseline controls joined
accepted HS-pilot all-stage histograms and service exactly and all 103,424
MSQ B/B_guard cycles aligned. The initial pilot precedes the two parent-review
fixes above and is retained as historical evidence. A final-source repeat is
recorded separately in `pilot-final-seed509/`.

`worker/time-training.py` measured a 100,000-cycle prefix of exact W5M Traffic
with actual local queues, not preloaded state. This is timing evidence only
(zero completed W5M windows): Main 3.5106 s / 28,485 cycles/s; RR10 3.1871 s /
31,377 cycles/s; FCFS 3.1179 s / 32,072 cycles/s. Peak RSS was 20,360 KiB at that
short prefix. Extrapolated 10M training times were 351/319/312 seconds,
excluding measurement/drain and outstanding-work memory growth.

The initial authorized execution selected one representative seed509 production
triplet, three concurrent isolated processes, plus a W256 repeat.
All three real W5M controls completed with two actual training closes and exact
accepted HS joins and103,424-cycle MSQ alignments. Outer walls including units:
Main452.9791s/RSS68,948KiB; RR10 410.0202s/64,492KiB;
FCFS400.8275s/64,240KiB. Each child and the outer orchestrator exited0.
The later production clock/accounting validator also accepts these three
historic reports when their unavailable new artifact binding is explicitly
bypassed for that read-only diagnostic. This does not make them eligible for
the current sealed-source gate.

The final-source W256 repeat completed 12/12 configurations, validation exit 0
and runner exit 0. Per-policy wall times were 16.819-19.519 seconds, summing
to 213.522 seconds; peak Linux RSS was 37,544 KiB. All three baseline joins
and each baseline's 103,424-cycle MSQ alignment passed. All 12 rows have one
identical source-hash set. The experimental model SHA256 is
`c190cab351f93497d1a34a31f8349fd73df38b2c12df39c0692f53142f39572e`.
This remains W256 sensitivity evidence with UNRESOLVED gate. These historical
pilots and the representative triplet have source hashes but NO complete
source-byte archive. They are not claimed fully reproducible from hashes.
Their old runner bytes were not invented or replaced.

The final source-sealed revision adds tests for the absolute-P99 tie-break
where delta ranking disagrees, four real W256 feedback windows across all eight
required policies, altered report/validation/ZIP rejection, immutable ZIP
creation, unrelated-source exclusion, malformed production rows, production
clock/accounting validation, and complete versus incomplete advancement.
Numerical gate unit tests isolate arithmetic with mocked validation; separate
tests exercise the real validation and artifact ingest paths. Synthetic
structural fixtures are unit data, never production results.

On2026-10-23 the owner additionally authorized all60 HOG configurations plus
eight feedback configurations at a shared maximum of three WSL simulation
workers. An ignored `worker/run-production-models.py` orchestrates this queue,
records each launch PID/command/cwd/log/return code, archives its own bytes and
the frozen source hashes, and executes sealed ingest/evaluation after all jobs.
Its batch `progress.json` and per-job command records are the live status
authority. Production completion and a frozen winner are not claimed merely
because the batch was launched. Measured baseline timing projects approximately
3-4 hours for the68-job queue; actual candidate/feedback timing may differ.

## Reproduction commands

Commands were executed with explicit repository cwd. Native Windows units
used `python -B` and absolute paths to each of the two new test files. The
WSL orchestrator uses the project-isolated Python 3.12 environment selected by
the unchanged `scripts/wsl_env.sh`. It records every child command, cwd,
stdout/stderr, numeric exit and wall time in
`.setup-logs/implementation/revision-20261023/worker/`.

The production triplet/final pilot outer command was:

```powershell
wsl.exe -e bash -lc 'source "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler/scripts/wsl_env.sh"; python -B "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler/.setup-logs/implementation/revision-20261023/worker/run-validation.py"'
```

The direct full HOG exploration command is shown below. Use a fresh output
directory; the runner refuses to overwrite an existing one. The batch
orchestrator instead splits it into one policy/seed per process, queues the
eight production feedback runs under the same three-worker cap, and invokes
`--evaluate <60 reports> --feedback-evidence <8 reports>` after completion.

```bash
cd "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler"
source "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler/scripts/wsl_env.sh"
python -B "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler/scripts/screen_scheduler_insights.py" \
  --scope production --seeds 509 510 511 512 513 \
  --out "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler/artifacts/implementation/insight-screen/production-exploration"
```

The source-sealed sensitivity pilot uses
`--scope pilot --out .../source-sealed-pilot-seed509`; the feedback sensitivity
pilot adds `--feedback` and uses `.../source-sealed-feedback-pilot-seed509`.
These W256 rows cannot pass production ingestion even if their production
boolean is relabeled. Each new output contains its exact source ZIP,
validation commands/results, report hashes and numeric exit statuses.

Final freeze and launch record (2026-10-23):

- Native model13/13 and screen13/13 tests passed, both command exits0.
  Both WSL pilot validation records also contain model13/13 and screen13/13
  passing, validation exit0.
- `source-sealed-pilot-seed509`:12/12 HOG configurations, exit0,
  wall14.5171-19.0699s/configuration, total191.0333s, peakRSS39,280KiB.
  Active-cycle rate11,003-14,454cycles/s includes three cold/trained lanes.
  All three accepted baseline joins and103,424-cycle alignments passed.
- `source-sealed-feedback-pilot-seed509`:8/8 configurations, exit0,
  four actual W256 closes each; configuration wall0.069-0.080s,
  process peakRSS24,564KiB. This is sensitivity evidence only.
- The two new pilots' exact source ZIPs verify against the same current
  15-file dependency hash set. Historical output directories were preserved.
- Frozen model SHA256:
  `c190cab351f93497d1a34a31f8349fd73df38b2c12df39c0692f53142f39572e`.
  Frozen runner SHA256:
  `7c917ece53352e4ac9f7cb318e531e2431d9702536c556abbcb2aadeddbdc039`.
  Screen-test SHA256:
  `314019f52aa39410d0ec98c6d92e8e8c2ff1cbbaa4c117490d5299ff3cf33fbb`.
- Batch `production-sealed-20261023T101008Z` launched at10:10:08UTC /
  18:10:08Asia/Taipei. The queue contains60 production HOG jobs and eight
  production feedback jobs, with a shared three-worker maximum.
  WSL orchestrator PID501; initial Main/FCFS/RR10 worker PIDs510/511/512.
  The desktop execution session is52409. Initial three production jobs each
  completed both validation suites with exit0 and entered real W5M simulation.
  Their simulation results and the final gate remain pending at this record.

The production launch runs the ignored orchestrator through `wsl_env.sh`,
with explicit repository cwd and Python `-B`. The batch archives its exact
orchestrator bytes and complete source-freeze manifest. Per-job
`*.command.json`, `*.log`, and `progress.json` preserve live status; after
completion `completed.json` preserves all return codes and the exact final
evaluation command. No performance winner is established by this launch.

## Completed production model gate, reviewed 2026-10-24

The sealed batch has now completed all60 HOG and eight feedback jobs.
`completed.json` records evaluation exit0 and unchanged frozen sources.
`evaluation/summary.json` records gate PASS and sole frozen candidate DAC2.
Parent independently re-ingested every report, validation record and source ZIP
under WSL and recomputed the gate; the result exactly matches the saved gate.
The audit is `.setup-logs/implementation/revision-20261024/screen-ingest-audit.json`.
An initial Windows ingest rejected the recorded WSL absolute artifact paths;
the successful audit used the original execution environment without relaxing
the binding checks. No experiment was rerun or overwritten by this ingest.

All values below are mean run P99 generation-to-fire cycles over the same five
exploration seeds509-513, with independent cold A/B starts.

| Policy | Cold A | Cold B | Trained A | Trained B |
| --- | ---: | ---: | ---: | ---: |
| Main | 18.2 | 33.8 | 10.0 | 20.8 |
| DAC1 ablation | 2.0 | 16.4 | 2.0 | 16.4 |
| DAC2 candidate | 2.0 | 16.0 | 1.0 | 12.0 |

DAC2 improves each endpoint in all five paired seeds. Its maximum heavy-service
fraction drop is0.000068360043, or0.0068360043 percentage points, within the
approved0.01-percentage-point gate. All six AGE settings have zero mean B P99
change in both cold and trained HOG and fail the numerical benefit gate.
DAC1 is an ablation, not a second candidate: its improvement shows that the
per-source allocation change contributes even without historical class weights.
Differences between DAC2 and DAC1 must be reported separately.

Four actual W5M feedback windows and the scenario checks passed for Main and
all seven eligible candidates. This is bounded correctness/stress evidence,
not a general stability proof. All results in this section remain MODEL_ONLY;
confirmation seeds and RTL benefits remain unmeasured. The approved next step
is one DAC RTL candidate with the1:1 ablation, followed by its independent
model checks, confirmation/robustness and own-netlist PPA/equivalence gates.
