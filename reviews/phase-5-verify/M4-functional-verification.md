# M4 functional verification verdict (Round Robin)

- Date: 2026-10-16 (Asia/Taipei). Run IDs are UTC: 20261016T0138Z is 09:38 Taipei.
- Reviewer: Claude RTL Agent Team `func-verifier`. This review is independent of the testbench-dev step. func-verifier did not write the RR testbench, runner, oracle or RTL, and changed none of them; sha256 was recorded before and after.
- Upper Spec: specs/CXL_SPEC.md v1.0, frozen at 1af80967bbc2fb83224f4725c4fb450889e69c62. Sections 3, 4, 5, 7, 9 and 10 apply. specs/DECISIONS.md D07, D10, D25, D26 and D32 also apply.
- Scope: switch_top POLICY=1 (RR) with the shared FIFOs, the shared hold controller and cxl_rr_sched, at N = 4/8/16. The primary quantum is 10. Quantum 1 (D32) is a separate supplementary scope. FAI and PPA are excluded.
- Source under test:
  - HEAD 3019b71, plus the uncommitted testbench-dev work: `M scripts/run_verify.py`, new `sim/common/switch_rr_tb.py` and new `sim/switch_top_rr/{test_switch_rr.py,test_switch_rr_primary.py}`.
  - RTL has no diff against e727eba, and the sha256 of every rtl/*.sv and filelist was the same before and after the campaign.
  - The RR oracle refc/cxl_model/rr_model.py has no diff against d09db33.
  - The frozen spec, the FCFS harness/tests, traffic_trace, tag_response, input_hold and reviews/evidence have no diff against HEAD.
- Verdict: **PASS** for M4 RR functional verification within the assigned scope. This is functional evidence, not project acceptance. **Codex must independently review the common framework, FCFS and RR before FAI begins.** Data: docs/phase-5-verification/M4-results.md.

## Basis (raw evidence, independently parsed)

| Check | Run (artifacts/implementation/) | Result |
| --- | --- | --- |
| RR primary matrix | M4-primary/20261016T013811Z_371 (func-verifier) | Exit 0. 67/67 steps: 3 strict RR lint, 3 FCFS metadata probes, 60 cocotb and the scope gate. **60 tests, 0 fail/error/skip.** The JUnit `random_seed` property equals the file seed in all 60. Logs have no `%Warning`/`%Error`/Traceback. |
| Intended-trace hashes | same | Each JSON `trace.sha256` and `trace_sha256` equals reviews/evidence/M3-primary-v2-trace-hashes.tsv in **60/60**. The runner's trace_hashes.tsv is byte-identical to the tracked TSV, and the scope gate reports `reference_hash_matches` 60. |
| FCFS regression (shared scope gate changed) | M3-primary/20261016T014224Z_3877 (func-verifier) | Exit 0. 64/64 steps, **60 tests, 0 fail/error/skip.** Hashes match the TSV 60/60. The full metrics JSON is **identical in 60/60 runs** (wall time excluded) to the Codex-accepted C1 run M3-primary/20261015T175309Z_4038. |
| RR unit suite, quantum 10 | M4/20261016T012639Z_374 (testbench-dev; not rerun, no source changed) | Exit 0. 41 steps: 35 PASS + 6 FAI XREJECT. **311 tests**: 93 refc pytest + 23 sim/common pytest + 195 cocotb (13 tests x N4/8/16 x seeds 509..513). Re-parsed: 17 XML files, 311 testcases, 0 bad. |
| RR supplementary, quantum 1 | M4-q1/20261016T012728Z_1477 (testbench-dev) | Exit 0. 24 steps, **195 tests**, 0 bad (re-parsed). |
| M1 / M2 / M3 regressions | M1 …012805Z_2386 (183), M2 …012826Z_2985 (423), M3 …012919Z_4752 (431) | All PASS. The counts reconcile: M1 144+39, M2 384+39, M3 93+23+105+210. Each switch_top milestone has exactly 6 XREJECT (FAI_MAIN/FAI_ALG2 x N) and 3 RR positive lints. |

Failed run kept as evidence: M4/20261016T012509Z_1035, 1 failure. See "test_12 bin relaxation" below.

## Review of the RR testbench and runner against the frozen spec (done before the campaign)

1. **Strict every-cycle oracle comparison: OK.**
   - `SwitchRrTb.cycle()` runs `_input_hold_check`, then `_check_against_model`, then `_pin_checks` on every cycle (switch_rr_tb.py:319-322). No test can switch these off.
   - The model comparison (:364-405) covers o_in_ready, o_out_valid, o_out_source and all 105 bits of o_out_desc when valid.
   - It also covers FIFO counts, head_valid and head descriptors, grant_held, internal fire/pop/push, the RR candidate valid/source, and the polling state `(ptr_q, used_q)`. The oracle's state is `(turn source, turn fires)`, or `(poll, 0)` when no turn is open.
   - The policy-slot head_ts is asserted 0, because RR has no metadata.
   - After each edge, `_check_edge` (:407-426) requires that the model's fired (source, desc), its turn event and its charged count equal the pin-level tracker's. It also requires that a fire whose candidate differs from the grant is a held grant, and that the model classifies it the same way.
   - The only skip is `state_known` before the first reset edge, when power-up state is unknown.
2. **Oracle independence: OK.**
   - rr_model.py is an abstract turn record (`poll`, `Turn(source, fires)`) built on the reviewed CommonCtrlModel. It has no pointer/used registers and no timestamps.
   - The RTL (cxl_rr_sched.sv) is a rotated priority encoder plus `ptr_q`/`used_q`, with `used_base = (grant == ptr_q) ? used_q : 0`. The oracle does not copy it.
3. **Model-free scoreboard: OK, independent of the oracle.** `_pin_checks` (:430-580) uses only pin values and its own per-source deques. It checks:
   - in_ready from pin-level beginning-of-cycle occupancy;
   - inactive outputs and handshakes in reset;
   - work conservation (`out_valid == any(occupancy)`, so no control-only bubble);
   - stall stability of valid, all 105 bits and source;
   - hold provenance;
   - that the offered descriptor is the oldest accepted descriptor of `o_out_source` (sideband, order and integrity, :506-512);
   - fire wait >= 1 on every fire (no bypass, :523);
   - full-plus-pop refusal and next-cycle readiness (:604-616).

   It also restates spec 7 over the pin history (:486-502, :536-571):
   - an open turn keeps the output; otherwise the first nonempty source from the polling position is offered;
   - a fire is charged to `o_out_source`;
   - a turn ends at the quantum even when a replacement keeps the source nonempty, or ends at post-edge pin occupancy 0;
   - reset polls source 0.

   Conservation (`accepted == delivered + dropped_by_reset + outstanding`) and exactly-once TB tag responses come from the reused FCFS methods and `TagResponder`. The responder never drives the DUT.
4. **C1 input hold and populations preserved: OK.**
   - `_input_hold_check`, `drain`, `finish`, `_close_epoch`, conservation and `run_trace` are the Codex-accepted SwitchFcfsTb implementations, bound unchanged (:186-192, :65-79). switch_fcfs_tb.py has no diff.
   - The checker runs on every cycle, including drain entry and exit. In the primary matrix it made 48,460,217 obligation checks.
   - Measured and drain-only populations are separated exactly as in M3. RR test_13 is the RR counterpart of the C1 regression, with literal push edges for each quantum.
5. **M2/M3 registry edits: no existing check weakened.**
   - RR changed from XREJECT to strict positive lint (`_switch_rr_lint`) in M2 and M3. `_UNIMPLEMENTED_POLICIES` now contains only FAI_MAIN and FAI_ALG2, which gives exactly 6 XREJECT with the unchanged exact UNDRIVEN/UNUSED sets.
   - The refc pytest count is now pinned at 93 in M1, M2, M3 and M4. Before, M1 and M2 had only `min_tests 1`, so this is stricter. sim/common is pinned at 23.
   - The FCFS cocotb entries, the M3-primary entry, SIM_STRICT_FLAGS and the empty SIM_BUILD_RELAXATIONS are unchanged.
   - The verilate and elab-check code was refactored into `verilate_cmd`/`run_elab_checks`. The refactor is byte-equivalent: same flag list, same checks.
   - The new `elab_probe` step (FCFS POLICY=0, N4/8/16) is a positive control. It proves that arrival_cnt_q, ts_mem_q and u_fcfs_sel ARE present where expected and u_rr_sched is absent, so the RR absence checks are meaningful.
   - No `-Wno`, `lint_off`, skip, xfail or waiver was found.
6. **M4-primary gate: OK** (run_verify.py `primary_scope_step` :1324-1390, `_load_reference_hashes`). The gate FAILs on any of:
   - `--lint-only`;
   - any `--seeds` override;
   - a missing or non-PASS (N, seed);
   - fewer or more than 60 valid runs;
   - a schema, seed, N, profile, requested or measured cycle count (100,000), or outstanding-after-drain value that differs from the declared one;
   - a JSON hash that differs from the runner's own regeneration;
   - a regenerated hash that differs from the tracked TSV;
   - a TSV that does not cover exactly the 60-pair matrix once each;
   - `policy` != RR, `policy_param` != 1 or `rr_quantum` != 10.

   testbench-dev's `--seeds 509` smoke run correctly FAILed the gate (14-…-not-evidence.log).
7. **test_12 bin relaxation: justified.**
   - In the failed run 012509Z_1035, N4 seed 511 passed every per-cycle oracle, pin and scoreboard check. It failed only the stimulus-reach bin `wrap_offers > 0`. Its log shows skip_offers 6, wrap_offers 0 and held_cand_mismatch 0, and 859 of 875 ended turns expired at the quantum in the saturated short trace.
   - The three bins made seed-dependent are asserted deterministically elsewhere, with literal expectations:
     - `wrap_offers >= 1` and `max_skip >= n-2` in test_04 (:282). Sources 0 and 2 are pushed while polling is at n-1.
     - `held_cand_mismatch == 2` in test_06 (:397), with literal held source, candidate source and charge.
     - `renew_same_source >= 3` with exact per-cycle `(ptr, used)` in test_09 (:478-484).
   - Every other test_12 bin stays mandatory, and the values are still recorded in rr_short_random.json.
8. **Required directed scenarios: all present, and each asserts literal spec-derived expectations for Q10 and Q1.**

| Required scenario | Test (test_switch_rr.py) |
| --- | --- |
| Reset to source 0 (Q1/D25) | t01 (state (0,0) after reset; order 1 before n-1; ascending order after reset), t10 |
| Exact successful-fire quota; Length cost-free | t02 (32 fires; exact source order and (ptr, used) per fire; histogram {10:2, 6:2}; Length 0xFF vs 0) |
| Stalls hold the offer and consume no quota | t03 (60-cycle stall with arrivals, including into the held source; state frozen; stall before the last fire of the turn) |
| Circular skips with no bubbles; all-empty retention | t04 (skip order, wrap, 400-cycle streaming fire-every-cycle), t09 |
| Post-edge replacement vs expiry | t05 A (final-head replacement continues q-1 times, expires at q), B (emptied turn), C (a push one cycle late does not reopen the turn) |
| Candidate change during a stall is charged to the actual held source | t06 (candidate moves to 0 while n-1 is held; charged=1 to n-1; emptied held-grant variant) |
| Full-plus-pop refusal | t07 (every source; refused on the pop edge; ready next cycle; turn bookkeeping unaffected) |
| No bypass | t08 (every source, including the polling position; wait exactly 1) |
| One / all active / all empty; single-source renewal | t09 |
| Reset mid-turn / mid-hold; reset pulse between edges | t10 (also no fire/pop on a reset edge with a ready unlocked offer) |
| 105-bit integrity | t11 (walking 1s/0s, every source), t01 structure (16 x 105 storage, no ts/counter/FCFS selector, RR regs exactly ptr_q/used_q) |
| Random stress, measurement-boundary C1 hold | t12 (short random), t13 |
| Q1 supplementary kept separate | Runner M4-q1 (quantum passed with -G); M4 uses the RTL default 10 |

Conclusion of the pre-campaign review: no concrete TB or runner defect was found, so nothing was changed and nothing needed a rerun before the campaign.

## Requirement traceability

| Spec item | Requirement | Evidence | Result |
| --- | --- | --- | --- |
| 3 | Ports and widths; 105 bits intact; source sideband; no debug port | t01 check_ports/structure, t11, scoreboard head-of-source check on every cycle | PASS (N4/8/16 x 5 seeds, Q10 and Q1) |
| 4 | push = valid & ready; in_ready from beginning-of-cycle occupancy | model and pin rule every cycle; t07 | PASS |
| 4 | Full FIFO refuses push on its pop edge; ready next cycle | t07; pin rule; 813,192 primary refusals, each followed by ready | PASS |
| 4 | No bypass (fire >= c+1) | t08; wait >= 1 on every fire (primary min wait 1 in 58/60 runs, otherwise > 1) | PASS |
| 4 | Stall holds valid, 105 bits and source; no preemption; FIFOs still accept | t03, t06; pin stall rule; 1,374,307 primary mid-turn stall cycles | PASS |
| 4 | Producer holds valid and data until push (C1), including at the measurement/drain boundary | always-active InputHoldChecker; t13; 48.46 M primary obligation checks; 516 drain-only accepts | PASS |
| 4/5 | At most one fire; no control-only bubbles; work conservation | pin rule `out_valid == any(occupancy)` every cycle; t04 streaming; drain fires every cycle | PASS |
| 5 | Synchronous active-low reset; RR pointer 0, used quota and hold cleared; handshakes inactive; new epoch | t01, t10 (mid-turn, mid-hold, pulse), t12 random resets | PASS |
| 5/11 | One common FIFO/hold framework; RR has no timestamp storage, arrival counter or oldest-head selector | t01 hierarchy; runner elab_checks (absent) with FCFS positive probes (present) at N4/8/16 | PASS |
| 7 | First nonempty source circularly from the polling position; skip empty sources | oracle candidate and pin tracker every cycle; t04; 7,412 primary wrap offers, 21,952 skip offers | PASS |
| 7 | At most 10 successful fires per turn (1 for Q1); Length does not alter cost | t02 literal; pin assert `1 <= charged <= q`; histogram max bin 10 | PASS |
| 7 | Advance at quantum or on emptiness | t05, t09; oracle and pin tracker; primary 431,127 expired / 39,267 emptied turns | PASS |
| 7 / Q2 | Emptiness after same-edge push/pop; final-head fire with replacement keeps the turn; expiry advances regardless | t05 A literal; primary 3,251 final-head-replacement continuations; 383,228 expiries with a same-edge replacement push | PASS |
| 7 | Stalls do not consume quota; held grant charged to the source that actually fired | t03, t06; `_check_edge` mismatch rule; primary 120 held-candidate-mismatch fires | PASS |
| 7 / Q2 | All empty: keep the polling position, consume no quota | t04, t09 (state literal over 12/20 idle cycles) | PASS |
| 7 / D32 | Quantum 1 is supplementary and separate | M4-q1 195 tests | PASS (supplementary) |
| 9 | Independent Python model with cycle-level comparison; no copied RTL control | rr_model.py + 39 pytest; per-cycle comparison including (ptr, used) | PASS |
| 9 | Scoreboards: integrity, conservation, no loss or duplication, order, policy selection | switch_rr_tb.py layers 2-3 | PASS |
| 9 | TB tagged responses exactly once; unique tags; reset epochs | TagResponder; t10/t12 cross-epoch bins; primary 4,404,580 issued = completed | PASS |
| 9 | 20 seeds 509..528 x 100,000 cycles per configuration, no warmup, identical intended traces, separate drain | M4-primary 60 runs; scope gate; hash 60/60 vs TSV | PASS (the RR share of the 180-run matrix) |
| 10 | Rate, push rate, mean/P99 wait with censored/drain labels, per-source service including zero, generation-to-acceptance, unaccepted | rr_primary_metrics.json x 60; tables in M4-results.md | REPORTED |
| 9 | FAI stress, W = 5M, FAI policies | none | NOT_RUN (out of scope) |

## Findings

### [Low] F1: primary stimulus bins are asserted on whole-run coverage, including the drain

test_switch_rr_primary.py:89-94 asserts `turns_emptied > 0` and similar bins on `tb.cov` after the drain. In N4 seed 518 the measurement interval has 0 emptied turns (7,215 expired), 0 skips, 0 wraps and min wait 10. Its 3 emptied turns occur only in the drain. This is the same saturated trace as M3 F2.

This is not a correctness gap:
- emptying is checked on every cycle by the oracle and the pin tracker;
- it is asserted literally in t05 and t12 (Q10).

The reported metrics use the measurement-only `coverage_measurement` and `rr_turns_measurement`. **Recommendation (not applied):** if Codex wants the primary bins to prove measurement-interval reach, assert them on `coverage_measurement`. As M3 F1 shows, saturated runs such as N4/518 would then need these bins to stay recorded rather than required.

### [Info] F2: the pin tracker and the oracle share one reading of spec 7

The pin-level turn tracker and rr_model.py come from the same author and encode the same Q2 interpretation. They are independent in their data sources (pin history versus model queues), not in how they formulate the rule. A misreading common to both would be caught only by the literal directed expectations (t02, t03, t05, t06, t09), which this review checked against spec 7 and Q2 and found correct.

### [Info] F3: identical RR/FCFS totals and different per-source distributions

On every (N, seed), RR and FCFS have identical total accepted pushes, measured fires and censored counts (60/60). Per-source pushes and per-source service differ in 60/60 runs.

This is consistent with:
- the shared, work-conserving datapath on an identical ready trace;
- sources that stay backlogged (at least one FIFO full in 92.5-99.97 % of measured cycles, every FIFO full in 13-28 %).

It is not a policy mix-up. Every RR cycle is compared with the RR oracle including `(ptr_q, used_q)`, the RR JSONs carry RR turn statistics, and FCFS-only bins (`counter_wraps`, `ties`) are absent from them. The equality is recorded as an observation; no throughput conclusion is drawn.

### [Info] F4: the M3-primary gate does not pin the tracked TSV

Only M4-primary declares `reference_hashes`. func-verifier checked the M3-primary rerun separately: 60/60 hashes match the TSV, and the runner TSV is byte-identical. Adding the same gate to M3-primary would be a strengthening. This was not applied, because M3 is accepted and was not part of this assignment.

### [Info] F5: no mutation evidence (carried over from M3 F5)

The RR suite has not been shown to fail on RR-specific RTL mutations. Examples: a quantum off-by-one, charging the candidate instead of the grant, pre-edge emptiness, or not resetting the pointer. Non-vacuity rests on the literal directed expectations and on the per-cycle `(ptr, used)` comparison. A Codex mutation spot-check is recommended before FAI.

### [Info] F6: no RTL defect; no TB, runner, model or RTL change by func-verifier

M3 F4 (an exception in the scope step leaves summary.json RUNNING) is unchanged. The plugin verify-gate marker was not touched.

## Not covered by this verdict

The following are NOT_RUN:
- FAI_MAIN / FAI_ALG2 simulation (only 6 XREJECT elaboration rejections exist);
- FAI stress, W = 64/256 and W = 5M;
- the remaining 60 runs of the 180-run nine-configuration matrix (Main FAI);
- integration across policies;
- mutation testing;
- code or functional coverage numbers (no numerical coverage was measured);
- formal/SVA, CDC, UVM and SystemC;
- synthesis, STA, power and PPA, and any FastX scheduler run.

The M4 unit and M4-q1 suites were not rerun by func-verifier. Their source is unchanged since the cited passing runs, and their raw JUnit was re-parsed.

## Verdict

**PASS** for M4 RR functional verification within the assigned scope. The basis is:
- a 60-run RR primary matrix with 0 failures and intended-trace hashes 60/60 identical to the tracked M3 record;
- an FCFS primary regression bit-identical to the accepted C1 run;
- unit and supplementary suites at 311 and 195 tests with 0 bad results;
- the M1, M2 and M3 regressions;
- a pre-campaign review that found no testbench or runner defect.

F1-F5 are non-blocking. **Codex independent review of the common framework, FCFS and RR is pending, and FAI integration must not begin before it.**


## Codex acceptance addendum 2026-10-16

This native verdict was written before Codex acceptance. Verification source is now committed as75270b8808946e880ca039a2fa06b629dff32cd8. Codex independently reran M4 PASS311 and M4-q1 PASS195, audited raw XML seeds/counts and all60 RR metrics/hashes, and verified all60 FCFS metric JSONs unchanged excluding walltime. Root and allthree native agents' actual returned models are Opus5.5; high effort was explicitly configured. Common/FCFS/RR gate ACCEPTED; F1-F5 remain labelled nonblocking limits, not unrun-test passes. Remaining primary matrix is Main FAI60, not120; all nine synthesis measurements remain NOT_RUN. No FAI or PPA started. See reviews/phase-4-rtl/codex-common-review.md.
