# H2 quota × ordering: bounded RTL confirmation preregistration

Date: 2026-11-01. Status: `PREREGISTERED_PLAN_ONLY / EXECUTION_NOT_RUN`.
Version: `ordering_confirmation_v1`. This is a new plan, not an amendment to
either exploration plan. Freeze its SHA-256 before any confirmation execution;
put that hash in the execution manifest rather than in this self-referencing file.
This task writes only this document. Commands below are prospective, not executed
checks or authorization to modify RTL, collectors, tests, historical artifacts,
STATUS, DEVELOPMENT_REPORT, PROGRESS_TRACKER, the prior review, or the manuscript.

## Material passport and provenance

- Origin workflow: academic-research-suite / experiment-agent, plan mode.
- Requested planning model: **GPT-6-Astra**; invocation path: **Codex CLI**;
  requested catalog slug: **`codex/gpt-6-astra`**; reasoning: **high**.
- Backend effective model: **`UNKNOWN`**. The requested name is provenance,
  not a verified identity of the backend serving this planning session.
- Earlier agent-spawn attempts recorded `Unknown model`; those attempts used
  a different invocation path. They do not establish the outcome of a CLI call,
  and acceptance of a CLI catalog slug would not establish backend identity.
- Planning verification: local read-only source/evidence inspection and hashing;
  no scheduler simulation, matrix, preflight pytest, or EDA run in this task.
- Working tree: existing `cxl-scheduler` repository, branch `experiment/main-sq`,
  HEAD `99400ded42cc63c3b206bd5d13f51d36344b2689`; pre-existing dirty/untracked
  work is preserved. HEAD alone does not identify the executed source snapshot.
- Independence means fresh confirmatory seeds and a frozen analysis rule, not
  blinded planning: the planner has read the exploratory results. No independent
  second reviewer or effective-model separation is claimed.

## Evidence basis and frozen boundary

Read AGENTS.md, the approval/decision and current status context, ENVIRONMENT.md,
and CXL_SPEC v1.0 §§4–5, 8.1–8.5, 9–10. The spec supplies fire-only accounting,
held outputs, window-close ordering, independent checking, nearest-rank statistics,
and separate active/drain accounting. Its primary nine-configuration verification
requirements are not replaced or completed by this supplemental W256 study.

The following local input hashes were checked during planning. Paths below the
exploration namespace are relative to
`artifacts/implementation/cgof-rtl-ordering-exploration/`.

| Input | SHA-256 |
| --- | --- |
| `specs/CXL_SPEC.md` | `797a5cdf01d2f769f44ca45225a33cc0510b04a408a8ff847e1db1c80928a4cf` |
| `docs/reviews/ordering-rtl-exploration-plan-20261101.md` | `181900933e327c7b29efee2100f277da44d16b25752b4d700e341a4d29991444` |
| `docs/reviews/ordering-rtl-exploration-correction-20261101.md` | `955ac86ae7cc6785f298ceaf58a78027eedf8e89034e9476969ffaeabc18a7d6` |
| `docs/reviews/evidence-review-followup-20261101.md`, ordering sections | `7678de79ebfc87ba2a8316eccf12790c0d2e1bb138d0a93b08550a282edd6124` |
| `correction-manifest-20261101T030414Z.json` | `4cc2aeac9c8976fe0186ef956439458f6e351605f96e825f108cf8877aa78d2b` |
| `correction-analysis-20261101T030414Z.json` | `76da0716572feea212b57a39cd8b382aabc7eb9f46205cc694ff44aff07a5fe8` |
| `correction-pair-audit-20261101T030414Z.json` | `c5fe80a1cdb5d7a13dcad4b3213da23be672f70e8093621c6e99828161a0dc76` |
| `correction-acceptance-20261101T030414Z.json` | `c667f419875aca59d8fa68e6a357a39bc0a6e91339f5bae376a3d4b0b7a44f92` |

All 31 source hashes in that manifest match current files at planning time.
This includes `scripts/run_rtl_diagnosis.py`,
`sim/experimental/test_cgof_diagnosis_traffic.py`,
`sim/experimental/test_cgof_diagnosis.py`, the traffic adapter, and
`refc/cxl_model/diagnosis.py`. The manifest's exact source map is incorporated
by its pinned hash; no source changes are needed for this design.

The five inspected scope files are in runs `20261101T025305Z_3219`,
`20261101T025436Z_7803`, `20261101T025606Z_12313`,
`20261101T025739Z_16918`, and `20261101T025918Z_21788` (6401–6405).
Their emitted schemas are `cxl-cgof-rtl-diagnosis-scope-v1` and raw
`cxl-cgof-diagnosis-rtl-v1`. Exploration supplied 40 jobs, not 40 independent
replicates. Its Q2 Sparse ordering deltas were 0, −1, −1, −1, −1 cycles;
Heavy maximum-gap deltas were 0, +1, −1, 0, −1. These observations motivate
the directional primary question; they contribute **zero** confirmation rows.

