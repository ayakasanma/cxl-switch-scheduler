> Codex addendum2026-10-15: this is the preserved Claude func-verifier report. Its raw test/evidence audit remains valid, but project acceptance is REVIEW_CHANGES_REQUIRED after independently reproduced C1 in reviews/phase-4-rtl/codex-fcfs-review.md. In particular, the input-hold statement below overlooks withdrawal at the measurement/drain boundary. Do not begin RR until Claude repairs C1 and required checks pass. No new architecture decision is needed; the saturated profile can remain labelled as such.

# M3 functional verification verdict (FCFS)

- Date: 2026-10-15 (Asia/Taipei)
- Reviewer: Claude RTL Agent Team `func-verifier`. This is an independent acceptance audit of the testbench-dev work plus a separate rerun of the M3 suite.
- Upper Spec: specs/CXL_SPEC.md v1.0, frozen at 1af80967bbc2fb83224f4725c4fb450889e69c62 (sections 3, 4, 5, 6, 9, 10). Acceptance criteria: blocks B-E of .setup-logs/implementation/resume-20261015/repaired-proxy/orchestrator/step2-testbench-dev-prompt.md. Block F was intentionally not requested.
- Scope: switch_top POLICY=0 (FCFS) with the shared cxl_fcfs_sel selector, common FIFOs and hold controller, at N = 4/8/16. RR, FAI and PPA are excluded.
- RTL under test: rtl/ unchanged since 99124df (sha256 identical before and after). Tree: HEAD b345968 plus the uncommitted testbench/runner files.
- Verdict: **PASS** for M3 FCFS functional verification within the B-E scope. One measurement-design decision (F1) is open for Codex/owner, and the Codex independent review is pending before M4. Data: docs/phase-5-verification/M3-results.md.

## Basis

- Independent rerun artifacts/implementation/M3/20261015T101013Z_277: exit 0, 47 steps (38 PASS, 9 XREJECT), 372 tests, 0 failures/errors/skips. The func-verifier parsed the 32 JUnit XML files independently and found 372 testcases and 0 bad results. The logs contain no %Warning/%Error/Traceback; the declared-rejection logs were checked separately and contain exactly the 10 declared diagnostics each.
- testbench-dev runs, re-parsed independently and in agreement with the runner tables:
  - M3/20261015T100746Z_3720: 372 tests.
  - M3/20261015T095912Z_273: 372 tests.
  - M1/20261015T100009Z_2120: 144 tests.
  - M2/20261015T100022Z_2712: 384 tests (3 FCFS positive lint, 9 XREJECT).
- The M3-primary/20261015T100412Z_272 evidence audit passed. It was not rerun:
  - 60 distinct (N, seed) runs, each with 100,000 measured cycles and 0 failures.
  - The scope gate passed, and every per-run JSON is consistent: conservation, responses, drain complete, every source served.
  - 3 trace hashes (N4/509, N8/518, N16/528) were recomputed in WSL from (seed, N, cycles, profile) alone and equal trace_hashes.tsv.

## Audit against blocks B-E

1. **Oracle independence: OK.**
   - refc/cxl_model/fcfs_model.py:111-118 orders by `min((absolute push-edge index, source))` and contains no modular or MSB test.
   - The stored 32-bit value (`counter()`, :88-92) is used only to check head_ts and the counter.
   - The selector oracle (sim/cxl_fcfs_sel/test_cxl_fcfs_sel.py:36-40) also takes the minimum of absolute times.
   - A third, model-free FCFS rule derives order from the pin history (accepting cycle of each scoreboard head, sim/common/switch_fcfs_tb.py:425-436).
2. **Per-cycle comparison: OK.** On every cycle of every test, all pins plus head_valid, count, head_desc, head_ts, held, fire, pop, push, the FCFS candidate and the arrival counter are compared with the model (switch_fcfs_tb.py:326-366).
3. **Model-free pin rules: OK** (switch_fcfs_tb.py:386-442). They check:
   - in_ready derived from the pin-level beginning-of-cycle occupancy;
   - outputs and handshakes inactive in reset;
   - work conservation;
   - stall stability of valid, all 105 bits and source;
   - hold provenance;
   - that the offered descriptor is the oldest accepted descriptor of its source.
