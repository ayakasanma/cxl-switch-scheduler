# CXL Project progress tracker

## Evidence-review follow-up — 2026-11-01

- PASS: P0–P4 required-source, common-generation, ordering identity, quota
  history, refill trace and output-contract fixes with targeted regressions.
- PASS: independent Buffer transition replay and W256 closed-loop exploration.
  Closed-loop used seeds 6101–6105, 120 common-input scenarios and 720 runs;
  all CGOF(1:1) classifier modes matched on full action/cohort/queue behavior.
- BOUNDARY: 480/780 event observations were COMPLETE/INCOMPLETE respectively;
  `INCOMPLETE` is an observation state, not an execution failure. CGOF(2:1)
  differences are descriptive, and no latency-recovery threshold was defined.
- PASS: corrected H2 quota × ordering `SCHEDULER_RTL` exploration, fresh seeds
  6401–6405, N4/D16/W256, near/bursty, Heavy work 256. All 40 jobs, 20 pairs,
  20 lint configurations and 25 traffic tests passed; effective High held at
  the sole active close 255. Independent full input replay, source ZIP/JUnit
  checks and reconstructed pair prefixes passed. Final censored requests=0.
- PRESERVED_FAILURE: original seed 6301 / Heavy work 1024 execution passed,
  but classification changed to effective Low. Excluded from the corrected
  campaign; seeds 6302–6305 were not run.
- BOUNDARY: five-seed exploration only; full-run Sparse G→F includes drain.
  Q1 ordering endpoints match; Q2 Sparse and Heavy-gap directions do not
  establish a general winner. No ranking, CI, p-value or confirmation claim.
- PASS_EXECUTION: separate preregistered ordering confirmation, fresh seeds
  6501–6520, same N4/D16/W256 near/bursty protocol. All 160 RTL jobs, 80 pairs,
  80 lint configurations, 100 traffic cases and 180 JUnit files passed.
  Effective High and full Sparse-cohort equality held in 20/20 seed blocks;
  input replay/source checks passed. Generated=accepted=fired=42,620,
  final censoring=0, Sparse pending at cut=0, drain completions=0.
- NOT_CONFIRMED: no primary reversal, but only 7/20 joint strict improvements
  in Q2 ordering and quota × ordering interaction versus the frozen 15/20 gate.
  Both means are −0.35 cycle, medians zero, ranges −1 to zero. This is neither
  equivalence nor an oldest-first superiority result; no exploration pooling.
- PROVENANCE: Astra planning succeeded through Codex CLI,
  `codex/gpt-6-astra`, high; executor `auto/deepseek-v4.1-flash`.
  Effective backend identity is `UNKNOWN`. Sparse cohorts have 12–32 requests;
  nearest-rank P99 equals the sample maximum. Ready=1 drain is part of the
  latency protocol, although these jobs needed no drain.
- PASS_DESCRIPTIVE (`COMPLETE_DESCRIPTIVE_EXPLORATION`): W5M ordering
  production completed, five-seed plan
  (N4/D16/W5,000,000, sole close 4,999,999, bursty ready, full-run Sparse G→F).
  All 40 RTL jobs, 20 pairs, 20 lint configurations, 25 traffic cases and
  45 JUnit files passed; 2026-11-01T08:43:43Z–2026-11-02T15:27:08Z (30.7h)
  inside the 36h cap. Every job single-close, effective High, full Sparse
  cohort match, final censoring=0 and drain completions=0.
- RESULT_DESCRIPTIVE: S=11/11/12/11 and I=−1 in 5/5 seeds (d1=0, d2=−1).
  Mixed Heavy max-gap RR−OF: Q1 +2/+2/+1/+2/+1 (mean +1.6), Q2 0/0/0/0/−1
  (mean −0.2). A=Cmixed−Cisolated is equal across the four settings within
  each seed (seeds 6601–6605: 3/0/7/1/8); its RR−OF contrast is 0 in 10/10.
  RR trades a one-cycle Q2 Sparse P99 gain for a higher Q1 worst-case Heavy
  gap. Not a winner/equivalence claim and not a confirmation; W256 stays
  NOT_CONFIRMED and the denominators are not pooled.
- PROVENANCE: W5M plan written through Codex CLI (`codex/gpt-6-astra`, high);
  effective backend UNKNOWN. Requested executor `auto/deepseek-v4.1-flash`
  was not offered by the sub-agent roster; 6602–6605 relaunches used the
  frozen wrapper under the supervisor, and 6602's first launch aborted before
  any cocotb job. Both are recorded in the campaign manifest.
- NOT_RUN: latency recovery, new formal/CDC/PPA/EDA signoff, and
  CXL/application measurements. The manuscript and October 29 confirmation
  keep their separate accepted scope.