Preserve failed design 6301, run `20261101T024757Z_2732`, and its hashes in the
correction manifest. Heavy work 1024 crossed a second close and became effective
Low despite execution PASS. Exclude it from estimates and controls here.
6302–6305 were not executed; none may be substituted into this study. Seed 6201
remains wiring smoke only. Do not pool any 6201/6301–6305/6401–6405 observations
with confirmation data or use them as additional degrees of freedom.

## Frozen matrix and unit of replication

| Factor | Fixed value |
| --- | --- |
| Evidence | `SCHEDULER_RTL`, scheduler boundary only |
| N / D / W | 4 / 16 / 256 |
| Mode / profile | `finite-heavy` / `near` |
| Heavy work / source | 256 requests / source 0, no role switching |
| Generation | Heavy p=0.80; each Sparse source 1–3 p=0.02 |
| Active ready | `bursty`, p=0.90, period=100: slots 0–89 ready, 90–99 stalled |
| Drain | Existing no-new-generation, forced `ready=1` cleanup |
| Quotas | CGOF(1:1), CGOF(2:1); Low weight stays 1 |
| Ordering | `oldest-first` (OF), `eligible-round-robin` (RR) |
| Lanes | mixed and isolated for every setting |
| Seeds, in order | 6501, 6502, 6503, 6504, 6505, 6506, 6507, 6508, 6509, 6510, 6511, 6512, 6513, 6514, 6515, 6516, 6517, 6518, 6519, 6520 |
| Concurrency | Sequential seeds; `--jobs 1 --make-jobs 1` |
| Output | `artifacts/implementation/cgof-rtl-ordering-confirmation/<new-run-id>/` |

The four settings are Q1-OF, Q1-RR, Q2-OF, Q2-RR. There are exactly 160 jobs,
80 mixed/isolated pairs, 80 lint configurations (four per seed), 20 campaign
traffic pytest invocations (five existing tests each), and 160 RTL tests.
The separate preflight also runs the traffic test file; its overlapping tests
are not added to these campaign counts or presented as unique RTL coverage.
Expected campaign JUnit inventory: 180 files, 160 RTL cases and 100 traffic
cases. Each seed's runner has 13 steps: four lint, one pytest, eight cocotb.

The independent analysis unit is a **seed block containing all eight jobs**.
Mixed/isolated lanes, four settings, sources, requests and gaps within a seed
are paired observations, not independent replicates. Each seed has equal
weight regardless of its Sparse or gap count. No sample-size expansion,
seed replacement, outlier deletion, optional stopping, or best-run selection.

## Questions, populations and estimands fixed before execution

Primary RQ: under this bounded finite-Heavy protocol, does eligible-RR reduce
the completed Sparse run-level G→F nearest-rank P99 at quota 2:1, and is that
reduction greater than at 1:1, on matched generation cohorts?

For seed s, let S(s,q,o) be the mixed-lane endpoint below. Define in cycles:

```text
d1(s) = S(s,Q1,RR) - S(s,Q1,OF)
d2(s) = S(s,Q2,RR) - S(s,Q2,OF)
I(s)  = d2(s) - d1(s)
      = [S(s,Q2,RR)-S(s,Q1,RR)] - [S(s,Q2,OF)-S(s,Q1,OF)]
```

The primary estimand is the joint finite-seed distribution of `(d2,I)`:
its two equally weighted arithmetic means, medians, ranges, signed counts,
and the joint success fraction defined below. Negative d2 means lower Sparse
waiting with RR at Q2; negative I means the RR-minus-OF change is more negative
at Q2 than Q1. This is an explicit quota × ordering interaction, not merely a
Q2 comparison. No logarithms, ratios, standardization, trimming, or weighting
by completed requests are applied to these primary cycle differences.

This is a finite-cohort scheduler experiment, not an estimate of the stationary
99th percentile or an application latency distribution. The primary population
contains every request generated as Sparse before each job's Heavy completion,
and subsequently completed, including drain completions. It measures the whole
declared active-plus-cleanup protocol. It cannot isolate active-only waiting or
the effect that would occur under continued bursty readiness during drain.

**Matched-cohort eligibility:** independently reconstruct the full ordered list
of `(generation_cycle, source, descriptor)` Sparse arrivals over each mixed
job's active interval. Require equality of that list across all four settings
within each of the 20 seeds for the matched-cohort primary claim. Equality of
counts or of a common prefix alone is insufficient. A cohort mismatch is not
an RTL failure: retain all jobs, finish valid scheduled seeds, report the
protocol-dependent cohort difference, and label the primary claim INCONCLUSIVE.
Do not restrict latency histograms to an invented common subset or silently
drop that seed. The current fields do not identify individual completion times
for a retrospective common-prefix latency analysis.

Secondary RQs: what happens to Heavy interruptions, finite completion duration,
and Q1 ordering invariance? Report all predeclared contrasts, without promoting
a favorable secondary endpoint into the primary decision:

- Mixed S: d1, both quota changes Q2−Q1 at OF and RR, and d2/I already defined.
- Heavy gap endpoints Hmax, H99 and R99: RR−OF at each quota and Q2−Q1 at each
  ordering, separately in mixed and isolated lanes; also their within-lane
  difference-of-differences I using the same formula.
- Completion: mixed-minus-isolated active cycles A and active-cycle ratio R for
  every seed/setting; their two ordering contrasts, two quota contrasts, and I.
