# CXL Scheduler status

## Evidence-review follow-up — 2026-11-01

P0–P4 contract fixes and two separate `MODEL_ONLY` Buffer screens are complete.
The transition-only screen has 78 replays per window; the independent
closed-loop screen covers W256 seeds 6101–6105, six classifier/quota
variants, 120 common-input scenarios and 720 runs. CGOF(1:1) live／1W／frozen
action, count, latency, gap and queue metrics match in all 120 groups
(negative control PASS); CGOF(2:1) differences remain descriptive only.
The exploratory closed-loop ledger has 480 `COMPLETE` and 780 `INCOMPLETE`
role-event observations, with zero final request censoring and no latency
recovery claim.

Evidence: `artifacts/implementation/buffer-transition-screen/20261031T234344Z/`
(manifest `66bb7863873e584ddca31b9c2882c46a30b041c1a6759fe3e359f4399e86441d`)
and `artifacts/implementation/buffer-closed-loop/20261101T015630Z/`
(manifest `d95bcdd4a38adddaa44a53be39fad3fc8d21007d63d0251d98d7c84bfd3a984a`;
acceptance `242c8a15f85b495914d13e68e4bb574518faea6729dff9cb55b691c3e3eb7d54`).
Final targeted evidence-review regression: 245 passed, 224 subtests passed.
The earlier fourteen power-vector errors remain unresolved and separate.

The H2 quota × ordering follow-up has now completed a separate bounded
`SCHEDULER_RTL` exploration: seeds 6401–6405, N4/D16/W256, near load,
256 Heavy requests, bursty ready, four settings and two lanes. All 40 jobs,
20 mixed/isolated pairs, 20 lint configurations and 25 traffic tests passed.
All jobs observed only the active close at 255 and remained effective High;
31 source files matched before/after, in all source ZIPs, and at audit time.
Independent full input replay, JUnit and 20 reconstructed Heavy/ready pair
prefix checks passed. Generated=accepted=fired=10,672, final censoring=0;
five Sparse requests completed during drain and remain in full-run G→F.

The original seed 6301 / Heavy-work 1024 run passed execution but became
effective Low at its second close. It is preserved as `MANIPULATION_NOT_HELD`
and excluded; 6302–6305 were not run. The corrected plan and fresh seeds were
fixed before the new execution. The corrected results are descriptive:
Q1 ordering endpoints match, while Q2 ordering shows different directions
across Sparse waiting and Heavy gaps. No universal winner is supported.

[Correction manifest](../artifacts/implementation/cgof-rtl-ordering-exploration/correction-manifest-20261101T030414Z.json)
SHA256 `4cc2aeac9c8976fe0186ef956439458f6e351605f96e825f108cf8877aa78d2b`;
[details](reviews/evidence-review-followup-20261101.md).

The separate preregistered ordering confirmation is complete on fresh seeds
6501–6520: 160 RTL jobs, 80 mixed/isolated pairs, 80 lint configurations and
100 traffic cases passed, with 180 clean JUnit files. All 20 seed blocks held
effective High, matched the full Sparse generation cohort across four settings,
and passed source, input-replay and conservation checks. Generated=accepted=
fired=42,620; final censoring, Sparse cut pending and drain completions are zero.
The plan was written through Codex CLI using `codex/gpt-6-astra`, high, and
execution was delegated to `auto/deepseek-v4.1-flash`; effective backend model
identity is `UNKNOWN` for both.

Primary verdict: **`NOT_CONFIRMED`**. Q1 ordering delta is zero in 20/20 seeds;
Q2 ordering delta and quota × ordering interaction are both −1 cycle in 7/20
and zero in 13/20. There are no reversals, but the frozen rule requires at
least 15/20 joint strict improvements. This establishes neither equivalence
nor superiority of oldest-first. Exploration seeds were not pooled.
[Confirmation manifest](../artifacts/implementation/cgof-rtl-ordering-confirmation/manifest-20261101T045246Z.json)
SHA256 `5d6e690d1844eeae66f4b3da9fc505fdfc34f0a7176b49352abf978ce5d49384`;
[analysis](../artifacts/implementation/cgof-rtl-ordering-confirmation/analysis-20261101T045246Z.json).
Small Sparse cohorts (12–32 requests/run) make sampled P99 equal the run
maximum. The latency contract includes ready=1 drain; these jobs required none.
The W5M ordering production is complete (`COMPLETE_DESCRIPTIVE_EXPLORATION`)
under the frozen five-seed descriptive plan: N4/D16/W5,000,000 finite-Heavy,
one real classifier close at 4,999,999,
bursty ready, full-run Sparse G→F. All five seeds 6601–6605 passed every
gate: 40 RTL jobs, 20 mixed/isolated pairs, 20 lint configurations, 25 traffic
cases and 45 JUnit files, from 2026-11-01T08:43:43Z to 2026-11-02T15:27:08Z
(30.7 h inside the 36 h cap). Every job crossed only the close at 4,999,999
and stayed effective High; the full Sparse generation cohort matched across
the four settings, final censoring and drain completions are zero, and
completion is about 6.25M cycles.

All five seeds read S = 11/11/12/11 cycles, d1 = 0, d2 = −1 and I = −1.
Mixed Heavy max-gap ordering differences (RR−OF) are +2/+2/+1/+2/+1 cycles
for Q1 (mean +1.6) and 0/0/0/0/−1 for Q2 (mean −0.2). A = C_mixed −
C_isolated is identical across all four settings within each seed (seeds
6601–6605: 3/0/7/1/8 cycles), and its RR−OF contrast is zero in 10/10 quota
comparisons. RR thus lowers the Q2 mixed Sparse P99 by one cycle while
raising the Q1 worst-case Heavy gap. That is a descriptive tradeoff, not a
winner or equivalence claim, and it is not a confirmation. It does not revise
the W256 `NOT_CONFIRMED` verdict or pool the two denominators.
[Campaign manifest](../artifacts/implementation/cgof-rtl-ordering-w5m-production/manifest-w5m-campaign-20261102T154205Z.json)
SHA256 `de7f657240ed4dc24c46be3e2166893502dbd2b229aebedf6cc07739649edee5`;
[acceptance](../artifacts/implementation/cgof-rtl-ordering-w5m-production/acceptance-w5m-campaign-20261102T154205Z.json)
SHA256 `9b3f8588f87b6fe980b6181bb61f1224907686242ec24e1e89e4dba8c455ffab`.
Latency recovery, new formal/CDC/PPA/EDA signoff, and CXL/application
measurements remain `NOT_RUN`. Existing October 29 confirmation and the
manuscript retain their separate accepted scope.

