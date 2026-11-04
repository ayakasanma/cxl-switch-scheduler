# Revision issue ledger

## Material Passport

- Origin: adversarial paper review, owner-approved execution plan2026-10-23.
- Verification status: findings mapped to evidence and executable closure criteria.
- The owner approved the v3 manuscript revision on2026-10-27. Original evidence
  locations below identify the pre-revision findings; final dispositions are
  recorded in PAPER_REREVIEW.md and V3_REVISION_QA.md.
- Severity: Major affects validity/central interpretation; Moderate limits scope/reproducibility.
- A corrected working analysis is not a corrected published manuscript.

| ID / severity | Exact evidence location | Reviewer objection | Concrete correction / closure evidence | New experiments? / current state |
| --- | --- | --- | --- | --- |
| F1 Major | Original `docs/final-report/sections/hotnets-body-v3.tex:14` and `:386`; `docs/ppa/primary-20261021-v2.json`, cases indexed by policy/N | Inverting the percentage denominator overstates RR's area reduction; "overall" adds a separate unsupported ranking. | Generate Main-over-RR and RR-below-Main separately; ranges38.22-39.27% and27.65-28.20%. | No RTL. Approved v3 abstract/body/conclusion corrected; three-role round1 review supports the arithmetic and scope. |
| F2 Major | `docs/FORMAL_EQUIVALENCE_2026-10-21.md:10`; `docs/ppa/formality-20261021.json`, current-main-bridge groups; `docs/performance/hog-sparse-source-execution.json` | Different source bytes cannot be equated solely by branch/HEAD. | Reuse three hash-matched Main bridges; prove six FCFS/RR bridges against original mapped netlists; archive exact source/report hashes. Equivalence does not predict re-synthesized PPA. | Six new bridges accepted PASS in `artifacts/fastx/revision-bridges-20261023T185951Z/`; historical proofs retained. |
| F3 Major | `sim/performance/test_hog_sparse.py:27`; `scripts/run_hog_sparse.py:14` | N4/D16/ready1 trained HOG cannot support arbitrary CXL/system behavior. Existing other-profile results do not fill the matched-trained gap. | Keep descriptor-slice scope; add60 trained N8/16 and180 robustness jobs with explicit aggregate-load change. | All60 N expansion rows are sealed and parent-accepted after independent review, including the prior FCFS/N16 resource case exactly once. The full498-row matrix is accepted (498 PASS, zero RUNNING/NOT_RUN/FAIL/UNRESOLVED). N_EXPANSION_RESULTS.md and full60 descriptive analysis are independently reviewed and parent-accepted; this does not close manuscript scope/wording corrections. All180 core robustness and ten DAC robustness rows are sealed and strictly accepted; ROBUSTNESS_RESULTS.md and its independent narrative review are accepted. |
| F4 Major | `docs/final-report/sections/hotnets-body-v3.tex:1`; six-policy comparison absent from original HOG registry | New scheduling claims need relevant baselines, exact original-vs-adapted algorithm boundaries and a literature novelty check. | Six policies, source/method differences for FAI/BLISS/UET; BLISS threshold4, clearing10k, nonblacklisted-first, timestamp/ID within group, no DRAM row-hit. Freeze clear/count ordering before runs. | Baseline correctness accepted:36 lint/15 model/226 cocotb PASS. Six-policy120-run confirmation, independent strict index and paired analysis accepted; see CONFIRMATION_RESULTS.md. Novelty not declared established. |
| F5 Major | `docs/experiments/main-sq/BASELINE_DIAGNOSIS.md:47`; HOG raw metrics per phase/source | Successful service is not offered demand; equal-weight fairness conflicts with DAC's2:1 entitlement. Saturated output is not a general throughput gain. | Separate offered/accepted/fired/backlog and eligible-ready utilization. Residual heavy service expectation is1-3/128;128/131 is normalized offered load. Declare DAC's3H/1L targets2/7 eachH,1/7 L. | ROBUSTNESS_RESULTS.md reports separate generation-cohort latency, measured-phase fired fractions and eligible-ready utilization;190 runs drain outstanding/backlog to zero. Lower heavy arrival rates retain training backlog and do not establish unsaturated low-load behavior. No equal-share fairness claim for DAC2. |
| F6 Major | `docs/experiments/main-sq/BASELINE_DIAGNOSIS.md:55`; `sim/performance/main_sq_diagnosis.py:84` | Aggregate P99 cannot identify whether quotas, High ordering, admission or classification cause the tail. | Reuse tag-linked actual replay; isolate SQ, quota, Main-1W and winner. Trained classes are fixed, sparse FIFO full events0; do not attribute trained-B reversal to slow classification or full sparse FIFOs. | SQ diagnosis, quota/Main-1W sweeps, DAC confirmation and nine adaptation runs accepted. The matching180 core robustness rows are now sealed; all four paired DAC/Main backpressure groups improve for five of five exploration seeds. These are descriptive results without confidence intervals. See SENSITIVITY_RESULTS.md, CONFIRMATION_RESULTS.md, ADAPTATION_RESULTS.md and independently accepted ROBUSTNESS_RESULTS.md. Earlier classification did not improve sparse whole-role waiting in the adaptation cohort; manuscript interpretation remains pending. |
| F7 Moderate | `rtl/top/switch_top.sv:94`; matrix groups rr-quantum/high-quota/depth | A favorable fixed quantum/window/depth may be a tuning artifact. | Freeze single-factor sweeps and exploration seeds before confirmation. Retain Main-1W rows but disclose its quota10/10 model pin-equivalence to Alg2; do not count them as independent mechanisms. | Main-1W5, High-quota15, RR-quantum25 and depth45 are strictly accepted. SENSITIVITY_RESULTS.md and DEPTH_RESULTS.md report exploration-seed results without tuning or confirmation intervals. |
| F8 Moderate | `docs/ppa/primary-20261021-v2.json`, area_partition in each case; `docs/experiments/main-sq/PPA_COMPARISON.md:24` | Whole-area deltas conflate storage, timestamp metadata and policy logic. | Report whole boundary plus nonoverlapping descriptor/timestamp/policy/common decomposition and depth sweep. Keep necessary metadata costs; no unused RR timestamps. Hierarchical rounded FIFO totals alone do not isolate timestamp cost. | Nine historic leaf-area audits accepted, zero unresolved; candidate matched PPA and depth45 performance runs accepted. Cell-count semantic residuals retained. D8/D32 PPA was not measured; no depth area/latency optimum is established. |
| F9 Major | `scripts/run_hog_sparse.py:21`; original seeds509-513 | Five synthetic seeds and request counts do not provide independent repetitions for tuned claims. | Explore509-513; confirm529-548, paired run unit, fixed10k bootstrap, separate cold/trained/A/B/source; disclose finite synthetic-generator scope. | Core120/120 and DAC20/20 confirmation are sealed and strictly accepted on2026-10-25. Complete paired20-seed intervals independently recomputed; see CONFIRMATION_RESULTS.md. Robustness and other matrix groups remain separate. |
| F10 Major | Original `docs/final-report/sections/hotnets-body-v3.tex:14` and `:389` | "Stronger overall" hides profile-dependent latency tradeoffs and unstated workload weights. | Report conditional findings/Pareto; no arbitrary aggregate winner. Insight tie-break allocates research effort only. | Approved v3 retains adverse Main/RR10 comparisons and rejects overall ranking; no new experiment. |
| F11 Moderate | `docs/ppa/primary-20261021-v2.json`, signoff/untested fields; `docs/experiments/main-sq/PPA_COMPARISON.md:38` | Single TT pre-layout25ns and140 disabled checks are not physical/multicorner signoff. | Keep constraints, disabled-check reasons, critical path and exact tool/library/profile provenance; candidate must pass same25ns profile. | DAC matched PPA/formal accepted at TT/25ns;68 constant-disabled checks disclosed. Existing primary9 retained; no physical signoff claim. |
| F12 Moderate | `docs/POWER_EXTENSION_TEST_PLAN.md`, final outcome; `docs/ppa/power-supplement-20261021.json` | Cold and classification-boundary-focused activity are not matched trained-HOG power or natural boundary frequency. | Preserve existing27 cold +3 boundary cases; add9 matched trained jobs with A/B activities separately and coverage/extrapolation qualifications. | All18 local and18 remote captures strictly indexed: nine complete A/B rows (three policies x seeds509-511). Final detached extension passed parent/independent review on2026-10-26; actual controller exit0. Earlier SSH255 and recovered actual EDA0 remain separate. Qualified static-pin table-range warnings retained; descriptive report TRAINED_POWER_RESULTS.md is parent/independent accepted. This closes the matched activity evidence gap, not manuscript revision or physical signoff. |
| F13 Major | `docs/final-report/generated/evidence_manifest.json`; `docs/final-report/QA.md`; existing HOG run indexes | Stale cutoff/PDF metadata does not describe current evidence/artifact. Dirty HEAD alone does not invalidate recoverable exact sources. | Immutable source/trace/config/run indexes, failure retention, new final PDF page/hash/visual QA after approved revision. Source freeze per executed cohort; do not overwrite old archives. | All498 accepted; approved v3 generator/manifest and PDF exist. Round1 DA-R1 identifies missing bridge/diagnosis/audit bindings in the new release; repair and final scoped verification are tracked in PAPER_REREVIEW.md, final QA in V3_REVISION_QA.md. |
| F14 Moderate | `docs/FORMAL_EQUIVALENCE_2026-10-21.md:3`; original `docs/final-report/sections/hotnets-body-v3.tex:18` | RTL-to-netlist equivalence/audit is not a proof that the scheduling specification or workloads are correct. | State exact14 scoped pairs, constant-register exclusions in six baseline cases, independent model/simulation scope; new policy proves equivalence to its own netlist. | Six new bridges and DAC-to-own-netlist proof accepted; original scoped proofs retained. Approved v3 states these separate proof boundaries; bridge evidence binding is handled under DA-R1. |
| F15 Major | `docs/experiments/main-sq/BASELINE_DIAGNOSIS.md:47`; original service-window classifier | B/S classifies realized service. FIFO activity only sees admitted demand;2:1 credits are a policy choice. | Name DAC active-source weighted allocation; expose queue/backlog diagnostics separately; never feed TB-only upstream backlog into selection or claim full demand estimation. | DAC1/DAC2 model ablations and four-window feedback complete; sole DAC2 RTL correctness accepted. Ten RTL robustness rows and20 confirmation rows accepted. New-seed trained-A/B improvements are actual RTL evidence; paired backpressure comparisons now have complete matching Main baselines (five exploration seeds per group, no confidence intervals). No full upstream-demand claim. |
| F16 Moderate | `docs/phase-5-verification/M6-long-results.md`; original W256 and W5M records | Conflating pilots, production, model-only screens and actual interventions creates unsupported causal/production claims. | Keep Algorithm-2's existing20M/four realW5M-window evidence, existing Main production/multisource/stall evidence, and boundary power. Explicitly label new incomplete/model-only results. | No blanket rerun; missing comparative arms only. |