- Q1 ordering equality and isolated-setting equality: exact observed endpoint
  equality across all 20 seeds, with number and magnitude of discrepancies.
  Equality is descriptive, not an equivalence test or full action-trace proof.

## Canonical endpoint dictionary and accounting

In this table `d` means one raw result JSON, equivalently
`diagnosis_scope.json.results[i].data`. There is no extra raw `data` wrapper.
`g = d.generation_roles`. Higher S/H/A/R means longer waiting/interruption or
completion duration; higher counts are quantities, not performance rankings.

| Symbol | Exact emitted path or derivation | Unit / population |
| --- | --- | --- |
| S, primary | `g.latency.sparse.generation_to_fire.p99_nearest_rank` | cycles; completed Sparse generation cohort, mixed only, includes drain |
| Smax, Smean, nS | Same object: `.max`, `.mean`, `.count`; retain `.histogram` | cycles / cycles / requests; descriptive diagnostic |
| Hmax | `d.heavy.max_wall_gap`; require equality to `g.heavy_gaps.samples.inter_service.wall_cycles.max` | cycles; active Heavy accepted-but-not-fired backlog episodes |
| H99 | `g.heavy_gaps.samples.inter_service.wall_cycles.p99_nearest_rank` | cycles; same completed inter-service gap population |
| R99 | `g.heavy_gaps.samples.inter_service.eligible_ready_opportunities.p99_nearest_rank` | ready opportunities; same gaps, not wall cycles |
| C | `d.active_cycles` | cycles from epoch start through final Heavy fire, inclusive |
| A | mixed C − isolated C within `(seed,quota,ordering)` | cycles; finite completion overhead |
| R | `finite_heavy_pairs[].heavy_active_cycle_ratio_mixed_over_isolated`; independently recompute mixed C / isolated C | dimensionless; no log transform, not throughput/bytes |
| Heavy timing | `d.heavy.completion_cycle`, `.first_release_cycle`, `.last_release_cycle`, `.first_release_to_last_fire` | zero-based cycles / elapsed cycles; completion=C−1, elapsed=completion−first release |
| Drain | `d.drain_cycles`; `d.metrics.phases.drain`; `d.metrics.cohorts["finite-heavy"].completed_by_phase` | cycles and per-source request counts |
| Cut pending, role r | `sum(g.at_cut[r].generated) - sum(g.at_cut[r].fired)` | requests pending at the active cut, not final censoring |
| Drain completed, role r | `sum(g.counts[r].fired) - sum(g.counts[r].active_fired)` | requests; cross-check phase/cohort counters |
| Final request censor, role r | `sum(g.counts[r].generated) - sum(g.counts[r].fired)` | requests; must be zero for accepted complete data |

Nearest-rank P99 is the value at 1-based rank `ceil(99*n/100)`, recomputed from
the integer-key histogram; use integer arithmetic `(99*n+99)//100`. Preserve
ties. Exploration nS was 17–28 and P99 equaled the run maximum in every mixed
job. This equality follows for nonempty n<100, not for arbitrary cohort sizes.
In confirmation always report nS, S and Smax; do not switch the primary endpoint
if an unexpected n≥100 makes S differ from Smax. No minimum of 17 is imposed,
no smoothing or interpolation, and no pooled-request P99 across seeds.

Five exploration jobs had one Sparse request pending at cut, completed during
one forced-ready drain cycle: 6402 Q2-OF and all four 6404 mixed settings.
Those five completions were included in S; they were not losses or zero waits.
Use exactly that full-completed-cohort convention in confirmation. Final request
censoring must be zero. Record cut pending and drain completed separately, even
when their totals coincide. Do not subtract a drain count from a latency
histogram: phase-specific Sparse latency samples are not emitted.

Gap populations must stay separate. `initial` includes the first eligible slot
of a new nonempty episode. `inter_service` counts slots after a preceding fire
while the Heavy accepted backlog remains nonempty. `terminated_by_empty` closes
an episode and may contain zero; it is not a completed inter-service wait.
`right_censored` and `left_censored_completed`, when present, remain their own
categories. Retain per-kind histograms/counts and
`g.heavy_gaps_per_source[].empty_terminated_episodes`. Never pool these kinds
or interpret Hmax as the largest interval including arbitrary idle time or
initial waiting. Hmax/H99/R99 use only `inter_service`; available censored-gap
counts accompany them, without imputation into the completed-gap estimand.
RoleBook uses accepted-minus-fired backlog here, not producer-plus-FIFO backlog.

Missing JSON fields, inconsistent histograms or identities are integrity failures,
not numeric zeros. An empty mixed Sparse cohort gives S=UNAVAILABLE and makes
the primary outcome INCONCLUSIVE; an isolated empty Sparse cohort is expected
and excluded from S by design. An empty inter-service population makes that
secondary endpoint UNAVAILABLE; never replace it with an initial gap. Keep the
fixed denominator 20 in primary reporting; do not quietly use complete-case n<20.

## Confirmatory decision and multiplicity