## Accepted report update — 2026-10-29

The current [13-page report](../output/pdf/cxl-scheduler-revised-20261029.pdf) integrates the completed twenty-seed finite-Heavy RTL confirmation (80 jobs, 40 pairs) and current-source CGOF replay (30 runs, 60 A/B endpoints). It contains 9 figures and 7 tables, including two new vector figures. [Source](final-report/main-v3.tex), [acceptance/provenance](final-report/update-20261029/REVISION_QA.md), and [release record](final-report/update-20261029/revision-release.json) supersede the earlier report checkpoints below.

The confirmed near-load 1:1/2:1 settings give Sparse mean run-P99 3/4 cycles and mean run-maximum Heavy gaps 9.45/10.85; mixed completion exceeds isolated by 3.05/3.00 cycles on average. All jobs cross one boundary and remain effective High. H3 now has partial multi-seed, single-boundary support; the updated [theory](final-report/update-20261029/THEORY_AND_EVIDENCE.md) and [follow-up protocol](final-report/update-20261029/FOLLOWUP_EXPERIMENTS.md) separate supported conclusions from remaining mechanisms.

Sol/high writing, figures and independent evidence review, agy Gemini 3.8 Flash/high language review, and parent acceptance are complete. The new generator tests pass 5/5; both new figures and all 13 PDF pages were inspected. This report task launched no simulations or EDA. Broader finite-work classification adaptation, CGOF power, and CXL/application measurements remain unmeasured. Historical status statements below retain their original dates.

## Accepted report revision — 2026-10-28

The latest report is the accepted 11-page October 28 revision: [PDF](../output/pdf/cxl-scheduler-revised-20261028.pdf), [source](final-report/main-v3.tex), [QA and provenance](final-report/improvement-20261028/REVISION_QA.md). It incorporates the completed 180 equal-demand, 100 fixed-class and 300 finite-Heavy model jobs, separate single-seed production CGOF RTL, and six CGOF area/STA configurations. The older MODEL_ONLY checkpoint below describes October 27, not the current evidence inventory.

Sol/high authoring and figures, agy Gemini 3.8 Flash/high language review, and parent evidence/layout acceptance are complete. Final report/figure tests pass 10/10 and 5/5; two clean LaTeX passes and all 11 rendered pages were checked. This writing task ran no new scheduler or EDA experiments. H1–H5, CGOF power, broader multi-seed/multi-window RTL and full-system application measurements remain follow-up work. The [release record](final-report/improvement-20261028/revision-release.json) supplies current hashes while preserving the immutable planning snapshot.

## FAI-inspired/CGOF measurement diagnosis —2026-10-27

**MODEL_ONLY HARNESS PASS; PRODUCTION AND SYSTEM EVIDENCE NOT RUN.** Added a
frozen diagnosis matrix for CGOF (Credit-Gated Oldest-First) settings
`CGOF (1:1)` and `CGOF (2:1)`, with FAI-inspired as the public baseline.
It separates quota from ordering via oldest-first/eligible-RR controls,
adds WRR/IWRR model baselines, and reports demand-referenced fairness,
latency decomposition, finite-Heavy completion/span/throughput, service gaps,
quota error, conservation and censoring. Internal evidence keys retain old
identifiers; public output contains no historical-name explanation.

The final post-edit W256 smoke
`artifacts/implementation/diagnosis-20261027/w256-smoke-20261027T091556Z`
passed27/27 jobs,0failures,source-stable; manifest
`5b25f6bca497165e497d58a8e667230081ae0b726c788dcd5240a0ee23304781`,
summary `5a70ab871ae64d5481aa95697e288a5021eee248e9b746696fbc0fdf3a848627`.
All18 comparisons are `NOT_RUN` because smoke cannot infer. `--verify-manifest`
PASS. Full model tests270/270; targeted diagnosis18/18.

No W5M, exploration, confirmation, RTL-control, system, or application run
was performed. Scheduler fire/cycle is not measured memory bandwidth;
generation-to-fire is not memory-response latency. If WRR/IWRR or eligible-RR
controls explain a gain, retain the diagnosis and stop the novelty claim.
The accepted498-row matrix is unchanged.

The v3 report was regenerated with six figures and recompiled twice. Final PDF
`output/pdf/cxl-scheduler-v3-cgof-diagnosis-final-20261027T092103Z.pdf`
is12pages, SHA256
`E277786796638EE3F1DDCABF0CFE87BBF79AC67CDBB3EDC988614FF33C233FCD`;
8report/figure tests pass, all12pages visually checked, and no
overfull/undefined/LaTeX-warning remains. Figure1 label overlap found in the
first visual pass was fixed without changing data. See
[diagnosis evidence](experiments/diagnosis-20261027/README.md),
[literature boundary](experiments/diagnosis-20261027/LITERATURE.md) and
[report QA](final-report/CGOF_DIAGNOSIS_QA.md).

## Main-SQ extension diagnosis —2026-10-23 (COMPLETE; conditional stop)

Experimental branch `experiment/main-sq`, branch pointbb7f407. Original15 heavy/sparse
results/PPA independently re-audited PASS; frozen Spec and accepted Main remain unchanged.
Native Opus5.5/medium RTL Agent Team testbench-dev implemented passive tracing; W256
pilot20261023T082655Z_633 passes3strictlint/32units/3RTL and exact oldmetrics/trace joins.
First workflow's internal safeguard and two repaired recorder-unit failures are retained.
Real W5M seed509 three-policy replay `MSQ-main/20261023T083405Z_1850` completed from
3e457cc, outerexit0/2825.623s, full10M training per job. All lint/32units/3RTL/JUnit and
independent trace audit PASS; every nonvolatile metric equals the old seed509. Pilot plus
production: six actual RTL runs/31,962,468 nonreset cycles. High quota exhaustion with
pending High work is directly observed. Offline fixed-slot SQ1/SQ2 P99=24/25 vs Main24,
max34 vs31, with source2 regressions: benefit gate FAIL. SQ RTL/model/five-policy matrix/
Formality/PPA remain NOT_RUN by the approved conditional stop. Main-HQ/Main-AGE require
a separate design decision. Final518protectedfiles and264earlier rawmetrics unchanged;
no Final edit/build/render or FastX job. [Evidence and recommendation](experiments/main-sq/README.md).