## Priority and acceptance

1. Source chain, F1 denominator correction data and immutable evidence.
2. Six-policy baseline correctness and new-seed confirmation.
3. Causal replay/ablations, then trained robustness.
4. N expansion and single selected insight RTL only after complete validated gate.
5. New power, manuscript revision after separate approval, independent three-seat re-review.

The model gate is not a paper acceptance verdict. A negative model outcome closes candidate
screening without adding RTL; missing production evidence leaves it UNRESOLVED.
The full study is not complete until every required row is executed or the owner explicitly
changes scope. The original two-week budget does not authorize silently dropping rows.

## Execution checkpoint

- F1/F9/F13: parent rechecked42 Python tests across matrix, statistics, baseline
  configuration, bridge tooling, insight model and screen suites, all exit0.
  `parent-audit/checkpoint-20261023T1022/summary.json` retains commands/logs.
  Its535 protected source/document paths match the native RTL entry snapshot;
  all15 production-model frozen dependencies also match. This count reflects
  that checkpoint's recorded path filter, not an expanded formal scope.
- F2/F11/F14: six missing bridges are BLOCKED at authentication,0/6.
  No remote shell, license probe, new PPA or proof executed.
- F4/F6/F7: native RTL/models/testbench exist. Three-case diagnostic passed;
  first complete36-case run failed nine RR empty-generate structure assertions.
  Strong structure-check repair is assigned to the native agent. Baselines
  are not yet accepted for production performance.
