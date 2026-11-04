# Strict revision evidence index

Historical index checkpoint at 2026-10-23T18:20:12.970635Z (2026-10-24 Asia/Taipei), repository
HEAD `99400de`. This is an evidence inventory, not experiment execution.
Only the indexer, its tests, this document, and new ignored index outputs were
written. Shared matrix source, performance/area work, RTL, paper, and shared
status documents were not edited.

## Current coverage

| Status | Planned matrix rows |
| --- | ---: |
| NOT_RUN | 367 |
| RUNNING | 130 |
| PASS | 1 |
| FAIL | 0 |
| UNRESOLVED | 0 |

Core unconditional coverage is 1/468; conditional coverage is 0/30.
Ten conditional robustness rows are RUNNING in
`dac2-production-20261024-launcherfix-00-insight-robustness`; no candidate production row
has passed at this checkpoint.
`core-99400de-trainingfix-20261024-00-n4-confirmation` is RUNNING for 120 core rows.
`resource-n16-fcfs-seed509-w5m-trainingfix` passed strict inspection and contributes
one N-expansion row. Index-09 explicitly selects those active bundles and both
DAC W256 pilots. Older core pilot attempts remain in historical index-08.
Baseline correctness and model screens contribute zero performance matrix rows.
All 498 jobs and row statuses are present in the JSON; missing production lanes
are explicit. Discovered performance records retain frozen configs, source and
evidence archive hashes, job/seed/cohort/result hashes, exits, and missing or
failed checks. There is one accepted resource performance record; no candidate
production completion or global matrix PASS is claimed.

## Exact matrix inputs

The index uses an explicitly supplied fresh snapshot of the current matrix:

`artifacts/implementation/revision-evidence-index/20261024-index-01/input-current/matrix.json`

- Current matrix canonical SHA256:
  `e72b5e35e32dd446022cc7e429fdaaf690f22cedd474cab790fb787f97f41d62`.
- Current snapshot file SHA256:
  `eff769659bd0714a3d3417a164874d48ae846de824480507bd58de125aff4e6c`.
- Current `scripts/revision_matrix.py` SHA256:
  `317bbc8aeede273d01e4b63b57bad0b6de78f6eb078cd3e71a20fbbbf1d024ee`.
- Thirty corrected `heavy-id3` rows use static permutation from reset.
- The original `artifacts/implementation/revision-20261023/matrix-initial/matrix.json`
  remains historical and untouched. Its canonical matrix hash is
  `0377136c2f2b4584dc911e90942f8a3548829d81d052426e9d2cb09dafc91dfb`;
  its file SHA256 is
  `6e5cfb25df15887c544e3fb0c8038a00beae19d45386d68f8b872f54adc08b90`.
  Thirty historical IDs are absent from the current matrix. Historical PASS
  claims are never inherited by current rows; same-ID changed payloads are
  also recorded explicitly if encountered.

The new snapshot was created with the existing `revision_matrix.py --output`
entry point, in a fresh ignored directory. It does not replace the initial plan.

## Separate evidence

The sealed model screen
`artifacts/implementation/insight-screen/production-sealed-20261023T101008Z/`
has 69 indexed summaries: 60 HOG runs, eight feedback runs, and one evaluation.
All indexed source archive manifests and local report hashes checked without
problems. The evaluation reports gate PASS and sole frozen candidate DAC2,
60 completed HOG records and eight validated feedback records. It remains
MODEL_ONLY, with matrix contribution zero. This index does not rerun its numerical
gate or simulation.

Source-complete baseline
`artifacts/implementation/revision-baseline/20261023T171608Z_276/`
reports PASS, full scope, 36 lint cases, 15 model tests and 226 cocotb tests,
zero failures, errors, skips or not-run steps. Its separate scope record reports
complete matrix, stable source hashes, runner exit0 and exit0. Its ZIP hash and
manifest bytes were checked, including `sim/common/hier_util.py`.
Config, scope, source archive
hash and per-step tool exits are retained as correctness inventory; this is
not production performance acceptance.

`docs/experiments/revision-20261023/BRIDGES.md` reports BLOCKED by SSH
authentication, 0/6 accepted, zero proofs executed. No SSH connection was made
by this task. Formal evidence is separate from the performance matrix.

## Outputs and reproduction

Final ignored output directory:

`artifacts/implementation/revision-evidence-index/20261024-index-01/index-09/`

- `matrix-coverage.json`: complete index, SHA256
  `aed7219fe93a5bf5f5782bb72d5c86a0e9231cfec0f654ba1257495a573717bf`.
- `EVIDENCE_INDEX.md`: generated coverage, group counts and input inventory.
- Earlier `index/` and `index-02/` outputs remain preserved as checkpoints.
  `index-02/` used the excessive cold-lane requirement corrected below; its
  unchanged JSON SHA256 is
  `98d4fea00f3baeff0b957f189b0a91a3d800cbbb5c50a50371e64b0829639d16`.
- `index-03/` remains unchanged (SHA256
  `26e145fd3d7f2bd546d3679a7e088ef3dbc80edaf05051b2584758386766a57d`);
  its blanket selected-subset rejection is corrected in `index-04/`.
- `index-04/` remains unchanged (SHA256
  `12000c69cc97c4d0f3201fccb5873def8049de0adb95994bb9f02579951f1c03`).
  `index-05/` refreshes inputs with the same indexer after the final 14-test PASS.
