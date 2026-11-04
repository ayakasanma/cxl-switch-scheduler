# PPA runner (DC/PT) — executed nine-case measurement flow

Independent Codex orchestration review added an explicit common `set_host_options -max_cores 1` in the DC flow and its test stub after native revision3 completed. This preserves the pilot's single-core methodology for every policy/N instead of inheriting site defaults. The applied profile report records the limit; no RTL or timing-constraint change.

Status 2026-10-20: **PRIMARY_NINE_COMMANDS_COMPLETED; SETUP_MET_8_OF_9; ELECTRICAL_RULES_OPEN.** All nine exported from clean flow commit081f8a2 actually completed DC/PT; Main N16 has32 setup violations, worst−0.870709ns, and all nine hold results meet constraints. All cases retain OPEN capacitance findings. See [actual nine-case results](../PPA_RESULTS_2026-10-20.md) and [independent methodology review](../../reviews/phase-5-verify/FastX-PPA-methodology-review.md). The preparation/repair checkpoints below preserve history; their pending-execution statements are superseded by this final result. The common measurement profile is frozen in `syn/profiles/saed32-rvt-tt-25ns-forqa-v1.json`; see [actual execution record](../PPA_EXECUTION_2026-10-20.md). Freezing measurement assumptions does not accept the outstanding electrical-rule violations or claim signoff.

- These files prepare one self-contained Design Compiler / PrimeTime run per configuration.
- Revision 1 was uploaded and run once by Codex on FastX. It stopped at `RUN_FAILURE [tools]: dc_shell -version failed`; that evidence is preserved, unchanged, in `artifacts/fastx/runner-probe-fcfs-n4-failure-a/`.
- Revision 2 repairs that failure and the other W-2024.09 facts in §7. Codex then ran the revision 2 FCFS N4 probe through `run.sh` on FastX (`artifacts/fastx/runner-probe-fcfs-n4-false-positive-b/`):
  - All DC analysis, elaboration, link, `report_units` and structural steps completed; DC exited 0, and `reports/dc_status.rpt` matched the expected marker.
  - `run.sh` still stopped correctly, at `STAGE: dc`, on its log scan. `dc_shell -f` echoes every top-level command's return value, so the initialization `set PPA_FAIL_TAG "EDA_[string toupper failure]"` printed a bare `EDA_FAILURE` line (`logs/dc-error-lines.txt`: only `63:EDA_FAILURE`). This was a false positive from the script itself, not a tool error.
- Revision 3 (this version) builds the tag inside a proc, so no top-level command returns it. PT timing reports now also list met paths (§6). Every error scan, exit, marker and report check is unchanged.
- Codex also ran the revision 2 Tcl directly (`dc_shell -x source` / `pt_shell -x source`, FCFS N4, an explicit 25 ns `PILOT` profile with ForQA):
  - Both batch exits were 0, both markers matched, and no Error/Fatal/EDA_FAILURE-colon line appeared in any report or log.
  - Area reconciled exactly (cell area 103009.393996, 8856 sequential cells).
  - PT coverage was 0 violated / 64 untested (constant-disabled).
  - This validates Tcl syntax and units on the host. It does not validate the `-f` wrapper path, the revision 3 changes or the formal nine.
- The final revision3 plus explicit common DC core limit ran through `run.sh` on FastX: both actual batches exited0, exact markers and every result hash checked, with positive worst-path reports. FCFS N4 at25ns has cell area103009.393996, PT worst setup slack+9.860374ns and hold+0.049066ns. Evidence: `artifacts/fastx/runner-syn-fcfs-n4-wrapper-c/`. Electrical-rule findings remain open.
- Nine common-profile measurements have completed; timing/electrical findings are preserved and power remains NOT_RUN. Codex independently reran all36 infrastructure tests after the core-limit addition: Windows28PASS/8 platform skips, WSL28PASS/8 platform skips, with every unique test actually executed in at least one environment and no jointly skipped tests.
- Source basis: HEAD `83cec17`, frozen Spec `1af80967`, accepted RTL `cefbbb0`/`3006b23`. RTL, models, testbenches, Spec and the existing `remote_eda.py`, `syn/dc.tcl`, `sta/pt.tcl` and guides are unchanged.

