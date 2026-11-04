# Accepted Main: baseline audit and causal diagnosis

## Material Passport

- Origin: owner Main-SQ task; Codex independent audit, 2026-10-23 (Asia/Taipei).
- Verification status: archive audit and tag-linked actual-RTL replay **PASS**; persistent SQ1/SQ2 benefit gate **FAIL**.
- Baseline branch point: `bb7f407623812c1866bafe2352a0433ffad263c8`.
- No accepted architecture, RTL, old measurements or Final manuscript is changed by this audit.

## Independently reproduced archived observations — PASS

The 15 original metrics files in `artifacts/implementation/HS-main/20261022T034507Z_311/`
were re-audited with `scripts/audit_hog_sparse.py`, actual exit 0. Independent read-only
review also recomputed the statistics from the raw histograms and checked raw JUnit/exits.
This reproduces recorded calculations, not a new RTL execution.

| Sparse profile | FCFS mean run P99 | RR10 mean run P99 | Main mean run P99 | Main vs FCFS paired reduction | Main vs RR10 paired reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| A: singles | 18.2 | 11.0 | 10.0 | 45.0292% | 9.0909% |
| B: eight-request bursts | 33.8 | 17.2 | 20.8 | 38.6401% | -20.7843% |

Units are scheduler cycles. Negative reduction denotes worse Main latency. Each P99 is
nearest rank `ceil(0.99*K)` on **direct generation-to-fire** for the complete sparse
generation cohort; no stage percentiles are added. Table P99s are means of five run P99s.
Percentages are calculated per paired seed and then averaged. They are not ratios of
the table means. No population confidence interval or significance claim is made.

| Policy | B run P99s, seeds 509–513 | Sample SD |
| --- | --- | ---: |
| FCFS | 34, 34, 36, 31, 34 | 1.78885 |
| RR10 | 17, 17, 18, 17, 17 | 0.447214 |
| Main | 24, 19, 24, 17, 20 | 3.11448 |

All use N4, D16, descriptor105, RR quantum10, W5M and identical per-seed intended traffic
and sink-ready1. Main naturally trains for **10,000,000 real nonreset cycles**; the two
closing states are B_H/H/H/H then L/H/H/H. A/B remain L/H/H/H and end before the third
window closes. Main and FCFS match the complete first10M observed pin digests in all seeds.

A cohort counts per run are 2,284 / 2,346 / 2,405 / 2,346 / 2,257 sparse requests; B has
800/source, 2,400/run. All complete with heavy generation still active, including any
measurement-end spill into the background-on guard. Final drain completes all generated
producer/FIFO/response work, including heavy backlog. No unfinished sparse request is omitted.

All30 measured A/B intervals have fires = measured cycles = ready cycles = eligible-ready
cycles. Therefore both total throughput and eligible-ready utilization are1 here. This is
not a statement about every training/drain cycle or real CXL link bandwidth.

Heavy service means **heavy fires / all measured fires**, not accepted/offered heavy demand
or a guaranteed allocation. A means FCFS/RR/Main are 97.6728/97.6726/97.6724%; B means
97.657617/97.656445/97.656445%. Empty High visits relinquish unused credit.

## Hypothesis status before grant replay

| Hypothesis | Current evidence | Status / remaining test |
| --- | --- | --- |
| H1 shared High quota10 | Class quota expires despite remaining High heads; actual aggregate visits exist. | Plausible, not yet tail-attributed. Join actual tail tags to Low visits. |
| H2 within-High FCFS concentration | Main selects oldest accepted head within class, source-ID tie break. Aggregate histograms do not expose competing heads. | Unresolved. Count other-High fires while each tail request is head-eligible. |
| H3 slow classification | Cold Main matches FCFS; protection waits two W5M windows. Production A/B class map is already fixed. | Explains adaptation lag; excluded as a new class-transition cause of the measured trained B difference. |
| H4 sparse FIFO admission blockage | Across all45 B source/seed/policy cohorts, sparse full events are0; exact G2A histogram is100 samples at each delay0…7/source. | Rejected for these cases. The3.5-cycle mean is burst serialization; confirm tail-tag joins in replay. |