## Heavy-host/sparse-host experiment —2026-10-22 (ACCEPTED15/15)

**15/15 production RTL simulations PASS**, all actual outer/build/sim exits0, raw JUnit and
independent exact matrix/cohort/histogram/source audit PASS;5 matched external trace groups.
Run20261022T034507Z_311 finished UTC05:45:13, elapsed7210.594s. Actual156,657,531 nonreset
cycles including150M real training; no preload/skip. All sparse cohorts complete before heavy-off.
Single-arrival sparse runP99 means FCFS18.2/RR11/Main10cycles; burst33.8/17.2/20.8.
Main vsFCFS pairedP99 reduction45.03%/38.64%; vsRR9.09% better isolated,20.78% worse burst.
All30 measured intervals output1transfer/cycle; heavy host retains~97.7%, no permanent50%cap.
Five seeds/N4 finite trained-state evidence; no universal/application claims. [Accepted results](performance/HOG_SPARSE_RESULTS_2026-10-22.md).
Previous264rawmetrics/348protectedfiles/188Finalfiles unchanged. No active scope/writer.

The following RUNNING wording preserves the startup checkpoint:

Pilot20261022T034155Z_369/outerexit0 ACCEPTED: lint3/units26/RTL3, independent raw audit and
13 corruption rejections PASS; code frozen. HS-main20261022T034507Z_311 started UTC03:45:02,
15 production runs pending, six jobs/buildjobs2. No aggregate acceptance or production benefit
claim until full raw audit. Prior shell-exit capture failure retained; successful repeat uses
Python subprocess numeric exit. Final/old348protectedfiles unchanged.

Owner authorized execution of the saved plan. Native Opus5.5/medium focused workflow actually
returned weekly429/exit1 after248.676s before code writes; approved Sol/high fallback implements
new isolated verification tooling, Codex independently reviews. Initial checkpoint below is historical.
[Execution record](performance/HOG_SPARSE_RESULTS_2026-10-22.md); Final/RTL/model/Spec/PPA protected.

The following paragraph records the initial design checkpoint; its NOT_RUN wording is historical:

Owner asks to test Main's intended sparse-request protection under one persistent heavy host.
[Saved experiment design](performance/HOG_SPARSE_PLAN_2026-10-22.md): N4, FCFS/RR10/Main,
native W5M/two real training windows;15 planned policy/seed runs, isolated and burst sparse
profiles with background-on completion guards. Primary sparse directG2F P99 vs FCFS; RR10
separate comparison. Allows no-benefit/regression outcomes; no new result claimed.
No new code delegation/simulation/SSH/PPA or Final edits. Previous31 tracked performance
files and264 raw metrics hash-verified; [preservation index](performance/EVIDENCE_PRESERVATION_2026-10-22.json).

## Source-placement/cardinality sensitivity —2026-10-22 (accepted)

Owner-authorized tests1/2: **42/42 real RTL runs PASS**,14 Low-source placements×three policies,
N4/W256/512 training+240 measurement. Raw JUnit/exits/trace/cohort audit PASS;63,498 nonreset
cycles. Source permutations and1L/3H,2L/2H,3L/1H confirm Main half-output class allocation;
per-source equality depends on class size. Same measured throughput239/240 for all policies.
First unsupported W4096 lint failure preserved; corrected without RTL change. Pilot9PASS,
98 units, three strict lint sets; independent six tests/11 subtests and ten evidence mutations.
Native weekly429/exit1 triggers approved Sol/high fallback; Codex independently accepts.
[Actual results](performance/PLACEMENT_RESULTS_2026-10-22.md). Final188 files, RTL/model/Spec/PPA
unchanged; no SSH or active test writer. Short-window finite sensitivity, not production/adaptation proof.

## Controlled performance follow-up —2026-10-22 (accepted)

Owner authorized the review's four complementary tests. [Follow-up plan](performance/FOLLOWUP_PLAN_2026-10-22.md):
N4 true-W5M trained competition, fixed-load controls, finite complete batch, per-source latency
and ready-opportunity service gaps. **ACCEPTED:42/42 formal RTL runs PASS**, all three outer exits0;
raw JUnit/trace/cohort/histogram audit PASS,14 matched intended trace groups,35,376,594 actual
nonreset cycles (warmup30,360,000;measurement3,903,072;drain1,113,522). No active scope/writer.
Final frozen pilot21 RTL cases/43 unit tests INFRA_SMOKE_PASS; parent73 tests/16 subtests PASS.
Native Opus5.5/medium was actually invoked;195s/exit1 weekly429 before code changes. Owner-authorized
GPT6.1Sol/high fallback implements isolated verification tooling; Codex independently reviews.
No RTL/model/Spec/PPA or Final-report changes, no SSH, gem5 or Algorithm-2 expansion.
[Detailed accepted result](performance/FOLLOWUP_RESULTS_2026-10-22.md): trained throughput0.99999
for all policies; Main source0Low share50.001% versus~25% FCFS/RR, source-service Jain~0.75
versus~1 under equal persistent demand. Complete eligible-ready gap max FCFS4/RR31/Main13.
This is the approved class-quota reconstruction's observed tradeoff, not a general fairness benefit.

## Descriptor performance instrumentation —2026-10-22 (latest owner scope)

Owner confirmed descriptor-only/project-owned workloads; gem5 deferred and Algorithm-2 excluded
from the main matrix. **Do not edit/rebuild the Final report.** This supersedes the v0.1 owner
choices/closed-loop execution plan below. [Plan v0.2](APPLICATION_EVALUATION_PLAN.md),
[evidence inventory](performance/EVIDENCE_INVENTORY_2026-10-22.md),
[new test record](performance/TEST_RECORD_2026-10-22.md).

