# M3 FCFS functional verification results

## Codex project acceptance2026-10-16: COMPLETE_M3, C1 CLOSED

Corrected source07d12ca5b8e997d93a49c20c54c08b2bb55e9f9e. Codex independently reviewed the input-hold/drain-only repair, reran full M3 PASS392 and unchanged original boundary diagnostic PASS1, and audited all60 corrected primary runs/hash/accounting. Measured statistics and intended traces are unchanged;516 drain-only accepts are separately completed. See reviews/phase-4-rtl/codex-fcfs-review.md October16 closure. M4 RR may now begin. Earlier review/quota notes below are historical. No Spec/RTL/model/generator change or PPA result.


## 2026-10-16 C1 repair: independent func-verifier rerun (Claude). Codex acceptance still pending

Date: 2026-10-16 (Asia/Taipei). Run timestamps in the run IDs are UTC, so 20261015T17xxZ means 2026-10-16 01:xx Taipei. Tree: HEAD 764a074 plus uncommitted testbench-dev changes. No commit was made. RTL, spec, refc and the trace generator have no diff against HEAD. `git diff --stat HEAD -- rtl specs refc sim/common/traffic_trace.py sim/common/tag_response.py` is empty. The only changed source files are the harness and the runner. Codex independent acceptance of C1 is still pending, and M4 (RR) must not start until Codex accepts.

### Repair under test (testbench-dev; func-verifier reviewed it and did not change it)

- `sim/common/input_hold.py` (new) adds `InputHoldChecker`, a pure-Python Spec 4 producer-hold checker with no enable switch. In a non-reset cycle, a request with in_valid[h]=1 and in_ready[h]=0 creates an obligation for the next cycle: valid=1 and an identical 105-bit descriptor. The obligation repeats until the request is pushed or a reset cycle occurs. A reset cycle releases all obligations and creates none.
- `sim/common/switch_fcfs_tb.py`:
  - `cycle()` calls `_input_hold_check` on every cycle of every test, including bring-up reset, measurement, drain entry, drain, the drain-completion idle and the response wait. It does this before the model and pin checks.
  - The check reads `rst_n`, `i_in_valid` and `i_in_desc` back from the DUT pins and asserts that they equal the driven values. It steps the checker with the pin values and with the sampled `o_in_ready`.
  - `drain()` drives only `in_hold.obligations()`. These are the descriptors that were already offered and refused. It loops while FIFOs are non-empty or obligations are pending, with a bound of n*(D+1)+8.
  - `run_trace()` snapshots the boundary obligations and asserts that each one is that source's producer head. A drain callback asserts that any valid seen in the drain belongs to a boundary-held source that has not been pushed yet. Nothing else is ever offered.
- `sim/switch_top_fcfs/test_switch_fcfs.py` adds `test_14_measurement_boundary_input_hold`, a deterministic C1 regression:
  - Two sources fill their D16 FIFOs while ready=0, and a third source has backlog that is never offered.
  - At the first drain edge the FIFO is full and pops, so the offer is refused. The boundary offers are then pushed at drain cycles +1 and +2 with identical bits.
  - The test checks the frozen measurement snapshot, the drain-only accounting and that responses are issued exactly once.
- `sim/common/tests/test_input_hold.py` (new) adds 5 pytest cases: hold until push, withdraw rejected, changed bits rejected, reset release, and no obligation after acceptance.
- `scripts/run_verify.py`: the expected switch tests per run went from 13 to 14, and the expected trace/util pytest count went from 18 to 23. No other runner change.
- The Codex diagnostic files under `.setup-logs/implementation/resume-20261015/cocotb-resume-1/codex-review/` are unmodified. Their mtimes are 2026-10-15 18:17:50 +0800, before the failing run 20261015T101752Z_358. The sha256 values were recorded before and after this rerun:
  - `run_boundary_diagnostic.py` 8fb97c49…0985
  - `test_input_hold_boundary.py` ab2c2d81…db63
  - The assertion is not suppressed.

### Drain accounting design ("hold the boundary offers, release nothing else")

Measurement metrics are snapshotted at the measurement boundary, and the drain does not change them:
- trace cycles 0..99,999;
- push/fire counts and rates (denominator = measured non-reset cycles);
- `per_source_*`;
- `generation_to_acceptance`;
- `wait_acceptance_to_fire` (measured-accept population only: `all_completed` = `fired_in_measurement` + `drain_completed`);
- `generated_but_unaccepted` (boundary snapshot, including the boundary-held offers);
- `coverage_measurement`.

