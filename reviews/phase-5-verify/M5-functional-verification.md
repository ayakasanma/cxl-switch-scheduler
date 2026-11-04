# M5 functional verification verdict (FAI-inspired Main) — final evidence review

- Date: 2026-10-17 (run IDs UTC).
- Reviewer: Claude RTL Agent Team `func-verifier`, native `--agent` invocation, `claude/claude-opus-5-5` at `--effort high`. This session's response records are all `claude-opus-5-5`.
- Upper spec: `specs/CXL_SPEC.md` v1.0 frozen at `1af80967bbc2fb83224f4725c4fb450889e69c62`. Sections 3-10 apply; §11 applies for NOT_RUN status only. Also applicable: specs/APPROVAL.md, AGENTS.md.
- Source under test: `cefbbb0bda8dab21c9dd962378041fc5e0c4a426`. The 144 tracked files match the launch-time sha256 and git blobs, the working tree is clean, and the frozen spec diff is 0.
- Data and per-run detail: [docs/phase-5-verification/M5-integration-results.md](../../docs/phase-5-verification/M5-integration-results.md).
- Provenance:
  - Claude RTL Agent Team authored the RTL, models, testbenches, runner and the batch script.
  - The native detached launch failed (lost PID; preserved, no stage ran).
  - Codex ran the same verifier-authored `batch/run_batch.sh` in foreground WSL (exec session 76144) and independently audited the raw stress/primary/production evidence.
  - This reviewer did not execute the long batch and re-ran no functional test. The batch exit 0 is runner success only; this verdict is based on the original raw evidence.

## Verdict

**PASS_M5_MAIN_FUNCTIONAL** — functional verification of switch_top POLICY=2 (FAI-inspired Main) at N4/8/16, D16, M1, full105, within the requirement scope and limits below.

This is **not** whole-project completion. It does not cover:

- FAI Algorithm-2 (not implemented; rejected at elaboration);
- any synthesis/STA/power/PPA (all NOT_RUN);
- formal, CDC, SystemC, UVM, numerical coverage or RTL mutation (NOT_RUN/deferred).

No gate marker was reset and no PPA is approved. No new correctness-critical decision or contradiction with the frozen spec was found.

## Basis (raw evidence, independently parsed in this review)

| Check | Run (artifacts/implementation/) | Result |
| --- | --- | --- |
| Long stress, full matrix | M5-stress/20261017T013952Z_8032 | Exit 0, 37/37 steps. **30/30 tests, 0 F/E/S.** 30 unique (N, W, seed) with 30 distinct trace hashes. 18,000,000 measured trace cycles. All 16 measured Main transitions in **each** run (minimum count 2). Every mandatory bin and the exact full-plus-pop relations in both populations hold. Full-matrix gate `valid_runs 30`, `problems []`. |
| Stress initial failure | M5-stress/20261017T010035Z_1025 (ae5a682) | **7 FAIL / 9 executed, 21 NOT_RUN**: snapshot-population bookkeeping at the old `:121`. Repaired in cefbbb0 (TB only). The 9 overlapping configurations in 8032 have identical trace hashes and identical measured/whole-run coverage. Originally failing configurations record owed = 1; originally passing ones record owed = 0. |
| Seed-510 subset | M5-stress/20261017T011825Z_1587 | 6/6 simulations PASS. Gate FAIL as expected for the seed override. **Not counted as stress PASS.** |
| Primary, production W | M5-primary/20261017T015238Z_9805 | Exit 0, 67/67 steps, **60/60 tests**, 6,000,000 measured cycles. Hashes match the tracked TSV 60/60. The FCFS mirror checked every simulated cycle (6,011,803). Every common metric equals the accepted FCFS M3-primary/20261016T014224Z_3877 in 60/60. No window closes, so this is **not** classification evidence. |
| Production windows | M5-production/20261017T015838Z_13196 | Exit 0, 10/10 steps, **3/3 tests**. 20,000,000 real non-reset cycles per N = 4 complete W = 5,000,000 windows (60,000,000 in total). Per-window evidence and class maps were recomputed from raw B_close/S_close with exact integers and match. Held offer at boundaries 1/3, closing fire at 2/4. Conservation holds, with 0 outstanding. Peak RSS about 48 MiB per process. |
| Unit / regression at cefbbb0 | M1 …034126Z_13943, M2 …034156Z_14547, M3 …034300Z_16317, M4 …034404Z_18077, M4-q1 …034453Z_19058 | **286 / 526 / 550 / 430 / 195** tests, all 0 F/E/S. 3 ALG2 XREJECTs separate in M2/M3/M4. 0 lint diagnostics. No `-Wno-*`. |
| M5 unit | M5/20261017T012755Z_5680 (native) + M5/20261017T012115Z_2007 (Codex) | 805 each = 196 refc + 39 helpers + 570 cocotb; 27 strict lint, 9 probes, 3 XREJECT, 0 bad. The tested source equals cefbbb0 blobs. test_19 passes in 30/30. |

## Review of method (checked against source, not report text)

