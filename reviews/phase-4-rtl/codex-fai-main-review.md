# Codex Main FAI independent review — functional acceptance

Updated2026-10-17 (Asia/Taipei). **M5_MAIN_FUNCTIONAL_ACCEPTED**. Approved Spec v1.0 remains frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Verified source: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`. This accepts Main functional integration and the common/FCFS/RR regression, not the whole project or PPA.

Native final-review outcome: both reports, all raw audits, post-review hashes and the manifest were saved before the final-summary API call returned HTTP429/session limit. The CLI then exited1 naturally after its built-in retries; this is not a successful CLI exit. It reported reset2026-10-17 13:50 Asia/Taipei (an estimate, not verified availability). All148 actual inference response records are claude-opus-5-5; the additional synthetic record is the API error, not another model. Native written verdict PASS_M5_MAIN_FUNCTIONAL and Codex acceptance rest on inspectable completed evidence, not process success. No further API retry, settings change or automation was started. Future native Claude work waits for account availability; current documentation/independent acceptance can finish locally.

Verdict: **ACCEPTED_M5_MAIN_FUNCTIONAL**. Reviewed the native final evidence reports, exact source/configuration/run IDs, original JUnit and source-stable batch. Approved project semantics and common synthesis boundary are retained; no new correctness-critical contradiction or owner design decision was identified. This is bounded functional acceptance, not formal proof, paper reproduction, quantitative fairness or PPA acceptance.

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

## Independent checks and common architecture

The batch audit independently reparsed raw XML for all eight scopes and verified expected collections, zero failure/error/skip/NOT_RUN, no warning relaxations, fatal strict lint, all structural checks and separate expected ALG2 rejections. All144 tracked-file hashes matched launch source through the batch. The independent source-stable M5 execution separately805PASS; directed case19 ran30 times.

Stress audit checked all30 unique N/window/seed combinations and all16 measured transitions in each, exact measured-boundary/whole-run full-FIFO follow-up relations and first-drain held pushes. Primary audit checked60 tracked intended hashes, exact common deterministic metrics against accepted FCFS and separate measurement/drain populations. Production audit recomputed every closing-edge threshold/class transition with Python integers and the literal approved Main table, checked20million real measured cycles per N, four exact closing edges, S=sum(B), held/fire boundaries, and full per-source conservation through responses/drain. Actual per-cycle RTL verification remained active; no state preload or time skip.

Static review retains the earlier Main table/width/quota/hold analysis below. Common descriptor package/FIFO/output-hold/FCFS selector/RR remain unchanged from accepted common architecture. Main reuses the shared oldest-eligible selector, carries only its necessary5-bit hold context and adds no data buffer/pipeline/bypass. FCFS/RR retain1-bit opaque context; RR timestamp/counter/oldest-selector exclusions have positive controls for real storage and FCFS/Main metadata. Generated-model structure is not a mapped-area measurement.

The first full stress attempt `20261017T010035Z_1025` executed9 cases (7FAIL/2PASS;21NOT_RUN). Failures were the summary assertion that incorrectly required a full-FIFO closing measurement fire's next-cycle-ready observation to remain inside the frozen measurement snapshot. The first drain cycle owns that observation. Claude's source `cefbbb0` repairs only TB accounting, adds directed case19 and updates the pinned collection/report. The repair asserts exact measured-plus-observed-boundary-owed and exact whole-run relations, including actual first-drain ready/held-push/descriptor checks. No RTL/model/shared-helper/trace/Spec change or arbitrary off-by-one tolerance. Original failed logs remain preserved. Fixed-seed510 six simulations passed, but their subset gate correctly failed; only the later full30 is accepted.

Native Claude Code2.1.301 and installed RTL Agent Team0.14.6 actually ran the focused verification and implementation/verification workflows. All inspected root/subagent response models are `claude-opus-5-5`, with explicit invocation-local high effort and route `claude/claude-opus-5-5`; global service/settings preserved. Native sessions `49e427c2-a597-447d-b40b-a8ece8c67d92`, `d14dce3f-1edc-44a4-bc34-ba8319dc7b19` and `b10049ae-345e-4f26-8930-b6b83e1caf8e` cover long-run preparation and the narrow TB repair. Final installed `rtl-agent-team:func-verifier` review session: `19094c25-e5cc-4189-a1af-68113637ad07`.

Claude authored RTL/models/TB/runner and the exact eight-stage batch script. Detached native launches failed before batch startup; failed launch evidence is preserved. Codex then executed that same native-authored script in foreground WSL, exit0, and independently audited original JUnit, metrics, exact scope gates and source hashes. Final native func-verifier reviewed the completed evidence; it did not personally execute the long batch. Codex did not substitute as RTL/TB author.

Evidence roots (ignored raw files stay local): `artifacts/implementation/<scope>/<run-id>/` contains summary/logs/raw JUnit/metrics. `.setup-logs/implementation/resume-20261017/m5-long-regression-2/` contains exact batch commands/exits, all144 tracked-file launch hashes, native provenance and Codex `stress-audit.json`, `primary-audit.json`, `production-audit.json`, `batch-audit.json`. The source stayed unchanged through the complete batch. Unit independent audit is in `m5-stress-boundary-repair/codex-review/independent-m5-verdict.json`. Native final review logs/diff/manifest are in `m5-final-review/`.

Algorithm-2 is NOT_STARTED, remains a separate approved interpretation, and follows the primary nine synthesis experiments. No IEEE PDF inspection or cycle-identical paper reproduction is claimed; Main four-state hysteresis and the shared one-output10/10 alternation follow the approved project specification. Multi-output/APR/optional extensions remain deferred.

All nine FastX synthesis/STA/power/PPA configurations are NOT_RUN. SSH/tool/license access is NOT_VERIFIED; the registered-adder smoke is user-reported environment evidence only. Existing remote templates need reviewed N/policy parameter selection and a frozen pilot-derived common methodology before the sweep. Formal/CDC/SystemC/UVM, numerical coverage and RTL mutation campaigns are NOT_RUN/deferred, not PASS; prior14 model mutants do not establish RTL coverage. Strict Verilator checks passed; the earlier default Verible style conflicts remain separately recorded.

## Historical bounded reviews (superseded)

The following earlier reviews are preserved as history; their incomplete/quota states no longer describe the current functional result.

# Codex Main FAI review — bounded unit acceptance, complete M5 pending

Date:2026-10-17 Asia/Taipei. Source `db96961935060fe4ccac686fc9c0fe1b277e38f0`. **UNIT_VERIFIED; FULL_M5_NOT_ACCEPTED**. Native Claude primary author and Codex independent reviewer each executed M5 with775PASS (196reference+39helpers+540cocotb),0failure/error/skip,27strictlint/9probes/3separateALG2 rejections. Stable final independent source hashes and raw JUnit audited; evidence artifacts/implementation/M5/20261016T194435Z_363 and .setup-logs/implementation/resume-20261017/m5-verify-resume/codex-review/independent-m5-final-verdict.json.

All RTL/refc/frozen specs and accepted common FIFO/hold/FCFS/RR helpers unchanged. The FAI-specific harness retains three independent checking layers, observed producer hold and TB-only responses; its opt-in FCFS mirror and informational-log trimming do not change synthesized design or oracle decisions. Runner correctly separates full scopes from smoke/N/seed overrides and pins actual collections. The18directed/random cases ran for allN/windows/five seeds. No new architecture contradiction found in this bounded review.

Initial NameError repaired. The removed short-random per-seed UP assertion was a coverage assumption unsupported by that unchanged saturation-heavy profile, with actual45window evidence UP0/DOWN58/KEEP118/S04. It is explicitly documented, not silently waived; mandatory directed all16/threshold assertions remain and every full stress run must reach all16. Complete acceptance still requires actual long stress coverage; offline prediction is not a replacement. The stress-only helper changed during the first Codex rerun, so a stable-source final rerun was required and passed.

New long scopes/streaming production harness reviewed statically and via labelled smokes only. N16 2million-cycle smoke passed with0windows and~48MiB peak RSS; no production boundary behavior or full matrix conclusion follows. Full stress30, exact-hash primary60,20million real cycles perN (four windows), relevant old full regressions and final native func-verifier remain unrun. Do not mark complete M5/common integration gate accepted or launch PPA.

Actual native Opus5.5/high root/orchestrator/testbench-dev hit HTTP429 session limit after completed jobs, reported2026-10-17 08:00 reset. Codex stopped only this CLI; no natural completion, no final verifier, no substitute author. Source/diff/native transcripts/quota evidence: .setup-logs/implementation/resume-20261017/m5-verify-resume/checkpoint/. Resume after account availability. No new owner design decision.

## Historical bounded static/model review (2026-10-16)

# Codex independent Main FAI review â€” partial checkpoint

Date2026-10-16 (Asia/Taipei). Source `91bf36f84bff7ad5251a8414509191c3f39f26ab`, approved v1.0 unchanged at1af80967bbc2fb83224f4725c4fb450889e69c62. **PARTIAL_RTL_MODEL_TB_DRAFT; no hardware acceptance.** Current blocker is actual native Claude HTTP429 session limit, estimated19:20 reset; the task CLI was stopped after the error, exit-1.

Read-only checks completed:

- Main table and effective classes match Option A: buffers preserve previous class; KEEP/opposing/S0 cancel pending transitions. No Algorithm-2 target-class semantics mixed into Main.
- B/S/index widths are23 in production; unsigned32-bit operands are zero-extended before exact thresholds. Independent arithmetic boundary facts include N16,S5m,B93750 and312500 equality KEEP and maximum10*N*B=800million.
- Counters count actual granted-source fire; closing counts include its fire then classify/clear. Visit/quota uses retained class/used context, with windows not independently resetting it. Post-edge class-live uses closing-cycle map consistently with Spec8.4 transfer-before-classification derivation.
- Candidate is isolated from same-edge fire/push/ready; a single shared FCFS selector filters eligible heads by effective class. Shared FIFO/hold/selector/RR/package unchanged, Main context5bits and FCFS/RR1bit; no added stage/bypass/buffer/debug port.
- Abstract model uses class names, unbounded counters, absolute arrival order and opaque context conversion. It was authored by the model agent without reading FAI RTL; manually specified tests constrain the shared interpretation. Codex independently PASS196 reference pytest (103new) and27 strict Verilator configs,0diagnostics.
- Draft TB retains oracle plus independent pin-history class/window/visit accounting, S=sum(B), full105/source/order/conservation, C1 input hold/drain and TB-only responses.18 directed/random cases are present. AST parsing succeeds; **none has run**. Partial runner has196 expected reference count and ALG2-only rejection helpers, but no registered M5 and no finished Main-positive wiring in older scopes.

Failures were retained/repaired at their proper level: structural simulation-build warning fixed by splitting combinational blocks; random model event misses fixed by longer runs with mandatory assertions retained; mutation helper pattern error fixed. Fourteen selected Python model mutants were killed; no RTL mutation or numerical coverage is claimed. Verible default-style conflicts are recorded separately from required strict Verilator passes.

Native root/orchestrator/rtl-coder/two testbench-dev agents all actually returned claude-opus-5-5, with explicit high effort; no fallback implementation by Codex. Original logs, task patch and hashes: .setup-logs/implementation/resume-20261016/m5-fai-main/checkpoint/. Independent lint/model/static evidence: codex-review/ and artifacts/independent/m5/model-review/.

Remaining required evidence: actual M5 cocotb, W64/256 stress, post-change common/FCFS/RR regression, exact-hash primary60, productionW5million over>=3real windows perN, native final func-verifier and Codex independent acceptance. Current functional matrix remains120/180; FAI60 and all PPA NOT_RUN. Prior M1-M4 acceptance is for its recorded source, not this new unverified integration. No new correctness-critical conflict or owner architecture choice identified. Resume task and exact incomplete registry details are in docs/RESUME_CLAUDE.md and docs/phase-5-verification/M5-results.md.
