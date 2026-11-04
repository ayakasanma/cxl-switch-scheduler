# Synthesis Review: common measurement profile cap075-v2 (pre-nine-case method review)
- Date: 2026-10-21
- Reviewer: synthesis-reviewer (native RTL Agent Team, Claude Opus 5.5 / medium, no subagents)
- Target: ASIC pre-layout, Synopsys DC/PT W-2024.09, SAED32 RVT `saed32rvt_tt0p78v25c` (TT 0.78V 25°C)
- Upper Spec: specs/CXL_SPEC.md v1.0 §11 (frozen 1af80967); specs/APPROVAL.md
- Reviewed object: `syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json` (untracked at review time)
- Repository HEAD at review: `e131f85f1164725ab7a3d186a8b8fbccd574ae27`
- Mode: method review of existing actual results (Mode A evidence; no new synthesis, STA or commercial run)
- Verdict: **PASS_COMMON_METHOD — nine-case execution may proceed, subject to precondition P-1 (commit the profile) and the per-case judging rules in §7**

## 1. Scope and what this verdict means

This review covers the measurement method only. It checks whether the new FROZEN profile reproduces the numerical and flow settings of the successful cap075 pilots exactly and whether the generator/DC/PT flow applies those settings the same way. It does **not** state that any of the nine configurations meets timing or electrical limits. As the profile itself says, FROZEN fixes the experiment method; it does not close all nine cases. Power remains NOT_RUN. No area-unit conversion, NAND2 equivalence or Fmax claim is made or permitted.

## 2. Profile comparison: v2 vs cap075-pilot-v1 vs original frozen v1

Mechanically verified by `check_profile_v2.py` (§8). Equality is type-strict, so `25.0` ≠ `25` and int/float/bool/str mismatches would fail.

| Section | Field(s) | v2 | cap075-pilot-v1 | frozen v1 | v2 = pilot |
|---|---|---|---|---|---|
| schema | — | cxl-scheduler-ppa-profile/v1 | same | same | ✔ |
| library | db_basename / name / OC | saed32rvt_tt0p78v25c(.db) / tt0p78v25c | same | same | ✔ |
| library | sha256 | 844d4474…434094 | same | same | ✔ |
| units | time / capacitance | 1ns / 1ff | same | same | ✔ (evidence text = pilot) |
| clock | port / name | clk / core_clk | same | same | ✔ |
| clock | period | 25.0 ns | same | same | ✔ |
| clock | setup / hold uncertainty | 0.1 / 0.05 ns | same | same | ✔ |
| clock | transition | 0.1 ns | same | same | ✔ |
| io | in/out delay min/max | 0.0 / 2.0 ns | same | same | ✔ |
| io | input_transition | 0.1 ns | same | same | ✔ |
| io | output_load | 2.656828 fF (FO4 of INVX1_RVT/A) | same | same | ✔ |
| wire_load | method / model / mode | fixed_model / ForQA / top | same | same | ✔ (rationale text = pilot) |
| compile | command / map_effort | compile / medium | same | same | ✔ |
| optimization | max_capacitance_scale | 0.75 | 0.75 | *(absent)* | ✔ |
| power | status | NOT_RUN | same | same | ✔ |
| identity | profile_id | …-cap075-v2 | …-cap075-pilot-v1 | …-v1 | differs (expected) |
| identity | status | FROZEN | PILOT | FROZEN | differs (expected) |
| identity | review.* | 2026-10-21 Codex text | 2026-10-20 | 2026-10-20 | differs (expected) |

Result: all nine non-identity sections are type-strictly equal to the pilot. Compared with original v1, the only differences are the added `optimization` section and the two descriptive strings `units.evidence` and `wire_load.rationale`. The single-core DC setting (`max_cores=1`) is not a profile field. It comes from the unchanged `syn/ppa_dc.tcl` and appears as `compile = compile map_effort=medium max_cores=1` in both pilots' `profile_applied.rpt`.

Canonical SHA256 values, using the generator's `canonical_json`:

| Profile | Canonical SHA256 | Raw file SHA256 |
|---|---|---|
| cap075-v2 (new) | `6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d` | see manifest (§9) |
| cap075-pilot-v1 | `51a518e98d01ffd5788ee73ab4e39951e680411f494294c59da52bd4cb98fe6f` (matches all three pilot manifests) | `8bfb426f…e03a` |
| frozen v1 | `6baba481319955c0a0425e7fb50a20eed3c8c1a224f2a90ee86a60afd92783af` | — |