4. **Scoreboard: OK.**
   - Whole-105-bit per-source FIFO scoreboard, with conservation `accepted == delivered + dropped_by_reset + outstanding` (:529-532).
   - Fire wait >= 1 is checked on every fire (:451).
   - A full source with in_valid on its fire edge must refuse the push (:505-507), and must be ready on the next non-reset cycle (:495-499).
5. **Directed tests (test_switch_fcfs.py): OK.** Each test asserts literal expectations written from the spec:
   - reset, ports, widths, structure and the counter starting at 0 (t01);
   - ties ascending (t02); older head beats a lower source ID (t03);
   - FIFO order interleaved with age (t04); counter advancing through a 300-cycle stall without preemption (t05);
   - no bypass for every source (t06); full-plus-pop refusal (t07); simultaneous push/pop (t08);
   - back-to-back fires with no bubbles (t09); reset mid-traffic, mid-hold and on a glitch pulse (t10);
   - walking 1s/0s over all 105 bits per source (t11).
6. **True wrap (t12): OK.**
   - The VPI deposit sets `gen_arrival_ts.arrival_cnt_q = 2^32-6` and the model mirrors it through `deposit_counter`, which is allowed only right after reset with everything empty. There is no port.
   - The stored values 0xFFFFFFFA..0xFFFFFFFF, 0..5 are asserted literally.
   - Order is pre-wrap then post-wrap, with >= 5 wrap-discriminating selections.
   - A second wrap is exercised under 1500 random cycles.
7. **TB-only responses: OK.** sim/common/tag_response.py:
   - only consumes fires and never writes a DUT handle;
   - is keyed by (epoch, tag), rejects outstanding reuse and (in trace runs) any reuse in the run, and matches exactly once in seq order;
   - has asserted reorder and cross-epoch bins.
8. **Intended traces and acceptance: OK.**
   - sim/common/traffic_trace.py:148-220 is a pure function of (seed, N, cycles, profile), with a hashed canonical header that includes the full profile configuration.
   - `Producers` holds valid and data until push and records the push cycle separately (AcceptRecord).
   - Measurement, drain and censored samples are reported separately (switch_fcfs_tb.py:582-707), and drain fires are excluded from the rate.
9. **Runner: OK.**
   - Fail-fast is kept, and SIM_STRICT_FLAGS is unchanged.
   - M2 now runs strict positive FCFS lint. The 9 RR/FAI XREJECT steps carry exact `expect_undriven`/`expect_unused` sets and still count 0 tests.
   - The M3 pytest counts (54/18) and cocotb counts (7/13) are pinned.
   - The M3-primary scope gate (run_verify.py `primary_scope_step`) FAILs on a missing, overridden, lint-only or short run, or on a hash mismatch. Failure evidence shows it working: 100158Z_4684 (seed override) and 100230Z_4891 (lint-only) both exit 1.
10. **Forbidden-construct grep: clean.**
    - No `-Wno-`, `lint_off`, xfail/skip or waivers; SIM_BUILD_RELAXATIONS is empty.
    - The only `except` blocks in the runner turn errors into FAIL.
    - `# fmt: skip` appears, but it is a formatter directive only.

## Assertion changes made by testbench-dev after failures

