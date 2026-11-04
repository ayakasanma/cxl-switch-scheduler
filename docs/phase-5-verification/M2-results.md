# M2 results — common output hold/stall controller + common FIFO integration

Date: 2026-10-13 (Asia/Taipei). Author: Claude RTL Agent Team `func-verifier` (independent acceptance audit and execution). Upper spec: specs/CXL_SPEC.md v1.0, frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Working tree: HEAD `b58b23e48627bd013269ecfc88ab9240d77bd25e` plus the uncommitted M2 changes listed in section 10. Everything below was executed and observed in the cited run directories; nothing unrun is reported as passing.

## 1. Scope and non-scope

In scope (M2 common blocks only):

- `rtl/common/cxl_out_hold.sv` — the one common output hold/stall controller (N_SRC 4/8/16, opaque CTX_W).
- Integration of N real `cxl_desc_fifo` + one real `cxl_out_hold`, verified through the simulation-only candidate-injection fixture `sim/cxl_common_ctrl/cxl_common_ctrl_fixture.sv` (wired port-for-port as `rtl/top/switch_top.sv` wires them; the policy-slot signals are fixture ports).
- Independent abstract Python model `refc/cxl_model/common_ctrl_model.py` and its pure-Python tests.
- `rtl/top/switch_top.sv` as a common shell: strict parse/type resolution ending in an explicit unsupported-policy rejection.

Not in scope / not claimed:

- NO scheduling policy is implemented (FCFS, RR, FAI Main, FAI Algorithm-2 are all explicit `$fatal`). The fixture is not a policy and not a functional switch baseline.
- `switch_top` was NOT simulated: every policy is intentionally unsupported until M3/M4, so it cannot elaborate. No functional switch result is claimed.
- No synthesis, STA, power, PPA, formal, CDC, UVM/SystemC, waveform review or numerical code-coverage run.

## 2. Tools (as recorded in versions.txt of the acceptance run)

Verilator 5.052 2026-09-05; Python 3.12.3; cocotb 2.1.0; pytest 9.1.1; GNU Make 4.3; g++ 13.3.0 (Ubuntu 13.3.0-6ubuntu2~24.04.1); Linux 6.6.87.2-microsoft-standard-WSL2 x86_64. Lint flags `--lint-only -Wall -Wpedantic -Werror-IMPLICIT`; simulation build `-Wall -Wpedantic -Werror-IMPLICIT --vpi --public-flat-rw`, `SIM_BUILD_RELAXATIONS` empty, timescale 1ns/1ps, no waves.

## 3. Commands

```
wsl.exe -d Ubuntu --exec bash -c 'set -euo pipefail; cd "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler"; source scripts/wsl_env.sh; bash scripts/run_verify.sh M2'
wsl.exe -d Ubuntu --exec bash -c 'set -euo pipefail; cd "/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler"; source scripts/wsl_env.sh; bash scripts/run_verify.sh M1'
```

Both are full default scope (no `--seeds`, `--lint-only` or `--keep-going`). Every individual tool command is in `commands.txt` of each run directory.

## 4. Runs and evidence

| Run | Executor | Scope | Exit | Result |
| --- | --- | --- | ---: | --- |
| artifacts/implementation/M2/20261013T062040Z_376 | testbench-dev, first cocotb debug run | M2 | 0 | green (earlier, shorter random tests) |
| artifacts/implementation/M2/20261013T062236Z_2136 | testbench-dev, author's full run | M2 full | 0 | PASS, 49 steps, 367 tests |
| **artifacts/implementation/M2/20261013T062752Z_279** | func-verifier, independent acceptance | M2 full | 0 | PASS, 49 steps, 367 tests, 0 failures/errors/skips |
| artifacts/implementation/M1/20261013T062340Z_3897 | testbench-dev rerun | M1 full | 0 | PASS, 13 steps, 127 tests |
| **artifacts/implementation/M1/20261013T062852Z_2130** | func-verifier, independent rerun | M1 full | 0 | PASS, 13 steps, 127 tests, 0 failures/errors/skips |

Each run directory holds config.json, versions.txt, commands.txt, summary.json, logs/ and junit/. The acceptance run additionally holds `independent-check/` (JUnit/log/exit-code parser and its output), `negative-control/` (section 8) and `task-evidence/` (section 10). The repeated runs are repetitions of the same scope, not additional distinct tests.