Drain-only accepts are reported separately under `drain_only`:
- boundary-held offers and sources;
- pushes/fires per source;
- their own acceptance-to-fire and generation-to-acceptance stats;
- `unoffered_backlog_at_boundary` = `generated_never_accepted`.

Drain-only accepts are excluded from every measured population. `responses.issued == completed == fires_measurement + fires_drain + drain_only.fires`, and `issued_for_drain_only_accepts` is reported. The `input_hold` block reports the obligation checks for measurement and drain separately.

### Commands (log: .setup-logs/implementation/resume-20261016/c1-repair-2/func-verifier-commands.log)

All commands ran as `wsl.exe -e bash -lc 'cd /mnt/c/.../cxl-scheduler && source scripts/wsl_env.sh && …'`. No -Wno, waiver, skip/xfail or gate-marker reset was used.
1. `bash scripts/run_verify.sh M3`
2. `PYTHONDONTWRITEBYTECODE=1 python .setup-logs/implementation/resume-20261015/cocotb-resume-1/codex-review/run_boundary_diagnostic.py` (the unchanged Codex launcher)
3. `bash scripts/run_verify.sh M3-primary`
4. `python -I .setup-logs/implementation/resume-20261016/c1-repair-2/fv_compare_primary.py artifacts/implementation/M3-primary/20261015T175309Z_4038`. This is func-verifier's own comparison. It reads the raw JUnit XML and the per-run metrics JSON; it does not use summary.json.

### Results (func-verifier independent rerun, artifacts/implementation/)

| Run | Raw result (independently parsed JUnit) |
| --- | --- |
| M3/20261015T175152Z_1799 | PASS. Strict lint 6/6 PASS; 9 XREJECT (0 tests, not counted). pytest 77 = 54 refc + 23 trace/util/input-hold. cocotb 105 selector (7 x 3N x 5 seeds) + 210 switch_top (14 x 3N x 5 seeds). **392 tests, 0 failure / 0 error / 0 skip.** |
| M3-review-boundary/20261015T175255Z_3947 | Codex diagnostic, unchanged: strict lint PASS, **1/1 PASS**, 0 failure/error/skip. It failed at cycle 22 in 20261015T101752Z_358 before the repair. |
| M3-primary/20261015T175309Z_4038 | Strict lint 3/3 PASS, scope:primary_full_matrix PASS. **60 JUnit files, 60 tests, 0 failure / 0 error / 0 skip.** The `random_seed` property matches the file in every case. 60 distinct (N, seed) = N4/8/16 x 509..528 at 100,000 measured cycles each, **6,000,000 measured cycles**. Wall time 239.1 s. |

testbench-dev's earlier runs (M3/20261015T174434Z_380, M3-review-boundary/20261015T174531Z_2133, M3-primary/20261015T174542Z_2220) reported the same counts. The func-verifier runs above are a separate rerun, not a repeat count.

### Trace-hash and metric comparison (fv_compare_primary.py)

- Intended trace hashes (`trace.sha256` in each metrics JSON) match reviews/evidence/M3-primary-v2-trace-hashes.tsv for **60/60**. The runner's trace_hashes.tsv also matches 60/60.
- Measurement metrics vs the pre-repair run M3-primary/20261015T100412Z_272: **0 differences** over all 60 runs. Every key was compared except the new `drain_only`/`input_hold`/`responses` blocks, `phases` (drain cycle counts), `coverage_total`, `wall_time_s` and the note string. The comparison therefore covers rates, push/fire counts, per-source service, generation-to-acceptance, all wait-population stats, generated / generated_but_unaccepted, coverage_measurement and the trace summary.
- Full metrics JSON vs testbench-dev's post-repair run 20261015T174542Z_2220: 0 differences, excluding wall time. The results are deterministic.
- Per-run invariants asserted for all 60 runs:
  - drain_only pushes == fires == boundary-held offers, with at most 1 per source;
  - generated_but_unaccepted == boundary-held + unoffered backlog;
  - responses issued == completed == fires_measurement + fires_drain + drain-only fires;
  - all_completed count == measured pushes - dropped_by_reset;
  - outstanding_after_drain == 0.
