# Current-result analysis sidecar

Implemented against repository HEAD `99400de` on 2026-10-24 (Asia/Taipei).
Owned files are `scripts/analyze_revision_results.py`, its adjacent test, and
this document. Generated files live under the ignored
`artifacts/implementation/revision-current-analysis/` directory. Existing
scripts, shared reports, RTL, source-freeze dependencies, model/legacy results,
pilot execution and the production queue are outside this change.

## Acceptance and inputs

The adapter accepts either an explicitly named saved
`cxl-revision-evidence-index-v1` JSON file or repeated exact runner directories.
It calls `index_revision_evidence.inspect_performance_bundle` for every referenced
bundle. A saved index must contain the exact current matrix; every accepted
record must match the reinspected result, result SHA256, trace SHA256, seed,
exit codes, production flag and both archive SHA256 values. Extra or duplicate
accepted records are rejected. Relative bundle paths in saved indexes are
rejected rather than resolved against a guessed working directory.

The existing inspector remains the acceptance boundary for ZIP safety and
contents, source manifests and archives, frozen configs, exact current jobs and
parameters, scope/summary/result agreement, tests and tool exits. FAIL,
RUNNING and UNRESOLVED bundles are rejected. No model-only or W256 input can
become accepted production metrics. A complete selected production subset can
be analyzed without claiming matrix completion.

Output is a new directory containing `analysis.json` and content-addressed
`inputs/<sha256>.json` copies of the exact input index, selected result bytes,
and inspected JSON metadata (frozen spec, source manifests, scope and summary).
Original paths and SHA256 values are recorded. Full inspector records retain
archive hashes and member inventories; ZIP archives stay at their original
paths. Adapter, indexer, matrix and statistics implementation hashes are also
recorded. Metadata and result bytes are checked again against the inspection
hashes before use. Existing output directories are refused, and output inside
an evidence bundle is refused because it would alter the bundle's contents.

## Metrics and inference

Each trained job supplies two separate generation cohorts, A and B. The adapter
recomputes nearest-rank P50/P90/P99/P999, maximum, count and mean from direct
histograms for every source and pooled sparse population, for all three stages:
generation to acceptance, acceptance to fire, and generation to fire.
Reported statistics must agree with the histogram. Histogram keys/counts must
be canonical nonnegative integer cycles and positive integer frequencies.
Generated and completed populations must agree. Each source histogram count
must match that population, and every pooled sparse histogram must equal the
sum of the source histograms excluding the configured heavy source.

Source arrays retain physical source-ID order. The traffic generator swaps
canonical streams 0 and `heavy_source` before producing events; its passive
metrics are already indexed by those physical IDs. The adapter therefore
excludes `job.heavy_source` directly and does not swap the arrays again. An
asymmetric heavy-ID3 fixture verifies that sparse source 0 stays in the pool
and heavy source 3 stays out. This fixed heavy identity applies only to HOG;
adaptation changes its heavy role during the continuous run and is excluded.

Zero generated/completed counts for individual sources are valid when their
histograms are empty and their reported statistics are null. Counts are
nonnegative, not necessarily positive for every source. A selected A/B cohort
must still contain a nonempty sparse generation-to-fire population to form a
seed/run P99 endpoint; an entirely empty or heavy-only selected cohort is
rejected rather than counted as a replicate. The unused `cold` cohort and the
inactive A or B in a cold replay may be empty and are not normalized as HOG
endpoints. Tests include these actual serializer shapes.

Every endpoint also preserves `phase_metrics` verbatim from the corresponding
`metrics.phases[A/B]`: cycles, ready, generated, offered, accepted, fired,
backlog/occupancy summaries, eligible-ready opportunities/utilization,
avoidable bubbles and service-gap samples, including their censoring labels.
These are original phase observations, not recomputed statistics or additional
fairness metrics. `completed_by_phase` is copied separately from the generation
cohort. Phase fires include work generated in other phases; cohort latency
populations include that cohort's eventual completions in guard/drain phases.
The phase counts never replace the cohort histogram's count or the seed/run
denominator. A fixture with two per-source in-phase fires and three eventual
cohort completions checks that both are retained without conflating them.

