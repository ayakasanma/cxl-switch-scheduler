# Codex independent common-framework review

## Current acceptance 2026-10-16: M1-M4 ACCEPTED

Authority: frozen approved Spec v1.0 `1af80967bbc2fb83224f4725c4fb450889e69c62`. Verified RR testbench/runner source: `75270b8808946e880ca039a2fa06b629dff32cd8`, with unchanged RTL `e727eba` and oracle `d09db33`. **Common/FCFS/RR gate before FAI: ACCEPTED.** No correctness-critical contradiction, new architectural choice or waived failing requirement remains. FAI/PPA are outside this bounded acceptance and have not started.

Codex independently reviewed the package/FIFO/hold/top wiring, FCFS/RR selectors and state, abstract oracle, model-free pin scoreboard, literal directed scenarios, runner source diff and actual evidence. Claude Code is the author/verifier; Codex authored no RTL or verification harness in this continuation.

### Architecture and policy correctness

- The single switch_top reuses N identical D16/full105 descriptor FIFOs and one cxl_out_hold. No policy-specific stage, bypass, buffering, input-ready dependency or memory sink was added. Common FIFO/hold RTL and FCFS behavior are unchanged.
- FIFO readiness uses beginning occupancy, full-plus-pop refuses, empty pushes become eligible next cycle; all105 bits/source/FIFO order are checked on every offered descriptor. Reset suppresses handshakes, clears control and starts a TB epoch.
- Shared hold latches offered source/context only on stall and retains it until fire/reset. The FIFO head remains stable because it cannot pop before that fire; continued input pushes cannot preempt it. No extra descriptor register or altered transfer timing is introduced for RR.
- RR resets polling0; the circular candidate depends on beginning heads, not same-edge ready/push/fire. Only actual granted-source fire consumes quota. Post-edge occupancy includes accepted replacement pushes, and expiry advances even with replacement. Stalls leave quota unchanged; all-empty retains polling. Directed expectations prove Q10/Q1 exact service sequences, skipped-source initial polling state, final-head replacement/late arrival, held-candidate mismatch and single-source renewal.
- RR has no arrival counter, timestamp bank or FCFS selector in actual generated models. FCFS controls at each N show those structures present, while descriptor and common hold state remain present in both. This is structural simulation evidence, not mapped PPA.
- The oracle represents an abstract open Turn/poll and queues, not RTL register expressions. Its model-free companion uses observed pin history; literal manually specified sequence tests independently constrain the common interpretation. Input hold, drain, conservation and TB tag-response methods are the accepted C1 implementations reused unchanged. Responses never drive quota/state.
- Runner changes strengthen positive RR lint and reference-test count pinning, preserve FCFS tests and strict diagnostics, and retain exactly6 unsupported FAI XREJECT. RR primary scope requires the full60 matrix/length/schema/policy/quantum/hash record and rejects seed overrides. Refactored common build flags remain equivalent; no suppression/xfail/skip/waiver.

### Independently executed and audited evidence

| Scope | Evidence | Result |
| --- | --- | --- |
| Codex full RR Q10 | M4/20261016T014545Z_7139 | PASS311 =93 model pytest +23 utilities +195 cocotb (13 x3N x5seeds). |
| Codex full RR Q1 | M4-q1/20261016T014656Z_8457 | PASS195 supplementary cocotb, separate from primary nine. |
| Claude native RR primary | M4-primary/20261016T013811Z_371 | PASS60, N4/8/16 xseeds509..528 x100000 measured cycles =6million; scope gate PASS. |
| Claude current FCFS primary | M3-primary/20261016T014224Z_3877 | PASS60; all60 full metric JSONs equal accepted C1 run20261015T175309Z_4038, excluding wall time. |
| Claude current M1/M2/M3 |20261016T012805Z_2386 /012826Z_2985 /012919Z_4752 | PASS183/423/431. Increased shared reference pytest counts are not new hardware coverage. |

Codex parsed raw XML case counts and actual random_seed properties (not summaries alone), all final exits, strict diagnostic logs and generated structural controls. No final failures/errors/skips or build relaxations. The expected FAI rejections have zero tests and are excluded from totals. Repeated scopes are not distinct coverage.

Every RR trace hash and complete trace object matches FCFS at all60(N,seed) pairs. Measured pushes/fires/waits/censored counts, per-source service, backlog, response completion and516 drain-only requests reconcile in every run. All60 FCFS current metric JSONs equal the accepted C1 baseline except wall time; all60 RR per-source service vectors differ from FCFS. Identical aggregate totals under the shared saturated ready trace are recorded observations, not a fairness/throughput/PPA conclusion.