- `index-05/` remains unchanged (SHA256
  `5c3e97fbef9c8de37ce898581dd70deab2ee24516a74f570d63928825eea533c`).
  `index-06/` refreshes inputs after another 14-test PASS and rechecks the
  source-complete baseline archive, helper inclusion and zero exits.
- `index-06/` remains unchanged (SHA256
  `45ad8b3b00072750b72ac255d72c974b2bb4856a1efd2a79ce887b533ebe354c`).
  `index-07/` applies the real boolean cold payload correction after 16 tests PASS.
- `index-07/` remains unchanged (SHA256
  `dab877d6aea62e51e6a9beb557381aabc2432d8fa7b9f7ac709c98c24df782a4`).
  `index-08/` adds the separately released DAC schema and actual W256 pilots.
- `index-08/` remains unchanged (SHA256
  `b76902863df44335d336fc8c305c7f7833d3a9c3d07ac9a1fb44685528bf3fd9`).
  Index-09 observes resource PASS and active core120/DAC10 using explicit inputs.

Run from the repository root, choosing a new output directory on every run:

```powershell
python -B -m unittest discover -s scripts -p test_index_revision_evidence.py -v
python -B scripts/index_revision_evidence.py `
  --input artifacts/implementation/revision-evidence-index/20261024-index-01/input-current/matrix.json `
  --input artifacts/implementation/revision-20261023/matrix-initial/matrix.json `
  --input artifacts/implementation/revision-performance/resource-n16-fcfs-seed509-w5m-trainingfix `
  --input artifacts/implementation/revision-performance/core-99400de-trainingfix-20261024-00-n4-confirmation `
  --input artifacts/implementation/revision-dac-performance/dac2-production-20261024-launcherfix-00-insight-robustness `
  --input artifacts/implementation/revision-dac-performance/pilot-dac2-seed509-w256-20261024 `
  --input artifacts/implementation/revision-dac-performance/pilot-dac1-seed509-w256-20261024 `
  --input artifacts/implementation/insight-screen/production-sealed-20261023T101008Z `
  --input artifacts/implementation/revision-baseline/20261023T171608Z_276 `
  --input docs/experiments/revision-20261023/BRIDGES.md `
  --out artifacts/implementation/revision-evidence-index/20261024-index-01/index-10