The seed/run endpoint is the pooled sparse generation-to-fire P99. Sources,
requests, latency stages, and A/B cohorts are never independent bootstrap
replicates. Cohorts are separated by policy, profile and exact configuration,
including matrix group and seed role; source manifests must also agree across
seeds. Legitimate configuration sweeps remain separate cohorts. Duplicate
seed/run endpoints and heterogeneous sources within a cohort are rejected.

Comparisons require the same profile, traffic/experimental boundary and source
manifest, plus identical intended trace hashes for each shared seed. Policy
parameters (RR quantum and High/Low quotas) may differ as the treatment; each
policy's own configuration must be constant across its seeds. Pairs with
incompatible groups or other boundaries are not combined.

Only a complete prespecified 529--548 pair calls
`revision_statistics.paired_runs(..., confirmation=True)`: 20 seed/run pairs,
10,000 paired bootstrap resamples, fixed RNG seed `20261023`, and the existing
95% percentile convention. Complete 509--513 pairs use the helper's descriptive
exploration mode without a CI. Missing seeds are listed separately for each
policy; incomplete pairs produce no effect estimate or confirmation interval.
Coverage bookkeeping never bootstraps a policy against itself. P999 and maximum
remain descriptive.

The core denominator is exactly 120 trained N4 confirmation jobs across six
policies and 20 seeds. A/B do not double it. Optional `--include-cold` output
uses separate cold-A/cold-B profiles, zero training cycles and independent
coverage/comparisons. Cold runs do not complete trained jobs. Adaptation's
continuous role-change experiment and non-RTL-required matrix jobs are excluded
from this HOG adapter. The JSON explicitly lists their IDs and exclusion
reasons in `excluded_matrix_jobs`, including all nine adaptation rows.
`scope` identifies this as HOG A/B subset analysis, not full-matrix analysis.

Default comparisons are FCFS:MAIN and RR10:MAIN. Repeat `--compare` to request
other policy pairs; this replaces the defaults.

```powershell
python scripts/analyze_revision_results.py `
  --index artifacts/implementation/revision-evidence-index/20261024-index-01/index-05/matrix-coverage.json `
  --out artifacts/implementation/revision-current-analysis/NEW-DIRECTORY

python scripts/analyze_revision_results.py `
  --bundle PATH-TO-TRAINED-RUNNER-DIRECTORY `
  --compare FCFS:MAIN `
  --out artifacts/implementation/revision-current-analysis/ANOTHER-NEW-DIRECTORY