Exact source SHA256 stayed unchanged throughout the Codex reruns. Evidence: ignored `.setup-logs/implementation/resume-20261016/m4-verify-opus-high-2/codex-review/` (`audit.py`, audit.json, fcfs-comparison.json, independent command logs/exits and source-review-start.json). Full native prompts/stream/agent transcripts/task patch/model fields/source hashes: sibling checkpoint/. Durable native review: reviews/phase-5-verify/M4-functional-verification.md; metrics/results: docs/phase-5-verification/M4-results.md.

### Failure handling, limitations and next stage

Authoring failures were incorrect test expectations, not cycle-level RTL/model disagreement: polling remains at2 before circularly selecting0; Q1 reaches expiry even on an emptying fire; N4/511 did not randomly reach a wrap bin under saturation. Repairs retain deterministic mandatory wrap/mismatch/renewal checks and all per-cycle assertions. Failed runs are retained. A seed509 primary smoke correctly fails the full-matrix gate; it is not claimed acceptance. Launch-only path/CRLF issues and a verifier-only tabulation key error were fixed separately before relevant final checks. No failing requirement was waived.

Nonblocking limits: some primary stimulus bins refer to whole-run coverage including drain, while reported measurement metrics stay separate; saturation/backlog and finite-run assumptions are labelled. Numerical coverage, mutation, formal/CDC/SystemC/UVM and all synthesis/STA/power remain NOT_RUN. M3-primary TSV equivalence was independently audited rather than newly pinned in its gate. A scope-audit exception can leave a RUNNING summary, which is never accepted as PASS. These limits do not constitute scheduler results or extra tests. No mutation campaign was added without a concrete concern; literal directed cases and cycle checks were inspected.

Actual successful native session2822abc6-fe5c-4052-9a4c-cf37e0cd5fd1 completed exit0, serial orchestrator -> testbench-dev -> func-verifier. Codex verified root and allthree agents' returned model fields are `claude-opus-5-5`; CLI and invocation-local settings explicitly request high effort. Two earlier model mismatches were stopped before tracked edits; the existing service's supported namespaced route corrected selection without global configuration change. No current OAuth/quota/safeguard block remains.

Next planned development milestone: Main FAI under the already approved contract, followed by its stress/production/primary tests. This continuation stops at the completed RR/common gate. Primary functional progress is120/180 (FCFS60+RR60; Main FAI60 pending); all nine synthesis measurements remain NOT_RUN. Algorithm-2 remains a separate later supplement. No fresh architecture approval is needed.

## Historical review checkpoints (superseded where noted)

Reviewer: Codex,2026-10-13 (Asia/Taipei). Authority: approved v1.0 at 1af80967bbc2fb83224f4725c4fb450889e69c62. Scope: completed Claude-authored M1/M2 and October15 partial M3 RTL/model; no review of unimplemented RR/FAI.

## M1 verdict: PASS_M1

Reviewed package packing, FIFO descriptor/pointer/occupancy and optional timestamp generate branches, abstract Python deque model, independent pin-handshake scoreboard, directed/random tests and fail-fast runner. FIFO ready uses beginning occupancy, simultaneous updates conserve count/order, empty push cannot pop/bypass, sync reset clears control, all105 bits are preserved. TS-disabled elaboration contains no timestamp memory; TS-enabled control contains it. No unused RR bank is asserted as a complete-policy result.

Observed independent strict FIFO lint and complete M1 rerun20261013T004258Z_375:110 tests,13 steps, no failure/error/skip. Failures in earlier runner trials were repaired and retained. No unresolved M1 correctness finding; broader integration/production-policy acceptance remains pending.

## M2 verdict: PASS_M2 (common control only)

Reviewed the final shared hold controller, switch shell and fixture wiring, abstract model, pin-level invariants/scoreboard, directed/random tests and runner. Codex independently ran full M2 at artifacts/implementation/M2/20261013T063859Z_367:367 tests (37 Python +330 cocotb), zero failures/errors/skips; six strict lint configurations pass, no relaxation. Twelve intentional unsupported-policy rejections are separate XREJECT checks with zero simulation tests. Test seeds509..513; N4/8/16, context widths1..6 and FIFO metadata option exercised as documented in docs/phase-5-verification/M2-results.md. M2 source checkpoint: 7febabbb67584c0d5df65e8e77394127abfd8422.