[Closed-loop evidence](../artifacts/implementation/buffer-closed-loop/20261101T015630Z/manifest.json),
[RTL correction evidence](../artifacts/implementation/cgof-rtl-ordering-exploration/correction-manifest-20261101T030414Z.json),
[ordering confirmation](../artifacts/implementation/cgof-rtl-ordering-confirmation/manifest-20261101T045246Z.json),
[W5M campaign](../artifacts/implementation/cgof-rtl-ordering-w5m-production/manifest-w5m-campaign-20261102T154205Z.json),
[follow-up report](reviews/evidence-review-followup-20261101.md).

## Accepted report update — 2026-10-29

The current [13-page report](../output/pdf/cxl-scheduler-revised-20261029.pdf) integrates the completed twenty-seed finite-Heavy RTL confirmation (80 jobs, 40 pairs) and current-source CGOF replay (30 runs, 60 A/B endpoints). It contains 9 figures and 7 tables, including two new vector figures. [Source](final-report/main-v3.tex), [acceptance/provenance](final-report/update-20261029/REVISION_QA.md), and [release record](final-report/update-20261029/revision-release.json) supersede the earlier report checkpoints below.

The confirmed near-load 1:1/2:1 settings give Sparse mean run-P99 3/4 cycles and mean run-maximum Heavy gaps 9.45/10.85; mixed completion exceeds isolated by 3.05/3.00 cycles on average. All jobs cross one boundary and remain effective High. H3 now has partial multi-seed, single-boundary support; the updated [theory](final-report/update-20261029/THEORY_AND_EVIDENCE.md) and [follow-up protocol](final-report/update-20261029/FOLLOWUP_EXPERIMENTS.md) separate supported conclusions from remaining mechanisms.

Sol/high writing, figures and independent evidence review, agy Gemini 3.8 Flash/high language review, and parent acceptance are complete. The new generator tests pass 5/5; both new figures and all 13 PDF pages were inspected. This report task launched no simulations or EDA. Broader finite-work classification adaptation, CGOF power, and CXL/application measurements remain unmeasured. Historical status statements below retain their original dates.

## Accepted report revision — 2026-10-28

The latest report is the accepted 11-page October 28 revision: [PDF](../output/pdf/cxl-scheduler-revised-20261028.pdf), [source](final-report/main-v3.tex), [QA and provenance](final-report/improvement-20261028/REVISION_QA.md). It incorporates the completed 180 equal-demand, 100 fixed-class and 300 finite-Heavy model jobs, separate single-seed production CGOF RTL, and six CGOF area/STA configurations. The older MODEL_ONLY checkpoint below describes October 27, not the current evidence inventory.

Sol/high authoring and figures, agy Gemini 3.8 Flash/high language review, and parent evidence/layout acceptance are complete. Final report/figure tests pass 10/10 and 5/5; two clean LaTeX passes and all 11 rendered pages were checked. This writing task ran no new scheduler or EDA experiments. H1–H5, CGOF power, broader multi-seed/multi-window RTL and full-system application measurements remain follow-up work. The [release record](final-report/improvement-20261028/revision-release.json) supplies current hashes while preserving the immutable planning snapshot.

## FAI-inspired/CGOF measurement diagnosis —2026-10-27

- PASS: frozen MODEL_ONLY runner and diagnosis model for quota x ordering,
  WRR/IWRR controls, paired finite-Heavy work, fairness, latency decomposition,
  service gaps, conservation and censoring.
- PASS: final W256 smoke27/27 jobs with source stability and manifest
  verification;18/18 comparisons remain NOT_RUN because smoke is non-inferential.
- PASS: model tests270/270; targeted diagnosis tests18/18; report/figure tests8/8.
- PASS: v3 report and six vector figures regenerated; final12-page PDF compiled
  twice with no overfull/undefined/LaTeX-warning and all pages visually checked.
- NOT_RUN: W5M production, exploration/confirmation cohorts, minimum RTL
  control group, system bandwidth/response latency, and application slowdown.
- BOUNDARY: CGOF is evaluated, not claimed novel; fire/cycle is not measured
  memory bandwidth and generation-to-fire is not memory-response latency.
- PRESERVED: accepted498-row matrix and old smoke checkpoint; public names are
  CGOF (1:1)/(2:1) and FAI-inspired, with no historical-name explanation.

[Evidence](experiments/diagnosis-20261027/README.md),
[literature](experiments/diagnosis-20261027/LITERATURE.md),
[plan](MEASUREMENT_DIAGNOSIS_PLAN.md),
[final report QA](final-report/CGOF_DIAGNOSIS_QA.md).

## Main-SQ conditional optimization —2026-10-23