- F5: parent requested an explicit joint eligible-and-ready opportunity count,
  separating it from all ready cycles and offered-source-cycle counts.
- F15/F16: sealed60 HOG +8 feedback model queue is running; first three
  baseline configurations exited0. Final gate and candidate advancement remain
  unresolved. W256 pilots are retained as sensitivity evidence.
- F3: heavy-ID robustness is a static source0/3 permutation from reset.
  Role changes with retained queues remain the separate adaptation experiment;
  original immutable matrix snapshot is preserved.

## Superseding checkpoint: approved99400de, 2026-10-24

- F4/F6/F7: source-complete full correctness acceptance now PASS at
  revision-baseline/20261023T171608Z_276:36 lint,15 model and226 cocotb tests,
  zero failures/errors/skips, stable sources and exit0. The RR repair used
  the approved Sol/high fallback only after explicit native quota exhaustion.
  Production performance remains separate and unexecuted at this checkpoint.
- F15/F16: all60 production HOG and eight real-four-W5M model feedback jobs
  completed. Parent strict re-ingest reproduces the PASS gate and sole frozen
  DAC2 candidate; all six AGE settings fail benefit screening. DAC1 ablation
  is retained. MODEL_ONLY results authorize one DAC RTL implementation, not
  a hardware benefit claim or paper acceptance.