## 3. Generator and flow binding

- `scripts/prepare_ppa_run.py::load_profile` accepts v2, the pilot and v1 against the actual host library path recorded in the pilot manifest. The v2 review-evidence string is ≤1000 characters, so it passes the validator's text limit.
- `run_config()` regenerated from each pilot's recorded `parameters.json` and filelist order with the **pilot** profile reproduces the downloaded `run_config.tcl` **byte-for-byte**. This holds for FCFS4 (046721b), the old Main16 (aa89771) and the comparator Main16 (b257ee8).
- Regenerating with **v2** changes exactly three Tcl variables: `PROFILE_ID`, `PROFILE_STATUS` and `PROFILE_SHA256`. Every numeric/flow variable, including `MAX_CAPACITANCE_SCALE 0.75`, is identical. `PROFILE_STATUS` only appears in `profile_applied.rpt`/PT report headers, `environment.log` and `execution-status.txt`. It has no control-flow effect in `ppa_dc.tcl`, `ppa_pt.tcl` or `run.sh`.
- Generator SHA256 `23fa1250…4611` and flow scripts `syn/ppa_dc.tcl` (`29b26a9d…`) and `sta/ppa_pt.tcl` (`ae2da515…`) at current HEAD are identical to those recorded in all three cap075 pilot manifests. `git diff b257ee8 HEAD` and `git diff 046721b HEAD` over the flow, generator, tracked profiles and specs are empty. `git diff d82f1b5 HEAD -- rtl` is empty.
- Current RTL source hashes (8 files) equal `docs/ppa/comparator-main16-20261021.json` `source_hashes`.
- The generator unit suite (`scripts/test_prepare_ppa_run.py`) ran on Windows with exit 0: 44 collected, 36 pass, 8 skipped. Seven skips are bash/coreutils-only `run.sh` tests and one is a Windows symlink-privilege test. The generator is unchanged since its recorded Windows/WSL infrastructure pass, so I did not rerun it under WSL.

## 4. Cap overlay, restoration and original-library acceptance (actual evidence)

| Evidence | FCFS4 cap075 pilot (046721b) | Main16 comparator (b257ee8) |
|---|---|---|
| `dc_cap_optimization.rpt` scale | 0.75 | 0.75 |
| applied / restored / undefined-skipped | 390 / 390 / 20 | 390 / 390 / 20 |
| Host library SHA256 (`logs/library.log`) | 844d4474… | 844d4474… |
| Emitted SDC `set_max_capacitance` | none | none |
| Emitted SDC timing exceptions (run.sh EXCEPTION_RE) | none | none |
| PT link_path | `* $TARGET_LIBRARY` (fresh read of the original .db) | same |
| `sta/ppa_pt.tcl` contains `max_capacitance`/`set_attribute` | no | no |
| PT coverage | 64 untested (constant-disabled), rest met | 143344/143344 tested and met |

The overlay applies only to library pins in DC memory and is restored before reports and export. PT then rereads the unmodified library. No library file was edited, no check was disabled and no flow stage was added.

### Driver-load surveys (recomputed locally from the actual `driver-loads.tsv`)

| Survey | Driver pins | Undefined/nonpositive original limit | Ordinary > limit | CCS > limit | Constant pseudo-drivers | DC exit |
|---|---:|---:|---:|---:|---:|---|
| Original FCFS4 (`closure-full-loads-20261020b`, v1 netlist) | 26731 | 0 | 0 | **1118** | 2 | 0 |
| FCFS4 cap075 (`closure-full-loads-cap075-20261020a`) | 27231 | 0 | 0 | 0 | 2 | 0 |
| Main16 cap075 old (`…main16-cap075-20261020a-final`) | 116345 | 0 | 0 | 0 | 20 | 0 |
| Main16 comparator (`comparator-full-loads-main16-20261021a`) | 116993 | 0 | 0 | 0 | 20 | 0 |

These results match the recorded claims: 1118 CCS violators originally, then 27231/116345/116993 clean drivers after cap075. They show that the 0.75 margin removed the CCS-vs-ordinary discrepancy on **these two designs**. The original observed minimum ratio was 0.7725. A 0.75 target is therefore a measured working margin, **not a proven bound** for the other seven netlists.