- PASS: independent original15run/PPA audit, native Opus5.5medium passive recorder,
  W256pilot3RTL/32units/3strictlint, exact metrics and per-request trace reconstruction.
- PASS: W5Mseed509 FCFS/RR10/Main replayMSQ-main/20261023T083405Z_1850, outerexit0,
  exact old stable metrics and full real10M training each. Pilot plus production sixRTL/
  31,962,468 nonresetcycles;32 distinct native unit cases repeated across scopes.
- FAIL: proposed persistent SQ benefit gate. Actual Main burstP99=24; offline fixed-slot
  SQ1=24/SQ2=25, maxima34vs31 and source2 regressions. Shared class-quota delay observed.
- NOT_RUN: SQ RTL/reference model/regression/Formality/PPA and five-policy matrix, stopped
  at the owner's conditional gate. HQ/AGE remain separate unapproved future designs.
- Preserved: accepted Main/Spec/results,264earlier rawmetrics and existing Final files.

[Task evidence](experiments/main-sq/README.md) distinguishes actual RTL traces from offline
fixed-slot source-rotation design screens. No Final rewrite or FastX job this task.

## Heavy-host/sparse-host comparison —2026-10-22 (ACCEPTED15/15)

Full N4 productionW5M15 matrix completed/outerexit0; raw strict JUnit/exits/cohort/trace/source
auditPASS,5pairedtracegroups. Actual156,657,531nonresetcycles,150Mrealtraining, no statepreload.
Sparse P99 means Main10vsFCFS18.2/RR11 (single);20.8vsFCFS33.8/RR17.2 (burst). Main protects
sparse latency vsFCFS; bursttailworse thanRRin4/5seeds,1tie. Allmeasuredthroughput1/cycle,
heavy~97.7%; noapplication/universal claim. [Results](performance/HOG_SPARSE_RESULTS_2026-10-22.md).
348protected/188Finalfiles and264previousrawmetrics preserved; noactivejob. Startup history:

Code frozen; actual three-policy W256 pilot20261022T034155Z_369/exit0 PASS, independent audit
and13 corruption rejections PASS. Full W5M15run20261022T034507Z_311 launched UTC03:45:02,
six jobs/buildjobs2; still RUNNING, not an accepted result. Shell-exit capture repair and
earlier attempt retained. No Final/RTL/model/Spec/PPA changes. Initial checkpoint follows:

Execution authorized; actual native weekly429/exit1 triggers owner-approved Sol/high fallback.
Single new verification-tool writer, Codex independent review; pilot and15 formal runs NOT_RUN.
[Actual execution record](performance/HOG_SPARSE_RESULTS_2026-10-22.md). Original design checkpoint:

[Experiment design](performance/HOG_SPARSE_PLAN_2026-10-22.md) saved for owner-requested use
case: one continuously offered heavy source, three sparse sources, FCFS/RR10/Main, production
W5M natural training, five paired seeds/two profiles. W256 execution pilot precedes15 formal
runs. No new test implementation/run or benefit claim; Final unchanged. Previous264 raw
metrics and31 tracked performance files hash-verified/preserved with a separate manifest.

## Source-placement/cardinality sensitivity —2026-10-22 (accepted)

Owner's tests1/2 **COMPLETE:42/42 actual RTL simulations PASS**, all14 proper Low subsets
under FCFS/RR10/Main; N4, supported W256, natural two-window training512+240 measured cycles.
Run20261022T024651Z_297/exit0; independent raw audit63,498 nonreset cycles/14 matched traces.
Main service follows classes, not source0:1L/3H about50%/16.7%,2/2 about25%,3/1 reversed.
Finite boundary offsets retained; all policies239fires/240cycles, zero avoidable bubbles.
Pilot9/units98/strictlint3 PASS; unsupportedW4096 first failure retained. Native quota429
and authorized Sol/high fallback recorded. [Results](performance/PLACEMENT_RESULTS_2026-10-22.md).
No Final/RTL/refc/Spec/PPA change or active job; no long-term/application generalization.

## Controlled performance follow-up —2026-10-22 (accepted)

[Owner-approved follow-up](performance/FOLLOWUP_PLAN_2026-10-22.md) supplements the accepted
primary180 with trained N4 contention,36 fixed controls,3 finite batches and per-source/gap
instrumentation. Frozen pilot21 RTL/43 unit cases PASS; parent73 tests/16 subtests PASS.
Full controls36/36, finite3/3, trained3/3 **ACCEPTED PASS**, outer exits0 and independent raw
audit42runs/14tracegroups PASS. Actual35,376,594 nonreset RTL cycles; no active scope/writer.
Trained equal-demand Main serviceJain~0.75 (singleLow source50.001%) versusFCFS/RR~1;
same throughput0.99999, complete eligible-ready gap max4/31/13. Record all observations in
[accepted follow-up](performance/FOLLOWUP_RESULTS_2026-10-22.md), no claim of universal fairness.
Actual native Opus5.5/medium
weekly429/exit1 triggers authorized Sol/high fallback; one source writer, Codex independent review.
Final remains unedited/unbuilt; no RTL/model/Spec/PPA modification or external workload scope change.

