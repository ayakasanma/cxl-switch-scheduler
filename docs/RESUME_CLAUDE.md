# Continue after accepted Main functional integration

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

## Current power continuation —2026-10-21

**NINE_CASE_ACTIVITY_POWER_ACCEPTED_WITH_LIMITATIONS.** Actual FastX-NN VCS/PT W-2024.09/PrimePower, nine compile/sim/PT/wrapper exit0, 900000 checked cycles; clean power export c0658fb, unchanged accepted mapped source759f86b/profile6f4777f0. All553754nets activity-file annotated, all172007FFclockpins reviewed;70literal-constant leaf gaps individually verified. FCFS/RR retain2ramp+1load table-range warnings percase on unusedconstantcontext, Main3/3check_power succeeds; no clean-signoff claim. All171145TFIPC warnings are audited unusedoutput omissions. Final remoteimmutablehashcheck and allnine independent rawaudits/diagnoses PASS. [Power report](POWER_RESULTS_2026-10-21.md),[JSON](ppa/power-20261021.json),[method](POWER_METHOD.md),[development record](DEVELOPMENT_REPORT.md). Main all-H, single seed/coldreset100kcycles; no trained-state/physical/glitch/multicorner/formal/Algorithm2power claim. Native power-analyzer quota failure and owner-authorized Sol/high tooling provenance preserved. No RTL/model/Spec/profile change, no new architecture decision. Next: consolidate final project report using accepted functional, area/STA, Algorithm-2N4 and qualified power evidence; additional long/train-state power only if that claim is needed.

**The sections below retain earlier checkpoints; their pending/NOT_RUN statements describe those dates and are superseded by this latest power outcome.**

## Active Algorithm-2 task —2026-10-21

**LATEST COMPLETED MILESTONE:** Algorithm-2 N4 functional+pre-layoutarea/STA supplementaccepted. Cleanmeasurement sourcec8e7ea8; actualFastX-NN Main/Alg2twoDC/PT/wrapperexit0 underunchangedv2profile. Areas110089.845892/110058.332037 (−0.028626%), seq9011both, setup+10.496409/+10.547482ns, hold+0.039940both. Each68constant_disableduntestedchecks;58906useddrivers0ordinary/CCScapviolations; originalDBhashunchanged/finalremotecheckexit0. Read[supplementreport](PPA_FAI_SUPPLEMENT_2026-10-21.md),[JSON](ppa/algorithm2-n4-20261021.json),[longresults](phase-5-verification/M6-long-results.md) and DEVELOPMENT_REPORT. Alltasks/writersended; do notrerunacceptedmeasurementsabsentnewconcern. N4differencedoesnotmateriallychangeprimaryPPAconclusions, soN8/16supplementdeferredperownerinstruction. Noownerarchitecturedecisionpending. Power/activityannotation,physical/multicorner/formalremainunrun. Anyfuturepowerworkneedsactualactivity/capability/coverage, noautomaticresultclaim. Primarynine/Mainbaselineunchanged.

**Latest outcome supersedes pending text below:** LONG_FUNCTIONAL_ACCEPTED. Sol/high completed actual M6-production `20261021T011237Z_23785`20million measuredcycles/4windows and M6-stress `20261021T011237Z_23789`10/10/6millioncycles with all16transitions each; source hashes stable. Main/M6units856/447PASS; parent329smallchecks and independentJUnit/closing/state/digest/hash auditPASS. Worker then hitAPI429 before final report; parent finished[long report](phase-5-verification/M6-long-results.md). No active code writer remains. RTL/model/Spec/Tcl/profile unchanged since1cec68d. New explicit supplementaryN4preparer+tests ready. Next: cleancommit/export, actual same-source MainN4/Algorithm-2N4 FastX runs with frozenv2profile; parent owns remoteEDA. Do not rerun longtests absentchanges/failures.