## 5. Functional gates (no rerun; checked actual audit)

`.setup-logs/implementation/comparator-20261021/independent-final-audit.json` lists 11 stages. For each one I recomputed the `summary_sha256` of `artifacts/implementation/<scope>/<run>/summary.json`, and all 11 match.

| Scope | Run | Tests | Fail/Err/Skip/NOT_RUN | Full scope |
|---|---|---:|---|---|
| M1 | 20261020T190753Z_4587 | 286 | 0/0/0/0 | — |
| M2 | 20261020T190823Z_5191 | 526 | 0/0/0/0 | — |
| M3 | 20261020T165234Z_2953 | 550 | 0/0/0/0 | — |
| M4 | 20261020T190924Z_6959 | 430 | 0/0/0/0 | — |
| M4-q1 | 20261020T191009Z_7942 | 195 | 0/0/0/0 | — |
| M5 units | 20261020T165357Z_386 | 805 | 0/0/0/0 | — |
| FCFS primary | 20261020T165716Z_534 | 60 | 0/0/0/0 | 60 valid |
| RR primary | 20261020T170247Z_5075 | 60 | 0/0/0/0 | 60 valid |
| Main primary | 20261020T172737Z_382 | 60 | 0/0/0/0 | 60 valid |
| Main stress | 20261020T170825Z_8460 | 30 | 0/0/0/0 | 30 valid |
| Main production | 20261020T173518Z_3766 | 3 | 0/0/0/0 | 3 valid |

`primary-comparison.json` shows identical run records and all 60 trace hashes matching the frozen record for each policy. `production-comparison.json` shows 60,000,000 measured non-reset cycles and 12 windows, with 0 outstanding after drain; only host-performance fields differ. The SIGHUP-interrupted Main primary `20261020T172119Z_10354` is preserved as NOT_ACCEPTED_INCOMPLETE and is not counted. The functional precondition for a synthesis sweep (Spec §12, CLAUDE.md) is satisfied for the RTL at d82f1b5/b257ee8, which is byte-identical to HEAD.

## 6. Findings

### Critical findings
None.

### Major findings

**MJ-1: v2 profile is untracked; the nine runs must not be prepared until it is committed.**
`git status` shows `?? syn/profiles/saed32-rvt-tt-25ns-forqa-cap075-v2.json`. `prepare_ppa_run.py` does not require the profile to be committed. It records only canonical and file hashes, and `source_state` counts the untracked file as a dirty worktree, so manifests would record `worktree_clean=false`. All three cap075 pilots were prepared clean. Codex should commit the profile, together with this review if desired, and prepare all nine from **one** clean commit. Each manifest should then show `worktree_clean=true`, the same `source.head`, generator `23fa1250…`, flow hashes `29b26a9d…`/`ae2da515…` and profile canonical `6f4777f0…`. This is provenance hygiene, not a numeric defect. Impact: avoids an unattributable profile. Area/timing impact: none.

### Minor / informational

- **MI-1:** The FCFS4 cap075 pilot ran at pre-comparator RTL 046721b. FCFS N4 under the comparator RTL has not been measured. The v2 sweep will be its first measurement, and the comparator also affects FCFS (shared selector).
- **MI-2:** The FCFS4 pilot recorded 64 constant-disabled untested PT checks. Untested checks may recur in other cases, especially RR or small N, and must be enumerated and explained per case, not ignored.
- **MI-3:** PT sources `run_config.tcl`, which defines `MAX_CAPACITANCE_SCALE` in the PT session (`CMD-041`), but `ppa_pt.tcl` never references it. This is harmless and does not leak into the SDC or the PT library.
- **MI-4:** The overlay counts 390/390/20 depend on the library, not the design, so all nine should report exactly these values. Any deviation is a run failure to investigate, not a tolerance.
- **MI-5:** The v2 `units.evidence`/`wire_load.rationale` strings are copied from the pilot and differ in wording from v1. They are descriptive only and excluded from numeric comparison.

## 7. Conditions for the nine-case execution and per-case judging

