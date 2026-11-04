# M2 functional verification verdict

- Date: 2026-10-13 (Asia/Taipei)
- Reviewer: Claude RTL Agent Team `func-verifier` (independent acceptance audit + separate execution)
- Upper Spec: specs/CXL_SPEC.md v1.0, frozen at 1af80967bbc2fb83224f4725c4fb450889e69c62 (sections 3, 4, 5, 8.3, 9)
- Scope: common output hold/stall controller and its integration with the common FIFOs (sim-only fixture). No policy, no switch_top simulation.
- Verdict: **PASS** (M2 common-control functional verification). Data: docs/phase-5-verification/M2-results.md.

## Basis

- Acceptance run artifacts/implementation/M2/20261013T062752Z_279: exit 0, 49 steps (37 PASS, 12 XREJECT), 367 tests, 0 failures/errors/skips, no warning relaxation.
- M1 rerun artifacts/implementation/M1/20261013T062852Z_2130: exit 0, 13 steps, 127 tests, 0 failures/errors/skips.
- Independent JUnit/log/exit-code parse agrees with the runner tables.

## Findings

1. Fixture fidelity: OK — same FIFO/hold wiring as switch_top, no logic or state, sim-only; switch_top ports are the spec section 3 list; every policy is an explicit `$fatal`.
2. Model independence: OK — abstract queue + held-grant model; per-cycle model comparison plus model-free pin rules and scoreboard.
3. Non-vacuity: OK — unconditional literal assertions, asserted coverage bins, no exception swallowing/skips; negative controls on the final suite fail the gate (exit 1).
4. Runner integrity: OK — strict flags unchanged, no suppression, XREJECT contributes zero tests and cannot mask a failure; M1 entries unchanged.
5. No RTL defect found. No test, model or runner change was needed by this audit.

## Not covered by this verdict

The 12 XREJECT steps are expected rejections, not simulation passes. switch_top simulation, FCFS/RR/FAI, integrated tests, long random regressions, code coverage, formal, CDC and synthesis/STA/power are NOT_RUN. Known limitation for M4: strict-lint UNUSEDSIGNAL `head_ts` for a timestamp-free policy.