Directed/behavior milestone committed `1cec68d8cca6dcb132f000fa72e5de45f3468383`. Later native `func-verifier` session `9a30d2e0-4d95-4f42-bb1a-67362c1441ab` hit a Claude safety-classifier response stop before source writes or longrun. Exit0/empty success result is not task success; logs `.setup-logs/implementation/alg2-production-20261021/native/`, no quota fallback. A **new active invocation** uses official focused skill `/rtl-agent-team:rtl-p5s-func-verify M6-long`, logs `.setup-logs/implementation/alg2-long-workflow-20261021/native/`. Check its process/exit before another writer. Assignment: test-only shared production/stress interpretation support, full N4 W5M four-window run and ten long stress cases. Opus5.5/medium, no RTL/model/Spec/method changes; parent owns report/status and independent acceptance. Supplementary preparer opt-in and actual PPA remain pending outside this focused verification task.

**Superseding live state:** workflow session33d5c612 exhausted10retries and explicitly reported Claude session limit/reset12pmTaipei; no tools or source writes. Parent stopped only its own final-error CLI. Owner-authorized fallback **GPT6.1 Sol/high**, worker `/root/sol_alg2_long`, now owns remaining verification + supplementarypreparer + strictcomparisonrecordvalidation. Its logs `.setup-logs/implementation/alg2-long-sol-20261021/`; check worker/PIDs before new writes. No native CLI writer remains. Parent owns report/status/independent review/remoteEDA. Longruns and supplementary PPA still pending until actual evidence.

Owner restored VPN; pinned SSH, FastX-NN, unchanged library844d4474… and DC/PTW-2024.09 were actually checked (version-only DC exit1 preserved, separate PT probe exit0). Native rtl-coder session `77281b50-edbf-4a55-9539-a77ad9d0736d`, Opus5.5/medium, completed exit0; full logs/diff in `.setup-logs/implementation/alg2-20261021/native/`. Parent owns DEVELOPMENT_REPORT/STATUS/TRACKER/RESUME; native owns assigned code/tests/focused reports. Spec unchanged. No supplementary synthesis yet.

Current milestone **DIRECTED_AND_BEHAVIOR_SCOPE_ACCEPTED**: final M6 `20261021T004406Z_12107`,441tests/45lint/12probes/4XREJECT; six shared unit scopes331/571/595/475/195/850PASS. M6-compare `20261021T004131Z_10929`,20runs/10pairs/1,920,000totalcyclesPASS; identical intended hashes with actual acceptance differences retained. Codex raw/JUnit/digest/matrix/hash audit and [review](../reviews/phase-4-rtl/codex-fai-alg2-review.md) pass; old/new Main abstract model9configs/270kcycles equal. No new Main long regressions claimed. Production20k smoke is not W5M-window evidence. Next: full N4 Algorithm-2 production-window and longer stress verification, then same-v2-profile supplementary synthesis with explicit opt-in (preparer currently primary-only). Preserve primary-nine history/results. Original failed tests/launches and quick-lint false labels retained; no warning relaxation or fallback. See latest DEVELOPMENT_REPORT for exact evidence/failures.

## Latest completed common-v2 milestone —2026-10-21

**ACCEPTED_FOR_PRE_LAYOUT_COMPARATIVE_AREA_STA**: actual9/9DC/PT/wrapperexit0 from clean759f86b, samecap075-v2 canonical6f4777f0…, setup/hold/electrical9/9MET.140untested checks allconstant_disabled (4cases);5cases alltested.542065used driver pins audited, original positive caps,0ordinary/CCS violations,390limits restored percase. Native synthesis-reviewer sessionb73c8c4f-2906-4b42-956e-098749f8d110 /Opus5.5 mediumcompletedexit0,492checks pass;one transientserver_error recovered, nofallback. Codex independent raw audits agree. Read[PPA results](PPA_RESULTS_2026-10-21.md),[JSON](ppa/primary-20261021-v2.json),[native review](../reviews/phase-5-verify/primary-v2-results-review.md),[detailed development record](DEVELOPMENT_REPORT.md). No RTL/Spec/flow-code change; do not rerun accepted tests/sweep absent a new concern.