- F13: the first passing full baseline ZIP omitted a new hierarchy helper.
  The dependency list and a regression were fixed, and the complete fresh
  source-bound run above replaces it for reproducible correctness acceptance.
- F2/F11/F14: authentication still blocks all six new bridges and remote
  candidate PPA/equivalence/power. No missing check is treated as PASS.
- Manuscript fixes and final PDF QA remain pending separate revision approval;
  no paper text was changed by this continuation.
- F8: nine archived mapped netlists now have540,590 disjoint attributed leaves,
  zero unresolved ownership and precision-bounded area reconciliation.
  Neither leaves nor leaves+hierarchy explains the archived number_of_cells
  fields; retain count-definition warnings. This closes the offline area
  partition subtask, while planned depth measurements/new candidate PPA remain.
- F5/F13: N16 pilot exposed an overstrict new training guard; repair restores
  the historical cohort-only training check while preserving A/B drainage
  checks and the exact exogenous traffic. Fresh source-bound pilots are required
  after this repair; no production batch has advanced on the failed pilot.

## Subsequent acceptance and execution checkpoint: 2026-10-24

- F4/F6/F7: native DAC correctness is accepted at
  revision-dac/20261023T174033Z_1699:54 strict lint, six intentional rejection
  cases,192 cocotb tests across18 configurations,four runner and13 model
  unittest tests, zero failures/errors/skips, source ZIP independently checked.
  This does not close candidate performance, mapped equivalence or PPA.
- F5/F9/F13: fresh core N4/N16 pilots pass. The parent started the reviewed
  supervisor waiting for actual resource exit0 and complete sealed W5M
  validation before the459-row core queue can advance. These include the
  single reused resource row and458 queued rows; no missing job is PASS.
- F6/F9: DAC2 and separate DAC1 W256 pilots pass with the same trace, zero
  production matrix contribution. Parent repeated23 runner tests and
  revalidated102 native,275 sealed-screen and10 DAC2 pilot bindings.
  Independent read-only review found no concrete production blocker. Frozen
  DAC2 production is authorized for the original30 conditional rows; launch
  and completion remain separate recorded events. No parameters may be tuned
  using confirmation seeds.
- F9/F13: analysis adapter14, index16 and statistics4 tests pass. At that
  checkpoint no complete confirmation cohort is accepted and no interval is
  computed. Optional cold runs remain outside the120 core denominator.
- F13:535 protected accepted RTL/spec/manuscript files still match the native
  entry snapshot. No manuscript edit or new remote transport attempt was made.

Subsequent2026-10-24 recovery supersedes the preceding remote-access status:
owner SSH login and authenticated batch probe exit0; six-bridge preflight
passes and FCFS/RR N4/N8 tool wrappers exit0. F2 remains open until all six
downloaded proof reports are independently accepted. F8/F11 DAC preparation
passes11 parent unit tests plus independent payload review; the single matched
TT25ns DC/PT and mapped-equivalence run is authorized, with no measured DAC
PPA or formal acceptance claimed yet.

F2 source-bridge follow-up: all six declared FCFS/RR N4/N8/N16 bridges now
PASS at `revision-bridges-20261023T185951Z`. Parent repeated the strict audit
of every downloaded report and matched every remote/local report hash.
Together with the retained Main bridge evidence, the identified six-case
cross-version equivalence gap is closed within its exact source/parameter
scope. This does not close the remaining experiment-comparability work.

F8/F11/F13 DAC follow-up: the matched N4 DC/PT and mapped equivalence
completed with all exits0 and independent actual-report acceptance.
Cell area109794.784709;9014 registers;9126 passing formal points;
worst setup/hold slack+10.398800/+0.038578ns. All68 untested timing
checks are disclosed propagated-constant disabled arcs. Leaf area reconciles
within report precision; the63-cell tool-count residual remains documented.
This satisfies the candidate's specified mapped-equivalence/timing evidence
within TT25ns pre-layout scope, while candidate performance adoption and
matched power remain open. See DAC_PPA_RESULTS.md.


