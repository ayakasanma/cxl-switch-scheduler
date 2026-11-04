# Descriptor-level performance test record —2026-10-22

Owner scope: record the new performance tests; **do not edit or rebuild the Final report**.
The existing manuscript/literature edits are independent, preserved work. No RTL, reference
model, approved Spec, PPA profile or accepted synthesis/power dataset is changed here.

## Purpose and evidence selection

[Inventory](EVIDENCE_INVENTORY_2026-10-22.md) separates reusable, missing and incomparable data.
The archive audit accepts the original180 primary runs and44 long/stress runs after checking
raw JUnit, exit codes, parameters and source/trace provenance. It executes **zero RTL cycles**.
Existing aggregate primary metrics are reusable; only phase-cohort latency, sampled backlog
and FIFO occupancy require new observation. Production/stress/PPA are not rerun.

## Execution provenance

Claude Code2.1.306, RTL Agent Team0.14.6 enabled, was actually invoked using
`/rtl-agent-team:rtl-p5s-func-verify descriptor-performance-phase-gaps`, requested
`claude/claude-opus-5-5`, medium. Session6f0f88a0-fc44-44b5-b154-cf1ceab97f0a exited1 with
weekly quota429 before implementation. The owner-authorized fallback GPT6.1Sol/high implemented
the passive recorder and three N4 pilots; Codex independently reviewed and audited it. No native
Claude implementation PASS is claimed. Invocation-local settings preserve global configuration.

Prompt/settings/stream/stderr/exits, fallback diff/hashes/tests/pilots and parent audits are kept
under ignored `.setup-logs/implementation/descriptor-perf-20261022/`; no credentials are recorded
in this tracked report. The fallback writer was frozen before the parent batch; no concurrent
source writes occur. New source paths:

- `sim/common/primary_phase_metrics.py`: passive pin/generation-event recorder.
- `sim/common/switch_fcfs_tb.py`: observer calls in the existing common run_trace; no driving change.
- `scripts/test_primary_phase_metrics.py`: hand-derived recorder checks.
- `scripts/audit_descriptor_performance.py` and test: archived evidence acceptance boundary.
- `scripts/summarize_primary_phases.py` and test: replay/legacy equality and phase ingestion audit.

## Stimulus, cohorts and measurement contract

Project-owned `sim/common/traffic_trace.py`, profile `primary`; FCFS/POLICY0, RR10/POLICY1,
Main/POLICY2; N4/8/16, D16, descriptor105, one output, seeds509–528. Each full run measures
100,000 trace-relative closing edges; initial3 reset cycles excluded, warm-up0, no measurement
reset. Same N/seed has identical external generated descriptors and downstream-ready trace/hash.
Acceptance may differ through backpressure; intended, accepted and fired counts remain distinct.
The legacy `accepted_transfer_rate` means **fires/measured cycle**, not input acceptance rate.
Latency units here are scheduler cycles. The common cocotb clock is10ns; do not silently convert
these results with the separate25ns synthesis constraint or describe them as application time.

Record each phase segment and pool repeated kinds (idle/light/burst_one/saturate/overload/balanced).
Do not assume an idle generation phase empties carried-over queues. Phase throughput, acceptance
and stalls count events in that phase. Latency is assigned to a **cohort**, which is different:

- Acceptance→fire follows acceptance phase; measured accepts completing in the existing drain
  are included, with drain contribution separately counted. All measured accepts must complete.
- Generation→acceptance follows generation phase, only for accepts during measurement. Its
  mean/P99 describe the accepted subset; unaccepted requests remain right censored.
- Cohort age snapshots at its phase end and measurement end use exclusive boundary−birth edge.
  Phase-end snapshots are not summed as a measure of the same total producer queue.
- Existing C1 boundary-only drain forces ready1, stops new generation, and may accept a request
  already offered but refused at the boundary. Those drain-only accepts/fires stay excluded.
  Other producer backlog does not drain; accepted-cohort tail is not a continued-load estimate.