- Aggregate over 60 runs:
  - 516 boundary-held offers: 516 drain-only pushes and 516 fires/responses;
  - 1,525,154 generated requests never offered and never accepted;
  - 48,607,548 input-hold obligation checks in measurement and 8,918 in drain;
  - 4,404,580 responses issued and completed exactly once.

### Func-verifier conclusion

C1 repair functional evidence: PASS (details and minor observations in reviews/phase-5-verify/M3-functional-verification.md, "C1-repair verification addendum"). This is not project acceptance. **Codex independent acceptance is still pending before M4.** RR/FAI simulation, FAI stress/W5M, the nine-configuration sweep and all PPA remain NOT_RUN.

## Codex acceptance checkpoint: REVIEW_CHANGES_REQUIRED

Reviewed source7a81dc0182aef4df59ca5449688c38b45828e893. Claude's raw M3 PASS372 and primary60-run results below are real, and Codex independently audited their JUnit/seed/exit/accounting evidence. They are provisional, not project signoff: Codex reproduced a Spec4 input-hold violation at the measurement/drain boundary. The producer drops a request's valid before push/reset. Independent actual cocotb diagnostic M3-review-boundary/20261015T101752Z_358 has1 failure at the intended assertion. See reviews/phase-4-rtl/codex-fcfs-review.md C1 for the concrete repair and required reruns. Do not start RR until C1 is fixed and independently reviewed.

Native session1674e596-4f46-44d3-a0d6-24b6426e67b4 actually ran testbench-dev and func-verifier, then stopped with HTTP429 session limit, reported reset2026-10-15 at21:40 Asia/Taipei. Global settings/RTL/spec remain unchanged; no waiver. The full primary trace hash record is preserved in reviews/evidence/M3-primary-v2-trace-hashes.tsv. Retain this saturated profile as a labelled workload; no new owner decision or silent primary-profile retuning is required. All PPA remains NOT_RUN.

## Claude reported status before Codex C1 review: blocks B-E pass

This section records the results from the M3-cocotb-resume session. The sections below it keep the
earlier PARTIAL_MODEL_UNIT and RTL-only checkpoints unchanged as history.