```

Existing output directories are refused. Explicit nonexistent inputs fail
instead of silently producing an empty inventory. The JSON records all supplied
inputs, the UTC checkpoint and indexer SHA256.

## Checks and acceptance limits

The original sixteen unittest cases PASS: trained-row acceptance and optional cold separation,
complete selected-bundle acceptance, incomplete/false-claim and W256 rejection,
nonzero/missing tool exits, RUNNING configs, tampered/missing archives,
source-byte and frozen-config mismatch, wrong job/params/cohort/schema,
historical same-ID changes, baseline separation, model-only gate/hash separation,
missing input/no-overwrite, and unsafe archive paths/links.
Core N4 allocation is asserted to remain 120 declared runs: six policies times
20 seeds, each containing A/B and 10M real training cycles. Optional cold-only
evidence cannot complete a core row; an optional cold failure cannot fail an
otherwise accepted trained row. Adaptation retains its continuous 30M-cycle run.
Actual-output assertions verified 498 distinct indexed rows and status totals,
30 corrected heavy-ID rows, exact snapshot selection, 69 model summaries with
no recorded hash problems, and the PASS/DAC2/60/8 evaluation fields.

The partial starting script had a syntax error (`pass=` as a keyword), repaired
before the first successful suite. No scheduler or EDA regression was launched.
No dependency was added.

Production PASS requires exact frozen config/job/params/seed/cohort, applicable
declared run (trained default; adaptation continuous), production scope,
source archive/manifest consistency, evidence archive byte consistency,
result/scope joins, and passing tool exits with no failed or skipped tests.
W256, MODEL_ONLY, incomplete selected bundles, old schemas, missing fields and mismatched
hashes cannot establish production PASS. The index does not recompute trace
statistics or rerun archived source code; numerical validation remains the
responsibility of the producing runner and independent experiment review.
The earlier index overrequired trained+cold-A+cold-B for every core RTL row.
That rule was corrected after parent review: cold replays remain separate
model-screen/candidate-benefit evidence, recorded under `optional_lane_evidence`,
and do not multiply the 120 core N4 runs into 360. Conditional candidate cold
benefit scope needs explicit separate review and is not imposed on core rows.
The actual runner uses `scope="selected-production-subset"` even when all selected
frozen configs complete. This scope is now eligible for exact per-row acceptance
with `milestone_acceptance_scope=true` and `full_498_matrix_executed=false`.
Completeness is checked against selected configs/results/steps/exits; it does not
require executing all 498 rows. A sealed one-trained-row fixture asserts one PASS,
497 NOT_RUN, and global completion false. Missing acceptance fields, mismatched
job counts, absent scope runs and false full-matrix claims remain rejected.
Statuses describe this checkpoint and may change as other writers finish runs.

## Existing adapter interface

`inspect_performance_bundle(bundle, rows_by_id)` returns bundle `status`, `runs`,
`configs`, source/evidence archive records and file hashes. A reusable accepted
run requires both bundle and run status PASS. `build_index(inputs)` exposes
these bindings in `performance.accepted_records`.

Each accepted record contains `bundle`, `matrix_job_id`, `lane`, `seed`, `cohort`,
relative `result`, `result_sha256`, `trace_sha256`, `exit_codes`, `failures`,
`missing`, `production_evidence`, `source_archive_sha256` and
`evidence_archive_sha256`. Join the job ID to `matrix.jobs`; bundle configs retain
the exact frozen parameters. Load `Path(bundle) / result` only after rechecking
the bound result hash with the existing `sha256_file` helper.

The payload has `job`, `params`, `training_cycles`, `cold`, `cold_cohort`, and
`metrics.cohorts[cohort].pooled_sparse[stage]` or
`metrics.cohorts[cohort].per_source[source_id][stage]`. For trained runs the index
label `cohort="trained"` identifies the lane; A/B are separate payload cohorts,
to be mapped to profiles trained-A/trained-B by the adapter. Optional cold
accepted records require explicit lane selection. This interface does not
normalize metrics or implement the analysis worker's adapter.

The cold schema was checked directly with Erdos against
`revision_traffic.Traffic` and the RTL result serializer. Frozen env
`CXL_REVISION_COLD` is JSON `"A"`/`"B"` for replay selection, whereas result
`cold` is strictly boolean `true`, `cold_cohort` is `"A"`/`"B"`, and
`training_cycles` is zero. Trained results use `false`, null, and the declared
training cycles. The original inspector incorrectly expected a string in
result.cold. Real-schema fixtures reproduced the failure before the fix.
The helper now validates bool and cohort independently, rejecting numeric 1,
string "A", wrong cohort, wrong bool and wrong training cycles.

Sealed cold-A/B bundles both pass strict inspection and produce accepted raw-run
bindings. Cold-only evidence leaves 498 matrix rows NOT_RUN; adding their trained
run yields exactly one PASS and 497 NOT_RUN. Optional cold evidence remains
separate and the N4 denominator stays 120. Erdos was notified that the helper
is ready for its separately owned adapter integration tests. Runner, traffic,
performance sources and frozen archives were not modified.

## Released DAC branch and adapter handoff

The parent released the final DAC schema and source freeze on 2026-10-24.
Read-only checks before editing found none of the three owned paths in either
core39 or DAC53. All 39 and 53 on-disk source hashes still match their retained
manifests after the indexer tests. No runner, performance testbench, matrix,
RTL, adapter or shared document was edited.

`inspect_performance_bundle(bundle, rows_by_id)` now dispatches
`cxl-dac-performance-spec-v1` to `inspect_dac_bundle`; the existing core branch,
signature and acceptance checks remain intact. DAC summary uses `scope="full"`
for its selected configs, with `full_498_matrix_executed=false`; the DAC scope
has `expected_jobs` and `runs`, without core `valid_jobs`. Exact selected rows
can pass independently of the other 498 rows.

Only exact current conditional rows qualify: 20 confirmation and 10 robustness,
original `INSIGHT_WINNER` job policy and IDs, separate `selected_policy="DAC2"`,
native `dac_unit_top`, HIGH_WEIGHT=2, W5M, trained lane and real 10M training.
Optional cold remains separate; candidate rows never enlarge core N4's 120-run
denominator. DAC1 and W256 can have inspected PASS bundles, but contribute zero
matrix rows and never enter production `accepted_records`.

Acceptance checks include exact config/result/scope joins, numeric tool exits,
the declared lint/two-pytest/cocotb/scope steps, raw zero-skip JUnit test/seed,
stable source manifests, source ZIP bytes and complete evidence ZIP bytes.
`context/EXECUTION.md` is the producer's allowed source ZIP context member.
Content-addressed `acceptance/manifest.json` blobs must bind every native,
screen, release and (for production) reviewed pilot input. Original WSL paths
are identifiers; validation uses the archived blobs, without remote path access.
Self-consistent replacement gate maps cannot grant acceptance.

The immutable audit anchors are the specific parent-approved release inputs:

- DAC53 canonical source SHA256:
  `4eca15454a0ba1c75a88e5f0431f32730a50c02bc047fa8ca3a899715b206227`.
- Shared core39 projection SHA256:
  `800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86`.
- Native102 binding-map SHA256:
  `a34fa32ecacb213d39e0d1b6f53c5da18bc457b71769a419e391fa4ac48d6c18`.
- Screen275 binding-map SHA256:
  `28e3dc360df2104f79804e3e4e326c0c9629176fbd89243bb9bb6b354c978e9e`.
- Matching DAC2 W256 pilot ten-file binding-map SHA256:
  `dcb4d4b9d423dacdbf4c0c43ff3c9bf9c3da5214e57f3c3977aa4a13cda7147b`.

These bind the already reviewed native correctness and sole DAC2 MODEL_ONLY
gate, including their source ZIPs, raw reports and exits. The screen itself
still contributes zero rows. A new source/gate/pilot release requires an
explicit audit-anchor update. DAC53 is a source superset: compare the shared39
projection, never require the full DAC manifest to equal core39.

For Erdos: bundle and run must both have `status="PASS"`.
`performance.accepted_records` retains existing result/trace/archive hashes,
job ID, seed, lane and exits. DAC entries additionally expose:

| Field | Meaning |
| --- | --- |
| `selected_policy` | Separate frozen candidate, DAC2 for accepted conditional rows |
| `declared_job_id` | Original matrix identity; preserved for descriptive pilots/ablation |
| `matrix_contribution` | 1 for an accepted DAC2 production row, otherwise 0 |
| `source_sha256` | Canonical full source-manifest hash |
| `core_source_sha256` | Canonical shared39 projection hash |
| `acceptance_binding_sha256` | Per-group canonical native/screen/release/pilot map hashes |

Approved core39 bundles also expose `source_sha256` and `core_source_sha256`.
The direct DAC run includes `trace_config`; saved records bind the raw result
which contains it. Recheck `result_sha256` before reading metrics or trace
config. Join `matrix_job_id` to `matrix.jobs` and retain the separate selected
policy; pairing/normalization remains owned by the adapter.

Verified W256/DAC1 runs are in `performance.descriptive_records` using the same
hash/exit fields, with `matrix_job_id=null`, original `declared_job_id`, and
`matrix_contribution=0`. Actual `pilot-dac2-seed509-w256-20261024` and
`pilot-dac1-seed509-w256-20261024` both passed this branch with all 378 bound
acceptance inputs intact. The actual W5M resource remains RUNNING in index-08;
baseline correctness `20261023T171608Z_276` remains PASS/full in its separate
inventory. Neither statement is a production or global matrix PASS claim.

Reusable fixture: `EvidenceIndexTests.dac_bundle(policy="DAC2", pilot=False,
jobs=None)` in `scripts/test_index_revision_evidence.py`, after its `setUp()`.
It creates a sealed small fixture with released config/result/JUnit shapes and
patches only the immutable audit anchors for synthetic evidence until cleanup.
`jobs` may select one row or all 30 conditional rows. Its shared39 uses the repo
filelist bytes, allowing a MAIN fixture with the same projected source bytes.
`expected_dac_config(job, policy)` is the reusable exact config constructor.

Final checks: indexer 23 tests PASS on Windows and WSL; current adapter 19 and
statistics four tests PASS on Windows (46 total, zero skips). Regressions cover
one selected row, all 30 trained rows, unchanged N4 denominator, DAC1/W256 zero
contribution, forged native/screen/pilot bindings, absent pilot, false release,
missing/tampered blobs, unsafe manifest paths, incorrect job/result/production
claims, numeric exits, raw JUnit skip/seed and running production. Actual
checkpoint assertions verify 498 rows, status totals, zero accepted production
records and two descriptive pilots. No simulation or EDA regression was run.

Index-09 refresh after the parent's completion notice: resource PASS is now
independently verified by the unchanged core inspector, with one accepted
result SHA256
`96b2d45c1b0579709fcb82d1846bd199220c16b7796eb8b24bc03b8324244584`.
Core N4 120 and candidate robustness ten rows remain RUNNING. Status totals are
one PASS, 130 RUNNING and 367 NOT_RUN; no candidate or global completion.

The earlier `dac2-production-20261024-finalgo-00-insight-robustness` attempt
is preserved as controlled-abort history, excluded from active index-09 inputs.
The adjacent receipt
`.setup-logs/implementation/revision-20261024/dac-performance/production-authorization-correction.json`
(SHA256 `d2c5736eb1886229a315beffb758c178d1f1004565f34b16add914d0618f9c5d`)
records owned launcher SIGTERM/cleanup while repairing only the ignored
launcher's context-ZIP membership check. It explicitly reports no observed
RTL/result failure, unchanged frozen53, and valid parent authorization within
the user's approved plan. Original artifacts and index-08 remain untouched;
this history is not classified as a hardware failure.

## Matched trained-power ingestion release (2026-10-24)

This section supersedes the earlier absence of power ingestion; it does not
refresh any running index snapshot. The unchanged 489 non-power rows retain
their existing inspectors. Nine `matched-power` rows are eligible: FCFS,
RR10 and MAIN, seeds 509--511. Each requires separate accepted A and B cases
in the same explicit manifest. A single accepted arm remains UNRESOLVED and
contributes zero matrix rows. Power records appear in `matched_power` and
row `power_evidence`, never in latency `performance.accepted_records`.

Explicit input basename: `matched-power-acceptance.json`. Minimal schema:

```json
{
  "schema": "cxl-matched-trained-power-acceptance-v1",
  "cases": [{
    "policy": "fai-main", "seed": 509, "arm": "A",
    "export_dir": "/absolute/local/export",
    "remote_dir": "/absolute/local/downloaded-run",
    "native_exit": {"path": "/absolute/local/native-exit.json", "sha256": "<sha256>"},
    "native_exit_field": "exit",
    "semantic_receipt": {"path": "/absolute/local/semantic-release.json", "sha256": "<sha256>"}
  }]
}
```

Paths resolve relative to the manifest, or may be absolute. `native_exit_field`
is `exit` for the first native exporter wrapper and `exit_code` for remaining
capture receipts. Policy values are the actual exporter names `fcfs`, `rr`,
`fai-main`; duplicate identities are rejected. Missing semantic receipts may
be null while raw evidence is inspected. Missing, malformed, mismatched or
unreviewed evidence never becomes PASS.

The case inspector reuses `check_power_replay.check_mode`, `check_replay` and
`check_pt`. It recomputes native metadata/audit/vector/source-ZIP hashes and
archive member hashes; checks exact real W5M training, trace configuration,
phase counts, closing evidence, conservation, native process exit; and binds
prepared payload/runtime bytes, all four transport exits, command transcript,
remote stage exits, every returned report, identical remote before/after
sources, mapped netlist/SDC/config, cell-model/database and replay/SAIF/PT
audits. It does not rerun the ten-million-cycle model or start tools remotely.

The actual export archive has **32** project members. Its canonical digest is
`52311700ace139bbbae6ed2f324b17404291322c60ed18df4247a71e86f61918`.
These equal the common projection of the parent's frozen33; the additional
parent entry is `scripts/test_power_extension.py`. The three mapped archives
have separate policy-specific anchors, not one shared netlist digest.

Semantic approval is an immutable parent-reviewed receipt, pinned in
`POWER_REVIEW_RELEASE_SHA256`; the input cannot choose another anchor. The
only production receipt currently pinned is
`remote-matrix/first-main509a-semantic.json`, SHA256
`4158918ed4d602d5f0427f904a9074b14e6ff44b6af926808814395179abca22`.
Its actual `cxl-main509a-semantic-release-v1` fields are checked against the
export, prepared receipt, payload, remote result, transcript and complete
reviewed file inventory. Its independently reviewed JSON is separately hashed
and checked for an adopted decision, no blocking issues, matching returned
hashes, and matching recomputed checker audits. Parent acceptance covers the
56 disconnected SAIF aliases, 34 literal-constant leaf gaps and 9011 FF clocks;
this index does not substitute generic tool exit0 for that review.

For future individually reviewed cases the parent may provide
`cxl-trained-power-semantic-acceptance-v1` with `case` (policy/seed/arm),
`decision=ADOPT_PRE_LAYOUT_TT25NS_MATCHED_POWER`, empty `problems`, nonempty
`limitations`, complete `reports` (remote-result file/hash map), and `bindings`:
`metadata`, `audit`, `source_archive`, `vectors`, `native_exit`, `prepared`,
`payload`, `remote_result`, `transcript` (each the corresponding file SHA256).
It also needs `independent_review` (path) and `independent_review_sha256`.
That review uses the actual first-case fields `status=ADOPTED_...`, empty
`blocking_issues`, `downloaded_hashes`, `checker_replay`, and `checker_pt`.
Each future receipt hash requires separate parent review before being added
to the pinned set. The first release authorizes no later case automatically.

Actual single-case input and read-only check results are retained in
`.setup-logs/implementation/revision-20261024/power-index/`:
`matched-power-acceptance.json`, `first-case-pending-check.json` (before the
parent release), and `first-case-released-check.json`. Main509A raw contracts
and semantic receipt pass; Main509 has only A, so the row stays UNRESOLVED.
No production index CLI snapshot was refreshed by this sidecar.

After parent source review, append this input to the existing explicit inputs:

```text
python -B scripts/index_revision_evidence.py --input <existing-matrix-or-bundle> --input .setup-logs/implementation/revision-20261024/power-index/matched-power-acceptance.json --out <fresh-output-directory>
```

Validation: original 23 index tests plus five power tests pass (28 total).
Adversarial coverage includes wrong arm/seed/policy, unapproved source closure,
W256/legacy schema, trace digest, tampered reports/SAIF/payload, nonzero or
missing stage evidence, rebound native failure, duplicate identity, caller
PASS, unpinned receipt and mismatched semantic bindings. Synthetic complete
A/B fixtures exercise the only path to a power-row PASS. Existing analysis
regression: 20 tests PASS (48 combined, zero skips/failures). No simulation,
export, SSH or remote job is launched.

## Explicit recovered FCFS509A ingestion (2026-10-24)

The only recovered case authorized here is FCFS509A. Its original prepared
payload, transcript, preflight/upload exits0, and power/fetch exits255 remain
in the original `remote_dir`. Nothing replaces those failures with exit0.
An optional case `recovery` object adds seven `{path, sha256}` references:
`plan`, `inspection`, `result`, `inspect_exit`, `fetch_exit`, `fetch_archive`,
and `reviewer_receipt`. All are explicit retained local evidence; report paths
resolve from the recovery result's parent directory under `results/`.

Acceptance additionally checks the recovery plan's original prepared/transcript/
failed-exit hashes, exact same remote case/payload/runtime/source paths, idle
completed inspection, inspection/fetch exits0, inspected actual EDA exits0,
result-to-inspection/archive hashes, exact28 inventory, every safe unique tar
member hash and every downloaded report hash. The existing native export,
source archive, mapped-policy, replay/SAIF/PT checks still run. Actual downloaded
compile/sim/PT/shell exits must all be0 regardless of the transport outcome.
No remote-result file is fabricated in the original failed directory.

The pinned parent release is
`remote-matrix/parent-fcfs509a-semantic-1528/parent-release.json`, SHA256
`846560b2efffdb832d417b5e95adbc77cf3660a187258eaf75b7b75dec09c008`.
The independent recovered receipt SHA256 is
`a0494a4f23daf63e8d3dc3475f365c4c8d890c3eb3420ad8be7f8de078ae4b82`.
Its accepted reviewer source hash, parent copy, original failed transcript,
recovery result, all returned hashes, actual stage exits and recomputed
`replay`/`pt` audits are checked. Its three qualified table-range diagnostics
(two ramp, one load) remain in the record: PT process exit0 does not turn
`check_power` tool_result0 into a clean check. The original clean-input semantic
guard remains in force for other cases.

Output keeps `original_transport_exits`, `original_history_sha256`,
`recovery_actual_eda_exits`, explicit `recovery_evidence`, and the retained
`power_quality_status`/`qualified_range_issues`. FCFS509A alone contributes0;
the FCFS509 row is UNRESOLVED until B is individually accepted.

Implementation-specific diff, raw acceptance checks, tests and a fresh explicit
index/analysis snapshot are retained under
`.setup-logs/implementation/revision-20261024/power-index/recovery-implementation/`.
Tests: 33 index and 20 analysis PASS. Recovery mutations rebind mutable hashes
to ensure actual EDA failure, duplicate tar records, wrong case/root/payload,
active inspection, nonzero recovery exits and changed accepted reviewer are
rejected. The original expected-failure test run before the implementation is
retained. This sidecar launches no simulations, exports, SSH or EDA jobs.

Released snapshot: `power-index/recovery-implementation/snapshot-20261024T073322Z/`
under the ignored implementation root. Index and analysis CLIs both exited0.
Coverage is 11 PASS, 140 declared RUNNING, 2 UNRESOLVED, 345 NOT_RUN (498 total).
Both accepted power A cases remain incomplete A/B rows, with zero power-row
contribution. Index SHA256:
`24e589dc02cfae1b89c044fded8bbeacf535fbf31ab93fe71608a1e9b9972889`.

## Three calibrated standard releases (2026-10-24 17:05)

The parent-approved standard wrappers for FCFS509B, RR509A and RR509B are
individually pinned, respectively:
`cf4211b15b16df0024b511b40370a80cb1801c593555e3e95f08b18ab69cf92f`,
`6c522abdb73c562ab510ece17b71be2dd671c3bdfafb11e193609ef1f7843d54`,
`8651b8b42391ad9628be00cd9fa71bc16c0cbc0d643212d51cdc61e44fcf28fd`.
The earlier Main509A and recovered FCFS509A anchors remain unchanged.

For explicit `review_contract=calibrated-replay-pt-v1`, the index reads the
actual independent receipt's `replay` and `pt` fields and compares them to
the unchanged raw checker audits. It hashes the referenced calibrated caller
and its immutable base `caller.parent.parent/review.py`, checking the wrapper
and actual review's caller/base/reviewer hashes. Missing/unknown contracts or
changed source bytes cannot grant acceptance. Legacy receipts retain the
existing `checker_replay`/`checker_pt` validation. The index adds no floating
FF-clock-rate tolerance: the parent-approved calibrated reviewer owns the
six-significant-digit PT display check, while exact SAIF TC/window checks stay
in the frozen replay checker. Table-range qualifications are retained for
standard and recovered cases.

The parent five-case manifest is preserved. A corrected copy in
`power-index/standard-implementation-1705/matched-power-acceptance.json`
uses the real `exit_code` native receipt field for the three new cases, rather
than the parent manifest's nonexistent `native_exit` field. Native receipt
bytes and hashes, wrappers, continuation, reviewer and all frozen inputs are
unchanged. `manifest-corrections.json` records these three input corrections.

All five actual cases pass inspection; FCFS509 and RR509 form exactly two
accepted power rows. Main509 retains only A and stays UNRESOLVED. Tests:
36 index plus 20 analysis PASS, including calibrated actual-field pairs,
missing-B behavior, rebound bad contracts/audits/caller/base hashes and changed
reviewer files. The expected failing run before the implementation is retained.
Diff, tests, actual checks and a fresh index/analysis snapshot are under
`power-index/standard-implementation-1705/`; no new experiment is launched.

Snapshot `snapshot-20261024T090714Z/index/matrix-coverage.json`: 13 PASS,
140 declared RUNNING, 1 UNRESOLVED, 344 NOT_RUN (498 total); power rows2/9.
Index and analysis CLI exits0; SHA256
`e7167fa0f034cd81526a77b41a462aed14b178ec086adfc4f247b1eab1c10216`.

## Conditional completion subtotal correction (2026-10-25)

`matrix.completion.matrix_contribution_from_insight` now counts accepted
conditional matrix rows. It previously remained hardcoded0 after the actual
DAC20 confirmation and10 robustness rows passed; the overall PASS total was
already correct. The count uses final unique row statuses, so duplicated
inputs do not multiply it. Model-only insight inventory remains contribution0,
and W256 remains contribution0. The regression checks empty inputs, a W256
pilot, all30 accepted conditional rows, and duplicate production input plus
the pilot. Previous snapshots/hashes remain unchanged; a uniquely named
corrected index/analysis lives under
`power-index/continuation-20261025/conditional-count-fix/`.

## Exact recovered Main509B extension (2026-10-25)

The new parent release SHA256 is
`7f0477ea451d003355c4e8af064408e41b58b21e58fe500959f388feaa2ef82e`.
Recovery is allowed only for FCFS509A or Main509B with the original
preflight/upload0 and power/fetch255. The shared recovery inspector retains
exact plan/case/payload/source binding, idle actual EDA completion, inspected
and fetched28-file inventories, unique tar members and full report hashes.
No original standard exit0 result is fabricated.

Main509B additionally checks the parent-bound result/inspection references,
both independent and parent semantic receipts (equal except checked_utc),
the exact MainB adapter, calibrated caller, frozen recovery reviewer and
immutable base reviewer hashes. Raw replay/SAIF/PT audits and original failed
transcript must match the accepted reviews. The five legacy contracts and
their anchors remain unchanged. Tests cover altered receipts, wrong arm/case,
synthetic original0, missing B, dual-review/source drift, and accepted Main A+B.

Implementation evidence is under `power-index/main509b-implementation-20261025/`:
40 index and20 analysis tests PASS; actual six-case manifest inspection
accepts all three seed509 policy A/B pairs. Native exit uses actual `exit_code`.
The six-case manifest is new; the accepted five-case manifest, prior snapshots,
reviewers and frozen39/53/33 are preserved. A fresh strict index/analysis is
provided for parent review; no simulation or remote EDA is launched.

Six-case snapshot `snapshot-20261024T201624Z` under that scope has199 PASS,
45 RUNNING,254 NOT_RUN,0 UNRESOLVED/FAIL; matched power3/9, conditional30,
W2560. Index and analysis exit0; core/DAC inference is unchanged. Index SHA256
`1d1f1363c79bbee74e2da601827a1cdc018ee8b430780da8a413ba7d5c0c0a86`.

## Four exact seed510 standard releases (2026-10-25)

Only four parent-approved hashes are added to the existing allowlist:
FCFS510A `607dd4a59a50a00405c98a566ef37f5a600e378eb79a87bd2ef5081568ff77be`,
FCFS510B `fab86204015b85623eb40c15c96a421e1394277ce02003990a38423d2a98b2eb`,
RR510A `e1f32b3575df13039aeeed10dfaf1181d34e39028c716164d1f62c75aaaf595e`,
RR510B `3be1c1bbec8fc7ca472858643b2af72e36d59394f24dcd30af9089cd5fc6857b`.
They use the unchanged calibrated standard contract. No schema, reviewer,
recovery, frozen runtime or acceptance logic changes are introduced.

The cumulative10-case input is the parent's original
`parent-continuation-20261025T0728/power-acceptance/matched-power-acceptance.json`.
All10 actual native receipt fields and hashes check correctly; all10 cases
pass strict inspection and form5 accepted power pairs. Main510 and all seed511
pairs are not supplied or inferred. The regression rejects a modified release
with a caller-updated digest and separately rejects wrong identity bindings,
then verifies restoration of the exact release. Index41 and analysis20 tests
PASS. Tests, actual checks, diff, input hashes and fresh combined snapshot are
under `power-index/seed510-implementation-20261025/`, for parent review.

## Exact recovered Main510A extension (2026-10-25)

Only recovered `fai-main-A-s510` is added to the existing recovery contract,
with parent release SHA256
`63d1278c39245511d136f4d6413c6eed49b2274f04325d9ec75f594cad655c66`.
The original preflight/upload0 and power/fetch255 history remains required and
unchanged; the separate read-only recovery proves idle actual compile/sim/PT/
shell0 with all28 downloaded hashes. No rerun or fabricated original0 is used.

Main510A requires its exact recovery schema/status, parent-bound result and
inspection, pinned independent review, parent/independent equality except
checked_utc, and the accepted Main510A reviewer, calibrated caller, frozen
recovery reviewer and immutable base hashes. Recovery/continuation plan hashes
must match the accepted review. The actual parent release omits the warning
count: only this exact case defaults that omission to0, which must equal the
recomputed raw PT count. FCFS509A/Main509B contracts retain their requirements.

The cumulative11-case manifest under
`power-index/main510a-implementation-20261025T1557/` has SHA256
`8bd53d832a5ad7c151b20635a2d95e6d668b13c510a2573905af9875be90fe53`. All11 actual cases pass strict local inspection;
matched-power remains5/9 accepted pairs. Main510A alone adds0 rows; no Main510B
or seed511 acceptance is inferred from the active remaining7 executor.

45 index tests and20 analysis regression tests PASS. New negative cases cover
wrong identities/old labels, pending or unpinned releases, synthetic original0,
active/failed recovery, changed archive/payload/reports, plan drift and dual
review/source drift. The initial expected failing Main510A test, final logs,
diff, actual checks, preservation receipts and release are in that ignored
scope. This is prepared evidence for parent review, not adoption of a new
combined index. No SSH, EDA, model replay or cleanup was performed.

## Exact recovered Main510B extension (2026-10-26)

Only recovered `fai-main-B-s510` is additionally accepted, with parent wrapper
SHA256 `a99c7cb934407753df9ed1d394b314c08d05f26c998f4d7228071c9b420a2f92`.
The existing recovery inspector verifies its actual plan/result labels, original
preflight/upload0 and power/fetch255, separate inspect/fetch0, actual
compile/sim/PT/shell0, exact28 returned/archive hashes, and source/mapped/runtime
bindings. No original255 record is changed to0 and no standard-success bypass
is used.

The parent wrapper binds both semantic receipts, equal except checked_utc,
and the exact reviewer adapter
`835a09407e31ed3e9e93bbd1a994756630e35c250d265e18767b2adc747e4fa8`.
Its calibrated caller, frozen recovery reviewer, immutable base, prior Main510A
adapter, recovery/continuation plan hashes, actual replay/PT and native export
audit remain checked. As with exact Main510A, the wrapper's omitted warning
count defaults to0 only for this case and must equal the recomputed PT count.
Existing11 cases and their contracts remain unchanged.

The cumulative12-case manifest and actual inspection receipts are under
`power-index/main510b-index-20261026T0534/`; only accepted Main510B is appended
to the unchanged11-case input. All12 actual cases PASS and form6 complete
matched-power pairs. Missing B contributes0. No seed511 case is inferred.
49 index tests (existing45 plus4 new Main510B regressions) and20 analysis tests
PASS. New mutations cover wrong arm/seed/case, pending/changed parent release,
synthetic original0, actual payload/archive/source changes, plan drift, dual
semantic mismatch and every frozen reviewer dependency. Initial pre-extension
rejection, final test logs, diff, preserved input/source hashes and the fresh
combined snapshot are retained for independent parent review. No new
simulation, SSH, EDA, model replay or frozen-source edit was performed.

## Explicit detached FCFS511A contract (2026-10-26)

The only newly accepted detached case is `fcfs-A-s511`, under parent wrapper
SHA256 `b401165cc68e36c0cf29601f95de4ae6bfa9218f4af6cfb7903415edaff7c89f`,
schema `cxl-detached-trained-power-semantic-release-v1` and status
`PARENT_ACCEPTED_DETACHED_TRAINED_POWER_CASE`. The manifest explicitly declares
`transport_contract=cxl-detached-trained-power-v1`; all12 prior foreground and
recovered cases retain their original contracts and failed-transport history.

The index reuses only `bindings`, `ready`, `validate_transport` and
`launch_context` from the local reviewer pinned to
`4d04b00deac1a2b19cd24abab70f2cdeb1439daed407674bdd127d9f52fcf4e2`.
The controller plan and imported helper bindings are checked before import.
No `review_case`, producer, SSH, cleanup, simulation or EDA function is called.
Actual detached PID/startticks, claims, wrapper/terminal poll, inspection,
transport requests/exits/logs, exact28 fetched files/archive, launch-context,
source/runtime/mapped and native export bindings are rechecked. Foreground
`power.exit.json` must be absent; the power stage's0 denotes inspected actual
EDA completion, not a fabricated SSH exit.

Both exact parent/independent semantic receipts must agree except checked_utc
and match the recomputed transport/launch proof, source pins, native window,
raw replay/PT and returned hashes. The reviewed adapter's historical
`PARENT_ADOPTION_REQUIRED` status alone cannot grant acceptance; the pinned
parent wrapper is also required. No other seed511 case is authorized by this
release.

The cumulative13-case manifest under
`power-index/index-detached-20261026t0623/` appends only accepted FCFS511A to
the unchanged12-case input. All13 actual cases pass strict inspection; power
remains6/9 complete A/B pairs. The single FCFS511A contributes0 matrix rows
and its missing-B pair remains UNRESOLVED.

55 index tests (existing49 plus6 detached regressions) and20 analysis tests
PASS. Detached synthetic fixtures mock only the separately reviewed transport
module; production inspection imports and checks the exact real module and
actual returned evidence. New tests reject wrong identity/contract, unpinned
or rebound parent claims, semantic disagreement, fake foreground receipts,
incomplete wrapper/launch proof, changed actual source/archive/reports and
unpinned executable code. Final tests, actual13 inspection, source guards,
diff, hashes and a unique strict index/analysis snapshot are retained in that
ignored scope for parent review. No frozen33/39/53 or other tracked path is
changed.

## Exact detached FCFS511 A/B pair (2026-10-26)

Parent-approved FCFS511B wrapper SHA256
`2b6888ef0c6a3a87ba3c05b069514e5e30a860af7082e41050aa8e7344df280f`
uses the unchanged detached schema/status and pinned reviewer. The existing
identity guard now allows only FCFS seed511 armsA/B and checks the derived
exact case ID. No helper, transport-proof or other-policy acceptance change
is introduced. The A-only release and its13-case manifest remain intact.

`power-index/index-detached-pair-20261026t0636/` adds only accepted B to that
manifest. All14 actual cases pass strict inspection, closing the seventh
matched-power pair. Missing either arm still contributes0. One new focused
pair-closure regression checks accepted B, A/B pairing, each missing arm,
wrong-arm metadata and rebound parent/independent semantic disagreement.
Existing55 tests plus that regression (56 total) PASS. The unchanged20-analysis
test receipt from the adopted A release is hash-bound and is not rerun; the
actual new strict snapshot and analysis are run after code freeze. Source
guards, exact hashes, logs and old-input bindings are retained in the new
ignored scope for parent review. RR/Main seed511 remain unaccepted here.

## Final four exact detached seed511 cases (2026-10-26)

The parent adopted RR/Main seed511 armsA/B under four exact wrapper pins:
RR A `5b58cbf94de2ffb16f4841f4621dc0ec694a353d520d94330db53c557ac65aff`,
RR B `9d5b5148caf27be893edd450690d7224aca2dc6c59725eeffaada574ce2a8cca`,
Main A `c97c90c0205085e2228c10cb1dfb82ee80e8d652cde40b5ac1ab7729f4ce739d`,
Main B `0ef576f6744ed94371e317d3c2b282dd97e441471ecde05b6e8dba3b8bf4f7f4`.
The existing identity guard now allows exactly FCFS/RR/Main, seed511, armsA/B,
deriving the case ID from policy and arm. Schema, reviewer, controller,
native/raw transport, launch context and dual semantic proofs are unchanged;
no new helper or transport framework is introduced.

`power-index/index-detached-final4-20261026t0912/` appends only those four
accepted cases to the unchanged14-case manifest objects, retaining earlier
inputs and releases. All18 actual cases pass strict inspection and complete
9/9 matched-power pairs. One parameterized regression covers each new policy/
arm, same-policy pair closure, either missing arm, wrong policy/arm/seed and
rebound parent/independent semantic disagreement, with isolated fixture state.
All57 index tests (prior56 plus that regression) PASS. The unchanged adopted
analysis20 receipt is hash-bound, not rerun; actual strict index/analysis are
executed after source freeze. Source39/53/33 and protected539 guards, test log,
diff, exact adoption/manifest bindings and final artifact hashes are retained
for independent parent review. Power completion does not imply completion of
the remaining simulation matrix or physical power signoff.