One primary claim, evaluated once after all 20 seeds; both clauses are necessary.
First require all execution/integrity/manipulation gates, no final request
censoring, available S in all 80 mixed results, and matched Sparse cohorts for
every seed. Then apply exactly:

```text
CONFIRMED iff
  d2(s) <= 0 AND I(s) <= 0 for EVERY one of the 20 seeds,
  AND count{s : d2(s) <= -1 AND I(s) <= -1} >= 15 of 20.
```

Thus ties are allowed in at most five seeds for the joint strict-improvement
criterion, but **no positive reversal** of either primary contrast is allowed.
Evaluate integer differences exactly, without rounding or an epsilon margin.
Any ordered primary statement must satisfy this rule over all 20 fresh seeds.

- **CONFIRMED:** every gate and the joint rule pass. Permitted language:
  “In the preregistered N4/D16/W256 near/bursty finite-Heavy protocol on these
  20 fresh seeds, RR reduced completed-cohort Sparse run-P99 more at 2:1 than
  at 1:1 under the specified no-reversal/15-seed rule.”
- **NOT_CONFIRMED:** all 20 valid, matched, available seed blocks exist, but
  either clause fails. Report reversals, ties, strict counts and effect sizes.
  This does not establish no effect, equivalence, or superiority of OF.
- **INCONCLUSIVE:** incomplete execution, failed manipulation/integrity,
  missing primary observations, final censoring, or any full-cohort mismatch.
  Report every observed row and the exact gate failure; no subset confirmation.

One cycle is the smallest resolvable nonzero difference for these integer
endpoints. Requiring joint improvement in 15/20 seeds demands a three-quarter
majority with a median improvement of at least one cycle in each component;
requiring zero reversals prevents a few large gains from masking regressions.
These are deliberately conservative, operational replication thresholds chosen
before fresh outcomes, not an empirically calibrated power calculation, an
application meaningfulness threshold, or a promise of 75% future-seed success.
Five exploratory seeds cannot establish statistical power for this criterion.

Multiplicity is handled by one conjunctive decision, not by picking any
successful endpoint or contrast. No p-values, bootstrap, permutation intervals,
formal population hypothesis tests, or inferential secondary decisions are
planned; therefore no unearned alpha/FWER guarantee is asserted. Report all
secondary seed-level contrasts, arithmetic means, medians, min/max and
negative/zero/positive counts, with available counts. Do not treat gaps or
requests as independent resamples. Any later uncertainty/resampling analysis
requires a separately labeled post hoc protocol and cannot change this verdict.
No aggregate policy score, universal winner, or Heavy noninferiority claim is
permitted, even if the Sparse primary claim is CONFIRMED.

## Collector sufficiency and acceptance gates

**No harness or collector change is required or planned.** The current fields
suffice for the finite-cohort endpoints, reconstruction checks, accounting and
bounded claim above. They do not suffice for matched individual completion
traces, active-only Sparse P99, phase-specific latency removal, full output
action equivalence, or sustained-bursty drain counterfactuals. Those remain
outside this confirmation. If such an endpoint becomes essential, stop before
execution and issue a separate versioned collector/preflight proposal and new
preregistration; do not retrofit old JSON or expand this plan after seeing seeds.

Before seed 6501: seal this plan/hash, validate the pinned source set and
preflight tests below, record the environment, verify seeds have no earlier
confirmation runs, and reserve exclusive execution ownership of this namespace.
No other agent may write source files while the campaign runs.

After each seed and **before** the next:

1. Require runner exit 0, final summary PASS, 13/13 steps PASS, four distinct
   lint parameter sets, one five-test traffic JUnit, eight one-test RTL JUnits,
   zero failures/errors/skips/expected rejections. Inspect logs for build/lint
   errors even when an OS process exits 0. No absent run counts as PASS.
2. Require `smoke=true`, `production_reviewed=false`, evidence kind
   SCHEDULER_RTL, eight unique job identities and four unique paired identities.
   `summary.scope="full"` only means all specified runner steps; it does not
   mean W5M/primary-matrix signoff. `--smoke` is the runner's W256 guard.
3. Cross-check command seed, directory run ID, config env job JSON, scope job,
   raw job, raw `params`, elaboration arguments and testbench identity.
   N_SRC=4, DEPTH=16, FAI_W=256, HIGH_WEIGHT=1/2, ELIGIBLE_RR=0/1 must agree.
   Pair key includes seed, mode, N, D, W, windows, Heavy work, profile, source
   schedule, ready pattern/period, quota and ordering; lane is its only difference.
4. Require exactly one classifier row per job: active phase, window 0,
   closing_cycle=255, and `255 < active_cycles < 512`. Every old/new state maps
   through EFFECTIVE_CLASS to High (H or B_H); source at/after close is 0.
   No later or drain close; active+drain cycles must stay below 512. Initial H,
   continuous classifier state and held-grant checks rely on the frozen native
   harness/model assertions. No new class assumption is inferred from endpoints.
5. Source hashes before/after, the execution-time current files, and every ZIP
   member must equal the planning-pinned 31-file map across all seeds. Preserve
   hashes of additional preflight files and the plan, Git dirty snapshot/diff,
   runtime/tool versions and command evidence. Do not refresh the historical pin
   to match changed sources. Confirm raw result equals its embedded scope data.