Archive audit accepts180 primary and44 long/stress jobs, adding0 RTL cycles. Three N4/seed509
infrastructure pilots pass100k measured cycles each;27 recorder/audit tests plus10 subtests pass.
New180-run primary replay for missing phase/backlog/occupancy observation is **ACCEPTED:180/180 PASS**
after raw JUnit/metrics/legacy-equality audit. Total18.3M new measured RTL cycles including pilots;
1,080 phase-kind rows and10,080 per-source rows,20-run descriptive uncertainty/paired differences.
All old metric fields except host wall time identical;188 existing manuscript/literature and58
frozen functional files verified unchanged. No active batch/writer remains for this task.
No Spec/RTL/model/PPA changes, SSH or new application-performance claim. Existing manuscript
and literature modifications are preserved independently.

## Application-performance experiment planning —2026-10-22

[Evaluation plan v0.1](APPLICATION_EVALUATION_PLAN.md) defines paired FCFS/RR/Main descriptor
and closed-loop application studies: IPC, weighted/harmonic speedup, max/mean slowdown,
latency cohorts, fairness, memory goodput and separately qualified slot/link utilization.
**PLAN_ONLY / NOT_RUN.** N4 application pilot precedes a proposed36-run shared matrix plus
matched alone baselines; workload/trace sources and byte/link scope still need owner selection.
No new RTL, simulator installation, SSH, delegation, application result or PPA claim. Existing
uncommitted final-report/literature changes are preserved and not adopted as new evidence here.

## Academic final report prepared —2026-10-21

Evidence-backed English LaTeX report prepared in [final-report/main.tex](final-report/main.tex),
matching the supplied first progress report's two-column academic format. Native editor and
standalone PDFLaTeX compilation succeed; the 8-page PDF has been rendered and reviewed page by
page. [Editing/rebuild guide](final-report/README.md), [delivery QA](final-report/QA.md),
[local PDF](../output/pdf/cxl-scheduler-final-report.pdf). Numerical tables and vector-plot
coordinates are generated from pinned accepted JSON/profile inputs, with changed-input rejection.

The report consolidates completed functional, primary v2 area/STA, Algorithm-2N4, Formality and
qualified power results. Newly available progress/FAI/BLISS PDFs were inspected for formatting
and source discussion; historical frozen-Spec provenance is preserved. No RTL/model/Spec/profile
or accepted result changes, SSH/EDA rerun or new implementation claim. Owner wording/course
submission review remains; this is a reviewable report, not claimed submission/grade acceptance.

## Latest accepted test supplement —2026-10-21

**TEST_GAPS_CLOSED_WITH_DOCUMENTED_LIMITATIONS.** Actual14/14 RTL/netlist Formality pairs pass
(primary9, supplementary Main/Algorithm-2 N4 pair, current Main N4/8/16 bridges), with intentional
mutation correctly failing. Actual18/18 cold seed510/511 and3/3 N4 real-boundary gate/SAIF/PT
cases pass:32,098,500 checked cycles,2,100,000 measured. No shortened production W, preload,
time skip or RTL/model/Spec/profile change. Frozen export source43bf975; original seed509
dataset remains intact. [Equivalence](FORMAL_EQUIVALENCE_2026-10-21.md),
[supplementary results](POWER_SUPPLEMENT_2026-10-21.md),[JSON](ppa/power-supplement-20261021.json).

Independent actual raw audits,21case constant/range/unknown-record connectivity diagnoses and
final source/SAIF hashes pass. Six N16 redirected empty-collection query errors were discovered,
retained and repaired with explicit zero-inventory assertions; the accepted replacement reports
have no errors.1,186,585 nets file annotated,368,663 FFclock pins reviewed;206 literal-constant
cells and42 zero-activity range pins diagnosed. FCFS/RR table-range warnings remain qualified;
cold transient X retained, three warmed measurement windows have no transient X/Z. Native
weekly-quota block and owner-authorized Sol/high provenance retained; no new native PASS claim.

N4 boundary total mW:FCFS3.383/RR2.586/Main3.495. Sample deliberately includes1classification/100k
vs natural1/5M; not production-average power or clean physical signoff. Main high/low labels
are model evidence, with full gate-pin agreement and independent equivalence. No active code
writer/test batch remains; no owner architecture decision is pending. Next: final project report
using accepted functional, area/STA, Algorithm-2N4, Formality and qualified power evidence.
APR/SDFglitches/CTS/multicorner,Algorithm-2power and trainedN8/16 power remain deferred.

**Earlier RUNNING/NOT_RUN checkpoints below are historical and superseded by this outcome.**

## Supplementary execution in progress —2026-10-21 UTC05:27

Clean tooling/export source `43bf9755810cb5ce920b14cc16deb258f352f150`. All18 cold seed510/511
and all three true10,099,500-cycle N4 model exports completed exit0. Six cold intended-trace
groups match across policies; the boundary intended trace also matches across all three.
FCFS/Main600k cold pin rows are identical; the boundary pair first differs exactly at global
cycle10,000,000, following the second closing. File comparison is not extra simulation coverage.

Actual FastX supplementary VCS/PT runs are **RUNNING**, not accepted results yet. Latest parent
raw audits14/18 cold cases pass; long gate replays Main/FCFS/RR are active (Main3M checked,
FCFS2M at this checkpoint). Cold-only SAIF unknown residency and unused declarations are being
audited separately. Existing primary seed509 dataset and14 accepted Formality proofs remain
unchanged. Do not restart active jobs or mark model exports as completed gate/power tests.
See DEVELOPMENT_REPORT and ignored `.setup-logs/power-20261021/` monitors/batch logs.

## Additional verification —2026-10-21

**FORMALITY_EQUIVALENCE_ACCEPTED:**14/14 actual source/parameter pairs pass: primary9,
supplementary Main/Algorithm-2 N4 pair and current Main RTL versus original primary mapped
netlists N4/8/16. Strict undriven-output handling;0 failures/aborts/unverified/unmatched/active
black boxes/user exclusions. Six primary FCFS/RR cases retain one constant register not compared
each. Primary post-match diagnostics0undriven nets; intentional output inversion correctly fails.
Final remote14/14 immutable-input recheck exit0. See [equivalence report](FORMAL_EQUIVALENCE_2026-10-21.md)
and [audit](ppa/formality-20261021.json). This is RTL/netlist equivalence, not proof against Spec.

