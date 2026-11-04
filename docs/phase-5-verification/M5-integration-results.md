# M5 FAI Main integration results — long regressions and final functional evidence review

- Date: 2026-10-17. Run IDs and times are UTC.
- Reviewer: Claude RTL Agent Team `func-verifier`, invoked natively through Claude Code `--agent rtl-agent-team:func-verifier` (`claude/claude-opus-5-5`, `--effort high`), for the FINAL evidence review.
- Source under test: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426` (tree `26d157cf7f2ff7a1d85c94cd36ce685991586846`).
- Frozen spec: `specs/CXL_SPEC.md` v1.0 at `1af80967bbc2fb83224f4725c4fb450889e69c62`. `git diff 1af8096 cefbbb0 -- specs/CXL_SPEC.md` is empty.
- Verdict and traceability: [reviews/phase-5-verify/M5-functional-verification.md](../../reviews/phase-5-verify/M5-functional-verification.md).
- Verifier working evidence (ignored): `.setup-logs/implementation/resume-20261017/m5-final-review/verifier/`.

## 1. Provenance (who did what)

| Role | Actor | Evidence |
| --- | --- | --- |
| RTL, reference models, testbenches, runner registry, stress-boundary repair (cefbbb0) | Claude Code RTL Agent Team (testbench-dev / func-verifier sessions) | Commits db96961, ae5a682, cefbbb0; [M5-stress-boundary-repair.md](M5-stress-boundary-repair.md) |
| Batch script `batch/run_batch.sh` (sha256 `039f76a8…91fd3e1`) | Native RTL Agent Team func-verifier. The only difference from the attempt-1 script is the batch directory path (`batch/script-diff-vs-original.txt`). | `.setup-logs/…/m5-long-regression-2/batch/` |
| Detached native launch | **FAILED.** The PID was lost before the wrapper started, even though the WSL holder was alive. No stage started and no test ran. The failure is preserved, not retried. | `batch/launch-outcome.detached-failed.txt`, `launch-manifest.detached-failed.json`, `diag-launch.out` |
| Long-batch execution | **Codex local orchestration** ran the SAME verifier-authored script in foreground WSL (exec session 76144, wrapper PID 8004), starting 2026-10-17T01:39:51Z. Codex did not author or replace any source or test, and changed no settings. | `batch/codex-foreground-launch.json`, `batch/combined.log` |
| Independent raw audit (stress / primary / production) | Codex | `m5-long-regression-2/codex-review/{stress,primary,production}-audit.json` |
| Final evidence review (this report) | Native func-verifier | This session re-parsed the original raw JUnit, metrics JSON, logs, commands and configs with its own scripts (§8). |

This reviewer did **not** execute the long batch. The batch exit 0 is runner success only: `batch-status.txt` reads "COMPLETED_ALL_STAGES_EXIT0 (runner success only; NOT_ACCEPTED pending verifier review)". Acceptance below rests on the raw evidence review, not on that exit code. No functional test was re-run in this review: no failure, new source change or unresolved concern justified one. Native Opus/high model provenance of the earlier sessions is in `m5-long-regression-2/checkpoint/native-provenance.json` (all response records `claude-opus-5-5`, requested effort high). This session's own stream has 116 response records with `claude-opus-5-5` and init model `claude/claude-opus-5-5` (`m5-final-review/run-stream.jsonl`, `session-settings.json`).

### Source stability

- Wrapper first log line: `HEAD cefbbb0… porcelain=[]`. `versions.txt` of every batch run records HEAD cefbbb0 with an empty `git status --short`.
- Launch baseline `batch/source-sha256.txt` covers 144 tracked files. In this review `sha256sum -c` gives **144/144 OK**, `git ls-files -s` is identical to `batch/source-git-blobs.txt`, and the working tree is clean. All tracked source hashes were therefore stable from launch through the run and up to this review.
- cefbbb0 vs ae5a682 changes only: `scripts/run_verify.py` (count pin 18→19 plus comments), `sim/switch_top_fai/test_switch_fai.py` (append-only test_19), `sim/switch_top_fai/test_switch_fai_stress.py` (one assertion line removed and replaced by the exact boundary relation, plus observation helpers), and the repair report. Across both test files exactly one line was removed: the old `:121` snapshot relation.
- `rtl/`, `refc/`, `sim/common/` and `sim/switch_top_fai/fai_stream.py` (traffic/stress trace v2) have no diff from db96961 to cefbbb0.
- Shared blocks `cxl_desc_fifo.sv`, `cxl_out_hold.sv`, `cxl_fcfs_sel.sv`, `cxl_rr_sched.sv` and `rtl/include/` have no diff since the accepted common/RR review commit 23f8032. Since then, `switch_top.sv` changed only by the FAI_W elaboration check, the FAI_MAIN policy-slot instance and the policy-dependent opaque context width (5 bits for FAI Main, 1 bit for FCFS/RR). cxl_out_hold itself is unchanged.

## 2. Batch stages (from `batch/stages.tsv`, all exit 0, sequential fail-fast)

Every stage ran under `source scripts/wsl_env.sh` with Verilator 5.052, Python 3.12.3, cocotb 2.1.0, pytest 9.1.1 and g++ 13.3.0 (WSL2 6.6.87.2).

| # | Scope | Command | Start → End | Run ID | Raw tests (JUnit) | Steps |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | M5-stress | `scripts/run_verify.sh M5-stress -j 8 --make-jobs 2` | 01:39:51 → 01:52:37 | 20261017T013952Z_8032 | 30 / 0 F / 0 E / 0 S | 37 PASS (6 lint, 30 cocotb, scope gate) |
| 2 | M5-primary | `scripts/run_verify.sh M5-primary -j 8 --make-jobs 2` | 01:52:38 → 01:58:37 | 20261017T015238Z_9805 | 60 / 0 / 0 / 0 | 67 PASS (3 lint, 3 probes, 60 cocotb, gate) |
| 3 | M5-production | `scripts/run_verify.sh M5-production -j 3 --make-jobs 2` | 01:58:37 → 03:41:25 | 20261017T015838Z_13196 | 3 / 0 / 0 / 0 | 10 PASS (3 lint, 3 probes, 3 cocotb, gate) |
| 4 | M1 | `scripts/run_verify.sh M1 -j 8 --make-jobs 2` | 03:41:26 → 03:41:56 | 20261017T034126Z_13943 | 286 / 0 / 0 / 0 | 13 PASS |
| 5 | M2 | `scripts/run_verify.sh M2 -j 8 --make-jobs 2` | 03:41:56 → 03:42:59 | 20261017T034156Z_14547 | 526 / 0 / 0 / 0 | 46 PASS + 3 XREJECT |
| 6 | M3 | `scripts/run_verify.sh M3 -j 8 --make-jobs 2` | 03:43:00 → 03:44:04 | 20261017T034300Z_16317 | 550 / 0 / 0 / 0 | 44 PASS + 3 XREJECT |
| 7 | M4 | `scripts/run_verify.sh M4 -j 8 --make-jobs 2` | 03:44:04 → 03:44:53 | 20261017T034404Z_18077 | 430 / 0 / 0 / 0 | 41 PASS + 3 XREJECT |
| 8 | M4-q1 | `scripts/run_verify.sh M4-q1 -j 8 --make-jobs 2` | 03:44:53 → 03:45:20 | 20261017T034453Z_19058 | 195 / 0 / 0 / 0 | 24 PASS |

Evidence directories: `artifacts/implementation/<scope>/<run-id>/`. Stage logs: `.setup-logs/implementation/resume-20261017/m5-long-regression-2/batch/stage-logs/0N-<scope>.log`.

Every run has `overall PASS`, `scope full`, `milestone_acceptance_scope true`, `infra_smoke false`, `sim_build_relaxations []` and `not_run 0`. No `--seeds`, `--n-src` or `--infra-smoke` override was used, and `CXL_INFRA_SMOKE` appears in no command block. Lint and simulation builds use `-Wall -Wpedantic -Werror-IMPLICIT` with no `-Wno-*` flag. Every lint step reports 0 diagnostics. `%Warning` text appears only in the classified POLICY=3 expected-rejection logs (`unexpected_diagnostics: []`).

## 3. M5-stress — 20261017T013952Z_8032 (full 30-run matrix)

Parameters: switch_top POLICY=2. FAI_W 64 and 256 are passed with `-G`. N 4/8/16 × seeds 509..513. `CXL_STRESS_CYCLES` = 400,000 (W64) / 800,000 (W256), pinned in every command block. The stimulus is `cxl-fai-stress-trace-v2`, unchanged.

| Item | Result (own re-parse of 30 JUnit + 30 metrics JSON + 30 logs) |
| --- | --- |
| Runs | 30/30 unique (N, W, seed). Each JUnit has 1 testcase `test_stress_random_regression` with `random_seed` = file seed and no failure/error/skipped child. Each log reads `TESTS=1 PASS=1 FAIL=0 SKIP=0` and exit 0. |
| Measured trace cycles | **18,000,000** (15 × 400,000 + 15 × 800,000). Of these, 17,988,782 are non-reset and 11,218 are in-measurement reset cycles (directed/random resets restart the window). Fires in measurement: 12,571,316. |
| Windows closed in measurement | 137,726 in total. Minimum per run is 6,097 at W64 (≥ 5,000 required) and 3,045 at W256 (≥ 2,500 required). |
| All 16 (state × evidence) Main transitions | Reached in the **measured** population in **every** run, each with count > 0. The smallest count of any transition in any run is 2. All four states are reached, and effective class changes are > 0. |
| Requirements still asserted per run (test source at cefbbb0) | Evidence UP/DOWN/KEEP/S0 > 0; closing-edge fires; held offers across closing edges, max windows in one hold ≥ 2; held grant whose class changed at closing (`held_cls_change`, `held_fire_cls_differs` > 0); visit continue / expired / emptied / relinquished / expired-with-replacement / renewal; class-switch offers; Low and High fires; class-over-age and in-class ties; full-plus-pop refusals; resets mid-window / mid-visit / mid-hold / non-H / nonempty; idle cycles; valid-ready-low run ≥ W; every source fires; minimum wait 1; reordered and cross-epoch TB responses; responses issued == completed == delivered; 0 outstanding after drain. My audit re-checked each of these from the JSON: 0 problems. |
| Full-plus-pop follow-ups (repaired check) | Measured `R + T + owed == F` and whole-run `R + T == F` are exact in 30/30. `owed` = 1 in 18 runs and 0 in 12, so both branches were exercised. Where owed = 1, the first drain cycle has `in_ready[src] = push[src] = 1`, the pushed descriptor is identical to the held one, `src` is a boundary-held source and `prev_at_boundary == ["fire", src, src]`. `cov_at_entry == coverage_measurement` and `drain_calls == 2` in 30/30. Nothing is pending after `finish()`. |
| Trace | 30 distinct SHA-256 hashes. |
| Gate | `stress_full_matrix_summary.json`: `full_scope true`, `valid_runs 30`, `problems []`, `require_all_transitions true`. |
| Peak RSS | Up to 336 MiB per stress process (343,664 KiB). Recorded only; no bounded-memory claim is made for stress. |

**Initial failure and fix (not hidden).** The original long stress run `M5-stress/20261017T010035Z_1025` (source ae5a682) had **7 failures among the 9 runs that executed**, and fail-fast left **21 NOT_RUN**. All 7 failed at the old `test_switch_fai_stress.py:121`, which applied the whole-run full-plus-pop relation to the frozen measurement snapshot. Root cause: a full-plus-pop fire in the last measured cycle has its follow-up in the first drain cycle. The fix (testbench bookkeeping only) is in [M5-stress-boundary-repair.md](M5-stress-boundary-repair.md). In this review, all 9 originally executed configurations in run 8032 have **identical `trace_sha256`, `coverage_measurement` and `coverage_total`** to run 1025. Every originally failing configuration (lag 1) now records `owed = 1`, and the two originally passing ones (N4/W64/511, N8/W64/509, lag 0) record `owed = 0`. The narrow seed-510 six-configuration run `M5-stress/20261017T011825Z_1587` had all 6 simulations PASS and its scope gate FAIL as expected for a subset (26 problems, all caused by the seed override). It is **not** a full-stress PASS and is not counted. The full 30-run PASS evidence is run 8032 only.

## 4. M5-primary — 20261017T015238Z_9805 (60 runs, production W, no window close)

Parameters: N 4/8/16 × seeds 509..528, 100,000 measured cycles each, and `CXL_PRIMARY_CYCLES=100000`. There is no `-GFAI_W`, so the RTL default W = 5,000,000 applies. The profile is `primary`, there is no warmup, and the trace is `cxl-traffic-trace-v2`.

- 60/60 JUnit clean, seed property = file seed. **6,000,000 measured cycles.**
- Intended-trace SHA-256 equals `reviews/evidence/M3-primary-v2-trace-hashes.tsv` and the FCFS run's trace in **60/60**.
- Every cycle is checked against an independent FCFS switch mirror: 6,011,803 mirrored cycles in total, which equals every simulated cycle after bring-up, measured plus drain/response wait. `windows_closed` is 0, the only state seen is H, and `fires_low` is 0 in every run. The label reads: **"NOT evidence of window classification/adaptation."**
- Comparison with the accepted FCFS run `M3-primary/20261016T014224Z_3877`, per (N, seed), over every common key: all top-level metrics are equal. Equal keys include trace, generated, accepted-transfer rate, input push count/rate, per-source pushes and service, wait and generation-to-acceptance statistics, fires in measurement/drain, drain_only, responses, phases and input_hold. The only differences are `schema`, `policy`, `policy_param`, `wall_time_s` and the coverage dicts as wholes. Every shared coverage key (≥ 30 per population) is equal in both the measured and whole-run populations; the coverage dicts differ only by the extra FAI keys. Codex compared 17 keys; this review compared all common keys.
- Populations: actual acceptance in measurement totals 4,404,064; drain-only (boundary-held) pushes total 516, excluded from measurement metrics. Intended `generated` = accepted + generated-but-unaccepted in 60/60.
- Primary functional matrix: 180/180 initial runs, all from the initial attempt with no failures.

  | Policy | Run | Source | Result |
  | --- | --- | --- | --- |
  | FCFS | `M3-primary/20261016T014224Z_3877` | 3019b71 | PASS 60 |
  | RR q10 | `M4-primary/20261016T013811Z_371` | 3019b71 plus RR TB files committed byte-identically in 75270b8 | PASS 60 |
  | FAI Main | `M5-primary/9805` | cefbbb0 | PASS 60 |

  The FCFS/RR primaries were not re-run at cefbbb0. Their RTL/TB paths have no diff since 75270b8, except for the FAI-only additions in switch_top described in §1. At cefbbb0 the FCFS/RR paths are re-covered by M3/M4/M4-q1 and by the FAI-vs-FCFS mirror equality above. **This matrix is 180 functional runs, not 9 PPA results.**

## 5. M5-production — 20261017T015838Z_13196 (W = 5,000,000, real windows)

Parameters: N 4/8/16, seed 509, `CXL_PRODUCTION_CYCLES=20000000` = 4 complete windows (spec 9 requires ≥ 3). The RTL default `FAI_W` is used (no `-GFAI_W`). The test asserts on the DUT that `idx_q`, `s_q` and each `b_q[h]` are 23 bits. **60,000,000 real measured non-reset cycles in total.**

- **Method (source inspected).** `test_production_windows` loops `for k in range(cycles)` and awaits `tb.cycle(push, out_ready, meta)`. Each call drives only the top-level pins `rst_n`, `i_in_valid`, `i_in_desc` and `i_out_ready`, then awaits FallingEdge/ReadOnly (all checks) and one RisingEdge. The only internal write in the harness is the optional sim-only arrival-counter `deposit` for the directed timestamp-wrap test (spec 6). Production never passes it, and the harness forbids it when the FCFS mirror is on. There is no time skip, no deposit or preload of index/B/S/class, and no smaller window.
- **Timestamps.** Window closes are logged at sim times 50,000,030 / 100,000,030 / 150,000,030 / 200,000,030 ns. That is (k·5,000,000 + 3 bring-up reset cycles) × 10 ns, at closing edges 5,000,000 / 10,000,000 / 15,000,000 / 20,000,000. Each log has 40 progress lines, one every 500,000 cycles up to 20,000,000. Measurement wall time was 4,476 / 5,047 / 6,159 s (4,468 / 3,963 / 3,248 cycles/s) for N4/8/16.
- **Every-cycle checks.** Each cycle passed through the independent oracle, the model-free pin/history trackers (own spec 8.1 evidence and literal 8.2 table), the scoreboard (whole 105 bits, source, order, conservation), the observed-pin input hold (515,008 / 683,340 / 600,859 obligation checks) and the TB tagged responses.
- **Bounded memory.** Peak RSS was 48,920 / 49,152 / 49,092 KiB (about 48 MiB per process). This is a resource observation, not coverage or PPA.

Per-window evidence. This review recomputed it from raw `b_close`/`s_close` with exact integers (`UP iff 10·N·B < 3·S`, `DOWN iff N·B > S`, else KEEP; S0 iff S = 0; every intermediate < 2³²) and applied the spec 8.2 table independently, starting from all-H:

| Boundary (closing edge) | S_close N4 / N8 / N16 | Evidence N4 (×2 for N8, ×4 for N16) | Boundary pattern |
| --- | --- | --- | --- |
| 1 (5,000,000) | 2,747,980 / 2,749,350 / 2,750,371 | UP 1, DOWN 3 | offer **held across** the closing edge, no closing fire |
| 2 (10,000,000) | 2,749,750 / 2,750,298 / 2,749,616 | UP 1, DOWN 2, KEEP 1 | closing edge **carries a fire**, included in the closing counts |
| 3 (15,000,000) | 2,749,186 / 2,749,672 / 2,752,395 | UP 1, DOWN 2, KEEP 1 | held across |
| 4 (20,000,000) | 2,750,244 / 2,749,940 / 2,749,435 | UP 2, DOWN 1, KEEP 1 | closing fire |

- In every window `S_close = Σ B_close[h]` holds, S_close ≤ W < 2²³, and `closing_trace_cycle = (w+1)·W − 1`.
- The recomputed evidence equals the RTL-edge-recorded evidence and the designed `production_kinds`. The recomputed new class map equals the recorded map and `expected_class_sequence`. The final pin-level classes equal the last expected map.
- Main hysteresis exercised (N4 / N8 / N16):
  - downgrade H → B_H → L: 3 / 6 / 12;
  - restoration L → B_L → H: 1 / 2 / 4;
  - opposing-evidence cancellation B_H/UP → H: 1 / 2 / 4;
  - KEEP cancellation B_H/KEEP → H: 1 / 2 / 4;
  - effective class changes: 4 / 8 / 16.
- Measured transitions reached: 9 of 16 (`require_all_transitions: false` for production). S0, B_L/DOWN and B_L/KEEP do not occur in production, and `held_cls_change` = 0 there. Those cases are covered by M5-stress (§3) and the M5 unit directed tests, not by production.
- Codex `production-audit.json` per-window records are **identical** to the actual JSON `windows` lists for N4/8/16.

Final drain and conservation (asserted in the test and re-checked here):

| N | Fires in measurement | Accepted in measurement | Drain-completed fires | Drain-only pushes |
| --- | --- | --- | --- | --- |
| 4 | 10,997,160 | 10,997,179 | 19 | 0 |
| 8 | 10,999,260 | 10,999,280 | 20 | 0 |
| 16 | 11,001,817 | 11,001,838 | 21 | 0 |

- In each run, generated = accepted + backlog, and responses issued = completed = fires, with 0 outstanding and 0 dropped by reset.
- Accepted-transfer rate is about 0.55 (designed load 0.55), with nonzero service for every source.
- `production_full_matrix_summary.json`: `full_scope true`, `valid_runs 3`, `problems []`.

The RTL threshold path in `rtl/common/cxl_fai_main_sched.sv` uses `L_THR_W = 32`. `b_close` and `s_close` are zero-extended to 32 bits before the multiplication by the constant coefficients. Elaboration checks that 10·N·W < 2³². B/S are 23 bits and the index is 23 bits at W = 5,000,000.

## 6. Current unit/regression scopes at cefbbb0 (stages 4-8, plus the M5 unit pin)

| Scope | Run | Tests (raw JUnit) | Composition | Lint / probes / XREJECT |
| --- | --- | --- | --- | --- |
| M1 | 20261017T034126Z_13943 | 286 | refc pytest 196 + cocotb 90 | 2 / 0 / 0 |
| M2 | 20261017T034156Z_14547 | 526 | refc 196 + cocotb 330 | 15 / 0 / 3 |
| M3 | 20261017T034300Z_16317 | 550 | refc 196 + TB helpers 39 + cocotb 315 | 12 / 0 / 3 |
| M4 | 20261017T034404Z_18077 | 430 | refc 196 + helpers 39 + cocotb 195 | 18 / 6 / 3 |
| M4-q1 | 20261017T034453Z_19058 | 195 | cocotb 195 | 6 / 3 / 0 |
| M5 unit (not in this batch) | 20261017T012755Z_5680 (native) and 20261017T012115Z_2007 (Codex) | 805 each | refc 196 + helpers 39 + cocotb 570 (30 jobs × 19) | 27 / 9 / 3 |

- All counts equal the pins (286 / 526 / 550 / 430 / 195, and 805) and Codex `old-scope-expected-counts.json`.
- The refc suite (196) and TB-helper suite (39) are the **same** suites collected in several scopes. They are **not** summed as additional coverage, and repeated pytest runs are not new RTL coverage.
- The 3 XREJECTs per applicable scope are `switch_top POLICY=3` (FAI_ALG2) at N4/8/16. Each hits exactly one expected `$fatal` "POLICY_FAI_ALG2 (POLICY=3) is not implemented" with no unexpected diagnostics. They are expected rejections, never counted as tests or passes.
- Elaboration probes, all checks OK:
  - FCFS and FAI positive metadata controls: `arrival_cnt_q` and `ts_mem_q` present, `u_rr_sched` absent, FAI 5-bit `held_ctx_q`.
  - RR controls (M5 unit): `arrival_cnt_q`, `ts_mem_q` and `u_fcfs_sel` absent; `ptr_q`/`used_q` present; 1-bit context. RR has no timestamps.
- Both M5 unit runs ran at ae5a682 with the three repaired files uncommitted. Their sha256 values (`c4892e8b…`, `6982bbac…`, `9f88b9b9…`) and blobs (`efb2b6a4`, `60751465`, `d12ab964`) equal the committed cefbbb0 files, so their tested source equals cefbbb0 except for the report document. test_19 passed in 30/30 cocotb JUnit files.

## 7. Not run, deferred, remaining limits

| Item | Status |
| --- | --- |
| Formal/SVA proofs, CDC signoff, SystemC/BFM, UVM | **NOT_RUN** (spec 9: OPTIONAL_OR_DEFERRED; single clock, synchronous reset, no CDC boundary) |
| Numerical code/functional coverage thresholds, coverage-closure tooling | **NOT_RUN / deferred.** The counted bins are scenario-reach assertions, not a coverage metric. |
| RTL mutation testing | **NOT_RUN.** Selected earlier model mutants are model-level checks, not RTL coverage. |
| FAI Algorithm-2 (spec 8.6) | **Not implemented.** POLICY=3 is rejected at elaboration. Main and Algorithm-2 are distinct, and Algorithm-2 is not substituted for Main. |
| FastX DC / PrimeTime / SAED32 synthesis, STA, power, any PPA | **NOT_RUN.** Host, user, auth, workdir, library path and pilot clock/SDC constraints remain pending. The existing remote EDA templates (`syn/dc.tcl`, `sta/pt.tcl`, `scripts/remote_eda.py`) currently have no nine-configuration POLICY/N_SRC/FAI_W parameter selection and no frozen PPA timing profile (`syn/constraints/` holds only `.gitkeep`). Nothing here is PPA-ready, and no area/timing/power is claimed. |
| Paper fidelity | The original paper behavior is owner-supplied. The single-output 10/10 High/Low alternation is a project reconstruction. No IEEE PDF was inspected, and no cycle-identical paper claim is made. |
| Production scope | One seed (509) per N. 9/16 transitions, no S0, no held class change at a production boundary. Those are covered at W64/W256 and in directed tests. |
| FCFS/RR primary | Run at 3019b71 / 75270b8-equivalent TB, not re-run at cefbbb0 (see §4). |
| New correctness-critical decisions | None discovered; no contradiction with the frozen spec was found. |

## 8. Review commands (this session; read-only on evidence, Windows host Python 3 `-I`)

| # | Command | Exit | Result |
| --- | --- | --- | --- |
| 1 | `sha256sum -c batch/source-sha256.txt`; `git ls-files -s` vs `batch/source-git-blobs.txt`; `git diff --quiet 1af8096 HEAD -- specs/CXL_SPEC.md`; `git status --porcelain` | 0 | 144/144 OK, blobs identical, spec diff 0, clean |
| 2 | `python -I verifier/audit_stress.py artifacts/implementation/M5-stress/20261017T013952Z_8032 verifier/audit-stress.json` | 0 | 30 runs, problems [] |
| 3 | `python -I verifier/audit_primary.py <M5-primary 9805> <M3-primary 3877> reviews/evidence/M3-primary-v2-trace-hashes.tsv verifier/audit-primary.json` | 0 | 60 runs, problems [] |
| 4 | `python -I verifier/audit_production.py <M5-production 13196> codex-review/production-audit.json verifier/audit-production.json` | 0 | problems []. The first pass reported 8 false mismatches from my own comparison against the 4-group `trace.kinds` table without the `h % 4` expansion. I fixed the audit script; no evidence changed. |
| 5 | `python -I verifier/audit_units.py artifacts/implementation verifier/audit-units.json M1=… M2=… M3=… M4=… M4-q1=… M5=20261017T012755Z_5680` | 0 | all ok |
| 6 | Cross-checks: 1025 vs 8032 trace/coverage identity; Codex per-window records vs JSON; probe/XREJECT details; `-Wno-*` and `%Warning` scan; git diffs listed in §1 | 0 | as reported above |

The full command log, hash inventory and report manifest are in `.setup-logs/implementation/resume-20261017/m5-final-review/verifier/`.