6. Reconstruct each full active traffic trace from serialized `trace_config`,
   including descriptor values, event order and ready; compare the emitted
   `trace_sha256`, generated counts, ready count, first/last Heavy release.
   This is an input replay, not rerunning scheduler simulation. For each of 80
   pairs, configs differ only in `include_sparse`; reconstructed Heavy+ready
   prefixes match through min(active cycles). Across each of the four planned
   setting contrasts in each lane, compare the full intended common prefix
   (including Sparse in mixed): 160 setting-prefix comparisons total.
   Label hashes `reconstructed_declared_prefix_sha256`; the raw results do not
   preserve separate observed Heavy-prefix hashes.
7. Check Heavy work=generated=fired=256 and completed=true, completion=C−1;
   all generated=accepted=fired per generation role and source. Reconcile total
   generated/accepted/fired, phase counts, cohort counts, active-cut pending,
   drain completions and final request censor=0. Require testbench conservation,
   no residual producer/FIFO/held/scoreboard work and no avoidable bubbles.
   Record gap censoring separately from request censoring. Retain all native
   coverage and credit/refill counters; zero in an unexercised coverage bin is
   not a waived failed assertion or proof of coverage closure.
8. Recompute histogram count/max/mean/nearest-rank, verify the duplicate Hmax
   path and recompute pair A/R. Record the full Sparse-cohort equality and
   endpoint availability flags without discarding data. These flags may block
   the primary claim but are not grounds to substitute a seed or stop early
   for a favorable/unfavorable efficacy result.

Structural/test/source/replay/conservation/manipulation failure stops further
seed launches and preserves all partial files. The runner internally has
`keep_going=True`: it may finish other jobs in the failing seed before returning;
do not describe this as stopping at the first failing RTL job. No later seed may
start. A primary sign reversal does **not** stop an otherwise valid campaign.
No automatic retry. A timeout or partial run is retained and yields INCONCLUSIVE;
no replacement seed or overwritten run is permitted under this registration.
If a command fails before creating any run, a documented correction of that
launch command may repeat the same seed, preserving both command records and
without changing matrix/source/analysis. Post-run repairs need a separate plan.

## Exact prospective preflight and execution commands

Execute in Ubuntu WSL Bash at the existing repository root, not PowerShell,
Windows Python, Git Bash or FastX. Machine-specific paths stay in existing local
configuration. Do not create another checkout or change global model/tool settings.
Use selected executor `CommandExecution` transcript records for these blocks,
capturing exact text, UTC start/end, stdout/stderr, exit status and any launch
failure. Archive those selected records under the new campaign namespace after
execution. Alternatively capture equivalent campaign-owned logs with exclusive
creation. Do not invent one aggregate OS exit code if commands ran separately.

Preflight (600-second cap per bounded Python command, no scheduler simulation):

```bash
source scripts/wsl_env.sh
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/scripts:$PWD/refc:$PWD/sim/experimental:$PWD"
test -f docs/reviews/ordering-rtl-confirmation-plan-20261101.md
test ! -e artifacts/implementation/cgof-rtl-ordering-confirmation
git rev-parse HEAD
git status --short
git diff --stat
sha256sum docs/reviews/ordering-rtl-confirmation-plan-20261101.md
python -B --version
verilator --version
python -B -c 'import cocotb,pytest; print("cocotb",cocotb.__version__,"pytest",pytest.__version__)'
/usr/bin/timeout --kill-after=30s 600s python -B - <<'PY'
import hashlib, json
from pathlib import Path
import run_rtl_diagnosis as r
p = Path('artifacts/implementation/cgof-rtl-ordering-exploration/correction-manifest-20261101T030414Z.json')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '4cc2aeac9c8976fe0186ef956439458f6e351605f96e825f108cf8877aa78d2b'
m = json.loads(p.read_text())
assert r.freeze_sources() == m['source_hashes_before'] == m['source_hashes_after']
assert set(range(6501,6521)).isdisjoint({6201, *range(6301,6306), *range(6401,6406)})
for name in ('scripts/test_run_rtl_diagnosis.py', 'refc/tests/test_diagnosis.py',
             'sim/experimental/test_cgof_diagnosis_traffic.py'):
    print(name, hashlib.sha256(Path(name).read_bytes()).hexdigest())
print('PREFLIGHT_SOURCE_PIN_PASS; not a simulation result')
PY
/usr/bin/timeout --kill-after=30s 600s python -B -m pytest -q -p no:cacheprovider \
  scripts/test_run_rtl_diagnosis.py \
  sim/experimental/test_cgof_diagnosis_traffic.py \
  refc/tests/test_diagnosis.py
```

Use the following function once per listed seed in the same environment. It
invokes the existing runner with only its namespace overridden, then performs
a bounded read-only mechanical gate on the new artifacts. It neither modifies
the harness nor runs another RTL test. Preserve its output as command evidence.
The complete acceptance checklist above remains binding, including independent
log/config inspection and final artifact manifest review; this helper is not a
claim that all review work has been automated.

