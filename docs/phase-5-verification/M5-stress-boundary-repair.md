# M5-stress measurement-boundary repair — functional verification report

Task: M5-stress-boundary-repair / func-verifier (verification of a testbench-only repair).
Date: 2026-10-17. HEAD `ae5a682` with an uncommitted testbench-dev repair in 3 files (manifest below).
Authority: AGENTS.md, frozen specs/CXL_SPEC.md v1.0 (§4, §8, §9/§10), docs/RESUME_CLAUDE.md, CLAUDE.md.
Evidence: `.setup-logs/implementation/resume-20261017/m5-stress-boundary-repair/func-verifier/`.

**Scope status.** M5 unit: VERIFIED PASS (below). The full 30-run M5-stress, M5-primary, M5-production
and M1-M4 re-runs were **NOT RUN** in this task. The repair is pending Codex independent review and
the final verifier. Nothing here is a claim about the long M5-stress batch passing.

## 1. Symptom

The long M5-stress run `artifacts/implementation/M5-stress/20261017T010035Z_1025` (logs
`.setup-logs/implementation/resume-20261017/m5-long-regression-1/`) failed 7 of the 9 runs that
executed. Fail-fast skipped the remaining 21. Every failure is at `test_switch_fai_stress.py:121`
(pre-repair):

```python
assert c["full_refused"] > 0 and c["ready_after_full_fire"] + c["full_fire_then_reset"] == c["full_refused"]
```

Here `c = metrics["coverage_measurement"]`. In every failing run the measured lag
`full_refused - ready_after_full_fire - full_fire_then_reset` is exactly 1. In every one of the 9 runs,
including the failing ones, the whole-run (`coverage_total`) lag is exactly 0 (table in §6).

## 2. Root cause (checked against the unchanged harness code)

- `sim/common/switch_fai_tb.py:999-1000`: `full_refused` is incremented in the fire cycle t, when the
  fired source's FIFO is full (`occ[src] == depth`) and `in_valid[src] = 1` (full-plus-pop: push refused).
- `sim/common/switch_fai_tb.py:960-961`: on that same condition, `prev = ("fire", src, refused)` is
  recorded, with `refused = src`.
- The follow-up is counted only on the next observed cycle t+1. `switch_fai_tb.py:989-993` counts
  `ready_after_full_fire += in_ready[src]` and also asserts that `in_ready[src]` is 1, unconditionally,
  on every cycle. `switch_fai_tb.py:759-760` counts `full_fire_then_reset` when t+1 is a reset cycle.
- `sim/common/switch_fcfs_tb.py:695` (`run_trace`): `cov_meas = tb.cov.as_dict()` is frozen right after
  the last measured cycle. The drain starts at `switch_fcfs_tb.py:722`, and `finish()` follows at `:725`.

So a full-plus-pop fire in the last measured cycle counts `full_refused` inside the snapshot, while its
follow-up lands in the first drain cycle, outside the snapshot. The output port fires at most once per
cycle, so at most one follow-up is owed across the boundary (0 or 1). This exactly accounts for a lag of 1.
The whole-run relation (`tb.cov` / `coverage_total`) is unaffected and was exact in all 9 original runs.

The same relation also appears at `test_switch_fai.py:899` (test_17), in the FCFS/RR unit tests, and
in `test_switch_{fcfs,rr,fai}_primary.py`. All of those evaluate `tb.cov` after `finish()`, the whole-run
population. The stress test was the only place where the relation was applied to the frozen
measurement snapshot.

## 3. Why the RTL and models are not implicated

- `rtl/`, `refc/`, `specs/`, `sim/common/switch_fai_tb.py`, `sim/common/switch_fcfs_tb.py`, AGENTS.md
  and CLAUDE.md are byte-identical to HEAD (`git diff --quiet HEAD` exit 0 for each; blob
  `d03e61c6…` / `f22f67c8…` for the two harness files).
  `git diff 1af80967bbc2fb83224f4725c4fb450889e69c62 HEAD -- specs/` is empty.
- Every per-cycle check stayed active through the failing runs and none fired. These checks include
  the unconditional "ready the cycle after a full fire" assertion (`switch_fai_tb.py:991`), the oracle,
  the pin/history trackers, the scoreboard and the input-hold checker. The failure was raised only by
  the end-of-run coverage-relation assertion.