## Descriptor performance instrumentation —2026-10-22 (latest owner scope)

Owner-approved descriptor-only/project-owned primary180 matrix replaces the v0.1 closed-loop
proposal below; gem5 deferred, Algorithm-2 supplementary. Final report is on hold, not edited
or rebuilt. [Scope v0.2](APPLICATION_EVALUATION_PLAN.md),
[inventory](performance/EVIDENCE_INVENTORY_2026-10-22.md),
[test record](performance/TEST_RECORD_2026-10-22.md).

Archive audit180 primary/44 long jobs PASS (0 new RTL cycles); three N4 infrastructure pilots
PASS (300k measured cycles);27 independent recorder/audit tests and10 subtests PASS.
Phase-instrumented primary180 replay **ACCEPTED:180/180 PASS**, raw JUnit/exits/fullscope verified.
18.3M new measured RTL cycles including pilots; all legacy fields except host wall time unchanged.
Durable CSV:1,080 phase-kind rows/10,080 per-source rows,20-seed run statistics/paired differences.
Frozen58 functional-source and188 pre-existing manuscript/literature file hashes verified unchanged
at final acceptance. No active batch, long production/stress/PPA rerun or new architecture decision.

## Application-performance plan —2026-10-22

[Plan v0.1](APPLICATION_EVALUATION_PLAN.md) prepared for three-policy throughput/latency/fairness
controls and a separate CPU/memory closed-loop IPC/slowdown/speedup comparison. Implementation
and all new runs remain NOT_RUN. Proposed progression: metric contracts → descriptor controls →
N4 closed-loop pilot →36paired shared runs plus alone references →conditional N8/16 expansion.
Application traces, execution scope and byte/link interpretation remain owner choices; frozen
Spec/RTL/PPA and existing uncommitted manuscript revisions are unchanged by this planning work.

## Academic final report prepared —2026-10-21

Report preparation is complete for owner review: [editable LaTeX](final-report/main.tex),
[rebuild/source guide](final-report/README.md), [QA](final-report/QA.md), and
[local rendered PDF](../output/pdf/cxl-scheduler-final-report.pdf). Eight pages, English
two-column academic layout following the supplied progress report, numbered figures/tables,
paper references, limitations and reproduction appendix. All final pages visually inspected;
native LaTeX compiler and standalone PDFLaTeX succeed. Data generator checks the frozen accepted
datasets and rejects modified evidence before writing; no scheduler/remote experiment rerun.

The paper's Algorithm2 page5 is now actually available/inspected for report preparation. Main
and the project-defined one-output reconstruction remain unchanged. All measured/unmeasured
boundaries and the actual qualified-power warnings remain explicit. Author/course submission
review is pending; no submission acceptance, additional PPA or new architecture decision claimed.

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

## Active power-method task —2026-10-21

**NINE_CASE_ACTIVITY_POWER_ACCEPTED_WITH_LIMITATIONS.** Actual FastX-NN VCS/PT W-2024.09/PrimePower, nine compile/sim/PT/wrapper exit0, 900000 checked cycles; clean power export c0658fb, unchanged accepted mapped source759f86b/profile6f4777f0. All553754nets activity-file annotated, all172007FFclockpins reviewed;70literal-constant leaf gaps individually verified. FCFS/RR retain2ramp+1load table-range warnings percase on unusedconstantcontext, Main3/3check_power succeeds; no clean-signoff claim. All171145TFIPC warnings are audited unusedoutput omissions. Final remoteimmutablehashcheck and allnine independent rawaudits/diagnoses PASS. [Power report](POWER_RESULTS_2026-10-21.md),[JSON](ppa/power-20261021.json),[method](POWER_METHOD.md),[development record](DEVELOPMENT_REPORT.md). Main all-H, single seed/coldreset100kcycles; no trained-state/physical/glitch/multicorner/formal/Algorithm2power claim. Native power-analyzer quota failure and owner-authorized Sol/high tooling provenance preserved. No RTL/model/Spec/profile change, no new architecture decision. Next: consolidate final project report using accepted functional, area/STA, Algorithm-2N4 and qualified power evidence; additional long/train-state power only if that claim is needed.

**The sections below retain earlier checkpoints; their pending/NOT_RUN statements describe those dates and are superseded by this latest power outcome.**

## Active Algorithm-2 supplement —2026-10-21