## 5. Results of acceptance run M2/20261013T062752Z_279

### 5.1 Strict lint (6 steps, all exit 0, zero `%Warning`/`%Error` lines)

| Top | Filelist | Parameters |
| --- | --- | --- |
| cxl_out_hold | rtl/filelist_common.f | N_SRC=4, CTX_W=5 |
| cxl_out_hold | rtl/filelist_common.f | N_SRC=8, CTX_W=1 |
| cxl_out_hold | rtl/filelist_common.f | N_SRC=16, CTX_W=3 |
| cxl_common_ctrl_fixture | sim/cxl_common_ctrl/filelist_fixture.f | N_SRC=4, CTX_W=4, TS_EN=0 |
| cxl_common_ctrl_fixture | sim/cxl_common_ctrl/filelist_fixture.f | N_SRC=8, CTX_W=6, TS_EN=1 |
| cxl_common_ctrl_fixture | sim/cxl_common_ctrl/filelist_fixture.f | N_SRC=16, CTX_W=1, TS_EN=0 |

DESC_W/DEPTH/TS_W stay at their package defaults (105/16/32) and are verified on the DUT pins by the tests.

### 5.2 Simulation (cocotb 2.1.0 on Verilator), seeds 509, 510, 511, 512, 513

Counts are from an independent parse of every JUnit XML (`independent-check/parse_junit.out`), not from the runner table; they agree with the runner table.

| Configuration | Parameters | XML files | Tests | Failures | Errors | Skipped |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| fixture N4 | N_SRC=4, CTX_W=4, TS_EN=0 | 5 | 75 (15 x 5) | 0 | 0 | 0 |
| fixture N8 | N_SRC=8, CTX_W=6, TS_EN=1 | 5 | 75 (15 x 5) | 0 | 0 | 0 |
| fixture N16 | N_SRC=16, CTX_W=1, TS_EN=0 | 5 | 75 (15 x 5) | 0 | 0 | 0 |
| standalone hold N4 | N_SRC=4, CTX_W=5 | 5 | 35 (7 x 5) | 0 | 0 | 0 |
| standalone hold N8 | N_SRC=8, CTX_W=1 | 5 | 35 (7 x 5) | 0 | 0 | 0 |
| standalone hold N16 | N_SRC=16, CTX_W=3 | 5 | 35 (7 x 5) | 0 | 0 | 0 |
| cocotb subtotal | | 30 | 330 | 0 | 0 | 0 |
| pytest refc/tests | 20 FIFO-model + 17 common-control-model | 1 | 37 | 0 | 0 | 0 |
| **Total** | | 31 | **367** | 0 | 0 | 0 |

Every cocotb XML records the requested seed on every test case; the same test-name set appears for all five seeds of a configuration. Each cocotb step recorded exit 0 for verilate, make and simulation, and its generated-model checks (`held_source_q` and `desc_mem_q` present; `ts_mem_q` present exactly when TS_EN=1) are OK. Random tests: 3 x 10,000 driven cycles per fixture configuration and seed, 12,000 per standalone configuration and seed, each asserting its mandatory Python event bins.

Log scan of this run: 0 `%Warning`/`%Error` lines in the 6 lint logs, the pytest log and the 30 cocotb build/run logs; 141 such lines exist only in the 12 `elab_reject_*` logs (12 USERFATAL, 45 UNDRIVEN, 72 UNUSEDSIGNAL, 12 exit lines), all on declared policy-slot pins. No Python traceback in any simulation log; every simulation log ends `TESTS=n PASS=n FAIL=0 SKIP=0`.

### 5.3 Expected-rejection checks — reported separately, NOT simulation passes

12 `elab_reject` steps: `switch_top`, N_SRC in {4, 8, 16} x POLICY in {0 FCFS, 1 RR, 2 FAI_MAIN, 3 FAI_ALG2}, strict lint command on rtl/filelist_switch.f. Each ended with Verilator exit 1 (non-zero by design), exactly one USERFATAL with the declared "policy ... is not implemented" message, and only UNDRIVEN/UNUSEDSIGNAL on the absent policy slot's own pins (`cand_valid`, `cand_source`, `cand_ctx`, `arrival_ts`; `head_ts`, `fifo_count`, `push`, `grant_ctx`, `grant_held`, `fire`). Status XREJECT. They contribute 0 tests and are not counted in the 367. They show only that the shell parses/type-resolves and refuses every policy; they are not functional evidence.