| File | Role |
| --- | --- |
| `scripts/prepare_ppa_run.py` | Local, standard-library-only bundle generator. No network, SSH or credentials. |
| `syn/ppa_dc.tcl` | DC probe/syn flow driven by the generated `run_config.tcl`. |
| `sta/ppa_pt.tcl` | PT flow on the exact DC netlist/SDC of the same run. |
| `scripts/test_prepare_ppa_run.py` | Local infrastructure tests (fake tools / stub commands only). |

## 1. Scope

Only the primary nine: `--policy fcfs|rr|fai-main` (POLICY 0/1/2) × `--n-src 4|8|16`, always `RR_QUANTUM=10`, `FAI_W=5000000`, D16, M1, 105-bit descriptor. Algorithm-2, RR quantum1 and stress windows are rejected. The synthesis boundary is the whole `switch_top` (all D16 FIFOs, hold controller, policy state); nothing is blackboxed, no timing exception is written, `rst_n` is an ordinary timed input, and there is no policy-specific script path, staging, macro or optimization. Power is always `NOT_RUN`.

### Optional synthesis-only capacitance target (candidate flow)

A separately reviewed profile may add `"optimization": {"max_capacitance_scale": 0.75}`. The scale must be a finite JSON number strictly above0 and at most1; no other optimization keys are accepted. Missing optimization means1 and leaves baseline config, required outputs and library operations unchanged. The frozen primary profile is not edited or automatically replaced. The0.75 value is an experimental candidate informed by the FCFS4 driver-population diagnostic, not demonstrated closure or a bound for all nine.

For scale<1, DC iterates the selected target library's output/inout pins and tightens defined positive `max_capacitance` values in memory immediately before compile. Every attempted edit retains its original value. Native W-2024.09 calibration establishes float32 attribute storage and six-decimal `get_attribute` output: requested50.76502425 reads50.765026, while50.765024 reads50.765022. The flow predicts this representation using Tcl binary float conversion and six-decimal formatting, and requires exact numeric equality to that prediction, both during apply and restore. Applied readback must also be finite, positive and strictly below its original limit; rounding that erases tightening is rejected. The scale is subject only to this explicit representation, with no broad tolerance or relaxed original library acceptance rule. The original failed pilot's exact-double readback mismatch and successful restoration remain preserved; a fresh directory is required for the repaired pilot.

No `.db` or library asset is written. Immediately after compile, including a false result or Tcl exception, the flow attempts restoration/readback for every attempted pin. A partial apply, failed compile, failed restore, or incorrect readback prevents completion; failed restores also prevent final design reports and netlist/SDC handoff. The original library limits are required for final acceptance reports and exported SDC; PT is unmodified and loads the original `.db` in a separate process.

Active runs require `reports/dc_cap_optimization.rpt`, which records the scale, applied/restored counts, skipped undefined limits, aggregate original-limit bins and final-library restoration status. It contains no full library dump. Native W-2024.09 support for an in-memory library-pin cap edit and its DC constraint-engine effect was observed in `closure-cap-canary-20261020a`; the new full-loop compile/restoration flow still needs an actual FastX pilot. Local schema/fake-tool/Tcl-stub checks are infrastructure evidence only. A candidate must retain common settings and be measured/reviewed across all nine before adoption; original-limit PT cap/slew, setup/hold and structural checks remain required.

Actual follow-up: after the preserved initial exact-double readback failure, the calibrated full-loop flow completed FCFS4 and Main16 DC/PT pilots with390/390 limits applied/restored and original-limit PT cap/slew0/0 in both. FCFS4 meets timing; Main16 retains32setup violations, worst−0.907946ns. All used remapped output pins have original positive limits, so20 undefined skipped library outputs are unused in these results. The candidate remains PILOT, no replacement sweep/adoption; see [actual results and failed attempts](../PPA_CLOSURE_DIAGNOSIS_2026-10-20.md). The44 unique Windows/WSL infrastructure tests and actual commercial runs remain separate evidence.

## 2. Preparing a run (local)

```bash
python scripts/prepare_ppa_run.py --mode probe --policy fcfs --n-src 4 \
  --library /ABSOLUTE/REMOTE/PATH/lib.db --output <new local directory>
python scripts/prepare_ppa_run.py --mode syn --policy rr --n-src 8 \
  --library /ABSOLUTE/REMOTE/PATH/lib.db --profile <reviewed profile.json> --output <new directory>
python scripts/prepare_ppa_run.py --print-profile-template   # placeholders; rejected until filled
```