Next task: approved supplementary Algorithm-2 N4 implementation with shared framework and separate model/verification/behavior comparisons, then same-method synthesis; do not replace Main in the primarynine. No pipeline/FIFO/hold/semantics change. Power needs real activity annotation/capability/coverage; allphysical/multicorner/commercialequivalence remainNOT_RUN. Future nativeOpus5.5medium; owner-approvedquota fallbackSol/high unchanged. Native CLI/plugin verified2.1.304/0.14.6. Preserve single-writer ownership, actual logs/hashes/model records, and DEVELOPMENT_REPORT updates.

FastX all experiment/survey/allowlisted retrieval commands finished before final readonly cleanup query hitmastertimeout/brokenpipe. Failed query/reconnect logs preserved; no localSSHprocess remains. Future remote work needs authentication, same approvedpinnedkey; do not guess saved master availability, disable checking or persist credentials. Existing remote759f86b case directories and raw local evidence remain intact.

## Earlier checkpoints (historical; completed outcome above supersedes RUNNING/NOT_RUN entries)

## Active common-v2 measurement task —2026-10-21

Native RTL Agent Team synthesis-reviewer / Opus5.5/medium sessionb73c8c4f-2906-4b42-956e-098749f8d110 completed exit0 with PASS_COMMON_METHOD and97/97binding checks. New `syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json` is frozen with canonical6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d; all numerical settings equal the successful pilot. Commit first, prepare all nine from one clean source, then run/retrieve/audit using existing flow and source/result guards. Evidence under `.setup-logs/FastX-NN/` and native-review under `.setup-logs/implementation/rebaseline-20261021/`. Actual measurement status is recorded in DEVELOPMENT_REPORT; NOT_RUN at freeze, never infer it from methodology approval. Keep prior completed functional tests and v1/pilot data. No RTL/Spec/architecture change is part of this task.

## Latest completed checkpoint —2026-10-21

**FULL_COMPARATOR_FUNCTIONAL_REGRESSION_ACCEPTED; MAIN16_SINGLE_PILOT_MET.** Read [detailed report source](DEVELOPMENT_REPORT.md) and [pilot/test report](PPA_COMPARATOR_PILOT_2026-10-21.md). RTL commitd82f1b5, clean synthesis sourceb257ee8, Spec1af80967 unchanged. Native RTL Agent Team rtl-coder / Opus5.5/medium completed exit0, actual model records checked. M1/M2/M3/M4/M4-q1/M5 pass286/526/550/430/195/805; primary180/180; stress30/30; production3/3,60million measured cycles/12windows. Raw JUnit, full_scope, source hashes and unchanged functional metrics independently audited. No reason to repeat completed regression without a new change/failure. First batch SIGHUP during Main primary is preserved as incomplete; resume1 all six stages ended exit0 at2026-10-21 03:10:36 Asia/Taipei.

Actual FastX Main16 same-cap075 pilot: setup+1.158148ns, hold+0.084335ns, area437622.506788, FF35773,0timing/electrical violations,0untested;390limits restored and116993used driver pins audited, original library hash unchanged. This is one pilot; cap075 profile remains PILOT and old nine-case data are not replaced. Next task: freeze a common revised profile and run/review all nine with the same verified RTL/method. Do not change Spec, pipelines, FIFO/hold, service timing or constraints to favor a policy. Power/Algorithm-2/commercial equivalence/APR/multicorner remain unrun. Preserve owner-requested DEVELOPMENT_REPORT and provenance for every later experiment. Keep future Opus5.5 effortmedium; quota fallbackSol/high remains authorized.

## Earlier checkpoints (historical; superseded by completed results above)