## Continuation checkpoint: 2026-10-24 08:53 Taipei

- Owner temporarily replaces future Opus work with explicit GPT6.1 Sol/high.
  Power replay mode implementation remains pending verification; no paper edit.
- F3/F4/F9/F13: queue status files are stale RUNNING; their WSL processes no
  longer exist. Core39 and DAC7 raw result JSONs are retained, with zero failed
  steps in saved summaries. Complete bundle/cohort acceptance remains pending.
  Interruption cause is unknown; source-bound recovery is being prepared.
- Both frozen source closures (39/53) and539 protected RTL/spec/manuscript
  files match. F2 bridges and the accepted DAC mapped PPA/proof are unaffected.

## Current disposition: 2026-10-24 09:18 Taipei

This checkpoint supersedes earlier pending/access/interruption statements only
within the scopes listed below. It is not manuscript closure.

| Issues | Accepted evidence / remaining work |
| --- | --- |
| F1, F10, F14-F16 wording | Arithmetic, attribution and claim boundaries documented; manuscript correction still awaits separate approval. F14's six missing source bridges have passed. |
| F2 source chain | All six FCFS/RR bridges accepted; three existing Main bridges retained. No further bridge rerun is needed merely to reconnect SSH. |
| F3, F4, F6, F7, F9 comparative experiments | Baseline correctness accepted. Recovered core queue is live with three simulators; final groups, confirmation statistics and complete matrix remain pending. |
| F5, F15 allocation / demand | DAC2 won the sealed model-only gate; DAC1 remains the allocation-weight ablation. Thirty selected DAC2 RTL performance jobs are in the recovered lane with one simulator. No confirmed RTL benefit is claimed yet. |
| F8 area attribution | Nine historic full-design leaf-area audits accepted. DAC matched area also reconciles; tool cell-count semantics remain an explicitly unresolved limitation. Depth sensitivity remains in the core queue. |
| F11 candidate feasibility | DAC N4 mapped equivalence and original TT/25ns pre-layout timing passed. Disabled checks remain disclosed; physical signoff is outside scope. |
| F12 matched trained power | Native trained-mode extension passed its released tests and independent contract review. First actual Main/seed509/A W5M export and serialized audit are running; no actual SAIF/PT power result exists yet. Other 17 captures remain prepared, not launched. |
| F13 reproducibility | Recovery reuses 39 core plus seven DAC raw completed simulations without rerunning them. Final archive acceptance remains pending; index keeps incomplete bundles RUNNING. Frozen core39, DAC53 and power33 sources still match. |

WSL's observed kernel-instance change removed the old SSH control socket.
This is distinct from a failed password or unavailable remote EDA service.
The remote-power preparation has not reauthenticated or run remote tools.
Local simulation and export continue independently. The three requested
independent manuscript re-review seats remain pending an approved revision.

F12 follow-up at09:37: the first Main509A actualW5M capture and its serialized
audit passed, including parent independent archive/phase/closing integrity
validation. The remaining17 captures now run sequentially under a source-bound
Windows batch. Two sidecar schema/scope integration errors were caught before
continuation and repaired with real-data regressions; the first capture was
not rerun. Local capture acceptance does not close the nine power jobs:
gate replay, measured-only SAIF, PT and semantic review still remain.


## Evidence checkpoint2026-10-24 ~13:03 Taipei

- F2: the six FCFS/RR N4/8/16 bridges remain accepted PASS from
  `artifacts/fastx/revision-bridges-20261023T185951Z`; a lost SSH session
  does not reopen these already archived proofs.
- F3/F5/F9/F13: all ten DAC trained robustness rows now pass strict sealed
  evidence inspection. Confirmation remains incomplete. The current index
  `queue-recovery/index-handoff/snapshot-20261024t0510z` contains11/498 PASS,
  including the prior N16 resource row; no partial-cohort confidence interval
  is reported. Core60/120 and DAC1/20 completed raw confirmation runs are
  reused by the next recovery attempts, not treated as sealed group acceptance.
- F11: accepted DAC TT/25ns pre-layout PPA/equivalence stays valid with its
  disabled-check disclosures. It is not a power or physical-signoff result.
- F12: first Main509A serialized capture is accepted. Six further captures
  have completed records under local validation. A stale Windows producer
  receipt is under recovery review; no remote SAIF/PT result is accepted yet.