`--library` is a remote path string only (letters, digits, `. _ + - /`, ending `.db`); it is never opened locally and only appears in the generated `run_config.tcl`, `run.sh` and `manifest.json`. `--output` must not exist; inside the repository it must be under ignored `artifacts/`. A failed preparation removes only the directory it created.

Output: `payload/<run>/` (reviewable), `payload.tar` (deterministic: sorted members, uid/gid 0, `run.sh` 0755, others 0644, single top directory `<run>`, no links) and `payload.tar.sha256`. The run name is `cxl-ppa-<mode>-<policy>-n<N>`.

Payload contents: the seven sources exactly as listed by `rtl/filelist_switch.f` (package first, `switch_top.sv` last), the filelist, `specs/APPROVAL.md`, the Tcl flow files, `run_config.tcl` (explicit `ELAB_PARAMETERS` such as `N_SRC=4,POLICY=0,RR_QUANTUM=10,FAI_W=5000000` plus structural expectations), `parameters.json`, `profile.json` (syn), `expected/` markers and required-output lists, `run.sh`, `manifest.json` and `SHA256SUMS`.

Attribution: RTL, filelist and approval must byte-match their `HEAD` blobs or preparation stops. Flow scripts are exported as-is and recorded with `matches_head`; while they are uncommitted, the manifest shows `false` and the summary lists them under `uncommitted_flow_files`. The manifest also records HEAD, its commit time, `git status --porcelain`, per-file SHA256/git blob, the generator SHA256, profile hashes and `content_bundled: false` for the library. Only allowlisted text types are bundled; `.db/.lib/.so/.lic`, hidden, `.git`, symlinked, junctioned or out-of-workspace paths are refused.

## 3. Executing on the EDA host (actually completed by Codex for all nine)

```bash
sha256sum -c payload.tar.sha256
mkdir <new run root> && tar -xf payload.tar -C <new run root> --no-same-owner
cd <new run root>/<run> && bash ./run.sh        # optional: EDA_MODULE=<module> bash ./run.sh
```

`run.sh` refuses a used directory (exit 91) and then, stopping at the first failure with `execution-status.txt = FAILED / STAGE / EXIT`:

1. `payload`: `sha256sum --strict -c SHA256SUMS`.
2. `environment`: date, hostname, kernel; if `module` exists, `module load ${EDA_MODULE:-Synopsys_x86-64/2024}` and `module list` must show it. No module init file is guessed. Home `.synopsys_dc/pt.setup` presence and hashes are recorded, not their contents.
3. `tools`: `dc_shell` (and `pt_shell` for syn) must be on PATH. `<tool> -version` is informational: stdout, stderr and exit are recorded separately (`logs/<tool>-version.stdout/.stderr`, `<tool>_version_query_exit` in `logs/environment.log`). W-2024.09 `dc_shell -version` prints a valid banner but exits 1, so a nonzero exit is accepted only when the banner identifies the tool (`dc_shell|Design Compiler`, `pt_shell|PrimeTime`) and carries a release token such as `W-2024.09`, recorded as `<tool>_release`. No output, unrelated text, the other tool's banner, a banner without a release, or any Error/Fatal line stops the run. The batch `-f` runs below still require exit 0.
4. `library`: regular and readable; path, size and SHA256 are logged. In syn mode the hash must equal `profile.library.sha256`.
5. `dc`: `dc_shell -f syn/ppa_dc.tcl < /dev/null`. Exit 0 is not enough. Any of these fails the stage:
   - an `Error:`/`Fatal:`/`EDA_FAILURE` line;
   - an unresolved-reference or black-box-creation message;
   - a `Diagnostics summary: N error(s)` line with N>0 (PT prints this, and it counts errors that went into redirected reports);
   - a marker that differs from `expected/dc_status.rpt`;
   - a missing or empty required output, or a report file containing error lines.

   Both tools echo the `-f` script into their logs: each top-level source line and its return value. Neither may match these patterns. Tests check every source line, and every top-level return value in stub execution.
