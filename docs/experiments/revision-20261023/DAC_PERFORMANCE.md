# DAC conditional performance orchestration

Status: PREPARED; native writer release and full correctness acceptance were
provided by the parent. The new source freeze and W256 diagnostic pilots are
authorized after final unit checks, at one simulation worker / two build jobs.
Production and confirmation are NOT authorized. No RTL performance result is
claimed by the pure unit tests.

Only `scripts/run_revision_dac_experiments.py`,
`scripts/test_revision_dac_experiments.py`,
`sim/experimental/test_dac_performance.py`, and this document are added.
Existing core runner, Traffic, models, native testbench, RTL, matrix, and paper
remain unchanged. Native correctness PASS and writer release were reported by
the parent for `revision-dac/20261023T174033Z_1699`.

## Identity and scope

The sole selected candidate is DAC2, with HIGH_WEIGHT=2. The exact 30 approved
conditional matrix rows retain their original `INSIGHT_WINNER` policy, complete
job dictionary, and ID. `selected_policy="DAC2"` is a separate configuration and
result field:

- 20 trained confirmation rows, seeds 529..548.
- 10 trained robustness rows: both approved readiness perturbations, seeds 509..513.

There is no automatic production queue. Every invocation requires an explicit
group and seeds, or one W256 exploration pilot. No confirmation seed is used in
the pilot. DAC1 requires `--selected-policy DAC1 --ablation`, separate output and
a matching DAC1 pilot; it always contributes zero approved matrix rows. It is
not a second candidate. Independent cold A/B are not required for all 30 trained
rows and are not implemented as implicit extra jobs.

## Native interface and passive metrics

The adapter imports `test_dac_sched.Harness` and calls `start()` once, then
`cycle(push, ready=...)` on every active/drain edge. The returned `o` must be the
pre-edge sample with `in_ready`, `out_valid`, `out_source`, `out_desc`, and `fire`.
The native Harness exclusively owns clocks, reset, RTL state checks, independent
oracle and pin scoreboard. The adapter does not inject state or call model
`view`/`commit`, and does not replace native module globals.

Unchanged Traffic generates every training and measured arrival/descriptor.
StreamProducers retains rejected requests. Metrics observes returned pre-edge
pins and accounts for generated/offered/accepted/fired populations, upstream
backlog, FIFO occupancy, exact cohorts and direct latency histograms, and joint
eligible-ready utilization. Training checks cohort completeness; A/B guards also
require sparse queues empty. A final bounded drain includes every generated
request. Native input/output/state checks remain active on all edges.

Window records include closing-edge fires. Every 250k active/drain cycles the
adapter logs actual monotonic wall seconds, backlog and simulator VmHWM.
W256 is sensitivity evidence only. W5M runs use real 10M-cycle training; no
preload, clock skipping, quiet training or extra guard is introduced.

## Required acceptance and source release

Both pilot and production require:

1. `--screen-summary` pointing to the sealed MODEL_ONLY evaluation summary.
   All 60 HOG and eight feedback reports, their validations and source archives
   are re-ingested through the existing screen checker. The gate must recompute
   exactly as PASS with sole frozen candidate DAC2. Use WSL: sealed paths bind
   the original WSL execution environment.
2. `--native-correctness` pointing to a completed full native run. Require all
   declared lint/reject/runner/cocotb steps, raw zero-skip JUnit, numeric zero exits
   for positive checks and XREJECT/nonzero exits for intentional rejections,
   the 13-model-test record, unchanged source hashes and exact source ZIP bytes.
   Diagnostic subsets do not qualify.
3. A parent-issued `--release` receipt, after native writer exit/release and
   explicit acceptance. Its schema is:

```json
{
  "schema": "cxl-dac-performance-release-v1",
  "native_released": true,
  "parent_correctness_accepted": true,
  "source_hashes": {"every performance source relative path": "sha256"},
  "native_bindings": {"absolute accepted native evidence path": "sha256"},
  "screen_bindings": {"absolute validated sealed screen evidence path": "sha256"}
}
```

`source_hashes` must equal `common.hash_sources(source_paths())` from the new
runner. `native_bindings` and `screen_bindings` must equal its `verify_native`
and `verify_screen` return values. The parent creates this receipt only after
reviewing the concrete native release and final performance files. Preparation
does not issue a receipt or automatically freeze sources.

Production additionally requires `--production-reviewed --reviewed-pilot` with
a PASS W256 artifact for the same selected policy, source bytes and acceptance
bindings. Missing/failed/stale input fails before an output run is created.
Output must be a new strict child of
`artifacts/implementation/revision-dac-performance/`.

## Runner and evidence

The new class uses `run_verify.Run` directly, with a local entry/configuration.
It does not mutate MILESTONES or any frozen module global. The strict engine
records commands, versions, lint/build/simulation exits, raw JUnit, result files,
and failures. Its normal fail-fast flag is enabled. Up to three simulation
workers and exactly two build jobs are permitted; initial default is one worker.
Builds use the existing external cache convention to avoid Make space-path
failures. Keep global worker scheduling under parent control.

The archive closure includes native RTL/filelist/Harness, oracle package,
Traffic/Metrics and their imports, strict engine, reused core validators/tests,
screen verifier/tests and the three new Python files. `sources.zip` binds the
bytes used, with before/after hash maps. `frozen-spec.json` binds exact matrix
jobs and selected policy separately, plus acceptance evidence hashes.
`dac_performance_scope.json` is PASS only after strict steps, replay, metrics,
source and acceptance rechecks pass. `evidence.zip` preserves commands, numeric
exits, failure records, results and source archive. Bound acceptance inputs are
copied into content-addressed `acceptance/` blobs with their original-path/hash
manifest, so the final archive retains the actual gate inputs and exits.

Memory is sampled every 0.25 seconds. Crossing 70% of starting available memory
sets the strict engine abort event so pending simulations do not start; active
jobs finish. Final acceptance also rejects excess system growth or summed
largest simulator high-water RSS values for the worker count. This is not a
hard kill or an OS memory reservation. Runtime, drained backlog and memory must
be reviewed before selecting production concurrency.

The existing evidence indexer has not been changed. It does not automatically
accept this new DAC result schema; parent-owned index integration is PENDING.
No core queue, confirmation, production, synthesis or power launch is authorized
by this preparation record. W256 diagnostic launch permission is the parent's
explicit subsequent message; diagnostic results belong in durable run artifacts.

## Preparation verification

Before the performance freeze, 21 pure tests passed under both Windows and the
project WSL environment. Two additional gate rejection tests were then added
for sealed model evaluation and stale pilot inputs; final counts are recorded
in the diagnostic handoff receipt. The first 14-test attempt had one test-fixture
error (missing keep_going); its log is retained and the fixture was repaired.
No native or frozen core source was edited to repair that test.

Read-only WSL gate inspection reproduced the actual sealed model PASS/DAC2 gate
and validated the native full correctness artifact: 102 native evidence-file
bindings, 275 sealed-screen bindings. This inspection took 24.822 seconds and
did not simulate any performance trace. The new performance closure contains
53 source files; it extends the unchanged 39-file core freeze.
