# M5 Main FAI — functional integration accepted

Updated2026-10-17 (Asia/Taipei). **M5_MAIN_FUNCTIONAL_ACCEPTED**. Approved Spec v1.0 remains frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Verified source: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`. This accepts Main functional integration and the common/FCFS/RR regression, not the whole project or PPA.

Native final-review outcome: both reports, all raw audits, post-review hashes and the manifest were saved before the final-summary API call returned HTTP429/session limit. The CLI then exited1 naturally after its built-in retries; this is not a successful CLI exit. It reported reset2026-10-17 13:50 Asia/Taipei (an estimate, not verified availability). All148 actual inference response records are claude-opus-5-5; the additional synthetic record is the API error, not another model. Native written verdict PASS_M5_MAIN_FUNCTIONAL and Codex acceptance rest on inspectable completed evidence, not process success. No further API retry, settings change or automation was started. Future native Claude work waits for account availability; current documentation/independent acceptance can finish locally.

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

## Execution, failures and acceptance

Native Claude Code2.1.301 and installed RTL Agent Team0.14.6 actually ran the focused verification and implementation/verification workflows. All inspected root/subagent response models are `claude-opus-5-5`, with explicit invocation-local high effort and route `claude/claude-opus-5-5`; global service/settings preserved. Native sessions `49e427c2-a597-447d-b40b-a8ece8c67d92`, `d14dce3f-1edc-44a4-bc34-ba8319dc7b19` and `b10049ae-345e-4f26-8930-b6b83e1caf8e` cover long-run preparation and the narrow TB repair. Final installed `rtl-agent-team:func-verifier` review session: `19094c25-e5cc-4189-a1af-68113637ad07`.

Claude authored RTL/models/TB/runner and the exact eight-stage batch script. Detached native launches failed before batch startup; failed launch evidence is preserved. Codex then executed that same native-authored script in foreground WSL, exit0, and independently audited original JUnit, metrics, exact scope gates and source hashes. Final native func-verifier reviewed the completed evidence; it did not personally execute the long batch. Codex did not substitute as RTL/TB author.

The first full stress attempt `20261017T010035Z_1025` executed9 cases (7FAIL/2PASS;21NOT_RUN). Failures were the summary assertion that incorrectly required a full-FIFO closing measurement fire's next-cycle-ready observation to remain inside the frozen measurement snapshot. The first drain cycle owns that observation. Claude's source `cefbbb0` repairs only TB accounting, adds directed case19 and updates the pinned collection/report. The repair asserts exact measured-plus-observed-boundary-owed and exact whole-run relations, including actual first-drain ready/held-push/descriptor checks. No RTL/model/shared-helper/trace/Spec change or arbitrary off-by-one tolerance. Original failed logs remain preserved. Fixed-seed510 six simulations passed, but their subset gate correctly failed; only the later full30 is accepted.

Evidence roots (ignored raw files stay local): `artifacts/implementation/<scope>/<run-id>/` contains summary/logs/raw JUnit/metrics. `.setup-logs/implementation/resume-20261017/m5-long-regression-2/` contains exact batch commands/exits, all144 tracked-file launch hashes, native provenance and Codex `stress-audit.json`, `primary-audit.json`, `production-audit.json`, `batch-audit.json`. The source stayed unchanged through the complete batch. Unit independent audit is in `m5-stress-boundary-repair/codex-review/independent-m5-verdict.json`. Native final review logs/diff/manifest are in `m5-final-review/`.

Native final evidence review: [M5-integration-results](M5-integration-results.md) and [functional verification](../../reviews/phase-5-verify/M5-functional-verification.md). Independent acceptance: [Codex review](../../reviews/phase-4-rtl/codex-fai-main-review.md). No unresolved correctness-critical contradiction was found within this functional scope.

Algorithm-2 is NOT_STARTED, remains a separate approved interpretation, and follows the primary nine synthesis experiments. No IEEE PDF inspection or cycle-identical paper reproduction is claimed; Main four-state hysteresis and the shared one-output10/10 alternation follow the approved project specification. Multi-output/APR/optional extensions remain deferred.

All nine FastX synthesis/STA/power/PPA configurations are NOT_RUN. SSH/tool/license access is NOT_VERIFIED; the registered-adder smoke is user-reported environment evidence only. Existing remote templates need reviewed N/policy parameter selection and a frozen pilot-derived common methodology before the sweep. Formal/CDC/SystemC/UVM, numerical coverage and RTL mutation campaigns are NOT_RUN/deferred, not PASS; prior14 model mutants do not establish RTL coverage. Strict Verilator checks passed; the earlier default Verible style conflicts remain separately recorded.

## Historical checkpoints (superseded)

The following is retained verbatim as historical evidence, including its then-pending states and quota errors. It does not describe current acceptance.

# M5 Main FAI — unit verified, long regressions pending

Date:2026-10-17 (Asia/Taipei). Source `db96961935060fe4ccac686fc9c0fe1b277e38f0`. Approved v1.0 at1af80967bbc2fb83224f4725c4fb450889e69c62 unchanged. **PARTIAL_UNIT_VERIFIED_LONG_REGRESSIONS_PENDING**; complete M5 integration is not accepted.

## Current M5 checkpoint 2026-10-17 (Asia/Taipei)

**M5 PARTIAL_UNIT_VERIFIED_LONG_REGRESSIONS_PENDING**, source `db96961935060fe4ccac686fc9c0fe1b277e38f0`. Native Claude Code 2.1.301 / RTL Agent Team 0.14.6 actually invoked `/rtl-agent-team:rtl-p5s-func-verify M5-verify-resume`, session `1b78e4d1-9fc8-4c5d-a586-7d28154d2dca`. Root, p5s-func-verify-orchestrator and serial testbench-dev all returned `claude-opus-5-5`; high effort was explicitly configured. The TB/runner are now implemented and the M5 unit scope passed; the complete M5 integration gate is not accepted yet.

Claude final M5 `20261016T193753Z_5024` and independent Codex final M5 `20261016T194435Z_363` each PASS **775 tests = 196 reference + 39 TB-helper pytest + 540 cocotb** (18 cases x N4/8/16 x W64/256 x seeds509..513), zero failures/errors/skips. Each also passed27 strict lint configurations and9 structural probes, plus3 Algorithm-2 expected rejections (not simulation tests). Codex parsed raw JUnit and confirmed source hashes stable during its final run. All RTL, models and frozen Spec are unchanged in this continuation.

Registered but NOT_RUN: full M5-stress30 (W64 400k/W256 800k cycles), M5-primary60 (100k cycles, exact tracked FCFS/RR intended hashes), M5-production3 (each20million real non-reset cycles =4 windows), current full M1-M4/q1 regression and final func-verifier. Smoke runs are labelled INFRA_SMOKE_PASS and never full-scope acceptance. N16 production-harness smoke300k/2million cycles passed with0windows; the2million run observed2856.3cycles/s and49184KiB peak RSS. Offline model-only stress planning reached16/16 transitions in30cases; it is not RTL stress evidence.

The testbench-dev then returned actual HTTP429/session limit, reporting **2026-10-17 08:00 Asia/Taipei** reset (CLI estimate). Codex stopped only this matching task CLI after the error; wrapper4294967295 (Windows -1), not natural success. No final verifier launched and no full long run remains active. No repeated quota probe, authentication/settings/service change, substitute RTL author or new architecture decision. Source/logs/native transcripts/full patch/hashes: `.setup-logs/implementation/resume-20261017/m5-verify-resume/checkpoint/`. Next task is native final-verifier long regressions after availability; see docs/RESUME_CLAUDE.md and docs/phase-5-verification/M5-results.md.

Primary functional matrix remains120/180 (60FCFS+60RR); FAI60 and all nine PPA results remain NOT_RUN. Prior M1-M4 acceptance remains for its recorded source. Algorithm-2 stays separate.


## Current files and verification limits

Eight source files changed: scripts/run_verify.py; sim/common/switch_fai_tb.py; sim/common/tests/test_fai_stream.py; sim/switch_top_fai/{fai_stream.py,test_switch_fai.py,test_switch_fai_primary.py,test_switch_fai_stress.py,test_switch_fai_production.py}. All RTL/model/spec and accepted common/FCFS/RR helpers remain unchanged. No policy-dependent buffering or timing change. New FAI harness hooks provide an opt-in FCFS oracle mirror for pre-classification primary runs and trim append-only informational model logs for long runs without changing model decisions.

Unit tests exercise actual RTL at both stress windows/N4/8/16, all16 literal Main transitions, exact thresholds/widths, closing fires, retained class/quota across stalls/boundaries, resets, visits/empty classes/no banking, FCFS ties/wrap, full-plus-pop/no bypass/105-bit fields and C1 input-hold/drain/response conservation. Twenty-seven strict lint configs, nine structural probes and three separate ALG2 expected rejections passed. Raw JUnit counts independently audited. Numerical coverage, RTL mutations and production behavior are not inferred from unit checks.

Failure preservation and repairs: initial missing run_trace import (NameError); short-random W256/N4/seed510 UP=0 was an unjustified per-seed coverage assumption for the unchanged saturation-heavy common trace. Final test records UP but relies on mandatory directed all16/threshold tests and requires all16 in each full stress run. All every-cycle assertions remain. Original failures/diagnoses: testbench-dev/initial-failures/ and codex-review/initial-failures.json. Stimulus v2 window-aligned flip phases and400k/800k lengths were chosen using offline oracle planning; neither planning nor shortened smoke is RTL stress acceptance.

Production smoke is N16 only, not N4/8 production evidence. The longest smoke reached2million cycles with0windows,2856.3cycles/s and49184KiB peak RSS. This is an observed memory/throughput sample under concurrent work, not a bound or a guaranteed full-run duration. Full production is20million cycles perN with an8-hour timeout; plan bounded parallel simulator processes and preserve every-cycle checking. No time skips or internal FAI-state deposits.

No final func-verifier launched before the new quota error. Current full stress30, primary60, production3 and full post-change M1-M4/q1 are NOT_RUN; only older accepted-source regressions and this continuation's lint-only controls exist. No PPA or Algorithm-2. See docs/RESUME_CLAUDE.md for focused next invocation.

## Historical 2026-10-16 checkpoint (superseded by current section)

# M5 Main FAI checkpoint â€” PARTIAL_RTL_MODEL_TB_DRAFT

Date2026-10-16 (Asia/Taipei). Frozen approved Spec v1.0 `1af80967bbc2fb83224f4725c4fb450889e69c62`, unchanged. Partial source `91bf36f84bff7ad5251a8414509191c3f39f26ab`. Main FAI is not functionally accepted.

## Actual delegation and interruption

Native CLI2.1.301/plugin0.14.6 actually ran `/rtl-agent-team:rat-p4p5-impl-verify M5-fai-main`, sessionf9056d2a-3e38-41e7-814f-31cb921d35c3. Serial foreground Opus agents: uarch-to-verify-orchestrator aa98846661be49424, rtl-coder a3435f3283b780246, testbench-dev model a2c530d3b3b472686, then testbench-dev TB/runner a38ba5a9bd2d7cee7. Codex verified actual returned model IDs are claude-opus-5-5 throughout; invocation --effort high and session-local settings were explicit. Global settings/service were preserved. The model stage's long API wait eventually returned normally.

The TB/runner stage then returned **HTTP429 session limit**, reporting2026-10-16 at19:20 Asia/Taipei reset (CLI estimate). Codex stopped only this task's CLI after that actual error, preserving partial work and avoiding quota retries; wrapper exit-1. This is not a successful completion or a permission/OAuth failure. No final func-verifier launched. Monitor permission denial was an optional orchestration tool earlier; ordinary Read/Bash fallback worked and did not block implementation. No permission workaround or extra install.

## Files and boundaries

| Files | Actual state |
| --- | --- |
| docs/phase-3-uarch/fai_main.md | Main implementation derivation; no Spec change. |
| rtl/common/cxl_fai_main_sched.sv | Main H/B_H/L/B_L policy, one masked shared FCFS selector, window counters/class visits. |
| rtl/top/switch_top.sv and two filelists | Main branch, FAI_W default5million/stress64/256, 5-bit held class/used context only for Main. |
| refc/cxl_model/fai_main_model.py / __init__.py | Abstract class names/unbounded counters/absolute arrival order, isolated context encoding; exports. |
| refc/tests/test_fai_main_model.py |103 new model tests, passing after random-duration correction. |
| sim/common/switch_fai_tb.py | Draft every-cycle oracle + independent pin/history/window/class/visit/105-bit/hold/response checks. NOT_RUN. |
| sim/switch_top_fai/test_switch_fai.py |18 drafted directed/short-random tests, no simulation execution. |
| scripts/run_verify.py | Partial helpers,196 model count, only ALG2 unsupported list; M5 registration and older Main positive-control wiring unfinished. |

Common descriptor FIFO/output hold/FCFS selector/RR/package remain byte-identical to the accepted baseline; no pipeline/bypass/buffering/debug ports. Main uses 5-bit opaque context; FCFS/RR retain1-bit. Production B/S/index23-bit and zero-extended unsigned32 threshold operations; all-source average, fire-only window counts/closing inclusion and no independent window quota reset. Algorithm-2 remains unsupported. This is static/source evidence, not mapped area or behavioral acceptance.

## Actually executed checks

| Check | Result | Evidence |
| --- | --- | --- |
| Native Main lint and simulation-build elaboration | Final PASS; no functional simulation | rtl-coder command logs49-95; required Main top/standalone windows/N and controls. |
| Codex independent strict Verilator | PASS27 configs,0diagnostics | codex-review/lint/audit.json:18 Main top/standalone(N4/8/16 xW64/256/default5m) +9FCFS/RR controls. |
| Claude new Main reference pytest | PASS103,0failure/error/skip | testbench-dev/02.xml,02-fai-model-pytest.log. |
| Claude all reference pytest | PASS196 =93prior +103Main | testbench-dev/05.xml,05-refc-all-pytest.log. |
| Codex independent all reference pytest | PASS196,0failure/error/skip | artifacts/independent/m5/model-review/pytest.xml; source-hashes.json. |
| Model-only mutation checks |14selected mutants killed | testbench-dev/04-fai-model-mutation-check.log; not RTL mutation/coverage. |
| Python AST / actual WSL runner --list | PASS infrastructure only | Six changed Python sources parse; runner-list.log exits0 but shows no M5 entry. |
| FAI cocotb / long stress / primary60 / real production3windows | NOT_RUN | No M5 summary/result directory exists. |
| Current post-M5 common/FCFS/RR full regression / final func-verifier | NOT_RUN | Old accepted-source results retained, no new full acceptance inferred. |
| Synthesis / STA / power / FastX scheduler | NOT_RUN | No remote invocation. |

Failures preserved: native simulation-build elaboration initially reported a structural combinational-cycle warning when eff_low shared an always_comb with fire-dependent expressions. Splitting candidate-state computation from fire-dependent terms fixed it; final strict lint/elaboration passed with no suppression. Default Verible style exits1 on project convention differences (including preexisting L_ naming); it is not claimed PASS or a new waiver. Initial Main pytest100PASS/3FAIL missed a random relinquished-visit event. Claude doubled randomized windows (400 atW64,120 atW256), retained the event assertions and all deterministic cases; final103PASS. Mutation helper search-pattern bug was repaired before final14/14 model-only result.

No skipped/xfail/suppressed requirement or RTL-functional PASS is claimed. The model magnitude/width tests are arithmetic-only, not production-cycle evidence. Partial runner helpers are not a completed milestone. Existing100k primary traces under W5million would remain allH and therefore match FCFS, so separate real three-window tests are mandatory.

## Independent review and resume

Codex bounded static/model review found no new correctness-critical Spec contradiction; it is not M5 hardware acceptance. See reviews/phase-4-rtl/codex-fai-main-review.md. Finish existing TB/runner via native Opus5.5/high after account availability, then meaningful cocotb/unit/stress, applicable regressions, primary60 exact hashes and >=15million real non-reset cycles perN. No time skip/preload/smaller-W production substitute. Preserve logs and independent review before acceptance. No new owner architecture decision is needed.

Evidence root: `.setup-logs/implementation/resume-20261016/m5-fai-main/`. Original prompts/settings/stream/stderr/native transcripts/quota text/full patch/source hashes preserved in checkpoint/. Independent partial code/source review artifacts are in codex-review/. Approved M1-M4 remains intact in Git; global setup/spec/credentials untouched. Current matrix120/180; all nine PPA measurements NOT_RUN.