## 6. M1 rerun

Run M1/20261013T062852Z_2130: 13 steps PASS, 127 tests, 0 failures/errors/skips, all exit codes 0, no `%Warning`/`%Error` line in any log. Per configuration: cxl_desc_fifo TS_EN=0 45 tests (9 x 5 seeds), TS_EN=1 45 tests, pytest 37.

Why rerun: `rtl/filelist_common.f` (the M1 filelist) gained `rtl/common/cxl_out_hold.sv` relative to the verified M1 commit d0f2989, and `refc/tests` (the shared pytest target) grew. The FIFO RTL, FIFO tests and the M1 runner-table entries are unchanged (`git diff b58b23e -- scripts/run_verify.py` removes only the two lines of the former M2 placeholder). The total moved from 110 to 127 solely because the pytest target now contains the 17 new common-control model tests (20 -> 37); the cocotb FIFO count is still 90. There are no new FIFO tests.

## 7. Requirement-to-test traceability (M2 contract items)

Fixture tests are `sim/cxl_common_ctrl/test_cxl_common_ctrl.py::test_NN`, standalone tests `sim/cxl_out_hold/test_cxl_out_hold.py::test_NN` ("hold NN"). "Harness" = checks in `sim/common/common_ctrl_tb.py` / `out_hold_tb.py` executed on every cycle of every test: (1) all pins vs the Python model, (2) model-free pin rules, (3) model-free pin-level conservation/order scoreboard.

| Spec | Contract item | Tests |
| --- | --- | --- |
| 3 | Port widths, 105-bit descriptor transported intact, source sideband | Harness `check_ports` + scoreboard on every fire; fixture 12; hold 06 (walking-1 over all 105 bits, every source) |
| 4 | Only fire dequeues; selection without acceptance never pops | fixture 02, 09; hold 02; harness `fire == out_valid & out_ready` |
| 4 | pop is one-hot for the offered source, only on fire | fixture 03; harness pop identity; hold 02, 03 |
| 4 | Stalled offer: valid, all 105 bits, source and context stable; candidate/arrivals cannot preempt | fixture 04 (400-cycle stall, 4 adversarial candidate kinds x 100, then 15 random-length stalls), 05, 10, 11; hold 03, 06; harness stall-stability on every held cycle |
| 4 | FIFOs keep accepting pushes during a stall; per-source order | fixture 05 (fill every FIFO to full while held), 04 part 2; random 13/14 bins `hold_push_any`, `hold_push_held_src`, `hold_all_full` |
| 4 | in_ready from beginning-of-cycle occupancy; full refuses push even when its head fires; ready next cycle | fixture 05, 08; harness in_ready rule; random 14 bins `fire_full_push_refused > 0`, `ready_after_full_fire == fire_full_push_refused` |
| 4 | Simultaneous push+pop table | fixture 07 (streaming), 08 (40 consecutive, storage wraps) |
| 4, 5 | No empty bypass and no extra output stage: eligible exactly at c+1 | fixture 06 (push at c with candidate+ready: no offer; fire at c+1, every source), 07; scoreboard `waited >= 1`; bin `min_wait == 1`; fixture 12 / hold 01 (only state: `held_q`, `held_source_q`, `held_ctx_q`) |
| 4, 5 | At most one fire per cycle, back-to-back without bubbles from the common path | fixture 07 (`b2b_fires == 4N-1`) |
| 5 | Synchronous active-low reset, outputs inactive in reset, reset mid-hold, fresh epoch, inter-edge pulse does not clear | fixture 01, 10 (step 3), 15 (`reset_during_hold > 0`); hold 01, 04, 07 |
| 4, 5 | Held grant set only by a stalled valid offer, released only by its fire or reset | fixture 09, 10; hold 05; harness hold-provenance rule on every cycle |
| 4 (stall clarification), 8.3 | Grant context retained across later context/classification changes; fire charged to the retained context | fixture 11 (64 cycles, same source other context; boundary context values), 04; hold 03 |
| 4, 5 (hold header) | Selected-head-valid invariant in the integrated framework | Harness asserts head of the held source valid and unchanged on every held cycle of every fixture test; model `_check_invariant` |
| hold header | Behaviour if an environment violates the invariant: no offer/fire/pop, grant stays held, released by fire after revalidation or by reset | hold 04, 07 (bins `held_head_invalid`, `held_head_invalid_ready`, `fire_after_revalidation` asserted > 0) |
| 5 | One common FIFO implementation + one common controller, same wiring as switch_top | fixture 12 (N `u_fifo`, exactly one `u_out_hold`, no state in the fixture); runner generated-model checks; line-by-line instantiation comparison (section 9, finding 1) |
| 6 (FIFO option) | Arrival timestamp travels with its descriptor when TS_EN=1 | Harness timestamp checks (fixture N8 only); pytest `test_ctrl_arrival_timestamp_follows_descriptor` |
| 9 | Independent Python model, cycle-level comparison | 17 pytest tests in refc/tests/test_common_ctrl_model.py; harness layer 1 |
| 4, 5 | Whole contract under random traffic, candidates, stalls, resets | fixture 13, 14, 15; hold 07 |