Power extension tooling independently accepted locally: Windows18PASS+5simulator skips,
WSL22PASS+1Tcl skip (complementary platforms), actual three-policy strict Verilator fixtures,
100k legacy replay,14 expected malformed/mutated rejections and genuine four-state X controls.
Native Opus5.5/medium was blocked then explicitly exhausted weekly quota; authorized Sol/high
completed the frozen tooling. No RTL/model/Spec/profile change. [Supplementary plan](POWER_EXTENSION_TEST_PLAN.md):
18 additional cold-seed cases and three true10,099,500-cycle N4 boundary replays remain
**NOT_RUN** at this checkpoint. Old seed509 power dataset remains accepted with its limits.
No new architecture decision is required. Earlier dated entries below are historical.

## Activity-annotated power continuation —2026-10-21

**NINE_CASE_ACTIVITY_POWER_ACCEPTED_WITH_LIMITATIONS.** Actual FastX-NN VCS/PT W-2024.09/PrimePower, nine compile/sim/PT/wrapper exit0, 900000 checked cycles; clean power export c0658fb, unchanged accepted mapped source759f86b/profile6f4777f0. All553754nets activity-file annotated, all172007FFclockpins reviewed;70literal-constant leaf gaps individually verified. FCFS/RR retain2ramp+1load table-range warnings percase on unusedconstantcontext, Main3/3check_power succeeds; no clean-signoff claim. All171145TFIPC warnings are audited unusedoutput omissions. Final remoteimmutablehashcheck and allnine independent rawaudits/diagnoses PASS. [Power report](POWER_RESULTS_2026-10-21.md),[JSON](ppa/power-20261021.json),[method](POWER_METHOD.md),[development record](DEVELOPMENT_REPORT.md). Main all-H, single seed/coldreset100kcycles; no trained-state/physical/glitch/multicorner/formal/Algorithm2power claim. Native power-analyzer quota failure and owner-authorized Sol/high tooling provenance preserved. No RTL/model/Spec/profile change, no new architecture decision. Next: consolidate final project report using accepted functional, area/STA, Algorithm-2N4 and qualified power evidence; additional long/train-state power only if that claim is needed.

**The sections below retain earlier checkpoints; their pending/NOT_RUN statements describe those dates and are superseded by this latest power outcome.**

## Active supplementary work —2026-10-21

**SUPPLEMENTARY_N4_AREA_STA_ACCEPTED**, clean sourcec8e7ea8, unchangedfrozenv2profile. Actual FastX-NN DC/PT/wrapper2/2exit0, setup/hold/electrical2/2MET. Main/Alg2area110089.845892/110058.332037 (−0.028626%), sequentialcells9011/9011, setup+10.496409/+10.547482ns, holdboth+0.039940ns. Each68constant_disabled untestedchecks retained.58906used drivers audited under positive original limits,0ordinary/CCSviolations,390temporarylimits restoredpercase; finalremotehashcheckexit0. [Supplement report](PPA_FAI_SUPPLEMENT_2026-10-21.md),[JSON](ppa/algorithm2-n4-20261021.json). No materialprimaryPPAconclusionchange; N8/16supplementdeferred. Primarynineunchanged; power/physical/multicorner/formalunrun.

Long verification/tooling continuation **LONG_FUNCTIONAL_ACCEPTED**, owner-authorized **GPT6.1 Sol/high** after Claude session-limit. Actual N4 production20million measured cycles/4W5M windows PASS, longstress10/10/6millioncycles PASS; every stress run all16transitions, stable source hashes, zero outstanding after drain. Main/M6 units856/447PASS; parent329smallchecksPASS and independent raw/JUnit/closing/state audit complete. Worker later hit API429; parent completed audit/report. No RTL/model/Spec/Tcl/profile change. [Long results](phase-5-verification/M6-long-results.md). Supplementary PPA remains NOT_RUN pending clean export/actual FastX run.

Earlier directed milestone: Algorithm-2 N4 **DIRECTED_AND_BEHAVIOR_SCOPE_ACCEPTED** (long verification subsequently completed above). Native RTL Agent Team `rtl-coder`, Claude Code2.1.304/plugin0.14.6, actual `claude-opus-5-5` / medium, session `77281b50-edbf-4a55-9539-a77ad9d0736d`, exit0. Final M6 `20261021T004406Z_12107`:441 tests,45 strict lint,12 probes,4 expected rejections; six shared baseline unit scopes pass. Identical-stimulus comparison20runs/10pairs/1,920,000 total trace cycles passes. Codex independently checked raw JUnit, trace/digest/count integrity, full pairing and matching source hashes. See [M6 results](phase-5-verification/M6-results.md) and [independent review](../reviews/phase-4-rtl/codex-fai-alg2-review.md). Frozen Spec and accepted primary-nine dataset unchanged. No Algorithm-2 PPA claim.

VPN-restored SSH verified on FastX backend4-16 with the previously approved pinned key. Library SHA256 still844d4474…; DC/PT reportW-2024.09. DC `-version` returns1 despite printing its version, so the first fail-fast preflight stopped before PT; separate captured version/status probe established PT version/exit0. This is connection/tool discovery, not scheduler synthesis.

## Common v2 nine-case results accepted —2026-10-21

**ACCEPTED_FOR_PRE_LAYOUT_COMPARATIVE_AREA_STA.** All9 actual DC/PT/wrapper runs exit0 from clean759f86b under one frozen cap075-v2 profile/canonical6f4777f0…. Setup9/9, hold9/9 and original-limit electrical9/9 MET. Minimum setupMain16+1.158148ns, hold+0.084335ns, area437622.506788/FF35773.140untested checks in4cases are allconstant_disabled;5cases alltested.542065used driver pins have positive original caps and0ordinary/CCS violations,390temporary limits restored per case. Codex raw audits and native RTL Agent Team synthesis-reviewer Opus5.5/medium492checks pass, CLIexit0. [Results](PPA_RESULTS_2026-10-21.md),[JSON](ppa/primary-20261021-v2.json),[native review](../reviews/phase-5-verify/primary-v2-results-review.md),[development record](DEVELOPMENT_REPORT.md).