```bash
run_confirmation_seed() {
  local confirmation_seed="$1"
  local confirmation_left=$((43200 - $(date +%s) + confirmation_start))
  (( confirmation_left > 0 )) || return 124
  local confirmation_cap=1800
  (( confirmation_left >= confirmation_cap )) || confirmation_cap=$confirmation_left
  /usr/bin/timeout --kill-after=30s "${confirmation_cap}s" \
    python -B - "$confirmation_seed" <<'PY'
import hashlib, itertools, json, sys, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import run_rtl_diagnosis as r
from cgof_diagnosis_traffic import DiagnosisTraffic
from cxl_model.fai_main_model import EFFECTIVE_CLASS, HIGH

seed = int(sys.argv[1])
assert 6501 <= seed <= 6520
r.NAME = 'cgof-rtl-ordering-confirmation'
root = Path('artifacts/implementation') / r.NAME
before_dirs = set(root.glob('*/'))
p = Path('artifacts/implementation/cgof-rtl-ordering-exploration/correction-manifest-20261101T030414Z.json')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '4cc2aeac9c8976fe0186ef956439458f6e351605f96e825f108cf8877aa78d2b'
pin = json.loads(p.read_text())['source_hashes_before']
assert r.freeze_sources() == pin
argv = ['--smoke', '--window', '256', '--mode', 'finite-heavy',
        '--policy', 'both', '--ordering', 'both', '--seed', str(seed),
        '--windows', '1', '--depth', '16', '--profile', 'near',
        '--heavy-work', '256', '--ready-pattern', 'bursty', '--ready-period', '100',
        '--jobs', '1', '--make-jobs', '1']
print(json.dumps({'runner': 'scripts/run_rtl_diagnosis.py', 'namespace': r.NAME,
                  'argv': argv}), flush=True)
code = r.main(argv)
if code:
    raise SystemExit(code)
new_dirs = set(root.glob('*/')) - before_dirs
assert len(new_dirs) == 1, 'run identity collision or concurrent writer'
directory = new_dirs.pop()
scope = json.loads((directory/'diagnosis_scope.json').read_text())
summary = json.loads((directory/'summary.json').read_text())
assert summary['run_id'] == directory.name and summary['milestone'] == r.NAME
assert summary['overall'] == 'PASS' and len(summary['steps']) == 13
assert all(x['status'] == 'PASS' for x in summary['steps'])
assert scope['schema'] == 'cxl-cgof-rtl-diagnosis-scope-v1'
assert scope['status'] == 'PASS' and scope['evidence_kind'] == 'SCHEDULER_RTL'
assert scope['smoke'] is True and scope['production_reviewed'] is False
assert scope['source_stable'] is True
assert scope['source_hashes'] == scope['source_hashes_after'] == pin == r.freeze_sources()
with zipfile.ZipFile(directory/'sources.zip') as z:
    assert len(z.namelist()) == len(pin) and set(z.namelist()) == set(pin)
    assert all(hashlib.sha256(z.read(n)).hexdigest() == h for n,h in pin.items())
assert len(scope['configs']) == 8
assert r.load_results(directory, scope['configs']) == scope['results']
assert r.paired_results(scope['results']) == scope['finite_heavy_pairs']
assert len(scope['results']) == 8 and len(scope['finite_heavy_pairs']) == 4
xmls = list((directory/'junit').glob('*.xml'))
assert len(xmls) == 9
for path in xmls:
    xml = ET.parse(path).getroot()
    assert all(len(list(xml.iter(tag))) == 0 for tag in ('failure','error','skipped'))
    assert len(list(xml.iter('testcase'))) == (5 if path.name.startswith('pytest_') else 1)
assert not list((directory/'results').glob('*_failure.json'))
rows, traffic, sparse_inputs = {}, {}, {}
for item in scope['results']:
    d, job = item['data'], item['job']
    key = (job['high_weight'], job['ordering'], job['lane'])
    assert key not in rows
    rows[key] = d
    assert d['schema'] == 'cxl-cgof-diagnosis-rtl-v1'
    for name,value in dict(seed=seed,n_src=4,depth=16,window=256,windows=1,
                           mode='finite-heavy',heavy_work=256,profile='near',
                           heavy_sources=None,ready_pattern='bursty',ready_period=100).items():
        assert job[name] == value, (name,job)
    assert 'max_active_cycles' not in job
    assert d['params'] == r.params(job)
    closes = d['classifier']
    assert len(closes) == 1 and 255 < d['active_cycles'] < 512
    assert d['active_cycles'] + d['drain_cycles'] < 512
    close = closes[0]
    assert (close['phase'],close['window'],close['closing_cycle']) == ('active',0,255)
    assert close['heavy_source_at_close'] == close['next_heavy_source'] == 0
    assert len(close['old_classes']) == len(close['classes']) == 4
    assert all(EFFECTIVE_CLASS[x] == HIGH for x in close['old_classes']+close['classes'])
    assert d['heavy']['completed'] is True
    assert d['heavy']['work'] == d['heavy']['generated'] == d['heavy']['fired'] == 256
    assert d['heavy']['completion_cycle'] == d['active_cycles']-1
    assert sum(d['generated']) == d['accepted'] == d['fired']
    for role,c in d['generation_roles']['counts'].items():
        assert c['generated'] == c['accepted'] == c['fired']
        cut = d['generation_roles']['at_cut'][role]
        assert cut['generated'] == c['generated'] and cut['fired'] == c['active_fired']
    assert d['metrics']['phases']['active']['avoidable_bubbles'] == 0
    gap = d['generation_roles']['heavy_gaps']['samples'].get('inter_service',{})
    assert d['heavy']['max_wall_gap'] == gap.get('wall_cycles',{}).get('max')
    t = DiagnosisTraffic('finite-heavy',seed,n_src=4,window=256,depth=16,windows=1,
                         heavy_work=256,profile='near',include_sparse=job['lane']=='mixed',
                         ready_pattern='bursty',ready_period=100)
    assert t.config() == d['trace_config']
    cohort = []
    for k in range(d['active_cycles']):
        events,ready = t.step(k)
        cohort.extend((k,h,desc) for h,desc in events if h != 0)
    assert t.sha256 == d['trace_sha256'] and t.generated == d['generated']
    assert t.ready_count == d['ready_cycles']
    assert t.first_heavy_release_cycle == d['heavy']['first_release_cycle']
    assert t.last_heavy_release_cycle == d['heavy']['last_release_cycle']
    traffic[key], sparse_inputs[key] = t, cohort
expected = set(itertools.product((1,2),('oldest-first','eligible-round-robin'),('mixed','isolated')))
assert set(rows) == expected
for q,o in itertools.product((1,2),('oldest-first','eligible-round-robin')):
    a,b = (q,o,'mixed'),(q,o,'isolated')
    ca,cb = dict(rows[a]['trace_config']),dict(rows[b]['trace_config'])
    ca.pop('include_sparse'); cb.pop('include_sparse')
    assert ca == cb
    n = min(rows[a]['active_cycles'],rows[b]['active_cycles'])
    assert traffic[a].heavy_ready_prefix_sha256(n) == traffic[b].heavy_ready_prefix_sha256(n)
contrasts = [((1,'oldest-first'),(1,'eligible-round-robin')),
             ((2,'oldest-first'),(2,'eligible-round-robin')),
             ((1,'oldest-first'),(2,'oldest-first')),
             ((1,'eligible-round-robin'),(2,'eligible-round-robin'))]
for lane in ('mixed','isolated'):
    for x,y in contrasts:
        a,b = (*x,lane),(*y,lane)
        n = min(rows[a]['active_cycles'],rows[b]['active_cycles'])
        assert traffic[a].scenario.input_prefix_sha256(n,lane=='mixed') == traffic[b].scenario.input_prefix_sha256(n,lane=='mixed')
cohorts = [sparse_inputs[k] for k in sorted(rows) if k[2] == 'mixed']
print(json.dumps({'seed':seed,'run_id':directory.name,'mechanical_gate':'PASS',
                  'full_sparse_cohort_match':all(c == cohorts[0] for c in cohorts),
                  'primary_verdict':'NOT_EVALUATED_UNTIL_ALL_20'}),flush=True)
PY
}
```

