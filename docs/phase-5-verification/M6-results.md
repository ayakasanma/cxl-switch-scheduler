# M6 Supplementary FAI Algorithm-2 (N4) — implementation and functional verification

Date 2026-10-21 (Asia/Taipei). **M6_UNIT_SCOPE_PASS; NOT_ACCEPTED** (independent review and parent acceptance pending). Frozen Spec v1.0 `1af80967bbc2fb83224f4725c4fb450889e69c62` is unchanged: `specs/CXL_SPEC.md` blob `7b920bd7…` equals the frozen tree. Base `HEAD f0a75c5`, with uncommitted working-tree changes listed below. No synthesis, STA, SSH or PPA was run. No Algorithm-2 PPA, fairness or paper-reproduction claim is made. The Algorithm-2 behavior is the owner's supplied account (ICPADS 2025, Algorithm 2). No IEEE PDF was inspected.

## Agent and provenance

The work was done by the native RTL Agent Team `rtl-agent-team:rtl-coder` in Claude Code session `77281b50-edbf-4a55-9539-a77ad9d0736d`. The requested model was `claude/claude-opus-5-5` at medium effort, and the response records show `claude-opus-5-5`. No subagent or model substitution occurred. The launch files are in `.setup-logs/implementation/alg2-20261021/native/`: settings, prompt, stream and before-hashes.

A harmless permission probe written with both Write and Bash went to an ignored path (`permission-probe.txt`).

Model reading order is recorded truthfully in `reading-order.md`. I read the spec, the abstract Main model and its tests first. I then wrote `fai_alg2_model.py`, the hook and the model tests, and ran them: 148 passed. Only after that did I read the FAI RTL bodies and the TB harness. The model copies no RTL control.

## Implementation (minimal shared change)

- **RTL.** `cxl_fai_main_sched` gains `INTERP` (default 0 = Main, 1 = Algorithm-2, anything else `$fatal`). Only the closing-edge classification is generate-selected: `gen_interp_main` uses the unchanged `cls_next`, and `gen_interp_alg2` uses `alg2_next` on its own enum `A2_STABLE_HIGH/A2_STABLE_LOW/A2_BUFFER_P_HIGH/A2_BUFFER_P_LOW` (bit0 = target p = effective class). The rest of the block is shared by both interpretations: candidate, visits, B/S, index, 32-bit thresholds, the 5-bit context and the FCFS selector.
- **switch_top.** The POLICY=3 branch `gen_policy_fai_alg2.u_fai_sched` is the same module with INTERP=1. `L_CTX_W=5` applies to both FAI policies. FIFOs, hold, counter and ports are unchanged; there is no new stage, bypass or buffer. The stale POLICY=3 `$fatal` is gone, and unknown encodings still hit the default `$fatal`.
- **Model.** `FaiMainSwitchModel` gets a three-attribute hook (`TRANSITIONS`, `EFFECTIVE`, `RESET_STATE`) whose defaults are Main's. `FaiAlg2SwitchModel` overrides only those three attributes.
- **TB.** `switch_fai_tb.py` gets an explicit `FAI_INTERPS` selector covering the oracle class, an independently typed literal `SPEC_8_6`, the effective map, the `cls_q` decode, the reset state and the scope. All other layers are unchanged.
- **New tests and docs.** `sim/switch_top_fai_alg2/` holds 16 directed and random cases, a production-parameter smoke test and a comparison record test. The derivation is in `docs/phase-3-uarch/fai_alg2.md`.

**Main unchanged (structural evidence).** I verilated switch_top from HEAD and from the working tree for POLICY=2 (N4/W64, N8/W256, N16/W5M, N4/W5M), POLICY=0 N4 and POLICY=1 N16, then compared the generated C++ with comments stripped:

- Five of the six configurations are byte-identical.
- POLICY=2 N4/W5M differs only in Verilator DFG temporary numbering. After alpha-renaming, the only remaining difference is the order of 5 `= 0` constructor initializations, and the line multisets are equal.

This is generated-code comparison, not formal equivalence. Evidence is in `main-structure/compare.log`; attempt 1 is preserved as `compare-attempt1-INVALID-quoting.log` (path quoting bug, results void).