Accepted comparator functional regressions preserved; no RTL/Spec/flow code change this stage. v2 is the new common comparison dataset; v1/pilots remain history. Power/Algorithm-2/physical/multicorner/commercial equivalence unrun. Next: Algorithm-2 N4 implementation and independent model/functional/behavior review, then same-method supplementary synthesis. Final readonly SSH query failed after complete retrieval; logs retained and no local SSH process remains.

## Earlier checkpoints (historical)

## Common v2 measurement freeze —2026-10-21

Profile `saed32-rvt-tt-25ns-forqa-cap075-v2` fixes the same numerical/flow settings as the successful cap075 pilots for all nine configurations, canonical SHA256 `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`. Native RTL Agent Team synthesis-reviewer / Opus5.5/medium exit0,97binding checks pass, verdict[PASS_COMMON_METHOD](../reviews/phase-5-verify/common-profile-v2-review.md). Commit the profile and prepare one clean source for all nine; actual new results remain NOT_RUN at freeze. RTL/Spec/SDC/flow code unchanged, accepted functional gates preserved. FROZEN means fixed methodology, not all-case signoff. [Development record](DEVELOPMENT_REPORT.md) retains provenance and pending work.

## Current comparator candidate —2026-10-21

Shared `cxl_fcfs_sel` at `d82f1b54ca54af2344ad07d914680547003f526f`, clean synthesis sourceb257ee8, frozen Spec1af80967. **FULL_FUNCTIONAL_REGRESSION_ACCEPTED; MAIN16_SINGLE_PILOT_MET.** Native RTL Agent Team `rtl-coder` / Opus5.5/medium exit0; all74 response records match. Native and independent actual RTL comparisons each pass21configs/81,108,288vectors; general equivalence is hand-derived, not formal-tool signoff. M1/M2/M3/M4/M4-q1/M5 pass286/526/550/430/195/805; primary180/180, Main stress30/30 (18million trace cycles), production3/3 (60million non-reset measured cycles,12complete windows). Raw JUnit/lint/full_scope/metrics and per-stage76source hashes independently checked. Original SIGHUP-interrupted Main primary preserved as incomplete; full replacement run passes.

Actual same-cap075 Main16 DC/PT/wrapper exit0: area437622.506788 library units, FF35773, setup+1.158148ns, hold+0.084335ns, zero timing/cap/slew violations and0untested (143344tested/met). Compared with the old same-profile pilot: setup+2.066094ns, area+0.09004%.390limits restored;116993used output-driver pins all have positive original limits and0ordinary/CCS violations; library disk hash unchanged. Single pilot does not replace original nine-case data; cap075 remains PILOT. See [measured result and test IDs](PPA_COMPARATOR_PILOT_2026-10-21.md), [JSON](ppa/comparator-main16-20261021.json) and [detailed report source](DEVELOPMENT_REPORT.md). Next: freeze a shared revised method and remeasure/review all nine; power/Algorithm-2/physical/multicorner remain unrun.

## Preserved primary FastX results —2026-10-20

The latest separate cap075 pilot outcome is in the closure follow-up below: both measured pilots clear cap/slew, while Main16 setup still fails. These original primary-nine measurements remain preserved without replacement.

**PRIMARY_NINE_COMMANDS_COMPLETED; SETUP_MET_8_OF_9; ELECTRICAL_CLOSURE_OPEN.** All nine DC/PT W-2024.09 batches actually ran on FastX from clean flow/export commit `081f8a219911909bda8472ae4b257d3e6ed3122d`, with the same frozen25ns/SAED32 RVT TT/FO4/ForQA-top/compile-medium/single-core profile. Each batch exited0, with exact completion markers, mandatory reports and independently verified source/result hashes. This establishes completed measurements, not signoff acceptance.

FAI Main N16 has **32 setup violations**, worst PT setup **−0.870709ns**; all nine hold checks meet their constraints. FCFS N16's +0.000811ns setup margin is only about0.81ps and is not robust timing closure. Every case has OPEN PT max-capacitance findings; FCFS N4, Main N4 and Main N16 also have slew violations. DC/PT capacitance-report disagreement remains unresolved. The main N16 failure is preserved; the earlier20ns pilot is a separate mapping run and does not replace the failed25ns result. No constraints or library limits were waived.

Owner-authorized SSH, pinned host key, module, DC/PT license use and existing SAED32 library read/hash are VERIFIED by actual commands. No proprietary asset was downloaded. RTL/models/TB/frozen Spec are unchanged. Existing functional acceptance remains180/180 primary plus the recorded Main unit/stress/production runs; the36 Windows/WSL runner infrastructure tests are separate evidence.

Native RTL Agent Team Opus5.5/high actually authored the runner and repairs before the owner changed future calls to medium. The subsequent native synthesis-reviewer hit HTTP429/session limit, exited1 and did not write a review; the explicitly authorized **GPT6.1 Sol/high** fallback completed the independent nine-case methodology review. Preserve the original failed invocation and fallback provenance. Power, commercial equivalence, physical implementation and multicorner signoff remain NOT_RUN; Algorithm-2 is NOT_STARTED.

See [nine-case results and self-inspection links](PPA_RESULTS_2026-10-20.md), [machine-readable results](ppa/primary-20261020-v1.json), [execution and repair history](PPA_EXECUTION_2026-10-20.md), [methodology review](../reviews/phase-5-verify/FastX-PPA-methodology-review.md) and [frozen profile](../syn/profiles/saed32-rvt-tt-25ns-forqa-v1.json). Earlier dated handoff/pilot/quota statements below are historical and superseded where these results record actual execution.

Next milestone: investigate the DC/PT electrical-rule discrepancy and Main N16 critical path under the shared framework, then review a common closure plan. Do not silently change RTL, add policy-specific stages or timing exceptions, relax library rules, or call these measurements accepted PPA. Any common flow revision requires new provenance and a fresh comparable nine-case sweep; supplementary Algorithm-2 remains separate.

## Closure diagnostic follow-up —2026-10-20