| # | Change | Judgment |
| --- | --- | --- |
| 2 | test_12 checked head_ts of every "hi" source. At N16 only 6 of the 8 hi sources receive a pre-wrap push, so invalid heads were read. Now only pushed sources are checked, plus an exact `head_valid` mask assertion (test_switch_fcfs.py:454-460). | **Legitimate correction, and stronger than before.** The old check read invalid FIFO heads, which the spec says need not hold data. The new exact mask catches spurious heads, and the model already compares head_ts on every valid head every cycle. |
| 3 | test_13 asserted `ready_after_full_fire == full_refused`. It now asserts `ready_after_full_fire + full_fire_then_reset == full_refused` (test_switch_fcfs.py:515). | **Legitimate.** When a full fire is followed by a reset cycle, in_ready is low because of reset (spec 5), so it cannot count as ready. The rule itself is still asserted unconditionally on every non-reset cycle after a full fire (switch_fcfs_tb.py:495-499). The reset branch counts the case (:394-395), so the bins still account for every refusal. The primary test, which has no resets, keeps the strict equality (test_switch_fcfs_primary.py:72). |
| 5 | The primary test asserted `min_wait == 1`; it now asserts `min_wait >= 1` (test_switch_fcfs_primary.py:77). | **Legitimate, a reduction in stimulus coverage only.** No-bypass (wait >= 1) is enforced on every fire (switch_fcfs_tb.py:451), and the per-cycle model comparison would expose a missing one-cycle path. An exact wait of 1 is only reachable when the switch drains and then receives a push with ready=1, which saturated traces may never produce (see F1). In the final run min_wait > 1 occurs in 9 of 60 runs, not only N4/518. The exact 1-cycle minimum stays mandatory in t06 (:281) and t13 (:519). |

## Requirement / feature traceability

| Spec item | Requirement | Tests | Result |
| --- | --- | --- | --- |
| 3 | Ports and widths; 105 bits intact; no debug/preload port | t01 check_ports/hierarchy, t11 walking 1/0 per source, scoreboard whole-descriptor | PASS (N4/8/16 x 5 seeds) |
| 4 | push = valid & ready; in_ready from beginning-of-cycle occupancy < 16 | model comparison + pin rule every cycle; t07 | PASS |
| 4 | Full FIFO refuses push on its pop edge; ready next cycle | t07, pin rule (:495-507), t13/primary bins | PASS |
| 4 | No empty-FIFO bypass (fire at c+1 at the earliest) | t06 every source, wait >= 1 on every fire | PASS |
| 4 | Simultaneous push/pop; per-source FIFO order | t08, t04, scoreboard | PASS |
| 4 | Stall holds valid, 105 bits and source; no preemption; FIFOs still accept during stall | t05 (300-cycle stall), pin stall rule, hold bins | PASS |
| 4/5 | At most one fire; back-to-back without bubbles; work conservation | t09, pin work-conservation rule, drain no-bubble assertion | PASS |
| 5 | Synchronous active-low reset; handshakes inactive; state, hold and counter cleared; new epoch | t01, t10 (mid-traffic, mid-hold, glitch pulse), t13 random resets | PASS |
| 6 | 32-bit counter from 0, +1 every non-reset edge incl. stalls; push stores pre-edge value; same-cycle pushes share one ts | t01, t05, t02, per-cycle counter compare | PASS |
| 6 | Oldest eligible head wins; equal ts -> ascending ID; ineligible never wins | t02, t03, selector t01-t07, pin FCFS rule | PASS |
| 6 | Modular order inside a < 2^31 window; true wraparound directed test | selector t05-t07 (windows straddling 2^32, gaps up to 2^31-1), switch t12 (VPI deposit) | PASS |
| 9 | Independent Python model; cycle-level comparison; no copied RTL control | fcfs_model.py + 54 pytest; per-cycle compare | PASS |
| 9 | Scoreboards: integrity, conservation, no loss/duplication, order, policy selection | switch_fcfs_tb.py layers 2-3 | PASS |
| 9 | TB tagged responses exactly once; unique outstanding tags; reset epochs | tag_response.py, 18 pytest, t10/t13 bins | PASS |
| 9 | 20 seeds 509..528 x 100,000 active cycles, no warmup, bounded ready/stall + directed long stalls, drain separately | M3-primary 60 runs, scope gate | PASS (N4/8/16; FCFS share of the 180-run matrix) |
| 9 | Identical intended traces reusable across policies | trace hashes in tsv/JSON, 3 recomputed, pytest goldens | PASS |
| 10 | Rate, push rate, mean/P99 wait with censored/drain labels, per-source service, gen-to-accept, unaccepted | fcfs_primary_metrics.json x 60, primary_summary.json | REPORTED (see F1 on interpretation) |
| 9 | FAI stress, W=5M, RR/FAI policies | none | NOT_RUN (out of M3 scope) |