The controller explicitly retains held validity until fire/reset, latches source/context on the first stalled offer and takes data directly from the existing head. Real FIFO integration tests assert the held head stays valid/stable, allow continuing pushes during stalls and verify full-plus-pop refusal, no bypass, next-cycle eligibility and back-to-back transfers. The sim-only fixture reproduces common top wiring without a scheduling policy or new stage. The Python model is deque-based with an optional grant record; additional model-free pin/scoreboard checks prevent agreement alone from hiding a bug.

Correction to prior review: the claimed missing fifo_count_t/ts_t aliases were already present at M1 commit d0f2989 (package lines30-31). That earlier finding was erroneous and is retracted; no alias code or Spec change was needed. The actual held-release/comment follow-ups are now implemented/tested. Non-fire reset/window/counter-clear/empty-visit updates remain allowed as specified; no extra window quota reset is authorized.

## Historical remaining gate

M3 is now COMPLETE_M3 and C1 CLOSED after October16 correction/independent reruns (see codex-fcfs-review.md). M4 RR RTL is PARTIAL_RTL_LINT at e727eba, with no model/cocotb yet. switch_top supports FCFS/RR at elaboration and rejects FAI; FCFS simulation accepted, RR functional verification pending. Common-framework acceptance before FAI remains NOT_COMPLETE until FCFS/RR independent models, N4/8/16 integration and required directed/random checks pass. No new correctness-critical Spec contradiction or owner architecture decision found.

M3 must complete actual FCFS functional verification while retaining common timing/storage and update the M2 rejection registry so the supported FCFS branch receives strict positive lint instead of an obsolete rejection expectation. RR/FAl remain explicitly unsupported until their own milestones. M4 must omit all unused timestamp storage/counter/selector, preserve post-edge occupancy and held actual-fire accounting, and verify quantum10/quantum1. No synthesis/STA/power result is implied by M2.

## Historical October15 M3 static review: LINT_ONLY, functional gate open

Partial Claude-authored source99124df75bf28532760601414c62f4f376fc6b6c reviewed by Codex after the repaired-proxy run. Balanced comparator tree has valid-mask propagation and contiguous source ranges; right wins only when valid and left absent or right strictly older by unsigned width-limited subtraction. Ties retain the left, hence smallest source ID. Under the approved outstanding-age half-range bound this matches absolute arrival order. Invalid timestamps do not defeat eligible heads. This reasoning is static review, not a simulated wrap result.

The optional counter resets0 and advances every non-reset edge, including idle/stalls; FIFOs capture its pre-edge value. The same existing FIFO and common hold controller serve FCFS; their files/ports/behavior are unchanged. No extra storage stage, bypass or debug port. The added descriptor-vector type alias has no hardware state and enables standalone-selector strict lint without warning suppression. Independent strict selector/top lint at N4/8/16 passes six configurations; logs/audit artifacts/independent/m3/lint/.

No correctness-critical source contradiction was found in this bounded static review. Functional acceptance is NOT_COMPLETE: no independent FCFS model, producer/response scoreboard, cocotb/real-wrap/random test or primary60-run regression exists. Testbench-dev was interrupted before writing by HTTP429 weekly quota, reported reset2026-10-15 at15:00 Asia/Taipei. func-verifier was not invoked. No marker waiver or failed-test bypass.

Known integration bookkeeping issue: M2 runner still expects FCFS rejection despite its now-supported branch; the next Claude testbench task must update this to positive lint and preserve actual common-control cases and RR/FAI rejection diagnostics. M3's runner entry still correctly refuses unimplemented verification. Historical M1/M2 test counts are not new M3 evidence. Resume verification before RR; common-framework acceptance before FAI remains NOT_COMPLETE. See docs/phase-5-verification/M3-results.md and docs/RESUME_CLAUDE.md.

## Current M3 model review: PARTIAL_MODEL_UNIT, RTL acceptance pending

Claude model checkpoint7014a1e2ffa87f88050c68351aa6c63fc50ea2df reviewed by Codex. FCFS order comes from unbounded absolute push-edge times and source ID in deque heads; modular timestamps are separate storage observations and do not determine oracle selection. The model composes reviewed common queue/hold behavior. Reset/deposit controls and held grant rules are explicit. No RTL/spec or common FIFO/output change in this continuation.