Current owner continuation2026-10-21: shared timestamp comparator candidate committed atd82f1b54ca54af2344ad07d914680547003f526f. Native RTL Agent Team rtl-coder / Opus5.5/medium session322c1671-e1c8-4f12-a942-50d733089ea1 completed exit0. Focused checks accepted: actual RTL comparison21configurations/81,108,288vectors (native and independent), M3 550PASS and M5 805PASS; no SMT/formal signoff or timing claim. Codex fixed the test baseline to pre-changeb54aa64 and tested identical-source rejection. Broad fail-fast regression is RUNNING at `.setup-logs/implementation/comparator-20261021/regression/`; inspect batch-status/current-stage/stages.tsv and actual processes before restarting anything. No new FastX candidate run until required regressions pass. Maintain [DEVELOPMENT_REPORT.md](DEVELOPMENT_REPORT.md) as the owner's requested detailed record and final-report source. Older statements that no RTL has changed are historical. No new architecture/Spec decision is needed for this equivalent comparator.

Latest continuation checkpoint: M3-primary60PASS (`20261020T165716Z_534`), M4-primary60PASS (`20261020T170247Z_5075`), Main stress30PASS /18million trace cycles (`20261020T170825Z_8460`) independently audited. Original batch received SIGHUP exit129 during Main primary when the turn was interrupted, followed by WSL restart; no RTL failure was observed. That partial Main primary run `20261020T172119Z_10354` is NOT_ACCEPTED_INCOMPLETE despite its stale RUNNING summary. The active six-stage continuation is now `.setup-logs/implementation/comparator-20261021/regression-resume1/`, starting a full Main primary run `20261020T172737Z_382`, then production and M1/M2/M4/M4-q1. Do not restart the completed scopes or an active process. Original logs are preserved. FastX readonly preflight succeeded on backendFastX-NN with unchanged library hash; SSH master ended with interruption. Candidate synthesis remains NOT_RUN; the local prepared payload uses clean sourceb257ee8 and the same cap075 profile.

Current owner update2026-10-20: FastX access and actual scheduler pilots are verified; all primary nine DC/PT measurements completed from committed flow081f8a2 under the frozen25ns profile. Setup8/9 MET, hold9/9 MET; Main N16 has32 setup violations and worst−0.870709ns. All cases have OPEN electrical findings; power is NOT_RUN. The native synthesis-reviewer hit HTTP429 and exited1 without a report; the authorized Sol/high fallback completed independent review. See [final measured results](PPA_RESULTS_2026-10-20.md). See [current execution record](PPA_EXECUTION_2026-10-20.md); older manual-only/stop/quota-reset statements below are history. Future Opus5.5 invocations use **medium** effort. If Claude allowance runs out, the owner explicitly authorizes **GPT6.1 Sol/high** to continue without waiting for a reset; preserve evidence/file ownership and record the fallback. Existing high-effort invocations need not be restarted. No RTL/model/Spec rewrite is part of this synthesis task.

**Historical owner handoff2026-10-17 (superseded for actual synthesis by2026-10-20 authorization):** stop further implementation at this accepted stage. The owner will execute [FastX手動操作](FASTX_HANDOFF.md) and return pilot/results. Read [階段小結](STAGE_SUMMARY_2026-10-17.md) first. No fresh Claude call, RTL rewrite, Algorithm-2 task or PPA claim is needed to deliver this handoff. Resume engineering review from the owner's actual logs, not assumed remote success.