1. **Every-cycle checking cannot be disabled in long runs.**
   - `SwitchFaiTb.cycle()` drives only the top-level pins, then runs input hold, oracle comparison, the optional FCFS mirror and the model-free pin checks every cycle before the rising edge (`sim/common/switch_fai_tb.py:497-519`).
   - Infra smoke is off in all runs: `infra_smoke false`, and there is no `CXL_INFRA_SMOKE` in any command block.
2. **Production really simulates the edges.** The loop runs 20,000,000 iterations of `tb.cycle` (`test_switch_fai_production.py:139-202`). The sim time at each closing edge equals (k·W + 3) × 10 ns. The only internal write path, the sim-only timestamp-wrap `deposit`, is never used there. The production window is the RTL default with 23-bit widths asserted on the DUT.
3. **Stress repair is not a tolerance.** Exactly one assertion line was removed in cefbbb0, replaced by the exact relations `R+T+owed==F` (measured) and `R+T==F` (whole run). `owed ∈ {0,1}` comes from the observed boundary record, with first-drain pin checks. All other per-run bin assertions are unchanged.
4. **Threshold arithmetic.** `cxl_fai_main_sched.sv` uses `L_THR_W = 32` and zero-extends `b_close`/`s_close` before multiplying. An elaboration check enforces 10·N·W < 2³². There is no division, truncation or sign extension.
5. **Shared framework.** FIFO, out_hold, fcfs_sel, rr_sched and the package are unchanged since the accepted common review 23f8032. switch_top adds only the FAI policy slot, the FAI_W check and the policy-dependent opaque context width. Probes confirm:
   - FCFS/FAI arrival metadata present;
   - RR without `arrival_cnt_q`/`ts_mem_q`/`u_fcfs_sel`;
   - FAI 5-bit and FCFS/RR 1-bit held context.

## Requirement traceability (spec v1.0)

Status: **PASS** = met by actual evidence in this scope. **PARTIAL** = met with a stated limit. **NOT_RUN** / **N/A** as marked.

