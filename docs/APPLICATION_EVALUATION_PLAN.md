# Descriptor-level RTL performance evaluation — scope v0.2

## Material Passport

- Origin Skill / Mode: Academic Research Suite / experiment-agent plan
- Revision: 2026-10-22, owner-confirmed scope; supersedes v0.1 at commit1dfbfb0.
- Execution status: archive audit and phase-gap replay accepted;180/180 primary runs PASS.
  Actual evidence, limitations and source/trace hashes: [test record](performance/TEST_RECORD_2026-10-22.md).

## Owner decisions and stopping boundary

This stage evaluates synthetic descriptors using project-owned/self-authored or explicitly
licensed workloads. gem5 is deferred; no integration, trace extraction or closed-loop work now.
Algorithm-2 remains supplementary correctness/reconstruction evidence, outside the primary
performance matrix. The latest owner steering is **do not change the Final report yet**;
record only performance tests/results, audit, reproducible tools and development progress.
Preserve every pre-existing manuscript/literature modification.

Future writing target: six body pages excluding references,10pt,two columns; title:
*From Scheduling Policies to Hardware Costs: A Comparative RTL Study of CXL Switch Arbitration*.
No manuscript/PDF changes are needed to complete the current testing task.

RQ: Within one synthesized switch boundary and controlled offered traffic, how much hardware
cost corresponds to differences in arbitration service behavior? No application IPC,
application slowdown, actual memory bandwidth or full CXL link utilization is inferred.

## 1. Reuse before rerun

Read code, raw metrics, summary/JUnit, trace/source hashes and retained incomplete/failed runs.
Classify evidence as reusable, missing instrumentation, or incomparable. Reuse complete accepted
runs if settings/version/hashes match; do not rerun long production or a full matrix merely to
obtain a newer timestamp. New phase/occupancy data requires actual recorded observation; neither
model-only inference nor existing total counters can be labeled direct per-phase RTL measurement.

## 2. Main matrix

- Generator: sim/common/traffic_trace.py primary, current version cxl-traffic-trace-v2.
- Policies: FCFS/POLICY0; RR/POLICY1 with RR_QUANTUM10; FAI_MAIN/POLICY2 with W5,000,000.
- N4/8/16, D16, M1, full105; seeds509..528,100000 measured nonreset cycles/run.
- Complete scope:180runs. Algorithm-2/POLICY3 is not a primary entry.
- Existing primary phases: light, balanced, overload, burst_one, saturate, idle; seeded
  shuffled phase order/length, ready probabilities and forced long stalls are preserved.
- Same N/seed gives exactly the same external generation and ready trace; retain trace SHA256,
  profile configuration, source hashes, parameters and actual acceptance/completion separately.
- No warmup;3initial reset cycles excluded. Main is allHigh, no production-window closing in100k;
  FCFS/Main equivalence is checked but is not evidence of adaptive fairness benefit.
- N4seed509 threepolicy execution pilot is authorized without another approval. Use full100k
  stimulus, measure actual cost, verify instrument counters and compare legacy metrics to
  archived records before completing missing phase-data scope for N4/8/16×20seeds.

## 3. Populations, phases and missing data

Successful output transfers are fire=out_valid&&out_ready. Main rate=measured fires/100000;
input acceptance=sum of source pushes/100000 can temporarily exceed1/cycle. Generated versus
accepted versus delivered descriptors versus modeled tagged responses are separate counts.

C1 drain holds only input requests already offered/refused in the last measurement cycle;
ready=1, no new producer backlog presentation. These drain-only accepts/fires are separate and
excluded from measurement rates/cohorts. Requests accepted during measurement finish in drain;
acceptance-to-fire all_completed includes them. FIFO cohort then has0outstanding, but the
producer's generated-unaccepted queue need not drain. Generation-to-acceptance mean/P99 is
therefore **accepted subset**, with unaccepted backlog and age/censor counts disclosed; do not
call it the unconditional latency of all intended requests.

Per-phase summaries label cycle attribution, acceptance-phase wait cohort and generation-phase
accept-delay cohort separately; carryover backlog can dominate idle/light phases after overload.
Record per-instance phases and aggregate same kinds within each run. Histogram merging across
segments yields run/phase P99; averaging segmentP99 is not a pooledP99.