- F13: core39/DAC53/power33 and539 protected RTL/spec/manuscript hashes match.
  The same frozen core/DAC recovery plan has resumed after a confirmed new
  WSL kernel instance. Interruption cause remains unknown; old attempts retained.
- F14-F16 and manuscript edits: remain subject to the declared scope and
  separate manuscript approval. No text or final PDF was changed in this turn.

At ~13:09 the local F12 capture inventory is7/18 accepted with zero validation
failures; exact remaining11 exports are actually running from fresh paths.
The approved single Main509A remote power stage has passed preflight/upload0
and is in progress, with no SAIF/PT semantic acceptance yet. Reconnection is
verified successful; no previously accepted bridges/PPA were rerun. Final
core39/DAC53/power33/protected539 hash checks have zero differences.


## Evidence checkpoint2026-10-24 15:48 Taipei

- F12: Main509A and recoveredFCFS509A gate/PT single-case evidence is independently
  accepted, with FCFS's three exact static-net table-range warnings retained.
  Neither matched A/B pair is complete. Local serialized captures16/18 accepted;
  remaining16 remote continuation is running serially onFCFS509B. Input captures
  and actual power results remain distinct. Original SSH255 and verified recovery
  are separately indexed without replaying the recovered case.
- F3/F5/F9/F13: core77/120 and DAC5/20 raw confirmation successes remain unsealed;
  DAC robustness10/10 stays sealedPASS. Parent repeated33 index+20 analysis tests
  PASS and reproduced strict snapshot11PASS/140RUNNING/345NOT_RUN/2UNRESOLVED.
  RUNNING is declared row scope, not worker count; no partial-cohort CI is reported.
- F13: core39/DAC53/power33/protected539 hashes unchanged. Full matrix, manuscript
  revision/PDF QA and independent post-revision review remain incomplete.


## Evidence checkpoint2026-10-24 17:05 Taipei

- F12 inputs: all18/18 exact trained captures accepted, including11 recovered
  exports revalidated by parent. This completes input generation only.
- F12 semantics: returned FCFS509B/RR509A/RR509B have independently accepted
  qualified prelayout results after parent repeated six calibration tests and
  three full semantic reviews. Old B blocked receipt remains immutable. Exact
  six-significant-digit PT display comparison fixes a proven local reviewer
  precision error; runtime/SAIF/source data were not changed. Each exact prior
  range warning remains disclosed and mapped to zero-activity measured SAIF nets.
  Pair-level strict-index adoption is pending the approved standard receipt patch.
  Main509B and remaining remote jobs continue; no cohort-level power claim yet.
- F3/F5/F9: core84/120 and DAC7/20 successful raw confirmation runs remain
  unsealed; no partial bootstrap. DAC robustness10/10 remains sealedPASS.
- F13: core39/DAC53/power33/protected539 all unchanged. New reviewers/receipts
  live in distinct ignored scopes; original SSH255 and semantic failure retained.
  Full matrix and approved manuscript revision/re-review remain incomplete.


At17:09 parent independently accepted strict FCFS509/RR509 A/B power rows after
36index+20analysis testsPASS and fresh index/analysis. Current matrix13PASS/
140RUNNING/344NOT_RUN/1UNRESOLVED; Main509B remains pending. F12 now has two of
nine matched rows, with all18 local input captures accepted. Exact table-range
limitations retained; one seed is not a multi-seed confidence interval.


## Evidence checkpoint2026-10-25 00:40 Taipei

Corrected strict index accepts173/498 rows:120core confirmation,5Main-1W,
15High-quota,20DAC confirmation,10DAC robustness,1N16 resource and2matched
power rows. RR quantum25 declared active;299NOT_RUN,1UNRESOLVED(Main509B),
zero FAIL. Declared active rows are not worker counts. Parent independently
recomputed all six complete-cohort intervals in CONFIRMATION_RESULTS.md.
Index insight-count reporting bug fixed with regression; old snapshot retained.
F12 requires fresh owner SSH authentication before bounded existing-result
recovery; actual Main509B EDA status remains unknown. Manuscript unchanged.


## Superseding checkpoint: 2026-10-25 04:20 Taipei

- F12/F13: all six seed509 remote cases are independently adopted and strictly
  indexed as three complete matched A/B power rows. MainB original255 transport
  history is retained alongside recovered actual EDA exits0. Parent repeated
  60 index/analysis tests and directly revalidated all six case contracts.
- Full-matrix snapshot:199PASS/45declaredRUNNING/254NOT_RUN/0FAIL/0UNRESOLVED
  of498. Depth45 remains unsealed and active with three actual workers.
