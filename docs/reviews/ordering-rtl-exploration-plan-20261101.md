# CGOF quota × ordering intermittent-arrival RTL exploration plan

Date: 2026-11-01. Status: `PLANNED_BOUNDED_EXPLORATION`, not confirmation.
Target: `SCHEDULER_RTL`, N4/D16/W256, five fresh seeds, 40 jobs and 20
mixed/isolated pairs. This plan does not authorize a W5M production matrix,
PPA, formal/CDC, CXL-response, bandwidth, application, or latency-recovery claim.

## Provenance and baseline

- Requested planning model: `GPT6Astra(high)`.
- Spawn result: `Unknown model`; no Astra run is claimed.
- Owner-approved fallback used for this plan: `group/gpt-6.1-sol`, high effort.
- Backend effective model: `UNKNOWN` (the routing/request label is not backend
  model evidence).
- Repository: `C:\Users\USER\Documents\Coding Space\CXL\cxl-scheduler`.
- Branch: `experiment/main-sq`; HEAD at planning time:
  `99400ded42cc63c3b206bd5d13f51d36344b2689`.
- The worktree already contains many user changes and untracked files. Preserve
  them. Do not reset, clean, stash, commit, replace, or rewrite historical
  artifacts.

The only prior quota × ordering RTL evidence is seed 6201:
`artifacts/implementation/cgof-rtl-diagnosis/20261031T232608Z_1153/`.
It contains 8 W256 jobs / 4 mixed-isolated pairs with `heavy_work=256`,
near load and Bernoulli ready. It established wiring and result identity only.
Its mixed active cycles were 331 and isolated active cycles 325;
2:1 oldest showed Sparse P99 5 and Heavy max wall gap 5, while 2:1 eligible-RR
showed Sparse P99 4 and Heavy max wall gap 6. That opposing direction is a
reason to run a bounded matrix, not evidence for a winner.

The currently open H2 question is whether, under matched intermittent arrivals,
absolute High-credit size and eligible-source ordering independently change Sparse
tail waiting or Heavy service interruptions. Continuous-backlog equality and the
single-seed smoke do not answer that question.

## Fixed exploratory matrix

Use exactly:

| Factor | Fixed value |
| --- | --- |
| Sources / depth / window | N4 / D16 / W256 |
| Mode | `finite-heavy` |
| Offered load | `near` (`heavy_p=0.80`, `sparse_p=0.02`) |
| Heavy work | 1024 requests per lane |
| Heavy source schedule | Default source 0 (`--windows 1`, no role switching) |
| Sink readiness | `bursty`, `ready_p=0.90`, period 100 (90 ready slots, then 10 unavailable) |
| Quotas | `CGOF(1:1)` and `CGOF(2:1)` |
| Orderings | `oldest-first` and `eligible-round-robin` |
| Lanes | `mixed` and `isolated` |
| Fresh seeds | `6301, 6302, 6303, 6304, 6305` |

Seeds `6301–6305` are fresh and do not reuse the 6201 wiring smoke. Do not add
seeds, profiles, phases, ready patterns, D8/D32, W64/W5M, or a sixth lane after
seeing results. `heavy_work=1024` is deliberately about four W256 windows; it is
large enough to exercise repeated bursty-ready and intermittent-arrival
re-entry while remaining a bounded exploration. It is not a production length.

The four setting IDs are fixed:

| ID | High:Low | Ordering |
| --- | --- | --- |
| `Q1-OF` | 1:1 | oldest-first |
| `Q1-RR` | 1:1 | eligible-round-robin |
| `Q2-OF` | 2:1 | oldest-first |
| `Q2-RR` | 2:1 | eligible-round-robin |

Each `(seed, setting)` has one mixed and one isolated lane. Therefore:

- 5 seeds × 4 settings × 2 lanes = **40 SCHEDULER_RTL jobs**.
- 5 seeds × 4 settings = **20 mixed/isolated lane pairs**.
- Per seed there are four matched ordering contrasts and four matched quota
  contrasts after separating mixed and isolated lanes:
  - `Q1-OF -> Q1-RR`
  - `Q2-OF -> Q2-RR`
  - `Q1-OF -> Q2-OF`
  - `Q1-RR -> Q2-RR`

The arrow means `candidate - reference`; it does not assign a preferred policy.

## Primary descriptive endpoints

No endpoint is a production performance metric. Extract exactly these fields:

| Endpoint | Source path | Orientation |
| --- | --- | --- |
| Sparse G→F P99 | `data.generation_roles.latency.sparse.generation_to_fire.p99_nearest_rank` | Higher means longer completed Sparse scheduler waiting. Censored work is excluded, never zero-filled. |
| Heavy max wall gap | `data.heavy.max_wall_gap` (diagnostic source: `data.generation_roles.heavy_gaps.samples.inter_service.wall_cycles.max`) | Higher means a longer observed active-cycle service interruption. |
| Heavy wall-gap P99 | `data.generation_roles.heavy_gaps.samples.inter_service.wall_cycles.p99_nearest_rank` | Higher is worse; nearest-rank, as emitted by the existing statistics code. |
| Heavy ready-opportunity P99 | `data.generation_roles.heavy_gaps.samples.inter_service.eligible_ready_opportunities.p99_nearest_rank` | Higher means more ready slots elapsed during a gap. |
| Mixed/isolated active-cycle ratio | pair field `heavy_active_cycle_ratio_mixed_over_isolated` | `1.0` means equal active duration; greater than 1 means mixed lasted longer. This is not a completed-byte or bandwidth ratio. |

For each setting and seed, also retain without reinterpretation:

- `active_cycles`, `drain_cycles`, generated/accepted/fired counts, and all
  per-role generation-time cohort counts;
- Heavy completion cycle and first-release-to-last-fire interval;
- Sparse completed count and uncompleted/censored count;
- window closings and class snapshots;
- native coverage and credit/refill counters already emitted by the testbench.

For each matched contrast, report the raw reference value, candidate value, and
`candidate - reference` for every applicable endpoint. Sparse endpoints apply
to mixed lanes only; isolated lanes have no Sparse workload. Keep the 20
mixed/isolated lane pairs separate from the 40 setting contrasts.

Do not build an aggregate score, rank, p-value, confidence interval,
equivalence margin, or universal winner in this round. With five exploration
seeds, results are descriptive only. If every seed points in one direction, the
permitted statement is a bounded directional observation; it is not a
confirmation claim.

## Input and execution integrity

Before any run:

1. Record `git rev-parse HEAD`, `git status --short`, Python/pytest/Verilator
   versions, and SHA-256 hashes of all tracked/untracked source files used by
   `source_paths()` plus this plan.
2. Run the relevant tests below. A failed test blocks RTL execution.
3. Verify the current `cgof-rtl-ordering-exploration` evidence namespace does
   not already contain the run IDs about to be created. Never delete or replace
   an earlier run.
4. Run one seed command at a time with `--jobs 1 --make-jobs 1`; no parallel
   builds or simulations.

Use the existing runner through a namespace override that does not rewrite the
historical `cgof-rtl-diagnosis/latest.txt`:

```bash
cd '/mnt/c/Users/USER/Documents/Coding Space/CXL/cxl-scheduler'
source scripts/wsl_env.sh
export PYTHONPATH="$PWD/scripts:$PWD"

PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider \
  scripts/test_run_rtl_diagnosis.py \
  sim/experimental/test_cgof_diagnosis_traffic.py \
  refc/tests/test_diagnosis.py

run_order_seed() {
  local seed="$1"
  timeout --foreground 1800 \
    python -B -c 'import sys, run_rtl_diagnosis as r; r.NAME="cgof-rtl-ordering-exploration"; raise SystemExit(r.main(sys.argv[1:]))' \
      --smoke --window 256 --mode finite-heavy --policy both --ordering both \
      --seed "$seed" --windows 1 --depth 16 --profile near --heavy-work 1024 \
      --ready-pattern bursty --ready-period 100 --jobs 1 --make-jobs 1
}

run_order_seed 6301
run_order_seed 6302
run_order_seed 6303
run_order_seed 6304
run_order_seed 6305
```

`--smoke` is the existing CLI's W256/bounded execution guard, not a confirmation
label. The `r.NAME` override gives the campaign a new evidence namespace:
`artifacts/implementation/cgof-rtl-ordering-exploration/<run-id>/`. The original
seed-6201 artifact and its directory-level `latest.txt` remain untouched.

Per seed, the runner must produce exactly:

- 4 lint configurations: 1:1/2:1 × oldest-first/eligible-RR;
- 1 traffic pytest target containing its existing 5 tests;
- 8 cocotb jobs: 4 settings × mixed/isolated;
- 4 finite-Heavy lane pairs.

For all five seeds the expected totals are 20 lint configurations, 5 traffic
pytest invocations (25 tests), 40 cocotb jobs, and 20 lane pairs. Each command
has a 30-minute operational cap. Overall exploration cap: 3 hours. A timeout,
crash, source drift, or missing artifact is a failed campaign; preserve logs and
do not silently retry with a different seed.

## Pair and result acceptance

A campaign is executable-complete only if all of the following hold:

- every lint/pytest/cocotb step exits 0; `summary.json` has no FAIL, missing, or
  skipped step;
- every run has `source_stable=true` and identical before/after source hashes;
- each seed has exactly 8 passing results and 4 pairs, with unique
  `(seed, window, depth, quota, ordering, lane)` identities;
- `job`, `params`, `ELIGIBLE_RR`, and serialized result identity agree for every
  job;
- every lane reports Heavy generated=fired=1024, all generated work drains, and
  generation-role generated=accepted=fired; no writer, FIFO, or hold remains;
- the mixed and isolated scenario configurations agree after removing
  `include_sparse`; their declared Heavy source/events, bursty-ready period, and
  deterministic Heavy+ready prefix hash agree through
  `min(mixed.active_cycles, isolated.active_cycles)`;
- each pair's expected `ready_pattern=bursty`, `ready_period=100`,
  `heavy_work=1024`, `profile=near`, and `windows=1`;
- raw result, `diagnosis_scope.json`, source ZIP, commands, versions, logs, and
  JUnit files all exist and their SHA-256 values are recorded.

The existing `test_cgof_diagnosis_traffic.py` replay test and the runner's
job/parameter checks are necessary but not sufficient. The campaign acceptance
step must independently reconstruct the deterministic Heavy/ready prefix from
the serialized `trace_config` and record a `pair_input_audit.json`; it must not
claim pairing from elapsed time, trace hashes that differ only because one lane
has Sparse work, or a hard-coded boolean.

If a run completes but has zero completed Sparse requests, report
`SPARSE_SAMPLE_UNAVAILABLE`; do not encode zero latency. If a full window shows
an effective class other than High, preserve the data but mark the fixed-class
control `CONTROL_NOT_HELD`; do not convert that into a quota conclusion.

## Artifacts and evidence manifest

Each new run directory must retain:

```text
artifacts/implementation/cgof-rtl-ordering-exploration/<run-id>/
  config.json
  commands.txt
  versions.txt
  summary.json
  diagnosis_scope.json
  sources.zip
  logs/
  junit/
  results/
```

After all five runs, create a new campaign manifest without moving or rewriting
any run:

```text
artifacts/implementation/cgof-rtl-ordering-exploration/
  manifest-<UTC-timestamp>.json
  pair-input-audit-<UTC-timestamp>.json
  analysis-<UTC-timestamp>.json
```

The manifest must include:

- requested/fallback model provenance and backend effective model `UNKNOWN`;
- Git HEAD, dirty snapshot, Python/pytest/Verilator versions, exact commands,
  exit codes, start/end times, and each run ID;
- raw SHA-256 for every `summary.json`, `diagnosis_scope.json`, `sources.zip`,
  and result JSON;
- source-hash before/after equality;
- counts proving 40 jobs and 20 pairs;
- the fixed matrix and explicit exclusions;
- references to the 6201 smoke as prior context only.

The analysis file must contain one row per job and one row per matched contrast,
with endpoint units, orientation, null/censoring status, and no confidence
interval. The Markdown report, if produced, is a human-readable rendering of the
same JSON and must be labeled `bounded five-seed exploratory RTL evidence`.

## Stop, failure, and reporting rules

Stop and preserve evidence if any of these occurs:

- source hashes change during a run, a required source is missing, or output
  identity collides;
- any lint, compile, simulation, traffic test, or assertion fails;
- any expected job/pair is missing, duplicated, or mismatched;
- a heavy lane cannot complete 1024 requests or drains do not conserve work;
- a mixed/isolated Heavy+ready prefix differs;
- the operational timeout or total cap is exceeded.

Do not fix a failed result by changing the workload, deleting a seed, reusing a
history artifact, or selecting a favorable run. A purely infrastructural retry
is allowed only with a new run ID, the original failure retained, and the cause
recorded.

Regardless of outcome, the report must state:

- `SCHEDULER_RTL`, scheduler-boundary evidence only;
- five fresh exploration seeds, no confirmation or statistical equivalence;
- `fire/cycle` is not memory bandwidth;
- generation-to-fire is not CXL issue-to-response latency;
- no PPA, formal/CDC, calibrated CXL, application slowdown, or W5M result;
- mixed/isolated active-cycle ratio is not a completed-byte ratio;
- no winner may be declared unless a later, separately pre-registered
  confirmation plan defines the estimand, margin/test, and seed set.

## Scope exclusions

Not in this round: W5M production, more than five seeds, more workloads or
ready patterns, role switching, D8/D32, W64, Main/WRR/IWRR expansion, Buffer
feedback, RTL policy changes, PPA/STA, formal/CDC, CXL system simulation,
application measurement, or report-main-text integration.