- The whole-run relation is exact in all 9 original runs. Only the bookkeeping population differed.
- Seed-510 re-runs under the repaired test produce identical trace SHA-256 and identical
  `coverage_measurement` / `coverage_total` dictionaries to the failing run (§6). The DUT behaviour is
  unchanged, and only the check differs.

## 4. Fix, and why it is not a tolerance

The change is testbench-only. `sim/switch_top_fai/test_switch_fai_stress.py` adds:

- `observe_measurement_boundary(tb)` installs a test-local wrapper on `tb.drain`. The first call is
  run_trace's drain, entered right after the snapshot. On that call the wrapper records `tb.prev`, the
  coverage at entry, the input-hold obligations and the first drain cycle's observation. It then
  forwards the identical arguments and `on_cycle` to the original drain. The second call (`finish()`)
  is passed straight through.
- `owed` is set to 1 if `prev == ("fire", src, src)`, the same condition that incremented `full_refused`
  in the last measured cycle, and 0 otherwise. It is derived from observed state and is never a free
  allowance.
- `check_full_followups` asserts all of the following:
  - The observation is the exact freeze instant: `cov_at_entry == coverage_measurement`, and the
    boundary cycle equals `meas_end`.
  - The measured relation `R + T + owed == F` holds exactly.
  - The whole-run relation `R + T == F` holds exactly.
  - If `owed`, the first drain cycle has `in_ready[src] = 1` and `push[src] = 1` with the identical held
    descriptor, and `src` is in `boundary_held_sources`.
  - `drain_calls == 2`.
  - No follow-up is pending after `finish()`.
- Only the `:121` line changed. It became `assert c["full_refused"] > 0` plus `check_full_followups(...)`.
  Every other measurement-only bin assertion still uses `c = coverage_measurement`.

This cannot mask a defect. A missing or extra follow-up anywhere in the run breaks the exact
whole-run relation, and the per-cycle assertion at `switch_fai_tb.py:991` is untouched. A wrong
`owed` (for example 1 without a boundary full fire) breaks the measured relation by one in the other
direction, and when `owed = 1`, check (d) pins the actual first-drain-cycle pins.

`scripts/run_verify.py` changes only the count pin and its comments: `_M5_SWITCH_EXPECT_TESTS` goes
from 18 to 19.

## 5. Directed reproducer: `test_19_full_fire_last_measured_cycle`

The test is added to `sim/switch_top_fai/test_switch_fai.py`. test_18 is unchanged; the diff only appends.

- A 24-cycle trace drives one source. The first 16 pushes fill D16 while `ready = 0`, and the 17th
  descriptor is refused and held. The last measured cycle sets `ready = 1`, so the head fires from full
  with `in_valid = 1`.
- **Failing before:** the test evaluates the original `:121` relation on `coverage_measurement` and
  asserts it is False (`(F, R, T) == (1, 0, 0)`).
- **Fixed after:** `owed == 1`, and `check_full_followups` passes. The first drain cycle pushes the held
  descriptor, the whole run gives `(1, 1, 0)`, and the drain order has no bubble.
- The lazy import of `test_switch_fai_stress` inside the test body collects no extra test. All 30 unit
  JUnit files list exactly the same 19 names, with no stress test among them, and test_19 passed in all
  30 cocotb logs.

## 6. Verification runs

| Run | Command (WSL, `source scripts/wsl_env.sh`) | Exit | Result |
|---|---|---|---|
| M5 unit `artifacts/implementation/M5/20261017T012755Z_5680` (this verifier) | `scripts/run_verify.sh M5 -j 8 --make-jobs 2` | 0 | overall PASS, scope full, acceptance scope true, 90.1 s |
| M5-stress seed-510 override `artifacts/implementation/M5-stress/20261017T011825Z_1587` (testbench-dev, re-checked read-only) | `scripts/run_verify.sh M5-stress --seeds 510 -j 6 --make-jobs 2` | 1 | 6/6 cocotb PASS, 0 failures; scope gate FAIL only because of the seed override |

M5 unit counts (from summary.json, cross-checked against the 32 JUnit XMLs):

| Item | Expected | Actual |
|---|---|---|
| refc pytest | 196 | 196 |
| TB-utils pytest | 39 | 39 |
| cocotb (30 jobs x 19) | 570 | 570 |
| Total tests | 805 | 805 (failures 0, errors 0, skipped 0) |
| Strict lint | 27 | 27 PASS |
| Elaboration probes | 9 | 9 PASS |
| ALG2 expected rejections | 3 | 3 XREJECT (not counted as tests) |
| Steps | 71 | 71 (68 PASS + 3 XREJECT, 0 fail, 0 not run) |