SQ changes only the ordering of the same10 High fires. It cannot remove the intervening
Low visit. With unchanged admitted traffic and nonfull sparse FIFOs, aggregate High service
opportunities can remain identical while individual waiting times are redistributed. Other
High service is not automatically harmful: older requests may appropriately precede a new
burst. Lower pooled P99, per-source exceptions and max waiting must all be inspected.

**Historical pre-replay gate: open.** No SQ RTL/model implementation was justified by an aggregate
P99 explanation alone. The representative replay targets seed509 (Main24/RR17), with
seed512 (both17) available as a no-regression control if required by the diagnosis.

## RTL/PPA provenance cross-check — PASS

Frozen Spec v1.0 is `1af80967bbc2fb83224f4725c4fb450889e69c62`. Primary mapped RTL source is
`759f86b24f13ed5984c19034eeeea2ca43b0e971`, functional comparator `d82f1b54ca54af2344ad07d914680547003f526f`.
October22 simulations use the later Algorithm2-capable Main source
`c8e7ea8c0e4530572b3abf5b14ea9958e24f1789`, connected to
those primary Main netlists by the recorded N4/8/16 current-Main bridge equivalence proofs.
The two RTL snapshots are **not byte-identical**.

Profile `syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json`, canonical SHA256
`6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`, is the accepted common
SAED32 RVT TT0.78V25C /25ns method. Nine original area summaries and minimum setup slacks
match `docs/ppa/primary-20261021-v2.json`; actual DC/PT exits are0. Main area over FCFS is
5.886106/5.232663/4.974109% at N4/8/16. Main N16 setup slack is +1.158148ns.
Area uses library units; these are pre-layout single-corner measurements, not physical signoff.

## Native execution history

Claude Code2.1.306 / enabled RTL Agent Team0.14.6 was actually invoked, Opus5.5/medium,
session `9f4e4095-5ccb-4e8c-ba98-7769a01f1c44`. The focused functional-verification workflow
read existing sources, then reported an internal response safeguard and returned without
new files or simulations. Outer exit0 after140.459s is **not implementation success**.
Its stale plugin RTL-modified hook list is retained and not waived or deleted; Git confirms
no RTL changes. A smaller direct installed `testbench-dev` task with explicit PROJECT_ROOT
completed, session `9ab3c007-4b1b-4a3d-b32b-526bdc477b88`, actual exit0 after713.204s.
All recorded model fields are Opus5.5; effort medium. No quota fallback was invoked.
Prompts, model usage, stderr, outputs and numeric exits remain in the ignored execution
root documented in [README](README.md).

## Passive replay infrastructure — PASS

Native `MSQ-pilot/20261023T082655Z_633` completed, actual outer exit0 and92.4s runner time:
three strict lint configurations, six new recorder unit cases,26 existing traffic cases,
three actual RTL runs and scope gate PASS. P99 FCFS34/RR18/Main23 exactly matches the
accepted W256 pilot; all nonvolatile metrics match, including the exogenous trace hash.
Each B-plus-guard trace has103,424 actual rows and2,400 joined sparse requests. Codex's
independent reconstruction from those rows also passes and matches every request's timing
and waiting decomposition. W256 remains **infrastructure/sensitivity evidence**.

Two failed unit attempts are retained:4fail/2pass, then1fail/5pass. Repairs covered a
recorder count after deletion, a mistaken fixture age expectation, first-row same-cycle
generation and fixture FIFO-depth handling. Returned raw failure output is preserved in
the native stream and extracted `attempt02/failed-unit-tool-output.txt`; complete standalone
pytest process logs were not captured for those first two attempts. There was no failed
RTL pilot. These repairs did not modify RTL, models or traffic.

An independent order-only design screen feeds the observed Main High slots to source
rotation1/2 while holding actual sparse admissions fixed. In the W256 pilot, pooled P99
changes23→24/25 and max30→33, for each of three initial High pointers. Latency sums remain
equal, as required by the fixed-slot invariant. This is **offline diagnostic analysis,
not SQ RTL execution**, and cannot decide the production gate by itself. Its hand-derived
simultaneous-generation, exact percentile and corruption controls pass3 tests/8 subtests.
The following production result supersedes that pending checkpoint. The independent controls
were subsequently expanded to6 tests/14 subtests, all PASS.

