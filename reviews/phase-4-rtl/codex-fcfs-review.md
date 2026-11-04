# Codex FCFS independent review

Date2026-10-15 (Asia/Taipei). Frozen Spec v1.0:1af80967bbc2fb83224f4725c4fb450889e69c62. Reviewed source7a81dc0182aef4df59ca5449688c38b45828e893; RTL99124df unchanged; Python model7014a1e unchanged. Historical verdict at7a81dc0: REVIEW_CHANGES_REQUIRED. Superseded by the October16 C1 closure below.

## Observed evidence

Actual native Claude session1674e596-4f46-44d3-a0d6-24b6426e67b4 invoked rtl-p5s-func-verify, with serial foreground testbench-dev and func-verifier. The API later returned HTTP429 session limit, reported reset2026-10-15 at21:40 Asia/Taipei. No current reasoning_extraction error, global configuration change, permission denial or verification waiver. CLI exit1 is distinct from completed simulation results.

Codex read the model, selector/top wiring, trace/producer/response code, directed/primary tests and runner. The independent absolute-time oracle and pin-history ordering checks do not reproduce the modular RTL comparator. Tests exercise real counter wrap by internal VPI deposit, source ties, shared hold/FIFO behavior, reset and full105-bit integrity. RTL/spec source diffs remain empty against their checkpoints. No RTL mismatch was found by the existing tests.

Codex independently parsed raw JUnit, test counts, seed properties, simulation process exits, strict positive lint logs and primary metrics accounting:

| Recorded run | Raw result |
| --- | --- |
| M3/20261015T101013Z_277, Claude func-verifier rerun |372 tests,0 failure/error/skip;47 steps (38 PASS +9 XREJECT). |
| M3/20261015T100746Z_3720, testbench-dev |Same372-test scope. Repeated runs are not distinct coverage. |
| M3-primary/20261015T100412Z_272 |60 distinct N4/8/16 x509..528 runs,100000 measured cycles each;6million measured cycles,0 test failure/error/skip. Provisional because of C1. |
| M1/20261015T100009Z_2120 |144 =54 Python +90 FIFO cocotb;0 failure/error/skip. More Python cases do not imply more FIFO RTL coverage. |
| M2/20261015T100022Z_2712 |384 =54 Python +330 common cocotb;9 FCFS-positive/common lint and9 separate RR/FAI XREJECT;0 failure/error/skip. |

M3's372 =54 reference pytest +18 trace/response pytest +105 selector cocotb (7x3Nx5seeds) +195 top cocotb (13x3Nx5seeds). XREJECT contributes zero tests. The primary JSONs account for generated/push/fire/drain/response counts and exact measured duration. Hashes are recorded; producer backlog is explicitly reported. Existing primary metrics are not final comparative performance conclusions.

## C1 [P2]: offered input is withdrawn at measurement/drain boundary

Affected source: sim/common/switch_fcfs_tb.py, run_trace() and drain(), at source7a81dc0. run_trace ends measurement then calls drain() with no pushes. If the last measured cycle has in_valid=1 and in_ready=0, the first drain cycle drops valid and descriptor before push/reset, violating Spec4's producer hold contract. The harness currently checks output hold but does not assert the corresponding input hold across all phase boundaries. Counting a request as generated-but-unaccepted does not authorize withdrawing an already offered descriptor.

Independent actual Verilator/cocotb reproducer: fill source0's D16 FIFO with ready0, continue offering a pending request, then call run_trace's drain. A wrapper checks every previously blocked source keeps valid/data. Strict lint passes; the single diagnostic test fails at cycle22: `SPEC4 input hold violation ... source0 valid withdrawn before push/reset`. Raw evidence: artifacts/implementation/M3-review-boundary/20261015T101752Z_358 (1test,1failure,0error/skip). Diagnostic files and command are ignored under .setup-logs/implementation/resume-20261015/cocotb-resume-1/codex-review/. The first diagnostic launcher attempt had no lint configuration and was rejected by the runner; after adding strict lint it reaches the intended assertion. No project RTL/test source was changed for this independent diagnostic.

The real primary boundary is also relevant: N4/seed509 ends with ready0,64 accepted requests in FIFO storage and21274 generated-but-unaccepted requests. The trace policy therefore cannot assume all producer offers have been accepted at the boundary.

Required focused Claude repair:

- Track input valid/data stability from observed pins across every non-reset cycle, including entry to and completion of drain. Keep that assertion active; fix any directed-test stimulus that violates it.
- Preserve the per-source request already offered and blocked at measurement end until it pushes. Then stop releasing further unoffered producer backlog, or drain all pending producer traffic with explicit bounded accounting. Choose the smallest contract-preserving approach; no RTL architecture change is needed.
- Keep measurement push/fire/rate/wait statistics frozen. Record drain pushes separately, distinguish requests accepted during measurement from drain-only accepts, and snapshot generated-but-unaccepted at the measurement boundary. Resolve all tag responses exactly once without mixing sample populations.
- Add a deterministic boundary regression (full FIFO, pending valid, measurement ends), and reuse the independent diagnostic. Rerun relevant M3 tests and full60 primary matrix on corrected harness; verify intended trace hashes remain identical.

This is an open verification/stimulus defect, not a demonstrated scheduler RTL defect. Raw existing passes survive as evidence, but Codex acceptance and the gate before RR remain open.

## Nonblocking observations

The primary profile is strongly saturated (Claude review F1). Keep its existing traces as a saturation/backpressure workload; label finite-run generation-to-acceptance metrics and backlog accordingly. Spec fixes no load level, so this needs no new architecture approval and is not grounds to silently retune primary hashes. Any future separately named lighter profile can be evaluated later.

The60 recorded primary trace hashes are copied verbatim into reviews/evidence/M3-primary-v2-trace-hashes.tsv for durable cross-policy comparison. M4 should compare intended hashes against this record, not only regenerate using whichever generator version is current. No new mandatory mutation/coverage threshold is introduced; none was measured. The future-exception RUNNING-summary limitation noted by func-verifier is recorded and does not create a false PASS.

All nine-configuration PPA, FastX scheduler synthesis/STA/power, RR/FAI simulation, FAI stress/production windows and integrated180-run acceptance remain incomplete/unrun. No owner architecture decision is needed for C1; continue the authorized Claude repair after account availability.

## 2026-10-16 independent acceptance: C1 CLOSED, M3 COMPLETE

Reviewed corrected source07d12ca5b8e997d93a49c20c54c08b2bb55e9f9e. Claude native session65bc0850-526f-4996-bcac-e271a535cb2e actually delegated serial testbench-dev then func-verifier and returned CLI exit0. Owner reauthentication repaired the initial expired-OAuth attempt; no global settings/route changes. Source scope is TB/runner only; RTL99124df, Python oracle, approved frozen Spec1af8096 and generator/response code unchanged.

The always-active InputHoldChecker reads observed input pins each cycle, including phase transitions. drain keeps only refused offers until accepted, adds no new unoffered backlog, and terminates with no obligation. run_trace snapshots measured counts and separates drain-only push/fire/wait/generation populations and responses. A deterministic two-full-source boundary test asserts literal expected counts and push edges, and five pure checker cases test valid/data violations/reset/acceptance. No bypass/disable/skip/waiver introduced. Static review finds C1 repaired without architecture change.

Codex independently reran full M3/20261015T175123Z_363 PASS392 (54reference pytest +23trace/hold/response pytest +105selector cocotb +210top cocotb), zero failure/error/skip,47steps (38PASS +9 separate XREJECT), no warning suppression. The exact unchanged original failing diagnostic rerun M3-review-boundary/20261015T175123Z_362 now PASS1. Claude func-verifier separate M3/20261015T175152Z_1799 PASS392 and independent primary/20261015T175309Z_4038 PASS60 agree; testbench primary/20261015T174542Z_2220 also PASS60. Repeated runs are the same scope, not extra distinct coverage.

Codex audited raw JUnit counts/seed properties/process exits/positive lint and all60 primary metrics. All intended trace hashes equal tracked reviews/evidence/M3-primary-v2-trace-hashes.tsv; measured counts/rates/waits/generation/unaccepted snapshots equal old pre-C1 results. All516 drain-only pushes across60 runs have separate matching fires and responses; measured-accept wait population excludes them. No uncompleted request/response after drain. Independent audit .setup-logs/implementation/resume-20261016/c1-repair-2/codex-review/c1-audit.json and copied session/diff/hash manifest checkpoint preserve the evidence.

Verdict PASS_M3; C1 CLOSED. Authorized next milestone M4 RR in the same shared framework with identical intended traces, independent RR oracle and actual WSL tests; no new owner decision needed. Full common/FCFS/RR review before FAI still awaits M4. No FastX/PPA result or numerical coverage/mutation claim.
