# M4 Round Robin functional verification results

## Status 2026-10-16 (Asia/Taipei): COMPLETE_M4; Codex common/FCFS/RR review ACCEPTED


Codex acceptance: verification source `75270b8808946e880ca039a2fa06b629dff32cd8`. Independent WSL full reruns M4/20261016T014545Z_7139 PASS311 and M4-q1/20261016T014656Z_8457 PASS195, zero failure/error/skip. Raw XML seeds/counts, strict logs, all60 primary hashes/complete trace objects, FCFS regression equality and measured/drain-only conservation independently audited. All516 drain-only requests complete separately. Native root/orchestrator/testbench-dev/func-verifier actual response models verified `claude-opus-5-5`, invocation high effort, exit0. Model route correction preserved global configuration. Detailed audit/checkpoint evidence is in .setup-logs/implementation/resume-20261016/m4-verify-opus-high-2/codex-review/ and checkpoint/. Current matrix120/180; Main FAI60 and all PPA remain NOT_RUN. Historical authoring-state source references below describe what the native agent observed before Codex committed/accepted it.

This section supersedes the PARTIAL_MODEL_UNIT and RTL-only checkpoints below. Those are kept unchanged as history and evidence pointers. Verdict and review details: reviews/phase-5-verify/M4-functional-verification.md.