6. syn only, `dc-handoff`: the SDC must have `create_clock` and none of `set_false_path`, `set_multicycle_path`, `set_disable_timing`, `set_case_analysis`, `set_max_delay`, `set_min_delay` or `set_clock_groups`; the netlist must contain `module switch_top`. Netlist and SDC hashes are recorded.
7. syn only, `pt`: the same checks against `expected/pt_status.rpt`; afterwards the netlist/SDC hashes must still match.
8. `finalize`: writes `reports/power_status.rpt = NOT_RUN`, `RESULT_SHA256SUMS` and `execution-status.txt`. The status file starts `COMMANDS_COMPLETED_REVIEW_REQUIRED` and lists `PROFILE_STATUS`, `POWER: NOT_RUN` and review facts:
   - `dc_constraints_violated_lines` and `pt_constraints_violated_lines` (count of `(VIOLATED)` lines);
   - `pt_analysis_coverage`.

   Violations and untested checks never fail the run, and they are never waived automatically.

That final status means only that the commands ran and the automatic failure checks found nothing. It is not PASS, timing closure or accepted PPA. Return `execution-status.txt`, `manifest.json`, `run_config.tcl`, `profile.json`, `logs/`, `reports/`, `output/` and `RESULT_SHA256SUMS`; `work/` and tool scratch files are not needed. Never return library or license content.

## 4. Probe mode (no compile, no PPA)

`ppa_dc.tcl` runs these steps:

1. Record versions and command availability (`dc_commands.rpt`, including `report_power`/`read_saif` as capability facts only).
2. Set `search_path`, `target_library` and `link_library`, then `read_db`.
3. Library identity and attributes:
   - `list_libs` is saved as information only; its redirected text may be empty.
   - `get_libs` must show a loaded library named after the `.db` file root (`saed32rvt_tt0p78v25c` on FastX).
   - The library attributes `time_unit_name` and `capacitive_load_units` must be nonempty and are recorded. Codex observed these names on the real library; `time_unit`/`capacitive_load_unit` do not exist.
   - `report_lib` is not used: its redirected text was observed empty on W-2024.09 DC.
4. `analyze -format sverilog` on the exact list.
5. `elaborate switch_top -parameters <explicit list>`, then `rename_design <suffixed name> switch_top` if needed (observed: `switch_top_N_SRC4_POLICY0_RR_QUANTUM10_FAI_W5000000`), `current_design switch_top` and `link`.
6. After link, `report_units` (`dc_units.rpt`). Time and capacitive-load units are parsed in seconds/farads; DC prints `1.0e-09 Second(ns)` and `1.0e-15 Farad(fF)`, PT prints `1e-09 Second` and `1e-15 Farad`. Missing or unparsable units fail. A unit attribute whose text parses (e.g. `1ns`, `1.000000ff`) must agree with `report_units`; text that does not parse is recorded as `NOT_PARSED_RECORDED_ONLY`, never guessed. `lib_metadata.rpt` holds these facts only, with no cell or timing-table data.
7. `report_design`, `report_hierarchy -noleaf`, `report_port -verbose`, `check_design` and app-variable values.
8. `elab_structure.rpt` checks:
   - Port widths per N, e.g. `i_in_desc` 420/840/1680.
   - Exactly N `cxl_desc_fifo*` and one `cxl_out_hold*`.
   - The policy module present and the other policies' modules absent.
   - Zero latches.
   - Register bits at least the descriptor storage plus, for FCFS/Main, the timestamp storage. For RR they must stay below that sum: no timestamp bank.

Any inconsistency fails the run. Codex uses the probe reports to choose the library name, operating condition, units and an existing wire-load model before writing a profile.

## 5. Profile schema (`cxl-scheduler-ppa-profile/v1`, syn only)

Every key is required. Unknown or duplicate keys, `NaN`/`Infinity`, non-numbers, booleans and negative values are rejected, and no numeric default exists. Numbers are in the declared library units.

| Section | Keys and rules |
| --- | --- |
| top | `schema`, `profile_id`, `status` = `PILOT` or `FROZEN` |
| `review` | `reviewed_by`, `reviewed_on` (ISO date), `evidence` (e.g. the probe run) |
| `library` | `db_basename` must equal the `--library` basename; `sha256` (64 lowercase hex) is checked on the host; `name` and `operating_conditions` come from the probe |
| `units` | `time` ∈ {1,10,100}{ps,ns}; `capacitance` ∈ {1,10,100}{ff,pf}; `evidence`. DC and PT fail if `report_units` after link disagrees or cannot be parsed. |
| `clock` | `port` = `clk`; `name`; `period` > 0; `setup_uncertainty` < period; `hold_uncertainty`; `transition` |
| `io` | `input_delay_min` ≤ `input_delay_max` < period; same for outputs; `input_transition`; `output_load` |
| `wire_load` | `{method: fixed_model, model, mode: top, rationale}` or `{method: zero_wireload, rationale}`. `auto_wire_load_selection` is always false; there is no automatic area-based selection. |
| `compile` | `command` = `compile`; `map_effort` ∈ `tool_default` (plain `compile`), `medium`, `high` |
| `power` | `status` = `NOT_RUN` |