The exact twenty calls follow; their explicit seed list is fixed, not generated
from successful-run availability. Set a 12-hour
campaign wall-clock budget starting at the first seed and a 30-minute cap for
each seed including its mechanical gate. The inner runner's nominal 172800-second
cocotb timeout is not the campaign cap; GNU timeout here bounds the process group
(no `--foreground`). Allow at most a further 30 seconds for forced termination.
The executor must issue **one call at a time**, complete the remaining independent
log/config/accounting checks, and record its disposition before issuing the next
call. Do not batch-paste these calls into an unattended shell: the mechanical
gate does not replace that review. This requires no additional owner approval.

```bash
confirmation_start=$(date +%s)
run_confirmation_seed 6501
run_confirmation_seed 6502
run_confirmation_seed 6503
run_confirmation_seed 6504
run_confirmation_seed 6505
run_confirmation_seed 6506
run_confirmation_seed 6507
run_confirmation_seed 6508
run_confirmation_seed 6509
run_confirmation_seed 6510
run_confirmation_seed 6511
run_confirmation_seed 6512
run_confirmation_seed 6513
run_confirmation_seed 6514
run_confirmation_seed 6515
run_confirmation_seed 6516
run_confirmation_seed 6517
run_confirmation_seed 6518
run_confirmation_seed 6519
run_confirmation_seed 6520
```

Keep the function and campaign start time in the same WSL shell context; if
commands use separate shells, preserve the original start timestamp and function
definition rather than resetting the time budget. Do not mark an unperformed
review PASS. No seed is rerun to fill a missing row. Preserve timeout exit
124/137, exceptions, partial outputs and launch errors as failures.

## Artifact contract and final analysis

Every run keeps the existing runner artifacts: `config.json`, `commands.txt`,
`versions.txt`, `summary.json`, `diagnosis_scope.json`, `sources.zip`, `logs/`,
`junit/`, and `results/`. Runner directories use exclusive timestamp/PID creation.
Only the confirmation namespace's `latest.txt` may advance; it is a convenience
pointer, never final evidence selection. Identify seeds from verified argv/job
and directory identity, not whichever run `latest.txt` names at analysis time.