**SUPPLEMENTARY_N4_COMPLETE_FOR_FUNCTIONAL_AND_PRE_LAYOUT_AREA_STA.** Sourcec8e7ea8, FastX-NN, samev2profile. TwoactualMainN4/Alg2N4DC/PT/wrapperexit0; timing/hold/electricalMET. Area−0.028626%, sequentialcellsunchanged9011; minimumsetup+10.496409ns, hold+0.039940ns. Each68constant_disableduntestedchecks;58906driversoriginalcaplimitsdefined/positiveand0violations. Allownartifactsretrieved/hashchecked; Codexindependentrawreviewaccepted. [Report](PPA_FAI_SUPPLEMENT_2026-10-21.md),[JSON](ppa/algorithm2-n4-20261021.json). N4differenceimmaterialtoexistingprimarycostconclusions; N8/16supplementdeferredperownercondition. Power/formal/physical/multicornerNOT_RUN.

Long verification/preparer task **ACCEPTED_FOR_N4_FUNCTIONAL_SCOPE**: actual20million productioncycles/4windows and10stressruns/6millioncyclesPASS, all16transitions each; Main/M6units856/447PASS. Sol/high worker completed tests then its turn hit429; parent verifiedrawJUnit/metrics/hashes and completed reporting. Parent329smalltestsPASS; PPAinfra Windows40PASS/8platformskips, WSL34PASS/14platformskips complement each other. Explicit supplementaryN4opt-in payload ready; actual supplementaryPPA stillNOT_RUN. NoRTL/model/Spec/Tcl/profile changes. [Long results](phase-5-verification/M6-long-results.md).

**DIRECTED_AND_BEHAVIOR_SCOPE_ACCEPTED.** Native rtl-coder session77281b50-edbf-4a55-9539-a77ad9d0736d, Opus5.5/medium exit0. M6 final441tests plus45lint/12probes/4XREJECT; M1/M2/M3/M4/M4-q1/M5 units331/571/595/475/195/850 PASS (repeated241reference/39helper tests are not unique RTL coverage). Main/Algorithm-2 comparison20runs,10paired identical intended traces,1,920,000 total cycles; actual acceptance differences retained. Codex raw/JUnit/digest/matrix/hash review passes. Production-parameter20k smoke is explicitly not a complete W5M-window test. Long Algorithm-2 stress/production and supplementary PPA remain NOT_RUN. Original failed M6/launches preserved. See[review](../reviews/phase-4-rtl/codex-fai-alg2-review.md) and[development record](DEVELOPMENT_REPORT.md). VPN/pinned FastX-NN preflight verified; primary-nine dataset unchanged.

## Completed common-v2 PPA milestone —2026-10-21

**Nine-case pre-layout comparative area/STA dataset ACCEPTED.** One clean source759f86b, one frozen cap075-v2 canonical6f4777f0…, no RTL/Spec/flow-code edit. Actual setup/hold/electrical9/9MET, minsetupMain16+1.158148ns.140constant_disabled untested checks explicitly retained,5cases alltested.542065drivers audited under original limits,0ordinary/CCS violations;390temporary limits restored per case. Codex raw/result/source/SDC/storage checks plus native synthesis-reviewer Opus5.5/medium492checks PASS, CLIexit0. [Results](PPA_RESULTS_2026-10-21.md),[JSON](ppa/primary-20261021-v2.json),[review](../reviews/phase-5-verify/primary-v2-results-review.md). v1history preserved; physical/multicorner/power unrun. Next: separate Algorithm-2 N4 implementation/verification/behavior comparison. [Development report](DEVELOPMENT_REPORT.md) records failures, numeric precision, API recovery and post-retrieval SSH timeout; no experiment loss.

## Earlier checkpoints (historical)

## Common v2 measurement —2026-10-21

Method review PASS_COMMON_METHOD, actual native RTL Agent Team synthesis-reviewer / Opus5.5/medium exit0,97/97binding checks. New cap075-v2 profile is numerically identical to the successful pilot settings and will apply uniformly to nine cases; canonical6f4777f0…. Freeze/clean export precedes execution. New nine-case results NOT_RUN at freeze; original v1 dataset and all pilot results preserved. No RTL/Spec/flow code change, no new scheduler test claim. See[method review](../reviews/phase-5-verify/common-profile-v2-review.md) and[development record](DEVELOPMENT_REPORT.md).

## Current continuation —2026-10-21

Shared comparator `d82f1b54ca54af2344ad07d914680547003f526f`: **FULL_FUNCTIONAL_REGRESSION_ACCEPTED; MAIN16_SINGLE_PILOT_MET.** Native Opus5.5/medium implementation and Codex independent audit complete. M1/M2/M3/M4/M4-q1/M5 pass286/526/550/430/195/805; primary180/180, Main stress30/30 and production3/3 with60million measured cycles/12windows. Interrupted partial primary preserved, full rerun passes. Actual RTL comparison/native and independent each21configs/81,108,288vectors; no formal-tool signoff.