- FIFO occupancy is pin-history accepts−fires **before the edge**, per source depth16.
  Producer backlog is sampled after generation/before push and again post-edge, including carryover.
  This is derived state, not an internal mapped-hardware probe or a full saved time series.
- Successful fire, valid&&!ready stall, !valid&&ready idle and !valid&&!ready idle partition cycles.
- Histograms use exact nearest-rank P99. Repeated-kind histograms are count-pooled before P99.
  Across seeds use20 **run-level** samples: arithmetic mean, sampleSD and t19 95% mean interval.
  Mean of20 runP99 values is not a pooled-request P99. Undefined cohorts stay blank; no partial-seed CI.
  Paired differences use the same N/seed, not millions of requests as independent replications.

RR quantum stays10. Main W5,000,000 exceeds each primary run; it closes no classification window,
and remains all-High with cycle-by-cycle FCFS mirror checks. Primary cannot demonstrate an adaptive
FAI fairness benefit. Production and stress establish different behavior under different conditions.

## Actual infrastructure pilots and controls

| Policy | N / seed / measured cycles | Infrastructure-only run ID | Result |
| --- | --- | --- | --- |
| FCFS | 4 /509 /100,000 | M3-primary-infra-smoke/20261022T002800Z_277 | PASS |
| RR10 | 4 /509 /100,000 | M4-primary-infra-smoke/20261022T002816Z_442 | PASS |
| Main | 4 /509 /100,000 | M5-primary-infra-smoke/20261022T002816Z_445 | PASS |

All compile/make/simulation exits0, one actual cocotb case each. All previous metric fields match
their accepted seed509 archive, except host wall time and Main's explicitly true infrastructure flag.
These pilots are not full milestone acceptance or additional independent seeds. FCFS/RR pilot
launcher supplies missing smoke_env in memory without changing the tracked runner/configuration.

Parent independent WSL checks: **27 tests and10 subtests PASS**, no skips,0.58s. Include hand-derived
phase/carryover/drain and histogram checks; deliberate bad cohort, partition, depth, histogram,
changed legacy metric, raw JUnit failure, nonzero exit and incomplete/relaxed scope are rejected.
JUnit: `.setup-logs/implementation/descriptor-perf-20261022/final-unit.xml`.

Preserved non-results: first ignored pilot launcher had a path/import error before simulator startup
(wrapper exit0 did not make it PASS); no RTL coverage is attributed. Parent first unit command used
an unavailable `Ubuntu-24.04` distribution name, failed before pytest; actual installed `Ubuntu`
retry produced the27-test result. Neither failure is silently counted as a completed simulation.

## Reproduction

In the installed Ubuntu WSL, from the existing repo:

```sh
source scripts/wsl_env.sh
python -m pytest scripts/test_primary_phase_metrics.py scripts/test_audit_descriptor_performance.py scripts/test_summarize_primary_phases.py -q
python scripts/run_verify.py M3-primary -j 3 --make-jobs 2
python scripts/run_verify.py M4-primary -j 3 --make-jobs 2
python scripts/run_verify.py M5-primary -j 3 --make-jobs 2
```

Each runner creates a new run ID; preserve prior artifacts. Parent launched the three independent
scopes concurrently, each with3 jobs/2 build jobs, under the same frozen source manifest. Raw
metrics, histograms, per-case logs/JUnit and runner configuration live under each artifact run.
Run the audit with explicit run IDs and a **fresh** output directory:

```sh
python scripts/summarize_primary_phases.py --runs FCFS_RUN_ID RR_RUN_ID MAIN_RUN_ID --output artifacts/performance/NEW_AUDIT
```

## Claim limits and remaining gaps

Synthetic descriptor transfers are not application IPC/slowdown, bytes/s, DRAM bandwidth or
full CXL link utilization. Service share must be interpreted with offered demand; equal shares
are not a universal fairness target. No independently instrumented longest continuously-backlogged
service gap or starvation bound is provided. Algorithm-2 stays supplementary, outside the matrix.
gem5 integration/trace extraction/closed loop, application workloads and physical PPA are deferred.
No new SSH or licensing check: 「目前帳號可見環境未確認 SPEC 安裝或使用授權。」