## Production reproduction and decision gate — COMPLETE

`MSQ-main/20261023T083405Z_1850` completed UTC09:21:11.092159, actual outer exit0,
2825.623s. All three real RTL cases, three strict lint configurations,32 unit cases and
the scope gate pass. Every nonvolatile metric matches the accepted seed509 exactly.
Each run executes10,444,417 nonreset cycles, including two actual W5M windows; total
31,333,251 cycles. Pilot plus production is31,962,468 actual cycles, six RTL cases.
Audits/screens are zero additional RTL cycles. The32 native unit cases repeat across
scopes; they are not64 distinct tests.

Independent reconstruction of103,424 consecutive B-plus-guard rows/policy matches all
2,400 sparse request joins and all three stage histograms. Main's2,400 High selections
also match an independent oldest-accepted-head positive control. Two independent Codex
reviewers recomputed the production statistics/joins; one separately recomputed the SQ
screen schedules. Their verdict agrees with the parent audit.

| Hypothesis | Final assessment for this trained B workload |
| --- | --- |
| H1 shared High quota | **SUPPORTED directly.** Seven High visits expire at10 while High work remains. Visits are286×8,7×10,7×6 fires. Empty visits discard600 credits; borrowing preserves capacity. |
| H2 within-class concentration | **Present but not an effective SQ remedy here.** A source can receive up to6 consecutive High fires while multiple heads exist. All grants obey accepted-age FCFS. Fixed-slot SQ fails to improve pooled P99 and worsens source2/max waiting. The key example already alternates two sources. |
| H3 slow classification | **Not the trained B difference.** L/H/H/H is fixed throughout B; two-window adaptation remains a separately verified cold-start limitation. |
| H4 sparse admission backpressure | **REJECTED in this cohort.** No sparse full events; exact G2A distribution100 at each0…7/source under every policy. Matched tags have identical generation and acceptance cycles. |

### Actual tail request

Source2/tag10410514 is generated at10171350 and accepted at10171357 under all policies.
Main serves ten High transfers at10171357–10171366, alternating **2,1,2,1,…**. Six High
requests remain, but its class quota expires; Low receives10171367–10171376. The target
fires at10171381: G2F31, versus RR10's22 and FCFS's37 for this exact tag. This is a
specific shared-class-capacity delay even with alternating in-class sources.

Main's26 requests at or above its P99 threshold24 accumulate148 serialization,
132 same-source predecessor-fire,262 Low-service-wait and129 other-High-service-wait
request-cycles, plus26 own-fire cycles =697. These are overlapping **request-wait
exposures**, not697 distinct output cycles or a causal percentage of runtime. Including
ties means the tail can contain more than exactly1% of requests. High/Low waiting while
behind a same-source predecessor is included; counting only head waiting would miss it.

### Gate result

| Endpoint | Main actual RTL | SQ1 offline screen | SQ2 offline screen |
| --- | ---: | ---: | ---: |
| Pooled G2F P99 |24|24|25|
| Mean G2F |9.415|9.415|9.415|
| Observed maximum |31|34|34|
| Source1 P99 |26|26|26|
| Source2 P99 |21|28|29|
| Source3 P99 |18|18|17|

All three starting pointers give the same screen result; these are sensitivity settings,
not extra replications. Equal means follow the fixed-slot invariant. SQ2's source3 gain
does not hide its source2 regression. **The prespecified trained-burst benefit gate fails.**
Do not incur candidate RTL/PPA work for these persistent SQ1/SQ2 rules. This decision is
limited to the diagnosed objective/representative seed; it does not reject every refill
rule, cold-state use case or workload. Keep the accepted Main unchanged. A bounded class
quota study is a narrower future hypothesis; Main-HQ/Main-AGE remain unimplemented.

Raw joins/slot evidence, counts and hashes are available in [the production audit](data/production_audit.json)
and [portable raw bundle](production-replay-seed509.tar.gz). See the [performance comparison](PERFORMANCE_COMPARISON.md)
for the measured/offline boundary and the [recommendation](RECOMMENDATION.md).