Policy-level items of sections 6, 7, 8 (ordering, quotas, windows, classification) have no M2 test: no policy exists.

## 8. Failures, defects and fixes across the M2 work

- No RTL defect was found by the tests or by this audit. `rtl/` was not modified by the verification agents.
- rtl-coder (before verification): made the held release explicit, `assign held_d = held_q ? !o_fire : stall;` (previously `held_d = stall`, which relied on the selected-head invariant), and corrected the policy-slot comments (fire-only accounting does not forbid reset, window classification/clear or empty-visit renewal). These address follow-ups 2-3 of reviews/phase-4-rtl/codex-common-review.md. Regarding follow-up 1: `fifo_count_t` and `ts_t` are defined in rtl/include/cxl_sched_pkg.sv (unchanged since commit d0f2989), and the 12 rejection logs of this run contain no type-resolution error — switch_top resolves them and stops only at the intentional policy `$fatal`.
- First cocotb debug run M2/20261013T062040Z_376 was green; the random tests were lengthened afterwards and the author's full run M2/20261013T062236Z_2136 was green.
- This acceptance audit: no failing step in either run, no test/model/runner defect requiring a change. No file under sim/, refc/, rtl/ or scripts/ was edited by the acceptance agent. A cosmetic defect in the acceptance agent's own one-off JUnit parser (it compared the per-test-case seed list with a one-element list and printed a false "MISMATCH") was corrected before the saved output; it never affected the runner.

Diagnostics (NOT acceptance evidence; mutated copies only in the WSL cache, repository `rtl/` byte-identical before/after, sha256 recorded):

| Diagnostic | Where | Suite | Result |
| --- | --- | --- | --- |
| control, unmutated copy | M2/20261013T062752Z_279/negative-control | final | runner exit 0, 13 PASS, 12 XREJECT |
| nc1 `held_d = stall` (release when the held head looks invalid) | same | final | runner exit 1; 3 standalone steps FAIL (tests 04 and 07, 2 of 7 each); 3 fixture steps PASS, as expected, because the real FIFOs never violate the invariant, so the mutant is equivalent there |
| nc2 `held_d = held_q ? !o_fire : o_out_valid` (hold set by an accepted offer) | same | final | runner exit 1; all 6 cocotb steps FAIL (fixture 14 of 15, standalone 7 of 7). Fixture test 10 passes because it contains no direct, unheld fire |
| m1 hold follows candidate; m2 pop without ready; m3 release when candidate drops | M2/mutation_check (testbench-dev) | earlier, shorter random tests | each runner exit 1, 6 of 6 cocotb steps FAIL; control exit 0 |

The negative control relied on for the final suite is the acceptance agent's own nc0/nc1/nc2 run (one seed, 509, `--keep-going`, seed override so by construction not acceptance scope). nc1 shows that the explicit-release behaviour is distinguishable only by the standalone invariant-violation tests, and that they do distinguish it.

## 9. Audit findings (independent, read-only)