## Findings

### [Medium, decision for Codex/owner] F1: the primary profile is permanently saturated

**Observation.** Across the 60 runs, offered generation is 0.907-1.074 descriptors/cycle while downstream ready is 0.705-0.808/cycle. As a result:
- At least one FIFO is full in 92-99.97 % of measured cycles, and all FIFOs are full in 14-29 %.
- Mean acceptance-to-fire waits (84.5 / 164.8 / 332.4 for N4/8/16) are close to the Little's-law saturation value of about N*16/rate (88 / 173 / 350).
- The producer backlog grows through the whole run: 13.8k-37.8k generated-but-unaccepted, and generation-to-acceptance means of 5.9k-18k cycles. These two metrics depend on run length and are not steady-state values.

**Against spec 9/10.** This is not a violation. The spec fixes no load level. It requires comparable intended traces, a fixed offered-traffic interval, and separate reporting of the unaccepted backlog, and all three are met. Overload phases were explicitly required by block B.

**Consequences.**
- Under constant saturation, policy comparison of the *mean* wait is largely set by FIFO depth. Differences will mostly appear in P99/max wait, per-source service and backpressure distribution.
- Every source still receives service in every run.

**Options.** Keep the profile as the saturation/backpressure profile and label it as such in M4+ comparisons, or add a separately named sub-saturation profile. Adding a new profile name leaves the "primary" hashes unchanged. Changing "primary" would invalidate all 60 recorded hashes and the pytest goldens.

**Decision status.** Not changed by this audit. [RAT: DECISION | AGENT_ASSUMED] Treated as non-blocking for M3 functional acceptance, because correctness checking does not depend on the load level.

### [Low] F2: the min_wait relaxation is broader than first reported

The primary `min_wait >= 1` change is legitimate (see the table above). However, the first fail-fast run reported only N4/518. The final run shows min_wait > 1 in 9 of 60 runs: N4: 518; N8: 514, 515, 518; N16: 519, 521, 522, 526, 528. This follows from F1 and is recorded in M3-results.md.

### [Low] F3: hash reproducibility across sessions rests on short goldens

The scope gate regenerates hashes with the same traffic_trace module. That proves the run replayed the intended trace, but it would not detect a later edit to the generator. Cross-session stability is pinned only by three 3000-cycle golden hashes (sim/common/tests/test_traffic_trace.py:27-31).

**Recommendation (not applied):** M4 should compare its regenerated hashes against the recorded artifacts/implementation/M3-primary/20261015T100412Z_272/trace_hashes.tsv, or pin at least one 100,000-cycle primary hash in pytest.

### [Low] F4: a runner crash in the scope step leaves summary.json at RUNNING

Sizing run M3-primary/20261015T100116Z_4475 crashed with KeyError 'log', since fixed. It left `overall=RUNNING`, `milestone_acceptance_scope=false`, and process exit 1. Nothing was mislabelled as a pass. However, `primary_scope_step` runs outside the per-job exception guard, so any future exception there would again leave a non-final summary instead of FAIL. This is not a masking defect; it is noted for Codex.

### [Info] F5: no mutation evidence

Block F was not run, so the tests have not been shown to fail on targeted RTL mutations: inverted tie-break, plain unsigned compare, or a frozen counter. Non-vacuity rests on reading the code: unconditional literal assertions, asserted coverage bins, and three independent ordering oracles. A Codex mutation spot-check is recommended before M4.

### [Info] F6: no RTL defect and no test or runner change

No RTL defect was found, and no test, model or runner change was made by this audit. Two notes:
- The plugin's RTL verify-gate hook asked for `.rat/state/rtl-verify-done` to be touched. That is forbidden by the assignment and was not done.
- The rerun updated the ignored file artifacts/implementation/M3/latest.txt.

## Not covered by this verdict

The following were NOT_RUN:
- block F mutation;
- code/functional coverage numbers (none were measured);
- formal/SVA, CDC, UVM, SystemC;
- RR/FAI_MAIN/FAI_ALG2 simulation (only the 9 XREJECT elaboration rejections exist, and they are not simulation passes);
- FAI stress and W=5M tests;
- the nine-configuration sweep, synthesis/STA/power/PPA, and the remote scheduler.