Main16 same-cap075 pilot/sourceb257ee8: DC/PT/wrapper exit0, setup+1.158148ns, hold+0.084335ns, area437622.506788, FF35773;0timing/electrical violations and0untested.390temporary limits restored;116993used output-driver pins audited; original library unchanged. Compared with old same-profile pilot: setup improves2.066094ns for+0.09004%total area. No new nine-case dataset or power result; profile remains PILOT. [Pilot report](PPA_COMPARATOR_PILOT_2026-10-21.md) and [DEVELOPMENT_REPORT.md](DEVELOPMENT_REPORT.md) retain exact runs, failures, versions and report limitations. Next: common revised-method nine-case measurement/review, then separate supplementary work.

## Preserved primary FastX results —2026-10-20

See the closure follow-up below for the latest two cap075 pilots. They clear measured cap/slew while Main16 setup still fails; the original primary-nine matrix here remains unchanged.

**PRIMARY_NINE_COMMANDS_COMPLETED; SETUP_MET_8_OF_9; ELECTRICAL_CLOSURE_OPEN.** All nine DC/PT W-2024.09 batches actually ran on FastX from clean flow/export commit `081f8a219911909bda8472ae4b257d3e6ed3122d`, with the same frozen25ns/SAED32 RVT TT/FO4/ForQA-top/compile-medium/single-core profile. Each batch exited0, with exact completion markers, mandatory reports and independently verified source/result hashes. This establishes completed measurements, not signoff acceptance.

FAI Main N16 has **32 setup violations**, worst PT setup **−0.870709ns**; all nine hold checks meet their constraints. FCFS N16's +0.000811ns setup margin is only about0.81ps and is not robust timing closure. Every case has OPEN PT max-capacitance findings; FCFS N4, Main N4 and Main N16 also have slew violations. DC/PT capacitance-report disagreement remains unresolved. The main N16 failure is preserved; the earlier20ns pilot is a separate mapping run and does not replace the failed25ns result. No constraints or library limits were waived.

Owner-authorized SSH, pinned host key, module, DC/PT license use and existing SAED32 library read/hash are VERIFIED by actual commands. No proprietary asset was downloaded. RTL/models/TB/frozen Spec are unchanged. Existing functional acceptance remains180/180 primary plus the recorded Main unit/stress/production runs; the36 Windows/WSL runner infrastructure tests are separate evidence.

Native RTL Agent Team Opus5.5/high actually authored the runner and repairs before the owner changed future calls to medium. The subsequent native synthesis-reviewer hit HTTP429/session limit, exited1 and did not write a review; the explicitly authorized **GPT6.1 Sol/high** fallback completed the independent nine-case methodology review. Preserve the original failed invocation and fallback provenance. Power, commercial equivalence, physical implementation and multicorner signoff remain NOT_RUN; Algorithm-2 is NOT_STARTED.

See [nine-case results and self-inspection links](PPA_RESULTS_2026-10-20.md), [machine-readable results](ppa/primary-20261020-v1.json), [execution and repair history](PPA_EXECUTION_2026-10-20.md), [methodology review](../reviews/phase-5-verify/FastX-PPA-methodology-review.md) and [frozen profile](../syn/profiles/saed32-rvt-tt-25ns-forqa-v1.json). Earlier dated handoff/pilot/quota statements below are historical and superseded where these results record actual execution.

Next milestone: investigate the DC/PT electrical-rule discrepancy and Main N16 critical path under the shared framework, then review a common closure plan. Do not silently change RTL, add policy-specific stages or timing exceptions, relax library rules, or call these measurements accepted PPA. Any common flow revision requires new provenance and a fresh comparable nine-case sweep; supplementary Algorithm-2 remains separate.

## Closure diagnostic follow-up —2026-10-20

**TWO_CAP075_PILOTS_ELECTRICAL_MET; MAIN16_SETUP_NOT_MET.** Main N16 same-profile DC/PT/wrapper actually exited0 ataa89771: area437228.837383 (+0.2244%),FF35773, setup−0.907946ns (32violated checks),hold+0.085328ns;0cap/0slew.390temporary limits restored; all116345 used output pins have original positive caps and0CCS cap violations. No new nine-case replacement/adoption; original baseline measurements remain unchanged. Next: shared comparator RTL equivalence/verification candidate rather than more cap-only retries. RTL/models/TB/Spec remain unchanged in this stage; power NOT_RUN.