The canonical profile SHA256 (sorted keys) is written to the manifest, `run_config.tcl` and DC/PT reports. The nine formal runs must show one identical canonical hash, `FROZEN` status and the same library hash. A changed profile makes earlier runs pilot-only.

## 6. Syn mode

After the probe steps, DC:

1. Checks library name and units against the profile.
2. Applies `set_operating_conditions -library`, sets `auto_wire_load_selection` false, and applies the fixed `set_wire_load_mode top` / `set_wire_load_model -name -library` (or `set_zero_interconnect_delay_mode true` only if that command exists).
3. Writes the clock (`create_clock`, setup/hold uncertainty, clock transition) and min/max input delays on all inputs except `clk`. That set must be exactly N+105N+2 bits and include `rst_n`. It then sets min/max output delays, input transition and output load.
4. Writes `profile_applied.rpt`, `check_design` and `check_timing`.
5. Runs `compile` with the profile effort.
6. Runs post-compile checks and reports: `report_area` flat and `-hierarchy`, `report_reference -hierarchy`, `report_qor`, max/min `report_timing -max_paths 20 -significant_digits 6`, `report_constraint -all_violators -significant_digits 6`, `report_clock` and `report_design`. DC uses no `-nosplit`, because it was only observed working in PT. Six digits keep slew violations of about 0.001 ns visible (pilot: required 0.107692, actual 0.109245).
7. Writes `area_summary.rpt`: combinational, buf/inv, noncombinational, macro/black-box and total cell area plus cell, sequential and reference counts. It fails on nonzero macro/black-box area or count and marks whether combinational + noncombinational reconciles to the total cell area.
8. Records post-compile register and latch counts (latches must be 0).
9. Runs `change_names -rules verilog -hierarchy`, `write -format verilog -hierarchy` and `write_sdc`.

PT then:

1. Sets `link_path` and `link_create_black_boxes false`.
2. Runs `read_verilog`, then `link_design switch_top`; only after that does it check `current_design`.
3. Requires the profile library to be linked.
4. Runs `read_sdc` on the same SDC and re-applies the same operating condition and wire-load methodology.
5. Repeats the netlist structure check, then runs `update_timing -full`.
6. `report_units` (required; must match the profile).
7. Reports:
   - `report_design`, `report_clock`, `check_timing -verbose`;
   - max/min `report_timing -max_paths 20 -slack_lesser_than 1e9 -significant_digits 6 -nosplit`, and `report_constraint -all_violators -significant_digits 6 -nosplit`. Without the slack filter, PT applied `-slack_lesser_than 0.000000` in the real pilot, so the reports held only `No paths with slack less than 0.000000.` The `1e9` value is a report filter, not a constraint. Each timing report must contain a `Startpoint:` line and a `slack (MET|VIOLATED)` record, or the run fails.
   - `report_analysis_coverage`, plus `report_analysis_coverage -status_details untested` (`pt_coverage_untested.rpt`);
   - `report_disable_timing` (`pt_disable_timing.rpt`, to classify constant or loop-broken arcs);
   - `report_global_timing` and `report_exceptions` when available.
8. Writes `pt_coverage_summary.rpt` with exact Total/Met/Violated/Untested counts from the `All Checks` row. Its `ANALYSIS_COVERAGE` status is one of:
   - `ALL_CHECKS_TESTED_AND_MET`
   - `UNTESTED_CHECKS_PRESENT_REVIEW_REQUIRED`
   - `VIOLATED_CHECKS_PRESENT_REVIEW_REQUIRED`
   - `COUNTS_DO_NOT_ADD_UP_REVIEW_REQUIRED`
   - `NOT_PARSED_REVIEW_REQUIRED`

   The tool's rounded percentages are never used. In the pilot the row reads `(100%)` while 64 checks were untested.

Hold is reported but not fixed (no `set_fix_hold`), and clocks are ideal, pre-layout, under the common wire-load assumption. The runner adds no extra compile pass, design-rule-only incremental compile or constraint beyond the profile.