**TWO_CAP075_PILOTS_ELECTRICAL_MET; MAIN16_SETUP_NOT_MET.** The identical candidate profile also completed actual Main N16 DC/PT/wrapper exit0 at clean sourceaa89771. Area437228.837383 (+0.2244%),FF35773, setup−0.907946ns/hold+0.085328ns;32setup violations remain, cap/slew0/0. All390temporary limits restored; all116345 remapped output pins have positive original limits and0ordinary/CCS cap violations. No SDC cap leakage or proprietary library changes. This fails timing despite electrical improvement; candidate stays PILOT and no replacement nine-case sweep is launched. Next: equivalent shared timestamp-comparison candidate, proof/tests and required regressions before synthesis. Original nine results remain unchanged and power is NOT_RUN.

**CAP075_FCFS4_PILOT_MET; PRIMARY_NINE_BASELINE_UNCHANGED.** The full26731-driver original FCFS4 load survey reconciles all1118 PT capacitance violators to receiver-load accounting. A separate reversible0.75 DC optimization-only cap target was implemented/tested by the authorized Sol/high agent and reviewed by Codex. After an actual pre-compile float32 readback failure (all attempted edits restored), a native-calibrated repair passed44 unique Windows/WSL infrastructure tests. Fresh actual DC/PT/wrapper exit0 at source046721b gives FCFS4 area103730.908806 (+0.70%),8856 FFs, setup+9.881229ns/hold+0.033790ns and0cap/0slew violations against original library limits.390 temporary limits restored; no cap overlay leaks to SDC. All27231 new used output pins have defined original limits;0full-driver CCS cap violations.64constant-disabled untested timing checks remain explicitly recorded. Candidate status PILOT, not adopted; Main16 and all-nine closure remain pending. See the actual cap075 section in the diagnosis below.

Same-net DC/PT re-read probes and an isolated FCFS N4 high-effort DC/PT pilot actually completed. Three sampled pins show DC ordinary capacitance below the library limit while DC CCS totals match PT violating loads; available setting sensitivities did not remove DC0/PT1118 findings. High-effort FCFS4 emits the same mapped module bodies and unchanged area/slack/cap/slew results as medium, so it is not adopted. Main16 path analysis attributes20.249199ns to the shared balanced FCFS selector, including120 ripple-carry cells across four32-bit subtractors. No RTL/frozen profile/Spec change or Main16 high-effort run.

See [diagnosis, actual pilot and common closure gates](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md). Next engineering step is full-net receiver-load comparison and a supported, conservative synthesis optimization target while retaining original PT/library acceptance limits. The sampled discrepancy is explained; all-nine electrical closure and Main16 setup remain OPEN. Power/Algorithm-2 are unchanged.

## Functional acceptance and historical handoff —2026-10-17

Owner handoff2026-10-17: [階段小結](STAGE_SUMMARY_2026-10-17.md) and [FastX手動操作](FASTX_HANDOFF.md). Functional work is closed for this stage; the owner will run commercial EDA. The handoff describes explicit N/policy selection in a manual DC copy; generic remote runner parameterization and all actual FastX execution remain pending. No RTL/model/test/toolchain or frozen Spec changes in this handoff.