1. Fixture fidelity — OK. The `cxl_desc_fifo` generate block and the `cxl_out_hold` instance of the fixture are connection-for-connection those of switch_top (same ports, same slices; `pop`/`head_*`/`fifo_count` are renamed to observation outputs, `arrival_ts`/`cand_*` to inputs). Differences are limited to the documented ones: CTX_W and TS_EN are fixture parameters (switch_top: L_CTX_W=1, L_TS_EN from POLICY). The fixture has no always block, no register, no selection logic; its only assign is `o_push = i_in_valid & o_in_ready`, identical to switch_top's `push`. It is listed only in sim/cxl_common_ctrl/filelist_fixture.f. switch_top's port list is exactly the spec section 3 list (clk, rst_n, i_in_valid, o_in_ready, i_in_desc, o_out_valid, i_out_ready, o_out_desc, o_out_source); all four policies and the default branch are `$fatal`; there is no dummy/default scheduler.
2. Model independence — OK. The model is queues plus one optional held-grant record with offer/commit methods; it shares no expression structure with the RTL (no one-hot decode, no head mux, no `held_d`). The harness compares every pin with the model on every cycle and separately runs model-free pin rules and a pin-level scoreboard built only from sampled pins and driven inputs.
3. Non-vacuity — OK. Directed tests assert literal expected tuples unconditionally; coverage counters used as preconditions are asserted (exact values in directed tests, mandatory bins at the end of every random test); there is no try/except, skip, xfail or early return in the tests or harnesses; `expect_tests` (15 and 7) equals the number of `@cocotb.test` functions. The negative controls confirm sensitivity, including for the invariant-violation behaviour.
4. Runner integrity — OK. LINT_FLAGS/SIM_STRICT_FLAGS unchanged by the diff, SIM_BUILD_RELAXATIONS empty, no `-Wno-*`, no `lint_off`/verilator pragma/`translate_off` in rtl/ or the fixture. Every exit code and JUnit file is judged (tests > 0, == expect_tests, failures = errors = skipped = 0, seed match). XREJECT steps carry no test count; overall PASS still requires no FAIL and no NOT_RUN step. An `elab_reject` step fails on exit 0, on a missing/duplicated USERFATAL, on any undeclared diagnostic and on an exit line that does not account for the diagnostics seen. M1 table entries are unchanged.

Observations that did not require a change: the pytest step only requires `min_tests >= 1` (the count 37 is not pinned by the runner; it is reported here from the XML); the simulation is 2-state Verilator without randomized power-up state, so reset is exercised from live non-reset states rather than from X.

## 10. Changed files and task evidence

Tracked, modified vs b58b23e: refc/cxl_model/__init__.py, rtl/filelist_common.f, scripts/run_verify.py. Untracked: refc/cxl_model/common_ctrl_model.py, refc/tests/test_common_ctrl_model.py, rtl/common/cxl_out_hold.sv, rtl/filelist_switch.f, rtl/top/switch_top.sv, sim/common/common_ctrl_tb.py, sim/common/out_hold_tb.py, sim/cxl_common_ctrl/ (fixture, filelist, tests), sim/cxl_out_hold/test_cxl_out_hold.py, this note and reviews/phase-5-verification/M2-functional-verification.md.

Inventory with sha256 and the full patch: `.setup-logs/implementation/resume-20261013/m2-changed-files.txt` and `m2-git-diff.patch` (ignored paths), copied to `artifacts/implementation/M2/20261013T062752Z_279/task-evidence/`.

## 11. Open items and NOT-RUN list

NOT_RUN / NOT_STARTED: switch_top simulation; FCFS (M3), RR (M4), FAI Main and Algorithm-2; integrated policy/response tests; the 120 FCFS/RR and 180 primary random runs (20 seeds x 100,000 cycles); FAI W=64/256 stress and W=5,000,000 tests; coverage metrics beyond the Python event bins (no line/toggle/FSM coverage); waveform capture/review; formal; CDC; synthesis/STA/power/PPA.

Known limitations of the M2 evidence:

- In the fixture TS_EN=1 is exercised only at N=8 and CTX_W=1 only at N=16 (the standalone hold covers CTX_W=1 at N=8). Other N x TS_EN x CTX_W combinations are not run.
- M2 unit runs use the 5 project seeds 509..513, not the 20-seed set required for primary configurations.
- Under strict lint, `head_ts` is reported UNUSEDSIGNAL in switch_top for a policy that does not read timestamps (visible today in the POLICY=1 rejection logs). RR in M4 will have to resolve this structurally (no warning suppression) while still containing no timestamp storage or counter.
- `switch_top` carries L_CTX_W=1; an FAI milestone must widen it there, the hold controller itself being width-generic (verified up to CTX_W=6).
- The remaining Codex follow-up 4 (FCFS/RR with independent models) and the full common-framework review before FAI are still open.
