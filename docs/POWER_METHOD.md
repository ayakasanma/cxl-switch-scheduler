# Experimental activity-annotated prelayout power pilot

The original v1 method below preserves the accepted seed509 cold dataset contract. The fixed
supplementary v2 cold-seed and N4 production-boundary modes are specified separately in
[POWER_EXTENSION_TEST_PLAN](POWER_EXTENSION_TEST_PLAN.md); current execution/adoption is in
[STATUS](STATUS.md). They reuse the same accepted netlists/SDCs and unchanged PT script.
No arbitrary shortened production window, state preload or primary-dataset replacement is allowed.

This is a new experimental method for the approved primary nine, initially RR N4. It does not
change the accepted synthesis/STA profile or constitute measured power results. Expand to the
remaining configurations only after independent review of the actual gate replay, SAIF, and
PrimeTime reports. Source author: owner-authorized GPT-6.1 Sol/high quota fallback after native
RTL Agent Team Opus 5.5/medium exhausted its session allowance. Parent Codex owns remote execution,
independent review and formal status. Local task evidence is under the ignored
`.setup-logs/implementation/power-flow-sol-20261021/` directory.

## Frozen inputs and reproducible replay

Use the existing accepted `primary-20261021-v2-{policy}-n{N}` mapped netlist and emitted SDC from
clean source `759f86b24f13ed5984c19034eeeea2ca43b0e971`. No synthesis recompilation is involved.
The profile remains `saed32-rvt-tt-25ns-forqa-cap075-v2`, canonical SHA-256
`6f4777f001fba4e80c28ebda22bd071bc316d6ff3b2b267ff688145d8aa9774d`: original SAED32 RVT
TT 0.78 V/25 C DB, ForQA/top wire load, original I/O loads/transitions and 25 ns clock. The
electrical library-limit overlay used during accepted synthesis is not applied to library power
tables; power reads the original DB and unchanged accepted netlist/SDC. Each run records and
checks hashes of the accepted netlist/SDC/run configuration/manifest, original DB and simulation
cell model. No university library, PDK, license, executable, or full library-table report is
copied into the repository. PT writes selected library metadata and units only.

`scripts/export_power_vectors.py --policy rr --n 4 --out artifacts/power/RUN_ID` exports an
exclusive new directory; existing output is refused. The supported set is exactly
FCFS/RR/Main x N4/N8/N16, D16, full105, RR quantum10, Main W=5,000,000. The CLI intentionally
offers no seed, duration, shortened-window, or warmup overrides. It reuses the unchanged
`traffic_trace.make_trace(509, N, 100000, "primary")`, `Producers`, `InputHoldChecker`, and
independent policy model. The policy-independent intended trace/hash and downstream-ready sequence
are identical per N. Presented pins and actual input acceptance can differ by policy because
backpressure changes producer-queue advancement. Intended generation and acceptance are recorded
separately. Do not call equal intended traces equal accepted traffic.

Three synchronous reset edges occur outside measurement. No preload or training is performed.
Reset deasserts at the measurement start and its one transition is included in SAIF; reset
clock edges are excluded, not every reset-related transition.
Exactly 100,000 measured edges span 2,500,000 ns with 25 ns cycles, from the first post-reset
cycle, with no drain. Producer valid/full105 remain held until push; a full queue refuses a
same-edge-pop replacement; empty queues never bypass. Model queue conservation, hold obligations,
acceptance/fire counts and outstanding descriptors at the cut are checked and recorded. Inputs
that are invalid drive zero descriptors consistently across all configurations. No descriptors
are withdrawn before the cutoff to make a drain look like workload activity.

**Main limitation:** 100,000 cycles do not reach a W=5,000,000 classification edge. Main stays
untrained all-H; its production window/counters run, but class-transition power and trained-state
fairness are unmeasured. This flow makes no power-fairness claim and provides no production-state
preload. Algorithm-2 power, longer/trained workloads and other seeds remain separate future work.