Updated2026-10-17 (Asia/Taipei). **M5_MAIN_FUNCTIONAL_ACCEPTED**. Approved Spec v1.0 remains frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Verified source: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`. This accepts Main functional integration and the common/FCFS/RR regression, not the whole project or PPA.

Native final-review outcome: both reports, all raw audits, post-review hashes and the manifest were saved before the final-summary API call returned HTTP429/session limit. The CLI then exited1 naturally after its built-in retries; this is not a successful CLI exit. It reported reset2026-10-17 13:50 Asia/Taipei (an estimate, not verified availability). All148 actual inference response records are claude-opus-5-5; the additional synthetic record is the API error, not another model. Native written verdict PASS_M5_MAIN_FUNCTIONAL and Codex acceptance rest on inspectable completed evidence, not process success. No further API retry, settings change or automation was started. Future native Claude work waits for account availability; current documentation/independent acceptance can finish locally.

## Do not repeat completed work

M1-M5 functional milestones are accepted, primary functional matrix180/180, and the full current common/FCFS/RR regression passed. Do not recreate the repository/toolchain, regenerate accepted RTL/models/tests, rerun long scopes without a new change/failure/concern, or reopen approved Q1-Q3/Option A. The new final-summary quota result is recorded above; do not reuse earlier reset times.

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

## Next task and remaining constraints

Newest actual Main16 pilot: same cap075 profile, clean sourceaa89771, DC/PT/wrapper exit0, cap/slew0/0 and all390 limits restored; setup **−0.907946ns with32 violations**, hold+0.085328ns, area437228.837383 (+0.2244%). All116345 used remapped output pins have positive original caps and0CCS cap violations; no SDC overlay leak. This completes the two-pilot electrical experiment but does not meet Main16 timing. Candidate remains PILOT; do not launch a replacement nine-case sweep or retry only cap factors as a timing fix. Next delegated work is a behavior-preserving shared `cxl_fcfs_sel` timestamp-comparison candidate, with bitvector equivalence, wrap/tie/eligible-mask tests, strict lint and required regressions before synthesis. No RTL has changed yet. See final Main16 section of [diagnosis](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md); older next-pilot instructions below are historical.

Latest actual outcome: the [cap075 FCFS4 pilot](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md) completes DC/PT/wrapper exit0 at046721b with original-limit PT cap/slew0/0, setup+9.881229ns, hold+0.033790ns, area103730.908806 (+0.70%).390 temporary library limits restored; all27231 used remapped output pins have defined original limits and0CCS cap violations. Native-calibrated float32/six-decimal exact readback repair is tested (44unique Windows/WSL infrastructure cases); preserve the original failed pilot and all historical baselines. Candidate profile `syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-pilot-v1.json` remains PILOT, canonical51a518e98d01ffd5788ee73ab4e39951e680411f494294c59da52bd4cb98fe6f. Next run the identical method on Main N16 before deciding on a common new nine-case measurement. No Main16 repair or all-nine electrical acceptance follows from FCFS4. No RTL/model/TB/Spec has changed.

The2026-10-20 [closure diagnosis](PPA_CLOSURE_DIAGNOSIS_2026-10-20.md) now includes real same-net DC/PT receiver-load checks and a completed isolated FCFS N4 high-effort pilot with no improvement. Read that record before repeating experiments. Three sampled disagreements are explained by ordinary versus CCS receiver-load totals; all-nine reconciliation remains open. Sol/high identified the shared32-bit ripple comparator chains as the largest term in Main16's path. Next: full-net load-ratio assessment and a supported conservative synthesis-only optimization target, retaining the original PT/library limits. No blanket0.85 margin is established by three samples. No RTL rewrite, Main16 high run or replacement sweep has been performed.

Nine commercial measurements and source/result audits are complete; read [results](PPA_RESULTS_2026-10-20.md), [execution history](PPA_EXECUTION_2026-10-20.md) and [methodology review](../reviews/phase-5-verify/FastX-PPA-methodology-review.md). Do not rerun completed functional scopes or the sweep solely because Main N16 has a measured timing failure. Preserve that baseline and its raw reports.

Next: investigate the unresolved DC/PT capacitance disagreement and Main N16 critical path, then review a common closure plan. No architecture change is authorized by this report: no extra policy-specific stage, bypass, FIFO rewrite, multicycle or disabled library check. Any flow revision must be recorded and applied equally across all nine configurations. Power needs real activity annotation/capability checks; equivalence, physical/multicorner work remain NOT_RUN. Algorithm-2 remains a separate NOT_STARTED supplement after the baseline review.

FastX SSH/module/DC/PT/library use is now actually VERIFIED. University assets stay remote. The remote session is task-scoped and must be closed after evidence collection; a future connection needs valid authentication, with the already approved pinned host key. Do not save credentials or change global auth/service settings.

## Native workflow and evidence

Native Claude Code2.1.301 and installed RTL Agent Team0.14.6 actually ran the focused verification and implementation/verification workflows. All inspected root/subagent response models are `claude-opus-5-5`, with explicit invocation-local high effort and route `claude/claude-opus-5-5`; global service/settings preserved. Native sessions `49e427c2-a597-447d-b40b-a8ece8c67d92`, `d14dce3f-1edc-44a4-bc34-ba8319dc7b19` and `b10049ae-345e-4f26-8930-b6b83e1caf8e` cover long-run preparation and the narrow TB repair. Final installed `rtl-agent-team:func-verifier` review session: `19094c25-e5cc-4189-a1af-68113637ad07`.

Claude authored RTL/models/TB/runner and the exact eight-stage batch script. Detached native launches failed before batch startup; failed launch evidence is preserved. Codex then executed that same native-authored script in foreground WSL, exit0, and independently audited original JUnit, metrics, exact scope gates and source hashes. Final native func-verifier reviewed the completed evidence; it did not personally execute the long batch. Codex did not substitute as RTL/TB author.

For future Claude calls in the current execution/review work, invoke native Windows Claude Code with the installed focused RTL Agent Team workflow, `--model claude/claude-opus-5-5 --effort medium`, invocation-local settings and actual response-model checks for every agent. If allowance is exhausted, the owner's2026-10-20 exception authorizes GPT6.1 Sol/high to continue and requires recording that provenance. Codex orchestrates and independently reviews; no concurrent writers or unapproved replacement of RTL/TB authorship. Preserve exact prompt/commands/logs/diff/hashes/results. Do not change global auth/service/settings. Do not run rat-auto-design.

WSL uses `source scripts/wsl_env.sh`: Python3.12.3, Verilator5.052, cocotb2.1.0, pytest9.1.1. Native Git Bash calls need LF wrappers and MSYS_NO_PATHCONV=1 for `/mnt/c` paths. Native Claude is the installed agent; no WSL-Claude replacement or reinstall is needed.

Evidence roots (ignored raw files stay local): `artifacts/implementation/<scope>/<run-id>/` contains summary/logs/raw JUnit/metrics. `.setup-logs/implementation/resume-20261017/m5-long-regression-2/` contains exact batch commands/exits, all144 tracked-file launch hashes, native provenance and Codex `stress-audit.json`, `primary-audit.json`, `production-audit.json`, `batch-audit.json`. The source stayed unchanged through the complete batch. Unit independent audit is in `m5-stress-boundary-repair/codex-review/independent-m5-verdict.json`. Native final review logs/diff/manifest are in `m5-final-review/`.

Algorithm-2 is NOT_STARTED, remains a separate approved interpretation, and follows the primary nine synthesis experiments. No IEEE PDF inspection or cycle-identical paper reproduction is claimed; Main four-state hysteresis and the shared one-output10/10 alternation follow the approved project specification. Multi-output/APR/optional extensions remain deferred.

**Historical2026-10-17 checkpoint, superseded by the final nine-case results above:** All nine FastX synthesis/STA/power/PPA configurations were NOT_RUN. SSH/tool/license access was NOT_VERIFIED; the registered-adder smoke is user-reported environment evidence only. Existing remote templates need reviewed N/policy parameter selection and a frozen pilot-derived common methodology before the sweep. Formal/CDC/SystemC/UVM, numerical coverage and RTL mutation campaigns are NOT_RUN/deferred, not PASS; prior14 model mutants do not establish RTL coverage. Strict Verilator checks passed; the earlier default Verible style conflicts remain separately recorded.