## Accepted full replay and new phase observations

**180/180 actual primary cocotb cases PASS**, zero failures/errors/skips; all compile/make/simulation
exits0 and full-scope gates pass. The three run IDs are:

| Policy | Scope / run ID | Actual measured RTL cycles |
| --- | --- | ---: |
| FCFS | M3-primary/20261022T003252Z_406 | 6,000,000 |
| RR10 | M4-primary/20261022T003252Z_407 | 6,000,000 |
| Main | M5-primary/20261022T003252Z_404 | 6,000,000 |

Nine actual Verilator lint configurations pass; RR/Main metadata elaboration controls also pass.
New full matrix18M plus three infrastructure pilots0.3M = **18,300,000 new measured RTL cycles**.
Reset/drain and reference calculations are not added to this measured-cycle count; repeated
archive/JSON audits are not new RTL simulation or new independent replicates.

[Replay audit](phase-audit.json) verifies all180 raw JUnit records, full60-case matrix per policy,
every legacy field except host wall time, exact original trace hashes, phase cycle/ready partitions,
histogram/cohort conservation, depth limits and pooled phase histograms. **All old metric fields
are identical**, including coverage/waits/drain details; the new observer changes measurement only.
Main/FCFS also match every pooled-kind scalar metric in phase_runs.csv. Original accepted artifacts remain intact.

New durable data:

- [Phase-kind run data](phase_runs.csv):1,080 rows (180runs×6kinds), measured events, latency/censor
  cohorts and mean/max occupancy/backlog. Per-segment histograms remain in the linked raw artifacts.
- [Per-source phase data](phase_sources.csv):10,080 rows; generated/accepted/fire counts and
  offered/service shares. Shares with no offered/fired requests remain blank.
- [20-seed summaries](phase_seed_summary.csv) and [paired policy differences](phase_paired_differences.csv):
  run-level mean/sampleSD/t19 95% mean interval, with metric/cohort units defined above.
- [Source/execution manifest](replay-source-execution.json): exact source hashes, actual scope
  start/end/exit/elapsed and preserved-file checks. Raw metric hashes/paths are in the replay audit.

Illustrative **N=4,20-seed arithmetic means of per-run pooled-kind rates/state means** below.
Occupancy/backlog units are requests, total across all four sources. No row is a steady-state
experiment: carried-over backlog is retained across phase changes. All uncertainty and the full
N4/8/16 metric matrix are in the CSV; this compact table omits intervals for readability.

| Phase kind | Offered/cycle | FCFS fires/cycle | RR10 fires/cycle | Main fires/cycle | FCFS mean total FIFO occupancy | FCFS mean post-edge producer backlog |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| idle | 0.000000 | 0.878038 | 0.878038 | 0.878038 | 59.317287 | 13273.710195 |
| light | 0.299331 | 0.859402 | 0.859402 | 0.859402 | 58.759685 | 13061.000232 |
| burst_one | 1.198948 | 0.793317 | 0.793317 | 0.793317 | 61.301877 | 13610.618045 |
| balanced | 0.899524 | 0.856682 | 0.856682 | 0.856682 | 62.021604 | 13389.821890 |
| saturate | 2.001231 | 0.215621 | 0.215621 | 0.215621 | 63.715842 | 13474.552497 |
| overload | 1.600518 | 0.755443 | 0.755443 | 0.755443 | 63.102399 | 13258.747497 |

An idle phase means no **new** generation; it can still dispatch carried-over work. A kind's
fires can therefore exceed its newly generated requests. Do not interpret phase fires/generated
as completion fraction of that generation cohort. Latency/censor columns provide cohort accounting.
Mean producer-delay values remain accepted-subset summaries, with censored counts/ages alongside.

Acceptance checks confirm188 pre-existing manuscript/literature files and all58 frozen functional
files unchanged during the full batch. No protected RTL/model/Spec/synthesis/STA/PPA diff, no SSH,
no Final edit/build/render. Full source/metrics are specific to these runs; subsequent changes must
not silently inherit this acceptance. No remaining test batch or source writer is active for this task.