The deterministic ASCII gzip starts with
`43585031 N 100000 509 POLICY_ID 25000 3`. Each following line is
`cycle valid_hex packed_input_desc_hex sink_ready_hex expected_input_ready_hex expected_output_valid_hex expected_source_hex expected_full105_hex`.
Source h occupies input descriptor bits `[105*h +: 105]`. Expected outputs are computed in Python;
the SV testbench contains no scheduling oracle. Plaintext/gzip hashes, generator/profile/source
hashes, Python environment, source revision and per-policy populations are in `metadata.json`.

## Execution and evidence

Upload only the generated metadata/gzip and project-owned `sim/power/tb_power.sv`,
`sta/power_pt.tcl`, `scripts/check_power_replay.py`, and `scripts/run_power_pilot.sh`. Load the
approved remote Synopsys module, enter the dedicated uploaded payload directory, and run:

```sh
bash scripts/run_power_pilot.sh CASE_ROOT N POLICY EXISTING_CELL_MODEL EXISTING_ORIGINAL_DB
```

All machine-specific absolute paths are arguments/local configuration. `CASE_ROOT` is the
accepted synthesis run directory, containing `run_config.tcl`, `manifest.json`, and `output/`.
The script creates an exclusive `execution/`, validates hashes and configuration, then compiles
the existing mapped netlist with VCS zero-delay cell models and `+notimingcheck`. The common
testbench compares every ready/valid using four-state case comparison and valid source/full105
using four-state comparison before each closing edge. X/Z on relevant output pins fails replay.
Reset handshakes must be known inactive. SAIF collection uses `$set_toggle_region(tb.dut)` and
starts after reset; it ends exactly 2,500,000 ns later. Every vector must be consumed exactly
once. Per-source acceptance/fire/outstanding and passed-cycle counts must match metadata.

`execution/reports/` preserves compile/simulation/PT logs and exits, before/after immutable
source hashes, replay/audit results and raw PT reports. Keep raw SAIF remotely and retain its
SHA-256 and inspected scope/timing/clock evidence locally. Compile/simulator exit success alone
is insufficient; replay totals and the actual SAIF TIMESCALE/DURATION/tb/dut hierarchy must
pass independent checks before PT starts. Keep the exact command, tool/module versions and run
identifier with the parent execution record. The script never downloads remote assets.

`sta/power_pt.tcl` separately enables power analysis and averaged mode, requires successful
linking without black boxes, uses one PT core, reads the original SDC explicitly as version2.1,
and reapplies the original PVT/WLM. Actual W-2024.09 help and the parent's capability smoke
confirmed `read_saif -strip_path tb/dut`. Its return value is retained as data, not compared to1.
The pilot runs timing update, `check_power`, `update_power`, power/hierarchy reports, unit and
clock reports, and register/clock-pin activity enumeration. It never sets fallback switching
activity. The status marker means commands completed and semantic review is still required.
The Python audit rejects missing/empty reports, emitted errors, zero annotated nets, missing
annotation summaries or missing total power. It distinguishes explicit `check_power succeeded.`
with numeric result1 from the observed W-2024.09 result0 accompanied solely by complete
out-of-range ramp/load diagnostics. The latter gets
`QUALIFIED_TABLE_RANGE_WARNINGS_REVIEW_REQUIRED`, retains result0, counts and every affected
pin/range, and does **not** become check_power success. Missing-table/function, unknown warnings,
missing/ambiguous results, missing default checks, or inconsistent diagnostic counts still fail.
CLI exit0 means evidence was read and classified; the JSON quality status and parent review
control estimate acceptance. `method_acceptance` remains `NOT_GRANTED_BY_THIS_AUDIT` in both
cases. Echoed Tcl source is not an emitted error. Nonempty reports alone do not establish
trustworthy power.