- Frozen spec: v1.0 1af80967bbc2fb83224f4725c4fb450889e69c62. The diff is empty.
- RTL under test: e727ebaae310a2a039ee2592f564f894f9668c2a. There is no diff, and the sha256 of every rtl/*.sv and filelist was identical before and after the campaign.
- RR oracle: refc/cxl_model/rr_model.py at d09db3330ff8d59f4a1735d905ac3243b9e0efca, no diff.
- Tree: HEAD 3019b71 plus the uncommitted testbench-dev work. No commit was made.
  - New files: sim/common/switch_rr_tb.py, sim/switch_top_rr/test_switch_rr.py (13 tests) and sim/switch_top_rr/test_switch_rr_primary.py (schema cxl-m4-rr-primary-v1).
  - Modified: scripts/run_verify.py. RR now gets strict positive lint in M2/M3; only the 6 FAI XREJECT remain; refc pytest is pinned at 93; the M4 / M4-q1 / M4-primary entries and the FCFS metadata elab_probe controls were added; the primary gate gained `reference_hashes` and `expect_fields`.
  - func-verifier changed none of these files.
- Tools (WSL, via scripts/wsl_env.sh): Verilator 5.052 with strict flags; SIM_BUILD_RELAXATIONS is empty; no `-Wno`, waiver, skip or xfail.

### Results (artifacts/implementation/)

| Run | Who | Exit | Steps | Tests | fail/err/skip | Notes |
| --- | --- | ---: | --- | ---: | --- | --- |
| M4-primary/20261016T013811Z_371 | func-verifier | 0 | 67 (3 RR lint + 3 FCFS probes + 60 cocotb + scope gate) | 60 | 0/0/0 | No `--seeds` override. N4/8/16 x seeds 509..528 x 100,000 measured cycles = 6,000,000 cycles. Scope gate PASS, milestone_acceptance_scope=true, `reference_hash_matches` 60. 244.8 s with -j 14. |
| M3-primary/20261016T014224Z_3877 | func-verifier (FCFS regression; the shared gate code changed) | 0 | 64 | 60 | 0/0/0 | Hashes 60/60 vs TSV. Metrics JSON identical in 60/60 runs (wall time excluded) to the Codex-accepted 20261015T175309Z_4038. |
| M4/20261016T012639Z_374 | testbench-dev | 0 | 41 (35 PASS + 6 FAI XREJECT) | 311 | 0/0/0 | 93 refc + 23 sim/common pytest + 195 cocotb (13 x N4/8/16 x seeds 509..513). Quantum 10 is the RTL default. |
| M4-q1/20261016T012728Z_1477 | testbench-dev | 0 | 24 | 195 | 0/0/0 | SUPPLEMENTARY quantum 1 (D32), passed with -G; not a primary configuration. |
| M1 …012805Z_2386 / M2 …012826Z_2985 / M3 …012919Z_4752 | testbench-dev | 0 | | 183 / 423 / 431 | 0/0/0 | Regressions after the registry update. M2/M3 each have 6 XREJECT and 3 RR positive lints. |

func-verifier re-parsed the raw JUnit independently for M4-primary (60 XML, 60 testcases, seed property = file seed), M3-primary (60), M4 (311) and M4-q1 (195), with 0 bad results. Every M4-primary and M3-primary metrics JSON passed 22 per-run accounting invariants, including:
- generated = accepted + unaccepted;
- unaccepted = boundary-held + unoffered;
- sum of per-source service = fires;
- censored = drain-completed;
- all_completed = accepted pushes;
- drain-only pushes = fires = held offers, at most 1 per source;
- responses issued = completed = measured fires + drain fires + drain-only fires;
- nothing outstanding after the drain;
- no reset drops;
- min wait >= 1.

The audit scripts are in the func-verifier log directory (below).

Earlier failure kept as evidence: M4/20261016T012509Z_1035 exited 1. In test_12, N4 seed 511 passed every oracle, pin and scoreboard check but did not reach the stimulus bin `wrap_offers > 0` on its saturated short trace: skips 6, wraps 0, and 859 of 875 turns expired. testbench-dev made the wrap, held-mismatch and renewal bins recorded instead of required in test_12. They remain literal, mandatory assertions in the deterministic test_04 / test_06 / test_09. func-verifier reviewed and accepted this; see the review.

### Intended traces versus actual acceptance

- Intended-trace SHA-256 matches reviews/evidence/M3-primary-v2-trace-hashes.tsv for **60/60** runs. This holds in each JSON, in the runner's regeneration and in the gate.
- The runner trace_hashes.tsv is byte-identical to the tracked TSV.
- Generated counts, per-source generation and ready cycles are identical to FCFS for 60/60 (N, seed).

Actual acceptance is reported separately from intended generation, per run and per source.

### RR primary metrics (quantum 10; per N over 20 seeds, min / mean / max of per-run values, totals where marked)

Source: rr_primary_metrics.json x 60, tabulated by func-verifier (04-fv-tabulate-audit-rerun.log). Rates, means (including means of per-run values) and ratios are rounded to 4 significant digits. Counts, totals and integer per-run statistics (P99, maximum, service counts) are exact.

| Metric | N4 | N8 | N16 |
| --- | --- | --- | --- |
| Intended generated, total | 1,978,000 | 1,962,795 | 1,988,939 |
| Accepted (FIFO pushes in measurement), total | 1,454,725 | 1,479,681 | 1,469,658 |
| Generated-but-unaccepted at the boundary, total | 523,275 | 483,114 | 519,281 |
| … per run | 15,547 / 26,160 / 37,758 | 15,848 / 24,160 / 34,799 | 13,824 / 25,960 / 34,960 |
| Input push rate | 0.6817 / 0.7274 / 0.7636 | 0.6852 / 0.7398 / 0.8093 | 0.6804 / 0.7348 / 0.7889 |
| Accepted-transfer rate (measured fires / 100,000) | 0.6811 / 0.7267 / 0.7630 | 0.6839 / 0.7386 / 0.8080 | 0.6778 / 0.7323 / 0.7863 |
| Measured fires, total | 1,453,461 | 1,477,138 | 1,464,584 |
| Mean acceptance-to-fire wait (measured accepts, including drain-completed) | 79.60 / 84.19 / 88.12 | 154.4 / 163.8 / 176.5 | 287.4 / 329.7 / 353.6 |
| P99 wait (nearest rank, per run) | 405 / 462.9 / 659 | 667 / 845.4 / 1,188 | 1,272 / 1,609 / 2,073 |
| Max wait | 1,349 / 1,767 / 2,592 | 1,263 / 2,098 / 2,821 | 1,854 / 2,637 / 4,169 |
| Runs with min wait = 1 (otherwise > 1) | 19 | 19 | 20 |
| Censored at measurement end (= drain-completed) per run | 63 / 63.2 / 64 | 127 / 127.2 / 128 | 223 / 253.7 / 256 |
| Drain-only accepts (boundary-held), total / per run | 64 / 3-4 | 145 / 7-8 | 307 / 13-16 |
| Drain-only mean wait (separate population) | 39 / 42.9 / 48 | 73 / 76.2 / 83.3 | 124 / 144.1 / 151.9 |
| Unoffered backlog at the boundary, total | 523,211 | 482,969 | 518,974 |
| Generation-to-acceptance mean | 8,897 / 13,230 / 18,000 | 6,815 / 12,010 / 16,030 | 5,916 / 12,010 / 15,440 |
| Generation-to-acceptance P99 | 24,304 / 32,230 / 41,558 | 26,064 / 36,750 / 52,469 | 33,928 / 44,420 / 56,381 |
| Per-source service: min / max over all sources and runs | 16,623 / 19,981 | 8,070 / 11,204 | 4,129 / 5,747 |
| Zero-service (source, run) pairs | 0 | 0 | 0 |
| Per-run max/min source-service ratio | 1.000 / 1.049 / 1.118 | 1.008 / 1.122 / 1.235 | 1.015 / 1.159 / 1.348 |
| TB responses issued = completed, total | 1,454,789 | 1,479,826 | 1,469,965 |
| RR turns ended: expired / emptied | 143,458 / 8,870 | 144,539 / 15,208 | 143,130 / 15,189 |
| Expired with a same-edge replacement push | 127,950 | 128,983 | 126,295 |
| Final-head fire + replacement, turn continued | 1,345 | 1,333 | 573 |
| Skip / wrap offers | 4,139 / 1,783 | 8,149 / 2,826 | 9,664 / 2,803 |
| Held-grant fires with a different candidate (charged to the held source) | 25 (11 runs) | 39 (13 runs) | 56 (12 runs) |
| Same-source renewal after expiry | 337 (13 runs) | 356 (12 runs) | 251 (7 runs) |
| Full-plus-pop refusals (each followed by ready) | 275,853 | 271,411 | 265,928 |
| Input-hold obligation checks | 6,280,944 | 13,669,109 | 28,510,164 |

Fires per ended turn (1..10), summed per N:

| N | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| N4 | 4,917 | 1,612 | 876 | 543 | 329 | 244 | 148 | 121 | 80 | 143,458 |
| N8 | 8,524 | 2,901 | 1,475 | 808 | 507 | 325 | 298 | 202 | 168 | 144,539 |
| N16 | 9,330 | 2,046 | 996 | 754 | 578 | 440 | 414 | 337 | 294 | 143,130 |

Measured response, wait and drain totals over all 60 runs:
- 4,404,580 responses issued and completed exactly once;
- 516 drain-only accepts, all pushed, fired and answered;
- 48,460,217 input-hold obligation checks.

### Observed RR and FCFS numbers on identical intended traces

FCFS values are from M3-primary/20261016T014224Z_3877. This is only a comparison of observed data. It is not a fairness, throughput or PPA conclusion. Both runs use the saturated "primary" workload (M3 F1, retained by Codex as a labelled workload).

| Metric (per N, min / mean / max) | RR N4 | FCFS N4 | RR N8 | FCFS N8 | RR N16 | FCFS N16 |
| --- | --- | --- | --- | --- | --- | --- |
| Accepted pushes, total | 1,454,725 | 1,454,725 | 1,479,681 | 1,479,681 | 1,469,658 | 1,469,658 |
| Measured fires, total | 1,453,461 | 1,453,461 | 1,477,138 | 1,477,138 | 1,464,584 | 1,464,584 |
| Mean wait | 79.60 / 84.19 / 88.12 | 80.41 / 84.47 / 88.52 | 154.4 / 163.8 / 176.5 | 156.1 / 164.8 / 177.2 | 287.4 / 329.7 / 353.6 | 294.9 / 332.4 / 353.8 |
| P99 wait | 405 / 462.9 / 659 | 363 / 447.1 / 618 | 667 / 845.4 / 1,188 | 623 / 797.4 / 1,184 | 1,272 / 1,609 / 2,073 | 1,291 / 1,569 / 2,128 |
| Max wait | 1,349 / 1,767 / 2,592 | 1,265 / 1,604 / 2,417 | 1,263 / 2,098 / 2,821 | 1,164 / 2,006 / 2,793 | 1,854 / 2,637 / 4,169 | 1,591 / 2,474 / 4,092 |
| Min / max per-source service | 16,623 / 19,981 | 16,622 / 19,976 | 8,070 / 11,204 | 8,056 / 11,222 | 4,129 / 5,747 | 4,121 / 5,769 |
| Generation-to-acceptance mean | 8,897 / 13,230 / 18,000 | 8,896 / 13,230 / 18,000 | 6,815 / 12,010 / 16,030 | 6,814 / 12,020 / 16,030 | 5,916 / 12,010 / 15,440 | 5,930 / 12,020 / 15,450 |
| Full-plus-pop refusals, total | 275,853 | 1,186,157 | 271,411 | 1,278,203 | 265,928 | 1,321,670 |
| Drain-only mean wait | 39 / 42.9 / 48 | 49 / 60.1 / 63 | 73 / 76.2 / 83.3 | 112.4 / 119.7 / 126.4 | 124 / 144.1 / 151.9 | 216 / 239.5 / 250.1 |

Observations:
- Totals of accepted pushes, measured fires and censored samples are identical between the policies in 60/60 runs. Per-source pushes and per-source service differ in 60/60 runs.
- Generated-but-unaccepted totals are therefore also equal, but individual generation-to-acceptance samples differ.
- The per-run RR versus FCFS listing is in 04-fv-tabulate-audit-rerun.log.

### Commands (log directory .setup-logs/implementation/resume-20261016/m4-verify-opus-high-2/func-verifier/)

All commands ran as `wsl.exe -e bash -lc '<wrapper> <label> "<cmd>"'`. The wrapper sources scripts/wsl_env.sh and records the timestamp, command and exit code in commands.txt and NN-label.log.

1. `bash scripts/run_verify.sh M4-primary -j 14`: exit 0 (01-M4-primary-full60.log)
2. `bash scripts/run_verify.sh M3-primary -j 14`: exit 0 (02-M3-primary-full60-regression.log)
3. `python -I …/fv_m4_tabulate.py <M4-primary> <M3-primary new> <M3-primary accepted> <TSV> <out>`:
   - first attempt exit 1: a KeyError in func-verifier's own script after the audit lines (03);
   - rerun exit 0 (04-fv-tabulate-audit-rerun.log, fv-tabulate.json).
4. `python -I …/fv_m4_persource.py <M4-primary> <M3-primary new>`: exit 0 (05)

00-notes.txt records a host-side Git Bash path-conversion error. It occurred before the first launch reached WSL, so nothing ran. The directory also holds the git status/diff/patch and the sha256 records. The M4 unit and M4-q1 suites were not rerun, because no source changed after testbench-dev's passing runs. Their logs are in ../testbench-dev/.

### Not run / not claimed

The following are NOT_RUN:
- FAI_MAIN/FAI_ALG2 simulation, FAI stress, W = 5M;
- the FAI share of the 180-run matrix;
- integration across policies, mutation testing, numerical code/functional coverage;
- formal, CDC, UVM and SystemC;
- synthesis, STA, power, PPA and FastX.

No fairness, throughput or PPA conclusion is drawn. **Codex independent common/FCFS/RR review is now ACCEPTED**; see reviews/phase-4-rtl/codex-common-review.md. FAI was not started by this bounded continuation.

---

# History: superseded M4 checkpoints (kept for evidence pointers)

## Former model checkpoint 2026-10-16 (PARTIAL_MODEL_UNIT, superseded)

Sourced09db3330ff8d59f4a1735d905ac3243b9e0efca adds Claude-authored RrSwitchModel/turn-record oracle, model export and39 pytest cases. RR RTL e727ebaae310a2a039ee2592f564f894f9668c2a unchanged. Model derives polling from abstract open turn/source/fire count, reviewed common deques/hold and post-edge queue occupancy; it uses no timestamp representation. Tests include manually specified sequences, held actual-source mismatch, replacement/expiry boundaries, closed-form preloaded queue drains and model-free randomized service bounds/conservation. Generic model quanta3 are additional unit checks; approved RTL/top configurations remain10/1.

Native CLI2.1.301/plugin0.14.6 session24a5679a-23ab-420d-925a-85573a8b1d61 actually invoked rtl-p5s-func-verify and serial testbench-dev. Spec/read-write/WSL preflight passed. Claude ran39 RR pytest PASS (exit0); Codex independently ran all refc/tests with JUnit:93 =54existing +39RR, zero failure/error/skip. This is pure Python unit evidence, not RTL/reference comparison or new FIFO coverage. Codex's bounded model review found no new correctness-critical Spec contradiction; M4 acceptance remains pending actual simulation.

The native API then returned HTTP429 session limit, CLI exit1; reported reset2026-10-16T06:30:00+08:00. No current safeguards/authentication error or permission denial. Actual completed files/tests survive orchestration interruption. No RR cocotb/harness/runner/primary60 or final func-verifier exists yet. Global settings/RTL/spec/common tests unchanged; no waiver or fallback author. The runner's reference-test expected counts also need93 instead of54 when extending M4, alongside the previously recorded stale RR rejection registry.

Evidence: .setup-logs/implementation/resume-20261016/m4-verify-1/checkpoint/ and m4-verify-resume/testbench-dev/01-pytest-rr-model.log; independent artifacts/independent/m4/model-review/pytest.{xml,log}. Next task: preserve this model, finish RR cocotb/runner and real60-run primary matrix on unchanged intended traces; then independent common/FCFS/RR review before FAI. No new architecture decision, timing/area/power or measured RTL performance claim.

## Historical RTL-only checkpoint

Date2026-10-16 (Asia/Taipei). Frozen Spec v1.0:1af80967bbc2fb83224f4725c4fb450889e69c62. Partial RR source:e727ebaae310a2a039ee2592f564f894f9668c2a. M3/C1 is accepted at07d12ca/6bbc4bf; M4 is not functionally accepted.

## Actual native workflow

Native CLI2.1.299/plugin0.14.6 invoked rat-p4p5-impl-verify in fresh sessions bd7aa1c9-1b09-414b-adb6-2d33cdbbc476 and eff8d1e2-84d7-4f02-b864-a2b60de09c70. The first orchestrator stopped before rtl-coder delegation, with safety_stops=1. The fresh shorter retry delegated serial rtl-coder, which finished RR RTL and lint. The orchestrator then stopped with API safeguards reasoning_extraction before testbench-dev. No RR oracle, cocotb, runner extension,60-run campaign or final func-verifier was created/invoked. Global model/auth/routing settings unchanged. There is no current quota reset estimate for this error.

The root summary incorrectly said no lint ran. Child tool logs and independent Codex execution prove the actual strict lint/structural work below; that summary is corrected here. A CLI exit0 does not mean M4 completion.

## Source and bounded review

New rtl/common/cxl_rr_sched.sv; changed top and common/switch filelists. The shared descriptor FIFO, output hold controller and FCFS selector are unchanged. switch_top adds RR_QUANTUM default10, with supplementary1; external ports/timing/storage boundaries unchanged. The RR branch instantiates the scheduler; FAI variants remain explicitly unsupported.

Polling uses the beginning head-valid mask, circularly rotated from ptr_q, without bubbles. Only actual fire changes turn state, using actual grant_source rather than a candidate that may differ under hold. Used quota is preserved for the pointer's current source and starts0 for a skipped-to source. Post-edge occupancy includes accepted push and pop; quantum expiry or emptiness advances regardless of replacement on expiry. Reset clears pointer/usage. Candidate selection does not depend on ready/pop/push of that cycle. These are Codex static review observations, not verified RR behavior in simulation.

## Observed checks

| Check | Actual result |
| --- | --- |
| Claude standalone RR and integrated top strict lint | PASS N4/8/16,Q10/Q1, plus FCFS positive and explicit FAI/invalid-param checks; logs retained. |
| Codex independent strict Verilator lint | PASS15 configurations:6 RR standalone +6 RR top +3 FCFS top;0 warning/error. |
| Claude structural elaboration | Q10 N4/8/16 and Q1 N4/16: arrival counter/timestamp bank/FCFS selector absent; RR ptr/used and common descriptor/hold state present. |
| Positive FCFS control | Arrival metadata/selector present. Generated FCFS C++ models N4/8/16 byte-identical to pre-M4 source, per retained comparison log. |
| Existing M3 lint-only check | Positive FCFS lint and FAI rejection evidence only; now-obsolete RR rejection fails as expected after RR support, not a full regression. |
| RR model / cocotb / primary matrix | NOT_STARTED / NOT_RUN. |
| M4 final functional verification / synthesis / STA / power | NOT_RUN. |

Strict command: `verilator --lint-only -Wall -Wpedantic -Werror-IMPLICIT -f rtl/filelist_switch.f --top-module switch_top -GN_SRC=N -GPOLICY=1 -GRR_QUANTUM=Q`. Standalone uses common filelist,cxl_rr_sched top and QUANTUM; FCFS control POLICY0. No warning suppression or verification waiver.

Verible's unconfigured default style checker exits1 for naming/style conventions, including preexisting project L_ constants. This is recorded, not claimed PASS. Approved project naming overrides plugin/default style; no global config/RTL-style rewrite or new waiver was introduced. Required strict Verilator checks pass; actual hardware tests remain absent.

## Remaining gate

Runner currently still expects RR unsupported in M2/M3 and declares M4 implemented=false. Claude must update supported FCFS/RR to positive lint and retain six FAI XREJECT checks before current full suites can pass. Previous accepted M3 evidence refers to its recorded source, not a new post-M4 functional run. Preserve the accepted C1 input-hold/drain population semantics when generalizing the harness.

Next is focused Claude testbench-dev/func-verifier: independent abstract RR model, N4/8/16,Q10/Q1 directed/random/reference tests including held actual grant, exact quota and replacement boundaries, no metadata structural checks with FCFS controls, full60 RR primary runs with tracked identical intended hashes, and applicable FCFS regression. Codex independently reviews common/FCFS/RR before FAI. No new architecture decision needed; no fallback Codex RTL implementation.

Native logs/agent prompts, copies of sessions/children, complete task patch/hashes and manifest:.setup-logs/implementation/resume-20261016/m4-rr-2/checkpoint/. Claude lint/structural logs:../rtl-coder/. Independent strict lint:artifacts/independent/m4/lint/. Interactive continuation command is in docs/RESUME_CLAUDE.md. No FastX scheduler/PPA result.