- F12: exact remaining12 seed510/511 serial continuation launched once after
  fresh existing-master probe0 and six offline checks. First FCFS510A preflight
  and upload exits0; no new remote case is yet adopted. No seed509 rerun.
- F13: core39,DAC53,power33,protected539 hashes unchanged. Parent acceptance
  receipt:parent-continuation-20261025T0418/acceptance.json. No Opus invocation.
- Paper arithmetic/claims, final PDF QA and independent manuscript re-review
  remain pending separate approval; experiments in progress are not PASS.


### 2026-10-25 07:33 Taipei - strict index201/498; five power pairs

Parent accepted only the four exact standard seed510 release hashes in the
existing index allowlist. The indexer schema and semantic acceptance logic are
unchanged. Parent independently repeated41index+20analysis tests:61PASS, then
directly checked all10 actual case contracts and release/source hashes.
Strict snapshot power-index/seed510-implementation-20261025/
snapshot-20261024T233121Z/ reports201PASS,45declaredRUNNING,252NOT_RUN,
0FAIL,0UNRESOLVED of498. Five of nine matched A/B power rows are complete;
10of18 individual activity captures have adopted returned power evidence.
Main510 and all511 power pairs remain unaccepted. The producer inputs for
all18 captures were already accepted; this count concerns remote output review.

Parent receipt:parent-continuation-20261025T0728/index-acceptance.json.
Core/DAC confirmation inference is unchanged. No partial power-cohort CI or
cross-profile overall ranking. Depth45 remains unsealed; no raw result is
promoted merely because its cocotb step passed. Existing local/remote queues
continue without duplicate jobs. Manuscript remains read-only.


### 2026-10-25 10:26 Taipei - depth45 sealed; adaptation active; remote transport stopped

Depth45 scope is PASS with45valid jobs,94steps/91tests,zero failures/errors/
skips. Parent independently ran the existing strict bundle inspector:sourceZIP,
evidenceZIP, exact configs/traces/rows/JUnit/exit/source binding all PASS.
Core queue advanced ordinal4exit0 to adaptation9 ordinal5 with three live
simulators near100%CPU. Parent fresh strict index and analysis both exit0:
246PASS/9declaredRUNNING/243NOT_RUN/0FAIL/0UNRESOLVED of498; power remains5/9
accepted pairs. Adaptation raw summary has no completed cocotb job yet.
Index/analysis and parent release:parent-continuation-20261025T1025/.

Remote continuation12 stopped at Main510A. Power SSHouter255 ended07:57:22,
fetch255 ended07:57:23; parent supervisor exit1. The first four seed510 cases
remain accepted. Actual master-control check at10:22:47 exits255 because the
configured Unix control socket does not exist. This establishes transport/
authenticated-session unavailability only, not VPN root cause or actual EDA
failure. Main510A remote EDA exit remains UNKNOWN until real inspection.
No blind rerun, upload, cleanup or continuation restart was attempted.

Sol/high prepared an exact existing-case read-only Main510A recovery using the
frozen earlier verified inspect/fetch implementation. Parent identified copied
MainB labels; author fixed both labels and added assertions before release.
Parent repeated all5 testsPASS, checked exact plan9b81a4efeaf10234ea0ccadff253f86d
db00b4dc3ed79042aa6c26e8a5c068bd and source freeze. Recovery has NOT executed;
it requires an actual restored-master sentinel probe. Prior failed transport
records and failed drafts are retained; remaining seven never-started cases
are not silently resumed. No credential was used or logged by the agent.

Core39,DAC53,power33,protected539 remain unchanged. Depth descriptive analysis
and independent adversarial evidence review are underway; no extra parameter
selection, confidence interval or full-system claim. No Opus, manuscript edits
or commits. Full matrix/power cohort and manuscript re-review remain pending.


### 2026-10-26 01:34 Taipei - adaptation interpretation adopted; robustness93 raw; Main510B transport loss

Parent repeated45index+20analysis testsPASS and adopted the exact Main510A
index extension. Eleven accepted single captures yield5completeA/Bpower rows;
Main510A alone creates one explicit unresolved pair, not a sixth PASS. Fresh
strict snapshot/index+analysis exit0:255PASS/180declaredRUNNING/62NOT_RUN/
1UNRESOLVED/0FAIL of498. Parent rehashed all snapshot release members.
Robustness has93/180raw successful simulations but remains unsealed; three
actualsimulators advanceCPUtime, so raw93 does not promote formalrows.