## Results (WSL Verilator 5.052, cocotb 2.1.0, pytest 9.1.1, Python 3.12.3)

| Scope | Run ID | Result |
| --- | --- | --- |
| M6 run 1 | `20261021T002805Z_856` | **FAIL**, preserved. 59 PASS / 4 XREJECT / 8 FAIL / 3 NOT_RUN. Failures were two test-expectation errors, see below |
| M6 run 2 | `20261021T003108Z_1588` | PASS |
| **M6 final** (final source, hashes stable before/after) | `20261021T004406Z_12107` | **PASS**: 45 strict lint, 4 XREJECT, 12 probes, pytest 241+39, cocotb 10×16 + 1 = 161 |
| M6-compare | `20261021T004131Z_10929` | PASS: 4 lint, 20 record runs |
| M5 Main unit | `20261021T003506Z_3137` | PASS 850 = 241+39+570, 27 lint, 9 probes, 3 XREJECT |
| M1 | `20261021T003658Z_4971` | PASS 331 |
| M2 | `20261021T003730Z_5556` | PASS 571, 3 XREJECT |
| M3 | `20261021T003840Z_7305` | PASS 595, 3 XREJECT |
| M4 | `20261021T003951Z_9043` | PASS 475, 3 XREJECT |
| M4-q1 | `20261021T004043Z_10025` | PASS 195 |

Every PASS scope has zero failures, errors, skips and NOT_RUN steps, and `SIM_BUILD_RELAXATIONS` is still empty. The refc pin moved from 196 to **241**: the actual collection, +45 Algorithm-2 model tests. The M1–M5 totals each rise by exactly those 45 repeated model tests. Earlier M1–M5 runs were 286/526/550/430/805, and M4-q1 has no refc and stays at 195. `scripts/test_compare_fai_interps.py` (6 tests) is a separate script test outside the pinned collections.

**Rejection replacement.** The POLICY=3 XREJECT in M2–M5 is replaced, not removed. It is now `POLICY=4` at N4/8/16, requiring the exact message `switch_top: POLICY=4 is not a cxl_sched_pkg::policy_e encoding`, exactly 1 USERFATAL, and the same exact 3 undriven + 6 unused slot pins ("Exiting due to 10 warning(s)", re-derived from actual output). M6 adds `INTERP=2` rejection with the exact message and nothing else allowed. All earlier unknown and bad-parameter checks remain.

**M6 directed coverage (N4 × W64/W256 × seeds 509..513).** The 16 cases cover:

- ports, reset to all STABLE_HIGH with High first, and shared-framework structure without a Main block;
- the exhaustive 4×{UP, DOWN, KEEP, S0} table through real windows, with all 16 pairs required;
- immediate target-class service for both targets, with the Main outcome documented;
- a held grant across a Buffer target flip plus two idle windows (retained Low context, Buffer retained on S0);
- threshold equality N4 and widened 32-bit arithmetic;
- closing-fire inclusion, including KEEP retaining a Buffer;
- 10/10 quota with a Buffer class, expiry with replacement, emptied relinquish and no banking;
- FCFS ties and age inside a Buffer class, and class precedence over age;
- true timestamp wrap (simulation-only counter deposit);
- reset mid-window, mid-visit and mid-hold with a pending Buffer;
- full-plus-pop refusal and no bypass;
- walking ones/zeros across all 105 bits;
- a short random trace;
- a class-dynamics trace requiring all four states and the six Buffer-entry/settle transitions.

Every cycle of every case runs the oracle comparison, the model-free table and pin history, the scoreboard (integrity, conservation, order), the producer hold and the TB tagged responses.

**Production smoke** (N4, RTL default W = 5,000,000, 20,000 cycles). This confirms the 23-bit index/B/S widths, the 5-bit context, all STABLE_HIGH and FCFS-equal selection every cycle. No window closes, so it is not production-window evidence.

**Run 1 failures and repairs (test-only, RTL unchanged).**