The func-verifier did not rerun the 60-run primary campaign; it audited the evidence instead.

## Verdict

PASS for M3 FCFS functional verification within the B-E scope. The basis is the independent rerun (372/372), the audited 60-run primary campaign and 3 recomputed trace hashes. The three post-failure assertion changes are legitimate corrections. F1 is open as a measurement-design decision. The Codex independent review is pending and must be completed before M4 begins.

---

## C1-repair verification addendum (2026-10-16, Asia/Taipei)

- Reviewer: Claude RTL Agent Team `func-verifier`. This is an independent Tier 3 rerun and review of the testbench-dev C1 repair. func-verifier did not author the repair.
- Upper Spec: specs/CXL_SPEC.md v1.0 (1af8096), section 4 (input/output hold) and sections 9/10 (measurement). Requirement source: reviews/phase-4-rtl/codex-fcfs-review.md C1, "Required focused Claude repair".
- Tree: HEAD 764a074 plus uncommitted changes to `sim/common/switch_fcfs_tb.py`, `sim/switch_top_fcfs/test_switch_fcfs.py` and `scripts/run_verify.py`, and the new files `sim/common/input_hold.py` and `sim/common/tests/test_input_hold.py`. `docs/IMPLEMENTATION_RESULTS.md` has an edit by Codex that this review did not touch. RTL, spec, refc and the trace generator (`traffic_trace.py`, `tag_response.py`) have no diff against HEAD.
- Data and commands: docs/phase-5-verification/M3-results.md, section "2026-10-16 C1 repair". Command log: .setup-logs/implementation/resume-20261016/c1-repair-2/func-verifier-commands.log.

### C1 requirement check (diff review)

| C1 requirement | Evidence in the diff | Status |
| --- | --- | --- |
| Input valid/data stability is tracked from observed pins over every non-reset cycle, including drain entry and completion, and the assertion stays active | `SwitchFcfsTb.cycle()` calls `_input_hold_check` on every cycle and has no switch. The check reads `dut.rst_n` / `i_in_valid` / `i_in_desc` in ReadOnly, asserts they equal the driven values, and steps `InputHoldChecker` with the pin values and the sampled `o_in_ready`. Every other input-driving path goes through `cycle()`; the only direct pin writes are in `start()`, during reset. Drain entry is checked: the first drain cycle checks the last measured cycle's obligations, with 44 drain checks for N4/509 and 8,918 over 60 runs. Drain exit is checked too: the loop runs while obligations are pending, `assert not in_hold.pending` follows, and the idle and response-wait cycles are still checked. The existing tests 1-13 run with the checker on and pass without stimulus changes. | MET |
| The already-offered, blocked request is held until push, and no new backlog is released | `drain()` drives only `in_hold.obligations()`. `run_trace` asserts that each obligation is that source's producer head, and `on_drain_cycle` rejects any drain-cycle valid from a source that owed nothing or was already pushed. test_14 checks this pin by pin, including a refusal on a full FIFO with a pop at the first drain edge, and checks that the never-offered source stays at valid=0. | MET |
| Measurement statistics are frozen, drain pushes are recorded separately, measured accepts are distinguished from drain-only accepts, and generated-but-unaccepted is snapshotted at the boundary | `pushes_src` / `gen_to_accept` are appended only in the trace loop. `on_fire` classifies each fire as measured, drain-completed (accepted in measurement) or drain-only. `completed = waits_meas + waits_drain`. The new `drain_only` block is reported separately. Independently confirmed with 0 measurement-metric differences against the pre-repair run in all 60 runs. | MET |
| Every tag response is resolved exactly once without mixing populations | `tb.resp.issued == completed == fires_m + fires_drain + pushes_d` is asserted in every run_trace, and TagResponder checks for exactly-once responses. Confirmed in all 60 JSONs: 4,404,580 issued = completed, including 516 drain-only. | MET |
| A deterministic boundary regression is added, and the independent diagnostic is reused | test_14 runs in every M3 switch run (15 runs). The unchanged Codex diagnostic now passes; it previously failed at cycle 22. | MET |
| M3 and the 60-run primary matrix are rerun, and the intended hashes stay identical | See the next section. | MET |
| Codex diagnostic is not modified, its assertion is not suppressed, and the protocol is not waived | The file mtimes come before the failing Codex run, and the sha256 values were recorded before and after this rerun. Its wrapper intercepts `tb.cycle`, which `drain()` uses through the instance attribute, so the assertion is exercised. | MET |
| The trace generator and measurement stimulus are unchanged | `traffic_trace.py` has no diff. The trace-loop push/ready/reset code in `run_trace` is unchanged. Hashes match 60/60, and measured metrics are bit-identical to the pre-repair run. | MET |