**CAP075_FCFS4_PILOT_MET; PRIMARY_NINE_BASELINE_UNCHANGED.** Original FCFS4 full-driver calibration26731pins reconciles all1118 PT cap violations. Optional synthesis-only cap scale0.75 is implemented with native float32/six-decimal readback and mandatory restoration;44 unique infrastructure tests executed across Windows/WSL. Fresh actual DC/PT/wrapper exit0 at046721b: area103730.908806 (+0.70%),FF8856, setup+9.881229/hold+0.033790ns,0cap/0slew violations under original library limits.390temporary limits restored and SDC unchanged in constraint semantics. All27231 remapped output pins have original defined cap limits and0CCS cap violations.64constant-disabled timing checks remain untested. Failed initial exact-double readback attempt retained. No RTL/Spec/model/TB change, no scheduler functional regression rerun, no new all-nine/profile adoption claim. Next: Main N16 same-method pilot and review.

Same-net DC/PT re-read probes and an isolated FCFS N4 high-effort DC/PT pilot actually completed. Three sampled pins show DC ordinary capacitance below the library limit while DC CCS totals match PT violating loads; available setting sensitivities did not remove DC0/PT1118 findings. High-effort FCFS4 emits the same mapped module bodies and unchanged area/slack/cap/slew results as medium, so it is not adopted. Main16 path analysis attributes20.249199ns to the shared balanced FCFS selector, including120 ripple-carry cells across four32-bit subtractors. No RTL/frozen profile/Spec change or Main16 high-effort run.

See [diagnosis, actual pilot and common closure gates](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md). Next engineering step is full-net receiver-load comparison and a supported, conservative synthesis optimization target while retaining original PT/library acceptance limits. The sampled discrepancy is explained; all-nine electrical closure and Main16 setup remain OPEN. Power/Algorithm-2 are unchanged.

## Functional acceptance and historical handoff —2026-10-17

Owner handoff2026-10-17: 本階段功能驗收收尾，FastX由 owner依[手動手冊](FASTX_HANDOFF.md)執行；[中文小結](STAGE_SUMMARY_2026-10-17.md)集中列出完成與未完成項目。操作範本／來源匯出不等於商用工具執行或九組 PPA完成。