```

## Verification and observed result

Executed locally with Python 3.13.5:

```powershell
python -m unittest discover -s scripts -p test_analyze_revision_results.py -v
python -m unittest discover -s scripts -p test_index_revision_evidence.py -v
python -m unittest discover -s scripts -p test_revision_statistics.py -v
```

Results after the cold-helper handoff: 14 adapter tests, 16 indexer tests and 4 statistics
tests passed, with no skips. The adapter tests reuse the indexer's sealed
source-bound fixture builder and its full inspector. These small synthetic
fixtures exercise arithmetic and acceptance wiring; they are not observed
production RTL measurements.

Coverage includes a 40-bundle end-to-end confirmation fixture (20 FCFS and
20 MAIN jobs, independently analyzed A/B), deterministic bootstrap, a 10-bundle
descriptive exploration pipeline, incomplete seeds with no inference call, corrupt histograms and
populations, wrong sparse pooling, unpaired traces, heterogeneous
configuration/source cohorts, duplicate seed/runs, stale index result hashes,
extra accepted index rows, bad ZIP/config/job/model/exit evidence, original-byte
preservation and refusal to overwrite or modify an input bundle.
The added tests cover unconditional cold-A/B acceptance through both direct
bundles and a saved index, empty inactive cohorts, physical heavy-ID3 ordering,
zero-count sources, rejected empty selected populations, raw phase/gap field
preservation and explicit adaptation exclusion.

The saved `index-05/matrix-coverage.json` was also analyzed directly.
Its input SHA256 is
`5c3e97fbef9c8de37ce898581dd70deab2ee24516a74f570d63928825eea533c`.
The initial output is
`artifacts/implementation/revision-current-analysis/20261024-adapter-01/`;
the initial final-code rerun and test logs are under
`artifacts/implementation/revision-current-analysis/20261024-adapter-02/`.
The cold-helper/phase-metrics follow-up rerun, with `--include-cold`, and its
final test logs are under
`artifacts/implementation/revision-current-analysis/20261024-adapter-03/`.
Observed result: 0 endpoints, 0/120 accepted core jobs, all 120 missing;
150 trained policy/config/profile coverage cohorts, 48 requested comparison
records, and zero bootstrap intervals. The `--include-cold` follow-up adds
separate optional coverage (300 profiles/configurations and 96 comparison
records total), still with zero endpoints, zero intervals and 0/120 core jobs.
This reflects that saved index's
accepted records and does not inspect unlisted experiments or infer queue state.

## Cold acceptance handoff

During the first verification, the inspector's `result_payload_check` expected
`cold="A"` or `"B"`, while the actual RTL result writer emits boolean
`cold=true` and a separate `cold_cohort`. The specific locations and the
source-bound fixture builder were sent directly to the indexer owner, Hegel.
Hegel released `cold=bool(lane_cold(lane))` plus a strict boolean type check;
`cold_cohort` and the frozen config's A/B environment value remain separate.
The adapter did not modify or bypass the inspector.

The optional-cold test now unconditionally requires real boolean cold-A and
cold-B fixtures to pass strict inspection, saved-index analysis and adapter
analysis. There is no conditional success path or skip for helper rejection.
Cold-only fixtures leave core acceptance at 0/120; adding one trained fixture
gives 1/120 despite four profile endpoints. Default analysis excludes cold
endpoints. These remain synthetic acceptance fixtures, not production runs.

No production simulation, pilot rerun, queue launch, plot, dashboard, new
dependency, manuscript change or legacy-result rewrite was performed.

## DAC conditional integration release (2026-10-24)

The adapter, tests and this document are outside both production source
closures. The verified core closure has 39 files and canonical manifest SHA256
`800653c08ab5d2047ae4f11362c653344b49953c18c0ccfb33c89bd62d84af86`;
the DAC closure has 53 files and SHA256
`4eca15454a0ba1c75a88e5f0431f32730a50c02bc047fa8ca3a899715b206227`.
Both remain unchanged. Only the three adapter-owned files were edited.

DAC intake uses the released `inspect_performance_bundle` dispatch and
reinspects saved-index records. In addition to the existing archive, source,
config, job, result, trace and exit checks, DAC index rows bind
`selected_policy`, `declared_job_id`, `matrix_contribution`, `source_sha256`,
`core_source_sha256` and `acceptance_binding_sha256`. Accepted and descriptive
record classifications must match inspection; boolean/integer substitutions
are rejected. DAC1 and W256 records enter through `performance.descriptive_records`
with zero matrix contribution.

The separate `conditional_dac` report compares DAC2 against trained MAIN.
Each policy's full source/config cohort must be homogeneous across seeds.
Cross-policy compatibility requires matching hashes for all actual shared
39 core files, rather than equality of the DAC53 and MAIN39 full manifests.
Full manifests remain in the output. Paired runs also require identical seed,
arrival trace hash, trace configuration and mapped experimental configuration.
Confirmation maps to MAIN N4 confirmation; each readiness robustness case maps
to the corresponding trained MAIN readiness case.

The core denominator remains 120 trained N4 jobs. Conditional confirmation
has its own 20-job denominator; conditional robustness has its own 10-job
denominator, split into two five-seed configurations. A/B profiles do not
double any job denominator. Only a complete 529--548 confirmation pair uses
the existing fixed 10,000-resample bootstrap. Robustness seeds 509--513 are
descriptive. Missing pairs list missing seeds and produce no effect estimate
or CI. DAC1 and W256 endpoints contribute to neither denominator nor paired
inference. Each DAC profile preserves the original `metrics.phases[A/B]`,
including phase counts and service gaps, plus generation-cohort
`completed_by_phase`; phase/fire counts are not substituted for cohort counts.
Adaptation remains explicitly excluded. This is subset analysis, not analysis
of the full matrix.

Final validation: Windows adapter **20/20**, indexer **23/23**, statistics
**4/4**, totaling **47 PASS**, with no skips. The adapter also passed
**20/20 under WSL**. The earlier 14/16/4 counts above describe the historical
cold-helper handoff. New strict source-bound fixtures exercise shared39
compatibility with different full manifests, complete confirmation and
robustness cohorts, incomplete and empty cohorts, source/config/trace/policy
mismatches, saved-index binding corruption and DAC1/W256 descriptive-only
intake. These are synthetic acceptance fixtures, not production measurements.
The parent independently confirmed the final Windows 47-test result.

The final saved-index analysis uses
`artifacts/implementation/revision-evidence-index/20261024-index-01/index-09/matrix-coverage.json`,
whose SHA256 was checked against the released value:
`aed7219fe93a5bf5f5782bb72d5c86a0e9231cfec0f654ba1257495a573717bf`.
Reproduce into a new directory with:

```powershell
python -B scripts/analyze_revision_results.py `
  --index artifacts/implementation/revision-evidence-index/20261024-index-01/index-09/matrix-coverage.json `
  --out artifacts/implementation/revision-current-analysis/NEW-DIRECTORY