Create campaign evidence with exclusive new filenames in the confirmation
namespace: `manifest-<campaign-id>.json`, `acceptance-<campaign-id>.json`,
`pair-input-audit-<campaign-id>.json`, `analysis-<campaign-id>.json`, and
`command-records-<campaign-id>.json` (or equivalent preserved logs). Freeze and
hash any future extraction/audit code before applying the primary decision.
Its small self-check must cover signed interaction, ties, exactly 14 versus 15
joint improvements, one reversal, missing primary data, cohort mismatch,
histogram nearest rank and the separation of cut pending from final censoring.
This plan does not create or execute that analysis implementation.

The manifest must contain:

- Schema/version, UTC timestamps, plan path/hash, all historical context hashes,
  explicitly excluded failed-6301 reference, and discovery/confirmation seed roles.
- Requested planner/executor/reviewer models, invocation paths, reasoning,
  observable request/session IDs if available, fallbacks and effective model
  `UNKNOWN` unless independently evidenced. Never infer backend from routing.
- Git HEAD/branch, dirty-file inventory and diff evidence, before/after source
  hashes including untracked used sources, ZIP member checks, tool/module/OS
  versions, exact argv/env overrides, commands, log paths, exit/signal/timeout,
  retries/launch failures, and start/end times. Preserve stdout and stderr.
- A bijective seed→run-ID map for all 20 scheduled seeds, including NOT_RUN
  entries after a stop; all 160 planned job identities and 80 planned pairs.
- Per-file SHA-256 for every raw result, summary, config, scope, ZIP, JUnit,
  command/version/log file and derived audit/analysis artifact; source stability
  within and across seeds. Record counts as observed versus expected separately.
- Per-job classifier/effective-class gate, complete input replay status, per-pair
  common-prefix length/hashes, per-setting prefix checks, full Sparse-cohort
  length/hash/equality, and exact emitted schema versions.
- Per-role/source conservation, active-cut pending, drain completed, final
  request censoring, gap-kind counts/censoring, endpoint availability, native
  coverage/credit/refill counters and duplicate-path checks.
- Independent review dispositions for logs/config/JUnit/pairing, and separate
  execution, manipulation, estimand-eligibility and primary-claim statuses.

Analysis JSON contains all 160 job rows and 80 lane-pair rows, all four setting
contrasts × two lanes × 20 seeds (160 rows; Sparse isolated values explicitly
N/A), 80 pair-derived setting contrast rows, and 20 primary `(d1,d2,I)` rows.
Keep full raw reference/candidate values, delta, units, population, eligibility
and reason codes. Add the predeclared interaction summaries for each secondary
endpoint/lane. Do not let a derived report hide missing cells or mix old seeds.
No unavailable field is coerced to zero and no cohort/gap sample is promoted
to an independent seed. An external manifest records this plan's hash; the
plan and historical artifacts remain immutable after execution begins.

## Concise final reporting template

```text
Study: H2 ordering confirmation v1; SCHEDULER_RTL; N4/D16/W256;
near; finite Heavy=256/source0; bursty active ready=.9/period100; drain ready=1.
Plan SHA256 / campaign ID / source snapshot / tool versions: ...
Requested model / invocation / effort / effective model: ... / ... / ... / UNKNOWN.
Scheduled seeds: 6501–6520. Observed valid seed blocks: .../20.
Execution: .../160 jobs, .../80 pairs, .../80 lint, .../20 traffic invocations,
.../160 RTL tests; failures/skips/timeouts and NOT_RUN identities: ...
Controls: source/JUnit/replay/manipulation/conservation ...;
full Sparse-cohort match .../20; final censored requests ...;
cut pending / drain completed / gap censoring ... (separate columns).
Primary: d2<=0 in .../20; I<=0 in .../20;
joint d2<=-1 and I<=-1 in .../20; reversals ...; unavailable ... .
Means / medians / ranges of d2 and I: ... cycles; all seed rows linked.
Verdict: CONFIRMED | NOT_CONFIRMED | INCONCLUSIVE, exact rule/gate reason ... .
Sparse n/P99/max and drain populations: ... .
Secondary: complete Heavy-gap and active-duration contrast table, including
opposing directions and exact Q1/isolated endpoint equalities/discrepancies.
Scope: bounded finite-cohort protocol only; no universal winner, stationary
tail, active-only latency, CXL response, bytes/bandwidth or application claim.
Artifacts / manifest SHA256 / independent acceptance disposition: ... .
```

## Explicit exclusions

No W5M, additional seeds/profiles/readiness patterns, role switching, new depths
or windows, longer Heavy work, new RTL policy, Buffer feedback, primary-nine
replacement, PPA/STA/power, formal/CDC, CXL/system/application experiment,
latency-recovery claim, main-manuscript integration, or revisions to the prior
review/status/development documents. No scheduler performance or coverage result
is established by writing this plan. Its material risks are small discrete
Sparse cohorts, protocol-dependent stopping/drain behavior, and the possibility
that the strict all-seed controls or matched-cohort gate make it INCONCLUSIVE.