Updated2026-10-17 (Asia/Taipei). **M5_MAIN_FUNCTIONAL_ACCEPTED**. Approved Spec v1.0 remains frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Verified source: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`. This accepts Main functional integration and the common/FCFS/RR regression, not the whole project or PPA.

Native final-review outcome: both reports, all raw audits, post-review hashes and the manifest were saved before the final-summary API call returned HTTP429/session limit. The CLI then exited1 naturally after its built-in retries; this is not a successful CLI exit. It reported reset2026-10-17 13:50 Asia/Taipei (an estimate, not verified availability). All148 actual inference response records are claude-opus-5-5; the additional synthetic record is the API error, not another model. Native written verdict PASS_M5_MAIN_FUNCTIONAL and Codex acceptance rest on inspectable completed evidence, not process success. No further API retry, settings change or automation was started. Future native Claude work waits for account availability; current documentation/independent acceptance can finish locally.

## Accepted functional milestones

M1 descriptor/FIFO, M2 common output/hold, M3 FCFS/C1, M4 RR and M5 Main FAI are functionally accepted. One policy-selectable switch_top retains the shared105-bit descriptor, D16 per-source FIFOs, M1 output, ready/valid timing, hold controller and TB-only responses. No policy-specific pipeline/bypass/buffering was introduced. RR has no unused timestamp bank/counter/oldest selector; FCFS/Main retain required arrival metadata, confirmed by structural positive/negative controls. Existing independent common review remains applicable with the current full regressions.

| Scope | Actual tests | Run ID |
| --- | --- | --- |
| Main M5, native verifier | 805 PASS | `20261017T012755Z_5680` |
| Main M5, independent Codex execution | 805 PASS | `20261017T012115Z_2007` |
| Main stress | 30 PASS | `20261017T013952Z_8032` |
| Main primary | 60 PASS | `20261017T015238Z_9805` |
| Main production | 3 PASS | `20261017T015838Z_13196` |
| M1 descriptor/FIFO regression | 286 PASS | `20261017T034126Z_13943` |
| M2 common output/hold regression | 526 PASS | `20261017T034156Z_14547` |
| M3 FCFS regression | 550 PASS | `20261017T034300Z_16317` |
| M4 RR10 regression | 430 PASS | `20261017T034404Z_18077` |
| M4-q1 supplementary regression | 195 PASS | `20261017T034453Z_19058` |

Both805-test unit runs recorded ae5a682 with the repaired code uncommitted; audited tested-file hashes match committed cefbbb0 (the later report document is excluded). The full long batch ran clean at cefbbb0.

M5 unit805 =196 reference pytest +39 TB-helper pytest +570 cocotb (19 cases x N4/8/16 x W64/256 x seeds509..513). Each full M5 unit run also passed27 strict lint configurations and9 structural probes;3 Algorithm-2 expected rejections are separate negative checks. Repeated reference/helper collections across scopes are not unique additional RTL coverage. Final scopes have zero failures/errors/skips/NOT_RUN and no simulator warning relaxations.

Full stress30 covers N4/8/16 x W64/256 x seeds509..513,400,000/800,000 measured trace cycles:18million total, with all16 Main state/evidence transitions in every run. These trace cycles include recorded resets. Primary60 covers N4/8/16 x seeds509..528 x100,000 measured cycles:6million total, all60 intended trace hashes match the tracked FCFS record. Every primary cycle matches the FCFS mirror and the accepted FCFS common metrics. No primary window closes at W5,000,000; this is pre-classification evidence, not a fairness/adaptation conclusion.

Production3 runs each simulate20,000,000 actual non-reset measured cycles at W5,000,000:60million total and12 complete windows. No time skip, state deposit/preload or smaller-window substitute. All three N configurations verify closing-edge fire inclusion, S=sum(B), exact integer thresholds, Main class changes, held grants across boundaries and final drain/response conservation. B/S/index are23-bit and threshold operations unsigned32-bit. Per-cycle oracle, independent pin/history, full105-bit/source/order/hold checks remain active.

Primary functional matrix is **180/180**: accepted FCFS60 (`20261016T014224Z_3877`), RR60 (`20261016T013811Z_371`) and current Main60. This does not mean nine synthesis experiments completed.

## Actual agent execution and repaired failure

Native Claude Code2.1.301 and installed RTL Agent Team0.14.6 actually ran the focused verification and implementation/verification workflows. All inspected root/subagent response models are `claude-opus-5-5`, with explicit invocation-local high effort and route `claude/claude-opus-5-5`; global service/settings preserved. Native sessions `49e427c2-a597-447d-b40b-a8ece8c67d92`, `d14dce3f-1edc-44a4-bc34-ba8319dc7b19` and `b10049ae-345e-4f26-8930-b6b83e1caf8e` cover long-run preparation and the narrow TB repair. Final installed `rtl-agent-team:func-verifier` review session: `19094c25-e5cc-4189-a1af-68113637ad07`.

Claude authored RTL/models/TB/runner and the exact eight-stage batch script. Detached native launches failed before batch startup; failed launch evidence is preserved. Codex then executed that same native-authored script in foreground WSL, exit0, and independently audited original JUnit, metrics, exact scope gates and source hashes. Final native func-verifier reviewed the completed evidence; it did not personally execute the long batch. Codex did not substitute as RTL/TB author.

The first full stress attempt `20261017T010035Z_1025` executed9 cases (7FAIL/2PASS;21NOT_RUN). Failures were the summary assertion that incorrectly required a full-FIFO closing measurement fire's next-cycle-ready observation to remain inside the frozen measurement snapshot. The first drain cycle owns that observation. Claude's source `cefbbb0` repairs only TB accounting, adds directed case19 and updates the pinned collection/report. The repair asserts exact measured-plus-observed-boundary-owed and exact whole-run relations, including actual first-drain ready/held-push/descriptor checks. No RTL/model/shared-helper/trace/Spec change or arbitrary off-by-one tolerance. Original failed logs remain preserved. Fixed-seed510 six simulations passed, but their subset gate correctly failed; only the later full30 is accepted.

## Evidence and remaining work

Evidence roots (ignored raw files stay local): `artifacts/implementation/<scope>/<run-id>/` contains summary/logs/raw JUnit/metrics. `.setup-logs/implementation/resume-20261017/m5-long-regression-2/` contains exact batch commands/exits, all144 tracked-file launch hashes, native provenance and Codex `stress-audit.json`, `primary-audit.json`, `production-audit.json`, `batch-audit.json`. The source stayed unchanged through the complete batch. Unit independent audit is in `m5-stress-boundary-repair/codex-review/independent-m5-verdict.json`. Native final review logs/diff/manifest are in `m5-final-review/`.

Algorithm-2 is NOT_STARTED, remains a separate approved interpretation, and follows the primary nine synthesis experiments. No IEEE PDF inspection or cycle-identical paper reproduction is claimed; Main four-state hysteresis and the shared one-output10/10 alternation follow the approved project specification. Multi-output/APR/optional extensions remain deferred.

Historical2026-10-17 handoff checkpoint (superseded by actual2026-10-20 results above): all nine FastX synthesis/STA/power/PPA configurations were NOT_RUN. SSH/tool/license access was NOT_VERIFIED; the registered-adder smoke is user-reported environment evidence only. Existing remote templates need reviewed N/policy parameter selection and a frozen pilot-derived common methodology before the sweep. Formal/CDC/SystemC/UVM, numerical coverage and RTL mutation campaigns are NOT_RUN/deferred, not PASS; prior14 model mutants do not establish RTL coverage. Strict Verilator checks passed; the earlier default Verible style conflicts remain separately recorded.

Historical2026-10-17 next step (completed by the2026-10-20 execution above): the owner runs the manual FastX preflight/pilot, freezes one common PPA profile and then runs the nine DC/PT configurations. Use the exported source snapshot and FASTX_HANDOFF.md; the manual parameter-selection instructions are not yet validated on the host. Required there: working FastX login/tool licenses, a writable project directory, the existing absolute SAED32 RVT `.db` path/permission and pilot-derived constraints. SSH hostname/authentication/host key are needed only if the optional remote automation route is chosen; sharing SSH access with Codex is not required for this manual handoff. Do not copy proprietary assets. DC/PT W-2024.09, module `Synopsys_x86-64/2024`, SAED32 RVT `saed32rvt_tt0p78v25c.db` remain the user-reported target environment.

Parameter plumbing, source lists and constraint proposals are engineering work; final shared clock/uncertainty/I/O/load/transition/effort/wire-load/reporting and power assumptions must be recorded from the real pilot. No new correctness-critical architecture choice or fresh Spec approval is currently needed. Do not start the supplementary Algorithm-2 implementation or claim mapped policy overhead before actual synthesis.

See [M5 results](phase-5-verification/M5-results.md), [native integration report](phase-5-verification/M5-integration-results.md), [native review](../reviews/phase-5-verify/M5-functional-verification.md), [independent acceptance](../reviews/phase-4-rtl/codex-fai-main-review.md) and [continuation](RESUME_CLAUDE.md). Historical failures/quota checkpoints remain in IMPLEMENTATION_RESULTS.md, older phase reports and Git. The prior08:00 quota checkpoint is superseded by actual work; the later final-summary429 is recorded above.

Existing repository/main and WSL toolchain are preserved: Python3.12.3, Verilator5.052, cocotb2.1.0, pytest9.1.1. No recreation, reinstall or proprietary asset copy.