Updated2026-10-17 (Asia/Taipei). **M5_MAIN_FUNCTIONAL_ACCEPTED**. Approved Spec v1.0 remains frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Verified source: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`. This accepts Main functional integration and the common/FCFS/RR regression, not the whole project or PPA.

Native final-review outcome: both reports, all raw audits, post-review hashes and the manifest were saved before the final-summary API call returned HTTP429/session limit. The CLI then exited1 naturally after its built-in retries; this is not a successful CLI exit. It reported reset2026-10-17 13:50 Asia/Taipei (an estimate, not verified availability). All148 actual inference response records are claude-opus-5-5; the additional synthetic record is the API error, not another model. Native written verdict PASS_M5_MAIN_FUNCTIONAL and Codex acceptance rest on inspectable completed evidence, not process success. No further API retry, settings change or automation was started. Future native Claude work waits for account availability; current documentation/independent acceptance can finish locally.

## Continuity and completed scope

Existing sole repository: `C:\Users\USER\Documents\Coding Space\CXL\cxl-scheduler`, main. Scaffold e001b77, WSL d1c9d02, RC1 a518e1e, frozen v1.0, accepted M4/common23f8032, Main RTL/model91bf36f, TB/runnerdb96961 and boundary-accounting fixcefbbb0 remain in Git. Q1-Q3/Option A are approved; no new architecture decision was opened.

| Item | State | Current evidence |
| --- | --- | --- |
| Spec / existing setup | PRESERVED_READY | Approved v1.0; WSL pinned toolchain. |
| M1 common FIFO | COMPLETE | Current full286PASS,90 cocotb. |
| M2 common output/hold | COMPLETE | Current full526PASS,330 cocotb. |
| M3 FCFS/model; C1 | COMPLETE / CLOSED | Current full550PASS;60 accepted primary runs. |
| M4 RR10/model | COMPLETE | Current full430PASS;60 accepted primary runs. |
| RR1 supplement | VERIFIED | Current195PASS. |
| Main M5 | FUNCTIONAL_ACCEPTED | Native and Codex805PASS each; stress30/primary60/production3PASS; native and independent review. |
| Shared architecture | ACCEPTED_FUNCTIONAL | Same FIFO/hold/timing; RR timestamp exclusion and FCFS/Main positive controls. |
| Primary functional matrix | COMPLETE_180_OF_180 | FCFS60 + RR60 + Main60; repeated runs are not new configurations. |
| Algorithm-2 supplement | NOT_STARTED | Separate, after the primary nine synthesis configurations. |
| FastX access | VERIFIED_2026_10_20 | Actual pinned SSH, module/library hash and DC/PT command execution; supersedes initial handoff. |

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

M5 unit805 =196 reference pytest +39 TB-helper pytest +570 cocotb (19 cases x N4/8/16 x W64/256 x seeds509..513). Each full M5 unit run also passed27 strict lint configurations and9 structural probes;3 Algorithm-2 expected rejections are separate negative checks. Repeated reference/helper collections across scopes are not unique additional RTL coverage. Final scopes have zero failures/errors/skips/NOT_RUN and no simulator warning relaxations.

Full stress30 covers N4/8/16 x W64/256 x seeds509..513,400,000/800,000 measured trace cycles:18million total, with all16 Main state/evidence transitions in every run. These trace cycles include recorded resets. Primary60 covers N4/8/16 x seeds509..528 x100,000 measured cycles:6million total, all60 intended trace hashes match the tracked FCFS record. Every primary cycle matches the FCFS mirror and the accepted FCFS common metrics. No primary window closes at W5,000,000; this is pre-classification evidence, not a fairness/adaptation conclusion.

Production3 runs each simulate20,000,000 actual non-reset measured cycles at W5,000,000:60million total and12 complete windows. No time skip, state deposit/preload or smaller-window substitute. All three N configurations verify closing-edge fire inclusion, S=sum(B), exact integer thresholds, Main class changes, held grants across boundaries and final drain/response conservation. B/S/index are23-bit and threshold operations unsigned32-bit. Per-cycle oracle, independent pin/history, full105-bit/source/order/hold checks remain active.

## Nine primary synthesis configurations — actual2026-10-20 results

All entries have DC/PT command exit0. Timing labels below refer only to setup/hold; **electrical closure is OPEN for every entry, power NOT_RUN**.

| Policy | N4 | N8 | N16 |
| --- | --- | --- | --- |
| FCFS | MEASURED / TIMING_MET | MEASURED / TIMING_MET | MEASURED / TIMING_MET, setup only+0.000811ns |
| RR quantum10 | MEASURED / TIMING_MET | MEASURED / TIMING_MET | MEASURED / TIMING_MET |
| Main FAI W5,000,000;10/10 | MEASURED / TIMING_MET | MEASURED / TIMING_MET | MEASURED / SETUP_NOT_MET, −0.870709ns /32 checks |

Algorithm-2 is NOT_STARTED, remains a separate approved interpretation, and follows the primary nine synthesis experiments. No IEEE PDF inspection or cycle-identical paper reproduction is claimed; Main four-state hysteresis and the shared one-output10/10 alternation follow the approved project specification. Multi-output/APR/optional extensions remain deferred.

Historical2026-10-17 handoff checkpoint (superseded by actual2026-10-20 results above): all nine FastX synthesis/STA/power/PPA configurations were NOT_RUN. SSH/tool/license access was NOT_VERIFIED; the registered-adder smoke is user-reported environment evidence only. Existing remote templates need reviewed N/policy parameter selection and a frozen pilot-derived common methodology before the sweep. Formal/CDC/SystemC/UVM, numerical coverage and RTL mutation campaigns are NOT_RUN/deferred, not PASS; prior14 model mutants do not establish RTL coverage. Strict Verilator checks passed; the earlier default Verible style conflicts remain separately recorded.

Historical2026-10-17 next step (completed by the2026-10-20 execution above): the owner runs the manual FastX preflight/pilot, freezes one common PPA profile and then runs the nine DC/PT configurations. Use the exported source snapshot and FASTX_HANDOFF.md; the manual parameter-selection instructions are not yet validated on the host. Required there: working FastX login/tool licenses, a writable project directory, the existing absolute SAED32 RVT `.db` path/permission and pilot-derived constraints. SSH hostname/authentication/host key are needed only if the optional remote automation route is chosen; sharing SSH access with Codex is not required for this manual handoff. Do not copy proprietary assets. DC/PT W-2024.09, module `Synopsys_x86-64/2024`, SAED32 RVT `saed32rvt_tt0p78v25c.db` remain the user-reported target environment.

Parameter plumbing, source lists and constraint proposals are engineering work; final shared clock/uncertainty/I/O/load/transition/effort/wire-load/reporting and power assumptions must be recorded from the real pilot. No new correctness-critical architecture choice or fresh Spec approval is currently needed. Do not start the supplementary Algorithm-2 implementation or claim mapped policy overhead before actual synthesis.

Detailed actual execution, repaired failures, provenance and run IDs: [STATUS](STATUS.md), [M5 results](phase-5-verification/M5-results.md), [history](IMPLEMENTATION_RESULTS.md). Current successful work supersedes prior quota/interruption checkpoints; those are retained as history.