- Frozen spec: specs/CXL_SPEC.md v1.0 at 1af80967bbc2fb83224f4725c4fb450889e69c62. Source tree: HEAD b3459680ea3e47256faed05785005a91a3bb5636 plus uncommitted testbench/runner work (listed below). No commit was made.
- RTL under test: rtl/ is unchanged from 99124df (FCFS RTL checkpoint). The sha256 of every rtl/*.sv and filelist was the same before and after testbench-dev and func-verifier (.setup-logs/implementation/resume-20261015/m3-cocotb-resume/func-verifier/rtl-sha256-{before,after}.txt).
- Tools (WSL Ubuntu, sourced through scripts/wsl_env.sh): Verilator 5.052, Python 3.12.3, cocotb 2.1.0, pytest 9.1.1. Strict flags are the same as in M1/M2. SIM_BUILD_RELAXATIONS is empty. There are no -Wno-*, lint_off, skip/xfail or waivers.
- Claude functional verdict: PASS for its blocks B-E scope. Codex independent review subsequently requires C1 input-hold repair; project M3 acceptance is not complete and M4 cannot begin.

### Files written for M3 (testbench-dev; func-verifier only audited them)

New: sim/common/switch_fcfs_tb.py, sim/common/tag_response.py, sim/common/tests/test_traffic_trace.py, sim/cxl_fcfs_sel/test_cxl_fcfs_sel.py, sim/switch_top_fcfs/test_switch_fcfs.py, sim/switch_top_fcfs/test_switch_fcfs_primary.py. Modified: sim/common/traffic_trace.py (generator v2), scripts/run_verify.py (M2 registry update, M3 and M3-primary entries, full-scope gate). Committed earlier: refc/cxl_model/fcfs_model.py and refc/tests/test_fcfs_model.py.

### Commands

Every command ran as `wsl.exe -d Ubuntu --exec bash -c 'set -euo pipefail; cd "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler"; source scripts/wsl_env.sh; <cmd>'`:

- `bash scripts/run_verify.sh M3`
- `bash scripts/run_verify.sh M1` and `bash scripts/run_verify.sh M2` (regression runs after the registry/filelist change)
- `bash scripts/run_verify.sh M3-primary -j <N>` (testbench-dev, run_in_background)

### Acceptance runs (artifacts/implementation/)

| Run | Who | Exit | Steps | Tests | fail/err/skip | Notes |
| --- | --- | ---: | --- | ---: | --- | --- |
| M3/20261015T101013Z_277 | func-verifier independent rerun | 0 | 47 (38 PASS + 9 XREJECT) | 372 | 0/0/0 | 45.1 s; JUnit parsed independently: 32 XML files, 372 testcases, 0 bad. No %Warning/%Error/Traceback outside the declared-rejection logs. |
| M3/20261015T100746Z_3720 | testbench-dev, final tree | 0 | 47 (38 + 9 XREJECT) | 372 | 0/0/0 | Same independent parse result. |
| M3/20261015T095912Z_273 | testbench-dev | 0 | 47 (38 + 9 XREJECT) | 372 | 0/0/0 | Same independent parse result. |
| M3-primary/20261015T100412Z_272 | testbench-dev | 0 | 64 (3 lint + 60 cocotb + scope gate) | 60 | 0/0/0 | Wall time 198.0 s. Scope gate PASS, milestone_acceptance_scope=true. |
| M1/20261015T100009Z_2120 | testbench-dev | 0 | 13 | 144 | 0/0/0 | 90 cocotb + 54 pytest. |
| M2/20261015T100022Z_2712 | testbench-dev | 0 | 49 (40 PASS incl. 3 FCFS positive lint + 9 XREJECT) | 384 | 0/0/0 | |

M3 contents (372 tests): 6 strict lint (switch_top POLICY=0 and cxl_fcfs_sel, N4/8/16); 9 XREJECT steps (RR/FAI_MAIN/FAI_ALG2 at N4/8/16), counted as 0 tests; pytest refc/tests 54; pytest sim/common/tests 18; selector cocotb 7 tests x 3 N x seeds 509..513 = 105; switch_top FCFS cocotb 13 tests x 3 N x 5 seeds = 195. Each XREJECT log contains exactly the declared 10 diagnostics: 1 USERFATAL, UNDRIVEN cand_valid/cand_source/cand_ctx, and UNUSEDSIGNAL head_ts/fifo_count/push/grant_ctx/grant_held/fire. The runner enforces this set exactly. The func-verifier inspected it again.

### Primary random regression (M3-primary/20261015T100412Z_272)

- Scope: switch_top FCFS, N = 4/8/16 x seeds 509..528 x exactly 100,000 measured non-reset cycles, profile "primary", no warmup = 60 runs. Each run is followed by a separately reported drain/response-completion phase (93-300 cycles).
- Independent completeness audit (.setup-logs/.../func-verifier/audit_evidence.py, output audit-evidence.txt):
  - 60 metrics JSON files cover exactly the 60 distinct (N, seed) pairs.
  - Every run has requested_cycles = measured_cycles = 100,000, warmup 0, outstanding_after_drain 0 and dropped_by_reset 0.
  - In every run, responses completed = issued = fires = pushes, and generated = pushed + unaccepted.
  - Every source received service in every run. The minimum wait is >= 1 in all runs.
  - trace_hashes.tsv has 60 rows, and each row matches its JSON.
  - JUnit has 60 testcases and 0 bad results. The logs contain no %Warning/%Error/Traceback.
- Trace-hash recomputation (func-verifier, WSL python, generator only, no simulation; hash-recompute.txt): N4/509 98db926f..0a477e, N8/518 ae581f86..2d97f3 and N16/528 3436a357..1decb2 all equal trace_hashes.tsv. The pytest golden hashes (3000-cycle traces) are pinned in sim/common/tests/test_traffic_trace.py.

Per-N metrics over 20 runs each, shown as min / mean / max (4 significant digits; source: primary_summary.json):

| Metric | N4 | N8 | N16 |
| --- | --- | --- | --- |
| Accepted-transfer rate (fires / measured cycles, drain excluded) | 0.6811 / 0.7267 / 0.7630 | 0.6839 / 0.7386 / 0.8080 | 0.6778 / 0.7323 / 0.7863 |
| Input push rate | 0.6817 / 0.7274 / 0.7636 | 0.6852 / 0.7398 / 0.8093 | 0.6804 / 0.7348 / 0.7889 |
| Mean wait, acceptance to fire (all completed, incl. drain-completed) | 80.41 / 84.47 / 88.52 | 156.1 / 164.8 / 177.2 | 294.9 / 332.4 / 353.8 |
| P99 wait (nearest rank) | 363 / 447.1 / 618 | 623 / 797.4 / 1184 | 1291 / 1569 / 2128 |
| Max wait | 1265 / 1604 / 2417 | 1164 / 2006 / 2793 | 1591 / 2474 / 4092 |
| Censored at measurement end (completed in drain) | 63 / 63.2 / 64 | 127 / 127.2 / 128 | 223 / 253.7 / 256 |
| Generation-to-acceptance mean | 8896 / 13230 / 18000 | 6814 / 12020 / 16030 | 5930 / 12020 / 15450 |
| Generation-to-acceptance P99 | 24310 / 32230 / 41540 | 26050 / 36720 / 52460 | 33610 / 44350 / 56350 |
| Generated but unaccepted | 15547 / 26160 / 37758 | 15848 / 24160 / 34799 | 13824 / 25960 / 34960 |
| Fires in measurement, total | 1,453,461 | 1,477,138 | 1,464,584 |
| Input pushes, total | 1,454,725 | 1,479,681 | 1,469,658 |
| Minimum per-source service count (any run) | 16622 | 8056 | 4121 |
| TB responses completed, total | 1,454,725 | 1,479,681 | 1,469,658 |

Load characterization (Claude F1; Codex retains this profile as saturated finite-run traffic, no owner architecture decision needed):
- Offered generation is 0.907-1.074 descriptors/cycle against a downstream ready of 0.705-0.808/cycle.
- At least one FIFO is full in 92-99.97 % of measured cycles, and all FIFOs are full in 14-29 %.
- Mean waits are therefore close to Little's-law saturation values (about N*16/rate).
- Generation-to-acceptance delay and the unaccepted backlog grow with run length; they are not steady-state values.
- The profile was not changed.

### Failures encountered and kept as evidence (all were testbench/runner defects; no RTL defect)

| Run | Exit | What it shows |
| --- | ---: | --- |
| M3/20261015T095808Z_386 | 0 | Lint-only run. summary.json labels it lint-only with milestone_acceptance_scope=false. It is not acceptance evidence. |
| M3/20261015T095816Z_474 | 1 | Debug run with seed override 509 and --keep-going: 7 failures (F1 ts_mem_q generate-scope path; F2 test_12 checked head ts of unpushed sources at N16; F3 test_13 bin miscount when a full fire is followed by a reset cycle). Repairs were audited (see review). |
| M3-primary/20261015T100116Z_4475 | 1 | Sizing run with seed 509. Cocotb 3/3 passed, then the scope step crashed (runner KeyError 'log', F4). summary.json stayed at overall=RUNNING with milestone_acceptance_scope=false, so it was not labelled a pass. Fixed. |
| M3-primary/20261015T100158Z_4684 | 1 | Sizing rerun with seed override [509]. The scope gate failed by design ("seed override ... missing"). |
| M3-primary/20261015T100230Z_4891 | 1 | --lint-only. The scope gate failed by design. |
| M3-primary/20261015T100236Z_4922 | 1 | Full run #1, stopped by fail-fast after N4 seed 518 failed the primary bin `min_wait == 1` (observed 10). All model, pin and scoreboard checks passed. Repair: the primary test now asserts min_wait >= 1, while the exact 1-cycle minimum remains mandatory in the directed test_06 and the short random test_13. In the final run, min_wait > 1 occurs in 9 of 60 runs (N4: 518; N8: 514, 515, 518; N16: 519, 521, 522, 526, 528). |

### Not run / not claimed

- Block F mutation sanity was not requested and not run, so the tests have not been shown to fail on targeted RTL mutations.
- No code or functional coverage was measured, so no coverage numbers are reported.
- Formal/SVA, CDC, UVM and SystemC were not run.
- RR/FAI_MAIN/FAI_ALG2 simulation was not run; only the 9 expected elaboration rejections exist.
- FAI stress and W=5,000,000 tests were not run. Integration across policies, the nine-configuration sweep, synthesis/STA/power/PPA and the remote scheduler were not run.
- The func-verifier did not rerun the 60-run primary campaign. It audited its evidence and recomputed 3 hashes instead.
- Codex review found open C1; repair and rerun are required before M4.

Func-verifier notes, command log and audit outputs: .setup-logs/implementation/resume-20261015/m3-cocotb-resume/func-verifier/. Testbench-dev notes: .setup-logs/implementation/resume-20261015/m3-cocotb-resume/testbench-dev/notes.md. Note: the independent rerun updated the ignored file artifacts/implementation/M3/latest.txt to 20261015T101013Z_277.

---

# History: M3 FCFS checkpoint — PARTIAL_MODEL_UNIT (superseded by the section above)

## Current model checkpoint2026-10-15

Source7014a1e2ffa87f88050c68351aa6c63fc50ea2df adds the Claude-authored absolute-time/deque FCFS model,17 FCFS pytest cases, model export and draft traffic_trace.py. RTL99124df75bf28532760601414c62f4f376fc6b6c remains lint-clean and unchanged, frozen Spec1af80967bbc2fb83224f4725c4fb450889e69c62 unchanged. M3 is not functionally accepted.

| Current check | Actual result |
| --- | --- |
| Pure Python model tests | PASS54 =37 preexisting +17 FCFS, Claude and independent Codex;0 failure/error/skip. |
| Age-boundary review finding | Fixed by Claude; original independent reproducer now passes, six regression cases added. |
| Trace generator | DRAFT; integrated replay/producer/measurement/drain tests pending. |
| Selector/top cocotb / true hardware timestamp wrap | NOT_RUN. |
| TB response scoreboard / M3 runner / primary60-run matrix | NOT_STARTED / NOT_RUN. |
| M2 current runner | Stale FCFS rejection expectation; repair before rerunning. |
| Final func-verifier / hardware acceptance | NOT_INVOKED / NOT_COMPLETE. |
| PPA / remote scheduler run | NOT_RUN. |

Actual sessions52c2ef03-8d99-4839-8919-18949e074ccd (Phase4/5) and d439ab3c-9569-456d-8cf7-4c347a073733 (focused functional-verification workflow) used installed native CLI/plugin and serial testbench-dev. Both stopped mid-authoring on API safeguards reasoning_extraction. The latter fixed the model first; this was no new quota event, and the earlier15:00 reset is historical. Neither CLI exit0 nor a plugin orchestration label is module verification. No global settings, RTL/spec or gate-waiver/reset change. Interactive Claude or service repair is required to continue.

The first draft's48 pytest passed but missed a model boundary bug: commit advanced edge_index before age-checking, so a legal age2^31-1 head passed view but failed commit. Codex preserved the failing reproducer; Claude checks the current edge before advancing and added legal fire/non-fire, invalid >=2^31 and reset cases. Claude JUnit: .setup-logs/implementation/resume-20261015/m3-verify-resume2/testbench-dev/step1-pytest/pytest-junit.xml. Independent before/after XML and reproducer logs: artifacts/independent/m3/model-review/. Both final XML files contain54 tests and no failure/error/skip. These are Python tests, not RTL comparisons or added FIFO coverage.

Logs/prompts/transcripts/patch/hashes: .setup-logs/implementation/resume-20261015/model-checkpoint/ and verify-resume-1/verify-focused-1 directories. See docs/RESUME_CLAUDE.md for the concrete remaining cocotb/runner task. No new architecture decision is required.

## Historical initial RTL-only checkpoint

Recorded2026-10-15 (Asia/Taipei) by Codex from actual Claude execution. Frozen approved Spec v1.0:1af80967bbc2fb83224f4725c4fb450889e69c62. Partial RTL source:99124df75bf28532760601414c62f4f376fc6b6c. This is not functional acceptance.

## Actual implementation and delegation

Native Claude Code2.1.299 / RTL Agent Team0.14.6 session c4cabc42-6d6e-4e17-9262-ff68d7de6eaa invoked rat-p4p5-impl-verify after the owner repaired the proxy. Foreground serial orchestrator/rtl-coder/testbench-dev ran; no func-verifier invocation. Global configuration unchanged. Frozen-spec access/diff, ignored artifact write and WSL checks passed.

Claude changed five files: new rtl/common/cxl_fcfs_sel.sv, rtl/top/switch_top.sv, rtl/include/cxl_sched_pkg.sv and common/switch filelists. The balanced combinational selector uses unsigned modular age ordering and lower-source-ID ties. FCFS0 uses it over FIFO-valid heads. The conditional32-bit counter at switch_top.gen_arrival_ts.arrival_cnt_q resets0, increments on every non-reset edge and supplies pre-edge push timestamps. No simulation preload/debug port. The new desc_vec_t alias resolves standalone-selector UNUSEDPARAM lint without hardware storage. Existing FIFO/hold modules are unchanged.

## Observed checks and limits

| Check | Result |
| --- | --- |
| Claude strict selector/top lint, N4/8/16 | PASS six configurations, no warning/error or suppression. |
| Codex independent strict selector/top lint, N4/8/16 | PASS six configurations; process exit0 and log scan. |
| Claude standalone common FIFO/hold lint | PASS; preserved logs. |
| RR/MainFAI/Alg2 rejection diagnostics | Still intentionally unsupported; N4 logs inspected, not simulation. |
| Frozen-spec/common FIFO/hold source diff | Empty against recorded baselines. |
| Independent FCFS model / intended trace / TB tag tracking | NOT_STARTED; no new files. |
| FCFS selector/top cocotb / timestamp-wrap simulation | NOT_RUN. |
| Primary60-run FCFS matrix / metrics | NOT_RUN. |
| Functional verification agent / acceptance marker | NOT_RUN / NOT_SET. |
| Synthesis/STA/power | NOT_RUN. |

Strict lint command for each N is `verilator --lint-only -Wall -Wpedantic -Werror-IMPLICIT -f rtl/filelist_switch.f --top-module switch_top -GN_SRC=N -GPOLICY=0`; selector uses common filelist and cxl_fcfs_sel top. Claude logs: .setup-logs/implementation/resume-20261015/repaired-proxy/step1-lint/. Independent logs/audit: artifacts/independent/m3/lint/. WSL rg was unavailable during the independent extra log scan; Codex instead scanned all six logs using Python regex. No lint diagnostic was ignored.

Testbench-dev was interrupted before file authoring by HTTP429 weekly limit, CLI exit1. Reported reset2026-10-15 at15:00 Asia/Taipei, from resetsAt1792047600; future availability is not independently verified. No hardware test failed or was waived; none ran. The original standalone-selector lint trial found unused package L_DESC_W and was repaired by the type alias, followed by clean lint. No overage purchase, credential/configuration change or alternative RTL author was used.

## Resume requirements

Use the saved serial testbench-dev assignment, then func-verifier. Existing M2 runner still expects FCFS rejection; replace its three FCFS rejection cases with positive lint and retain nine RR/FAI rejections before rerunning M2. M3 runner still declares implemented=false and cannot pass. Preserve actual JUnit/config/seeds/logs/trace hashes, perform meaningful N4/8/16 directed/random/wrap tests and the full primary scope, then obtain Codex independent functional review before M4. Prior M1/M2 PASS results refer to their recorded source checkpoints; no current full runner pass after this draft is claimed.

Full native transcripts, changed-file hashes and tracked/untracked Git patch are archived in .setup-logs/implementation/resume-20261015/repaired-proxy/quota-checkpoint/. No frozen specification or architecture decision changed.

## 2026-10-15 M3-verify-resume attempt (Claude orchestrator, from actual evidence)

Preflight passed at HEAD 9c0828e: frozen-spec diff vs 1af8096 empty, ignored artifact write OK, WSL Verilator 5.052 / Python 3.12.3 / cocotb 2.1.0 / pytest 9.1.1 / nproc 16. The saved step-2 testbench-dev assignment plus a short addendum (.setup-logs/implementation/resume-20261015/m3-verify-resume/orchestrator/step2-testbench-dev-addendum.md) was delegated serially in the foreground. testbench-dev stopped mid-authoring on an API error (`[reasoning_extraction]`, invalid_request, req_011Cg3jrT1HyRKprUViuskn5). That session stopped without retrying or replacing the worker. A later fresh focused session, recorded above, repaired the model before another API stop.

Left on disk at that interruption: refc/cxl_model/fcfs_model.py, refc/tests/test_fcfs_model.py, sim/common/traffic_trace.py and the model export. Correction to the initial orchestrator summary: the testbench agent DID execute48 pure pytest successfully; Codex independently confirmed48 before discovering the uncaught boundary bug. Trace generator was still a draft. Selector/top cocotb, runner updates, M1/M2/M3 full suites, primary regression and final func-verifier were not run. The later54-case repaired model is recorded above. rtl/ is byte-identical to the start of the attempt (sha256). Status remains PARTIAL_RTL_LINT, and no functional acceptance is claimed. Patch, hashes and file copies are in .setup-logs/implementation/resume-20261015/m3-verify-resume/orchestrator/.