Seed-510 stress run 1587:

- The gate reported 26 problems: the seed override, 24 "run … missing" entries (6 configs x the 4
  non-510 seeds), and "6 valid full-length runs, exactly 30 required". All of them follow from the seed
  override, and there are no other problems.
- For N4/W64/510 and N8/W64/510, `trace_sha256`, `coverage_measurement` and `coverage_total` are
  identical to the failing run 1025. The only differing keys are `throughput` and `wall_time_s`, plus
  the new `measurement_boundary`.
- `owed = 1` for both: N4/W64 (src 3, F/R/T measured 209240/209111/128, total 209242/209114/128) and
  N8/W64 (src 7, measured 193363/193243/119, total 193363/193244/119). Both exact relations hold.
- Across all 6 configs, `owed = 1` in 5 runs and `owed = 0` in 1 (N16/W64), so both branches were
  exercised. Every run has `cov_at_entry == coverage_measurement` and `drain_calls = 2`.
- The run started at 01:18:25Z, after the last source edit at 01:17:00Z. The current file hashes equal
  testbench-dev's `after-hashes.txt`.

Original run 1025: lag check over all 9 executed runs. `lag ∈ {0, 1}` together with an exact whole-run
relation is a necessary condition only. `owed` was not observable in those runs, because the
instrumentation did not exist yet.

| Run | Measured F/R/T | lag | Whole-run lag | Original `:121` | Necessary condition |
|---|---|---|---|---|---|
| N4 W64 509 | 226115/225957/157 | 1 | 0 | FAIL | met |
| N4 W64 510 | 209240/209111/128 | 1 | 0 | FAIL | met (owed = 1 confirmed by re-run) |
| N4 W64 511 | 199191/199045/146 | 0 | 0 | PASS | met |
| N4 W64 512 | 218698/218571/126 | 1 | 0 | FAIL | met |
| N4 W64 513 | 216839/216704/134 | 1 | 0 | FAIL | met |
| N8 W64 509 | 172242/172127/115 | 0 | 0 | PASS | met |
| N8 W64 510 | 193363/193243/119 | 1 | 0 | FAIL | met (owed = 1 confirmed by re-run) |
| N8 W64 511 | 161689/161575/113 | 1 | 0 | FAIL | met |
| N8 W64 512 | 154648/154566/81 | 1 | 0 | FAIL | met |

## 7. Review notes (non-blocking)

1. `owed` comes from the harness's own `prev` record: scoreboard occupancy plus the observed
   `in_valid` pin. It is not an independent pin observation. This is acceptable because the scoreboard
   is cross-checked against the RTL every cycle, the whole-run relation is exact, and check (d) asserts
   the real first-drain-cycle pins.
2. The `drain_calls == 2` and `cycle_no == meas_end` assertions tie the check to run_trace's current
   structure. Any future change there would fail loudly, not silently.
3. test_19 imports helpers from the stress module at runtime. That module has only constant
   module-level state, and the import adds no collected test, as the JUnit name lists show.
4. In infra-smoke mode the relation is still skipped, as it was before the repair.

## 8. Source manifest (working tree, uncommitted; identical to `testbench-dev/repair.patch`, sha256 `7326887e…64c7fe`)

| File | sha256 | git blob |
|---|---|---|
| scripts/run_verify.py | c4892e8b8caa47ea12a7193ce5c786d04054d37020717383bdfbde607bcbe796 | efb2b6a404883510109ed06f5df03553bedc9f60 |
| sim/switch_top_fai/test_switch_fai.py | 6982bbac7f29811eaa64ddfd17bf09e2f724e7fbf853d7bafb771ad8714c3234 | 607514653be2a7e203193ce6b5ac96f1143d1e76 |
| sim/switch_top_fai/test_switch_fai_stress.py | 9f88b9b97cef7ad09497717904329316c07eaa7913d041f186215b3b51f1de8b | d12ab96485fce020fcd9f185b9a53378fb0916ad |

## 9. Remaining before acceptance

- Codex independent review of the repair.
- Full 30-run M5-stress (NOT RUN here).
- M5-primary and M5-production (NOT RUN here).
- Final verifier sign-off.