1. test_09 asserted `ties_in_class >= 2`. I had copied that bound from Main's test_12, whose first half supplies the second tie, and my scenario doesn't contain it. The test derivation was wrong, so I re-derived it: the scenario was adjusted to also force one older-higher-ID win, and both counts are now asserted exactly (== 1).
2. test_16 at W256 seed 509 did not reach BUFFER_P_LOW/UP in 48 windows. I lengthened the stimulus to 200 windows at W64 and 100 at W256 and kept the requirement.

The RTL, model and harness passed every per-cycle check in run 1.

Separately, two launch attempts are void and preserved:

- `unit-regressions-attempt1-VOID-no-milestone-arg.log`: inline `wsl.exe bash -lc` expanded `$m` to empty, so no scope ran.
- The inline `EXIT=$?` echoes in `m6-run1.log` / `m6-run2.log` are unreliable for the same reason. Outcomes are taken from each runner's `summary.json`.

## Behavior comparison (observations only)

All 10 (W, seed) pairs share an identical intended trace (same generator and SHA-256), identical length and an identical reset trace. Every cycle of both runs passed all harness layers.

| W | Main fires | Alg2 fires | Main Low-visit fires | Alg2 Low-visit fires |
| --- | ---: | ---: | ---: | ---: |
| 64 (5 seeds × 64,000 cycles) | 223,685 | 223,695 | 147,649 | 180,706 |
| 256 (5 seeds × 128,000 cycles) | 443,530 | 443,513 | 290,994 | 369,579 |

Offers differ in about 57–69% of measured cycles, actual push masks in about 41–49%, and effective class maps at 198–634 closings per run. Accepted pushes differ by at most 0.05%. Mean acceptance-to-fire waits differ by 0.15–1.92 cycles per run, in both directions: Algorithm-2 is higher in 8 of 10 runs. The per-run table is in `.setup-logs/implementation/alg2-20261021/compare-output.md`; the full JSON is in `artifacts/implementation/M6-compare/20261021T004131Z_10929/fai_compare.json`.

The larger Low-visit share is consistent with Buffer states being serviced immediately in their target class. These are stress-window observations of one workload family. No fairness, latency or PPA conclusion is drawn.

## Changed inventory (uncommitted)

**Modified:** `rtl/common/cxl_fai_main_sched.sv`, `rtl/top/switch_top.sv`, `refc/cxl_model/fai_main_model.py`, `refc/cxl_model/__init__.py`, `sim/common/switch_fai_tb.py`, `scripts/run_verify.py`.

**New:** `refc/cxl_model/fai_alg2_model.py`, `refc/tests/test_fai_alg2_model.py`, `sim/switch_top_fai_alg2/{test_switch_fai_alg2,test_switch_fai_alg2_production_smoke,test_switch_fai_compare}.py`, `scripts/compare_fai_interps.py`, `scripts/test_compare_fai_interps.py`, `docs/phase-3-uarch/fai_alg2.md`, this report.

Hashes are in `hashes-after-final-m6.txt` and the tracked diff in `diff-tracked.patch` (`.setup-logs/implementation/alg2-20261021/`). Parent-owned STATUS/PROGRESS_TRACKER/DEVELOPMENT_REPORT/RESUME_CLAUDE were not edited by this task. Specs were not touched. Nothing was committed.

## Required parent regression and remaining NOT_RUN

The shared sources changed: `cxl_fai_main_sched.sv`, `switch_top.sv`, `switch_fai_tb.py`, `fai_main_model.py` and `run_verify.py` (rejects/pins). The unit scopes M1–M5 pass on the final source, but the long Main suites were deliberately not rerun: **M5-stress (30), M5-primary (60), M5-production (3)**. M3-primary and M4-primary use unchanged RTL paths but the changed `switch_top.sv`/runner, so the parent should decide whether to rerun them for acceptance.

Also NOT_RUN or out of scope:

- an Algorithm-2 long stress run and an Algorithm-2 production run spanning ≥ 3 windows;
- N8/N16 Algorithm-2 simulation (lint and probes only);
- independent Codex review;
- supplementary synthesis/STA/power;
- formal verification.

Stale text left for the owners: `docs/phase-3-uarch/fai_main.md` §header still says POLICY=3 "stays an elaboration-time rejection", and `rtl/CLAUDE.md` / `sim/CLAUDE.md` describe Algorithm-2 as unrun.