The actual RR N4 pilot1 completed VCS compilation/replay and PT with process exits0, but its
original checker correctly stopped because check_power did not succeed. Keep those original
logs, failed audit and hashes unchanged. Its report has two zero-ramp range issues
(`u_out_hold/U13/A1`, `u_out_hold/U14/A4`) and one zero-load issue (`u_out_hold/U13/Y`). The
parent's separate precision/connectivity diagnosis in
`artifacts/fastx/power-rr-n4-pilot-diagnosis1/reports/` identifies the ramp pins on the constant
unused RR candidate-context net and the output on the unloaded grant-context net, each with
zero activity from the activity file. Disabled arcs have constant-propagation reason `p`.
This supports a **qualified estimate with table-domain extrapolation issues in unused constant
RR context**, pending parent adoption; it is not permission to ignore arbitrary table warnings
in other cases. No RTL/profile/load/transition changes or warning suppression are used to make
the report appear clean. A local reclassification is new evidence, not a replacement for the
original failed audit or a repeated EDA measurement.

Pilot1's retained VCS `TFIPC` warnings concern omitted unused outputs: 6,735 DFF QN outputs and
one `u_out_hold.o_grant_held` output. The parent checked actual cell port directions and found
inputs connected. They are preserved as mapped-netlist diagnostics; successful full105/four-state
gate replay provides functional evidence for this workload, not a blanket waiver for omitted
inputs or unknown warnings in another configuration. The parent audits each later case.

## Acceptance review before expanding the matrix

Review actual evidence rather than imposing a new unapproved numerical coverage percentage:

- Confirm exact reset exclusion, 100,000 checked cycles, 2,500,000 ns duration, 25 ns clock,
  correct tb/dut-to-switch_top scope, intended per-N trace hashes and per-policy pin populations.
- Read the `saif-read.rpt` annotated-net and fully-annotated-leaf counts separately. The parent's
  earlier idle capability smoke showed 100% nets but 99.88% fully annotated leaf cells; neither
  is a workload result or a target to copy into new reports.
- Inspect Activity File/direct SAIF, Clock, Default, Propagated, Implied and Not Annotated columns
  in both toggle-rate and static-probability overview tables. `report_switching_activity -coverage`
  counts nets with at least one toggle, **not** SAIF annotation coverage. Constant annotated nets
  legitimately have zero toggles. Retain exact counts and reasons for default/unannotated objects;
  explain unused/invalid FIFO storage or X residency rather than assuming 100% meaningful activity.
- Audit all primary inputs and every FF clock pin/net against the SAIF/annotation tables and
  `registers-and-clock-pins.rpt`. Every FF clock must have known full-window clock activity;
  25 ns gives an ideal two transitions per period (0.08 transitions/ns after confirming tool
  time units). Collection endpoints exclude a boundary transition in the observed VCS pilot:
  199,999 transitions / 2,500,000 ns gives 0.0799996 transitions/ns, with source `file` at every
  observed FF clock. This does not shorten the exact-duration window or change its 100,000
  measured rising edges. Audit the actual finite-window transition count/phase and known-state
  residency instead of requiring an exactly0.08 reported rate or inventing a new rate tolerance.
  Retain the raw `get_switching_activity` pin/rate/source tuples.
  An unknown or missing clock fails method acceptance, even if report_power prints numbers.
- Check touched FIFO/storage/state coverage and distinguish annotation from state excitation.
  Main's all-H/no-classification scope must remain explicit in the result table and conclusions.
- Review `check_power`, all warnings and `disable-timing.rpt`. Preserve the existing PTE-003
  constant-propagation/loop-breaking warning and identify its disabled arcs; do not hide it or add
  user timing exceptions. Confirm license success, no unresolved cells and unchanged source hashes.
- Audit report/library units and preserve reported internal, switching, leakage and total values
  with their actual units. This flow does not invent a watts conversion. Explain any difference
  between top totals and rounded hierarchy sums.

Only after those checks may the parent accept a workload-annotated pilot and decide expansion to
the remaining primary cases. Local focused tests exercise deterministic generation, producer
hold/full-plus-pop/no-bypass, fixed windows, configuration/overwrite rejection, result/SAIF
corruption and emitted-vs-echoed error handling. Tcl stubs check control flow only; actual
commercial option/annotation semantics remain remote calibration.

This is zero-delay, activity-annotated **prelayout** power. It excludes SDF glitch activity,
extracted parasitics, placed routing, clock-tree and gate timing signoff. It is an estimate for
this exact cold-reset workload/window and library/profile, not production power or fairness.