Found/repaired model bug: commit initially advanced edge_index before the environment check. At allowed age2^31-1, view permitted a fire while commit incorrectly raised at2^31. Codex reproduced this failure independently. Claude moved the check before incrementing and added six regression cases. Claude and independent Codex final JUnit each contain54 tests (37 existing +17 FCFS),0 failure/error/skip; the original failing diagnostic now passes. Failure/fix evidence is retained in artifacts/independent/m3/model-review/ and archived native sessions. No unresolved version of this model finding remains.

Traffic generator is a draft with policy-independent seed/config inputs and a canonical hash; no integration acceptance is claimed for its producer/reset/drain behavior, tag responses or metrics. No cocotb selector/top/wrap/random run, primary60 FCFS matrix, M3 runner extension, M2 registry fix or final func-verifier acceptance exists. Two fresh native plugin workflows stopped in API safeguards reasoning_extraction after partial authoring; global settings unchanged and no Codex replacement RTL. The prior agent's no-pytest summary was inaccurate:48 tests ran before the model fix,54 after it. Current documentation corrects that distinction.

Common-framework gate before FAI remains NOT_COMPLETE. Next task is actual Claude cocotb/runner development and execution, then Codex independent functional review before RR. No new architecture decision, hardware performance/PPA result or verification waiver.

## Current M3 functional checkpoint: REVIEW_CHANGES_REQUIRED

Source7a81dc0182aef4df59ca5449688c38b45828e893 includes Claude M3 cocotb/runner work. Native func-verifier actually ran; raw372-test rerun and60 FCFS primary runs pass, independently audited by Codex. However independent diagnostic M3-review-boundary/20261015T101752Z_358 fails the Spec4 producer-hold assertion at measurement/drain transition. This is open C1 in reviews/phase-4-rtl/codex-fcfs-review.md. Fix pending input preservation, unconditional input pin hold checks and drain-only accept accounting, then rerun before RR. No RTL/spec/common-control change or demonstrated RTL mismatch. Raw passes are provisional and do not close the common-framework gate before FAI. Reported Claude session-limit reset2026-10-15 at21:40 Asia/Taipei; no waiver/fallback author. No owner architecture decision needed.

## 2026-10-16 M3 acceptance

C1 CLOSED at source07d12ca5b8e997d93a49c20c54c08b2bb55e9f9e: Codex full M3 PASS392, original boundary diagnostic PASS1, all60 corrected primary traces/measurement/accounting audited. Detailed verdict in codex-fcfs-review.md. M3 COMPLETE; M4 RR is next, and the full common-framework gate before FAI remains pending M4. No RTL/spec/model/generator change in the C1 repair.

## 2026-10-16 M4 RTL static review: PARTIAL_RTL_LINT

Reviewed partial RR sourcee727ebaae310a2a039ee2592f564f894f9668c2a. Shared FIFO/hold/FCFS selector unchanged. RR candidate is circular first valid from pointer and independent of same-edge handshake; only actualfire updates ptr/used, post-edge occupancy includes accepted replacement, expiry always advances. Actual held source accounting is used even when candidate changes. Q10/Q1 widths and power-of-two wrap reviewed. No new correctness-critical Spec contradiction found; this is static reasoning, not RR functional acceptance.

Codex independently PASS15 strict Verilator configs (RR standalone/top,N4/8/16,Q10/Q1 andFCFS controls), logs artifacts/independent/m4/lint/. Claude structural logs show absent RR timestamp bank/counter/oldest selector with FCFS-present control, and generated FCFS C++ equality vs preceding source. Scope/Verible style limitations in M4-results.md. The API stopped after rtl-coder and before model/testbench; root summary saying no lint was wrong. RR model/cocotb/primary60/final func-verifier NOT_RUN, current rejection registry stale. Common-framework gate before FAI remains NOT_COMPLETE; next task focused Claude M4 verification.

## 2026-10-16 RR model checkpoint: PARTIAL_MODEL_UNIT

Claude sourced09db3330ff8d59f4a1735d905ac3243b9e0efca adds independent abstract Turn/poll oracle +39model pytest. Codex read it and independently PASS93total reference pytest,0failure/error/skip; Claude RR-only PASS39. Closed-form preloaded drain and randomized service/conservation tests supplement directed turn/quota/replacement/held cases. No timestamp logic in RR model. RTL e727eba unchanged; no RR cocotb/runner/primary60 yet. This is model-unit acceptance only, not hardware signoff. HTTP429 session limit interrupted the actual testbench-dev workflow after these tests (reported2026-10-16 06:30 Asia/Taipei). Preserve current model and complete RR verification before the full common gate/FAI; no new architecture decision. Detailed evidence in M4-results.md.