| Req (spec §) | Requirement | Evidence | Status |
| --- | --- | --- | --- |
| §3 | Full 105-bit descriptor stored and transported intact | Walking ones/zeros: M5 test_16, M3 test_11, M4 test_11. Scoreboard compares all 105 bits on every fire in stress/primary/production. | PASS |
| §4 | push/fire definitions, in_ready from beginning-of-cycle occupancy, full refuses even with same-edge pop | M5 test_14, M3 test_07, M4 test_07. Stress `full_refused` > 0 with an exact follow-up relation in 30/30. Production per-cycle checks. | PASS |
| §4 | No empty-FIFO bypass; eligibility next cycle | M5 test_15, M3 test_06, M4 test_08. `min_wait == 1` in all 30 stress runs and in production. | PASS |
| §4 | Producer hold until push; output stall stability (valid, 105 bits, source, context) | Input-hold checker every cycle (production 515,008 / 683,340 / 600,859 checks). M5 test_18/19. Stress held-across-closing > 0 in 30/30. Production held offers at boundaries 1/3. | PASS |
| §4 | Per-source FIFO order; ≤ 1 fire per cycle; no loss/duplication | Pin-level scoreboard (order, conservation). Responses issued == completed == delivered in all runs. | PASS |
| §5 | Synchronous active-low reset clears state; all Main sources H; inactive handshakes in reset | M5 test_01, test_11. Stress resets mid-window / mid-visit / mid-hold / non-H / nonempty > 0 in 30/30. | PASS |
| §5 | One shared switch_top/FIFO/output controller; no policy-dependent stages; no control-only bubbles | Source diff (method item 5). Probes. Work-conservation pin check. Primary FCFS mirror equality over all cycles. | PASS |
| §6 | FCFS timestamp selection within class; ascending-ID ties; modular age; wrap | M5 test_12, test_13; M3 test_02-04, test_12. Stress `ties_in_class`, `class_over_age` > 0. | PASS |
| §6/§7 | RR has no timestamps or arrival selector; FCFS/FAI retain arrival metadata | M5 RR/FCFS context-control probes and FAI/FCFS metadata probes (M4, M5, M5-production). | PASS |
| §7 | RR q10 (and q1 supplement) behavior | M4 (430) and M4-q1 (195) at cefbbb0. M4-primary/20261016T013811Z_371 PASS 60. | PASS (primary run at a pre-FAI equivalent RR source; see limits) |
| §8.1 | W = 5,000,000; index advances every non-reset cycle incl. stalls | M5 test_07. Production closings at edges 5M/10M/15M/20M. Stress windows closed ≥ 80 % nominal with stalls. | PASS |
| §8.1 | Window-local B/S, closing fire included, clear after classify | M5 test_04. Production boundaries 2/4 closing fire, with S_close = ΣB_close. Stress `closing_fire` > 0. | PASS |
| §8.1 | Exact integer thresholds UP 10·N·B < 3·S, DOWN N·B > S, KEEP incl. equality, all N in the average | M5 test_05, test_06. Production evidence independently recomputed from raw counts for 4 windows × N4/8/16 and matching. | PASS |
| §8.2 | Main four-state table with prior-effective-class hysteresis; opposing/KEEP/S0 cancellation | M5 test_02 (all transitions directed). All 16 measured transitions in each of 30 stress runs. Production through real windows: downgrade 3/6/12, restoration 1/2/4, B_H/UP and B_H/KEEP cancellations 1/2/4 each. | PASS |
| §8.3 | 10/10 High/Low visits, relinquish, renewal without bubble, no banking | M5 test_03, test_09. Stress visit continue / expired / emptied / relinquished / replaced / renewal > 0 in 30/30. Primary High-quota expiry renewed without a bubble. | PASS |
| §8.3/§8.4 | Held grant keeps source/class/quota context across classification changes | M5 test_08, test_10. Stress `held_cls_change`, `held_fire_cls_differs` > 0 in 30/30. Production: held across boundaries 1/3; no class change for the held grant in production. | PASS (class-change case at W64/W256 and directed) |
| §8.4 | Closing-edge order (commit, closing counts, parallel classification, next-cycle visibility) | Oracle edge records vs RTL nets every cycle. M5 test_04, test_10. Production per-window assertions. | PASS |
| §8.5 | 23-bit B/S/index at production; ≥ 31-bit (32-bit) unsigned threshold intermediates | DUT width assertions (M5-primary, M5-production). RTL `L_THR_W = 32` with zero-extension and elaboration range check. M5 test_06. | PASS |
| §8.6 | Algorithm-2 distinct from Main; not substituted | POLICY=3 rejected at elaboration (3 XREJECT per scope). | N/A: not implemented (deferred by spec) |
| §9 | Independent Python models; cycle-level comparison | refc pytest 196 (incl. FAI Main model). Oracle compared every cycle in every cocotb run. | PASS |
| §9 | Directed test list | M5 tests 01-19, M3 tests 01-14, M4 tests 01-13, M1/M2 FIFO/common control. | PASS |
| §9 | 20 seeds × 100,000 cycles × 9 configurations = 180 primary runs | FCFS 60 (M3-primary 3877), RR 60 (M4-primary 371), FAI Main 60 (M5-primary 9805): **180/180 PASS**. Identical intended traces. | PASS (functional only; not PPA) |
| §9 | FAI stress W = 64 and W = 256 | M5-stress 8032, 30/30. | PASS |
| §9 | ≥ 1 W = 5,000,000 test spanning ≥ 3 complete windows per FAI N | M5-production 13196: 4 windows each for N4/8/16. | PASS |
| §9 | Scoreboards; TB tagged responses exactly once; delays never charge quota/B/S | Responses issued == completed, reordered > 0, cross-epoch > 0 (stress). Responses are TB-only. | PASS |
| §9 | Preserve source/config/seed/tools/logs; failed/absent runs not PASS | versions.txt, commands.txt, config.json, logs and JUnit in each run. Run 1025's failures are preserved and disclosed, and subset 1587 is not counted. | PASS |
| §10 | Accepted-transfer rate, push rate, mean/P99 waits incl. drain-completed and censored samples, per-source service, generation-to-acceptance, generated-but-unaccepted | Metrics JSON in each primary/stress/production run. Measured vs drain-only populations kept separate (primary 4,404,064 vs 516). | PASS (observed data; no fairness/throughput conclusion) |
| §9 optional | Formal/SVA, CDC, SystemC/BFM, UVM, numerical coverage thresholds | — | NOT_RUN (OPTIONAL_OR_DEFERRED) |
| — | RTL mutation testing | Earlier selected model mutants are not RTL coverage. | NOT_RUN |
| §11 | Nine-configuration DC/PT/SAED32 synthesis, STA, power, PPA | Remote templates lack nine-configuration parameter selection and a frozen timing profile. Host/user/auth/workdir/library path/pilot constraints are pending. | NOT_RUN |

## Remaining limits (stated, not waived)

- The original-paper behavior is owner-supplied. The single-output 10/10 alternation is a project reconstruction. No IEEE PDF was inspected, and no cycle-identical paper claim is made.
- Production uses one seed (509) per N and reaches 9/16 transitions, with no S0 and no held class change at a production boundary. Full transition and S0 coverage comes from W64/W256 stress and directed tests.
- The FCFS/RR primaries ran at 3019b71 plus RR TB files committed byte-identically in 75270b8. They were not re-run at cefbbb0; their paths are unchanged except for the FAI-only switch_top additions, and M3/M4/M4-q1 re-ran at cefbbb0.
- The stress peak RSS of up to 336 MiB is recorded only. The production RSS of about 48 MiB is a resource observation, not coverage or PPA.

## Recommendation

M5 Main functional evidence is complete for the scope above. Next, pending owner/Codex acceptance:

1. Codex independent audit of this review.
2. FastX access/capability checks and pilot-derived common SDC.
3. Parameterized nine-configuration synthesis scripts before any PPA run.

Algorithm-2 remains for after the nine Main configurations.