```

Released output:
`artifacts/implementation/revision-current-analysis/20261024-adapter-dac-index09-01/analysis.json`.
Its `inputs/` directory retains content-addressed original input bytes;
the report records input and implementation hashes. Output directories cannot
be overwritten. The saved snapshot has core **0/120**, DAC confirmation
**0/20**, DAC robustness **0/10**, four strictly inspected W256 descriptive
A/B endpoints and **zero CIs**. The resource PASS row is an accepted N16
n-expansion RTL job, but not an N4 core-confirmation or DAC conditional job.
RUNNING rows do not contribute completed performance evidence.
This does not infer live queue progress or wait for production completion.

Earlier DAC verification artifacts, including the WSL adapter log and closure
checks, remain under
`artifacts/implementation/revision-current-analysis/20261024-adapter-dac-01-checks/`.
The prior index-08 output is historical; index-09 is the current handoff
snapshot. No simulation or experiment launch was performed for this integration.


## Superseding acceptance snapshot2026-10-26

The index-09 handoff above is historical. The accepted current snapshot is
`.setup-logs/implementation/revision-20261024/power-index/index-detached-final4-20261026t0912/snapshot/`:
index/matrix-coverage.json and analysis/analysis.json both exited0. It retains
120/120 core confirmation,20/20 DAC confirmation and10/10 DAC robustness, plus
all18 trained-power captures/nine A/B rows. Parent/independent final index review
accepted259PASS/180declaredRUNNING/59NOT_RUN of498; unsealed core robustness
still contributes0 and no partial robustness CI is inferred. This checkpoint
does not rerun simulations or alter the frozen statistical method.

## Superseding robustness acceptance2026-10-26

The later accepted snapshot is
`.setup-logs/implementation/revision-20261024/power-index/robustness-sealed-20261026t1518/snapshot/`.
It adds180 sealed core robustness rows and preserves the previous259:
439PASS/30declaredRUNNING/29NOT_RUN of498, zeroFAIL/UNRESOLVED.
Parent rehashed all19 release artifacts and independently inspected the180-run
bundle; adoption is recorded in
`parent-continuation-20261026T1518/robustness-index-adoption.json`.
The four DAC/Main backpressure comparisons each contain five paired exploration
seeds and receive no confidence intervals. N8 is active with three simulators;
unsealed results contribute no PASS. ROBUSTNESS_RESULTS.md and its independent review were subsequently accepted;
see parent-continuation-20261026T1600/robustness-report-adoption.json.


## Superseding N8 acceptance2026-10-27

The current accepted snapshot is
`.setup-logs/implementation/revision-20261024/power-index/n8-sealed-20261027t0202/snapshot/`.
It preserves the prior439 and accepts30 sealed N8 jobs:
469PASS/25declaredRUNNING/4NOT_RUN of498, zeroFAIL/UNRESOLVED.
Parent independently rechecked30 runs/60 sparse endpoints and all12 descriptive
cohorts, then adopted the snapshot after independent review:
`parent-continuation-20261027T0202/n8-adoption.json`.
Four same-N Main-versus-FCFS/RR10 comparisons use exploration509-513 without CI.
Main A/B mean run-P99 is10/27.6, RR10 is12/21, and FCFS is20/37.6 cycles.
No global winner, cross-N matched trace or full60 acceptance is claimed.
N16 has only the earlier resource case accepted; unsealed raw outputs remain
outside PASS. The full N expansion report awaits all60 exact rows.


## Superseding N16 partial acceptance2026-10-27

The current accepted snapshot is
`.setup-logs/implementation/revision-20261024/power-index/n16-25-sealed-20261027t0248/snapshot/`.
It preserves469 prior rows and adds25 sealed non-FCFS N16 rows:
494PASS/4declaredRUNNING/0NOT_RUN, zeroFAIL/UNRESOLVED. Parent adoption after
independent review is parent-continuation-20261027T0248/n16-25-adoption.json.
Ten five-seed non-FCFS cohorts and two Main/RR10 comparisons are complete.
N16 Main A/B mean run-P99 is10/34.8 versus RR10 13/24.4 cycles; the B
regression10.4cycles is retained. No CI for exploration509-513.
N16 FCFS remains incomplete: only the earlier seed509 resource case is accepted;
seeds510-513 are the final active group. Full60 N expansion analysis/report
remains gated on their seal and independent parent acceptance.


## Final498 experiment acceptance2026-10-27

All498 declared rows are sealed and accepted after independent review:
468 unconditional plus30 DAC insight rows; zero RUNNING/NOT_RUN/FAIL/UNRESOLVED.
The exact498 matrix IDs retain the prior494 rows,485 prior performance records,
and all18 power captures/nine complete pairs without change. N expansion60
counts the earlier FCFS/N16/seed509 resource case once. Final four FCFS/N16
runs pass12 steps/50 tests, zero failures/errors/skips. Core lane ordinals0-9
all exited0 and active is null. No simulation was restarted for this adoption.

Strict snapshot: power-index/final498-20261027/snapshot under ignored
revision-20261024 evidence. Writer release SHA256:
75399940a90fa0973552e78ee1c64341b47b6b0873fa96dc3e29ac4bfa113771.
Independent release SHA256:
d2f0b08e211a2b9822709641aa8499d2c3aa6918a516ac79f27a59b8600bf2cc.
Parent adoption: parent-continuation-20261027T0325/final498-adoption.json.
Parent separately rehashed15 release artifacts, re-inspected the final bundle,
recomputed all8 sparse P99 endpoints and checked drain/bubbles; an initial
diagnostic field-name mistake was corrected without modifying evidence.
Core39/DAC53/power33/protected539 files remain unchanged.

Full60 descriptive analysis/report is authorized from this exact accepted
index; narrative adoption remains pending. MANUSCRIPT_REVISION_PACKET.md
contains proposed F1-F16 edits only. The main.tex original body already uses
the correct Main-over-RR denominator; the reviewed v3 is a separate proposed
revision target, not an owner-selected replacement entry. No manuscript, PDF,
SSH or unchanged test suite was modified/run for this checkpoint. Separate
manuscript approval, final PDF QA and independent post-revision three-seat
review remain pending. Matrix PASS is not automatic closure of paper claims.


## Full60 N expansion report adoption2026-10-27

N_EXPANSION_RESULTS.md is independently reviewed and parent-accepted, SHA256
e64149b686c8b326f6baa4881108c2d9abff59ddc8e8c07bf74f03c383dc0e7c.
The frozen full60 analysis covers120 A/B endpoints,24 five-seed cohorts and8
same-N pairs; all78 input hashes and24 means/8 comparisons match the parent
independent raw-histogram/service checks. Writer release:
c6255e142c21750d2ed6c4c19ad3b561ff342116f38666772c260c984a5689e7.
Independent report release:
8e3c216b5092f5764f1a2837f9ee8ffc08adcc29992d94e81ce88059d8545f23.
Parent receipt: parent-continuation-20261027T0325/n60-report-adoption.json.

N16 FCFS mean run-P99 A/B is22/41.8, Main10/34.8 and RR10 13/24.4.
Main beats FCFS in each seed/arm but loses B to RR10 by10.4cycles; N8 B
regression is6.6cycles. Allfive B seeds regress at eachN. Exploration results
have no CI. Aggregate sparse demand7/128 versus15/128 and storage128 versus256
slots change withN; no isolated scaling causality, DAC N8/16 benefit or general
throughput improvement is inferred. All measured A/B eligible-ready opportunities
are served, while overloaded producer backlog remains distinct from localFIFO
occupancy and drains at experiment end.

This closes the planned N expansion experiment/report gap, not manuscript
revision, final evidence-manifest/PDF QA or independent post-revision paper
review. EXPERIMENT_COMPLETION.md records all498 accepted matrix rows and exact
receipts. No new simulation, SSH, source change or unchanged test-suite rerun
was needed for the analysis/report adoption.