1. Prepare all nine from one clean commit containing v2 (MJ-1), with new run directories. Do not reuse `primary-20261020-v1-*` or pilot names. Old v1 results and pilots stay preserved and are never mixed with v2 cases in one comparison table.
2. No change to RTL, the profile, the generator, `ppa_dc.tcl`/`ppa_pt.tcl` or library files between cases. There must be no timing exceptions, no disabled checks, no extra or policy-specific stages and no per-case effort/clock change.
3. Judge each case **independently** from its own actual reports:
   - DC/PT/wrapper exit 0, with markers and the result hash file.
   - PT setup and hold WNS and violated-check count.
   - PT max-cap/max-transition counts against the **original** library.
   - Untested-check count, enumerated with an explanation.
   - Cap overlay 390/390/20.
   - Host library SHA256 equal to 844d4474….
   - Emitted SDC with no cap overlay and no exceptions.
   - Structural expectations (FIFO instances, register lower bound, RR no timestamp bank).
4. A failing case stays recorded as failed. A cap075 pass on FCFS4 or Main16 is not evidence for any other case, and the overall all-library cap margin remains **unproven**. A full driver-load survey for further cases is useful supplementary evidence but does not replace PT original-library checks.
5. Report area only in library units, as total/combinational/sequential area, FF count and hierarchy partition. Report no NAND2/µm² conversion, no Fmax and no power (NOT_RUN). Areas from v2 and v1 are not comparable as the same method.

## PPA Summary (existing actual pilot measurements only; no new values)

| Metric | FCFS4 cap075 (046721b) | Main16 comparator (b257ee8) | Target / rule |
|---|---|---|---|
| Total cell area (library units) | 103730.908806 | 437622.506788 | No budget in Spec; report only |
| FF cells | 8856 | 35773 | ≥ logical storage bits |
| PT setup slack | +9.881229 ns | +1.158148 ns | ≥ 0 at 25 ns |
| PT hold slack | +0.033790 ns | +0.084335 ns | ≥ 0 |
| PT cap/slew violations | 0/0 | 0/0 | 0 vs original library |
| Untested checks | 64 | 0 | Enumerate per case |
| Power | NOT_RUN | NOT_RUN | — |

(The remaining seven configurations are not yet measured under v2.)

## Optimization Recommendations
None for this review. The method is frozen, and changes to RTL or the flow are out of scope. Any later closure work on a failing v2 case requires a new profile identity and a new full nine-case sweep.

## 8. Commands and evidence

Ignored evidence directory: `.setup-logs/implementation/rebaseline-20261021/native-review/`

| Step | Command | Result / file |
|---|---|---|
| Permission probe | `git rev-parse HEAD`; write `probe.txt`; `git check-ignore -v` | e131f85; probe written; ignored by `.gitignore:14 .setup-logs/` |
| Binding check | `python -I check_profile_v2.py "<repo>"` (Windows Python 3.13.5, stdlib) | exit 0, **97/97 checks pass**; `check_profile_v2.out.json`, `.cmd.txt`, `.exit.txt` |
| Generator tests | `python -m unittest scripts/test_prepare_ppa_run.py` | exit 0, 44 run / 8 skipped; `generator-unittest.log`; worktree unchanged |
| Drift | `git diff --stat b257ee8 HEAD -- rtl syn/ppa_dc.tcl sta/ppa_pt.tcl scripts/prepare_ppa_run.py specs syn/profiles`, `git diff --stat d82f1b5 HEAD -- rtl`, `git diff --stat 046721b HEAD -- <flow>` | all empty |
| Functional audit | recomputed summary SHA256 for the 11 audit stages | 11/11 match |
| Final inventory | `final-inventory.txt`, `final-hashes.txt`, `final-git-diff.txt` | written after this report |

No SSH, network, commercial tool, RTL/model/TB/Spec/flow/profile/status-document edit, commit or global setting change was made.

## Verdict
**PASS_COMMON_METHOD.** cap075-v2 is numerically and procedurally identical to the cap075 pilot profile that produced both successful pilots. Only identity, status and review metadata differ, and v2 is the original frozen v1 plus the reviewed in-memory 0.75 DC cap overlay. Common nine-case execution may proceed once MJ-1 is resolved by committing the profile and preparing from one clean commit. Each of the nine results must then be measured and judged on its own. This verdict does not claim all-nine closure, a universal cap margin, power, Fmax or signoff.