Preferred metrics: rate, acceptance rate, acceptance-to-fire mean/P99, generation-to-acceptance
mean/P99, generated-unaccepted at cut, per-source service share, producer backlog, FIFO
occupancy and output stall cycles. Missing measurements remain explicit gaps. Snapshot average
and max occupancy/backlog state pre/post-edge convention must be labeled. No finite observed
max waiting time establishes an unbounded starvation guarantee. Service equality is not a
universal fairness target under unequal offered demand; show offered share next to service share.

## 4. FAI evidence

Reuse Main production N4/8/16 seed509 W5M 20Mreal cycles (fourwindows), and Main stress
N4/8/16 W64/256 seeds509..513 with400k/800ktrace cycles. Explicitly enumerate observed versus
missing transition/evidence bins; four realwindows do not imply all16transitions. Stress has
resets, window-scaled hotspot/flip/idle/stall/saturation; its measured nonreset denominator and
reset-dropped cohort differ from primary. Do not place it in the primary comparison table.
Algorithm-2 N4 correctness/stress/production and paired reconstruction cases remain supplemental;
no full matrix or general equivalence claim. No forced rerun if existing evidence suffices.

## 5. Statistics, figures and provenance

Each independent seed/run is the comparison unit; retain20paired seeds for each N/policy.
Report per-run values, arithmetic mean and sampleSD; any95%CI of mean uses an explicit formula
and describes only this synthetic trace family. Pair differences by N/seed, not unpaired mixes.
A runP99 mean must be labeled mean of20runP99 values, not the combined request populationP99.
Avoid pseudoreplication by treating millions of requests as independent experiments.

Save raw-run index and hashes, source versions, exact commands/exits, old/new metrics and a
failure/incomplete inventory. Frozen PPA datasets remain separately attributable to their source,
synthesis boundary/profile/clock/library and activity assumptions; no new FastX run required.

Only create distinct, useful result plots outside the Final project for now. Legends outside
plot data; each panel axis/unit explicit; captions state seed aggregation/interval meaning and
conditioning. Use per-phase results before overall summary; do not multiply figures repeating
the same observation. Reporting scripts are deterministic and reject incomplete/wrong-policy/
wrongtrace inputs. No model export/file compare is counted again as RTL test cycles.

## 6. Tools and scope limits

Use existing WSL Verilator/cocotb and the installed Claude Code RTL Agent Team for focused
verification implementation; Codex independently audits. Opus5.5 medium; actual quota exhaustion
permits the owner's GPT6.1Sol/high fallback. Preserve prompts/logs/changed-file inventory/diffs.
No RTL/architecture change, heavy dependency install, workload download, SSH or system settings
change is planned. Retain exact failures; remedy tests without silently waiving checks.

For FastX licensing the allowed conclusion is only:
「目前帳號可見環境未確認 SPEC 安裝或使用授權。」
Failure to find an install/module/WebStore entry cannot prove university-wide absence of rights.
This task makes no fresh FastX/license inspection claim and uses no unconfirmed external data.
gem5 on the other VM is owner-reported; next-stage future work only: version and authorized
workload inventory, then N4pilot. No IPC/slowdown extrapolation from current tests.

BLISS is related work/methodology, with original RTL/synthesis/evaluation statements checked;
not a direct numerical baseline for this CXL switch boundary. Retain the bounded literature claim:
“Within the reviewed literature, we found no directly comparable complete area, timing, and
power baseline at the same CXL switch boundary.” No new literature universality claim.

## 7. Deliverables

1. docs/performance/ evidence inventory: reuse / rerun gap / incomparable with reasons.
2. N4pilot and targeted missing-data run logs/JUnit/source/trace hashes; performance results
   in new artifacts, preserving original180records and all failures.
3. Reproducible analysis and per-phase/overall/per-source tables, uncertainty definitions,
   missing/censored counts; optional standalone academic plots.
4. Development/status record, no Final manuscript/PDF edit or publication claim.

This owner clarification resolves previous v0.1 requests for application/trace and64B choices:
no application integration or byte-mapping approval is needed at this stage. Details of actual
implemented instrumentation and accepted results belong in the performance outcome document,
not predeclared PASS entries in this plan.