Independent adversarial review of adaptation9 finds no material discrepancy:
54windows/216literal transitions/405latency distributions/three complete
Alg2-Main1W observable pairs/104report table rows/55existingJUnit cases match.
Parent adopted the report and preserved its reviewed original bytes/hash.
One prose precision correction changes22numericexit0 to21toolsteps numeric0
plus one derivedscopePASS. Numeric results, source and reporttables unchanged.
Direct frozen-v1 audit correctly detected that reporthash change; noassertion
was waived. Parent reran all5mutation tests against the exact archived report
bytes:PASS. Parent asserts the current report differs only by that one sentence.
Evidence:parent-continuation-20261026T0124/adoption.json and
adaptation-independent-20261026t0124/RELEASE.json.

Observed adaptation result:Alg2/Main1W classes react at5M versusMain10Mcycles
after alignedroleswitches, but earlier classification does not reduce sparse
whole-role latency here; heavymeanwait is lower and sparsemeanwait higher.
Main settles at phaseend. No latencyrecoverybound, per-windowP99, independent
Alg2/1Wmechanism, fullcyclecrossRTLproof or universalwinner is inferred.
Three explorationseeds only; negative results retained.

Remote exact7 stopped atMain510B:powerSSH255 ended2026-10-25 17:56:29Taipei
after7218.474seconds, fetch255 followed. Noneofremaining6waslaunched. Actual
remoteEDAexit remainsUNKNOWN. Currentmastercheck2026-10-26 01:24:43 exits255
because configuredsocketmissing; noownerloginor remoteinspection attempted.
Existingcase-only recovery is being prepared; no blind rerun, upload, signal
or cleanup. Repeatedapproximately2htransportloss is underread-onlydiagnosis,
notattributed toVPN orEDAwithout evidence.

Core39,DAC53,power33,protected539 unchanged byparenthashguards. NoOpus,
passwordhandling, manuscriptedits orcommits. Wholematrix/powercohort and
post-approved-manuscript independentre-review remainincomplete.


## 2026-10-27 v3 revision, final PDF QA and scoped re-review complete

The owner explicitly approved the v3 manuscript revision. This supersedes earlier
approval-pending/manuscript-pending notes without changing their historical receipts.
All498 experiment rows remain accepted PASS; no experiment, SSH, EDA or Opus was
launched for this revision. The historical main.tex/body and frozen core39/DAC53/power33
inputs remain preserved. Sol/high handled bounded author/data/reviewer tasks; the
parent integrated the driver, corrections, build and visual QA.

Round1 found one Major release-evidence gap and three Minor reporting issues:
missing exact bridge/replay/leaf-audit/screen bindings; N-expansion table locator;
DAC reset/mid-round credit contract; numerical disjoint-area presentation. The
repair binds588 existing records, adds the N4 category-area subset table and exact
state/locator wording, and separates performance-index scope from supplemental
proof/diagnostic records. No new experiments were requested or used to close these.
The historical initial findings and pre-repair freezes remain unchanged.

The parent independently repeated allfour final generator tests PASS, rehashed
all18 repaired-data release artifacts, compiled twice with exits0, and visually
inspected allnine rendered pages plus contact sheet. Final log: zero overfull or
undefined references/citations;29 underfull hboxes and the MiKTeX update-check notice
are retained. Final PDF output/pdf/cxl-scheduler-v3-revised-20261027.pdf SHA256:
892abcf3102c17bb75a5825ded5628368cf86a1c8397a727819136cb7a776400.

Devil's Advocate DA-R1, Methodology M-R1-01 and Domain W1/W2/U1/U2 are closed in
scoped round2 with no open scoped findings. Parent checked actual release/child
report hashes before adoption. See PAPER_REREVIEW.md and V3_REVISION_QA.md for
exact role releases, findings, F1-F16 dispositions, prioritized completed roadmap
and limits. Parent receipt: manuscript-revision-20261027/parent-round2-adoption.json
under .setup-logs/implementation/revision-20261024/.

Final reviewable bundle: output/pdf/cxl-scheduler-v3-release-20261027.zip; exact
archive/manifest hashes are recorded separately under the same manuscript scope's
final-release/archive-receipt.json. The bundle contains paper, presentation data,
review records and hash locators, not all raw experiments or proprietary inputs.
This is local uncalibrated advisory review, not external peer-review acceptance,
independent model-error assurance, physical signoff or full-system CXL validation.
No commit or publication was requested or performed.