## 7. W-2024.09 revision2 facts and historical pre-execution questions

**Observed on FastX.** These come from Codex's runs (reported by Codex, or read by me in `artifacts/fastx/pilot-fcfs-n4-pt-20261020a/reports/` and `design-rule-20261020a/reports/`):

- `dc_shell -version` prints a valid W-2024.09 banner but exits 1; `pt_shell -version` exits 0. This caused the revision 1 failure.
- Redirected `report_lib` text is empty even after `read_db`.
- The working library attributes are `time_unit_name` and `capacitive_load_units`.
- The library is `saed32rvt_tt0p78v25c`, with operating condition `tt0p78v25c`.
- Linked `report_units` gives the DC and PT formats quoted in §4.
- Option support:
  - DC accepts `-significant_digits 6` on `report_timing` and `report_constraint`.
  - PT accepts those plus `-nosplit`.
  - PT accepts `check_timing -verbose`, `report_analysis_coverage`, `report_global_timing` and `link_create_black_boxes`.
- `elaborate -parameters` with the explicit list, followed by `rename_design`, works.
- Both tools echo `-f` scripts into the log.
- The PT log ends with `Diagnostics summary: N error…`. That count includes a SEL-005 error the pilot had redirected into a report.

**Pilot (FCFS N4, 10 ns, plain `compile`):**

- Total cell area 104530.954213 and 8856 sequential cells.
- No setup or hold violation in DC or PT.
- DC reports 31 `max_transition` violations of about −0.0016 (required 0.107692, actual 0.109245), concentrated on the arrival timestamp counter. PT confirms them and adds `max_capacitance` violations.
- Codex's trial `compile -incremental_mapping -only_design_rule` on a copy exited 0 but did not remove the 31 violations.
- A 0.09 ns global-transition pilot was internally inconsistent with `input_transition 0.1` and was rejected.

None of this is adopted methodology; the profile, clock and sweep decisions belong to Codex. The runner only reports these facts with six digits. It neither fails nor waives on them, and it does not add a design-rule pass.

**Historical pre-execution checklist, now exercised in actual final nine-case logs.** The final wrapper and independent audit confirmed the items below, including actual units, marker/error scans, structure, coverage and populated met/violated timing reports. Their validity does not waive the measured setup/electrical failures. A future failure still stops with preserved logs; checks must not be weakened to make a run pass.

1. The exact `-version` banner text matches the identity/release rule in §3, step 3. Codex holds the real banner in the preserved failed-probe logs.
2. Inside `redirect -variable`:
   - `get_libs -quiet *` with `get_object_name` lists the loaded library names;
   - `get_attribute [get_libs <lib>] time_unit_name` returns nonempty text;
   - `report_units` output is captured, not empty like `report_lib`.
3. Before compile, `all_registers` counts per-bit hierarchical SEQGEN registers. The register bounds depend on this.
4. `get_cells -hierarchical -filter "ref_name=~<module>*"` finds the hierarchical instances before compile, after compile and in the PT netlist.
5. `report_analysis_coverage -status_details untested` and `report_disable_timing` run as expected in PT.
6. Option spellings `report_hierarchy -noleaf`, `report_port -verbose` and `compile -map_effort` (only if a profile selects medium/high).
7. If DC's SDC already contains operating-condition or wire-load commands, PT re-applies identical values, which must not error.
8. PT accepts `report_timing -slack_lesser_than 1e9`, and its path text has `Startpoint:` and `slack (MET)`/`slack (VIOLATED)` lines. The local stub uses a synthetic path shape.
9. The failure patterns are strict. A benign tool line matching `Error:` or a nonzero diagnostics summary stops the run; review it rather than filtering it out.

## 8. Local evidence (infrastructure only)

Logs are in ignored `.setup-logs/FastX-NN/native/`.

`python -m unittest scripts/test_prepare_ppa_run.py` (revision 3) ran 36 tests:

| Environment | Ran | Skipped | Result |
| --- | --- | --- | --- |
| Windows Python 3.13.5, Tcl 8.6.14 | 28 | 8: POSIX `run.sh` tests and symlink creation without privilege | OK |
| WSL Python 3.12.3 | 28 | 8: no tkinter Tcl | OK |

Revision 3 adds two tests:

- **Echoed return values.** A stub mirrors `-f` echo: it evaluates every top-level command of `ppa_dc.tcl` and `ppa_pt.tcl` and checks each return value against the `run.sh` patterns, for probe and syn, all three policies. The revision 2 initialization line is used as a control and is detected. A real failure still prints the tag.
- **Timing path records.** PT fails without a marker when a timing report holds only the observed `No paths …` text, or lacks either `Startpoint:` or a slack record.

Every test executed in at least one environment. Revision 2 adds these checks:

- **Version query.** With fake tools:
  - The default fake `dc_shell -version` mirrors the host (banner, exit 1). Runs complete and record `dc_shell_version_query_exit=1` and `dc_shell_release=W-2024.09`.
  - A banner on stderr with exit 1 is accepted for either tool.
  - Silent, unrelated, wrong-tool, release-less or Error-bearing banners stop at `tools`, for both tools.
  - A batch exit 1 still fails.
- **Diagnostics summary.** A nonzero `Diagnostics summary` with exit 0 fails DC and PT.
- **Review facts.** `(VIOLATED)` counts and the coverage status appear in the final status and never change its outcome.
- **Echo safety.** Every line of both Tcl scripts and the generated `run_config.tcl` is checked against the exact `run.sh` failure patterns.
- **Real pilot logs.** The same patterns run on the real pilot `dc.log`, `pt.log` and `pt_slew_driver.rpt`: the clean DC log passes, and the PT log's hidden SEL-005 error is caught only through its diagnostics summary.
- **Stub Tcl.**
  - Stubs return the observed `report_units` and coverage text; the embedded excerpts are checked to equal the pilot reports.
  - The library is identified through `get_libs`, attributes are cross-checked, and `report_lib` is never called.
  - Units are read after link and checked against the profile in DC and PT.
  - DC options carry `-significant_digits 6` without `-nosplit`; PT options carry both.
  - PT runs the untested coverage details and `report_disable_timing`.
  - The coverage summary reports exact counts (35776 total, 64 untested) and all states.
  - Unit, attribute and option failures never write a marker.

Unchanged checks from revision 1:

- The exact nine parameters, expected widths/bounds and markers.
- Filelist order plus SHA256 and git-blob equality with HEAD for every exported source.
- Identical profile hash and library pin across nine syn bundles.
- Tar safety and modes.
- Rejection of missing, unknown, duplicate, non-finite, non-numeric, negative and contradictory profile values.
- Unsafe or traversing filelist entries, symlinked files or directories, proprietary or hidden payload members, unsafe library paths, overwrite and in-repo outputs, and modified accepted sources.
- `run.sh` driven by fake test-only `dc_shell`/`pt_shell`. Error/Fatal/EDA_FAILURE or unresolved messages with exit 0, missing or wrong markers, missing/empty/error reports, a missing netlist, SDC exceptions, PT changing the netlist, a missing `pt_shell`, a library hash mismatch or missing library, a tampered payload, and a rerun never yield `COMMANDS_COMPLETED_REVIEW_REQUIRED`.
- `ppa_dc.tcl`/`ppa_pt.tcl` sourced in real Tcl 8.6 with stub commands. Probe never compiles or constrains, syn compiles once, PT reads the SDC after `link_design`, markers match byte-for-byte, and injected failures never write a marker.

This stub test found and fixed a portability issue: Tcl's default CRLF output on Windows. Files are now written with `-translation lf`.

Also checked: `bash -n` on generated probe/syn `run.sh` and Tcl `info complete` on both scripts; the existing `test_remote_eda` suite still passes (9 tests).

None of these local tests is evidence of Synopsys execution, library facts, timing, area or power. Those come only from Codex's real FastX runs.

## 9. Completed execution and next milestone

The four flow files plus frozen profile were committed at081f8a2; all final bundle manifests attribute the clean exported files to that commit. The revision3/full-wrapper pilot and the nine-case sweep have actually executed. Do not repeat those completed steps without a new flow/source change or unresolved evidence issue.

Preserve the measured Main N16 setup failure and all9 electrical findings. Investigate the DC/PT capacitance discrepancy and the Main classification path before proposing a common closure iteration. A revised profile/flow requires a new identifier/hash and the same methodology for all nine; retain this baseline for comparison. Do not add timing exceptions, blackbox storage, vary effort per policy, relax library rules or silently insert stages. Power and supplementary Algorithm-2 remain separate incomplete work.