### Independent rerun (real WSL, func-verifier)

| Check | Run dir (artifacts/implementation/) | Result |
| --- | --- | --- |
| Strict lint (M3) | M3/20261015T175152Z_1799 | 6/6 PASS; 9 XREJECT (0 tests) |
| Model/trace pytest | same | 77/77: 54 refc + 23 trace/util/input-hold; 0 fail/error/skip |
| cocotb | same | 315/315: 105 selector + 210 switch_top (14 tests x 3N x 5 seeds); 0 fail/error/skip |
| M3 total | same | **392 PASS, 0 failure / 0 error / 0 skip** |
| Codex diagnostic (unchanged launcher) | M3-review-boundary/20261015T175255Z_3947 | lint PASS; **1/1 PASS** |
| Primary matrix | M3-primary/20261015T175309Z_4038 | lint 3/3; **60/60 PASS**, 0 fail/error/skip; 6,000,000 measured cycles; the JUnit seed property matches every run |
| Trace hashes vs reviews/evidence/M3-primary-v2-trace-hashes.tsv | same, via fv_compare_primary.py | **60/60 identical** |
| Measurement metrics vs pre-repair 20261015T100412Z_272 | same | 0 differences |
| Full metrics vs testbench-dev 20261015T174542Z_2220 | same | 0 differences (deterministic) |

No -Wno, waiver, skip/xfail or gate-marker reset was used. No runs were repeated beyond this single rerun.

### Observations (non-blocking)

- [Info] O1. The pin read-back happens in the same ReadOnly phase as the TB's own drive, so it confirms delivery to the DUT pins rather than independent producer behaviour. The hold obligation itself is derived from pin values and the DUT's `o_in_ready`, which is what C1 asked for.
- [Info] O2. Only the FCFS switch harness (`switch_fcfs_tb.py`) has `InputHoldChecker`. The M1 FIFO harness (`fifo_tb.py`) and the M2 common-controller harness (`common_ctrl_tb.py`) drive inputs directly and do not run it. That is outside C1's scope. The RR/FAI harnesses for M4 should reuse the shared checker from the start.
- [Info] O3. `generated_but_unaccepted` is a boundary snapshot that includes the 516 boundary-held requests later accepted in drain. The JSON note and `drain_only.generated_never_accepted` (1,525,154 over 60 runs) make the distinction explicit. Consumers should quote the field that matches their question.
- F1 (saturated primary profile) is unchanged, and the Codex review keeps it as a labelled workload.

### C1-repair verdict

**PASS** (func-verifier, functional evidence) for the C1 repair. The input hold from observed pins is unconditional on every non-reset transition, including drain entry and exit. The drain holds only boundary-refused offers and releases no backlog. Measurement metrics and the 60 intended trace hashes are identical to the pre-repair record. Drain-only accepts are separated, and every tag is answered exactly once. The Codex diagnostic is unmodified and passes. No RTL defect was found, and RTL is unchanged.

This is not project acceptance. **Codex independent acceptance of the C1 repair is still pending, and M4 (RR) must not start before it.** NOT_RUN: RR/FAI simulation, FAI stress/W5M, mutation and coverage numbers, formal/CDC, the nine-configuration sweep, synthesis/STA/power/PPA.
